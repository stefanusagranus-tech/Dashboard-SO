# backend/routers/realtime.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.supabase_client import get_supabase  # ✅ Import fungsi, bukan variabel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/realtime", tags=["Realtime"])

class ConnectionManager:
    def __init__(self):
        # Menyimpan koneksi aktif berdasarkan username
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        username = username.upper() # Pastiin selalu uppercase
        if username not in self.active_connections:
            self.active_connections[username] = []
        self.active_connections[username].append(websocket)
        logger.info(f"User {username} connected to WebSocket.")

    def disconnect(self, websocket: WebSocket, username: str):
        username = username.upper()
        if username in self.active_connections:
            if websocket in self.active_connections[username]:
                self.active_connections[username].remove(websocket)
            if not self.active_connections[username]:
                del self.active_connections[username]
        logger.info(f"User {username} disconnected.")

    async def send_personal_message(self, message: dict, username: str):
        username = username.upper()
        if username in self.active_connections:
            for connection in self.active_connections[username]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def broadcast_to_all(self, message: dict):
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

# =========================================================
# ENDPOINT: WEBSOCKET UNTUK FRONTEND
# =========================================================
@router.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    username = username.upper()
    await manager.connect(websocket, username)
    try:
        while True:
            # Kita cuma butuh koneksi tetap hidup
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, username)
    except Exception:
        manager.disconnect(websocket, username)

# =========================================================
# ENDPOINT: HITUNG NOTIF BELUM DIBACA
# =========================================================
@router.get("/unread-count/{username}")
async def get_unread_count(username: str):
    try:
        sb = get_supabase()
        if sb is None:
            return {"success": False, "count": 0, "error": "DB Error"}
        
        # Panggil SQL function langsung (bypass RLS)
        response = sb.rpc("get_unread_count", {"p_username": username.upper()}).execute()
        
        count = response.data if isinstance(response.data, int) else 0
        return {"success": True, "count": count}
    except Exception as e:
        return {"success": False, "count": 0, "error": str(e)}
    
@router.get("/list/{username}")
async def get_notif_list(username: str):
    try:
        sb = get_supabase()
        if sb is None:
            return {"success": False, "data": []}

        response = sb.table("notifications") \
            .select("*") \
            .eq("target_username", username.upper()) \
            .eq("is_read", False) \
            .order("created_at", desc=True) \
            .execute()
        
        return {"success": True, "data": response.data or []}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}