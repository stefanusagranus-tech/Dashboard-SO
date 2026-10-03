"""
Dashboard Stock Opname
======================
Toko C383 - Karang Satria

Dashboard SO dengan tema Emerald & Copper.
Hybrid: Hari Ini + Akumulasi + Trend.

Struktur:
- Halaman 1: Dashboard (default)
- Halaman 2: Input Harian (SPD + SO Rak)
- Halaman 3: Analisis
- Halaman 4: Download Laporan
- Halaman 5: Refresh
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
# CUSTOM CSS — EMERALD & COPPER
# =========================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700;900&display=swap');

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

    :root {
        --emerald-deep: #004D3B;
        --emerald: #0F8A72;
        --emerald-light: #7FB99B;
        --copper: #B87333;
        --copper-light: #E8B189;
        --bg-dark: #0a1612;
        --bg-dark-2: #0d1f1a;
        --text-light: #e8f3ee;
        --text-muted: #7a9b8e;
    }

    .stApp {
        background: 
            radial-gradient(circle at 20% 0%, #0F8A72 0%, transparent 50%),
            radial-gradient(circle at 80% 100%, #B87333 0%, transparent 50%),
            linear-gradient(180deg, #050d0a 0%, #0a1612 50%, #050d0a 100%);
        background-attachment: fixed;
        color: var(--text-light);
        font-family: 'Quicksand', sans-serif;
    }

    .main .block-container {
        padding: 1rem 1.5rem 6rem 1.5rem !important;
        max-width: 1400px !important;
    }

    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #050d0a; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--emerald), var(--copper));
        border-radius: 5px;
        border: 2px solid #050d0a;
    }

    h1, h2, h3, h4 {
        font-family: 'Cinzel', serif !important;
        color: var(--copper-light) !important;
        letter-spacing: 1.5px;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
    }
    p, span, div { color: var(--text-light); }

    .royal-header {
        position: relative;
        background: linear-gradient(135deg, #050d0a 0%, #0F8A72 50%, #050d0a 100%);
        border: 3px double var(--copper);
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 0 40px rgba(184, 115, 51, 0.35), inset 0 0 30px rgba(0, 0, 0, 0.7);
        overflow: hidden;
    }
    .royal-header::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, var(--copper) 20%, var(--copper-light) 50%, var(--copper) 80%, transparent);
        box-shadow: 0 0 15px rgba(232, 177, 137, 0.9);
    }
    .royal-title {
        font-family: 'Cinzel', serif;
        font-size: 28px;
        font-weight: 900;
        color: var(--copper-light);
        text-align: center;
        margin: 0;
        letter-spacing: 3px;
        text-shadow: 0 0 20px rgba(232, 177, 137, 0.7), 0 2px 8px rgba(0, 0, 0, 0.8);
    }
    .royal-subtitle {
        font-family: 'Quicksand', sans-serif;
        font-size: 12px;
        color: var(--emerald-light);
        text-align: center;
        margin-top: 6px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .royal-ornament {
        position: absolute;
        color: var(--copper);
        font-size: 16px;
        opacity: 0.85;
        filter: drop-shadow(0 0 5px rgba(184, 115, 51, 0.9));
    }
    .royal-orn-tl { top: 8px; left: 12px; }
    .royal-orn-tr { top: 8px; right: 12px; }
    .royal-orn-bl { bottom: 8px; left: 12px; }
    .royal-orn-br { bottom: 8px; right: 12px; }

    .header-clock {
        text-align: center;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px dashed rgba(232, 177, 137, 0.3);
    }
    .clock-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 20px;
        font-weight: 900;
        color: var(--copper-light);
        letter-spacing: 3px;
        text-shadow: 0 0 12px rgba(232, 177, 137, 0.6);
    }
    .clock-date {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--emerald-light);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 4px;
    }

    .metric-card-v2 {
        position: relative;
        background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
        border: 2px solid var(--copper);
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.6);
        overflow: hidden;
        transition: all 0.3s ease;
    }
    .metric-card-v2::before {
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 5px; height: 100%;
        background: var(--accent-color, var(--copper));
        box-shadow: 0 0 15px var(--accent-color, var(--copper));
    }
    .metric-card-v2:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.7), 0 0 25px var(--accent-color, rgba(184, 115, 51, 0.4));
    }
    .metric-label-v2 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 700;
        color: var(--text-muted);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value-v2 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 900;
        color: var(--copper-light);
        text-shadow: 0 0 15px rgba(232, 177, 137, 0.5);
        line-height: 1.1;
        word-wrap: break-word;
    }
    .metric-sub-v2 {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--text-muted);
        margin-top: 6px;
        font-weight: 600;
    }

    .menu-card-v2 {
        position: relative;
        background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
        border: 2px solid var(--copper);
        border-radius: 16px;
        padding: 24px 18px;
        text-align: center;
        transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1);
        cursor: pointer;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        margin-bottom: 10px;
    }
    .menu-card-v2:hover {
        border-color: var(--accent-color, var(--copper));
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7), 0 0 30px var(--accent-glow, rgba(184, 115, 51, 0.5));
        transform: translateY(-6px) scale(1.02);
    }
    .menu-icon-v2 {
        font-size: 48px;
        margin-bottom: 12px;
        filter: drop-shadow(0 0 15px var(--accent-glow, rgba(184, 115, 51, 0.7)));
    }
    .menu-title-v2 {
        font-family: 'Cinzel', serif;
        font-size: 14px;
        font-weight: 900;
        color: var(--copper-light);
        letter-spacing: 2px;
        margin-bottom: 6px;
        text-transform: uppercase;
    }
    .menu-desc-v2 {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--text-muted);
        line-height: 1.5;
    }

    div.stButton > button {
        background: linear-gradient(135deg, #0a1612 0%, #0d1f1a 100%) !important;
        color: var(--copper-light) !important;
        border: 2px solid var(--copper) !important;
        border-radius: 10px !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        padding: 10px 16px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5) !important;
        width: 100% !important;
        min-height: 44px !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, var(--emerald) 0%, var(--copper) 100%) !important;
        color: #ffffff !important;
        border-color: var(--copper-light) !important;
        box-shadow: 0 0 20px rgba(232, 177, 137, 0.7) !important;
        transform: translateY(-2px) !important;
    }

    div.stFormSubmitButton > button {
        background: linear-gradient(135deg, var(--emerald) 0%, var(--copper) 100%) !important;
        color: #ffffff !important;
        border: 2px solid var(--copper-light) !important;
        border-radius: 12px !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 900 !important;
        font-size: 14px !important;
        padding: 14px 20px !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        min-height: 54px !important;
    }

    div[data-testid="stDataFrame"] {
        border: 2px solid var(--copper) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        background-color: rgba(10, 22, 18, 0.95) !important;
        border: 2px solid var(--copper) !important;
        border-radius: 10px !important;
        min-height: 44px !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span {
        color: var(--copper-light) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
    }
    label, div[data-testid="stWidgetLabel"] label {
        color: var(--text-muted) !important;
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, var(--copper) 50%, transparent) !important;
        margin: 20px 0 !important;
    }

    .rak-result-card {
        background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
        border: 2px solid var(--emerald);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 6px;
        transition: all 0.25s ease;
    }
    .rak-result-card:hover {
        border-color: var(--copper-light);
        background: linear-gradient(135deg, rgba(15, 31, 26, 0.98), rgba(15, 138, 114, 0.3));
    }
    .rak-result-id {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 900;
        color: var(--copper-light);
        letter-spacing: 1px;
    }
    .rak-result-name {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--text-muted);
        margin-top: 2px;
    }

    .copyright-footer {
        text-align: center;
        margin-top: 60px;
        padding-top: 20px;
        border-top: 1px dashed rgba(232, 177, 137, 0.3);
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: var(--text-muted);
        letter-spacing: 1.5px;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in-up { animation: fadeInUp 0.6s ease-out forwards; }

    @media (max-width: 768px) {
        .royal-title { font-size: 18px; letter-spacing: 1.5px; }
        .royal-subtitle { font-size: 9px; }
        .royal-header { padding: 16px 20px; }
        .clock-time { font-size: 16px; }
        .clock-date { font-size: 9px; }
        .metric-value-v2 { font-size: 22px; }
        .menu-card-v2 { min-height: 150px; padding: 16px 12px; }
        .menu-icon-v2 { font-size: 38px; }
        .menu-title-v2 { font-size: 12px; }
        .main .block-container { padding: 0.5rem 1rem 5rem 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# SESSION STATE
# =========================================================================
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "dashboard"

if "selected_rak_list" not in st.session_state:
    st.session_state["selected_rak_list"] = []

if "last_loaded_date" not in st.session_state:
    st.session_state["last_loaded_date"] = None

# =========================================================================
# IMPORT MODULES
# =========================================================================
try:
    from modules.data_loader import load_rak_master, load_so_hasil, clear_cache
    from modules.rak_monitor import hitung_progress_so, get_rak_belum_so as get_rak_belum_so_df
    from modules.spd_calculator import (
        load_spd_harian, save_spd_harian,
        hitung_btsb_harian, hitung_btsb_akumulatif,
        analisis_btsb_vs_selisih,
    )
    from modules.input_handler import (
        save_input_harian,
        load_spd_by_date,
        load_so_rak_by_date,
        search_rak,
        get_akumulasi_nominal_bulan,
        get_nominal_per_hari,
        get_so_rak_detail,
        get_rak_belum_so,
        get_so_hari_ini,
        get_spd_hari_ini,
        get_rak_by_kode_exact,
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
└── input_handler.py
    """)
    st.stop()

# =========================================================================
# HELPER FUNCTIONS
# =========================================================================
def render_royal_header(show_clock=True):
    """Render header banner royal dengan jam & tanggal (tanpa detik)."""
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _time_str = _now.strftime("%H:%M")
    
    _day_map = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
    }
    _month_map = {
        "January": "Januari", "February": "Februari", "March": "Maret",
        "April": "April", "May": "Mei", "June": "Juni", "July": "Juli",
        "August": "Agustus", "September": "September", "October": "Oktober",
        "November": "November", "December": "Desember"
    }
    _day_id = _day_map.get(_now.strftime("%A"), _now.strftime("%A"))
    _month_id = _month_map.get(_now.strftime("%B"), _now.strftime("%B"))
    _date_id = f"{_day_id}, {_now.day} {_month_id} {_now.year}"
    
    _clock_html = ""
    if show_clock:
        _clock_html = (
            "<div class='header-clock'>"
            "<div class='clock-time'>🕐 " + _time_str + " WIB</div>"
            "<div class='clock-date'>📅 " + _date_id + "</div>"
            "</div>"
        )
    
    _header_html = (
        "<div class='royal-header fade-in-up'>"
        "<div class='royal-ornament royal-orn-tl'>⚜</div>"
        "<div class='royal-ornament royal-orn-tr'>⚜</div>"
        "<div class='royal-ornament royal-orn-bl'>⚜</div>"
        "<div class='royal-ornament royal-orn-br'>⚜</div>"
        "<div class='royal-title'>DASHBOARD STOCK OPNAME</div>"
        "<div class='royal-subtitle'>⚜ Toko C383 - Karang Satria ⚜</div>"
        + _clock_html +
        "</div>"
    )
    
    st.markdown(_header_html, unsafe_allow_html=True)


def render_copyright():
    """Render footer copyright."""
    st.markdown("""
    <div class='copyright-footer'>
        ⚜ Dashboard SO KGS V.1 ⚜
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(label, value, sub_text="", accent="#E8B189", icon=""):
    """Render metric card."""
    st.markdown(f"""
    <div class='metric-card-v2 fade-in-up' style='--accent-color: {accent};'>
        <div class='metric-label-v2'>{icon} {label}</div>
        <div class='metric-value-v2' style='color: {accent};'>{value}</div>
        <div class='metric-sub-v2'>{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_menu_card(icon, title, desc, accent, accent_glow, key, target_page):
    """Render menu card."""
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
    try:
        return f"Rp {int(value):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp_short(value):
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


def go_to_page(page):
    st.session_state["current_page"] = page
    st.rerun()


# =========================================================================
# 🏠 HALAMAN 1: DASHBOARD (HYBRID)
# =========================================================================
def render_dashboard():
    """Render dashboard — Hybrid: Hari Ini + Akumulasi + Trend."""
    render_royal_header()
    
    # ============================================================
    # LOAD DATA
    # ============================================================
    with st.spinner("⏳ Memuat data..."):
        rak_df = load_rak_master()
        so_df = load_so_hasil()
        _akumulasi = get_akumulasi_nominal_bulan()
        _trend = get_nominal_per_hari()
        _detail_so = get_so_rak_detail(limit=20)
        _btsb_result = hitung_btsb_akumulatif()
    
    if rak_df.empty:
        st.error("❌ **Data rak kosong!**")
        st.info("💡 Pastikan tabel `rak_master` di Supabase sudah di-import.")
        render_copyright()
        return
    
    # ============================================================
    # 👥 SHIFT HARI INI (dari Master Shift)
    # ============================================================
    _shift_today_ada = False
    try:
        from modules.master_shift_handler import get_shift_hari_ini, KODE_SHIFT
        
        _shift_today = get_shift_hari_ini()
        
        if _shift_today:
            _shift_today_ada = True
            st.markdown("### 👥 Personil Shift Hari Ini")
            
            # Group by kode shift
            _grouped = {}
            for _nama, _kode in _shift_today.items():
                if _kode not in _grouped:
                    _grouped[_kode] = []
                _grouped[_kode].append(_nama)
            
            # Urutan kode
            _urutan_kode = ["P7", "S15", "M22", "O", "C", "AO"]
            _cols_shift = st.columns(4)
            
            _col_idx = 0
            for _kode in _urutan_kode:
                if _kode not in _grouped:
                    continue
                
                _info = KODE_SHIFT.get(_kode, {
                    "label": _kode, "warna": "#CCCCCC", "icon": "❓"
                })
                _nama_list = _grouped[_kode]
                _nama_str = ", ".join(sorted(_nama_list))
                
                with _cols_shift[_col_idx % 4]:
                    st.markdown(
                        f"<div style='"
                        f"background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));"
                        f"border: 2px solid {_info['warna']};"
                        f"border-left: 5px solid {_info['warna']};"
                        f"border-radius: 12px;"
                        f"padding: 14px 16px;"
                        f"margin-bottom: 10px;"
                        f"box-shadow: 0 4px 12px rgba(0,0,0,0.4);"
                        f"'>"
                        f"<div style='"
                        f"font-family: JetBrains Mono, monospace;"
                        f"font-size: 11px;"
                        f"color: {_info['warna']};"
                        f"letter-spacing: 1.5px;"
                        f"font-weight: 900;"
                        f"margin-bottom: 8px;"
                        f"'>"
                        f"{_info['icon']} {_info['label'].upper()}"
                        f"</div>"
                        f"<div style='"
                        f"font-family: Quicksand, sans-serif;"
                        f"font-size: 12px;"
                        f"color: #e8f3ee;"
                        f"font-weight: 700;"
                        f"line-height: 1.5;"
                        f"'>"
                        f"{_nama_str}"
                        f"</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                
                _col_idx += 1
            
            st.markdown("---")
    
    except ImportError:
        pass
    except Exception as _e_shift:
        print(f"[SHIFT TODAY ERROR] {_e_shift}")
    
    # ============================================================
    # ✅ REMINDER kalau belum ada shift hari ini
    # ============================================================
    if not _shift_today_ada:
        st.markdown(
            "<div style='"
            "background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(245, 158, 11, 0.20));"
            "border: 2px solid #fbbf24;"
            "border-left: 5px solid #fbbf24;"
            "border-radius: 12px;"
            "padding: 14px 18px;"
            "margin-bottom: 16px;"
            "box-shadow: 0 0 15px rgba(251, 191, 36, 0.3);"
            "'>"
            "<div style='"
            "font-family: JetBrains Mono, monospace;"
            "font-size: 12px;"
            "font-weight: 900;"
            "color: #fcd34d;"
            "letter-spacing: 1px;"
            "'>"
            "⚠️ BELUM ADA SHIFT HARI INI"
            "</div>"
            "<div style='"
            "font-family: Quicksand, sans-serif;"
            "font-size: 11px;"
            "color: #fde68a;"
            "margin-top: 6px;"
            "line-height: 1.5;"
            "'>"
            "Jadwal shift belum di-set. "
            "Buka halaman <b>📅 Master Shift</b> untuk update jadwal, "
            "atau ketik langsung via Chat AI."
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

# ============================================================
# METRIC HARI INI
# ============================================================
st.markdown("### 📊 Ringkasan Hari Ini")
...
    
    # ============================================================
    # METRIC HARI INI
    # ============================================================
    st.markdown("### 📊 Ringkasan Hari Ini")
    
    _progress = hitung_progress_so(rak_df, so_df)
    _so_today = get_so_hari_ini()
    _spd_today = get_spd_hari_ini()
    _nominal_today = sum(float(r.get("nominal_adjust", 0)) for r in _so_today) if _so_today else 0
    _rak_so_today = len(_so_today) if _so_today else 0
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        render_metric_card(
            label="Rak di-SO Hari Ini",
            value=f"{_rak_so_today}",
            sub_text=f"dari {_progress['total_rak']} total rak",
            accent="#E8B189",
            icon="📦"
        )
    
    with col_m2:
        _btsb_today = hitung_btsb_harian(_spd_today) if _spd_today > 0 else 0
        render_metric_card(
            label="SPD Hari Ini",
            value=fmt_rp_short(_spd_today),
            sub_text=f"BTSB: {fmt_rp_short(_btsb_today)}",
            accent="#7FB99B",
            icon="💰"
        )
    
    with col_m3:
        _color_today = "#E88B8B" if _nominal_today < 0 else "#7FB99B"
        _sign_today = "+" if _nominal_today >= 0 else ""
        render_metric_card(
            label="Nominal SO Hari Ini",
            value=f"{_sign_today}{fmt_rp_short(_nominal_today)}",
            sub_text=f"{_rak_so_today} rak di-SO",
            accent=_color_today,
            icon="⚖️"
        )
    
    with col_m4:
        render_metric_card(
            label="Progres SO Bulan Ini",
            value=f"{_progress['persen_selesai']:.1f}%",
            sub_text=f"Target: 80% • {_progress['rak_selesai']}/{_progress['total_rak']} rak",
            accent="#E8B189",
            icon="🎯"
        )
    
    st.markdown("---")
    
    # ============================================================
    # METRIC AKUMULASI BULAN INI
    # ============================================================
    st.markdown("### 📈 Akumulasi Bulan Ini")
    
    col_a1, col_a2, col_a3 = st.columns(3)
    
    with col_a1:
        render_metric_card(
            label="Total SPD Bulan Ini",
            value=fmt_rp_short(_btsb_result["total_spd"]),
            sub_text=f"{_btsb_result['jumlah_hari']} hari terinput",
            accent="#7FB99B",
            icon="📅"
        )
    
    with col_a2:
        _total_nominal = _akumulasi["total_nominal"]
        _color_akum = "#E88B8B" if _total_nominal < 0 else "#7FB99B"
        _sign_akum = "+" if _total_nominal >= 0 else ""
        render_metric_card(
            label="Total Nominal SO",
            value=f"{_sign_akum}{fmt_rp_short(_total_nominal)}",
            sub_text=f"{_akumulasi['total_rak']} rak • {_akumulasi['jumlah_hari']} hari",
            accent=_color_akum,
            icon="⚖️"
        )
    
    with col_a3:
        _btsb_total = _btsb_result["btsb_akumulatif"]
        _analisis = analisis_btsb_vs_selisih(_total_nominal, _btsb_total)
        
        # ✅ Hitung %NSB dari Sales
        _total_spd_akum = _btsb_result["total_spd"]
        if _total_spd_akum > 0:
            _pct_nsb_sales = (abs(_total_nominal) / _total_spd_akum) * 100
        else:
            _pct_nsb_sales = 0.0
        
        render_metric_card(
            label="Status BTSB",
            value=f"{_analisis['icon']} {_analisis['status']}",
            sub_text=(
                f"BTSB: {fmt_rp_short(_btsb_total)} • "
                f"{_analisis['persen_penggunaan']:.1f}% • "
                f"📊 %NSB: {_pct_nsb_sales:.3f}%"
            ),
            accent=_analisis['warna'],
            icon="🎯"
        )
    
    # ============================================================
    # ✅ SECTION BARU: %NSB dari Sales (Detail)
    # ============================================================
    st.markdown("### 📊 Detail NSB vs Sales")
    
    col_nsb1, col_nsb2, col_nsb3 = st.columns(3)
    
    with col_nsb1:
        _total_spd_akum2 = _btsb_result["total_spd"]
        if _total_spd_akum2 > 0:
            _pct_nsb_sales2 = (abs(_total_nominal) / _total_spd_akum2) * 100
        else:
            _pct_nsb_sales2 = 0.0
        
        _color_pct = "#7FB99B" if _pct_nsb_sales2 <= 0.15 else "#E88B8B"
        _icon_pct = "✅" if _pct_nsb_sales2 <= 0.15 else "⚠️"
        
        render_metric_card(
            label="% NSB vs Sales",
            value=f"{_icon_pct} {_pct_nsb_sales2:.3f}%",
            sub_text="Target: ≤ 0.15%",
            accent=_color_pct,
            icon="📊"
        )
    
    with col_nsb2:
        _pct_btsb = _analisis["persen_penggunaan"]
        _color_btsb = "#7FB99B" if _pct_btsb <= 100 else "#E88B8B"
        
        render_metric_card(
            label="% BTSB Terpakai",
            value=f"{_pct_btsb:.2f}%",
            sub_text="Dari budget BTSB",
            accent=_color_btsb,
            icon="🎯"
        )
    
    with col_nsb3:
        _target_nsb = _total_spd_akum2 * 0.0015
        _selisih_budget = _target_nsb - abs(_total_nominal)
        _color_sisa = "#7FB99B" if _selisih_budget >= 0 else "#E88B8B"
        _icon_sisa = "✅" if _selisih_budget >= 0 else "⚠️"
        
        render_metric_card(
            label="Sisa Budget NSB",
            value=f"{_icon_sisa} {fmt_rp_short(_selisih_budget)}",
            sub_text=f"Target: {fmt_rp_short(_target_nsb)}",
            accent=_color_sisa,
            icon="💰"
        )
    
    st.markdown("---")
    
    # ============================================================
    # 📊 CARD METRIC + MINI TREND CHART (TRADING STYLE)
    # ============================================================
    if _trend and len(_trend) >= 2:
        # ✅ Siapkan data
        _dates_full = [pd.to_datetime(t["tanggal"]) for t in _trend]
        _dates_label = [d.strftime("%d/%m") for d in _dates_full]
        _values = [float(t["nominal"]) for t in _trend]
        
        # ✅ Hitung summary
        _min_val = min(_values) if _values else 0
        _max_val = max(_values) if _values else 0
        _last_val = _values[-1] if _values else 0
        _prev_val = _values[-2] if len(_values) > 1 else _last_val
        _delta = _last_val - _prev_val
        _delta_pct = (_delta / abs(_prev_val) * 100) if _prev_val != 0 else 0
        
        # ✅ Warna
        _color_main = "#E88B8B" if _last_val < 0 else "#7FB99B"
        _color_delta = "#7FB99B" if _delta >= 0 else "#E88B8B"
        _icon_delta = "📈" if _delta >= 0 else "📉"
        _sign_delta = "+" if _delta >= 0 else ""
        
        # ✅ CSS TRADING CARD
        st.markdown("""
        <style>
            .trading-card {
                background: linear-gradient(135deg, #0a1612 0%, #0d1f1a 100%);
                border: 2px solid #B87333;
                border-radius: 14px;
                padding: 16px 20px;
                margin-bottom: 12px;
                position: relative;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
            }
            .trading-card::before {
                content: "";
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 2px;
                background: linear-gradient(90deg, transparent, #E8B189, transparent);
                box-shadow: 0 0 12px #E8B189;
            }
            .trading-label {
                font-family: 'JetBrains Mono', monospace;
                font-size: 9px;
                color: #7a9b8e;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                margin-bottom: 6px;
            }
            .trading-value {
                font-family: 'JetBrains Mono', monospace;
                font-size: 26px;
                font-weight: 900;
                line-height: 1.1;
                letter-spacing: -0.5px;
                text-shadow: 0 0 15px currentColor;
            }
            .trading-delta {
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                margin-top: 6px;
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .trading-sub {
                font-family: 'Quicksand', sans-serif;
                font-size: 10px;
                color: #7a9b8e;
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px dashed rgba(232, 177, 137, 0.2);
            }
        </style>
        """, unsafe_allow_html=True)
        
        # ✅ Layout: Card kiri + Mini Chart kanan
        st.markdown("### 📈 Trend Nominal SO")
        
        _col_trading_left, _col_trading_right = st.columns([1, 2])
        
        with _col_trading_left:
            # Card metric
            st.markdown(
                "<div class='trading-card'>"
                "<div class='trading-label'>⚖️ Total Nominal SO</div>"
                "<div class='trading-value' style='color: " + _color_main + ";'>"
                + fmt_rp_short(_last_val) + "</div>"
                "<div class='trading-delta' style='color: " + _color_delta + ";'>"
                + _icon_delta + " Δ vs kemarin: " + _sign_delta + f"{_delta:,.0f}".replace(",", ".") +
                " <span style='color:#7a9b8e;'>(" + _sign_delta + f"{_delta_pct:.1f}%)" + "</span>"
                "</div>"
                "<div class='trading-sub'>"
                + f"📊 Min: {fmt_rp_short(_min_val)} • Max: {fmt_rp_short(_max_val)}"
                + "</div>"
                "</div>",
                unsafe_allow_html=True
            )
        
        with _col_trading_right:
            # Mini chart (sparkline trading style)
            try:
                import plotly.graph_objects as go
                
                _color_line = "#E88B8B" if _last_val < 0 else "#7FB99B"
                _color_fill = "rgba(232, 139, 139, 0.2)" if _last_val < 0 else "rgba(127, 185, 155, 0.2)"
                
                _fig_mini = go.Figure()
                
                _fig_mini.add_trace(go.Scatter(
                    x=_dates_label,
                    y=_values,
                    mode="lines+markers",
                    line=dict(
                        color=_color_line,
                        width=3,
                        shape="spline",
                    ),
                    marker=dict(
                        size=8,
                        color=_color_line,
                        line=dict(color="#0a1612", width=1.5),
                    ),
                    fill="tozeroy",
                    fillcolor=_color_fill,
                    hovertemplate="<b>%{x}</b><br>Nominal: Rp %{y:+,.0f}<extra></extra>",
                ))
                
                # Baseline
                _fig_mini.add_hline(
                    y=0,
                    line=dict(color="#7FB99B", width=1.5, dash="dot"),
                    opacity=0.5,
                )
                
                _fig_mini.update_layout(
                    height=180,
                    margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E8B189", family="JetBrains Mono", size=9),
                    xaxis=dict(
                        showgrid=False,
                        showline=False,
                        showticklabels=False,
                        type="category",
                        zeroline=False,
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor="rgba(232, 177, 137, 0.08)",
                        showline=False,
                        showticklabels=True,
                        tickfont=dict(size=8, color="#7a9b8e"),
                        zeroline=True,
                        zerolinecolor="#7FB99B",
                        zerolinewidth=1,
                    ),
                    showlegend=False,
                    hovermode="x unified",
                )
                
                st.plotly_chart(_fig_mini, use_container_width=True, key="chart_mini_trend")
            
            except Exception as e:
                st.warning(f"⚠️ Mini chart gagal render: {str(e)[:100]}")
        
        # ============================================================
        # 📊 CHART BESAR (DETAIL HARIAN)
        # ============================================================
        st.markdown("#### 📊 Detail Harian")
        
        try:
            import plotly.graph_objects as go
            
            _colors_bar = ["#E88B8B" if v < 0 else "#7FB99B" for v in _values]
            
            _max_abs_bar = max([abs(v) for v in _values]) if _values else 1000000
            _y_max_bar = max(_max_abs_bar * 1.5, 100000)
            
            _fig_bar = go.Figure()
            
            _fig_bar.add_trace(go.Bar(
                x=_dates_label,
                y=_values,
                marker=dict(
                    color=_colors_bar,
                    line=dict(color="#B87333", width=1.5),
                ),
                text=[f"{v:+,.0f}".replace(",", ".") for v in _values],
                textposition="outside",
                textfont=dict(color="#E8B189", size=10, family="JetBrains Mono"),
                hovertemplate="<b>%{x}</b><br>Nominal: Rp %{y:+,.0f}<extra></extra>",
            ))
            
            _fig_bar.add_hline(
                y=0,
                line=dict(color="#7FB99B", width=2, dash="dash"),
                annotation_text="Batas Aman",
                annotation_position="right",
                annotation_font=dict(color="#7FB99B", size=10, family="JetBrains Mono"),
            )
            
            _fig_bar.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=30, b=50),
                plot_bgcolor="rgba(10, 22, 18, 0.4)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E8B189", family="JetBrains Mono", size=11),
                xaxis=dict(
                    title="Tanggal",
                    gridcolor="rgba(232, 177, 137, 0.15)",
                    type="category",
                ),
                yaxis=dict(
                    title="Nominal (Rp)",
                    gridcolor="rgba(232, 177, 137, 0.15)",
                    zeroline=True,
                    zerolinecolor="#7FB99B",
                    zerolinewidth=2,
                    range=[-_y_max_bar, _y_max_bar],
                ),
                showlegend=False,
            )
            
            st.plotly_chart(_fig_bar, use_container_width=True, key="chart_trend_nominal")
        
        except Exception as e:
            st.warning(f"⚠️ Chart gagal render: {str(e)[:100]}")
    
    elif _trend and len(_trend) == 1:
        # ✅ Handle 1 hari — empty state
        st.markdown("### 📈 Trend Nominal SO")
        st.markdown("""
        <div style='
            background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
            border: 2px dashed #B87333;
            border-radius: 14px;
            padding: 40px 20px;
            text-align: center;
        '>
            <div style='font-size: 48px; opacity: 0.5; margin-bottom: 12px;'>📊</div>
            <div style='
                font-family: "Cinzel", serif;
                font-size: 14px;
                color: #E8B189;
                letter-spacing: 2px;
                margin-bottom: 8px;
            '>BUTUH MINIMAL 2 HARI</div>
            <div style='
                font-family: "Quicksand", sans-serif;
                font-size: 11px;
                color: #7a9b8e;
                line-height: 1.6;
            '>Input data minimal 2 hari untuk melihat trend.<br>
            Baru ada <b>1 hari</b> data: <b>""" + _trend[0]["tanggal"] + """</b></div>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown("### 📈 Trend Nominal SO")
        st.info("📭 Belum ada data. Input SPD & SO di menu **📝 Input Harian**.")
    
    st.markdown("---")
    
    # ============================================================
    # ✅ STEP 3: CHART TREND NSB% DARI SALES
    # ============================================================
    if _trend and len(_trend) > 0:
        st.markdown("### 📉 Trend %NSB dari Sales")
        st.caption("Monitor kenaikan/penurunan NSB per hari — Target: ≤ 0.15%")
        
        try:
            import plotly.graph_objects as go
            
            # ✅ Parse tanggal
            _dates_full_pct = [pd.to_datetime(t["tanggal"]) for t in _trend]
            _dates_label_pct = [d.strftime("%d/%m") for d in _dates_full_pct]
            
            # ✅ Hitung SPD harian average
            _total_spd_akum_pct = _btsb_result["total_spd"]
            _jumlah_hari_pct = _btsb_result["jumlah_hari"] if _btsb_result["jumlah_hari"] > 0 else 1
            _spd_harian_avg_pct = _total_spd_akum_pct / _jumlah_hari_pct
            
            # ✅ Hitung %NSB per hari
            _pct_nsb_per_hari = []
            for t in _trend:
                _nominal_abs_pct = abs(float(t["nominal"]))
                if _spd_harian_avg_pct > 0:
                    _pct = (_nominal_abs_pct / _spd_harian_avg_pct) * 100
                else:
                    _pct = 0.0
                _pct_nsb_per_hari.append(_pct)
            
            # ✅ Warna marker
            _colors_pct = ["#7FB99B" if p <= 0.15 else "#E88B8B" for p in _pct_nsb_per_hari]
            
            # ✅ Range Y fixed
            _max_pct = max(_pct_nsb_per_hari) if _pct_nsb_per_hari else 0.15
            _y_max_pct = max(_max_pct * 2.0, 0.5)
            
            _fig_pct = go.Figure()
            
            # ✅ Line chart
            _fig_pct.add_trace(go.Scatter(
                x=_dates_label_pct,
                y=_pct_nsb_per_hari,
                mode="lines+markers+text",
                line=dict(color="#E8B189", width=3, shape="spline"),
                marker=dict(
                    size=12,
                    color=_colors_pct,
                    line=dict(color="#B87333", width=2),
                ),
                text=[f"{p:.3f}%" for p in _pct_nsb_per_hari],
                textposition="bottom center",
                textfont=dict(color="#E8B189", size=10, family="JetBrains Mono"),
                fill="tozeroy",
                fillcolor="rgba(232, 177, 137, 0.12)",
                hovertemplate="<b>%{x}</b><br>NSB%: %{y:.3f}%<extra></extra>",
            ))
            
            # ✅ Garis target 0.15%
            _fig_pct.add_hline(
                y=0.15,
                line=dict(color="#E88B8B", width=2, dash="dash"),
                annotation_text="⚠️ Target: 0.15%",
                annotation_position="right",
                annotation_font=dict(color="#E88B8B", size=10, family="JetBrains Mono"),
            )
            
            # ✅ Layout
            _fig_pct.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=30, b=30),
                plot_bgcolor="rgba(10, 22, 18, 0.4)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E8B189", family="JetBrains Mono", size=11),
                xaxis=dict(
                    title="Tanggal",
                    gridcolor="rgba(232, 177, 137, 0.15)",
                    type="category",
                ),
                yaxis=dict(
                    title="%NSB dari Sales",
                    gridcolor="rgba(232, 177, 137, 0.15)",
                    zeroline=True,
                    zerolinecolor="#7FB99B",
                    zerolinewidth=1.5,
                    range=[0, _y_max_pct],
                ),
                showlegend=False,
            )
            
            st.plotly_chart(_fig_pct, use_container_width=True, key="chart_trend_nsb_pct")
        
        except Exception as e:
            st.warning(f"⚠️ Chart NSB% gagal render: {str(e)[:100]}")
    
    st.markdown("---")

    # ============================================================
    # TABEL DETAIL SO RAK
    # ============================================================
    st.markdown("### 📋 Detail SO Rak (Terbaru)")
    
    if _detail_so:
        _df_detail = pd.DataFrame(_detail_so)
        _cols_show = ["so_date", "rak_id", "nominal_adjust", "pic", "keterangan"]
        _cols_show = [c for c in _cols_show if c in _df_detail.columns]
        _df_show = _df_detail[_cols_show].copy()
        
        if "nominal_adjust" in _df_show.columns:
            _df_show["nominal_adjust"] = _df_show["nominal_adjust"].apply(
                lambda v: f"{float(v):+,.0f}".replace(",", ".")
            )
        
        _col_names = ["Tanggal", "Kode Rak", "Nominal (Rp)", "PIC", "Keterangan"]
        _df_show.columns = _col_names[:len(_df_show.columns)]
        
        st.dataframe(_df_show, use_container_width=True, hide_index=True, height=400)
        st.caption(f"📊 Menampilkan **{len(_df_show)}** SO rak terbaru")
    else:
        st.info("📭 Belum ada SO rak yang tercatat.")
    
    st.markdown("---")
    
    # ============================================================
    # MENU CARD
    # ============================================================
    st.markdown("### 📋 Pilih Menu")
    
    col_menu1, col_menu2 = st.columns(2)
    
    with col_menu1:
        render_menu_card(
            icon="📝",
            title="Input Harian",
            desc="Input SPD & SO<br>dalam 1 form",
            accent="#7FB99B",
            accent_glow="rgba(127, 185, 155, 0.6)",
            key="btn_menu_input",
            target_page="input_harian"
        )
    
    with col_menu2:
        render_menu_card(
            icon="📊",
            title="Analisis",
            desc="BTSB, selisih<br>& rak belum SO",
            accent="#E8B189",
            accent_glow="rgba(232, 177, 137, 0.6)",
            key="btn_menu_analisis",
            target_page="analisis"
        )
    
    col_menu3, col_menu4 = st.columns(2)
    
    with col_menu3:
        st.markdown("""
        <div style='
            background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
            border: 2px solid #7FB99B;
            border-radius: 12px;
            padding: 16px 14px;
            text-align: center;
            margin-bottom: 8px;
        '>
            <div style='font-size: 32px; margin-bottom: 6px;'>🔄</div>
            <div style='
                font-family: "Cinzel", serif;
                font-size: 12px;
                font-weight: 900;
                color: #7FB99B;
                letter-spacing: 1.5px;
                text-transform: uppercase;
            '>Refresh</div>
            <div style='
                font-family: "Quicksand", sans-serif;
                font-size: 9px;
                color: #7a9b8e;
                margin-top: 4px;
            '>Muat ulang data</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Refresh", key="btn_menu_refresh", use_container_width=True):
            go_to_page("refresh")
    
    with col_menu4:
        st.markdown("""
        <div style='
            background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
            border: 2px solid #E8B189;
            border-radius: 12px;
            padding: 16px 14px;
            text-align: center;
            margin-bottom: 8px;
        '>
            <div style='font-size: 32px; margin-bottom: 6px;'>📥</div>
            <div style='
                font-family: "Cinzel", serif;
                font-size: 12px;
                font-weight: 900;
                color: #E8B189;
                letter-spacing: 1.5px;
                text-transform: uppercase;
            '>Download</div>
            <div style='
                font-family: "Quicksand", sans-serif;
                font-size: 9px;
                color: #7a9b8e;
                margin-top: 4px;
            '>Export laporan</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📥 Download", key="btn_menu_download", use_container_width=True):
            go_to_page("download")
    
    # ✅ Menu BARU: MASTER SHIFT
    st.markdown("---")
    st.markdown("### 📅 Menu Master Shift")
    
    col_menu5, col_menu6 = st.columns(2)
    
    with col_menu5:
        st.markdown("""
        <div style='
            background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
            border: 2px solid #a855f7;
            border-radius: 12px;
            padding: 20px 16px;
            text-align: center;
            margin-bottom: 8px;
            box-shadow: 0 0 15px rgba(168, 85, 247, 0.3);
        '>
            <div style='font-size: 42px; margin-bottom: 10px; 
                        filter: drop-shadow(0 0 15px rgba(168, 85, 247, 0.7));'>📅</div>
            <div style='
                font-family: "Cinzel", serif;
                font-size: 14px;
                font-weight: 900;
                color: #a855f7;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-bottom: 6px;
            '>Master Shift</div>
            <div style='
                font-family: "Quicksand", sans-serif;
                font-size: 10px;
                color: #7a9b8e;
                line-height: 1.5;
            '>Kelola jadwal shift<br>dengan Chat AI</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(
            "📅 Buka Master Shift",
            key="btn_menu_master_shift",
            use_container_width=True,
            type="primary",
        ):
            try:
                st.switch_page("pages/master_shift.py")
            except Exception as e:
                st.error(f"⚠️ Gagal pindah: {e}")
    
    with col_menu6:
        # Placeholder kosong atau menu lain di masa depan
        st.markdown("<br>", unsafe_allow_html=True)
        
    render_copyright()


# =========================================================================
# 📝 HALAMAN 2: INPUT HARIAN (SPD + SO RAK)
# =========================================================================
def render_input_harian():
    """Render halaman input harian: SPD + SO rak (multiple)."""
    render_royal_header(show_clock=True)
    
    # Back button + Master Shift shortcut
    col_back, col_shift_shortcut, _ = st.columns([1, 1, 3])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_input"):
            st.session_state["selected_rak_list"] = []
            st.session_state["last_loaded_date"] = None
            go_to_page("dashboard")
    
    with col_shift_shortcut:
        if st.button("📅 Master Shift", key="btn_shortcut_master_shift"):
            try:
                st.switch_page("pages/master_shift.py")
            except Exception as e:
                st.error(f"⚠️ {e}")
    
    st.markdown("### 📝 Input Harian")
    st.caption("Input SPD & SO rak dalam 1 form — bisa edit data yang sudah ada")
    
    # ============================================================
    # BAGIAN A: TANGGAL
    # ============================================================
    st.markdown("#### 📅 Tanggal & SPD")
    
    _today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    _tanggal = st.date_input(
        "📅 Tanggal",
        value=_today,
        key="input_tanggal"
    )
    
    # AUTO-LOAD DATA EXISTING saat tanggal berubah
    if st.session_state["last_loaded_date"] != _tanggal:
        _existing_spd = load_spd_by_date(_tanggal)
        _existing_so = load_so_rak_by_date(_tanggal)
        
        st.session_state["loaded_spd"] = int(_existing_spd["spd"]) if _existing_spd else 0
        st.session_state["selected_rak_list"] = [
            {
                "rak_id": r["rak_id"],
                "nominal_adjust": float(r.get("nominal_adjust", 0)),
            }
            for r in _existing_so
        ]
        st.session_state["last_loaded_date"] = _tanggal
        st.rerun()
    
    # ============================================================
    # BAGIAN B: SPD (OPSIONAL)
    # ============================================================
    _spd_val = st.number_input(
        "💰 SPD Hari Ini (Rp) — Opsional, boleh 0",
        min_value=0,
        step=100000,
        value=int(st.session_state.get("loaded_spd", 0)),
        key="input_spd_val",
        help="Kosongkan / isi 0 kalau belum ada SPD hari ini"
    )
    
    if _spd_val > 0:
        _btsb_harian = hitung_btsb_harian(_spd_val)
        st.success(f"💡 BTSB Otomatis: **{fmt_rp(_btsb_harian)}** (0,15% × SPD)")
    else:
        st.info("💡 BTSB: — (SPD = 0)")
    
    st.markdown("---")
    
    # ============================================================
    # BAGIAN C: SO RAK (SEARCH + ADD)
    # ============================================================
    st.markdown("#### 📦 Stock Opname (Opsional)")
    st.caption("Cari rak, klik untuk menambahkan ke daftar SO")
    
    _search_query = st.text_input(
        "🔍 Cari Rak",
        key="input_rak_search",
        placeholder="Ketik kode rak (contoh: AT, AU, CHILLER)"
    )
    
    # Tampilkan hasil search
    if _search_query and len(_search_query.strip()) >= 2:
        _search_results = search_rak(_search_query, limit=10)
        
        if _search_results:
            st.caption(f"💡 {len(_search_results)} rak ditemukan:")
            
            for _idx, _rak in enumerate(_search_results):
                _rid = _rak.get("rak_id", "-")
                _rname = _rak.get("rak_name", "-")
                _status = _rak.get("status_so", "BELUM")
                
                _already_selected = any(
                    r["rak_id"] == _rid for r in st.session_state["selected_rak_list"]
                )
                
                col_r1, col_r2 = st.columns([4, 1])
                with col_r1:
                    _status_icon = "✅" if _status == "SELESAI" else "⬜"
                    st.markdown(
                        "<div class='rak-result-card'>"
                        "<div>"
                        "<div class='rak-result-id'>" + _status_icon + " " + _rid + "</div>"
                        "<div class='rak-result-name'>" + _rname + "</div>"
                        "</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                with col_r2:
                    if _already_selected:
                        st.button("✓ Ada", key=f"btn_add_{_idx}_{_rid}", disabled=True)
                    else:
                        if st.button("+ Add", key=f"btn_add_{_idx}_{_rid}"):
                            st.session_state["selected_rak_list"].append({
                                "rak_id": _rid,
                                "nominal_adjust": 0.0,
                            })
                            st.rerun()
        else:
            st.warning(f"⚠️ Rak **'{_search_query}'** tidak ditemukan.")
    elif _search_query and len(_search_query.strip()) < 2:
        st.info("💡 Ketik minimal **2 karakter**.")
    
    st.markdown("---")
    
    # ============================================================
    # BAGIAN D: LIST RAK TERPILIH + INPUT NOMINAL
    # ============================================================
    if st.session_state["selected_rak_list"]:
        st.markdown(f"#### 📋 Rak Terpilih ({len(st.session_state['selected_rak_list'])})")
        st.caption("Isi nominal adjustment per rak (bisa +/-)")
        
        _items_to_remove = []
        
        for _idx, _item in enumerate(st.session_state["selected_rak_list"]):
            _rid = _item["rak_id"]
            _rak_info = get_rak_by_kode_exact(_rid)
            _rname = _rak_info.get("rak_name", "-") if _rak_info else "-"
            
            col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
            
            with col_d1:
                st.markdown(
                    "<div style='"
                    "padding: 12px 14px;"
                    "background: rgba(15, 138, 114, 0.15);"
                    "border: 1.5px solid #7FB99B;"
                    "border-radius: 10px;"
                    "margin-top: 8px;"
                    "'>"
                    "<div style='"
                    "font-family: \"JetBrains Mono\", monospace;"
                    "font-size: 14px;"
                    "font-weight: 900;"
                    "color: #E8B189;"
                    "'>" + _rid + "</div>"
                    "<div style='"
                    "font-family: \"Quicksand\", sans-serif;"
                    "font-size: 10px;"
                    "color: #7a9b8e;"
                    "margin-top: 2px;"
                    "'>" + _rname + "</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
            
            with col_d2:
                _new_nominal = st.number_input(
                    f"Nominal #{_idx+1}",
                    min_value=-999999999,
                    max_value=999999999,
                    step=1000,
                    value=int(_item.get("nominal_adjust", 0)),
                    key=f"nominal_{_rid}_{_idx}",
                    label_visibility="collapsed"
                )
                st.session_state["selected_rak_list"][_idx]["nominal_adjust"] = float(_new_nominal)
            
            with col_d3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"btn_del_{_rid}_{_idx}"):
                    _items_to_remove.append(_idx)
        
        if _items_to_remove:
            for _i in sorted(_items_to_remove, reverse=True):
                st.session_state["selected_rak_list"].pop(_i)
            st.rerun()
        
        # Total nominal
        _total_nominal_input = sum(
            item.get("nominal_adjust", 0)
            for item in st.session_state["selected_rak_list"]
        )
        _color_total = "#E88B8B" if _total_nominal_input < 0 else "#7FB99B"
        _sign_total = "+" if _total_nominal_input >= 0 else ""
        
        st.markdown(
            "<div style='"
            "background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.85));"
            "border: 2px solid " + _color_total + ";"
            "border-radius: 12px;"
            "padding: 14px 20px;"
            "margin-top: 16px;"
            "text-align: center;"
            "'>"
            "<div style='"
            "font-family: monospace;"
            "font-size: 10px;"
            "color: #7a9b8e;"
            "letter-spacing: 1.5px;"
            "'>💰 TOTAL NOMINAL SO</div>"
            "<div style='"
            "font-family: \"JetBrains Mono\", monospace;"
            "font-size: 22px;"
            "font-weight: 900;"
            "color: " + _color_total + ";"
            "margin-top: 6px;"
            "'>" + _sign_total + fmt_rp(_total_nominal_input) + "</div>"
            "</div>",
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # ============================================================
    # BAGIAN E: KETERANGAN & PIC
    # ============================================================
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        _keterangan = st.text_input(
            "📝 Keterangan",
            placeholder="Contoh: Barang rusak, dll",
            key="input_keterangan"
        )
    
    with col_k2:
        # ✅ AUTO-FILL PIC dari shift hari ini
        _default_pic = st.session_state.get("input_pic", "")
        
        try:
            from modules.master_shift_handler import get_shift_hari_ini, KODE_SHIFT
            _shift_today_pic = get_shift_hari_ini(_tanggal)
            
            # Ambil nama yang shift P7/S15/M22 (bukan O/C/AO)
            _personil_aktif = [
                nama for nama, kode in _shift_today_pic.items()
                if kode in ["P7", "S15", "M22"]
            ]
            
            if _personil_aktif:
                _default_pic = ", ".join(_personil_aktif[:3])  # Max 3 nama
        except Exception:
            pass
        
        _pic = st.text_input(
            "👤 PIC (Nama) — auto dari shift",
            value=_default_pic,
            placeholder="Nama penanggung jawab",
            key="input_pic_autofill"
        )
    
    st.markdown("---")
    
    # ============================================================
    # BAGIAN F: TOMBOL SIMPAN
    # ============================================================
    if st.button(
        "💾 SIMPAN SEMUA",
        use_container_width=True,
        type="primary",
        key="btn_save_all"
    ):
        _has_spd = _spd_val > 0
        _has_so = len(st.session_state["selected_rak_list"]) > 0
        
        if not _has_spd and not _has_so:
            st.error("⚠️ Minimal isi SPD atau tambahkan 1 rak SO!")
        else:
            with st.spinner("⏳ Menyimpan data..."):
                _ok, _msg, _detail = save_input_harian(
                    tanggal=_tanggal,
                    spd=_spd_val,
                    rak_items=st.session_state["selected_rak_list"],
                    keterangan=_keterangan,
                    pic=_pic,
                    update_status_rak=True,
                )
            
            if _ok:
                st.success(_msg)
                st.balloons()
                
                with st.expander("📊 Detail Tersimpan", expanded=True):
                    if _detail.get("spd_saved"):
                        st.write(f"- 💰 SPD: {fmt_rp(_spd_val)}")
                    if _detail.get("rak_saved", 0) > 0:
                        st.write(f"- 📦 Rak di-SO: {_detail['rak_saved']}")
                        st.write(f"- ⚖️ Total Nominal: {fmt_rp(_detail.get('total_nominal', 0))}")
                
                st.session_state["selected_rak_list"] = []
                st.session_state["last_loaded_date"] = None
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()
            else:
                st.error(_msg)
    
    render_copyright()


# =========================================================================
# 📊 HALAMAN 3: ANALISIS
# =========================================================================
def render_analisis():
    """Render halaman analisis: BTSB, selisih, rak belum SO."""
    render_royal_header(show_clock=True)
    
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_analisis"):
            go_to_page("dashboard")
    
    st.markdown("### 📊 Analisis & Laporan")
    
    # ============================================================
    # LOAD DATA
    # ============================================================
    with st.spinner("⏳ Memuat data..."):
        rak_df = load_rak_master()
        so_df = load_so_hasil()
        _btsb_result = hitung_btsb_akumulatif()
        _akumulasi = get_akumulasi_nominal_bulan()
    
    if rak_df.empty:
        st.error("❌ Data rak kosong.")
        render_copyright()
        return
    
    # ============================================================
    # ANALISIS BTSB
    # ============================================================
    st.markdown("#### 💰 Analisis BTSB")
    
    _total_spd = _btsb_result["total_spd"]
    _btsb_akum = _btsb_result["btsb_akumulatif"]
    _total_nominal = _akumulasi["total_nominal"]
    
    _analisis = analisis_btsb_vs_selisih(_total_nominal, _btsb_akum)
    
    # Card besar status
    st.markdown(
        "<div class='metric-card-v2 fade-in-up' style='--accent-color: " + _analisis["warna"] + "; padding: 24px 28px;'>"
        "<div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;'>"
        "<div>"
        "<div class='metric-label-v2' style='font-size: 11px;'>⚖️ STATUS BTSB</div>"
        "<div style='font-family: \"Cinzel\", serif; font-size: 32px; font-weight: 900; "
        "color: " + _analisis["warna"] + "; text-shadow: 0 0 20px " + _analisis["warna"] + "; "
        "margin: 8px 0; letter-spacing: 3px;'>" + _analisis["icon"] + " " + _analisis["status"] + "</div>"
        "<div class='metric-sub-v2'>"
        "Penggunaan: <b style='color: " + _analisis["warna"] + ";'>" + f"{_analisis['persen_penggunaan']:.2f}%" + "</b> "
        "dari BTSB • Gap: <b>" + fmt_rp(_analisis["gap"]) + "</b>"
        "</div>"
        "</div>"
        "<div style='text-align: right;'>"
        "<div class='metric-label-v2'>Total Nominal SO</div>"
        "<div style='font-family: \"JetBrains Mono\", monospace; font-size: 22px; "
        "font-weight: 900; color: #E88B8B;'>" + fmt_rp(_total_nominal) + "</div>"
        "<div class='metric-label-v2' style='margin-top: 12px;'>BTSB Akumulatif</div>"
        "<div style='font-family: \"JetBrains Mono\", monospace; font-size: 22px; "
        "font-weight: 900; color: #0F8A72;'>" + fmt_rp(_btsb_akum) + "</div>"
        "</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )
    
    # 3 metric
    col_a1, col_a2, col_a3 = st.columns(3)
    
    with col_a1:
        render_metric_card(
            label="Total SPD Bulan Ini",
            value=fmt_rp_short(_total_spd),
            sub_text=f"{_btsb_result['jumlah_hari']} hari terinput",
            accent="#7FB99B",
            icon="📅"
        )
    
    with col_a2:
        render_metric_card(
            label="BTSB Akumulatif",
            value=fmt_rp_short(_btsb_akum),
            sub_text="0,15% × Total SPD",
            accent="#0F8A72",
            icon="🎯"
        )
    
    with col_a3:
        render_metric_card(
            label="Sisa Budget",
            value=fmt_rp_short(_analisis["gap"]),
            sub_text="BTSB - |Nominal SO|",
            accent="#E8B189",
            icon="💰"
        )
    
    st.markdown("---")
    
    # ============================================================
    # # ============================================================
    # LIST RAK BELUM SO (GRID COMPACT + SEARCH)
    # ============================================================
    st.markdown("#### 📋 Rak Belum SO")
    
    _rak_belum_df = get_rak_belum_so_df(rak_df)
    
    if not _rak_belum_df.empty:
        _jumlah_belum = len(_rak_belum_df)
        st.caption(f"⚠️ **{_jumlah_belum} rak** belum di-SO. Segera lakukan SO!")
        
        # ============================================
        # SEARCH BOX
        # ============================================
        _search_belum = st.text_input(
            "🔍 Cari Rak",
            key="search_rak_belum_so",
            placeholder="Ketik kode/nama rak (contoh: AT, CHILLER)",
            label_visibility="collapsed"
        )
        
        # Filter by search
        _rak_filtered_df = _rak_belum_df.copy()
        if _search_belum and len(_search_belum.strip()) >= 1:
            _q = _search_belum.strip().upper()
            _rak_filtered_df = _rak_filtered_df[
                _rak_filtered_df["rak_id"].astype(str).str.upper().str.contains(_q, na=False) |
                _rak_filtered_df["rak_name"].astype(str).str.upper().str.contains(_q, na=False)
            ]
        
        _jumlah_filtered = len(_rak_filtered_df)
        if _search_belum:
            st.caption(f"🔍 **{_jumlah_filtered}** rak ditemukan")
        
        # ============================================
        # GRID COMPACT
        # ============================================
        if not _rak_filtered_df.empty:
            # CSS Grid
            st.markdown("""
            <style>
                .rak-grid-container {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 8px;
                    margin-top: 12px;
                }
                @media (max-width: 768px) {
                    .rak-grid-container {
                        grid-template-columns: repeat(3, 1fr);
                        gap: 6px;
                    }
                }
                @media (max-width: 480px) {
                    .rak-grid-container {
                        grid-template-columns: repeat(2, 1fr);
                        gap: 6px;
                    }
                }
                .rak-mini-card {
                    background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
                    border: 1.5px solid #E88B8B;
                    border-left: 3px solid #E88B8B;
                    border-radius: 8px;
                    padding: 8px 10px;
                    text-align: center;
                    transition: all 0.25s ease;
                    cursor: pointer;
                }
                .rak-mini-card:hover {
                    border-color: #E8B189;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(232, 177, 137, 0.3);
                }
                .rak-mini-id {
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 13px;
                    font-weight: 900;
                    color: #E8B189;
                    letter-spacing: 1px;
                    margin-bottom: 2px;
                }
                .rak-mini-name {
                    font-family: 'Quicksand', sans-serif;
                    font-size: 8px;
                    color: #7a9b8e;
                    line-height: 1.2;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Build grid HTML
            _grid_html = "<div class='rak-grid-container'>"
            for _rak in _rak_filtered_df[["rak_id", "rak_name"]].to_dict("records"):
                _rid = str(_rak.get("rak_id", "-"))
                _rname = str(_rak.get("rak_name", "-"))[:20]
                _grid_html += (
                    "<div class='rak-mini-card'>"
                    "<div class='rak-mini-id'>" + _rid + "</div>"
                    "<div class='rak-mini-name'>" + _rname + "</div>"
                    "</div>"
                )
            _grid_html += "</div>"
            
            st.markdown(_grid_html, unsafe_allow_html=True)
        else:
            st.info(f"📭 Tidak ada rak yang match dengan **'{_search_belum}'**")
        
        st.markdown("---")
        
        # Download list (yang terfilter atau semua?)
        _list_download = _rak_filtered_df if _search_belum else _rak_belum_df
        _list_text = "\n".join([
            f"{r['rak_id']} — {r['rak_name']}"
            for r in _list_download[["rak_id", "rak_name"]].to_dict("records")
        ])
        
        _label_dl = (
            f"📥 Download List Rak Belum SO ({_jumlah_filtered} terfilter)"
            if _search_belum
            else f"📥 Download List Rak Belum SO ({_jumlah_belum} rak)"
        )
        
        st.download_button(
            label=_label_dl,
            data=_list_text,
            file_name=f"Rak_Belum_SO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
            key="dl_rak_belum"
        )
    else:
        st.success("🎉 **Semua rak sudah di-SO!** Mantap!")
        
    # ============================================================
    # CHART: SELISIH PER RAK (dari so_rak_harian)
    # ============================================================
    _detail_so = get_so_rak_detail(limit=500)
    
    if _detail_so:
        st.markdown("#### 📈 Nominal SO per Rak")
        
        try:
            import plotly.graph_objects as go
            
            _df_so = pd.DataFrame(_detail_so)
            _df_so["nominal_adjust"] = pd.to_numeric(_df_so["nominal_adjust"], errors="coerce").fillna(0)
            
            _grp = _df_so.groupby("rak_id")["nominal_adjust"].sum().reset_index()
            _grp = _grp.sort_values("nominal_adjust", ascending=True)
            _grp = _grp.head(20)  # Top 20
            
            _colors = ["#E88B8B" if v < 0 else "#7FB99B" for v in _grp["nominal_adjust"]]
            
            _fig = go.Figure()
            _fig.add_trace(go.Bar(
                x=_grp["nominal_adjust"],
                y=_grp["rak_id"],
                orientation="h",
                marker=dict(color=_colors, line=dict(color="#B87333", width=1.5)),
                text=_grp["nominal_adjust"],
                textposition="outside",
                textfont=dict(color="#E8B189", size=11, family="JetBrains Mono"),
                hovertemplate="<b>%{y}</b><br>Nominal: %{x:+,.0f}<extra></extra>",
            ))
            
            _fig.update_layout(
                height=max(300, len(_grp) * 30),
                margin=dict(l=10, r=40, t=20, b=20),
                plot_bgcolor="rgba(10, 22, 18, 0.4)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E8B189", family="JetBrains Mono", size=11),
                xaxis=dict(
                    title="Nominal (Rp)",
                    gridcolor="rgba(232, 177, 137, 0.15)",
                    zeroline=True,
                    zerolinecolor="#E8B189",
                    zerolinewidth=2,
                ),
                yaxis=dict(gridcolor="rgba(232, 177, 137, 0.15)", autorange="reversed"),
                showlegend=False,
            )
            
            st.plotly_chart(_fig, use_container_width=True, key="chart_nominal_per_rak")
        except Exception as e:
            st.warning(f"⚠️ Chart gagal render: {str(e)[:100]}")
    else:
        st.info("📭 Belum ada data SO untuk dianalisis.")
    
    render_copyright()


# =========================================================================
# 📥 HALAMAN 4: DOWNLOAD LAPORAN
# =========================================================================
def render_download():
    """Render halaman download laporan."""
    render_royal_header(show_clock=True)
    
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_download"):
            go_to_page("dashboard")
    
    st.markdown("### 📥 Download Laporan")
    st.caption("Export data ke Excel atau PDF")
    
    rak_df = load_rak_master()
    so_df = load_so_hasil()
    spd_df = load_spd_harian()
    _akumulasi = get_akumulasi_nominal_bulan()
    _detail_so = get_so_rak_detail(limit=1000)
    
    if rak_df.empty:
        st.error("❌ Data rak kosong.")
        render_copyright()
        return
    
    # ============================================================
    # EXPORT EXCEL
    # ============================================================
    st.markdown("#### 📊 Export Excel")
    
    try:
        import io
        
        _output = io.BytesIO()
        
        with pd.ExcelWriter(_output, engine="xlsxwriter") as _writer:
            # Sheet 1: Rak Master
            _df_rak = rak_df[["rak_id", "rak_name", "kategori", "pic", "status_so", "last_so_date"]].copy()
            _df_rak.columns = ["Kode Rak", "Nama Rak", "Kategori", "PIC", "Status SO", "Tanggal SO"]
            _df_rak.to_excel(_writer, sheet_name="Rak", index=False)
            
            # Sheet 2: SO Rak Harian
            if _detail_so:
                _df_so = pd.DataFrame(_detail_so)
                _cols = ["so_date", "rak_id", "nominal_adjust", "pic", "keterangan"]
                _cols = [c for c in _cols if c in _df_so.columns]
                _df_so = _df_so[_cols]
                _df_so.columns = ["Tanggal", "Kode Rak", "Nominal (Rp)", "PIC", "Keterangan"][:len(_df_so.columns)]
                _df_so.to_excel(_writer, sheet_name="SO Rak", index=False)
            
            # Sheet 3: SPD
            if not spd_df.empty:
                _df_spd = spd_df[["tanggal", "spd", "keterangan"]].copy()
                _df_spd.columns = ["Tanggal", "SPD (Rp)", "Keterangan"]
                _df_spd.to_excel(_writer, sheet_name="SPD", index=False)
            
            # Sheet 4: Summary
            _btsb_result = hitung_btsb_akumulatif()
            _analisis = analisis_btsb_vs_selisih(_akumulasi["total_nominal"], _btsb_result["btsb_akumulatif"])
            
            _summary_data = {
                "Metric": [
                    "Total SPD Bulan Ini",
                    "BTSB Akumulatif",
                    "Total Nominal SO",
                    "Sisa Budget",
                    "Status",
                    "Rak Selesai SO",
                    "Rak Belum SO",
                ],
                "Nilai": [
                    fmt_rp(_btsb_result["total_spd"]),
                    fmt_rp(_btsb_result["btsb_akumulatif"]),
                    fmt_rp(_akumulasi["total_nominal"]),
                    fmt_rp(_analisis["gap"]),
                    f"{_analisis['icon']} {_analisis['status']}",
                    f"{len(rak_df[rak_df['status_so'] == 'SELESAI'])} rak",
                    f"{len(rak_df[rak_df['status_so'] == 'BELUM'])} rak",
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
        
        st.success(f"✅ File siap: **{_filename}**")
    
    except Exception as e:
        st.error(f"❌ Gagal generate Excel: {str(e)[:150]}")
    
    st.markdown("---")
    
    # ============================================================
    # EXPORT PDF
    # ============================================================
    st.markdown("#### 📄 Export PDF")
    st.caption("PDF ringkasan siap cetak")
    
    if st.button("📄 Generate PDF", use_container_width=True, key="btn_gen_pdf"):
        with st.spinner("⏳ Membuat PDF..."):
            try:
                from fpdf import FPDF
                
                _pdf = FPDF()
                _pdf.add_page()
                _pdf.set_auto_page_break(auto=True, margin=15)
                
                _pdf.set_font("Helvetica", "B", 16)
                _pdf.cell(0, 10, "LAPORAN STOCK OPNAME", ln=True, align="C")
                _pdf.set_font("Helvetica", "", 10)
                _pdf.cell(0, 5, "Toko C383 - Karang Satria", ln=True, align="C")
                _pdf.cell(0, 5, f"Generated: {datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%d/%m/%Y %H:%M:%S WIB')}", ln=True, align="C")
                _pdf.ln(10)
                
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
                
                _pdf.cell(0, 6, f"Total SPD: {fmt_rp(_btsb_result['total_spd'])}", ln=True)
                _pdf.cell(0, 6, f"BTSB Akumulatif: {fmt_rp(_btsb_result['btsb_akumulatif'])}", ln=True)
                _pdf.cell(0, 6, f"Total Nominal SO: {fmt_rp(_akumulasi['total_nominal'])}", ln=True)
                
                _analisis = analisis_btsb_vs_selisih(_akumulasi["total_nominal"], _btsb_result["btsb_akumulatif"])
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
                st.success("✅ PDF siap!")
            
            except ImportError:
                st.error("❌ Library `fpdf2` belum terinstall.")
            except Exception as e:
                st.error(f"❌ Gagal: {str(e)[:150]}")
    
    render_copyright()


# =========================================================================
# 🔄 HALAMAN 5: REFRESH
# =========================================================================
def render_refresh():
    """Halaman refresh — clear cache & reload data."""
    render_royal_header(show_clock=True)
    
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Dashboard", key="btn_back_from_refresh"):
            go_to_page("dashboard")
    
    st.markdown("### 🔄 Refresh Data")
    st.caption("Muat ulang data dari Supabase")
    
    st.markdown("---")
    
    # Info card
    st.markdown(
        "<div class='metric-card-v2' style='--accent-color: #7FB99B; padding: 20px 24px;'>"
        "<div class='metric-label-v2'>ℹ️ INFO</div>"
        "<div style='font-family: \"Quicksand\", sans-serif; font-size: 12px; "
        "color: #e8f3ee; margin-top: 8px; line-height: 1.6;'>"
        "Refresh akan memuat ulang data dari Supabase. Gunakan ini kalau "
        "ada perubahan data di database yang belum muncul di dashboard."
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )
    
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
            st.session_state["last_loaded_date"] = None
            st.session_state["selected_rak_list"] = []
            time.sleep(1.5)
        st.success("✅ Data berhasil di-refresh!")
        st.balloons()
        time.sleep(1.5)
        go_to_page("dashboard")
    
    render_copyright()


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