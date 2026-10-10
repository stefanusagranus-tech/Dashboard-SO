"""
Test pictex — Halaman 1 Fix v2
=================================
Strategi: size() eksplisit + no stretch
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
st.title("🎨 Halaman 1 — Fix v2")


# =========================================================
# PALET WARNA
# =========================================================
WARNA = {
    "bg": "#F5F1EA",
    "accent": "#5E7A75",
    "accent_deep": "#3D5A55",
    "accent_light": "#D9E4E0",
    "terracotta": "#B5745E",
    "terracotta_light": "#E8D5C9",
    "cream": "#F5F1EA",
    "highlight": "#EDE8DE",
    "text_primary": "#2D2A26",
    "text_secondary": "#6B6560",
    "text_muted": "#9C9488",
    "divider": "#DDD5C8",
    "white": "#FFFFFF",
    "red": "#B8383A",
    "green": "#4A7C59",
    "bar_pos": "#7B9B95",
    "bar_neg": "#C9907E",
}


# =========================================================
# DATA DUMMY
# =========================================================
_data = {
    "periode": "2026-10-10 s/d 2026-10-10",
    "total_rak": 3,
    "total_item": 21,
    "total_nominal": -34556,
    "sales_periode": 10,
    "btsb": 0,
    "status": "OVER",
    "insight": (
        "Rak S14 menyumbang minus terbesar (-Rp 24.785) oleh PIC REZA. "
        "Total selisih periode melebihi batas BTSB."
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
# CHART: TREND
# =========================================================
def _chart_trend(trend_data, output_path, width_px=520, height_px=300):
    if not trend_data:
        return None

    _labels = [t["tanggal"] for t in trend_data]
    _values = [t["nominal"] for t in trend_data]

    _dpi = 100
    _fig_size = (width_px / _dpi, height_px / _dpi)

    fig, ax = plt.subplots(figsize=_fig_size, dpi=_dpi)
    fig.patch.set_facecolor(WARNA["cream"])
    ax.set_facecolor(WARNA["cream"])

    _x = np.arange(len(_labels))

    _bar_colors = [WARNA["bar_neg"] if v < 0 else WARNA["bar_pos"] for v in _values]
    ax.bar(_x, _values, color=_bar_colors, width=0.55, alpha=0.75, edgecolor="white", linewidth=1.5)

    ax.plot(_x, _values, color=WARNA["accent_deep"], linewidth=2.5,
            marker="o", markersize=7, markerfacecolor="white",
            markeredgecolor=WARNA["accent_deep"], markeredgewidth=2, zorder=5)

    for i, v in enumerate(_values):
        _color = WARNA["red"] if v < 0 else WARNA["green"]
        if v >= 0:
            ax.text(i, v + 3000, f"+Rp {abs(int(v)):,}".replace(",", "."),
                    ha="center", va="bottom", fontsize=8, fontweight="bold", color=_color)
        else:
            ax.text(i, v - 3000, f"-Rp {abs(int(v)):,}".replace(",", "."),
                    ha="center", va="top", fontsize=8, fontweight="bold", color=_color)

    ax.axhline(0, color=WARNA["text_muted"], linewidth=0.8, alpha=0.5)
    ax.set_xticks(_x)
    ax.set_xticklabels(_labels)
    ax.tick_params(axis="x", labelsize=9, colors=WARNA["text_secondary"])
    ax.tick_params(axis="y", labelsize=8, colors=WARNA["text_muted"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(WARNA["divider"])
    ax.grid(axis="y", linestyle=":", alpha=0.3, color=WARNA["divider"])
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", ".")))

    _min_v = min(_values)
    _max_v = max(_values)
    _pad = abs(_max_v - _min_v) * 0.40 if _max_v != _min_v else 8000
    ax.set_ylim(_min_v - _pad, _max_v + _pad)

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["cream"])
    plt.close(fig)
    return output_path


# =========================================================
# CHART: DONUT
# =========================================================
def _chart_donut(list_rak, output_path, size_px=360):
    _sorted = sorted(list_rak, key=lambda x: abs(x["nominal"]), reverse=True)
    _labels = [f"Rak {r['rak_id']}" for r in _sorted if abs(r["nominal"]) > 0]
    _sizes = [abs(r["nominal"]) for r in _sorted if abs(r["nominal"]) > 0]

    if not _sizes:
        return None

    _colors = ["#5E7A75", "#B5745E", "#7B9B95", "#D9C4B5", "#A8B5AE", "#E8D5C9"]
    _dpi = 100
    _fig_size = size_px / _dpi

    fig, ax = plt.subplots(figsize=(_fig_size, _fig_size), dpi=_dpi)
    fig.patch.set_facecolor(WARNA["cream"])
    ax.set_facecolor(WARNA["cream"])

    wedges, texts, autotexts = ax.pie(
        _sizes, labels=None, colors=_colors[:len(_sizes)],
        autopct=lambda p: f"{p:.0f}%", pctdistance=0.78, startangle=90,
        wedgeprops=dict(width=0.40, edgecolor=WARNA["cream"], linewidth=3),
    )

    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(11)
        at.set_fontweight("bold")

    for i, (wedge, label) in enumerate(zip(wedges, _labels)):
        angle = (wedge.theta2 + wedge.theta1) / 2.0
        x = np.cos(np.radians(angle))
        y = np.sin(np.radians(angle))
        ha = "right" if x < 0 else "left"
        ax.annotate(label, xy=(x * 0.85, y * 0.85), xytext=(x * 1.30, y * 1.30),
                    ha=ha, va="center", fontsize=10, fontweight="bold", color=WARNA["text_primary"])

    _total = sum(_sizes)
    ax.text(0, 0.05, _fmt_rp_no_sign(_total), ha="center", va="center",
            fontsize=12, fontweight="bold", color=WARNA["accent_deep"])
    ax.text(0, -0.10, "TOTAL", ha="center", va="center",
            fontsize=8, fontweight="bold", color=WARNA["text_muted"])

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["cream"])
    plt.close(fig)
    return output_path
    

# =========================================================
# KONSTRUKSI INFOGRAFIS
# =========================================================
def _build_infografis(data, tmp_dir):
    from pictex import Canvas, Row, Column, Text, Image

    _W = 1000
    _H = 1750

    # === GENERATE CHART PNG ===
    _trend_path = os.path.join(tmp_dir, "chart_trend.png")
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _chart_trend(data["trend_data"], _trend_path, width_px=520, height_px=300)
    _chart_donut(data["list_rak"], _donut_path, size_px=360)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=_H)
        .background_color(WARNA["bg"])
        .padding(50)
    )

    # =========================================================
    # HELPER: DIVIDER
    # =========================================================
    def _divider(w=1000, h=1, color=None):
        if color is None:
            color = WARNA["divider"]
        return (
            Column(Text("").font_size(1))
            .size(width=w, height=h)
            .background_color(color)
        )

    # =========================================================
    # HEADER
    # =========================================================
    header_bar = _divider(w=8, h=100, color=WARNA["accent_deep"])

    header_text = (
        Column(
            Text("LAPORAN STOCK OPNAME").font_size(30).color(WARNA["text_primary"]).font_weight("bold"),
            Text("Toko C383 — Karang Satria").font_size(13).color(WARNA["text_secondary"]),
            Text(data["periode"]).font_size(11).color(WARNA["text_muted"]),
        )
        .size(width=972)
        .gap(5)
    )

    header = Row(header_bar, header_text).gap(20).size(width=_W)

    divider_top = _divider(w=_W, h=1)

    # =========================================================
    # KPI CARDS
    # =========================================================
    def _kpi_card(label, value, sublabel, bg_color):
        return (
            Column(
                Text(label).font_size(11).color(WARNA["text_muted"]).font_weight("bold"),
                Text(value).font_size(46).color(WARNA["text_primary"]).font_weight("bold"),
                Text(sublabel).font_size(11).color(WARNA["text_secondary"]),
            )
            .padding(22)
            .background_color(bg_color)
            .border_radius(12)
            .gap(3)
            .flex_grow(1)
        )

    kpi_row = Row(
        _kpi_card("TOTAL RAK", str(data["total_rak"]), "rak ter-SO", WARNA["accent_light"]),
        _kpi_card("TOTAL ITEM", str(data["total_item"]), "item tercatat", WARNA["terracotta_light"]),
        _kpi_card("TOTAL NOMINAL", _fmt_rp(data["total_nominal"]), "selisih periode", WARNA["highlight"]),
    ).gap(20).size(width=_W)

    # =========================================================
    # SECTION TITLE
    # =========================================================
    def _section_title(num, title):
        return Row(
            Text("▌").font_size(20).color(WARNA["accent_deep"]).font_weight("bold"),
            Text(f"{num}").font_size(13).color(WARNA["terracotta"]).font_weight("bold").width(32),
            Text(title).font_size(15).color(WARNA["text_primary"]).font_weight("bold"),
        ).size(width=_W).gap(8)

    # =========================================================
    # SECTION 01 — KIRI: TREND | KANAN: RINGKASAN + INSIGHT
    # =========================================================
    _title_01 = _section_title("01", "TREND & RINGKASAN")

    # --- KIRI: TREND CHART — height fixed 480 ---
    _trend_col = (
        Column(
            Text("TREND SELISIH HARIAN").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=520, h=2, color=WARNA["accent_deep"]),
            Image(_trend_path).size(width=520),
        )
        .size(width=520, height=480)   # ✅ HEIGHT FIXED
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(8)
    )

    # --- KANAN: RINGKASAN + INSIGHT — height fixed 480 ---
    _status_color = WARNA["red"] if data["status"] == "OVER" else WARNA["green"]

    def _metric_row(label, value, value_color=None):
        if value_color is None:
            value_color = WARNA["text_primary"]
        return Row(
            Text(label).font_size(11).color(WARNA["text_muted"]).width(120),
            Text(value).font_size(12).color(value_color).font_weight("bold"),
        ).gap(8).size(width=400)

    _status_badge = (
        Row(
            Column(Text("").font_size(1))
            .size(width=10, height=10)
            .background_color(_status_color)
            .border_radius(5),
            Text(f" {data['status']}").font_size(12).color(_status_color).font_weight("bold"),
        ).gap(6)
    )

    _ringkasan_col = (
        Column(
            Text("RINGKASAN PERIODE").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=400, h=2, color=WARNA["accent_deep"]),

            _metric_row("Tanggal", data["periode"]),
            _divider(w=400, h=1),
            _metric_row("Total Rak", f"{data['total_rak']} rak"),
            _divider(w=400, h=1),
            _metric_row("Nominal SO", _fmt_rp(data["total_nominal"]), WARNA["red"]),
            _divider(w=400, h=1),
            _metric_row("Sales Periode", _fmt_rp_no_sign(data["sales_periode"])),
            _divider(w=400, h=1),
            _metric_row("BTSB (0,15%)", _fmt_rp_no_sign(data["btsb"])),
            _divider(w=400, h=1),
            Row(
                Text("Status").font_size(11).color(WARNA["text_muted"]).width(120),
                _status_badge,
            ).gap(8).size(width=400),

            Column(Text("").font_size(1)).size(width=1, height=8),

            Text("INSIGHT").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=400, h=2, color=WARNA["accent_deep"]),
            Column(
                Text(data["insight"]).font_size(11).color(WARNA["text_primary"]).font_weight("bold"),
            ).padding(14).background_color(WARNA["terracotta_light"]).border_radius(8).gap(0),
        )
        .size(width=450, height=480)   # ✅ HEIGHT FIXED, SAMA
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(6)
    )

    # ✅ Row tanpa stretch — biar size(height) ke-apply
    _row_01 = Row(_trend_col, _ringkasan_col).gap(30).size(width=_W)

    # =========================================================
    # SECTION 02 — KIRI: TABEL | KANAN: DONUT
    # =========================================================
    _title_02 = _section_title("02", "DETAIL PER RAK & KONTRIBUSI")

    # --- KIRI: TABEL ---
    _col_w = [80, 280, 120, 150]

    _header_cells = Row(
        Text("RAK").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[0]),
        Text("NAMA RAK").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[1]),
        Text("PIC").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[2]),
        Text("SELISIH").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[3]),
    ).size(width=630).background_color(WARNA["accent_deep"]).gap(0)

    _rows = [_header_cells]
    for _i, _r in enumerate(data["list_rak"]):
        _bg = WARNA["cream"] if _i % 2 == 0 else WARNA["white"]
        _color = WARNA["red"] if _r["nominal"] < 0 else WARNA["green"]
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(12).width(_col_w[0]),
                Text(_r["nama"][:22]).font_size(11).color(WARNA["text_primary"]).padding(12).width(_col_w[1]),
                Text(_r["pic"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(12).width(_col_w[2]),
                Text(_fmt_rp(_r["nominal"])).font_size(12).color(_color).font_weight("bold").padding(12).width(_col_w[3]),
            ).size(width=630).background_color(_bg).gap(0)
        )

    tabel_rak = Column(*_rows).size(width=630).gap(0)

    _total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
    _total_row = (
        Row(
            Text("TOTAL").font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(14).width(480),
            Text(_fmt_rp(data["total_nominal"])).font_size(13).color(_total_color).font_weight("bold").padding(14).width(150),
        )
        .size(width=630)
        .background_color(WARNA["terracotta_light"])
    )

    _tabel_col = (
        Column(
            tabel_rak,
            _total_row,
        )
        .gap(0)
        .flex_grow(2)
    )

    # --- KANAN: DONUT ---
    _donut_col = (
        Column(
            Text("KONTRIBUSI PER RAK").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=310, h=2, color=WARNA["accent_deep"]),
            Image(_donut_path).size(width=310),
        )
        .padding(18)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(8)
        .flex_grow(1)
    )

    _row_02 = Row(_tabel_col, _donut_col).gap(30).size(width=_W)

    # =========================================================
    # FOOTER
    # =========================================================
    footer_line = _divider(w=_W, h=1)

    footer = (
        Column(
            Text("Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383")
            .font_size(10)
            .color(WARNA["text_muted"]),
        )
        .size(width=_W)
        .padding(10)
        .gap(0)
    )

    # =========================================================
    # SUSUN LAYOUT
    # =========================================================
    layout = Column(
        header,
        divider_top,
        kpi_row,
        _title_01,
        _row_01,
        _title_02,
        _row_02,
        footer_line,
        footer,
    ).size(width=_W).gap(22)

    return canvas.render(layout)


# =========================================================
# RENDER UTAMA
# =========================================================
if st.button("🎨 Render Halaman 1", type="primary"):
    try:
        _tmp_dir = tempfile.mkdtemp()

        with st.spinner("Bikin infografis..."):
            _image = _build_infografis(_data, _tmp_dir)

        _output_path = os.path.join(_tmp_dir, "infografis_so.png")
        _image.save(_output_path)

        with open(_output_path, "rb") as _f:
            _img_bytes = _f.read()

        st.success(f"✅ Berhasil! Ukuran: {len(_img_bytes):,} bytes")

        st.markdown("---")
        st.markdown("### 📸 Preview")
        st.image(_img_bytes, caption="Halaman 1 Fix v2")

        st.download_button(
            "📥 Download PNG",
            data=_img_bytes,
            file_name=f"laporan_so_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png",
            key="dl_fix_v2",
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
    **Halaman 1 — Fix v2**

    **Strategi:**
    - `_trend_col`: `.size(width=520, height=480)` — height fixed
    - `_ringkasan_col`: `.size(width=450, height=480)` — height sama
    - `_row_01`: **tanpa `align_items("stretch")`** — biar size(height) ke-apply
    - Section 02 tetap pakai `flex_grow` — tabel & donut proporsional
    """)