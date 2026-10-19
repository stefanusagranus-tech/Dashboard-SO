from fastapi import APIRouter, Depends
from services.supabase_client import get_supabase
from middleware.role import require_token

router = APIRouter(prefix="/api/broadcast", tags=["Broadcast"])

@router.get("/list")
async def list_broadcast(user: dict = Depends(require_token)):
    _sb = get_supabase()
    _res = _sb.table("broadcast").select("*").order("created_at", desc=True).execute()
    return {"success": True, "data": _res.data or []}