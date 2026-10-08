"""
SO — Stock Opname (Konsolidasi v2)
===================================
Full replacement pages/input_so.py.

Mode: Multi-Rak + Nominal (tanpa detail per PLU)
Tab:
1. 📝 Input SO   — SPD + Multi-Rak (compact)
2. 📊 Analisis   — Tabel + Keterangan + Chart (expand)
3. 📋 Preview    — Preview & hapus SO per rak
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
# CSS — PROFESIONAL, DARK ELEGANT, HALLOWEEN-ISH
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

        /* Base typography */
        .stApp {
            font-family: 'Quicksand', -apple-system, sans-serif;
        }

        /* Header profile card */
        .profile-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 20px;
            background: linear-gradient(135deg, rgba(28, 16, 48, 0.9), rgba(45, 25, 75, 0.85));
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

        /* Input label - lebih kecil & subtle */
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

        /* Input fields - lebih compact */
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox > div > div,
        .stDateInput input {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            color: #F5E6D3 !important;
            background: rgba(20, 12, 35, 0.8) !important;
            border: 1px solid rgba(168, 85, 247, 0.3) !important;
            border-radius: 8px !important;
            min-height: 38px !important;
        }

        /* Buttons - subtle professional */
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

        /* Metric cards - clean, gak rame */
        .metric-clean {
            background: linear-gradient(135deg, rgba(28, 16, 48, 0.7), rgba(45, 25, 75, 0.6));
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

        /* Rak result card - compact */
        .rak-result {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: rgba(20, 12, 35, 0.6);
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

        /* Rak selected item - compact */
        .rak-selected {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            background: rgba(20, 12, 35, 0.5);
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

        /* Custom HTML table - professional */
        .so-table {
            width: 100%;
            border-collapse: collapse;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 12px;
            margin-top: 8px;
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
        .so-table td.keterangan {
            font-family: 'Quicksand', sans-serif;
            font-size: 11px;
            color: #A89B8E;
            max-width: 300px;
        }

        /* Big keterangan panel (di kanan tabel analisis) */
        .keterangan-panel {
            background: linear-gradient(135deg, rgba(28, 16, 48, 0.9), rgba(45, 25, 75, 0.85));
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

        /* Section divider */
        .section-divider {
            margin: 24px 0 16px 0;
            border: none;
            border-top: 1px solid rgba(168, 85, 247, 0.15);
        }
    </style>
    """, unsafe_allow_html=True)


inject_css()


# =========================================================================
# HEADER — PROFILE CARD STYLE
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
if "so_rak_list" not in st.session_state:
    st.session_state["so_rak_list"] = []

if "so_last_saved" not in st.session_state:
    st.session_state["so_last_saved"] = None

if "so_analisis_loaded" not in st.session_state:
    st.session_state["so_analisis_loaded"] = False

if "so_tab" not in st.session_state:
    st.session_state["so_tab"] = "input"

if "so_last_loaded_date" not in st.session_state:
    st.session_state["so_last_loaded_date"] = None


# =========================================================================
# NOTIFIKASI SUKSES
# =========================================================================
if st.session_state["so_last_saved"]:
    st.success(st.session_state["so_last_saved"])
    st.session_state["so_last_saved"] = None
    time.sleep(1)


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
# TAB 1: INPUT SO (Compact Layout)
# =========================================================================
def render_input_so():
    """Input SO: SPD + Multi-Rak (nominal per rak) — compact & efisien."""
    st.markdown("### 📝 Input SO")
    st.caption("Input SPD (opsional) + rak yang di-SO dalam 1 form")

    # ============================================================
    # INFO SO — 3 kolom compact (tanggal, PIC, keterangan)
    # ============================================================
    _col_tgl, _col_pic, _col_ket = st.columns([1.2, 1.5, 2])

    with _col_tgl:
        _tanggal = st.date_input(
            "📅 Tanggal SO",
            value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
            key="so_input_tanggal",
        )

    with _col_pic:
        if _personil_list:
            _pic_pilih = st.selectbox(
                "👤 PIC",
                options=_personil_list,
                key="so_input_pic",
            )
        else:
            _pic_pilih = st.text_input(
                "👤 PIC",
                placeholder="Nama PIC",
                key="so_input_pic_manual",
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
            }
            for r in (_existing or [])
        ]
        st.session_state["so_last_loaded_date"] = _tanggal
        st.rerun()

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # SPD — compact single row
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
                f"<div class='metric-clean' style='border-left-color: #7FB99B; padding: 10px 14px; margin-top: 4px;'>"
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
    # MULTI-RAK — Search + Add
    # ============================================================
    st.markdown("#### 📦 Stock Opname (Multi-Rak)")
    st.caption("Cari rak → klik **+ Add** → isi nominal per rak")

    _search_query = st.text_input(
        "🔍 Cari Rak",
        key="so_search_rak",
        placeholder="Ketik kode rak (contoh: QA1, AT, CHILLER)...",
        label_visibility="collapsed",
    )

    # === HASIL SEARCH ===
    if _search_query and len(_search_query.strip()) >= 2:
        _search_results = search_rak(_search_query, limit=10)

        if _search_results:
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
                            st.session_state["so_rak_list"].append({
                                "rak_id": _rid,
                                "nominal_adjust": 0.0,
                            })
                            st.rerun()
        else:
            st.warning(f"⚠️ Rak **'{_search_query}'** tidak ditemukan.")
    elif _search_query and len(_search_query.strip()) < 2:
        st.info("💡 Ketik minimal **2 karakter**.")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # LIST RAK TERPILIH — Compact 1-row per rak
    # ============================================================
    if st.session_state["so_rak_list"]:
        st.markdown(f"#### 📋 Rak Terpilih ({len(st.session_state['so_rak_list'])})")

        _items_to_remove = []

        for _idx, _item in enumerate(st.session_state["so_rak_list"]):
            _rid = _item["rak_id"]
            _rak_info = get_rak_by_kode_exact(_rid)
            _rname = _rak_info.get("rak_name", "-") if _rak_info else "-"

            # Compact: rak info + nominal + delete dalam 1 baris
            _c1, _c2, _c3 = st.columns([2.5, 2, 0.6])

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
                    key=f"nominal_{_rid}_{_idx}",
                    label_visibility="collapsed",
                )
                st.session_state["so_rak_list"][_idx]["nominal_adjust"] = float(_new_nominal)

            with _c3:
                if st.button("🗑️", key=f"btn_del_{_rid}_{_idx}", width="stretch"):
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
    # TOMBOL SIMPAN
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    _col_save, _col_cancel = st.columns([3, 1])

    with _col_save:
        if st.button(
            "💾 SIMPAN SO",
            width="stretch",
            type="primary",
            key="btn_save_all_so",
        ):
            _has_rak = len(st.session_state["so_rak_list"]) > 0
            _has_spd = _spd_val > 0

            if not _has_rak and not _has_spd:
                st.error("⚠️ Minimal isi SPD atau tambahkan 1 rak!")
            elif not _pic_pilih:
                st.error("⚠️ Pilih/isi PIC dulu")
            else:
                with st.spinner("⏳ Menyimpan..."):
                    _ok, _msg, _detail = save_input_harian(
                        tanggal=_tanggal,
                        spd=_spd_val,
                        rak_items=st.session_state["so_rak_list"],
                        keterangan=_keterangan,
                        pic=_pic_pilih,
                        update_status_rak=True,
                    )

                if _ok:
                    st.session_state["so_last_saved"] = _msg
                    st.session_state["so_rak_list"] = []
                    st.session_state["so_last_loaded_date"] = None
                    st.cache_data.clear()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(_msg)

    with _col_cancel:
        if st.button(
            "🗑️ Clear",
            width="stretch",
            key="btn_clear_so",
        ):
            st.session_state["so_rak_list"] = []
            st.rerun()


# =========================================================================
# TAB 2: ANALISIS SO (Redesign)
# =========================================================================
def render_analisis():
    """Analisis: Tabel kiri + Keterangan kanan + Chart di expander bawah."""
    st.markdown("### 📊 Analisis SO")
    st.caption("Ringkasan SO per periode")

    # ============================================================
    # FILTER PERIODE — compact 1 row
    # ============================================================
    _col_p1, _col_p2, _col_p3 = st.columns([2, 2, 1])

    with _col_p1:
        _tgl_start = st.date_input(
            "📅 Dari",
            value=date.today().replace(day=1),
            key="so_analisis_start",
        )

    with _col_p2:
        _tgl_end = st.date_input(
            "📅 Sampai",
            value=date.today(),
            key="so_analisis_end",
        )

    with _col_p3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Analisis", width="stretch", type="primary", key="btn_analisis_so"):
            st.session_state["so_analisis_loaded"] = True
            st.session_state["so_analisis_periode"] = (_tgl_start, _tgl_end)

    if not st.session_state["so_analisis_loaded"]:
        st.info("💡 Pilih periode & klik **🔍 Analisis** untuk mulai")
        return

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # HITUNG DATA ANALISIS
    # ============================================================
    with st.spinner("⏳ Load analytics..."):
        _akumulasi = get_akumulasi_nominal_bulan()
        _btsb_result = hitung_btsb_akumulatif()
        _so_detail = get_so_rak_detail(limit=500)

    _total_rak = _akumulasi.get("total_rak", 0)
    _jumlah_hari = _akumulasi.get("jumlah_hari", 0)
    _total_nominal = _akumulasi.get("total_nominal", 0)
    _total_spd = _btsb_result.get("total_spd", 0)
    _btsb_akum = _btsb_result.get("btsb_akumulatif", 0)

    # %NSB
    if _total_spd > 0:
        _pct_nsb = (abs(_total_nominal) / _total_spd * 100)
    else:
        _pct_nsb = 0.0

    # Status BTSB
    _pct_btsb = (abs(_total_nominal) / _btsb_akum * 100) if _btsb_akum > 0 else 0
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
    # TABEL ANALISIS — Kiri (tabel) + Kanan (keterangan besar)
    # ============================================================
    _col_table, _col_ket = st.columns([3, 2])

    with _col_table:
        st.markdown("#### 📋 Ringkasan SO")

        # Build custom HTML table
        _table_html = (
            "<table class='so-table'>"
            "<thead><tr>"
            "<th>Metric</th>"
            "<th style='text-align: right;'>Nilai</th>"
            "</tr></thead><tbody>"
            f"<tr><td class='rak-id'>🏪 Jumlah Rak di-SO</td>"
            f"<td class='nominal pos'>{_total_rak} rak</td></tr>"
            f"<tr><td class='rak-id'>📅 Jumlah Hari</td>"
            f"<td class='nominal pos'>{_jumlah_hari} hari</td></tr>"
            f"<tr><td class='rak-id'>💰 Total Nominal SO</td>"
            f"<td class='nominal {'neg' if _total_nominal < 0 else 'pos'}'>"
            f"{fmt_rp_signed(_total_nominal)}</td></tr>"
            f"<tr><td class='rak-id'>📈 Total SPD</td>"
            f"<td class='nominal pos'>{fmt_rp(_total_spd)}</td></tr>"
            f"<tr><td class='rak-id'>🎯 BTSB Akumulatif</td>"
            f"<td class='nominal pos'>{fmt_rp(_btsb_akum)}</td></tr>"
            f"<tr><td class='rak-id'>📊 %NSB dari Sales</td>"
            f"<td class='nominal {'neg' if _pct_nsb > 0.15 else 'pos'}'>"
            f"{_pct_nsb:.3f}%</td></tr>"
            "</tbody></table>"
        )
        st.markdown(_table_html, unsafe_allow_html=True)

    with _col_ket:
        st.markdown("#### 💡 Keterangan")

        # Keterangan besar — status
        st.markdown(
            f"<div class='keterangan-panel {_status_class}'>"
            f"<div class='panel-label'>🎯 STATUS BTSB</div>"
            f"<div class='panel-value' style='color: {_status_color};'>"
            f"{_status}</div>"
            f"<div class='panel-sub'>Penggunaan: {_pct_btsb:.2f}% dari BTSB</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Keterangan besar — gap
        _gap = _btsb_akum - abs(_total_nominal)
        _gap_color = "#7FB99B" if _gap >= 0 else "#E88B8B"
        st.markdown(
            f"<div class='keterangan-panel' style='border-left-color: {_gap_color};'>"
            f"<div class='panel-label'>💰 SISA BUDGET BTSB</div>"
            f"<div class='panel-value' style='color: {_gap_color}; font-size: 22px;'>"
            f"{fmt_rp(_gap)}</div>"
            f"<div class='panel-sub'>{'✅ Masih aman' if _gap >= 0 else '⚠️ Over budget'}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ============================================================
    # DETAIL PER RAK — Scroll ke bawah (di expander biar gak berat)
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    with st.expander(f"📋 Daftar Rak yang di-SO ({len(_so_detail) if _so_detail else 0} baris)", expanded=False):
        if _so_detail:
            _df_detail = pd.DataFrame(_so_detail)
            _cols_show = ["so_date", "rak_id", "nominal_adjust", "pic", "keterangan"]
            _cols_show = [c for c in _cols_show if c in _df_detail.columns]

            if _cols_show:
                _df_show = _df_detail[_cols_show].copy()

                if "nominal_adjust" in _df_show.columns:
                    _df_show["nominal_adjust"] = _df_show["nominal_adjust"].apply(
                        lambda v: fmt_rp_signed(v)
                    )

                _col_names = ["Tanggal", "Kode Rak", "Nominal", "PIC", "Keterangan"]
                _df_show.columns = _col_names[:len(_df_show.columns)]

                st.dataframe(_df_show, width="stretch", hide_index=True, height=400)
                st.caption(f"📊 Total **{len(_df_show)}** baris SO")
        else:
            st.info("📭 Belum ada data SO di periode ini")

    # ============================================================
    # CHART ADJUST SO — di expander (biar gak bikin berat)
    # ============================================================
    with st.expander("📈 Grafik Adjust SO per Rak (Klik untuk buka)", expanded=False):
        if _so_detail:
            try:
                _df = pd.DataFrame(_so_detail)
                if "nominal_adjust" in _df.columns and "rak_id" in _df.columns:
                    _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
                    _grp = _df.groupby("rak_id")["nominal_adjust"].sum().reset_index()
                    _grp = _grp.sort_values("nominal_adjust", ascending=True)

                    import plotly.graph_objects as go

                    _colors = ["#E88B8B" if v < 0 else "#7FB99B" for v in _grp["nominal_adjust"]]

                    _fig = go.Figure()
                    _fig.add_trace(go.Bar(
                        x=_grp["nominal_adjust"],
                        y=_grp["rak_id"],
                        orientation="h",
                        marker=dict(color=_colors, line=dict(color="rgba(184, 115, 51, 0.5)", width=1)),
                        text=[f"{v:+,.0f}".replace(",", ".") for v in _grp["nominal_adjust"]],
                        textposition="outside",
                        textfont=dict(color="#E8B189", size=10, family="JetBrains Mono"),
                        hovertemplate="<b>%{y}</b><br>Nominal: %{x:+,.0f}<extra></extra>",
                    ))

                    _fig.update_layout(
                        height=max(400, len(_grp) * 28),
                        margin=dict(l=10, r=60, t=20, b=40),
                        plot_bgcolor="rgba(28, 16, 48, 0.3)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#A89B8E", family="JetBrains Mono", size=10),
                        xaxis=dict(
                            title="Nominal (Rp)",
                            gridcolor="rgba(168, 85, 247, 0.1)",
                            zeroline=True,
                            zerolinecolor="rgba(232, 177, 137, 0.5)",
                            zerolinewidth=1,
                        ),
                        yaxis=dict(
                            gridcolor="rgba(168, 85, 247, 0.1)",
                            autorange="reversed",
                        ),
                        showlegend=False,
                    )

                    st.plotly_chart(_fig, width="stretch", key="chart_adjust_so")
                else:
                    st.info("📭 Data SO kosong")
            except Exception as _e_chart:
                st.warning(f"⚠️ Chart gagal render: {str(_e_chart)[:150]}")
        else:
            st.info("📭 Belum ada data SO di periode ini")
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
    # LOAD DATA — ✅ FIX NameError: pake try-except
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
    # SUMMARY METRIC — 3 kolom compact
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
    # TABEL SUMMARY PER RAK — Custom HTML
    # ============================================================
    st.markdown("#### 📊 Summary per Rak")

    _rows_html = ""
    for _r in _so_summary:
        _rak = _r.get("rak_id", "-")
        _pic = _r.get("pic", "-") or "-"
        _item = int(_r.get("total_item", 0))
        _qty_var = int(_r.get("total_qty_var", 0))
        _nom = float(_r.get("nominal_adjust", 0))
        _ket = _r.get("keterangan", "") or "-"

        _nom_class = "neg" if _nom < 0 else "pos"

        _rows_html += (
            f"<tr>"
            f"<td class='rak-id'>{_rak}</td>"
            f"<td>{_pic}</td>"
            f"<td style='text-align: center;'>{_item}</td>"
            f"<td style='text-align: center;'>{_qty_var:+d}</td>"
            f"<td class='nominal {_nom_class}'>{fmt_rp_signed(_nom)}</td>"
            f"<td class='keterangan'>{_ket[:80]}</td>"
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
        "<th>Keterangan</th>"
        "</tr></thead>"
        f"<tbody>{_rows_html}</tbody>"
        "</table>"
    )

    st.markdown(_table_html, unsafe_allow_html=True)

    # ============================================================
    # DETAIL PRODUK (kalau ada) — Expander
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
# INFO PANEL — CARA INPUT SO
# =========================================================================
with st.expander("ℹ️ Cara Input SO", expanded=False):
    st.markdown("""
    **📋 Langkah Input SO:**
    
    1. **Pilih Tanggal SO** — default hari ini
    2. **Pilih PIC** — nama yang ngelakuin SO
    3. **Isi Keterangan** (opsional)
    4. **Isi SPD** (opsional) — kalau ada penjualan hari ini
    5. **Cari Rak** — ketik kode rak (contoh: QA1)
    6. **Klik + Add** untuk menambahkan rak ke daftar
    7. **Isi Nominal** per rak (boleh minus)
    8. **Klik 💾 SIMPAN SO**
    
    **💡 Tips:**
    - **1x input bisa multi rak** — tinggal cari & add beberapa rak sekaligus
    - **Nominal** diisi per rak, bisa positif/negatif
    - **Total nominal** auto-sum dari semua rak
    - SPD disimpan terpisah ke tabel `spd_harian`
    - Status rak otomatis jadi **SELESAI** setelah di-SO
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