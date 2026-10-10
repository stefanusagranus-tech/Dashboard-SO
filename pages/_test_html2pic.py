"""
Test pictex Canvas — Infografis NEXT LEVEL (v2 RAPIH)
======================================================
"""
import streamlit as st
import io
import os
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


st.set_page_config(page_title="Test pictex", page_icon="🎨", layout="wide")
st.title("🎨 Test pictex — Infografis Next Level")


# =========================================================
# PALET WARNA
# =========================================================
WARNA = {
    "sage": "#97B3AE",
    "sage_light": "#D2E0D3",
    "peach": "#F0DDD6",
    "salmon": "#F2C3B9",
    "beige": "#D6CBBF",
    "offwhite": "#F0EEEA",
    "dark": "#2E2E2E",
    "grey": "#666666",
    "white": "#FFFFFF",
    "red": "#C83232",
    "green": "#329632",
}


# =========================================================
# DATA DUMMY
# =========================================================
_data = {
    "periode": "2026-10-10 s/d 2026-10-10",
    "tanggal": "10/10/2026",
    "total_rak": 3,
    "total_item": 21,
    "total_nominal": -34556,
    "sales_periode": 10,
    "btsb": 0,
    "status": "OVER",
    "insight": (
        "Total SO: 3 rak dengan nominal -Rp 34.556. Sales periode: Rp 10. "
        "BTSB (0,15%): Rp 0. Rak penyumbang minus terbesar: S14 (-Rp 24.785) "
        "oleh PIC REZA. Status: OVER."
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
# CHART 1: DONUT
# =========================================================
def _chart_donut(list_rak, output_path, size_px=400):
    _sorted = sorted(list_rak, key=lambda x: abs(x["nominal"]), reverse=True)
    _labels = [f"Rak {r['rak_id']}" for r in _sorted if abs(r["nominal"]) > 0]
    _sizes = [abs(r["nominal"]) for r in _sorted if abs(r["nominal"]) > 0]

    if not _sizes:
        return None

    _colors = ["#97B3AE", "#F2C3B9", "#D2E0D3", "#F0DDD6", "#D6CBBF", "#B5C9C3"]
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
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
        textprops=dict(color=WARNA["dark"], fontsize=10, fontweight="bold"),
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(11)
        at.set_fontweight("bold")

    ax.set_title(
        "KONTRIBUSI PER RAK",
        fontsize=12, fontweight="bold", color=WARNA["dark"], pad=15,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["white"])
    plt.close(fig)
    return output_path


# =========================================================
# CHART 2: TREND LINE
# =========================================================
def _chart_trend(trend_data, output_path, width_px=900, height_px=220):
    if not trend_data:
        return None

    _labels = [t["tanggal"] for t in trend_data]
    _values = [t["nominal"] for t in trend_data]

    _dpi = 100
    _fig_size = (width_px / _dpi, height_px / _dpi)

    fig, ax = plt.subplots(figsize=_fig_size, dpi=_dpi)
    fig.patch.set_facecolor(WARNA["white"])
    ax.set_facecolor(WARNA["white"])

    ax.plot(
        _labels, _values,
        color="#97B3AE", linewidth=2.5,
        marker="o", markersize=8,
        markerfacecolor="#F2C3B9",
        markeredgecolor="#97B3AE", markeredgewidth=2,
    )
    ax.axhline(0, color=WARNA["dark"], linewidth=0.8, linestyle="--", alpha=0.5)
    ax.fill_between(range(len(_labels)), _values, 0, alpha=0.15, color="#97B3AE")

    ax.set_title(
        "TREND SELISIH (5 HARI TERAKHIR)",
        fontsize=12, fontweight="bold", color=WARNA["dark"], pad=10,
    )
    ax.tick_params(axis="x", labelsize=10, colors=WARNA["dark"])
    ax.tick_params(axis="y", labelsize=9, colors=WARNA["dark"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#D6CBBF")
    ax.spines["bottom"].set_color("#D6CBBF")
    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#D6CBBF")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", ".")))

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["white"])
    plt.close(fig)
    return output_path
    

# =========================================================
# KONSTRUKSI INFOGRAFIS
# =========================================================
def _build_infografis(data, tmp_dir):
    from pictex import Canvas, Row, Column, Text, Image

    _W = 1000
    _H = 1500

    # === GENERATE CHART PNG ===
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _trend_path = os.path.join(tmp_dir, "chart_trend.png")
    _chart_donut(data["list_rak"], _donut_path, size_px=380)
    _chart_trend(data["trend_data"], _trend_path, width_px=960, height_px=220)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=_H)
        .background_color(WARNA["offwhite"])
        .padding(40)
    )

    # =========================================================
    # HEADER BAND
    # =========================================================
    header = (
        Column(
            Text("LAPORAN STOCK OPNAME").font_size(30).color(WARNA["white"]).font_weight("bold"),
            Text("Toko C383 — Karang Satria").font_size(15).color(WARNA["offwhite"]),
            Text(f"Periode: {data['periode']}").font_size(13).color(WARNA["sage_light"]),
        )
        .width(_W)
        .padding(26)
        .background_color(WARNA["sage"])
        .border_radius(16)
        .gap(5)
    )

    # =========================================================
    # KPI CARDS — 3 kolom, gak pakai emoji
    # =========================================================
    kpi_row = Row(
        Column(
            Text("TOTAL RAK").font_size(11).color(WARNA["grey"]).font_weight("bold"),
            Text(f"{data['total_rak']}").font_size(38).color(WARNA["dark"]).font_weight("bold"),
            Text("rak").font_size(13).color(WARNA["grey"]),
        ).width(320).padding(20).background_color(WARNA["sage_light"]).border_radius(14).gap(2),

        Column(
            Text("TOTAL ITEM").font_size(11).color(WARNA["grey"]).font_weight("bold"),
            Text(f"{data['total_item']}").font_size(38).color(WARNA["dark"]).font_weight("bold"),
            Text("item").font_size(13).color(WARNA["grey"]),
        ).width(320).padding(20).background_color(WARNA["peach"]).border_radius(14).gap(2),

        Column(
            Text("TOTAL NOMINAL").font_size(11).color(WARNA["grey"]).font_weight("bold"),
            Text(_fmt_rp(data['total_nominal'])).font_size(26).color(WARNA["red"]).font_weight("bold"),
            Text("periode ini").font_size(13).color(WARNA["grey"]),
        ).width(320).padding(20).background_color(WARNA["salmon"]).border_radius(14).gap(2),
    ).gap(20)

    # =========================================================
    # DONUT + RINGKASAN (2 kolom)
    # =========================================================
    _donut_col = (
        Column(
            Image(_donut_path).width(380),
        )
        .width(460)
        .padding(18)
        .background_color(WARNA["white"])
        .border_radius(14)
    )

    _ringkasan_col = (
        Column(
            Text("RINGKASAN PERIODE").font_size(15).color(WARNA["dark"]).font_weight("bold"),
            Row(
                Text("Tanggal").font_size(12).color(WARNA["grey"]).width(160),
                Text(data["periode"]).font_size(12).color(WARNA["dark"]).font_weight("bold"),
            ),
            Row(
                Text("Total Rak di-SO").font_size(12).color(WARNA["grey"]).width(160),
                Text(f"{data['total_rak']} rak").font_size(12).color(WARNA["dark"]).font_weight("bold"),
            ),
            Row(
                Text("Nominal SO").font_size(12).color(WARNA["grey"]).width(160),
                Text(_fmt_rp(data["total_nominal"])).font_size(12).color(WARNA["dark"]).font_weight("bold"),
            ),
            Row(
                Text("Sales Periode").font_size(12).color(WARNA["grey"]).width(160),
                Text(_fmt_rp_no_sign(data["sales_periode"])).font_size(12).color(WARNA["dark"]).font_weight("bold"),
            ),
            Row(
                Text("BTSB (0,15%)").font_size(12).color(WARNA["grey"]).width(160),
                Text(_fmt_rp_no_sign(data["btsb"])).font_size(12).color(WARNA["dark"]).font_weight("bold"),
            ),
            Row(
                Text("Status").font_size(12).color(WARNA["grey"]).width(160),
                Text(data["status"]).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ),
        )
        .width(520)
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(14)
        .gap(8)
    )

    _mid_row = Row(_donut_col, _ringkasan_col).gap(20)

    # =========================================================
    # INSIGHT
    # =========================================================
    insight = (
        Column(
            Text("INSIGHT").font_size(15).color(WARNA["dark"]).font_weight("bold"),
            Text(data["insight"]).font_size(12).color(WARNA["dark"]),
        )
        .width(_W)
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(14)
        .gap(6)
    )
    
    # =========================================================
    # TABEL RAK
    # =========================================================
    _col_w = [100, 380, 180, 260]  # total 920

    _header_cells = Row(
        Text("RAK").font_size(12).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[0]),
        Text("NAMA RAK").font_size(12).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[1]),
        Text("PIC").font_size(12).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[2]),
        Text("SELISIH").font_size(12).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[3]),
    ).background_color(WARNA["sage"])

    _rows = [_header_cells]
    for _i, _r in enumerate(data["list_rak"]):
        _bg = WARNA["offwhite"] if _i % 2 == 0 else WARNA["white"]
        _color = WARNA["red"] if _r["nominal"] < 0 else WARNA["green"]
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(12).color(WARNA["dark"]).font_weight("bold").padding(12).width(_col_w[0]),
                Text(_r["nama"]).font_size(11).color(WARNA["dark"]).padding(12).width(_col_w[1]),
                Text(_r["pic"]).font_size(12).color(WARNA["dark"]).padding(12).width(_col_w[2]),
                Text(_fmt_rp(_r["nominal"])).font_size(12).color(_color).font_weight("bold").padding(12).width(_col_w[3]),
            ).background_color(_bg)
        )

    # Footer: TOTAL SELISIH
    _total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
    _rows.append(
        Row(
            Text("TOTAL SELISIH").font_size(13).color(WARNA["dark"]).font_weight("bold").padding(12).width(_col_w[0] + _col_w[1] + _col_w[2]),
            Text(_fmt_rp(data["total_nominal"])).font_size(14).color(_total_color).font_weight("bold").padding(12).width(_col_w[3]),
        ).background_color(WARNA["beige"])
    )

    tabel_rak = Column(*_rows).background_color(WARNA["white"]).border_radius(14)

    # =========================================================
    # TREND CHART
    # =========================================================
    _trend_section = (
        Column(
            Image(_trend_path).width(_W - 60),
        )
        .width(_W)
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(14)
        .gap(0)
    )

    # =========================================================
    # FOOTER WATERMARK
    # =========================================================
    footer = (
        Column(
            Text("Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383")
            .font_size(10)
            .color(WARNA["grey"]),
        )
        .width(_W)
        .padding(14)
        .gap(0)
    )

    # =========================================================
    # SUSUN LAYOUT
    # =========================================================
    layout = Column(
        header,
        kpi_row,
        _mid_row,
        insight,
        tabel_rak,
        _trend_section,
        footer,
    ).width(_W).gap(16)

    return canvas.render(layout)


# =========================================================
# RENDER UTAMA
# =========================================================
if st.button("🎨 Render Infografis", type="primary"):
    try:
        _tmp_dir = tempfile.mkdtemp()

        with st.spinner("Bikin infografis..."):
            _image = _build_infografis(_data, _tmp_dir)

        _output_path = os.path.join(_tmp_dir, "infografis_so.png")
        _image.save(_output_path)

        with open(_output_path, "rb") as _f:
            _img_bytes = _f.read()

        st.success(f"✅ Infografis berhasil! Ukuran: {len(_img_bytes):,} bytes")

        st.markdown("---")
        st.markdown("### 📸 Preview")
        st.image(_img_bytes, caption="Infografis SO — Next Level")

        st.download_button(
            "📥 Download PNG",
            data=_img_bytes,
            file_name=f"infografis_so_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png",
            key="dl_infografis_test",
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
    **Layout infografis:**
    1. Header band sage
    2. 3 KPI cards
    3. Donut chart + Ringkasan periode (2 kolom)
    4. Insight
    5. Tabel rak + Total Selisih
    6. Trend chart 5 hari
    7. Watermark footer

    **Ukuran:** 1080 × 1500 px
    """)