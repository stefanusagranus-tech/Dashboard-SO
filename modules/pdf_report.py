"""
PDF Report Generator v3.0 — Professional Layout
================================================
Layout upgrade:
- Header banner + strip "Disusun Oleh"
- Card metric
- Bullet dengan kotak
- Layout 2 kolom (kiri-kanan)
- Section header dengan garis
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
_C_PRIMARY = (46, 30, 120)       # ungu tua
_C_ACCENT = (120, 80, 220)       # ungu terang
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
_CONTENT_W = _PAGE_W - _MARGIN_L - _MARGIN_R  # = 180

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
    try:
        _dt = datetime.strptime(tgl_str, "%Y-%m-%d")
        return _dt.strftime("%d/%m/%Y")
    except Exception:
        try:
            _dt = datetime.strptime(tgl_str[:10], "%Y-%m-%d")
            return _dt.strftime("%d/%m/%Y")
        except Exception:
            return tgl_str


def _sanitize_text(text):
    _replacements = {
        "—": "-", "–": "-", "−": "-", "…": "...",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "•": "-", "·": "-", "→": "->", "←": "<-",
        "≥": ">=", "≤": "<=", "×": "x", "÷": "/",
        "≈": "~=", "≠": "!=", "\u00a0": " ", "\u200b": "",
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
        _pdf.set_auto_page_break(auto=True, margin=15)
        _pdf.add_page()

        # ✅ 1. HEADER BANNER
        _render_header_banner(_pdf, period_label)

        # ✅ 2. STRIP "DISUSUN OLEH"
        _render_strip(_pdf)

        # ✅ 3. CARD METRIC (jika ada)
        if extra_stats:
            _render_metric_cards(_pdf, extra_stats)

        # ✅ 4. KONTEN AI (dengan bullet kotak)
        _render_ai_content(_pdf, ai_content)

        # ✅ 5. GRAFIK 2 KOLOM
        if extra_stats:
            _render_charts_2col(_pdf, extra_stats)

        # ✅ 6. TABEL SO
        if so_data:
            _render_so_table(_pdf, so_data, period_type)

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


# === 1. HEADER BANNER ===
def _render_header_banner(pdf, period_label):
    """Banner ungu besar di atas."""
    # Background banner
    pdf.set_fill_color(*_C_PRIMARY)
    pdf.rect(0, 0, _PAGE_W, 42, "F")

    # Garis oranye di kiri (aksen)
    pdf.set_fill_color(*_C_ORANGE)
    pdf.rect(0, 0, 6, 42, "F")

    # Judul utama
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_y(10)
    pdf.set_x(_MARGIN_L + 6)
    pdf.cell(_CONTENT_W - 6, 12, "Laporan Stock Opname", align="L")

    # Subjudul
    pdf.set_font("Helvetica", "", 11)
    pdf.set_y(23)
    pdf.set_x(_MARGIN_L + 6)
    pdf.cell(_CONTENT_W - 6, 6, f"Periode: {period_label}", align="L")

    # Sub-sub
    pdf.set_font("Helvetica", "", 10)
    pdf.set_y(30)
    pdf.set_x(_MARGIN_L + 6)
    pdf.cell(_CONTENT_W - 6, 5, "Toko C383 - Karang Satria", align="L")

    # Reset
    pdf.set_text_color(*_C_DARK)
    pdf.set_y(50)
    _reset_x(pdf)


# === 2. STRIP "DISUSUN OLEH" ===
def _render_strip(pdf):
    """Strip ungu tipis di bawah header."""
    _y = pdf.get_y()

    pdf.set_fill_color(*_C_PRIMARY)
    pdf.rect(0, _y, _PAGE_W, 8, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_y(_y + 2)
    pdf.set_x(_MARGIN_L)
    pdf.cell(_CONTENT_W / 2, 4, "Disusun Oleh", align="L")

    pdf.set_x(_MARGIN_L + _CONTENT_W / 2)
    pdf.cell(_CONTENT_W / 2, 4, "Staff Karang Satria", align="R")  # ✅ GANTI INI

    pdf.set_text_color(*_C_DARK)
    pdf.set_y(_y + 14)
    _reset_x(pdf)


# === 3. CARD METRIC ===
def _render_metric_cards(pdf, stats):
    """4 card metric di atas body."""
    _sudah = stats.get("sudah_so", 0)
    _belum = stats.get("belum_so", 0)
    _total_rak = _sudah + _belum
    _adjust = stats.get("adjust_so", 0)
    _btsb = stats.get("btsb", 0)

    _cards = [
        {"label": "Rak di-SO", "value": f"{_sudah}", "color": _C_GREEN},
        {"label": "Belum SO", "value": f"{_belum}", "color": _C_RED},
        {"label": "Adjust SO", "value": _fmt_rp(_adjust)[:15], "color": _C_ORANGE},
        {"label": "BTSB", "value": _fmt_rp(_btsb)[:15], "color": _C_PRIMARY},
    ]

    _card_w = (_CONTENT_W - 6) / 4  # 4 cards + 3 gaps of 2mm
    _card_h = 22
    _y_start = pdf.get_y()

    for _i, _card in enumerate(_cards):
        _x = _MARGIN_L + _i * (_card_w + 2)

        # Card background
        pdf.set_fill_color(*_card["color"])
        pdf.rect(_x, _y_start, _card_w, _card_h, "F")

        # Label
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(_x, _y_start + 3)
        pdf.cell(_card_w, 4, _card["label"], align="C")

        # Value
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_xy(_x, _y_start + 10)
        pdf.cell(_card_w, 8, _card["value"], align="C")

    pdf.set_text_color(*_C_DARK)
    pdf.set_y(_y_start + _card_h + 6)
    _reset_x(pdf)


# === 4. KONTEN AI ===
def _render_ai_content(pdf, content_text):
    """Render markdown dengan bullet kotak."""
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

            pdf.ln(4)
            _reset_x(pdf)

            if _level <= 1:
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(*_C_PRIMARY)
                # Kotak kecil di depan heading
                pdf.set_fill_color(*_C_ACCENT)
                pdf.rect(_MARGIN_L, pdf.get_y() + 1.5, 3, 4, "F")
                pdf.set_x(_MARGIN_L + 5)
                pdf.cell(_CONTENT_W - 5, 7, _text, align="L")
                pdf.ln(8)
                # Garis tipis
                pdf.set_draw_color(*_C_ACCENT)
                pdf.set_line_width(0.3)
                pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
                pdf.ln(3)
            elif _level == 2:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*_C_PRIMARY)
                pdf.cell(_CONTENT_W, 6, _text, ln=True)
                pdf.ln(1)
            else:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(*_C_DARK)
                pdf.cell(_CONTENT_W, 5, _text, ln=True)

            pdf.set_text_color(*_C_DARK)
            _reset_x(pdf)
            continue

        # BULLET (kotak kecil)
        if _line_clean.startswith(("- ", "* ", "• ")):
            _text = _line_clean[2:].strip().replace("**", "").replace("*", "")
            _y = pdf.get_y()

            # Kotak kecil
            pdf.set_fill_color(*_C_ACCENT)
            pdf.rect(_MARGIN_L + 2, _y + 1.5, 2, 2, "F")

            # Text
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(_MARGIN_L + 7)
            pdf.multi_cell(_CONTENT_W - 7, 5.5, _text)
            pdf.ln(0.5)
            _reset_x(pdf)
            continue

        # NUMBERED (arrow)
        _match_num = re.match(r'^(\d+)\.\s+(.+)', _line_clean)
        if _match_num:
            _num = _match_num.group(1)
            _text = _match_num.group(2).replace("**", "").replace("*", "")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_C_DARK)
            pdf.set_x(_MARGIN_L + 5)
            pdf.multi_cell(_CONTENT_W - 5, 5.5, f"{_num}.  {_text}")
            pdf.ln(0.5)
            _reset_x(pdf)
            continue

        # PARAGRAF
        _text = _line_clean.replace("**", "").replace("*", "")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_C_DARK)
        _reset_x(pdf)
        pdf.multi_cell(_CONTENT_W, 5.5, _text)
        pdf.ln(1)
        _reset_x(pdf)


# === 5. GRAFIK 2 KOLOM ===
def _render_charts_2col(pdf, stats):
    """Render 2 grafik side-by-side."""
    _sudah = stats.get("sudah_so", 0)
    _belum = stats.get("belum_so", 0)
    _adjust = stats.get("adjust_so", 0)
    _btsb = stats.get("btsb", 0)

    if _sudah + _belum == 0 and _adjust == 0 and _btsb == 0:
        return

    # Cek page break
    if pdf.get_y() > 150:
        pdf.add_page()

    pdf.ln(5)
    _reset_x(pdf)

    # Section header
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*_C_PRIMARY)
    pdf.set_fill_color(*_C_ACCENT)
    pdf.rect(_MARGIN_L, pdf.get_y() + 1.5, 3, 4, "F")
    pdf.set_x(_MARGIN_L + 5)
    pdf.cell(_CONTENT_W - 5, 7, "Grafik Analisis", align="L")
    pdf.ln(8)

    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.3)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(5)
    _reset_x(pdf)

    _y_start = pdf.get_y()
    _chart_w = (_CONTENT_W - 6) / 2

    # PIE CHART (kiri)
    _pie_buf = _make_pie_chart(_sudah, _belum)
    if _pie_buf:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_C_DARK)
        pdf.set_xy(_MARGIN_L, _y_start)
        pdf.cell(_chart_w, 5, "1. Rasio Stock Opname", align="C")

        try:
            pdf.image(_pie_buf, x=_MARGIN_L + 3, y=_y_start + 5, w=_chart_w - 6)
        except Exception as _e:
            print(f"[PDF IMG PIE ERROR] {_e}")

    # BAR CHART (kanan)
    _bar_buf = _make_bar_chart(_adjust, _btsb)
    if _bar_buf:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_C_DARK)
        pdf.set_xy(_MARGIN_L + _chart_w + 6, _y_start)
        pdf.cell(_chart_w, 5, "2. Adjust SO vs BTSB", align="C")

        try:
            pdf.image(_bar_buf, x=_MARGIN_L + _chart_w + 9, y=_y_start + 5, w=_chart_w - 6)
        except Exception as _e:
            print(f"[PDF IMG BAR ERROR] {_e}")

    # Reset Y setelah chart
    pdf.set_y(_y_start + 75)
    _reset_x(pdf)


# === 6. TABEL SO ===
def _render_so_table(pdf, so_data, period_type):
    if pdf.get_y() > 180:
        pdf.add_page()

    pdf.ln(5)
    _reset_x(pdf)

    # Section header
    pdf.set_font("Helvetica", "B", 13)
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

    # Info
    pdf.set_font("Helvetica", "", 9)
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

    # Filter
    if period_type == "minggu":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:5]
    elif period_type == "bulan":
        _rows = sorted(so_data, key=lambda x: abs(float(x.get("nominal_adjust", 0))), reverse=True)[:10]
    else:
        _rows = so_data

    # Kolom
    _col_w = [38, 30, 70, 42]
    _headers = ["Tanggal", "Rak", "Nominal", "PIC"]

    pdf.set_fill_color(*_C_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    _reset_x(pdf)

    for _i, _h in enumerate(_headers):
        pdf.cell(_col_w[_i], 8, _h, border=0, fill=True, align="C")
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
        pdf.cell(_col_w[0], 7, _tgl_fmt, border=0, fill=_fill, align="C")
        pdf.cell(_col_w[1], 7, _rak, border=0, fill=_fill, align="C")
        pdf.cell(_col_w[2], 7, _fmt_rp(_nom), border=0, fill=_fill, align="R")
        pdf.cell(_col_w[3], 7, _pic[:20], border=0, fill=_fill, align="C")
        pdf.ln(7)

    # Garis bawah
    pdf.set_draw_color(*_C_ACCENT)
    pdf.set_line_width(0.3)
    pdf.line(_MARGIN_L, pdf.get_y(), _PAGE_W - _MARGIN_R, pdf.get_y())
    pdf.ln(2)

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
    pdf.cell(sum(_col_w[:2]), 8, "TOTAL", border=0, align="C")
    pdf.cell(_col_w[2], 8, _fmt_rp(_total_nom), border=0, align="R")
    pdf.cell(_col_w[3], 8, "", border=0)
    pdf.ln(8)