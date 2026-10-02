"""
Dashboard Stock Opname — File Utama
====================================
Toko C383 - Karang Satria
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
    from modules.data_loader import (
        load_rak_master,
        load_so_hasil,
        load_net_sales,
    )
    from modules.rak_monitor import (
        hitung_progress_so,
        get_rak_belum_so,
    )
except ImportError as e:
    st.error(f"❌ Gagal import modul: {e}")
    st.stop()

# =========================================================================
# CUSTOM CSS (Simple dulu)
# =========================================================================
st.markdown("""
<style>
    .main {
        background-color: #0f172a;
    }
    .stApp {
        background-color: #0f172a;
    }
    h1, h2, h3 {
        color: #fbbf24;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.85));
        border: 1.5px solid #b45309;
        border-left: 5px solid #fbbf24;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .metric-label {
        font-family: monospace;
        font-size: 11px;
        color: #94a3b8;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .metric-value {
        font-family: monospace;
        font-size: 24px;
        font-weight: 900;
        color: #fbbf24;
        text-shadow: 0 0 10px rgba(251, 191, 36, 0.4);
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
# LOAD DATA
# =========================================================================
with st.spinner("⏳ Memuat data..."):
    rak_df = load_rak_master()
    so_df = load_so_hasil()
    net_sales_df = load_net_sales()

# =========================================================================
# METRIC UTAMA
# =========================================================================
if not rak_df.empty:
    progress = hitung_progress_so(rak_df, so_df)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    with col_m1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>📦 Total Rak</div>
            <div class='metric-value'>{progress['total_rak']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m2:
        st.markdown(f"""
        <div class='metric-card' style='border-left-color: #34d399;'>
            <div class='metric-label'>✅ Sudah SO</div>
            <div class='metric-value' style='color: #34d399;'>{progress['rak_selesai']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m3:
        st.markdown(f"""
        <div class='metric-card' style='border-left-color: #fca5a5;'>
            <div class='metric-label'>❌ Belum SO</div>
            <div class='metric-value' style='color: #fca5a5;'>{progress['rak_belum']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m4:
        _status_color = "#34d399" if progress['persen_selesai'] >= 80 else "#fbbf24"
        st.markdown(f"""
        <div class='metric-card' style='border-left-color: {_status_color};'>
            <div class='metric-label'>🎯 Progres</div>
            <div class='metric-value' style='color: {_status_color};'>{progress['persen_selesai']:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # =========================================================
    # TABEL RAK
    # =========================================================
    st.markdown("### 📋 Daftar Rak")

    _filter = st.selectbox(
        "🔍 Filter Status",
        ["Semua", "✅ Sudah SO", "❌ Belum SO"],
        key="filter_status_rak"
    )

    _rak_show = rak_df.copy()
    if _filter == "✅ Sudah SO":
        _rak_show = _rak_show[_rak_show["status_so"] == "SELESAI"]
    elif _filter == "❌ Belum SO":
        _rak_show = _rak_show[_rak_show["status_so"] == "BELUM"]

    st.dataframe(
        _rak_show[["rak_id", "rak_name", "kategori", "pic", "status_so", "last_so_date"]],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"📊 Menampilkan **{len(_rak_show)}** dari **{len(rak_df)}** rak")

else:
    st.warning("⚠️ Belum ada data rak. Pastikan `data/rak_master.csv` sudah diisi.")

# =========================================================================
# FOOTER
# =========================================================================
st.markdown("---")
_waktu = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d/%m/%Y %H:%M:%S WIB")
st.caption(f"🕐 {_waktu} | Dashboard Stock Opname v1.0")
