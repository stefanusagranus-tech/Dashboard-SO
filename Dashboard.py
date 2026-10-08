"""
Dashboard Stock Opname — Homepage Only
=======================================
Toko C383 - Karang Satria

Homepage:
- Header banner
- Shift hari ini
- Summary metric (SPD, NSB, Status, Progres SO)
- Notifikasi input SO
- Menu card (SO, Master Shift, Chat AI)
- Footer

Halaman lain:
- pages/so.py             — Input SO + Analisis + Preview
- pages/master_shift.py   — Shift management + Hana + OCR
- pages/ai_chat_kurumi.py — Chat Kurumi
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from themes.theme_loader import (
    render_theme,
    render_theme_animations,
    render_greeting,
    get_theme_by_month,
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
        hitung_btsb_harian,
        hitung_btsb_akumulatif,
        analisis_btsb_vs_selisih,
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
# HELPER FUNCTIONS
# =========================================================================
def render_royal_header(show_clock=True):
    """Render header banner dengan emoji Halloween."""
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _time_str = _now.strftime("%H:%M")

    _day_map = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
                "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"}
    _month_map = {"January": "Januari", "February": "Februari", "March": "Maret",
                  "April": "April", "May": "Mei", "June": "Juni", "July": "Juli",
                  "August": "Agustus", "September": "September", "October": "Oktober",
                  "November": "November", "December": "Desember"}
    _day_id = _day_map.get(_now.strftime("%A"), _now.strftime("%A"))
    _month_id = _month_map.get(_now.strftime("%B"), _now.strftime("%B"))
    _date_id = f"{_day_id}, {_now.day} {_month_id} {_now.year}"

    _clock_html = ""
    if show_clock:
        _clock_html = (
            "<div class='header-clock'>"
            "<div class='clock-time'>🕐 " + _time_str + " WIB</div>"
            "<div class='clock-date'>🎃 " + _date_id + " 👻</div>"
            "</div>"
        )

    _header_html = (
        "<div class='royal-header fade-in-up'>"
        "<div class='royal-ornament royal-orn-tl'>🎃</div>"
        "<div class='royal-ornament royal-orn-tr'>👻</div>"
        "<div class='royal-ornament royal-orn-bl'>🦇</div>"
        "<div class='royal-ornament royal-orn-br'>🕷️</div>"
        "<div class='royal-title'>🎃 DASHBOARD STOCK OPNAME 🎃</div>"
        "<div class='royal-subtitle'>⚜ Toko C383 - Karang Satria ⚜</div>"
        + _clock_html +
        "</div>"
    )

    st.markdown(_header_html, unsafe_allow_html=True)


def render_copyright():
    st.markdown("""
    <div class='copyright-footer'>
        🎃 Dashboard SO KGS V.2 — Halloween Edition 👻
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
    """Render menu card — pake st.switch_page buat multipage."""
    st.markdown(f"""
    <div class='menu-card-v2' style='--accent-color: {accent}; --accent-glow: {accent_glow};'>
        <div class='menu-icon-v2'>{icon}</div>
        <div class='menu-title-v2'>{title}</div>
        <div class='menu-desc-v2'>{desc}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Masuk →", key=key, width="stretch"):
        # ✅ FIX: Pakai st.switch_page buat multipage
        try:
            if target_page == "so":
                st.switch_page("pages/so.py")
            elif target_page == "master_shift":
                st.switch_page("pages/master_shift.py")
            elif target_page == "chat_kurumi":
                st.switch_page("pages/ai_chat_kurumi.py")
            else:
                st.warning(f"⚠️ Halaman '{target_page}' tidak dikenal")
        except Exception as _e:
            st.error(f"⚠️ Gagal pindah: {_e}")


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


# =========================================================================
# 🏠 HOMEPAGE
# =========================================================================
def render_dashboard():
    """Render homepage — Hybrid: Hari Ini + Akumulasi + Trend."""
    render_royal_header()

    # ============================================================
    # LOAD DATA
    # ============================================================
    with st.spinner("⏳ Memuat data..."):
        rak_df = load_rak_master()
        so_df = load_so_hasil()
        _akumulasi = get_akumulasi_nominal_bulan()
        _trend = get_nominal_per_hari(limit=30)   # ✅ FIX M15: limit 30 hari
        _detail_so = get_so_rak_detail(limit=20)
        _btsb_result = hitung_btsb_akumulatif()

    if rak_df.empty:
        st.error("❌ **Data rak kosong!**")
        st.info("💡 Pastikan tabel `rak_master` di Supabase sudah di-import.")
        render_copyright()
        return

    # ============================================================
    # 👥 SHIFT HARI INI
    # ============================================================
    _shift_today_ada = False
    try:
        from modules.master_shift_handler import get_shift_hari_ini, KODE_SHIFT

        _shift_today = get_shift_hari_ini()

        if _shift_today:
            _shift_today_ada = True
            st.markdown("### 👥 Personil Shift Hari Ini")

            _grouped = {}
            for _nama, _kode in _shift_today.items():
                _grouped.setdefault(_kode, []).append(_nama)

            _urutan_kode = ["P7", "S15", "M22", "O", "C", "AO"]
            _cols_shift = st.columns(3)   # ✅ FIX H11: 3 kolom (2 baris x 3)

            _col_idx = 0
            for _kode in _urutan_kode:
                if _kode not in _grouped:
                    continue

                _info = KODE_SHIFT.get(_kode, {"label": _kode, "warna": "#CCCCCC", "icon": "❓"})
                _nama_list = _grouped[_kode]
                _nama_str = ", ".join(sorted(_nama_list))

                with _cols_shift[_col_idx % 3]:
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
                        f"'>{_info['icon']} {_info['label'].upper()}</div>"
                        f"<div style='"
                        f"font-family: Quicksand, sans-serif;"
                        f"font-size: 12px;"
                        f"color: #e8f3ee;"
                        f"font-weight: 700;"
                        f"line-height: 1.5;"
                        f"'>{_nama_str}</div>"
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
    # REMINDER kalau belum ada shift
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
            "'>⚠️ BELUM ADA SHIFT HARI INI</div>"
            "<div style='"
            "font-family: Quicksand, sans-serif;"
            "font-size: 11px;"
            "color: #fde68a;"
            "margin-top: 6px;"
            "line-height: 1.5;"
            "'>Jadwal shift belum di-set. "
            "Buka halaman <b>📅 Master Shift</b> untuk update jadwal, "
            "atau ketik langsung via Chat AI.</div>"
            "</div>",
            unsafe_allow_html=True
        )

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

        _total_spd_akum = _btsb_result["total_spd"]
        _pct_nsb_sales = (abs(_total_nominal) / _total_spd_akum * 100) if _total_spd_akum > 0 else 0.0

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

    st.markdown("---")

    # ============================================================
    # MENU CARD
    # ============================================================
    st.markdown("### 📋 Pilih Menu")

    col_menu1, col_menu2 = st.columns(2)

    with col_menu1:
        render_menu_card(
            icon="📝",
            title="Stock Opname",
            desc="Input SO + Analisis<br>+ Preview dalam 1 halaman",
            accent="#7FB99B",
            accent_glow="rgba(127, 185, 155, 0.6)",
            key="btn_menu_so",
            target_page="so"
        )

    with col_menu2:
        render_menu_card(
            icon="📅",
            title="Master Shift",
            desc="Kelola jadwal shift<br>dengan Hana AI",
            accent="#a855f7",
            accent_glow="rgba(168, 85, 247, 0.6)",
            key="btn_menu_master_shift",
            target_page="master_shift"
        )

    col_menu3, col_menu4 = st.columns(2)

    with col_menu3:
        render_menu_card(
            icon="🎀",
            title="Chat Kurumi",
            desc="Chief of Staff<br>siap bantu 24/7",
            accent="#E8B189",
            accent_glow="rgba(232, 177, 137, 0.6)",
            key="btn_menu_kurumi",
            target_page="chat_kurumi"
        )

    with col_menu4:
        st.markdown("""
        <div style='
            background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
            border: 2px solid #7FB99B;
            border-radius: 12px;
            padding: 16px 14px;
            text-align: center;
            margin-bottom: 8px;
            min-height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
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

        if st.button("🔄 Refresh", key="btn_menu_refresh", width="stretch"):
            with st.spinner("⏳ Refresh..."):
                clear_cache()
                st.cache_data.clear()
                import time
                time.sleep(1)
            st.success("✅ Data di-refresh!")
            st.rerun()

    render_copyright()

# =========================================================================
# 🎯 ROUTING UTAMA
# =========================================================================
def main():
    """Main router — homepage only (multipage via pages/)."""
    render_dashboard()


# =========================================================================
# RUN APP
# =========================================================================
if __name__ == "__main__":
    main()