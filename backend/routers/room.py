from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.supabase_client import get_supabase
from middleware.role import require_token

router = APIRouter(prefix="/api/room", tags=["Room Chat"])

class SendMessageRequest(BaseModel):
    room_id: int
    pesan: str

@router.get("/list")
async def list_rooms(user: dict = Depends(require_token)):
    _sb = get_supabase()
    _res = _sb.table("chat_rooms").select("*").execute()
    return {"success": True, "data": _res.data or []}

@router.get("/messages/{room_id}")
async def get_messages(room_id: int, user: dict = Depends(require_token)):
    _sb = get_supabase()
    _res = _sb.table("messages").select("*, users(nama_lengkap, username)").eq("room_id", room_id).order("created_at").execute()
    return {"success": True, "data": _res.data or []}

@router.post("/send")
async def send_message(req: SendMessageRequest, user: dict = Depends(require_token)):
    if not req.pesan.strip(): raise HTTPException(400, "Pesan kosong")
    _sb = get_supabase()
    _res = _sb.table("messages").insert({
        "room_id": req.room_id,
        "user_id": user.get("id"),
        "pesan": req.pesan.strip()
    }).execute()
    return {"success": True, "data": _res.data}