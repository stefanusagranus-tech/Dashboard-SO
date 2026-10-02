"""
Dashboard Stock Opname — File Utama
====================================
Toko C383 - Karang Satria

Iterasi 1: "Hello 144 Rak"
- Load data rak dari Supabase
- Tampilkan metric cards (Total, Sudah SO, Belum SO, Progres)
- Tabel daftar rak + filter
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================================================================
# KONFIGURASI HALAMAN
# =========================================================================
st.set_page_config(
    page_title="Dashboard Stock Opname",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================================
# IMPORT MODULES
# =========================================================================
try:
    from modules.supabase_client import get_supabase
    from modules.data_loader import (
        load_rak_master,
        load_so_hasil,
        load_net_sales,
        clear_cache,
    )
    from modules.rak_monitor import hitung_progress_so
except ImportError as e:
    st.error(f"❌ Gagal import modul: {e}")
    st.info("💡 Pastikan semua file di folder `modules/` sudah di-upload.")
    st.stop()

# =========================================================================
# CUSTOM CSS
# =========================================================================
st.markdown("""
<style>
    .stApp {
        background-color: #0f172a;
    }
    .main {
        background-color: #0f172a;
    }
    h1, h2, h3, h4 {
        color: #fbbf24 !important;
    }
    p, span, div {
        color: #e2e8f0;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.85));
        border: 1.5px solid #9a7b38;
        border-left: 5px solid #fbbf24;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    .metric-label {
        font-family: monospace;
        font-size: 11px;
        color: #94a3b8;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-value {
        font-family: monospace;
        font-size: 26px;
        font-weight: 900;
        color: #fbbf24;
        text-shadow: 0 0 10px rgba(251, 191, 36, 0.4);
        word-wrap: break-word;
    }
    .metric-sub {
        font-family: monospace;
        font-size: 10px;
        color: #64748b;
        margin-top: 4px;
    }
    div[data-testid="stDataFrame"] {
        border: 1.5px solid #9a7b38 !important;
        border-radius: 10px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #0f172a !important;
        border: 1.5px solid #9a7b38 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] span {
        color: #fbbf24 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# HEADER
# =========================================================================
st.markdown("""
<div style='
    background: radial-gradient(circle, #1e3a5f 0%, #0f172a 100%);
    border: 2px solid #b45309;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 0 25px rgba(180, 83, 9, 0.35);
    position: relative;
'>
    <div style='
        font-family: monospace;
        font-size: 24px;
        font-weight: 900;
        color: #fbbf24;
        letter-spacing: 2px;
        text-shadow: 0 0 15px rgba(251, 191, 36, 0.6);
    '>📊 DASHBOARD STOCK OPNAME 📊</div>
    <div style='
        font-family: monospace;
        font-size: 12px;
        color: #94a3b8;
        letter-spacing: 1px;
        margin-top: 4px;
    '>Toko C383 - Karang Satria</div>
</div>
""", unsafe_allow_html=True)

# =========================================================================
# SIDEBAR
# =========================================================================
with st.sidebar:
    st.markdown("### ⚙️ Menu")
    
    if st.button("🔄 Refresh Data", use_container_width=True, key="btn_refresh"):
        clear_cache()
        st.cache_data.clear()
        st.toast("✅ Cache dibersihkan! Data akan dimuat ulang...", icon="🔄")
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Info")
    
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    st.caption(f"🕐 {_now.strftime('%d/%m/%Y %H:%M')} WIB")
    st.caption(f"📅 Bulan: {_now.strftime('%B %Y')}")
    
    st.markdown("---")
    st.caption("💡 Dashboard SO v1.0")

# =========================================================================
# LOAD DATA
# =========================================================================
with st.spinner("⏳ Memuat data dari Supabase..."):
    rak_df = load_rak_master()
    so_df = load_so_hasil()
    net_sales_df = load_net_sales()

# =========================================================================
# CEK DATA KOSONG
# =========================================================================
if rak_df.empty:
    st.error("❌ **Data rak kosong!**")
    st.markdown("""
    **Kemungkinan penyebab:**
    1. Tabel `rak_master` belum di-import datanya
    2. Credential Supabase di `.streamlit/secrets.toml` salah
    3. Row Level Security (RLS) memblokir akses
    
    **Solusi:**
    - Buka Supabase → Table Editor → cek `rak_master` ada 144 baris
    - Cek `.streamlit/secrets.toml` ada `[supabase]` dengan `url` dan `key`
    - Kalau RLS aktif: buka Supabase → Authentication → Policies → disable RLS sementara
    """)
    st.stop()

# =========================================================================
# METRIC CARDS
# =========================================================================
progress = hitung_progress_so(rak_df, so_df)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>📦 Total Rak</div>
        <div class='metric-value'>{progress['total_rak']}</div>
        <div class='metric-sub'>Rak terdaftar</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
    <div class='metric-card' style='border-left-color: #34d399;'>
        <div class='metric-label'>✅ Sudah SO</div>
        <div class='metric-value' style='color: #34d399;'>{progress['rak_selesai']}</div>
        <div class='metric-sub'>Rak selesai di-SO</div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class='metric-card' style='border-left-color: #fca5a5;'>
        <div class='metric-label'>❌ Belum SO</div>
        <div class='metric-value' style='color: #fca5a5;'>{progress['rak_belum']}</div>
        <div class='metric-sub'>Perlu di-SO</div>
    </div>
    """, unsafe_allow_html=True)

with col_m4:
    _persen = progress['persen_selesai']
    if _persen >= 80:
        _color = "#34d399"
        _status = "✅ TERCAPAI"
    elif _persen >= 64:
        _color = "#fbbf24"
        _status = "⚠️ MENDEKATI"
    else:
        _color = "#fca5a5"
        _status = "🔴 BELUM"
    
    st.markdown(f"""
    <div class='metric-card' style='border-left-color: {_color};'>
        <div class='metric-label'>🎯 Progres SO</div>
        <div class='metric-value' style='color: {_color};'>{_persen:.1f}%</div>
        <div class='metric-sub'>Target: 80% • {_status}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# =========================================================================
# FILTER & TABEL RAK
# =========================================================================
st.markdown("### 📋 Daftar Rak")

col_f1, col_f2, col_f3 = st.columns([2, 2, 1])

with col_f1:
    _filter_status = st.selectbox(
        "🔍 Filter Status SO",
        ["Semua", "✅ Sudah SO", "❌ Belum SO"],
        key="filter_status_rak"
    )

with col_f2:
    _kategori_list = ["Semua"] + sorted(rak_df["kategori"].dropna().unique().tolist())
    _filter_kategori = st.selectbox(
        "📂 Filter Kategori",
        _kategori_list,
        key="filter_kategori_rak"
    )

with col_f3:
    _search = st.text_input("🔍 Cari", placeholder="Kode/nama rak", key="search_rak")

# Apply filter
_rak_show = rak_df.copy()

if _filter_status == "✅ Sudah SO":
    _rak_show = _rak_show[_rak_show["status_so"] == "SELESAI"]
elif _filter_status == "❌ Belum SO":
    _rak_show = _rak_show[_rak_show["status_so"] == "BELUM"]

if _filter_kategori != "Semua":
    _rak_show = _rak_show[_rak_show["kategori"] == _filter_kategori]

if _search:
    _search_upper = _search.strip().upper()
    _rak_show = _rak_show[
        _rak_show["rak_id"].str.contains(_search_upper, na=False) |
        _rak_show["rak_name"].str.upper().str.contains(_search_upper, na=False)
    ]

# Tampilkan tabel
_cols_show = ["rak_id", "rak_name", "kategori", "pic", "status_so", "last_so_date"]
_cols_available = [c for c in _cols_show if c in _rak_show.columns]

st.dataframe(
    _rak_show[_cols_available],
    use_container_width=True,
    hide_index=True,
    height=500,
)

st.caption(
    f"📊 Menampilkan **{len(_rak_show)}** dari **{len(rak_df)}** rak"
)

# =========================================================================
# FOOTER
# =========================================================================
st.markdown("---")
_now_str = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d/%m/%Y %H:%M:%S WIB")
st.caption(f"🕐 {_now_str} | Dashboard Stock Opname v1.0 | Data dari Supabase")
