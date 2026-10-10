"""
Test pictex — Premium Report v2 (Bold & Symmetric)
====================================================
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
st.title("🎨 Premium Report v2")


# =========================================================
# PALET WARNA BERANI
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
# CHART 1: DONUT — Bold
# =========================================================
def _chart_donut(list_rak, output_path, size_px=400):
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
        _sizes,
        labels=_labels,
        colors=_colors[:len(_sizes)],
        autopct=lambda p: f"{p:.0f}%",
        startangle=90,
        wedgeprops=dict(width=0.38, edgecolor=WARNA["cream"], linewidth=3),
        textprops=dict(color=WARNA["text_primary"], fontsize=11, fontweight="bold"),
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(12)
        at.set_fontweight("bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["cream"])
    plt.close(fig)
    return output_path


# =========================================================
# CHART 2: DOUBLE CHART — Bar + Line Overlay
# =========================================================
def _chart_double(trend_data, output_path, width_px=960, height_px=260):
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
        width=0.5,
        alpha=0.7,
        edgecolor="white",
        linewidth=1.5,
    )

    # LINE
    ax.plot(
        _x, _values,
        color=WARNA["accent_deep"],
        linewidth=2.5,
        marker="o",
        markersize=9,
        markerfacecolor="white",
        markeredgecolor=WARNA["accent_deep"],
        markeredgewidth=2.5,
        zorder=5,
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
    ax.grid(axis="y", linestyle=":", alpha=0.4, color=WARNA["divider"])
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", ".")))

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
    _H = 1380

    # === GENERATE CHART PNG ===
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _double_path = os.path.join(tmp_dir, "chart_double.png")
    _chart_donut(data["list_rak"], _donut_path, size_px=400)
    _chart_double(data["trend_data"], _double_path, width_px=960, height_px=260)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=_H)
        .background_color(WARNA["bg"])
        .padding(50)
    )

    # =========================================================
    # HEADER — Bold dengan accent bar
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
        .gap(3)
    )

    header = Row(header_bar, header_text).gap(20).width(_W)

    divider_top = (
        Column(Text("").font_size(1))
        .width(_W)
        .background_color(WARNA["divider"])
    )

    # =========================================================
    # KPI CARDS — Warna berani
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
            Text(_fmt_rp(data['total_nominal'])).font_size(32).color(WARNA["red"]).font_weight("bold"),
            Text("selisih periode").font_size(11).color(WARNA["text_secondary"]),
        ).width(320).padding(22).background_color(WARNA["highlight"]).border_radius(12).gap(2),
    ).gap(20).width(_W)

    # =========================================================
    # SECTION TITLE
    # =========================================================
    def _section_title(num, title):
        return Row(
            Text("▌").font_size(18).color(WARNA["accent_deep"]).font_weight("bold"),
            Text(f"{num}").font_size(12).color(WARNA["terracotta"]).font_weight("bold").width(30),
            Text(title).font_size(14).color(WARNA["text_primary"]).font_weight("bold"),
        ).width(_W).gap(8)

    # =========================================================
    # SECTION 01 — DISTRIBUSI (Donut + Ringkasan + Insight)
    # =========================================================
    _title_01 = _section_title("01", "DISTRIBUSI PER RAK")

    # --- KOLOM KIRI: DONUT ---
    _donut_col = (
        Column(
            Image(_donut_path).width(440),
        )
        .width(480)
        .padding(10)
        .background_color(WARNA["bg"])
        .gap(0)
    )

    # --- KOLOM KANAN: RINGKASAN + INSIGHT ---
    _ringkasan_col = (
        Column(
            Text("RINGKASAN PERIODE").font_size(12).color(WARNA["accent_deep"]).font_weight("bold"),
            Row(
                Text("Tanggal").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(data["periode"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Total Rak").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(f"{data['total_rak']} rak").font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Nominal SO").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(_fmt_rp(data["total_nominal"])).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Sales Periode").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(_fmt_rp_no_sign(data["sales_periode"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("BTSB (0,15%)").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(_fmt_rp_no_sign(data["btsb"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(15),
            Row(
                Text("Status").font_size(12).color(WARNA["text_secondary"]).width(140),
                Text(data["status"]).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ).gap(15),

            # Spacer
            Text("").font_size(6).padding(6),

            # INSIGHT
            Text("INSIGHT").font_size(12).color(WARNA["accent_deep"]).font_weight("bold"),
            Column(
                Text(data["insight"]).font_size(11).color(WARNA["text_primary"]),
            ).padding(16).background_color(WARNA["accent_light"]).border_radius(8).gap(0),
        )
        .width(480)
        .padding(24)
        .background_color(WARNA["white"])
        .border_radius(12)
        .gap(10)
    )

    _mid_row = Row(_donut_col, _ringkasan_col).gap(40).width(_W)
    
    # =========================================================
    # SECTION 02 — DETAIL PER RAK
    # =========================================================
    _title_02 = _section_title("02", "DETAIL PER RAK")

    _col_w = [100, 420, 160, 280]

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

    # Total row
    _total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
    _rows.append(
        Row(
            Text("").padding(14).width(_col_w[0] + _col_w[1] + _col_w[2]),
            Text("TOTAL SELISIH").font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(14).width(180),
            Text(_fmt_rp(data["total_nominal"])).font_size(14).color(_total_color).font_weight("bold").padding(14).width(100),
        ).width(_W).background_color(WARNA["terracotta_light"]).gap(0)
    )

    tabel_rak = Column(*_rows).width(_W).gap(0)

    # =========================================================
    # SECTION 03 — TREND (Double Chart)
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
        _title_03,
        _chart_section,
        footer,
    ).width(_W).gap(22)

    return canvas.render(layout)


# =========================================================
# RENDER UTAMA
# =========================================================
if st.button("🎨 Render Premium Report v2", type="primary"):
    try:
        _tmp_dir = tempfile.mkdtemp()

        with st.spinner("Bikin infografis premium..."):
            _image = _build_infografis(_data, _tmp_dir)

        _output_path = os.path.join(_tmp_dir, "infografis_so.png")
        _image.save(_output_path)

        with open(_output_path, "rb") as _f:
            _img_bytes = _f.read()

        st.success(f"✅ Berhasil! Ukuran: {len(_img_bytes):,} bytes")

        st.markdown("---")
        st.markdown("### 📸 Preview")
        st.image(_img_bytes, caption="Premium Report v2")

        st.download_button(
            "📥 Download PNG",
            data=_img_bytes,
            file_name=f"laporan_so_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png",
            key="dl_premium_v2",
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
    **Style:** Premium Report v2 — Bold & Symmetric

    **Warna berani:**
    - Sage Deep `#5E7A75` (accent utama)
    - Terracotta `#B5745E` (accent kedua)
    - Cream `#F5F1EA` (background)
    - Charcoal `#2D2A26` (text)

    **Layout simetris:**
    - Donut kiri 480px + Ringkasan kanan 480px
    - Tabel zebra dengan header sage deep
    - Double chart bar + line

    **Section:**
    01. Distribusi + Ringkasan + Insight
    02. Detail per Rak
    03. Trend Harian
    """)