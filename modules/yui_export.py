"""
Yui Export — PDF Profesional (pastel theme) + Gambar
======================================================
- PDF: fpdf2 + DejaVu font + chart dari matplotlib
- Gambar: matplotlib (no browser)
- Palet: pastel warm (sage, peach, salmon, beige)
"""

import io
import os
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fpdf import FPDF


# =========================================================
# PALET WARNA PASTEL
# =========================================================
WARNA = {
    "sage":      (151, 179, 174),   # #97B3AE
    "sage_light": (210, 224, 211),  # #D2E0D3
    "peach":     (240, 221, 214),   # #F0DDD6
    "salmon":    (242, 195, 185),   # #F2C3B9
    "beige":     (214, 203, 191),   # #D6CBBF
    "offwhite":  (240, 238, 234),   # #F0EEEA
    "dark":      (60, 60, 60),      # teks
    "white":     (255, 255, 255),
    "red":       (200, 50, 50),
    "green":     (50, 150, 50),
}


# =========================================================
# PATH FONT
# =========================================================
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_PATH = os.path.join(_BASE_DIR, "fonts", "DejaVuSansCondensed.ttf")
_FONT_PATH_BOLD = os.path.join(_BASE_DIR, "fonts", "DejaVuSansCondensed-Bold.ttf")


def _font_tersedia():
    return os.path.exists(_FONT_PATH) and os.path.exists(_FONT_PATH_BOLD)


# =========================================================
# HELPER FORMAT
# =========================================================
def _format_nominal(val):
    """Round nominal jadi integer."""
    try:
        return int(round(float(val)))
    except Exception:
        return 0


def _format_rp(val):
    """Format Rp dengan pemisah ribuan."""
    _n = _format_nominal(val)
    _sign = "+" if _n >= 0 else "-"
    return f"{_sign}Rp {abs(_n):,}".replace(",", ".")


def _format_rp_no_sign(val):
    """Format Rp tanpa sign."""
    _n = _format_nominal(val)
    return f"Rp {abs(_n):,}".replace(",", ".")


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
# GENERATE CHARTS (matplotlib → BytesIO)
# =========================================================
def _generate_bar_chart(hasil, max_rak=10):
    """Bar chart nominal per rak. Mingguan/bulanan: top 10 minus."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _list_rak = hasil.get("list_rak", [])
        if not _list_rak:
            return None

        _df = pd.DataFrame(_list_rak)
        _df["total"] = pd.to_numeric(_df["total"], errors="coerce").fillna(0)

        # Kalau lebih dari max_rak, ambil 10 minus terdalam
        if len(_df) > max_rak:
            _df = _df.nsmallest(max_rak, "total")
            _title = f"TOP {max_rak} MINUS PER RAK"
        else:
            _title = "NOMINAL PER RAK"

        _df = _df.sort_values("total")

        _fig, _ax = plt.subplots(figsize=(10, 4))
        _fig.patch.set_facecolor("#F0EEEA")
        _ax.set_facecolor("#F0EEEA")

        _colors = ["#F2C3B9" if v < 0 else "#97B3AE" for v in _df["total"]]
        _bars = _ax.bar(_df["rak_id"].astype(str), _df["total"], color=_colors, edgecolor="white", linewidth=1)

        _ax.axhline(0, color="#3C3C3C", linewidth=0.8)
        _ax.set_title(_title, fontsize=13, fontweight="bold", color="#3C3C3C", pad=10)
        _ax.set_ylabel("Nominal (Rp)", fontsize=10, color="#3C3C3C")
        _ax.tick_params(axis="x", rotation=45, labelsize=9)
        _ax.tick_params(axis="y", labelsize=9)
        _ax.spines["top"].set_visible(False)
        _ax.spines["right"].set_visible(False)
        _ax.spines["left"].set_color("#D6CBBF")
        _ax.spines["bottom"].set_color("#D6CBBF")
        _ax.grid(axis="y", linestyle="--", alpha=0.4, color="#D6CBBF")

        # Format label y
        _ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", "."))
        )

        plt.tight_layout()
        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", dpi=130, bbox_inches="tight", facecolor="#F0EEEA")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as e:
        print(f"[CHART_BAR ERROR] {e}")
        return None


def _generate_trend_nsb(hasil):
    """Trend line NSB per hari (dari so_rak_harian)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from modules.supabase_client import get_supabase

        _sb = get_supabase()
        if _sb is None:
            return None

        # Ambil data bulan ini
        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _start = datetime(_now.year, _now.month, 1).date()
        if _now.month == 12:
            _end = datetime(_now.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            _end = datetime(_now.year, _now.month + 1, 1).date() - timedelta(days=1)

        _res = (
            _sb.table("so_rak_harian")
            .select("so_date, nominal_adjust")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
            .execute()
        )

        if not _res.data:
            return None

        _df = pd.DataFrame(_res.data)
        _df["so_date"] = pd.to_datetime(_df["so_date"], errors="coerce")
        _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
        _df = _df.dropna(subset=["so_date"])

        # Group by tanggal — SUM biasa (bukan abs)
        _grp = _df.groupby("so_date")["nominal_adjust"].sum().reset_index()
        _grp = _grp.sort_values("so_date")

        if _grp.empty:
            return None

        _fig, _ax = plt.subplots(figsize=(10, 3.5))
        _fig.patch.set_facecolor("#F0EEEA")
        _ax.set_facecolor("#F0EEEA")

        _ax.plot(
            _grp["so_date"].dt.strftime("%d/%m"),
            _grp["nominal_adjust"],
            color="#97B3AE",
            linewidth=2.5,
            marker="o",
            markersize=6,
            markerfacecolor="#F2C3B9",
            markeredgecolor="#97B3AE",
            markeredgewidth=1.5,
        )
        _ax.axhline(0, color="#3C3C3C", linewidth=0.8, linestyle="--")
        _ax.fill_between(
            range(len(_grp)),
            _grp["nominal_adjust"],
            0,
            alpha=0.15,
            color="#97B3AE",
        )

        _ax.set_title("TREND NSB HARIAN", fontsize=13, fontweight="bold", color="#3C3C3C", pad=10)
        _ax.set_ylabel("Nominal (Rp)", fontsize=10, color="#3C3C3C")
        _ax.tick_params(axis="x", rotation=45, labelsize=9)
        _ax.tick_params(axis="y", labelsize=9)
        _ax.spines["top"].set_visible(False)
        _ax.spines["right"].set_visible(False)
        _ax.spines["left"].set_color("#D6CBBF")
        _ax.spines["bottom"].set_color("#D6CBBF")
        _ax.grid(axis="y", linestyle="--", alpha=0.4, color="#D6CBBF")

        _ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", "."))
        )

        plt.tight_layout()
        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", dpi=130, bbox_inches="tight", facecolor="#F0EEEA")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as e:
        print(f"[CHART_TREND ERROR] {e}")
        return None


def _generate_donut_sales_nsb(net_sales, nsb):
    """Donut chart perbandingan Sales vs NSB."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if net_sales <= 0:
            return None

        # Rekomendasi: proporsi BTSB cover vs NSB (uncovered)
        _btsb = net_sales * 0.0015
        _covered = min(_btsb, _btsb)  # BTSB selalu cover BTSB itu sendiri
        _uncovered = max(0, nsb)
        _aman = max(0, _btsb - _uncovered)

        _labels = ["Tertutup BTSB", "NSB (Beban)"]
        _sizes = [_aman, _uncovered]
        _colors = ["#97B3AE", "#F2C3B9"]

        if sum(_sizes) == 0:
            return None

        _fig, _ax = plt.subplots(figsize=(5, 5))
        _fig.patch.set_facecolor("#F0EEEA")

        _wedges, _texts, _autotexts = _ax.pie(
            _sizes,
            labels=_labels,
            colors=_colors,
            autopct=lambda p: f"{p:.1f}%",
            startangle=90,
            wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2),
            textprops=dict(color="#3C3C3C", fontsize=10),
        )

        for _at in _autotexts:
            _at.set_color("white")
            _at.set_fontweight("bold")
            _at.set_fontsize(11)

        _ax.set_title(
            f"COVERAGE BTSB\n(Net Sales: {_format_rp_no_sign(net_sales)})",
            fontsize=12, fontweight="bold", color="#3C3C3C", pad=15,
        )

        plt.tight_layout()
        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", dpi=130, bbox_inches="tight", facecolor="#F0EEEA")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as e:
        print(f"[CHART_DONUT ERROR] {e}")
        return None


# =========================================================
# PDF PROFESIONAL
# =========================================================
class PDFLaporan(FPDF):
    """PDF dengan header & footer custom, font DejaVu."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._font_family = None
        self._font_family_bold = None

    def _setup_font(self):
        """Setup font DejaVu sekali."""
        if self._font_family:
            return
        if _font_tersedia():
            self.add_font(fname=_FONT_PATH)
            self.add_font(fname=_FONT_PATH_BOLD, style="B")
            self._font_family = "DejaVuSansCondensed"
            self._font_family_bold = "DejaVuSansCondensed"
        else:
            self._font_family = "Helvetica"
            self._font_family_bold = "Helvetica"

    def set_my_font(self, style="", size=10):
        """Set font dengan fallback aman."""
        self._setup_font()
        try:
            self.set_font(self._font_family, style=style, size=size)
        except Exception:
            self.set_font("Helvetica", style=style, size=size)

    def header(self):
        # Header band sage
        self.set_fill_color(*WARNA["sage"])
        self.rect(0, 0, 210, 30, style="F")

        self.set_my_font(style="B", size=15)
        self.set_text_color(*WARNA["white"])
        self.set_xy(12, 7)
        self.cell(0, 8, "LAPORAN STOCK OPNAME", new_x="LMARGIN", new_y="NEXT")

        self.set_my_font(style="", size=9)
        self.set_text_color(*WARNA["offwhite"])
        self.set_xy(12, 17)
        self.cell(0, 6, "Toko C383 - Karang Satria", new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*WARNA["dark"])
        self.set_y(38)

    def footer(self):
        self.set_y(-15)
        self.set_my_font(style="I", size=8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Halaman {self.page_no()}", align="C")


def _draw_kpi_cards(pdf, total_rak, total_item, total_nominal):
    """Gambar 3 KPI cards warna pastel."""
    _y_start = pdf.get_y()
    _card_w = 58
    _card_h = 22
    _gap = 4

    _cards = [
        ("TOTAL RAK", f"{total_rak} rak", WARNA["sage_light"]),
        ("TOTAL ITEM", f"{total_item} item", WARNA["peach"]),
        ("TOTAL NOMINAL", _format_rp(total_nominal), WARNA["salmon"]),
    ]

    _x_start = (210 - (3 * _card_w + 2 * _gap)) / 2

    for _i, (_label, _value, _bg) in enumerate(_cards):
        _x = _x_start + _i * (_card_w + _gap)
        pdf.set_fill_color(*_bg)
        pdf.rect(_x, _y_start, _card_w, _card_h, style="F")

        pdf.set_my_font(style="B", size=8)
        pdf.set_text_color(*WARNA["dark"])
        pdf.set_xy(_x + 3, _y_start + 3)
        pdf.cell(_card_w - 6, 5, _label, align="L")

        pdf.set_my_font(style="B", size=13)
        pdf.set_text_color(*WARNA["dark"])
        pdf.set_xy(_x + 3, _y_start + 10)
        pdf.cell(_card_w - 6, 8, _value, align="L")

    pdf.set_y(_y_start + _card_h + 6)


def export_rekap_pdf(hasil, net_sales=0, filename="rekap_so.pdf"):
    """Export rekap SO jadi PDF profesional (pastel theme)."""
    try:
        _pdf = PDFLaporan()
        _pdf.add_page()
        _pdf.set_auto_page_break(auto=True, margin=18)

        # =========================================================
        # KPI CARDS
        # =========================================================
        _draw_kpi_cards(
            _pdf,
            hasil.get("total_rak", 0),
            hasil.get("total_item", 0),
            hasil.get("total_nominal", 0),
        )
        _pdf.ln(4)

        # =========================================================
        # RINGKASAN + BTSB/NSB (2 kolom)
        # =========================================================
        _y_section = _pdf.get_y()
        _col_w = 90

        # Kolom kiri: Ringkasan
        _pdf.set_xy(12, _y_section)
        _pdf.set_fill_color(*WARNA["sage"])
        _pdf.rect(12, _y_section, _col_w, 7, style="F")
        _pdf.set_my_font(style="B", size=10)
        _pdf.set_text_color(*WARNA["white"])
        _pdf.set_xy(14, _y_section + 1.5)
        _pdf.cell(_col_w - 4, 5, "RINGKASAN", align="L")

        _pdf.set_text_color(*WARNA["dark"])
        _pdf.set_my_font(style="", size=9)
        _pdf.set_xy(14, _y_section + 10)
        _pdf.cell(45, 5.5, "Periode")
        _pdf.cell(0, 5.5, f": {hasil.get('periode', '-')}", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_x(14)
        _pdf.cell(45, 5.5, "Total Rak")
        _pdf.cell(0, 5.5, f": {hasil.get('total_rak', 0)}", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_x(14)
        _pdf.cell(45, 5.5, "Total Item")
        _pdf.cell(0, 5.5, f": {hasil.get('total_item', 0)}", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_x(14)
        _pdf.cell(45, 5.5, "Total Nominal")
        _pdf.cell(0, 5.5, f": {_format_rp(hasil.get('total_nominal', 0))}", new_x="LMARGIN", new_y="NEXT")

        # Kolom kanan: BTSB/NSB
        _total_selisih = hasil.get("_total_selisih_bulan", 0)
        _total_rak_bulan = hasil.get("_total_rak_bulan", 0)
        _calc = _hitung_btsb_nsb(net_sales, _total_selisih) if net_sales > 0 else None

        _pdf.set_xy(108, _y_section)
        _pdf.set_fill_color(*WARNA["sage"])
        _pdf.rect(108, _y_section, _col_w, 7, style="F")
        _pdf.set_my_font(style="B", size=10)
        _pdf.set_text_color(*WARNA["white"])
        _pdf.set_xy(110, _y_section + 1.5)
        _pdf.cell(_col_w - 4, 5, "ANALISIS BTSB & NSB", align="L")

        _pdf.set_text_color(*WARNA["dark"])
        _pdf.set_my_font(style="", size=9)
        _pdf.set_xy(110, _y_section + 10)

        if _calc:
            _pdf.cell(45, 5.5, "Net Sales")
            _pdf.cell(0, 5.5, f": {_format_rp(net_sales)}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_x(110)
            _pdf.cell(45, 5.5, "BTSB (0,15%)")
            _pdf.cell(0, 5.5, f": {_format_rp(_calc['btsb'])}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_x(110)
            _pdf.cell(45, 5.5, "Total Selisih")
            _pdf.cell(0, 5.5, f": {_format_rp(_calc['selisih'])}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_x(110)
            _pdf.cell(45, 5.5, "NSB")
            _pdf.cell(0, 5.5, f": {_format_rp(_calc['nsb'])}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_x(110)
            _pdf.cell(45, 5.5, "Total Rak")
            _pdf.cell(0, 5.5, f": {_total_rak_bulan} rak", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_x(110)
            _pdf.cell(45, 5.5, "Status")
            _pdf.set_my_font(style="B", size=9)
            if _calc["status"] == "OVER":
                _pdf.set_text_color(*WARNA["red"])
            else:
                _pdf.set_text_color(*WARNA["green"])
            _pdf.cell(0, 5.5, f": {_calc['status']}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_my_font(style="", size=9)
        else:
            _pdf.cell(0, 5.5, "Data net sales belum tersedia", new_x="LMARGIN", new_y="NEXT")

        _pdf.set_y(max(_pdf.get_y(), _y_section + 45) + 5)

        # =========================================================
        # BAR CHART
        # =========================================================
        _bar_buf = _generate_bar_chart(hasil)
        if _bar_buf:
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.rect(12, _pdf.get_y(), 186, 7, style="F")
            _pdf.set_my_font(style="B", size=10)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(14, _pdf.get_y() + 1.5)
            _pdf.cell(0, 5, "NOMINAL PER RAK", align="L")
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.ln(10)
            _pdf.image(_bar_buf, x=15, w=180)
            _pdf.ln(4)
            _bar_buf.close()

        # =========================================================
        # TREND + DONUT (2 kolom)
        # =========================================================
        _y_chart = _pdf.get_y()
        if _y_chart > 200:
            _pdf.add_page()

        _trend_buf = _generate_trend_nsb(hasil)
        _donut_buf = _generate_donut_sales_nsb(net_sales, _calc["nsb"] if _calc else 0)

        if _trend_buf and _donut_buf:
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.rect(12, _pdf.get_y(), 120, 7, style="F")
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.rect(136, _pdf.get_y(), 62, 7, style="F")

            _pdf.set_my_font(style="B", size=9)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(14, _pdf.get_y() + 1.5)
            _pdf.cell(0, 5, "TREND NSB", align="L")
            _pdf.set_xy(138, _pdf.get_y() - 5 + 1.5)
            _pdf.cell(0, 5, "COVERAGE", align="L")

            _pdf.set_text_color(*WARNA["dark"])
            _pdf.ln(10)

            _y_img = _pdf.get_y()
            _pdf.image(_trend_buf, x=12, y=_y_img, w=120)
            _pdf.image(_donut_buf, x=138, y=_y_img, w=60)
            _pdf.ln(50)

            _trend_buf.close()
            _donut_buf.close()

        # =========================================================
        # DAFTAR RAK LENGKAP
        # =========================================================
        _pdf.add_page()
        _pdf.set_fill_color(*WARNA["sage"])
        _pdf.rect(12, _pdf.get_y(), 186, 7, style="F")
        _pdf.set_my_font(style="B", size=10)
        _pdf.set_text_color(*WARNA["white"])
        _pdf.set_xy(14, _pdf.get_y() + 1.5)
        _pdf.cell(0, 5, "DAFTAR RAK YANG DI-SO", align="L")
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.ln(10)

        # Header tabel
        _pdf.set_my_font(style="B", size=9)
        _pdf.set_fill_color(*WARNA["sage"])
        _pdf.set_text_color(*WARNA["white"])
        _pdf.cell(25, 7, "RAK", border=0, fill=True, align="C")
        _pdf.cell(60, 7, "PIC", border=0, fill=True, align="C")
        _pdf.cell(45, 7, "TANGGAL", border=0, fill=True, align="C")
        _pdf.cell(56, 7, "NOMINAL", border=0, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

        # Body tabel
        _pdf.set_my_font(style="", size=9)
        _pdf.set_text_color(*WARNA["dark"])
        _list_rak = hasil.get("list_rak", [])
        for _i, _r in enumerate(_list_rak):
            _bg = WARNA["offwhite"] if _i % 2 == 0 else WARNA["white"]
            _pdf.set_fill_color(*_bg)
            _pdf.cell(25, 6, str(_r.get("rak_id", "-"))[:15], border=0, fill=True, align="C")
            _pdf.cell(60, 6, str(_r.get("pic", "-"))[:25], border=0, fill=True, align="L")
            _pdf.cell(45, 6, str(_r.get("tanggal", "-"))[:12], border=0, fill=True, align="C")
            _nom = _r.get("total", 0)
            if _nom < 0:
                _pdf.set_text_color(*WARNA["red"])
            else:
                _pdf.set_text_color(*WARNA["green"])
            _pdf.cell(56, 6, _format_rp(_nom), border=0, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(*WARNA["dark"])

        _pdf.ln(6)

        # =========================================================
        # TOP 5 MINUS & PLUS
        # =========================================================
        try:
            from modules.yui_rekap import get_top_items
            _tops = get_top_items(limit=5)
            _top_minus = _tops.get("top_minus", [])
            _top_plus = _tops.get("top_plus", [])

            # TOP 5 MINUS
            _pdf.set_fill_color(*WARNA["salmon"])
            _pdf.rect(12, _pdf.get_y(), 186, 7, style="F")
            _pdf.set_my_font(style="B", size=10)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(14, _pdf.get_y() + 1.5)
            _pdf.cell(0, 5, "TOP 5 MINUS TERTINGGI (PER ITEM)", align="L")
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.ln(10)

            _pdf.set_my_font(style="B", size=8)
            _pdf.set_fill_color(*WARNA["salmon"])
            _pdf.set_text_color(*WARNA["white"])
            _pdf.cell(15, 7, "RAK", fill=True, align="C")
            _pdf.cell(22, 7, "PLU", fill=True, align="C")
            _pdf.cell(75, 7, "NAMA PRODUK", fill=True, align="C")
            _pdf.cell(46, 7, "NOMINAL", fill=True, align="C")
            _pdf.cell(28, 7, "PIC", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

            _pdf.set_my_font(style="", size=8)
            _pdf.set_text_color(*WARNA["dark"])
            for _i, _r in enumerate(_top_minus):
                _bg = WARNA["offwhite"] if _i % 2 == 0 else WARNA["white"]
                _pdf.set_fill_color(*_bg)
                _pdf.cell(15, 6, str(_r.get("rak_id", "-"))[:10], fill=True, align="C")
                _pdf.cell(22, 6, str(_r.get("plu", "-"))[:10], fill=True, align="C")
                _pdf.cell(75, 6, str(_r.get("nama_produk", "-"))[:40], fill=True, align="L")
                _pdf.set_text_color(*WARNA["red"])
                _pdf.cell(46, 6, _format_rp(_r.get("nominal_adjust", 0)), fill=True, align="R")
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.cell(28, 6, str(_r.get("pic", "-"))[:12], fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
            _pdf.ln(6)

            # TOP 5 PLUS
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.rect(12, _pdf.get_y(), 186, 7, style="F")
            _pdf.set_my_font(style="B", size=10)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(14, _pdf.get_y() + 1.5)
            _pdf.cell(0, 5, "TOP 5 PLUS TERTINGGI (PER ITEM)", align="L")
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.ln(10)

            _pdf.set_my_font(style="B", size=8)
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.set_text_color(*WARNA["white"])
            _pdf.cell(15, 7, "RAK", fill=True, align="C")
            _pdf.cell(22, 7, "PLU", fill=True, align="C")
            _pdf.cell(75, 7, "NAMA PRODUK", fill=True, align="C")
            _pdf.cell(46, 7, "NOMINAL", fill=True, align="C")
            _pdf.cell(28, 7, "PIC", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

            _pdf.set_my_font(style="", size=8)
            _pdf.set_text_color(*WARNA["dark"])
            for _i, _r in enumerate(_top_plus):
                _bg = WARNA["offwhite"] if _i % 2 == 0 else WARNA["white"]
                _pdf.set_fill_color(*_bg)
                _pdf.cell(15, 6, str(_r.get("rak_id", "-"))[:10], fill=True, align="C")
                _pdf.cell(22, 6, str(_r.get("plu", "-"))[:10], fill=True, align="C")
                _pdf.cell(75, 6, str(_r.get("nama_produk", "-"))[:40], fill=True, align="L")
                _pdf.set_text_color(*WARNA["green"])
                _pdf.cell(46, 6, _format_rp(_r.get("nominal_adjust", 0)), fill=True, align="R")
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.cell(28, 6, str(_r.get("pic", "-"))[:12], fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
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
# GAMBAR — matplotlib (pastel theme)
# =========================================================
def export_rekap_image(hasil, net_sales=0, filename="rekap_so.png"):
    """Export rekap SO jadi gambar pakai matplotlib (pastel theme)."""
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

        _fig = plt.figure(figsize=(12, 14))
        _fig.patch.set_facecolor("#F0EEEA")

        # ===== Subplot 1: Rekap per Rak =====
        _ax1 = _fig.add_subplot(4, 1, 1)
        _ax1.axis("off")
        _ax1.set_title(
            "REKAP PER RAK", fontsize=13, fontweight="bold", color="#3C3C3C", pad=12
        )

        _df_rak = pd.DataFrame(_list_rak).rename(columns={
            "rak_id": "Rak", "total": "Nominal",
            "pic": "PIC", "tanggal": "Tanggal",
        })
        _df_rak["Nominal"] = _df_rak["Nominal"].apply(
            lambda x: f"{'+' if _format_nominal(x) >= 0 else '-'}Rp {abs(_format_nominal(x)):,}".replace(",", ".")
        )

        _tbl1 = _ax1.table(
            cellText=_df_rak[["Rak", "Nominal", "PIC", "Tanggal"]].values,
            colLabels=["Rak", "Nominal", "PIC", "Tanggal"],
            cellLoc="center", loc="center",
            colWidths=[0.15, 0.35, 0.25, 0.25],
        )
        _tbl1.auto_set_font_size(False)
        _tbl1.set_fontsize(9)
        _tbl1.scale(1, 1.5)
        for _i in range(4):
            _cell = _tbl1[(0, _i)]
            _cell.set_facecolor("#97B3AE")
            _cell.set_text_props(color="white", weight="bold")
        for _i in range(1, len(_df_rak) + 1):
            for _j in range(4):
                _cell = _tbl1[(_i, _j)]
                _cell.set_facecolor("#FFFFFF" if _i % 2 == 1 else "#F0EEEA")

        # ===== Subplot 2: Bar Chart per Rak =====
        _ax2 = _fig.add_subplot(4, 1, 2)
        _ax2.set_facecolor("#F0EEEA")
        _df_bar = pd.DataFrame(_list_rak)
        _df_bar["total"] = pd.to_numeric(_df_bar["total"], errors="coerce").fillna(0)
        if len(_df_bar) > 10:
            _df_bar = _df_bar.nsmallest(10, "total")
            _bar_title = "TOP 10 MINUS PER RAK"
        else:
            _bar_title = "NOMINAL PER RAK"
        _df_bar = _df_bar.sort_values("total")

        _colors = ["#F2C3B9" if v < 0 else "#97B3AE" for v in _df_bar["total"]]
        _ax2.bar(_df_bar["rak_id"].astype(str), _df_bar["total"], color=_colors, edgecolor="white", linewidth=1)
        _ax2.axhline(0, color="#3C3C3C", linewidth=0.8)
        _ax2.set_title(_bar_title, fontsize=12, fontweight="bold", color="#3C3C3C", pad=8)
        _ax2.tick_params(axis="x", rotation=45, labelsize=8)
        _ax2.tick_params(axis="y", labelsize=8)
        _ax2.spines["top"].set_visible(False)
        _ax2.spines["right"].set_visible(False)
        _ax2.spines["left"].set_color("#D6CBBF")
        _ax2.spines["bottom"].set_color("#D6CBBF")
        _ax2.grid(axis="y", linestyle="--", alpha=0.4, color="#D6CBBF")
        _ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", "."))
        )

        # ===== Subplot 3: Top 5 Minus =====
        _ax3 = _fig.add_subplot(4, 1, 3)
        _ax3.axis("off")
        _ax3.set_title(
            "TOP 5 MINUS (PER ITEM)", fontsize=12, fontweight="bold", color="#C83232", pad=10
        )

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
            _tbl2 = _ax3.table(
                cellText=_rows_minus,
                colLabels=["Rak", "PLU", "Nama Produk", "Nominal"],
                cellLoc="center", loc="center",
                colWidths=[0.1, 0.15, 0.55, 0.2],
            )
            _tbl2.auto_set_font_size(False)
            _tbl2.set_fontsize(8)
            _tbl2.scale(1, 1.5)
            for _i in range(4):
                _cell = _tbl2[(0, _i)]
                _cell.set_facecolor("#F2C3B9")
                _cell.set_text_props(color="white", weight="bold")

        # ===== Subplot 4: Top 5 Plus =====
        _ax4 = _fig.add_subplot(4, 1, 4)
        _ax4.axis("off")
        _ax4.set_title(
            "TOP 5 PLUS (PER ITEM)", fontsize=12, fontweight="bold", color="#329632", pad=10
        )

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
            _tbl3 = _ax4.table(
                cellText=_rows_plus,
                colLabels=["Rak", "PLU", "Nama Produk", "Nominal"],
                cellLoc="center", loc="center",
                colWidths=[0.1, 0.15, 0.55, 0.2],
            )
            _tbl3.auto_set_font_size(False)
            _tbl3.set_fontsize(8)
            _tbl3.scale(1, 1.5)
            for _i in range(4):
                _cell = _tbl3[(0, _i)]
                _cell.set_facecolor("#97B3AE")
                _cell.set_text_props(color="white", weight="bold")

        plt.tight_layout()
        plt.savefig(filename, dpi=110, bbox_inches="tight", facecolor="#F0EEEA")
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