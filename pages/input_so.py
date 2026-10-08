"""
SO — Stock Opname (Konsolidasi)
================================
Halaman gabungan: Input SO + Analisis + Preview/Hapus.

Tab:
1. Input SO (SPD + Multi-Produk SO)
2. Analisis SO (Top produk, Grafik, Per kategori)
3. Preview & Hapus (SO hari ini)
"""

import streamlit as st
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

from themes.theme_loader import (
    render_theme, render_theme_animations, get_theme_by_month,
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
        save_so_input, load_so_detail_by_date, load_so_summary_by_date,
        delete_so_by_date, get_so_analytics,
    )
    from modules.master_shift_handler import load_personil_master
    from modules.data_loader import load_rak_master
    from modules.spd_calculator import save_spd_harian, hitung_btsb_harian
    from modules.input_handler import (
        save_input_harian, get_rak_by_kode_exact,
        get_so_rak_detail, search_rak,
    )
except ImportError as _e:
    st.error(f"❌ Gagal import module: {_e}")
    st.stop()

# =========================================================================
# CSS + HEADER (existing)
# =========================================================================
def inject_css():
    # ... (existing from input_so.py)
    pass

def render_header():
    # ... (existing)
    pass

inject_css()
render_header()

# =========================================================================
# SESSION STATE
# =========================================================================
if "so_tab" not in st.session_state:
    st.session_state["so_tab"] = "input"

if "so_produk_list" not in st.session_state:
    st.session_state["so_produk_list"] = []

# =========================================================================
# TAB NAVIGATION
# =========================================================================
_TABS = [
    ("input", "📝 Input SO"),
    ("analisis", "📊 Analisis"),
    ("preview", "📋 Preview & Hapus"),
]

_cols = st.columns(len(_TABS))
for _i, (_key, _label) in enumerate(_TABS):
    with _cols[_i]:
        _is_active = st.session_state["so_tab"] == _key
        if st.button(
            _label,
            key=f"so_tab_btn_{_key}",
            use_container_width=True,
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["so_tab"] = _key
            st.rerun()

st.markdown("---")

# =========================================================================
# TAB 1: INPUT SO (SPD + SO)
# =========================================================================
def render_input_so():
    st.markdown("### 📝 Input SO")
    
    # === BAGIAN A: INFO SO ===
    st.markdown("#### 📅 Info SO")
    
    _col_tgl, _col_rak, _col_pic = st.columns([2, 2, 2])
    
    with _col_tgl:
        _tanggal = st.date_input(
            "📅 Tanggal SO",
            value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
            key="so_tanggal",
        )
    
    with _col_rak:
        _rak_df = load_rak_master()
        _rak_list = _rak_df["rak_id"].tolist() if not _rak_df.empty else []
        _rak_pilih = st.selectbox("🏪 Kode Rak", options=_rak_list, key="so_rak") if _rak_list else None
    
    with _col_pic:
        _personil_df = load_personil_master(only_active=True)
        _personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []
        _pic_pilih = st.selectbox("👤 PIC", options=_personil_list, key="so_pic") if _personil_list else None
    
    st.markdown("---")
    
    # === BAGIAN B: SPD (opsional) ===
    st.markdown("#### 💰 SPD Hari Ini (Opsional)")
    _spd_val = st.number_input(
        "SPD (Rp)", min_value=0, step=100000, value=0,
        key="so_spd", help="Kosongkan / 0 kalau belum ada SPD hari ini"
    )
    
    if _spd_val > 0:
        _btsb = hitung_btsb_harian(_spd_val)
        st.success(f"💡 BTSB Otomatis: **Rp {_btsb:,.0f}**".replace(",", "."))
    
    st.markdown("---")
    
    # === BAGIAN C: INPUT PRODUK ===
    st.markdown("#### 📦 Input Produk (Multi-Produk)")
    st.caption("💡 Input 5 PLU tertinggi + 5 PLU terendah (max 10 produk per rak)")
    
    _col_btn_add, _col_info = st.columns([2, 5])
    with _col_btn_add:
        if st.button("➕ Tambah Produk", use_container_width=True, key="btn_add_produk"):
            if len(st.session_state["so_produk_list"]) >= 10:
                st.warning("⚠️ Max 10 produk per rak")
            else:
                st.session_state["so_produk_list"].append({
                    "plu": "", "nama_produk": "", "qty_sistem": 0,
                    "qty_fisik": 0, "nominal_adjust": 0,
                })
                st.rerun()
    
    with _col_info:
        _count = len(st.session_state["so_produk_list"])
        st.markdown(f"<div style='padding-top: 8px; color: #7FB99B; font-size: 12px;'>"
                    f"📊 **{_count} / 10** produk terinput</div>", unsafe_allow_html=True)
    
    # List produk (existing)
    if st.session_state["so_produk_list"]:
        _items_to_remove = []
        for _idx, _produk in enumerate(st.session_state["so_produk_list"]):
            with st.expander(f"📦 Produk #{_idx+1}: {_produk.get('nama_produk') or '(belum diisi)'}", expanded=True):
                # ... (existing input form)
                pass
        
        if _items_to_remove:
            for _i in sorted(_items_to_remove, reverse=True):
                st.session_state["so_produk_list"].pop(_i)
            st.rerun()
    
    # === BAGIAN D: KETERANGAN ===
    _keterangan = st.text_input("📝 Keterangan (opsional)", key="so_keterangan")
    
    # === BAGIAN E: SUMMARY + SIMPAN ===
    if st.session_state["so_produk_list"]:
        # ... (existing summary)
        
        if st.button("💾 SIMPAN SEMUA", use_container_width=True, type="primary", key="btn_save_all_so"):
            # ... (existing save logic — gabung SPD + SO)
            pass

# =========================================================================
# TAB 2: ANALISIS SO
# =========================================================================
def render_analisis_so():
    st.markdown("### 📊 Analisis SO")
    
    # Pilih periode
    _col_p1, _col_p2, _col_p3 = st.columns(3)
    with _col_p1:
        _tgl_start = st.date_input("📅 Dari", value=date.today().replace(day=1), key="analisis_start")
    with _col_p2:
        _tgl_end = st.date_input("📅 Sampai", value=date.today(), key="analisis_end")
    with _col_p3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Analisis", use_container_width=True, type="primary", key="btn_analisis"):
            st.session_state["analisis_loaded"] = True
    
    if st.session_state.get("analisis_loaded"):
        with st.spinner("⏳ Load analytics..."):
            _analytics = get_so_analytics(_tgl_start, _tgl_end)
        
        # Top produk minus
        st.markdown("#### 📉 Top 5 Produk Minus Terbesar")
        if _analytics["top_minus"]:
            _df_minus = pd.DataFrame(_analytics["top_minus"])
            st.dataframe(_df_minus, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Tidak ada produk minus")
        
        # Top produk plus
        st.markdown("#### 📈 Top 5 Produk Plus Terbesar")
        if _analytics["top_plus"]:
            _df_plus = pd.DataFrame(_analytics["top_plus"])
            st.dataframe(_df_plus, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Tidak ada produk plus")

# =========================================================================
# TAB 3: PREVIEW & HAPUS
# =========================================================================
def render_preview_hapus():
    st.markdown("### 📋 Preview & Hapus SO")
    
    _tanggal = st.date_input(
        "📅 Pilih Tanggal",
        value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
        key="preview_tanggal",
    )
    
    with st.spinner("⏳ Load SO..."):
        _so_summary = load_so_summary_by_date(_tanggal)
        _so_detail = load_so_detail_by_date(_tanggal)
    
    if not _so_summary:
        st.info(f"📭 Belum ada SO untuk **{_tanggal.strftime('%d/%m/%Y')}**")
        return
    
    # Summary
    _total_rak = len(_so_summary)
    _total_item = sum(int(r.get("total_item", 0)) for r in _so_summary)
    _total_nominal = sum(float(r.get("nominal_adjust", 0)) for r in _so_summary)
    
    _c1, _c2, _c3 = st.columns(3)
    _c1.metric("🏪 Total Rak", _total_rak)
    _c2.metric("📦 Total Item", _total_item)
    _c3.metric("💰 Total Nominal", f"Rp {_total_nominal:,.0f}".replace(",", "."))
    
    # Tabel summary
    _df_summary = pd.DataFrame(_so_summary)
    _cols_show = ["rak_id", "pic", "total_item", "total_qty_var", "nominal_adjust", "keterangan"]
    _cols_show = [c for c in _cols_show if c in _df_summary.columns]
    st.dataframe(_df_summary[_cols_show], use_container_width=True, hide_index=True)
    
    # Detail (expander)
    if _so_detail:
        with st.expander(f"🔍 Detail Produk ({len(_so_detail)} produk)", expanded=False):
            _df_detail = pd.DataFrame(_so_detail)
            st.dataframe(_df_detail, use_container_width=True, hide_index=True, height=400)
    
    # Hapus
    st.markdown("#### 🗑️ Hapus SO")
    _rak_list = [r.get("rak_id") for r in _so_summary if r.get("rak_id")]
    
    if _rak_list:
        _col_h1, _col_h2 = st.columns([3, 1])
        with _col_h1:
            _rak_hapus = st.selectbox("Pilih rak:", options=_rak_list, key="hapus_rak")
        with _col_h2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ HAPUS", use_container_width=True, key="btn_hapus_so"):
                _ok, _msg, _ = delete_so_by_date(_tanggal, rak_id=_rak_hapus)
                if _ok:
                    st.success(_msg)
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()

# =========================================================================
# ROUTING
# =========================================================================
_tab = st.session_state["so_tab"]

if _tab == "input":
    render_input_so()
elif _tab == "analisis":
    render_analisis_so()
elif _tab == "preview":
    render_preview_hapus()

# Footer
st.markdown(
    "<div style='text-align: center; padding: 20px 0; "
    "font-family: Quicksand, sans-serif; font-size: 10px; "
    "color: #7a9b8e; letter-spacing: 1px;'>"
    "📝 Stock Opname — Toko C383 🎀"
    "</div>",
    unsafe_allow_html=True,
)