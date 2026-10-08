"""
Chat Memory — Persistent Chat History
======================================
Simpan & load chat history dari Supabase.
Digunakan oleh semua AI (Kurumi, Hana, Yui, Rei, dll).
"""

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================================
# SAVE MESSAGE
# =========================================================================
def save_message(ai_name, session_id, role, content, file_metadata=None):
    """Simpan 1 pesan ke Supabase."""
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        if not _sb:
            return False

        _data = {
            "ai_name": str(ai_name),
            "session_id": str(session_id),
            "role": str(role),
            "content": str(content),
        }
        if file_metadata:
            _data["file_metadata"] = file_metadata

        _sb.table("ai_chat_history").insert(_data).execute()
        return True
    except Exception as e:
        print(f"[CHAT MEMORY SAVE ERROR] {e}")
        return False


def save_messages_bulk(ai_name, session_id, messages):
    """Simpan banyak pesan sekaligus (bulk)."""
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        if not _sb or not messages:
            return False

        _rows = []
        for _msg in messages:
            _row = {
                "ai_name": str(ai_name),
                "session_id": str(session_id),
                "role": str(_msg.get("role", "user")),
                "content": str(_msg.get("content", "")),
            }
            if _msg.get("file_metadata"):
                _row["file_metadata"] = _msg["file_metadata"]
            _rows.append(_row)

        _sb.table("ai_chat_history").insert(_rows).execute()
        return True
    except Exception as e:
        print(f"[CHAT MEMORY BULK ERROR] {e}")
        return False


# =========================================================================
# LOAD MESSAGES
# =========================================================================
def load_messages(ai_name, session_id, limit=50):
    """Load chat history dari Supabase."""
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        if not _sb:
            return []

        _res = _sb.table("ai_chat_history") \
            .select("role, content, file_metadata, created_at") \
            .eq("ai_name", str(ai_name)) \
            .eq("session_id", str(session_id)) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .execute()

        return _res.data or []
    except Exception as e:
        print(f"[CHAT MEMORY LOAD ERROR] {e}")
        return []


def load_recent_messages(ai_name, session_id, limit=10):
    """Load N pesan terakhir (buat context AI)."""
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        if not _sb:
            return []

        _res = _sb.table("ai_chat_history") \
            .select("role, content") \
            .eq("ai_name", str(ai_name)) \
            .eq("session_id", str(session_id)) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        _data = _res.data or []
        return list(reversed(_data))
    except Exception as e:
        print(f"[CHAT MEMORY RECENT ERROR] {e}")
        return []


# =========================================================================
# CLEAR / DELETE
# =========================================================================
def clear_session(ai_name, session_id):
    """Hapus semua chat history untuk session tertentu."""
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        if not _sb:
            return False

        _sb.table("ai_chat_history") \
            .delete() \
            .eq("ai_name", str(ai_name)) \
            .eq("session_id", str(session_id)) \
            .execute()
        return True
    except Exception as e:
        print(f"[CHAT MEMORY CLEAR ERROR] {e}")
        return False


# =========================================================================
# SESSION ID HELPER
# =========================================================================
def get_or_create_session_id(ai_name):
    """
    ✅ FIX: Session ID persistent — gak berubah tiap refresh.
    Format: {ai_name}_{YYYYMMDD}
    Auto-reset tiap hari baru.
    """
    _key = f"session_id_{ai_name}"

    if _key not in st.session_state:
        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        st.session_state[_key] = f"{ai_name}_{_now.strftime('%Y%m%d')}"

    return st.session_state[_key]

def new_session_id(ai_name):
    """Force bikin session ID baru (buat reset chat)."""
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _new_id = f"{ai_name}_{_now.strftime('%Y%m%d_%H%M%S')}"
    st.session_state[f"session_id_{ai_name}"] = _new_id
    return _new_id
