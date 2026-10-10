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
    """Export rekap SO jadi PDF profesional."""
    try:
        _pdf = PDFLaporan()
        _pdf.add_page()
        _pdf.set_auto_page_break(auto=True, margin=20)

        # =========================================================
        # RINGKASAN
        # =========================================================
        _pdf.set_font("Helvetica", "B", 12)
        _pdf.set_text_color(30, 20, 60)
        _pdf.cell(0, 8, "RINGKASAN", ln=True)
        _pdf.set_text_color(0, 0, 0)
        _pdf.set_font("Helvetica", "", 10)

        _pdf.cell(60, 6, "Periode", border=0)
        _pdf.cell(0, 6, f": {hasil.get('periode', '-')}", ln=True)
        _pdf.cell(60, 6, "Total Rak", border=0)
        _pdf.cell(0, 6, f": {hasil.get('total_rak', 0)}", ln=True)
        _pdf.cell(60, 6, "Total Item", border=0)
        _pdf.cell(0, 6, f": {hasil.get('total_item', 0)}", ln=True)
        _pdf.cell(60, 6, "Total Nominal", border=0)
        _pdf.cell(0, 6, f": {_format_rp(hasil.get('total_nominal', 0))}", ln=True)
        _pdf.ln(5)

        # =========================================================
        # SALES, BTSB, NSB
        # =========================================================
        if net_sales > 0:
                _total_selisih = hasil.get("_total_selisih_bulan", 0)
                _total_rak = hasil.get("_total_rak_bulan", 0)
                _calc = _hitung_btsb_nsb(net_sales, _total_selisih)
            
                _pdf.set_font("Helvetica", "B", 12)
                _pdf.set_text_color(30, 20, 60)
                _pdf.cell(0, 8, "ANALISIS BTSB & NSB (BULAN INI)", ln=True)
                _pdf.set_text_color(0, 0, 0)
                _pdf.set_font("Helvetica", "", 10)
            
                _pdf.cell(70, 6, "Net Sales Bulan Ini")
                _pdf.cell(0, 6, f": {_format_rp(net_sales)}", ln=True)
                _pdf.cell(70, 6, "BTSB (0,15%)")
                _pdf.cell(0, 6, f": {_format_rp(_calc['btsb'])}", ln=True)
                _pdf.cell(70, 6, "Total Selisih Bulan")
                _pdf.cell(0, 6, f": {_format_rp(_calc['selisih'])}", ln=True)
                _pdf.cell(70, 6, "NSB (beban personil)")
                _pdf.cell(0, 6, f": {_format_rp(_calc['nsb'])}", ln=True)
                _pdf.cell(70, 6, "Total Rak di-SO Bulan Ini")
                _pdf.cell(0, 6, f": {_total_rak} rak", ln=True)
                _pdf.cell(70, 6, "Status")
                _pdf.set_font("Helvetica", "B", 10)
                if _calc["status"] == "OVER":
                    _pdf.set_text_color(200, 50, 50)
                else:
                    _pdf.set_text_color(50, 150, 50)
                _pdf.cell(0, 6, f": {_calc['status']}", ln=True)
                _pdf.set_text_color(0, 0, 0)
                _pdf.set_font("Helvetica", "", 10)
                _pdf.ln(5)
                
        # =========================================================
        # TOP 5 MINUS & TOP 5 PLUS
        # =========================================================
        _list_rak = hasil.get("list_rak", [])
        if _list_rak:
            _df = pd.DataFrame(_list_rak)
            _df["total"] = pd.to_numeric(_df["total"], errors="coerce").fillna(0)

            _top_minus = _df.nsmallest(5, "total")
            _top_plus = _df.nlargest(5, "total")

            _pdf.set_font("Helvetica", "B", 12)
            _pdf.set_text_color(30, 20, 60)
            _pdf.cell(0, 8, "TOP 5 MINUS TERTINGGI", ln=True)
            _pdf.set_text_color(0, 0, 0)

            _pdf.set_font("Helvetica", "B", 9)
            _pdf.set_fill_color(200, 50, 50)
            _pdf.set_text_color(255, 255, 255)
            _pdf.cell(40, 7, "RAK", border=1, fill=True, align="C")
            _pdf.cell(60, 7, "NOMINAL", border=1, fill=True, align="C")
            _pdf.cell(50, 7, "PIC", border=1, fill=True, align="C")
            _pdf.cell(40, 7, "TANGGAL", border=1, fill=True, align="C", ln=True)

            _pdf.set_font("Helvetica", "", 9)
            _pdf.set_text_color(0, 0, 0)
            for _, _r in _top_minus.iterrows():
                _pdf.cell(40, 6, str(_r.get("rak_id", "-"))[:15], border=1, align="C")
                _pdf.cell(60, 6, _format_rp(_r.get("total", 0)), border=1, align="R")
                _pdf.cell(50, 6, str(_r.get("pic", "-"))[:20], border=1, align="C")
                _pdf.cell(40, 6, str(_r.get("tanggal", "-"))[:10], border=1, align="C", ln=True)
            _pdf.ln(4)

            _pdf.set_font("Helvetica", "B", 12)
            _pdf.set_text_color(30, 20, 60)
            _pdf.cell(0, 8, "TOP 5 PLUS TERTINGGI", ln=True)
            _pdf.set_text_color(0, 0, 0)

            _pdf.set_font("Helvetica", "B", 9)
            _pdf.set_fill_color(50, 150, 50)
            _pdf.set_text_color(255, 255, 255)
            _pdf.cell(40, 7, "RAK", border=1, fill=True, align="C")
            _pdf.cell(60, 7, "NOMINAL", border=1, fill=True, align="C")
            _pdf.cell(50, 7, "PIC", border=1, fill=True, align="C")
            _pdf.cell(40, 7, "TANGGAL", border=1, fill=True, align="C", ln=True)

            _pdf.set_font("Helvetica", "", 9)
            _pdf.set_text_color(0, 0, 0)
            for _, _r in _top_plus.iterrows():
                _pdf.cell(40, 6, str(_r.get("rak_id", "-"))[:15], border=1, align="C")
                _pdf.cell(60, 6, _format_rp(_r.get("total", 0)), border=1, align="R")
                _pdf.cell(50, 6, str(_r.get("pic", "-"))[:20], border=1, align="C")
                _pdf.cell(40, 6, str(_r.get("tanggal", "-"))[:10], border=1, align="C", ln=True)
            _pdf.ln(4)

        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        print(f"[EXPORT_PDF ERROR] {e}")
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
    """Export rekap SO jadi gambar pakai html2pic (no browser)."""
    try:
        from html2pic import Html2Pic

        _list_rak = hasil.get("list_rak", [])
        if not _list_rak:
            return None

        # Build HTML
        _rows_html = ""
        for _r in _list_rak:
            _nom = _format_nominal(_r.get("total", 0))
            _color = "#C83232" if _nom < 0 else "#329632"
            _sign = "+" if _nom >= 0 else "-"
            _rows_html += f"""
            <tr>
                <td>{_r.get('rak_id', '-')}</td>
                <td style="color:{_color}; text-align:right; font-weight:bold;">
                    {_sign}Rp {abs(_nom):,}
                </td>
                <td>{_r.get('pic', '-')}</td>
            </tr>"""

        _html = f"""
        <html>
        <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #1E143C;
                padding: 20px;
                color: #F5E6D3;
            }}
            .header {{
                text-align: center;
                margin-bottom: 20px;
            }}
            .header h1 {{
                color: #7FB99B;
                font-size: 22px;
                margin: 0;
                letter-spacing: 2px;
            }}
            .header p {{
                color: #E8B189;
                font-size: 12px;
                margin: 4px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: #2A1F4A;
                border-radius: 8px;
                overflow: hidden;
            }}
            th {{
                background: #7FB99B;
                color: #1E143C;
                padding: 10px;
                text-align: left;
                font-size: 12px;
                font-weight: bold;
            }}
            td {{
                padding: 8px 10px;
                border-bottom: 1px solid #3A2F5A;
                font-size: 12px;
            }}
            .footer {{
                margin-top: 15px;
                text-align: right;
                font-size: 11px;
                color: #A89B8E;
            }}
        </style>
        </head>
        <body>
            <div class="header">
                <h1>LAPORAN STOCK OPNAME</h1>
                <p>Toko C383 — {hasil.get('periode', '-')}</p>
            </div>
            <table>
                <tr><th>RAK</th><th>NOMINAL</th><th>PIC</th></tr>
                {_rows_html}
            </table>
            <div class="footer">
                Total: {_format_rp(hasil.get('total_nominal', 0))} | {hasil.get('total_rak', 0)} rak
            </div>
        </body>
        </html>
        """

        _renderer = Html2Pic(_html)
        _image = _renderer.render()
        _image.save(filename)
        return filename
    except ImportError:
        print("[EXPORT_IMG] html2pic gak keinstall")
        return None
    except Exception as e:
        print(f"[EXPORT_IMG ERROR] {e}")
        return None