"""
Test pictex — Final (Semua Pelajaran Diterapkan)
==================================================
Section 1: Trend (kiri) + Ringkasan (kanan) — 470×470
Section 2: Tabel (kiri) + Donut (kanan) — auto-grow
Canvas: Dynamic height
"""
import streamlit as st
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


st.set_page_config(page_title="Final", page_icon="🎨", layout="wide")
st.title("🎨 Final — Semua Fix")


# =========================================================
# PALET
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
# DATA
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
def _chart_trend(trend_data, output_path, width_px=430, height_px=388):
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
                    ha="center", va="bottom", fontsize=9, fontweight="bold", color=_color)
        else:
            ax.text(i, v - 3000, f"-Rp {abs(int(v)):,}".replace(",", "."),
                    ha="center", va="top", fontsize=9, fontweight="bold", color=_color)
    ax.axhline(0, color=WARNA["text_muted"], linewidth=0.8, alpha=0.5)
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
    _min_v, _max_v = min(_values), max(_values)
    _pad = abs(_max_v - _min_v) * 0.40 if _max_v != _min_v else 8000
    ax.set_ylim(_min_v - _pad, _max_v + _pad)
    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["cream"])
    plt.close(fig)
    return output_path


# =========================================================
# CHART: DONUT
# =========================================================
def _chart_donut(list_rak, output_path, size_px=280):
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
        at.set_fontsize(10)
        at.set_fontweight("bold")
    for i, (wedge, label) in enumerate(zip(wedges, _labels)):
        angle = (wedge.theta2 + wedge.theta1) / 2.0
        x, y = np.cos(np.radians(angle)), np.sin(np.radians(angle))
        ha = "right" if x < 0 else "left"
        ax.annotate(label, xy=(x * 0.85, y * 0.85), xytext=(x * 1.18, y * 1.18),
                    ha=ha, va="center", fontsize=9, fontweight="bold", color=WARNA["text_primary"])
    _total = sum(_sizes)
    ax.text(0, 0.05, _fmt_rp_no_sign(_total), ha="center", va="center",
            fontsize=11, fontweight="bold", color=WARNA["accent_deep"])
    ax.text(0, -0.10, "TOTAL", ha="center", va="center",
            fontsize=7, fontweight="bold", color=WARNA["text_muted"])
    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["cream"])
    plt.close(fig)
    return output_path
    

# =========================================================
# FILTER RAK
# =========================================================
_THRESHOLD_RAK = 15


def _siapkan_rak_untuk_tabel(list_rak, threshold=15, max_tampil=6):
    if len(list_rak) <= threshold:
        return list_rak, False, 0
    _sorted = sorted(list_rak, key=lambda x: x["nominal"])[:max_tampil]
    return _sorted, True, len(list_rak) - max_tampil


# =========================================================
# KONSTRUKSI
# =========================================================
def _build_infografis(data, tmp_dir):
    from pictex import Canvas, Row, Column, Text, Image

    # =========================================================
    # UKURAN
    # =========================================================
    _CANVAS_W = 1080
    _PADDING = 50
    _W = _CANVAS_W - (_PADDING * 2)   # 980

    # Section 1
    _GAP_S1 = 40
    _CARD_W = int((_W - _GAP_S1) / 2)   # 470
    _CARD_H = _CARD_W                    # 470
    _CHART_W = _CARD_W - 40              # 430
    _CHART_H = _CHART_W - 42             # 388

    # Section 2
    _GAP_S2 = 40
    _TABEL_W = 540
    _DONUT_W = _W - _TABEL_W - _GAP_S2   # 400
    _DONUT_PNG = 280

    _ROW_H = 48
    _HEADER_H = 42
    _TOTAL_H = 48
    _PAD_TABEL = 40

    _rak_tabel, _terpotong, _sisa = _siapkan_rak_untuk_tabel(data["list_rak"], _THRESHOLD_RAK)
    _n_rak = len(_rak_tabel)

    _TABEL_H = (_n_rak * _ROW_H) + _HEADER_H + _TOTAL_H + _PAD_TABEL
    _DONUT_CARD_MIN = _DONUT_PNG + 100
    _SECTION_02_H = max(_TABEL_H, _DONUT_CARD_MIN)

    # Canvas
    _BASE = 80 + 1 + 110 + 30 + 50   # header + divider + kpi + title + footer
    _GAP_TOTAL = 22 * 6
    _H = _BASE + _CARD_H + 30 + _SECTION_02_H + _GAP_TOTAL + 100

    print(f"[INFO] Canvas: {_CANVAS_W} × {_H}px")
    print(f"[INFO] Card S1: {_CARD_W} × {_CARD_H}px")
    print(f"[INFO] Chart: {_CHART_W} × {_CHART_H}px")
    print(f"[INFO] Tabel: {_TABEL_W} × {_TABEL_H}px ({_n_rak} rak)")
    print(f"[INFO] Donut card: {_DONUT_W} × {_SECTION_02_H}px")

    # === CHART PNG ===
    _trend_path = os.path.join(tmp_dir, "chart_trend.png")
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _chart_trend(data["trend_data"], _trend_path, width_px=_CHART_W, height_px=_CHART_H)
    _chart_donut(data["list_rak"], _donut_path, size_px=_DONUT_PNG)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=_CANVAS_W, height=_H)
        .background_color(WARNA["bg"])
        .padding(_PADDING)
    )

    def _divider(w=980, h=1, color=None):
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
        .size(width=_W - 28)
        .gap(5)
    )
    header = Row(header_bar, header_text).gap(20).size(width=_W)
    divider_top = _divider(w=_W, h=1)

    # =========================================================
    # KPI
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

    def _section_title(num, title):
        return Row(
            Text("▌").font_size(20).color(WARNA["accent_deep"]).font_weight("bold"),
            Text(f"{num}").font_size(13).color(WARNA["terracotta"]).font_weight("bold").width(32),
            Text(title).font_size(15).color(WARNA["text_primary"]).font_weight("bold"),
        ).size(width=_W).gap(8)

    # =========================================================
    # SECTION 01 — TREND (KIRI) + RINGKASAN (KANAN)
    # =========================================================
    _title_01 = _section_title("01", "TREND & RINGKASAN")

    _trend_col = (
        Column(
            Text("TREND SELISIH HARIAN").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=_CHART_W, h=2, color=WARNA["accent_deep"]),
            Image(_trend_path).size(width=_CHART_W),
        )
        .size(width=_CARD_W, height=_CARD_H)
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(10)
    )

    _status_color = WARNA["red"] if data["status"] == "OVER" else WARNA["green"]

    def _metric_row(label, value, value_color=None):
        if value_color is None:
            value_color = WARNA["text_primary"]
        return Row(
            Text(label).font_size(11).color(WARNA["text_muted"]).width(120),
            Text(value).font_size(12).color(value_color).font_weight("bold"),
        ).gap(8).size(width=_CARD_W - 40)

    _status_badge = Row(
        Column(Text("").font_size(1))
        .size(width=10, height=10)
        .background_color(_status_color)
        .border_radius(5),
        Text(f" {data['status']}").font_size(12).color(_status_color).font_weight("bold"),
    ).gap(6)

    _ringkasan_col = (
        Column(
            Text("RINGKASAN PERIODE").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=_CARD_W - 40, h=2, color=WARNA["accent_deep"]),
            _metric_row("Tanggal", data["periode"]),
            _divider(w=_CARD_W - 40, h=1),
            _metric_row("Total Rak", f"{data['total_rak']} rak"),
            _divider(w=_CARD_W - 40, h=1),
            _metric_row("Nominal SO", _fmt_rp(data["total_nominal"]), WARNA["red"]),
            _divider(w=_CARD_W - 40, h=1),
            _metric_row("Sales Periode", _fmt_rp_no_sign(data["sales_periode"])),
            _divider(w=_CARD_W - 40, h=1),
            _metric_row("BTSB (0,15%)", _fmt_rp_no_sign(data["btsb"])),
            _divider(w=_CARD_W - 40, h=1),
            Row(
                Text("Status").font_size(11).color(WARNA["text_muted"]).width(120),
                _status_badge,
            ).gap(8).size(width=_CARD_W - 40),
            Column(Text("").font_size(1)).size(width=1, height=8),
            Text("INSIGHT").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=_CARD_W - 40, h=2, color=WARNA["accent_deep"]),
            Column(
                Text(data["insight"]).font_size(11).color(WARNA["text_primary"]).font_weight("bold"),
            ).padding(14).background_color(WARNA["terracotta_light"]).border_radius(8).gap(0),
        )
        .size(width=_CARD_W, height=_CARD_H)
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(6)
    )

    _row_01 = Row(_trend_col, _ringkasan_col).gap(_GAP_S1).size(width=_W)

    # =========================================================
    # SECTION 02 — TABEL (KIRI) + DONUT (KANAN)
    # =========================================================
    _title_02 = _section_title("02", "DETAIL PER RAK & KONTRIBUSI")

    _col_w = [70, 250, 100, 120]

    _header_cells = Row(
        Text("RAK").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[0]),
        Text("NAMA RAK").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[1]),
        Text("PIC").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[2]),
        Text("SELISIH").font_size(11).color(WARNA["white"]).font_weight("bold").padding(12).width(_col_w[3]),
    ).size(width=_TABEL_W).background_color(WARNA["accent_deep"]).gap(0)

    _rows = [_header_cells]
    for _i, _r in enumerate(_rak_tabel):
        _bg = WARNA["cream"] if _i % 2 == 0 else WARNA["white"]
        _color = WARNA["red"] if _r["nominal"] < 0 else WARNA["green"]
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(12).width(_col_w[0]),
                Text(_r["nama"][:22]).font_size(11).color(WARNA["text_primary"]).padding(12).width(_col_w[1]),
                Text(_r["pic"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(12).width(_col_w[2]),
                Text(_fmt_rp(_r["nominal"])).font_size(12).color(_color).font_weight("bold").padding(12).width(_col_w[3]),
            ).size(width=_TABEL_W).background_color(_bg).gap(0)
        )

    tabel_rak = Column(*_rows).size(width=_TABEL_W).gap(0)

    _total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
    _total_row = Row(
        Text("TOTAL").font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(14).width(420),
        Text(_fmt_rp(data["total_nominal"])).font_size(13).color(_total_color).font_weight("bold").padding(14).width(120),
    ).size(width=_TABEL_W).background_color(WARNA["terracotta_light"])

    _info_row = (
        Text(f"* Menampilkan {len(_rak_tabel)} dari {len(data['list_rak'])} rak")
        .font_size(10).color(WARNA["text_muted"]).padding(6)
        if _terpotong else
        Text("").font_size(1).size(width=1, height=1)
    )

    _tabel_col = Column(tabel_rak, _total_row, _info_row).gap(0)

    _donut_col = (
        Column(
            Text("KONTRIBUSI PER RAK").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=_DONUT_W - 40, h=2, color=WARNA["accent_deep"]),
            Image(_donut_path).size(width=_DONUT_PNG),
        )
        .size(width=_DONUT_W, height=_SECTION_02_H)
        .padding(20)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(10)
    )

    _row_02 = Row(_tabel_col, _donut_col).gap(_GAP_S2).size(width=_W)

    # =========================================================
    # FOOTER
    # =========================================================
    footer_line = _divider(w=_W, h=1)
    footer = (
        Column(
            Text("Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383")
            .font_size(10).color(WARNA["text_muted"]),
        )
        .size(width=_W).padding(10).gap(0)
    )

    # =========================================================
    # LAYOUT
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
# RENDER
# =========================================================
if st.button("🎨 Render Final", type="primary"):
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
        st.image(_img_bytes, caption="Final")
        st.download_button(
            "📥 Download PNG", data=_img_bytes,
            file_name=f"laporan_so_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png", key="dl_final", type="primary",
        )
        try:
            import shutil
            shutil.rmtree(_tmp_dir, ignore_errors=True)
        except Exception:
            pass
    except Exception as e:
        import traceback
        st.error(f"❌ Gagal:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")