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
# PAGE-SPECIFIC CSS (sisanya di themes/halloween.py)
# =========================================================================
def inject_css():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        .main .block-container {
            max-width: 100% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-top: 0.5rem !important;
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
# =========================================================================
# DIALOG: KONFIRMASI (POP-UP)
# =========================================================================
@st.dialog("✅ Konfirmasi Data SO", width="large")
def _dialog_konfirmasi_so():
    _pending = st.session_state.get("so_pending_data")
    if not _pending:
        st.error("Data tidak ditemukan.")
        return

    st.markdown("Review data sebelum disimpan:")

    # Metric
    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.markdown(f"<div class='metric-clean'><div class='label'>📅 TANGGAL</div><div class='value' style='font-size: 16px;'>{_pending['tanggal'].strftime('%d/%m/%Y')}</div></div>", unsafe_allow_html=True)
    with _c2:
        st.markdown(f"<div class='metric-clean'><div class='label'>🏪 RAK</div><div class='value' style='font-size: 16px;'>{len(_pending['rak_items'])}</div></div>", unsafe_allow_html=True)
    with _c3:
        st.markdown(f"<div class='metric-clean'><div class='label'>💰 SPD</div><div class='value' style='font-size: 16px; color: #7FB99B;'>{fmt_rp(_pending['spd']) if _pending['spd'] > 0 else '—'}</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 10px;'>", unsafe_allow_html=True)
    
    # Tabel
    _rows_html = ""
    _total_nom = 0
    for _item in _pending["rak_items"]:
        _nom = float(_item.get("nominal_adjust", 0))
        _total_nom += _nom
        _rak_info = get_rak_by_kode_exact(_item["rak_id"])
        _rname = _rak_info.get("rak_name", "-") if _rak_info else "-"
        _pic = _item.get("pic", "-")
        _rows_html += f"<tr><td class='rak-id'>{_item['rak_id']}</td><td>{_rname}</td><td>{_pic}</td><td class='nominal {'neg' if _nom < 0 else 'pos'}'>{fmt_rp_signed(_nom)}</td></tr>"

    st.markdown(f"<table class='so-table'><thead><tr><th>Rak</th><th>Nama</th><th>PIC</th><th style='text-align:right;'>Nominal</th></tr></thead><tbody>{_rows_html}</tbody></table>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='metric-clean' style='border-left-color: {'#E88B8B' if _total_nom < 0 else '#7FB99B'}; margin-top: 16px; text-align: right;'><div class='label'>💰 TOTAL NOMINAL</div><div class='value'>{fmt_rp_signed(_total_nom)}</div></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Tombol Aksi
    _col_ok, _col_batal = st.columns(2)
    with _col_ok:
        if st.button("✅ SIMPAN SEKARANG", use_container_width=True, type="primary", key="btn_simpan_dialog"):
            with st.spinner("⏳ Menyimpan..."):
                _ok_all = True
                _msg_list = []
                if _pending.get("spd", 0) > 0:
                    save_spd_harian(_pending["tanggal"], _pending["spd"], _pending.get("keterangan", ""))
                
                for _item in _pending["rak_items"]:
                    try:
                        _ok, _msg, _ = save_input_harian(
                            tanggal=_pending["tanggal"], spd=0, rak_items=[_item],
                            keterangan=_pending.get("keterangan", ""), pic=_item.get("pic", ""), update_status_rak=True
                        )
                        if _ok: _msg_list.append(f"✅ {_item['rak_id']}")
                        else: _ok_all = False
                    except Exception as _e: _ok_all = False

            if _ok_all:
                st.session_state["so_saved_data"] = _pending
                st.session_state["so_rak_list"] = []
                st.session_state["so_pending_data"] = None
                st.rerun()  # ✅ Tutup dialog & refresh halaman utama
            else:
                st.error("Gagal menyimpan beberapa data.")

    with _col_batal:
        if st.button("❌ BATAL", use_container_width=True, key="btn_batal_dialog"):
            st.rerun()  # ✅ Tutup dialog

# =========================================================================
# DIALOG: KONFIRMASI (POP-UP)
# =========================================================================
@st.dialog("✅ Konfirmasi Data SO", width="large")
def _dialog_konfirmasi_so():
    _pending = st.session_state.get("so_pending_data")
    if not _pending:
        st.error("Data tidak ditemukan.")
        return

    st.markdown("Review data sebelum disimpan:")

    # Metric
    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>📅 TANGGAL</div>"
            f"<div class='value' style='font-size: 16px;'>"
            f"{_pending['tanggal'].strftime('%d/%m/%Y')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _c2:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>🏪 RAK</div>"
            f"<div class='value' style='font-size: 16px;'>"
            f"{len(_pending['rak_items'])}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _c3:
        _spd_txt = fmt_rp(_pending['spd']) if _pending['spd'] > 0 else '—'
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>💰 SPD</div>"
            f"<div class='value' style='font-size: 16px; color: #7FB99B;'>"
            f"{_spd_txt}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Tabel
    _rows_html = ""
    _total_nom = 0
    for _item in _pending["rak_items"]:
        _nom = float(_item.get("nominal_adjust", 0))
        _total_nom += _nom
        _rak_info = get_rak_by_kode_exact(_item["rak_id"])
        _rname = _rak_info.get("rak_name", "-") if _rak_info else "-"
        _pic = _item.get("pic", "-")
        _nom_class = "neg" if _nom < 0 else "pos"
        _rows_html += (
            f"<tr>"
            f"<td class='rak-id'>{_item['rak_id']}</td>"
            f"<td style='font-family: Quicksand, sans-serif;'>{_rname}</td>"
            f"<td style='font-family: Quicksand, sans-serif; color: #E8B189;'>{_pic}</td>"
            f"<td class='nominal {_nom_class}'>{fmt_rp_signed(_nom)}</td>"
            f"</tr>"
        )

    st.markdown(
        f"<table class='so-table'>"
        f"<thead><tr>"
        f"<th>Rak</th><th>Nama</th><th>PIC</th>"
        f"<th style='text-align:right;'>Nominal</th>"
        f"</tr></thead>"
        f"<tbody>{_rows_html}</tbody>"
        f"</table>",
        unsafe_allow_html=True,
    )

    _color_total = "#E88B8B" if _total_nom < 0 else "#7FB99B"
    st.markdown(
        f"<div class='metric-clean' style='border-left-color: {_color_total}; "
        f"margin-top: 16px; text-align: right;'>"
        f"<div class='label'>💰 TOTAL NOMINAL</div>"
        f"<div class='value'>{fmt_rp_signed(_total_nom)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Tombol Aksi
    _col_ok, _col_batal = st.columns(2)

    with _col_ok:
        if st.button(
            "✅ SIMPAN SEKARANG",
            use_container_width=True,
            type="primary",
            key="btn_simpan_dialog",
        ):
            with st.spinner("⏳ Menyimpan..."):
                _ok_all = True
                _msg_list = []

                # Simpan SPD
                if _pending.get("spd", 0) > 0:
                    try:
                        save_spd_harian(
                            _pending["tanggal"],
                            _pending["spd"],
                            _pending.get("keterangan", ""),
                        )
                    except Exception as _e_spd:
                        print(f"[SAVE SPD ERROR] {_e_spd}")

                # Simpan per rak
                for _item in _pending["rak_items"]:
                    try:
                        _ok, _msg, _ = save_input_harian(
                            tanggal=_pending["tanggal"],
                            spd=0,
                            rak_items=[_item],
                            keterangan=_pending.get("keterangan", ""),
                            pic=_item.get("pic", ""),
                            update_status_rak=True,
                        )
                        if _ok:
                            _msg_list.append(f"✅ {_item['rak_id']}")
                        else:
                            _ok_all = False
                            _msg_list.append(f"❌ {_item['rak_id']}")
                    except Exception as _e_rak:
                        _ok_all = False
                        _msg_list.append(f"❌ {_item['rak_id']}: {str(_e_rak)[:50]}")

            if _ok_all:
                st.session_state["so_saved_data"] = dict(_pending)
                st.session_state["so_pending_data"] = None
                st.session_state["so_rak_list"] = []
                st.session_state["so_search_results"] = []
                st.session_state["so_search_shown"] = False
                st.session_state["so_last_loaded_date"] = None
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Gagal menyimpan:\n" + "\n".join(_msg_list))

    with _col_batal:
        if st.button(
            "❌ BATAL",
            use_container_width=True,
            key="btn_batal_dialog",
        ):
            st.session_state["so_pending_data"] = None
            st.rerun()


# =========================================================================
# DIALOG: SUKSES (POP-UP)
# =========================================================================
@st.dialog("🎉 Berhasil Disimpan", width="small")
def _dialog_sukses_so():
    _saved = st.session_state.get("so_saved_data")
    if not _saved:
        st.session_state["so_saved_data"] = None
        st.rerun()
        return

    # Notifikasi sukses
    st.markdown(
        "<div style='text-align: center; padding: 10px 0;'>"
        "<div class='success-icon'>✅</div>"
        "<div class='success-title'>DATA TERSIMPAN</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Summary
    _total_rak = len(_saved.get("rak_items", []))
    _total_nom = sum(float(i.get("nominal_adjust", 0)) for i in _saved.get("rak_items", []))
    _spd_val = _saved.get("spd", 0)

    st.markdown(
        f"<div class='metric-clean' style='text-align: center;'>"
        f"<div class='label'>🏪 RAK DI-SO</div>"
        f"<div class='value'>{_total_rak}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    _color_nom = "#E88B8B" if _total_nom < 0 else "#7FB99B"
    st.markdown(
        f"<div class='metric-clean' style='text-align: center; "
        f"border-left-color: {_color_nom};'>"
        f"<div class='label'>💰 TOTAL NOMINAL</div>"
        f"<div class='value' style='color: {_color_nom};'>{fmt_rp_signed(_total_nom)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if _spd_val > 0:
        st.markdown(
            f"<div class='metric-clean' style='text-align: center; "
            f"border-left-color: #7FB99B;'>"
            f"<div class='label'>💰 SPD</div>"
            f"<div class='value' style='color: #7FB99B;'>{fmt_rp(_spd_val)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Tombol tutup
    if st.button("TUTUP & INPUT LAGI", use_container_width=True, key="btn_tutup_sukses"):
        st.session_state["so_saved_data"] = None
        st.rerun()
        
# =========================================================================
# TAB 1: INPUT SO (FORM UTAMA)
# =========================================================================
def render_input_so():
    """Router: dialog sukses → dialog konfirmasi → form input."""
    # ✅ Cek saved data DULU (sukses)
    if st.session_state.get("so_saved_data"):
        _dialog_sukses_so()
        st.info("📌 Selesaikan dialog di atas untuk melanjutkan.")
        return

    # ✅ Cek pending data (dialog konfirmasi)
    if st.session_state.get("so_pending_data"):
        _dialog_konfirmasi_so()
        # Form tetap dirender di belakang
        _render_input_form()
        return

    # ✅ Default: render form
    _render_input_form()


# =========================================================================
# SCREEN 1: FORM INPUT
# =========================================================================
def _render_input_form():
    """Layar 1: Form input SO."""
    st.markdown("### 📝 Input SO")
    st.caption("Input SPD (opsional) + rak yang di-SO dalam 1 form")

    # --- INFO SO ---
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

    # --- SPD ---
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
            st.markdown(
                f"<div class='metric-clean' style='border-left-color: #7FB99B; "
                f"padding: 10px 14px; margin-top: 4px;'>"
                f"<div class='label'>💡 BTSB OTOMATIS</div>"
                f"<div class='value' style='font-size: 18px; color: #7FB99B;'>"
                f"{fmt_rp(hitung_btsb_harian(_spd_val))}</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='padding: 12px 0; font-family: JetBrains Mono, monospace; "
                "font-size: 11px; color: #A89B8E;'>💡 BTSB: — (SPD = 0)</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # --- SEARCH RAK ---
    st.markdown("#### 📦 Stock Opname (Multi-Rak)")
    st.caption("Cari rak → klik **+ Add** → isi nominal & PIC per rak")

    _col_search, _col_btn, _col_custom = st.columns([3, 1, 1])

    with _col_search:
        _search_query = st.text_input(
            "🔍 Cari Rak",
            placeholder="Ketik kode rak...",
            key="so_search_input",
            label_visibility="collapsed",
        )
    
    with _col_btn:
        _search_submit = st.button("🔍 Cari", key="btn_search_rak", width="stretch", type="primary")
    
    with _col_custom:
        if st.button(
            "➕ Custom Rak",
            key="btn_custom_rak_open",
            width="stretch",
            help="Tambah rak yang belum ada di master",
        ):
            _dialog_custom_rak()
        
    if _search_submit and _search_query and len(_search_query.strip()) >= 2:
        st.session_state["so_search_results"] = search_rak(_search_query, limit=10)
        st.session_state["so_search_shown"] = True
    elif _search_query and len(_search_query.strip()) < 2:
        st.session_state["so_search_results"] = []
        st.session_state["so_search_shown"] = False
        st.info("💡 Ketik minimal **2 karakter**.")

    if st.session_state.get("so_search_shown") and st.session_state.get("so_search_results"):
        st.caption(f"💡 {len(st.session_state['so_search_results'])} rak ditemukan")
        for _idx, _rak in enumerate(st.session_state["so_search_results"]):
            _rid = _rak.get("rak_id", "-")
            _already_selected = any(r["rak_id"] == _rid for r in st.session_state["so_rak_list"])
            _c1, _c2 = st.columns([4, 1])
            with _c1:
                _status_icon = "✅" if _rak.get("status_so") == "SELESAI" else "⬜"
                st.markdown(
                    f"<div class='rak-result'><div>"
                    f"<div class='rak-result-id'>{_status_icon} {_rid}</div>"
                    f"<div class='rak-result-name'>{_rak.get('rak_name', '-')}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            with _c2:
                if _already_selected:
                    st.button("✓", key=f"btn_add_{_idx}_{_rid}", disabled=True, width="stretch")
                else:
                    if st.button("+ Add", key=f"btn_add_{_idx}_{_rid}", width="stretch", type="primary"):
                        _default_pic = _personil_list[0] if _personil_list else ""
                        st.session_state["so_rak_list"].append({
                            "rak_id": _rid,
                            "nominal_adjust": 0.0,
                            "pic": _default_pic,
                        })
                        st.rerun()
    elif st.session_state.get("so_search_shown") and not st.session_state.get("so_search_results"):
        st.warning("⚠️ Rak tidak ditemukan.")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # --- LIST RAK TERPILIH ---
    if st.session_state["so_rak_list"]:
        st.markdown(f"#### 📋 Rak Terpilih ({len(st.session_state['so_rak_list'])})")
        _items_to_remove = []
        for _idx, _item in enumerate(st.session_state["so_rak_list"]):
            _rid = _item["rak_id"]
            _rak_info = get_rak_by_kode_exact(_rid)
            _rname = _rak_info.get("rak_name", "-") if _rak_info else "-"
            _c1, _c2, _c3, _c4 = st.columns([2, 1.5, 1.5, 0.5])
            with _c1:
                st.markdown(
                    f"<div class='rak-selected' style='margin-top: 4px;'>"
                    f"<div class='rak-selected-id'>{_rid}</div>"
                    f"<div class='rak-selected-name'>{_rname}</div></div>",
                    unsafe_allow_html=True,
                )
            with _c2:
                _new_nominal = st.number_input(
                    f"Nominal {_rid}",
                    min_value=-999_999_999,
                    max_value=999_999_999,
                    step=1000,
                    value=int(_item.get("nominal_adjust", 0)),
                    key=f"so_nominal_{_rid}_{_idx}",
                    label_visibility="collapsed",
                )
                st.session_state["so_rak_list"][_idx]["nominal_adjust"] = float(_new_nominal)
            with _c3:
                _current_pic = _item.get("pic", "")
                _new_pic = st.selectbox(
                    f"PIC {_rid}",
                    options=_personil_list,
                    index=_personil_list.index(_current_pic) if _current_pic in _personil_list else 0,
                    key=f"so_pic_{_rid}_{_idx}",
                    label_visibility="collapsed",
                )
                st.session_state["so_rak_list"][_idx]["pic"] = _new_pic
            with _c4:
                if st.button("🗑️", key=f"so_del_{_rid}_{_idx}", width="stretch"):
                    _items_to_remove.append(_idx)

        if _items_to_remove:
            for _i in sorted(_items_to_remove, reverse=True):
                st.session_state["so_rak_list"].pop(_i)
            st.rerun()

        _total_nominal_input = sum(item.get("nominal_adjust", 0) for item in st.session_state["so_rak_list"])
        _color_total = "#E88B8B" if _total_nominal_input < 0 else "#7FB99B"
        st.markdown(
            f"<div class='metric-clean' style='border-left-color: {_color_total}; "
            f"margin-top: 16px; text-align: right;'>"
            f"<div class='label'>💰 TOTAL NOMINAL SO ({len(st.session_state['so_rak_list'])} RAK)</div>"
            f"<div class='value' style='color: {_color_total};'>"
            f"{fmt_rp_signed(_total_nominal_input)}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("📭 Belum ada rak. Cari & klik **+ Add** untuk menambahkan.")

    # --- TOMBOL AKSI ---
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    _col_save, _col_cancel = st.columns([3, 1])

    with _col_save:
        if st.button("➡️ LANJUT KONFIRMASI", key="btn_ke_konfirmasi", width="stretch", type="primary"):
            _rak_tanpa_pic = [r["rak_id"] for r in st.session_state["so_rak_list"] if not r.get("pic")]
            if not st.session_state["so_rak_list"] and _spd_val == 0:
                st.error("⚠️ Minimal isi SPD atau tambahkan 1 rak!")
            elif _rak_tanpa_pic:
                st.error(f"⚠️ Rak berikut belum punya PIC: **{', '.join(_rak_tanpa_pic)}**")
            else:
                st.session_state["so_pending_data"] = {
                    "tanggal": _tanggal,
                    "spd": _spd_val,
                    "rak_items": list(st.session_state["so_rak_list"]),
                    "keterangan": _keterangan,
                }
                st.rerun()

    with _col_cancel:
        if st.button("🗑️ Clear", key="btn_clear_so", width="stretch"):
            st.session_state["so_rak_list"] = []
            st.session_state["so_search_results"] = []
            st.session_state["so_search_shown"] = False
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

# =========================================================================
# HELPER: HEATMAP RAK × TANGGAL
# =========================================================================
def _render_analisis_heatmap(_so_detail_raw, _start, _end):
    """Heatmap rak × tanggal — visual nominal SO."""
    import plotly.graph_objects as go

    if not _so_detail_raw:
        st.info("📭 Belum ada data untuk heatmap")
        return

    _df = pd.DataFrame(_so_detail_raw)
    _df["so_date"] = pd.to_datetime(_df["so_date"], errors="coerce")
    _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
    _df["rak_id"] = _df["rak_id"].astype(str).str.upper()

    # Pivot: rak × tanggal
    _pivot = _df.pivot_table(
        index="rak_id",
        columns="so_date",
        values="nominal_adjust",
        aggfunc="sum",
        fill_value=0,
    )

    if _pivot.empty:
        st.info("📭 Data kosong setelah pivot")
        return

    # Sort: rak dengan total minus terbesar di atas
    _pivot["_total"] = _pivot.sum(axis=1)
    _pivot = _pivot.sort_values("_total", ascending=True)
    _pivot = _pivot.drop(columns=["_total"])

    # Batasi tampilan: max 30 rak
    _max_rak = 30
    if len(_pivot) > _max_rak:
        st.caption(f"⚠️ Menampilkan **{_max_rak} rak** dengan minus terbesar (dari {len(_pivot)})")
        _pivot = _pivot.head(_max_rak)

    # Label tanggal
    _x_labels = [_d.strftime("%d/%m") for _d in _pivot.columns]

    # Heatmap
    _fig = go.Figure(data=go.Heatmap(
        z=_pivot.values,
        x=_x_labels,
        y=_pivot.index.tolist(),
        colorscale=[
            [0.0, "#7FB99B"],       # plus (hijau)
            [0.5, "#1A0D2E"],       # netral (gelap)
            [1.0, "#E88B8B"],       # minus (merah)
        ],
        zmid=0,
        text=_pivot.values,
        texttemplate="%{text:,.0f}",
        textfont=dict(size=9, color="#F5E6D3", family="JetBrains Mono"),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Tanggal: %{x}<br>"
            "Nominal: Rp %{z:,.0f}"
            "<extra></extra>"
        ),
        colorbar=dict(
            title=dict(
                text="Nominal (Rp)",
                font=dict(color="#E8B189", size=10),
            ),
            tickfont=dict(color="#A89B8E", size=9),
            bgcolor="rgba(20, 12, 35, 0.9)",
            bordercolor="#4C1D95",
            borderwidth=1,
        ),
    ))

    _fig.update_layout(
        height=max(400, len(_pivot) * 30),
        margin=dict(l=10, r=20, t=30, b=60),
        plot_bgcolor="rgba(20, 12, 35, 0.5)",
        paper_bgcolor="rgba(20, 12, 35, 0.95)",
        font=dict(color="#A89B8E", family="JetBrains Mono", size=10),
        xaxis=dict(
            title="Tanggal",
            gridcolor="rgba(168, 85, 247, 0.1)",
            type="category",
            tickangle=-45,
        ),
        yaxis=dict(
            title="Rak",
            gridcolor="rgba(168, 85, 247, 0.1)",
            autorange="reversed",
        ),
    )

    st.plotly_chart(_fig, width="stretch", key="chart_heatmap_rak")
    
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
    # 🆕 TREND CHART (NSB vs BTSB Harian)
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    with st.expander("📈 Trend NSB vs BTSB Harian (Klik untuk buka)", expanded=False):
        _render_analisis_trend(_so_detail_raw, _start, _end)
    
    # ============================================================
    # 🆕 ANALYTICS PER PIC
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    with st.expander("👤 Analytics per PIC (Klik untuk buka)", expanded=False):
        _render_analisis_pic(_so_detail_raw)
    
    # ============================================================
    # 🆕 ANALYTICS PER KATEGORI
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    with st.expander("🏷️ Analytics per Kategori (Klik untuk buka)", expanded=False):
        _render_analisis_kategori(_so_detail_raw, _rak_df)
    
    # ============================================================
    # 🆕 HEATMAP RAK × TANGGAL
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    with st.expander("🔥 Heatmap Rak × Tanggal (Klik untuk buka)", expanded=False):
        _render_analisis_heatmap(_so_detail_raw, _start, _end)  
        
    # ============================================================
    # RAK BELUM SO — st.dataframe (scroll internal)
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    
    try:
        from modules.rak_monitor import get_rak_belum_so as _get_belum_so_df
    
        _rak_belum_df = _get_belum_so_df(_rak_df)
    
        if not _rak_belum_df.empty:
            _jumlah_belum = len(_rak_belum_df)
    
            with st.expander(f"📋 Rak Belum SO ({_jumlah_belum} rak)", expanded=False):
                _search_belum = st.text_input(
                    "🔍 Cari Rak",
                    key="search_rak_belum",
                    placeholder="Ketik kode/nama rak...",
                    label_visibility="collapsed",
                )
    
                _df_belum = _rak_belum_df.copy()
    
                # Filter by search
                if _search_belum and len(_search_belum.strip()) >= 1:
                    _q = _search_belum.strip().upper()
                    _df_belum = _df_belum[
                        _df_belum["rak_id"].astype(str).str.upper().str.contains(_q, na=False) |
                        _df_belum["rak_name"].astype(str).str.upper().str.contains(_q, na=False)
                    ]
    
                # ✅ Siapkan DataFrame dengan kolom rename untuk display
                _df_display = _df_belum[["rak_id", "rak_name"]].copy()
                _df_display.columns = ["Kode Rak", "Nama Rak"]
    
                # ✅ Download pakai data ASLI (sebelum rename)
                _download_text = "\n".join([
                    f"{r.get('rak_id', '-')} — {r.get('rak_name', '-')}"
                    for r in _df_belum.to_dict("records")
                ])
    
                st.dataframe(_df_display, width="stretch", hide_index=True, height=400)
                st.caption(f"📊 Total **{len(_df_display)}** rak belum di-SO")
    
                st.download_button(
                    label=f"📥 Download List ({len(_df_display)} rak)",
                    data=_download_text,
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
# HELPER: ANALYTICS SO — TREND, PIC, KATEGORI
# =========================================================================
def _render_analisis_trend(_so_detail_raw, _start, _end):
    """Render trend chart NSB vs BTSB per hari — sinkron sama ringkasan."""
    import plotly.graph_objects as go

    if not _so_detail_raw:
        st.info("📭 Belum ada data untuk trend")
        return

    _df = pd.DataFrame(_so_detail_raw)
    _df["so_date"] = pd.to_datetime(_df["so_date"], errors="coerce")
    _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)

    _per_hari = _df.groupby("so_date")["nominal_adjust"].sum().reset_index()
    _per_hari = _per_hari.sort_values("so_date")

    if _per_hari.empty:
        st.info("📭 Belum ada data trend")
        return

    # ✅ FIX: Ambil SPD total periode (konsisten sama ringkasan)
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()
        _spd_res = _sb.table("spd_harian") \
            .select("tanggal, spd") \
            .gte("tanggal", _start.isoformat()) \
            .lte("tanggal", _end.isoformat()) \
            .execute()
        _spd_map = {
            pd.to_datetime(r["tanggal"]): float(r.get("spd", 0))
            for r in (_spd_res.data or [])
        }
    except Exception:
        _spd_map = {}

    _tanggal_list = _per_hari["so_date"].dt.strftime("%d/%m").tolist()
    _nominal_list = _per_hari["nominal_adjust"].abs().tolist()

    # ✅ FIX: BTSB harian = (SPD hari itu) × 0.15%
    _btsb_list = [
        _spd_map.get(_tgl, 0) * 0.0015
        for _tgl in _per_hari["so_date"]
    ]

    # ✅ Total BTSB = SUM semua SPD × 0.15% (konsisten sama ringkasan)
    _total_spd_periode = sum(_spd_map.values())
    _total_btsb_periode = _total_spd_periode * 0.0015

    _fig = go.Figure()

    # Line 1: Nominal SO (abs per hari)
    _fig.add_trace(go.Scatter(
        x=_tanggal_list,
        y=_nominal_list,
        mode="lines+markers",
        name="Nominal SO",
        line=dict(color="#E88B8B", width=3, shape="spline"),
        marker=dict(size=10, color="#E88B8B", line=dict(color="#0F0A1E", width=2)),
        fill="tozeroy",
        fillcolor="rgba(232, 139, 139, 0.15)",
        hovertemplate="<b>%{x}</b><br>Nominal: Rp %{y:,.0f}<extra></extra>",
    ))

    # Line 2: BTSB Harian (per hari)
    if any(_b > 0 for _b in _btsb_list):
        _fig.add_trace(go.Scatter(
            x=_tanggal_list,
            y=_btsb_list,
            mode="lines+markers",
            name="BTSB Harian",
            line=dict(color="#7FB99B", width=2, dash="dash"),
            marker=dict(size=8, color="#7FB99B"),
            hovertemplate="<b>%{x}</b><br>BTSB: Rp %{y:,.0f}<extra></extra>",
        ))

    # ✅ FIX: Anotasi peak (hari dengan nominal tertinggi)
    if _nominal_list:
        _max_val = max(_nominal_list)
        _max_idx = _nominal_list.index(_max_val)
        _max_tgl = _tanggal_list[_max_idx]
        _max_btsb = _btsb_list[_max_idx] if _max_idx < len(_btsb_list) else 0

        _fig.add_annotation(
            x=_max_tgl,
            y=_max_val,
            text=f"⚠️ PEAK: Rp {int(_max_val):,}".replace(",", "."),
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor="#E88B8B",
            ax=0,
            ay=-40,
            bgcolor="rgba(232, 139, 139, 0.9)",
            bordercolor="#E88B8B",
            borderwidth=1,
            borderpad=6,
            font=dict(color="#0F0A1E", size=10, family="JetBrains Mono"),
        )

    _fig.update_layout(
        height=400,
        margin=dict(l=10, r=20, t=50, b=40),
        plot_bgcolor="rgba(20, 12, 35, 0.5)",
        paper_bgcolor="rgba(20, 12, 35, 0.95)",
        font=dict(color="#A89B8E", family="JetBrains Mono", size=10),
        xaxis=dict(
            title="Tanggal",
            gridcolor="rgba(168, 85, 247, 0.1)",
            type="category",
        ),
        yaxis=dict(
            title="Nominal (Rp)",
            gridcolor="rgba(168, 85, 247, 0.1)",
            zeroline=True,
            zerolinecolor="rgba(232, 177, 137, 0.3)",
            tickformat=",.0f",         # ✅ Full angka (tanpa k)
            tickprefix="Rp ",           # ✅ Prefix Rp
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#E8B189", size=10),
        ),
        hovermode="x unified",
    )

    st.plotly_chart(_fig, width="stretch", key="chart_trend_nsb_btsb")

    # ✅ FIX: Insight sinkron sama Ringkasan (pake BTSB periode)
    _total_abs = sum(_nominal_list)
    _pct = (_total_abs / _total_btsb_periode * 100) if _total_btsb_periode > 0 else 0

    _color = "#7FB99B" if _pct <= 80 else ("#fbbf24" if _pct <= 100 else "#E88B8B")

    st.markdown(
        f"<div style='background: rgba(20, 12, 35, 0.95); "
        f"border-left: 3px solid {_color}; border-radius: 8px; "
        f"padding: 12px 14px; margin-top: 12px; "
        f"font-family: JetBrains Mono, monospace; font-size: 11px; "
        f"color: #A89B8E; line-height: 1.6;'>"
        f"📊 <b style='color: {_color};'>Total Nominal SO:</b> Rp {int(_total_abs):,}".replace(",", ".") +
        f"<br>🎯 <b style='color: #7FB99B;'>BTSB Periode:</b> Rp {int(_total_btsb_periode):,}".replace(",", ".") +
        f"<br>📈 <b style='color: {_color};'>Penggunaan:</b> {_pct:.2f}%"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_analisis_pic(_so_detail_raw):
    """Render analytics per PIC — dengan normalize + detail rak."""
    import plotly.graph_objects as go

    if not _so_detail_raw:
        st.info("📭 Belum ada data PIC")
        return

    _df = pd.DataFrame(_so_detail_raw)
    _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)

    # ✅ FIX: Normalize PIC
    _df["pic"] = _df["pic"].fillna("").astype(str).str.strip().str.upper()
    _df["pic"] = _df["pic"].str.replace(r'\s+', ' ', regex=True)
    _df["pic"] = _df["pic"].replace("", "(KOSONG)")

    # Group by PIC
    _per_pic = _df.groupby("pic").agg(
        jumlah_rak=("rak_id", "nunique"),
        total_nominal=("nominal_adjust", "sum"),
        total_baris=("rak_id", "count"),
    ).reset_index()

    _per_pic["rata_rata"] = _per_pic["total_nominal"] / _per_pic["jumlah_rak"].replace(0, 1)
    _per_pic = _per_pic.sort_values("total_nominal", ascending=True)

    # Chart horizontal bar
    _fig = go.Figure()

    _colors = ["#E88B8B" if v < 0 else "#7FB99B" for v in _per_pic["total_nominal"]]

    _fig.add_trace(go.Bar(
        x=_per_pic["total_nominal"],
        y=_per_pic["pic"],
        orientation="h",
        marker=dict(color=_colors, line=dict(color="rgba(184, 115, 51, 0.5)", width=1)),
        text=[f"{v:+,.0f}".replace(",", ".") for v in _per_pic["total_nominal"]],
        textposition="outside",
        textfont=dict(color="#E8B189", size=10, family="JetBrains Mono"),
        customdata=_per_pic[["jumlah_rak", "total_baris"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Nominal: Rp %{x:+,.0f}<br>"
            "Rak: %{customdata[0]}<br>"
            "Baris SO: %{customdata[1]}"
            "<extra></extra>"
        ),
    ))

    _fig.update_layout(
        height=max(280, len(_per_pic) * 40),
        margin=dict(l=10, r=100, t=20, b=40),
        plot_bgcolor="rgba(20, 12, 35, 0.5)",
        paper_bgcolor="rgba(20, 12, 35, 0.95)",
        font=dict(color="#A89B8E", family="JetBrains Mono", size=10),
        xaxis=dict(
            title="Nominal (Rp)",
            gridcolor="rgba(168, 85, 247, 0.1)",
            zeroline=True,
            zerolinecolor="rgba(232, 177, 137, 0.5)",
            tickformat=",.0f",
            tickprefix="Rp ",
        ),
        yaxis=dict(
            gridcolor="rgba(168, 85, 247, 0.1)",
            autorange="reversed",
        ),
        showlegend=False,
    )

    st.plotly_chart(_fig, width="stretch", key="chart_pic_analytics")

    # Tabel detail
    _per_pic_show = _per_pic.sort_values("total_nominal").copy()

    _rows_html = ""
    for _, _r in _per_pic_show.iterrows():
        _nom = _r["total_nominal"]
        _nom_class = "neg" if _nom < 0 else "pos"
        _nom_str = f"{_nom:+,.0f}".replace(",", ".")
        _rata_str = f"{_r['rata_rata']:+,.0f}".replace(",", ".")

        _rows_html += (
            f"<tr>"
            f"<td class='rak-id'>{_r['pic']}</td>"
            f"<td style='text-align: center;'>{int(_r['jumlah_rak'])}</td>"
            f"<td style='text-align: center;'>{int(_r['total_baris'])}</td>"
            f"<td class='nominal {_nom_class}'>Rp {_nom_str}</td>"
            f"<td class='nominal {_nom_class}'>Rp {_rata_str}</td>"
            f"</tr>"
        )

    _table_html = (
        "<table class='so-table'>"
        "<thead><tr>"
        "<th>PIC</th>"
        "<th style='text-align: center;'>Rak</th>"
        "<th style='text-align: center;'>Baris</th>"
        "<th style='text-align: right;'>Total</th>"
        "<th style='text-align: right;'>Rata²/Rak</th>"
        "</tr></thead>"
        f"<tbody>{_rows_html}</tbody>"
        "</table>"
    )

    st.markdown(_table_html, unsafe_allow_html=True)

    # ✅ BARU: Detail rak per PIC
    with st.expander("🔍 Detail Rak per PIC (Klik untuk buka)", expanded=False):
        _col_filter, _col_count = st.columns([3, 1])

        with _col_filter:
            _pic_filter = st.selectbox(
                "Pilih PIC:",
                options=["(Semua)"] + sorted(_df["pic"].unique().tolist()),
                key="pic_detail_filter",
                label_visibility="collapsed",
            )

        _df_detail = _df.copy()
        if _pic_filter != "(Semua)":
            _df_detail = _df_detail[_df_detail["pic"] == _pic_filter]

        _df_detail = _df_detail.sort_values(["so_date", "rak_id"])

        with _col_count:
            st.markdown(
                f"<div style='text-align: right; padding-top: 8px; "
                f"font-family: JetBrains Mono, monospace; font-size: 11px; "
                f"color: #A89B8E;'>📊 {len(_df_detail)} baris</div>",
                unsafe_allow_html=True,
            )

        # Build custom table
        _rows_detail = ""
        for _, _r in _df_detail.iterrows():
            _nom = float(_r.get("nominal_adjust", 0))
            _nom_class = "neg" if _nom < 0 else "pos"
            _nom_str = f"{_nom:+,.0f}".replace(",", ".")
            _tgl = pd.to_datetime(_r.get("so_date")).strftime("%d/%m/%Y") if _r.get("so_date") else "-"
            _rak = _r.get("rak_id", "-")
            _pic = _r.get("pic", "-")
            _ket = (_r.get("keterangan", "") or "")[:40]

            _rows_detail += (
                f"<tr>"
                f"<td>{_tgl}</td>"
                f"<td class='rak-id'>{_rak}</td>"
                f"<td style='font-family: Quicksand, sans-serif; color: #E8B189;'>{_pic}</td>"
                f"<td class='nominal {_nom_class}'>{_nom_str}</td>"
                f"<td style='font-family: Quicksand, sans-serif; font-size: 10px; color: #A89B8E;'>{_ket}</td>"
                f"</tr>"
            )

        _table_detail = (
            "<table class='so-table'>"
            "<thead><tr>"
            "<th>Tanggal</th>"
            "<th>Rak</th>"
            "<th>PIC</th>"
            "<th style='text-align: right;'>Nominal</th>"
            "<th>Keterangan</th>"
            "</tr></thead>"
            f"<tbody>{_rows_detail}</tbody>"
            "</table>"
        )

        st.markdown(_table_detail, unsafe_allow_html=True)


def _render_analisis_kategori(_so_detail_raw, _rak_df):
    """Render analytics per kategori rak."""
    import plotly.graph_objects as go

    if not _so_detail_raw:
        st.info("📭 Belum ada data kategori")
        return

    if _rak_df is None or _rak_df.empty:
        st.info("📭 Data rak_master kosong")
        return

    _kategori_map = dict(zip(
        _rak_df["rak_id"].astype(str).str.upper(),
        _rak_df["kategori"].astype(str).str.upper(),
    ))

    _df = pd.DataFrame(_so_detail_raw)
    _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
    _df["rak_id"] = _df["rak_id"].astype(str).str.upper()
    _df["kategori"] = _df["rak_id"].map(_kategori_map).fillna("LAINNYA")

    _per_kat = _df.groupby("kategori").agg(
        jumlah_rak=("rak_id", "nunique"),
        total_nominal=("nominal_adjust", "sum"),
        total_baris=("rak_id", "count"),
    ).reset_index()

    _per_kat = _per_kat.sort_values("total_nominal")

    if _per_kat.empty:
        st.info("📭 Belum ada data kategori")
        return

    _col_pie, _col_tab = st.columns([1, 1])

    with _col_pie:
        _fig_pie = go.Figure(data=[go.Pie(
            labels=_per_kat["kategori"],
            values=_per_kat["total_nominal"].abs(),
            hole=0.5,
            marker=dict(
                colors=["#E8B189", "#7FB99B", "#E88B8B", "#A855F7", "#FBBF24", "#64748B"],
                line=dict(color="#0F0A1E", width=2),
            ),
            textinfo="label+percent",
            textfont=dict(color="#F5E6D3", size=10, family="JetBrains Mono"),
            hovertemplate="<b>%{label}</b><br>Nominal: Rp %{value:,.0f}<br>%{percent}<extra></extra>",
        )])

        _fig_pie.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=20, b=20),
            plot_bgcolor="rgba(20, 12, 35, 0.5)",
            paper_bgcolor="rgba(20, 12, 35, 0.95)",
            font=dict(color="#A89B8E", family="JetBrains Mono", size=10),
            showlegend=True,
            legend=dict(
                font=dict(color="#E8B189", size=10),
                bgcolor="rgba(20, 12, 35, 0.8)",
            ),
        )

        st.plotly_chart(_fig_pie, width="stretch", key="chart_kategori_pie")

    with _col_tab:
        _rows_html = ""
        for _, _r in _per_kat.iterrows():
            _nom = _r["total_nominal"]
            _nom_class = "neg" if _nom < 0 else "pos"
            _nom_str = f"{_nom:+,.0f}".replace(",", ".")

            _rows_html += (
                f"<tr>"
                f"<td class='rak-id'>{_r['kategori']}</td>"
                f"<td style='text-align: center;'>{int(_r['jumlah_rak'])}</td>"
                f"<td class='nominal {_nom_class}'>Rp {_nom_str}</td>"
                f"</tr>"
            )

        _table_html = (
            "<table class='so-table'>"
            "<thead><tr>"
            "<th>Kategori</th>"
            "<th style='text-align: center;'>Rak</th>"
            "<th style='text-align: right;'>Total</th>"
            "</tr></thead>"
            f"<tbody>{_rows_html}</tbody>"
            "</table>"
        )

        st.markdown(_table_html, unsafe_allow_html=True)
        
# =========================================================================
# TAB 3: PREVIEW & HAPUS (v2 — Edit Inline + Multi-Select)
# =========================================================================
def render_preview():
    """Preview SO hari ini + edit inline + hapus per rak / massal."""
    st.markdown("### 📋 Preview & Edit SO")
    st.caption("Lihat, edit, dan hapus SO yang sudah diinput")

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

    # Simpan tanggal aktif ke session state (buat save handler)
    st.session_state["preview_active_date"] = _tanggal

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ============================================================
    # SUMMARY METRIC
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
    # SEARCH + FILTER
    # ============================================================
    st.markdown("#### 📊 Summary per Rak")
    st.caption("Centang **Pilih** untuk multi-select, edit langsung di tabel")

    _col_search, _col_pic_filter = st.columns([3, 2])

    with _col_search:
        _search_preview = st.text_input(
            "🔍 Cari Rak",
            key="search_preview_rak",
            placeholder="Ketik kode rak...",
            label_visibility="collapsed",
        )

    with _col_pic_filter:
        _pic_options = ["(Semua)"] + sorted(set(
            str(r.get("pic", "")).strip().upper()
            for r in _so_summary
            if r.get("pic")
        ))
        _pic_filter = st.selectbox(
            "👤 Filter PIC",
            options=_pic_options,
            key="preview_pic_filter",
            label_visibility="collapsed",
        )

    # Filter summary
    _so_summary_filtered = _so_summary

    if _search_preview and len(_search_preview.strip()) >= 1:
        _q = _search_preview.strip().upper()
        _so_summary_filtered = [
            r for r in _so_summary_filtered
            if _q in str(r.get("rak_id", "")).upper()
        ]

    if _pic_filter != "(Semua)":
        _so_summary_filtered = [
            r for r in _so_summary_filtered
            if str(r.get("pic", "")).strip().upper() == _pic_filter
        ]

    # ============================================================
    # TABEL EDITABLE (st.data_editor) — dengan checkbox
    # ============================================================
    if not _so_summary_filtered:
        st.info(f"📭 Tidak ada rak yang match dengan filter")
    else:
        # Build DataFrame buat data_editor
        _editor_data = []
        for _r in _so_summary_filtered:
            _editor_data.append({
                "Pilih": False,
                "Rak": _r.get("rak_id", "-"),
                "PIC": _r.get("pic", "") or "",
                "Nominal": float(_r.get("nominal_adjust", 0)),
                "Keterangan": _r.get("keterangan", "") or "",
            })

        _df_editor = pd.DataFrame(_editor_data)

        # Editable table
        _edited = st.data_editor(
            _df_editor,
            use_container_width=True,
            hide_index=True,
            height=min(400, 60 + len(_df_editor) * 40),
            column_config={
                "Pilih": st.column_config.CheckboxColumn(
                    "✅",
                    help="Centang untuk hapus massal",
                    default=False,
                    width="small",
                ),
                "Rak": st.column_config.TextColumn(
                    "Kode Rak",
                    disabled=True,
                    width="small",
                ),
                "PIC": st.column_config.SelectboxColumn(
                    "PIC",
                    options=_personil_list if _personil_list else ["-"],
                    required=False,
                    width="medium",
                ),
                "Nominal": st.column_config.NumberColumn(
                    "Nominal (Rp)",
                    format="%+d",
                    step=1000,
                    width="medium",
                ),
                "Keterangan": st.column_config.TextColumn(
                    "Keterangan",
                    max_chars=200,
                    width="large",
                ),
            },
            key=f"preview_editor_{_tanggal}",
        )

        # Detect perubahan
        _changes = _df_editor.compare(_edited)
        _has_changes = not _changes.empty

        # Cek apakah ada yang dicentang
        _selected_rows = _edited[_edited["Pilih"] == True]
        _count_selected = len(_selected_rows)

        st.markdown("")

        # Tombol aksi
        _col_save, _col_delete, _col_info2 = st.columns([2, 2, 2])

        with _col_save:
            _save_disabled = not _has_changes
            if st.button(
                "💾 SIMPAN PERUBAHAN",
                key="btn_save_changes_preview",
                width="stretch",
                type="primary",
                disabled=_save_disabled,
            ):
                with st.spinner("⏳ Menyimpan perubahan..."):
                    _saved_count = 0
                    _error_count = 0

                    for _, _row in _edited.iterrows():
                        _rak_id = _row["Rak"]

                        # Cari data asli
                        _original = next(
                            (r for r in _so_summary if str(r.get("rak_id")) == str(_rak_id)),
                            None,
                        )
                        if not _original:
                            continue

                        _new_pic = str(_row["PIC"]).strip().upper() if _row["PIC"] else ""
                        _new_nominal = float(_row["Nominal"])
                        _new_keterangan = str(_row["Keterangan"]).strip() if _row["Keterangan"] else ""

                        _old_pic = str(_original.get("pic", "")).strip().upper()
                        _old_nominal = float(_original.get("nominal_adjust", 0))
                        _old_keterangan = str(_original.get("keterangan", "")).strip()

                        # Skip kalau gak ada perubahan
                        if (_new_pic == _old_pic and
                            _new_nominal == _old_nominal and
                            _new_keterangan == _old_keterangan):
                            continue

                        # Update ke Supabase
                        try:
                            from modules.supabase_client import get_supabase
                            _sb = get_supabase()

                            _update_data = {
                                "pic": _new_pic,
                                "nominal_adjust": _new_nominal,
                                "keterangan": _new_keterangan,
                                "updated_at": datetime.now(ZoneInfo("Asia/Jakarta")).isoformat(),
                            }

                            _res = _sb.table("so_rak_harian") \
                                .update(_update_data) \
                                .eq("so_date", _tanggal.isoformat()) \
                                .eq("rak_id", _rak_id) \
                                .execute()

                            if _res.data:
                                _saved_count += 1
                            else:
                                _error_count += 1
                        except Exception as _e_upd:
                            print(f"[UPDATE ERROR] {_rak_id}: {_e_upd}")
                            _error_count += 1

                    if _saved_count > 0:
                        st.success(f"✅ {_saved_count} perubahan tersimpan!")
                        if _error_count > 0:
                            st.warning(f"⚠️ {_error_count} gagal update")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.info("ℹ️ Tidak ada perubahan tersimpan")

        with _col_delete:
            if st.button(
                f"🗑️ HAPUS TERPILIH ({_count_selected})",
                key="btn_delete_selected",
                width="stretch",
                disabled=(_count_selected == 0),
            ):
                if _count_selected > 0:
                    st.session_state["confirm_delete_rak_list"] = _selected_rows["Rak"].tolist()
                    st.rerun()

        with _col_info2:
            if _has_changes:
                st.markdown(
                    f"<div style='padding-top: 10px; font-family: JetBrains Mono, monospace; "
                    f"font-size: 11px; color: #FBBF24; text-align: right;'>"
                    f"⚠️ Ada perubahan belum disimpan</div>",
                    unsafe_allow_html=True,
                )
            elif _count_selected > 0:
                st.markdown(
                    f"<div style='padding-top: 10px; font-family: JetBrains Mono, monospace; "
                    f"font-size: 11px; color: #E88B8B; text-align: right;'>"
                    f"🗑️ {_count_selected} rak siap dihapus</div>",
                    unsafe_allow_html=True,
                )

    # ============================================================
    # KONFIRMASI HAPUS MASSAL
    # ============================================================
    if st.session_state.get("confirm_delete_rak_list"):
        _rak_to_delete = st.session_state["confirm_delete_rak_list"]

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        st.warning(
            f"⚠️ **Konfirmasi Hapus Massal**\n\n"
            f"Kamu akan menghapus **{len(_rak_to_delete)} rak**:\n\n"
            f"`{', '.join(_rak_to_delete)}`\n\n"
            f"Tindakan ini tidak bisa dibatalkan."
        )

        _col_confirm_yes, _col_confirm_no = st.columns(2)

        with _col_confirm_yes:
            if st.button(
                f"✅ YA, HAPUS {len(_rak_to_delete)} RAK",
                key="btn_confirm_delete_yes",
                width="stretch",
                type="primary",
            ):
                with st.spinner("⏳ Menghapus..."):
                    _deleted_count = 0
                    _error_count = 0

                    for _rak_id in _rak_to_delete:
                        try:
                            _ok, _msg, _detail = delete_so_by_date(
                                _tanggal,
                                rak_id=_rak_id,
                            )
                            if _ok:
                                _deleted_count += 1
                            else:
                                _error_count += 1
                        except Exception as _e_del:
                            print(f"[DELETE ERROR] {_rak_id}: {_e_del}")
                            _error_count += 1

                    st.session_state["confirm_delete_rak_list"] = None

                    if _deleted_count > 0:
                        st.success(f"✅ {_deleted_count} rak dihapus!")
                        if _error_count > 0:
                            st.warning(f"⚠️ {_error_count} gagal dihapus")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Gagal hapus semua rak")

        with _col_confirm_no:
            if st.button(
                "❌ BATAL",
                key="btn_confirm_delete_no",
                width="stretch",
            ):
                st.session_state["confirm_delete_rak_list"] = None
                st.rerun()

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
    # HAPUS SO PER RAK (Single — cara lama, buat fallback)
    # ============================================================
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    with st.expander("🗑️ Hapus SO per Rak (Single)", expanded=False):
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