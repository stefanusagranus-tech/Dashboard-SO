"""
Chat Memory — Persistent Chat History v2
==========================================
Simpan & load chat history dari Supabase.
Digunakan oleh semua AI (Kurumi, Hana, Yui, Rei, dll).

Changelog v2:
- Session ID pakai timestamp (gak auto-reset jam 12 malam)
- Tambah get_session_list() buat restore
- Tambah load_messages_by_session()
- Tambah get_session_info()
- Tambah delete_session()
- Timestamp pakai created_at asli dari DB
"""

import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _format_time_wib(created_at_str):
    """Convert created_at (UTC ISO) ke jam WIB 'HH:MM'."""
    if not created_at_str:
        return "—"
    try:
        # Handle format "2026-10-12T22:30:00+00:00" atau "2026-10-12T22:30:00Z"
        _s = str(created_at_str).replace("Z", "+00:00")
        _dt = datetime.fromisoformat(_s)
        _dt_wib = _dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return _dt_wib.strftime("%H:%M")
    except Exception as e:
        print(f"[FORMAT_TIME ERROR] {e}")
        return "—"


def _format_date_wib(created_at_str):
    """Convert created_at ke tanggal WIB 'DD/MM/YYYY'."""
    if not created_at_str:
        return "—"
    try:
        _s = str(created_at_str).replace("Z", "+00:00")
        _dt = datetime.fromisoformat(_s)
        _dt_wib = _dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return _dt_wib.strftime("%d/%m/%Y")
    except Exception:
        return "—"


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
# LOAD MESSAGES (dengan timestamp asli dari DB)
# =========================================================================
def load_messages(ai_name, session_id, limit=100):
    """
    Load chat history dari Supabase — LENGKAP dengan timestamp asli.
    
    Returns:
        list[dict]: [{
            "role": str,
            "content": str,
            "file_metadata": dict|None,
            "created_at": str (ISO UTC),
            "time_wib": str (HH:MM),
            "date_wib": str (DD/MM/YYYY),
        }]
    """
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

        _data = _res.data or []

        # Tambah timestamp WIB yang udah di-format
        for _msg in _data:
            _created = _msg.get("created_at")
            _msg["time_wib"] = _format_time_wib(_created)
            _msg["date_wib"] = _format_date_wib(_created)

        return _data
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
# SESSION LIST — BUAT RESTORE
# =========================================================================
def get_session_list(ai_name, limit=20):
    """
    Ambil daftar session_id yang ada di DB buat AI tertentu.
    
    Returns:
        list[dict]: [{
            "session_id": str,
            "first_message_at": str,
            "last_message_at": str,
            "total_messages": int,
            "preview": str (50 char pertama),
        }]
    """
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        if not _sb:
            return []

        # Ambil semua session_id unik + hitung pesan
        _res = _sb.table("ai_chat_history") \
            .select("session_id, created_at, content") \
            .eq("ai_name", str(ai_name)) \
            .order("created_at", desc=True) \
            .limit(2000) \
            .execute()

        _rows = _res.data or []
        if not _rows:
            return []

        # Group by session_id
        _sessions = {}
        for _row in _rows:
            _sid = _row.get("session_id", "")
            if not _sid:
                continue
            if _sid not in _sessions:
                _sessions[_sid] = {
                    "session_id": _sid,
                    "first_message_at": _row.get("created_at"),
                    "last_message_at": _row.get("created_at"),
                    "total_messages": 0,
                    "preview": "",
                }
            _sessions[_sid]["total_messages"] += 1
            # update last
            _sessions[_sid]["last_message_at"] = _row.get("created_at")
            # update first
            if _row.get("created_at") < _sessions[_sid]["first_message_at"]:
                _sessions[_sid]["first_message_at"] = _row.get("created_at")
            # preview: isi pesan pertama yang user
            if not _sessions[_sid]["preview"] and _row.get("content"):
                _sessions[_sid]["preview"] = str(_row["content"])[:50]

        # Sort by last message
        _result = sorted(
            _sessions.values(),
            key=lambda x: x.get("last_message_at") or "",
            reverse=True,
        )
        return _result[:limit]
    except Exception as e:
        print(f"[GET_SESSION_LIST ERROR] {e}")
        return []


def get_session_info(ai_name, session_id):
    """Info singkat satu session."""
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        if not _sb:
            return None

        _res = _sb.table("ai_chat_history") \
            .select("created_at") \
            .eq("ai_name", str(ai_name)) \
            .eq("session_id", str(session_id)) \
            .order("created_at", desc=False) \
            .limit(1) \
            .execute()

        _first = _res.data[0]["created_at"] if _res.data else None

        _res2 = _sb.table("ai_chat_history") \
            .select("created_at") \
            .eq("ai_name", str(ai_name)) \
            .eq("session_id", str(session_id)) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        _last = _res2.data[0]["created_at"] if _res2.data else None

        return {
            "session_id": session_id,
            "first_message_at": _first,
            "last_message_at": _last,
        }
    except Exception as e:
        print(f"[GET_SESSION_INFO ERROR] {e}")
        return None


def load_messages_by_session(ai_name, session_id):
    """Load semua pesan dari session tertentu (buat restore)."""
    return load_messages(ai_name, session_id, limit=500)


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


def delete_session(ai_name, session_id):
    """Alias buat clear_session."""
    return clear_session(ai_name, session_id)


# =========================================================================
# SESSION ID HELPER
# =========================================================================
def get_or_create_session_id(ai_name):
    """
    Session ID persistent — pakai timestamp, GAK auto-reset jam 12 malam.
    Format: {ai_name}_{YYYYMMDD_HHMMSS}
    
    Cuma reset kalau user klik "New Chat" (panggil new_session_id()).
    """
    _key = f"session_id_{ai_name}"

    if _key not in st.session_state:
        _now = _now_jkt()
        st.session_state[_key] = f"{ai_name}_{_now.strftime('%Y%m%d_%H%M%S')}"

    return st.session_state[_key]


def new_session_id(ai_name):
    """
    Bikin session ID baru (buat "New Chat").
    Sesi lama tetap ada di DB, bisa di-restore.
    """
    _now = _now_jkt()
    _new_id = f"{ai_name}_{_now.strftime('%Y%m%d_%H%M%S')}"
    st.session_state[f"session_id_{ai_name}"] = _new_id
    return _new_id


def set_session_id(ai_name, session_id):
    """Set session_id aktif ke session tertentu (buat restore)."""
    st.session_state[f"session_id_{ai_name}"] = session_id
    return session_id