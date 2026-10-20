# backend/routers/realtime.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/realtime", tags=["Realtime"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        if username not in self.active_connections:
            self.active_connections[username] = []
        self.active_connections[username].append(websocket)
        logger.info(f"User {username} connected to WebSocket.")

    def disconnect(self, websocket: WebSocket, username: str):
        if username in self.active_connections:
            if websocket in self.active_connections[username]:
                self.active_connections[username].remove(websocket)
            if not self.active_connections[username]:
                del self.active_connections[username]
        logger.info(f"User {username} disconnected.")

    async def send_personal_message(self, message: dict, username: str):
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