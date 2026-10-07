"""
Input SO — Stock Opname Multi-Produk
======================================
Halaman input SO dengan detail per produk (PLU).

Fitur:
- Input multi-produk per rak
- 5 PLU tertinggi + 5 PLU terendah
- Auto-save ke 2 tabel: so_hasil + so_rak_harian
- Preview + konfirmasi
"""

import streamlit as st
import time
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
    page_title="Input SO | Toko C383",
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
        save_so_input,
        load_so_detail_by_date,
        load_so_summary_by_date,
        delete_so_by_date,
    )
    from modules.master_shift_handler import load_personil_master
    from modules.data_loader import load_rak_master
except ImportError as _e:
    st.error(f"❌ Gagal import module: {_e}")
    st.info("💡 Pastikan `modules/so_handler.py` & `modules/data_loader.py` udah di-upload.")
    st.stop()


# =========================================================================
# CSS
# =========================================================================
def inject_css():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1rem !important;
        }
        .stApp, .stApp * {
            color: #F5E6D3 !important;
        }
        .stApp button {
            color: inherit !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
        }
        .stApp input, .stApp textarea, .stApp select {
            color: #F5E6D3 !important;
            background: rgba(30, 20, 60, 0.6) !important;
            border-radius: 8px !important;
        }
        .stApp input::placeholder, .stApp textarea::placeholder {
            color: rgba(245, 230, 211, 0.5) !important;
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

    _col_back, _col_title, _col_status = st.columns([1, 3, 1])

    with _col_back:
        if st.button("← Dashboard", key="btn_back_iso", use_container_width=True):
            try:
                st.switch_page("Dashboard.py")
            except Exception:
                st.warning("⚠️ Gagal pindah halaman.")

    with _col_title:
        st.markdown(
            "<div style='text-align: center;'>"
            "<div style='font-family: Cinzel, serif; font-size: 22px; "
            "font-weight: 900; color: #E8B189; letter-spacing: 2px; "
            "text-shadow: 0 0 15px rgba(232, 177, 137, 0.6);'>"
            "📝 INPUT STOCK OPNAME 📝</div>"
            "<div style='font-family: Quicksand, sans-serif; font-size: 10px; "
            "color: #7FB99B; letter-spacing: 1.5px; margin-top: 2px;'>"
            "Toko C383 - Karang Satria</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    with _col_status:
        st.markdown(
            f"<div style='text-align: right; font-family: JetBrains Mono, monospace; "
            f"font-size: 10px; color: #7FB99B; padding-top: 8px;'>"
            f"🕐 {_time_str} WIB<br>● ONLINE</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")


render_header()


# =========================================================================
# SESSION STATE
# =========================================================================
if "so_produk_list" not in st.session_state:
    st.session_state["so_produk_list"] = []

if "so_last_saved" not in st.session_state:
    st.session_state["so_last_saved"] = None


# =========================================================================
# NOTIFIKASI SUKSES
# =========================================================================
if st.session_state["so_last_saved"]:
    st.success(st.session_state["so_last_saved"])
    st.balloons()
    st.session_state["so_last_saved"] = None
    time.sleep(1)


# =========================================================================
# LOAD MASTER DATA
# =========================================================================
with st.spinner("⏳ Load master data..."):
    _rak_df = load_rak_master()
    _personil_df = load_personil_master(only_active=True)

_rak_list = _rak_df["rak_id"].tolist() if not _rak_df.empty else []
_personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []


# =========================================================================
# BAGIAN A: TANGGAL + RAK + PIC
# =========================================================================
st.markdown("### 📅 Info SO")

_col_tgl, _col_rak, _col_pic = st.columns([2, 2, 2])

with _col_tgl:
    _tanggal = st.date_input(
        "📅 Tanggal SO",
        value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
        key="iso_tanggal",
    )

with _col_rak:
    if _rak_list:
        _rak_pilih = st.selectbox(
            "🏪 Kode Rak",
            options=_rak_list,
            key="iso_rak",
            help="Pilih rak yang di-SO",
        )
    else:
        st.warning("⚠️ Master rak kosong")
        _rak_pilih = None

with _col_pic:
    if _personil_list:
        _pic_pilih = st.selectbox(
            "👤 PIC",
            options=_personil_list,
            key="iso_pic",
        )
    else:
        _pic_pilih = st.text_input("👤 PIC", key="iso_pic_manual")


st.markdown("---")


# =========================================================================
# BAGIAN B: INPUT PRODUK
# =========================================================================
st.markdown("### 📦 Input Produk (Multi-Produk)")
st.caption("💡 Input 5 PLU tertinggi + 5 PLU terendah (max 10 produk per rak)")

# Tombol tambah produk
_col_btn_add, _col_info = st.columns([2, 5])

with _col_btn_add:
    if st.button("➕ Tambah Produk", use_container_width=True, key="btn_add_produk"):
        if len(st.session_state["so_produk_list"]) >= 10:
            st.warning("⚠️ Max 10 produk per rak")
        else:
            st.session_state["so_produk_list"].append({
                "plu": "",
                "nama_produk": "",
                "qty_sistem": 0,
                "qty_fisik": 0,
                "nominal_adjust": 0,
            })
            st.rerun()

with _col_info:
    _count = len(st.session_state["so_produk_list"])
    st.markdown(f"<div style='padding-top: 8px; color: #7FB99B; font-size: 12px;'>"
                f"📊 **{_count} / 10** produk terinput</div>",
                unsafe_allow_html=True)


# =========================================================================
# LIST PRODUK
# =========================================================================
if st.session_state["so_produk_list"]:
    st.markdown("")
    _items_to_remove = []

    for _idx, _produk in enumerate(st.session_state["so_produk_list"]):
        with st.expander(f"📦 Produk #{_idx+1}: {_produk.get('nama_produk') or '(belum diisi)'}", expanded=True):
            _c1, _c2, _c3, _c4, _c5, _c6 = st.columns([2, 3, 1, 1, 2, 0.8])

            with _c1:
                _new_plu = st.text_input(
                    "PLU",
                    value=_produk.get("plu", ""),
                    key=f"plu_{_idx}",
                    placeholder="433288",
                )
                st.session_state["so_produk_list"][_idx]["plu"] = _new_plu

            with _c2:
                _new_nama = st.text_input(
                    "Nama Produk",
                    value=_produk.get("nama_produk", ""),
                    key=f"nama_{_idx}",
                    placeholder="Baygon AEO Japan P",
                )
                st.session_state["so_produk_list"][_idx]["nama_produk"] = _new_nama

            with _c3:
                _new_qty_sis = st.number_input(
                    "Qty Sistem",
                    min_value=0,
                    value=int(_produk.get("qty_sistem", 0)),
                    key=f"qty_sis_{_idx}",
                    step=1,
                )
                st.session_state["so_produk_list"][_idx]["qty_sistem"] = int(_new_qty_sis)

            with _c4:
                _new_qty_fis = st.number_input(
                    "Qty Fisik",
                    min_value=0,
                    value=int(_produk.get("qty_fisik", 0)),
                    key=f"qty_fis_{_idx}",
                    step=1,
                )
                st.session_state["so_produk_list"][_idx]["qty_fisik"] = int(_new_qty_fis)

            with _c5:
                _new_nominal = st.number_input(
                    "Nominal Adjust (Rp)",
                    min_value=-999999999,
                    max_value=999999999,
                    value=int(_produk.get("nominal_adjust", 0)),
                    key=f"nom_{_idx}",
                    step=1000,
                    help="Nominal selisih dari laporan SO (boleh minus)",
                )
                st.session_state["so_produk_list"][_idx]["nominal_adjust"] = float(_new_nominal)

            with _c6:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{_idx}"):
                    _items_to_remove.append(_idx)

    # Hapus item
    if _items_to_remove:
        for _i in sorted(_items_to_remove, reverse=True):
            st.session_state["so_produk_list"].pop(_i)
        st.rerun()


# =========================================================================
# BAGIAN C: KETERANGAN
# =========================================================================
st.markdown("")
_keterangan = st.text_input(
    "📝 Keterangan (opsional)",
    placeholder="Contoh: Pendingan rak FE1 1 item",
    key="iso_keterangan",
)


st.markdown("---")


# =========================================================================
# BAGIAN D: SUMMARY + SIMPAN
# =========================================================================
if st.session_state["so_produk_list"]:
    _total_item = len(st.session_state["so_produk_list"])
    _total_qty_var = sum(
        int(p.get("qty_fisik", 0)) - int(p.get("qty_sistem", 0))
        for p in st.session_state["so_produk_list"]
    )
    _total_nominal = sum(
        float(p.get("nominal_adjust", 0))
        for p in st.session_state["so_produk_list"]
    )

    _color_nom = "#E88B8B" if _total_nominal < 0 else "#7FB99B"

    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.metric("📦 Total Produk", f"{_total_item}")
    with _c2:
        st.metric("📊 Total Qty Var", f"{_total_qty_var}")
    with _c3:
        st.metric("💰 Total Nominal", f"Rp {_total_nominal:,.0f}".replace(",", "."))

    st.markdown("")
    _col_save, _col_cancel = st.columns([2, 1])

    with _col_save:
        if st.button("💾 SIMPAN SO", use_container_width=True, type="primary", key="btn_save_so"):
            _produk_valid = [
                p for p in st.session_state["so_produk_list"]
                if p.get("plu") and p.get("nama_produk")
            ]

            if not _produk_valid:
                st.error("⚠️ Minimal 1 produk harus diisi PLU & Nama")
            elif not _rak_pilih:
                st.error("⚠️ Pilih rak dulu")
            elif not _pic_pilih:
                st.error("⚠️ Pilih PIC dulu")
            else:
                with st.spinner("⏳ Menyimpan SO..."):
                    _ok, _msg, _detail = save_so_input(
                        tanggal=_tanggal,
                        rak_id=_rak_pilih,
                        pic=_pic_pilih,
                        produk_list=_produk_valid,
                        keterangan=_keterangan,
                    )

                if _ok:
                    st.session_state["so_last_saved"] = _msg
                    st.session_state["so_produk_list"] = []
                    st.cache_data.clear()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(_msg)

    with _col_cancel:
        if st.button("🗑️ Clear Semua", use_container_width=True, key="btn_clear_so"):
            st.session_state["so_produk_list"] = []
            st.rerun()


# =========================================================================
# FOOTER
# =========================================================================
st.markdown(
    "<div style='text-align: center; padding: 20px 0; "
    "font-family: Quicksand, sans-serif; font-size: 10px; "
    "color: #7a9b8e; letter-spacing: 1px;'>"
    "📝 Input SO — Toko C383 🎀"
    "</div>",
    unsafe_allow_html=True,
)
# =========================================================================
# BAGIAN E: PREVIEW SO HARI INI
# =========================================================================
st.markdown("---")
st.markdown("### 📋 Preview SO Hari Ini")

with st.spinner("⏳ Load SO..."):
    _so_summary_today = load_so_summary_by_date(_tanggal)
    _so_detail_today = load_so_detail_by_date(_tanggal)

if not _so_summary_today:
    st.info(f"📭 Belum ada SO untuk tanggal **{_tanggal.strftime('%d/%m/%Y')}**")
else:
    # === SUMMARY PER RAK ===
    _total_rak_so = len(_so_summary_today)
    _total_item_all = sum(int(r.get("total_item", 0)) for r in _so_summary_today)
    _total_nominal_all = sum(float(r.get("nominal_adjust", 0)) for r in _so_summary_today)

    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.metric("🏪 Total Rak di-SO", f"{_total_rak_so}")
    with _c2:
        st.metric("📦 Total Produk", f"{_total_item_all}")
    with _c3:
        _color = "#E88B8B" if _total_nominal_all < 0 else "#7FB99B"
        st.metric("💰 Total Nominal", f"Rp {_total_nominal_all:,.0f}".replace(",", "."))

    st.markdown("")

    # === TABEL SUMMARY PER RAK ===
    import pandas as pd
    _df_summary = pd.DataFrame(_so_summary_today)

    _cols_show = ["rak_id", "pic", "total_item", "total_qty_var", "nominal_adjust", "keterangan"]
    _cols_show = [c for c in _cols_show if c in _df_summary.columns]

    if _cols_show:
        _df_show = _df_summary[_cols_show].copy()

        if "nominal_adjust" in _df_show.columns:
            _df_show["nominal_adjust"] = _df_show["nominal_adjust"].apply(
                lambda v: f"{float(v):+,.0f}".replace(",", ".")
            )

        _col_names = ["Rak", "PIC", "Total Item", "Qty Var", "Nominal", "Keterangan"]
        _df_show.columns = _col_names[:len(_df_show.columns)]

        st.dataframe(_df_show, use_container_width=True, hide_index=True)

    # === DETAIL PER PRODUK (expander) ===
    if _so_detail_today:
        with st.expander(f"🔍 Detail Produk ({len(_so_detail_today)} produk)", expanded=False):
            _df_detail = pd.DataFrame(_so_detail_today)
            _cols_detail = ["rak_id", "plu", "nama_produk", "qty_sistem", "qty_fisik", "qty_var", "nominal_adjust", "pic"]
            _cols_detail = [c for c in _cols_detail if c in _df_detail.columns]

            _df_detail_show = _df_detail[_cols_detail].copy()

            if "nominal_adjust" in _df_detail_show.columns:
                _df_detail_show["nominal_adjust"] = _df_detail_show["nominal_adjust"].apply(
                    lambda v: f"{float(v):+,.0f}".replace(",", ".")
                )

            _col_names_detail = ["Rak", "PLU", "Nama Produk", "Qty Sistem", "Qty Fisik", "Qty Var", "Nominal", "PIC"]
            _df_detail_show.columns = _col_names_detail[:len(_df_detail_show.columns)]

            st.dataframe(_df_detail_show, use_container_width=True, hide_index=True, height=400)

    # === HAPUS SO PER RAK ===
    st.markdown("")
    st.markdown("#### 🗑️ Hapus SO")

    _rak_so_list = [r.get("rak_id") for r in _so_summary_today if r.get("rak_id")]

    if _rak_so_list:
        _col_hapus1, _col_hapus2 = st.columns([3, 1])

        with _col_hapus1:
            _rak_hapus = st.selectbox(
                "Pilih rak yang mau dihapus:",
                options=_rak_so_list,
                key="iso_rak_hapus",
            )

        with _col_hapus2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ HAPUS", use_container_width=True, key="btn_hapus_so"):
                _ok, _msg, _detail = delete_so_by_date(_tanggal, rak_id=_rak_hapus)
                if _ok:
                    st.success(_msg)
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(_msg)


# =========================================================================
# BAGIAN F: INFO PANEL
# =========================================================================
st.markdown("---")
with st.expander("ℹ️ Cara Input SO", expanded=False):
    st.markdown("""
    **📋 Langkah Input SO:**
    
    1. **Pilih Tanggal SO** — default hari ini
    2. **Pilih Rak** — kode rak dari master (contoh: Q51)
    3. **Pilih PIC** — nama yang ngelakuin SO
    4. **Klik ➕ Tambah Produk** — max 10 produk per rak
    5. **Isi Detail Produk:**
       - **PLU**: Kode produk (dari laporan)
       - **Nama Produk**: Nama barang
       - **Qty Sistem**: Stok sistem
       - **Qty Fisik**: Stok fisik (hasil hitung)
       - **Nominal Adjust**: Nominal selisih (boleh minus)
    6. **Isi Keterangan** (opsional)
    7. **Klik 💾 SIMPAN SO**
    
    **💡 Tips:**
    - Input **5 PLU tertinggi** + **5 PLU terendah** per rak
    - **Qty Var** otomatis dihitung = Qty Fisik - Qty Sistem
    - **Total Nominal** auto-sum dari semua produk
    - Data disimpan ke **2 tabel**: `so_hasil` (detail) + `so_rak_harian` (summary)
    - Status rak otomatis jadi **SELESAI** setelah di-SO
    """)


# =========================================================================
# FOOTER
# =========================================================================
st.markdown(
    "<div style='text-align: center; padding: 20px 0; "
    "font-family: Quicksand, sans-serif; font-size: 10px; "
    "color: #7a9b8e; letter-spacing: 1px;'>"
    "📝 Input SO — Toko C383 🎀"
    "</div>",
    unsafe_allow_html=True,
)
