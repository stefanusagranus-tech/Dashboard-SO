"""
Yui Export — PDF Profesional 2 Halaman (pastel theme)
========================================================
- Halaman 1: Analisis Gambaran SO (KPI + ringkasan + donut + insight + tabel rak)
- Halaman 2: List Item yang Minus (per rak + total + insight)
- Gambar: matplotlib (pastel theme)
- Excel: ringkasan + rekap per rak
"""

import io
import os
import html as _html
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fpdf import FPDF


# =========================================================
# PALET WARNA PASTEL
# =========================================================
WARNA = {
    "sage":       (151, 179, 174),
    "sage_light": (210, 224, 211),
    "peach":      (240, 221, 214),
    "salmon":     (242, 195, 185),
    "beige":      (214, 203, 191),
    "offwhite":   (240, 238, 234),
    "dark":       (60, 60, 60),
    "white":      (255, 255, 255),
    "red":        (200, 50, 50),
    "green":      (50, 150, 50),
}

# Chart colors (hex, buat matplotlib)
CHART_COLORS = [
    "#97B3AE", "#F2C3B9", "#D2E0D3", "#F0DDD6", "#D6CBBF",
    "#B5C9C3", "#E8A99C", "#C4D4C5", "#E0CCC4", "#BEB0A5",
]


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
def _clean_text(text):
    """Clean HTML entities & karakter aneh."""
    try:
        _t = str(text)
        _t = _html.unescape(_t)
        _t = _t.replace("&#39;", "'").replace("&amp;", "&")
        _t = _t.replace("&quot;", '"').replace("&nbsp;", " ")
        return _t.strip()
    except Exception:
        return str(text)


def _format_nominal(val):
    try:
        return int(round(float(val)))
    except Exception:
        return 0


def _format_rp(val):
    _n = _format_nominal(val)
    _sign = "+" if _n >= 0 else "-"
    return f"{_sign}Rp {abs(_n):,}".replace(",", ".")


def _format_rp_no_sign(val):
    _n = _format_nominal(val)
    return f"Rp {abs(_n):,}".replace(",", ".")


def _hitung_btsb_nsb(net_sales, total_selisih, btsb_persen=0.15):
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
# DONUT CHART — Kontribusi per Rak
# =========================================================
def _generate_donut_per_rak(hasil):
    """Donut chart: kontribusi tiap rak terhadap total selisih."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _list_rak = hasil.get("list_rak", [])
        if not _list_rak:
            return None

        # Sort by abs nominal, descending
        _sorted = sorted(_list_rak, key=lambda x: abs(x.get("total", 0)), reverse=True)
        _top = _sorted[:6]
        _sisa = _sorted[6:]

        _labels = []
        _sizes = []
        for _r in _top:
            _nom = abs(_r.get("total", 0))
            if _nom > 0:
                _labels.append(f"Rak {_r.get('rak_id', '?')}")
                _sizes.append(_nom)

        if _sisa:
            _sisa_total = sum(abs(_r.get("total", 0)) for _r in _sisa)
            if _sisa_total > 0:
                _labels.append(f"Lainnya ({len(_sisa)} rak)")
                _sizes.append(_sisa_total)

        if not _sizes:
            return None

        _fig, _ax = plt.subplots(figsize=(6, 5))
        _fig.patch.set_facecolor("#F0EEEA")

        _wedges, _texts, _autotexts = _ax.pie(
            _sizes,
            labels=_labels,
            colors=CHART_COLORS[:len(_sizes)],
            autopct=lambda p: f"{p:.1f}%",
            startangle=90,
            wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
            textprops=dict(color="#3C3C3C", fontsize=9),
        )

        for _at in _autotexts:
            _at.set_color("white")
            _at.set_fontweight("bold")
            _at.set_fontsize(9)

        _ax.set_title(
            "KONTRIBUSI PER RAK",
            fontsize=12, fontweight="bold", color="#3C3C3C", pad=12,
        )

        plt.tight_layout()
        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", dpi=130, bbox_inches="tight", facecolor="#F0EEEA")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as e:
        print(f"[DONUT ERROR] {e}")
        return None


# =========================================================
# INSIGHT OTOMATIS
# =========================================================
def _generate_insight_hal1(hasil, sales_periode):
    """Insight otomatis halaman 1."""
    try:
        _list_rak = hasil.get("list_rak", [])
        _total_nom = hasil.get("total_nominal", 0)
        _btsb = sales_periode * 0.0015
        _status = "OVER" if abs(_total_nom) > _btsb else "AMAN"

        _insights = []
        _insights.append(
            f"Total SO: {hasil.get('total_rak', 0)} rak dengan nominal {_format_rp(_total_nom)}."
        )
        _insights.append(
            f"Sales periode: {_format_rp(sales_periode)}. BTSB (0,15%): {_format_rp(_btsb)}."
        )

        if _list_rak:
            _worst = min(_list_rak, key=lambda x: x.get("total", 0))
            _insights.append(
                f"Rak penyumbang minus terbesar: {_worst.get('rak_id', '?')} "
                f"({_format_rp(_worst.get('total', 0))}) oleh PIC {_worst.get('pic', '-')}."
            )

        _insights.append(
            f"Status: {_status} — "
            f"{'selisih melebihi batas BTSB, perlu perhatian.' if _status == 'OVER' else 'selisih masih dalam batas aman.'}"
        )

        return " ".join(_insights)
    except Exception as e:
        print(f"[INSIGHT1 ERROR] {e}")
        return "Data insight belum tersedia."


def _generate_insight_hal2(hasil):
    """Insight otomatis halaman 2."""
    try:
        _items_by_rak = hasil.get("items_by_rak", {})
        if not _items_by_rak:
            return "Belum ada item minus pada periode ini."

        # Cari item minus terbesar
        _all_items = []
        for _rak, _items in _items_by_rak.items():
            for _it in _items:
                _nom = float(_it.get("nominal_adjust", 0) or 0)
                if _nom < 0:
                    _all_items.append({**_it, "_nom": _nom})

        if not _all_items:
            return "Tidak ada item minus pada periode ini."

        _worst = min(_all_items, key=lambda x: x["_nom"])
        _total_minus = sum(_it["_nom"] for _it in _all_items)

        return (
            f"Item minus terbesar: {_clean_text(_worst.get('nama_produk', '-'))} "
            f"(PLU {_worst.get('plu', '-')}, rak {_worst.get('rak_id', '-')}) "
            f"senilai {_format_rp(_worst['_nom'])}. "
            f"Total {len(_all_items)} item minus dengan akumulasi {_format_rp(_total_minus)}."
        )
    except Exception as e:
        print(f"[INSIGHT2 ERROR] {e}")
        return "Data insight belum tersedia."


# =========================================================
# PDF CLASS
# =========================================================
class PDFLaporan(FPDF):
    """PDF dengan header & footer custom, font DejaVu."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._font_family = None
        self.judul_halaman = "LAPORAN STOCK OPNAME"

    def _setup_font(self):
        if self._font_family:
            return
        if _font_tersedia():
            self.add_font(fname=_FONT_PATH)
            self.add_font(fname=_FONT_PATH_BOLD, style="B")
            self._font_family = "DejaVuSansCondensed"
        else:
            self._font_family = "Helvetica"

    def set_my_font(self, style="", size=10):
        self._setup_font()
        try:
            self.set_font(self._font_family, style=style, size=size)
        except Exception:
            self.set_font("Helvetica", style=style, size=size)

    def header(self):
        # Header band sage
        self.set_fill_color(*WARNA["sage"])
        self.rect(0, 0, 210, 26, style="F")

        self.set_my_font(style="B", size=14)
        self.set_text_color(*WARNA["white"])
        self.set_xy(12, 6)
        self.cell(0, 7, self.judul_halaman, new_x="LMARGIN", new_y="NEXT")

        self.set_my_font(style="", size=9)
        self.set_text_color(*WARNA["offwhite"])
        self.set_xy(12, 14)
        self.cell(0, 5, "Toko C383 - Karang Satria", new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*WARNA["dark"])
        self.set_y(32)

    def footer(self):
        self.set_y(-15)
        self.set_my_font(style="I", size=8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Halaman {self.page_no()}", align="C")


# =========================================================
# KPI CARDS
# =========================================================
def _draw_kpi_cards(pdf, total_rak, total_item, total_nominal):
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


# =========================================================
# SECTION HEADER
# =========================================================
def _draw_section_header(pdf, judul, x=12, w=186, fill=None):
    if fill is None:
        fill = WARNA["sage"]
    _y = pdf.get_y()
    pdf.set_fill_color(*fill)
    pdf.rect(x, _y, w, 7, style="F")
    pdf.set_my_font(style="B", size=10)
    pdf.set_text_color(*WARNA["white"])
    pdf.set_xy(x + 2, _y + 1.5)
    pdf.cell(w - 4, 5, judul, align="L")
    pdf.set_text_color(*WARNA["dark"])
    pdf.ln(9)


# =========================================================
# EXPORT PDF — 2 HALAMAN
# =========================================================
def export_rekap_pdf(hasil, net_sales=0, filename="rekap_so.pdf"):
    """Export rekap SO jadi PDF 2 halaman (analisis + list item minus)."""
    try:
        _pdf = PDFLaporan()
        _pdf.set_auto_page_break(auto=True, margin=18)

        _list_rak = hasil.get("list_rak", [])
        _items_by_rak = hasil.get("items_by_rak", {})
        _rak_names = hasil.get("rak_names", {})
        _sales_periode = hasil.get("sales_periode", 0)
        _mode = hasil.get("mode", "hari_ini")
        _periode = hasil.get("periode", "-")

        # =========================================================
        # HALAMAN 1: ANALISIS GAMBARAN SO
        # =========================================================
        _pdf.judul_halaman = "ANALISIS GAMBARAN SO"
        _pdf.add_page()

        # --- KPI Cards ---
        _draw_kpi_cards(
            _pdf,
            hasil.get("total_rak", 0),
            hasil.get("total_item", 0),
            hasil.get("total_nominal", 0),
        )
        _pdf.ln(4)

        # --- Ringkasan + Sales ---
        _draw_section_header(_pdf, "RINGKASAN PERIODE")

        _total_nom = hasil.get("total_nominal", 0)
        _btsb = _sales_periode * 0.0015
        _status = "OVER" if abs(_total_nom) > _btsb else "AMAN"

        _pdf.set_my_font(style="", size=9)
        _pdf.set_text_color(*WARNA["dark"])

        _rows = [
            ("Tanggal", _periode),
            ("Total Rak di-SO", f"{hasil.get('total_rak', 0)} rak"),
            ("Nominal SO", _format_rp(_total_nom)),
            ("Sales Periode", _format_rp_no_sign(_sales_periode)),
            ("BTSB (0,15%)", _format_rp_no_sign(_btsb)),
        ]

        for _label, _val in _rows:
            _pdf.set_x(14)
            _pdf.cell(55, 6, _label)
            _pdf.set_my_font(style="B", size=9)
            _pdf.cell(0, 6, f": {_val}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_my_font(style="", size=9)

        # Keterangan status
        _pdf.set_x(14)
        _pdf.cell(55, 6, "Keterangan")
        _pdf.set_my_font(style="B", size=9)
        if _status == "OVER":
            _pdf.set_text_color(*WARNA["red"])
        else:
            _pdf.set_text_color(*WARNA["green"])
        _pdf.cell(0, 6, f": {_status}", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.ln(4)

        # --- Donut Chart ---
        _donut_buf = _generate_donut_per_rak(hasil)
        if _donut_buf:
            _draw_section_header(_pdf, "KONTRIBUSI PER RAK")
            _y_img = _pdf.get_y()
            _pdf.image(_donut_buf, x=55, y=_y_img, w=100)
            _pdf.set_y(_y_img + 85)
            _donut_buf.close()
            _pdf.ln(2)

        # --- Insight Halaman 1 ---
        _draw_section_header(_pdf, "INSIGHT", fill=WARNA["beige"])
        _pdf.set_my_font(style="I", size=9)
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.set_x(14)
        _pdf.multi_cell(182, 5.5, _generate_insight_hal1(hasil, _sales_periode))
        _pdf.ln(4)

        # --- Tabel List Rak ---
        _draw_section_header(_pdf, "DAFTAR RAK YANG DI-SO")

        # Header tabel
        _pdf.set_my_font(style="B", size=9)
        _pdf.set_fill_color(*WARNA["sage"])
        _pdf.set_text_color(*WARNA["white"])
        _col_w = [22, 70, 40, 25, 29]
        _pdf.cell(_col_w[0], 7, "RAK", fill=True, align="C")
        _pdf.cell(_col_w[1], 7, "NAMA RAK", fill=True, align="C")
        _pdf.cell(_col_w[2], 7, "PIC", fill=True, align="C")
        _pdf.cell(_col_w[3], 7, "TANGGAL", fill=True, align="C")
        _pdf.cell(_col_w[4], 7, "SELISIH", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

        # Body
        _pdf.set_my_font(style="", size=8)
        _pdf.set_text_color(*WARNA["dark"])
        for _i, _r in enumerate(_list_rak):
            _bg = WARNA["offwhite"] if _i % 2 == 0 else WARNA["white"]
            _pdf.set_fill_color(*_bg)
            _rak_id = str(_r.get("rak_id", "-"))
            _rak_name = _rak_names.get(_rak_id, "") or "RAK CUSTOM"
            _nom = _r.get("total", 0)

            _pdf.cell(_col_w[0], 6, _rak_id[:12], fill=True, align="C")
            _pdf.cell(_col_w[1], 6, _clean_text(_rak_name)[:40], fill=True, align="L")
            _pdf.cell(_col_w[2], 6, str(_r.get("pic", "-"))[:18], fill=True, align="C")
            _pdf.cell(_col_w[3], 6, str(_r.get("tanggal", "-"))[:12], fill=True, align="C")

            if _nom < 0:
                _pdf.set_text_color(*WARNA["red"])
            else:
                _pdf.set_text_color(*WARNA["green"])
            _pdf.cell(_col_w[4], 6, _format_rp(_nom), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(*WARNA["dark"])

        # =========================================================
        # HALAMAN 2: LIST ITEM YANG MINUS
        # =========================================================
        _pdf.judul_halaman = "LIST ITEM YANG MINUS"
        _pdf.add_page()

        # Limit item per rak berdasarkan mode
        if _mode == "hari_ini":
            _limit_per_rak = None  # semua
        elif _mode == "minggu_ini":
            _limit_per_rak = 10
        else:  # bulan_ini
            _limit_per_rak = 20

        # Loop per rak
        if _items_by_rak:
            # Urutkan rak berdasarkan total minus (terbesar dulu)
            _rak_sorted = sorted(
                _items_by_rak.items(),
                key=lambda x: sum(
                    float(i.get("nominal_adjust", 0) or 0) for i in x[1]
                ),
            )

            for _rak_id, _items in _rak_sorted:
                # Filter item minus
                _items_minus = [
                    i for i in _items
                    if float(i.get("nominal_adjust", 0) or 0) < 0
                ]

                if not _items_minus:
                    continue

                # Sort by nominal (paling minus dulu)
                _items_minus.sort(key=lambda x: float(x.get("nominal_adjust", 0) or 0))

                # Limit
                if _limit_per_rak is not None:
                    _items_minus = _items_minus[:_limit_per_rak]

                # Section header per rak
                _rak_name = _rak_names.get(_rak_id, "") or "RAK CUSTOM"
                _total_rak = sum(float(i.get("nominal_adjust", 0) or 0) for i in _items_minus)

                _draw_section_header(
                    _pdf,
                    f"RAK {_rak_id} — {_clean_text(_rak_name)[:40]}",
                    fill=WARNA["salmon"],
                )

                # Header tabel
                _pdf.set_my_font(style="B", size=8)
                _pdf.set_fill_color(*WARNA["salmon"])
                _pdf.set_text_color(*WARNA["white"])
                _c = [22, 75, 15, 20, 54]
                _pdf.cell(_c[0], 6, "PLU", fill=True, align="C")
                _pdf.cell(_c[1], 6, "NAMA PRODUK", fill=True, align="C")
                _pdf.cell(_c[2], 6, "QTY VAR", fill=True, align="C")
                _pdf.cell(_c[3], 6, "PIC", fill=True, align="C")
                _pdf.cell(_c[4], 6, "NOMINAL", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

                # Body
                _pdf.set_my_font(style="", size=8)
                _pdf.set_text_color(*WARNA["dark"])
                for _idx, _it in enumerate(_items_minus):
                    _bg = WARNA["offwhite"] if _idx % 2 == 0 else WARNA["white"]
                    _pdf.set_fill_color(*_bg)
                    _nom = float(_it.get("nominal_adjust", 0) or 0)
                    _qty_var = _it.get("qty_var", 0)

                    _pdf.cell(_c[0], 5.5, str(_it.get("plu", "-"))[:12], fill=True, align="C")
                    _pdf.cell(_c[1], 5.5, _clean_text(_it.get("nama_produk", "-"))[:42], fill=True, align="L")
                    _pdf.cell(_c[2], 5.5, str(_qty_var), fill=True, align="C")
                    _pdf.cell(_c[3], 5.5, str(_it.get("pic", "-"))[:12], fill=True, align="C")
                    _pdf.set_text_color(*WARNA["red"])
                    _pdf.cell(_c[4], 5.5, _format_rp(_nom), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                    _pdf.set_text_color(*WARNA["dark"])

                # Total per rak
                _pdf.set_fill_color(*WARNA["beige"])
                _pdf.set_my_font(style="B", size=9)
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.cell(sum(_c[:4]), 6.5, f"TOTAL RAK {_rak_id}", fill=True, align="R")
                _pdf.set_text_color(*WARNA["red"])
                _pdf.cell(_c[4], 6.5, _format_rp(_total_rak), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.ln(5)

            # Insight Halaman 2
            _draw_section_header(_pdf, "INSIGHT", fill=WARNA["beige"])
            _pdf.set_my_font(style="I", size=9)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_x(14)
            _pdf.multi_cell(182, 5.5, _generate_insight_hal2(hasil))
        else:
            _pdf.set_my_font(style="I", size=10)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.cell(0, 10, "Tidak ada item minus pada periode ini.", align="C")

        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        print(f"[EXPORT_PDF ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return None


# =========================================================
# GAMBAR
# =========================================================
def export_rekap_image(hasil, net_sales=0, filename="rekap_so.png"):
    """Export rekap jadi gambar (matplotlib pastel theme)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _list_rak = hasil.get("list_rak", [])
        if not _list_rak:
            return None

        _rak_names = hasil.get("rak_names", {})

        _fig = plt.figure(figsize=(12, 8))
        _fig.patch.set_facecolor("#F0EEEA")

        # Title
        _fig.suptitle(
            "LAPORAN STOCK OPNAME — TOKO C383",
            fontsize=14, fontweight="bold", color="#3C3C3C", y=0.98,
        )

        # Subplot 1: Tabel Rekap
        _ax1 = _fig.add_subplot(2, 1, 1)
        _ax1.axis("off")
        _ax1.set_title("REKAP PER RAK", fontsize=11, fontweight="bold", color="#3C3C3C", pad=8)

        _df = pd.DataFrame(_list_rak)
        _df["Nama Rak"] = _df["rak_id"].apply(lambda x: _rak_names.get(x, "") or "RAK CUSTOM")
        _df["Nominal"] = _df["total"].apply(
            lambda x: f"{'+' if _format_nominal(x) >= 0 else '-'}Rp {abs(_format_nominal(x)):,}".replace(",", ".")
        )

        _tbl = _ax1.table(
            cellText=_df[["rak_id", "Nama Rak", "pic", "Nominal"]].values,
            colLabels=["Rak", "Nama Rak", "PIC", "Nominal"],
            cellLoc="center", loc="center",
            colWidths=[0.12, 0.38, 0.18, 0.32],
        )
        _tbl.auto_set_font_size(False)
        _tbl.set_fontsize(9)
        _tbl.scale(1, 1.5)
        for _i in range(4):
            _cell = _tbl[(0, _i)]
            _cell.set_facecolor("#97B3AE")
            _cell.set_text_props(color="white", weight="bold")

        # Subplot 2: Donut
        _ax2 = _fig.add_subplot(2, 2, 3)
        _list_sorted = sorted(_list_rak, key=lambda x: abs(x.get("total", 0)), reverse=True)
        _top = _list_sorted[:6]
        _labels = [f"Rak {r.get('rak_id', '?')}" for r in _top]
        _sizes = [abs(r.get("total", 0)) for r in _top]

        if _sizes:
            _wedges, _texts, _autotexts = _ax2.pie(
                _sizes, labels=_labels,
                colors=CHART_COLORS[:len(_sizes)],
                autopct=lambda p: f"{p:.1f}%",
                startangle=90,
                wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2),
                textprops=dict(color="#3C3C3C", fontsize=8),
            )
            for _at in _autotexts:
                _at.set_color("white")
                _at.set_fontweight("bold")
                _at.set_fontsize(8)
            _ax2.set_title("KONTRIBUSI PER RAK", fontsize=11, fontweight="bold", color="#3C3C3C")

        # Subplot 3: Insight
        _ax3 = _fig.add_subplot(2, 2, 4)
        _ax3.axis("off")
        _ax3.set_title("INSIGHT", fontsize=11, fontweight="bold", color="#3C3C3C")
        _insight = _generate_insight_hal1(hasil, hasil.get("sales_periode", 0))
        _ax3.text(
            0.05, 0.5, _insight,
            fontsize=9, color="#3C3C3C",
            wrap=True, verticalalignment="center",
            transform=_ax3.transAxes,
        )

        plt.tight_layout()
        plt.savefig(filename, dpi=110, bbox_inches="tight", facecolor="#F0EEEA")
        plt.close(_fig)
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
        _rak_names = hasil.get("rak_names", {})

        _df_rak = pd.DataFrame(hasil.get("list_rak", []))
        if not _df_rak.empty:
            _df_rak["Nama Rak"] = _df_rak["rak_id"].apply(lambda x: _rak_names.get(x, "") or "RAK CUSTOM")
            _df_rak = _df_rak.rename(columns={
                "rak_id": "Rak", "total": "Nominal",
                "pic": "PIC", "tanggal": "Tanggal",
            })
            _df_rak["Nominal"] = _df_rak["Nominal"].apply(_format_nominal)
            _df_rak = _df_rak[["Rak", "Nama Rak", "Nominal", "PIC", "Tanggal"]]

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

def export_rekap_pdf(hasil, net_sales=0, filename="rekap_so.pdf"):
    """Export rekap SO jadi PDF — versi PALING SIMPLE."""
    try:
        from fpdf import FPDF
        _pdf = FPDF()
        _pdf.add_page()
        _pdf.set_font("Helvetica", "B", 20)
        _pdf.cell(0, 20, "HELLO YUI", ln=True, align="C")
        _pdf.set_font("Helvetica", "", 12)
        _pdf.cell(0, 10, "PDF test berhasil", ln=True, align="C")
        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        import traceback
        _err = f"ERROR: {str(e)}\n\n{traceback.format_exc()}"
        print(_err)
        return _err.encode("utf-8")