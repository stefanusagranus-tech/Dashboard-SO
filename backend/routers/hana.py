"""
Router Hana — Master Shift (AI-1)
====================================
Endpoint untuk bot Hana.

Bot ini fokus handle jadwal shift.

Rewrite v2 — Sprint 3 PART 2:
- Semua endpoint POST diproteksi Bearer token
- Personil add/delete khusus admin
- Save shift khusus operator+
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional

from middleware.rate_limit import limiter
from middleware.role import require_token, require_operator, require_admin

try:
    from services.ai_shift_manager import (
        chat_response,
        parse_shift_update,
        suggest_pengganti,
        ai_suggest_pengganti_text,
        check_conflict,
        ai_check_conflict_text,
        save_shift,
        save_batch,
        get_master_shift,
        check_konflik,
        add_personil,
        delete_personil,
        get_personil_aktif,
        get_shift_hari_ini,
        parse_tanggal,
        SHIFT_MAP,
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
    needs_confirm: Optional[bool] = False
    error: Optional[str] = None


class ParseRequest(BaseModel):
    text: str = Field(..., description="Text natural language")


class SuggestRequest(BaseModel):
    nama_libur: str = Field(..., description="Nama yang libur")
    tanggal: Optional[str] = Field(None, description="Tanggal (YYYY-MM-DD)")


class ConflictRequest(BaseModel):
    tanggal: str = Field(..., description="Tanggal (YYYY-MM-DD)")
    shift_map: dict = Field(..., description="Mapping nama -> kode shift")


class SaveShiftRequest(BaseModel):
    tanggal: str = Field(..., description="Tanggal (YYYY-MM-DD) atau natural language")
    nama: str = Field(..., description="Nama personil")
    kode_shift: str = Field(..., description="P7, S15, M22, O, CUTI")
    action: str = Field("update", description="'update' atau 'delete'")
    force: bool = Field(False, description="Force delete (hapus history)")


class SaveBatchRequest(BaseModel):
    tanggal: str = Field(..., description="Tanggal (YYYY-MM-DD) atau natural language")
    items: list[dict] = Field(..., description="List {nama, kode_shift}")


class MasterShiftQuery(BaseModel):
    tgl_start: Optional[str] = Field(None, description="YYYY-MM-DD")
    tgl_end: Optional[str] = Field(None, description="YYYY-MM-DD")
    nama_filter: Optional[str] = Field(None, description="Filter 1 personil")


class PersonilRequest(BaseModel):
    nama: str = Field(..., description="Nama personil")
    urutan: Optional[int] = Field(None, description="Urutan (opsional)")


class DeletePersonilRequest(BaseModel):
    nama: str = Field(..., description="Nama personil")
    force: bool = Field(False, description="True: hard delete + history")


# =========================================================
# HEALTH — PUBLIC
# =========================================================
@router.get("/health")
async def hana_health():
    return {
        "bot": "hana",
        "role": "Master Shift",
        "status": "ok" if _HANA_OK else "error",
        "error": _import_error,
    }


# =========================================================
# CHAT
# =========================================================
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def hana_chat_endpoint(
    request: Request,
    req: ChatRequest,
    user: dict = Depends(require_token),
):
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
            needs_confirm=_resp.get("needs_confirm", False),
        )
    except Exception as _e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# PARSE
# =========================================================
@router.post("/parse")
@limiter.limit("30/minute")
async def hana_parse_endpoint(
    request: Request,
    req: ParseRequest,
    user: dict = Depends(require_token),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _parsed = parse_shift_update(req.text)

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


# =========================================================
# SUGGEST
# =========================================================
@router.post("/suggest")
@limiter.limit("30/minute")
async def hana_suggest_endpoint(
    request: Request,
    req: SuggestRequest,
    user: dict = Depends(require_token),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        from datetime import datetime

        _tgl = None
        if req.tanggal:
            _tgl = datetime.strptime(req.tanggal, "%Y-%m-%d").date()

        _text = ai_suggest_pengganti_text(req.nama_libur, _tgl)
        _structured = suggest_pengganti(req.nama_libur, _tgl)

        return {
            "success": True,
            "text": _text,
            "candidates": _structured,
        }

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# CONFLICT
# =========================================================
@router.post("/conflict")
@limiter.limit("30/minute")
async def hana_conflict_endpoint(
    request: Request,
    req: ConflictRequest,
    user: dict = Depends(require_token),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        from datetime import datetime

        _tgl = datetime.strptime(req.tanggal, "%Y-%m-%d").date()

        _text = ai_check_conflict_text(_tgl, req.shift_map)
        _issues = check_conflict(_tgl, req.shift_map)

        return {
            "success": True,
            "text": _text,
            "issues": _issues,
            "has_conflict": len(_issues) > 0,
        }

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# SAVE SHIFT — Butuh operator+
# =========================================================
@router.post("/save-shift")
@limiter.limit("30/minute")
async def hana_save_shift_endpoint(
    request: Request,
    req: SaveShiftRequest,
    user: dict = Depends(require_operator),
):
    """Simpan/update/hapus 1 shift."""
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        from datetime import datetime
        _tgl = req.tanggal
        if not (len(_tgl) == 10 and _tgl[4] == "-"):
            _tgl = parse_tanggal(_tgl)

        _res = save_shift(
            tanggal=_tgl,
            nama=req.nama,
            kode_shift=req.kode_shift,
            action=req.action,
            force=req.force,
        )

        if not _res.get("success"):
            raise HTTPException(status_code=400, detail=_res.get("message", "Gagal"))

        return _res

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# SAVE BATCH — Butuh operator+
# =========================================================
@router.post("/save-batch")
@limiter.limit("20/minute")
async def hana_save_batch_endpoint(
    request: Request,
    req: SaveBatchRequest,
    user: dict = Depends(require_operator),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _tgl = req.tanggal
        if not (len(_tgl) == 10 and _tgl[4] == "-"):
            _tgl = parse_tanggal(_tgl)

        _res = save_batch(items=req.items, tanggal=_tgl)

        if not _res.get("success"):
            raise HTTPException(status_code=400, detail=_res.get("message", "Gagal"))

        return _res

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# MASTER SHIFT — query
# =========================================================
@router.post("/master-shift")
@limiter.limit("60/minute")
async def hana_master_shift_endpoint(
    request: Request,
    req: MasterShiftQuery,
    user: dict = Depends(require_token),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _res = get_master_shift(
            tgl_start=req.tgl_start,
            tgl_end=req.tgl_end,
            nama_filter=req.nama_filter,
        )

        if not _res.get("success"):
            raise HTTPException(status_code=500, detail=_res.get("error", "Gagal"))

        return _res

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# PERSONIL — list
# =========================================================
@router.get("/personil")
@limiter.limit("60/minute")
async def hana_personil_endpoint(
    request: Request,
    user: dict = Depends(require_token),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _res = get_personil_aktif()
        return {
            "success": True,
            "data": _res,
            "total": len(_res),
        }

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# PERSONIL — ADD (admin only)
# =========================================================
@router.post("/personil/add")
@limiter.limit("20/minute")
async def hana_personil_add_endpoint(
    request: Request,
    req: PersonilRequest,
    user: dict = Depends(require_admin),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _res = add_personil(nama=req.nama, urutan=req.urutan)

        if not _res.get("success"):
            raise HTTPException(status_code=400, detail=_res.get("message", "Gagal"))

        return _res

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# PERSONIL — DELETE (admin only)
# =========================================================
@router.post("/personil/delete")
@limiter.limit("20/minute")
async def hana_personil_delete_endpoint(
    request: Request,
    req: DeletePersonilRequest,
    user: dict = Depends(require_admin),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _res = delete_personil(nama=req.nama, force=req.force)

        if not _res.get("success"):
            raise HTTPException(status_code=400, detail=_res.get("message", "Gagal"))

        return _res

    except HTTPException:
        raise
    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])


# =========================================================
# SHIFT HARI INI
# =========================================================
@router.get("/shift-hari-ini")
@limiter.limit("60/minute")
async def hana_shift_hari_ini_endpoint(
    request: Request,
    user: dict = Depends(require_token),
):
    if not _HANA_OK:
        raise HTTPException(status_code=503, detail=f"Hana error: {_import_error}")

    try:
        _res = get_shift_hari_ini()
        return _res

    except Exception as _e:
        raise HTTPException(status_code=500, detail=str(_e)[:200])