"""
Rei Export — PDF Generator (Jurnal Ilmiah Style)
=================================================
Generate PDF laporan analisis SO dengan gaya jurnal ilmiah profesional.

Dependencies: fpdf2, matplotlib
Style: Halloween theme (ungu/emas) — sementara
"""

import os
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from zoneinfo import ZoneInfo
from fpdf import FPDF, FontFace


# =========================================================
# KONFIGURASI STYLE
# =========================================================
class ReiTheme:
    """Theme colors — Halloween style"""
    BG_DARK = (20, 12, 35)           # Background gelap
    PURPLE = (76, 29, 149)           # Ungu
    GOLD = (232, 177, 137)           # Emas
    SAGE = (127, 185, 155)           # Sage green
    TEXT_LIGHT = (245, 230, 211)     # Text terang
    TEXT_MUTED = (168, 155, 142)     # Text muted
    WHITE = (255, 255, 255)
    RED = (220, 60, 60)
    GREEN = (60, 180, 100)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def fmt_rp(value):
    """Format Rupiah: Rp 1.234.567"""
    try:
        return f"Rp {int(float(value)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp_short(value):
    """Format Rupiah singkat: Rp 1,2 jt / Rp 399 rb"""
    try:
        _v = abs(float(value))
        if _v >= 1_000_000_000:
            return f"Rp {_v/1_000_000_000:.1f} M"
        if _v >= 1_000_000:
            return f"Rp {_v/1_000_000:.1f} jt"
        if _v >= 1_000:
            return f"Rp {_v/1_000:.0f} rb"
        return f"Rp {_v:.0f}"
    except Exception:
        return "Rp 0"


# =========================================================
# CUSTOM PDF CLASS — Header & Footer
# =========================================================
class ReiPDF(FPDF):
    """PDF class dengan header & footer custom."""

    def __init__(self, title="Laporan Analisis Stock Opname", theme=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.rei_title = title
        self.theme = theme or ReiTheme()
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        """Header tiap halaman."""
        if self.page_no() == 1:
            return  # Cover page gak perlu header

        # Bar header
        self.set_fill_color(*self.theme.PURPLE)
        self.rect(0, 0, 210, 18, "F")

        # Title header
        self.set_y(5)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.theme.GOLD)
        self.cell(0, 8, "LAPORAN ANALISIS STOCK OPNAME — TOKO C383", align="L")

        # Page number di kanan
        self.set_y(5)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*self.theme.TEXT_LIGHT)
        self.cell(0, 8, f"Halaman {self.page_no()}", align="R")

        self.ln(15)

    def footer(self):
        """Footer tiap halaman."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*self.theme.TEXT_MUTED)

        # Garis atas footer
        self.set_draw_color(*self.theme.GOLD)
        self.set_line_width(0.3)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)

        self.cell(0, 10, "Dashboard SO Toko C383 — Rei (AI Analis)", align="C")
        
        # =========================================================
# CHART GENERATOR (Matplotlib)
# =========================================================
def _chart_to_image(fig, dpi=200):
    """Convert matplotlib figure ke BytesIO image."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="#140C23", edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


def _create_donut_chart(gross_minus, total_plus, net_lost):
    """Bikin donut chart Gross vs Net Lost Sales."""
    fig, ax = plt.subplots(figsize=(5, 4), facecolor="#140C23")

    _labels = ["Gross Lost", "Kompensasi Plus", "Net Lost"]
    _values = [gross_minus, total_plus, net_lost]
    _colors = ["#E8B189", "#7FB99B", "#4C1D95"]

    _wedges, _texts, _autotexts = ax.pie(
        _values, labels=None, autopct="%1.0f%%",
        colors=_colors, startangle=90,
        wedgeprops=dict(width=0.4, edgecolor="#140C23", linewidth=2),
        textprops=dict(color="#F5E6D3", fontsize=9, weight="bold"),
    )

    ax.set_title("Komposisi Lost Sales", color="#E8B189",
                 fontsize=11, weight="bold", pad=10)

    # Legend
    ax.legend(_wedges, _labels, loc="lower center",
              bbox_to_anchor=(0.5, -0.15), ncol=3,
              facecolor="#1E143C", edgecolor="#E8B189",
              labelcolor="#F5E6D3", fontsize=8, framealpha=0.9)

    fig.tight_layout()
    return _chart_to_image(fig)


def _create_trend_chart(chart_data):
    """Bikin line chart trend SO."""
    if not chart_data:
        return None

    fig, ax = plt.subplots(figsize=(6, 3.5), facecolor="#140C23")

    _labels = [str(c.get("tanggal", ""))[-5:] for c in chart_data]
    _values = [float(c.get("nominal", 0)) for c in chart_data]

    _colors = ["#7FB99B" if v >= 0 else "#E8B189" for v in _values]

    _bars = ax.bar(_labels, _values, color=_colors,
                   edgecolor="#140C23", linewidth=1.5)

    # Garis nol
    ax.axhline(y=0, color="#A89B8E", linewidth=0.8, linestyle="--", alpha=0.5)

    # Style
    ax.set_facecolor("#1E143C")
    ax.set_title("Trend Selisih SO (7 Hari Terakhir)", color="#E8B189",
                 fontsize=11, weight="bold", pad=10)
    ax.set_ylabel("Nominal (Rp)", color="#F5E6D3", fontsize=9)
    ax.tick_params(axis="x", colors="#F5E6D3", labelsize=8)
    ax.tick_params(axis="y", colors="#F5E6D3", labelsize=8)

    # Grid
    ax.grid(axis="y", color="#A89B8E", alpha=0.15, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#A89B8E")
    ax.spines["left"].set_color("#A89B8E")

    # Value labels
    for _bar, _val in zip(_bars, _values):
        _y = _val + (max(_values) * 0.03 if _val >= 0 else min(_values) * 0.08)
        _color = "#7FB99B" if _val >= 0 else "#E8B189"
        ax.text(_bar.get_x() + _bar.get_width()/2, _y,
                fmt_rp_short(_val), ha="center", va="bottom" if _val >= 0 else "top",
                color=_color, fontsize=7, weight="bold")

    fig.tight_layout()
    return _chart_to_image(fig)
    
    # =========================================================
# MAIN EXPORT FUNCTION
# =========================================================
def generate_rei_pdf(data_context):
    """
    Generate PDF laporan Rei dari data context.

    Args:
        data_context: dict dengan keys:
            - periode: str
            - rekap: dict (dari rekap_so)
            - lost_sales: dict {gross, plus, net, shrinkage, net_sales}
            - btsb: dict {net_sales, btsb, total_selisih, nsb, status}
            - chart_data: list
            - top_items: list
            - top_rak: list
            - ai_analysis: str (dari Rei)

    Returns:
        bytes: PDF file bytes, atau None kalau gagal
    """
    try:
        _theme = ReiTheme()
        _pdf = ReiPDF(theme=_theme)
        _periode = data_context.get("periode", "-")
        _tgl_cetak = _now_jkt().strftime("%d %B %Y, %H:%M WIB")

        # =====================================================
        # HALAMAN 1 — COVER
        # =====================================================
        _pdf.add_page()

        # Background gelap
        _pdf.set_fill_color(*_theme.BG_DARK)
        _pdf.rect(0, 0, 210, 297, "F")

        # Border emas
        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(1.5)
        _pdf.rect(10, 10, 190, 277)

        _pdf.set_draw_color(*_theme.SAGE)
        _pdf.set_line_width(0.5)
        _pdf.rect(13, 13, 184, 271)

        # Spacer atas
        _pdf.ln(50)

        # Judul utama
        _pdf.set_font("Helvetica", "B", 28)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 15, "LAPORAN ANALISIS", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 15, "STOCK OPNAME", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(5)

        # Subtitle
        _pdf.set_font("Helvetica", "", 14)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.cell(0, 10, "Toko C383 — Karang Satria", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(3)

        # Periode
        _pdf.set_font("Helvetica", "I", 12)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 10, f"Periode: {_periode}", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(30)

        # Divider
        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(0.8)
        _pdf.line(60, _pdf.get_y(), 150, _pdf.get_y())
        _pdf.ln(20)

        # Metadata
        _pdf.set_font("Helvetica", "", 11)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.cell(0, 8, "Disusun oleh:", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font("Helvetica", "B", 14)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 10, "Rei — Analis SO (AI-3)", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(5)

        _pdf.set_font("Helvetica", "", 10)
        _pdf.set_text_color(*_theme.TEXT_MUTED)
        _pdf.cell(0, 6, f"Tanggal Cetak: {_tgl_cetak}", align="C", new_x="LMARGIN", new_y="NEXT")

        # =====================================================
        # HALAMAN 2 — EXECUTIVE SUMMARY
        # =====================================================
        _pdf.add_page()
        _pdf.set_text_color(*_theme.TEXT_LIGHT)

        _pdf.set_font("Helvetica", "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "1. EXECUTIVE SUMMARY", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        # KPI Boxes
        _lost = data_context.get("lost_sales", {})
        _btsb = data_context.get("btsb", {})

        _kpi_data = [
            ("Net Sales", fmt_rp(_lost.get("net_sales", 0)), _theme.SAGE),
            ("Net Lost Sales", fmt_rp(_lost.get("net", 0)), _theme.GOLD),
            ("Shrinkage Rate", f"{_lost.get('shrinkage', 0):.2f}%", 
             _theme.RED if _lost.get("shrinkage", 0) > 2 else _theme.GREEN),
        ]

        _x_start = 15
        _box_w = 58
        _box_h = 25
        _gap = 3

        for _i, (_label, _value, _color) in enumerate(_kpi_data):
            _x = _x_start + (_i * (_box_w + _gap))
            _y = _pdf.get_y()

            # Box
            _pdf.set_fill_color(*_theme.PURPLE)
            _pdf.rect(_x, _y, _box_w, _box_h, "F")

            _pdf.set_draw_color(*_color)
            _pdf.set_line_width(0.8)
            _pdf.rect(_x, _y, _box_w, _box_h)

            # Label
            _pdf.set_xy(_x, _y + 3)
            _pdf.set_font("Helvetica", "", 8)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.cell(_box_w, 5, _label, align="C")

            # Value
            _pdf.set_xy(_x, _y + 10)
            _pdf.set_font("Helvetica", "B", 13)
            _pdf.set_text_color(*_color)
            _pdf.cell(_box_w, 8, _value, align="C")

        _pdf.ln(_box_h + 8)

        # BTSB Box
        _pdf.set_font("Helvetica", "B", 12)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 8, "Status BTSB & NSB", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(2)

        _status_color = _theme.RED if _btsb.get("status") == "PERLU PERHATIAN" else _theme.GREEN

        _pdf.set_font("Helvetica", "", 10)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.cell(0, 6, f"Net Sales: {fmt_rp(_btsb.get('net_sales', 0))}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 6, f"BTSB (0,15%): {fmt_rp(_btsb.get('btsb', 0))}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 6, f"Total Selisih: {fmt_rp(abs(_btsb.get('total_selisih', 0)))}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 6, f"NSB: {fmt_rp(_btsb.get('nsb', 0))}", new_x="LMARGIN", new_y="NEXT")

        _pdf.set_font("Helvetica", "B", 10)
        _pdf.set_text_color(*_status_color)
        _pdf.cell(0, 8, f"Status: {_btsb.get('status', '-')}", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(5)

        # =====================================================
        # HALAMAN 3 — METODOLOGI
        # =====================================================
        _pdf.add_page()

        _pdf.set_font("Helvetica", "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "2. METODOLOGI", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        _pdf.set_font("Helvetica", "", 10)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)

        _metodologi = [
            ("2.1 Sumber Data", 
             f"Data diambil dari sistem SO periode {_periode}. "
             f"Total rak: {data_context.get('rekap', {}).get('total_rak', 0)}. "
             f"Total item: {data_context.get('rekap', {}).get('total_item', 0)}."),
            ("2.2 Metrik yang Digunakan",
             "1. Gross Lost Sales = Σ |nominal_adjust| item dengan qty_var < 0.\n"
             "2. Net Lost Sales = |Σ nominal_adjust semua item|.\n"
             "3. Shrinkage Rate = (Net Lost Sales / Net Sales) × 100%."),
            ("2.3 Batasan",
             "1. Data hanya dari SO periode ini.\n"
             "2. Tidak ada data benchmark internal Alfamart.\n"
             "3. Analisis berbasis pola data yang tersedia."),
        ]

        for _title, _content in _metodologi:
            _pdf.set_font("Helvetica", "B", 11)
            _pdf.set_text_color(*_theme.SAGE)
            _pdf.cell(0, 8, _title, new_x="LMARGIN", new_y="NEXT")
            _pdf.set_font("Helvetica", "", 10)
            _pdf.set_text_color(*_theme.TEXT_LIGHT)
            _pdf.multi_cell(0, 6, _content)
            _pdf.ln(4)

        # =====================================================
        # HALAMAN 4 — CHART & TREND
        # =====================================================
        _pdf.add_page()

        _pdf.set_font("Helvetica", "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "3. ANALISIS TREND", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        # Trend chart
        _chart_data = data_context.get("chart_data", [])
        if _chart_data:
            _trend_img = _create_trend_chart(_chart_data)
            if _trend_img:
                _pdf.image(_trend_img, x=20, w=170)
                _pdf.ln(3)

        # Interpretasi
        _pdf.set_font("Helvetica", "B", 11)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 8, "Interpretasi:", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font("Helvetica", "", 10)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)

        _ai_analysis = data_context.get("ai_analysis", "")
        if _ai_analysis:
            _pdf.multi_cell(0, 6, _ai_analysis[:2000])
        else:
            _pdf.multi_cell(0, 6, "Data tidak tersedia untuk interpretasi.")

        # =====================================================
        # HALAMAN 5 — TOP ITEM & RAK
        # =====================================================
        _pdf.add_page()

        _pdf.set_font("Helvetica", "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "4. TOP ITEM & RAK", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        # Top Items table
        _pdf.set_font("Helvetica", "B", 11)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 8, "4.1 Top 10 Item Selisih", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(2)

        _top_items = data_context.get("top_items", [])
        if _top_items:
            _headings = FontFace(emphasis="BOLD", color=(232, 177, 137),
                                 fill_color=(76, 29, 149))
            with _pdf.table(
                col_widths=(80, 25, 35, 25),
                headings_style=_headings,
                line_height=6,
                text_align=("LEFT", "CENTER", "RIGHT", "CENTER"),
                repeat_headings=1,
            ) as _table:
                _row = _table.row()
                for _h in ["Nama Produk", "Rak", "Nominal (Rp)", "PIC"]:
                    _row.cell(_h)

                for _item in _top_items[:10]:
                    _row = _table.row()
                    _row.cell(str(_item.get("nama_produk", "-"))[:40])
                    _row.cell(str(_item.get("rak_id", "-")))
                    _row.cell(fmt_rp(abs(_item.get("nominal_adjust", 0))))
                    _row.cell(str(_item.get("pic", "-")))
        else:
            _pdf.set_font("Helvetica", "I", 10)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.multi_cell(0, 6, "Data tidak tersedia.")

        _pdf.ln(8)

        # Top Rak table
        _pdf.set_font("Helvetica", "B", 11)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 8, "4.2 Top 5 Rak Minus", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(2)

        _top_rak = data_context.get("top_rak", [])
        if _top_rak:
            with _pdf.table(
                col_widths=(30, 40, 45, 30),
                headings_style=_headings,
                line_height=6,
                text_align=("CENTER", "LEFT", "RIGHT", "CENTER"),
                repeat_headings=1,
            ) as _table:
                _row = _table.row()
                for _h in ["Rak", "PIC", "Nominal (Rp)", "Jml Item"]:
                    _row.cell(_h)

                for _r in _top_rak[:5]:
                    _row = _table.row()
                    _row.cell(str(_r.get("rak_id", "-")))
                    _row.cell(str(_r.get("pic", "-")))
                    _row.cell(fmt_rp(abs(_r.get("total", 0))))
                    _row.cell(str(_r.get("total_item", 0)))
        else:
            _pdf.set_font("Helvetica", "I", 10)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.multi_cell(0, 6, "Data tidak tersedia.")

        # =====================================================
        # HALAMAN 6 — REKOMENDASI
        # =====================================================
        _pdf.add_page()

        _pdf.set_font("Helvetica", "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "5. REKOMENDASI AUDIT", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        _pdf.set_font("Helvetica", "", 10)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)

        # Generate rekomendasi dari data
        _rekomendasi = _generate_rekomendasi(data_context)
        for _i, _rek in enumerate(_rekomendasi, 1):
            _pdf.set_font("Helvetica", "B", 10)
            _pdf.set_text_color(*_theme.SAGE)
            _pdf.cell(0, 7, f"{_i}. {_rek.get('title', '-')}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_font("Helvetica", "", 10)
            _pdf.set_text_color(*_theme.TEXT_LIGHT)
            _pdf.multi_cell(0, 6, _rek.get("detail", "-"))
            _pdf.ln(2)

        # =====================================================
        # HALAMAN 7 — PENUTUP
        # =====================================================
        _pdf.add_page()

        _pdf.set_font("Helvetica", "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "6. PENUTUP", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(5)

        _pdf.set_font("Helvetica", "", 11)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.multi_cell(0, 7,
            "Laporan ini disusun berdasarkan data SO periode yang tertera. "
            "Data yang tidak tersedia tidak diestimasi atau diasumsikan. "
            "Analisis dan rekomendasi bersifat sebagai bahan pertimbangan "
            "untuk pengambilan keputusan manajemen."
        )

        _pdf.ln(20)

        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(0.5)
        _pdf.line(100, _pdf.get_y(), 180, _pdf.get_y())
        _pdf.ln(5)

        _pdf.set_font("Helvetica", "B", 12)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 8, "Rei — Analis SO", align="R", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font("Helvetica", "", 10)
        _pdf.set_text_color(*_theme.TEXT_MUTED)
        _pdf.cell(0, 6, "Dashboard SO Toko C383", align="R", new_x="LMARGIN", new_y="NEXT")

        # Output
        _pdf_output = _pdf.output()
        return bytes(_pdf_output)

    except Exception as _e:
        print(f"[REI EXPORT PDF ERROR] {_e}")
        import traceback
        print(traceback.format_exc())
        return None


def _generate_rekomendasi(data_context):
    """Generate rekomendasi dari data."""
    _rekom = []
    _lost = data_context.get("lost_sales", {})
    _top_rak = data_context.get("top_rak", [])

    # Rekomendasi 1: Verifikasi rak top minus
    if _top_rak:
        _rak_names = ", ".join([r.get("rak_id", "-") for r in _top_rak[:3]])
        _rekom.append({
            "title": f"Verifikasi Prosedur Scan pada Rak {_rak_names}",
            "detail": f"Lakukan spot-check pada rak dengan selisih tertinggi. "
                      f"Periksa apakah ada indikasi scan error atau masalah penempatan."
        })

    # Rekomendasi 2: Shrinkage rate
    if _lost.get("shrinkage", 0) > 2:
        _rekom.append({
            "title": "Evaluasi Menyeluruh Shrinkage",
            "detail": f"Shrinkage rate {_lost.get('shrinkage', 0):.2f}% di atas benchmark 2%. "
                      f"Perlu review SOP, training PIC, dan audit proses."
        })
    else:
        _rekom.append({
            "title": "Pertahankan Prosedur Existing",
            "detail": f"Shrinkage rate {_lost.get('shrinkage', 0):.2f}% dalam toleransi. "
                      f"Pertahankan prosedur saat ini dan lakukan monitoring berkala."
        })

    # Rekomendasi 3: Cross-check
    _rekom.append({
        "title": "Cross-check Data Penjualan dengan POS",
        "detail": "Bandingkan data SO dengan data penjualan POS untuk mendeteksi "
                  "anomali dan memastikan akurasi data."
    })

    return _rekom