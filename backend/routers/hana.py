"""
Router Hana — Master Shift (AI-1)
====================================
Endpoint untuk bot Hana.

Bot ini fokus handle jadwal shift:
- Cek jadwal (hari ini, besok, dst)
- Update shift (atur/pindah)
- Hapus shift
- Saran pengganti
- Chat general tentang shift

Flow: Android → FastAPI → Groq → balik ke Android
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional


try:
    from services.ai_shift_manager import (
        chat_response,
        parse_shift_update,
        suggest_pengganti,
        ai_suggest_pengganti_text,
        check_conflict,
        ai_check_conflict_text,
    )
    _HANA_OK = True
    _import_error = None
except ImportError as _e:
    _HANA_OK = False
    _import_error = str(_e)


router = APIRouter(prefix="/api/hana", tags=["Hana"])


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
    intent: Optional[str] = None
    parsed: Optional[dict] = None
    engine: Optional[str] = None
    error: Optional[str] = None


class ParseRequest(BaseModel):
    text: str = Field(..., description="Text natural language")


class SuggestRequest(BaseModel):
    nama_libur: str = Field(..., description="Nama yang libur")
    tanggal: Optional[str] = Field(None, description="Tanggal (YYYY-MM-DD)")


class ConflictRequest(BaseModel):
    tanggal: str = Field(..., description="Tanggal (YYYY-MM-DD)")
    shift_map: dict = Field(..., description="Mapping nama -> kode shift")


# =========================================================
# ENDPOINTS
# =========================================================
@router.get("/health")
async def hana_health():
    """Cek status Hana."""
    return {
        "bot": "hana",
        "role": "Master Shift",
        "status": "ok" if _HANA_OK else "error",
        "error": _import_error,
    }


@router.post("/chat", response_model=ChatResponse)
async def hana_chat_endpoint(req: ChatRequest):
    """
    Endpoint chat Hana.
    
    Deteksi intent otomatis:
    - Query: "jadwal hari ini?"
    - Update: "atur Reza ke siang"
    - Delete: "hapus shift Pandu"
    """
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message kosong")

    try:
        _history = [{"role": m.role, "content": m.content} for m in req.history]

        _resp = chat_response(req.message, _history)

        return ChatResponse(
            text=_resp.get("text", ""),
            intent=_resp.get("intent"),
            parsed=_resp.get("parsed"),
            engine=_resp.get("engine"),
        )

    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


@router.post("/parse")
async def hana_parse_endpoint(req: ParseRequest):
    """
    Parse natural language jadi struktur shift.
    
    Body: {"text": "Atur Reza dan Pandu libur besok"}
    """
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _parsed = parse_shift_update(req.text)

        # Convert date object ke string biar JSON-serializable
        if "tanggal" in _parsed and hasattr(_parsed["tanggal"], "isoformat"):
            _parsed["tanggal"] = _parsed["tanggal"].isoformat()

        if "tanggal_list" in _parsed:
            _parsed["tanggal_list"] = [
                d.isoformat() if hasattr(d, "isoformat") else str(d)
                for d in _parsed["tanggal_list"]
            ]

        return {"success": True, "data": _parsed}

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


@router.post("/suggest")
async def hana_suggest_endpoint(req: SuggestRequest):
    """
    Saran pengganti kalau ada yang libur.
    
    Body: {"nama_libur": "REZA", "tanggal": "2026-10-14"}
    """
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        from datetime import datetime

        _tgl = None
        if req.tanggal:
            _tgl = datetime.strptime(req.tanggal, "%Y-%m-%d").date()

        # Pakai versi AI-text
        _text = ai_suggest_pengganti_text(req.nama_libur, _tgl)

        # Plus structured data
        _structured = suggest_pengganti(req.nama_libur, _tgl)

        return {
            "success": True,
            "text": _text,
            "candidates": _structured,
        }

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


@router.post("/conflict")
async def hana_conflict_endpoint(req: ConflictRequest):
    """
    Cek konflik shift.
    
    Body: {
        "tanggal": "2026-10-14",
        "shift_map": {"REZA": "S15", "PANDU": "P7"}
    }
    """
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        from datetime import datetime

        _tgl = datetime.strptime(req.tanggal, "%Y-%m-%d").date()

        # Pakai versi AI-text
        _text = ai_check_conflict_text(_tgl, req.shift_map)

        # Plus structured issues
        _issues = check_conflict(_tgl, req.shift_map)

        return {
            "success": True,
            "text": _text,
            "issues": _issues,
            "has_conflict": len(_issues) > 0,
        }

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])
