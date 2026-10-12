"""
AI Chat Rei — Analis SO (AI-3) v1
===================================
Rei = analis SO: trend, LPJ, prediksi, insight.
Bukan data entry — itu tugasnya Yui.
"""

import streamlit as st
import time
import pandas as pd
from datetime import datetime, date
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
    )
    from modules.yui_rekap import rekap_so, get_top_items, _get_net_sales_bulan, _get_total_selisih_bulan
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
# CSS
# =========================================================
def inject_rei_css():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        .main .block-container {
            max-width: 100% !important;
            padding: 1rem 2rem !important;
        }
        .stApp, .stApp * { color: #F5E6D3 !important; }
        .stApp textarea, .stApp input, .stApp [contenteditable="true"] {
            color: #F5E6D3 !important;
            background: rgba(30, 20, 60, 0.6) !important;
        }
        [data-testid="stChatMessage"] {
            padding: 0.85rem 1.2rem !important;
            margin-bottom: 0.6rem !important;
            border-radius: 16px !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(135deg, rgba(127, 185, 155, 0.25), rgba(232, 177, 137, 0.15)) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.6) !important;
            margin-left: 20% !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.85), rgba(76, 29, 149, 0.65)) !important;
            border: 1.5px solid rgba(232, 177, 137, 0.5) !important;
            margin-right: 20% !important;
        }
        [data-testid="stChatInputContainer"] {
            background: rgba(30, 20, 60, 0.6) !important;
            border-radius: 16px !important;
            border: 1.5px solid rgba(232, 177, 137, 0.6) !important;
        }
        .memory-info {
            background: rgba(20, 12, 35, 0.95);
            border-left: 3px solid #E8B189;
            border-radius: 8px;
            padding: 8px 14px;
            margin-bottom: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: #A89B8E;
        }
        .model-badge {
            display: inline-block;
            background: rgba(232, 177, 137, 0.15);
            border: 1px solid rgba(232, 177, 137, 0.5);
            border-radius: 6px;
            padding: 2px 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            color: #E8B189;
            margin-left: 8px;
        }
    </style>
    """, unsafe_allow_html=True)


inject_rei_css()


if not _REI_OK:
    st.error(f"❌ Gagal import: {_import_error}")
    st.stop()


# =========================================================
# HEADER
# =========================================================
def render_header():
    _time_str = _now_jkt().strftime("%H:%M")
    _col_back, _col_title, _col_status = st.columns([1, 3, 1])

    with _col_back:
        if st.button("← Dashboard", key="btn_back_rei", width="stretch"):
            try:
                st.switch_page("Dashboard.py")
            except Exception:
                st.warning("⚠️ Gagal pindah.")

    with _col_title:
        st.markdown(
            "<div style='text-align: center;'>"
            "<div style='font-family: Cinzel, serif; font-size: 22px; font-weight: 900; "
            "color: #E8B189; letter-spacing: 2px; text-shadow: 0 0 15px rgba(232, 177, 137, 0.6);'>"
            "📊 REI 📊</div>"
            "<div style='font-family: Quicksand, sans-serif; font-size: 10px; "
            "color: #7FB99B; letter-spacing: 1.5px; margin-top: 2px;'>"
            "Analis SO — Trend, LPJ, Prediksi, Insight</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    with _col_status:
        st.markdown(
            f"<div style='text-align: right; font-family: JetBrains Mono, monospace; "
            f"font-size: 10px; color: #E8B189; padding-top: 8px;'>"
            f"🕐 {_time_str} WIB<br>● ONLINE</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")


render_header()


# =========================================================
# SESSION STATE
# =========================================================
_session_id = get_or_create_session_id("rei")

if "rei_history" not in st.session_state:
    with st.spinner("⏳ Load chat..."):
        _saved = load_messages("rei", _session_id, limit=100)
    st.session_state["rei_history"] = [
        {"role": _m.get("role", "user"), "content": _m.get("content", "")}
        for _m in _saved
    ]

if "rei_preset" not in st.session_state:
    st.session_state["rei_preset"] = ""

if "rei_last_model" not in st.session_state:
    st.session_state["rei_last_model"] = None


# Welcome
if not st.session_state["rei_history"]:
    _welcome = (
        "📊 **Halo Bos!** Aku Rei, analis SO Toko C383.\n\n"
        "Aku bisa bantu analisis:\n"
        "- 📈 Trend SO (harian, mingguan, bulanan)\n"
        "- 📋 LPJ (Laporan Pertanggungjawaban)\n"
        "- 🔮 Prediksi SO bulan depan\n"
        "- 💡 Insight & rekomendasi audit\n\n"
        "**Catatan:** Aku ANALIS — buat input data, tanya Yui ya 📦\n\n"
        "Mau mulai dari mana?"
    )
    st.session_state["rei_history"].append({"role": "assistant", "content": _welcome})
    save_message("rei", _session_id, "assistant", _welcome)


_total_msg = len(st.session_state["rei_history"])
_model_badge = ""
if st.session_state["rei_last_model"]:
    _model_badge = f" | Model terakhir: <b style='color: #E8B189;'>{st.session_state['rei_last_model']}</b>"

st.markdown(
    f"<div class='memory-info'>"
    f"🧠 <b>Memory Aktif</b> | Session: <code style='color: #E8B189;'>{_session_id[-15:]}</code> | "
    f"Total: <b style='color: #7FB99B;'>{_total_msg}</b> pesan{_model_badge}"
    f"</div>",
    unsafe_allow_html=True,
)


# =========================================================
# TOOLBAR AKSI CEPAT
# =========================================================
st.markdown("#### ⚡ Analisis Cepat")
_c1, _c2, _c3, _c4, _c5 = st.columns(5)

with _c1:
    if st.button("📈 Trend SO", width="stretch", key="btn_rei_trend"):
        st.session_state["rei_preset"] = "Analisis trend SO bulan ini dong. Bandingin sama bulan lalu, kasih insight."

with _c2:
    if st.button("📋 LPJ SO", width="stretch", key="btn_rei_lpj"):
        st.session_state["rei_preset"] = "Buatkan LPJ (Laporan Pertanggungjawaban) SO bulan ini. Lengkap dengan analisis BTSB/NSB."

with _c3:
    if st.button("🔮 Prediksi", width="stretch", key="btn_rei_prediksi"):
        st.session_state["rei_preset"] = "Prediksi SO bulan depan berdasarkan trend 3 bulan terakhir. Kasih angka + rekomendasi."

with _c4:
    if st.button("💡 Insight", width="stretch", key="btn_rei_insight"):
        st.session_state["rei_preset"] = "Kasih insight dari data SO bulan ini. Rak mana paling minus? PIC mana paling sering selisih?"

with _c5:
    if st.button("🗑️ Reset", width="stretch", key="btn_rei_reset"):
        clear_session("rei", _session_id)
        st.session_state["rei_history"] = []
        st.session_state["rei_last_model"] = None
        st.rerun()

st.markdown("---")


# =========================================================
# RENDER CHAT HISTORY
# =========================================================
st.markdown("#### 💬 Percakapan")
for _msg in st.session_state["rei_history"]:
    _role = _msg.get("role", "user")
    with st.chat_message(_role, avatar="👤" if _role == "user" else "📊"):
        st.markdown(_msg.get("content", ""))
        

# =========================================================
# HELPER: BUILD DATA CONTEXT
# =========================================================
def _build_data_context():
    """Ambil data SO real dari DB buat konteks Rei."""
    try:
        _ctx_parts = []

        # === REKAP BULAN INI ===
        _hasil_bulan = rekap_so(mode="bulan_ini")
        if _hasil_bulan.get("success"):
            _nom = _hasil_bulan.get("total_nominal", 0)
            _ctx_parts.append(
                f"REKAP BULAN INI ({_hasil_bulan.get('periode', '-')}):\n"
                f"- Total Rak: {_hasil_bulan.get('total_rak', 0)}\n"
                f"- Total Item: {_hasil_bulan.get('total_item', 0)}\n"
                f"- Total Nominal: {fmt_rp_signed(_nom)}\n"
            )

            _list_rak = _hasil_bulan.get("list_rak", [])
            if _list_rak:
                _top_minus = sorted(_list_rak, key=lambda x: x["total"])[:5]
                _ctx_parts.append("TOP 5 RAK MINUS BULAN INI:")
                for _r in _top_minus:
                    _ctx_parts.append(
                        f"  - Rak {_r['rak_id']}: {fmt_rp_signed(_r['total'])} (PIC: {_r['pic']})"
                    )
                _ctx_parts.append("")

        # === BTSB & NSB ===
        try:
            _net_sales = _get_net_sales_bulan()
            _total_selisih = _get_total_selisih_bulan()
            _btsb = _net_sales * 0.0015
            _nsb = max(0, abs(_total_selisih) - _btsb)

            _ctx_parts.append(
                f"BTSB & NSB BULAN INI:\n"
                f"- Net Sales: {fmt_rp(_net_sales)}\n"
                f"- BTSB (0,15%): {fmt_rp(_btsb)}\n"
                f"- Total Selisih: {fmt_rp(abs(_total_selisih))}\n"
                f"- NSB: {fmt_rp(_nsb)}\n"
                f"- Status: {'OVER' if abs(_total_selisih) > _btsb else 'AMAN'}\n"
            )
        except Exception as _e:
            pass

        # === TREND 7 HARI TERAKHIR ===
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

                _ctx_parts.append("TREND 7 HARI TERAKHIR:")
                for _, _r in _grp.iterrows():
                    _ctx_parts.append(
                        f"  - {_r['so_date'].strftime('%d/%m')}: {fmt_rp_signed(_r['nominal_adjust'])}"
                    )
                _ctx_parts.append("")
        except Exception as _e:
            pass

        # === TOP 5 ITEM ===
        try:
            _top = get_top_items(limit=5)
            _top_minus = _top.get("top_minus", [])
            if _top_minus:
                _ctx_parts.append("TOP 5 ITEM MINUS:")
                for _it in _top_minus:
                    _ctx_parts.append(
                        f"  - {_it.get('nama_produk', '-')[:30]} "
                        f"(rak {_it.get('rak_id', '-')}): {fmt_rp_signed(_it.get('nominal_adjust', 0))}"
                    )
                _ctx_parts.append("")
        except Exception as _e:
            pass

        return "\n".join(_ctx_parts)
    except Exception as _e:
        print(f"[Rei] Gagal build context: {_e}")
        return ""


# =========================================================
# CHAT INPUT
# =========================================================
_preset = st.session_state.pop("rei_preset", "")
_user_msg = st.chat_input("Tanya Rei soal analisis SO...", key="rei_chat_input")

if _preset and not _user_msg:
    _user_msg = _preset

if _user_msg:
    st.session_state["rei_history"].append({"role": "user", "content": _user_msg})
    save_message("rei", _session_id, "user", _user_msg)

    with st.chat_message("user", avatar="👤"):
        st.markdown(_user_msg)

    with st.chat_message("assistant", avatar="📊"):
        with st.spinner("📊 Rei analisis data..."):
            # Build context dari DB
            _data_context = _build_data_context()

            # Panggil Rei
            _result = rei_chat(
                user_message=_user_msg,
                conversation_history=st.session_state["rei_history"],
                data_context=_data_context,
            )

            _resp = _result.get("text", "")
            _model = _result.get("model")
            _err = _result.get("error")

            # Tampilkan response
            st.markdown(_resp)

            # Badge model yang dipake
            if _model:
                st.markdown(
                    f"<div style='text-align: right; margin-top: 4px;'>"
                    f"<span class='model-badge'>⚙️ {_model}</span></div>",
                    unsafe_allow_html=True,
                )
                st.session_state["rei_last_model"] = _model

            # Simpan history
            st.session_state["rei_history"].append({"role": "assistant", "content": _resp})
            save_message("rei", _session_id, "assistant", _resp)

    st.rerun()


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    "<div style='text-align: center; padding: 20px 0; font-family: Quicksand; "
    "font-size: 10px; color: #7a9b8e; letter-spacing: 1px;'>"
    "📊 Rei — Analis SO | Dashboard SO Toko C383 📊"
    "</div>",
    unsafe_allow_html=True,
)