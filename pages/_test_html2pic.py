"""
Test pictex — Premium Report FINAL (Bener Secara Teknis)
==========================================================
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
st.title("🎨 Premium Report — Final")


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
# CHART 1: DONUT
# =========================================================
def _build_infografis(data, tmp_dir):
    from pictex import Canvas, Row, Column, Text, Image

    _W = 1000
    _H = 1750  # naikkan dikit

    # === GENERATE CHART PNG ===
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _double_path = os.path.join(tmp_dir, "chart_double.png")
    _chart_donut(data["list_rak"], _donut_path, size_px=460)
    _chart_double(data["trend_data"], _double_path, width_px=940, height_px=280)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=_H)
        .background_color(WARNA["bg"])
        .padding(50)
    )

    # =========================================================
    # HELPER: DIVIDER (wajib pakai size eksplisit)
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
            Text("LAPORAN STOCK OPNAME").font_size(32).color(WARNA["text_primary"]).font_weight("bold"),
            Text("Toko C383 — Karang Satria").font_size(14).color(WARNA["text_secondary"]),
            Text(data["periode"]).font_size(12).color(WARNA["text_muted"]),
        )
        .size(width=972)  # ← pakai size, bukan width
        .gap(6)
    )

    header = Row(header_bar, header_text).gap(20).size(width=_W)

    divider_top = _divider(w=_W, h=1)

    # =========================================================
    # KPI CARDS — pakai flex_grow biar proporsional
    # =========================================================
    def _kpi_card(label, value, sublabel, bg_color):
        return (
            Column(
                Text(label).font_size(11).color(WARNA["text_muted"]).font_weight("bold"),
                Text(value).font_size(52).color(WARNA["text_primary"]).font_weight("bold"),
                Text(sublabel).font_size(12).color(WARNA["text_secondary"]),
            )
            .padding(24)
            .background_color(bg_color)
            .border_radius(12)
            .gap(3)
            .flex_grow(1)  # ← bagi lebar proporsional
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
            Text("▌").font_size(22).color(WARNA["accent_deep"]).font_weight("bold"),
            Text(f"{num}").font_size(14).color(WARNA["terracotta"]).font_weight("bold").width(34),
            Text(title).font_size(17).color(WARNA["text_primary"]).font_weight("bold"),
        ).size(width=_W).gap(10)

    # =========================================================
    # SECTION 01 — DISTRIBUSI
    # =========================================================
    _title_01 = _section_title("01", "DISTRIBUSI PER RAK")

    # KIRI: DONUT — pakai flex_grow biar seimbang
    _donut_col = (
        Column(
            Image(_donut_path).size(width=460, height=460),
        )
        .padding(20)
        .background_color(WARNA["bg"])
        .gap(0)
        .flex_grow(1)  # ← proporsional
    )

    # =========================================================
    # KANAN: RINGKASAN (TANPA INSIGHT)
    # =========================================================
    _status_color = WARNA["red"] if data["status"] == "OVER" else WARNA["green"]

    def _metric_row(label, value, value_color=None):
        if value_color is None:
            value_color = WARNA["text_primary"]
        return Row(
            Text(label).font_size(13).color(WARNA["text_muted"]).width(150),
            Text(value).font_size(14).color(value_color).font_weight("bold"),
        ).gap(12).size(width=428)

    _status_badge = (
        Row(
            Column(Text("").font_size(1))
            .size(width=12, height=12)
            .background_color(_status_color)
            .border_radius(6),
            Text(f" {data['status']}").font_size(14).color(_status_color).font_weight("bold"),
        ).gap(8)
    )

    _ringkasan_col = (
        Column(
            Text("RINGKASAN PERIODE").font_size(15).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=428, h=2, color=WARNA["accent_deep"]),

            _metric_row("Tanggal", data["periode"]),
            _divider(w=428, h=1),
            _metric_row("Total Rak", f"{data['total_rak']} rak"),
            _divider(w=428, h=1),
            _metric_row("Nominal SO", _fmt_rp(data["total_nominal"]), WARNA["red"]),
            _divider(w=428, h=1),
            _metric_row("Sales Periode", _fmt_rp_no_sign(data["sales_periode"])),
            _divider(w=428, h=1),
            _metric_row("BTSB (0,15%)", _fmt_rp_no_sign(data["btsb"])),
            _divider(w=428, h=1),

            Row(
                Text("Status").font_size(13).color(WARNA["text_muted"]).width(150),
                _status_badge,
            ).gap(12).size(width=428),
        )
        .padding(26)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(10)
        .flex_grow(1)  # ← proporsional
    )

    # Row utama — pakai flex_grow biar bagi lebar
    _mid_row = Row(_donut_col, _ringkasan_col).gap(40).size(width=_W).align_items("start")

    # =========================================================
    # SECTION INSIGHT — Full Width (di luar kolom)
    # =========================================================
    _insight_section = (
        Column(
            Text("INSIGHT").font_size(15).color(WARNA["accent_deep"]).font_weight("bold"),
            _divider(w=_W, h=2, color=WARNA["accent_deep"]),
            Column(
                Text(data["insight"]).font_size(14).color(WARNA["text_primary"]).font_weight("bold"),
            ).padding(20).background_color(WARNA["terracotta_light"]).border_radius(10).gap(0),
        )
        .size(width=_W)
        .gap(10)
    )
    
# =========================================================
# SECTION 02 — DETAIL PER RAK
# =========================================================
_title_02 = _section_title("02", "DETAIL PER RAK")

_col_w = [110, 420, 170, 300]

_header_cells = Row(
    Text("RAK").font_size(13).color(WARNA["white"]).font_weight("bold").padding(16).width(_col_w[0]),
    Text("NAMA RAK").font_size(13).color(WARNA["white"]).font_weight("bold").padding(16).width(_col_w[1]),
    Text("PIC").font_size(13).color(WARNA["white"]).font_weight("bold").padding(16).width(_col_w[2]),
    Text("SELISIH").font_size(13).color(WARNA["white"]).font_weight("bold").padding(16).width(_col_w[3]),
).size(width=_W).background_color(WARNA["accent_deep"]).gap(0)

_rows = [_header_cells]
for _i, _r in enumerate(data["list_rak"]):
    _bg = WARNA["cream"] if _i % 2 == 0 else WARNA["white"]
    _color = WARNA["red"] if _r["nominal"] < 0 else WARNA["green"]
    _rows.append(
        Row(
            Text(_r["rak_id"]).font_size(14).color(WARNA["text_primary"]).font_weight("bold").padding(16).width(_col_w[0]),
            Text(_r["nama"]).font_size(14).color(WARNA["text_primary"]).padding(16).width(_col_w[1]),
            Text(_r["pic"]).font_size(14).color(WARNA["text_primary"]).font_weight("bold").padding(16).width(_col_w[2]),
            Text(_fmt_rp(_r["nominal"])).font_size(14).color(_color).font_weight("bold").padding(16).width(_col_w[3]),
        ).size(width=_W).background_color(_bg).gap(0)
    )

tabel_rak = Column(*_rows).size(width=_W).gap(0)

# TOTAL SELISIH
_total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
_total_row = (
    Row(
        Text("TOTAL SELISIH").font_size(14).color(WARNA["text_primary"]).font_weight("bold").padding(18).width(700),
        Text(_fmt_rp(data["total_nominal"])).font_size(16).color(_total_color).font_weight("bold").padding(18).width(300),
    )
    .size(width=_W)
    .background_color(WARNA["terracotta_light"])
)

# =========================================================
# SECTION 03 — TREND
# =========================================================
_title_03 = _section_title("03", "TREND SELISIH HARIAN")

_chart_section = (
    Column(
        Image(_double_path).size(width=_W),
    )
    .size(width=_W)
    .padding(0)
    .gap(0)
)

# =========================================================
# FOOTER
# =========================================================
footer_line = _divider(w=_W, h=1)

footer = (
    Column(
        Text("Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383")
        .font_size(11)
        .color(WARNA["text_muted"]),
    )
    .size(width=_W)
    .padding(12)
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
    _mid_row,
    _insight_section,   # ← Insight full width
    _title_02,
    tabel_rak,
    _total_row,
    _title_03,
    _chart_section,
    footer_line,
    footer,
).size(width=_W).gap(24)

return canvas.render(layout)