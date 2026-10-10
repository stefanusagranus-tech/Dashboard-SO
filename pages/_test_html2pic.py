"""
Test pictex — Premium Report + Double Chart
=============================================
"""
import streamlit as st
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


st.set_page_config(page_title="Test pictex", page_icon="🎨", layout="wide")
st.title("🎨 Test pictex — Premium Report")


# =========================================================
# PALET PREMIUM
# =========================================================
WARNA = {
    "bg": "#FAF8F3",           # off-white warm
    "accent": "#7B9B95",        # sage premium (lebih gelap)
    "accent_dark": "#4A6B65",   # sage deep
    "accent_light": "#D9E4E0",  # sage pale
    "highlight": "#F5EFE3",     # warm highlight
    "text_primary": "#1F2937",  # slate dark
    "text_secondary": "#6B7280",# grey medium
    "text_muted": "#9CA3AF",    # grey light
    "divider": "#E5E1D8",       # warm divider
    "white": "#FFFFFF",
    "red": "#B8383A",           # merah elegan
    "green": "#4A7C59",         # hijau elegan
    "bar": "#C9D6D2",           # bar color (sage soft)
}


# =========================================================
# DATA DUMMY
# =========================================================
_data = {
    "periode": "2026-10-10 s/d 2026-10-10",
    "tanggal": "10 Oktober 2026",
    "total_rak": 3,
    "total_item": 21,
    "total_nominal": -34556,
    "sales_periode": 10,
    "btsb": 0,
    "status": "OVER",
    "insight": (
        "Rak S14 menyumbang minus terbesar (-Rp 24.785) oleh PIC REZA. "
        "Total selisih periode melebihi batas BTSB — perlu perhatian."
    ),
    "list_rak": [
        {"rak_id": "S14", "nama": "PERSONAL & TOOTH CARE 4", "pic": "REZA", "nominal": -24785},
        {"rak_id": "S15", "nama": "PERSONAL & TOOTH CARE 5", "pic": "KUSDEWI", "nominal": -10273},
        {"rak_id": "800", "nama": "RAK CUSTOM", "pic": "REZA", "nominal": 503},
    ],
    "trend_data": [
        {"tanggal": "06/10", "nominal": -10878},
        {"tanggal": "07/10", "nominal": -24316},
        {"tanggal": "08/10", "nominal": 9948},
        {"tanggal": "09/10", "nominal": -41592},
        {"tanggal": "10/10", "nominal": -34556},
    ],
}


# =========================================================
# HELPER
# =========================================================
def _fmt_rp(val):
    _n = int(round(float(val)))
    _sign = "+" if _n >= 0 else "-"
    return f"{_sign}Rp {abs(_n):,}".replace(",", ".")


def _fmt_rp_no_sign(val):
    _n = int(round(float(val)))
    return f"Rp {abs(_n):,}".replace(",", ".")


# =========================================================
# CHART 1: DONUT — premium
# =========================================================
def _chart_donut(list_rak, output_path, size_px=400):
    _sorted = sorted(list_rak, key=lambda x: abs(x["nominal"]), reverse=True)
    _labels = [f"Rak {r['rak_id']}" for r in _sorted if abs(r["nominal"]) > 0]
    _sizes = [abs(r["nominal"]) for r in _sorted if abs(r["nominal"]) > 0]

    if not _sizes:
        return None

    _colors = ["#7B9B95", "#C9D6D2", "#D9E4E0", "#B8C5BF", "#9BAAA4", "#E5E1D8"]
    _dpi = 100
    _fig_size = size_px / _dpi

    fig, ax = plt.subplots(figsize=(_fig_size, _fig_size), dpi=_dpi)
    fig.patch.set_facecolor(WARNA["white"])
    ax.set_facecolor(WARNA["white"])

    wedges, texts, autotexts = ax.pie(
        _sizes,
        labels=_labels,
        colors=_colors[:len(_sizes)],
        autopct=lambda p: f"{p:.0f}%",
        startangle=90,
        wedgeprops=dict(width=0.36, edgecolor="white", linewidth=3),
        textprops=dict(color=WARNA["text_secondary"], fontsize=11, fontweight="normal"),
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(11)
        at.set_fontweight("bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["white"])
    plt.close(fig)
    return output_path


# =========================================================
# CHART 2: DOUBLE CHART — Bar + Line Overlay
# =========================================================
def _chart_double(trend_data, output_path, width_px=960, height_px=280):
    """Bar chart + line chart overlay."""
    if not trend_data:
        return None

    _labels = [t["tanggal"] for t in trend_data]
    _values = [t["nominal"] for t in trend_data]

    _dpi = 100
    _fig_size = (width_px / _dpi, height_px / _dpi)

    fig, ax = plt.subplots(figsize=_fig_size, dpi=_dpi)
    fig.patch.set_facecolor(WARNA["white"])
    ax.set_facecolor(WARNA["white"])

    _x = np.arange(len(_labels))

    # === BAR CHART ===
    # Warna dinamis: merah kalau minus, hijau kalau plus
    _bar_colors = [WARNA["red"] if v < 0 else WARNA["green"] for v in _values]
    _bars = ax.bar(
        _x, _values,
        color=_bar_colors,
        width=0.55,
        alpha=0.55,
        edgecolor="white",
        linewidth=1,
        label="Nominal Harian",
    )

    # === LINE CHART (overlay) ===
    _line = ax.plot(
        _x, _values,
        color=WARNA["accent_dark"],
        linewidth=2.5,
        marker="o",
        markersize=8,
        markerfacecolor="white",
        markeredgecolor=WARNA["accent_dark"],
        markeredgewidth=2,
        label="Trend",
        zorder=5,
    )

    # === AXIS ===
    ax.axhline(0, color=WARNA["text_muted"], linewidth=0.8, linestyle="-", alpha=0.5)
    ax.set_xticks(_x)
    ax.set_xticklabels(_labels)

    ax.tick_params(axis="x", labelsize=10, colors=WARNA["text_secondary"])
    ax.tick_params(axis="y", labelsize=9, colors=WARNA["text_muted"])

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(WARNA["divider"])
    ax.grid(axis="y", linestyle=":", alpha=0.3, color=WARNA["divider"])
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", ".")))

    # === LEGEND ===
    ax.legend(
        loc="upper right",
        frameon=False,
        fontsize=9,
        labelcolor=WARNA["text_secondary"],
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["white"])
    plt.close(fig)
    return output_path
    

# =========================================================
# KONSTRUKSI INFOGRAFIS — PREMIUM REPORT
# =========================================================
def _build_infografis(data, tmp_dir):
    from pictex import Canvas, Row, Column, Text, Image

    _W = 1000
    _H = 1420

    # === GENERATE CHART PNG ===
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _double_path = os.path.join(tmp_dir, "chart_double.png")
    _chart_donut(data["list_rak"], _donut_path, size_px=400)
    _chart_double(data["trend_data"], _double_path, width_px=960, height_px=280)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=_H)
        .background_color(WARNA["bg"])
        .padding(50)
    )

    # =========================================================
    # HEADER — Premium Report Style
    # =========================================================
    header_bar = (
        Column(Text("").font_size(1))
        .width(80)
        .background_color(WARNA["accent"])
    )

    header_text = (
        Column(
            Text("LAPORAN STOCK OPNAME").font_size(28).color(WARNA["text_primary"]).font_weight("bold"),
            Text("Toko C383 — Karang Satria").font_size(13).color(WARNA["text_secondary"]),
            Text(data["periode"]).font_size(11).color(WARNA["text_muted"]),
        )
        .width(880)
        .gap(3)
    )

    header = Row(header_bar, header_text).gap(20).width(_W)

    divider_top = (
        Column(Text("").font_size(1))
        .width(_W)
        .background_color(WARNA["divider"])
    )

    # =========================================================
    # KPI — 3 card dengan background warm
    # =========================================================
    kpi_row = Row(
        Column(
            Text("TOTAL RAK").font_size(10).color(WARNA["text_muted"]).font_weight("bold"),
            Text(f"{data['total_rak']}").font_size(52).color(WARNA["text_primary"]).font_weight("bold"),
            Text("rak ter-SO").font_size(11).color(WARNA["text_secondary"]),
        ).width(320).padding(20).background_color(WARNA["highlight"]).border_radius(10).gap(2),

        Column(
            Text("TOTAL ITEM").font_size(10).color(WARNA["text_muted"]).font_weight("bold"),
            Text(f"{data['total_item']}").font_size(52).color(WARNA["text_primary"]).font_weight("bold"),
            Text("item tercatat").font_size(11).color(WARNA["text_secondary"]),
        ).width(320).padding(20).background_color(WARNA["highlight"]).border_radius(10).gap(2),

        Column(
            Text("TOTAL NOMINAL").font_size(10).color(WARNA["text_muted"]).font_weight("bold"),
            Text(_fmt_rp(data['total_nominal'])).font_size(34).color(WARNA["red"]).font_weight("bold"),
            Text("selisih periode").font_size(11).color(WARNA["text_secondary"]),
        ).width(320).padding(20).background_color(WARNA["highlight"]).border_radius(10).gap(2),
    ).gap(20).width(_W)

    # =========================================================
    # SECTION TITLE — Accent bar kiri
    # =========================================================
    def _section_title(num, title):
        return Row(
            Text("▌").font_size(18).color(WARNA["accent"]).font_weight("bold"),
            Text(f"{num}").font_size(12).color(WARNA["accent_dark"]).font_weight("bold").width(30),
            Text(title).font_size(14).color(WARNA["text_primary"]).font_weight("bold"),
        ).width(_W).gap(8)

    # =========================================================
    # SECTION 01 — DISTRIBUSI
    # =========================================================
    _title_01 = _section_title("01", "DISTRIBUSI PER RAK")

    _donut_col = (
        Column(
            Image(_donut_path).width(360),
        )
        .width(400)
        .padding(0)
        .gap(0)
    )

    # Ringkasan — pakai titik dua biar rapi
    _ringkasan_col = (
        Column(
            Text("RINGKASAN PERIODE").font_size(12).color(WARNA["text_muted"]).font_weight("bold"),
            Row(
                Text("Tanggal").font_size(12).color(WARNA["text_secondary"]).width(150),
                Text(data["periode"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Total Rak").font_size(12).color(WARNA["text_secondary"]).width(150),
                Text(f"{data['total_rak']} rak").font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Nominal SO").font_size(12).color(WARNA["text_secondary"]).width(150),
                Text(_fmt_rp(data["total_nominal"])).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Sales Periode").font_size(12).color(WARNA["text_secondary"]).width(150),
                Text(_fmt_rp_no_sign(data["sales_periode"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("BTSB (0,15%)").font_size(12).color(WARNA["text_secondary"]).width(150),
                Text(_fmt_rp_no_sign(data["btsb"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Status").font_size(12).color(WARNA["text_secondary"]).width(150),
                Text(data["status"]).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ).gap(15),
        )
        .width(560)
        .padding(24)
        .background_color(WARNA["white"])
        .border_radius(10)
        .gap(12)
    )

    _mid_row = Row(_donut_col, _ringkasan_col).gap(30).width(_W)

    # =========================================================
    # SECTION 02 — INSIGHT (Highlight Box)
    # =========================================================
    _title_02 = _section_title("02", "INSIGHT")

    insight = (
        Column(
            Text(data["insight"]).font_size(13).color(WARNA["text_primary"]),
        )
        .width(_W - 20)
        .padding(22)
        .background_color(WARNA["accent_light"])
        .border_radius(10)
        .gap(0)
    )
    
    # =========================================================
    # SECTION 03 — DETAIL PER RAK (Tabel Premium)
    # =========================================================
    _title_03 = _section_title("03", "DETAIL PER RAK")

    _col_w = [100, 420, 160, 280]

    # Header tabel — bg sage tipis + text sage dark
    _header_cells = Row(
        Text("RAK").font_size(11).color(WARNA["accent_dark"]).font_weight("bold").padding(12).width(_col_w[0]),
        Text("NAMA RAK").font_size(11).color(WARNA["accent_dark"]).font_weight("bold").padding(12).width(_col_w[1]),
        Text("PIC").font_size(11).color(WARNA["accent_dark"]).font_weight("bold").padding(12).width(_col_w[2]),
        Text("SELISIH").font_size(11).color(WARNA["accent_dark"]).font_weight("bold").padding(12).width(_col_w[3]),
    ).width(_W).background_color(WARNA["accent_light"]).gap(0)

    # Body rows — zebra stripe
    _rows = [_header_cells]
    for _i, _r in enumerate(data["list_rak"]):
        _bg = "#FAFAF7" if _i % 2 == 0 else WARNA["white"]
        _color = WARNA["red"] if _r["nominal"] < 0 else WARNA["green"]
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(13).color(WARNA["text_primary"]).font_weight("bold").padding(14).width(_col_w[0]),
                Text(_r["nama"]).font_size(12).color(WARNA["text_secondary"]).padding(14).width(_col_w[1]),
                Text(_r["pic"]).font_size(12).color(WARNA["text_secondary"]).padding(14).width(_col_w[2]),
                Text(_fmt_rp(_r["nominal"])).font_size(13).color(_color).font_weight("bold").padding(14).width(_col_w[3]),
            ).width(_W).background_color(_bg).gap(0)
        )

    # Total row
    _total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
    _rows.append(
        Row(
            Text("").padding(14).width(_col_w[0] + _col_w[1] + _col_w[2]),
            Text("TOTAL SELISIH").font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(14).width(180),
            Text(_fmt_rp(data["total_nominal"])).font_size(14).color(_total_color).font_weight("bold").padding(14).width(100),
        ).width(_W).background_color(WARNA["highlight"]).gap(0)
    )

    tabel_rak = Column(*_rows).width(_W).gap(0)

    # =========================================================
    # SECTION 04 — DOUBLE CHART (Bar + Line)
    # =========================================================
    _title_04 = _section_title("04", "TREND SELISIH HARIAN")

    _chart_section = (
        Column(
            Image(_double_path).width(_W - 40),
        )
        .width(_W)
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(10)
        .gap(0)
    )

    # =========================================================
    # FOOTER
    # =========================================================
    footer = (
        Column(
            Text("Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383")
            .font_size(10)
            .color(WARNA["text_muted"]),
        )
        .width(_W)
        .padding(0)
        .gap(0)
    )

    # =========================================================
    # SUSUN LAYOUT — PREMIUM REPORT
    # =========================================================
    layout = Column(
        header,          # Header dengan accent bar
        divider_top,     # Divider
        kpi_row,         # 3 KPI card warm
        _title_01,       # 01 DISTRIBUSI
        _mid_row,        # Donut + Ringkasan
        _title_02,       # 02 INSIGHT
        insight,         # Highlight box
        _title_03,       # 03 DETAIL PER RAK
        tabel_rak,       # Tabel
        _title_04,       # 04 TREND
        _chart_section,  # Double chart
        footer,          # Footer
    ).width(_W).gap(22)

    return canvas.render(layout)


# =========================================================
# RENDER UTAMA
# =========================================================
if st.button("🎨 Render Premium Report", type="primary"):
    try:
        _tmp_dir = tempfile.mkdtemp()

        with st.spinner("Bikin infografis premium..."):
            _image = _build_infografis(_data, _tmp_dir)

        _output_path = os.path.join(_tmp_dir, "infografis_so.png")
        _image.save(_output_path)

        with open(_output_path, "rb") as _f:
            _img_bytes = _f.read()

        st.success(f"✅ Infografis berhasil! Ukuran: {len(_img_bytes):,} bytes")

        st.markdown("---")
        st.markdown("### 📸 Preview")
        st.image(_img_bytes, caption="Infografis SO — Premium Report")

        st.download_button(
            "📥 Download PNG",
            data=_img_bytes,
            file_name=f"laporan_so_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png",
            key="dl_infografis_premium",
            type="primary",
        )

        try:
            import shutil
            shutil.rmtree(_tmp_dir, ignore_errors=True)
        except Exception:
            pass

    except Exception as e:
        import traceback
        st.error(f"❌ Gagal:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")


st.markdown("---")
with st.expander("ℹ️ Info", expanded=False):
    st.markdown("""
    **Style:** Premium Report
    - Accent bar kiri header
    - KPI card warm highlight
    - Section title dengan accent bar
    - Insight box sage pale
    - Tabel zebra stripe
    - **Double chart:** Bar + Line overlay
    """)