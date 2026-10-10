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
    "peach": (240, 221, 214),
    "salmon": (242, 195, 185),
    "beige": (214, 203, 191),
    "offwhite": (240, 238, 234),
    "dark": (60, 60, 60),
    "white": (255, 255, 255),
    "red": (200, 50, 50),
    "green": (50, 150, 50),
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

        _fig, _ax = plt.subplots(figsize=(5, 4.5))
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
    """Export rekap SO jadi PDF profesional — 2 halaman."""
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
            _pdf.cell(0, 5, "Dokumen ini di-generate otomatis oleh Yui - Dashboard SO Toko C383",
                      align="C", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(*WARNA["dark"])

        # =========================================================
        # HALAMAN 1: ANALISIS GAMBARAN SO
        # =========================================================
        _pdf.add_page()

        # Header band
        _pdf.set_fill_color(*WARNA["sage"])
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

        # === KPI CARDS ===
        _y = _pdf.get_y()
        _card_w = 58
        _gap = 4
        _x_start = (210 - (3 * _card_w + 2 * _gap)) / 2

        _kpi = [
            ("TOTAL RAK", f"{hasil.get('total_rak', 0)} rak", WARNA["sage_light"]),
            ("TOTAL ITEM", f"{hasil.get('total_item', 0)} item", WARNA["peach"]),
            ("TOTAL NOMINAL", _format_rp(hasil.get("total_nominal", 0)), WARNA["salmon"]),
        ]
        for _i, (_lbl, _val, _bg) in enumerate(_kpi):
            _x = _x_start + _i * (_card_w + _gap)
            _pdf.set_fill_color(*_bg)
            _pdf.rect(_x, _y, _card_w, 18, style="F")
            _sf(style="B", size=8)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_xy(_x + 3, _y + 2)
            _pdf.cell(_card_w - 6, 5, _lbl)
            _sf(style="B", size=11)
            _pdf.set_xy(_x + 3, _y + 9)
            _pdf.cell(_card_w - 6, 7, _val)
        _pdf.set_y(_y + 22)

            # =========================================================
            # LAYOUT: RINGKASAN + INSIGHT (ATAS) | DONUT + TREND (BAWAH)
            # =========================================================
            _y_dual = _pdf.get_y()
            
            # --- ATAS KIRI: RINGKASAN PERIODE ---
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.rect(12, _y_dual, 90, 7, style="F")
            _sf(style="B", size=10)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(14, _y_dual + 1.5)
            _pdf.cell(86, 5, "RINGKASAN PERIODE")
            _pdf.set_text_color(*WARNA["dark"])
            
            _sales = hasil.get("sales_periode", 0)
            _btsb = _sales * 0.0015
            _total_nom = hasil.get("total_nominal", 0)
            _status = "OVER" if abs(_total_nom) > _btsb else "AMAN"
            
            _rows = [
                ("Tanggal", hasil.get("periode", "-")),
                ("Total Rak", f"{hasil.get('total_rak', 0)} rak"),
                ("Nominal SO", _format_rp(_total_nom)),
                ("Sales Periode", _format_rp_no_sign(_sales)),
                ("BTSB (0,15%)", _format_rp_no_sign(_btsb)),
            ]
            _sf(style="", size=8)
            _y_row = _y_dual + 9
            for _lbl, _val in _rows:
                _pdf.set_xy(14, _y_row)
                _pdf.cell(30, 4.5, _lbl)
                _sf(style="B", size=8)
                _pdf.cell(0, 4.5, f": {_val}", new_x="LMARGIN", new_y="NEXT")
                _sf(style="", size=8)
                _y_row += 4.5
            
            _pdf.set_xy(14, _y_row)
            _pdf.cell(30, 4.5, "Keterangan")
            _sf(style="B", size=8)
            if _status == "OVER":
                _pdf.set_text_color(*WARNA["red"])
            else:
                _pdf.set_text_color(*WARNA["green"])
            _pdf.cell(0, 4.5, f": {_status}", new_x="LMARGIN", new_y="NEXT")
            _pdf.set_text_color(*WARNA["dark"])
            
            # --- ATAS KANAN: INSIGHT ---
            _x_kanan = 108
            _w_kanan = 90
            
            _pdf.set_fill_color(*WARNA["beige"])
            _pdf.rect(_x_kanan, _y_dual, _w_kanan, 7, style="F")
            _sf(style="B", size=10)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_xy(_x_kanan + 2, _y_dual + 1.5)
            _pdf.cell(_w_kanan - 4, 5, "INSIGHT")
            
            _sf(style="I", size=7)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_xy(_x_kanan + 2, _y_dual + 9)
            _pdf.multi_cell(_w_kanan - 4, 3.8, _generate_insight_hal1(hasil))
            
            # Geser ke baris berikutnya
            _y_row2 = max(_y_row + 4, _y_dual + 48)
            _pdf.set_y(_y_row2)
            _pdf.ln(2)
            
            # --- BAWAH KIRI: DONUT ---
            _y_donut = _pdf.get_y()
            
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.rect(12, _y_donut, 90, 7, style="F")
            _sf(style="B", size=10)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(14, _y_donut + 1.5)
            _pdf.cell(86, 5, "KONTRIBUSI PER RAK")
            _pdf.set_text_color(*WARNA["dark"])
            
            _donut_buf = _generate_donut_per_rak(hasil)
            if _donut_buf:
                _pdf.image(_donut_buf, x=18, y=_y_donut + 9, w=76)
                _donut_buf.close()
            
            # --- BAWAH KANAN: TREND ---
            _pdf.set_fill_color(*WARNA["sage"])
            _pdf.rect(_x_kanan, _y_donut, _w_kanan, 7, style="F")
            _sf(style="B", size=10)
            _pdf.set_text_color(*WARNA["white"])
            _pdf.set_xy(_x_kanan + 2, _y_donut + 1.5)
            _pdf.cell(_w_kanan - 4, 5, "TREND SELISIH (5 HARI)")
            _pdf.set_text_color(*WARNA["dark"])
            
            _line_buf = _generate_trend_line_5hari(hasil)
            if _line_buf:
                _pdf.image(_line_buf, x=_x_kanan + 2, y=_y_donut + 9, w=_w_kanan - 4)
                _line_buf.close()
            
            # Geser Y ke bawah chart
            _pdf.set_y(_y_donut + 78)
            _pdf.ln(4)
            
        # =========================================================
        # DAFTAR RAK (full width)
        # =========================================================
        _y_daftar = _pdf.get_y()
        _pdf.set_fill_color(*WARNA["sage"])
        _pdf.rect(12, _y_daftar, 186, 7, style="F")
        _sf(style="B", size=10)
        _pdf.set_text_color(*WARNA["white"])
        _pdf.set_xy(14, _y_daftar + 1.5)
        _pdf.cell(0, 5, "DAFTAR RAK YANG DI-SO")
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.set_y(_y_daftar + 9)

        _sf(style="B", size=8)
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

        # Total Selisih
        _pdf.set_x(12)
        _pdf.set_fill_color(*WARNA["beige"])
        _sf(style="B", size=9)
        _pdf.cell(sum(_col[:4]), 7, "TOTAL SELISIH", fill=True, align="R")
        if _total_nom < 0:
            _pdf.set_text_color(*WARNA["red"])
        else:
            _pdf.set_text_color(*WARNA["green"])
        _pdf.cell(_col[4], 7, _format_rp(_total_nom), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        _pdf.set_text_color(*WARNA["dark"])
        _pdf.ln(5)

        _watermark()

        # =========================================================
        # HALAMAN 2: LIST ITEM
        # =========================================================
        _pdf.add_page()

        _pdf.set_fill_color(*WARNA["sage"])
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

                _pdf.set_fill_color(*WARNA["salmon"])
                _y_sect = _pdf.get_y()
                _pdf.rect(12, _y_sect, 186, 7, style="F")
                _sf(style="B", size=10)
                _pdf.set_text_color(*WARNA["white"])
                _pdf.set_xy(14, _y_sect + 1.5)
                _pdf.cell(0, 5, f"RAK {_rak_id} - {_rak_name[:40]}")
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.ln(9)

                _sf(style="B", size=8)
                _pdf.set_fill_color(*WARNA["salmon"])
                _pdf.set_text_color(*WARNA["white"])
                _c = [22, 70, 15, 20, 59]
                _pdf.set_x(12)
                _pdf.cell(_c[0], 7, "PLU", fill=True, align="C")
                _pdf.cell(_c[1], 7, "NAMA PRODUK", fill=True, align="C")
                _pdf.cell(_c[2], 7, "QTY", fill=True, align="C")
                _pdf.cell(_c[3], 7, "PIC", fill=True, align="C")
                _pdf.cell(_c[4], 7, "NOMINAL", fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

                _sf(style="", size=8)
                _pdf.set_text_color(*WARNA["dark"])
                for _idx, _it in enumerate(_items_all):
                    _bg = WARNA["offwhite"] if _idx % 2 == 0 else WARNA["white"]
                    _pdf.set_fill_color(*_bg)
                    _pdf.set_x(12)

                    _plu = str(_it.get("plu", "-"))[:12]
                    _nama = _clean_text(_it.get("nama_produk", "-"))[:38]
                    _qty_var = _it.get("qty_var", 0)
                    _pic = str(_it.get("pic", "-"))[:12]
                    _nom_it = float(_it.get("nominal_adjust", 0) or 0)

                    _pdf.cell(_c[0], 6, _plu, fill=True, align="C")
                    _pdf.cell(_c[1], 6, _nama, fill=True, align="L")
                    _pdf.cell(_c[2], 6, str(_qty_var), fill=True, align="C")
                    _pdf.cell(_c[3], 6, _pic, fill=True, align="C")

                    if _nom_it < 0:
                        _pdf.set_text_color(*WARNA["red"])
                    else:
                        _pdf.set_text_color(*WARNA["green"])
                    _pdf.cell(_c[4], 6, _format_rp(_nom_it), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                    _pdf.set_text_color(*WARNA["dark"])

                _pdf.set_x(12)
                _pdf.set_fill_color(*WARNA["beige"])
                _sf(style="B", size=9)
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.cell(sum(_c[:4]), 7, f"TOTAL RAK {_rak_id}", fill=True, align="R")
                if _total_rak < 0:
                    _pdf.set_text_color(*WARNA["red"])
                else:
                    _pdf.set_text_color(*WARNA["green"])
                _pdf.cell(_c[4], 7, _format_rp(_total_rak), fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                _pdf.set_text_color(*WARNA["dark"])
                _pdf.ln(4)

            # Insight halaman 2
            _y_ins = _pdf.get_y()
            _pdf.set_fill_color(*WARNA["beige"])
            _pdf.rect(12, _y_ins, 186, 7, style="F")
            _sf(style="B", size=10)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.set_xy(14, _y_ins + 1.5)
            _pdf.cell(0, 5, "INSIGHT")

            _sf(style="I", size=8)
            _pdf.set_xy(14, _y_ins + 9)
            _pdf.multi_cell(182, 4.5, _generate_insight_hal2(hasil))
        else:
            _sf(style="I", size=10)
            _pdf.set_text_color(*WARNA["dark"])
            _pdf.cell(0, 10, "Tidak ada item pada periode ini.", align="C")

        _watermark()

        _output = _pdf.output()
        return bytes(_output) if isinstance(_output, bytearray) else _output
    except Exception as e:
        import traceback
        _err = f"ERROR: {str(e)}\n\nTRACEBACK:\n{traceback.format_exc()}"
        print(_err)
        return _err.encode("utf-8")
        
        

# =========================================================
# EXPORT GAMBAR (matplotlib)
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

        _fig.suptitle(
            "LAPORAN STOCK OPNAME - TOKO C383",
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
        _insight = _generate_insight_hal1(hasil)
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