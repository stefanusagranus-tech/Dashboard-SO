from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.supabase_client import get_supabase
from middleware.role import require_token
from services.ai_so_input import yui_chat
# Kalau ada service buat hana, rei, kurumi, import juga di sini
# from services.ai_hana import hana_chat
# from services.ai_rei import rei_chat
# from services.ai_kurumi import kurumi_chat

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
    _res = _sb.table("messages").select("*, users(nama_lengkap, username, avatar_url)").eq("room_id", room_id).order("created_at").execute()
    return {"success": True, "data": _res.data or []}

@router.post("/send")
async def send_message(req: SendMessageRequest, user: dict = Depends(require_token)):
    if not req.pesan.strip(): 
        raise HTTPException(400, "Pesan kosong")
    
    _sb = get_supabase()
    _pesan = req.pesan.strip()
    
    # ✅ 1. Simpan pesan user
    _res = _sb.table("messages").insert({
        "room_id": req.room_id,
        "user_id": user.get("id"),
        "pesan": _pesan
    }).execute()
    
    # ✅ 2. Deteksi Tag Bot (@Yui, @Hana, @Rei, @Kurumi)
    _lower = _pesan.lower()
    _bot_id = None
    _bot_name = None
    if _lower.startswith("@yui"): _bot_id, _bot_name = "yui", "Yui"
    elif _lower.startswith("@hana"): _bot_id, _bot_name = "hana", "Hana"
    elif _lower.startswith("@rei"): _bot_id, _bot_name = "rei", "Rei"
    elif _lower.startswith("@kurumi"): _bot_id, _bot_name = "kurumi", "Kurumi"
    
    # ✅ 3. Kalau ada tag, panggil AI
    if _bot_id:
        # Hapus tag dari pesan buat dikirim ke AI
        _clean_msg = _pesan.split(" ", 1)[1] if " " in _pesan else ""
        if not _clean_msg:
            _clean_msg = "Halo, apa kabar?"
        
        try:
            # SEMENTARA: Cuma Yui yang disambungin. Nanti tinggal tambahin logic lain.
            if _bot_id == "yui":
                _ai_resp = yui_chat(_clean_msg, [])
                _ai_text = _ai_resp.get("text") if isinstance(_ai_resp, dict) else str(_ai_resp)
            else:
                _ai_text = f"Halo! Aku {_bot_name}, masih dalam pengembangan. Sabar ya! 😊"
            
            # Simpan jawaban bot ke database (user_id = None / system)
            _sb.table("messages").insert({
                "room_id": req.room_id,
                "user_id": None, # None = Bot
                "pesan": f"🤖 {_bot_name}: {_ai_text}"
            }).execute()
        except Exception as _e:
            print(f"[ROOM_BOT] Gagal panggil AI: {_e}")
            _sb.table("messages").insert({
                "room_id": req.room_id,
                "user_id": None,
                "pesan": f"🤖 {_bot_name}: Maaf, aku lagi error. Coba lagi nanti."
            }).execute()
    
    return {"success": True, "data": _res.data}