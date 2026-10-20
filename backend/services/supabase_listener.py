# backend/services/supabase_listener.py
import os
from supabase import create_client
from routers.realtime import manager  # ✅ FIX: Ambil manager dari routers

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def start_supabase_listener():
    # Inisialisasi client Supabase (bisa sinkron, Supabase-py handle sendiri)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Fungsi callback kalau ada data baru di tabel notifications
    def handle_insert(payload):
        new_record = payload.get("new", {})
        target = new_record.get("target_username")
        
        notif_data = {
            "type": new_record.get("type"),
            "message": new_record.get("message"),
            "sender_name": new_record.get("sender_name"),
            "room_id": new_record.get("room_id"),
            "target": target
        }

        # Karena callback ini sinkron, kita lempar ke async task manager
        import asyncio
        loop = asyncio.get_event_loop()
        
        if target == "ALL":
            loop.create_task(manager.broadcast_to_all({"event": "new_notification", "data": notif_data}))
        else:
            loop.create_task(manager.send_personal_message({"event": "new_notification", "data": notif_data}, target))

    # Subscribe ke tabel notifications
    channel = supabase.channel("public:notifications")
    channel.on_postgres_changes(
        event="INSERT",
        schema="public",
        table="notifications",
        callback=handle_insert
    )
    
    # Jalanin listener
    channel.subscribe()
    print("✅ Realtime Supabase Listener Aktif di Background!")