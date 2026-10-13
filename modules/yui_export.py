"""
Yui Export — PDF Profesional 2 Halaman (pastel theme) + Gambar + Excel
========================================================================
- PDF: fpdf2 + DejaVu font + donut + line chart + insight otomatis + watermark
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
    "sage": (151, 179, 174),
    "sage_light": (210, 224, 211),
    "sage_deep": (95, 122, 117),              # ← TAMBAH: sage gelap
    "peach": (240, 221, 214),
    "salmon": (242, 195, 185),
    "beige": (214, 203, 191),
    "offwhite": (240, 238, 234),
    "dark": (60, 60, 60),
    "white": (255, 255, 255),
    "red": (200, 50, 50),
    "green": (50, 150, 50),
    "terracotta_light": (232, 213, 201),      # ← TAMBAH: pastel terracotta
    "highlight": (237, 232, 222),             # ← TAMBAH: highlight cream
}

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
    return {"btsb": _btsb, "selisih": _selisih_abs, "nsb": _nsb, "status": _status}


# =========================================================
# CHART: DONUT PER RAK
# =========================================================
def _generate_donut_per_rak(hasil):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _list_rak = hasil.get("list_rak", [])
        if not _list_rak:
            return None

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
                _labels.append(f"Lainnya ({len(_sisa)})")
                _sizes.append(_sisa_total)

        if not _sizes:
            return None

        _fig, _ax = plt.subplots(figsize=(6, 6))
        _ax.set_aspect("equal")
        _fig.patch.set_facecolor("#F0EEEA")

        _wedges, _texts, _autotexts = _ax.pie(
            _sizes, labels=_labels,
            colors=CHART_COLORS[:len(_sizes)],
            autopct=lambda p: f"{p:.1f}%",
            startangle=90,
            wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
            textprops=dict(color="#3C3C3C", fontsize=8),
        )
        for _at in _autotexts:
            _at.set_color("white")
            _at.set_fontweight("bold")
            _at.set_fontsize(8)

        _ax.set_title("KONTRIBUSI PER RAK", fontsize=11, fontweight="bold", color="#3C3C3C", pad=8)

        plt.tight_layout()
        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", dpi=120, bbox_inches="tight", facecolor="#F0EEEA")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as e:
        print(f"[DONUT ERROR] {e}")
        return None


# =========================================================
# CHART: LINE 5 HARI TERAKHIR
# =========================================================
def _generate_trend_line_5hari(hasil):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from modules.supabase_client import get_supabase

        _sb = get_supabase()
        if _sb is None:
            return None

        _now = datetime.now(ZoneInfo("Asia/Jakarta")).date()
        _start = _now - timedelta(days=4)

        _res = (
            _sb.table("so_rak_harian")
            .select("so_date, nominal_adjust")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _now.isoformat())
            .execute()
        )

        if not _res.data:
            return None

        _df = pd.DataFrame(_res.data)
        _df["so_date"] = pd.to_datetime(_df["so_date"], errors="coerce")
        _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
        _df = _df.dropna(subset=["so_date"])

        _grp = _df.groupby("so_date")["nominal_adjust"].sum().reset_index()
        _grp = _grp.sort_values("so_date")

        if _grp.empty:
            return None

        _fig, _ax = plt.subplots(figsize=(10, 2.3))
        _fig.patch.set_facecolor("#F0EEEA")
        _ax.set_facecolor("#F0EEEA")

        _x_labels = _grp["so_date"].dt.strftime("%d/%m")
        _ax.plot(_x_labels, _grp["nominal_adjust"],
                 color="#97B3AE", linewidth=2.5,
                 marker="o", markersize=6,
                 markerfacecolor="#F2C3B9",
                 markeredgecolor="#97B3AE", markeredgewidth=1.5)
        _ax.axhline(0, color="#3C3C3C", linewidth=0.7, linestyle="--")
        _ax.fill_between(range(len(_grp)), _grp["nominal_adjust"], 0, alpha=0.15, color="#97B3AE")

        _ax.tick_params(axis="x", labelsize=8)
        _ax.tick_params(axis="y", labelsize=8)
        _ax.spines["top"].set_visible(False)
        _ax.spines["right"].set_visible(False)
        _ax.spines["left"].set_color("#D6CBBF")
        _ax.spines["bottom"].set_color("#D6CBBF")
        _ax.grid(axis="y", linestyle="--", alpha=0.4, color="#D6CBBF")
        _ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}".replace(",", ".")))

        plt.tight_layout()
        _buf = io.BytesIO()
        plt.savefig(_buf, format="png", dpi=120, bbox_inches="tight", facecolor="#F0EEEA")
        plt.close(_fig)
        _buf.seek(0)
        return _buf
    except Exception as e:
        print(f"[TREND LINE ERROR] {e}")
        return None


# =========================================================
# INSIGHT OTOMATIS
# =========================================================
def _generate_insight_hal1(hasil):
    try:
        _list_rak = hasil.get("list_rak", [])
        _total_nom = hasil.get("total_nominal", 0)
        _sales = hasil.get("sales_periode", 0)
        _btsb = _sales * 0.0015
        _status = "OVER" if abs(_total_nom) > _btsb else "AMAN"

        _insights = [
            f"Total SO: {hasil.get('total_rak', 0)} rak dengan nominal {_format_rp(_total_nom)}.",
            f"Sales periode: {_format_rp_no_sign(_sales)}. BTSB (0,15%): {_format_rp_no_sign(_btsb)}.",
        ]

        if _list_rak:
            _worst = min(_list_rak, key=lambda x: x.get("total", 0))
            _insights.append(
                f"Rak penyumbang minus terbesar: {_worst.get('rak_id', '?')} "
                f"({_format_rp(_worst.get('total', 0))}) oleh PIC {_worst.get('pic', '-')}."
            )

        _insights.append(
            f"Status: {_status} - "
            + ("selisih melebihi batas BTSB, perlu perhatian." if _status == "OVER" else "selisih masih dalam batas aman.")
        )
        return " ".join(_insights)
    except Exception as e:
        print(f"[INSIGHT1 ERROR] {e}")
        return "Data insight belum tersedia."


def _generate_insight_hal2(hasil):
    try:
        _items_by_rak = hasil.get("items_by_rak", {})
        if not _items_by_rak:
            return "Belum ada item pada periode ini."

        _all_items = []
        for _rak, _items in _items_by_rak.items():
            for _it in _items:
                _nom = float(_it.get("nominal_adjust", 0) or 0)
                _all_items.append({**_it, "_nom": _nom})

        if not _all_items:
            return "Belum ada item pada periode ini."

        _worst_minus = min(_all_items, key=lambda x: x["_nom"])
        _best_plus = max(_all_items, key=lambda x: x["_nom"])
        _total_minus = sum(_it["_nom"] for _it in _all_items if _it["_nom"] < 0)
        _total_plus = sum(_it["_nom"] for _it in _all_items if _it["_nom"] > 0)
        _total_all = _total_minus + _total_plus
        _count_minus = sum(1 for _it in _all_items if _it["_nom"] < 0)
        _count_plus = sum(1 for _it in _all_items if _it["_nom"] > 0)

        return (
            f"Item minus terbesar: {_clean_text(_worst_minus.get('nama_produk', '-'))} "
            f"(PLU {_worst_minus.get('plu', '-')}, rak {_worst_minus.get('rak_id', '-')}) "
            f"senilai {_format_rp(_worst_minus['_nom'])}. "
            f"Item plus terbesar: {_clean_text(_best_plus.get('nama_produk', '-'))} "
            f"(PLU {_best_plus.get('plu', '-')}, rak {_best_plus.get('rak_id', '-')}) "
            f"senilai {_format_rp(_best_plus['_nom'])}. "
            f"Total {len(_all_items)} item ({_count_minus} minus, {_count_plus} plus). "
            f"Total selisih barang 1 hari: {_format_rp(_total_all)}."
        )
    except Exception as e:
        print(f"[INSIGHT2 ERROR] {e}")
        return "Data insight belum tersedia."



# =========================================================
# EXPORT PDF — 2 HALAMAN
# =========================================================
def export_rekap_pdf(hasil, net_sales=0, filename="rekap_so.pdf"):
    """Export rekap SO jadi PDF profesional — 2 halaman + auto-break per rak."""
    try:
        from fpdf import FPDF
        import os

        _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _font_reg = os.path.join(_base, "fonts", "DejaVuSansCondensed.ttf")
        _font_bold = os.path.join(_base, "fonts", "DejaVuSansCondensed-Bold.ttf")

        _pdf = FPDF()
        _pdf.set_auto_page_break(auto=True, margin=15)

        _use_dejavu = False
        try:
            if os.path.exists(_font_reg) and os.path.exists(_font_bold):
                _pdf.add_font(fname=_font_reg)
                _pdf.add_font(fname=_font_bold, style="B")
                _use_dejavu = True
                print("[PDF] Pakai DejaVu font")
            else:
                print(f"[PDF] Font gak ada: {_font_reg} / {_font_bold}")
        except Exception as _e:
            print(f"[PDF] Gagal load DejaVu: {_e}")

        def _sf(style="", size=10):
            try:
                if _use_dejavu:
                    _pdf.set_font("DejaVuSansCondensed", style=style, size=size)
                else:
                    _pdf.set_font("Helvetica", style=style, size=size)
            except Exception:
                _pdf.set_font("Helvetica", style=style, size=size)

        def _section_header(judul, fill_color=None, x=12, w=186):
            if fill_color is None:
                fill_color = WARNA["sage"]
            _y = _pdf.get_y()
            _pdf.set_fill_color(*fill_color)
            _pdf.rect(x, _y, w, 7, style="F")
            _sf(style="B", size=10)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(x + 2, _y + 1.5)
            _pdf.cell(w - 4, 5, judul)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.ln(9)

        def _watermark():
            _pdf.set_y(-25)
            _sf(style="I", size=7)
            _pdf.set_text_color(180, 180, 180)
            _pdf.cell(0, 5, "Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383",
                      align="C", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(*WARNA["dark"])

        # =========================================================
        # HALAMAN 1: ANALISIS GAMBARAN SO
        # =========================================================
        _pdf.add_page()

        # Header band
        _pdf.set_fill_color(*WARNA["sage_deep"])
        _pdf.rect(0, 0, 210, 22, style="F")
        _sf(style="B", size=14)
        _pdf.set_text_color(*WARNA["white"])
        _pdf.set_xy(12, 4)
        _pdf.cell(0, 7, "ANALISIS GAMBARAN SO", new_x="LMARGIN", new_y="NEXT")
        _sf(style="", size=9)
        _pdf.set_xy(12, 12)
        _pdf.cell(0, 5, "Toko C383 - Karang Satria", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.set_y(28)

        # KPI CARDS
        _y = _pdf.get_y()
        _card_w = 58
        _gap = 4
        _x_start = (210 - (3 * _card_w + 2 * _gap)) / 2

        _kpi = [
            ("TOTAL RAK", f"{hasil.get('total_rak', 0)} rak", WARNA["sage_light"]),
            ("TOTAL ITEM", f"{hasil.get('total_item', 0)} item", WARNA["terracotta_light"]),
            ("TOTAL NOMINAL", _format_rp(hasil.get("total_nominal", 0)), WARNA["highlight"]),
        ]
        for _i, (_lbl, _val, _bg) in enumerate(_kpi):
            _x = _x_start + _i * (_card_w + _gap)
            _pdf.set_fill_color(*_bg)
            _pdf.rect(_x, _y, _card_w, 20, style="F")
            _sf(style="B", size=8)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_xy(_x + 3, _y + 3)
            _pdf.cell(_card_w - 6, 5, _lbl)
            _sf(style="B", size=12)
            _pdf.set_xy(_x + 3, _y + 10)
            _pdf.cell(_card_w - 6, 7, _val)
        _pdf.set_y(_y + 24)

        # RINGKASAN
        _section_header("RINGKASAN PERIODE")

        _sales = hasil.get("sales_periode", 0)
        _btsb = _sales * 0.0015
        _total_nom = hasil.get("total_nominal", 0)
        _status = "OVER" if abs(_total_nom) > _btsb else "AMAN"

        _rows = [
            ("Tanggal", hasil.get("periode", "-")),
            ("Total Rak di-SO", f"{hasil.get('total_rak', 0)} rak"),
            ("Nominal SO", _format_rp(_total_nom)),
            ("Sales Periode", _format_rp_no_sign(_sales)),
            ("BTSB (0,15%)", _format_rp_no_sign(_btsb)),
        ]
        _sf(style="", size=9)
        for _lbl, _val in _rows:
            _pdf.set_x(14)
            _pdf.cell(55, 6, _lbl)
            _sf(style="B", size=9)
            _pdf.cell(0, 6, f": {_val}", new_x="LMARGIN", new_y="NEXT")
            _sf(style="", size=9)

        _pdf.set_x(14)
        _pdf.cell(55, 6, "Keterangan")
        _sf(style="B", size=9)
        if _status == "OVER":
            _pdf.set_text_color(*WARNA["red"])
        else:
            _pdf.set_text_color(*WARNA["green"])
        _pdf.cell(0, 6, f": {_status}", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.ln(6)

        # DONUT CHART
        _donut_buf = _generate_donut_per_rak(hasil) if "_generate_donut_per_rak" in globals() else None
        if _donut_buf:
            _section_header("KONTRIBUSI PER RAK")
            _y_img = _pdf.get_y()
            _pdf.image(_donut_buf, x=55, y=_y_img, w=100)
            _pdf.set_y(_y_img + 85)
            _donut_buf.close()
            _pdf.ln(2)

        # INSIGHT
        _section_header("INSIGHT", fill_color=WARNA["beige"])
        _sf(style="I", size=9)
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.set_x(14)
        _insight_text = _generate_insight_hal1(hasil) if "_generate_insight_hal1" in globals() else "Insight belum tersedia."
        _pdf.multi_cell(182, 5.5, _insight_text)
        _pdf.ln(4)

        # DAFTAR RAK
        _section_header("DAFTAR RAK YANG DI-SO")

        _pdf.set_font("Helvetica", "B", 9) if not _use_dejavu else _sf(style="B", size=9)
        _sf(style="B", size=9)
        _pdf.set_fill_color(*WARNA["sage"])
        _pdf.set_text_color(*WARNA["white"])
        _col = [22, 65, 35, 30, 34]
        _pdf.set_x(12)
        _pdf.cell(_col[0], 7, "RAK", fill=True, align="C")
        _pdf.cell(_col[1], 7, "NAMA RAK", fill=True, align="C")
        _pdf.cell(_col[2], 7, "PIC", fill=True, align="C")
        _pdf.cell(_col[3], 7, "TANGGAL", fill=True, align="C")
        _pdf.cell(_col[4], 7, "SELISIH", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

        _sf(style="", size=8)
        _pdf.set_text_color(*WARNA["dark"])
        _rak_names = hasil.get("rak_names", {})
        for _i, _r in enumerate(hasil.get("list_rak", [])):
            _bg = WARNA["offwhite"] if _i % 2 == 0 else WARNA["white"]
            _pdf.set_fill_color(*_bg)
            _pdf.set_x(12)
            _rak_id = str(_r.get("rak_id", "-"))
            _rak_name = _clean_text(_rak_names.get(_rak_id, "") or "RAK CUSTOM")
            _nom = _r.get("total", 0)

            _pdf.cell(_col[0], 6, _rak_id[:12], fill=True, align="C")
            _pdf.cell(_col[1], 6, _rak_name[:38], fill=True, align="L")
            _pdf.cell(_col[2], 6, str(_r.get("pic", "-"))[:16], fill=True, align="C")
            _pdf.cell(_col[3], 6, str(_r.get("tanggal", "-"))[:12], fill=True, align="C")

            if _nom < 0:
                _pdf.set_text_color(*WARNA["red"])
            else:
                _pdf.set_text_color(*WARNA["green"])
            _pdf.cell(_col[4], 6, _format_rp(_nom), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(*WARNA["dark"])

        _watermark()

        # =========================================================
        # HALAMAN 2+: LIST ITEM — AUTO-BREAK PER RAK
        # =========================================================
        _pdf.add_page()

        _pdf.set_fill_color(*WARNA["sage_deep"])
        _pdf.rect(0, 0, 210, 22, style="F")
        _sf(style="B", size=14)
        _pdf.set_text_color(*WARNA["white"])
        _pdf.set_xy(12, 4)
        _pdf.cell(0, 7, "LIST ITEM YANG DI-SO", new_x="LMARGIN", new_y="NEXT")
        _sf(style="", size=9)
        _pdf.set_xy(12, 12)
        _pdf.cell(0, 5, "Toko C383 - Karang Satria", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.set_y(28)

        _items_by_rak = hasil.get("items_by_rak", {})
        _mode = hasil.get("mode", "hari_ini")
        _limit = None if _mode == "hari_ini" else (10 if _mode == "minggu_ini" else 20)

        # Hitung tinggi minimum halaman baru
        _PAGE_BOTTOM_MARGIN = 30
        _MIN_SPACE_FOR_RAK = 40  # minimal buat header + 1 row + total

        if _items_by_rak:
            _rak_sorted = sorted(
                _items_by_rak.items(),
                key=lambda x: sum(float(i.get("nominal_adjust", 0) or 0) for i in x[1]),
            )

            for _rak_id, _items in _rak_sorted:
                _items_all = list(_items)
                if not _items_all:
                    continue
                _items_all.sort(key=lambda x: float(x.get("nominal_adjust", 0) or 0))
                if _limit:
                    _items_all = _items_all[:_limit]

                _total_rak = sum(float(i.get("nominal_adjust", 0) or 0) for i in _items_all)
                _rak_name = _clean_text(_rak_names.get(_rak_id, "") or "RAK CUSTOM")

                # ✅ Cek apakah cukup ruang untuk header + 1 row + total
                _y_now = _pdf.get_y()
                _space_left = 297 - _y_now - _PAGE_BOTTOM_MARGIN

                # Perkiraan tinggi: header (9) + tabel header (6) + row pertama (5.5) + total (6.5) + margin (5)
                _need = 9 + 6 + 5.5 + 6.5 + 5 + 10

                if _space_left < _need:
                    _pdf.add_page()
                    # Header band lagi
                    _pdf.set_fill_color(*WARNA["sage_deep"])
                    _pdf.rect(0, 0, 210, 22, style="F")
                    _sf(style="B", size=14)
                    _pdf.set_text_color(*WARNA["white"])
                    _pdf.set_xy(12, 4)
                    _pdf.cell(0, 7, "LIST ITEM YANG DI-SO (lanjutan)", new_x="LMARGIN", new_y="NEXT")
                    _sf(style="", size=9)
                    _pdf.set_xy(12, 12)
                    _pdf.cell(0, 5, "Toko C383 - Karang Satria", new_x="LMARGIN", new_y="NEXT")
                    _pdf.set_text_color(*WARNA["dark"])
                    _pdf.set_y(28)

                # Section header per rak
                _pdf.set_fill_color(*WARNA["terracotta_light"])
                _y_sect = _pdf.get_y()
                _pdf.rect(12, _y_sect, 186, 7, style="F")
                _sf(style="B", size=10)
                _pdf.set_text_color(*WARNA["white"])
                _pdf.set_xy(14, _y_sect + 1.5)
                _pdf.cell(0, 5, f"RAK {_rak_id} - {_rak_name[:40]}")
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.ln(9)

                # Header tabel — TANPA QTY
                _sf(style="B", size=8)
                _pdf.set_fill_color(*WARNA["terracotta_light"])
                _pdf.set_text_color(*WARNA["white"])
                _c = [22, 95, 20, 49]  # RAK, NAMA, PIC, NOMINAL (Qty dihapus)
                _pdf.set_x(12)
                _pdf.cell(_c[0], 6, "PLU", fill=True, align="C")
                _pdf.cell(_c[1], 6, "NAMA PRODUK", fill=True, align="C")
                _pdf.cell(_c[2], 6, "PIC", fill=True, align="C")
                _pdf.cell(_c[3], 6, "NOMINAL", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

                # Body
                _sf(style="", size=8)
                _pdf.set_text_color(*WARNA["dark"])
                for _idx, _it in enumerate(_items_all):
                    # Cek page break per row
                    _y_row = _pdf.get_y()
                    if _y_row > 297 - _PAGE_BOTTOM_MARGIN:
                        _pdf.add_page()
                        _pdf.set_fill_color(*WARNA["sage_deep"])
                        _pdf.rect(0, 0, 210, 22, style="F")
                        _sf(style="B", size=14)
                        _pdf.set_text_color(*WARNA["white"])
                        _pdf.set_xy(12, 4)
                        _pdf.cell(0, 7, "LIST ITEM YANG DI-SO (lanjutan)", new_x="LMARGIN", new_y="NEXT")
                        _sf(style="", size=9)
                        _pdf.set_xy(12, 12)
                        _pdf.cell(0, 5, "Toko C383 - Karang Satria", new_x="LMARGIN", new_y="NEXT")
                        _pdf.set_text_color(*WARNA["dark"])
                        _pdf.set_y(28)
                        # Header tabel lagi
                        _sf(style="B", size=8)
                        _pdf.set_fill_color(*WARNA["terracotta_light"])
                        _pdf.set_text_color(*WARNA["white"])
                        _pdf.set_x(12)
                        _pdf.cell(_c[0], 6, "PLU", fill=True, align="C")
                        _pdf.cell(_c[1], 6, "NAMA PRODUK", fill=True, align="C")
                        _pdf.cell(_c[2], 6, "PIC", fill=True, align="C")
                        _pdf.cell(_c[3], 6, "NOMINAL", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
                        _sf(style="", size=8)
                        _pdf.set_text_color(*WARNA["dark"])

                    _bg = WARNA["offwhite"] if _idx % 2 == 0 else WARNA["white"]
                    _pdf.set_fill_color(*_bg)
                    _pdf.set_x(12)
                    _nom = float(_it.get("nominal_adjust", 0) or 0)
                    _plu = str(_it.get("plu", "-"))[:12]
                    _nama = _clean_text(_it.get("nama_produk", "-"))[:55]
                    _pic = str(_it.get("pic", "-"))[:12]

                    _pdf.cell(_c[0], 5.5, _plu, fill=True, align="C")
                    _pdf.cell(_c[1], 5.5, _nama, fill=True, align="L")
                    _pdf.cell(_c[2], 5.5, _pic, fill=True, align="C")
                    if _nom < 0:
                        _pdf.set_text_color(*WARNA["red"])
                    else:
                        _pdf.set_text_color(*WARNA["green"])
                    _pdf.cell(_c[3], 5.5, _format_rp(_nom), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                    _pdf.set_text_color(*WARNA["dark"])

                # Total per rak
                _pdf.set_x(12)
                _pdf.set_fill_color(*WARNA["beige"])
                _sf(style="B", size=9)
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.cell(sum(_c[:3]), 6.5, f"TOTAL RAK {_rak_id}", fill=True, align="R")
                if _total_rak < 0:
                    _pdf.set_text_color(*WARNA["red"])
                else:
                    _pdf.set_text_color(*WARNA["green"])
                _pdf.cell(_c[3], 6.5, _format_rp(_total_rak), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.ln(5)

            # Insight halaman 2
            _section_header("INSIGHT", fill_color=WARNA["beige"])
            _sf(style="I", size=9)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_x(14)
            _insight2 = _generate_insight_hal2(hasil) if "_generate_insight_hal2" in globals() else "Insight belum tersedia."
            _pdf.multi_cell(182, 5.5, _insight2)
        else:
            _sf(style="I", size=10)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.cell(0, 10, "Tidak ada item pada periode ini.", align="C")

        _watermark()

        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        import traceback
        print(f"[EXPORT_PDF ERROR] {e}")
        print(traceback.format_exc())
        # Return error dalam bytes biar caller bisa nampilin di UI
        _err = f"ERROR:{type(e).__name__}: {str(e)[:500]}"
        return _err.encode("utf-8")
        

# =========================================================
# EXPORT GAMBAR (matplotlib)
# =========================================================
def export_rekap_image(hasil, net_sales=0, filename="rekap_so.png"):
    """Export rekap SO jadi infografis PNG — matplotlib murni."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch, Rectangle
        import numpy as np
        import textwrap
        import pandas as pd
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        # =========================================================
        # PALET
        # =========================================================
        W = {
            "bg": "#F5F1EA",
            "sage": "#5E7A75",
            "sage_deep": "#3D5A55",
            "sage_light": "#D9E4E0",
            "terracotta": "#B5745E",
            "terracotta_light": "#E8D5C9",
            "highlight": "#EDE8DE",
            "text": "#2D2A26",
            "text_sec": "#6B6560",
            "text_muted": "#9C9488",
            "divider": "#DDD5C8",
            "white": "#FFFFFF",
            "red": "#B8383A",
            "green": "#4A7C59",
            "bar_neg": "#C9907E",
            "bar_pos": "#7B9B95",
        }

        # =========================================================
        # FORMAT HELPERS
        # =========================================================
        def _rp(val):
            n = int(round(float(val)))
            sign = "+" if n >= 0 else "-"
            return f"{sign}Rp {abs(n):,}".replace(",", ".")

        def _rp_no_sign(val):
            n = int(round(float(val)))
            return f"Rp {abs(n):,}".replace(",", ".")

        def _rp_short(val):
            n = int(round(float(val)))
            if abs(n) >= 1_000_000:
                return f"{n/1_000_000:+.1f}M"
            if abs(n) >= 1_000:
                return f"{n/1_000:+.0f}K"
            return f"{n:+d}"

        def _rp_short_no_sign(val):
            n = int(round(float(val)))
            if abs(n) >= 1_000_000:
                return f"{n/1_000_000:.1f}M"
            if abs(n) >= 1_000:
                return f"{n/1_000:.0f}K"
            return f"{n:d}"

        # =========================================================
        # DRAW HELPERS
        # =========================================================
        def _draw_card(ax, x, y, w, h, color, radius=0.015):
            card = FancyBboxPatch(
                (x, y), w, h,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                facecolor=color, edgecolor="none",
                transform=ax.transAxes, zorder=1,
            )
            ax.add_patch(card)

        def _text(ax, x, y, s, size=10, color=None, weight="normal",
                  ha="left", va="center"):
            if color is None:
                color = W["text"]
            return ax.text(
                x, y, s, fontsize=size, color=color, fontweight=weight,
                ha=ha, va=va, transform=ax.transAxes, zorder=10,
            )

        def _divider(ax, x, y, w, color=None, thickness=0.0015):
            if color is None:
                color = W["divider"]
            line = Rectangle(
                (x, y), w, thickness,
                facecolor=color, edgecolor="none",
                transform=ax.transAxes, zorder=5,
            )
            ax.add_patch(line)

        def _divider_v(ax, x, y, h, color=None, thickness=0.0008):
            if color is None:
                color = W["divider"]
            line = Rectangle(
                (x, y), thickness, h,
                facecolor=color, edgecolor="none",
                transform=ax.transAxes, zorder=5,
            )
            ax.add_patch(line)

        # =========================================================
        # EXTRACT DATA
        # =========================================================
        _periode = hasil.get("periode", "-")
        _total_rak = hasil.get("total_rak", 0)
        _total_item = hasil.get("total_item", 0)
        _total_nominal = hasil.get("total_nominal", 0)
        _sales = hasil.get("sales_periode", 0)
        _btsb = _sales * 0.0015
        _status = "OVER" if abs(_total_nominal) > _btsb else "AMAN"

        # Insight
        try:
            _insight = _generate_insight_hal1(hasil)
        except Exception:
            _insight = "Insight belum tersedia."

        _list_rak = hasil.get("list_rak", [])
        _rak_names = hasil.get("rak_names", {})

        # ✅ MAX 10 RAK
        _MAX_RAK = 10
        _terpotong = False
        _sisa_rak = 0
        if len(_list_rak) > _MAX_RAK:
            _list_rak = sorted(_list_rak, key=lambda x: x.get("total", 0))[:_MAX_RAK]
            _terpotong = True
            _sisa_rak = len(hasil.get("list_rak", [])) - _MAX_RAK

        # ✅ TREND 5 HARI TERAKHIR — fetch dari DB
        _trend_clean = []
        try:
            from modules.supabase_client import get_supabase
            _sb = get_supabase()
            if _sb is not None:
                _now = datetime.now(ZoneInfo("Asia/Jakarta")).date()
                _start = _now - timedelta(days=4)

                _res_trend = (
                    _sb.table("so_rak_harian")
                    .select("so_date, nominal_adjust")
                    .gte("so_date", _start.isoformat())
                    .lte("so_date", _now.isoformat())
                    .execute()
                )

                if _res_trend.data:
                    _df_trend = pd.DataFrame(_res_trend.data)
                    _df_trend["so_date"] = pd.to_datetime(_df_trend["so_date"], errors="coerce")
                    _df_trend["nominal_adjust"] = pd.to_numeric(_df_trend["nominal_adjust"], errors="coerce").fillna(0)
                    _df_trend = _df_trend.dropna(subset=["so_date"])

                    _grp = _df_trend.groupby("so_date")["nominal_adjust"].sum().reset_index()
                    _grp = _grp.sort_values("so_date")

                    for _, _r in _grp.iterrows():
                        _trend_clean.append({
                            "tanggal": _r["so_date"].strftime("%d/%m"),
                            "nominal": float(_r["nominal_adjust"]),
                        })
                    print(f"[IMG] Trend 5 hari: {len(_trend_clean)} titik")
        except Exception as _e_trend:
            print(f"[IMG] Gagal fetch trend: {_e_trend}")

        # Fallback kalau trend_clean kosong — pake chart_data
        if not _trend_clean:
            for t in hasil.get("chart_data", []):
                _tgl = t.get("tanggal") or t.get("so_date") or "-"
                try:
                    if "-" in str(_tgl) and len(str(_tgl)) == 10:
                        _tgl = f"{_tgl[8:10]}/{_tgl[5:7]}"
                except Exception:
                    pass
                _trend_clean.append({"tanggal": _tgl, "nominal": t.get("nominal", 0)})

        # =========================================================
        # RENDER FIGURE
        # =========================================================
        FIG_W, FIG_H = 8.27, 11.0
        DPI = 130
    
        fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=W["bg"])
    
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_facecolor(W["bg"])
    
        # LAYOUT
        PAD = 0.04
        W_CONTENT = 1 - 2 * PAD
        X_LEFT = PAD
    
        Y_HEADER_TOP = 0.98
        Y_HEADER_BOT = 0.90
        Y_KPI_TOP = 0.885
        Y_KPI_BOT = 0.79
        Y_S1_TOP = 0.760
        Y_S1_BOT = 0.44
        Y_S2_TOP = 0.410
        Y_S2_BOT = 0.10
        Y_FOOTER = 0.045
    
        # HEADER BAND
        _draw_card(ax, X_LEFT, Y_HEADER_BOT, W_CONTENT, Y_HEADER_TOP - Y_HEADER_BOT,
                   W["sage_deep"], radius=0.012)
    
        _text(ax, X_LEFT + 0.02, Y_HEADER_TOP - 0.028,
              "LAPORAN STOCK OPNAME", size=15, color=W["white"], weight="bold")
        _text(ax, X_LEFT + 0.02, Y_HEADER_TOP - 0.048,
              "Toko C383 — Karang Satria", size=8, color=W["sage_light"])
        _text(ax, X_LEFT + 0.02, Y_HEADER_TOP - 0.065,
              _periode, size=7, color=W["sage_light"])
    
        # KPI CARDS
        GAP = 0.015
        KPI_W = (W_CONTENT - 2 * GAP) / 3
        KPI_H = Y_KPI_TOP - Y_KPI_BOT
    
        kpi_data = [
            ("TOTAL RAK", f"{_total_rak}", "rak ter-SO", W["sage_light"]),
            ("TOTAL ITEM", f"{_total_item}", "item tercatat", W["terracotta_light"]),
            ("TOTAL NOMINAL", _rp(_total_nominal), "selisih periode", W["highlight"]),
        ]
    
        for i, (label, value, sub, bg) in enumerate(kpi_data):
            x = X_LEFT + i * (KPI_W + GAP)
            _draw_card(ax, x, Y_KPI_BOT, KPI_W, KPI_H, bg, radius=0.012)
            _text(ax, x + 0.012, Y_KPI_TOP - 0.018,
                  label, size=7, color=W["text_muted"], weight="bold")
            _text(ax, x + 0.012, Y_KPI_TOP - 0.048,
                  value, size=16, color=W["text"], weight="bold")
            _text(ax, x + 0.012, Y_KPI_TOP - 0.072,
                  sub, size=7, color=W["text_sec"])
    
        # SECTION TITLE 01
        _text(ax, X_LEFT, Y_S1_TOP - 0.015, "▌", size=15, color=W["sage_deep"], weight="bold")
        _text(ax, X_LEFT + 0.025, Y_S1_TOP - 0.015, "01", size=10, color=W["terracotta"], weight="bold")
        _text(ax, X_LEFT + 0.052, Y_S1_TOP - 0.015,
              "DISTRIBUSI & RINGKASAN", size=11, color=W["text"], weight="bold")
    
        # SECTION 01
        S1_H = (Y_S1_TOP - 0.02) - Y_S1_BOT
        LEFT_W = (W_CONTENT - 0.02) * 0.45
        RIGHT_W = (W_CONTENT - 0.02) * 0.55
        LEFT_X = X_LEFT
        RIGHT_X = X_LEFT + LEFT_W + 0.02
    
        # DONUT
        _draw_card(ax, LEFT_X, Y_S1_BOT, LEFT_W, S1_H, W["white"], radius=0.012)
        _text(ax, LEFT_X + 0.015, Y_S1_TOP - 0.04,
              "KONTRIBUSI PER RAK", size=8.5, color=W["sage_deep"], weight="bold")
        _divider(ax, LEFT_X + 0.015, Y_S1_TOP - 0.05, LEFT_W - 0.03, W["sage_deep"], 0.0015)
    
        donut_ax = fig.add_axes([
            LEFT_X + 0.03, Y_S1_BOT + 0.015,
            LEFT_W - 0.06, S1_H - 0.075
        ])
        donut_ax.set_facecolor(W["white"])
    
        # Ambil data untuk donut (pakai _list_rak yang udah di-cap 10)
        list_sorted = sorted(_list_rak, key=lambda x: abs(x.get("total", 0)), reverse=True)
        sizes = [abs(r.get("total", 0)) for r in list_sorted if abs(r.get("total", 0)) > 0]
        labels = [f"Rak {r.get('rak_id', '?')}" for r in list_sorted if abs(r.get("total", 0)) > 0]
        colors = ["#5E7A75", "#B5745E", "#7B9B95", "#D9C4B5", "#A8B5AE",
                  "#E8D5C9", "#C9907E", "#9C9488", "#B5C9C3", "#D6CBBF"][:len(sizes)]
    
        if sizes:
            wedges, _, autotexts = donut_ax.pie(
                sizes, labels=None, colors=colors,
                autopct=lambda p: f"{p:.0f}%", pctdistance=0.78, startangle=90,
                wedgeprops=dict(width=0.40, edgecolor=W["white"], linewidth=2.5),
            )
            for at in autotexts:
                at.set_color("white")
                at.set_fontsize(9)
                at.set_fontweight("bold")
    
            for i, (wedge, label) in enumerate(zip(wedges, labels)):
                ang = (wedge.theta2 + wedge.theta1) / 2
                x = np.cos(np.radians(ang))
                y = np.sin(np.radians(ang))
                ha = "right" if x < 0 else "left"
                donut_ax.annotate(
                    label, xy=(x * 0.85, y * 0.85), xytext=(x * 1.18, y * 1.18),
                    ha=ha, va="center", fontsize=7, fontweight="bold", color=W["text"],
                )
    
            total_nom = sum(sizes)
            donut_ax.text(0, 0.05, _rp_no_sign(total_nom), ha="center", va="center",
                          fontsize=10, fontweight="bold", color=W["sage_deep"])
            donut_ax.text(0, -0.12, "TOTAL", ha="center", va="center",
                          fontsize=6.5, fontweight="bold", color=W["text_muted"])
    
        donut_ax.set_aspect("equal")
    
        # RINGKASAN
        _draw_card(ax, RIGHT_X, Y_S1_BOT, RIGHT_W, S1_H, W["white"], radius=0.012)
        _text(ax, RIGHT_X + 0.015, Y_S1_TOP - 0.04,
              "RINGKASAN PERIODE", size=8.5, color=W["sage_deep"], weight="bold")
        _divider(ax, RIGHT_X + 0.015, Y_S1_TOP - 0.05, RIGHT_W - 0.03, W["sage_deep"], 0.0015)
    
        status_color = W["red"] if _status == "OVER" else W["green"]
    
        metrics = [
            ("Tgl", _periode, W["text"]),
            ("Rak", f"{_total_rak} rak", W["text"]),
            ("SO", _rp(_total_nominal), W["red"]),
            ("Sales", _rp_no_sign(_sales), W["text"]),
            ("BTSB", _rp_no_sign(_btsb), W["text"]),
            ("Status", _status, status_color),
        ]
    
        y_metric = Y_S1_TOP - 0.07
        for label, val, color in metrics:
            _text(ax, RIGHT_X + 0.015, y_metric, label, size=7.5, color=W["text_muted"])
            _divider_v(ax, RIGHT_X + 0.070, y_metric - 0.008, 0.016, W["divider"], 0.0008)
            _text(ax, RIGHT_X + 0.075, y_metric, val, size=8, color=color, weight="bold")
            y_metric -= 0.022
            _divider(ax, RIGHT_X + 0.015, y_metric + 0.008, RIGHT_W - 0.03, W["divider"], 0.0008)
    
        # INSIGHT
        y_insight = y_metric - 0.018
        _text(ax, RIGHT_X + 0.015, y_insight,
              "INSIGHT", size=8.5, color=W["sage_deep"], weight="bold")
        _divider(ax, RIGHT_X + 0.015, y_insight - 0.012, RIGHT_W - 0.03, W["sage_deep"], 0.0015)
    
        insight_y = y_insight - 0.03
        insight_h = 0.06
        _draw_card(ax, RIGHT_X + 0.015, insight_y - insight_h, RIGHT_W - 0.03, insight_h,
                   W["terracotta_light"], radius=0.008)
    
        insight_wrapped = textwrap.fill(_insight, width=48)
        _text(ax, RIGHT_X + RIGHT_W / 2, insight_y - insight_h / 2,
              insight_wrapped, size=6.5, color=W["text"], weight="bold",
              ha="center", va="center")
    
        # SECTION TITLE 02
        _text(ax, X_LEFT, Y_S2_TOP - 0.015, "▌", size=15, color=W["sage_deep"], weight="bold")
        _text(ax, X_LEFT + 0.025, Y_S2_TOP - 0.015, "02", size=10, color=W["terracotta"], weight="bold")
        _text(ax, X_LEFT + 0.052, Y_S2_TOP - 0.015,
              "DETAIL & TREND", size=11, color=W["text"], weight="bold")
    
        # SECTION 02
        S2_H = (Y_S2_TOP - 0.02) - Y_S2_BOT
        TBL_W = (W_CONTENT - 0.02) * 0.55
        TRD_W = (W_CONTENT - 0.02) * 0.45
        TBL_X = X_LEFT
        TRD_X = X_LEFT + TBL_W + 0.02
    
        # ✅ TABLE — AUTO-SCALE ROW HEIGHT
        _n_rak = len(_list_rak)
        _header_h_tbl = 0.10
        _total_h_tbl = 0.10
        _row_per_rak = (S2_H - _header_h_tbl - _total_h_tbl) / max(_n_rak, 1)
        # Batas minimal row
        _row_per_rak = max(_row_per_rak, 0.045)
        # Hitung ulang total tinggi tabel
        _tabel_h = _header_h_tbl + _n_rak * _row_per_rak + _total_h_tbl
        _tabel_h = min(_tabel_h, S2_H)
    
        _draw_card(ax, TBL_X, Y_S2_TOP - 0.02 - _tabel_h, TBL_W, _tabel_h, W["white"], radius=0.012)
    
        tbl_ax = fig.add_axes([
            TBL_X + 0.015, Y_S2_TOP - 0.02 - _tabel_h + 0.005,
            TBL_W - 0.03, _tabel_h - 0.01
        ])
        tbl_ax.axis("off")
        tbl_ax.set_xlim(0, 1)
        tbl_ax.set_ylim(0, 1)
    
        col_labels = ["RAK", "NAMA RAK", "PIC", "SELISIH"]
        col_w = [0.09, 0.52, 0.15, 0.24]
    
        # Header
        tbl_ax.add_patch(Rectangle((0, 1 - _header_h_tbl / _tabel_h), 1, _header_h_tbl / _tabel_h,
                                    facecolor=W["sage_deep"], edgecolor="none",
                                    transform=tbl_ax.transAxes))
        x_pos = 0
        for i, lbl in enumerate(col_labels):
            tbl_ax.text(x_pos + 0.01, 1 - (_header_h_tbl / _tabel_h) / 2, lbl,
                        fontsize=7, color=W["white"], fontweight="bold",
                        va="center", transform=tbl_ax.transAxes)
            x_pos += col_w[i]
    
        # Body
        _y_cursor = 1 - _header_h_tbl / _tabel_h
        _row_h_norm = _row_per_rak / _tabel_h
        for idx, r in enumerate(_list_rak):
            bg = W["sage_light"] if idx % 2 == 0 else W["white"]
            tbl_ax.add_patch(Rectangle((0, _y_cursor - _row_h_norm), 1, _row_h_norm,
                                        facecolor=bg, edgecolor="none",
                                        transform=tbl_ax.transAxes))
            tbl_ax.plot([0, 1], [_y_cursor - _row_h_norm, _y_cursor - _row_h_norm],
                        color=W["divider"], linewidth=0.5,
                        transform=tbl_ax.transAxes, clip_on=False)
            _nom = r.get("total", 0)
            color = W["red"] if _nom < 0 else W["green"]
            _rak_id = str(r.get("rak_id", "-"))
            _nama = _clean_text(_rak_names.get(_rak_id, "") or r.get("nama", "-"))[:26]
            _pic = str(r.get("pic", "-"))
            x_pos = 0
            vals = [_rak_id, _nama, _pic, _rp(_nom)]
            for i, v in enumerate(vals):
                tbl_ax.text(x_pos + 0.01, _y_cursor - _row_h_norm / 2, v,
                            fontsize=6.5, color=color if i == 3 else W["text"],
                            fontweight="bold" if i in (0, 2, 3) else "normal",
                            va="center", transform=tbl_ax.transAxes)
                x_pos += col_w[i]
            _y_cursor -= _row_h_norm
    
        # Total row
        tbl_ax.add_patch(Rectangle((0, _y_cursor - _total_h_tbl / _tabel_h), 1, _total_h_tbl / _tabel_h,
                                    facecolor=W["terracotta_light"], edgecolor="none",
                                    transform=tbl_ax.transAxes))
        total_color = W["red"] if _total_nominal < 0 else W["green"]
        tbl_ax.text(0.60, _y_cursor - (_total_h_tbl / _tabel_h) / 2, "TOTAL",
                    fontsize=7.5, color=W["text"], fontweight="bold",
                    va="center", transform=tbl_ax.transAxes)
        tbl_ax.text(0.75, _y_cursor - (_total_h_tbl / _tabel_h) / 2, _rp(_total_nominal),
                    fontsize=7.5, color=total_color, fontweight="bold",
                    va="center", transform=tbl_ax.transAxes)
    
        # Info terpotong
        if _terpotong:
            tbl_ax.text(0.5, 0.02, f"* Menampilkan {_MAX_RAK} dari {_MAX_RAK + _sisa_rak} rak",
                        fontsize=6, color=W["text_muted"], style="italic",
                        ha="center", va="bottom", transform=tbl_ax.transAxes)
    
        # TREND
        _draw_card(ax, TRD_X, Y_S2_TOP - 0.02 - _tabel_h, TRD_W, _tabel_h, W["white"], radius=0.012)
        _text(ax, TRD_X + 0.015, Y_S2_TOP - 0.04,
              "TREND SELISIH HARIAN (5 HARI)", size=8.5, color=W["sage_deep"], weight="bold")
        _divider(ax, TRD_X + 0.015, Y_S2_TOP - 0.05, TRD_W - 0.03, W["sage_deep"], 0.0015)
    
        trend_ax = fig.add_axes([
            TRD_X + 0.02, Y_S2_TOP - 0.02 - _tabel_h + 0.01,
            TRD_W - 0.06, _tabel_h - 0.08
        ])
        trend_ax.set_facecolor(W["white"])
    
        if _trend_clean:
            trend_labels = [t["tanggal"] for t in _trend_clean]
            trend_values = [t["nominal"] for t in _trend_clean]
            x_idx = np.arange(len(trend_labels))
    
            bar_colors = [W["bar_neg"] if v < 0 else W["bar_pos"] for v in trend_values]
            trend_ax.bar(x_idx, trend_values, color=bar_colors, width=0.55,
                         alpha=0.75, edgecolor="white", linewidth=1)
            trend_ax.fill_between(x_idx, trend_values, 0, alpha=0.08, color=W["sage_deep"])
            trend_ax.plot(x_idx, trend_values, color=W["sage_deep"], linewidth=2,
                          marker="o", markersize=5, markerfacecolor="white",
                          markeredgecolor=W["sage_deep"], markeredgewidth=1.5, zorder=5)
    
            for i, v in enumerate(trend_values):
                c = W["red"] if v < 0 else W["green"]
                off = 2500 if v >= 0 else -2500
                trend_ax.text(i, v + off, _rp_short(v),
                              ha="center", va="bottom" if v >= 0 else "top",
                              fontsize=6.5, fontweight="bold", color=c)
    
            trend_ax.axhline(0, color=W["text_muted"], linewidth=0.6, alpha=0.5)
            trend_ax.set_xticks(x_idx)
            trend_ax.set_xticklabels(trend_labels)
            trend_ax.tick_params(axis="x", labelsize=6.5, colors=W["text_sec"])
            trend_ax.tick_params(axis="y", labelsize=6, colors=W["text_muted"])
            trend_ax.spines["top"].set_visible(False)
            trend_ax.spines["right"].set_visible(False)
            trend_ax.spines["left"].set_visible(False)
            trend_ax.spines["bottom"].set_color(W["divider"])
            trend_ax.grid(axis="y", linestyle="-", alpha=0.5, color=W["divider"], linewidth=0.5)
            trend_ax.set_axisbelow(True)
            trend_ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, p: _rp_short_no_sign(int(x)))
            )
    
            min_v, max_v = min(trend_values), max(trend_values)
            pad = abs(max_v - min_v) * 0.40 if max_v != min_v else 8000
            trend_ax.set_ylim(min_v - pad, max_v + pad)
    
        # FOOTER
        _divider(ax, X_LEFT, Y_FOOTER + 0.015, W_CONTENT, W["divider"], 0.0008)
        _text(ax, X_LEFT, Y_FOOTER,
              "Dokumen di-generate otomatis oleh Yui — Dashboard SO Toko C383",
              size=6.5, color=W["text_muted"])
    
        # SAVE
        fig.savefig(filename, dpi=DPI, facecolor=W["bg"], bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)
        return filename
    
    except Exception as e:
        print(f"[EXPORT_IMG ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return None

# =========================================================
# EXPORT EXCEL
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


# =========================================================
# EXPORT TEXT
# =========================================================
def export_rekap_text(hasil, net_sales=0):
    """Export text rekap profesional."""
    try:
        _nom = hasil.get("total_nominal", 0)
        _sales = hasil.get("sales_periode", 0)
        _btsb = _sales * 0.0015
        _status = "OVER" if abs(_nom) > _btsb else "AMAN"

        _lines = [
            "=" * 55,
            "  LAPORAN STOCK OPNAME - TOKO C383",
            "=" * 55,
            f"Periode     : {hasil.get('periode', '-')}",
            f"Total Rak   : {hasil.get('total_rak', 0)} rak",
            f"Total Item  : {hasil.get('total_item', 0)} item",
            f"Nominal SO  : {_format_rp(_nom)}",
            f"Sales       : {_format_rp_no_sign(_sales)}",
            f"BTSB (0,15%): {_format_rp_no_sign(_btsb)}",
            f"Status      : {_status}",
            "",
            "-" * 55,
            "  DETAIL PER RAK",
            "-" * 55,
        ]

        _rak_names = hasil.get("rak_names", {})
        for _r in hasil.get("list_rak", []):
            _rak_id = str(_r.get("rak_id", "-"))
            _rak_name = _rak_names.get(_rak_id, "") or "RAK CUSTOM"
            _lines.append(
                f"  {_rak_id:8s} | {_format_rp(_r.get('total', 0)):>15s} | "
                f"{_r.get('pic', '-'):15s} | {_rak_name[:25]}"
            )

        _lines.extend([
            "",
            "=" * 55,
            "  Keterangan:",
            "  - BTSB = 0,15% dari Sales",
            "  - Status OVER = selisih melebihi BTSB",
            "=" * 55,
        ])
        return "\n".join(_lines)
    except Exception as e:
        print(f"[EXPORT_TEXT ERROR] {e}")
        return "Gagal generate text."