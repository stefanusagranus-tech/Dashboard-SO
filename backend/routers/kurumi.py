"""
Router Kurumi — Chief of Staff (AI-0)
========================================
Endpoint untuk bot Kurumi.

Bot ini adalah LEADER — bisa jawab semua, tapi fokusnya:
- Rangkum laporan (hari/minggu/bulan)
- Kirim laporan (text/PDF/Excel)
- Chat general
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

# Rate limiter
from middleware.rate_limit import limiter

# Import service
try:
    from services.ai_core import (
        kurumi_chat_response,
        kurumi_summarize,
        kurumi_generate_report,
    )
    _KURUMI_OK = True
    _import_error = None
except ImportError as _e:
    _KURUMI_OK = False
    _import_error = str(_e)


router = APIRouter(prefix="/api/kurumi", tags=["Kurumi"])


# =========================================================
# SCHEMA
# =========================================================
class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' atau 'assistant'")
    content: str = Field(..., description="Isi pesan")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Pesan user")
    session_id: str = Field(..., description="ID session")
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    text: str
    model: Optional[str] = None
    file: Optional[dict] = None
    error: Optional[str] = None


class SummarizeRequest(BaseModel):
    period: str = Field("hari", description="'hari', 'minggu', atau 'bulan'")


class ReportRequest(BaseModel):
    period: str = Field("hari", description="'hari', 'minggu', atau 'bulan'")
    format: str = Field("text", description="'text', 'pdf', atau 'excel'")


# =========================================================
# HEALTH
# =========================================================
@router.get("/health")
async def kurumi_health():
    """Cek status Kurumi."""
    return {
        "bot": "kurumi",
        "role": "Chief of Staff",
        "status": "ok" if _KURUMI_OK else "error",
        "error": _import_error,
    }


# =========================================================
# CHAT
# =========================================================
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def kurumi_chat_endpoint(request: Request, req: ChatRequest):
    """
    Endpoint chat Kurumi.
    
    Body:
    {
        "message": "Rangkum hari ini dong",
        "session_id": "kurumi_20261013_140500",
        "history": [...]
    }
    """
    if not _KURUMI_OK:
        raise HTTPException(
            status_code=503,
            detail=f"Kurumi module error: {_import_error}",
        )

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message kosong")

    try:
        _history = [{"role": m.role, "content": m.content} for m in req.history]

        _resp = kurumi_chat_response(req.message, _history)

        if isinstance(_resp, dict):
            _text = _resp.get("text", "")
            _file = _resp.get("file")
        else:
            _text = str(_resp)
            _file = None

        return ChatResponse(text=_text, file=_file)

    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# SUMMARIZE
# =========================================================
@router.post("/summarize", response_model=ChatResponse)
@limiter.limit("30/minute")
async def kurumi_summarize_endpoint(request: Request, req: SummarizeRequest):
    """
    Endpoint rangkum Kurumi.
    
    Body: {"period": "hari" | "minggu" | "bulan"}
    """
    if not _KURUMI_OK:
        raise HTTPException(status_code=503, detail=f"Kurumi error: {_import_error}")

    _valid_periods = ["hari", "minggu", "bulan"]
    if req.period not in _valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Period harus salah satu dari: {', '.join(_valid_periods)}",
        )

    try:
        _summary = kurumi_summarize(period=req.period)
        return ChatResponse(text=_summary or "")

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# REPORT
# =========================================================
@router.post("/report")
@limiter.limit("10/minute")
async def kurumi_report_endpoint(request: Request, req: ReportRequest):
    """
    Endpoint generate laporan.
    
    Body: {"period": "hari", "format": "text" | "pdf" | "excel"}
    """
    if not _KURUMI_OK:
        raise HTTPException(status_code=503, detail=f"Kurumi error: {_import_error}")

    _valid_formats = ["text", "pdf", "excel"]
    if req.format not in _valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Format harus salah satu dari: {', '.join(_valid_formats)}",
        )

    try:
        _report = kurumi_generate_report(period=req.period, format=req.format)

        if not _report.get("success"):
            raise HTTPException(status_code=500, detail=_report.get("content", "Gagal generate"))

        import base64
        _content = _report.get("content")

        if isinstance(_content, (bytes, bytearray)):
            _content_b64 = base64.b64encode(_content).decode("utf-8")
        else:
            _content_b64 = _content

        return {
            "success": True,
            "filename": _report.get("filename", f"laporan.{req.format}"),
            "mime": _report.get("mime", "application/octet-stream"),
            "format": req.format,
            "content_b64": _content_b64,
        }

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])
        