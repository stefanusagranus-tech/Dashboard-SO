"""
Yui Export — PDF Profesional & Gambar
======================================
- PDF: fpdf2 + DejaVu 字体 + Header/Footer 自定义
- Gambar: matplotlib (no browser, aman di Streamlit Cloud)
"""

import io
import os
import pandas as pd
from datetime import datetime

from fpdf import FPDF, FontFace
from fpdf.enums import TableBordersLayout


# =========================================================
# PATH FONT
# =========================================================
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_PATH = os.path.join(_BASE_DIR, "fonts", "DejaVuSansCondensed.ttf")
_FONT_PATH_BOLD = os.path.join(_BASE_DIR, "fonts", "DejaVuSansCondensed-Bold.ttf")


def _font_tersedia():
    """Cek apakah font DejaVu tersedia."""
    return os.path.exists(_FONT_PATH)


# =========================================================
# HELPER
# =========================================================
def _format_nominal(val):
    """Round nominal, hilangkan desimal."""
    try:
        return int(round(float(val)))
    except Exception:
        return 0


def _format_rp(val):
    """Format Rp dengan pemisah ribuan."""
    _n = _format_nominal(val)
    _sign = "+" if _n >= 0 else "-"
    return f"{_sign}Rp {abs(_n):,}".replace(",", ".")


def _hitung_btsb_nsb(net_sales, total_selisih, btsb_persen=0.15):
    """Hitung BTSB & NSB."""
    _btsb = net_sales * (btsb_persen / 100)
    _selisih_abs = abs(total_selisih)
    _nsb = max(0, _selisih_abs - _btsb)
    _status = "OVER" if _selisih_abs > _btsb else "AMAN"
    return {
        "btsb": _btsb,
        "selisih": _selisih_abs,
        "nsb": _nsb,
        "status": _status,
    }


# =========================================================
# PDF PROFESIONAL
# =========================================================
class PDFLaporan(FPDF):
    """PDF dengan header & footer custom, font DejaVu."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._font_family = None

    def _setup_font(self):
        """Setup font DejaVu sekali."""
        if self._font_family:
            return
        if _font_tersedia():
            self.add_font(fname=_FONT_PATH)
            if os.path.exists(_FONT_PATH_BOLD):
                self.add_font(fname=_FONT_PATH_BOLD, style="B")
            self._font_family = "DejaVuSansCondensed"
        else:
            # Fallback ke Helvetica (tapi gak support Unicode)
            self._font_family = "Helvetica"

    def set_my_font(self, style="", size=10):
        """Set font dengan aman."""
        self._setup_font()
        try:
            self.set_font(self._font_family, style=style, size=size)
        except Exception:
            self.set_font("Helvetica", style=style, size=size)

    def header(self):
        # Header band
        self.set_fill_color(30, 20, 60)
        self.rect(0, 0, 210, 28, style="F")

        self.set_my_font(style="B", size=14)
        self.set_text_color(127, 185, 155)
        self.set_xy(10, 6)
        self.cell(0, 8, "LAPORAN STOCK OPNAME", new_x="LMARGIN", new_y="NEXT")

        self.set_my_font(style="", size=9)
        self.set_text_color(232, 177, 137)
        self.set_xy(10, 15)
        self.cell(0, 6, "Toko C383 - Karang Satria", new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(0, 0, 0)
        self.set_y(35)

    def footer(self):
        self.set_y(-15)
        self.set_my_font(style="I", size=8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Halaman {self.page_no()}", align="C")


def export_rekap_pdf(hasil, net_sales=0, filename="rekap_so.pdf"):
    """Export rekap SO jadi PDF profesional."""
    try:
        _pdf = PDFLaporan()
        _pdf.add_page()
        _pdf.set_auto_page_break(auto=True, margin=20)

        # =========================================================
        # RINGKASAN
        # =========================================================
        _pdf.set_my_font(style="B", size=12)
        _pdf.set_text_color(30, 20, 60)
        _pdf.cell(0, 8, "RINGKASAN", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_text_color(0, 0, 0)
        _pdf.set_my_font(style="", size=10)

        _pdf.cell(60, 6, "Periode")
        _pdf.cell(0, 6, f": {hasil.get('periode', '-')}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(60, 6, "Total Rak")
        _pdf.cell(0, 6, f": {hasil.get('total_rak', 0)}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(60, 6, "Total Item")
        _pdf.cell(0, 6, f": {hasil.get('total_item', 0)}", new_x="LMARGIN", new_y="NEXT")
        _pdf.cell(60, 6, "Total Nominal")
        _pdf.cell(0, 6, f": {_format_rp(hasil.get('total_nominal', 0))}", new_x="LMARGIN", new_y="NEXT")
        _pdf.ln(5)

        # =========================================================
        # BTSB & NSB
        # =========================================================
        if net_sales > 0:
            _total_selisih = hasil.get("_total_selisih_bulan", 0)
            _total_rak_bulan = hasil.get("_total_rak_bulan", 0)
            _calc = _hitung_btsb_nsb(net_sales, _total_selisih)

            _pdf.set_my_font(style="B", size=12)
            _pdf.set_text_color(30, 20, 60)
            _pdf.cell(0, 8, "ANALISIS BTSB & NSB (BULAN INI)", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(0, 0, 0)
            _pdf.set_my_font(style="", size=10)

            _pdf.cell(70, 6, "Net Sales Bulan Ini")
            _pdf.cell(0, 6, f": {_format_rp(net_sales)}", new_x="LMARGIN", new_y="NEXT")
            _pdf.cell(70, 6, "BTSB (0,15%)")
            _pdf.cell(0, 6, f": {_format_rp(_calc['btsb'])}", new_x="LMARGIN", new_y="NEXT")
            _pdf.cell(70, 6, "Total Selisih Bulan")
            _pdf.cell(0, 6, f": {_format_rp(_calc['selisih'])}", new_x="LMARGIN", new_y="NEXT")
            _pdf.cell(70, 6, "NSB (beban personil)")
            _pdf.cell(0, 6, f": {_format_rp(_calc['nsb'])}", new_x="LMARGIN", new_y="NEXT")
            _pdf.cell(70, 6, "Total Rak di-SO Bulan Ini")
            _pdf.cell(0, 6, f": {_total_rak_bulan} rak", new_x="LMARGIN", new_y="NEXT")
            _pdf.cell(70, 6, "Status")
            _pdf.set_my_font(style="B", size=10)
            if _calc["status"] == "OVER":
                _pdf.set_text_color(200, 50, 50)
            else:
                _pdf.set_text_color(50, 150, 50)
            _pdf.cell(0, 6, f": {_calc['status']}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(0, 0, 0)
            _pdf.set_my_font(style="", size=10)
            _pdf.ln(5)

        # =========================================================
        # TOP 5 MINUS & PLUS (per item)
        # =========================================================
        try:
            from modules.yui_rekap import get_top_items
            _tops = get_top_items(limit=5)
            _top_minus = _tops.get("top_minus", [])
            _top_plus = _tops.get("top_plus", [])

            # TOP 5 MINUS
            _pdf.set_my_font(style="B", size=12)
            _pdf.set_text_color(30, 20, 60)
            _pdf.cell(0, 8, "TOP 5 MINUS TERTINGGI (PER ITEM)", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(0, 0, 0)

            _pdf.set_my_font(style="B", size=8)
            _pdf.set_fill_color(200, 50, 50)
            _pdf.set_text_color(255, 255, 255)
            _pdf.cell(15, 7, "RAK", border=1, fill=True, align="C")
            _pdf.cell(22, 7, "PLU", border=1, fill=True, align="C")
            _pdf.cell(75, 7, "NAMA PRODUK", border=1, fill=True, align="C")
            _pdf.cell(50, 7, "NOMINAL", border=1, fill=True, align="C")
            _pdf.cell(28, 7, "PIC", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

            _pdf.set_my_font(style="", size=8)
            _pdf.set_text_color(0, 0, 0)
            for _r in _top_minus:
                _pdf.cell(15, 6, str(_r.get("rak_id", "-"))[:10], border=1, align="C")
                _pdf.cell(22, 6, str(_r.get("plu", "-"))[:10], border=1, align="C")
                _pdf.cell(75, 6, str(_r.get("nama_produk", "-"))[:40], border=1, align="L")
                _pdf.cell(50, 6, _format_rp(_r.get("nominal_adjust", 0)), border=1, align="R")
                _pdf.cell(28, 6, str(_r.get("pic", "-"))[:12], border=1, align="C", new_x="LMARGIN", new_y="NEXT")
            _pdf.ln(4)

            # TOP 5 PLUS
            _pdf.set_my_font(style="B", size=12)
            _pdf.set_text_color(30, 20, 60)
            _pdf.cell(0, 8, "TOP 5 PLUS TERTINGGI (PER ITEM)", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(0, 0, 0)

            _pdf.set_my_font(style="B", size=8)
            _pdf.set_fill_color(50, 150, 50)
            _pdf.set_text_color(255, 255, 255)
            _pdf.cell(15, 7, "RAK", border=1, fill=True, align="C")
            _pdf.cell(22, 7, "PLU", border=1, fill=True, align="C")
            _pdf.cell(75, 7, "NAMA PRODUK", border=1, fill=True, align="C")
            _pdf.cell(50, 7, "NOMINAL", border=1, fill=True, align="C")
            _pdf.cell(28, 7, "PIC", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

            _pdf.set_my_font(style="", size=8)
            _pdf.set_text_color(0, 0, 0)
            for _r in _top_plus:
                _pdf.cell(15, 6, str(_r.get("rak_id", "-"))[:10], border=1, align="C")
                _pdf.cell(22, 6, str(_r.get("plu", "-"))[:10], border=1, align="C")
                _pdf.cell(75, 6, str(_r.get("nama_produk", "-"))[:40], border=1, align="L")
                _pdf.cell(50, 6, _format_rp(_r.get("nominal_adjust", 0)), border=1, align="R")
                _pdf.cell(28, 6, str(_r.get("pic", "-"))[:12], border=1, align="C", new_x="LMARGIN", new_y="NEXT")
            _pdf.ln(4)
        except Exception as _e:
            print(f"[PDF TOP5 WARN] {_e}")

        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        print(f"[EXPORT_PDF ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return None


# =========================================================
# GAMBAR — matplotlib (aman, no browser)
# =========================================================
def export_rekap_image(hasil, net_sales=0, filename="rekap_so.png"):
    """Export rekap SO jadi gambar pakai matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from modules.yui_rekap import get_top_items

        _list_rak = hasil.get("list_rak", [])
        if not _list_rak:
            return None

        _tops = get_top_items(limit=5)
        _top_minus = _tops.get("top_minus", [])
        _top_plus = _tops.get("top_plus", [])

        _fig = plt.figure(figsize=(11, 12))
        _fig.patch.set_facecolor("#FAFAFA")

        # Subplot 1: Rekap per Rak
        _ax1 = _fig.add_subplot(3, 1, 1)
        _ax1.axis("off")
        _ax1.set_title("REKAP PER RAK", fontsize=12, fontweight="bold", color="#2E1A47", pad=10)

        _df_rak = pd.DataFrame(_list_rak).rename(columns={
            "rak_id": "Rak", "total": "Nominal",
            "pic": "PIC", "tanggal": "Tanggal",
        })
        _df_rak["Nominal"] = _df_rak["Nominal"].apply(
            lambda x: f"{'+' if _format_nominal(x) >= 0 else '-'}Rp {abs(_format_nominal(x)):,}".replace(",", ".")
        )

        _tbl1 = _ax1.table(
            cellText=_df_rak[["Rak", "Nominal", "PIC"]].values,
            colLabels=["Rak", "Nominal", "PIC"],
            cellLoc="center", loc="center", colWidths=[0.2, 0.4, 0.3],
        )
        _tbl1.auto_set_font_size(False)
        _tbl1.set_fontsize(9)
        _tbl1.scale(1, 1.4)
        for _i in range(3):
            _cell = _tbl1[(0, _i)]
            _cell.set_facecolor("#7FB99B")
            _cell.set_text_props(color="white", weight="bold")

        # Subplot 2: Top 5 Minus
        _ax2 = _fig.add_subplot(3, 1, 2)
        _ax2.axis("off")
        _ax2.set_title("TOP 5 MINUS (PER ITEM)", fontsize=12, fontweight="bold", color="#C83232", pad=10)

        if _top_minus:
            _rows_minus = []
            for _r in _top_minus:
                _nom = _format_nominal(_r.get("nominal_adjust", 0))
                _rows_minus.append([
                    str(_r.get("rak_id", "-"))[:8],
                    str(_r.get("plu", "-"))[:10],
                    str(_r.get("nama_produk", "-"))[:35],
                    f"-Rp {abs(_nom):,}".replace(",", "."),
                ])
            _tbl2 = _ax2.table(
                cellText=_rows_minus,
                colLabels=["Rak", "PLU", "Nama Produk", "Nominal"],
                cellLoc="center", loc="center", colWidths=[0.1, 0.15, 0.55, 0.2],
            )
            _tbl2.auto_set_font_size(False)
            _tbl2.set_fontsize(8)
            _tbl2.scale(1, 1.4)
            for _i in range(4):
                _cell = _tbl2[(0, _i)]
                _cell.set_facecolor("#C83232")
                _cell.set_text_props(color="white", weight="bold")

        # Subplot 3: Top 5 Plus
        _ax3 = _fig.add_subplot(3, 1, 3)
        _ax3.axis("off")
        _ax3.set_title("TOP 5 PLUS (PER ITEM)", fontsize=12, fontweight="bold", color="#329632", pad=10)

        if _top_plus:
            _rows_plus = []
            for _r in _top_plus:
                _nom = _format_nominal(_r.get("nominal_adjust", 0))
                _rows_plus.append([
                    str(_r.get("rak_id", "-"))[:8],
                    str(_r.get("plu", "-"))[:10],
                    str(_r.get("nama_produk", "-"))[:35],
                    f"+Rp {abs(_nom):,}".replace(",", "."),
                ])
            _tbl3 = _ax3.table(
                cellText=_rows_plus,
                colLabels=["Rak", "PLU", "Nama Produk", "Nominal"],
                cellLoc="center", loc="center", colWidths=[0.1, 0.15, 0.55, 0.2],
            )
            _tbl3.auto_set_font_size(False)
            _tbl3.set_fontsize(8)
            _tbl3.scale(1, 1.4)
            for _i in range(4):
                _cell = _tbl3[(0, _i)]
                _cell.set_facecolor("#329632")
                _cell.set_text_props(color="white", weight="bold")

        plt.tight_layout()
        plt.savefig(filename, dpi=100, bbox_inches="tight", facecolor="#FAFAFA")
        plt.close(_fig)
        print(f"[EXPORT_IMG] Saved: {filename}")
        return filename
    except Exception as e:
        print(f"[EXPORT_IMG ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return None


# =========================================================
# EXCEL
# =========================================================
def export_rekap_excel(hasil, net_sales=0):
    """Export Excel: ringkasan + rekap per rak."""
    try:
        _buf = io.BytesIO()

        _df_rak = pd.DataFrame(hasil.get("list_rak", []))
        if not _df_rak.empty:
            _df_rak = _df_rak.rename(columns={
                "rak_id": "Rak", "total": "Nominal",
                "pic": "PIC", "tanggal": "Tanggal",
            })
            _df_rak["Nominal"] = _df_rak["Nominal"].apply(_format_nominal)

        _summary = {
            "Periode": [hasil.get("periode", "-")],
            "Total Rak": [hasil.get("total_rak", 0)],
            "Total Item": [hasil.get("total_item", 0)],
            "Total Nominal": [_format_nominal(hasil.get("total_nominal", 0))],
        }
        if net_sales > 0:
            _calc = _hitung_btsb_nsb(net_sales, hasil.get("total_nominal", 0))
            _summary["Net Sales"] = [_format_nominal(net_sales)]
            _summary["BTSB (0,15%)"] = [_format_nominal(_calc["btsb"])]
            _summary["Total Selisih"] = [_format_nominal(_calc["selisih"])]
            _summary["NSB"] = [_format_nominal(_calc["nsb"])]
            _summary["Status"] = [_calc["status"]]

        _df_summary = pd.DataFrame(_summary).T.reset_index()
        _df_summary.columns = ["Item", "Nilai"]

        with pd.ExcelWriter(_buf, engine="openpyxl") as _writer:
            _df_summary.to_excel(_writer, index=False, sheet_name="Ringkasan")
            if not _df_rak.empty:
                _df_rak.to_excel(_writer, index=False, sheet_name="Rekap per Rak")

        _buf.seek(0)
        return _buf.getvalue()
    except Exception as e:
        print(f"[EXPORT_EXCEL ERROR] {e}")
        return None