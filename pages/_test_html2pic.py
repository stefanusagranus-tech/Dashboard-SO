"""
Test pictex — Premium Report (Final Rapih)
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
# CHART 1: DONUT — RAPIH
# =========================================================
def _chart_donut(list_rak, output_path, size_px=420):
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

    # Donut — persen di dalam wedge
    wedges, texts, autotexts = ax.pie(
        _sizes,
        labels=None,
        colors=_colors[:len(_sizes)],
        autopct=lambda p: f"{p:.0f}%",
        pctdistance=0.80,      # ← persen di dalam donut
        startangle=90,
        wedgeprops=dict(width=0.40, edgecolor=WARNA["cream"], linewidth=3),
        textprops=dict(color="white", fontsize=11, fontweight="bold"),
    )

    # Persen — putih bold
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(12)
        at.set_fontweight("bold")

    # Nilai total di tengah
    _total = sum(_sizes)
    ax.text(
        0, 0.05, _fmt_rp_no_sign(_total),
        ha="center", va="center",
        fontsize=14, fontweight="bold",
        color=WARNA["accent_deep"],
    )
    ax.text(
        0, -0.10, "TOTAL",
        ha="center", va="center",
        fontsize=9, fontweight="bold",
        color=WARNA["text_muted"],
    )

    # Legend di bawah
    ax.legend(
        wedges, _labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=len(_labels),
        frameon=False,
        fontsize=10,
        labelcolor=WARNA["text_primary"],
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["cream"])
    plt.close(fig)
    return output_path


# =========================================================
# CHART 2: DOUBLE CHART — RAPIH
# =========================================================
def _chart_double(trend_data, output_path, width_px=960, height_px=280):
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

    # BAR
    _bar_colors = [WARNA["bar_neg"] if v < 0 else WARNA["bar_pos"] for v in _values]
    ax.bar(
        _x, _values,
        color=_bar_colors,
        width=0.55,
        alpha=0.75,
        edgecolor="white",
        linewidth=1.5,
    )

    # LINE
    ax.plot(
        _x, _values,
        color=WARNA["accent_deep"],
        linewidth=2.5,
        marker="o",
        markersize=8,
        markerfacecolor="white",
        markeredgecolor=WARNA["accent_deep"],
        markeredgewidth=2.5,
        zorder=5,
    )

    # Angka — di atas bar, tapi kalau minus ditaruh di bawah bar (di atas axis)
    for i, v in enumerate(_values):
        _color = WARNA["red"] if v < 0 else WARNA["green"]
        if v >= 0:
            ax.text(
                i, v + 1500,
                f"+Rp {abs(int(v)):,}".replace(",", "."),
                ha="center", va="bottom",
                fontsize=8.5, fontweight="bold",
                color=_color,
            )
        else:
            ax.text(
                i, v - 1500,
                f"-Rp {abs(int(v)):,}".replace(",", "."),
                ha="center", va="top",
                fontsize=8.5, fontweight="bold",
                color=_color,
            )

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

    # Padding
    _min_v = min(_values)
    _max_v = max(_values)
    _pad = abs(_max_v - _min_v) * 0.15 if _max_v != _min_v else 5000
    ax.set_ylim(_min_v - _pad, _max_v + _pad)

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
    _H = 1420

    # === GENERATE CHART PNG ===
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _double_path = os.path.join(tmp_dir, "chart_double.png")
    _chart_donut(data["list_rak"], _donut_path, size_px=420)
    _chart_double(data["trend_data"], _double_path, width_px=960, height_px=280)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=_H)
        .background_color(WARNA["bg"])
        .padding(50)
    )

    # =========================================================
    # HEADER
    # =========================================================
    header_bar = (
        Column(Text("").font_size(1))
        .width(6)
        .background_color(WARNA["accent_deep"])
    )

    header_text = (
        Column(
            Text("LAPORAN STOCK OPNAME").font_size(30).color(WARNA["text_primary"]).font_weight("bold"),
            Text("Toko C383 — Karang Satria").font_size(13).color(WARNA["text_secondary"]),
            Text(data["periode"]).font_size(11).color(WARNA["text_muted"]),
        )
        .width(974)
        .gap(4)
    )

    header = Row(header_bar, header_text).gap(20).width(_W)

    divider_top = (
        Column(Text("").font_size(1))
        .width(_W)
        .background_color(WARNA["divider"])
    )

    # =========================================================
    # KPI CARDS
    # =========================================================
    kpi_row = Row(
        Column(
            Text("TOTAL RAK").font_size(10).color(WARNA["text_muted"]).font_weight("bold"),
            Text(f"{data['total_rak']}").font_size(50).color(WARNA["text_primary"]).font_weight("bold"),
            Text("rak ter-SO").font_size(11).color(WARNA["text_secondary"]),
        ).width(320).padding(22).background_color(WARNA["accent_light"]).border_radius(12).gap(2),

        Column(
            Text("TOTAL ITEM").font_size(10).color(WARNA["text_muted"]).font_weight("bold"),
            Text(f"{data['total_item']}").font_size(50).color(WARNA["text_primary"]).font_weight("bold"),
            Text("item tercatat").font_size(11).color(WARNA["text_secondary"]),
        ).width(320).padding(22).background_color(WARNA["terracotta_light"]).border_radius(12).gap(2),

        Column(
            Text("TOTAL NOMINAL").font_size(10).color(WARNA["text_muted"]).font_weight("bold"),
            Text(_fmt_rp(data['total_nominal'])).font_size(30).color(WARNA["red"]).font_weight("bold"),
            Text("selisih periode").font_size(11).color(WARNA["text_secondary"]),
        ).width(320).padding(22).background_color(WARNA["highlight"]).border_radius(12).gap(2),
    ).gap(20).width(_W)

    # =========================================================
    # SECTION TITLE HELPER
    # =========================================================
    def _section_title(num, title):
        return Row(
            Text("▌").font_size(18).color(WARNA["accent_deep"]).font_weight("bold"),
            Text(f"{num}").font_size(12).color(WARNA["terracotta"]).font_weight("bold").width(30),
            Text(title).font_size(14).color(WARNA["text_primary"]).font_weight("bold"),
        ).width(_W).gap(8)

    # =========================================================
    # SECTION 01 — DISTRIBUSI (Donut + Ringkasan/Insight)
    # =========================================================
    _title_01 = _section_title("01", "DISTRIBUSI PER RAK")

    # KIRI: DONUT (480)
    _donut_col = (
        Column(
            Image(_donut_path).width(460),
        )
        .width(480)
        .padding(10)
        .background_color(WARNA["bg"])
        .gap(0)
    )

    # KANAN: RINGKASAN + INSIGHT (480)
    _ringkasan_col = (
        Column(
            # RINGKASAN
            Text("RINGKASAN PERIODE").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            Row(
                Text("Tanggal").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(data["periode"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(12),
            Row(
                Text("Total Rak").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(f"{data['total_rak']} rak").font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(12),
            Row(
                Text("Nominal SO").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(_fmt_rp(data["total_nominal"])).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ).gap(12),
            Row(
                Text("Sales Periode").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(_fmt_rp_no_sign(data["sales_periode"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(12),
            Row(
                Text("BTSB (0,15%)").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(_fmt_rp_no_sign(data["btsb"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(12),
            Row(
                Text("Status").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(data["status"]).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ).gap(12),

            # Spacer
            Column(Text("").font_size(1)).width(1).padding(4),

            # INSIGHT — tegas
            Text("INSIGHT").font_size(13).color(WARNA["accent_deep"]).font_weight("bold"),
            Column(
                Text(data["insight"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).padding(16).background_color(WARNA["terracotta_light"]).border_radius(8).gap(0),
        )
        .width(480)
        .padding(24)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(12)
    )

    _mid_row = Row(_donut_col, _ringkasan_col).gap(40).width(_W)
    
    # =========================================================
    # SECTION 02 — DETAIL PER RAK
    # =========================================================
    _title_02 = _section_title("02", "DETAIL PER RAK")

    _col_w = [110, 430, 160, 300]  # total 1000

    # Header tabel
    _header_cells = Row(
        Text("RAK").font_size(11).color(WARNA["white"]).font_weight("bold").padding(14).width(_col_w[0]),
        Text("NAMA RAK").font_size(11).color(WARNA["white"]).font_weight("bold").padding(14).width(_col_w[1]),
        Text("PIC").font_size(11).color(WARNA["white"]).font_weight("bold").padding(14).width(_col_w[2]),
        Text("SELISIH").font_size(11).color(WARNA["white"]).font_weight("bold").padding(14).width(_col_w[3]),
    ).width(_W).background_color(WARNA["accent_deep"]).gap(0)

    # Body rows
    _rows = [_header_cells]
    for _i, _r in enumerate(data["list_rak"]):
        _bg = WARNA["cream"] if _i % 2 == 0 else WARNA["white"]
        _color = WARNA["red"] if _r["nominal"] < 0 else WARNA["green"]
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(13).color(WARNA["text_primary"]).font_weight("bold").padding(14).width(_col_w[0]),
                Text(_r["nama"]).font_size(12).color(WARNA["text_secondary"]).padding(14).width(_col_w[1]),
                Text(_r["pic"]).font_size(12).color(WARNA["text_secondary"]).padding(14).width(_col_w[2]),
                Text(_fmt_rp(_r["nominal"])).font_size(13).color(_color).font_weight("bold").padding(14).width(_col_w[3]),
            ).width(_W).background_color(_bg).gap(0)
        )

    tabel_rak = Column(*_rows).width(_W).gap(0)

    # =========================================================
    # TOTAL SELISIH — Kotak sendiri, simetris
    # =========================================================
    _total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
    _total_row = (
        Row(
            Text("TOTAL SELISIH").font_size(13).color(WARNA["text_primary"]).font_weight("bold").padding(14).width(700),
            Text(_fmt_rp(data["total_nominal"])).font_size(15).color(_total_color).font_weight("bold").padding(14).width(300),
        )
        .width(_W)
        .background_color(WARNA["terracotta_light"])
    )

    # =========================================================
    # SECTION 03 — TREND
    # =========================================================
    _title_03 = _section_title("03", "TREND SELISIH HARIAN")

    _chart_section = (
        Column(
            Image(_double_path).width(_W),
        )
        .width(_W)
        .padding(0)
        .gap(0)
    )

    # =========================================================
    # FOOTER — dengan garis
    # =========================================================
    footer_divider = (
        Column(Text("").font_size(1))
        .width(_W)
        .background_color(WARNA["divider"])
    )

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
    # SUSUN LAYOUT
    # =========================================================
    layout = Column(
        header,
        divider_top,
        kpi_row,
        _title_01,
        _mid_row,
        _title_02,
        tabel_rak,
        _total_row,
        _title_03,
        _chart_section,
        footer_divider,
        footer,
    ).width(_W).gap(20)

    return canvas.render(layout)


# =========================================================
# RENDER UTAMA
# =========================================================
if st.button("🎨 Render Premium Report", type="primary"):
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
        st.image(_img_bytes, caption="Premium Report — Final")

        st.download_button(
            "📥 Download PNG",
            data=_img_bytes,
            file_name=f"laporan_so_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png",
            key="dl_premium_final",
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
    **Premium Report — Final Polish**
    - Donut chart: persen di dalam wedge, legend di bawah, nilai total di tengah
    - Ringkasan: 12pt, rapi
    - Insight: 13pt bold, box terracotta light (tegas)
    - Tabel: header sage deep, zebra stripe
    - Total Selisih: baris sendiri
    - Trend: bar + line + angka di atas, padding pas
    - Footer: ada garis pemisah
    """)