"""
Yui Export — Export rekap SO ke PDF, Excel, Gambar.
PDF: profesional, gak kelihatan AI-generated.
Gambar: pakai html2pic (no browser).
"""

import io
import pandas as pd
from datetime import datetime
from fpdf import FPDF, FontFace


def _format_nominal(val):
    """Round nominal, hilangkan desimal aneh."""
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
    """PDF dengan header & footer custom."""

    def header(self):
        # Header band
        self.set_fill_color(30, 20, 60)
        self.rect(0, 0, 210, 25, "F")
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(127, 185, 155)
        self.set_xy(10, 6)
        self.cell(0, 8, "LAPORAN STOCK OPNAME", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(232, 177, 137)
        self.set_xy(10, 14)
        self.cell(0, 6, "Toko C383 — Karang Satria", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Halaman {self.page_no()} — Dicetak oleh Yui", align="C")


def export_rekap_pdf(hasil, net_sales=0, filename="rekap_so.pdf"):
    """Export rekap SO jadi PDF — versi paling simple."""
    try:
        from fpdf import FPDF
        import pandas as pd

        _pdf = FPDF()
        _pdf.add_page()
        _pdf.set_auto_page_break(auto=True, margin=15)

        # Header
        _pdf.set_font("Helvetica", "B", 14)
        _pdf.cell(0, 10, "LAPORAN STOCK OPNAME", ln=True, align="C")
        _pdf.set_font("Helvetica", "", 10)
        _pdf.cell(0, 6, f"Toko C383 - {hasil.get('periode', '-')}", ln=True, align="C")
        _pdf.ln(5)

        # Ringkasan
        _pdf.set_font("Helvetica", "B", 12)
        _pdf.cell(0, 8, "RINGKASAN", ln=True)
        _pdf.set_font("Helvetica", "", 10)
        _pdf.cell(70, 6, "Total Rak")
        _pdf.cell(0, 6, f": {hasil.get('total_rak', 0)}", ln=True)
        _pdf.cell(70, 6, "Total Item")
        _pdf.cell(0, 6, f": {hasil.get('total_item', 0)}", ln=True)
        _pdf.cell(70, 6, "Total Nominal")
        _pdf.cell(0, 6, f": {_format_rp(hasil.get('total_nominal', 0))}", ln=True)
        _pdf.ln(5)

        # BTSB/NSB
        if net_sales > 0:
            try:
                _total_selisih = hasil.get("_total_selisih_bulan", 0)
                _total_rak_bulan = hasil.get("_total_rak_bulan", 0)
                _calc = _hitung_btsb_nsb(net_sales, _total_selisih)

                _pdf.set_font("Helvetica", "B", 12)
                _pdf.cell(0, 8, "ANALISIS BTSB & NSB", ln=True)
                _pdf.set_font("Helvetica", "", 10)
                _pdf.cell(70, 6, "Net Sales Bulan Ini")
                _pdf.cell(0, 6, f": {_format_rp(net_sales)}", ln=True)
                _pdf.cell(70, 6, "BTSB (0,15%)")
                _pdf.cell(0, 6, f": {_format_rp(_calc['btsb'])}", ln=True)
                _pdf.cell(70, 6, "Total Selisih Bulan")
                _pdf.cell(0, 6, f": {_format_rp(_calc['selisih'])}", ln=True)
                _pdf.cell(70, 6, "NSB")
                _pdf.cell(0, 6, f": {_format_rp(_calc['nsb'])}", ln=True)
                _pdf.cell(70, 6, "Total Rak di-SO")
                _pdf.cell(0, 6, f": {_total_rak_bulan} rak", ln=True)
                _pdf.cell(70, 6, "Status")
                _pdf.cell(0, 6, f": {_calc['status']}", ln=True)
                _pdf.ln(5)
            except Exception as _e_btsb:
                print(f"[PDF BTSB ERROR] {_e_btsb}")

        # Top 5 Minus
        _list_rak = hasil.get("list_rak", [])
        if _list_rak:
            try:
                _df = pd.DataFrame(_list_rak)
                _df["total"] = pd.to_numeric(_df["total"], errors="coerce").fillna(0)

                _pdf.set_font("Helvetica", "B", 12)
                _pdf.cell(0, 8, "TOP 5 MINUS TERTINGGI", ln=True)
                _pdf.set_font("Helvetica", "B", 9)
                _pdf.cell(40, 7, "RAK", border=1, align="C")
                _pdf.cell(60, 7, "NOMINAL", border=1, align="C")
                _pdf.cell(50, 7, "PIC", border=1, align="C")
                _pdf.cell(40, 7, "TGL", border=1, align="C", ln=True)

                _pdf.set_font("Helvetica", "", 9)
                for _, _r in _df.nsmallest(5, "total").iterrows():
                    _pdf.cell(40, 6, str(_r.get("rak_id", "-"))[:15], border=1, align="C")
                    _pdf.cell(60, 6, _format_rp(_r.get("total", 0)), border=1, align="R")
                    _pdf.cell(50, 6, str(_r.get("pic", "-"))[:20], border=1, align="C")
                    _pdf.cell(40, 6, str(_r.get("tanggal", "-"))[:10], border=1, align="C", ln=True)
                _pdf.ln(4)

                # Top 5 Plus
                _pdf.set_font("Helvetica", "B", 12)
                _pdf.cell(0, 8, "TOP 5 PLUS TERTINGGI", ln=True)
                _pdf.set_font("Helvetica", "B", 9)
                _pdf.cell(40, 7, "RAK", border=1, align="C")
                _pdf.cell(60, 7, "NOMINAL", border=1, align="C")
                _pdf.cell(50, 7, "PIC", border=1, align="C")
                _pdf.cell(40, 7, "TGL", border=1, align="C", ln=True)

                _pdf.set_font("Helvetica", "", 9)
                for _, _r in _df.nlargest(5, "total").iterrows():
                    _pdf.cell(40, 6, str(_r.get("rak_id", "-"))[:15], border=1, align="C")
                    _pdf.cell(60, 6, _format_rp(_r.get("total", 0)), border=1, align="R")
                    _pdf.cell(50, 6, str(_r.get("pic", "-"))[:20], border=1, align="C")
                    _pdf.cell(40, 6, str(_r.get("tanggal", "-"))[:10], border=1, align="C", ln=True)
            except Exception as _e_top:
                print(f"[PDF TOP5 ERROR] {_e_top}")

        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        import traceback
        print(f"[EXPORT_PDF ERROR] {e}")
        print(traceback.format_exc())
        return None

# =========================================================
# EXCEL — SEMUA ITEM
# =========================================================
def export_rekap_excel(hasil, net_sales=0):
    """Export Excel: ringkasan + semua item + BTSB/NSB."""
    try:
        _buf = io.BytesIO()

        # Sheet 1: Rekap per rak
        _df_rak = pd.DataFrame(hasil.get("list_rak", []))
        if not _df_rak.empty:
            _df_rak = _df_rak.rename(columns={
                "rak_id": "Rak", "total": "Nominal",
                "pic": "PIC", "tanggal": "Tanggal",
            })
            _df_rak["Nominal"] = _df_rak["Nominal"].apply(_format_nominal)

        # Sheet 2: Ringkasan + BTSB/NSB
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


# =========================================================
# GAMBAR — HTML to Image (html2pic)
# =========================================================
def export_rekap_image(hasil, net_sales=0, filename="rekap_so.png"):
    """Export rekap SO jadi gambar pakai matplotlib (no external browser)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _list_rak = hasil.get("list_rak", [])
        if not _list_rak:
            return None

        _df = pd.DataFrame(_list_rak)
        _df = _df.rename(columns={
            "rak_id": "Rak", "total": "Nominal",
            "pic": "PIC", "tanggal": "Tanggal",
        })
        _df["Nominal"] = _df["Nominal"].apply(_format_nominal)
        _df["Nominal"] = _df["Nominal"].apply(
            lambda x: f"{'+' if x >= 0 else '-'}Rp {abs(x):,}".replace(",", ".")
        )

        # Figure
        _fig, _ax = plt.subplots(figsize=(8, max(3, len(_df) * 0.5 + 1.5)))
        _ax.axis("off")

        # Title
        _ax.text(
            0.5, 0.98,
            "LAPORAN STOCK OPNAME",
            ha="center", va="top",
            fontsize=14, fontweight="bold",
            color="#2E1A47",
            transform=_ax.transAxes,
        )
        _ax.text(
            0.5, 0.93,
            f"Toko C383 — {hasil.get('periode', '-')}",
            ha="center", va="top",
            fontsize=9,
            color="#7FB99B",
            transform=_ax.transAxes,
        )

        # Table
        _tbl = _ax.table(
            cellText=_df[["Rak", "Nominal", "PIC"]].values,
            colLabels=["Rak", "Nominal", "PIC"],
            cellLoc="center", loc="center",
            colWidths=[0.2, 0.4, 0.3],
        )
        _tbl.auto_set_font_size(False)
        _tbl.set_fontsize(10)
        _tbl.scale(1, 1.6)

        # Style header
        for _i in range(3):
            _cell = _tbl[(0, _i)]
            _cell.set_facecolor("#7FB99B")
            _cell.set_text_props(color="white", weight="bold")

        # Style rows
        for _i in range(1, len(_df) + 1):
            for _j in range(3):
                _cell = _tbl[(_i, _j)]
                _cell.set_facecolor("#FFFFFF" if _i % 2 == 0 else "#F5F5F5")

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