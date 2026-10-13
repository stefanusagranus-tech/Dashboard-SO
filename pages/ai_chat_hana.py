"""
AI Chat Hana — Master Shift Specialist (AI-1) v4 FINAL
=======================================================
Halaman chat fullscreen untuk Hana.
Persona: Hana 🌸 — asisten HR/jadwal Toko C383.

Fitur v4:
- Header 1 baris (custom component v2)
- Popover menu ⋮ (aksi cepat + session)
- Chat bubble + timestamp scrollable
- Preview update/delete di body
- Command /help
- Footer tipis
- Full screen
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from themes.theme_loader import (
    render_theme,
    render_theme_animations,
    get_theme_by_month,
)

# =========================================================================
# KONFIGURASI
# =========================================================================
st.set_page_config(
    page_title="Hana — Master Shift",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CURRENT_THEME = get_theme_by_month()
render_theme(CURRENT_THEME)
render_theme_animations(CURRENT_THEME)


# =========================================================================
# IMPORT MODULES
# =========================================================================
try:
    from modules.master_shift_handler import (
        KODE_SHIFT,
        save_master_shift,
        delete_shift_by_name,
        delete_shift_all_dates,
    )
    from modules.ai_shift_manager import (
        chat_response,
        parse_shift_update,
    )
    from modules.chat_memory import (
        save_message,
        load_messages,
        get_or_create_session_id,
        clear_session,
        new_session_id,
    )
    _HANA_OK = True
except ImportError as _e:
    _HANA_OK = False
    _import_error = str(_e)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


# =========================================================================
# COMMAND PARSER
# =========================================================================
COMMANDS = {
    "/jadwal": "Jadwal hari ini?",
    "/libur": "Siapa aja yang libur hari ini?",
    "/besok": "Jadwal besok?",
    "/atur": "Atur shift — contoh: `atur Reza ke shift siang`",
    "/saran": "Kasih saran pengganti kalau ada yang libur",
    "/help": "__HELP__",
}


def _parse_command(text):
    """Kalau user ngetik /command, ganti jadi prompt lengkap."""
    if not text:
        return text
    _t = text.strip().lower()
    if _t in COMMANDS:
        if COMMANDS[_t] == "__HELP__":
            return None
        return COMMANDS[_t]
    return text


def _get_help_text():
    """Return text help lengkap."""
    return (
        "🌸 **Hana — Asisten Jadwal Shift** 🌸\n\n"
        "Aku bantu urusan jadwal shift Toko C383. Ini yang bisa aku lakuin:\n\n"
        "**📅 CEK JADWAL**\n"
        "- `/jadwal` — Jadwal hari ini\n"
        "- `/besok` — Jadwal besok\n"
        "- `/libur` — Siapa aja yang libur hari ini\n"
        "- Ketik bebas: *\"siapa shift pagi hari ini?\"*\n\n"
        "**🔄 ATUR SHIFT**\n"
        "- Ketik: *\"atur Reza ke shift siang\"*\n"
        "- Ketik: *\"Kusdewi dan Zaki libur besok\"*\n"
        "- Ketik: *\"hapus shift Pandu hari ini\"*\n"
        "- Aku bakal kasih **preview** sebelum disimpan\n\n"
        "**💡 SARAN**\n"
        "- `/saran` — Saran pengganti kalau ada yang libur\n"
        "- Ketik: *\"siapa pengganti Reza?\"*\n\n"
        "**ℹ️ INFO**\n"
        "- Ketik: *\"ada berapa personil aktif?\"*\n"
        "- Ketik: *\"kode shift apa aja?\"*\n\n"
        "**KODE SHIFT:**\n"
        "- 🌅 **P7** = Pagi (07:00)\n"
        "- ☀️ **S15** = Siang (15:00)\n"
        "- 🌙 **M22** = Malam (22:00)\n"
        "- 💤 **O** = Libur\n"
        "- 🏖️ **C** = Cuti\n"
        "- 📌 **AO** = Additional Off\n\n"
        "**Tips:** Klik `⋮` di kanan atas buat aksi cepat ya~ 🌸"
    )
  
  # =========================================================================
# CSS — FULL SCREEN + BUBBLE + POPOVER
# =========================================================================
def inject_hana_css():
    st.markdown("""
    <style>
        /* === HIDE STREAMLIT CHROME === */
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        #MainMenu { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }

        /* === ZERO PADDING + PADDING TOP BUAT HEADER FIXED === */
        .main .block-container {
            max-width: 100% !important;
            padding: 70px 0.6rem 0.4rem 0.6rem !important;
            margin: 0 !important;
        }
        .main, .stApp, section.main { padding: 0 !important; }

        /* === COLORS === */
        .stApp, .stApp * { color: #F5E6D3 !important; }
        .stApp textarea, .stApp input, .stApp [contenteditable="true"] {
            color: #F5E6D3 !important;
            background: rgba(30, 20, 60, 0.6) !important;
            caret-color: #E8B189 !important;
        }
        .stApp textarea::placeholder, .stApp input::placeholder {
            color: rgba(245, 230, 211, 0.5) !important;
        }

        /* === CHAT MESSAGES — BUBBLE === */
        [data-testid="stChatMessage"] {
            padding: 0.6rem 1rem !important;
            margin-bottom: 0.8rem !important;
            border-radius: 18px !important;
            max-width: 85% !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div,
        [data-testid="stChatMessage"] li {
            color: #F5E6D3 !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(135deg, rgba(127, 185, 155, 0.85), rgba(232, 177, 137, 0.6)) !important;
            border: 1px solid rgba(127, 185, 155, 0.8) !important;
            margin-left: auto !important;
            margin-right: 0 !important;
            border-bottom-right-radius: 4px !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.95), rgba(76, 29, 149, 0.85)) !important;
            border: 1px solid rgba(232, 177, 137, 0.6) !important;
            margin-right: auto !important;
            margin-left: 0 !important;
            border-bottom-left-radius: 4px !important;
        }

        /* === CHAT INPUT === */
        [data-testid="stChatInputContainer"] {
            background: rgba(30, 20, 60, 0.9) !important;
            border-radius: 14px !important;
            border: 1.5px solid rgba(232, 177, 137, 0.6) !important;
        }
        [data-testid="stChatInputContainer"] button {
            background: linear-gradient(135deg, #E8B189, #7FB99B) !important;
            border: none !important;
            color: #fff !important;
        }

        /* === SCROLLABLE CONTAINER === */
        div[data-testid="stVerticalBlock"] > div[style*="height"] {
            background: rgba(20, 12, 35, 0.4) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(232, 177, 137, 0.2) !important;
            padding: 8px !important;
        }

        /* === FOOTER TIPIS === */
        .memory-info-footer {
            background: rgba(20, 12, 35, 0.95);
            border-left: 3px solid #E8B189;
            border-radius: 8px;
            padding: 6px 12px;
            margin-top: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            color: #A89B8E;
            text-align: center;
        }

        /* === POPOVER === */
        [data-testid="stPopover"] > button {
            background: rgba(30, 20, 60, 0.6) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.5) !important;
            border-radius: 10px !important;
            color: #E8B189 !important;
            font-size: 18px !important;
            font-weight: 900 !important;
            height: 34px !important;
            width: 34px !important;
            padding: 0 !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stPopover"] > button:hover {
            background: rgba(232, 177, 137, 0.2) !important;
            border-color: #E8B189 !important;
        }
        [data-testid="stPopoverBody"] {
            background: rgba(20, 12, 35, 0.98) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.5) !important;
            border-radius: 12px !important;
            padding: 12px !important;
        }
        [data-testid="stPopoverBody"] button {
            background: rgba(30, 20, 60, 0.6) !important;
            border: 1px solid rgba(232, 177, 137, 0.3) !important;
            border-radius: 8px !important;
            color: #F5E6D3 !important;
            font-size: 12px !important;
            margin-bottom: 4px !important;
        }

        /* === TIMESTAMP BUBBLE === */
        .bubble-time {
            font-family: JetBrains Mono, monospace;
            font-size: 8px;
            color: rgba(245, 230, 211, 0.5);
            margin-top: 2px;
        }

        /* === DIALOG / MODAL === */
        [data-testid="stDialog"] {
            background: rgba(20, 12, 35, 0.98) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.6) !important;
            border-radius: 16px !important;
        }
        [data-testid="stDialog"] h2 {
            font-family: Cinzel, serif !important;
            color: #E8B189 !important;
            font-size: 18px !important;
        }

        /* === PREVIEW BOX === */
        .preview-box {
            background: rgba(30, 20, 60, 0.7);
            border: 1.5px solid rgba(232, 177, 137, 0.5);
            border-radius: 12px;
            padding: 12px 16px;
            margin: 8px 0;
        }
    </style>
    """, unsafe_allow_html=True)


inject_hana_css()


# =========================================================================
# GUARD
# =========================================================================
if not _HANA_OK:
    st.error(f"❌ Gagal import module: {_import_error}")
    st.stop()
  
# =========================================================================
# SESSION STATE
# =========================================================================
_session_id = get_or_create_session_id("hana")

if "hana_history" not in st.session_state:
    with st.spinner("⏳ Load chat history..."):
        _saved = load_messages("hana", _session_id, limit=100)
    st.session_state["hana_history"] = [
        {
            "role": _m.get("role", "user"),
            "content": _m.get("content", ""),
            "time": _m.get("time_wib", "—"),
        }
        for _m in _saved
    ]

if "hana_pending_update" not in st.session_state:
    st.session_state["hana_pending_update"] = None

if "hana_last_saved" not in st.session_state:
    st.session_state["hana_last_saved"] = None

if "hana_preset" not in st.session_state:
    st.session_state["hana_preset"] = ""

if "hana_show_menu" not in st.session_state:
    st.session_state["hana_show_menu"] = False


# =========================================================================
# WELCOME MESSAGE
# =========================================================================
if not st.session_state["hana_history"]:
    _welcome = (
        "🌸 **Halo Bos!** Aku Hana, asisten jadwal shift Toko C383.\n\n"
        "Aku bisa bantu:\n"
        "- 📅 Cek jadwal shift\n"
        "- 🔄 Atur/pindah shift personil\n"
        "- 🗑️ Hapus shift\n"
        "- 💡 Kasih saran pengganti\n\n"
        "**Tips:** Ketik `/help` buat liat semua yang bisa aku lakuin, "
        "atau klik `⋮` di kanan atas buat aksi cepat~ 🌸"
    )
    _now_str = _now_jkt().strftime("%H:%M")
    _entry = {"role": "assistant", "content": _welcome, "time": _now_str}
    st.session_state["hana_history"].append(_entry)
    save_message("hana", _session_id, "assistant", _welcome)
  
# =========================================================================
# HEADER 1 BARIS — CUSTOM COMPONENT V2
# =========================================================================
_hana_header_component = st.components.v2.component(
    name="hana_header",
    html="""
    <div class="hana-header">
        <button id="btn-back" class="hdr-btn">←</button>
        <span class="hdr-title">🌸 HANA</span>
        <button id="btn-menu" class="hdr-btn">⋮</button>
    </div>
    """,
    css="""
    .hana-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 16px;
        background: linear-gradient(135deg, rgba(30, 20, 60, 0.98), rgba(76, 29, 149, 0.9));
        border-bottom: 2px solid rgba(232, 177, 137, 0.6);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        min-height: 52px;
        box-sizing: border-box;
        font-family: 'Cinzel', serif;
    }
    .hdr-btn {
        width: 40px;
        height: 36px;
        background: rgba(30, 20, 60, 0.85);
        border: 1.5px solid rgba(232, 177, 137, 0.6);
        border-radius: 10px;
        color: #E8B189;
        font-size: 16px;
        font-weight: 900;
        cursor: pointer;
        padding: 0;
        transition: all 0.2s ease;
        flex-shrink: 0;
    }
    .hdr-btn:hover {
        background: rgba(232, 177, 137, 0.25);
        border-color: #E8B189;
    }
    .hdr-title {
        font-size: 18px;
        font-weight: 900;
        color: #E8B189;
        letter-spacing: 1.5px;
        text-shadow: 0 0 10px rgba(232, 177, 137, 0.6);
        text-align: center;
        flex-grow: 1;
    }
    """,
    js="""
    export default function(component) {
        const { parentElement, setTriggerValue } = component;
        const backBtn = parentElement.querySelector('#btn-back');
        const menuBtn = parentElement.querySelector('#btn-menu');
        if (backBtn) {
            backBtn.onclick = () => { setTriggerValue('back', true); };
        }
        if (menuBtn) {
            menuBtn.onclick = () => { setTriggerValue('menu', true); };
        }
    }
    """,
    isolate_styles=True,
)

_header_result = _hana_header_component(
    data={},
    key="hana_header",
    on_back_change=lambda: None,
    on_menu_change=lambda: None,
)

if _header_result.get("back"):
    try:
        st.switch_page("Dashboard.py")
    except Exception:
        st.warning("⚠️ Gagal pindah.")

if _header_result.get("menu"):
    st.session_state["hana_show_menu"] = True
    st.rerun()


# =========================================================================
# MENU DIALOG (MODAL)
# =========================================================================
@st.dialog("🌸 Menu Hana", width="small")
def _hana_menu_dialog():
    st.caption("🎯 AKSI CEPAT")
    if st.button("📅 Jadwal Hari Ini", use_container_width=True, key="menu_jadwal"):
        st.session_state["hana_show_menu"] = False
        st.session_state["hana_preset"] = "Jadwal hari ini?"
        st.rerun()
    if st.button("👤 Siapa Libur", use_container_width=True, key="menu_libur"):
        st.session_state["hana_show_menu"] = False
        st.session_state["hana_preset"] = "Siapa aja yang libur hari ini?"
        st.rerun()
    if st.button("🔄 Atur Shift", use_container_width=True, key="menu_atur"):
        st.session_state["hana_show_menu"] = False
        st.session_state["hana_preset"] = "Atur "
        st.rerun()
    if st.button("💡 Saran Pengganti", use_container_width=True, key="menu_saran"):
        st.session_state["hana_show_menu"] = False
        st.session_state["hana_preset"] = "Kasih saran pengganti kalau ada yang libur"
        st.rerun()

    st.divider()

    st.caption("📖 HELP")
    if st.button("ℹ️ /help — Kegunaan Hana", use_container_width=True, key="menu_help"):
        st.session_state["hana_show_menu"] = False
        st.session_state["hana_preset"] = "/help"
        st.rerun()

    st.divider()

    st.caption("💾 SESSION")
    if st.button("🗑️ Reset Chat", use_container_width=True, key="menu_reset"):
        clear_session("hana", _session_id)
        st.session_state["hana_history"] = []
        st.session_state["hana_pending_update"] = None
        st.session_state["hana_show_menu"] = False
        st.rerun()

    st.divider()

    st.caption("🌸 SISTEM")
    _total_msg_menu = len(st.session_state.get("hana_history", []))
    st.caption(f"🧠 Session: `{_session_id[-12:]}`")
    st.caption(f"💬 Total: {_total_msg_menu} pesan")

    st.divider()

    if st.button("❌ Tutup", use_container_width=True, key="menu_close"):
        st.session_state["hana_show_menu"] = False
        st.rerun()


if st.session_state.get("hana_show_menu"):
    _hana_menu_dialog()

# =========================================================================
# CHAT CONTAINER — BUBBLE + TIMESTAMP
# =========================================================================
_CHAT_HEIGHT = 500

_chat_container = st.container(height=_CHAT_HEIGHT, border=False)

with _chat_container:
    for _msg in st.session_state["hana_history"]:
        _role = _msg.get("role", "user")
        _content = _msg.get("content", "")
        _time_msg = _msg.get("time", _now_jkt().strftime("%H:%M"))

        with st.chat_message(_role, avatar="👤" if _role == "user" else "🌸"):
            st.markdown(_content)
            _align = "right" if _role == "user" else "left"
            st.markdown(
                f"<div class='bubble-time' style='text-align: {_align};'>"
                f"● {_time_msg}</div>",
                unsafe_allow_html=True,
            )

# =========================================================================
# PREVIEW UPDATE / DELETE
# =========================================================================
if st.session_state["hana_pending_update"]:
    _parsed = st.session_state["hana_pending_update"]
    _mode = _parsed.get("mode", "update")

    st.markdown("---")

    # === MODE DELETE ===
    if _mode == "delete":
        _delete_targets = _parsed.get("delete_targets", [])
        _delete_all_dates = _parsed.get("delete_all_dates", False)

        st.markdown("#### 🗑️ Preview Hapus Shift")

        if _delete_all_dates:
            st.warning(
                f"⚠️ Akan hapus **SEMUA shift** untuk: "
                f"**{', '.join(_delete_targets)}**"
            )
        else:
            _tgl_list = _parsed.get("tanggal_list", [_parsed.get("tanggal")])
            _tgl_str = ", ".join([t.strftime("%d/%m/%Y") for t in _tgl_list])
            st.warning(
                f"⚠️ Akan hapus shift **{', '.join(_delete_targets)}** "
                f"untuk: {_tgl_str}"
            )

        _col1, _col2 = st.columns(2)

        with _col1:
            if st.button(
                "✅ KONFIRMASI HAPUS",
                width="stretch",
                type="primary",
                key="btn_hana_delete",
            ):
                _total_deleted = 0

                if _delete_all_dates:
                    for _nama in _delete_targets:
                        _ok, _msg = delete_shift_all_dates(_nama)
                        if _ok:
                            _total_deleted += 1
                else:
                    for _tgl_hapus in _parsed.get("tanggal_list", [_parsed.get("tanggal")]):
                        _ok, _msg, _detail = delete_shift_by_name(_tgl_hapus, _delete_targets)
                        if _ok:
                            _total_deleted += _detail.get("deleted", 0)

                if _total_deleted > 0:
                    _msg_confirm = f"🗑️ {_total_deleted} shift dihapus!"
                    _time_now = _now_jkt().strftime("%H:%M")

                    st.session_state["hana_last_saved"] = _msg_confirm
                    st.session_state["hana_history"].append({
                        "role": "assistant",
                        "content": f"🗑️ Sip! **{_total_deleted} shift** udah Hana hapus 🌸",
                        "time": _time_now,
                    })
                    save_message("hana", _session_id, "assistant", f"🗑️ Sip! **{_total_deleted} shift** udah Hana hapus 🌸")

                    st.session_state["hana_pending_update"] = None
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Gagal hapus shift")

        with _col2:
            if st.button(
                "❌ BATAL",
                width="stretch",
                key="btn_hana_cancel_delete",
            ):
                _batal_msg = "Oke, gak jadi hapus ya! 🌸"
                _time_now = _now_jkt().strftime("%H:%M")
                st.session_state["hana_history"].append({
                    "role": "assistant",
                    "content": _batal_msg,
                    "time": _time_now,
                })
                save_message("hana", _session_id, "assistant", _batal_msg)
                st.session_state["hana_pending_update"] = None
                st.rerun()

    # === MODE UPDATE ===
    elif _mode == "update":
        _shift_map = _parsed.get("shift_map", {})
        _tgl_list = _parsed.get("tanggal_list", [_parsed.get("tanggal")])

        if _shift_map:
            st.markdown("#### 📊 Preview Perubahan")

            _preview_rows = []
            for _nama, _kode in _shift_map.items():
                _info = KODE_SHIFT.get(_kode, {"label": "-", "icon": "❓"})
                for _tgl in _tgl_list:
                    _preview_rows.append({
                        "👤 Nama": _nama,
                        "📅 Tanggal": _tgl.strftime("%d/%m/%Y"),
                        "🔄 Kode": _kode,
                        "📋 Ket.": _info["label"],
                    })
            st.dataframe(pd.DataFrame(_preview_rows), use_container_width=True, hide_index=True)

            _catatan = st.text_input(
                "📝 Catatan (opsional)",
                placeholder="Contoh: Ganti dadakan",
                key="hana_catatan",
            )

            _col1, _col2 = st.columns(2)

            with _col1:
                if st.button(
                    "✅ KONFIRMASI SIMPAN",
                    width="stretch",
                    type="primary",
                    key="btn_hana_save",
                ):
                    _total = 0
                    for _tgl_save in _tgl_list:
                        _ok, _msg = save_master_shift(
                            tanggal=_tgl_save,
                            shift_map=_shift_map,
                            sumber="hana_chat",
                            catatan=f"{_catatan} | Chat: {_parsed.get('raw_text', '')[:100]}",
                        )
                        if _ok:
                            _total += len(_shift_map)

                    if _total > 0:
                        _nama_updated = ", ".join(_shift_map.keys())
                        _confirm_msg = (
                            f"✅ **{_total} shift** berhasil disimpan! "
                            f"({_nama_updated})"
                        )
                        _time_now = _now_jkt().strftime("%H:%M")

                        st.session_state["hana_last_saved"] = _confirm_msg
                        st.session_state["hana_history"].append({
                            "role": "assistant",
                            "content": f"✅ Sip! **{_total} shift** udah Hana simpan 🌸 "
                                       f"({_nama_updated}). Cek dashboard ya!",
                            "time": _time_now,
                        })
                        save_message("hana", _session_id, "assistant", f"✅ Sip! **{_total} shift** udah Hana simpan 🌸 ({_nama_updated}).")

                        st.session_state["hana_pending_update"] = None
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Gagal simpan")

            with _col2:
                if st.button(
                    "❌ BATAL",
                    width="stretch",
                    key="btn_hana_cancel",
                ):
                    _batal_msg = "Oke, gak jadi update ya! 🌸"
                    _time_now = _now_jkt().strftime("%H:%M")
                    st.session_state["hana_history"].append({
                        "role": "assistant",
                        "content": _batal_msg,
                        "time": _time_now,
                    })
                    save_message("hana", _session_id, "assistant", _batal_msg)
                    st.session_state["hana_pending_update"] = None
                    st.rerun()
                    
# =========================================================================
# CHAT INPUT
# =========================================================================
_preset = st.session_state.pop("hana_preset", "")
_user_msg = st.chat_input("Tanya atau perintah Hana... (ketik /help)", key="hana_chat_input")

if _preset and not _user_msg:
    _user_msg = _preset


# =========================================================================
# CHAT HANDLER
# =========================================================================
if _user_msg:
    _time_now = _now_jkt().strftime("%H:%M")
    _parsed_cmd = _parse_command(_user_msg)

    # === HANDLE /help ===
    if _parsed_cmd is None:
        _help_text = _get_help_text()
        st.session_state["hana_history"].append({
            "role": "user", "content": _user_msg, "time": _time_now,
        })
        save_message("hana", _session_id, "user", _user_msg)
        st.session_state["hana_history"].append({
            "role": "assistant", "content": _help_text, "time": _time_now,
        })
        save_message("hana", _session_id, "assistant", _help_text)
        st.rerun()

    # === PARSE COMMAND / GANTI KE PROMPT ===
    _final_msg = _parsed_cmd

    st.session_state["hana_history"].append({
        "role": "user", "content": _user_msg, "time": _time_now,
    })
    save_message("hana", _session_id, "user", _user_msg)

    with _chat_container:
        with st.chat_message("user", avatar="👤"):
            st.markdown(_user_msg)
            st.markdown(
                f"<div class='bubble-time' style='text-align: right;'>"
                f"● {_time_now}</div>",
                unsafe_allow_html=True,
            )

        with st.chat_message("assistant", avatar="🌸"):
            with st.spinner("🌸 Hana lagi mikir..."):
                _resp = chat_response(_final_msg, st.session_state["hana_history"])

            _text = _resp.get("text", "")
            st.markdown(_text)
            st.markdown(
                f"<div class='bubble-time' style='text-align: left;'>"
                f"● {_time_now}</div>",
                unsafe_allow_html=True,
            )

    st.session_state["hana_history"].append({
        "role": "assistant", "content": _text, "time": _time_now,
    })
    save_message("hana", _session_id, "assistant", _text)

    # Kalau intent UPDATE atau DELETE, set pending
    if _resp.get("parsed"):
        st.session_state["hana_pending_update"] = _resp["parsed"]

    st.rerun()

# =========================================================================
# FOOTER TIPIS
# =========================================================================
_total_msg = len(st.session_state["hana_history"])
_model_str = "hana"

st.markdown(
    f"<div class='memory-info-footer'>"
    f"🧠 Session: <code style='color: #E8B189;'>{_session_id[-12:]}</code> | "
    f"💬 <b style='color: #F5E6D3;'>{_total_msg}</b> pesan | "
    f"⚙️ <b style='color: #E8B189;'>{_model_str}</b> | "
    f"💡 Ketik <code>/help</code>"
    f"</div>",
    unsafe_allow_html=True,
)