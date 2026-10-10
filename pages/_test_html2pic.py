"""
Infografis SO — Matplotlib Murni
==================================
1 canvas, 1 savefig(), no pictex, no card embed
"""
import streamlit as st
import io
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd


st.set_page_config(page_title="Infografis SO", page_icon="🎨", layout="wide")
st.title("🎨 Infografis SO — Matplotlib Murni")


# =========================================================
# PALET WARNA
# =========================================================
W = {
    "bg": "#F5F1EA",
    "sage": "#5E7A75",
    "sage_deep": "#3D5A55",
    "sage_light": "#D9E4E0",
    "terracotta": "#B5745E",
    "terracotta_light": "#E8D5C9",
    "highlight": "#EDE8DE",
    "text": "#2D2A26",
    "text_sec": "#6B6560",
    "text_muted": "#9C9488",
    "divider": "#DDD5C8",
    "white": "#FFFFFF",
    "red": "#B8383A",
    "green": "#4A7C59",
    "bar_neg": "#C9907E",
    "bar_pos": "#7B9B95",
}


# =========================================================
# DATA DUMMY
# =========================================================
DATA = {
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
# HELPER FORMAT
# =========================================================
def _rp(val):
    n = int(round(float(val)))
    sign = "+" if n >= 0 else "-"
    return f"{sign}Rp {abs(n):,}".replace(",", ".")


def _rp_no_sign(val):
    n = int(round(float(val)))
    return f"Rp {abs(n):,}".replace(",", ".")


def _rp_short(val):
    n = int(round(float(val)))
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:+.1f}jt"
    if abs(n) >= 1_000:
        return f"{n/1_000:+.0f}rb"
    return f"{n:+d}"


# =========================================================
# HELPER DRAW: CARD (rounded rectangle)
# =========================================================
def _draw_card(ax, x, y, w, h, color, radius=0.02):
    """Gambar card rounded di axes (koordinat 0-1)."""
    card = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=color, edgecolor="none",
        transform=ax.transAxes, zorder=1,
    )
    ax.add_patch(card)


# =========================================================
# HELPER DRAW: TEXT
# =========================================================
def _text(ax, x, y, s, size=10, color=None, weight="normal",
          ha="left", va="center"):
    if color is None:
        color = W["text"]
    return ax.text(
        x, y, s, fontsize=size, color=color, fontweight=weight,
        ha=ha, va=va, transform=ax.transAxes, zorder=10,
    )


# =========================================================
# HELPER DRAW: DIVIDER
# =========================================================
def _divider(ax, x, y, w, color=None, thickness=0.002):
    if color is None:
        color = W["divider"]
    line = Rectangle(
        (x, y), w, thickness,
        facecolor=color, edgecolor="none",
        transform=ax.transAxes, zorder=5,
    )
    ax.add_patch(line)
    

# =========================================================
# FUNGSI UTAMA: RENDER INFOGRAFIS
# =========================================================
def render_infografis(data, output_path):
    """Render infografis SO — 1 canvas matplotlib."""

    # === FIGURE SIZE ===
    # A4 portrait: 8.27 x 11.69 inch → kita pakai 8.27 x 10.5
    FIG_W, FIG_H = 8.27, 11.0
    DPI = 130

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=W["bg"])

    # === AXES UTAMA (full canvas) ===
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor(W["bg"])

    # =========================================================
    # LAYOUT KOORDINAT (semua 0-1, dari ATAS ke BAWAH)
    # =========================================================
    PAD = 0.04           # padding kiri/kanan
    W_CONTENT = 1 - 2 * PAD
    X_LEFT = PAD
    X_RIGHT = 1 - PAD

    # Y positions (dari atas, konversi ke 0-1 bawah)
    Y_HEADER_TOP = 1.00
    Y_HEADER_BOT = 0.90
    Y_KPI_TOP = 0.885
    Y_KPI_BOT = 0.80
    Y_S1_TOP = 0.785
    Y_S1_BOT = 0.46
    Y_S2_TOP = 0.445
    Y_S2_BOT = 0.10
    Y_FOOTER = 0.04

    # =========================================================
    # 1. HEADER BAND
    # =========================================================
    _draw_card(ax, X_LEFT, Y_HEADER_BOT, W_CONTENT, Y_HEADER_TOP - Y_HEADER_BOT,
               W["sage_deep"], radius=0.015)

    _text(ax, X_LEFT + 0.02, Y_HEADER_TOP - 0.035,
          "LAPORAN STOCK OPNAME", size=17, color=W["white"], weight="bold")
    _text(ax, X_LEFT + 0.02, Y_HEADER_TOP - 0.058,
          "Toko C383 — Karang Satria", size=9, color=W["sage_light"])
    _text(ax, X_LEFT + 0.02, Y_HEADER_TOP - 0.075,
          data["periode"], size=8, color=W["sage_light"])

    # =========================================================
    # 2. KPI CARDS (3 kolom)
    # =========================================================
    GAP = 0.015
    KPI_W = (W_CONTENT - 2 * GAP) / 3
    KPI_H = Y_KPI_TOP - Y_KPI_BOT

    kpi_data = [
        ("TOTAL RAK", f"{data['total_rak']}", "rak ter-SO", W["sage_light"]),
        ("TOTAL ITEM", f"{data['total_item']}", "item tercatat", W["terracotta_light"]),
        ("TOTAL NOMINAL", _rp(data["total_nominal"]), "selisih periode", W["highlight"]),
    ]

    for i, (label, value, sub, bg) in enumerate(kpi_data):
        x = X_LEFT + i * (KPI_W + GAP)
        _draw_card(ax, x, Y_KPI_BOT, KPI_W, KPI_H, bg, radius=0.012)

        _text(ax, x + 0.012, Y_KPI_TOP - 0.018,
              label, size=7.5, color=W["text_muted"], weight="bold")
        _text(ax, x + 0.012, Y_KPI_TOP - 0.043,
              value, size=22, color=W["text"], weight="bold")
        _text(ax, x + 0.012, Y_KPI_TOP - 0.062,
              sub, size=8, color=W["text_sec"])

    # =========================================================
    # 3. SECTION TITLE 01
    # =========================================================
    _text(ax, X_LEFT, Y_S1_TOP + 0.012, "▌", size=14, color=W["sage_deep"], weight="bold")
    _text(ax, X_LEFT + 0.02, Y_S1_TOP + 0.012, "01", size=9, color=W["terracotta"], weight="bold")
    _text(ax, X_LEFT + 0.045, Y_S1_TOP + 0.012,
          "DISTRIBUSI & RINGKASAN", size=10, color=W["text"], weight="bold")

    # =========================================================
    # 4. SECTION 01: DONUT (kiri) + RINGKASAN + INSIGHT (kanan)
    # =========================================================
    S1_H = Y_S1_TOP - Y_S1_BOT
    LEFT_W = (W_CONTENT - 0.02) * 0.48
    RIGHT_W = (W_CONTENT - 0.02) * 0.52
    LEFT_X = X_LEFT
    RIGHT_X = X_LEFT + LEFT_W + 0.02

    # --- KIRI: DONUT ---
    _draw_card(ax, LEFT_X, Y_S1_BOT, LEFT_W, S1_H, W["white"], radius=0.012)

    _text(ax, LEFT_X + 0.015, Y_S1_TOP - 0.018,
          "KONTRIBUSI PER RAK", size=9, color=W["sage_deep"], weight="bold")
    _divider(ax, LEFT_X + 0.015, Y_S1_TOP - 0.028, LEFT_W - 0.03, W["sage_deep"], 0.0015)

    # Sub-axes buat donut (dalam section 1 kiri)
    donut_ax = fig.add_axes([
        LEFT_X + 0.03, Y_S1_BOT + 0.01,
        LEFT_W - 0.06, S1_H - 0.055
    ])
    donut_ax.set_facecolor(W["white"])

    list_sorted = sorted(data["list_rak"], key=lambda x: abs(x["nominal"]), reverse=True)
    sizes = [abs(r["nominal"]) for r in list_sorted if abs(r["nominal"]) > 0]
    labels = [f"Rak {r['rak_id']}" for r in list_sorted if abs(r["nominal"]) > 0]
    colors = ["#5E7A75", "#B5745E", "#7B9B95", "#D9C4B5", "#A8B5AE", "#E8D5C9"][:len(sizes)]

    wedges, texts, autotexts = donut_ax.pie(
        sizes, labels=None, colors=colors,
        autopct=lambda p: f"{p:.0f}%", pctdistance=0.78, startangle=90,
        wedgeprops=dict(width=0.40, edgecolor=W["white"], linewidth=2.5),
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(9)
        at.set_fontweight("bold")

    # Label di luar
    for i, (wedge, label) in enumerate(zip(wedges, labels)):
        ang = (wedge.theta2 + wedge.theta1) / 2
        x = np.cos(np.radians(ang))
        y = np.sin(np.radians(ang))
        ha = "right" if x < 0 else "left"
        donut_ax.annotate(
            label, xy=(x * 0.85, y * 0.85), xytext=(x * 1.18, y * 1.18),
            ha=ha, va="center", fontsize=7.5, fontweight="bold", color=W["text"],
        )

    # Nilai total di tengah
    total_nom = sum(sizes)
    donut_ax.text(0, 0.05, _rp_no_sign(total_nom), ha="center", va="center",
                  fontsize=10, fontweight="bold", color=W["sage_deep"])
    donut_ax.text(0, -0.12, "TOTAL", ha="center", va="center",
                  fontsize=7, fontweight="bold", color=W["text_muted"])
    donut_ax.set_aspect("equal")

    # --- KANAN: RINGKASAN + INSIGHT ---
    _draw_card(ax, RIGHT_X, Y_S1_BOT, RIGHT_W, S1_H, W["white"], radius=0.012)

    _text(ax, RIGHT_X + 0.015, Y_S1_TOP - 0.018,
          "RINGKASAN PERIODE", size=9, color=W["sage_deep"], weight="bold")
    _divider(ax, RIGHT_X + 0.015, Y_S1_TOP - 0.028, RIGHT_W - 0.03, W["sage_deep"], 0.0015)

    # Metrics
    status_color = W["red"] if data["status"] == "OVER" else W["green"]

    metrics = [
        ("Tanggal", data["periode"], W["text"]),
        ("Total Rak", f"{data['total_rak']} rak", W["text"]),
        ("Nominal SO", _rp(data["total_nominal"]), W["red"]),
        ("Sales Periode", _rp_no_sign(data["sales_periode"]), W["text"]),
        ("BTSB (0,15%)", _rp_no_sign(data["btsb"]), W["text"]),
        ("Status", data["status"], status_color),
    ]

    y_metric = Y_S1_TOP - 0.05
    for label, val, color in metrics:
        _text(ax, RIGHT_X + 0.015, y_metric, label, size=8, color=W["text_muted"])
        _text(ax, RIGHT_X + 0.13, y_metric, val, size=9, color=color, weight="bold")
        y_metric -= 0.022
        _divider(ax, RIGHT_X + 0.015, y_metric + 0.008, RIGHT_W - 0.03, W["divider"], 0.0008)

    # --- INSIGHT ---
    y_insight = y_metric - 0.02

    _text(ax, RIGHT_X + 0.015, y_insight,
          "INSIGHT", size=9, color=W["sage_deep"], weight="bold")
    _divider(ax, RIGHT_X + 0.015, y_insight - 0.012, RIGHT_W - 0.03, W["sage_deep"], 0.0015)

    # Insight box
    insight_y = y_insight - 0.035
    insight_h = 0.055
    _draw_card(ax, RIGHT_X + 0.015, insight_y - insight_h, RIGHT_W - 0.03, insight_h,
               W["terracotta_light"], radius=0.008)
    _text(ax, RIGHT_X + 0.025, insight_y - insight_h / 2,
          data["insight"], size=7.5, color=W["text"], weight="bold")

    # =========================================================
    # 5. SECTION TITLE 02
    # =========================================================
    _text(ax, X_LEFT, Y_S2_TOP + 0.012, "▌", size=14, color=W["sage_deep"], weight="bold")
    _text(ax, X_LEFT + 0.02, Y_S2_TOP + 0.012, "02", size=9, color=W["terracotta"], weight="bold")
    _text(ax, X_LEFT + 0.045, Y_S2_TOP + 0.012,
          "DETAIL & TREND", size=10, color=W["text"], weight="bold")

    # =========================================================
    # 6. SECTION 02: TABEL (kiri) + TREND (kanan)
    # =========================================================
    S2_H = Y_S2_TOP - Y_S2_BOT
    TBL_W = (W_CONTENT - 0.02) * 0.55
    TRD_W = (W_CONTENT - 0.02) * 0.45
    TBL_X = X_LEFT
    TRD_X = X_LEFT + TBL_W + 0.02

    # --- KIRI: TABEL ---
    _draw_card(ax, TBL_X, Y_S2_BOT, TBL_W, S2_H, W["white"], radius=0.012)

    # Sub-axes buat tabel
    tbl_ax = fig.add_axes([
        TBL_X + 0.015, Y_S2_BOT + 0.01,
        TBL_W - 0.03, S2_H - 0.02
    ])
    tbl_ax.axis("off")

    # Header tabel
    col_labels = ["RAK", "NAMA RAK", "PIC", "SELISIH"]
    col_w = [0.10, 0.45, 0.18, 0.27]

    # Header bg
    tbl_ax.add_patch(Rectangle((0, 0.88), 1, 0.10,
                                facecolor=W["sage_deep"], edgecolor="none",
                                transform=tbl_ax.transAxes))

    x_pos = 0
    for i, lbl in enumerate(col_labels):
        tbl_ax.text(x_pos + 0.01, 0.93, lbl, fontsize=7.5, color=W["white"],
                    fontweight="bold", va="center", transform=tbl_ax.transAxes)
        x_pos += col_w[i]

    # Body tabel
    y_pos = 0.82
    row_h = 0.14
    for idx, r in enumerate(data["list_rak"]):
        bg = W["bg"] if idx % 2 == 0 else W["white"]
        tbl_ax.add_patch(Rectangle((0, y_pos - row_h + 0.02), 1, row_h,
                                    facecolor=bg, edgecolor="none",
                                    transform=tbl_ax.transAxes))
        color = W["red"] if r["nominal"] < 0 else W["green"]

        x_pos = 0
        vals = [r["rak_id"], r["nama"][:22], r["pic"], _rp(r["nominal"])]
        for i, v in enumerate(vals):
            tbl_ax.text(x_pos + 0.01, y_pos - row_h / 2 + 0.02, v,
                        fontsize=7, color=color if i == 3 else W["text"],
                        fontweight="bold" if i in (0, 2, 3) else "normal",
                        va="center", transform=tbl_ax.transAxes)
            x_pos += col_w[i]

        y_pos -= row_h

    # Total row
    tbl_ax.add_patch(Rectangle((0, y_pos - row_h + 0.02), 1, row_h,
                                facecolor=W["terracotta_light"], edgecolor="none",
                                transform=tbl_ax.transAxes))
    total_color = W["red"] if data["total_nominal"] < 0 else W["green"]
    tbl_ax.text(0.60, y_pos - row_h / 2 + 0.02, "TOTAL",
                fontsize=8, color=W["text"], fontweight="bold",
                va="center", transform=tbl_ax.transAxes)
    tbl_ax.text(0.74, y_pos - row_h / 2 + 0.02, _rp(data["total_nominal"]),
                fontsize=8, color=total_color, fontweight="bold",
                va="center", transform=tbl_ax.transAxes)

    # --- KANAN: TREND ---
    _draw_card(ax, TRD_X, Y_S2_BOT, TRD_W, S2_H, W["white"], radius=0.012)

    _text(ax, TRD_X + 0.015, Y_S2_TOP - 0.018,
          "TREND SELISIH HARIAN", size=9, color=W["sage_deep"], weight="bold")
    _divider(ax, TRD_X + 0.015, Y_S2_TOP - 0.028, TRD_W - 0.03, W["sage_deep"], 0.0015)

    # Sub-axes buat trend chart
    trend_ax = fig.add_axes([
        TRD_X + 0.03, Y_S2_BOT + 0.02,
        TRD_W - 0.06, S2_H - 0.06
    ])
    trend_ax.set_facecolor(W["white"])

    trend_labels = [t["tanggal"] for t in data["trend_data"]]
    trend_values = [t["nominal"] for t in data["trend_data"]]
    x_idx = np.arange(len(trend_labels))

    bar_colors = [W["bar_neg"] if v < 0 else W["bar_pos"] for v in trend_values]
    trend_ax.bar(x_idx, trend_values, color=bar_colors, width=0.55,
                 alpha=0.75, edgecolor="white", linewidth=1)

    trend_ax.plot(x_idx, trend_values, color=W["sage_deep"], linewidth=2,
                  marker="o", markersize=5, markerfacecolor="white",
                  markeredgecolor=W["sage_deep"], markeredgewidth=1.5, zorder=5)

    for i, v in enumerate(trend_values):
        c = W["red"] if v < 0 else W["green"]
        off = 2500 if v >= 0 else -2500
        trend_ax.text(i, v + off, _rp_short(v),
                      ha="center", va="bottom" if v >= 0 else "top",
                      fontsize=6.5, fontweight="bold", color=c)

    trend_ax.axhline(0, color=W["text_muted"], linewidth=0.6, alpha=0.5)
    trend_ax.set_xticks(x_idx)
    trend_ax.set_xticklabels(trend_labels)
    trend_ax.tick_params(axis="x", labelsize=7, colors=W["text_sec"])
    trend_ax.tick_params(axis="y", labelsize=6.5, colors=W["text_muted"])
    trend_ax.spines["top"].set_visible(False)
    trend_ax.spines["right"].set_visible(False)
    trend_ax.spines["left"].set_visible(False)
    trend_ax.spines["bottom"].set_color(W["divider"])
    trend_ax.grid(axis="y", linestyle=":", alpha=0.3, color=W["divider"])
    trend_ax.set_axisbelow(True)

    min_v, max_v = min(trend_values), max(trend_values)
    pad = abs(max_v - min_v) * 0.40 if max_v != min_v else 8000
    trend_ax.set_ylim(min_v - pad, max_v + pad)

    # =========================================================
    # 7. FOOTER
    # =========================================================
    _divider(ax, X_LEFT, Y_FOOTER + 0.015, W_CONTENT, W["divider"], 0.001)
    _text(ax, X_LEFT, Y_FOOTER,
          "Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383",
          size=7, color=W["text_muted"])

    # =========================================================
    # SAVE
    # =========================================================
    fig.savefig(output_path, dpi=DPI, facecolor=W["bg"], bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return output_path


# =========================================================
# STREAMLIT APP
# =========================================================
if st.button("🎨 Render Infografis", type="primary"):
    try:
        tmp_dir = tempfile.mkdtemp()
        output_path = os.path.join(tmp_dir, "infografis_so.png")

        with st.spinner("Bikin infografis..."):
            render_infografis(DATA, output_path)

        with open(output_path, "rb") as f:
            img_bytes = f.read()

        st.success(f"✅ Berhasil! Ukuran: {len(img_bytes):,} bytes")
        st.markdown("---")
        st.markdown("### 📸 Preview")
        st.image(img_bytes, caption="Infografis SO — Matplotlib Murni")

        st.download_button(
            "📥 Download PNG",
            data=img_bytes,
            file_name=f"laporan_so_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png",
            key="dl_mpl",
            type="primary",
        )

        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    except Exception as e:
        import traceback
        st.error(f"❌ Gagal:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")