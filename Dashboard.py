"""
Dashboard Stock Opname — Homepage
==================================
Toko C383 - Karang Satria

Homepage only:
- Header banner
- Shift hari ini
- Summary metric (SPD, NSB, Status, Progres SO)
- Notifikasi input SO
- Running text input terakhir
- Menu card (SO, Master Shift, Chat AI)
- Footer

Halaman lain: pages/so.py, pages/master_shift.py, pages/ai_chat_kurumi.py
"""

import streamlit as st
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from themes.theme_loader import (
    render_theme, render_theme_animations, render_greeting, get_theme_by_month,
)

# =========================================================================
# KONFIGURASI
# =========================================================================
st.set_page_config(
    page_title="Dashboard SO | Toko C383",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CURRENT_THEME = get_theme_by_month()
render_theme(CURRENT_THEME)
render_theme_animations(CURRENT_THEME)
render_greeting()

# =========================================================================
# IMPORT MODULES
# =========================================================================
try:
    from modules.data_loader import load_rak_master, load_so_hasil, clear_cache
    from modules.rak_monitor import hitung_progress_so
    from modules.spd_calculator import (
        hitung_btsb_akumulatif, analisis_btsb_vs_selisih,
    )
    from modules.input_handler import (
        get_akumulasi_nominal_bulan,
        get_nominal_per_hari,
        get_so_rak_detail,
        get_so_hari_ini,
        get_spd_hari_ini,
    )
except ImportError as e:
    st.error(f"❌ Gagal import modul: {e}")
    st.stop()

# =========================================================================
# HELPER FUNCTIONS (existing, keep)
# =========================================================================
# === SHIFT HARI INI ===
_urutan_kode = ["P7", "S15", "M22", "O", "C", "AO"]
_cols_shift = st.columns(3)  # ✅ FIX H11: 3 kolom (2 baris x 3 kolom = 6 slot)

_col_idx = 0
for _kode in _urutan_kode:
    if _kode not in _grouped:
        continue
    
    _info = KODE_SHIFT.get(_kode, {"label": _kode, "warna": "#CCCCCC", "icon": "❓"})
    _nama_list = _grouped[_kode]
    _nama_str = ", ".join(sorted(_nama_list))
    
    with _cols_shift[_col_idx % 3]:  # ✅ Modulo 3
        st.markdown(
            f"<div style='background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));"
            f"border: 2px solid {_info['warna']};"
            f"border-left: 5px solid {_info['warna']};"
            f"border-radius: 12px;"
            f"padding: 14px 16px;"
            f"margin-bottom: 10px;"
            f"box-shadow: 0 4px 12px rgba(0,0,0,0.4);'>"
            f"<div style='font-family: JetBrains Mono, monospace; font-size: 11px;"
            f"color: {_info['warna']}; letter-spacing: 1.5px; font-weight: 900;"
            f"margin-bottom: 8px;'>{_info['icon']} {_info['label'].upper()}</div>"
            f"<div style='font-family: Quicksand, sans-serif; font-size: 12px;"
            f"color: #e8f3ee; font-weight: 700; line-height: 1.5;'>{_nama_str}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    _col_idx += 1

# =========================================================================
# 🏠 HOMEPAGE ONLY
# =========================================================================
def render_dashboard():
    """Render homepage — Hybrid: Hari Ini + Akumulasi + Trend."""
    render_royal_header()
    
    # Load data
    with st.spinner("⏳ Memuat data..."):
        rak_df = load_rak_master()
        so_df = load_so_hasil()
        _akumulasi = get_akumulasi_nominal_bulan()
        _btsb_result = hitung_btsb_akumulatif()
        _progress = hitung_progress_so(rak_df, so_df)
        _so_today = get_so_hari_ini()
        _spd_today = get_spd_hari_ini()
    
    # ... (render shift, metric, menu card — keep existing)
    
    render_copyright()

# =========================================================================
# ROUTING — CUMA HOMEPAGE
# =========================================================================
def main():
    render_dashboard()

if __name__ == "__main__":
    main()