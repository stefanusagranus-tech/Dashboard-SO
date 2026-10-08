"""
SO — Stock Opname (Konsolidasi)
================================
Full replacement pages/input_so.py.

Tab:
1. 📝 Input SO   — SPD + Multi-Produk SO dalam 1 form
2. 📊 Analisis   — Top produk minus/plus + grafik
3. 📋 Preview    — Preview & hapus SO per rak
"""

import streamlit as st
import time
import pandas as pd
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
        save_so_input,
        load_so_detail_by_date,
        load_so_summary_by_date,
        delete_so_by_date,
        get_so_analytics,
    )
    from modules.master_shift_handler import load_personil_master
    from modules.data_loader import load_rak_master
    from modules.spd_calculator import (
        save_spd_harian,
        hitung_btsb_harian,
    )
except ImportError as _e:
    st.error(f"❌ Gagal import module: {_e}")
    st.info("💡 Pastikan `modules/so_handler.py`, `data_loader.py`, `spd_calculator.py`, `master_shift_handler.py` udah ada.")
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

        /* Summary Card CSS */
        .summary-card {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.85), rgba(76, 29, 149, 0.65));
            border: 2px solid #E8B189;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            text-align: center;
        }
        .summary-card .label {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: #7FB99B;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }
        .summary-card .value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 22px;
            font-weight: 900;
            color: #E8B189;
            margin-top: 6px;
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
        if st.button("← Dashboard", key="btn_back_so", width="stretch"):
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
            "📝 STOCK OPNAME 📝</div>"
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
# SESSION STATE (WAJIB — biar gak ilang pas switch page)
# =========================================================================
if "so_produk_list" not in st.session_state:
    st.session_state["so_produk_list"] = []

if "so_last_saved" not in st.session_state:
    st.session_state["so_last_saved"] = None

if "so_analisis_loaded" not in st.session_state:
    st.session_state["so_analisis_loaded"] = False

if "so_tab" not in st.session_state:
    st.session_state["so_tab"] = "input"


# =========================================================================
# NOTIFIKASI SUKSES
# =========================================================================
if st.session_state["so_last_saved"]:
    st.success(st.session_state["so_last_saved"])
    st.balloons()
    st.session_state["so_last_saved"] = None
    time.sleep(1)


# =========================================================================
# LOAD MASTER DATA (cached)
# =========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def _load_master():
    _rak_df = load_rak_master()
    _personil_df = load_personil_master(only_active=True)
    return _rak_df, _personil_df


_rak_df, _personil_df = _load_master()
_rak_list = _rak_df["rak_id"].tolist() if not _rak_df.empty else []
_personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []


# =========================================================================
# HELPER
# =========================================================================
def fmt_rp(value):
    try:
        return f"Rp {int(value):,.0f}".replace(",", ".")
    except Exception:
        return "Rp 0"


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
            width="stretch",
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["so_tab"] = _key
            st.rerun()

st.markdown("---")
# =========================================================================
# TAB 1: INPUT SO (SPD + Multi-Produk — 1 FORM)
# =========================================================================
def render_input_so():
    """Input SO: SPD + Multi-Produk dalam 1 form."""
    st.markdown("### 📝 Input SO")
    st.caption("Isi SPD (opsional) + produk yang di-SO, lalu klik SIMPAN SEMUA")

    # ============================================================
    # INFO SO
    # ============================================================
    st.markdown("#### 📅 Info SO")

    _col_tgl, _col_rak, _col_pic = st.columns([2, 2, 2])

    with _col_tgl:
        _tanggal = st.date_input(
            "📅 Tanggal SO",
            value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
            key="so_input_tanggal",
        )

    with _col_rak:
        if _rak_list:
            _rak_pilih = st.selectbox(
                "🏪 Kode Rak",
                options=_rak_list,
                key="so_input_rak",
                help="Pilih rak yang di-SO",
            )
        else:
            st.warning("⚠️ Master rak kosong")
            _rak_pilih = None

    with _col_pic:
        if _personil_list:
            _pic_pilih = st.selectbox(
                "👤 PIC (Nama)",
                options=_personil_list,
                key="so_input_pic",
                help="Pilih nama penanggung jawab SO",
            )
        else:
            _pic_pilih = st.text_input(
                "👤 PIC (Nama)",
                placeholder="Ketik nama PIC",
                key="so_input_pic_manual",
            )

    st.markdown("---")

    # ============================================================
    # SPD (OPSIONAL)
    # ============================================================
    st.markdown("#### 💰 SPD Hari Ini (Opsional)")
    st.caption("Kosongkan / isi 0 kalau belum ada SPD hari ini")

    _spd_val = st.number_input(
        "SPD (Rp)",
        min_value=0,
        max_value=999_999_999_999,
        step=100_000,
        value=0,
        key="so_input_spd",
    )

    if _spd_val > 0:
        _btsb = hitung_btsb_harian(_spd_val)
        st.success(f"💡 BTSB Otomatis: **{fmt_rp(_btsb)}** (0,15% × SPD)")
    else:
        st.info("💡 BTSB: — (SPD = 0)")

    st.markdown("---")

    # ============================================================
    # MULTI-PRODUK
    # ============================================================
    st.markdown("#### 📦 Input Produk (Multi-Produk)")
    st.caption("💡 Input 5 PLU tertinggi + 5 PLU terendah (max 10 produk per rak)")

    _col_btn_add, _col_info = st.columns([2, 5])

    with _col_btn_add:
        if st.button("➕ Tambah Produk", width="stretch", key="btn_add_produk_so"):
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
        st.markdown(
            f"<div style='padding-top: 8px; color: #7FB99B; font-size: 12px;'>"
            f"📊 **{_count} / 10** produk terinput</div>",
            unsafe_allow_html=True,
        )

    # === LIST PRODUK ===
    if st.session_state["so_produk_list"]:
        st.markdown("")
        _items_to_remove = []

        for _idx, _produk in enumerate(st.session_state["so_produk_list"]):
            _nama_show = _produk.get("nama_produk") or "(belum diisi)"
            with st.expander(f"📦 Produk #{_idx+1}: {_nama_show}", expanded=True):
                _c1, _c2, _c3, _c4, _c5, _c6 = st.columns([2, 3, 1, 1, 2, 0.8])

                with _c1:
                    _new_plu = st.text_input(
                        "PLU",
                        value=_produk.get("plu", ""),
                        key=f"so_plu_{_idx}",
                        placeholder="433288",
                    )
                    st.session_state["so_produk_list"][_idx]["plu"] = _new_plu

                with _c2:
                    _new_nama = st.text_input(
                        "Nama Produk",
                        value=_produk.get("nama_produk", ""),
                        key=f"so_nama_{_idx}",
                        placeholder="Baygon AEO Japan P",
                    )
                    st.session_state["so_produk_list"][_idx]["nama_produk"] = _new_nama

                with _c3:
                    _new_qty_sis = st.number_input(
                        "Qty Sistem",
                        min_value=0,
                        max_value=99999,
                        value=int(_produk.get("qty_sistem", 0)),
                        key=f"so_qty_sis_{_idx}",
                        step=1,
                    )
                    st.session_state["so_produk_list"][_idx]["qty_sistem"] = int(_new_qty_sis)

                with _c4:
                    _new_qty_fis = st.number_input(
                        "Qty Fisik",
                        min_value=0,
                        max_value=99999,
                        value=int(_produk.get("qty_fisik", 0)),
                        key=f"so_qty_fis_{_idx}",
                        step=1,
                    )
                    st.session_state["so_produk_list"][_idx]["qty_fisik"] = int(_new_qty_fis)

                with _c5:
                    _new_nominal = st.number_input(
                        "Nominal Adjust (Rp)",
                        min_value=-999_999_999,
                        max_value=999_999_999,
                        value=int(_produk.get("nominal_adjust", 0)),
                        key=f"so_nom_{_idx}",
                        step=1000,
                        help="Nominal selisih dari laporan SO (boleh minus)",
                    )
                    st.session_state["so_produk_list"][_idx]["nominal_adjust"] = float(_new_nominal)

                with _c6:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"so_del_{_idx}"):
                        _items_to_remove.append(_idx)

        # Hapus item
        if _items_to_remove:
            for _i in sorted(_items_to_remove, reverse=True):
                st.session_state["so_produk_list"].pop(_i)
            st.rerun()
    else:
        st.info("📭 Belum ada produk. Klik ➕ Tambah Produk untuk mulai.")

    # ============================================================
    # KETERANGAN
    # ============================================================
    st.markdown("---")
    _keterangan = st.text_input(
        "📝 Keterangan (opsional)",
        placeholder="Contoh: Pendingan rak FE1 1 item",
        key="so_input_keterangan",
    )

    # ============================================================
    # SUMMARY + SIMPAN
    # ============================================================
    if st.session_state["so_produk_list"]:
        st.markdown("---")
        st.markdown("#### 📊 Summary")

        _total_item = len(st.session_state["so_produk_list"])
        _total_qty_var = sum(
            int(p.get("qty_fisik", 0)) - int(p.get("qty_sistem", 0))
            for p in st.session_state["so_produk_list"]
        )
        _total_nominal = sum(
            float(p.get("nominal_adjust", 0))
            for p in st.session_state["so_produk_list"]
        )

        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            st.metric("📦 Total Produk", f"{_total_item}")
        with _c2:
            st.metric("📊 Total Qty Var", f"{_total_qty_var}")
        with _c3:
            st.metric("💰 Total Nominal", fmt_rp(_total_nominal))

        st.markdown("")
        _col_save, _col_cancel = st.columns([2, 1])

        with _col_save:
            if st.button(
                "💾 SIMPAN SEMUA",
                width="stretch",
                type="primary",
                key="btn_save_all_so",
            ):
                # Validasi
                _produk_valid = [
                    p for p in st.session_state["so_produk_list"]
                    if p.get("plu") and p.get("nama_produk")
                ]

                if not _produk_valid:
                    st.error("⚠️ Minimal 1 produk harus diisi PLU & Nama")
                elif not _rak_pilih:
                    st.error("⚠️ Pilih rak dulu")
                elif not _pic_pilih:
                    st.error("⚠️ Pilih/isi PIC dulu")
                else:
                    with st.spinner("⏳ Menyimpan..."):
                        # 1. Simpan SPD kalau > 0
                        _spd_ok = True
                        if _spd_val > 0:
                            _spd_ok, _spd_msg = save_spd_harian(
                                _tanggal, _spd_val, _keterangan
                            )

                        # 2. Simpan SO
                        _so_ok, _so_msg, _detail = save_so_input(
                            tanggal=_tanggal,
                            rak_id=_rak_pilih,
                            pic=_pic_pilih,
                            produk_list=_produk_valid,
                            keterangan=_keterangan,
                        )

                    # Build pesan
                    _pesan_parts = []
                    if _spd_val > 0 and _spd_ok:
                        _pesan_parts.append(f"SPD {fmt_rp(_spd_val)}")
                    if _so_ok:
                        _pesan_parts.append(f"{len(_produk_valid)} produk di-SO")

                    if _so_ok:
                        _pesan = "✅ Tersimpan: " + " • ".join(_pesan_parts)
                        st.session_state["so_last_saved"] = _pesan
                        st.session_state["so_produk_list"] = []
                        st.cache_data.clear()
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(_so_msg)

        with _col_cancel:
            if st.button(
                "🗑️ Clear Semua",
                width="stretch",
                key="btn_clear_so",
            ):
                st.session_state["so_produk_list"] = []
                st.rerun()


# =========================================================================
# TAB 2: ANALISIS SO
# =========================================================================
def render_analisis():
    """Analisis SO: top produk minus/plus + grafik per rak."""
    st.markdown("### 📊 Analisis SO")
    st.caption("Analisis selisih produk & rak dalam periode tertentu")

    # ============================================================
    # FILTER PERIODE
    # ============================================================
    _col_p1, _col_p2, _col_p3 = st.columns([2, 2, 1])

    with _col_p1:
        _tgl_start = st.date_input(
            "📅 Dari Tanggal",
            value=date.today().replace(day=1),
            key="so_analisis_start",
        )

    with _col_p2:
        _tgl_end = st.date_input(
            "📅 Sampai Tanggal",
            value=date.today(),
            key="so_analisis_end",
        )

    with _col_p3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Analisis", width="stretch", type="primary", key="btn_analisis_so"):
            st.session_state["so_analisis_loaded"] = True
            st.session_state["so_analisis_periode"] = (_tgl_start, _tgl_end)

    # ============================================================
    # HASIL ANALISIS
    # ============================================================
    if st.session_state["so_analisis_loaded"]:
        _start, _end = st.session_state.get("so_analisis_periode", (_tgl_start, _tgl_end))

        with st.spinner("⏳ Load analytics..."):
            _analytics = get_so_analytics(_start, _end)

        # === METRIC SUMMARY ===
        _total_produk = _analytics.get("total_produk", 0)

        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            st.metric("📦 Total Produk di-SO", f"{_total_produk}")
        with _c2:
            _total_minus = sum(
                float(p.get("nominal", 0)) for p in _analytics.get("top_minus", [])
            )
            st.metric("📉 Total Minus (Top 5)", fmt_rp(_total_minus))
        with _c3:
            _total_plus = sum(
                float(p.get("nominal", 0)) for p in _analytics.get("top_plus", [])
            )
            st.metric("📈 Total Plus (Top 5)", fmt_rp(_total_plus))

        st.markdown("---")

        # === TOP 5 MINUS ===
        st.markdown("#### 📉 Top 5 Produk Minus Terbesar")
        _top_minus = _analytics.get("top_minus", [])

        if _top_minus:
            _df_minus = pd.DataFrame(_top_minus)
            _df_minus.columns = ["PLU", "Nama Produk", "Qty Var", "Nominal", "Rak", "PIC"][:_df_minus.shape[1]]
            st.dataframe(_df_minus, width="stretch", hide_index=True)
        else:
            st.success("✅ Tidak ada produk minus di periode ini")

        st.markdown("---")

        # === TOP 5 PLUS ===
        st.markdown("#### 📈 Top 5 Produk Plus Terbesar")
        _top_plus = _analytics.get("top_plus", [])

        if _top_plus:
            _df_plus = pd.DataFrame(_top_plus)
            _df_plus.columns = ["PLU", "Nama Produk", "Qty Var", "Nominal", "Rak", "PIC"][:_df_plus.shape[1]]
            st.dataframe(_df_plus, width="stretch", hide_index=True)
        else:
            st.info("📭 Tidak ada produk plus di periode ini")

        st.markdown("---")

        # === GRAFIK PER RAK ===
        st.markdown("#### 📊 Nominal SO per Rak")

        try:
            _so_detail = load_so_detail_by_date(_end)

            if _so_detail:
                _df = pd.DataFrame(_so_detail)
                if "nominal_adjust" in _df.columns and "rak_id" in _df.columns:
                    _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
                    _grp = _df.groupby("rak_id")["nominal_adjust"].sum().reset_index()
                    _grp = _grp.sort_values("nominal_adjust", ascending=True).head(20)

                    import plotly.graph_objects as go

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

                    st.plotly_chart(_fig, width="stretch", key="chart_nominal_per_rak_so")
                else:
                    st.info("📭 Data SO kosong")
            else:
                st.info(f"📭 Belum ada data SO untuk tanggal **{_end.strftime('%d/%m/%Y')}**")

        except Exception as _e_chart:
            st.warning(f"⚠️ Chart gagal render: {str(_e_chart)[:150]}")
    else:
        st.info("💡 Pilih periode & klik **🔍 Analisis** untuk mulai")
    # =========================================================================
# TAB 3: PREVIEW & HAPUS
# =========================================================================
def render_preview():
    """Preview SO hari ini + hapus per rak."""
    st.markdown("### 📋 Preview & Hapus SO")
    st.caption("Lihat semua SO yang sudah diinput & hapus kalau perlu")

    # ============================================================
    # PILIH TANGGAL
    # ============================================================
    _tanggal = st.date_input(
        "📅 Pilih Tanggal",
        value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
        key="so_preview_tanggal",
    )

    with st.spinner("⏳ Load SO..."):
        _so_summary = load_so_summary_by_date(_tanggal)
        _so_detail = load_so_detail_by_date(_tanggal)

    # ============================================================
    # EMPTY STATE
    # ============================================================
    if not _so_summary:
        st.info(f"📭 Belum ada SO untuk tanggal **{_tanggal.strftime('%d/%m/%Y')}**")
        return

    # ============================================================
    # SUMMARY METRIC
    # ============================================================
    _total_rak = len(_so_summary)
    _total_item = sum(int(r.get("total_item", 0)) for r in _so_summary)
    _total_nominal = sum(float(r.get("nominal_adjust", 0)) for r in _so_summary)

    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.metric("🏪 Total Rak di-SO", f"{_total_rak}")
    with _c2:
        st.metric("📦 Total Produk", f"{_total_item}")
    with _c3:
        st.metric("💰 Total Nominal", fmt_rp(_total_nominal))

    st.markdown("---")

    # ============================================================
    # TABEL SUMMARY PER RAK
    # ============================================================
    st.markdown("#### 📊 Summary per Rak")

    _df_summary = pd.DataFrame(_so_summary)

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

        st.dataframe(_df_show, width="stretch", hide_index=True)

    # ============================================================
    # DETAIL PRODUK (EXPANDER)
    # ============================================================
    if _so_detail:
        st.markdown("---")
        with st.expander(f"🔍 Detail Produk ({len(_so_detail)} produk)", expanded=False):
            _df_detail = pd.DataFrame(_so_detail)
            _cols_detail = ["rak_id", "plu", "nama_produk", "qty_sistem", "qty_fisik", "qty_var", "nominal_adjust", "pic"]
            _cols_detail = [c for c in _cols_detail if c in _df_detail.columns]

            _df_detail_show = _df_detail[_cols_detail].copy()

            if "nominal_adjust" in _df_detail_show.columns:
                _df_detail_show["nominal_adjust"] = _df_detail_show["nominal_adjust"].apply(
                    lambda v: f"{float(v):+,.0f}".replace(",", ".")
                )

            _col_names_detail = ["Rak", "PLU", "Nama Produk", "Qty Sistem", "Qty Fisik", "Qty Var", "Nominal", "PIC"]
            _df_detail_show.columns = _col_names_detail[:len(_df_detail_show.columns)]

            st.dataframe(_df_detail_show, width="stretch", hide_index=True, height=400)

    # ============================================================
    # HAPUS SO PER RAK
    # ============================================================
    st.markdown("---")
    st.markdown("#### 🗑️ Hapus SO")

    _rak_so_list = [r.get("rak_id") for r in _so_summary if r.get("rak_id")]

    if _rak_so_list:
        _col_h1, _col_h2 = st.columns([3, 1])

        with _col_h1:
            _rak_hapus = st.selectbox(
                "Pilih rak yang mau dihapus:",
                options=_rak_so_list,
                key="so_preview_rak_hapus",
            )

        with _col_h2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ HAPUS", width="stretch", key="btn_hapus_so"):
                with st.spinner(f"⏳ Hapus SO rak {_rak_hapus}..."):
                    _ok, _msg, _detail = delete_so_by_date(_tanggal, rak_id=_rak_hapus)

                if _ok:
                    st.success(_msg)
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(_msg)


# =========================================================================
# INFO PANEL — CARA INPUT SO
# =========================================================================
with st.expander("ℹ️ Cara Input SO", expanded=False):
    st.markdown("""
    **📋 Langkah Input SO:**
    
    1. **Pilih Tanggal SO** — default hari ini
    2. **Pilih Rak** — kode rak dari master (contoh: Q51)
    3. **Pilih PIC** — nama yang ngelakuin SO
    4. **Isi SPD** (opsional) — kalau ada penjualan hari ini
    5. **Klik ➕ Tambah Produk** — max 10 produk per rak
    6. **Isi Detail Produk:**
       - **PLU**: Kode produk (dari laporan)
       - **Nama Produk**: Nama barang
       - **Qty Sistem**: Stok sistem
       - **Qty Fisik**: Stok fisik (hasil hitung)
       - **Nominal Adjust**: Nominal selisih (boleh minus)
    7. **Isi Keterangan** (opsional)
    8. **Klik 💾 SIMPAN SEMUA**
    
    **💡 Tips:**
    - Input **5 PLU tertinggi** + **5 PLU terendah** per rak
    - **Qty Var** otomatis dihitung = Qty Fisik - Qty Sistem
    - **Total Nominal** auto-sum dari semua produk
    - Data disimpan ke **2 tabel**: `so_hasil` (detail) + `so_rak_harian` (summary)
    - Status rak otomatis jadi **SELESAI** setelah di-SO
    - SPD disimpan terpisah ke tabel `spd_harian`
    """)


# =========================================================================
# ROUTING TAB
# =========================================================================
_tab = st.session_state["so_tab"]

if _tab == "input":
    render_input_so()
elif _tab == "analisis":
    render_analisis()
elif _tab == "preview":
    render_preview()


# =========================================================================
# FOOTER
# =========================================================================
st.markdown(
    "<div style='text-align: center; padding: 20px 0; "
    "font-family: Quicksand, sans-serif; font-size: 10px; "
    "color: #7a9b8e; letter-spacing: 1px;'>"
    "📝 Stock Opname — Toko C383 🎀"
    "</div>",
    unsafe_allow_html=True,
)