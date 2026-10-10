"""
Test pictex Canvas — Swiss Grid (Minimalis Elegan)
====================================================
"""
import streamlit as st
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


st.set_page_config(page_title="Test pictex", page_icon="🎨", layout="wide")
st.title("🎨 Test pictex — Swiss Grid")


# =========================================================
# PALET WARNA — MINIMALIS
# =========================================================
WARNA = {
    "bg": "#FAFAF7",
    "accent": "#97B3AE",
    "accent_dark": "#5E7A75",
    "text_primary": "#1A1A1A",
    "text_secondary": "#666666",
    "text_muted": "#999999",
    "divider": "#D6CBBF",
    "white": "#FFFFFF",
    "red": "#C83232",
    "green": "#329632",
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
# CHART 1: DONUT — minimalis
# =========================================================
def _chart_donut(list_rak, output_path, size_px=420):
    _sorted = sorted(list_rak, key=lambda x: abs(x["nominal"]), reverse=True)
    _labels = [f"Rak {r['rak_id']}" for r in _sorted if abs(r["nominal"]) > 0]
    _sizes = [abs(r["nominal"]) for r in _sorted if abs(r["nominal"]) > 0]

    if not _sizes:
        return None

    _colors = ["#97B3AE", "#D6CBBF", "#B5C9C3", "#E8D5CC", "#C4D4C5", "#A89B8E"]
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
        wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2),
        textprops=dict(color=WARNA["text_secondary"], fontsize=10, fontweight="normal"),
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(10)
        at.set_fontweight("bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["white"])
    plt.close(fig)
    return output_path


# =========================================================
# CHART 2: TREND — minimalis, no gridline
# =========================================================
def _chart_trend(trend_data, output_path, width_px=960, height_px=200):
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
        color=WARNA["accent"], linewidth=2,
        marker="o", markersize=7,
        markerfacecolor="white",
        markeredgecolor=WARNA["accent"], markeredgewidth=2,
    )
    ax.axhline(0, color=WARNA["divider"], linewidth=0.8, linestyle="--")

    ax.tick_params(axis="x", labelsize=10, colors=WARNA["text_secondary"])
    ax.tick_params(axis="y", labelsize=9, colors=WARNA["text_muted"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(WARNA["divider"])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", ".")))

    plt.tight_layout()
    plt.savefig(output_path, dpi=_dpi, bbox_inches="tight", facecolor=WARNA["white"])
    plt.close(fig)
    return output_path
    

# =========================================================
# KONSTRUKSI INFOGRAFIS — SWISS GRID
# =========================================================
def _build_infografis(data, tmp_dir):
    from pictex import Canvas, Row, Column, Text, Image

    _W = 1000
    _H = 1550

    # === GENERATE CHART PNG ===
    _donut_path = os.path.join(tmp_dir, "chart_donut.png")
    _trend_path = os.path.join(tmp_dir, "chart_trend.png")
    _chart_donut(data["list_rak"], _donut_path, size_px=420)
    _chart_trend(data["trend_data"], _trend_path, width_px=960, height_px=200)

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=_H)
        .background_color(WARNA["bg"])
        .padding(60)
    )

    # =========================================================
    # HEADER — typography, no card
    # =========================================================
    header = (
        Column(
            Text("LAPORAN STOCK OPNAME").font_size(32).color(WARNA["text_primary"]).font_weight("bold"),
            Text("Toko C383 — Karang Satria").font_size(14).color(WARNA["text_secondary"]),
            Text(data["periode"]).font_size(12).color(WARNA["text_muted"]),
        )
        .width(_W)
        .padding(0)
        .gap(4)
    )

    # Divider
    divider_top = (
        Column(
            Text("").font_size(1),
        )
        .width(_W)
        .padding(0)
        .background_color(WARNA["divider"])
    )

    # =========================================================
    # KPI — typography gede, tanpa card, full width
    # =========================================================
    kpi_row = Row(
        Column(
            Text(f"{data['total_rak']}").font_size(52).color(WARNA["text_primary"]).font_weight("bold"),
            Text("RAK").font_size(12).color(WARNA["text_muted"]).font_weight("bold"),
        ).width(320).gap(2),

        Column(
            Text(f"{data['total_item']}").font_size(52).color(WARNA["text_primary"]).font_weight("bold"),
            Text("ITEM").font_size(12).color(WARNA["text_muted"]).font_weight("bold"),
        ).width(320).gap(2),

        Column(
            Text(_fmt_rp(data['total_nominal'])).font_size(40).color(WARNA["accent_dark"]).font_weight("bold"),
            Text("TOTAL NOMINAL").font_size(12).color(WARNA["text_muted"]).font_weight("bold"),
        ).width(360).gap(2),
    ).gap(0)

    # Divider
    divider_mid = (
        Column(Text("").font_size(1))
        .width(_W)
        .background_color(WARNA["divider"])
    )

    # =========================================================
    # SECTION TITLE HELPER
    # =========================================================
    def _section_title(num, title):
        return Row(
            Text(f"{num}").font_size(14).color(WARNA["accent"]).font_weight("bold").width(50),
            Text(title).font_size(14).color(WARNA["text_secondary"]).font_weight("bold"),
        ).width(_W).gap(10)

    # =========================================================
    # SECTION 01 — DISTRIBUSI (Donut + Ringkasan)
    # =========================================================
    _title_01 = _section_title("01", "DISTRIBUSI PER RAK")

    _donut_col = (
        Column(
            Image(_donut_path).width(380),
        )
        .width(440)
        .padding(0)
        .gap(0)
    )

    _ringkasan_col = (
        Column(
            Row(
                Text("Tanggal").font_size(12).color(WARNA["text_muted"]).width(150),
                Text(data["periode"]).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(10),
            Row(
                Text("Total Rak").font_size(12).color(WARNA["text_muted"]).width(150),
                Text(f"{data['total_rak']} rak").font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(10),
            Row(
                Text("Nominal SO").font_size(12).color(WARNA["text_muted"]).width(150),
                Text(_fmt_rp(data["total_nominal"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(10),
            Row(
                Text("Sales Periode").font_size(12).color(WARNA["text_muted"]).width(150),
                Text(_fmt_rp_no_sign(data["sales_periode"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(10),
            Row(
                Text("BTSB (0,15%)").font_size(12).color(WARNA["text_muted"]).width(150),
                Text(_fmt_rp_no_sign(data["btsb"])).font_size(12).color(WARNA["text_primary"]).font_weight("bold"),
            ).gap(10),
            Row(
                Text("Status").font_size(12).color(WARNA["text_muted"]).width(150),
                Text(data["status"]).font_size(12).color(WARNA["red"]).font_weight("bold"),
            ).gap(10),
        )
        .width(520)
        .padding(0)
        .gap(12)
    )

    _mid_row = Row(_donut_col, _ringkasan_col).gap(40)

    # =========================================================
    # SECTION 02 — INSIGHT
    # =========================================================
    _title_02 = _section_title("02", "INSIGHT")

    insight = (
        Column(
            Text(data["insight"]).font_size(13).color(WARNA["text_primary"]),
        )
        .width(_W)
        .padding(0)
        .gap(0)
    )
    
    # =========================================================
    # SECTION 03 — DETAIL PER RAK (Tabel minimalis)
    # =========================================================
    _title_03 = _section_title("03", "DETAIL PER RAK")

    _col_w = [100, 420, 160, 280]  # total 960

    # Header tabel — teks aja, divider di bawah
    _header_cells = Row(
        Text("RAK").font_size(11).color(WARNA["text_muted"]).font_weight("bold").padding(10).width(_col_w[0]),
        Text("NAMA RAK").font_size(11).color(WARNA["text_muted"]).font_weight("bold").padding(10).width(_col_w[1]),
        Text("PIC").font_size(11).color(WARNA["text_muted"]).font_weight("bold").padding(10).width(_col_w[2]),
        Text("SELISIH").font_size(11).color(WARNA["text_muted"]).font_weight("bold").padding(10).width(_col_w[3]),
    ).width(_W).gap(0)

    # Divider header
    _header_divider = (
        Column(Text("").font_size(1))
        .width(_W)
        .background_color(WARNA["divider"])
    )

    # Rows
    _rows = [_header_cells, _header_divider]
    for _r in data["list_rak"]:
        _color = WARNA["red"] if _r["nominal"] < 0 else WARNA["green"]
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(13).color(WARNA["text_primary"]).font_weight("bold").padding(12).width(_col_w[0]),
                Text(_r["nama"]).font_size(12).color(WARNA["text_secondary"]).padding(12).width(_col_w[1]),
                Text(_r["pic"]).font_size(12).color(WARNA["text_secondary"]).padding(12).width(_col_w[2]),
                Text(_fmt_rp(_r["nominal"])).font_size(13).color(_color).font_weight("bold").padding(12).width(_col_w[3]),
            ).width(_W).gap(0)
        )

    # Divider total
    _total_divider = (
        Column(Text("").font_size(1))
        .width(_W)
        .background_color(WARNA["divider"])
    )

    # Total row
    _total_color = WARNA["red"] if data["total_nominal"] < 0 else WARNA["green"]
    _total_row = Row(
        Text("TOTAL SELISIH").font_size(12).color(WARNA["text_primary"]).font_weight("bold").padding(12).width(_col_w[0] + _col_w[1] + _col_w[2]),
        Text(_fmt_rp(data["total_nominal"])).font_size(14).color(_total_color).font_weight("bold").padding(12).width(_col_w[3]),
    ).width(_W).gap(0)

    tabel_rak = Column(*_rows, _total_divider, _total_row).width(_W).gap(0)

    # =========================================================
    # SECTION 04 — TREND CHART
    # =========================================================
    _title_04 = _section_title("04", "TREND 5 HARI TERAKHIR")

    _trend_section = (
        Column(
            Image(_trend_path).width(_W - 40),
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
    # SUSUN LAYOUT — SWISS GRID
    # =========================================================
    layout = Column(
        header,          # Header typography
        divider_top,     # Divider
        kpi_row,         # 3 KPI gede
        divider_mid,     # Divider
        _title_01,       # 01 DISTRIBUSI
        _mid_row,        # Donut + Ringkasan
        _title_02,       # 02 INSIGHT
        insight,         # Insight
        _title_03,       # 03 DETAIL PER RAK
        tabel_rak,       # Tabel
        _title_04,       # 04 TREND
        _trend_section,  # Trend chart
        footer,          # Footer
    ).width(_W).gap(20)

    return canvas.render(layout)


# =========================================================
# RENDER UTAMA
# =========================================================
if st.button("🎨 Render Infografis Swiss Grid", type="primary"):
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
        st.image(_img_bytes, caption="Infografis SO — Swiss Grid")

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
    **Style:** Swiss Grid — Minimalis Elegan
    - Typography dominan
    - Tanpa card warna
    - Divider garis tipis
    - Spacing gede
    - Warna netral + accent sage
    """)