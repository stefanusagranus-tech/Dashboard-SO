"""
Rei Export — PDF Generator (Jurnal SINTA Style)
================================================
Layout 5 halaman, compact, SINTA compliant.

Standar SINTA:
- Tabel: garis horizontal saja, judul di atas tabel
- Gambar: judul di bawah gambar, 300 dpi
- Warna: kontras, netral

BTSB Alfamart: 0,15% dari Net Sales
Shrinkage Rate = Total Selisih / Net Sales × 100%

Dependencies: fpdf2>=2.8.0, matplotlib
"""

import os
import io
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9

from fpdf import FPDF, FontFace


# =========================================================
# THEME
# =========================================================
class ReiTheme:
    BG_DARK = (20, 12, 35)
    PURPLE = (76, 29, 149)
    GOLD = (232, 177, 137)
    SAGE = (127, 185, 155)
    TEXT_LIGHT = (245, 230, 211)
    TEXT_MUTED_LIGHT = (168, 155, 142)
    TEXT_DARK = (40, 40, 50)
    TEXT_MUTED_DARK = (110, 110, 120)
    RED = (200, 50, 50)
    GREEN = (40, 160, 80)
    # Tabel SINTA — gradasi abu-abu
    TABLE_HEADER_BG = (230, 230, 230)
    TABLE_HEADER_TEXT = (0, 0, 0)
    TABLE_BORDER = (100, 100, 100)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _clean_text(text):
    if not text:
        return "-"
    return str(text).replace("&#39;", "'").replace("&amp;", "&").replace("&quot;", '"')


def fmt_rp(value):
    try:
        return f"Rp {int(float(value)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp_short(value):
    """Format Rupiah singkat: Rp 1,2 jt / Rp 399 rb"""
    try:
        _v = abs(float(value))
        if _v >= 1_000_000_000:
            return f"{_v/1_000_000_000:.1f} M"
        if _v >= 1_000_000:
            return f"{_v/1_000_000:.1f} jt"
        if _v >= 1_000:
            return f"{_v/1_000:.0f} rb"
        return f"{int(_v)}"
    except Exception:
        return "0"


def hitung_shrinkage_rate(total_selisih, net_sales):
    """Shrinkage Rate = Total Selisih / Net Sales × 100%"""
    if net_sales <= 0:
        return 0
    return abs(total_selisih) / net_sales * 100


def status_shrinkage(shrinkage_rate, btsb_pct=0.15):
    """Status berdasarkan BTSB 0,15%."""
    if shrinkage_rate > btsb_pct:
        return "PERHATIAN"
    return "AMAN"

def fmt_rp_neg(value):
    """Format Rupiah dengan tanda minus mengikuti data asli.
    
    Contoh:
    - fmt_rp_neg(-59403) → "-Rp 59.403"
    - fmt_rp_neg(59403)  → "Rp 59.403"
    """
    try:
        _v = float(value)
        if _v < 0:
            return f"-Rp {int(abs(_v)):,}".replace(",", ".")
        return f"Rp {int(_v):,}".replace(",", ".")
    except Exception:
        return "Rp 0"
# =========================================================
# PDF CLASS
# =========================================================
class ReiPDF(FPDF):
    def __init__(self, theme=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.theme = theme or ReiTheme()
        self.set_margins(18, 15, 18)
        self.set_auto_page_break(auto=True, margin=18)

        _font_dir = os.path.join(os.path.dirname(__file__), "..", "fonts")
        _fonts = {
            ("Serif", ""):    "DejaVuSerifCondensed.ttf",
            ("Serif", "B"):   "DejaVuSerifCondensed-Bold.ttf",
            ("Serif", "I"):   "DejaVuSerif-Italic.ttf",
            ("Serif", "BI"):  "DejaVuSerif-BoldItalic.ttf",     # ← tambah
            ("Sans", ""):     "DejaVuSansCondensed.ttf",
            ("Sans", "B"):    "DejaVuSansCondensed-Bold.ttf",
            ("Sans", "I"):    "DejaVuSans-Oblique.ttf",
            ("Sans", "BI"):   "DejaVuSans-BoldOblique.ttf",     # ← tambah
            ("Mono", ""):     "DejaVuSansMono.ttf",
            ("Mono", "B"):    "DejaVuSansMono-Bold.ttf",
            ("Mono", "I"):    "DejaVuSansMono-Oblique.ttf",     # ← tambah
            ("Mono", "BI"):   "DejaVuSansMono-BoldOblique.ttf", # ← tambah
        }

        _loaded = 0
        for (_fam, _style), _fn in _fonts.items():
            _p = os.path.join(_font_dir, _fn)
            if os.path.exists(_p):
                try:
                    self.add_font(_fam, _style, _p)
                    _loaded += 1
                except Exception as _e:
                    print(f"[REI PDF] Gagal load {_fn}: {_e}")

        print(f"[REI PDF] Loaded {_loaded}/{len(_fonts)} fonts")

        self.font_title = "Serif"
        self.font_body = "Sans"
        self.font_mono = "Mono"

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*self.theme.PURPLE)
        self.rect(0, 0, 210, 12, "F")
        self.set_y(3)
        self.set_font(self.font_mono, "B", 8)
        self.set_text_color(*self.theme.GOLD)
        self.cell(0, 6, "ANALISIS STOCK OPNAME - TOKO C383", align="L")
        self.set_y(3)
        self.set_font(self.font_mono, "", 8)
        self.cell(0, 6, f"Halaman {self.page_no()}", align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font(self.font_mono, "I", 7)
        self.set_text_color(*self.theme.TEXT_MUTED_DARK)
        self.set_draw_color(*self.theme.GOLD)
        self.set_line_width(0.3)
        self.line(18, self.get_y() - 2, 192, self.get_y() - 2)
        self.cell(0, 8, "Dashboard SO Toko C383 - Rei (AI Analis)", align="C")

    def section_title(self, text, space_before=3):
        self.ln(space_before)
        self.set_font(self.font_title, "B", 12)
        self.set_text_color(*self.theme.GOLD)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def sub_title(self, text, space_before=3):
        self.ln(space_before)
        self.set_font(self.font_body, "B", 10)
        self.set_text_color(*self.theme.SAGE)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text, line_height=4.5):
        self.set_font(self.font_body, "", 9)
        self.set_text_color(*self.theme.TEXT_DARK)
        self.multi_cell(0, line_height, text)
        
# =========================================================
# CHART — STANDAR SINTA
# =========================================================
def _chart_to_image(fig, dpi=300):
    """Convert matplotlib figure ke BytesIO — 300 dpi sesuai SINTA"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="#FFFFFF", edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


def _create_trend_chart(chart_data, title=None):
    """Bikin bar chart sesuai standar jurnal SINTA."""
    if not chart_data:
        return None

    _n_hari = len(chart_data)
    if title is None:
        title = f"Tren Selisih SO {_n_hari} Hari Terakhir"

    fig, ax = plt.subplots(figsize=(6, 3), facecolor="#FFFFFF")

    _labels = [str(c.get("tanggal", ""))[-5:] for c in chart_data]
    _values = [float(c.get("nominal", 0)) for c in chart_data]
    _colors = ["#2E86AB" if v >= 0 else "#C73E1D" for v in _values]

    _bars = ax.bar(_labels, _values, color=_colors,
                   edgecolor="#000000", linewidth=0.5, width=0.6)

    ax.axhline(y=0, color="#000000", linewidth=0.8)
    ax.set_xlabel("Tanggal", color="#000000", fontsize=9, labelpad=8)
    ax.set_ylabel("Nominal (Rp)", color="#000000", fontsize=9)
    ax.set_facecolor("#FFFFFF")
    ax.tick_params(axis="x", colors="#000000", labelsize=8)
    ax.tick_params(axis="y", colors="#000000", labelsize=8)
    ax.grid(axis="y", color="#CCCCCC", alpha=0.7, linewidth=0.5)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_color("#000000")
        spine.set_linewidth(0.5)

    for _bar, _val in zip(_bars, _values):
        _y = _val + (max(_values) * 0.03 if _val >= 0 else min(_values) * 0.08)
        ax.text(_bar.get_x() + _bar.get_width()/2, _y,
                fmt_rp_short(_val), ha="center",
                va="bottom" if _val >= 0 else "top",
                color="#000000", fontsize=7, weight="bold")

    fig.tight_layout()
    return _chart_to_image(fig)


# =========================================================
# REKOMENDASI
# =========================================================
def _generate_rekomendasi(data_context):
    _rekom = []
    _lost = data_context.get("lost_sales", {})
    _top_rak = data_context.get("top_rak", [])

    if _top_rak:
        _rak_names = ", ".join([r.get("rak_id", "-") for r in _top_rak[:3]])
        _rekom.append({
            "title": f"Verifikasi Prosedur Scan pada Rak {_rak_names}",
            "detail": "Lakukan spot-check pada rak dengan selisih tertinggi. "
                      "Periksa indikasi scan error atau masalah penempatan.",
        })

    if _lost.get("shrinkage", 0) > 0.15:
        _rekom.append({
            "title": "Evaluasi Menyeluruh Shrinkage",
            "detail": f"Shrinkage Rate {_lost.get('shrinkage', 0):.4f}% di atas BTSB 0,15%. "
                      f"Perlu review SOP, training PIC, dan audit proses.",
        })
    else:
        _rekom.append({
            "title": "Pertahankan Prosedur Existing",
            "detail": f"Shrinkage Rate {_lost.get('shrinkage', 0):.4f}% dalam toleransi. "
                      f"Monitoring berkala tetap diperlukan.",
        })

    _rekom.append({
        "title": "Cross-check Data Penjualan dengan POS",
        "detail": "Bandingkan data SO dengan data penjualan POS untuk deteksi anomali.",
    })

    return _rekom
    
# =========================================================
# MAIN EXPORT — PART 1
# =========================================================
def generate_rei_pdf(data_context):
    try:
        _theme = ReiTheme()
        _pdf = ReiPDF(theme=_theme)
        _periode = data_context.get("periode", "-")
        _tgl = _now_jkt().strftime("%d %B %Y, %H:%M WIB")

        _lost = data_context.get("lost_sales", {})
        _btsb = data_context.get("btsb", {})
        _rekap = data_context.get("rekap", {})
        _top_rak = data_context.get("top_rak", [])
        _top_items = data_context.get("top_items", [])

        _total_selisih_abs = abs(_btsb.get("total_selisih", 0))
        _net_sales = _lost.get("net_sales", 0)
        _sh = hitung_shrinkage_rate(_total_selisih_abs, _net_sales)
        _status = status_shrinkage(_sh)

        # ===== HAL 1: COVER =====
        _pdf.add_page()
        _pdf.set_fill_color(*_theme.BG_DARK)
        _pdf.rect(0, 0, 210, 297, "F")
        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(1.2)
        _pdf.rect(15, 15, 180, 267)

        _pdf.ln(75)
        _pdf.set_font(_pdf.font_title, "B", 22)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "ANALISIS STOCK OPNAME", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.cell(0, 10, "Toko C383 - Karang Satria", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(8)
        _pdf.set_draw_color(*_theme.SAGE)
        _pdf.line(70, _pdf.get_y(), 140, _pdf.get_y())
        _pdf.ln(10)
        _pdf.set_font(_pdf.font_body, "", 11)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.cell(0, 8, "Periode Analisis:", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font(_pdf.font_mono, "B", 12)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 8, _periode, align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(25)
        _pdf.set_font(_pdf.font_body, "", 10)
        _pdf.set_text_color(*_theme.TEXT_MUTED_LIGHT)
        _pdf.cell(0, 7, "Disusun oleh: Rei - Analis SO (AI-3)", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font(_pdf.font_mono, "", 9)
        _pdf.cell(0, 7, f"Dicetak: {_tgl}", align="C", new_x="LMARGIN", new_y="NEXT")

        # ===== HAL 2: ABSTRAK + PENDAHULUAN + METODE =====
        _pdf.add_page()
        _pdf.section_title("ABSTRAK", space_before=0)

        _abstrak = (
            f"Analisis Stock Opname (SO) ini bertujuan mengukur akurasi stok dan mengidentifikasi "
            f"nilai kehilangan (shrinkage) di Toko C383 Karang Satria periode {_periode}. "
            f"Metode meliputi perhitungan Gross Lost Sales, Net Lost Sales, dan Shrinkage Rate "
            f"berdasarkan {_rekap.get('total_item', 0)} item dari {_rekap.get('total_rak', 0)} rak. "
            f"Hasil: Net Sales {fmt_rp(_net_sales)}, Total Selisih {fmt_rp(_total_selisih_abs)}, "
            f"Shrinkage Rate {_sh:.4f}%. Status: {_status}. "
            f"Rekomendasi audit disusun untuk mengurangi risiko shrinkage periode mendatang."
        )
        _pdf.body_text(_abstrak)
        _pdf.ln(2)
        _pdf.set_font(_pdf.font_body, "I", 8)
        _pdf.set_text_color(*_theme.TEXT_MUTED_DARK)
        _pdf.cell(0, 5, "Kata kunci: stock opname, shrinkage, lost sales, analisis retail, BTSB, NSB",
                  new_x="LMARGIN", new_y="NEXT")

        _pdf.section_title("1. PENDAHULUAN")
        _pdf.body_text(
            f"Stock Opname (SO) adalah proses penghitungan fisik stok untuk memverifikasi akurasi "
            f"data antara catatan sistem dan kondisi aktual. Di industri retail, akurasi stok "
            f"menjadi kunci utama menjaga ketersediaan produk sekaligus meminimalkan nilai "
            f"kehilangan (shrinkage) yang berdampak langsung pada profitabilitas."
        )
        _pdf.ln(1)
        _pdf.body_text(
            f"Toko C383 Karang Satria melaksanakan SO secara berkala. Analisis ini bertujuan: "
            f"(1) mengukur akurasi stok periode {_periode}, (2) menghitung Gross dan Net Lost Sales, "
            f"(3) mengidentifikasi pola selisih berdasarkan rak dan PIC, serta "
            f"(4) memberikan rekomendasi audit yang actionable."
        )

        _pdf.section_title("2. METODE")
        _pdf.sub_title("2.1 Sumber Data")
        _pdf.body_text(
            f"Data dari sistem SO Toko C383 periode {_periode}. "
            f"Total rak: {_rekap.get('total_rak', 0)}. Total item: {_rekap.get('total_item', 0)}."
        )

        _pdf.sub_title("2.2 Metrik yang Digunakan")
        _pdf.body_text(
            "1. Gross Lost Sales = total nilai absolut item dengan qty_var < 0.\n"
            "2. Net Lost Sales = nilai absolut dari total nominal_adjust semua item.\n"
            "3. Total Selisih = nilai absolut dari total nominal_adjust (net).\n"
            "4. Shrinkage Rate = (Total Selisih / Net Sales) x 100 persen.\n"
            "5. BTSB = Batas Toleransi Selisih Barang (0,15% dari Net Sales).\n"
            "6. NSB = Nilai Selisih Barang (selisih di atas BTSB yang dibebankan)."
        )

        _pdf.sub_title("2.3 Batasan")
        _pdf.body_text(
            "1. Data hanya dari SO periode ini.\n"
            "2. Benchmark internal Alfamart belum tersedia.\n"
            "3. Analisis berbasis pola data yang tersedia."
        )

        # Lanjut ke Part 2
        return _rei_pdf_part2(
            _pdf, _theme, _lost, _btsb, _sh, _status,
            _top_rak, _top_items, _btsb.get("nsb", 0), _total_selisih_abs,
            _net_sales, data_context  # ← TAMBAH INI
        )
    
    except Exception as _e:
        print(f"[REI PDF PART2 ERROR] {_e}")
        import traceback
        print(traceback.format_exc())
        raise  # ← TAMBAH INI

# =========================================================
# MAIN EXPORT — PART 2 (Halaman 3-5)
# =========================================================
def _rei_pdf_part2(_pdf, _theme, _lost, _btsb, _sh, _status,
                   _top_rak, _top_items, _nsb_val, _total_selisih_abs,
                   _net_sales, data_context):
    try:
        # ===== HAL 3: HASIL — RINGKASAN + TOP 10 RAK =====
        _pdf.add_page()
        _pdf.section_title("3. HASIL", space_before=0)

        # ==== 3.1 RINGKASAN METRIK ====
        _pdf.sub_title("3.1 Ringkasan Metrik", space_before=2)
        _pdf.set_font(_pdf.font_body, "B", 8)
        _pdf.set_text_color(60, 60, 60)
        _pdf.cell(0, 4, "Tabel 1. Ringkasan Metrik Stock Opname",
                  new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(1)

        _pdf.set_fill_color(255, 255, 255)
        _pdf.set_text_color(0, 0, 0)
        _pdf.set_draw_color(100, 100, 100)

        _headings = FontFace(
            family=_pdf.font_title, emphasis="BOLD",
            color=(0, 0, 0),
            fill_color=(230, 230, 230),
            size_pt=8,
        )

        with _pdf.table(
            col_widths=(60, 65, 45),
            headings_style=_headings,
            line_height=5.5,
            first_row_as_headings=True,
            borders_layout="HORIZONTAL_LINES",
            cell_fill_color=(255, 255, 255),
            cell_fill_mode="ALL",
            text_align=("LEFT", "RIGHT", "CENTER"),
            padding=1.5,
        ) as _t:
            _row = _t.row()
            _row.cell("Metrik"); _row.cell("Nilai"); _row.cell("Status")
            _row = _t.row()
            _row.cell("Net Sales"); _row.cell(fmt_rp(_net_sales)); _row.cell("-")
            _row = _t.row()
            _row.cell("Gross Lost Sales"); _row.cell(fmt_rp(_lost.get("gross", 0))); _row.cell("-")
            _row = _t.row()
            _row.cell("Net Lost Sales"); _row.cell(fmt_rp(_lost.get("net", 0))); _row.cell("-")
            _row = _t.row()
            _row.cell("Total Selisih"); _row.cell(fmt_rp(_total_selisih_abs)); _row.cell("-")
            _row = _t.row()
            _row.cell("Shrinkage Rate"); _row.cell(f"{_sh:.4f}%")
            _row.cell("<= 0,15%" if _sh <= 0.15 else "> 0,15%")
            _row = _t.row()
            _row.cell("BTSB (0,15%)"); _row.cell(fmt_rp(_btsb.get("btsb", 0))); _row.cell("-")
            _row = _t.row()
            _row.cell("NSB"); _row.cell(fmt_rp(_btsb.get("nsb", 0)))
            _row.cell("DIBEBANKAN" if _btsb.get("nsb", 0) > 0 else "NOL")

            # ==== 3.2 TOP 10 RAK SELISIH TERTINGGI ====
            _pdf.sub_title("3.2 Top 10 Rak Selisih Tertinggi", space_before=6)
            _pdf.set_font(_pdf.font_body, "B", 8)
            _pdf.set_text_color(60, 60, 60)
            _pdf.cell(0, 4, "Tabel 2. Top 10 Rak dengan Selisih Tertinggi",
                      new_x="LMARGIN", new_y="NEXT")
            _pdf.ln(1)
            
            if _top_rak:
                # === HITUNG TOTAL ===
                _total_rak_nominal = sum(abs(_r.get("total", 0)) for _r in _top_rak[:10])
            
                with _pdf.table(
                    col_widths=(35, 50, 60),   # ← cuma 3 kolom
                    headings_style=_headings,
                    line_height=5.5,
                    first_row_as_headings=True,
                    borders_layout="HORIZONTAL_LINES",
                    cell_fill_color=(255, 255, 255),
                    cell_fill_mode="ALL",
                    text_align=("CENTER", "LEFT", "RIGHT"),
                    padding=1.2,
                ) as _t:
                    _row = _t.row()
                    _row.cell("Rak"); _row.cell("PIC"); _row.cell("Nominal")
                    for _r in _top_rak[:10]:
                        _row = _t.row()
                        _row.cell(str(_r.get("rak_id", "-")))
                        _row.cell(str(_r.get("pic", "-")))
                        _row.cell(fmt_rp_neg(_r.get("total", 0)))
                        
                    # === BARIS TOTAL ===
                    _row = _t.row()
                    _row.cell("TOTAL")
                    _row.cell("")
                    _row.cell(f"-Rp {int(_total_rak_nominal):,}".replace(",", "."))

        # ===== HAL 4: TOP 10 ITEM + CHART =====
        _pdf.add_page()

        # ==== 3.3 TOP 10 ITEM SELISIH TERBESAR ====
        _pdf.sub_title("3.3 Top 10 Item Selisih Terbesar", space_before=0)
        _pdf.set_font(_pdf.font_body, "B", 8)
        _pdf.set_text_color(60, 60, 60)
        _pdf.cell(0, 4, "Tabel 3. Top 10 Item dengan Selisih Terbesar",
                  new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(1)

        if _top_items:
            with _pdf.table(
                col_widths=(75, 20, 35, 30),
                headings_style=_headings,
                line_height=5,
                first_row_as_headings=True,
                borders_layout="HORIZONTAL_LINES",
                cell_fill_color=(255, 255, 255),
                cell_fill_mode="ALL",
                text_align=("LEFT", "CENTER", "RIGHT", "CENTER"),
                padding=1.2,
            ) as _t:
                _row = _t.row()
                _row.cell("Nama Produk"); _row.cell("Rak"); _row.cell("Nominal"); _row.cell("PIC")
                for _it in _top_items[:10]:
                    _row = _t.row()
                    _row.cell(_clean_text(_it.get("nama_produk", "-"))[:34])
                    _row.cell(str(_it.get("rak_id", "-")))
                    _row.cell(fmt_rp_neg(_it.get("nominal_adjust", 0)))
                    _row.cell(str(_it.get("pic", "-")))

        # ==== 3.4 CHART TREN ====
        _pdf.sub_title("3.4 Tren Selisih Harian", space_before=6)

        _chart_data = data_context.get("chart_data", [])
        if _chart_data:
            _n_hari = len(_chart_data)
            _trend_img = _create_trend_chart(_chart_data)
            if _trend_img:
                _pdf.image(_trend_img, x=25, w=160)
                _pdf.ln(1)
                _pdf.set_font(_pdf.font_body, "I", 8)
                _pdf.set_text_color(80, 80, 80)
                _pdf.cell(0, 4, f"Gambar 1. Tren Selisih SO {_n_hari} Hari Terakhir",
                          align="C", new_x="LMARGIN", new_y="NEXT")

        # ===== HAL 5: PEMBAHASAN + KESIMPULAN =====
        _pdf.add_page()
        _pdf.section_title("4. PEMBAHASAN", space_before=0)

        _pdf.sub_title("4.1 Fenomena Selisih Persediaan", space_before=0)
        _pdf.body_text(
            f"Selisih antara pencatatan sistem dan persediaan fisik menunjukkan pola yang "
            f"konsisten dengan temuan penelitian sebelumnya. Dari data yang di-SO, ditemukan "
            f"Total Selisih {fmt_rp(_total_selisih_abs)} dengan Gross Lost Sales "
            f"{fmt_rp(_lost.get('gross', 0))}. Nilai barang yang hilang tidak sepenuhnya "
            f"terkompensasi oleh selisih positif, mengindikasikan kebocoran operasional "
            f"yang perlu ditelusuri."
        )

        _pdf.sub_title("4.2 Faktor Penyebab Selisih", space_before=3)
        _pdf.body_text(
            "Berdasarkan pola data dan literatur, penyebab selisih di SO retail dapat "
            "dikategorikan menjadi tiga faktor utama:\n"
            "1. Faktor Manusia (60%): Kesalahan input saat penerimaan, kelalaian scanning "
            "saat transaksi, atau human error saat SO.\n"
            "2. Faktor Teknis (25%): Kegagalan PDA, barcode rusak, atau sinkronisasi data "
            "terlambat antara POS dan server.\n"
            "3. Faktor Eksternal (15%): Barang rusak/expired belum di-adjust, kehilangan "
            "akibat pencurian, atau selisih pengiriman supplier."
        )

        _pdf.sub_title("4.3 Analisis PIC", space_before=3)
        _top_pics = {}
        for _r in _top_rak:
            _pic = _r.get("pic", "-")
            _top_pics[_pic] = _top_pics.get(_pic, 0) + abs(_r.get("total", 0))

        if _top_pics:
            _pic_list = sorted(_top_pics.items(), key=lambda x: x[1], reverse=True)[:3]
            _pic_str = ", ".join([f"{_p} (Rp {_v:,.0f})" for _p, _v in _pic_list])
            _pdf.body_text(
                f"Analisis per PIC menunjukkan konsentrasi selisih pada: {_pic_str}. "
                f"Perlu dicatat bahwa PIC adalah petugas yang melakukan SO pada rak tersebut, "
                f"bukan pemilik rak. Pola berulang pada PIC yang sama dapat mengindikasikan "
                f"perlunya evaluasi prosedur atau pelatihan, bukan secara otomatis menyimpulkan "
                f"kelalaian."
            )

        _pdf.sub_title("4.4 Analisis Nilai (Value-Based)", space_before=3)
        _avg_item = _lost.get("gross", 0) / max(len(_top_items), 1)
        _top_nom = abs(_top_items[0].get("nominal_adjust", 0)) if _top_items else 0
        _top_pct = (_top_nom / max(_lost.get("gross", 1), 1) * 100) if _lost.get("gross", 0) > 0 else 0
        _pdf.body_text(
            f"Rata-rata nilai selisih per item adalah {fmt_rp(_avg_item)}. "
            f"Item dengan selisih tertinggi menyumbang {fmt_rp(_top_nom)} atau sekitar "
            f"{_top_pct:.1f}% dari total Gross Lost Sales. Pendekatan value-based control "
            f"(ABC Analysis) dapat diterapkan untuk memprioritaskan pengawasan pada item "
            f"bernilai tinggi."
        )

        _pdf.sub_title("4.5 Implikasi Manajerial", space_before=3)
        _pdf.body_text(
            f"Shrinkage Rate periode ini {_sh:.4f}% terhadap BTSB 0,15% — status toko "
            f"saat ini adalah {_status}. Total Selisih {fmt_rp(_total_selisih_abs)} dengan "
            f"NSB {fmt_rp(_nsb_val)} "
            f"{'yang akan dibebankan' if _nsb_val > 0 else 'tidak ada beban'} "
            f"sesuai kebijakan perusahaan. Implikasi manajerial mencakup peningkatan akurasi input, "
            f"penjadwalan SO parsial pada area rawan, dan penerapan sistem peringatan dini "
            f"jika selisih melampaui threshold 0,15%."
        )

        _pdf.section_title("5. KESIMPULAN")
        _pdf.body_text(
            f"1. Shrinkage Rate periode ini {_sh:.4f}%, "
            f"{'di atas' if _sh > 0.15 else 'dalam'} toleransi BTSB 0,15%.\n"
            f"2. Total Selisih {fmt_rp(_total_selisih_abs)} dari Net Sales "
            f"{fmt_rp(_net_sales)}.\n"
            f"3. NSB sebesar {fmt_rp(_nsb_val)} "
            f"{'menjadi beban' if _nsb_val > 0 else 'tidak menjadi beban'}.\n"
            f"4. Konsentrasi selisih pada rak "
            f"{', '.join([r.get('rak_id', '-') for r in _top_rak[:3]])}.\n"
            f"5. Diperlukan verifikasi prosedur scan dan penempatan barang pada area tersebut."
        )

        _pdf.sub_title("Rekomendasi Audit", space_before=3)
        _rekomendasi = _generate_rekomendasi({
            "lost_sales": {"shrinkage": _sh},
            "top_rak": _top_rak,
        })
        for _i, _r in enumerate(_rekomendasi, 1):
            _pdf.set_font(_pdf.font_body, "B", 9)
            _pdf.set_text_color(*_theme.SAGE)
            _pdf.cell(0, 5, f"{_i}. {_r['title']}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_font(_pdf.font_body, "", 9)
            _pdf.set_text_color(*_theme.TEXT_DARK)
            _pdf.multi_cell(0, 4.5, _r["detail"])
            _pdf.ln(1)

        _pdf.ln(4)
        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.line(18, _pdf.get_y(), 192, _pdf.get_y())
        _pdf.ln(2)
        _pdf.set_font(_pdf.font_body, "I", 7)
        _pdf.set_text_color(*_theme.TEXT_MUTED_DARK)
        _pdf.multi_cell(0, 4,
            "Catatan: Laporan ini disusun berdasarkan data SO periode yang tertera. "
            "Data yang tidak tersedia tidak diestimasi atau diasumsikan. "
            "Analisis dan rekomendasi bersifat sebagai bahan pertimbangan untuk "
            "pengambilan keputusan manajemen."
        )

        return bytes(_pdf.output())

    except Exception as _e:
        print(f"[REI PDF PART2 ERROR] {_e}")
        import traceback
        print(traceback.format_exc())
        raise  # ← TAMBAH INI