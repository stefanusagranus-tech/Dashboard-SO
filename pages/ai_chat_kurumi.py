"""
AI Chat Kurumi — Chief of Staff (AI-0)
========================================
Halaman chat fullscreen untuk Kurumi.
Persona: Tokisaki Kurumi (versi ramah kerja).
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
except ImportError as e:
    st.error(f"❌ Gagal import module: {e}")
    st.info("💡 Pastikan `modules/ai_core.py` udah di-upload.")
    st.stop()


# =========================================================================
# CSS — ROOM CHAT (FIX WARNA TEXT)
# =========================================================================
def inject_chat_css():
    st.markdown("""
    <style>
        /* Sembunyiin sidebar default */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        /* Full width container */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1rem !important;
        }

        /* === GLOBAL FORCE TEXT COLOR === */
        .stApp, .stApp * {
            color: #F5E6D3 !important;
        }

        /* Tombol tetep punya warna sendiri */
        .stApp button {
            color: inherit !important;
        }

        /* Text input & chat input */
        .stApp textarea,
        .stApp input,
        .stApp [contenteditable="true"] {
            color: #F5E6D3 !important;
            background: rgba(30, 20, 60, 0.6) !important;
            caret-color: #a855f7 !important;
        }

        .stApp textarea::placeholder,
        .stApp input::placeholder {
            color: rgba(245, 230, 211, 0.5) !important;
        }

        /* === CHAT BUBBLE === */
        [data-testid="stChatMessage"] {
            padding: 0.85rem 1.2rem !important;
            margin-bottom: 0.6rem !important;
            border-radius: 16px !important;
            backdrop-filter: blur(8px) !important;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] strong,
        [data-testid="stChatMessage"] em {
            color: #F5E6D3 !important;
        }

        /* USER BUBBLE (KANAN) */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(232, 177, 137, 0.20)) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.6) !important;
            margin-left: 20% !important;
        }

        /* ASSISTANT BUBBLE (KIRI) */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.85), rgba(76, 29, 149, 0.65)) !important;
            border: 1.5px solid rgba(168, 85, 247, 0.6) !important;
            margin-right: 20% !important;
        }

        /* Avatar */
        [data-testid="chatAvatarIcon-assistant"] {
            background: linear-gradient(135deg, #a855f7, #E8B189) !important;
        }

        /* === CHAT INPUT CONTAINER === */
        [data-testid="stChatInputContainer"] {
            background: rgba(30, 20, 60, 0.6) !important;
            border-radius: 16px !important;
            border: 1.5px solid rgba(168, 85, 247, 0.6) !important;
        }

        [data-testid="stChatInputContainer"] textarea,
        [data-testid="stChatInputContainer"] input {
            color: #F5E6D3 !important;
            background: transparent !important;
            caret-color: #a855f7 !important;
        }

        [data-testid="stChatInputContainer"] textarea::placeholder,
        [data-testid="stChatInputContainer"] input::placeholder {
            color: rgba(245, 230, 211, 0.5) !important;
        }

        /* Tombol kirim chat */
        [data-testid="stChatInputContainer"] button {
            background: linear-gradient(135deg, #a855f7, #E8B189) !important;
            border: none !important;
            color: #fff !important;
        }

        /* Tombol action */
        div[data-testid="stHorizontalBlock"] button {
            border-radius: 12px !important;
            font-weight: 700 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# HEADER
# =========================================================================
def render_kurumi_header():
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _time_str = _now.strftime("%H:%M")

    _col_back, _col_title, _col_status = st.columns([1, 3, 1])

    with _col_back:
        if st.button("← Dashboard", key="btn_back_kurumi", use_container_width=True):
            try:
                st.switch_page("Dashboard.py")
            except Exception:
                st.warning("⚠️ Gagal pindah halaman. Refresh manual ya.")

    with _col_title:
        st.markdown(
            "<div style='text-align: center;'>"
            "<div style='font-family: Cinzel, serif; font-size: 22px; "
            "font-weight: 900; color: #a855f7; letter-spacing: 2px; "
            "text-shadow: 0 0 15px rgba(168, 85, 247, 0.6);'>"
            "🎀 KURUMI 🎀</div>"
            "<div style='font-family: Quicksand, sans-serif; font-size: 10px; "
            "color: #E8B189; letter-spacing: 1.5px; margin-top: 2px;'>"
            "Spirit of Time — Chief of Staff Toko C383</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    with _col_status:
        st.markdown(
            f"<div style='text-align: right; font-family: JetBrains Mono, monospace; "
            f"font-size: 10px; color: #7FB99B; padding-top: 8px;'>"
            f"🕐 {_time_str} WIB<br>● ONLINE</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")


render_kurumi_header()


# =========================================================================
# SESSION STATE
# =========================================================================
if "kurumi_history" not in st.session_state:
    st.session_state["kurumi_history"] = []

if "kurumi_mode" not in st.session_state:
    st.session_state["kurumi_mode"] = "chat"

if "kurumi_rangkum_choice" not in st.session_state:
    st.session_state["kurumi_rangkum_choice"] = None

if "kurumi_report_choice" not in st.session_state:
    st.session_state["kurumi_report_choice"] = None


# =========================================================================
# WELCOME MESSAGE
# =========================================================================
if not st.session_state["kurumi_history"]:
    _welcome = (
        "🎀 **Ara, ara~** Selamat datang, Tuan~ ✨\n\n"
        "Aku adalah **Kurumi**, Chief of Staff Toko C383. "
        "Kihihihi~ Senang akhirnya bisa bertemu Tuan di sini.\n\n"
        "Fufufu~ Ada yang bisa aku bantu hari ini, Tuan? "
        "Tuan bisa langsung ngobrol santai, atau pilih tombol di bawah~ 🎀"
    )
    st.session_state["kurumi_history"].append({
        "role": "assistant",
        "content": _welcome,
    })


# =========================================================================
# TOOLBAR — 2 TOMBOL ACTION
# =========================================================================
st.markdown("#### 🎯 Aksi Cepat")
_col_a1, _col_a2 = st.columns(2)

with _col_a1:
    if st.button("📊 Rangkum", use_container_width=True, key="btn_kurumi_rangkum"):
        st.session_state["kurumi_mode"] = "rangkum"
        st.session_state["kurumi_rangkum_choice"] = None
        st.rerun()

with _col_a2:
    if st.button("📤 Kirim Laporan", use_container_width=True, key="btn_kurumi_send"):
        st.session_state["kurumi_mode"] = "report"
        st.session_state["kurumi_report_choice"] = None
        st.rerun()

st.markdown("---")


# =========================================================================
# MODE RANGKUM
# =========================================================================
if st.session_state["kurumi_mode"] == "rangkum":
    st.markdown("#### 🎀 Kurumi Bertanya...")

    _q_msg = (
        "Ara, ara~ Tuan mau aku rangkum yang mana nih? 🎀\n\n"
        "Pilih salah satu di bawah ya~"
    )
    st.info(_q_msg)

    _col_r1, _col_r2, _col_r3, _col_r4 = st.columns(4)
    with _col_r1:
        if st.button("📅 Hari Ini", use_container_width=True, key="btn_r_hari"):
            st.session_state["kurumi_rangkum_choice"] = "hari"
    with _col_r2:
        if st.button("🗓️ Minggu Ini", use_container_width=True, key="btn_r_minggu"):
            st.session_state["kurumi_rangkum_choice"] = "minggu"
    with _col_r3:
        if st.button("📆 Bulan Ini", use_container_width=True, key="btn_r_bulan"):
            st.session_state["kurumi_rangkum_choice"] = "bulan"
    with _col_r4:
        if st.button("❌ Batal", use_container_width=True, key="btn_r_batal"):
            st.session_state["kurumi_mode"] = "chat"
            st.session_state["kurumi_rangkum_choice"] = None
            st.rerun()

    if st.session_state["kurumi_rangkum_choice"]:
        _choice = st.session_state["kurumi_rangkum_choice"]
        _label = {"hari": "hari ini", "minggu": "minggu ini", "bulan": "bulan ini"}[_choice]

        st.session_state["kurumi_history"].append({
            "role": "user",
            "content": f"Rangkum {_label} dong~",
        })

        with st.spinner(f"🎀 Aku rangkum {_label}..."):
            _summary = kurumi_summarize(period=_choice)

        st.session_state["kurumi_history"].append({
            "role": "assistant",
            "content": _summary,
        })

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
        if st.button("📄 Text", use_container_width=True, key="btn_f_text"):
            st.session_state["kurumi_report_choice"] = "text"
    with _col_f2:
        if st.button("📕 PDF", use_container_width=True, key="btn_f_pdf"):
            st.session_state["kurumi_report_choice"] = "pdf"
    with _col_f3:
        if st.button("📗 Excel", use_container_width=True, key="btn_f_excel"):
            st.session_state["kurumi_report_choice"] = "excel"
    with _col_f4:
        if st.button("❌ Batal", use_container_width=True, key="btn_f_batal"):
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
                use_container_width=True,
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
# RENDER CHAT HISTORY
# =========================================================================
st.markdown("#### 💬 Percakapan")

for _idx, _msg in enumerate(st.session_state["kurumi_history"]):
    _role = _msg.get("role", "user")
    _content = _msg.get("content", "")
    _file_data = _msg.get("file")   # ← ambil file dari history
    
    with st.chat_message(_role, avatar="👤" if _role == "user" else "🎀"):
        st.markdown(_content)
        
        # ✅ Re-render tombol download kalau ada file di history
        if _file_data:
            st.markdown("---")
            _col_dl, _ = st.columns([2, 3])
            with _col_dl:
                st.download_button(
                    label=f"📥 Download {_file_data.get('format', 'file').upper()}",
                    data=_file_data["content"],
                    file_name=_file_data["filename"],
                    mime=_file_data["mime"],
                    use_container_width=True,
                    type="primary",
                    key=f"dl_hist_{_idx}",
                )


# =========================================================================
# INPUT CHAT
# =========================================================================
_user_msg = st.chat_input("Ngobrol dengan Kurumi...", key="kurumi_chat_input")

if _user_msg:
    st.session_state["kurumi_history"].append({"role": "user", "content": _user_msg})

    with st.chat_message("user", avatar="👤"):
        st.markdown(_user_msg)

    with st.chat_message("assistant", avatar="🎀"):
        with st.spinner("🎀 Aku lagi mikir..."):
            _resp = kurumi_chat_response(_user_msg, st.session_state["kurumi_history"])

        # ✅ Handle dict response
        _text = _resp.get("text", "") if isinstance(_resp, dict) else _resp
        _file = _resp.get("file") if isinstance(_resp, dict) else None

        st.markdown(_text)

        # ✅ Tombol download
        if _file:
            st.markdown("---")
            _col_dl, _ = st.columns([2, 3])
            with _col_dl:
                st.download_button(
                    label=f"📥 Download {_file.get('format', 'file').upper()}",
                    data=_file["content"],
                    file_name=_file["filename"],
                    mime=_file["mime"],
                    use_container_width=True,
                    type="primary",
                    key=f"dl_chat_{time.time()}",
                )

    # ✅ Simpan history — TERMASUK FILE
    _entry = {
        "role": "assistant",
        "content": _text,
    }
    if _file:
        _entry["file"] = _file   # ← INI KUNCINYA
    
    st.session_state["kurumi_history"].append(_entry)
    st.rerun()
    
# =========================================================================
# CLEAR CHAT
# =========================================================================
if len(st.session_state["kurumi_history"]) > 1:
    st.markdown("---")
    _col_clr, _ = st.columns([1, 4])
    with _col_clr:
        if st.button("🗑️ Clear Chat", key="btn_clear_kurumi"):
            st.session_state["kurumi_history"] = []
            st.session_state["kurumi_mode"] = "chat"
            st.session_state["kurumi_rangkum_choice"] = None
            st.session_state["kurumi_report_choice"] = None
            st.rerun()


# =========================================================================
# FOOTER
# =========================================================================
st.markdown(
    "<div style='text-align: center; padding: 20px 0; "
    "font-family: Quicksand, sans-serif; font-size: 10px; "
    "color: #7a9b8e; letter-spacing: 1px;'>"
    "🎀 Kurumi — Spirit of Time | Chief of Staff Toko C383 🎀"
    "</div>",
    unsafe_allow_html=True,
)