"""
Master Shift Page v3
====================
Struktur:
- 🌸 Hana       (chat all-in-one dengan memory chat)
- 📸 Screenshot (OCR kalender)
- 📊 Matrix     (tabel master | personil | download)
- 📈 Usage      (monitoring token)

Fitur v3:
- Memory chat persistent (Supabase) — khusus tab Hana
- Delete shift dengan konfirmasi
- Token monitoring
"""

import streamlit as st
import pandas as pd
import time
import io
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from PIL import Image as PILImage

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
    page_title="Master Shift | Toko C383",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CURRENT_THEME = get_theme_by_month()
render_theme(CURRENT_THEME)
render_theme_animations(CURRENT_THEME)
render_greeting()

# =========================================================================
# IMPORT
# =========================================================================
try:
    from modules.master_shift_handler import (
        load_personil_master,
        add_personil,
        update_personil_status,
        save_master_shift,
        load_master_shift_matrix,
        get_shift_hari_ini,
        generate_master_shift_excel,
        delete_shift_by_name,
        delete_shift_all_dates,
        KODE_SHIFT,
        NAMA_BULAN_ID,
    )
    from modules.ai_shift_manager import (
        chat_response,
        parse_shift_update,
        ai_suggest_pengganti_text,
        ai_check_conflict_text,
    )
    from modules.chat_memory import (
        save_message,
        load_messages,
        get_or_create_session_id,
        clear_session,
    )
    _MEMORY_OK = True
except ImportError as e:
    _MEMORY_OK = False
    st.error(f"❌ Gagal import module: {e}")
    st.info("💡 Pastikan `modules/chat_memory.py` udah dibuat.")
    st.stop()


# =========================================================================
# CSS CUSTOM — PILL TAB
# =========================================================================
def inject_pill_css():
    st.markdown("""
    <style>
        div[data-testid="stHorizontalBlock"] > div > div > div > button[kind="secondary"],
        div[data-testid="stHorizontalBlock"] > div > div > div > button[kind="primary"] {
            border-radius: 999px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
            border-width: 1.5px !important;
        }

        div[data-testid="stHorizontalBlock"] > div > div > div > button[kind="primary"] {
            box-shadow: 0 0 15px rgba(232, 177, 137, 0.5) !important;
            transform: translateY(-1px) !important;
        }

        .memory-info-hana {
            background: rgba(20, 12, 35, 0.95);
            border-left: 3px solid #7FB99B;
            border-radius: 8px;
            padding: 8px 14px;
            margin-bottom: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: #A89B8E;
        }
    </style>
    """, unsafe_allow_html=True)


inject_pill_css()


# =========================================================================
# HEADER
# =========================================================================
def render_header():
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

    st.markdown(
        "<div class='royal-header fade-in-up'>"
        "<div class='royal-title'>🌸 MASTER SHIFT 🌸</div>"
        "<div class='royal-subtitle'>⚜ Hana — Asisten Jadwal Toko C383 ⚜</div>"
        "<div class='header-clock'>"
        f"<div class='clock-time'>🕐 {_time_str} WIB</div>"
        f"<div class='clock-date'>📅 {_date_id}</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


render_header()

# Back button
_col_back, _ = st.columns([1, 4])
with _col_back:
    if st.button("← Dashboard", key="btn_back_home", width="stretch"):
        try:
            st.switch_page("Dashboard.py")
        except Exception:
            pass


# =========================================================================
# TAB NAVIGATION — PILL
# =========================================================================
if "ms_tab" not in st.session_state:
    st.session_state["ms_tab"] = "screenshot"

_TABS = [
    ("screenshot", "📸 Screenshot"),
    ("matrix", "📊 Matrix"),
    ("usage", "📈 Usage"),
]
_cols = st.columns(len(_TABS))
for _i, (_key, _label) in enumerate(_TABS):
    with _cols[_i]:
        _is_active = st.session_state["ms_tab"] == _key
        if st.button(
            _label,
            key=f"ms_tab_btn_{_key}",
            width="stretch",
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["ms_tab"] = _key
            st.rerun()

st.markdown("---")

# =========================================================================
# TAB 2: SCREENSHOT (OCR)
# =========================================================================
def render_screenshot():
    st.markdown("### 📸 Upload Screenshot Kalender Shift")
    st.caption("💡 Upload screenshot dari web absen → AI baca kode shift otomatis")

    try:
        from modules.ocr_handler import log_ocr_upload
        _ocr_available = True
    except ImportError:
        _ocr_available = False

    if not _ocr_available:
        st.info("💡 Fitur OCR butuh file `modules/ocr_handler.py`.")
        return

    try:
        from modules.ocr_ai_handler import ocr_ai_smart
        from modules.ocr_handler import save_ocr_to_master_shift
    except ImportError as _e:
        st.error(f"❌ Import OCR error: {_e}")
        return

    # Pilih personil & bulan
    _personil_df = load_personil_master(only_active=True)
    _personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []

    col_n1, col_n2, col_n3 = st.columns([2, 1, 1])
    with col_n1:
        _nama_pilih = st.selectbox("👤 Nama Personil", options=_personil_list, key="ocr_nama") if _personil_list else None
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
            "📆 Tahun", min_value=2024, max_value=2100,
            value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
            key="ocr_tahun",
        )

    st.markdown("---")

    _uploaded = st.file_uploader(
        "Upload screenshot kalender (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        key="ocr_upload",
    )

    if _uploaded and _nama_pilih:
        st.image(_uploaded, caption=f"Preview: {_uploaded.name}", width="stretch")

        if st.button("🔍 PROSES OCR", type="primary", width="stretch", key="btn_ocr"):
            with st.spinner("🌸 Hana lagi baca kalender... (10-20 detik)"):
                _ai_result = ocr_ai_smart(
                    _uploaded.getvalue(),
                    nama_personil=_nama_pilih,
                    bulan=_bulan_ocr,
                    tahun=_tahun_ocr,
                )

            if _ai_result["success"]:
                _shift_map = _ai_result["shift_map"]
                _tanggal_list = []
                for _tgl_str, _kode in sorted(_shift_map.items()):
                    _tanggal_list.append({
                        "tanggal_int": int(_tgl_str.split("-")[2]),
                        "kode": _kode,
                    })

                st.session_state["ocr_result"] = {
                    "shift_map": _shift_map,
                    "tanggal_list": _tanggal_list,
                    "nama": _nama_pilih,
                    "bulan": _bulan_ocr,
                    "tahun": _tahun_ocr,
                    "provider": _ai_result.get("provider", "?"),
                }
                st.rerun()
            else:
                st.error(f"❌ OCR gagal: {_ai_result.get('error')}")

    # Preview hasil OCR
    if st.session_state.get("ocr_result"):
        _res = st.session_state["ocr_result"]
        _shift_map = _res["shift_map"]

        st.markdown("---")
        st.markdown("#### 📊 Hasil OCR")
        st.write(f"**Nama:** {_res['nama']} • **Provider:** {_res['provider']}")

        _preview_rows = []
        for _tgl_str, _kode in sorted(_shift_map.items()):
            _tgl = pd.to_datetime(_tgl_str)
            _info = KODE_SHIFT.get(_kode, {"label": "-", "icon": "❓"})
            _preview_rows.append({
                "📅 Tanggal": _tgl.strftime("%d/%m/%Y"),
                "🎨 Kode": _kode,
                "📋 Ket.": _info["label"],
            })
        st.dataframe(pd.DataFrame(_preview_rows), width="stretch", hide_index=True)

        _col1, _col2 = st.columns(2)
        with _col1:
            if st.button("💾 SIMPAN KE MASTER SHIFT", type="primary", width="stretch", key="btn_ocr_save"):
                with st.spinner("⏳ Menyimpan..."):
                    _ok, _msg = save_ocr_to_master_shift(
                        nama=_res["nama"],
                        bulan=_res["bulan"],
                        tahun=_res["tahun"],
                        shift_map=_shift_map,
                        sumber="ocr",
                    )
                if _ok:
                    st.success(_msg)
                    st.balloons()
                    st.session_state["ocr_result"] = None
                    st.cache_data.clear()
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(_msg)

        with _col2:
            if st.button("❌ BATAL", width="stretch", key="btn_ocr_cancel"):
                st.session_state["ocr_result"] = None
                st.rerun()
# =========================================================================
# TAB 3: MATRIX
# =========================================================================
def render_matrix():
    st.markdown("### 📊 Matrix & Data")

    if "matrix_sub" not in st.session_state:
        st.session_state["matrix_sub"] = "tabel"

    _subs = [
        ("tabel", "📋 Tabel Master"),
        ("personil", "👥 Personil Aktif"),
        ("download", "📥 Download"),
    ]

    _sub_cols = st.columns(len(_subs))
    for _i, (_key, _label) in enumerate(_subs):
        with _sub_cols[_i]:
            _is_active = st.session_state["matrix_sub"] == _key
            if st.button(
                _label,
                key=f"matrix_sub_{_key}",
                width="stretch",
                type="primary" if _is_active else "secondary",
            ):
                st.session_state["matrix_sub"] = _key
                st.rerun()

    st.markdown("---")

    # === SUB: TABEL MASTER ===
    if st.session_state["matrix_sub"] == "tabel":
        _col_b1, _col_b2, _col_b3 = st.columns([2, 1, 1])
        with _col_b1:
            _bulan_pilih = st.selectbox(
                "📅 Bulan",
                options=list(NAMA_BULAN_ID.keys()),
                format_func=lambda x: NAMA_BULAN_ID[x],
                index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
                key="matrix_bulan",
            )
        with _col_b2:
            _tahun_pilih = st.number_input(
                "📆 Tahun", min_value=2024, max_value=2100,
                value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
                key="matrix_tahun",
            )
        with _col_b3:
            if st.button("🔄 Refresh", width="stretch", key="matrix_refresh"):
                st.cache_data.clear()
                st.rerun()

        with st.spinner("⏳ Load matrix..."):
            _matrix_df = load_master_shift_matrix(_bulan_pilih, _tahun_pilih)

        if _matrix_df.empty:
            st.info("📭 Belum ada data shift bulan ini.")
        else:
            _all_cols = list(_matrix_df.columns)
            _nama_col = "NAMA"
            _cols_1_15 = [_nama_col] + [c for c in _all_cols if c != _nama_col and str(c).isdigit() and 1 <= int(c) <= 15]
            _cols_16_31 = [_nama_col] + [c for c in _all_cols if c != _nama_col and str(c).isdigit() and 16 <= int(c) <= 31]

            st.markdown("#### 📅 Tanggal 1 - 15")
            if len(_cols_1_15) > 1:
                st.dataframe(
                    _matrix_df[_cols_1_15],
                    width="stretch",
                    hide_index=True,
                    height=min(500, 40 + len(_matrix_df) * 38),
                )

            st.markdown("#### 📅 Tanggal 16 - 31")
            if len(_cols_16_31) > 1:
                st.dataframe(
                    _matrix_df[_cols_16_31],
                    width="stretch",
                    hide_index=True,
                    height=min(500, 40 + len(_matrix_df) * 38),
                )

    # === SUB: PERSONIL ===
    elif st.session_state["matrix_sub"] == "personil":
        _personil_all = load_personil_master(only_active=False)
        _personil_aktif = load_personil_master(only_active=True)

        _c1, _c2 = st.columns(2)
        with _c1:
            st.metric("👥 Personil Aktif", len(_personil_aktif))
        with _c2:
            st.metric("👤 Total", len(_personil_all))

        st.markdown("---")

        with st.expander("➕ Tambah Personil Baru"):
            with st.form("form_add_personil"):
                _new_nama = st.text_input("Nama", placeholder="Contoh: BUDI").strip().upper()
                _btn_add = st.form_submit_button("💾 TAMBAH", width="stretch", type="primary")
                if _btn_add:
                    if not _new_nama:
                        st.error("⚠️ Nama wajib diisi!")
                    else:
                        _ok, _msg = add_personil(_new_nama)
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
                _col_l1, _col_l2 = st.columns([3, 1])
                with _col_l1:
                    _icon = "✅" if _aktif else "❌"
                    _status = "AKTIF" if _aktif else "NON-AKTIF"
                    st.markdown(f"{_icon} **{_nama}** — {_status}")
                with _col_l2:
                    if _aktif:
                        if st.button("🚫 Non-aktif", key=f"deact_{_nama}", width="stretch"):
                            update_personil_status(_nama, False)
                            st.rerun()
                    else:
                        if st.button("✅ Aktifkan", key=f"act_{_nama}", width="stretch"):
                            update_personil_status(_nama, True)
                            st.rerun()

    # === SUB: DOWNLOAD ===
    elif st.session_state["matrix_sub"] == "download":
        _col_d1, _col_d2 = st.columns(2)
        with _col_d1:
            _dl_bulan = st.selectbox(
                "📅 Bulan",
                options=list(NAMA_BULAN_ID.keys()),
                format_func=lambda x: NAMA_BULAN_ID[x],
                index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
                key="dl_bulan",
            )
        with _col_d2:
            _dl_tahun = st.number_input(
                "📆 Tahun", min_value=2024, max_value=2100,
                value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
                key="dl_tahun",
            )

        with st.spinner("⏳ Prepare Excel..."):
            _dl_matrix = load_master_shift_matrix(_dl_bulan, _dl_tahun)

        if _dl_matrix.empty:
            st.warning("📭 Belum ada data.")
        else:
            _excel_bytes = generate_master_shift_excel(_dl_matrix, _dl_bulan, _dl_tahun)
            if _excel_bytes:
                st.download_button(
                    label="📥 DOWNLOAD EXCEL",
                    data=_excel_bytes,
                    file_name=f"Master_Shift_{NAMA_BULAN_ID[_dl_bulan]}_{_dl_tahun}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                    type="primary",
                    key="dl_excel",
                )


# =========================================================================
# TAB 4: USAGE
# =========================================================================
def render_usage():
    from modules.token_monitor import render_usage_dashboard
    st.markdown("### 📈 Penggunaan AI")
    st.caption("Pantau token & quota per AI.")
    render_usage_dashboard()


# =========================================================================
# ROUTING TAB
# =========================================================================
_tab = st.session_state["ms_tab"]

if _tab == "hana":
    render_hana()
elif _tab == "screenshot":
    render_screenshot()
elif _tab == "matrix":
    render_matrix()
elif _tab == "usage":
    render_usage()


# =========================================================================
# FOOTER
# =========================================================================
st.markdown(
    "<div class='copyright-footer'>🌸 Dashboard SO KGS V.3 — Hana Edition 🌸</div>",
    unsafe_allow_html=True,
)