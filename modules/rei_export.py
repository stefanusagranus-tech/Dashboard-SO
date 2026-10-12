"""
Rei Export — PDF Generator (Jurnal Ilmiah SINTA Style)
=======================================================
Generate PDF laporan analisis SO dengan standar jurnal SINTA.

Struktur: IMRaD (Introduction, Methods, Results, Discussion)
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
    TEXT_MUTED = (168, 155, 142)
    RED = (220, 60, 60)
    GREEN = (60, 180, 100)
    BLACK = (30, 30, 30)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _clean_text(text):
    """Bersihin HTML entity & karakter aneh."""
    if not text:
        return "-"
    return str(text).replace("&#39;", "'").replace("&amp;", "&").replace("&quot;", '"')


def fmt_rp(value):
    try:
        return f"Rp {int(float(value)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp_signed(value):
    try:
        _v = float(value)
        _sign = "-" if _v < 0 else ""
        return f"{_sign}Rp {int(abs(_v)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"

def section_title(self, text, space_before=4):
    """Heading section — compact."""
    self.ln(space_before)
    self.set_font(self.font_title, "B", 12)
    self.set_text_color(*self.theme.GOLD)
    self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    self.ln(2)

def sub_title(self, text, space_before=3):
    """Sub-heading."""
    self.ln(space_before)
    self.set_font(self.font_body, "B", 10)
    self.set_text_color(*self.theme.SAGE)
    self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
    self.ln(1)

def body_text(self, text, line_height=5):
    """Paragraf body."""
    self.set_font(self.font_body, "", 9)
    self.set_text_color(*self.theme.TEXT_LIGHT)
    self.multi_cell(0, line_height, text)
    
# =========================================================
# PDF CLASS
# =========================================================
class ReiPDF(FPDF):
    def __init__(self, theme=None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.theme = theme or ReiTheme()
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=25)

        _font_dir = os.path.join(os.path.dirname(__file__), "..", "fonts")

        # === REGISTER SEMUA FONT ===
        _fonts = {
            # Serif
            ("Serif", ""):    "DejaVuSerifCondensed.ttf",
            ("Serif", "B"):   "DejaVuSerifCondensed-Bold.ttf",
            ("Serif", "I"):   "DejaVuSerif-Italic.ttf",
            ("Serif", "BI"):  "DejaVuSerif-BoldItalic.ttf",
            # Sans
            ("Sans", ""):     "DejaVuSansCondensed.ttf",
            ("Sans", "B"):    "DejaVuSansCondensed-Bold.ttf",
            ("Sans", "I"):    "DejaVuSans-Oblique.ttf",
            ("Sans", "BI"):   "DejaVuSans-BoldOblique.ttf",
            # Mono
            ("Mono", ""):     "DejaVuSansMono.ttf",
            ("Mono", "B"):    "DejaVuSansMono-Bold.ttf",
            ("Mono", "I"):    "DejaVuSansMono-Oblique.ttf",
            ("Mono", "BI"):   "DejaVuSansMono-BoldOblique.ttf",
        }

        _loaded = 0
        _missing = []
        for (_fam, _style), _fn in _fonts.items():
            _p = os.path.join(_font_dir, _fn)
            if os.path.exists(_p):
                try:
                    self.add_font(_fam, _style, _p)
                    _loaded += 1
                except Exception as _e:
                    print(f"[REI PDF] Gagal load {_fn}: {_e}")
                    _missing.append(_fn)
            else:
                print(f"[REI PDF] File gak ada: {_fn}")
                _missing.append(_fn)

        print(f"[REI PDF] Loaded {_loaded}/{len(_fonts)} fonts")
        if _missing:
            print(f"[REI PDF] Missing: {_missing}")

        # === DEFAULT FONT ===
        self.font_title = "Serif"
        self.font_body = "Sans"
        self.font_mono = "Mono"

        # === FALLBACK kalau font Mono gagal load ===
        if _loaded == 0:
            self.font_title = "Helvetica"
            self.font_body = "Helvetica"
            self.font_mono = "Courier"
            print("[REI PDF] Fallback ke built-in fonts (Helvetica/Courier)")

# =========================================================
# CHART
# =========================================================
def _chart_to_image(fig, dpi=180):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="#140C23", edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


def _create_trend_chart(chart_data):
    if not chart_data:
        return None

    fig, ax = plt.subplots(figsize=(6, 3), facecolor="#140C23")
    _labels = [str(c.get("tanggal", ""))[-5:] for c in chart_data]
    _values = [float(c.get("nominal", 0)) for c in chart_data]
    _colors = ["#7FB99B" if v >= 0 else "#E8B189" for v in _values]

    _bars = ax.bar(_labels, _values, color=_colors, edgecolor="#140C23", linewidth=1.2)
    ax.axhline(y=0, color="#A89B8E", linewidth=0.8, linestyle="--", alpha=0.5)

    ax.set_facecolor("#1E143C")
    ax.set_title("Tren Selisih SO (7 Hari Terakhir)", color="#E8B189",
                 fontsize=10, weight="bold", pad=8)
    ax.set_ylabel("Nominal (Rp)", color="#F5E6D3", fontsize=8)
    ax.tick_params(axis="x", colors="#F5E6D3", labelsize=7)
    ax.tick_params(axis="y", colors="#F5E6D3", labelsize=7)
    ax.grid(axis="y", color="#A89B8E", alpha=0.15, linewidth=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#A89B8E")
    ax.spines["left"].set_color("#A89B8E")

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
                      "Periksa indikasi scan error atau masalah penempatan."
        })

    if _lost.get("shrinkage", 0) > 2:
        _rekom.append({
            "title": "Evaluasi Menyeluruh Shrinkage",
            "detail": f"Shrinkage Rate {_lost.get('shrinkage', 0):.2f}% di atas benchmark. "
                      f"Perlu review SOP, training PIC, dan audit proses."
        })
    else:
        _rekom.append({
            "title": "Pertahankan Prosedur Existing",
            "detail": f"Shrinkage Rate {_lost.get('shrinkage', 0):.2f}% dalam toleransi. "
                      f"Monitoring berkala tetap diperlukan."
        })

    _rekom.append({
        "title": "Cross-check Data Penjualan dengan POS",
        "detail": "Bandingkan data SO dengan data penjualan POS untuk deteksi anomali."
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

        # ===== HALAMAN 1: JUDUL =====
        _pdf.add_page()
        _pdf.set_fill_color(*_theme.BG_DARK)
        _pdf.rect(0, 0, 210, 297, "F")
        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(1.2)
        _pdf.rect(15, 15, 180, 267)

        _pdf.ln(60)
        _pdf.set_font(_pdf.font_title, "B", 22)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 12, "ANALISIS STOCK OPNAME", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font(_pdf.font_title, "B", 16)
        _pdf.cell(0, 10, "Toko C383 - Karang Satria", align="C", new_x="LMARGIN", new_y="NEXT")

        _pdf.ln(8)
        _pdf.set_draw_color(*_theme.SAGE)
        _pdf.set_line_width(0.4)
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
        _pdf.set_text_color(*_theme.TEXT_MUTED)
        _pdf.cell(0, 7, "Disusun oleh: Rei - Analis SO (AI-3)", align="C", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_font(_pdf.font_mono, "", 9)
        _pdf.cell(0, 7, f"Dicetak: {_tgl}", align="C", new_x="LMARGIN", new_y="NEXT")

        # ===== HALAMAN 2: ABSTRAK =====
        _pdf.add_page()
        _pdf.set_font(_pdf.font_title, "B", 14)
        _pdf.set_text_color(*_theme.GOLD)
        _pdf.cell(0, 10, "ABSTRAK", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(2)

        _lost = data_context.get("lost_sales", {})
        _btsb = data_context.get("btsb", {})
        _rekap = data_context.get("rekap", {})

        _abstrak = (
            f"Analisis Stock Opname (SO) ini bertujuan untuk mengukur akurasi stok "
            f"dan mengidentifikasi nilai kehilangan (shrinkage) di Toko C383 Karang Satria "
            f"periode {_periode}. Metode yang digunakan meliputi perhitungan Gross Lost Sales, "
            f"Net Lost Sales, dan Shrinkage Rate berdasarkan data {_rekap.get('total_item', 0)} item "
            f"dari {_rekap.get('total_rak', 0)} rak. Hasil menunjukkan Net Sales sebesar "
            f"{fmt_rp(_lost.get('net_sales', 0))} dengan Net Lost Sales {fmt_rp(_lost.get('net', 0))} "
            f"({_lost.get('shrinkage', 0):.2f}% dari Net Sales). Status BTSB: {_btsb.get('status', '-')}. "
            f"Analisis ini memberikan rekomendasi audit untuk mengurangi risiko shrinkage."
        )

        _pdf.set_font(_pdf.font_body, "", 10)
        _pdf.set_text_color(*_theme.TEXT_LIGHT)
        _pdf.multi_cell(0, 6, _abstrak)
        _pdf.ln(4)
        _pdf.set_font(_pdf.font_body, "I", 9)
        _pdf.cell(0, 6, "Kata kunci: stock opname, shrinkage, lost sales, analisis retail, BTSB",
                  new_x="LMARGIN", new_y="NEXT")

        # ===== HALAMAN 3: PENDAHULUAN + METODE (1 PAGE) =====
        _pdf.add_page()
        
        _pdf.section_title("1. PENDAHULUAN", space_before=0)
        _pdf.body_text(
            f"Stock Opname (SO) merupakan proses penghitungan fisik stok barang untuk "
            f"memverifikasi akurasi data antara catatan sistem dengan kondisi aktual. "
            f"Di industri retail, akurasi stok menjadi kunci utama dalam menjaga ketersediaan "
            f"produk sekaligus meminimalkan nilai kehilangan (shrinkage) yang berdampak "
            f"langsung pada profitabilitas."
        )
        _pdf.ln(2)
        _pdf.body_text(
            f"Toko C383 Karang Satria melaksanakan SO secara berkala. Analisis ini bertujuan untuk: "
            f"(1) mengukur tingkat akurasi stok periode {_periode}, (2) menghitung nilai Gross dan "
            f"Net Lost Sales, (3) mengidentifikasi pola selisih berdasarkan rak dan PIC, serta "
            f"(4) memberikan rekomendasi audit yang actionable."
        )
        
        _pdf.section_title("2. METODE")
        
        _pdf.sub_title("2.1 Sumber Data")
        _pdf.body_text(
            f"Data diperoleh dari sistem SO Toko C383 periode {_periode}. "
            f"Total rak: {_rekap.get('total_rak', 0)}. Total item: {_rekap.get('total_item', 0)}."
        )
        
        _pdf.sub_title("2.2 Metrik yang Digunakan")
        _pdf.body_text(
            "1. Gross Lost Sales = total nilai absolut item dengan qty_var < 0.\n"
            "2. Net Lost Sales = nilai absolut dari total nominal_adjust semua item.\n"
            "3. Shrinkage Rate = (Net Lost Sales / Net Sales) x 100 persen."
        )
        
        _pdf.sub_title("2.3 Batasan")
        _pdf.body_text(
            "1. Data hanya dari SO periode ini.\n"
            "2. Tidak ada data benchmark internal.\n"
            "3. Analisis berbasis pola data yang tersedia."
        )
        
        # ===== HALAMAN 4: HASIL (RINGKASAN + CHART) =====
        _pdf.add_page()
        
        _pdf.section_title("3. HASIL", space_before=0)
        
        _pdf.sub_title("3.1 Ringkasan Metrik")
        _sh = _lost.get("shrinkage", 0)
        
        _headings = FontFace(
            family=_pdf.font_title, emphasis="BOLD",
            color=(232, 177, 137), fill_color=(76, 29, 149), size_pt=9,
        )
        
        with _pdf.table(col_widths=(70, 60, 40), headings_style=_headings,
                        line_height=6, first_row_as_headings=True) as _t:
            _row = _t.row()
            _row.cell("Metrik"); _row.cell("Nilai"); _row.cell("Status")
            _row = _t.row()
            _row.cell("Net Sales"); _row.cell(fmt_rp(_lost.get("net_sales", 0))); _row.cell("-")
            _row = _t.row()
            _row.cell("Gross Lost Sales"); _row.cell(fmt_rp(_lost.get("gross", 0))); _row.cell("-")
            _row = _t.row()
            _row.cell("Net Lost Sales"); _row.cell(fmt_rp(_lost.get("net", 0)))
            _row.cell("PERHATIAN" if _sh > 2 else "AMAN")
            _row = _t.row()
            _row.cell("Shrinkage Rate"); _row.cell(f"{_sh:.2f}%")
            _row.cell("> 2%" if _sh > 2 else "< 2%")
        
        _pdf.sub_title("3.2 Tren Selisih 7 Hari", space_before=4)
        
        _chart_data = data_context.get("chart_data", [])
        if _chart_data:
            _trend_img = _create_trend_chart(_chart_data)
            if _trend_img:
                _pdf.image(_trend_img, x=30, w=150)
                _pdf.ln(2)
        else:
            _pdf.set_font(_pdf.font_body, "I", 9)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.cell(0, 6, "Data tren tidak tersedia.", new_x="LMARGIN", new_y="NEXT")
        
        # ===== HALAMAN 5: TOP ITEM & RAK =====
        _pdf.add_page()
        
        _pdf.sub_title("3.3 Top 10 Item Selisih Terbesar", space_before=0)
        _top_items = data_context.get("top_items", [])
        if _top_items:
            with _pdf.table(col_widths=(75, 20, 35, 30), headings_style=_headings,
                            line_height=5.5, first_row_as_headings=True) as _t:
                _row = _t.row()
                _row.cell("Nama Produk"); _row.cell("Rak"); _row.cell("Nominal"); _row.cell("PIC")
                for _it in _top_items[:10]:
                    _row = _t.row()
                    _row.cell(_clean_text(_it.get("nama_produk", "-"))[:38])
                    _row.cell(str(_it.get("rak_id", "-")))
                    _row.cell(fmt_rp(abs(_it.get("nominal_adjust", 0))))
                    _row.cell(str(_it.get("pic", "-")))
        else:
            _pdf.set_font(_pdf.font_body, "I", 9)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.cell(0, 6, "Data tidak tersedia.", new_x="LMARGIN", new_y="NEXT")
        
        _pdf.sub_title("3.4 Top 5 Rak dengan Selisih Tertinggi", space_before=4)
        _top_rak = data_context.get("top_rak", [])
        if _top_rak:
            with _pdf.table(col_widths=(30, 40, 45, 30), headings_style=_headings,
                            line_height=5.5, first_row_as_headings=True) as _t:
                _row = _t.row()
                _row.cell("Rak"); _row.cell("PIC"); _row.cell("Nominal"); _row.cell("Jml Item")
                for _r in _top_rak[:5]:
                    _row = _t.row()
                    _row.cell(str(_r.get("rak_id", "-")))
                    _row.cell(str(_r.get("pic", "-")))
                    _row.cell(fmt_rp(abs(_r.get("total", 0))))
                    _row.cell(str(_r.get("total_item", 0)))
        else:
            _pdf.set_font(_pdf.font_body, "I", 9)
            _pdf.set_text_color(*_theme.TEXT_MUTED)
            _pdf.cell(0, 6, "Data tidak tersedia.", new_x="LMARGIN", new_y="NEXT")
        
        # ===== HALAMAN 6: PEMBAHASAN + KESIMPULAN (1 PAGE) =====
        _pdf.add_page()
        
        _pdf.section_title("4. PEMBAHASAN", space_before=0)
        _pdf.body_text(
            f"Berdasarkan hasil analisis, Toko C383 mencatat Net Sales sebesar "
            f"{fmt_rp(_lost.get('net_sales', 0))} dengan Net Lost Sales {fmt_rp(_lost.get('net', 0))}. "
            f"Shrinkage Rate berada di {_sh:.2f}%, {'di atas' if _sh > 2 else 'di bawah'} "
            f"benchmark umum retail (2%). Status BTSB: {_btsb.get('status', '-')}."
        )
        _pdf.ln(2)
        _pdf.body_text(
            f"Dari sisi distribusi, konsentrasi selisih terbesar berada pada rak "
            f"{', '.join([r.get('rak_id', '-') for r in _top_rak[:3]])}. "
            f"Hal ini mengindikasikan perlunya verifikasi prosedur pada area tersebut."
        )
        _pdf.ln(2)
        _pdf.body_text(
            "Perlu dicatat bahwa PIC dalam konteks ini adalah petugas yang melakukan "
            "SO pada rak tersebut, bukan pemilik rak. Pola selisih berulang pada PIC "
            "tertentu dapat mengindikasikan perlunya evaluasi prosedur atau pelatihan."
        )
        
        _pdf.section_title("5. KESIMPULAN", space_before=4)
        _pdf.body_text(
            f"1. Shrinkage Rate periode ini sebesar {_sh:.2f}% "
            f"({'di atas' if _sh > 2 else 'dalam'}) toleransi 2%.\n"
            f"2. Net Lost Sales tercatat {fmt_rp(_lost.get('net', 0))} dari Net Sales "
            f"{fmt_rp(_lost.get('net_sales', 0))}.\n"
            f"3. Konsentrasi selisih tertinggi berada pada rak "
            f"{', '.join([r.get('rak_id', '-') for r in _top_rak[:3]])}.\n"
            f"4. Diperlukan verifikasi prosedur scan dan penempatan barang pada area tersebut."
        )
        
        _pdf.sub_title("Rekomendasi Audit", space_before=4)
        _rekomendasi = _generate_rekomendasi(data_context)
        for _i, _r in enumerate(_rekomendasi, 1):
            _pdf.set_font(_pdf.font_body, "B", 9)
            _pdf.set_text_color(*_theme.SAGE)
            _pdf.cell(0, 6, f"{_i}. {_r['title']}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_font(_pdf.font_body, "", 9)
            _pdf.set_text_color(*_theme.TEXT_LIGHT)
            _pdf.multi_cell(0, 5, _r["detail"])
            _pdf.ln(1)
        
        # ===== CATATAN (di halaman terakhir, gak perlu halaman baru) =====
        _pdf.ln(6)
        _pdf.set_draw_color(*_theme.GOLD)
        _pdf.set_line_width(0.4)
        _pdf.line(20, _pdf.get_y(), 190, _pdf.get_y())
        _pdf.ln(4)
        
        _pdf.set_font(_pdf.font_body, "I", 8)
        _pdf.set_text_color(*_theme.TEXT_MUTED)
        _pdf.multi_cell(0, 5,
            "Catatan: Laporan ini disusun berdasarkan data SO periode yang tertera. "
            "Data yang tidak tersedia tidak diestimasi atau diasumsikan. "
            "Analisis dan rekomendasi bersifat sebagai bahan pertimbangan untuk "
            "pengambilan keputusan manajemen."
        )
        
        return bytes(_pdf.output())