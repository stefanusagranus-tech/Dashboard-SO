"""
AI Chat Kurumi — Chief of Staff (AI-0) v8 FINAL
================================================
Halaman chat fullscreen untuk Kurumi.
Persona: Tokisaki Kurumi (versi ramah kerja).

Changelog v8:
- Header 1 baris (custom component v2)
- Popover menu ⋮ (toolbar pindah ke sini)
- Chat bubble + timestamp scrollable
- Footer tipis
- Full screen
- Logic chat & mode Rangkum/Report TETAP SAMA
"""

import streamlit as st
import time
from datetime import datetime, timedelta
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
    page_title="Kurumi — Chief of Staff",
    page_icon="🎀",
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
    from modules.ai_core import (
        kurumi_chat_response,
        kurumi_summarize,
        kurumi_generate_report,
    )
    from modules.chat_memory import (
        save_message,
        load_messages,
        get_or_create_session_id,
        clear_session,
        new_session_id,
    )
    _MEMORY_OK = True
    _AI_OK = True
except ImportError as e:
    _AI_OK = False
    _MEMORY_OK = False
    _import_error = str(e)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))

# =========================================================================
# CSS — FULL SCREEN + BUBBLE + POPOVER
# =========================================================================
def inject_chat_css():
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
            caret-color: #a855f7 !important;
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
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(232, 177, 137, 0.20)) !important;
            border: 1px solid rgba(232, 177, 137, 0.6) !important;
            margin-left: auto !important;
            margin-right: 0 !important;
            border-bottom-right-radius: 4px !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.95), rgba(76, 29, 149, 0.85)) !important;
            border: 1px solid rgba(168, 85, 247, 0.6) !important;
            margin-right: auto !important;
            margin-left: 0 !important;
            border-bottom-left-radius: 4px !important;
        }

        /* === CHAT INPUT === */
        [data-testid="stChatInputContainer"] {
            background: rgba(30, 20, 60, 0.9) !important;
            border-radius: 14px !important;
            border: 1.5px solid rgba(168, 85, 247, 0.6) !important;
        }
        [data-testid="stChatInputContainer"] textarea,
        [data-testid="stChatInputContainer"] input {
            color: #F5E6D3 !important;
            background: transparent !important;
        }
        [data-testid="stChatInputContainer"] button {
            background: linear-gradient(135deg, #a855f7, #E8B189) !important;
            border: none !important;
            color: #fff !important;
        }

        /* === SCROLLABLE CONTAINER === */
        div[data-testid="stVerticalBlock"] > div[style*="height"] {
            background: rgba(20, 12, 35, 0.4) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(168, 85, 247, 0.2) !important;
            padding: 8px !important;
        }

        /* === FOOTER TIPIS === */
        .memory-info-footer {
            background: rgba(20, 12, 35, 0.95);
            border-left: 3px solid #a855f7;
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
            border: 1.5px solid rgba(168, 85, 247, 0.5) !important;
            border-radius: 10px !important;
            color: #a855f7 !important;
            font-size: 18px !important;
            font-weight: 900 !important;
            height: 34px !important;
            width: 34px !important;
            padding: 0 !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stPopover"] > button:hover {
            background: rgba(168, 85, 247, 0.2) !important;
            border-color: #a855f7 !important;
        }
        [data-testid="stPopoverBody"] {
            background: rgba(20, 12, 35, 0.98) !important;
            border: 1.5px solid rgba(168, 85, 247, 0.5) !important;
            border-radius: 12px !important;
            padding: 12px !important;
        }
        [data-testid="stPopoverBody"] button {
            background: rgba(30, 20, 60, 0.6) !important;
            border: 1px solid rgba(168, 85, 247, 0.3) !important;
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
            border: 1.5px solid rgba(168, 85, 247, 0.6) !important;
            border-radius: 16px !important;
        }
        [data-testid="stDialog"] h2 {
            font-family: Cinzel, serif !important;
            color: #a855f7 !important;
            font-size: 18px !important;
        }
    </style>
    """, unsafe_allow_html=True)


inject_chat_css()


# =========================================================================
# GUARD — Cek import
# =========================================================================
if not _AI_OK:
    st.error(f"❌ Gagal import module: {_import_error}")
    st.info("💡 Pastikan `modules/ai_core.py` + `modules/chat_memory.py` udah ada.")
    st.stop()

# =========================================================================
# SESSION STATE
# =========================================================================
_session_id = get_or_create_session_id("kurumi") if _MEMORY_OK else "default"

if "kurumi_history" not in st.session_state:
    if _MEMORY_OK:
        with st.spinner("⏳ Load chat history..."):
            _saved = load_messages("kurumi", _session_id, limit=100)
        st.session_state["kurumi_history"] = [
            {
                "role": _m.get("role", "user"),
                "content": _m.get("content", ""),
                "time": _m.get("time_wib", "—"),
            }
            for _m in _saved
        ]
    else:
        st.session_state["kurumi_history"] = []

if "kurumi_mode" not in st.session_state:
    st.session_state["kurumi_mode"] = "chat"

if "kurumi_rangkum_choice" not in st.session_state:
    st.session_state["kurumi_rangkum_choice"] = None

if "kurumi_report_choice" not in st.session_state:
    st.session_state["kurumi_report_choice"] = None

if "kurumi_show_menu" not in st.session_state:
    st.session_state["kurumi_show_menu"] = False


# =========================================================================
# WELCOME MESSAGE
# =========================================================================
if not st.session_state["kurumi_history"]:
    _welcome = (
        "🎀 **Ara, ara~** Selamat datang, Tuan~ ✨\n\n"
        "Aku adalah **Kurumi**, Chief of Staff Toko C383. "
        "Kihihihi~ Senang akhirnya bisa bertemu Tuan di sini.\n\n"
        "Fufufu~ Ada yang bisa aku bantu hari ini, Tuan? "
        "Tuan bisa langsung ngobrol santai, atau pilih menu ⚙️ di kanan atas~ 🎀"
    )
    _now_str = _now_jkt().strftime("%H:%M")
    _entry = {"role": "assistant", "content": _welcome, "time": _now_str}
    st.session_state["kurumi_history"].append(_entry)

    if _MEMORY_OK:
        save_message("kurumi", _session_id, "assistant", _welcome)

# =========================================================================
# HEADER 1 BARIS — CUSTOM COMPONENT V2
# =========================================================================
_kurumi_header_component = st.components.v2.component(
    name="kurumi_header",
    html="""
    <div class="kurumi-header">
        <button id="btn-back" class="hdr-btn">←</button>
        <span class="hdr-title">🎀 KURUMI</span>
        <button id="btn-menu" class="hdr-btn">⋮</button>
    </div>
    """,
    css="""
    .kurumi-header {
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
        border-bottom: 2px solid rgba(168, 85, 247, 0.6);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        min-height: 52px;
        box-sizing: border-box;
        font-family: 'Cinzel', serif;
    }
    .hdr-btn {
        width: 40px;
        height: 36px;
        background: rgba(30, 20, 60, 0.85);
        border: 1.5px solid rgba(168, 85, 247, 0.6);
        border-radius: 10px;
        color: #a855f7;
        font-size: 16px;
        font-weight: 900;
        cursor: pointer;
        padding: 0;
        transition: all 0.2s ease;
        flex-shrink: 0;
    }
    .hdr-btn:hover {
        background: rgba(168, 85, 247, 0.25);
        border-color: #a855f7;
    }
    .hdr-title {
        font-size: 18px;
        font-weight: 900;
        color: #a855f7;
        letter-spacing: 1.5px;
        text-shadow: 0 0 10px rgba(168, 85, 247, 0.6);
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

_header_result = _kurumi_header_component(
    data={},
    key="kurumi_header",
    on_back_change=lambda: None,
    on_menu_change=lambda: None,
)

if _header_result.get("back"):
    try:
        st.switch_page("Dashboard.py")
    except Exception:
        st.warning("⚠️ Gagal pindah halaman. Refresh manual ya.")

if _header_result.get("menu"):
    st.session_state["kurumi_show_menu"] = True
    st.rerun()


# =========================================================================
# MENU DIALOG (MODAL)
# =========================================================================
@st.dialog("🎀 Menu Kurumi", width="small")
def _kurumi_menu_dialog():
    st.caption("🎯 AKSI CEPAT")
    if st.button("📊 Rangkum", use_container_width=True, key="menu_rangkum"):
        st.session_state["kurumi_show_menu"] = False
        st.session_state["kurumi_mode"] = "rangkum"
        st.session_state["kurumi_rangkum_choice"] = None
        st.rerun()
    if st.button("📤 Kirim Laporan", use_container_width=True, key="menu_report"):
        st.session_state["kurumi_show_menu"] = False
        st.session_state["kurumi_mode"] = "report"
        st.session_state["kurumi_report_choice"] = None
        st.rerun()

    st.divider()

    st.caption("💾 SESSION")
    if st.button("🗑️ Reset Chat", use_container_width=True, key="menu_reset"):
        if _MEMORY_OK:
            clear_session("kurumi", _session_id)
        st.session_state["kurumi_history"] = []
        st.session_state["kurumi_mode"] = "chat"
        st.session_state["kurumi_show_menu"] = False
        st.rerun()

    st.divider()

    st.caption("🎀 SISTEM")
    _total_msg_menu = len(st.session_state.get("kurumi_history", []))
    st.caption(f"🧠 Session: `{_session_id[-12:]}`")
    st.caption(f"💬 Total: {_total_msg_menu} pesan")

    st.divider()

    if st.button("❌ Tutup", use_container_width=True, key="menu_close"):
        st.session_state["kurumi_show_menu"] = False
        st.rerun()


if st.session_state.get("kurumi_show_menu"):
    _kurumi_menu_dialog()

# =========================================================================
# CHAT CONTAINER — BUBBLE + TIMESTAMP
# =========================================================================
_CHAT_HEIGHT = 600

_chat_container = st.container(height=_CHAT_HEIGHT, border=False)

with _chat_container:
    for _idx, _msg in enumerate(st.session_state["kurumi_history"]):
        _role = _msg.get("role", "user")
        _content = _msg.get("content", "")
        _file_data = _msg.get("file")
        _time_msg = _msg.get("time", _now_jkt().strftime("%H:%M"))

        with st.chat_message(_role, avatar="👤" if _role == "user" else "🎀"):
            st.markdown(_content)
            _align = "right" if _role == "user" else "left"
            st.markdown(
                f"<div class='bubble-time' style='text-align: {_align};'>"
                f"● {_time_msg}</div>",
                unsafe_allow_html=True,
            )

            if _file_data:
                st.markdown("---")
                _col_dl, _ = st.columns([2, 3])
                with _col_dl:
                    st.download_button(
                        label=f"📥 Download {_file_data.get('format', 'file').upper()}",
                        data=_file_data["content"],
                        file_name=_file_data["filename"],
                        mime=_file_data["mime"],
                        width="stretch",
                        type="primary",
                        key=f"dl_hist_{_idx}",
                    )
    
# =========================================================================
# MODE RANGKUM
# =========================================================================
if st.session_state["kurumi_mode"] == "rangkum":
    st.markdown("#### 🎀 Kurumi Bertanya...")

    st.info(
        "Ara, ara~ Tuan mau aku rangkum yang mana nih? 🎀\n\n"
        "Pilih salah satu di bawah ya~"
    )

    _col_r1, _col_r2, _col_r3, _col_r4 = st.columns(4)
    with _col_r1:
        if st.button("📅 Hari Ini", width="stretch", key="btn_r_hari"):
            st.session_state["kurumi_rangkum_choice"] = "hari"
    with _col_r2:
        if st.button("🗓️ Minggu Ini", width="stretch", key="btn_r_minggu"):
            st.session_state["kurumi_rangkum_choice"] = "minggu"
    with _col_r3:
        if st.button("📆 Bulan Ini", width="stretch", key="btn_r_bulan"):
            st.session_state["kurumi_rangkum_choice"] = "bulan"
    with _col_r4:
        if st.button("❌ Batal", width="stretch", key="btn_r_batal"):
            st.session_state["kurumi_mode"] = "chat"
            st.session_state["kurumi_rangkum_choice"] = None
            st.rerun()

    if st.session_state["kurumi_rangkum_choice"]:
        _choice = st.session_state["kurumi_rangkum_choice"]
        _label = {"hari": "hari ini", "minggu": "minggu ini", "bulan": "bulan ini"}[_choice]

        _user_msg = f"Rangkum {_label} dong~"
        _time_now = _now_jkt().strftime("%H:%M")

        st.session_state["kurumi_history"].append({
            "role": "user", "content": _user_msg, "time": _time_now,
        })
        if _MEMORY_OK:
            save_message("kurumi", _session_id, "user", _user_msg)

        with st.spinner(f"🎀 Aku rangkum {_label}..."):
            _summary = kurumi_summarize(period=_choice)

        st.session_state["kurumi_history"].append({
            "role": "assistant", "content": _summary, "time": _time_now,
        })
        if _MEMORY_OK:
            save_message("kurumi", _session_id, "assistant", _summary)

        st.session_state["kurumi_mode"] = "chat"
        st.session_state["kurumi_rangkum_choice"] = None
        st.rerun()

    st.markdown("---")


# =========================================================================
# MODE REPORT
# =========================================================================
if st.session_state["kurumi_mode"] == "report":
    st.markdown("#### 🎀 Kurumi Bertanya...")

    st.info(
        "Ara, ara~ Tuan mau laporan format apa nih? 🎀\n\n"
        "Pilih format di bawah ya~"
    )

    _col_f1, _col_f2, _col_f3, _col_f4 = st.columns(4)
    with _col_f1:
        if st.button("📄 Text", width="stretch", key="btn_f_text"):
            st.session_state["kurumi_report_choice"] = "text"
    with _col_f2:
        if st.button("📕 PDF", width="stretch", key="btn_f_pdf"):
            st.session_state["kurumi_report_choice"] = "pdf"
    with _col_f3:
        if st.button("📗 Excel", width="stretch", key="btn_f_excel"):
            st.session_state["kurumi_report_choice"] = "excel"
    with _col_f4:
        if st.button("❌ Batal", width="stretch", key="btn_f_batal"):
            st.session_state["kurumi_mode"] = "chat"
            st.session_state["kurumi_report_choice"] = None
            st.rerun()

    if st.session_state["kurumi_report_choice"]:
        _fmt = st.session_state["kurumi_report_choice"]
        _fmt_label = {"text": "TEXT", "pdf": "PDF", "excel": "EXCEL"}[_fmt]

        with st.spinner(f"🎀 Aku buat laporan {_fmt_label}..."):
            _report = kurumi_generate_report(period="hari", format=_fmt)

        if _report["success"]:
            st.success(f"✅ Laporan {_fmt_label} siap, Tuan~ 🎀")
            st.download_button(
                label=f"📥 Download {_fmt_label}",
                data=_report["content"],
                file_name=_report["filename"],
                mime=_report["mime"],
                width="stretch",
                type="primary",
                key=f"dl_{_fmt}",
            )
        else:
            st.error(f"❌ Gagal: {_report['content']}")

        if st.button("← Kembali ke Chat", key="btn_back_chat"):
            st.session_state["kurumi_mode"] = "chat"
            st.session_state["kurumi_report_choice"] = None
            st.rerun()

    st.markdown("---")

# =========================================================================
# INPUT CHAT
# =========================================================================
_user_msg = st.chat_input("Ngobrol dengan Kurumi...", key="kurumi_chat_input")

if _user_msg:
    _time_now = _now_jkt().strftime("%H:%M")

    st.session_state["kurumi_history"].append({
        "role": "user", "content": _user_msg, "time": _time_now,
    })
    if _MEMORY_OK:
        save_message("kurumi", _session_id, "user", _user_msg)

    with _chat_container:
        with st.chat_message("user", avatar="👤"):
            st.markdown(_user_msg)
            st.markdown(
                f"<div class='bubble-time' style='text-align: right;'>"
                f"● {_time_now}</div>",
                unsafe_allow_html=True,
            )

        with st.chat_message("assistant", avatar="🎀"):
            with st.spinner("🎀 Aku lagi mikir..."):
                _resp = kurumi_chat_response(_user_msg, st.session_state["kurumi_history"])

            _text = _resp.get("text", "") if isinstance(_resp, dict) else _resp
            _file = _resp.get("file") if isinstance(_resp, dict) else None

            st.markdown(_text)
            st.markdown(
                f"<div class='bubble-time' style='text-align: left;'>"
                f"● {_time_now}</div>",
                unsafe_allow_html=True,
            )

            if _file:
                st.markdown("---")
                _col_dl, _ = st.columns([2, 3])
                with _col_dl:
                    st.download_button(
                        label=f"📥 Download {_file.get('format', 'file').upper()}",
                        data=_file["content"],
                        file_name=_file["filename"],
                        mime=_file["mime"],
                        width="stretch",
                        type="primary",
                        key=f"dl_chat_{time.time()}",
                    )

    _entry = {"role": "assistant", "content": _text, "time": _time_now}
    if _file:
        _entry["file"] = _file

    st.session_state["kurumi_history"].append(_entry)
    if _MEMORY_OK:
        save_message("kurumi", _session_id, "assistant", _text)

    st.rerun()

# =========================================================================
# FOOTER TIPIS
# =========================================================================
_total_msg = len(st.session_state["kurumi_history"])
_model_str = "kurumi"

st.markdown(
    f"<div class='memory-info-footer'>"
    f"🧠 Session: <code style='color: #a855f7;'>{_session_id[-12:]}</code> | "
    f"💬 <b style='color: #F5E6D3;'>{_total_msg}</b> pesan | "
    f"⚙️ <b style='color: #a855f7;'>{_model_str}</b>"
    f"</div>",
    unsafe_allow_html=True,
)