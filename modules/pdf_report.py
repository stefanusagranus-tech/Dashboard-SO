"""
PDF Report Generator — Formal & Profesional
============================================
Render PDF dari data AI + tabel langsung dari DB.

Fitur:
- Header formal dengan warna
- Parse markdown (heading, list, bold)
- Strip emoji (gak support di fpdf2)
- Tabel SO per rak (langsung dari DB, gak lewat AI)
- Footer dengan timestamp
"""

import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


# === WARNA ===
_C_PRIMARY = (76, 29, 149)     # ungu gelap
_C_ACCENT = (168, 85, 247)     # ungu terang
_C_DARK = (30, 30, 50)
_C_GRAY = (100, 100, 100)
_C_LIGHT = (245, 240, 255)
_C_RED = (200, 50, 50)
_C_GREEN = (50, 150, 80)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _fmt_rp(value):
    """Format Rupiah: Rp 1.234.567"""
    try:
        _v = float(value)
        _sign = "-" if _v < 0 else ""
        _abs = abs(_v)
        _formatted = f"{int(_abs):,}".replace(",", ".")
        return f"{_sign}Rp {_formatted}"
    except Exception:
        return "Rp 0"

def _sanitize_text(text):
    """Ganti karakter unicode gak didukung Helvetica jadi ASCII."""
    _replacements = {
        "—": "-", "–": "-", "−": "-", "…": "...",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "•": "-", "·": "-", "→": "->", "←": "<-",
        "≥": ">=", "≤": "<=", "×": "x", "÷": "/",
        "≈": "~=", "≠": "!=",
        "\u00a0": " ", "\u200b": "",
    }
    _result = text
    for _k, _v in _replacements.items():
        _result = _result.replace(_k, _v)
    _result = "".join(c if ord(c) < 256 else "" for c in _result)
    return _result

def _strip_emoji(text):
    """Hapus emoji & sanitize unicode."""
    _result = []
    for _ch in text:
        _cat = unicodedata.category(_ch)
        if _cat in ("So", "Sk", "Cs", "Cn"):
            continue
        if ord(_ch) > 0x2600:
            continue
        _result.append(_ch)
    return _sanitize_text("".join(_result))

# =========================================================
# 📄 MAIN: GENERATE PDF
# =========================================================
def generate_pdf(
    ai_content: str,
    so_data: list,
    period_label: str,
    period_type: str = "hari",
    filename: str = "laporan.pdf",
) -> dict:
    """
    Generate PDF formal.
    
    Args:
        ai_content: text markdown dari AI (summary + insight)
        so_data: list of dict dari DB (so_rak_harian)
        period_label: "Harian — 03/10/2026"
        period_type: "hari" | "minggu" | "bulan"
        filename: nama file
    
    Returns:
        dict {success, content (bytes), filename, mime}
    """
    if not FPDF_AVAILABLE:
        return {"success": False, "content": "fpdf2 gak keinstall", "filename": "", "mime": ""}

    try:
        _pdf = FPDF(orientation="P", unit="mm", format="A4")
        _pdf.set_margins(left=15, top=15, right=15)
        _pdf.set_auto_page_break(auto=True, margin=20)
        _pdf.add_page()

        # === HEADER ===
        _render_header(_pdf, period_label)

        # === AI CONTENT (summary + insight) ===
        _render_ai_content(_pdf, ai_content)

        # === SO TABLE (dari DB) ===
        if so_data:
            _render_so_table(_pdf, so_data, period_type)

        # === FOOTER ===
        _render_footer(_pdf)

        # === OUTPUT ===
        _out = _pdf.output(dest="S")
        _pdf_bytes = _out.encode("latin-1") if isinstance(_out, str) else bytes(_out)

        return {
            "success": True,
            "content": _pdf_bytes,
            "filename": filename,
            "mime": "application/pdf",
        }
    except Exception as _e:
        import traceback
        print(f"[PDF GEN ERROR] {_e}")
        print(traceback.format_exc())
        return {"success": False, "content": f"PDF error: {_e}", "filename": "", "mime": ""}


# =========================================================
# 🎨 RENDER SECTIONS
# =========================================================
def _render_header(pdf, period_label):
    """Header dengan banner warna."""
    pdf.set_fill_color(*_C_PRIMARY)
    pdf.rect(0, 0, 210, 28, "F")

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 8)
    pdf.cell(0, 10, "LAPORAN TOKO C383", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(15, 18)
    pdf.cell(0, 5, f"Karang Satria - {period_label}", ln=True)

    pdf.set_text_color(*_C_DARK)
    pdf.ln(15)


def _render_ai_content(pdf, content_text):
    """Render markdown dari AI."""
    for _line in content_text.split("\n"):
        _line_clean = _strip_emoji(_line).strip()

        if not _line_clean:
            pdf.ln(2)
            continue

        # Heading
        if _line_clean.startswith("#"):
            _level = len(_line_clean) - len(_line_clean.lstrip("#"))
            _text = _line_clean.lstrip("#").strip().replace("**", "").replace("*", "")

            if _level == 1:
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(*_C_PRIMARY)
            elif _level == 2:
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(*_C_PRIMARY)
            else:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*_C_DARK)

            pdf.ln(2)
            pdf.multi_cell(0, 6, _text)

            if _level <= 2:
                pdf.set_draw_color(*_C_ACCENT)
                pdf.set_line_width(0.4)
                pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
                pdf.ln(3)

            pdf.set_text_color(*_C_DARK)
            continue

        # Bullet list
        if _line_clean.startswith(("- ", "* ", "• ")):
            _text = _line_clean[2:].strip().replace("**", "").replace("*", "")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(20)
            pdf.multi_cell(175, 5.5, f"-  {_text}")
            continue

        # Numbered list
        _match_num = re.match(r'^(\d+)\.\s+(.+)', _line_clean)
        if _match_num:
            _num = _match_num.group(1)
            _text = _match_num.group(2).replace("**", "").replace("*", "")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(20)
            pdf.multi_cell(175, 5.5, f"{_num}.  {_text}")
            continue

        # Paragraf biasa
        _text = _line_clean.replace("**", "").replace("*", "")
        if len(_text) > 150:
            _text = _text[:150]
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_C_DARK)
        pdf.multi_cell(0, 5.5, _text)


def _render_so_table(pdf, so_data, period_type):
    """Render tabel SO per rak."""
    pdf.ln(5)

    # Heading tabel
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.cell(0, 7, "DAFTAR STOCK OPNAME", ln=True)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)

    # Info jumlah
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_C_GRAY)
    _total = len(so_data)
    _limit_info = ""
    if period_type == "minggu":
        _limit_info = f" (menampilkan top 5 dari {_total})"
    elif period_type == "bulan":
        _limit_info = f" (menampilkan top 10 dari {_total})"

    pdf.cell(0, 5, f"Total rak di-SO: {_total} rak{_limit_info}", ln=True)
    pdf.ln(2)

    # Filter data
    if period_type == "minggu":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:5]
    elif period_type == "bulan":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:10]
    else:
        _rows = so_data  # semua rak (harian biasanya cuma 3)

    # === HEADER TABEL ===
    _col_w = [30, 30, 80, 35]
    _headers = ["Tanggal", "Rak", "Nominal", "PIC"]

    pdf.set_fill_color(*_C_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)

    pdf.set_x(15)
    for _i, _h in enumerate(_headers):
        pdf.cell(_col_w[_i], 8, _h, border=1, fill=True, align="C")
    pdf.ln(8)

    # === ISI TABEL ===
    pdf.set_font("Helvetica", "", 9)
    for _idx, _r in enumerate(_rows):
        _tgl = _r.get("so_date", "-")
        _rak = _r.get("rak_id", "-")
        _nom = float(_r.get("nominal_adjust", 0))
        _pic = _r.get("pic", "") or "-"

        # Format tanggal
        try:
            _tgl_fmt = datetime.strptime(_tgl, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            _tgl_fmt = _tgl

        # Warna selang-seling
        if _idx % 2 == 0:
            pdf.set_fill_color(*_C_LIGHT)
            _fill = True
        else:
            pdf.set_fill_color(255, 255, 255)
            _fill = False

        # Warna nominal (merah kalau minus, hijau kalau plus)
        if _nom < 0:
            pdf.set_text_color(*_C_RED)
        elif _nom > 0:
            pdf.set_text_color(*_C_GREEN)
        else:
            pdf.set_text_color(*_C_DARK)

        pdf.set_x(15)
        pdf.cell(_col_w[0], 7, _tgl_fmt, border=1, fill=_fill, align="C")
        pdf.cell(_col_w[1], 7, _rak, border=1, fill=_fill, align="C")
        pdf.cell(_col_w[2], 7, _fmt_rp(_nom), border=1, fill=_fill, align="R")
        pdf.cell(_col_w[3], 7, _pic[:20], border=1, fill=_fill, align="C")
        pdf.ln(7)

    pdf.ln(3)

    # === TOTAL ===
    _total_nom = sum(float(r.get("nominal_adjust", 0)) for r in so_data)
    pdf.set_font("Helvetica", "B", 10)
    if _total_nom < 0:
        pdf.set_text_color(*_C_RED)
    elif _total_nom > 0:
        pdf.set_text_color(*_C_GREEN)
    else:
        pdf.set_text_color(*_C_DARK)

    pdf.set_x(15)
    pdf.cell(sum(_col_w[:2]), 8, "TOTAL", border=1, align="C")
    pdf.cell(_col_w[2], 8, _fmt_rp(_total_nom), border=1, align="R")
    pdf.cell(_col_w[3], 8, "", border=1)
    pdf.ln(8)


def _render_footer(pdf):
    """Footer dengan timestamp."""
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_C_GRAY)
    pdf.cell(
        0, 5,
        f"Generated: {_now_jkt().strftime('%d/%m/%Y %H:%M')} WIB | Toko C383 - Karang Satria",
        align="C",
    )
