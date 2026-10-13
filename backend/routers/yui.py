"""
Router Yui — Data Entry (AI-2)
================================
Endpoint untuk bot Yui.

Fokus:
- Input SO via chat
- Rekap SO
- List item
- Top items
"""

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from middleware.rate_limit import limiter, get_real_ip

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
    text: str = Field(..., description="Text natural language")
    rak_list: list[str] = Field(default_factory=list, description="List rak valid")


class RekapRequest(BaseModel):
    mode: str = Field("bulan_ini", description="'hari_ini', 'minggu_ini', 'bulan_ini', 'custom'")
    tgl_start: Optional[str] = Field(None, description="YYYY-MM-DD (buat custom)")
    tgl_end: Optional[str] = Field(None, description="YYYY-MM-DD (buat custom)")


class TopItemsRequest(BaseModel):
    mode: str = Field("bulan_ini")
    limit: int = Field(10, ge=1, le=100)
    only_minus: bool = Field(True, description="True: minus, False: plus")
    order: str = Field("desc", description="'desc' atau 'asc'")


# =========================================================
# ENDPOINTS
# =========================================================
@router.get("/health")
async def yui_health():
    """Cek status Yui."""
    return {
        "bot": "yui",
        "role": "Data Entry",
        "status": "ok" if _YUI_OK else "error",
        "error": _import_error,
    }


# =========================================================
# CHAT — dengan intent detection
# =========================================================
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def yui_chat_endpoint(request: Request, req: ChatRequest):
    """
    Endpoint chat Yui dengan intent detection.
    Rekap → fetch data dulu, baru LLM.
    """
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message kosong")

    try:
        _msg = req.message.strip().lower()
        _history = [{"role": m.role, "content": m.content} for m in req.history]

        # ============================================================
        # INTENT: REKAP
        # ============================================================
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

        # ============================================================
        # INTENT: TOP ITEMS
        # ============================================================
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

        # ============================================================
        # FALLBACK: CHAT BIASA
        # ============================================================
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
# PARSE — Natural language
# =========================================================
@router.post("/parse")
async def yui_parse_endpoint(req: ParseRequest):
    """Parse natural language input SO. Response flat."""
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _parsed = parse_natural_language(req.text, req.rak_list or [])
        return _parsed
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# REKAP
# =========================================================
@router.post("/rekap")
async def yui_rekap_endpoint(req: RekapRequest):
    """Rekap SO."""
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        from datetime import datetime

        _tgl_start = None
        _tgl_end = None

        if req.mode == "custom":
            if not req.tgl_start or not req.tgl_end:
                raise HTTPException(
                    status_code=400,
                    detail="Mode custom butuh tgl_start dan tgl_end",
                )
            _tgl_start = datetime.strptime(req.tgl_start, "%Y-%m-%d").date()
            _tgl_end = datetime.strptime(req.tgl_end, "%Y-%m-%d").date()

        _hasil = rekap_so(
            mode=req.mode,
            tgl_start=_tgl_start,
            tgl_end=_tgl_end,
        )

        if not _hasil.get("success"):
            raise HTTPException(status_code=500, detail=_hasil.get("error", "Gagal rekap"))

        return _hasil

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# TOP ITEMS
# =========================================================
@router.post("/top-items")
async def yui_top_items_endpoint(req: TopItemsRequest):
    """Top item berdasarkan selisih."""
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _hasil = get_top_items(
            mode=req.mode,
            limit=req.limit,
            only_minus=req.only_minus,
            order=req.order,
        )

        if not _hasil.get("success"):
            raise HTTPException(status_code=500, detail=_hasil.get("error", "Gagal"))

        return _hasil

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# ITEMS BY RAK
# =========================================================
@router.get("/items-by-rak/{rak_id}")
async def yui_items_by_rak_endpoint(rak_id: str):
    """List item di rak tertentu — semua item (minus + plus)."""
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _hasil = get_items_by_rak(rak_id, mode="bulan_ini", show_all=True)
        return _hasil
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])