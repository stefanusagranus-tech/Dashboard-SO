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


@router.post("/chat", response_model=ChatResponse)
async def yui_chat_endpoint(req: ChatRequest):
    """
    Endpoint chat Yui.
    
    Deteksi intent otomatis:
    - Input SO: "Q51 minus 28rb PIC Pandu"
    - Input SPD: "input spd hari ini 12.750.800"
    - Rekap: "rekap SO bulan ini"
    - List item: "list item minus tertinggi"
    """
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message kosong")

    try:
        _history = [{"role": m.role, "content": m.content} for m in req.history]

        _resp = yui_chat(req.message, _history)

        if isinstance(_resp, dict):
            _text = _resp.get("text", "")
            _model = _resp.get("model")
        else:
            _text = str(_resp)
            _model = None

        return ChatResponse(text=_text, model=_model)

    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


@router.post("/parse")
async def yui_parse_endpoint(req: ParseRequest):
    """
    Parse natural language input SO.
    
    Body: {"text": "Q51 minus 28rb PIC Pandu", "rak_list": ["Q51", "S11"]}
    """
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _parsed = parse_natural_language(req.text, req.rak_list or [])
        return {"success": True, "data": _parsed}

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


@router.post("/rekap")
async def yui_rekap_endpoint(req: RekapRequest):
    """
    Rekap SO.
    
    Body: {"mode": "bulan_ini"} atau {"mode": "custom", "tgl_start": "2026-10-01", "tgl_end": "2026-10-12"}
    """
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


@router.post("/top-items")
async def yui_top_items_endpoint(req: TopItemsRequest):
    """
    Top item berdasarkan selisih.
    
    Body: {"mode": "bulan_ini", "limit": 10, "only_minus": true, "order": "desc"}
    """
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


@router.get("/items-by-rak/{rak_id}")
async def yui_items_by_rak_endpoint(rak_id: str):
    """List item di rak tertentu."""
    if not _YUI_OK:
        raise HTTPException(status_code=503, detail=f"Yui error: {_import_error}")

    try:
        _hasil = get_items_by_rak(rak_id)
        return _hasil

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])
