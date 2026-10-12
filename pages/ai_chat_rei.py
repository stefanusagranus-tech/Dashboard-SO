"""
AI Chat Rei — Analis SO (AI-3) v8
===================================
Layout: WhatsApp-style, full screen, bubble chat + timestamp
Changelog v8:
- Header 1 baris: [←] [📊 REI] [⏰ jam] [⋮] — semua sejajar horizontal
- Bubble chat dengan timestamp asli dari DB (created_at)
- Restore dialog (modal) untuk load sesi lama
- New Chat & Hapus Sesi di popover
- Session ID persistent (gak reset jam 12 malam)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from themes.theme_loader import (
    render_theme, render_theme_animations, get_theme_by_month,
)

st.set_page_config(
    page_title="Rei — Analis SO", page_icon="📊",
    layout="wide", initial_sidebar_state="collapsed",
)

CURRENT_THEME = get_theme_by_month()
render_theme(CURRENT_THEME)
render_theme_animations(CURRENT_THEME)


# =========================================================
# IMPORT MODULES
# =========================================================
try:
    from modules.ai_rei import rei_chat, rei_analisis
    from modules.chat_memory import (
        save_message, load_messages, get_or_create_session_id, clear_session,
        new_session_id, get_session_list, set_session_id, load_messages_by_session,
    )
    from modules.yui_rekap import (
        rekap_so, get_top_items, get_items_by_rak,
        _get_net_sales_bulan, _get_total_selisih_bulan,
    )
    from modules.supabase_client import get_supabase
    _REI_OK = True
except ImportError as _e:
    _REI_OK = False
    _import_error = str(_e)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def fmt_rp_signed(value):
    try:
        _v = float(value)
        _sign = "+" if _v >= 0 else "-"
        return f"{_sign}Rp {int(abs(_v)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp(value):
    try:
        return f"Rp {int(float(value)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


# =========================================================
# COMMAND PARSER
# =========================================================
COMMANDS = {
    "/trend":    "Analisis trend SO bulan ini dong. Bandingin sama bulan lalu, kasih insight.",
    "/lpj":      "Buatkan LPJ (Laporan Pertanggungjawaban) SO bulan ini. Lengkap dengan analisis BTSB/NSB.",
    "/prediksi": "Prediksi SO bulan depan berdasarkan trend 3 bulan terakhir. Kasih angka + rekomendasi.",
    "/insight":  "Kasih insight dari data SO bulan ini. Rak mana paling minus? PIC mana paling sering selisih?",
    "/item":     "Tampilkan top 10 item dengan selisih terbesar bulan ini. Analisis pola & kategorinya.",
    "/help":     "__HELP__",
}


def _parse_command(text):
    if not text:
        return text
    _t = text.strip().lower()
    if _t in COMMANDS:
        if COMMANDS[_t] == "__HELP__":
            return None
        return COMMANDS[_t]
    return text


# =========================================================
# EXPORT STUBS
# =========================================================
def _export_rei_pdf(history, session_id):
    st.info("🚧 **Export PDF belum diimplementasikan.** Coming soon!")

def _export_rei_ppt(history, session_id):
    st.info("🚧 **Export PPT belum diimplementasikan.** Coming soon!")
    
# =========================================================
# CSS — FULL SCREEN + BUBBLE + HEADER
# =========================================================
def inject_rei_css():
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
        }

        /* === CHAT MESSAGES — BUBBLE === */
        [data-testid="stChatMessage"] {
            padding: 0.6rem 1rem !important;
            margin-bottom: 0.8rem !important;
            border-radius: 18px !important;
            max-width: 85% !important;
            transition: all 0.2s ease !important;
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

        /* === SCROLLABLE CONTAINER === */
        div[data-testid="stVerticalBlock"] > div[style*="height"] {
            background: rgba(20, 12, 35, 0.4) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(232, 177, 137, 0.2) !important;
            padding: 8px !important;
        }

        /* ============================================
           HEADER BAR — FIXED DI ATAS (WA STYLE)
           ============================================ */
        .rei-header-bar {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 9999 !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 10px 60px 10px 60px !important;
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.98), rgba(76, 29, 149, 0.9)) !important;
            border-bottom: 2px solid rgba(232, 177, 137, 0.6) !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5) !important;
            min-height: 52px !important;
            box-sizing: border-box !important;
        }
        .rei-header-bar .rei-title {
            font-family: Cinzel, serif !important;
            font-size: 18px !important;
            font-weight: 900 !important;
            color: #E8B189 !important;
            letter-spacing: 1.5px !important;
            text-shadow: 0 0 10px rgba(232, 177, 137, 0.6) !important;
            line-height: 1 !important;
        }
        .rei-header-bar .rei-time {
            font-family: JetBrains Mono, monospace !important;
            font-size: 11px !important;
            color: #7FB99B !important;
            font-weight: 700 !important;
            padding: 4px 10px !important;
            background: rgba(127, 185, 155, 0.1) !important;
            border: 1px solid rgba(127, 185, 155, 0.4) !important;
            border-radius: 8px !important;
            line-height: 1 !important;
        }

        /* ============================================
           TOMBOL BACK — FIXED DI HEADER (KIRI)
           ============================================ */
        .main .block-container button[key="btn_back_rei"] {
            position: fixed !important;
            top: 8px !important;
            left: 10px !important;
            z-index: 10000 !important;
            height: 36px !important;
            min-height: 36px !important;
            width: 40px !important;
            background: rgba(30, 20, 60, 0.85) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.6) !important;
            border-radius: 10px !important;
            color: #E8B189 !important;
            font-size: 16px !important;
            font-weight: 900 !important;
            padding: 0 !important;
            transition: all 0.2s ease !important;
        }
        .main .block-container button[key="btn_back_rei"]:hover {
            background: rgba(232, 177, 137, 0.25) !important;
            border-color: #E8B189 !important;
        }

        /* ============================================
           POPOVER MENU — FIXED DI HEADER (KANAN)
           ============================================ */
        .main .block-container [data-testid="stPopover"] {
            position: fixed !important;
            top: 8px !important;
            right: 10px !important;
            z-index: 10000 !important;
            width: 40px !important;
        }
        .main .block-container [data-testid="stPopover"] > button {
            height: 36px !important;
            min-height: 36px !important;
            width: 40px !important;
            background: rgba(30, 20, 60, 0.85) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.6) !important;
            border-radius: 10px !important;
            color: #E8B189 !important;
            font-size: 18px !important;
            font-weight: 900 !important;
            padding: 0 !important;
            transition: all 0.2s ease !important;
        }
        .main .block-container [data-testid="stPopover"] > button:hover {
            background: rgba(232, 177, 137, 0.25) !important;
            border-color: #E8B189 !important;
        }

        /* === POPOVER BODY (MENU) === */
        [data-testid="stPopoverBody"] {
            background: rgba(20, 12, 35, 0.98) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.5) !important;
            border-radius: 12px !important;
            padding: 12px !important;
            z-index: 10001 !important;
        }
        [data-testid="stPopoverBody"] button {
            background: rgba(30, 20, 60, 0.6) !important;
            border: 1px solid rgba(232, 177, 137, 0.3) !important;
            border-radius: 8px !important;
            color: #F5E6D3 !important;
            font-size: 12px !important;
            margin-bottom: 4px !important;
        }

        /* === MODEL BADGE === */
        .model-badge {
            display: inline-block;
            background: rgba(232, 177, 137, 0.15);
            border: 1px solid rgba(232, 177, 137, 0.5);
            border-radius: 6px;
            padding: 2px 8px;
            font-family: JetBrains Mono, monospace;
            font-size: 9px;
            color: #E8B189;
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

        /* === MOBILE TWEAK === */
        @media (max-width: 480px) {
            .main .block-container {
                padding: 62px 0.4rem 0.4rem 0.4rem !important;
            }
            .rei-header-bar {
                padding: 8px 54px 8px 54px !important;
                min-height: 46px !important;
            }
            .rei-header-bar .rei-title { font-size: 15px !important; }
            .rei-header-bar .rei-time { font-size: 10px !important; padding: 3px 8px !important; }
            .main .block-container button[key="btn_back_rei"] {
                top: 6px !important;
                left: 8px !important;
                height: 34px !important;
                width: 38px !important;
                font-size: 15px !important;
            }
            .main .block-container [data-testid="stPopover"] {
                top: 6px !important;
                right: 8px !important;
                width: 38px !important;
            }
            .main .block-container [data-testid="stPopover"] > button {
                height: 34px !important;
                width: 38px !important;
                font-size: 16px !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)


inject_rei_css()

if not _REI_OK:
    st.error(f"❌ Gagal import: {_import_error}")
    st.stop()

# =========================================================
# SESSION STATE — PAKAI TIMESTAMP ASLI DARI DB
# =========================================================
_session_id = get_or_create_session_id("rei")

if "rei_history" not in st.session_state:
    with st.spinner("⏳ Load chat..."):
        _saved = load_messages("rei", _session_id, limit=100)

    st.session_state["rei_history"] = []
    for _m in _saved:
        st.session_state["rei_history"].append({
            "role": _m.get("role", "user"),
            "content": _m.get("content", ""),
            "time": _m.get("time_wib", "—"),
        })

if "rei_preset" not in st.session_state:
    st.session_state["rei_preset"] = ""

if "rei_last_model" not in st.session_state:
    st.session_state["rei_last_model"] = None

if "show_restore_dialog" not in st.session_state:
    st.session_state["show_restore_dialog"] = False

# Welcome
if not st.session_state["rei_history"]:
    _welcome = (
        "📊 **Halo Bos!** Aku Rei, analis SO Toko C383.\n\n"
        "Aku bisa bantu:\n"
        "- 📈 Trend SO\n"
        "- 📋 LPJ\n"
        "- 🔮 Prediksi SO\n"
        "- 💡 Insight audit\n"
        "- 🔍 Top item selisih\n\n"
        "**Command:** `/trend` `/lpj` `/prediksi` `/item` `/help`\n\n"
        "Aku ANALIS — buat input data, tanya Yui ya 📦"
    )
    st.session_state["rei_history"].append({
        "role": "assistant",
        "content": _welcome,
        "time": _now_jkt().strftime("%H:%M"),
    })
    save_message("rei", _session_id, "assistant", _welcome)
    
# =========================================================
# HEADER — HTML + TOMBOL OVERLAY (100% STABIL)
# =========================================================
_time_str = _now_jkt().strftime("%H:%M")

# 1. Header visual (HTML murni)
st.markdown(
    f"""
    <div class="rei-header-bar">
        <span class="rei-title">📊 REI</span>
        <span class="rei-time">⏰ {_time_str}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# 2. Tombol fungsional (di-render terpisah, di-overlay CSS)
_col_back, _col_spacer, _col_menu = st.columns([1, 6, 1])

with _col_back:
    if st.button("←", key="btn_back_rei", help="Balik ke Dashboard"):
        try:
            st.switch_page("Dashboard.py")
        except Exception:
            st.warning("⚠️ Gagal pindah.")

with _col_menu:
    with st.popover("⋮", use_container_width=False):
        st.markdown("**⚙️ Menu**")

        st.caption("📈 ANALISIS")
        if st.button("📈 Trend SO", use_container_width=True, key="pop_trend"):
            st.session_state["rei_preset"] = COMMANDS["/trend"]
            st.rerun()
        if st.button("📋 LPJ SO", use_container_width=True, key="pop_lpj"):
            st.session_state["rei_preset"] = COMMANDS["/lpj"]
            st.rerun()
        if st.button("🔮 Prediksi", use_container_width=True, key="pop_pred"):
            st.session_state["rei_preset"] = COMMANDS["/prediksi"]
            st.rerun()
        if st.button("🔍 Top Item", use_container_width=True, key="pop_item"):
            st.session_state["rei_preset"] = COMMANDS["/item"]
            st.rerun()
        if st.button("💡 Insight", use_container_width=True, key="pop_insight"):
            st.session_state["rei_preset"] = COMMANDS["/insight"]
            st.rerun()

        st.divider()

        st.caption("📤 EXPORT")
        if st.button("📄 PDF", use_container_width=True, key="pop_pdf"):
            _export_rei_pdf(st.session_state["rei_history"], _session_id)
        if st.button("📊 PPT", use_container_width=True, key="pop_ppt"):
            _export_rei_ppt(st.session_state["rei_history"], _session_id)

        st.divider()

        st.caption("💾 SESSION")
        if st.button("📂 Restore Chat", use_container_width=True, key="pop_restore"):
            st.session_state["show_restore_dialog"] = True
            st.rerun()
        if st.button("🆕 New Chat", use_container_width=True, key="pop_new"):
            new_session_id("rei")
            st.session_state["rei_history"] = []
            st.session_state["rei_last_model"] = None
            st.rerun()
        if st.button("🗑️ Hapus Sesi Ini", use_container_width=True, key="pop_delete"):
            clear_session("rei", _session_id)
            st.session_state["rei_history"] = []
            st.session_state["rei_last_model"] = None
            st.rerun()

        st.divider()

        st.caption("⚙️ SISTEM")
        _total_msg = len(st.session_state["rei_history"])
        _model_str = st.session_state.get("rei_last_model") or "—"
        st.caption(f"🧠 Session: `{_session_id[-12:]}`")
        st.caption(f"💬 Total: {_total_msg} pesan")
        st.caption(f"⚙️ Model: {_model_str}")

        st.divider()

        if st.button("💬 /help", use_container_width=True, key="pop_help"):
            st.session_state["rei_preset"] = "/help"
            st.rerun()
            
# =========================================================
# RESTORE DIALOG (MODAL)
# =========================================================
@st.dialog("📂 Restore Chat History", width="large")
def _restore_dialog():
    st.markdown(
        "<div style='font-family: Quicksand; font-size: 12px; color: #A89B8E;'>"
        "Pilih sesi yang mau di-restore. Sesi lama tetap tersimpan di database."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("⏳ Load sesi..."):
        _sessions = get_session_list("rei", limit=20)

    if not _sessions:
        st.info("📭 Belum ada sesi lain. Mulai chat dulu ya!")
        if st.button("Tutup", use_container_width=True):
            st.session_state["show_restore_dialog"] = False
            st.rerun()
        return

    st.markdown(f"**Total: {len(_sessions)} sesi**")
    st.divider()

    for _s in _sessions:
        _sid = _s["session_id"]
        _is_current = (_sid == _session_id)
        _total = _s["total_messages"]
        _preview = _s["preview"] or "(kosong)"

        from modules.chat_memory import _format_time_wib, _format_date_wib
        _last = _format_time_wib(_s["last_message_at"])
        _date = _format_date_wib(_s["last_message_at"])

        _marker = "🟢 **AKTIF**" if _is_current else ""

        with st.container(border=True):
            _c1, _c2 = st.columns([4, 1])
            with _c1:
                st.markdown(
                    f"**`{_sid}`** {_marker}\n\n"
                    f"💬 {_total} pesan · 🕐 {_date} {_last}\n\n"
                    f"> {_preview}..."
                )
            with _c2:
                if _is_current:
                    st.button(
                        "Aktif",
                        key=f"restore_{_sid}",
                        disabled=True,
                        use_container_width=True,
                    )
                else:
                    if st.button(
                        "📂 Restore",
                        key=f"restore_{_sid}",
                        use_container_width=True,
                        type="primary",
                    ):
                        set_session_id("rei", _sid)
                        _restored = load_messages_by_session("rei", _sid)
                        st.session_state["rei_history"] = [
                            {
                                "role": _m.get("role", "user"),
                                "content": _m.get("content", ""),
                                "time": _m.get("time_wib", "—"),
                            }
                            for _m in _restored
                        ]
                        st.session_state["show_restore_dialog"] = False
                        st.rerun()

    st.divider()
    if st.button("❌ Tutup", use_container_width=True):
        st.session_state["show_restore_dialog"] = False
        st.rerun()


# Trigger dialog
if st.session_state.get("show_restore_dialog"):
    _restore_dialog()

# =========================================================
# CHAT CONTAINER — BUBBLE + TIMESTAMP
# =========================================================
_CHAT_HEIGHT = 600

_chat_container = st.container(height=_CHAT_HEIGHT, border=False)

with _chat_container:
    for _msg in st.session_state["rei_history"]:
        _role = _msg.get("role", "user")
        _time_msg = _msg.get("time", "—")

        with st.chat_message(_role, avatar="👤" if _role == "user" else "📊"):
            st.markdown(_msg.get("content", ""))
            _align = "right" if _role == "user" else "left"
            st.markdown(
                f"<div class='bubble-time' style='text-align: {_align};'>"
                f"● {_time_msg}</div>",
                unsafe_allow_html=True,
            )

# =========================================================
# HELPER: BUILD DATA CONTEXT (ITEM-LEVEL)
# =========================================================
def _build_data_context():
    try:
        _ctx_parts = []

        _hasil_bulan = rekap_so(mode="bulan_ini")
        if _hasil_bulan.get("success"):
            _nom = _hasil_bulan.get("total_nominal", 0)
            _ctx_parts.append(
                f"=== REKAP BULAN INI ({_hasil_bulan.get('periode', '-')}) ===\n"
                f"Total Rak: {_hasil_bulan.get('total_rak', 0)}\n"
                f"Total Item: {_hasil_bulan.get('total_item', 0)}\n"
                f"Total Nominal: {fmt_rp_signed(_nom)}"
            )
            _list_rak = _hasil_bulan.get("list_rak", [])
            if _list_rak:
                _top_minus = sorted(_list_rak, key=lambda x: x["total"])[:5]
                _ctx_parts.append("\n=== TOP 5 RAK MINUS ===")
                for _r in _top_minus:
                    _ctx_parts.append(
                        f"- Rak {_r['rak_id']}: {fmt_rp_signed(_r['total'])} (PIC: {_r['pic']})"
                    )

            _pic_summary = {}
            for _r in _list_rak:
                _pic = _r.get("pic", "-")
                _pic_summary.setdefault(_pic, {"total": 0, "rak_count": 0})
                _pic_summary[_pic]["total"] += _r["total"]
                _pic_summary[_pic]["rak_count"] += 1
            if _pic_summary:
                _ctx_parts.append("\n=== DISTRIBUSI PER PIC ===")
                for _pic, _data in sorted(_pic_summary.items(), key=lambda x: x[1]["total"]):
                    _ctx_parts.append(
                        f"- {_pic}: {fmt_rp_signed(_data['total'])} ({_data['rak_count']} rak)"
                    )

        try:
            _net_sales = _get_net_sales_bulan()
            _total_selisih = _get_total_selisih_bulan()
            _btsb = _net_sales * 0.0015
            _nsb = max(0, abs(_total_selisih) - _btsb)
            _ctx_parts.append(
                f"\n=== BTSB & NSB BULAN INI ===\n"
                f"Net Sales: {fmt_rp(_net_sales)}\n"
                f"BTSB (0,15%): {fmt_rp(_btsb)}\n"
                f"Total Selisih: {fmt_rp(abs(_total_selisih))}\n"
                f"NSB: {fmt_rp(_nsb)}\n"
                f"Status: {'OVER' if abs(_total_selisih) > _btsb else 'AMAN'}"
            )
        except Exception as _e:
            print(f"[Rei ctx BTSB] {_e}")

        try:
            _sb = get_supabase()
            _now = _now_jkt().date()
            _start = _now - timedelta(days=6)
            _res = (
                _sb.table("so_rak_harian")
                .select("so_date, nominal_adjust")
                .gte("so_date", _start.isoformat())
                .lte("so_date", _now.isoformat())
                .execute()
            )
            if _res.data:
                _df = pd.DataFrame(_res.data)
                _df["so_date"] = pd.to_datetime(_df["so_date"], errors="coerce")
                _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
                _grp = _df.groupby("so_date")["nominal_adjust"].sum().reset_index().sort_values("so_date")
                _ctx_parts.append("\n=== TREND 7 HARI TERAKHIR ===")
                for _, _r in _grp.iterrows():
                    _ctx_parts.append(
                        f"- {_r['so_date'].strftime('%d/%m')}: {fmt_rp_signed(_r['nominal_adjust'])}"
                    )
        except Exception as _e:
            print(f"[Rei ctx trend] {_e}")

        try:
            _top = get_top_items(mode="bulan_ini", limit=15, only_minus=True)
            _items = _top.get("items", [])
            if _items:
                _ctx_parts.append(
                    f"\n=== TOP 15 ITEM SELISIH TERBESAR ({_top.get('periode', '-')}) ==="
                )
                for _i, _it in enumerate(_items, 1):
                    _ctx_parts.append(
                        f"{_i}. PLU {_it.get('plu', '-')} — {_it.get('nama_produk', '-')}\n"
                        f"   Rak: {_it.get('rak_id', '-')} | PIC: {_it.get('pic', '-')}\n"
                        f"   Qty var: {_it.get('qty_var', 0)} | Nominal: {fmt_rp_signed(_it.get('nominal_adjust', 0))}"
                    )
        except Exception as _e:
            print(f"[Rei ctx top items] {_e}")

        return "\n".join(_ctx_parts)
    except Exception as _e:
        print(f"[Rei] Gagal build context: {_e}")
        return ""
        
# =========================================================
# CHAT INPUT
# =========================================================
_preset = st.session_state.pop("rei_preset", "")

_user_msg = st.chat_input("Tanya Rei...", key="rei_chat_input")

if _preset and not _user_msg:
    _user_msg = _preset


# =========================================================
# CHAT HANDLER
# =========================================================
if _user_msg:
    _parsed = _parse_command(_user_msg)
    _time_now = _now_jkt().strftime("%H:%M")

    if _parsed is None:
        _help_text = (
            "**📋 Command:**\n\n"
            "- `/trend` — Trend SO bulan ini\n"
            "- `/lpj` — Laporan Pertanggungjawaban\n"
            "- `/prediksi` — Forecast bulan depan\n"
            "- `/insight` — Insight rak & PIC\n"
            "- `/item` — Top 10 item selisih\n"
            "- `/help` — Command ini\n\n"
            "Atau ketik bebas."
        )
        st.session_state["rei_history"].append({
            "role": "user",
            "content": _user_msg,
            "time": _time_now,
        })
        save_message("rei", _session_id, "user", _user_msg)
        st.session_state["rei_history"].append({
            "role": "assistant",
            "content": _help_text,
            "time": _time_now,
        })
        save_message("rei", _session_id, "assistant", _help_text)
        st.rerun()

    st.session_state["rei_history"].append({
        "role": "user",
        "content": _user_msg,
        "time": _time_now,
    })
    save_message("rei", _session_id, "user", _user_msg)

    with _chat_container:
        with st.chat_message("user", avatar="👤"):
            st.markdown(_user_msg)
            st.markdown(
                f"<div class='bubble-time' style='text-align: right;'>"
                f"● {_time_now}</div>",
                unsafe_allow_html=True,
            )

        with st.chat_message("assistant", avatar="📊"):
            with st.spinner("📊 Rei analisis data..."):
                _data_context = _build_data_context()

                _result = rei_chat(
                    user_message=_user_msg,
                    conversation_history=st.session_state["rei_history"],
                    data_context=_data_context,
                )

                _resp = _result.get("text", "")
                _model = _result.get("model")
                _time_resp = _now_jkt().strftime("%H:%M")

                st.markdown(_resp)

                if _model:
                    st.markdown(
                        f"<div style='text-align: right; margin-top: 4px;'>"
                        f"<span class='model-badge'>⚙️ {_model}</span></div>",
                        unsafe_allow_html=True,
                    )
                    st.session_state["rei_last_model"] = _model

                st.markdown(
                    f"<div class='bubble-time' style='text-align: left;'>"
                    f"● {_time_resp}</div>",
                    unsafe_allow_html=True,
                )

                st.session_state["rei_history"].append({
                    "role": "assistant",
                    "content": _resp,
                    "time": _time_resp,
                })
                save_message("rei", _session_id, "assistant", _resp)

    st.rerun()