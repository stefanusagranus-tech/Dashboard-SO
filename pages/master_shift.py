"""
Master Shift Page
=================
Halaman untuk kelola master shift dengan Chat AI.

Kode shift:
- P7  = Pagi jam 07:00
- S15 = Siang jam 15:00
- M22 = Malam jam 22:00
- O   = Off (Libur)
- C   = Cuti
- AO  = Additional Off
"""

import streamlit as st
import pandas as pd
import time
import io                                       
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from PIL import Image as PILImage                

# =========================================================================
# KONFIGURASI HALAMAN
# =========================================================================
st.set_page_config(
    page_title="Master Shift | Toko C383",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================================
# CUSTOM CSS — SAMA DENGAN DASHBOARD UTAMA
# =========================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700;900&display=swap');

    /* Hide sidebar */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarNav"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    .stDeployButton,
    #MainMenu,
    footer {
        display: none !important;
    }

    :root {
        --emerald: #0F8A72;
        --emerald-light: #7FB99B;
        --copper: #B87333;
        --copper-light: #E8B189;
        --bg-dark: #0a1612;
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

    /* BUTTONS */
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

    /* FORM INPUT */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: rgba(10, 22, 18, 0.95) !important;
        border: 2px solid var(--copper) !important;
        border-radius: 10px !important;
        min-height: 44px !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span,
    div[data-baseweb="textarea"] textarea {
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

    /* SUB-TAB NAVIGATION */
    .shift-subtab-btn {
        display: flex;
        gap: 8px;
        justify-content: center;
        margin-bottom: 20px;
    }

    /* PREVIEW CARD */
    .preview-card {
        background: linear-gradient(135deg, rgba(10, 22, 18, 0.98), rgba(15, 31, 26, 0.92));
        border: 2px solid #7FB99B;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 10px 0;
    }
    .preview-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #7FB99B;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px dashed rgba(127, 185, 155, 0.3);
    }

    .warning-box {
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(245, 158, 11, 0.15));
        border: 2px solid #fbbf24;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 10px 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #fcd34d;
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
        .main .block-container { padding: 0.5rem 1rem 5rem 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# IMPORT MODULE
# =========================================================================
try:
    from modules.master_shift_handler import (
        load_personil_master,
        add_personil,
        update_personil_status,
        parse_chat_update,
        save_master_shift,
        load_master_shift_matrix,
        get_shift_hari_ini,
        generate_master_shift_excel,
        delete_master_shift_by_date,
        KODE_SHIFT,
        NAMA_BULAN_ID,
    )
except ImportError as e:
    st.error(f"❌ Gagal import `master_shift_handler`: {e}")
    st.info("💡 Pastikan file `modules/master_shift_handler.py` udah di-upload.")
    st.stop()


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================
def render_royal_header(show_clock=True):
    """Render header banner royal."""
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
        "<div class='royal-title'>📅 MASTER SHIFT 📅</div>"
        "<div class='royal-subtitle'>⚜ Kelola Jadwal dengan Chat AI ⚜</div>"
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


def go_home():
    """Kembali ke Dashboard utama."""
    try:
        st.switch_page("Dashboard.py")
    except Exception as e:
        st.warning(f"⚠️ Gagal pindah halaman: {e}")


# =========================================================================
# 🎯 RENDER HALAMAN MASTER SHIFT
# =========================================================================
render_royal_header(show_clock=True)

# Back button
col_back, _ = st.columns([1, 4])
with col_back:
    if st.button("← Dashboard", key="btn_back_shift_home"):
        go_home()

# =========================================================================
# 🎛️ SUB-TAB NAVIGATION
# =========================================================================
st.markdown("---")

if "shift_sub_tab" not in st.session_state:
    st.session_state["shift_sub_tab"] = "chat"

col_t1, col_t2, col_t3, col_t4, col_t5, col_t6 = st.columns(6)

with col_t1:
    if st.button(
        "💬 Chat Update",
        use_container_width=True,
        key="btn_shift_tab_chat",
        type="primary" if st.session_state["shift_sub_tab"] == "chat" else "secondary",
    ):
        st.session_state["shift_sub_tab"] = "chat"
        st.rerun()

with col_t2:
    if st.button(
        "📊 Matrix View",
        use_container_width=True,
        key="btn_shift_tab_matrix",
        type="primary" if st.session_state["shift_sub_tab"] == "matrix" else "secondary",
    ):
        st.session_state["shift_sub_tab"] = "matrix"
        st.rerun()

with col_t3:
    if st.button(
        "👥 Personil",
        use_container_width=True,
        key="btn_shift_tab_personil",
        type="primary" if st.session_state["shift_sub_tab"] == "personil" else "secondary",
    ):
        st.session_state["shift_sub_tab"] = "personil"
        st.rerun()

with col_t4:
    if st.button(
        "📥 Download",
        use_container_width=True,
        key="btn_shift_tab_download",
        type="primary" if st.session_state["shift_sub_tab"] == "download" else "secondary",
    ):
        st.session_state["shift_sub_tab"] = "download"
        st.rerun()
with col_t5:
    if st.button(
        "📸 Screenshot",
        use_container_width=True,
        key="btn_shift_tab_screenshot",
        type="primary" if st.session_state["shift_sub_tab"] == "screenshot" else "secondary",
    ):
        st.session_state["shift_sub_tab"] = "screenshot"
        st.rerun()
with col_t6:
    if st.button(
        "📊 Usage",
        use_container_width=True,
        key="btn_shift_tab_usage",
        type="primary" if st.session_state["shift_sub_tab"] == "usage" else "secondary",
    ):
        st.session_state["shift_sub_tab"] = "usage"
        st.rerun()
        
st.markdown("---")


# ============================================================
# TAB 1: CHAT UPDATE
# ============================================================
if st.session_state["shift_sub_tab"] == "chat":
    st.markdown("### 💬 Chat Update Master Shift")
    st.caption("💡 Ketik update dalam bahasa natural. AI akan parse otomatis.")

    _placeholder = (
        "Besok Tika libur, ganti jadi:\n"
        "- Pagi: Reza, Pandu\n"
        "- Siang: Zaki\n"
        "- Malam: Kusdewi\n"
        "- Libur: Tika, Adel"
    )

    _chat_input = st.text_area(
        "📝 Ketik update:",
        placeholder=_placeholder,
        height=180,
        key="chat_shift_input",
    )

    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        _btn_proses = st.button(
            "🤖 PROSES CHAT",
            use_container_width=True,
            type="primary",
            key="btn_chat_proses",
        )
    with col_btn2:
        if st.button("🗑️ Clear", use_container_width=True, key="btn_chat_clear"):
            st.session_state["chat_shift_parsed"] = None
            st.rerun()

    if _btn_proses and _chat_input.strip():
        with st.spinner("⏳ Parsing chat..."):
            _parsed = parse_chat_update(
                _chat_input,
                datetime.now(ZoneInfo("Asia/Jakarta")).date()
            )
        st.session_state["chat_shift_parsed"] = _parsed
        st.rerun()
    elif _btn_proses and not _chat_input.strip():
        st.warning("⚠️ Chat kosong. Ketik dulu update-nya.")

    # Tampilkan hasil parse
    if st.session_state.get("chat_shift_parsed"):
        _parsed = st.session_state["chat_shift_parsed"]
        _mode = _parsed.get("mode", "update")   # ✅ DETEKSI MODE
    
        # Warning (kalau ada)
        if _parsed.get("warning"):
            st.markdown(
                f"<div class='warning-box'>⚠️ {_parsed['warning']}</div>",
                unsafe_allow_html=True
            )
    
        # ============================================
        # 🗑️ MODE DELETE — HAPUS SHIFT
        # ============================================
        if _mode == "delete":
            _targets = _parsed.get("delete_targets", [])
            _all_dates = _parsed.get("delete_all_dates", False)
    
            st.markdown("#### 🗑️ Preview Hapus Shift")
    
            if not _targets:
                st.warning("⚠️ Tidak ada nama yang terdeteksi untuk dihapus.")
                st.caption("Contoh: `Hapus shift TIA hari ini`")
            else:
                st.info(f"👤 **Nama target:** {', '.join(_targets)}")
    
                if _all_dates:
                    st.warning("📅 **Mode:** Hapus **SEMUA tanggal** untuk nama ini!")
                else:
                    st.info(
                        f"📅 **Mode:** Hapus hanya tanggal "
                        f"**{_parsed['tanggal'].strftime('%d/%m/%Y')}**"
                    )
    
                # Pilihan tanggal (kalau bukan all_dates)
                if not _all_dates:
                    _tanggal_hapus = st.date_input(
                        "📅 Tanggal yang dihapus:",
                        value=_parsed["tanggal"],
                        key="chat_delete_tanggal",
                    )
                else:
                    _tanggal_hapus = None
    
                # Preview tabel
                _preview_data = []
                for _t in _targets:
                    _preview_data.append({
                        "👤 Nama": _t,
                        "📅 Mode": (
                            "Semua Tanggal" if _all_dates 
                            else _parsed["tanggal"].strftime("%d/%m/%Y")
                        ),
                    })
                st.dataframe(
                    pd.DataFrame(_preview_data),
                    use_container_width=True,
                    hide_index=True
                )
    
                # Tombol konfirmasi
                col_del1, col_del2 = st.columns([2, 1])
    
                with col_del1:
                    if st.button(
                        "🗑️ KONFIRMASI HAPUS",
                        use_container_width=True,
                        type="primary",
                        key="btn_delete_confirm",
                    ):
                        # Import fungsi delete
                        from modules.master_shift_handler import (
                            delete_shift_by_name,
                            delete_shift_all_dates,
                        )
    
                        _total_deleted = 0
    
                        with st.spinner("⏳ Menghapus..."):
                            if _all_dates:
                                for _t in _targets:
                                    _ok, _msg = delete_shift_all_dates(_t)
                                    if _ok:
                                        _total_deleted += 1
                            else:
                                _ok, _msg, _detail = delete_shift_by_name(
                                    _tanggal_hapus, _targets
                                )
                                _total_deleted = _detail.get("deleted", 0)
    
                        if _total_deleted > 0:
                            st.success(f"🗑️ {_total_deleted} shift berhasil dihapus!")
                            st.balloons()
                            st.session_state["chat_shift_parsed"] = None
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.warning("⚠️ Tidak ada yang dihapus.")
    
                with col_del2:
                    if st.button(
                        "❌ BATAL",
                        use_container_width=True,
                        key="btn_delete_cancel",
                    ):
                        st.session_state["chat_shift_parsed"] = None
                        st.rerun()
    
        # ============================================
        # ✅ MODE UPDATE — SIMPAN SHIFT (yang sudah ada)
        # ============================================
        else:
            st.success(
                f"✅ Tanggal terdeteksi: **{_parsed['tanggal'].strftime('%d/%m/%Y')}** "
                f"({_parsed.get('tanggal_detect', '-')})"
            )
    
            if _parsed["shift_map"]:
                st.markdown("#### 📊 Preview Perubahan:")
    
                _preview_rows = []
                for _nama, _kode in _parsed["shift_map"].items():
                    _info = KODE_SHIFT.get(
                        _kode, {"label": "-", "icon": "❓", "warna": "#CCCCCC"}
                    )
                    _preview_rows.append({
                        "👤 Nama": _nama,
                        "📝 Kode": _kode,
                        "📋 Keterangan": _info["label"],
                        "🎨 Icon": _info["icon"],
                    })
    
                _preview_df = pd.DataFrame(_preview_rows)
                st.dataframe(_preview_df, use_container_width=True, hide_index=True)
    
                st.markdown("##### 📅 Konfirmasi Tanggal:")
                _tanggal_final = st.date_input(
                    "Tanggal yang akan disimpan:",
                    value=_parsed["tanggal"],
                    key="chat_shift_tanggal_final",
                )
    
                _catatan = st.text_input(
                    "📝 Catatan (opsional):",
                    placeholder="Contoh: Ganti shift dadakan",
                    key="chat_shift_catatan",
                )
    
                col_save1, col_save2 = st.columns([2, 1])
    
                with col_save1:
                    if st.button(
                        "💾 KONFIRMASI SIMPAN",
                        use_container_width=True,
                        type="primary",
                        key="btn_chat_save",
                    ):
                        with st.spinner("⏳ Menyimpan..."):
                            _ok, _msg = save_master_shift(
                                tanggal=_tanggal_final,
                                shift_map=_parsed["shift_map"],
                                sumber="chat",
                                catatan=f"{_catatan} | Raw: {_parsed['raw_text'][:200]}",
                            )
    
                        if _ok:
                            st.success(_msg)
                            st.balloons()
                            st.session_state["chat_shift_parsed"] = None
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(_msg)
    
                with col_save2:
                    if st.button(
                        "❌ BATAL",
                        use_container_width=True,
                        key="btn_chat_cancel",
                    ):
                        st.session_state["chat_shift_parsed"] = None
                        st.rerun()
            else:
                st.warning(
                    "⚠️ Tidak ada data shift yang ke-parse. Cek format chat."
                )
    
        with st.expander("📖 Format Chat yang Didukung"):
            st.markdown("""
            **1. Format Multi-Shift (Utama):**
            ```
            Besok Tika libur, ganti jadi:
            - Pagi: Reza, Pandu
            - Siang: Zaki
            - Malam: Kusdewi
            - Libur: Tika, Adel
            ```
    
            **2. Format Simple (1 Shift):**
            ```
            Tika libur besok
            Zaki sakit hari ini
            ```
    
            **3. Format Tanggal Eksplisit:**
            ```
            05/10: Tika libur
            05-10-2026: Rotasi shift pagi
            ```
    
            **4. Keyword yang Didukung:**
            - `pagi` → P7
            - `siang` → S15
            - `malam` → M22
            - `libur` / `off` → O
            - `cuti` → C
            - `ao` / `additional off` → AO
            """)

# ============================================================
# TAB 2: MATRIX VIEW (2 TABEL — TGL 1-15 & 16-31)
# ============================================================
elif st.session_state["shift_sub_tab"] == "matrix":
    st.markdown("### 📊 Master Shift (Matrix)")
    st.caption("💡 Tabel dipecah 2 bagian (mirip Excel master shift)")

    col_b1, col_b2, col_b3 = st.columns([2, 1, 1])

    with col_b1:
        _bulan_pilihan = st.selectbox(
            "📅 Bulan",
            options=list(NAMA_BULAN_ID.keys()),
            format_func=lambda x: NAMA_BULAN_ID[x],
            index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
            key="matrix_bulan",
        )
    with col_b2:
        _tahun_pilihan = st.number_input(
            "📆 Tahun",
            min_value=2024,
            max_value=2100,
            value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
            key="matrix_tahun",
        )
    with col_b3:
        if st.button("🔄 Refresh", use_container_width=True, key="btn_matrix_refresh"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("⏳ Load matrix..."):
        _matrix_df = load_master_shift_matrix(_bulan_pilihan, _tahun_pilihan)

    if _matrix_df.empty:
        st.info("📭 Belum ada data shift untuk bulan ini.")
        st.caption("Mulai isi di tab **💬 Chat Update**.")
    else:
        st.markdown(
            f"<div class='preview-card'>"
            f"<div class='preview-title'>"
            f"📊 {NAMA_BULAN_ID[_bulan_pilihan]} {_tahun_pilihan} — {len(_matrix_df)} Personil"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Split data tgl 1-15 & 16-31
        _all_cols = list(_matrix_df.columns)
        _nama_col = "NAMA"

        _cols_1_15 = [_nama_col] + [
            c for c in _all_cols
            if c != _nama_col and str(c).isdigit() and 1 <= int(c) <= 15
        ]
        _cols_16_31 = [_nama_col] + [
            c for c in _all_cols
            if c != _nama_col and str(c).isdigit() and 16 <= int(c) <= 31
        ]

        _df_part1 = _matrix_df[_cols_1_15].copy() if len(_cols_1_15) > 1 else pd.DataFrame()
        _df_part2 = _matrix_df[_cols_16_31].copy() if len(_cols_16_31) > 1 else pd.DataFrame()

        # Tabel 1: Tgl 1-15
        st.markdown("#### 📅 Tabel 1: Tanggal 1 - 15")
        if not _df_part1.empty:
            st.dataframe(
                _df_part1,
                use_container_width=True,
                hide_index=True,
                height=min(500, 40 + len(_df_part1) * 38),
            )
        else:
            st.info("📭 Tidak ada data tanggal 1-15.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabel 2: Tgl 16-31
        st.markdown("#### 📅 Tabel 2: Tanggal 16 - 31")
        if not _df_part2.empty:
            st.dataframe(
                _df_part2,
                use_container_width=True,
                hide_index=True,
                height=min(500, 40 + len(_df_part2) * 38),
            )
        else:
            st.info("📭 Tidak ada data tanggal 16-31.")

        # Legenda
        st.markdown("---")
        _legenda_html = (
            "<div style='"
            "background: rgba(10, 22, 18, 0.6);"
            "border: 1.5px solid #B87333;"
            "border-radius: 10px;"
            "padding: 12px 16px;"
            "margin-top: 10px;"
            "'>"
            "<div style='"
            "font-family: JetBrains Mono, monospace;"
            "font-size: 10px;"
            "color: #E8B189;"
            "letter-spacing: 1.5px;"
            "margin-bottom: 8px;"
            "text-transform: uppercase;"
            "'>🎨 Legenda Kode Shift</div>"
            "<div style='"
            "display: flex;"
            "flex-wrap: wrap;"
            "gap: 8px;"
            "font-family: JetBrains Mono, monospace;"
            "font-size: 11px;"
            "'>"
        )

        for _kode, _info in KODE_SHIFT.items():
            _legenda_html += (
                f"<div style='"
                f"background: {_info['warna']}20;"
                f"border: 1.5px solid {_info['warna']};"
                f"border-radius: 8px;"
                f"padding: 6px 10px;"
                f"color: {_info['warna']};"
                f"font-weight: 900;"
                f"'>"
                f"{_info['icon']} <b>{_kode}</b> = {_info['label']}"
                f"</div>"
            )

        _legenda_html += "</div></div>"
        st.markdown(_legenda_html, unsafe_allow_html=True)


# ============================================================
# TAB 3: PERSONIL MANAGEMENT
# ============================================================
elif st.session_state["shift_sub_tab"] == "personil":
    st.markdown("### 👥 Manajemen Personil")

    _personil_all = load_personil_master(only_active=False)
    _personil_aktif = load_personil_master(only_active=True)

    col_pm1, col_pm2 = st.columns(2)
    with col_pm1:
        st.metric("👥 Personil Aktif", len(_personil_aktif))
    with col_pm2:
        st.metric("👤 Total Personil", len(_personil_all))

    st.markdown("---")

    with st.expander("➕ Tambah Personil Baru", expanded=False):
        with st.form("form_add_personil"):
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                _new_nama = st.text_input(
                    "Nama Personil",
                    placeholder="Contoh: BUDI",
                    key="new_personil_nama",
                ).strip().upper()
            with col_f2:
                _new_urutan = st.number_input(
                    "Urutan (opsional)",
                    min_value=0,
                    value=0,
                    key="new_personil_urutan",
                    help="0 = otomatis di paling bawah",
                )

            _btn_add = st.form_submit_button(
                "💾 TAMBAH PERSONIL",
                use_container_width=True,
                type="primary",
            )

            if _btn_add:
                if not _new_nama:
                    st.error("⚠️ Nama wajib diisi!")
                else:
                    _ok, _msg = add_personil(
                        _new_nama,
                        _new_urutan if _new_urutan > 0 else None,
                    )
                    if _ok:
                        st.success(_msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(_msg)

    st.markdown("#### 📋 Daftar Personil")

    if _personil_all.empty:
        st.info("📭 Belum ada personil.")
    else:
        for _, _row in _personil_all.sort_values("urutan").iterrows():
            _nama = _row["nama"]
            _aktif = _row["aktif"]
            _urutan = _row["urutan"]

            col_l1, col_l2 = st.columns([3, 1])

            with col_l1:
                _status_icon = "✅" if _aktif else "❌"
                _status_text = "AKTIF" if _aktif else "NON-AKTIF"
                _status_color = "#7FB99B" if _aktif else "#E88B8B"

                st.markdown(
                    f"<div style='"
                    f"padding: 12px 16px;"
                    f"background: rgba(15, 138, 114, 0.1);"
                    f"border: 1.5px solid {_status_color};"
                    f"border-radius: 10px;"
                    f"margin-bottom: 8px;"
                    f"'>"
                    f"<span style='font-family: JetBrains Mono, monospace; "
                    f"font-size: 14px; font-weight: 900; color: #E8B189;'>"
                    f"{_status_icon} {_nama}</span>"
                    f"<span style='font-family: JetBrains Mono, monospace; "
                    f"font-size: 10px; color: {_status_color}; margin-left: 10px;'>"
                    f"#{_urutan} • {_status_text}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            with col_l2:
                if _aktif:
                    if st.button(
                        "🚫 Non-aktif",
                        key=f"btn_deact_{_nama}",
                        use_container_width=True,
                    ):
                        _ok, _msg = update_personil_status(_nama, False)
                        if _ok:
                            st.success(_msg)
                            time.sleep(0.8)
                            st.rerun()
                else:
                    if st.button(
                        "✅ Aktifkan",
                        key=f"btn_act_{_nama}",
                        use_container_width=True,
                    ):
                        _ok, _msg = update_personil_status(_nama, True)
                        if _ok:
                            st.success(_msg)
                            time.sleep(0.8)
                            st.rerun()


# ============================================================
# TAB 4: DOWNLOAD EXCEL
# ============================================================
elif st.session_state["shift_sub_tab"] == "download":
    st.markdown("### 📥 Download Excel Master Shift")

    col_d1, col_d2 = st.columns(2)

    with col_d1:
        _dl_bulan = st.selectbox(
            "📅 Bulan",
            options=list(NAMA_BULAN_ID.keys()),
            format_func=lambda x: NAMA_BULAN_ID[x],
            index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
            key="dl_shift_bulan",
        )
    with col_d2:
        _dl_tahun = st.number_input(
            "📆 Tahun",
            min_value=2024,
            max_value=2100,
            value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
            key="dl_shift_tahun",
        )

    with st.spinner("⏳ Prepare Excel..."):
        _dl_matrix = load_master_shift_matrix(_dl_bulan, _dl_tahun)

    if _dl_matrix.empty:
        st.warning("📭 Belum ada data untuk bulan ini.")
    else:
        st.success(f"✅ Siap download: **{len(_dl_matrix)} personil**")

        _excel_bytes = generate_master_shift_excel(_dl_matrix, _dl_bulan, _dl_tahun)

        if _excel_bytes:
            st.download_button(
                label="📥 DOWNLOAD EXCEL MASTER SHIFT",
                data=_excel_bytes,
                file_name=(
                    f"Master_Shift_{NAMA_BULAN_ID[_dl_bulan]}_"
                    f"{_dl_tahun}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
        else:
            st.error("❌ Gagal generate Excel.")

# ============================================================
# TAB 5: UPLOAD SCREENSHOT (OCR)
# ============================================================
elif st.session_state["shift_sub_tab"] == "screenshot":
    st.markdown("### 📸 Upload Screenshot Kalender Shift")
    st.caption("💡 Upload screenshot dari web absen → AI baca kode shift otomatis")

    # Import OCR handler
    try:
        from modules.ocr_handler import (
            ocr_kalender_screenshot,
            parse_kalender_ke_shift,
            save_ocr_to_master_shift,
            log_ocr_upload,
        )
        _ocr_available = True
    except ImportError as _e_ocr:
        _ocr_available = False
        st.error(f"❌ OCR handler tidak tersedia: {_e_ocr}")
        st.info("💡 Pastikan file `modules/ocr_handler.py` sudah di-upload.")

    if _ocr_available:
        # ============================================================
        # LANGKAH 1: PILIH NAMA & BULAN
        # ============================================================
        st.markdown("#### 📋 Langkah 1: Pilih Nama & Bulan")

        col_n1, col_n2, col_n3 = st.columns([2, 1, 1])

        with col_n1:
            # Load personil aktif
            _personil_df = load_personil_master(only_active=True)
            _personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []

            if not _personil_list:
                st.warning("⚠️ Belum ada personil aktif. Tambah dulu di tab 👥 Personil.")
            else:
                _nama_pilih = st.selectbox(
                    "👤 Nama Personil",
                    options=_personil_list,
                    key="ocr_nama_personil",
                )

        with col_n2:
            _bulan_ocr = st.selectbox(
                "📅 Bulan",
                options=list(NAMA_BULAN_ID.keys()),
                format_func=lambda x: NAMA_BULAN_ID[x],
                index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
                key="ocr_bulan",
            )

        with col_n3:
            _tahun_ocr = st.number_input(
                "📆 Tahun",
                min_value=2024,
                max_value=2100,
                value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
                key="ocr_tahun",
            )

        st.markdown("---")

        # ============================================================
        # LANGKAH 2: UPLOAD SCREENSHOT
        # ============================================================
        st.markdown("#### 📸 Langkah 2: Upload Screenshot Kalender")

        _uploaded_file = st.file_uploader(
            "Upload screenshot dari web absen",
            type=["png", "jpg", "jpeg"],
            key="ocr_file_uploader",
            help="Format: PNG/JPG. Screenshot kalender shift per orang.",
        )

        if _uploaded_file:
            st.markdown("---")
            st.markdown("#### 🔧 Kalibrasi Area Kalender")
            st.caption("💡 Atur slider sampai kotak hijau pas dengan area kalender")
            
            # Init calib di session
            _calib_key = f"calib_{_uploaded_file.name}"
            if _calib_key not in st.session_state:
                st.session_state[_calib_key] = {
                    "x_start": 0, "x_end": 1000,
                    "y_start": 0, "y_end": 1500,
                }
            
            _calib = st.session_state[_calib_key]
            
            # Ambil size image (via PIL)
            from PIL import Image as PILImage
            _img_preview = PILImage.open(io.BytesIO(_uploaded_file.getvalue()))
            _img_w, _img_h = _img_preview.size
            
            # Slider kalibrasi
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                _calib["x_start"] = st.slider(
                    "⬅️ X Start", 0, _img_w, _calib.get("x_start", 0),
                    key=f"xs_{_uploaded_file.name}"
                )
                _calib["x_end"] = st.slider(
                    "➡️ X End", 0, _img_w, _calib.get("x_end", _img_w),
                    key=f"xe_{_uploaded_file.name}"
                )
            
            with col_c2:
                _calib["y_start"] = st.slider(
                    "⬆️ Y Start", 0, _img_h, _calib.get("y_start", 0),
                    key=f"ys_{_uploaded_file.name}"
                )
                _calib["y_end"] = st.slider(
                    "⬇️ Y End", 0, _img_h, _calib.get("y_end", _img_h),
                    key=f"ye_{_uploaded_file.name}"
                )
            
            st.session_state[_calib_key] = _calib
            st.session_state[_calib_key] = _calib

            # Tombol AUTO-DETECT + PREVIEW
            col_a1, col_a2 = st.columns(2)
            
            with col_a1:
                if st.button("🤖 AUTO-DETECT", use_container_width=True, key="btn_auto_calib"):
                    with st.spinner("⏳ Auto-detect area kalender..."):
                        from modules.ocr_handler import (
                            _ocr_with_coords,
                            _auto_detect_calibration,
                        )
                        _img_temp = PILImage.open(io.BytesIO(_uploaded_file.getvalue()))
                        _items_temp = _ocr_with_coords(_img_temp)
                        _auto_calib = _auto_detect_calibration(_items_temp, _img_w, _img_h)
                        
                        st.session_state[_calib_key] = _auto_calib
                        st.success(
                            f"✅ Auto: Y={_auto_calib['y_start']}-{_auto_calib['y_end']}, "
                            f"X={_auto_calib['x_start']}-{_auto_calib['x_end']}"
                        )
                        time.sleep(0.8)
                        st.rerun()
            
            with col_a2:
                if st.button("👁️ PREVIEW KALIBRASI", use_container_width=True, key="btn_calib_preview"):
                    with st.spinner("⏳ Generate annotated image..."):
                        from modules.ocr_handler import ocr_debug_visual
                        _annotated, _items_prev = ocr_debug_visual(
                            _uploaded_file.getvalue(),
                            calib=st.session_state[_calib_key],
                        )
                        
                        if _annotated:
                            st.image(
                                _annotated,
                                caption="🟢 Tanggal | 🔵 Kode | 🔴 Noise | 🟩 Area Terpilih",
                                use_container_width=True,
                            )
                            st.success(f"✅ {len(_items_prev)} items terdeteksi")
                        else:
                            st.error("❌ Gagal generate annotated image")
            
            st.markdown("---")
            
            # Preview gambar asli
            st.image(
                _uploaded_file,
                caption=f"Preview: {_uploaded_file.name}",
                use_container_width=True,
            )
            
            # Tombol proses
            col_p1, col_p2 = st.columns([2, 1])
            with col_p1:
                _btn_proses_ocr = st.button(
                    "🔍 PROSES OCR (dengan kalibrasi)",
                    use_container_width=True,
                    type="primary",
                    key="btn_ocr_proses",
                )
            with col_p2:
                if st.button("🗑️ Clear", use_container_width=True, key="btn_ocr_clear"):
                    st.session_state["ocr_result"] = None
                    st.rerun()
            
            if _btn_proses_ocr:
                st.info("🤖 Menggunakan AI Vision (Gemini) — lebih akurat...")
                with st.spinner("⏳ AI membaca kalender... (10-20 detik)"):
                    from modules.ocr_ai_handler import ocr_ai_smart
                    _ai_result = ocr_ai_smart(
                        _uploaded_file.getvalue(),
                        nama_personil=_nama_pilih,
                        bulan=_bulan_ocr,
                        tahun=_tahun_ocr,
                    )
                
                if _ai_result["success"]:
                    _shift_map_ai = _ai_result["shift_map"]
                    
                    _tanggal_list_ai = []
                    for _tgl_str, _kode in sorted(_shift_map_ai.items()):
                        _tanggal_list_ai.append({
                            "tanggal_int": int(_tgl_str.split("-")[2]),
                            "kode": _kode,
                            "confidence": "AI",
                            "sumber": _ai_result.get("provider", "ai"),
                        })
                    
                    st.session_state["ocr_result"] = {
                        "ocr": {
                            "success": True,
                            "tanggal_list": _tanggal_list_ai,
                            "raw_text": _ai_result.get("raw_response", "")[:500],
                            "provider": _ai_result.get("provider"),
                        },
                        "parsed": {
                            "nama": _nama_pilih,
                            "bulan": _bulan_ocr,
                            "tahun": _tahun_ocr,
                            "shift_map": _shift_map_ai,
                        },
                        "nama": _nama_pilih,
                        "bulan": _bulan_ocr,
                        "tahun": _tahun_ocr,
                        "file_name": _uploaded_file.name,
                    }
                    st.rerun()
                else:
                    st.error(f"❌ AI OCR gagal: {_ai_result.get('error')}")
                    if _ai_result.get("raw_response"):
                        with st.expander("🔍 Raw AI Response"):
                            st.text(_ai_result["raw_response"][:1000])
                            
        # ============================================================
        # LANGKAH 3: PREVIEW HASIL OCR
        # ============================================================
        if st.session_state.get("ocr_result"):
            _res = st.session_state["ocr_result"]

            st.markdown("---")

            if "error" in _res:
                st.error(f"❌ Gagal OCR: {_res['error']}")
                st.caption("💡 Coba screenshot dengan resolusi lebih tinggi / kontras lebih baik.")
            else:
                _ocr_data = _res["ocr"]
                _parsed_data = _res["parsed"]
                _shift_map = _parsed_data["shift_map"]

                # Metrics
                st.markdown("#### 📊 Langkah 3: Preview Hasil OCR")

                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("👤 Nama", _parsed_data["nama"])
                with col_m2:
                    st.metric("📅 Periode", f"{NAMA_BULAN_ID[_res['bulan']]} {_res['tahun']}")
                with col_m3:
                    st.metric("📊 Hari Terdeteksi", len(_shift_map))

                # Raw text (debug)
                with st.expander("🔍 DEBUG INFO", expanded=True):
                    st.write("**Kalender area Y:**", _ocr_data.get("kalender_area", "?"))
                    st.write("**Kolom detected:**", _ocr_data.get("kolom_detected", 0))
                    st.write("**Baris detected:**", _ocr_data.get("baris_detected", 0))
                    st.write("**Total cells analyzed:**", len(_ocr_data.get("debug_cells", [])))
                    
                    _debug_cells = _ocr_data.get("debug_cells", [])
                    if _debug_cells:
                        st.write("**Sample debug cells:**")
                        _debug_df = pd.DataFrame(_debug_cells[:30])
                        st.dataframe(_debug_df, use_container_width=True)
                    else:
                        st.error("❌ TIDAK ADA CELL YANG DI-ANALISIS!")
                        st.write("**Kemungkinan penyebab:**")
                        st.write("- Kalender area gak ke-detect")
                        st.write("- Kolom/baris gak ke-detect")
                        st.write("- Semua cell ke-skip karena putih")
                    
                    st.write("**Raw OCR text:**")
                    st.text(_ocr_data.get("raw_text", "")[:800])

                # Preview tabel
                if _shift_map:
                    st.markdown("##### 📋 Preview Kode Shift")

                    _preview_rows = []
                    for _tgl_str, _kode in sorted(_shift_map.items()):
                        _tgl = pd.to_datetime(_tgl_str)
                        _info = KODE_SHIFT.get(_kode, {
                            "label": "-", "icon": "❓", "warna": "#CCCCCC"
                        })
                        _preview_rows.append({
                            "📅 Tanggal": _tgl.strftime("%d/%m/%Y"),
                            "🎨 Kode": _kode,
                            "📋 Keterangan": _info["label"],
                            "🔖 Icon": _info["icon"],
                        })

                    _preview_df = pd.DataFrame(_preview_rows)
                    st.dataframe(
                        _preview_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                    # ============================================================
                    # LANGKAH 4: KONFIRMASI SIMPAN
                    # ============================================================
                    st.markdown("#### 💾 Langkah 4: Simpan ke Master Shift")

                    st.info(
                        f"Akan **{len(_shift_map)} shift** disimpan untuk "
                        f"**{_parsed_data['nama']}** periode "
                        f"**{NAMA_BULAN_ID[_res['bulan']]} {_res['tahun']}**."
                    )

                    col_s1, col_s2 = st.columns([2, 1])

                    with col_s1:
                        if st.button(
                            "💾 KONFIRMASI SIMPAN",
                            use_container_width=True,
                            type="primary",
                            key="btn_ocr_save",
                        ):
                            with st.spinner("⏳ Menyimpan..."):
                                # Save
                                _ok, _msg = save_ocr_to_master_shift(
                                    nama=_parsed_data["nama"],
                                    bulan=_res["bulan"],
                                    tahun=_res["tahun"],
                                    shift_map=_shift_map,
                                    sumber="ocr",
                                )

                                # Log
                                if _ok:
                                    log_ocr_upload(
                                        nama=_parsed_data["nama"],
                                        bulan=_res["bulan"],
                                        tahun=_res["tahun"],
                                        file_name=_res["file_name"],
                                        ocr_result=_ocr_data,
                                        uploaded_by=st.session_state.get("username", "admin"),
                                    )

                            if _ok:
                                st.success(_msg)
                                st.balloons()
                                st.session_state["ocr_result"] = None
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(_msg)

                    with col_s2:
                        if st.button(
                            "❌ BATAL",
                            use_container_width=True,
                            key="btn_ocr_cancel",
                        ):
                            st.session_state["ocr_result"] = None
                            st.rerun()

                else:
                    st.warning(
                        "⚠️ Tidak ada kode shift yang terdeteksi. "
                        "Coba screenshot dengan kualitas lebih baik."
                    )

        # ============================================================
        # INFO FORMAT SCREENSHOT
        # ============================================================
        with st.expander("📖 Tips Screenshot yang Bagus"):
            st.markdown("""
            **✅ Yang bikin OCR akurat:**
            - 📸 Screenshot **zoom out** (kode keliatan full)
            - 🖼️ **Resolusi tinggi** (min 1080px lebar)
            - 💡 **Kontras bagus** (jangan gelap/blur)
            - 📐 **Kalender full** keliatan (tanggal 1-31)
            - 🎨 **Warna jelas** (hijau/biru/hitam kelihatan)

            **❌ Yang bikin OCR gagal:**
            - Kode shift **kepotong** (`P7~F`, `M2?`)
            - Screenshot **blur**
            - Warna **pudar** atau gelap
            - Ada **notifikasi** nutupin
            - **Zoom in** terlalu dekat

            **🔧 Kalau OCR gagal:**
            - Coba screenshot ulang dengan kualitas lebih baik
            - Atau pakai **Chat Update** sebagai alternatif
            - Atau **edit manual** via Grid Editor (next step)
            """)
# ============================================================
# TAB 6: API USAGE MONITORING
# ============================================================
elif st.session_state["shift_sub_tab"] == "usage":
    st.markdown("### 📊 Gemini API Usage Monitor")
    st.caption("Pantau penggunaan API Gemini kamu hari ini")
    
    try:
        from modules.ocr_ai_handler import (
            get_api_usage_summary,
            MODEL_PRIORITY,
            GEMINI_AVAILABLE,
        )
        
        # Info API Key
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            st.metric("🔑 API Key", "✅ Set" if _api_key else "❌ Belum")
        with col_a2:
            st.metric("📏 Key Length", len(_api_key))
        with col_a3:
            st.metric("🤖 Library", "✅ Ready" if GEMINI_AVAILABLE else "❌ Missing")
        
        st.markdown("---")
        
        # Usage hari ini
        _usage = get_api_usage_summary()
        
        st.markdown("#### 📈 Penggunaan Hari Ini")
        
        col_u1, col_u2, col_u3, col_u4 = st.columns(4)
        with col_u1:
            st.metric("📤 Requests", _usage.get("requests", 0))
        with col_u2:
            st.metric("📥 Input Tokens", f"{_usage.get('input_tokens', 0):,}")
        with col_u3:
            st.metric("📤 Output Tokens", f"{_usage.get('output_tokens', 0):,}")
        with col_u4:
            st.metric("❌ Errors", _usage.get("errors", 0))
        
        # Estimasi quota
        st.markdown("---")
        st.markdown("#### 🎯 Estimasi Sisa Kuota")
        
        _used = _usage.get("requests", 0)
        _limit_rpd = 1500  # Free tier RPD
        _sisa = max(0, _limit_rpd - _used)
        _pct = min(100, int((_used / _limit_rpd) * 100))
        
        st.progress(_pct / 100)
        st.caption(f"📊 **{_used} / ~{_limit_rpd}** requests hari ini (~{_pct}%)")
        st.caption(f"✅ Sisa: **~{_sisa} requests**")
        
        if _pct >= 80:
            st.warning(f"⚠️ Kuota hampir habis! Tunggu reset jam 14:00-15:00 WIB")
        elif _pct >= 50:
            st.info(f"ℹ️ Setengah kuota terpakai")
        else:
            st.success(f"✅ Kuota aman")
        
        # Info reset
        st.markdown("---")
        st.markdown("#### ⏰ Info Reset Quota")
        
        st.markdown("""
        **Reset Harian (RPD):**
        - 🌍 **Pacific Time**: 00:00 (tengah malam)
        - 🇮🇩 **Waktu Indonesia (WIB)**: **14:00 - 15:00** (siang/sore)
        
        **Reset Per Menit (RPM):**
        - ⏱️ Setiap **60 detik**
        
        **Limit Free Tier (perkiraan):**
        - 📤 **RPM**: 10-15 request/menit
        - 📅 **RPD**: ~1,500 request/hari
        - 🎫 **TPM**: ~1 juta token/menit
        """)
        
        # Model priority
        st.markdown("---")
        st.markdown("#### 🤖 Model Priority (Auto-Fallback)")
        
        for _i, _model in enumerate(MODEL_PRIORITY):
            _used_models = _usage.get("model_used", [])
            _is_used = _model in _used_models
            st.write(f"**{_i+1}.** `{_model}` {'✅' if _is_used else ''}")
        
        # Tombol reset tracker (untuk admin)
        st.markdown("---")
        if st.button("🗑️ Reset Tracker", key="btn_reset_usage"):
            st.session_state["api_usage_tracker"] = {}
            st.success("✅ Tracker direset!")
            time.sleep(0.5)
            st.rerun()
    
    except ImportError as _e_usage:
        st.error(f"❌ Module error: {_e_usage}")
# ============================================================
# FOOTER
# ============================================================
render_copyright()
