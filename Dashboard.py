"""
Dashboard Stock Opname
======================
Toko C383 - Karang Satria

Dashboard monitoring SO dengan navigasi card-based.
Tema: Royal Gold Dashboard

Struktur:
- Halaman 1: Dashboard (default)
- Halaman 2: Input Harian (SPD + SO)
- Halaman 3: Analisis & Laporan
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# =========================================================================
# KONFIGURASI HALAMAN
# =========================================================================
st.set_page_config(
    page_title="Dashboard SO | Toko C383",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================================
# CUSTOM CSS — TEMA ROYAL GOLD
# =========================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700;900&display=swap');

    /* HIDE SIDEBAR & HEADER */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    .stDeployButton,
    #MainMenu,
    footer {
        display: none !important;
    }

    /* BACKGROUND */
    .stApp {
        background: 
            radial-gradient(circle at 20% 0%, #1e3a5f 0%, transparent 50%),
            radial-gradient(circle at 80% 100%, #78350f 0%, transparent 50%),
            linear-gradient(180deg, #0a0f1a 0%, #0f172a 50%, #05070c 100%);
        background-attachment: fixed;
        color: #e2e8f0;
        font-family: 'Quicksand', sans-serif;
    }

    .main .block-container {
        padding: 1rem 1.5rem 4rem 1.5rem !important;
        max-width: 1400px !important;
    }

    /* SCROLLBAR */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #0a0f1a; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #d4af37, #9a7b38);
        border-radius: 5px;
        border: 2px solid #0a0f1a;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #fbbf24, #d4af37);
    }

    /* TYPOGRAPHY */
    h1, h2, h3, h4 {
        font-family: 'Cinzel', serif !important;
        color: #fbbf24 !important;
        letter-spacing: 1.5px;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
    }
    p, span, div { color: #e2e8f0; }

    /* HEADER BANNER */
    .royal-header {
        position: relative;
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
        border: 3px double #d4af37;
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 0 40px rgba(212, 175, 55, 0.25), inset 0 0 30px rgba(0, 0, 0, 0.6);
        overflow: hidden;
    }
    .royal-header::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, #fbbf24 20%, #fef3c7 50%, #fbbf24 80%, transparent);
        box-shadow: 0 0 15px rgba(251, 191, 36, 0.8);
    }
    .royal-title {
        font-family: 'Cinzel', serif;
        font-size: 28px;
        font-weight: 900;
        color: #fbbf24;
        text-align: center;
        margin: 0;
        letter-spacing: 3px;
        text-shadow: 0 0 20px rgba(251, 191, 36, 0.6);
    }
    .royal-subtitle {
        font-family: 'Quicksand', sans-serif;
        font-size: 12px;
        color: #94a3b8;
        text-align: center;
        margin-top: 6px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .royal-ornament {
        position: absolute;
        color: #d4af37;
        font-size: 16px;
        opacity: 0.7;
        filter: drop-shadow(0 0 4px rgba(212, 175, 55, 0.7));
    }
    .royal-orn-tl { top: 8px; left: 12px; }
    .royal-orn-tr { top: 8px; right: 12px; }
    .royal-orn-bl { bottom: 8px; left: 12px; }
    .royal-orn-br { bottom: 8px; right: 12px; }

    /* METRIC CARD */
    .metric-card-v2 {
        position: relative;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.92));
        border: 2px solid #9a7b38;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        overflow: hidden;
        transition: all 0.3s ease;
    }
    .metric-card-v2::before {
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 5px; height: 100%;
        background: var(--accent-color, #fbbf24);
        box-shadow: 0 0 15px var(--accent-color, #fbbf24);
    }
    .metric-card-v2:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.6), 0 0 25px var(--accent-color, rgba(251, 191, 36, 0.3));
    }
    .metric-label-v2 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 700;
        color: #94a3b8;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value-v2 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 900;
        color: #fbbf24;
        text-shadow: 0 0 15px rgba(251, 191, 36, 0.5);
        line-height: 1.1;
        word-wrap: break-word;
    }
    .metric-sub-v2 {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: #64748b;
        margin-top: 6px;
        font-weight: 600;
    }

    /* MENU CARD */
    .menu-card-v2 {
        position: relative;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.92));
        border: 2px solid #9a7b38;
        border-radius: 16px;
        padding: 28px 20px;
        text-align: center;
        transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1);
        cursor: pointer;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        margin-bottom: 12px;
    }
    .menu-card-v2::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, var(--accent-color, #fbbf24), transparent);
        opacity: 0.6;
    }
    .menu-card-v2:hover {
        border-color: var(--accent-color, #fbbf24);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6), 0 0 30px var(--accent-glow, rgba(251, 191, 36, 0.4));
        transform: translateY(-6px) scale(1.02);
    }
    .menu-card-v2:hover::before { opacity: 1; }
    .menu-icon-v2 {
        font-size: 56px;
        margin-bottom: 14px;
        filter: drop-shadow(0 0 15px var(--accent-glow, rgba(251, 191, 36, 0.6)));
        transition: transform 0.3s ease;
    }
    .menu-card-v2:hover .menu-icon-v2 {
        transform: scale(1.1) rotate(-5deg);
    }
    .menu-title-v2 {
        font-family: 'Cinzel', serif;
        font-size: 15px;
        font-weight: 900;
        color: #fbbf24;
        letter-spacing: 2px;
        margin-bottom: 6px;
        text-transform: uppercase;
    }
    .menu-desc-v2 {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: #94a3b8;
        line-height: 1.5;
        font-weight: 500;
    }

    /* BUTTON */
    div.stButton > button {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        color: #fbbf24 !important;
        border: 2px solid #b45309 !important;
        border-radius: 10px !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        padding: 10px 16px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
        width: 100% !important;
        min-height: 44px !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #b45309 0%, #d97706 100%) !important;
        color: #ffffff !important;
        border-color: #fbbf24 !important;
        box-shadow: 0 0 20px rgba(251, 191, 36, 0.6) !important;
        transform: translateY(-2px) !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #b45309 0%, #d97706 100%) !important;
        color: #ffffff !important;
        border-color: #fbbf24 !important;
    }

    /* FORM SUBMIT BUTTON */
    div.stFormSubmitButton > button {
        background: linear-gradient(135deg, #b45309 0%, #d97706 100%) !important;
        color: #ffffff !important;
        border: 2px solid #fbbf24 !important;
        border-radius: 12px !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 900 !important;
        font-size: 14px !important;
        padding: 14px 20px !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        box-shadow: 0 6px 20px rgba(180, 83, 9, 0.5) !important;
        min-height: 54px !important;
    }
    div.stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #d97706 0%, #fbbf24 100%) !important;
        color: #0f172a !important;
        box-shadow: 0 8px 30px rgba(251, 191, 36, 0.7) !important;
        transform: translateY(-2px) !important;
    }

    /* DATAFRAME */
    div[data-testid="stDataFrame"] {
        border: 2px solid #9a7b38 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.5) !important;
    }

    /* INPUT & SELECTBOX */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border: 2px solid #9a7b38 !important;
        border-radius: 10px !important;
        min-height: 44px !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span {
        color: #fbbf24 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
    }
    label, div[data-testid="stWidgetLabel"] label {
        color: #94a3b8 !important;
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    /* DIVIDER */
    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, #d4af37 50%, transparent) !important;
        margin: 24px 0 !important;
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.5) !important;
    }

    /* ALERT / INFO / WARNING */
    div[data-testid="stAlert"] {
        background: rgba(15, 23, 42, 0.95) !important;
        border: 2px solid #9a7b38 !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
    }

    /* ANIMASI */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in-up { animation: fadeInUp 0.6s ease-out forwards; }

    /* MOBILE */
    @media (max-width: 768px) {
        .royal-title { font-size: 18px; letter-spacing: 1.5px; }
        .royal-subtitle { font-size: 9px; letter-spacing: 1px; }
        .royal-header { padding: 16px 20px; }
        .metric-value-v2 { font-size: 22px; }
        .metric-label-v2 { font-size: 9px; }
        .menu-card-v2 { min-height: 160px; padding: 20px 16px; }
        .menu-icon-v2 { font-size: 42px; }
        .menu-title-v2 { font-size: 13px; }
        .menu-desc-v2 { font-size: 9px; }
        .main .block-container { padding: 0.5rem 1rem 3rem 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# SESSION STATE — ROUTING
# =========================================================================
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "dashboard"

if "so_items_temp" not in st.session_state:
    st.session_state["so_items_temp"] = []

# =========================================================================
# IMPORT MODULES
# =========================================================================
try:
    from modules.data_loader import load_rak_master, load_so_hasil, clear_cache
    from modules.rak_monitor import hitung_progress_so
    from modules.spd_calculator import (
        load_spd_harian, save_spd_harian,
        hitung_btsb_harian, hitung_btsb_akumulatif,
        analisis_btsb_vs_selisih,
    )
    from modules.input_handler import (
        save_input_harian, get_spd_hari_ini,
        get_rak_belum_so, get_so_hari_ini,
    )
except ImportError as e:
    st.error(f"❌ Gagal import modul: {e}")
    st.info("💡 Pastikan semua file di folder `modules/` sudah di-upload:")
    st.code("""
modules/
├── __init__.py
├── supabase_client.py
├── data_loader.py
├── rak_monitor.py
├── spd_calculator.py
└── input_handler.py   ← baru
    """)
    st.stop()

# =========================================================================
# HELPER FUNCTIONS
# =========================================================================
def render_royal_header():
    """Render header banner royal."""
    st.markdown("""
    <div class='royal-header fade-in-up'>
        <div class='royal-ornament royal-orn-tl'>⚜</div>
        <div class='royal-ornament royal-orn-tr'>⚜</div>
        <div class='royal-ornament royal-orn-bl'>⚜</div>
        <div class='royal-ornament royal-orn-br'>⚜</div>
        <div class='royal-title'>DASHBOARD STOCK OPNAME</div>
        <div class='royal-subtitle'>⚜ Toko C383 - Karang Satria ⚜</div>
    </div>
    """, unsafe_allow_html=True)


def render_back_button(label="← Kembali ke Dashboard", target="dashboard"):
    """Render tombol kembali."""
    if st.button(label, key=f"btn_back_{target}_{id(label)}"):
        st.session_state["current_page"] = target
        st.rerun()


def render_metric_card(label, value, sub_text="", accent="#fbbf24", icon=""):
    """Render metric card dengan custom style."""
    st.markdown(f"""
    <div class='metric-card-v2 fade-in-up' style='--accent-color: {accent};'>
        <div class='metric-label-v2'>{icon} {label}</div>
        <div class='metric-value-v2' style='color: {accent};'>{value}</div>
        <div class='metric-sub-v2'>{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_menu_card(icon, title, desc, accent, accent_glow, key, target_page):
    """Render menu card + tombol masuk."""
    st.markdown(f"""
    <div class='menu-card-v2' style='--accent-color: {accent}; --accent-glow: {accent_glow};'>
        <div class='menu-icon-v2'>{icon}</div>
        <div class='menu-title-v2'>{title}</div>
        <div class='menu-desc-v2'>{desc}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Masuk →", key=key, use_container_width=True):
        st.session_state["current_page"] = target_page
        st.rerun()


def fmt_rp(value):
    """Format angka jadi Rupiah."""
    try:
        return f"Rp {int(value):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp_short(value):
    """Format angka jadi Rupiah singkat (Jt/M)."""
    try:
        _v = float(value)
        if abs(_v) >= 1_000_000_000:
            return f"Rp {_v/1_000_000_000:.1f}M"
        elif abs(_v) >= 1_000_000:
            return f"Rp {_v/1_000_000:.1f}Jt"
        elif abs(_v) >= 1_000:
            return f"Rp {_v/1_000:.0f}K"
        return f"Rp {int(_v):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"


# =========================================================================
# 🏠 HALAMAN 1: DASHBOARD
# =========================================================================
def render_dashboard():
    """Render halaman dashboard utama."""
    render_royal_header()
    
    # ============================================================
    # LOAD DATA
    # ============================================================
    with st.spinner("⏳ Memuat data..."):
        rak_df = load_rak_master()
        so_df = load_so_hasil()
    
    if rak_df.empty:
        st.error("❌ **Data rak kosong!**")
        st.info("💡 Pastikan tabel `rak_master` di Supabase sudah di-import.")
        return
    
    # ============================================================
    # METRIC CARDS — 4 KARTU
    # ============================================================
    progress = hitung_progress_so(rak_df, so_df)
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        render_metric_card(
            label="Total Rak",
            value=f"{progress['total_rak']}",
            sub_text="Rak terdaftar",
            accent="#fbbf24",
            icon="📦"
        )
    
    with col_m2:
        render_metric_card(
            label="Sudah SO",
            value=f"{progress['rak_selesai']}",
            sub_text="Rak selesai",
            accent="#34d399",
            icon="✅"
        )
    
    with col_m3:
        render_metric_card(
            label="Belum SO",
            value=f"{progress['rak_belum']}",
            sub_text="Perlu di-SO",
            accent="#fca5a5",
            icon="❌"
        )
    
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
        
        render_metric_card(
            label="Progres SO",
            value=f"{_persen:.1f}%",
            sub_text=f"Target: 80% • {_status}",
            accent=_color,
            icon="🎯"
        )
    
    st.markdown("---")
    
    # ============================================================
    # SUMMARY SPD & BTSB
    # ============================================================
    st.markdown("### 💰 Summary SPD & BTSB")
    
    _btsb_result = hitung_btsb_akumulatif()
    _total_spd = _btsb_result["total_spd"]
    _btsb_akum = _btsb_result["btsb_akumulatif"]
    _jumlah_hari = _btsb_result["jumlah_hari"]
    
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        render_metric_card(
            label="Total SPD Bulan Ini",
            value=fmt_rp_short(_total_spd),
            sub_text=f"{_jumlah_hari} hari terinput",
            accent="#38bdf8",
            icon="📅"
        )
    
    with col_s2:
        render_metric_card(
            label="BTSB Akumulatif",
            value=fmt_rp_short(_btsb_akum),
            sub_text="0,15% × Total SPD",
            accent="#06b6d4",
            icon="🎯"
        )
    
    with col_s3:
        # Total selisih dari SO
        _total_selisih = 0
        if not so_df.empty and "selisih" in so_df.columns:
            _total_selisih = int(pd.to_numeric(so_df["selisih"], errors="coerce").fillna(0).sum())
        
        _analisis = analisis_btsb_vs_selisih(_total_selisih, _btsb_akum)
        
        render_metric_card(
            label="Selisih SO",
            value=fmt_rp_short(_total_selisih),
            sub_text=f"{_analisis['icon']} {_analisis['status']} • {_analisis['persen_penggunaan']:.1f}%",
            accent=_analisis['warna'],
            icon="⚖️"
        )
    
    st.markdown("---")
    
    # ============================================================
    # MENU CARD — 3 KARTU UTAMA
    # ============================================================
    st.markdown("### 📋 Pilih Menu")
    
    col_menu1, col_menu2 = st.columns(2)
    
    with col_menu1:
        render_menu_card(
            icon="📝",
            title="Input Harian",
            desc="Input SPD & SO<br>dalam 1 form",
            accent="#38bdf8",
            accent_glow="rgba(56, 189, 248, 0.6)",
            key="btn_menu_input",
            target_page="input_harian"
        )
    
    with col_menu2:
        render_menu_card(
            icon="📊",
            title="Analisis",
            desc="BTSB, selisih<br>& top item minus",
            accent="#a855f7",
            accent_glow="rgba(168, 85, 247, 0.6)",
            key="btn_menu_analisis",
            target_page="analisis"
        )
    
    col_menu3, col_menu4 = st.columns(2)
    
    with col_menu3:
        render_menu_card(
            icon="📥",
            title="Download Laporan",
            desc="Export Excel<br>& PDF laporan",
            accent="#fbbf24",
            accent_glow="rgba(251, 191, 36, 0.6)",
            key="btn_menu_download",
            target_page="download"
        )
    
    with col_menu4:
        render_menu_card(
            icon="🔄",
            title="Refresh Data",
            desc="Muat ulang data<br>dari Supabase",
            accent="#34d399",
            accent_glow="rgba(52, 211, 153, 0.6)",
            key="btn_menu_refresh",
            target_page="refresh"
        )
    
    # Footer
    st.markdown("---")
    _now_str = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d/%m/%Y %H:%M:%S WIB")
    st.caption(f"🕐 {_now_str} | Dashboard SO v1.0 | Data dari Supabase")


# =========================================================================
# 📝 HALAMAN 2: INPUT HARIAN (SPD + SO)
# =========================================================================
def render_input_harian():
    """Render halaman input harian: SPD + SO."""
    render_royal_header()
    
    # Back button
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_input"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
    
    st.markdown("### 📝 Input Harian")
    st.caption("Input SPD dan SO dalam 1 form — hemat waktu!")
    
    # ============================================================
    # LOAD DATA
    # ============================================================
    rak_df = load_rak_master()
    
    if rak_df.empty:
        st.error("❌ Data rak kosong. Pastikan tabel `rak_master` sudah di-import.")
        return
    
    # ============================================================
    # FORM INPUT
    # ============================================================
    with st.form("form_input_harian", clear_on_submit=False):
        
        # ---------- TANGGAL ----------
        st.markdown("#### 📅 Tanggal Input")
        _today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
        _tanggal = st.date_input(
            "Pilih Tanggal",
            value=_today,
            key="input_tanggal",
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # ---------- SPD ----------
        st.markdown("#### 💰 Sales Per Day (SPD)")
        
        # Cek SPD existing
        _spd_existing = 0
        _df_spd = load_spd_harian()
        if not _df_spd.empty:
            _match = _df_spd[_df_spd["tanggal"] == _tanggal]
            if not _match.empty:
                _spd_existing = int(_match.iloc[0]["spd"])
        
        col_spd1, col_spd2 = st.columns([2, 1])
        with col_spd1:
            _spd_val = st.number_input(
                "SPD Hari Ini (Rp)",
                min_value=0,
                step=100000,
                value=_spd_existing,
                key="input_spd_val",
                help="Total penjualan hari ini"
            )
        with col_spd2:
            st.markdown("<br>", unsafe_allow_html=True)
            if _spd_val > 0:
                _btsb_harian = hitung_btsb_harian(_spd_val)
                st.success(f"BTSB: {fmt_rp(_btsb_harian)}")
            else:
                st.info("BTSB: -")
        
        st.markdown("---")
        
        # ---------- SO ----------
        st.markdown("#### 📦 Stock Opname (Opsional)")
        st.caption("Kalau ada SO hari ini, isi di bawah. Kalau tidak, kosongkan.")
        
        # Dropdown rak (hanya yang BELUM SO)
        _rak_belum = get_rak_belum_so()
        _rak_options = ["-- Tidak Ada SO --"] + _rak_belum
        
        _selected_rak_opt = st.selectbox(
            "🎯 Pilih Rak yang Di-SO",
            options=_rak_options,
            key="input_rak_select"
        )
        
        _selected_rak_id = None
        if _selected_rak_opt != "-- Tidak Ada SO --":
            _selected_rak_id = _selected_rak_opt.split(" — ")[0].strip()
        
        # Kalau ada rak dipilih, tampilkan input items
        _so_items = []
        
        if _selected_rak_id:
            st.markdown(f"##### 📋 Item SO untuk Rak `{_selected_rak_id}`")
            
            # Info jumlah items
            _num_items = st.number_input(
                "Jumlah Item yang Di-SO",
                min_value=1,
                max_value=50,
                value=1,
                step=1,
                key="input_num_items"
            )
            
            st.caption("💡 Isi PLU, nama item, qty system, qty actual, dan harga")
            
            for _i in range(int(_num_items)):
                st.markdown(f"**Item #{_i+1}**")
                col_i1, col_i2 = st.columns(2)
                
                with col_i1:
                    _plu = st.text_input(
                        f"PLU #{_i+1}",
                        key=f"input_plu_{_i}",
                        placeholder="Contoh: 100234"
                    )
                    _nama_item = st.text_input(
                        f"Nama Item #{_i+1}",
                        key=f"input_nama_{_i}",
                        placeholder="Contoh: AQUA 600ML"
                    )
                
                with col_i2:
                    _qty_sys = st.number_input(
                        f"Qty System #{_i+1}",
                        min_value=0,
                        step=1,
                        value=0,
                        key=f"input_qsys_{_i}"
                    )
                    _qty_act = st.number_input(
                        f"Qty Actual #{_i+1}",
                        min_value=0,
                        step=1,
                        value=0,
                        key=f"input_qact_{_i}"
                    )
                
                _harga = st.number_input(
                    f"Harga Satuan #{_i+1} (Rp)",
                    min_value=0,
                    step=100,
                    value=0,
                    key=f"input_harga_{_i}"
                )
                
                # Hitung selisih preview
                _selisih = int(_qty_act) - int(_qty_sys)
                if _selisih != 0:
                    _selisih_color = "#fca5a5" if _selisih < 0 else "#34d399"
                    st.markdown(
                        f"<div style='text-align: right; font-family: monospace; "
                        f"font-size: 12px; color: {_selisih_color}; font-weight: 900;'>"
                        f"Selisih: {_selisih:+d}</div>",
                        unsafe_allow_html=True
                    )
                
                _so_items.append({
                    "plu": _plu,
                    "item_name": _nama_item,
                    "qty_system": int(_qty_sys),
                    "qty_actual": int(_qty_act),
                    "harga": float(_harga),
                })
                
                if _i < int(_num_items) - 1:
                    st.markdown("---")
        
        st.markdown("---")
        
        # ---------- KETERANGAN ----------
        st.markdown("#### 📝 Keterangan (Opsional)")
        _keterangan = st.text_area(
            "Catatan",
            key="input_keterangan",
            placeholder="Contoh: Ada event promo, barang rusak, dll",
            height=80,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # ---------- SUBMIT ----------
        _btn_submit = st.form_submit_button(
            "💾 SIMPAN SEMUA",
            use_container_width=True,
            type="primary"
        )
    
    # ============================================================
    # PROSES SIMPAN
    # ============================================================
    if _btn_submit:
        # Validasi
        if _spd_val <= 0 and _selected_rak_id is None:
            st.error("⚠️ Minimal isi SPD atau pilih rak untuk SO!")
            return
        
        with st.spinner("⏳ Menyimpan data..."):
            # Kalau rak dipilih tapi ada item kosong, filter
            _items_valid = []
            if _selected_rak_id and _so_items:
                _items_valid = [
                    it for it in _so_items
                    if it["plu"] or it["item_name"]
                ]
            
            _ok, _msg, _detail = save_input_harian(
                tanggal=_tanggal,
                spd=_spd_val,
                rak_id=_selected_rak_id,
                items_so=_items_valid,
                keterangan=_keterangan,
                update_status_rak=True,
            )
        
        if _ok:
            st.success(_msg)
            st.balloons()
            
            # Detail
            with st.expander("📊 Detail Tersimpan", expanded=True):
                st.write(f"- 💰 SPD: {fmt_rp(_spd_val)}")
                if _selected_rak_id:
                    st.write(f"- 📦 Rak: {_selected_rak_id}")
                    st.write(f"- 📋 Jumlah Item: {_detail.get('total_so_items', 0)}")
                    st.write(f"- ⚖️ Total Selisih: {_detail.get('total_selisih', 0):+d}")
            
            # Clear cache & refresh
            st.cache_data.clear()
            time.sleep(2)
            st.rerun()
        else:
            st.error(_msg)
    
    # ============================================================
    # PREVIEW SO HARI INI
    # ============================================================
    st.markdown("---")
    st.markdown("### 📋 Preview SO Hari Ini")
    
    _so_today = get_so_hari_ini()
    if _so_today:
        _so_today_df = pd.DataFrame(_so_today)
        _cols_show = ["rak_id", "plu", "item_name", "qty_system", "qty_actual", "selisih"]
        _cols_show = [c for c in _cols_show if c in _so_today_df.columns]
        st.dataframe(_so_today_df[_cols_show], use_container_width=True, hide_index=True)
        
        _total_selisih_today = int(pd.to_numeric(_so_today_df["selisih"], errors="coerce").fillna(0).sum())
        st.caption(f"📊 Total {len(_so_today)} item di-SO hari ini | Selisih: {_total_selisih_today:+d}")
    else:
        st.info("📭 Belum ada SO hari ini")


# =========================================================================
# 📊 HALAMAN 3: ANALISIS & LAPORAN
# =========================================================================
def render_analisis():
    """Render halaman analisis: BTSB, selisih, chart."""
    render_royal_header()
    
    # Back button
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_analisis"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
    
    st.markdown("### 📊 Analisis & Laporan")
    
    # ============================================================
    # LOAD DATA
    # ============================================================
    with st.spinner("⏳ Memuat data..."):
        rak_df = load_rak_master()
        so_df = load_so_hasil()
        _btsb_result = hitung_btsb_akumulatif()
    
    if rak_df.empty:
        st.error("❌ Data rak kosong.")
        return
    
    # ============================================================
    # ANALISIS BTSB
    # ============================================================
    st.markdown("#### 💰 Analisis BTSB")
    
    _total_spd = _btsb_result["total_spd"]
    _btsb_akum = _btsb_result["btsb_akumulatif"]
    _jumlah_hari = _btsb_result["jumlah_hari"]
    
    # Total selisih dari SO
    _total_selisih = 0
    if not so_df.empty and "selisih" in so_df.columns:
        _total_selisih = int(pd.to_numeric(so_df["selisih"], errors="coerce").fillna(0).sum())
    
    _analisis = analisis_btsb_vs_selisih(_total_selisih, _btsb_akum)
    
    # Card besar status
    st.markdown(f"""
    <div class='metric-card-v2 fade-in-up' style='--accent-color: {_analisis["warna"]}; padding: 24px 28px;'>
        <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;'>
            <div>
                <div class='metric-label-v2' style='font-size: 11px;'>⚖️ STATUS BTSB</div>
                <div style='font-family: "Cinzel", serif; font-size: 32px; font-weight: 900; 
                            color: {_analisis["warna"]}; text-shadow: 0 0 20px {_analisis["warna"]}; 
                            margin: 8px 0; letter-spacing: 3px;'>
                    {_analisis["icon"]} {_analisis["status"]}
                </div>
                <div class='metric-sub-v2'>
                    Penggunaan: <b style='color: {_analisis["warna"]};'>{_analisis["persen_penggunaan"]:.2f}%</b> 
                    dari BTSB • Gap: <b>{fmt_rp(_analisis["gap"])}</b>
                </div>
            </div>
            <div style='text-align: right;'>
                <div class='metric-label-v2'>Total Selisih</div>
                <div style='font-family: "JetBrains Mono", monospace; font-size: 22px; 
                            font-weight: 900; color: #fca5a5;'>
                    {fmt_rp(_total_selisih)}
                </div>
                <div class='metric-label-v2' style='margin-top: 12px;'>BTSB Akumulatif</div>
                <div style='font-family: "JetBrains Mono", monospace; font-size: 22px; 
                            font-weight: 900; color: #06b6d4;'>
                    {fmt_rp(_btsb_akum)}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3 kartu metrics
    col_a1, col_a2, col_a3 = st.columns(3)
    
    with col_a1:
        render_metric_card(
            label="Total SPD Bulan Ini",
            value=fmt_rp_short(_total_spd),
            sub_text=f"{_jumlah_hari} hari terinput",
            accent="#38bdf8",
            icon="📅"
        )
    
    with col_a2:
        render_metric_card(
            label="BTSB Akumulatif",
            value=fmt_rp_short(_btsb_akum),
            sub_text="0,15% × Total SPD",
            accent="#06b6d4",
            icon="🎯"
        )
    
    with col_a3:
        render_metric_card(
            label="Sisa Budget",
            value=fmt_rp_short(_analisis["gap"]),
            sub_text="BTSB - |Selisih|",
            accent="#a855f7",
            icon="💰"
        )
    
    st.markdown("---")
    
    # ============================================================
    # CHART: SELISIH PER RAK
    # ============================================================
    if not so_df.empty and "rak_id" in so_df.columns and "selisih" in so_df.columns:
        st.markdown("#### 📈 Selisih per Rak")
        
        try:
            import plotly.graph_objects as go
            
            # Group by rak
            _so_grp = so_df.groupby("rak_id")["selisih"].sum().reset_index()
            _so_grp = _so_grp.sort_values("selisih", ascending=True)
            
            # Warna: minus merah, plus hijau
            _colors = ["#fca5a5" if v < 0 else "#34d399" for v in _so_grp["selisih"]]
            
            _fig = go.Figure()
            _fig.add_trace(go.Bar(
                x=_so_grp["selisih"],
                y=_so_grp["rak_id"],
                orientation="h",
                marker=dict(
                    color=_colors,
                    line=dict(color="#78350f", width=1.5)
                ),
                text=_so_grp["selisih"],
                textposition="outside",
                textfont=dict(color="#fbbf24", size=11, family="JetBrains Mono"),
                hovertemplate="<b>%{y}</b><br>Selisih: %{x:+d}<extra></extra>",
            ))
            
            _fig.update_layout(
                height=max(300, len(_so_grp) * 35),
                margin=dict(l=10, r=40, t=20, b=20),
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#fbbf24", family="JetBrains Mono", size=11),
                xaxis=dict(
                    title="Selisih (Qty)",
                    gridcolor="rgba(251, 191, 36, 0.15)",
                    zeroline=True,
                    zerolinecolor="#fbbf24",
                    zerolinewidth=2,
                ),
                yaxis=dict(
                    title="",
                    gridcolor="rgba(251, 191, 36, 0.15)",
                    autorange="reversed",
                ),
                showlegend=False,
            )
            
            st.plotly_chart(_fig, use_container_width=True, key="chart_selisih_rak")
        except Exception as e:
            st.warning(f"⚠️ Chart gagal render: {str(e)[:100]}")
    
    st.markdown("---")
    
    # ============================================================
    # TOP 10 ITEM MINUS
    # ============================================================
    st.markdown("#### 🔥 Top 10 Item Minus Terbesar")
    
    if not so_df.empty and "selisih" in so_df.columns and "item_name" in so_df.columns:
        _so_df_copy = so_df.copy()
        _so_df_copy["selisih"] = pd.to_numeric(_so_df_copy["selisih"], errors="coerce").fillna(0)
        
        # Filter yang minus aja
        _minus_df = _so_df_copy[_so_df_copy["selisih"] < 0].copy()
        
        if not _minus_df.empty:
            # Group by item_name
            _top_minus = (
                _minus_df.groupby("item_name")
                .agg(
                    total_selisih=("selisih", "sum"),
                    total_qty_sys=("qty_system", "sum"),
                    total_qty_act=("qty_actual", "sum"),
                    jumlah_rak=("rak_id", "nunique"),
                )
                .reset_index()
                .sort_values("total_selisih", ascending=True)
                .head(10)
            )
            
            # Tampilkan sebagai card list
            for _idx, _row in _top_minus.iterrows():
                _rank = _idx + 1
                _icon = ["🥇", "🥈", "🥉"][_rank - 1] if _rank <= 3 else f"#{_rank}"
                
                st.markdown(f"""
                <div class='metric-card-v2' style='--accent-color: #fca5a5; padding: 14px 18px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;'>
                        <div style='flex: 1; min-width: 200px;'>
                            <div style='font-family: "JetBrains Mono", monospace; font-size: 13px; 
                                        font-weight: 900; color: #fbbf24; letter-spacing: 0.5px;'>
                                {_icon} {_row['item_name']}
                            </div>
                            <div style='font-family: "Quicksand", sans-serif; font-size: 10px; 
                                        color: #94a3b8; margin-top: 4px;'>
                                Muncul di <b style='color: #38bdf8;'>{_row['jumlah_rak']} rak</b> • 
                                System: {int(_row['total_qty_sys'])} → Actual: {int(_row['total_qty_act'])}
                            </div>
                        </div>
                        <div style='text-align: right;'>
                            <div style='font-family: "JetBrains Mono", monospace; font-size: 18px; 
                                        font-weight: 900; color: #fca5a5;'>
                                {int(_row['total_selisih']):+d}
                            </div>
                            <div style='font-family: "Quicksand", sans-serif; font-size: 9px; 
                                        color: #64748b;'>
                                qty
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🎉 Tidak ada item minus! Semua SO bersih.")
    else:
        st.info("📭 Belum ada data SO untuk dianalisis.")


# =========================================================================
# 📥 HALAMAN 4: DOWNLOAD LAPORAN
# =========================================================================
def render_download():
    """Render halaman download laporan."""
    render_royal_header()
    
    # Back button
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_download"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
    
    st.markdown("### 📥 Download Laporan")
    st.caption("Export data ke Excel atau PDF")
    
    # ============================================================
    # LOAD DATA
    # ============================================================
    rak_df = load_rak_master()
    so_df = load_so_hasil()
    spd_df = load_spd_harian()
    
    if rak_df.empty:
        st.error("❌ Data rak kosong.")
        return
    
    # ============================================================
    # PILIH JENIS LAPORAN
    # ============================================================
    st.markdown("#### 📋 Pilih Jenis Laporan")
    
    _jenis = st.selectbox(
        "Jenis Laporan",
        options=[
            "📊 Laporan Rak (Status SO)",
            "📦 Laporan SO (Detail Item)",
            "💰 Laporan SPD Harian",
            "📈 Laporan Komprehensif (Semua)",
        ],
        key="pilih_jenis_laporan",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # ============================================================
    # EXPORT EXCEL
    # ============================================================
    st.markdown("#### 📊 Export Excel")
    
    try:
        import io
        
        _output = io.BytesIO()
        
        with pd.ExcelWriter(_output, engine="xlsxwriter") as _writer:
            if "Laporan Rak" in _jenis:
                _df_rak = rak_df[["rak_id", "rak_name", "kategori", "pic", "status_so", "last_so_date"]].copy()
                _df_rak.columns = ["Kode Rak", "Nama Rak", "Kategori", "PIC", "Status SO", "Tanggal SO"]
                _df_rak.to_excel(_writer, sheet_name="Rak", index=False)
            
            elif "Laporan SO" in _jenis:
                if not so_df.empty:
                    _df_so = so_df.copy()
                    _cols = ["so_date", "rak_id", "plu", "item_name", "qty_system", "qty_actual", "selisih", "harga"]
                    _cols = [c for c in _cols if c in _df_so.columns]
                    _df_so = _df_so[_cols]
                    _df_so.columns = ["Tanggal", "Kode Rak", "PLU", "Nama Item", "Qty System", "Qty Actual", "Selisih", "Harga"]
                    _df_so.to_excel(_writer, sheet_name="SO", index=False)
                else:
                    pd.DataFrame({"Info": ["Tidak ada data SO"]}).to_excel(_writer, sheet_name="SO", index=False)
            
            elif "Laporan SPD" in _jenis:
                if not spd_df.empty:
                    _df_spd = spd_df[["tanggal", "spd", "keterangan"]].copy()
                    _df_spd.columns = ["Tanggal", "SPD (Rp)", "Keterangan"]
                    _df_spd.to_excel(_writer, sheet_name="SPD", index=False)
                else:
                    pd.DataFrame({"Info": ["Tidak ada data SPD"]}).to_excel(_writer, sheet_name="SPD", index=False)
            
            else:  # Komprehensif
                # Sheet 1: Rak
                _df_rak = rak_df[["rak_id", "rak_name", "kategori", "pic", "status_so", "last_so_date"]].copy()
                _df_rak.columns = ["Kode Rak", "Nama Rak", "Kategori", "PIC", "Status SO", "Tanggal SO"]
                _df_rak.to_excel(_writer, sheet_name="Rak", index=False)
                
                # Sheet 2: SO
                if not so_df.empty:
                    _df_so = so_df.copy()
                    _cols = ["so_date", "rak_id", "plu", "item_name", "qty_system", "qty_actual", "selisih", "harga"]
                    _cols = [c for c in _cols if c in _df_so.columns]
                    _df_so = _df_so[_cols]
                    _df_so.columns = ["Tanggal", "Kode Rak", "PLU", "Nama Item", "Qty System", "Qty Actual", "Selisih", "Harga"]
                    _df_so.to_excel(_writer, sheet_name="SO", index=False)
                
                # Sheet 3: SPD
                if not spd_df.empty:
                    _df_spd = spd_df[["tanggal", "spd", "keterangan"]].copy()
                    _df_spd.columns = ["Tanggal", "SPD (Rp)", "Keterangan"]
                    _df_spd.to_excel(_writer, sheet_name="SPD", index=False)
                
                # Sheet 4: Summary BTSB
                _btsb_result = hitung_btsb_akumulatif()
                _total_spd = _btsb_result["total_spd"]
                _btsb_akum = _btsb_result["btsb_akumulatif"]
                _total_selisih = int(pd.to_numeric(so_df["selisih"], errors="coerce").fillna(0).sum()) if not so_df.empty else 0
                _analisis = analisis_btsb_vs_selisih(_total_selisih, _btsb_akum)
                
                _summary_data = {
                    "Metric": ["Total SPD", "BTSB Akumulatif", "Total Selisih", "Sisa Budget", "Status"],
                    "Nilai": [
                        fmt_rp(_total_spd),
                        fmt_rp(_btsb_akum),
                        fmt_rp(_total_selisih),
                        fmt_rp(_analisis["gap"]),
                        f"{_analisis['icon']} {_analisis['status']}",
                    ]
                }
                pd.DataFrame(_summary_data).to_excel(_writer, sheet_name="Summary", index=False)
        
        _excel_bytes = _output.getvalue()
        _filename = f"Laporan_SO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        st.download_button(
            label="📥 DOWNLOAD EXCEL",
            data=_excel_bytes,
            file_name=_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
        
        st.success(f"✅ File siap didownload: **{_filename}**")
    
    except Exception as e:
        st.error(f"❌ Gagal generate Excel: {str(e)[:150]}")
    
    st.markdown("---")
    
    # ============================================================
    # EXPORT PDF
    # ============================================================
    st.markdown("#### 📄 Export PDF")
    st.caption("PDF siap dicetak — untuk briefing atau arsip")
    
    if st.button("📄 Generate PDF", use_container_width=True, key="btn_gen_pdf"):
        with st.spinner("⏳ Membuat PDF..."):
            try:
                from fpdf import FPDF
                
                # Build PDF
                _pdf = FPDF()
                _pdf.add_page()
                _pdf.set_auto_page_break(auto=True, margin=15)
                
                # Header
                _pdf.set_font("Helvetica", "B", 16)
                _pdf.cell(0, 10, "LAPORAN STOCK OPNAME", ln=True, align="C")
                _pdf.set_font("Helvetica", "", 10)
                _pdf.cell(0, 5, "Toko C383 - Karang Satria", ln=True, align="C")
                _pdf.cell(0, 5, f"Generated: {datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%d/%m/%Y %H:%M:%S WIB')}", ln=True, align="C")
                _pdf.ln(10)
                
                # Summary
                _progress = hitung_progress_so(rak_df, so_df)
                _btsb_result = hitung_btsb_akumulatif()
                
                _pdf.set_font("Helvetica", "B", 12)
                _pdf.cell(0, 8, "SUMMARY", ln=True)
                _pdf.set_font("Helvetica", "", 10)
                _pdf.cell(0, 6, f"Total Rak: {_progress['total_rak']}", ln=True)
                _pdf.cell(0, 6, f"Sudah SO: {_progress['rak_selesai']}", ln=True)
                _pdf.cell(0, 6, f"Belum SO: {_progress['rak_belum']}", ln=True)
                _pdf.cell(0, 6, f"Progres: {_progress['persen_selesai']:.1f}%", ln=True)
                _pdf.ln(5)
                
                _pdf.cell(0, 6, f"Total SPD Bulan Ini: {fmt_rp(_btsb_result['total_spd'])}", ln=True)
                _pdf.cell(0, 6, f"BTSB Akumulatif: {fmt_rp(_btsb_result['btsb_akumulatif'])}", ln=True)
                
                if not so_df.empty:
                    _total_selisih = int(pd.to_numeric(so_df["selisih"], errors="coerce").fillna(0).sum())
                    _analisis = analisis_btsb_vs_selisih(_total_selisih, _btsb_result['btsb_akumulatif'])
                    _pdf.cell(0, 6, f"Total Selisih: {fmt_rp(_total_selisih)}", ln=True)
                    _pdf.cell(0, 6, f"Status: {_analisis['status']} ({_analisis['persen_penggunaan']:.2f}%)", ln=True)
                
                _pdf_output = _pdf.output(dest="S")
                if isinstance(_pdf_output, str):
                    _pdf_bytes = _pdf_output.encode("latin-1")
                else:
                    _pdf_bytes = bytes(_pdf_output)
                
                st.download_button(
                    label="📥 DOWNLOAD PDF",
                    data=_pdf_bytes,
                    file_name=f"Laporan_SO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success("✅ PDF siap didownload!")
            
            except ImportError:
                st.error("❌ Library `fpdf2` belum terinstall. Tambahkan di `requirements.txt`.")
            except Exception as e:
                st.error(f"❌ Gagal generate PDF: {str(e)[:150]}")




# =========================================================================
# 🔄 HALAMAN REFRESH
# =========================================================================
def render_refresh():
    """Halaman refresh — clear cache."""
    render_royal_header()
    
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_refresh"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
    
    st.markdown("### 🔄 Refresh Data")
    st.caption("Muat ulang data dari Supabase")
    
    st.markdown("---")
    
    # Info card
    st.markdown("""
    <div class='metric-card-v2' style='--accent-color: #34d399; padding: 20px 24px;'>
        <div class='metric-label-v2'>ℹ️ INFO</div>
        <div style='font-family: "Quicksand", sans-serif; font-size: 12px; 
                    color: #e2e8f0; margin-top: 8px; line-height: 1.6;'>
            Refresh akan memuat ulang data dari Supabase. Gunakan ini kalau 
            ada perubahan data di database yang belum muncul di dashboard.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button(
        "🔄 REFRESH SEKARANG",
        use_container_width=True,
        type="primary",
        key="btn_refresh_now"
    ):
        with st.spinner("⏳ Refresh data..."):
            clear_cache()
            st.cache_data.clear()
            time.sleep(1.5)
        st.success("✅ Data berhasil di-refresh!")
        st.balloons()
        time.sleep(1.5)
        st.session_state["current_page"] = "dashboard"
        st.rerun()


# =========================================================================
# 🎯 ROUTING UTAMA
# =========================================================================
def main():
    """Main router — pilih halaman berdasarkan session state."""
    _page = st.session_state.get("current_page", "dashboard")
    
    if _page == "dashboard":
        render_dashboard()
    elif _page == "input_harian":
        render_input_harian()
    elif _page == "analisis":
        render_analisis()
    elif _page == "download":
        render_download()
    elif _page == "refresh":
        render_refresh()
    else:
        render_dashboard()


# =========================================================================
# RUN APP
# =========================================================================
if __name__ == "__main__":
    main()
