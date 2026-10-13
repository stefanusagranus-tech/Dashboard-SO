"""
Router Rei — Analis SO (AI-3)
================================
Endpoint untuk bot Rei.

Bot ini fokus analisis:
- Analisis trend SO
- LPJ (Laporan Pertanggungjawaban)
- Prediksi SO bulan depan
- Insight & rekomendasi audit
- Top item minus/plus

Flow: Android → FastAPI → Gemini/Groq/OpenRouter → balik ke Android
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional


try:
    from services.ai_rei import rei_chat, rei_analisis
    _REI_OK = True
    _import_error = None
except ImportError as _e:
    _REI_OK = False
    _import_error = str(_e)


router = APIRouter(prefix="/api/rei", tags=["Rei"])


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
    data_context: Optional[str] = Field(default="", description="Konteks data SO")


class ChatResponse(BaseModel):
    text: str
    model: Optional[str] = None
    error: Optional[str] = None


class AnalisisRequest(BaseModel):
    prompt: str = Field(..., description="Prompt analisis")
    prefer: str = Field("gemini", description="'gemini', 'groq', atau 'openrouter'")


# =========================================================
# ENDPOINTS
# =========================================================
@router.get("/health")
async def rei_health():
    """Cek status Rei."""
    return {
        "bot": "rei",
        "role": "Analis SO",
        "status": "ok" if _REI_OK else "error",
        "error": _import_error,
    }


@router.post("/chat", response_model=ChatResponse)
async def rei_chat_endpoint(req: ChatRequest):
    """
    Endpoint chat Rei.
    
    Triple hybrid: Gemini → Groq → OpenRouter.
    """
    if not _REI_OK:
        raise HTTPException(status_code=503, detail=f"Rei error: {_import_error}")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message kosong")

    try:
        _history = [{"role": m.role, "content": m.content} for m in req.history]

        _result = rei_chat(
            user_message=req.message,
            conversation_history=_history,
            data_context=req.data_context or "",
        )

        return ChatResponse(
            text=_result.get("text", ""),
            model=_result.get("model"),
            error=_result.get("error"),
        )

    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


@router.post("/analisis", response_model=ChatResponse)
async def rei_analisis_endpoint(req: AnalisisRequest):
    """
    Endpoint analisis (single-turn, tanpa history).
    
    Body: {"prompt": "Analisis trend SO bulan ini", "prefer": "gemini"}
    """
    if not _REI_OK:
        raise HTTPException(status_code=503, detail=f"Rei error: {_import_error}")

    _valid_prefer = ["gemini", "groq", "openrouter"]
    if req.prefer not in _valid_prefer:
        raise HTTPException(
            status_code=400,
            detail=f"Prefer harus salah satu dari: {', '.join(_valid_prefer)}",
        )

    try:
        _text, _model, _err = rei_analisis(req.prompt, prefer=req.prefer)

        if _text:
            return ChatResponse(text=_text, model=_model)
        else:
            return ChatResponse(text="", model=None, error=_err)

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])
