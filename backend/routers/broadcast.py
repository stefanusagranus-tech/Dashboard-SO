from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.supabase_client import get_supabase
from middleware.role import require_token, require_admin # Pastiin require_admin ada

router = APIRouter(prefix="/api/broadcast", tags=["Broadcast"])

class CreateBroadcastRequest(BaseModel):
    judul: str
    pesan: str
    tipe: str = "info"

@router.get("/list")
async def list_broadcast(user: dict = Depends(require_token)):
    _sb = get_supabase()
    _res = _sb.table("broadcast").select("*").order("created_at", desc=True).execute()
    return {"success": True, "data": _res.data or []}

@router.post("/create")
async def create_broadcast(req: CreateBroadcastRequest, user: dict = Depends(require_admin)):
    if not req.judul.strip() or not req.pesan.strip():
        raise HTTPException(400, "Judul dan pesan wajib diisi")
    
    _sb = get_supabase()
    _res = _sb.table("broadcast").insert({
        "judul": req.judul.strip(),
        "pesan": req.pesan.strip(),
        "tipe": req.tipe
    }).execute()
    
    return {"success": True, "data": _res.data}