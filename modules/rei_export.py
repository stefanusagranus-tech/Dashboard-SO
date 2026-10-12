"""
Rei Export — PDF Generator (Jurnal Ilmiah Style)
=================================================
Generate PDF laporan analisis SO dengan gaya jurnal ilmiah profesional.

Font: Full DejaVu Family
- Serif Condensed (Bold) → Judul
- Sans Condensed → Body text
- Sans Mono → Angka & tabel

Dependencies: fpdf2>=2.8.0, matplotlib
Style: Halloween theme (ungu/emas)
"""

import os
import io
from datetime import datetime
from zoneinfo import ZoneInfo

# === MATPLOTLIB SETUP ===
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Set matplotlib pakai DejaVu
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9
plt.rcParams["axes.titlesize"] = 11
plt.rcParams["axes.labelsize"] = 9

# === FPDF ===
from fpdf import FPDF, FontFace


# =========================================================
# KONFIGURASI STYLE
# =========================================================
class ReiTheme:
    """Theme colors — Halloween style"""
    BG_DARK = (20, 12, 35)
    PURPLE = (76, 29, 149)
    GOLD = (232, 177, 137)
    SAGE = (127, 185, 155)
    TEXT_LIGHT = (245, 230, 211)
    TEXT_MUTED = (168, 155, 142)
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
# CUSTOM PDF CLASS — Full DejaVu Family
# =========================================================
class ReiPDF(FPDF):
    """PDF class dengan header & footer custom — Full DejaVu family."""

    def __init__(self, title="Laporan Analisis Stock Opname", theme=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.rei_title = title
        self.theme = theme or ReiTheme()
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

        # === PATH FONTS ===
        _font_dir = os.path.join(os.path.dirname(__file__), "..", "fonts")

        # === REGISTER SEMUA FONT ===
        _fonts = {
            # Serif — buat judul & sub-judul
            ("Serif", ""):    "DejaVuSerifCondensed.ttf",
            ("Serif", "B"):   "DejaVuSerifCondensed-Bold.ttf",
            ("Serif", "I"):   "DejaVuSerif-Italic.ttf",
            ("Serif", "BI"):  "DejaVuSerif-BoldItalic.ttf",
            # Sans — buat body text
            ("Sans", ""):     "DejaVuSansCondensed.ttf",
            ("Sans", "B"):    "DejaVuSansCondensed-Bold.ttf",
            ("Sans", "I"):    "DejaVuSans-Oblique.ttf",
            ("Sans", "BI"):   "DejaVuSans-BoldOblique.ttf",
            # Mono — buat angka & tabel
            ("Mono", ""):     "DejaVuSansMono.ttf",
            ("Mono", "B"):    "DejaVuSansMono-Bold.ttf",
            ("Mono", "I"):    "DejaVuSansMono-Oblique.ttf",
            ("Mono", "BI"):   "DejaVuSansMono-BoldOblique.ttf",
        }

        _loaded = 0
        for (_family, _style), _filename in _fonts.items():
            _path = os.path.join(_font_dir, _filename)
            if os.path.exists(_path):
                try:
                    self.add_font(_family, _style, _path)
                    _loaded += 1
                except Exception as _e:
                    print(f"[REI PDF] Gagal load {_filename}: {_e}")

        print(f"[REI PDF] Loaded {_loaded}/{len(_fonts)} fonts")

        # === DEFAULT FONT SET ===
        self.font_title = "Serif"
        self.font_body = "Sans"
        self.font_mono = "Mono"

        if _loaded == 0:
            self.font_title = "Helvetica"
            self.font_body = "Helvetica"
            self.font_mono = "Courier"

    def header(self):
        """Header tiap halaman."""
        if self.page_no() == 1:
            return

        # Bar header
        self.set_fill_color(*self.theme.PURPLE)
        self.rect(0, 0, 210, 18, "F")

        # Title header
        self.set_y(5)
        self.set_font(self.font_mono, "B", 9)
        self.set_text_color(*self.theme.GOLD)
        self.cell(0, 8, "LAPORAN ANALISIS STOCK OPNAME — TOKO C383", align="L")

        # Page number di kanan
        self.set_y(5)
        self.set_font(self.font_mono, "", 9)
        self.set_text_color(*self.theme.TEXT_LIGHT)
        self.cell(0, 8, f"Halaman {self.page_no()}", align="R")

        self.ln(15)

    def footer(self):
        """Footer tiap halaman."""
        self.set_y(-15)
        self.set_font(self.font_mono, "I", 8)
        self.set_text_color(*self.theme.TEXT_MUTED)

        # Garis atas footer
        self.set_draw_color(*self.theme.GOLD)
        self.set_line_width(0.3)
        self.line(15, self.get_y() - 2, 195, self.get_y() - 2)

        self.cell(0, 10, "Dashboard SO Toko C383 — Rei (AI Analis)", align="C")


# =========================================================
# CHART GENERATOR
# =========================================================
def _chart_to_image(fig, dpi=200):
    """Convert matplotlib figure ke BytesIO image."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="#140C23", edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


def _create_trend_chart(chart_data):
    """Bikin bar chart trend SO."""
    if not chart_data:
        return None

    fig, ax = plt.subplots(figsize=(6, 3.5), facecolor="#140C23")

    _labels = [str(c.get("tanggal", ""))[-5:] for c in chart_data]
    _values = [float(c.get("nominal", 0)) for c in chart_data]

    _colors = ["#7FB99B" if v >= 0 else "#E8B189" for v in _values]

    _bars = ax.bar(_labels, _values, color=_colors,
                   edgecolor="#140C23", linewidth=1.5)

    ax.axhline(y=0, color="#A89B8E", linewidth=0.8, linestyle="--", alpha=0.5)

    ax.set_facecolor("#1E143C")
    ax.set_title("Trend Selisih SO (7 Hari Terakhir)", color="#E8B189",
                 fontsize=11, weight="bold", pad=10)
    ax.set_ylabel("Nominal (Rp)", color="#F5E6D3", fontsize=9)
    ax.tick_params(axis="x", colors="#F5E6D3", labelsize=8)
    ax.tick_params(axis="y", colors="#F5E6D3", labelsize=8)

    ax.grid(axis="y", color="#A89B8E", alpha=0.15, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#A89B8E")
    ax.spines["left"].set_color("#A89B8E")

    for _bar, _val in zip(_bars, _values):
        _y = _val + (max(_values) * 0.03 if _val >= 0 else min(_values) * 0.08)
        _color = "#7FB99B" if _val >= 0 else "#E8B189"
        ax.text(_bar.get_x() + _bar.get_width()/2, _y,
                fmt_rp_short(_val), ha="center",
                va="bottom" if _val >= 0 else "top",
                color=_color, fontsize=7, weight="bold")

    fig.tight_layout()
    return _chart_to_image(fig)


# =========================================================
# REKOMENDASI GENERATOR
# =========================================================
def _generate_rekomendasi(data_context):
    """Generate rekomendasi dari data."""
    _rekom = []
    _lost = data_context.get("lost_sales", {})
    _top_rak = data_context.get("top_rak", [])

    if _top_rak:
        _rak_names = ", ".join([r.get("rak_id", "-") for r in _top_rak[:3]])
        _rekom.append({
            "title": f"Verifikasi Prosedur Scan pada Rak {_rak_names}",
            "detail": f"Lakukan spot-check pada rak dengan selisih tertinggi. "
                      f"Periksa apakah ada indikasi scan error atau masalah penempatan."
        })

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

    _rekom.append({
        "title": "Cross-check Data Penjualan dengan POS",
        "detail": "Bandingkan data SO dengan data penjualan POS untuk mendeteksi "
                  "anomali dan memastikan akurasi data."
    })

    return _rekom


# =========================================================
# MAIN EXPORT FUNCTION
# =========================================================
def generate_rei_pdf(data_context):
    """Generate PDF laporan Rei dari data context."""
    try:
        _theme = ReiTheme()
        _pdf = ReiPDF(theme=_theme)
        _periode = data_context.get("periode", "-")
        _tgl_cetak = _now_jkt().strftime("%d %B %Y, %H:%M WIB")

        # =====================================================
        # HALAMAN 1 — COVER
        # =====================================================
        _pdf.add_page()

        _pdf.set_fill_color(*_theme.BG_DARK)
        _pdf.rect(0, 0, 210, 297, "F")

        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(1.5)
        _pdf.rect(10, 10, 190, 277)

        _pdf.set_draw_color(*_theme.SAGE)
        _pdf.set_line_width(0.5)
        _pdf.rect(13, 13, 184, 271)

        _pdf.ln(50)

        _pdf.set_font(_pdf.font_title, "B", 28)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 15, "LAPORAN ANALISIS", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 15, "STOCK OPNAME", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(5)

        _pdf.set_font(_pdf.font_body, "", 14)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.cell(0, 10, "Toko C383 — Karang Satria", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(3)

        _pdf.set_font(_pdf.font_body, "I", 12)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 10, f"Periode: {_periode}", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(30)

        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(0.8)
        _pdf.line(60, _pdf.get_y(), 150, _pdf.get_y())
        _pdf.ln(20)

        _pdf.set_font(_pdf.font_body, "", 11)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.cell(0, 8, "Disusun oleh:", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.set_font(_pdf.font_title, "B", 14)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 10, "Rei — Analis SO (AI-3)", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(5)

        _pdf.set_font(_pdf.font_mono, "", 9)
        _pdf.set_text_color(*_theme.TEXT_MUTED)
        _pdf.cell(0, 6, f"Tanggal Cetak: {_tgl_cetak}", align="C", new_x="LMARGIN", new_y="NEXT")

        # =====================================================
        # HALAMAN 2 — EXECUTIVE SUMMARY
        # =====================================================
        _pdf.add_page()
        _pdf.set_text_color(*_theme.TEXT_LIGHT)

        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "1. EXECUTIVE SUMMARY", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

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

            _pdf.set_fill_color(*_theme.PURPLE)
            _pdf.rect(_x, _y, _box_w, _box_h, "F")

            _pdf.set_draw_color(*_color)
            _pdf.set_line_width(0.8)
            _pdf.rect(_x, _y, _box_w, _box_h)

            _pdf.set_xy(_x, _y + 3)
            _pdf.set_font(_pdf.font_mono, "", 8)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.cell(_box_w, 5, _label, align="C")

            _pdf.set_xy(_x, _y + 10)
            _pdf.set_font(_pdf.font_mono, "B", 13)
            _pdf.set_text_color(*_color)
            _pdf.cell(_box_w, 8, _value, align="C")

        _pdf.ln(_box_h + 8)

        _pdf.set_font(_pdf.font_title, "B", 12)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 8, "Status BTSB & NSB", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(2)

        _status_color = _theme.RED if _btsb.get("status") == "PERLU PERHATIAN" else _theme.GREEN

        _pdf.set_font(_pdf.font_mono, "", 10)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.cell(0, 6, f"Net Sales: {fmt_rp(_btsb.get('net_sales', 0))}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 6, f"BTSB (0,15%): {fmt_rp(_btsb.get('btsb', 0))}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 6, f"Total Selisih: {fmt_rp(abs(_btsb.get('total_selisih', 0)))}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(0, 6, f"NSB: {fmt_rp(_btsb.get('nsb', 0))}", new_x="LMARGIN", new_y="NEXT")

        _pdf.set_font(_pdf.font_mono, "B", 10)
        _pdf.set_text_color(*_status_color)
        _pdf.cell(0, 8, f"Status: {_btsb.get('status', '-')}", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(5)

        # =====================================================
        # HALAMAN 3 — METODOLOGI
        # =====================================================
        _pdf.add_page()

        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "2. METODOLOGI", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        _metodologi = [
            ("2.1 Sumber Data",
             f"Data diambil dari sistem SO periode {_periode}. "
             f"Total rak: {data_context.get('rekap', {}).get('total_rak', 0)}. "
             f"Total item: {data_context.get('rekap', {}).get('total_item', 0)}."),
            ("2.2 Metrik yang Digunakan",
             "1. Gross Lost Sales = total nilai absolut item dengan qty_var < 0.\n"
             "2. Net Lost Sales = nilai absolut dari total nominal_adjust semua item.\n"
             "3. Shrinkage Rate = (Net Lost Sales / Net Sales) × 100 persen."),
            ("2.3 Batasan",
             "1. Data hanya dari SO periode ini.\n"
             "2. Tidak ada data benchmark internal Alfamart.\n"
             "3. Analisis berbasis pola data yang tersedia."),
        ]

        for _title, _content in _metodologi:
            _pdf.set_font(_pdf.font_body, "B", 11)
            _pdf.set_text_color(*_theme.SAGE)
            _pdf.cell(0, 8, _title, new_x="LMARGIN", new_y="NEXT")
            _pdf.set_font(_pdf.font_body, "", 10)
            _pdf.set_text_color(*_theme.TEXT_LIGHT)
            _pdf.multi_cell(0, 6, _content)
            _pdf.ln(4)

        # =====================================================
        # HALAMAN 4 — CHART & TREND
        # =====================================================
        _pdf.add_page()

        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "3. ANALISIS TREND", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        _chart_data = data_context.get("chart_data", [])
        if _chart_data:
            _trend_img = _create_trend_chart(_chart_data)
            if _trend_img:
                _pdf.image(_trend_img, x=20, w=170)
                _pdf.ln(3)

        _pdf.set_font(_pdf.font_body, "B", 11)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 8, "Interpretasi:", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font(_pdf.font_body, "", 10)
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

        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "4. TOP ITEM & RAK", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        _pdf.set_font(_pdf.font_body, "B", 11)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 8, "4.1 Top 10 Item Selisih", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(2)

        _top_items = data_context.get("top_items", [])
        if _top_items:
            _headings = FontFace(
                family=_pdf.font_title,
                emphasis="BOLD",
                color=(232, 177, 137),
                fill_color=(76, 29, 149),
                size_pt=9,
            )
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
            _pdf.set_font(_pdf.font_body, "I", 10)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.multi_cell(0, 6, "Data tidak tersedia.")

        _pdf.ln(8)

        _pdf.set_font(_pdf.font_body, "B", 11)
        _pdf.set_text_color(*_theme.SAGE)
        _pdf.cell(0, 8, "4.2 Top 5 Rak Minus", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(2)

        _top_rak = data_context.get("top_rak", [])
        if _top_rak:
            _headings2 = FontFace(
                family=_pdf.font_title,
                emphasis="BOLD",
                color=(232, 177, 137),
                fill_color=(76, 29, 149),
                size_pt=9,
            )
            with _pdf.table(
                col_widths=(30, 40, 45, 30),
                headings_style=_headings2,
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
            _pdf.set_font(_pdf.font_body, "I", 10)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.multi_cell(0, 6, "Data tidak tersedia.")

  # =====================================================
        # HALAMAN 6 — REKOMENDASI
        # =====================================================
        _pdf.add_page()

        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "5. REKOMENDASI AUDIT", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(3)

        _rekomendasi = _generate_rekomendasi(data_context)
        for _i, _rek in enumerate(_rekomendasi, 1):
            _pdf.set_font(_pdf.font_body, "B", 11)
            _pdf.set_text_color(*_theme.SAGE)
            _pdf.cell(0, 7, f"{_i}. {_rek.get('title', '-')}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_font(_pdf.font_body, "", 10)
            _pdf.set_text_color(*_theme.TEXT_LIGHT)
            _pdf.multi_cell(0, 6, _rek.get("detail", "-"))
            _pdf.ln(3)

        # =====================================================
        # HALAMAN 7 — PENUTUP
        # =====================================================
        _pdf.add_page()

        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "6. PENUTUP", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(5)

        _pdf.set_font(_pdf.font_body, "", 11)
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

        _pdf.set_font(_pdf.font_title, "B", 12)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 8, "Rei — Analis SO", align="R", new_x="LMARGIN", new_y="NEXT")

        _pdf.set_font(_pdf.font_mono, "", 9)
        _pdf.set_text_color(*_theme.TEXT_MUTED)
        _pdf.cell(0, 6, "Dashboard SO Toko C383", align="R", new_x="LMARGIN", new_y="NEXT")

        # === OUTPUT ===
        _pdf_output = _pdf.output()
        return bytes(_pdf_output)

    except Exception as _e:
        print(f"[REI EXPORT PDF ERROR] {_e}")
        import traceback
        print(traceback.format_exc())
        return None