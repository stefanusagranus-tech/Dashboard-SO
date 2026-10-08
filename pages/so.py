"""
SO — Stock Opname (Konsolidasi)
================================
Full replacement pages/input_so.py.

Mode sementara: Multi-Rak + Nominal (tanpa detail per PLU)

Tab:
1. 📝 Input SO   — SPD + Multi-Rak nominal (mode simple)
2. 📊 Analisis   — Top rak + grafik
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
        load_so_summary_by_date,
        delete_so_by_date,
    )
    from modules.master_shift_handler import load_personil_master
    from modules.data_loader import load_rak_master
    from modules.spd_calculator import (
        save_spd_harian,
        hitung_btsb_harian,
    )
    from modules.input_handler import (
        save_input_harian,
        search_rak,
        get_rak_by_kode_exact,
        get_so_rak_detail,
        get_akumulasi_nominal_bulan,
    )
except ImportError as _e:
    st.error(f"❌ Gagal import module: {_e}")
    st.info("💡 Pastikan module `so_handler.py`, `input_handler.py`, `spd_calculator.py`, `data_loader.py`, `master_shift_handler.py` udah ada.")
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

        /* Rak Result Card */
        .rak-result-card {
            background: linear-gradient(135deg, rgba(15, 31, 26, 0.95), rgba(10, 22, 18, 0.92));
            border: 1.5px solid #7FB99B;
            border-radius: 10px;
            padding: 10px 14px;
            margin-bottom: 6px;
        }
        .rak-result-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            font-weight: 900;
            color: #E8B189;
        }
        .rak-result-name {
            font-family: 'Quicksand', sans-serif;
            font-size: 10px;
            color: #7a9b8e;
            margin-top: 2px;
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
# SESSION STATE
# =========================================================================
if "so_rak_list" not in st.session_state:
    st.session_state["so_rak_list"] = []   # list of dict {rak_id, nominal_adjust}

if "so_last_saved" not in st.session_state:
    st.session_state["so_last_saved"] = None

if "so_analisis_loaded" not in st.session_state:
    st.session_state["so_analisis_loaded"] = False

if "so_tab" not in st.session_state:
    st.session_state["so_tab"] = "input"

# ✅ Auto-load existing SO saat tanggal berubah (biar bisa edit)
if "so_last_loaded_date" not in st.session_state:
    st.session_state["so_last_loaded_date"] = None


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
# TAB 1: INPUT SO (SPD + Multi-Rak Nominal)
# =========================================================================
def render_input_so():
    """Input SO: SPD + Multi-Rak (nominal per rak) dalam 1 form."""
    st.markdown("### 📝 Input SO")
    st.caption("Isi SPD (opsional) + rak yang di-SO, lalu klik SIMPAN SEMUA")

    # ============================================================
    # INFO SO
    # ============================================================
    st.markdown("#### 📅 Info SO")

    _col_tgl, _col_pic = st.columns([2, 2])

    with _col_tgl:
        _tanggal = st.date_input(
            "📅 Tanggal SO",
            value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
            key="so_input_tanggal",
        )

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

    # ✅ AUTO-LOAD data existing saat tanggal berubah
    if st.session_state["so_last_loaded_date"] != _tanggal:
        with st.spinner("⏳ Load SO existing..."):
            _existing = load_so_summary_by_date(_tanggal)
        st.session_state["so_rak_list"] = [
            {
                "rak_id": r.get("rak_id"),
                "nominal_adjust": float(r.get("nominal_adjust", 0)),
            }
            for r in (_existing or [])
        ]
        st.session_state["so_last_loaded_date"] = _tanggal
        st.rerun()

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
    # MULTI-RAK (SEARCH + ADD)
    # ============================================================
    st.markdown("#### 📦 Stock Opname (Multi-Rak)")
    st.caption("🔍 Cari rak → klik **+ Add** → isi nominal per rak")

    _search_query = st.text_input(
        "🔍 Cari Rak",
        key="so_search_rak",
        placeholder="Ketik kode rak (contoh: AT, AU, CHILLER)",
    )

    # === HASIL SEARCH ===
    if _search_query and len(_search_query.strip()) >= 2:
        _search_results = search_rak(_search_query, limit=10)

        if _search_results:
            st.caption(f"💡 {len(_search_results)} rak ditemukan:")

            for _idx, _rak in enumerate(_search_results):
                _rid = _rak.get("rak_id", "-")
                _rname = _rak.get("rak_name", "-")
                _status = _rak.get("status_so", "BELUM")

                _already_selected = any(
                    r["rak_id"] == _rid for r in st.session_state["so_rak_list"]
                )

                col_r1, col_r2 = st.columns([4, 1])
                with col_r1:
                    _status_icon = "✅" if _status == "SELESAI" else "⬜"
                    st.markdown(
                        "<div class='rak-result-card'>"
                        f"<div class='rak-result-id'>{_status_icon} {_rid}</div>"
                        f"<div class='rak-result-name'>{_rname}</div>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                with col_r2:
                    if _already_selected:
                        st.button("✓ Ada", key=f"btn_add_{_idx}_{_rid}", disabled=True, width="stretch")
                    else:
                        if st.button("+ Add", key=f"btn_add_{_idx}_{_rid}", width="stretch"):
                            st.session_state["so_rak_list"].append({
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
    # LIST RAK TERPILIH + INPUT NOMINAL
    # ============================================================
    if st.session_state["so_rak_list"]:
        st.markdown(f"#### 📋 Rak Terpilih ({len(st.session_state['so_rak_list'])})")
        st.caption("Isi nominal adjustment per rak (bisa +/-)")

        _items_to_remove = []

        for _idx, _item in enumerate(st.session_state["so_rak_list"]):
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
                    f"<div style='font-family: \"JetBrains Mono\", monospace;"
                    f"font-size: 14px; font-weight: 900; color: #E8B189;'>{_rid}</div>"
                    f"<div style='font-family: \"Quicksand\", sans-serif;"
                    f"font-size: 10px; color: #7a9b8e; margin-top: 2px;'>{_rname}</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )

            with col_d2:
                _new_nominal = st.number_input(
                    f"Nominal #{_idx+1}",
                    min_value=-999_999_999,
                    max_value=999_999_999,
                    step=1000,
                    value=int(_item.get("nominal_adjust", 0)),
                    key=f"nominal_{_rid}_{_idx}",
                    label_visibility="collapsed",
                )
                st.session_state["so_rak_list"][_idx]["nominal_adjust"] = float(_new_nominal)

            with col_d3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"btn_del_{_rid}_{_idx}"):
                    _items_to_remove.append(_idx)

        if _items_to_remove:
            for _i in sorted(_items_to_remove, reverse=True):
                st.session_state["so_rak_list"].pop(_i)
            st.rerun()

        # Total nominal
        _total_nominal_input = sum(
            item.get("nominal_adjust", 0)
            for item in st.session_state["so_rak_list"]
        )
        _color_total = "#E88B8B" if _total_nominal_input < 0 else "#7FB99B"
        _sign_total = "+" if _total_nominal_input >= 0 else ""

        st.markdown(
            "<div style='"
            "background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.85));"
            f"border: 2px solid {_color_total};"
            "border-radius: 12px;"
            "padding: 14px 20px;"
            "margin-top: 16px;"
            "text-align: center;"
            "'>"
            "<div style='font-family: monospace; font-size: 10px;"
            "color: #7a9b8e; letter-spacing: 1.5px;'>💰 TOTAL NOMINAL SO</div>"
            f"<div style='font-family: \"JetBrains Mono\", monospace;"
            f"font-size: 22px; font-weight: 900; color: {_color_total};"
            f"margin-top: 6px;'>{_sign_total}{fmt_rp(_total_nominal_input)}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("📭 Belum ada rak. Cari & klik **+ Add** untuk menambahkan.")

    st.markdown("---")

    # ============================================================
    # KETERANGAN
    # ============================================================
    _keterangan = st.text_input(
        "📝 Keterangan (opsional)",
        placeholder="Contoh: Pendingan rak FE1 1 item",
        key="so_input_keterangan",
    )

    # ============================================================
    # SIMPAN
    # ============================================================
    st.markdown("---")

    _col_save, _col_cancel = st.columns([2, 1])

    with _col_save:
        if st.button(
            "💾 SIMPAN SEMUA",
            width="stretch",
            type="primary",
            key="btn_save_all_so",
        ):
            _has_rak = len(st.session_state["so_rak_list"]) > 0
            _has_spd = _spd_val > 0

            if not _has_rak and not _has_spd:
                st.error("⚠️ Minimal isi SPD atau tambahkan 1 rak!")
            elif not _pic_pilih:
                st.error("⚠️ Pilih/isi PIC dulu")
            else:
                with st.spinner("⏳ Menyimpan..."):
                    _ok, _msg, _detail = save_input_harian(
                        tanggal=_tanggal,
                        spd=_spd_val,
                        rak_items=st.session_state["so_rak_list"],
                        keterangan=_keterangan,
                        pic=_pic_pilih,
                        update_status_rak=True,
                    )

                if _ok:
                    st.session_state["so_last_saved"] = _msg
                    st.session_state["so_rak_list"] = []
                    st.session_state["so_last_loaded_date"] = None
                    st.cache_data.clear()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(_msg)

    with _col_cancel:
        if st.button(
            "🗑️ Clear Semua",
            width="stretch",
            key="btn_clear_so",
        ):
            st.session_state["so_rak_list"] = []
            st.rerun()


# =========================================================================
# TAB 2: ANALISIS SO
# =========================================================================
def render_analisis():
    """Analisis SO: nominal per rak + summary."""
    st.markdown("### 📊 Analisis SO")
    st.caption("Analisis nominal SO per rak dalam periode tertentu")

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
            _akumulasi = get_akumulasi_nominal_bulan()

        # === METRIC SUMMARY ===
        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            st.metric("🏪 Total Rak di-SO", f"{_akumulasi.get('total_rak', 0)}")
        with _c2:
            st.metric("📅 Jumlah Hari", f"{_akumulasi.get('jumlah_hari', 0)}")
        with _c3:
            _total_nom = _akumulasi.get("total_nominal", 0)
            st.metric("💰 Total Nominal SO", fmt_rp(_total_nom))

        st.markdown("---")

        # === GRAFIK PER RAK ===
        st.markdown("#### 📊 Nominal SO per Rak")

        try:
            _so_detail = get_so_rak_detail(limit=500)

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
                st.info("📭 Belum ada data SO")

        except Exception as _e_chart:
            st.warning(f"⚠️ Chart gagal render: {str(_e_chart)[:150]}")
    else:
        st.info("💡 Pilih periode & klik **🔍 Analisis** untuk mulai"
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