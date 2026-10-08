"""
SO — Stock Opname (Konsolidasi v4 — Final)
============================================
Full replacement pages/input_so.py.

Alur 3-Screen di Tab 1 (Input SO):
1. Form Input   → isi SPD + multi-rak (PIC per rak)
2. Konfirmasi   → review sebelum simpan
3. Sukses       → notifikasi + summary

Tab:
1. 📝 Input SO   — 3-screen flow
2. 📊 Analisis   — Filter periode + tabel + Rak Belum SO + chart
3. 📋 Preview    — Preview & hapus SO per tanggal
"""

import streamlit as st
import time
import pandas as pd
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
    page_title="Stock Opname | Toko C383",
    page_icon="📝",
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
    from modules.so_handler import (
        load_so_summary_by_date,
        load_so_detail_by_date,
        delete_so_by_date,
    )
    from modules.master_shift_handler import load_personil_master
    from modules.data_loader import load_rak_master
    from modules.spd_calculator import (
        save_spd_harian,
        hitung_btsb_harian,
        hitung_btsb_akumulatif,
    )
    from modules.input_handler import (
        save_input_harian,
        search_rak,
        get_rak_by_kode_exact,
        get_so_rak_detail,
        get_akumulasi_nominal_bulan,
    )
except ImportError as _e:
    st.error(f"❌ Gagal import module: {_e}")
    st.stop()


# =========================================================================
# CSS — HALLOWEEN CONSISTENT
# =========================================================================
def inject_css():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        .main .block-container {
            max-width: 100% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-top: 0.5rem !important;
        }

        .stApp {
            font-family: 'Quicksand', -apple-system, sans-serif;
        }

        /* Header profile card */
        .profile-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 20px;
            background: linear-gradient(135deg, rgba(28, 16, 48, 0.95), rgba(45, 25, 75, 0.9));
            border: 1px solid rgba(232, 177, 137, 0.25);
            border-radius: 14px;
            margin-bottom: 20px;
        }
        .profile-title {
            font-family: 'Cinzel', serif;
            font-size: 16px;
            font-weight: 900;
            color: #E8B189;
            letter-spacing: 2px;
        }
        .profile-sub {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            color: #7FB99B;
            letter-spacing: 1px;
            margin-top: 2px;
        }
        .profile-status {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: #7FB99B;
            text-align: right;
        }

        /* Input labels */
        .stTextInput > label,
        .stNumberInput > label,
        .stSelectbox > label,
        .stDateInput > label {
            font-family: 'Quicksand', sans-serif !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            color: #A89B8E !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
        }

        /* Input fields */
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox > div > div,
        .stDateInput input {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            color: #F5E6D3 !important;
            background: rgba(20, 12, 35, 0.95) !important;
            border: 1px solid rgba(168, 85, 247, 0.3) !important;
            border-radius: 8px !important;
            min-height: 38px !important;
        }

        /* Buttons */
        div.stButton > button,
        div.stFormSubmitButton > button,
        div.stDownloadButton > button {
            font-family: 'Quicksand', sans-serif !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            letter-spacing: 0.5px !important;
            border-radius: 10px !important;
            min-height: 42px !important;
            transition: all 0.2s ease !important;
        }

        /* Metric clean */
        .metric-clean {
            background: linear-gradient(135deg, rgba(28, 16, 48, 0.95), rgba(45, 25, 75, 0.9));
            border: 1px solid rgba(168, 85, 247, 0.2);
            border-left: 3px solid #E8B189;
            border-radius: 10px;
            padding: 14px 18px;
            margin-bottom: 8px;
        }
        .metric-clean .label {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            color: #A89B8E;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .metric-clean .value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 900;
            color: #E8B189;
            line-height: 1.1;
        }
        .metric-clean .sub {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            color: #7a9b8e;
            margin-top: 4px;
        }

        /* Rak result */
        .rak-result {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: rgba(20, 12, 35, 0.95);
            border: 1px solid rgba(168, 85, 247, 0.25);
            border-radius: 8px;
            margin-bottom: 4px;
        }
        .rak-result-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            font-weight: 700;
            color: #E8B189;
        }
        .rak-result-name {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            color: #7a9b8e;
        }

        /* Rak selected */
        .rak-selected {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            background: rgba(20, 12, 35, 0.95);
            border: 1px solid rgba(127, 185, 155, 0.3);
            border-left: 3px solid #7FB99B;
            border-radius: 8px;
            margin-bottom: 6px;
        }
        .rak-selected-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            font-weight: 900;
            color: #E8B189;
            min-width: 70px;
        }
        .rak-selected-name {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            color: #7a9b8e;
            flex: 1;
        }

        /* Custom table */
        .so-table {
            width: 100%;
            border-collapse: collapse;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 12px;
            margin-top: 8px;
            background: rgba(20, 12, 35, 0.95);
            border-radius: 10px;
            padding: 4px;
            border: 1px solid rgba(168, 85, 247, 0.15);
        }
        .so-table thead th {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            font-weight: 600;
            color: #A89B8E;
            letter-spacing: 1px;
            text-transform: uppercase;
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid rgba(168, 85, 247, 0.3);
        }
        .so-table tbody td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(168, 85, 247, 0.1);
            color: #F5E6D3;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }
        .so-table tbody tr:last-child td {
            border-bottom: none;
        }
        .so-table tbody tr {
            background: rgba(20, 12, 35, 0.95) !important;
        }
        .so-table tbody tr:nth-child(even) {
            background: rgba(30, 20, 50, 0.95) !important;
        }
        .so-table td.rak-id {
            color: #E8B189;
            font-weight: 700;
        }
        .so-table td.nominal {
            text-align: right;
            font-weight: 700;
        }
        .so-table td.nominal.neg {
            color: #E88B8B;
        }
        .so-table td.nominal.pos {
            color: #7FB99B;
        }

        /* Keterangan panel */
        .keterangan-panel {
            background: rgba(20, 12, 35, 0.95);
            border: 1px solid rgba(232, 177, 137, 0.3);
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 12px;
        }
        .keterangan-panel .panel-label {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            font-weight: 700;
            color: #7FB99B;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .keterangan-panel .panel-value {
            font-family: 'Cinzel', serif;
            font-size: 28px;
            font-weight: 900;
            color: #E8B189;
            line-height: 1.1;
        }
        .keterangan-panel .panel-sub {
            font-family: 'Quicksand', sans-serif;
            font-size: 11px;
            color: #A89B8E;
            margin-top: 6px;
        }
        .keterangan-panel.danger {
            border-left: 4px solid #E88B8B;
        }
        .keterangan-panel.danger .panel-value {
            color: #E88B8B;
        }
        .keterangan-panel.safe {
            border-left: 4px solid #7FB99B;
        }
        .keterangan-panel.safe .panel-value {
            color: #7FB99B;
        }

        .section-divider {
            margin: 24px 0 16px 0;
            border: none;
            border-top: 1px solid rgba(168, 85, 247, 0.15);
        }

        /* Success screen */
        .success-icon {
            font-size: 72px;
            margin-bottom: 16px;
            filter: drop-shadow(0 0 25px rgba(127, 185, 155, 0.8));
        }
        .success-title {
            font-family: 'Cinzel', serif;
            font-size: 28px;
            font-weight: 900;
            color: #7FB99B;
            letter-spacing: 3px;
            text-shadow: 0 0 20px rgba(127, 185, 155, 0.6);
        }
        .success-sub {
            font-family: 'Quicksand', sans-serif;
            font-size: 13px;
            color: #A89B8E;
            margin-top: 12px;
            letter-spacing: 1px;
        }

        /* Mobile */
        @media (max-width: 768px) {
            .so-table td, .so-table th {
                padding: 8px 8px !important;
                font-size: 11px !important;
            }
            .metric-clean .value {
                font-size: 20px !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)


inject_css()


# =========================================================================
# HEADER
# =========================================================================
def render_header():
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _time_str = _now.strftime("%H:%M")

    _col_back, _col_profile = st.columns([1, 6])

    with _col_back:
        if st.button("← Dashboard", key="btn_back_so", width="stretch"):
            try:
                st.switch_page("Dashboard.py")
            except Exception:
                st.warning("⚠️ Gagal pindah halaman.")

    with _col_profile:
        st.markdown(
            f"<div class='profile-header'>"
            f"<div>"
            f"<div class='profile-title'>📝 STOCK OPNAME</div>"
            f"<div class='profile-sub'>Toko C383 — Karang Satria</div>"
            f"</div>"
            f"<div class='profile-status'>🕐 {_time_str} WIB<br>● ONLINE</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


render_header()


# =========================================================================
# SESSION STATE
# =========================================================================
if "so_screen" not in st.session_state:
    st.session_state["so_screen"] = "form"

if "so_pending_data" not in st.session_state:
    st.session_state["so_pending_data"] = None

if "so_saved_data" not in st.session_state:
    st.session_state["so_saved_data"] = None

if "so_rak_list" not in st.session_state:
    st.session_state["so_rak_list"] = []

if "so_last_loaded_date" not in st.session_state:
    st.session_state["so_last_loaded_date"] = None

if "so_analisis_loaded" not in st.session_state:
    st.session_state["so_analisis_loaded"] = False

if "so_analisis_start_val" not in st.session_state:
    st.session_state["so_analisis_start_val"] = date.today().replace(day=1)

if "so_analisis_end_val" not in st.session_state:
    st.session_state["so_analisis_end_val"] = date.today()

if "so_analisis_rak_val" not in st.session_state:
    st.session_state["so_analisis_rak_val"] = ""

if "so_analisis_pic_val" not in st.session_state:
    st.session_state["so_analisis_pic_val"] = ""

if "so_tab" not in st.session_state:
    st.session_state["so_tab"] = "input"

if "so_search_results" not in st.session_state:
    st.session_state["so_search_results"] = []

if "so_search_shown" not in st.session_state:
    st.session_state["so_search_shown"] = False


# =========================================================================
# LOAD MASTER DATA
# =========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def _load_master():
    _rak_df = load_rak_master()
    _personil_df = load_personil_master(only_active=True)
    return _rak_df, _personil_df


_rak_df, _personil_df = _load_master()
_personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []


# =========================================================================
# HELPER
# =========================================================================
def fmt_rp(value):
    try:
        _v = float(value)
        _sign = "-" if _v < 0 else ""
        return f"{_sign}Rp {int(abs(_v)):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp_signed(value):
    try:
        _v = float(value)
        _sign = "+" if _v >= 0 else "-"
        return f"{_sign}Rp {int(abs(_v)):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"


# =========================================================================
# TAB NAVIGATION
# =========================================================================
_TABS = [
    ("input", "📝 Input SO"),
    ("analisis", "📊 Analisis"),
    ("preview", "📋 Preview"),
]

_cols = st.columns(len(_TABS))
for _i, (_key, _label) in enumerate(_TABS):
    with _cols[_i]:
        _is_active = st.session_state["so_tab"] == _key
        if st.button(
            _label,
            key=f"so_tab_btn_{_key}",
            width="stretch",
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["so_tab"] = _key
            st.rerun()

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
# =========================================================================
# TAB 1: INPUT SO (3 Screen Flow)
# =========================================================================
def render_input_so():
    """Input SO dengan alur 3 layar: Form → Konfirmasi → Sukses."""
    _screen = st.session_state.get("so_screen", "form")

    if _screen == "form":
        _render_input_form()
    elif _screen == "konfirmasi":
        _render_konfirmasi()
    elif _screen == "sukses":
        _render_sukses()


# =========================================================================
# SCREEN 1: FORM INPUT
# =========================================================================
def _render_input_form():
    """Layar 1: Form input SO."""
    st.markdown("### 📝 Input SO")
    st.caption("Input SPD (opsional) + rak yang di-SO dalam 1 form")

    # ============================================================
    # INFO SO — 2 kolom (Tanggal + Keterangan)
    # ============================================================
    _col_tgl, _col_ket = st.columns([1.5, 3])

    with _col_tgl:
        _tanggal = st.date_input(
            "📅 Tanggal SO",
            value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
            key="so_input_tanggal",
        )

    with _col_ket:
        _keterangan = st.text_input(
            "📝 Keterangan (opsional)",
            placeholder="Contoh: Pendingan rak FE1",
            key="so_input_keterangan",
        )

    # ✅ AUTO-LOAD existing SO saat tanggal berubah
    if st.session_state["so_last_loaded_date"] != _tanggal:
        with st.spinner("⏳ Load..."):
            _existing = load_so_summary_by_date(_tanggal)
        st.session_state["so_rak_list"] = [
            {
                "rak_id": r.get("rak_id"),
                "nominal_adjust": float(r.get("nominal_adjust", 0)),
                "pic": r.get("pic", "") or "",
            }
            for r in (_existing or [])
        ]
        st.session_state["so_last_loaded_date"] = _tanggal
        st.rerun()

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # SPD — compact row
    # ============================================================
    _col_spd1, _col_spd2 = st.columns([1, 3])

    with _col_spd1:
        _spd_val = st.number_input(
            "💰 SPD Hari Ini",
            min_value=0,
            max_value=999_999_999_999,
            step=100_000,
            value=0,
            key="so_input_spd",
            help="Isi 0 kalau belum ada SPD hari ini",
        )

    with _col_spd2:
        if _spd_val > 0:
            _btsb = hitung_btsb_harian(_spd_val)
            st.markdown(
                f"<div class='metric-clean' style='border-left-color: #7FB99B; "
                f"padding: 10px 14px; margin-top: 4px;'>"
                f"<div class='label'>💡 BTSB OTOMATIS (0,15%)</div>"
                f"<div class='value' style='font-size: 18px; color: #7FB99B;'>{fmt_rp(_btsb)}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='padding: 12px 0; font-family: JetBrains Mono, monospace; "
                "font-size: 11px; color: #A89B8E;'>"
                "💡 BTSB: — (SPD = 0)"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # MULTI-RAK — Search pakai st.form
    # ============================================================
    st.markdown("#### 📦 Stock Opname (Multi-Rak)")
    st.caption("Cari rak → klik **+ Add** → isi nominal & PIC per rak")

    with st.form("form_search_rak", clear_on_submit=False, enter_to_submit=False):
        _col_search, _col_btn = st.columns([4, 1])

        with _col_search:
            _search_query = st.text_input(
                "🔍 Cari Rak",
                placeholder="Ketik kode rak (contoh: QA1, AT, CHILLER)...",
                key="so_search_input",
                label_visibility="collapsed",
            )

        with _col_btn:
            _search_submit = st.form_submit_button("🔍 Cari", width="stretch", type="primary")

    # === HASIL SEARCH ===
    if _search_submit and _search_query and len(_search_query.strip()) >= 2:
        st.session_state["so_search_results"] = search_rak(_search_query, limit=10)
        st.session_state["so_search_shown"] = True
    elif _search_query and len(_search_query.strip()) < 2:
        st.session_state["so_search_results"] = []
        st.session_state["so_search_shown"] = False
        st.info("💡 Ketik minimal **2 karakter**.")

    _search_results = st.session_state.get("so_search_results", [])

    if st.session_state.get("so_search_shown") and _search_results:
        st.caption(f"💡 {len(_search_results)} rak ditemukan — klik **+ Add** untuk menambahkan")

        for _idx, _rak in enumerate(_search_results):
            _rid = _rak.get("rak_id", "-")
            _rname = _rak.get("rak_name", "-")
            _status = _rak.get("status_so", "BELUM")

            _already_selected = any(
                r["rak_id"] == _rid for r in st.session_state["so_rak_list"]
            )

            col_r1, col_r2 = st.columns([4, 1])
            with col_r1:
                _status_icon = "✅" if _status == "SELESAI" else "⬜"
                st.markdown(
                    f"<div class='rak-result'>"
                    f"<div>"
                    f"<div class='rak-result-id'>{_status_icon} {_rid}</div>"
                    f"<div class='rak-result-name'>{_rname}</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_r2:
                if _already_selected:
                    st.button(
                        "✓",
                        key=f"btn_add_{_idx}_{_rid}",
                        disabled=True,
                        width="stretch",
                    )
                else:
                    if st.button(
                        "+ Add",
                        key=f"btn_add_{_idx}_{_rid}",
                        width="stretch",
                        type="primary",
                    ):
                        _default_pic = _personil_list[0] if _personil_list else ""
                        st.session_state["so_rak_list"].append({
                            "rak_id": _rid,
                            "nominal_adjust": 0.0,
                            "pic": _default_pic,
                        })
                        st.rerun()
                        
    elif st.session_state.get("so_search_shown") and not _search_results:
        st.warning("⚠️ Rak tidak ditemukan.")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    # ============================================================
    # LIST RAK TERPILIH — FIX: key unik pakai index statis
    # ============================================================
    if st.session_state["so_rak_list"]:
        st.markdown(f"#### 📋 Rak Terpilih ({len(st.session_state['so_rak_list'])})")
        st.caption("Isi nominal & PIC per rak")
    
        _items_to_remove = []
    
        for _idx, _item in enumerate(st.session_state["so_rak_list"]):
            _rid = _item["rak_id"]
            _rak_info = get_rak_by_kode_exact(_rid)
            _rname = _rak_info.get("rak_name", "-") if _rak_info else "-"
    
            # ✅ FIX: key pake rak_id + index biar selalu unik
            _key_suffix = f"{_rid}_{_idx}"
    
            _c1, _c2, _c3, _c4 = st.columns([2, 1.5, 1.5, 0.5])
    
            with _c1:
                st.markdown(
                    f"<div class='rak-selected' style='margin-top: 4px;'>"
                    f"<div class='rak-selected-id'>{_rid}</div>"
                    f"<div class='rak-selected-name'>{_rname}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    
            with _c2:
                _new_nominal = st.number_input(
                    f"Nominal {_rid}",
                    min_value=-999_999_999,
                    max_value=999_999_999,
                    step=1000,
                    value=int(_item.get("nominal_adjust", 0)),
                    key=f"so_nominal_{_key_suffix}",       # ✅ key unik
                    label_visibility="collapsed",
                )
                st.session_state["so_rak_list"][_idx]["nominal_adjust"] = float(_new_nominal)
    
            with _c3:
                _current_pic = _item.get("pic", "")
                if _personil_list:
                    _pic_index = _personil_list.index(_current_pic) if _current_pic in _personil_list else 0
                    _new_pic = st.selectbox(
                        f"PIC {_rid}",
                        options=_personil_list,
                        index=_pic_index,
                        key=f"so_pic_{_key_suffix}",          # ✅ key unik
                        label_visibility="collapsed",
                    )
                else:
                    _new_pic = st.text_input(
                        f"PIC {_rid}",
                        value=_current_pic,
                        key=f"so_pic_{_key_suffix}",          # ✅ key unik
                        label_visibility="collapsed",
                    )
                st.session_state["so_rak_list"][_idx]["pic"] = _new_pic
    
            with _c4:
                if st.button("🗑️", key=f"so_del_{_key_suffix}", width="stretch"):   # ✅ key unik
                    _items_to_remove.append(_idx)
    
        if _items_to_remove:
            for _i in sorted(_items_to_remove, reverse=True):
                st.session_state["so_rak_list"].pop(_i)
            st.rerun()
    
        # Total nominal
        _total_nominal_input = sum(
            item.get("nominal_adjust", 0)
            for item in st.session_state["so_rak_list"]
        )
        _color_total = "#E88B8B" if _total_nominal_input < 0 else "#7FB99B"
    
        st.markdown(
            f"<div class='metric-clean' style='border-left-color: {_color_total}; "
            f"margin-top: 16px; text-align: right;'>"
            f"<div class='label'>💰 TOTAL NOMINAL SO ({len(st.session_state['so_rak_list'])} RAK)</div>"
            f"<div class='value' style='color: {_color_total};'>"
            f"{fmt_rp_signed(_total_nominal_input)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("📭 Belum ada rak. Cari & klik **+ Add** untuk menambahkan.")
        
        # ============================================================
        # TOMBOL LANJUT KE KONFIRMASI
        # ============================================================
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        
        _col_save, _col_cancel = st.columns([3, 1])
        
        with _col_save:
            if st.button(
                "➡️ LANJUT KONFIRMASI",
                width="stretch",
                type="primary",
                key="btn_ke_konfirmasi",
            ):
                _has_rak = len(st.session_state["so_rak_list"]) > 0
                _has_spd = _spd_val > 0
        
                # Validasi: setiap rak harus punya PIC
                _rak_tanpa_pic = [
                    r["rak_id"] for r in st.session_state["so_rak_list"]
                    if not r.get("pic")
                ]
        
                if not _has_rak and not _has_spd:
                    st.error("⚠️ Minimal isi SPD atau tambahkan 1 rak!")
                elif _rak_tanpa_pic:
                    st.error(f"⚠️ Rak berikut belum punya PIC: **{', '.join(_rak_tanpa_pic)}**")
                else:
                    # Simpan data ke pending & pindah ke layar konfirmasi
                    st.session_state["so_pending_data"] = {
                        "tanggal": _tanggal,
                        "spd": _spd_val,
                        "rak_items": list(st.session_state["so_rak_list"]),
                        "keterangan": _keterangan,
                    }
                    st.session_state["so_screen"] = "konfirmasi"
                    st.rerun()
        
        with _col_cancel:
            if st.button(
                "🗑️ Clear",
                width="stretch",
                key="btn_clear_so",
            ):
                st.session_state["so_rak_list"] = []
                st.session_state["so_search_results"] = []
                st.session_state["so_search_shown"] = False
                st.rerun()
                
# =========================================================================
# SCREEN 2: KONFIRMASI
# =========================================================================
def _render_konfirmasi():
    """Layar 2: Review data sebelum simpan."""
    _pending = st.session_state.get("so_pending_data")

    if not _pending:
        st.session_state["so_screen"] = "form"
        st.rerun()
        return

    st.markdown("### ✅ Konfirmasi SO")
    st.caption("Review data sebelum disimpan. Pastikan semua sudah benar.")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # INFO CARD — 3 kolom
    # ============================================================
    _col_i1, _col_i2, _col_i3 = st.columns(3)

    with _col_i1:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>📅 TANGGAL SO</div>"
            f"<div class='value' style='font-size: 18px;'>"
            f"{_pending['tanggal'].strftime('%d/%m/%Y')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with _col_i2:
        _jumlah_rak = len(_pending.get("rak_items", []))
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>🏪 RAK DI-SO</div>"
            f"<div class='value' style='font-size: 18px;'>{_jumlah_rak}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with _col_i3:
        _spd_show = _pending.get("spd", 0)
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>💰 SPD</div>"
            f"<div class='value' style='font-size: 18px; color: #7FB99B;'>"
            f"{fmt_rp(_spd_show) if _spd_show > 0 else '—'}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Keterangan (kalau ada)
    if _pending.get("keterangan"):
        st.markdown(
            f"<div style='margin-top: 12px; padding: 12px 16px; "
            f"background: rgba(20, 12, 35, 0.95); "
            f"border-left: 3px solid #E8B189; border-radius: 8px;'>"
            f"<div style='font-family: Quicksand, sans-serif; font-size: 10px; "
            f"color: #A89B8E; letter-spacing: 1px; text-transform: uppercase;'>"
            f"📝 Keterangan</div>"
            f"<div style='font-family: Quicksand, sans-serif; font-size: 13px; "
            f"color: #F5E6D3; margin-top: 4px;'>{_pending['keterangan']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # TABEL RAK YANG AKAN DISIMPAN — with PIC per rak
    # ============================================================
    st.markdown(f"#### 📋 Rak yang Akan Disimpan ({len(_pending['rak_items'])} rak)")

    if _pending["rak_items"]:
        _rows_html = ""
        _total_nom = 0

        for _item in _pending["rak_items"]:
            _rid = _item.get("rak_id", "-")
            _nom = float(_item.get("nominal_adjust", 0))
            _pic = _item.get("pic", "-") or "-"
            _total_nom += _nom

            _rak_info = get_rak_by_kode_exact(_rid)
            _rname = _rak_info.get("rak_name", "-") if _rak_info else "-"
            _nom_class = "neg" if _nom < 0 else "pos"

            _rows_html += (
                f"<tr>"
                f"<td class='rak-id'>{_rid}</td>"
                f"<td style='font-family: Quicksand, sans-serif;'>{_rname}</td>"
                f"<td style='font-family: Quicksand, sans-serif; color: #E8B189;'>{_pic}</td>"
                f"<td class='nominal {_nom_class}'>{fmt_rp_signed(_nom)}</td>"
                f"</tr>"
            )

        _table_html = (
            "<table class='so-table'>"
            "<thead><tr>"
            "<th>Kode Rak</th>"
            "<th>Nama Rak</th>"
            "<th>PIC</th>"
            "<th style='text-align: right;'>Nominal</th>"
            "</tr></thead>"
            f"<tbody>{_rows_html}</tbody>"
            "</table>"
        )

        st.markdown(_table_html, unsafe_allow_html=True)

        _color_total = "#E88B8B" if _total_nom < 0 else "#7FB99B"
        st.markdown(
            f"<div class='metric-clean' style='border-left-color: {_color_total}; "
            f"margin-top: 16px; text-align: right;'>"
            f"<div class='label'>💰 TOTAL NOMINAL SO</div>"
            f"<div class='value' style='color: {_color_total};'>"
            f"{fmt_rp_signed(_total_nom)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("💡 Tidak ada rak (cuma SPD yang akan disimpan)")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # TOMBOL KONFIRMASI
    # ============================================================
    _col_ok, _col_batal = st.columns([2, 1])

    with _col_ok:
        if st.button(
            "✅ SIMPAN SEKARANG",
            width="stretch",
            type="primary",
            key="btn_konfirmasi_simpan",
        ):
            with st.spinner("⏳ Menyimpan..."):
                _ok_all = True
                _msg_list = []

                # Simpan SPD dulu (kalau ada)
                if _pending.get("spd", 0) > 0:
                    try:
                        save_spd_harian(
                            _pending["tanggal"],
                            _pending["spd"],
                            _pending.get("keterangan", ""),
                        )
                    except Exception as _e_spd:
                        print(f"[SAVE SPD ERROR] {_e_spd}")

                # Simpan per rak (karena PIC beda-beda)
                for _item in _pending["rak_items"]:
                    try:
                        _ok, _msg, _detail = save_input_harian(
                            tanggal=_pending["tanggal"],
                            spd=0,  # SPD udah disimpan
                            rak_items=[_item],  # 1 rak aja
                            keterangan=_pending.get("keterangan", ""),
                            pic=_item.get("pic", ""),
                            update_status_rak=True,
                        )
                        if _ok:
                            _msg_list.append(f"✅ {_item.get('rak_id')}")
                        else:
                            _ok_all = False
                            _msg_list.append(f"❌ {_item.get('rak_id')}: {_msg}")
                    except Exception as _e_rak:
                        _ok_all = False
                        _msg_list.append(f"❌ {_item.get('rak_id')}: {str(_e_rak)[:50]}")

            if _ok_all:
                st.session_state["so_saved_data"] = {
                    "tanggal": _pending["tanggal"],
                    "spd": _pending["spd"],
                    "rak_items": list(_pending["rak_items"]),
                    "keterangan": _pending["keterangan"],
                    "message": f"✅ {len(_pending['rak_items'])} rak tersimpan",
                }
                st.session_state["so_pending_data"] = None
                st.session_state["so_rak_list"] = []
                st.session_state["so_search_results"] = []
                st.session_state["so_search_shown"] = False
                st.session_state["so_last_loaded_date"] = None
                st.session_state["so_screen"] = "sukses"
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("\n".join(_msg_list))

    with _col_batal:
        if st.button(
            "❌ BATAL",
            width="stretch",
            key="btn_konfirmasi_batal",
        ):
            st.session_state["so_screen"] = "form"
            st.rerun()


# =========================================================================
# SCREEN 3: SUKSES
# =========================================================================
def _render_sukses():
    """Layar 3: Notifikasi sukses + summary."""
    _saved = st.session_state.get("so_saved_data")

    if not _saved:
        st.session_state["so_screen"] = "form"
        st.rerun()
        return

    # Notifikasi sukses besar
    st.markdown(
        "<div style='text-align: center; padding: 40px 20px 20px 20px;'>"
        "<div class='success-icon'>✅</div>"
        "<div class='success-title'>BERHASIL DISIMPAN</div>"
        "<div class='success-sub'>Data SO sudah tersimpan ke database</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # SUMMARY CARD
    # ============================================================
    _total_rak = len(_saved.get("rak_items", []))
    _total_nom = sum(float(i.get("nominal_adjust", 0)) for i in _saved.get("rak_items", []))
    _spd_val = _saved.get("spd", 0)

    _col_s1, _col_s2, _col_s3 = st.columns(3)

    with _col_s1:
        st.markdown(
            f"<div class='metric-clean' style='border-left-color: #7FB99B;'>"
            f"<div class='label'>🏪 RAK DI-SO</div>"
            f"<div class='value'>{_total_rak}</div>"
            f"<div class='sub'>rak</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with _col_s2:
        _color_nom = "#E88B8B" if _total_nom < 0 else "#7FB99B"
        st.markdown(
            f"<div class='metric-clean' style='border-left-color: {_color_nom};'>"
            f"<div class='label'>💰 TOTAL NOMINAL</div>"
            f"<div class='value' style='color: {_color_nom}; font-size: 20px;'>"
            f"{fmt_rp_signed(_total_nom)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with _col_s3:
        if _spd_val > 0:
            st.markdown(
                f"<div class='metric-clean' style='border-left-color: #7FB99B;'>"
                f"<div class='label'>💰 SPD</div>"
                f"<div class='value' style='color: #7FB99B; font-size: 20px;'>"
                f"{fmt_rp(_spd_val)}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='metric-clean'>"
                f"<div class='label'>💰 SPD</div>"
                f"<div class='value' style='font-size: 18px; color: #A89B8E;'>—</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # DETAIL RAK YANG DISIMPAN — with PIC
    # ============================================================
    if _saved.get("rak_items"):
        st.markdown("#### 📋 Rak yang Tersimpan")

        _rows_html = ""
        for _item in _saved["rak_items"]:
            _rid = _item.get("rak_id", "-")
            _nom = float(_item.get("nominal_adjust", 0))
            _pic = _item.get("pic", "-") or "-"
            _nom_class = "neg" if _nom < 0 else "pos"

            _rows_html += (
                f"<tr>"
                f"<td class='rak-id'>{_rid}</td>"
                f"<td style='font-family: Quicksand, sans-serif; color: #E8B189;'>{_pic}</td>"
                f"<td class='nominal {_nom_class}'>{fmt_rp_signed(_nom)}</td>"
                f"</tr>"
            )

        _table_html = (
            "<table class='so-table'>"
            "<thead><tr>"
            "<th>Kode Rak</th>"
            "<th>PIC</th>"
            "<th style='text-align: right;'>Nominal</th>"
            "</tr></thead>"
            f"<tbody>{_rows_html}</tbody>"
            "</table>"
        )

        st.markdown(_table_html, unsafe_allow_html=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # TOMBOL AKSI
    # ============================================================
    _col_again, _col_home = st.columns(2)

    with _col_again:
        if st.button(
            "📝 Input SO Lagi",
            width="stretch",
            type="primary",
            key="btn_input_again",
        ):
            st.session_state["so_saved_data"] = None
            st.session_state["so_screen"] = "form"
            st.rerun()

    with _col_home:
        if st.button(
            "🏠 Ke Dashboard",
            width="stretch",
            key="btn_back_home_from_sukses",
        ):
            st.session_state["so_saved_data"] = None
            st.session_state["so_screen"] = "form"
            try:
                st.switch_page("Dashboard.py")
            except Exception:
                st.rerun()
# =========================================================================
# TAB 2: ANALISIS SO
# =========================================================================
def render_analisis():
    """Analisis SO: Filter periode → hitung dari data yang di-filter."""
    st.markdown("### 📊 Analisis SO")
    st.caption("Filter periode → data otomatis update")

    # ============================================================
    # FILTER PERIODE + RAK + PIC
    # ============================================================
    _col_p1, _col_p2 = st.columns(2)

    with _col_p1:
        _tgl_start = st.date_input(
            "📅 Dari Tanggal",
            value=st.session_state["so_analisis_start_val"],
            key="widget_start_analisis",
        )

    with _col_p2:
        _tgl_end = st.date_input(
            "📅 Sampai Tanggal",
            value=st.session_state["so_analisis_end_val"],
            key="widget_end_analisis",
        )

    _col_f1, _col_f2 = st.columns([2, 2])

    with _col_f1:
        _filter_rak = st.text_input(
            "🔍 Filter Kode Rak (opsional)",
            value=st.session_state["so_analisis_rak_val"],
            placeholder="Contoh: Q51...",
            key="widget_rak_analisis",
        )

    with _col_f2:
        # Ambil daftar PIC dari data
        try:
            _so_all = get_so_rak_detail(limit=1000)
            _pic_list = sorted(set(
                str(r.get("pic", "")).strip().upper()
                for r in (_so_all or [])
                if r.get("pic")
            ))
        except Exception:
            _pic_list = []

        _pic_options = ["(Semua)"] + _pic_list

        _current_pic = st.session_state["so_analisis_pic_val"]
        _pic_index = _pic_options.index(_current_pic) if _current_pic in _pic_options else 0

        _filter_pic = st.selectbox(
            "👤 Filter PIC (opsional)",
            options=_pic_options,
            index=_pic_index,
            key="widget_pic_analisis",
        )

    _col_btn, _, _ = st.columns([1, 1, 2])

    with _col_btn:
        if st.button("🔍 Analisis", width="stretch", type="primary", key="btn_analisis_so"):
            st.session_state["so_analisis_start_val"] = _tgl_start
            st.session_state["so_analisis_end_val"] = _tgl_end
            st.session_state["so_analisis_rak_val"] = _filter_rak.strip().upper() if _filter_rak else ""
            st.session_state["so_analisis_pic_val"] = "" if _filter_pic == "(Semua)" else _filter_pic
            st.session_state["so_analisis_loaded"] = True
            st.rerun()

    if not st.session_state.get("so_analisis_loaded"):
        st.info("💡 Pilih periode & klik **🔍 Analisis** untuk mulai")
        return

    # ============================================================
    # AMBIL FILTER DARI SESSION STATE
    # ============================================================
    _start = st.session_state["so_analisis_start_val"]
    _end = st.session_state["so_analisis_end_val"]
    _f_rak = st.session_state["so_analisis_rak_val"]
    _f_pic = st.session_state["so_analisis_pic_val"]

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # Info filter aktif
    _filter_info = f"📅 {_start.strftime('%d/%m/%Y')} — {_end.strftime('%d/%m/%Y')}"
    if _f_rak:
        _filter_info += f" | 🔍 Rak: **{_f_rak}**"
    if _f_pic:
        _filter_info += f" | 👤 PIC: **{_f_pic}**"

    st.markdown(
        f"<div style='background: rgba(20, 12, 35, 0.95); "
        f"border-left: 3px solid #E8B189; border-radius: 8px; "
        f"padding: 10px 16px; margin-bottom: 16px; "
        f"font-family: JetBrains Mono, monospace; font-size: 11px; "
        f"color: #A89B8E;'>{_filter_info}</div>",
        unsafe_allow_html=True,
    )

    # ============================================================
    # LOAD DATA SESUAI FILTER
    # ============================================================
    with st.spinner("⏳ Load analytics..."):
        _so_detail_raw = []
        _total_spd = 0

        try:
            from modules.supabase_client import get_supabase
            _sb = get_supabase()

            if _sb:
                _query = _sb.table("so_rak_harian") \
                    .select("so_date, rak_id, nominal_adjust, pic, keterangan") \
                    .gte("so_date", _start.isoformat()) \
                    .lte("so_date", _end.isoformat())

                if _f_rak:
                    _query = _query.ilike("rak_id", f"%{_f_rak}%")
                if _f_pic:
                    _query = _query.eq("pic", _f_pic)

                _res = _query.order("so_date", desc=True).execute()
                _so_detail_raw = _res.data or []

                # SPD periode ini
                _spd_periode = _sb.table("spd_harian") \
                    .select("tanggal, spd") \
                    .gte("tanggal", _start.isoformat()) \
                    .lte("tanggal", _end.isoformat()) \
                    .execute()
                _total_spd = sum(float(r.get("spd", 0)) for r in (_spd_periode.data or []))
        except Exception as _e_load:
            print(f"[ANALISIS LOAD ERROR] {_e_load}")

    # ============================================================
    # HITUNG METRIC
    # ============================================================
    _total_rak = len(_so_detail_raw)
    _unique_hari = len(set(r.get("so_date") for r in _so_detail_raw if r.get("so_date")))
    _total_nominal = sum(float(r.get("nominal_adjust", 0)) for r in _so_detail_raw)
    _btsb_periode = _total_spd * 0.0015 if _total_spd > 0 else 0

    if _total_spd > 0:
        _pct_nsb = (abs(_total_nominal) / _total_spd * 100)
    else:
        _pct_nsb = 0.0

    _pct_btsb = (abs(_total_nominal) / _btsb_periode * 100) if _btsb_periode > 0 else 0

    if _pct_btsb <= 80:
        _status = "AMAN"
        _status_color = "#7FB99B"
        _status_class = "safe"
    elif _pct_btsb <= 100:
        _status = "WASPADA"
        _status_color = "#fbbf24"
        _status_class = ""
    else:
        _status = "BAHAYA"
        _status_color = "#E88B8B"
        _status_class = "danger"

    # ============================================================
    # TABEL ANALISIS + KETERANGAN
    # ============================================================
    _col_table, _col_ket = st.columns([3, 2])

    with _col_table:
        st.markdown("#### 📋 Ringkasan SO")
        _table_html = (
            "<table class='so-table'>"
            "<thead><tr><th>Metric</th><th style='text-align: right;'>Nilai</th></tr></thead><tbody>"
            f"<tr><td class='rak-id'>🏪 Total Rak di-SO</td>"
            f"<td class='nominal pos'>{_total_rak} rak</td></tr>"
            f"<tr><td class='rak-id'>📅 Jumlah Hari</td>"
            f"<td class='nominal pos'>{_unique_hari} hari</td></tr>"
            f"<tr><td class='rak-id'>💰 Total Nominal SO</td>"
            f"<td class='nominal {'neg' if _total_nominal < 0 else 'pos'}'>"
            f"{fmt_rp_signed(_total_nominal)}</td></tr>"
            f"<tr><td class='rak-id'>📈 Total SPD</td>"
            f"<td class='nominal pos'>{fmt_rp(_total_spd)}</td></tr>"
            f"<tr><td class='rak-id'>🎯 BTSB Periode</td>"
            f"<td class='nominal pos'>{fmt_rp(_btsb_periode)}</td></tr>"
            f"<tr><td class='rak-id'>📊 %NSB dari Sales</td>"
            f"<td class='nominal {'neg' if _pct_nsb > 0.15 else 'pos'}'>"
            f"{_pct_nsb:.3f}%</td></tr>"
            "</tbody></table>"
        )
        st.markdown(_table_html, unsafe_allow_html=True)

    with _col_ket:
        st.markdown("#### 💡 Keterangan")
        _gap = _btsb_periode - abs(_total_nominal)
        _gap_color = "#7FB99B" if _gap >= 0 else "#E88B8B"

        _col_k1, _col_k2 = st.columns(2)
        with _col_k1:
            st.markdown(
                f"<div class='keterangan-panel {_status_class}' style='margin-bottom: 0;'>"
                f"<div class='panel-label'>🎯 STATUS</div>"
                f"<div class='panel-value' style='color: {_status_color}; font-size: 22px;'>"
                f"{_status}</div>"
                f"<div class='panel-sub' style='font-size: 9px;'>"
                f"Penggunaan: {_pct_btsb:.2f}%</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with _col_k2:
            st.markdown(
                f"<div class='keterangan-panel' style='border-left-color: {_gap_color}; margin-bottom: 0;'>"
                f"<div class='panel-label'>💰 SISA BUDGET</div>"
                f"<div class='panel-value' style='color: {_gap_color}; font-size: 20px;'>"
                f"{fmt_rp(_gap)}</div>"
                f"<div class='panel-sub' style='font-size: 9px;'>"
                f"{'✅ Aman' if _gap >= 0 else '⚠️ Over budget'}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ============================================================
    # DETAIL PER RAK
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    with st.expander(f"📋 Daftar Rak yang di-SO ({len(_so_detail_raw)} baris)", expanded=False):
        if _so_detail_raw:
            _search_detail = st.text_input(
                "🔍 Cari Rak",
                key="search_detail_analisis",
                placeholder="Ketik kode rak...",
                label_visibility="collapsed",
            )

            _df_detail = pd.DataFrame(_so_detail_raw)
            _cols_show = ["so_date", "rak_id", "nominal_adjust", "pic"]
            _cols_show = [c for c in _cols_show if c in _df_detail.columns]

            if _cols_show:
                _df_show = _df_detail[_cols_show].copy()

                if _search_detail and len(_search_detail.strip()) >= 1:
                    _q = _search_detail.strip().upper()
                    _df_show = _df_show[
                        _df_show["rak_id"].astype(str).str.upper().str.contains(_q, na=False)
                    ]

                if "nominal_adjust" in _df_show.columns:
                    _df_show["nominal_adjust"] = _df_show["nominal_adjust"].apply(
                        lambda v: fmt_rp_signed(v)
                    )

                _col_names = ["Tanggal", "Kode Rak", "Nominal", "PIC"]
                _df_show.columns = _col_names[:len(_df_show.columns)]

                st.dataframe(_df_show, width="stretch", hide_index=True, height=400)
                st.caption(f"📊 Total **{len(_df_show)}** baris SO")
        else:
            st.info("📭 Belum ada data SO di periode ini")

    # ============================================================
    # GRAFIK TOP 10 MINUS
    # ============================================================
    with st.expander("📈 Grafik Top 10 Rak Minus (Klik untuk buka)", expanded=False):
        if _so_detail_raw:
            try:
                _df = pd.DataFrame(_so_detail_raw)
                if "nominal_adjust" in _df.columns and "rak_id" in _df.columns:
                    _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
                    _grp = _df.groupby("rak_id")["nominal_adjust"].sum().reset_index()
                    _grp_minus = _grp[_grp["nominal_adjust"] < 0].sort_values("nominal_adjust").head(10)

                    if _grp_minus.empty:
                        st.success("✅ Tidak ada rak minus di periode ini")
                    else:
                        import plotly.graph_objects as go

                        _fig = go.Figure()
                        _fig.add_trace(go.Bar(
                            x=_grp_minus["nominal_adjust"],
                            y=_grp_minus["rak_id"],
                            orientation="h",
                            marker=dict(color="#E88B8B", line=dict(color="rgba(184, 115, 51, 0.5)", width=1)),
                            text=[f"{v:+,.0f}".replace(",", ".") for v in _grp_minus["nominal_adjust"]],
                            textposition="outside",
                            textfont=dict(color="#E8B189", size=10, family="JetBrains Mono"),
                            hovertemplate="<b>%{y}</b><br>Nominal: %{x:+,.0f}<extra></extra>",
                        ))

                        _fig.update_layout(
                            height=max(300, len(_grp_minus) * 35),
                            margin=dict(l=10, r=60, t=20, b=40),
                            plot_bgcolor="rgba(20, 12, 35, 0.5)",
                            paper_bgcolor="rgba(20, 12, 35, 0.95)",
                            font=dict(color="#A89B8E", family="JetBrains Mono", size=10),
                            xaxis=dict(
                                title="Nominal (Rp)",
                                gridcolor="rgba(168, 85, 247, 0.1)",
                                zeroline=True,
                                zerolinecolor="rgba(232, 177, 137, 0.5)",
                                zerolinewidth=1,
                            ),
                            yaxis=dict(gridcolor="rgba(168, 85, 247, 0.1)", autorange="reversed"),
                            showlegend=False,
                        )

                        st.plotly_chart(_fig, width="stretch", key="chart_top10_minus")
            except Exception as _e_chart:
                st.warning(f"⚠️ Chart gagal render: {str(_e_chart)[:150]}")
        else:
            st.info("📭 Belum ada data SO di periode ini")

    # ============================================================
    # RAK BELUM SO — Tabel HTML (Limited + Load More)
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    with st.expander("📋 Rak Belum SO (Klik untuk buka)", expanded=False):
        try:
            from modules.rak_monitor import get_rak_belum_so as _get_belum_so_df
    
            _rak_belum_df = _get_belum_so_df(_rak_df)
    
            if not _rak_belum_df.empty:
                _jumlah_belum = len(_rak_belum_df)
                st.caption(f"⚠️ **{_jumlah_belum} rak** belum di-SO")
    
                _search_belum = st.text_input(
                    "🔍 Cari rak",
                    key="search_rak_belum",
                    placeholder="Ketik kode/nama rak...",
                    label_visibility="collapsed",
                )
    
                _rak_filtered = _rak_belum_df.copy()
                if _search_belum and len(_search_belum.strip()) >= 1:
                    _q = _search_belum.strip().upper()
                    _rak_filtered = _rak_filtered[
                        _rak_filtered["rak_id"].astype(str).str.upper().str.contains(_q, na=False) |
                        _rak_filtered["rak_name"].astype(str).str.upper().str.contains(_q, na=False)
                    ]
    
                # ✅ FIX: Batasi tampilan (default 20)
                _limit_key = "so_limit_belum"
                if _limit_key not in st.session_state:
                    st.session_state[_limit_key] = 20
    
                _total_filtered = len(_rak_filtered)
                _limit = st.session_state[_limit_key]
                _rak_shown = _rak_filtered.head(_limit)
    
                # Tabel HTML
                _rows_html = ""
                for _rak in _rak_shown[["rak_id", "rak_name"]].to_dict("records"):
                    _rid = str(_rak.get("rak_id", "-"))
                    _rname = str(_rak.get("rak_name", "-"))[:40]
                    _rows_html += (
                        f"<tr>"
                        f"<td class='rak-id'>{_rid}</td>"
                        f"<td style='font-family: Quicksand, sans-serif;'>{_rname}</td>"
                        f"</tr>"
                    )
    
                _table_html = (
                    "<table class='so-table'>"
                    "<thead><tr>"
                    "<th>Kode Rak</th>"
                    "<th>Nama Rak</th>"
                    "</tr></thead>"
                    f"<tbody>{_rows_html}</tbody>"
                    "</table>"
                )
                st.markdown(_table_html, unsafe_allow_html=True)
    
                # ✅ FIX: Load More button
                _col_info, _col_btn = st.columns([2, 1])
    
                with _col_info:
                    st.caption(f"📊 Menampilkan **{len(_rak_shown)}** dari **{_total_filtered}** rak")
    
                with _col_btn:
                    if _limit < _total_filtered:
                        if st.button(
                            "📥 Load More (+20)",
                            key="btn_load_more_belum",
                            width="stretch",
                        ):
                            st.session_state[_limit_key] += 20
                            st.rerun()
                    else:
                        if st.button(
                            "🔼 Sembunyikan",
                            key="btn_collapse_belum",
                            width="stretch",
                        ):
                            st.session_state[_limit_key] = 20
                            st.rerun()
    
                # Download
                _list_text = "\n".join([
                    f"{r['rak_id']} — {r['rak_name']}"
                    for r in _rak_filtered[["rak_id", "rak_name"]].to_dict("records")
                ])
    
                st.download_button(
                    label=f"📥 Download Semua List ({_total_filtered} rak)",
                    data=_list_text,
                    file_name=f"Rak_Belum_SO_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    width="stretch",
                    key="dl_rak_belum_so",
                )
            else:
                st.success("🎉 Semua rak sudah di-SO!")
        except Exception as _e_belum:
            st.warning(f"⚠️ Gagal load rak belum SO: {str(_e_belum)[:100]}")


# =========================================================================
# TAB 3: PREVIEW & HAPUS
# =========================================================================
def render_preview():
    """Preview SO hari ini + hapus per rak."""
    st.markdown("### 📋 Preview & Hapus SO")
    st.caption("Lihat semua SO yang sudah diinput & hapus kalau perlu")

    # ============================================================
    # PILIH TANGGAL
    # ============================================================
    _col_tgl, _col_info = st.columns([1, 3])

    with _col_tgl:
        _tanggal = st.date_input(
            "📅 Pilih Tanggal",
            value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
            key="so_preview_tanggal",
        )

    # ============================================================
    # LOAD DATA
    # ============================================================
    _so_summary = []
    _so_detail = []

    with st.spinner("⏳ Load SO..."):
        try:
            _so_summary = load_so_summary_by_date(_tanggal) or []
        except Exception as _e1:
            print(f"[PREVIEW SUMMARY ERROR] {_e1}")
            _so_summary = []

        try:
            _so_detail = load_so_detail_by_date(_tanggal) or []
        except Exception as _e2:
            print(f"[PREVIEW DETAIL ERROR] {_e2}")
            _so_detail = []

    with _col_info:
        st.markdown(
            f"<div style='padding-top: 8px; font-family: JetBrains Mono, monospace; "
            f"font-size: 11px; color: #A89B8E;'>"
            f"📅 Menampilkan data: <b style='color: #E8B189;'>"
            f"{_tanggal.strftime('%d/%m/%Y')}</b></div>",
            unsafe_allow_html=True,
        )

    # ============================================================
    # EMPTY STATE
    # ============================================================
    if not _so_summary:
        st.info(f"📭 Belum ada SO untuk tanggal **{_tanggal.strftime('%d/%m/%Y')}**")
        return

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # SUMMARY METRIC — 3 kolom
    # ============================================================
    _total_rak = len(_so_summary)
    _total_item = sum(int(r.get("total_item", 0)) for r in _so_summary)
    _total_nominal = sum(float(r.get("nominal_adjust", 0)) for r in _so_summary)

    _c1, _c2, _c3 = st.columns(3)

    with _c1:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>🏪 TOTAL RAK DI-SO</div>"
            f"<div class='value'>{_total_rak}</div>"
            f"<div class='sub'>rak</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with _c2:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>📦 TOTAL PRODUK</div>"
            f"<div class='value'>{_total_item}</div>"
            f"<div class='sub'>item</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with _c3:
        _color_nom = "#E88B8B" if _total_nominal < 0 else "#7FB99B"
        st.markdown(
            f"<div class='metric-clean' style='border-left-color: {_color_nom};'>"
            f"<div class='label'>💰 TOTAL NOMINAL</div>"
            f"<div class='value' style='color: {_color_nom}; font-size: 20px;'>"
            f"{fmt_rp_signed(_total_nominal)}</div>"
            f"<div class='sub'>nominal SO</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # TABEL SUMMARY PER RAK — Search + Tabel HTML
    # ============================================================
    st.markdown("#### 📊 Summary per Rak")

    _search_preview = st.text_input(
        "🔍 Cari Rak",
        key="search_preview_rak",
        placeholder="Ketik kode rak...",
        label_visibility="collapsed",
    )

    _so_summary_filtered = _so_summary
    if _search_preview and len(_search_preview.strip()) >= 1:
        _q = _search_preview.strip().upper()
        _so_summary_filtered = [
            r for r in _so_summary
            if _q in str(r.get("rak_id", "")).upper()
        ]

    if not _so_summary_filtered:
        st.info(f"📭 Tidak ada rak yang match dengan **'{_search_preview}'**")
    else:
        _rows_html = ""
        for _r in _so_summary_filtered:
            _rak = _r.get("rak_id", "-")
            _pic = _r.get("pic", "-") or "-"
            _item = int(_r.get("total_item", 0))
            _qty_var = int(_r.get("total_qty_var", 0))
            _nom = float(_r.get("nominal_adjust", 0))

            _nom_class = "neg" if _nom < 0 else "pos"

            _rows_html += (
                f"<tr>"
                f"<td class='rak-id'>{_rak}</td>"
                f"<td style='font-family: Quicksand, sans-serif; color: #E8B189;'>{_pic}</td>"
                f"<td style='text-align: center;'>{_item}</td>"
                f"<td style='text-align: center;'>{_qty_var:+d}</td>"
                f"<td class='nominal {_nom_class}'>{fmt_rp_signed(_nom)}</td>"
                f"</tr>"
            )

        _table_html = (
            "<table class='so-table'>"
            "<thead><tr>"
            "<th>Rak</th>"
            "<th>PIC</th>"
            "<th style='text-align: center;'>Item</th>"
            "<th style='text-align: center;'>Qty Var</th>"
            "<th style='text-align: right;'>Nominal</th>"
            "</tr></thead>"
            f"<tbody>{_rows_html}</tbody>"
            "</table>"
        )

        st.markdown(_table_html, unsafe_allow_html=True)
        st.caption(f"📊 Total **{len(_so_summary_filtered)}** rak")

    # ============================================================
    # DETAIL PRODUK (kalau ada)
    # ============================================================
    if _so_detail:
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        with st.expander(f"🔍 Detail Produk ({len(_so_detail)} baris)", expanded=False):
            _df_detail = pd.DataFrame(_so_detail)
            _cols_detail = ["rak_id", "plu", "nama_produk", "qty_sistem", "qty_fisik", "qty_var", "nominal_adjust", "pic"]
            _cols_detail = [c for c in _cols_detail if c in _df_detail.columns]

            if _cols_detail:
                _df_detail_show = _df_detail[_cols_detail].copy()

                if "nominal_adjust" in _df_detail_show.columns:
                    _df_detail_show["nominal_adjust"] = _df_detail_show["nominal_adjust"].apply(
                        lambda v: fmt_rp_signed(v)
                    )

                _col_names_detail = ["Rak", "PLU", "Nama Produk", "Qty Sistem", "Qty Fisik", "Qty Var", "Nominal", "PIC"]
                _df_detail_show.columns = _col_names_detail[:len(_df_detail_show.columns)]

                st.dataframe(_df_detail_show, width="stretch", hide_index=True, height=400)
            else:
                st.info("📭 Detail produk kosong")

    # ============================================================
    # HAPUS SO PER RAK
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.markdown("#### 🗑️ Hapus SO")

    _rak_so_list = [r.get("rak_id") for r in _so_summary if r.get("rak_id")]

    if _rak_so_list:
        _col_h1, _col_h2 = st.columns([3, 1])

        with _col_h1:
            _rak_hapus = st.selectbox(
                "Pilih rak yang mau dihapus:",
                options=_rak_so_list,
                key="so_preview_rak_hapus",
            )

        with _col_h2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(
                "🗑️ HAPUS",
                width="stretch",
                type="primary",
                key="btn_hapus_so",
            ):
                with st.spinner(f"⏳ Hapus SO rak {_rak_hapus}..."):
                    _ok, _msg, _detail = delete_so_by_date(_tanggal, rak_id=_rak_hapus)

                if _ok:
                    st.success(_msg)
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(_msg)
# =========================================================================
# INFO PANEL
# =========================================================================
with st.expander("ℹ️ Cara Input SO", expanded=False):
    st.markdown("""
    **📋 Alur Input SO (3 Layar):**

    **Layar 1 — Form:**
    1. Pilih tanggal, isi keterangan (opsional)
    2. Isi SPD (opsional)
    3. Cari rak → klik **🔍 Cari**
    4. Klik **+ Add** untuk menambahkan rak
    5. Isi nominal & PIC per rak
    6. Klik **➡️ LANJUT KONFIRMASI**

    **Layar 2 — Konfirmasi:**
    7. Review data (tanggal, rak, PIC, nominal)
    8. Klik **✅ SIMPAN SEKARANG** atau **❌ BATAL**

    **Layar 3 — Sukses:**
    9. Lihat notifikasi + summary
    10. Klik **📝 Input SO Lagi** atau **🏠 Ke Dashboard**

    **💡 Tips:**
    - 1x input bisa multi rak
    - Setiap rak punya PIC sendiri
    - Cek **Rak Belum SO** di tab **📊 Analisis**
    """)


# =========================================================================
# ROUTING TAB
# =========================================================================
_tab = st.session_state["so_tab"]

if _tab == "input":
    render_input_so()
elif _tab == "analisis":
    render_analisis()
elif _tab == "preview":
    render_preview()


# =========================================================================
# FOOTER
# =========================================================================
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; padding: 12px 0; "
    "font-family: 'Quicksand', sans-serif; font-size: 10px; "
    "color: #7a9b8e; letter-spacing: 1.5px; text-transform: uppercase;'>"
    "Stock Opname — Toko C383"
    "</div>",
    unsafe_allow_html=True,
)