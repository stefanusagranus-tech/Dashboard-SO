"""
PDF Report Generator v4 — Unicode Safe
========================================
Pake font DejaVu Unicode — anti-error, anti-emoji bocor.

Fix:
- DejaVuSans font (support Unicode: em-dash, bullet, basic emoji)
- Fallback Helvetica kalau DejaVu gak ada
- Validasi tahun (2024-2100)
- Layout profesional: banner, card metric, grafik 2 kolom
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
_C_PRIMARY = (46, 30, 120)
_C_ACCENT = (120, 80, 220)
_C_DARK = (30, 30, 50)
_C_GRAY = (100, 100, 100)
_C_LIGHT = (245, 243, 255)
_C_RED = (220, 60, 60)
_C_GREEN = (50, 160, 90)
_C_ORANGE = (245, 150, 50)

# === LAYOUT ===
_PAGE_W = 210
_PAGE_H = 297
_MARGIN_L = 15
_MARGIN_R = 15
_CONTENT_W = _PAGE_W - _MARGIN_L - _MARGIN_R

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


def _fmt_tgl_short(tgl_str):
    """Format tanggal: '2026-10-04' -> '04/10/2026'. Validasi tahun."""
    if not tgl_str:
        return "-"
    try:
        _tgl_clean = str(tgl_str).strip()[:10]
        _dt = datetime.strptime(_tgl_clean, "%Y-%m-%d")
        _now = _now_jkt()
        if _dt.year < 2024 or _dt.year > 2100:
            print(f"[PDF DATE FIX] Tahun aneh: {_dt.year} -> {_now.year}")
            _dt = _dt.replace(year=_now.year)
        return _dt.strftime("%d/%m/%Y")
    except Exception as _e:
        print(f"[PDF DATE ERROR] {_e} | input: {tgl_str}")
        return str(tgl_str)[:10]


def _clean_text(text):
    """Minimal cleanup: hapus char control, jaga unicode lain."""
    if not text:
        return ""
    _result = []
    for _ch in text:
        _cat = unicodedata.category(_ch)
        if _cat in ("Cc", "Cs", "Cn", "Co"):
            if _ch in "\n\t":
                _result.append(_ch)
            continue
        _result.append(_ch)
    return "".join(_result)


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
        _ax.set_title(f"Rasio SO ({sudah_so} dari {sudah_so + belum_so} rak)", fontsize=10, color="#2E1E78")

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
        _ax.set_title("Adjust SO vs BTSB", fontsize=10, color="#2E1E78")
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
# 🔧 PARSE AI CONTENT
# =========================================================
def _parse_sections(content_text):
    """Parse AI content jadi dict per section."""
    _sections = {
        "ringkasan": "",
        "analisis_spd": "",
        "analisis_btsb": "",
        "insight": "",
        "rekomendasi": "",
        "other": "",
    }

    _current = "other"
    _buffer = []

    for _line in content_text.split("\n"):
        _line_strip = _line.strip()
        _line_lower = _line_strip.lower()

        if _line_strip.startswith("#"):
            if _buffer:
                _sections[_current] += "\n".join(_buffer) + "\n"
                _buffer = []

            if "ringkasan" in _line_lower or "eksekutif" in _line_lower:
                _current = "ringkasan"
            elif "spd" in _line_lower or "sales" in _line_lower:
                _current = "analisis_spd"
            elif "btsb" in _line_lower or "nsb" in _line_lower:
                _current = "analisis_btsb"
            elif "insight" in _line_lower or "temuan" in _line_lower:
                _current = "insight"
            elif "rekomendasi" in _line_lower:
                _current = "rekomendasi"
            else:
                _current = "other"
            continue

        _buffer.append(_line)

    if _buffer:
        _sections[_current] += "\n".join(_buffer) + "\n"

    return _sections
# =========================================================
# 📄 MAIN: GENERATE PDF
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
        _pdf.set_margins(left=_MARGIN_L, top=15, right=_MARGIN_R)
        _pdf.set_auto_page_break(auto=True, margin=10)
        _pdf.add_page()

        # ✅ REGISTER FONT UNICODE (DejaVu)
        _FONT_NAME = "Helvetica"
        _FONT_PATHS = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        _FONT_PATHS_B = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
        _FONT_PATHS_I = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Oblique.ttf",
        ]

        _font_reg = next((p for p in _FONT_PATHS if __import__("os").path.exists(p)), None)
        _font_bold = next((p for p in _FONT_PATHS_B if __import__("os").path.exists(p)), None)
        _font_italic = next((p for p in _FONT_PATHS_I if __import__("os").path.exists(p)), None)

        if _font_reg:
            try:
                _pdf.add_font("DejaVu", "", _font_reg)
                if _font_bold:
                    _pdf.add_font("DejaVu", "B", _font_bold)
                if _font_italic:
                    _pdf.add_font("DejaVu", "I", _font_italic)
                _FONT_NAME = "DejaVu"
                print(f"[PDF] DejaVu loaded OK: {_font_reg}")
            except Exception as _e_font:
                print(f"[PDF] DejaVu error, fallback Helvetica: {_e_font}")
        else:
            print("[PDF] DejaVu not found, fallback Helvetica")

        # Simpan font name di variabel global-ish (pake attribute)
        _pdf.font_name = _FONT_NAME

        # Parse AI content
        _sections = _parse_sections(ai_content)

        # ============================================
        # HALAMAN 1
        # ============================================
        _render_header_banner(_pdf, period_label, _FONT_NAME)
        _render_strip(_pdf, _FONT_NAME)

        if extra_stats:
            _render_metric_cards(_pdf, extra_stats, _FONT_NAME)

        if _sections["ringkasan"]:
            _render_section(_pdf, "Ringkasan Eksekutif", _sections["ringkasan"], _FONT_NAME)

        if _sections["analisis_spd"]:
            _render_section(_pdf, "Analisis SPD & Sales", _sections["analisis_spd"], _FONT_NAME)

        if extra_stats:
            _render_charts_2col(_pdf, extra_stats, _FONT_NAME)

        # ============================================
        # HALAMAN 2
        # ============================================
        _pdf.add_page()

        if _sections["analisis_btsb"]:
            _render_section(_pdf, "Analisis BTSB & NSB", _sections["analisis_btsb"], _FONT_NAME)

        if so_data:
            _render_so_table(_pdf, so_data, period_type, _FONT_NAME)

        if _sections["insight"]:
            _render_section(_pdf, "Insight & Temuan", _sections["insight"], _FONT_NAME)

        if _sections["rekomendasi"]:
            _render_section(_pdf, "Rekomendasi", _sections["rekomendasi"], _FONT_NAME)

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
def _reset_x(pdf):
    pdf.set_x(_MARGIN_L)


def _render_header_banner(pdf, period_label, font_name="Helvetica"):
    pdf.set_fill_color(*_C_PRIMARY)
    pdf.rect(0, 0, _PAGE_W, 42, "F")

    pdf.set_fill_color(*_C_ORANGE)
    pdf.rect(0, 0, 6, 42, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_name, "B", 26)
    pdf.set_y(10)
    pdf.set_x(_MARGIN_L + 6)
    pdf.cell(_CONTENT_W - 6, 12, "Laporan Stock Opname", align="L")

    pdf.set_font(font_name, "", 11)
    pdf.set_y(23)
    pdf.set_x(_MARGIN_L + 6)
    pdf.cell(_CONTENT_W - 6, 6, f"Periode: {period_label}", align="L")

    pdf.set_font(font_name, "", 10)
    pdf.set_y(30)
    pdf.set_x(_MARGIN_L + 6)
    pdf.cell(_CONTENT_W - 6, 5, "Toko C383 - Karang Satria", align="L")

    pdf.set_text_color(*_C_DARK)
    pdf.set_y(50)
    _reset_x(pdf)


def _render_strip(pdf, font_name="Helvetica"):
    _y = pdf.get_y()

    pdf.set_fill_color(*_C_PRIMARY)
    pdf.rect(0, _y, _PAGE_W, 8, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_name, "", 9)
    pdf.set_y(_y + 2)
    pdf.set_x(_MARGIN_L)
    pdf.cell(_CONTENT_W / 2, 4, "Disusun Oleh", align="L")

    pdf.set_x(_MARGIN_L + _CONTENT_W / 2)
    pdf.cell(_CONTENT_W / 2, 4, "Staff Karang Satria", align="R")

    pdf.set_text_color(*_C_DARK)
    pdf.set_y(_y + 14)
    _reset_x(pdf)


def _render_metric_cards(pdf, stats, font_name="Helvetica"):
    _sudah = stats.get("sudah_so", 0)
    _belum = stats.get("belum_so", 0)
    _adjust = stats.get("adjust_so", 0)
    _btsb = stats.get("btsb", 0)

    if _btsb > 0:
        _penggunaan = (abs(_adjust) / _btsb * 100)
    else:
        _penggunaan = 0

    if _penggunaan <= 80:
        _status_text = "AMAN"
        _status_color = _C_GREEN
    elif _penggunaan <= 100:
        _status_text = "WASPADA"
        _status_color = _C_ORANGE
    else:
        _status_text = "BAHAYA"
        _status_color = _C_RED

    _cards = [
        {"label": "Rak di-SO", "value": f"{_sudah}", "color": _C_GREEN},
        {"label": "Belum SO", "value": f"{_belum}", "color": _C_RED},
        {"label": "Adjust SO", "value": _fmt_rp(_adjust)[:15], "color": _C_ORANGE},
        {"label": "Status", "value": _status_text, "color": _status_color},
    ]

    _card_w = (_CONTENT_W - 6) / 4
    _card_h = 22
    _y_start = pdf.get_y()

    for _i, _card in enumerate(_cards):
        _x = _MARGIN_L + _i * (_card_w + 2)

        pdf.set_fill_color(*_card["color"])
        pdf.rect(_x, _y_start, _card_w, _card_h, "F")

        pdf.set_text_color(255, 255, 255)
        pdf.set_font(font_name, "", 8)
        pdf.set_xy(_x, _y_start + 3)
        pdf.cell(_card_w, 4, _card["label"], align="C")

        pdf.set_font(font_name, "B", 13)
        pdf.set_xy(_x, _y_start + 10)
        pdf.cell(_card_w, 8, _card["value"], align="C")

    pdf.set_text_color(*_C_DARK)
    pdf.set_y(_y_start + _card_h + 6)
    _reset_x(pdf)


def _render_section(pdf, title, content, font_name="Helvetica"):
    _reset_x(pdf)
    pdf.ln(3)

    pdf.set_font(font_name, "B", 13)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.set_fill_color(*_C_ACCENT)
    pdf.rect(_MARGIN_L, pdf.get_y() + 1.5, 3, 4, "F")
    pdf.set_x(_MARGIN_L + 5)
    pdf.cell(_CONTENT_W - 5, 7, title, align="L")
    pdf.ln(8)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.3)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(3)
    _reset_x(pdf)

    _render_content_text(pdf, content, font_name)
    _reset_x(pdf)


def _render_content_text(pdf, content, font_name="Helvetica"):
    for _line in content.split("\n"):
        _line_clean = _clean_text(_line).strip()

        if not _line_clean:
            pdf.ln(1)
            _reset_x(pdf)
            continue

        if _line_clean.startswith(("- ", "* ", "• ", "■ ")):
            _text = _line_clean[2:].strip().replace("**", "").replace("*", "")
            _y = pdf.get_y()

            pdf.set_fill_color(*_C_ACCENT)
            pdf.rect(_MARGIN_L + 2, _y + 1.5, 2, 2, "F")

            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(_MARGIN_L + 7)
            pdf.multi_cell(_CONTENT_W - 7, 5.5, _text)
            pdf.ln(0.5)
            _reset_x(pdf)
            continue

        _match_num = re.match(r'^(\d+)\.\s+(.+)', _line_clean)
        if _match_num:
            _num = _match_num.group(1)
            _text = _match_num.group(2).replace("**", "").replace("*", "")
            pdf.set_font(font_name, "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(_MARGIN_L + 5)
            pdf.multi_cell(_CONTENT_W - 5, 5.5, f"{_num}.  {_text}")
            pdf.ln(0.5)
            _reset_x(pdf)
            continue

        _text = _line_clean.replace("**", "").replace("*", "")
        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(*_C_DARK)
        _reset_x(pdf)
        pdf.multi_cell(_CONTENT_W, 5.5, _text)
        pdf.ln(1)
        _reset_x(pdf)


def _render_charts_2col(pdf, stats, font_name="Helvetica"):
    _sudah = stats.get("sudah_so", 0)
    _belum = stats.get("belum_so", 0)
    _adjust = stats.get("adjust_so", 0)
    _btsb = stats.get("btsb", 0)

    if _sudah + _belum == 0 and _adjust == 0 and _btsb == 0:
        return

    pdf.ln(3)
    _reset_x(pdf)

    pdf.set_font(font_name, "B", 13)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.set_fill_color(*_C_ACCENT)
    pdf.rect(_MARGIN_L, pdf.get_y() + 1.5, 3, 4, "F")
    pdf.set_x(_MARGIN_L + 5)
    pdf.cell(_CONTENT_W - 5, 7, "Grafik Analisis", align="L")
    pdf.ln(8)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.3)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(4)
    _reset_x(pdf)

    _y_start = pdf.get_y()
    _chart_w = (_CONTENT_W - 6) / 2

    _pie_buf = _make_pie_chart(_sudah, _belum)
    if _pie_buf:
        pdf.set_font(font_name, "B", 9)
        pdf.set_text_color(*_C_DARK)
        pdf.set_xy(_MARGIN_L, _y_start)
        pdf.cell(_chart_w, 5, "1. Rasio Stock Opname", align="C")
        try:
            pdf.image(_pie_buf, x=_MARGIN_L + 3, y=_y_start + 5, w=_chart_w - 6)
        except Exception as _e:
            print(f"[PDF IMG PIE ERROR] {_e}")

    _bar_buf = _make_bar_chart(_adjust, _btsb)
    if _bar_buf:
        pdf.set_font(font_name, "B", 9)
        pdf.set_text_color(*_C_DARK)
        pdf.set_xy(_MARGIN_L + _chart_w + 6, _y_start)
        pdf.cell(_chart_w, 5, "2. Adjust SO vs BTSB", align="C")
        try:
            pdf.image(_bar_buf, x=_MARGIN_L + _chart_w + 9, y=_y_start + 5, w=_chart_w - 6)
        except Exception as _e:
            print(f"[PDF IMG BAR ERROR] {_e}")

    pdf.set_y(_y_start + 75)
    _reset_x(pdf)


def _render_so_table(pdf, so_data, period_type, font_name="Helvetica"):
    pdf.ln(3)
    _reset_x(pdf)

    pdf.set_font(font_name, "B", 13)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.set_fill_color(*_C_ACCENT)
    pdf.rect(_MARGIN_L, pdf.get_y() + 1.5, 3, 4, "F")
    pdf.set_x(_MARGIN_L + 5)
    pdf.cell(_CONTENT_W - 5, 7, "Daftar Stock Opname", align="L")
    pdf.ln(8)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.3)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(4)
    _reset_x(pdf)

    pdf.set_font(font_name, "", 9)
    pdf.set_text_color(*_C_GRAY)
    _total = len(so_data)
    _limit_info = ""
    if period_type == "minggu":
        _limit_info = f" (top 5 dari {_total})"
    elif period_type == "bulan":
        _limit_info = f" (top 10 dari {_total})"

    pdf.cell(_CONTENT_W, 5, f"Total rak di-SO: {_total} rak{_limit_info}", ln=True)
    pdf.ln(2)
    _reset_x(pdf)

    if period_type == "minggu":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:5]
    elif period_type == "bulan":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:10]
    else:
        _rows = so_data

    _col_w = [38, 30, 70, 42]
    _headers = ["Tanggal", "Rak", "Nominal", "PIC"]

    pdf.set_fill_color(*_C_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_name, "B", 9)
    _reset_x(pdf)

    for _i, _h in enumerate(_headers):
        pdf.cell(_col_w[_i], 8, _h, border=0, fill=True, align="C")
    pdf.ln(8)

    pdf.set_font(font_name, "", 9)
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
        pdf.cell(_col_w[0], 7, _tgl_fmt, border=0, fill=_fill, align="C")
        pdf.cell(_col_w[1], 7, _rak, border=0, fill=_fill, align="C")
        pdf.cell(_col_w[2], 7, _fmt_rp(_nom), border=0, fill=_fill, align="R")
        pdf.cell(_col_w[3], 7, _pic[:20], border=0, fill=_fill, align="C")
        pdf.ln(7)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.3)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(2)

    _total_nom = sum(float(r.get("nominal_adjust", 0)) for r in so_data)
    if _total_nom < 0:
        pdf.set_text_color(*_C_RED)
    elif _total_nom > 0:
        pdf.set_text_color(*_C_GREEN)
    else:
        pdf.set_text_color(*_C_DARK)

    pdf.set_font(font_name, "B", 10)
    _reset_x(pdf)
    pdf.cell(sum(_col_w[:2]), 8, "TOTAL", border=0, align="C")
    pdf.cell(_col_w[2], 8, _fmt_rp(_total_nom), border=0, align="R")
    pdf.cell(_col_w[3], 8, "", border=0)
    pdf.ln(8)