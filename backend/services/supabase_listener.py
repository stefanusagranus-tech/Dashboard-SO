# backend/services/supabase_listener.py
import os
import asyncio
from supabase import acreate_client  # ✅ PAKAI ASYNC CLIENT
from routers.realtime import manager

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def start_supabase_listener():
    try:
        print("⏳ Memulai Supabase Realtime Listener...")
        # ✅ PAKAI acreate_client (async)
        supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
        
        def handle_insert(payload):
            new_record = payload.get("new", {})
            target = new_record.get("target_username")
            
            print(f"🔔 [LISTENER] Notif baru masuk untuk: {target}")
            
            notif_data = {
                "type": new_record.get("type"),
                "message": new_record.get("message"),
                "sender_name": new_record.get("sender_name"),
                "room_id": new_record.get("room_id"),
            }

            loop = asyncio.get_event_loop()
            if target == "ALL":
                loop.create_task(manager.broadcast_to_all({"event": "new_notification", "data": notif_data}))
            else:
                loop.create_task(manager.send_personal_message({"event": "new_notification", "data": notif_data}, target))

        channel = supabase.channel("public:notifications")
        channel.on_postgres_changes(
            event="INSERT",
            schema="public",
            table="notifications",
            callback=handle_insert
        )
        
        await channel.subscribe()
        print("✅ Realtime Supabase Listener Aktif di Background (Async Mode)!")
    except Exception as e:
        print(f"❌ GAGAL START LISTENER: {e}")