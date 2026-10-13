"""
Router Yui — Data Entry (AI-2)
================================
Endpoint untuk bot Yui.

Bot ini fokus handle data entry:
- Input SO via chat
- Input SPD via chat
- Rekap SO
- List item
- Export laporan

Flow: Android → FastAPI → Groq/Supabase → balik ke Android
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from services.yui_rekap import rekap_so, get_top_items, get_items_by_rak

try:
    from services.ai_so_input import (
        yui_chat,
        parse_natural_language,
        parse_file_text,
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
# FIX BUG #4 — Chat dengan intent detection
# =========================================================
@router.post("/chat", response_model=ChatResponse)
async def yui_chat_endpoint(req: ChatRequest):
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
        # INTENT DETECTION — REKAP
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

            # Build text context yang ringkas
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

            # Prompt ke LLM — SURUH PAKAI DATA INI, JANGAN NGARANG
            _prompt = f"""Kamu Yui, Data Entry Specialist Toko C383.

=== DATA REAL DARI DATABASE ===
{_context}
=== END DATA ===

Bos: "{req.message}"

TUGAS: Rangkum data di atas jadi balasan singkat (max 8 baris).
- PAKAI ANGKA DARI DATA DI ATAS, JANGAN NGARANG
- Sebut periode, total rak, total item, total nominal
- Kalau nominal negatif, bilang "selisih minus"
- Gaya: santai, "Oke Bos", "Sip", "Beres"
- Kalau user minta list, tampilkan list rak
"""

            _ok, _text, _model, _err = _call_yui_groq(
                _prompt, function="chat_rekap", temperature=0.3,
            )

            if not _ok:
                return ChatResponse(
                    text=f"Data ada tapi gagal format: {str(_err)[:80]}",
                    intent="rekap",
                    data={
                        "total_rak": _data["total_rak"],
                        "total_item": _data["total_item"],
                        "total_nominal": _data["total_nominal"],
                    },
                    error=_err,
                )

            return ChatResponse(
                text=_text.strip(),
                model=_model,
                intent="rekap",
                data={
                    "periode": _data["periode"],
                    "total_rak": _data["total_rak"],
                    "total_item": _data["total_item"],
                    "total_nominal": _data["total_nominal"],
                    "list_rak": _data.get("list_rak", [])[:10],
                },
                error=None,
            )

        # ============================================================
        # INTENT DETECTION — TOP ITEMS
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

                _prompt = f"""Kamu Yui. Data dari database:
{_context}

Bos: "{req.message}"
Rangkum jadi balasan singkat (max 10 baris). PAKAI ANGKA DARI DATA."""

                _ok, _text, _model, _err = _call_yui_groq(
                    _prompt, function="chat_top", temperature=0.3,
                )
                if _ok:
                    return ChatResponse(
                        text=_text.strip(),
                        model=_model,
                        intent="top_items",
                        data=_data,
                    )

        # ============================================================
        # FALLBACK — CHAT BIASA (TANPA DATA)
        # ============================================================
        _history_str = ""
        for _m in _history[-6:]:
            _history_str += f"{_m.get('role', 'user')}: {_m.get('content', '')}\n"

        _prompt = f"""Kamu Yui — Data Entry & Audit Specialist Toko C383.

=== TUGAS ===
1. Input data SO & SPD
2. Edit / hapus data
3. Rekap data FAKTUAL
4. Filter data

=== BATASAN ===
- JANGAN analisis trend/insight/rekomendasi
- Kalau user minta analisis, arahin ke Rei
- Kalau user minta data, JANGAN NGARANG. Bilang: "Kirim command
  spesifik Bos — misal 'rekap SO bulan ini' biar aku query database."

Riwayat: {_history_str}
Bos: "{req.message}"

Balas sebagai Yui, singkat max 6 baris.
"""

        _ok, _text, _model, _err = _call_yui_groq(
            _prompt, function="chat", temperature=0.7,
        )

        if not _ok:
            return ChatResponse(
                text=f"Waduh error Bos. ({str(_err)[:50]})",
                intent="chat",
                error=_err,
            )

        return ChatResponse(
            text=_text.strip(),
            model=_model,
            intent="chat",
        )

    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# FIX BUG #1 — Parse langsung return, gak dibungkus
# =========================================================
@router.post("/parse")
async def yui_parse_endpoint(req: ParseRequest):
    """
    Parse natural language input SO.
    Response flat (gak double-nested).
    """
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _parsed = parse_natural_language(req.text, req.rak_list or [])
        # ✅ FIX: langsung return, jangan dibungkus {"success": True, "data": ...}
        return _parsed

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# FIX BUG #3 — items-by-rak pake fungsi baru
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