"""
Yui Export — Export rekap SO ke PDF, Excel, Gambar.
"""

import io
import pandas as pd
from datetime import datetime
from fpdf import FPDF


def export_rekap_pdf(hasil, filename="rekap_so.pdf"):
    """Export rekap SO jadi PDF pakai fpdf2."""
    try:
        _pdf = FPDF()
        _pdf.add_page()
        
        # Judul
        _pdf.set_font("Helvetica", "B", 16)
        _pdf.cell(0, 10, "REKAP SO TOKO C383", ln=True, align="C")
        _pdf.set_font("Helvetica", "", 10)
        _pdf.cell(0, 6, f"Periode: {hasil['periode']}", ln=True, align="C")
        _pdf.ln(5)
        
        # Summary
        _pdf.set_font("Helvetica", "B", 12)
        _pdf.cell(0, 8, "RINGKASAN", ln=True)
        _pdf.set_font("Helvetica", "", 10)
        _pdf.cell(0, 6, f"Total Rak: {hasil['total_rak']}", ln=True)
        _pdf.cell(0, 6, f"Total Item: {hasil['total_item']}", ln=True)
        _nom = hasil['total_nominal']
        _sign = "+" if _nom >= 0 else "-"
        _pdf.cell(0, 6, f"Total Nominal: {_sign}Rp {int(abs(_nom)):,}".replace(",", "."), ln=True)
        _pdf.ln(5)
        
        # Tabel detail per rak
        _pdf.set_font("Helvetica", "B", 10)
        _pdf.cell(40, 8, "RAK", border=1)
        _pdf.cell(50, 8, "NOMINAL", border=1)
        _pdf.cell(50, 8, "PIC", border=1)
        _pdf.cell(40, 8, "TANGGAL", border=1, ln=True)
        
        _pdf.set_font("Helvetica", "", 9)
        for _r in hasil.get("list_rak", []):
            _nom_r = _r.get("total", 0)
            _sign_r = "+" if _nom_r >= 0 else "-"
            _pdf.cell(40, 7, str(_r.get("rak_id", "-"))[:15], border=1)
            _pdf.cell(50, 7, f"{_sign_r}Rp {int(abs(_nom_r)):,}".replace(",", "."), border=1)
            _pdf.cell(50, 7, str(_r.get("pic", "-"))[:20], border=1)
            _pdf.cell(40, 7, str(_r.get("tanggal", "-"))[:10], border=1, ln=True)
        
        # Footer
        _pdf.ln(10)
        _pdf.set_font("Helvetica", "I", 8)
        _pdf.cell(0, 6, f"Dicetak oleh Yui pada {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")
        
        # Output ke bytes
        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        print(f"[EXPORT_PDF ERROR] {e}")
        return None


def export_rekap_image(hasil, filename="rekap_so.png"):
    """Export rekap SO jadi gambar pakai table-to-image."""
    try:
        from table_to_image import render
        
        _df = pd.DataFrame(hasil.get("list_rak", []))
        if _df.empty:
            return None
        
        _df = _df.rename(columns={
            "rak_id": "Rak",
            "total": "Nominal",
            "pic": "PIC",
        })
        
        # Format nominal
        _df["Nominal"] = _df["Nominal"].apply(
            lambda x: f"Rp {int(x):,}".replace(",", ".")
        )
        
        render(
            _df,
            filename,
            font_size=14,
            header_bg_color=(127, 185, 155),
            header_text_color=(255, 255, 255),
            cell_bg_color=(255, 255, 255),
            cell_text_color=(0, 0, 0),
        )
        return filename
    except ImportError:
        print("[EXPORT_IMG] table-to-image gak keinstall")
        return None
    except Exception as e:
        print(f"[EXPORT_IMG ERROR] {e}")
        return None