"""
Router Yui — Data Entry (AI-2)
================================
Endpoint untuk bot Yui.
Fokus: chat, rekap, list item, top items, save SPD/SO, upload file.

Rewrite v4 — Sprint 3 PART 2:
- Semua endpoint POST diproteksi Bearer token (require_token / require_operator)
- Endpoint /health tetep public
"""

from fastapi import APIRouter, HTTPException, Request, File, UploadFile, Depends
from pydantic import BaseModel, Field
from typing import Optional
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo

from middleware.rate_limit import limiter
from middleware.role import require_token, require_operator


try:
    from services.ai_so_input import (
        yui_chat,
        parse_natural_language,
        parse_file_text,
        yui_chat_with_context,
    )
    from services.yui_rekap import (
        rekap_so,
        get_top_items,
        get_items_by_rak,
    )
    from services.input_handler import save_input_harian
    from services.spd_calculator import save_spd_harian
    from services.file_reader import read_file, detect_file_type
    _YUI_OK = True
    _import_error = None
except ImportError as _e:
    _YUI_OK = False
    _import_error = str(_e)


router = APIRouter(prefix="/api/yui", tags=["Yui"])


# =========================================================
# SCHEMA
# =========================================================
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="Pesan user")
    session_id: str = Field(..., description="ID session")
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    text: str
    model: Optional[str] = None
    intent: Optional[str] = None
    data: Optional[dict] = None
    error: Optional[str] = None


class ParseRequest(BaseModel):
    text: str
    rak_list: list[str] = Field(default_factory=list)


class RekapRequest(BaseModel):
    mode: str = Field("bulan_ini")
    tgl_start: Optional[str] = None
    tgl_end: Optional[str] = None


class TopItemsRequest(BaseModel):
    mode: str = Field("bulan_ini")
    limit: int = Field(10, ge=1, le=100)
    only_minus: bool = Field(True)
    order: str = Field("desc")


class SaveSpdRequest(BaseModel):
    tanggal: str = Field(..., description="YYYY-MM-DD")
    nominal: int = Field(..., description="Nominal SPD dalam rupiah")
    keterangan: Optional[str] = ""


class SaveSoItem(BaseModel):
    rak_id: str
    plu: str
    nama_produk: str
    qty_sistem: int = 0
    qty_fisik: int = 0
    qty_var: int = 0
    nominal_adjust: float = 0
    pic: Optional[str] = ""


class SaveSoRequest(BaseModel):
    tanggal: str = Field(..., description="YYYY-MM-DD")
    items: list[SaveSoItem]
    keterangan: Optional[str] = ""
    pic_default: Optional[str] = ""


class ParseSpdRequest(BaseModel):
    text: str


class RakStatusRequest(BaseModel):
    mode: str = "bulan_ini"
    tgl_start: Optional[str] = None
    tgl_end: Optional[str] = None


class SpdListRequest(BaseModel):
    mode: str = "bulan_ini"
    tgl_start: Optional[str] = None
    tgl_end: Optional[str] = None


class TopRakRequest(BaseModel):
    mode: str = "bulan_ini"
    tgl_start: Optional[str] = None
    tgl_end: Optional[str] = None
    limit: int = Field(500, ge=1, le=1000)


class ItemsByRakRequest(BaseModel):
    mode: str = "bulan_ini"
    tgl_start: Optional[str] = None
    tgl_end: Optional[str] = None


class TopItemsExtendedRequest(BaseModel):
    mode: str = "bulan_ini"
    tgl_start: Optional[str] = None
    tgl_end: Optional[str] = None
    limit: Optional[int] = None
    search: str = ""
    order_by: str = "nominal_desc"
    sign: str = "minus"


class StatusAnalysisRequest(BaseModel):
    mode: str = "bulan_ini"
    tgl_start: Optional[str] = None
    tgl_end: Optional[str] = None


# =========================================================
# HEALTH — PUBLIC (nggak butuh token)
# =========================================================
@router.get("/health")
async def yui_health():
    return {
        "bot": "yui",
        "role": "Data Entry",
        "status": "ok" if _YUI_OK else "error",
        "error": _import_error,
    }


# =========================================================
# CHAT — Butuh token
# =========================================================
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def yui_chat_endpoint(
    request: Request,
    req: ChatRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message kosong")

    try:
        _msg = req.message.strip().lower()
        _history = [{"role": m.role, "content": m.content} for m in req.history]

        # INTENT: REKAP
        _is_rekap = any(k in _msg for k in [
            "rekap", "rekapan", "total so", "list so",
            "breakdown", "rincian so", "summary so",
        ])

        if _is_rekap:
            _mode = "bulan_ini"
            if "hari ini" in _msg or "harian" in _msg:
                _mode = "hari_ini"
            elif "minggu" in _msg or "weekly" in _msg:
                _mode = "minggu_ini"

            _data = rekap_so(mode=_mode)

            if not _data.get("success"):
                return ChatResponse(
                    text=f"Waduh gagal rekap Bos: {_data.get('error', 'unknown')[:80]}",
                    intent="rekap",
                    error=_data.get("error"),
                )

            _list_rak_str = "\n".join([
                f"- {r['rak_id']}: Rp {r['total']:,.0f} (PIC: {r.get('pic', '-')})"
                for r in _data.get("list_rak", [])[:15]
            ])

            _context = f"""PERIODE: {_data['periode']}
TOTAL RAK: {_data['total_rak']}
TOTAL ITEM: {_data['total_item']}
TOTAL NOMINAL: Rp {_data['total_nominal']:,.2f}

DETAIL RAK:
{_list_rak_str}
"""

            _resp = yui_chat_with_context(
                user_message=req.message,
                data_context=_context,
                intent="rekap",
                conversation_history=_history,
            )

            return ChatResponse(
                text=_resp.get("text", ""),
                model=_resp.get("model"),
                intent="rekap",
                data={
                    "periode": _data["periode"],
                    "total_rak": _data["total_rak"],
                    "total_item": _data["total_item"],
                    "total_nominal": _data["total_nominal"],
                    "list_rak": _data.get("list_rak", [])[:10],
                },
                error=_resp.get("error"),
            )

        # INTENT: TOP ITEMS
        _is_top = any(k in _msg for k in [
            "top item", "item minus", "item plus",
            "minus tertinggi", "plus tertinggi",
        ])

        if _is_top:
            _only_minus = "plus" not in _msg
            _data = get_top_items(
                mode="bulan_ini", limit=10, only_minus=_only_minus,
            )
            if _data.get("success"):
                _items_str = "\n".join([
                    f"- {it['plu']} {it.get('nama_produk', '')[:30]}: "
                    f"var {it['qty_var']}, Rp {it['nominal_adjust']:,.0f} "
                    f"(rak {it['rak_id']})"
                    for it in _data.get("items", [])[:10]
                ])
                _context = f"PERIODE: {_data['periode']}\nTOP ITEMS:\n{_items_str}"

                _resp = yui_chat_with_context(
                    user_message=req.message,
                    data_context=_context,
                    intent="top_items",
                    conversation_history=_history,
                )

                return ChatResponse(
                    text=_resp.get("text", ""),
                    model=_resp.get("model"),
                    intent="top_items",
                    data=_data,
                    error=_resp.get("error"),
                )

        # FALLBACK
        _resp = yui_chat(req.message, _history)

        if isinstance(_resp, dict):
            return ChatResponse(
                text=_resp.get("text", ""),
                model=_resp.get("model"),
                intent="chat",
            )
        return ChatResponse(text=str(_resp), intent="chat")

    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# PARSE NATURAL LANGUAGE (SO)
# =========================================================
@router.post("/parse")
@limiter.limit("30/minute")
async def yui_parse_endpoint(
    request: Request,
    req: ParseRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")
    try:
        _parsed = parse_natural_language(req.text, req.rak_list or [])
        return _parsed
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# PARSE SPD — Support tanggal custom
# =========================================================
_BULAN_MAP = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "ags": 8,
    "september": 9, "sep": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12,
}


def _extract_nominal(text):
    """
    Extract nominal dari text.
    Support: 12.750.800 / 5jt / 500rb / 500k
    Skip angka yang diikuti bulan (tanggal), skip tahun (20xx).
    """
    _lower = text.lower()

    _cleaned = re.sub(
        r'\d{1,2}\s+(januari|jan|februari|feb|maret|mar|april|apr|mei|'
        r'juni|jun|juli|jul|agustus|agu|ags|september|sep|oktober|okt|'
        r'november|nov|desember|des)\s*(\d{4})?',
        ' ',
        _lower,
    )

    _cleaned = re.sub(r'\d{4}-\d{1,2}-\d{1,2}', ' ', _cleaned)
    _cleaned = re.sub(r'\d{1,2}-\d{1,2}-\d{4}', ' ', _cleaned)
    _cleaned = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', ' ', _cleaned)

    _matches = re.findall(r'(\d[\d.,]*)\s*(jt|juta|rb|ribu|k)?', _cleaned)

    if not _matches:
        return 0

    _best_nominal = 0
    for _raw, _suffix in _matches:
        _raw_clean = _raw.replace(".", "").replace(",", "")
        try:
            _nominal = int(_raw_clean)
            if _suffix in ("jt", "juta"):
                _nominal *= 1_000_000
            elif _suffix in ("rb", "ribu", "k"):
                _nominal *= 1_000

            if _nominal < 100:
                continue
            if 2020 <= _nominal <= 2099:
                continue
            if _nominal > _best_nominal:
                _best_nominal = _nominal
        except Exception:
            continue

    return _best_nominal


def _extract_tanggal(text):
    """Extract tanggal dari text. Return YYYY-MM-DD atau None."""
    _lower = text.lower()
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))

    _match = re.search(
        r'(\d{1,2})\s+(januari|jan|februari|feb|maret|mar|april|apr|mei|'
        r'juni|jun|juli|jul|agustus|agu|ags|september|sep|oktober|okt|'
        r'november|nov|desember|des)\s*(\d{4})?',
        _lower,
    )
    if _match:
        try:
            _d = int(_match.group(1))
            _bulan = _BULAN_MAP.get(_match.group(2), 1)
            _tahun = int(_match.group(3)) if _match.group(3) else _now.year
            return date(_tahun, _bulan, _d).isoformat()
        except Exception:
            pass

    _match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if _match:
        try:
            return f"{_match.group(1)}-{int(_match.group(2)):02d}-{int(_match.group(3)):02d}"
        except Exception:
            pass

    _match = re.search(r'(\d{1,2})-(\d{1,2})-(\d{4})', text)
    if _match:
        try:
            return f"{_match.group(3)}-{int(_match.group(2)):02d}-{int(_match.group(1)):02d}"
        except Exception:
            pass

    _match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if _match:
        try:
            return f"{_match.group(3)}-{int(_match.group(2)):02d}-{int(_match.group(1)):02d}"
        except Exception:
            pass

    return None


@router.post("/parse-spd")
@limiter.limit("30/minute")
async def yui_parse_spd_endpoint(
    request: Request,
    req: ParseSpdRequest,
    user: dict = Depends(require_token),
):
    """
    Parse natural language SPD.

    Contoh:
    - "spd 5jt" → nominal 5.000.000, tanggal hari ini
    - "input spd tanggal 1 oktober 2026 16195070" → nominal 16.195.070, tanggal 2026-10-01
    """
    try:
        _text = req.text.strip()
        _nominal = _extract_nominal(_text)
        _tanggal = _extract_tanggal(_text)

        if not _tanggal:
            _tanggal = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()

        return {
            "success": _nominal > 0,
            "nominal": _nominal,
            "tanggal": _tanggal,
            "tanggal_from_user": bool(_extract_tanggal(_text)),
            "raw_text": req.text,
            "error": None if _nominal > 0 else "Gak nemu nominal SPD",
        }
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# SAVE SPD — Butuh role operator/admin
# =========================================================
@router.post("/save-spd")
@limiter.limit("20/minute")
async def yui_save_spd_endpoint(
    request: Request,
    req: SaveSpdRequest,
    user: dict = Depends(require_operator),
):
    """Simpan SPD ke tabel spd_harian."""
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _tgl = datetime.strptime(req.tanggal, "%Y-%m-%d").date()

        _ok, _msg = save_spd_harian(_tgl, req.nominal, req.keterangan or "")

        if not _ok:
            raise HTTPException(status_code=500, detail=_msg)

        _budget_so = req.nominal * 0.0015

        return {
            "success": True,
            "message": _msg,
            "tanggal": req.tanggal,
            "nominal": req.nominal,
            "budget_so": _budget_so,
        }
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# SAVE SO — Butuh role operator/admin
# =========================================================
@router.post("/save-so")
@limiter.limit("10/minute")
async def yui_save_so_endpoint(
    request: Request,
    req: SaveSoRequest,
    user: dict = Depends(require_operator),
):
    """Simpan SO ke so_hasil + so_rak_harian."""
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _tgl = datetime.strptime(req.tanggal, "%Y-%m-%d").date()

        if not req.items:
            raise HTTPException(status_code=400, detail="Items kosong")

        _items_by_rak = {}
        for _it in req.items:
            _rak = _it.rak_id.upper().strip()
            if not _rak:
                continue
            _items_by_rak.setdefault(_rak, []).append({
                "rak_id": _rak,
                "plu": _it.plu,
                "nama_produk": _it.nama_produk,
                "qty_sistem": _it.qty_sistem,
                "qty_fisik": _it.qty_fisik,
                "qty_var": _it.qty_var,
                "nominal_adjust": _it.nominal_adjust,
                "pic": (_it.pic or req.pic_default or "").upper(),
            })

        _saved_count = 0
        _error_count = 0
        _errors = []
        _total_nominal = 0
        _total_items = 0

        for _rak_id, _rak_items in _items_by_rak.items():
            _pic = _rak_items[0].get("pic", "")
            if not _pic:
                _error_count += 1
                _errors.append(f"Rak {_rak_id}: PIC kosong")
                continue

            try:
                _ok, _msg, _detail = save_input_harian(
                    tanggal=_tgl,
                    spd=0,
                    rak_items=_rak_items,
                    keterangan=req.keterangan or "Input via APK",
                    pic=_pic,
                    update_status_rak=True,
                )
                if _ok:
                    _saved_count += 1
                    _total_nominal += float(_detail.get("total_nominal", 0) or 0)
                    _total_items += int(_detail.get("hasil_saved", 0) or 0)
                else:
                    _error_count += 1
                    _errors.append(f"Rak {_rak_id}: {_msg[:100]}")
            except Exception as _e:
                _error_count += 1
                _errors.append(f"Rak {_rak_id}: {str(_e)[:100]}")

        return {
            "success": _saved_count > 0,
            "saved_count": _saved_count,
            "error_count": _error_count,
            "errors": _errors,
            "total_nominal": _total_nominal,
            "total_items": _total_items,
            "rak_saved": list(_items_by_rak.keys()),
        }

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# UPLOAD SO — Butuh role operator/admin
# =========================================================
@router.post("/upload-so")
@limiter.limit("10/minute")
async def yui_upload_so_endpoint(
    request: Request,
    file: UploadFile = File(...),
    tanggal: Optional[str] = None,
    rak_id: Optional[str] = None,
    user: dict = Depends(require_operator),
):
    """
    Upload file SO — parse & return preview.
    User confirm dulu, baru save via /save-so.
    """
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _bytes = await file.read()
        _filename = file.filename or "unknown"

        print(f"[UPLOAD-SO] File: {_filename} ({len(_bytes)} bytes)")

        _tanggal_dari_filename = None
        _match = re.search(r'(\d{1,2})-(\d{1,2})-(\d{4})', _filename)
        if _match:
            try:
                _tanggal_dari_filename = f"{_match.group(3)}-{int(_match.group(2)):02d}-{int(_match.group(1)):02d}"
                print(f"[UPLOAD-SO] Tanggal dari filename: {_tanggal_dari_filename}")
            except Exception:
                pass

        _read = read_file(_bytes, _filename)

        if not _read.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Gagal baca file: {_read.get('error', 'unknown')[:200]}"
            )

        _ctx = {"tanggal": tanggal, "rak_id": rak_id, "pic": None}
        _parse = parse_file_text(
            _read.get("text", ""),
            file_type=_read.get("type", "unknown"),
            context=_ctx,
            primary_df=_read.get("primary_df"),
        )

        if not _parse.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Gagal parse: {_parse.get('warnings', ['unknown'])[0][:200]}"
            )

        _data = _parse.get("data", {}) or {}
        _items = _data.get("items", [])
        _items_by_rak = _data.get("items_by_rak", {})
        _total_nominal = _data.get("total_nominal", 0)

        _tanggal_hasil = _data.get("tanggal") or tanggal or _tanggal_dari_filename

        if not _items_by_rak and _items:
            _grouped = {}
            for _it in _items:
                _r = _it.get("rak_id") or "UNKNOWN"
                _grouped.setdefault(_r, []).append(_it)
            _items_by_rak = _grouped

        return {
            "success": True,
            "filename": _filename,
            "file_type": _read.get("type", "unknown"),
            "tanggal": _tanggal_hasil,
            "tanggal_from_filename": bool(_tanggal_dari_filename),
            "total_items": len(_items),
            "total_rak": len(_items_by_rak),
            "total_nominal": _total_nominal,
            "items": _items,
            "items_by_rak": _items_by_rak,
            "model": _parse.get("model", ""),
            "warnings": _parse.get("warnings", []),
        }

    except HTTPException:
        raise
    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# REKAP
# =========================================================
@router.api_route("/rekap", methods=["GET", "POST"])
@limiter.limit("30/minute")
async def yui_rekap_endpoint(
    request: Request,
    req: RekapRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")
    try:
        _tgl_start = None
        _tgl_end = None
        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(400, "Mode custom butuh tgl_start & tgl_end")
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()

        _hasil = rekap_so(mode=req.mode, tgl_start=_tgl_start, tgl_end=_tgl_end)
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal rekap"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# TOP ITEMS
# =========================================================
@router.post("/top-items")
@limiter.limit("30/minute")
async def yui_top_items_endpoint(
    request: Request,
    req: TopItemsRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        _hasil = get_top_items(
            mode=req.mode, limit=req.limit,
            only_minus=req.only_minus, order=req.order,
        )
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# ITEMS BY RAK (GET)
# =========================================================
@router.get("/items-by-rak/{rak_id}")
@limiter.limit("30/minute")
async def yui_items_by_rak_endpoint(
    request: Request,
    rak_id: str,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        return get_items_by_rak(rak_id, mode="bulan_ini", show_all=True)
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# RAK STATUS
# =========================================================
@router.post("/rak-status")
@limiter.limit("30/minute")
async def yui_rak_status_endpoint(
    request: Request,
    req: RakStatusRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        from services.yui_rekap import get_rak_status
        _tgl_start = None
        _tgl_end = None
        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(400, "Butuh tgl_start & tgl_end")
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()
        _hasil = get_rak_status(mode=req.mode, tgl_start=_tgl_start, tgl_end=_tgl_end)
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# SPD LIST
# =========================================================
@router.post("/spd-list")
@limiter.limit("30/minute")
async def yui_spd_list_endpoint(
    request: Request,
    req: SpdListRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        from services.yui_rekap import get_spd_list
        _tgl_start = None
        _tgl_end = None
        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(400, "Butuh tgl_start & tgl_end")
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()
        _hasil = get_spd_list(mode=req.mode, tgl_start=_tgl_start, tgl_end=_tgl_end)
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# TOP RAK
# =========================================================
@router.post("/top-rak")
@limiter.limit("30/minute")
async def yui_top_rak_endpoint(
    request: Request,
    req: TopRakRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        from services.yui_rekap import get_top_rak
        _tgl_start = None
        _tgl_end = None
        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(400, "Butuh tgl_start & tgl_end")
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()
        _hasil = get_top_rak(mode=req.mode, tgl_start=_tgl_start, tgl_end=_tgl_end, limit=req.limit)
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# ITEMS BY RAK EXTENDED
# =========================================================
@router.post("/items-by-rak/{rak_id}")
@limiter.limit("60/minute")
async def yui_items_by_rak_extended_endpoint(
    request: Request,
    rak_id: str,
    req: ItemsByRakRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        from services.yui_rekap import get_items_by_rak_extended
        _tgl_start = None
        _tgl_end = None
        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(400, "Butuh tgl_start & tgl_end")
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()
        _hasil = get_items_by_rak_extended(rak_id=rak_id, mode=req.mode, tgl_start=_tgl_start, tgl_end=_tgl_end)
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# TOP ITEMS EXTENDED
# =========================================================
@router.post("/top-items-extended")
@limiter.limit("30/minute")
async def yui_top_items_extended_endpoint(
    request: Request,
    req: TopItemsExtendedRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        from services.yui_rekap import get_top_items_extended
        _tgl_start = None
        _tgl_end = None
        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(400, "Butuh tgl_start & tgl_end")
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()
        _hasil = get_top_items_extended(
            mode=req.mode, tgl_start=_tgl_start, tgl_end=_tgl_end,
            limit=req.limit, search=req.search, order_by=req.order_by, sign=req.sign,
        )
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])


# =========================================================
# STATUS ANALYSIS
# =========================================================
@router.post("/status-analysis")
@limiter.limit("30/minute")
async def yui_status_analysis_endpoint(
    request: Request,
    req: StatusAnalysisRequest,
    user: dict = Depends(require_token),
):
    if not _YUI_OK:
        raise HTTPException(503, f"Yui error: {_import_error}")
    try:
        from services.yui_rekap import get_status_analysis
        _tgl_start = None
        _tgl_end = None
        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(400, "Butuh tgl_start & tgl_end")
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()
        _hasil = get_status_analysis(mode=req.mode, tgl_start=_tgl_start, tgl_end=_tgl_end)
        if not _hasil.get("success"):
            raise HTTPException(500, _hasil.get("error", "Gagal"))
        return _hasil
    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(500, str(_e)[:200])