"""
PDF Report Generator v2.1 — Formal & Profesional
==================================================
Fix: Not enough horizontal space error
- Reset X position di setiap section
- Margin aman
- Layout lebih lega
"""

import io
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
_C_PRIMARY = (76, 29, 149)
_C_ACCENT = (168, 85, 247)
_C_DARK = (30, 30, 50)
_C_GRAY = (100, 100, 100)
_C_LIGHT = (245, 240, 255)
_C_RED = (200, 50, 50)
_C_GREEN = (50, 150, 80)
_C_BLUE = (50, 100, 200)

# === LAYOUT ===
_PAGE_W = 210
_MARGIN_L = 18
_MARGIN_R = 18
_CONTENT_W = _PAGE_W - _MARGIN_L - _MARGIN_R  # = 174

_NAMA_BULAN = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _fmt_rp(value):
    try:
        _v = float(value)
        _sign = "-" if _v < 0 else ""
        _abs = abs(_v)
        _formatted = f"{int(_abs):,}".replace(",", ".")
        return f"{_sign}Rp {_formatted}"
    except Exception:
        return "Rp 0"


def _fmt_tgl(tgl_str):
    try:
        _dt = datetime.strptime(tgl_str, "%Y-%m-%d")
        return f"{_dt.day} {_NAMA_BULAN[_dt.month]} {_dt.year}"
    except Exception:
        return tgl_str


def _fmt_tgl_short(tgl_str):
    try:
        _dt = datetime.strptime(tgl_str, "%Y-%m-%d")
        return _dt.strftime("%d/%m/%Y")
    except Exception:
        return tgl_str


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
# 📊 CHART GENERATORS
# =========================================================
def _make_pie_chart(sudah_so, belum_so):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _fig, _ax = plt.subplots(figsize=(4.5, 3), dpi=100)
        _labels = ["Sudah SO", "Belum SO"]
        _sizes = [sudah_so, belum_so]
        _colors = ["#7FB99B", "#E88B8B"]

        if sum(_sizes) == 0:
            _sizes = [1, 1]

        _ax.pie(
            _sizes, labels=_labels, colors=_colors,
            autopct="%1.1f%%", startangle=90,
            textprops={"fontsize": 9},
        )
        _ax.axis("equal")
        _ax.set_title(f"Rasio SO ({sudah_so} dari {sudah_so + belum_so} rak)", fontsize=10)

        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as _e:
        print(f"[CHART PIE ERROR] {_e}")
        return None


def _make_bar_chart(adjust_so, btsb):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _fig, _ax = plt.subplots(figsize=(4.5, 3), dpi=100)
        _labels = ["Adjust SO", "BTSB"]
        _values = [abs(adjust_so), abs(btsb)]
        _colors = ["#E88B8B", "#7FB99B"]

        _bars = _ax.bar(_labels, _values, color=_colors, edgecolor="#333", linewidth=0.8)

        for _bar, _val in zip(_bars, _values):
            _ax.text(
                _bar.get_x() + _bar.get_width() / 2,
                _bar.get_height(),
                f"Rp {int(_val):,}".replace(",", "."),
                ha="center", va="bottom", fontsize=8,
            )

        _ax.set_ylabel("Rupiah", fontsize=9)
        _ax.set_title("Adjust SO vs BTSB", fontsize=10)
        _ax.tick_params(axis="both", labelsize=8)
        _ax.spines["top"].set_visible(False)
        _ax.spines["right"].set_visible(False)

        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", bbox_inches="tight", facecolor="white")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as _e:
        print(f"[CHART BAR ERROR] {_e}")
        return None


# =========================================================
# 📄 MAIN
# =========================================================
def generate_pdf(
    ai_content: str,
    so_data: list,
    period_label: str,
    period_type: str = "hari",
    filename: str = "laporan.pdf",
    extra_stats: dict = None,
) -> dict:
    if not FPDF_AVAILABLE:
        return {"success": False, "content": "fpdf2 gak keinstall", "filename": "", "mime": ""}

    try:
        _pdf = FPDF(orientation="P", unit="mm", format="A4")
        _pdf.set_margins(left=_MARGIN_L, top=18, right=_MARGIN_R)
        _pdf.set_auto_page_break(auto=True, margin=25)
        _pdf.add_page()

        _render_header(_pdf, period_label)
        _render_ai_content(_pdf, ai_content)

        if extra_stats:
            _render_charts_section(_pdf, extra_stats)

        if so_data:
            _render_so_table(_pdf, so_data, period_type)

        _render_all_footers(_pdf)

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
# 🎨 RENDER — SEMUA SECTION RESET X POSITION
# =========================================================
def _reset_x(pdf):
    """Reset X ke margin kiri — kunci biar gak error."""
    pdf.set_x(_MARGIN_L)


def _render_header(pdf, period_label):
    pdf.set_fill_color(*_C_PRIMARY)
    pdf.rect(0, 0, _PAGE_W, 32, "F")

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(_MARGIN_L, 8)
    pdf.cell(_CONTENT_W, 10, "LAPORAN STOCK OPNAME", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(_MARGIN_L)
    pdf.cell(_CONTENT_W, 5, "Toko C383 - Karang Satria", ln=True)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(_MARGIN_L)
    pdf.cell(_CONTENT_W, 5, f"Periode: {period_label}", ln=True)

    pdf.set_text_color(*_C_DARK)
    pdf.ln(18)
    _reset_x(pdf)


def _render_ai_content(pdf, content_text):
    for _line in content_text.split("\n"):
        _line_clean = _strip_emoji(_line).strip()

        if not _line_clean:
            pdf.ln(2)
            _reset_x(pdf)
            continue

        # HEADING
        if _line_clean.startswith("#"):
            _level = len(_line_clean) - len(_line_clean.lstrip("#"))
            _text = _line_clean.lstrip("#").strip().replace("**", "").replace("*", "")

            pdf.ln(3)
            _reset_x(pdf)

            if _level == 1:
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(*_C_PRIMARY)
            elif _level == 2:
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(*_C_PRIMARY)
            else:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*_C_DARK)

            pdf.multi_cell(_CONTENT_W, 7, _text)

            if _level <= 2:
                pdf.set_draw_color(*_C_ACCENT)
                pdf.set_line_width(0.4)
                pdf.line(_MARGIN_L, pdf.get_y() + 1, _PAGE_W - _MARGIN_R, pdf.get_y() + 1)
                pdf.ln(4)

            pdf.set_text_color(*_C_DARK)
            _reset_x(pdf)
            continue

        # BULLET
        if _line_clean.startswith(("- ", "* ")):
            _text = _line_clean[2:].strip().replace("**", "").replace("*", "")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(_MARGIN_L + 4)
            pdf.multi_cell(_CONTENT_W - 4, 6, f"-  {_text}")
            pdf.ln(1)
            _reset_x(pdf)
            continue

        # NUMBERED
        _match_num = re.match(r'^(\d+)\.\s+(.+)', _line_clean)
        if _match_num:
            _num = _match_num.group(1)
            _text = _match_num.group(2).replace("**", "").replace("*", "")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(_MARGIN_L + 4)
            pdf.multi_cell(_CONTENT_W - 4, 6, f"{_num}.  {_text}")
            pdf.ln(1)
            _reset_x(pdf)
            continue

        # PARAGRAF
        _text = _line_clean.replace("**", "").replace("*", "")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_C_DARK)
        _reset_x(pdf)
        pdf.multi_cell(_CONTENT_W, 6, _text)
        pdf.ln(1)
        _reset_x(pdf)


def _render_charts_section(pdf, stats):
    _sudah = stats.get("sudah_so", 0)
    _belum = stats.get("belum_so", 0)
    _adjust = stats.get("adjust_so", 0)
    _btsb = stats.get("btsb", 0)

    if _sudah + _belum == 0 and _adjust == 0 and _btsb == 0:
        return

    if pdf.get_y() > 200:
        pdf.add_page()

    pdf.ln(3)
    _reset_x(pdf)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.cell(_CONTENT_W, 7, "GRAFIK ANALISIS", ln=True)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.4)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(4)
    _reset_x(pdf)

    # PIE CHART
    _pie_buf = _make_pie_chart(_sudah, _belum)
    if _pie_buf:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_C_DARK)
        _reset_x(pdf)
        pdf.cell(_CONTENT_W, 6, "1. Rasio Stock Opname", ln=True)
        pdf.ln(1)
        _reset_x(pdf)
        try:
            pdf.image(_pie_buf, x=_MARGIN_L + 35, w=100)
            pdf.ln(3)
        except Exception as _e:
            print(f"[PDF IMG PIE ERROR] {_e}")
        _reset_x(pdf)

    # BAR CHART
    _bar_buf = _make_bar_chart(_adjust, _btsb)
    if _bar_buf:
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_C_DARK)
        _reset_x(pdf)
        pdf.cell(_CONTENT_W, 6, "2. Perbandingan Adjust SO vs BTSB", ln=True)
        pdf.ln(1)
        _reset_x(pdf)
        try:
            pdf.image(_bar_buf, x=_MARGIN_L + 35, w=100)
            pdf.ln(3)
        except Exception as _e:
            print(f"[PDF IMG BAR ERROR] {_e}")
        _reset_x(pdf)


def _render_so_table(pdf, so_data, period_type):
    if pdf.get_y() > 200:
        pdf.add_page()

    pdf.ln(5)
    _reset_x(pdf)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.cell(_CONTENT_W, 7, "DAFTAR STOCK OPNAME", ln=True)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.4)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(3)
    _reset_x(pdf)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_C_GRAY)
    _total = len(so_data)
    _limit_info = ""
    if period_type == "minggu":
        _limit_info = f" (menampilkan top 5 dari {_total})"
    elif period_type == "bulan":
        _limit_info = f" (menampilkan top 10 dari {_total})"

    pdf.cell(_CONTENT_W, 5, f"Total rak di-SO: {_total} rak{_limit_info}", ln=True)
    pdf.ln(2)
    _reset_x(pdf)

    if period_type == "minggu":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:5]
    elif period_type == "bulan":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:10]
    else:
        _rows = so_data

    # Kolom: total = 174
    _col_w = [35, 30, 65, 44]
    _headers = ["Tanggal", "Rak", "Nominal", "PIC"]

    pdf.set_fill_color(*_C_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    _reset_x(pdf)

    for _i, _h in enumerate(_headers):
        pdf.cell(_col_w[_i], 8, _h, border=1, fill=True, align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 9)
    for _idx, _r in enumerate(_rows):
        _tgl = _r.get("so_date", "-")
        _rak = _r.get("rak_id", "-")
        _nom = float(_r.get("nominal_adjust", 0))
        _pic = _r.get("pic", "") or "-"

        _tgl_fmt = _fmt_tgl_short(_tgl)

        if _idx % 2 == 0:
            pdf.set_fill_color(*_C_LIGHT)
            _fill = True
        else:
            pdf.set_fill_color(255, 255, 255)
            _fill = False

        if _nom < 0:
            pdf.set_text_color(*_C_RED)
        elif _nom > 0:
            pdf.set_text_color(*_C_GREEN)
        else:
            pdf.set_text_color(*_C_DARK)

        _reset_x(pdf)
        pdf.cell(_col_w[0], 7, _tgl_fmt, border=1, fill=_fill, align="C")
        pdf.cell(_col_w[1], 7, _rak, border=1, fill=_fill, align="C")
        pdf.cell(_col_w[2], 7, _fmt_rp(_nom), border=1, fill=_fill, align="R")
        pdf.cell(_col_w[3], 7, _pic[:20], border=1, fill=_fill, align="C")
        pdf.ln(7)

    # Total
    _total_nom = sum(float(r.get("nominal_adjust", 0)) for r in so_data)
    if _total_nom < 0:
        pdf.set_text_color(*_C_RED)
    elif _total_nom > 0:
        pdf.set_text_color(*_C_GREEN)
    else:
        pdf.set_text_color(*_C_DARK)

    pdf.set_font("Helvetica", "B", 10)
    _reset_x(pdf)
    pdf.cell(sum(_col_w[:2]), 8, "TOTAL", border=1, align="C")
    pdf.cell(_col_w[2], 8, _fmt_rp(_total_nom), border=1, align="R")
    pdf.cell(_col_w[3], 8, "", border=1)
    pdf.ln(8)


def _render_all_footers(pdf):
    """Render footer di SETIAP halaman."""
    try:
        _total_pages = pdf.pages_count() if callable(getattr(pdf, "pages_count", None)) else pdf.pages_count if hasattr(pdf, "pages_count") else 1
    except Exception:
        _total_pages = 1

    _current_page = pdf.page_no()
    _y_backup = pdf.get_y()

    # Footer utama
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_C_GRAY)
    pdf.set_x(_MARGIN_L)

    _footer_text = (
        f"Toko C383 - Karang Satria | "
        f"Dicetak: {_now_jkt().strftime('%d/%m/%Y %H:%M')} WIB"
    )
    pdf.cell(_CONTENT_W, 5, _footer_text, align="C")

    # Page number
    pdf.set_y(-13)
    pdf.set_x(_MARGIN_L)
    pdf.cell(_CONTENT_W, 5, f"Halaman {_current_page}", align="C")

    pdf.set_y(_y_backup)