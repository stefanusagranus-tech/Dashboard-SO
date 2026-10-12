"""
AI Chat Rei — Analis SO (AI-3) v10
====================================
Layout: WhatsApp-style, full screen, bubble chat + timestamp
Header: Custom Component v2 (STABIL, tombol nempel di header)
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
# CSS — FULL SCREEN + BUBBLE + POPOVER
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

if "rei_show_menu" not in st.session_state:
    st.session_state["rei_show_menu"] = False

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
# HEADER — CUSTOM COMPONENT V2 (TANPA JAM, REI DI TENGAH)
# =========================================================
_rei_header_component = st.components.v2.component(
    name="rei_header",
    html="""
    <div class="rei-header">
        <button id="btn-back" class="hdr-btn">←</button>
        <span class="hdr-title">📊 REI</span>
        <button id="btn-menu" class="hdr-btn">⋮</button>
    </div>
    """,
    css="""
    .rei-header {
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
            backBtn.onclick = () => {
                setTriggerValue('back', true);
            };
        }

        if (menuBtn) {
            menuBtn.onclick = () => {
                setTriggerValue('menu', true);
            };
        }
    }
    """,
    isolate_styles=True,
)

# Mount komponen
_header_result = _rei_header_component(
    data={},
    key="rei_header",
    on_back_change=lambda: None,
    on_menu_change=lambda: None,
)

# Handle trigger back
if _header_result.get("back"):
    try:
        st.switch_page("Dashboard.py")
    except Exception:
        st.warning("⚠️ Gagal pindah.")

# Handle trigger menu → buka dialog
if _header_result.get("menu"):
    st.session_state["rei_show_menu"] = True
    st.rerun()
    
# =========================================================
# MENU DIALOG (MODAL — overlay, gak nyorong chat)
# =========================================================
@st.dialog("⚙️ Menu Rei", width="small")
def _rei_menu_dialog():
    st.caption("📈 ANALISIS")
    if st.button("📈 Trend SO", use_container_width=True, key="pop_trend"):
        st.session_state["rei_preset"] = COMMANDS["/trend"]
        st.session_state["rei_show_menu"] = False
        st.rerun()
    if st.button("📋 LPJ SO", use_container_width=True, key="pop_lpj"):
        st.session_state["rei_preset"] = COMMANDS["/lpj"]
        st.session_state["rei_show_menu"] = False
        st.rerun()
    if st.button("🔮 Prediksi", use_container_width=True, key="pop_pred"):
        st.session_state["rei_preset"] = COMMANDS["/prediksi"]
        st.session_state["rei_show_menu"] = False
        st.rerun()
    if st.button("🔍 Top Item", use_container_width=True, key="pop_item"):
        st.session_state["rei_preset"] = COMMANDS["/item"]
        st.session_state["rei_show_menu"] = False
        st.rerun()
    if st.button("💡 Insight", use_container_width=True, key="pop_insight"):
        st.session_state["rei_preset"] = COMMANDS["/insight"]
        st.session_state["rei_show_menu"] = False
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
        st.session_state["rei_show_menu"] = False
        st.session_state["show_restore_dialog"] = True
        st.rerun()
    if st.button("🆕 New Chat", use_container_width=True, key="pop_new"):
        new_session_id("rei")
        st.session_state["rei_history"] = []
        st.session_state["rei_last_model"] = None
        st.session_state["rei_show_menu"] = False
        st.rerun()
    if st.button("🗑️ Hapus Sesi Ini", use_container_width=True, key="pop_delete"):
        clear_session("rei", _session_id)
        st.session_state["rei_history"] = []
        st.session_state["rei_last_model"] = None
        st.session_state["rei_show_menu"] = False
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
        st.session_state["rei_show_menu"] = False
        st.rerun()
    if st.button("❌ Tutup", use_container_width=True, key="pop_close"):
        st.session_state["rei_show_menu"] = False
        st.rerun()


# Trigger menu dialog
if st.session_state.get("rei_show_menu"):
    _rei_menu_dialog()


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
    """Ambil data SO real dari DB buat konteks Rei — agregat + item-level."""
    try:
        _ctx_parts = []

        # === 1. REKAP BULAN INI ===
        _hasil_bulan = rekap_so(mode="bulan_ini")
        if _hasil_bulan.get("success"):
            _nom = _hasil_bulan.get("total_nominal", 0)
            _ctx_parts.append(
                f"=== REKAP BULAN INI ({_hasil_bulan.get('periode', '-')}) ===\n"
                f"Total Rak: {_hasil_bulan.get('total_rak', 0)}\n"
                f"Total Item: {_hasil_bulan.get('total_item', 0)}\n"
                f"Total Selisih (Net): {fmt_rp_signed(_nom)}"
            )

            _list_rak = _hasil_bulan.get("list_rak", [])
            if _list_rak:
                _top_minus = sorted(_list_rak, key=lambda x: x["total"])[:5]
                _ctx_parts.append("\n=== TOP 5 RAK MINUS ===")
                for _r in _top_minus:
                    _ctx_parts.append(
                        f"- Rak {_r['rak_id']}: {fmt_rp_signed(_r['total'])} (PIC: {_r['pic']})"
                    )

            # === DISTRIBUSI PER PIC ===
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

        # === 2. LOST SALES & SHRINKAGE (GROSS + NET) ===
        try:
            _sb = get_supabase()
            _now = _now_jkt().date()
            _start_of_month = _now.replace(day=1)

            _res = (
                _sb.table("so_hasil")
                .select("qty_var, nominal_adjust")
                .gte("so_date", _start_of_month.isoformat())
                .lte("so_date", _now.isoformat())
                .execute()
            )
            _rows = _res.data or []

            _gross_minus = 0
            _total_plus = 0
            for _r in _rows:
                _qty = int(_r.get("qty_var", 0) or 0)
                _nom = float(_r.get("nominal_adjust", 0) or 0)
                if _qty < 0:
                    _gross_minus += abs(_nom)
                elif _qty > 0:
                    _total_plus += _nom

            _net = abs(_gross_minus - _total_plus)
            _net_sales = _get_net_sales_bulan()
            _shrinkage = (_net / _net_sales * 100) if _net_sales > 0 else 0

            _ctx_parts.append(
                f"\n=== LOST SALES & SHRINKAGE ===\n"
                f"Gross Lost Sales (Σ minus): Rp {_gross_minus:,.0f}\n"
                f"Kompensasi (Σ plus): Rp {_total_plus:,.0f}\n"
                f"Net Lost Sales: Rp {_net:,.0f}\n"
                f"Shrinkage Rate: {_shrinkage:.2f}% dari Net Sales Rp {_net_sales:,.0f}\n"
                f"Benchmark: < 2% (aman) | > 2% (perlu perhatian)"
            )
        except Exception as _e:
            print(f"[Rei ctx lost sales] {_e}")

        # === 3. BTSB & NSB ===
        try:
            _net_sales = _get_net_sales_bulan()
            _total_selisih = _get_total_selisih_bulan()
            _btsb = _net_sales * 0.0015
            _nsb = max(0, abs(_total_selisih) - _btsb)
            _ctx_parts.append(
                f"\n=== BTSB & NSB ===\n"
                f"Net Sales: {fmt_rp(_net_sales)}\n"
                f"BTSB (0,15%): {fmt_rp(_btsb)}\n"
                f"Total Selisih: {fmt_rp(abs(_total_selisih))}\n"
                f"NSB: {fmt_rp(_nsb)}\n"
                f"Status: {'PERLU PERHATIAN' if abs(_total_selisih) > _btsb else 'DALAM TOLERANSI'}"
            )
        except Exception as _e:
            print(f"[Rei ctx BTSB] {_e}")

        # === 4. TREND 7 HARI ===
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

        # === 5. TOP ITEM (FOKUS NOMINAL) ===
        try:
            _top = get_top_items(mode="bulan_ini", limit=30, only_minus=True)
            _items = _top.get("items", [])
            if _items:
                _total_item_nominal = sum(abs(_it.get("nominal_adjust", 0)) for _it in _items)
                _ctx_parts.append(
                    f"\n=== TOP ITEM SELISIH TERBESAR ({_top.get('periode', '-')}) ===\n"
                    f"Total dari {len(_items)} item: Rp {_total_item_nominal:,.0f}"
                )
                for _i, _it in enumerate(_items[:15], 1):
                    _nom = abs(_it.get("nominal_adjust", 0))
                    _ctx_parts.append(
                        f"{_i}. {_it.get('nama_produk', '-')} "
                        f"(Rak {_it.get('rak_id', '-')}, PIC: {_it.get('pic', '-')}): "
                        f"Rp {_nom:,.0f}"
                    )
        except Exception as _e:
            print(f"[Rei ctx top items] {_e}")

        return "\n".join(_ctx_parts)
    except Exception as _e:
        print(f"[Rei] Gagal build context: {_e}")
        import traceback
        print(traceback.format_exc())
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

