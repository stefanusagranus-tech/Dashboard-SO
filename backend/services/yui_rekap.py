"""
Yui Rekap — Query & rekap data SO untuk Yui.
Semua fungsi di sini cuma baca data (read-only).
"""

import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import html

from services.supabase_client import get_supabase


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _get_supabase_safe():
    """Ambil Supabase client, return None kalau gagal."""
    try:
        return get_supabase()
    except Exception as e:
        print(f"[YUI_REKAP] Gagal ambil Supabase: {e}")
        return None


# =========================================================
# PERIODE
# =========================================================
def get_periode_range(mode="hari_ini", tgl_start=None, tgl_end=None):
    """Hitung rentang tanggal berdasarkan mode."""
    _today = _now_jkt().date()

    if mode == "hari_ini":
        return _today, _today

    if mode == "minggu_ini":
        _start = _today - timedelta(days=_today.weekday())
        _end = _start + timedelta(days=6)
        return _start, _end

    if mode == "bulan_ini":
        _start = _today.replace(day=1)
        if _today.month == 12:
            _end = _today.replace(year=_today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            _end = _today.replace(month=_today.month + 1, day=1) - timedelta(days=1)
        return _start, _end

    if mode == "custom" and tgl_start and tgl_end:
        return tgl_start, tgl_end

    return _today, _today


# =========================================================
# REKAP SO — Fungsi Utama
# =========================================================
def rekap_so(mode="hari_ini", tgl_start=None, tgl_end=None, pic_filter=None):
    """Rekap SO: summary + detail per rak + items per rak."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        _start, _end = get_periode_range(mode, tgl_start, tgl_end)

        # === QUERY so_rak_harian ===
        _q = (
            _sb.table("so_rak_harian")
            .select("*")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
        )
        if pic_filter:
            _q = _q.eq("pic", pic_filter.upper())

        _res = _q.order("so_date").execute()
        _rows = _res.data if _res.data else []

        if not _rows:
            return {
                "success": True,
                "mode": mode,
                "periode": f"{_start} s/d {_end}",
                "tgl_start": _start.isoformat(),
                "tgl_end": _end.isoformat(),
                "total_rak": 0,
                "total_item": 0,
                "total_nominal": 0,
                "list_rak": [],
                "items_by_rak": {},
                "chart_data": [],
                "sales_periode": 0,
                "rak_names": {},
            }

        _df = pd.DataFrame(_rows)
        _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)

        _total_rak = int(_df["rak_id"].nunique())
        _total_nominal = float(_df["nominal_adjust"].sum())

        # === QUERY so_hasil (untuk total item + items by rak) ===
        _res2 = (
            _sb.table("so_hasil")
            .select("*")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
            .execute()
        )
        _hasil_rows = _res2.data if _res2.data else []
        _total_item = len(_hasil_rows)

        # Group items by rak
        _items_by_rak = {}
        for _r in _hasil_rows:
            _rak = _r.get("rak_id", "UNKNOWN")
            _items_by_rak.setdefault(_rak, []).append(_r)

        # === LIST RAK (summary) ===
        _list_rak = []
        for _rak, _grp in _df.groupby("rak_id"):
            _list_rak.append({
                "rak_id": _rak,
                "total": float(_grp["nominal_adjust"].sum()),
                "pic": _grp["pic"].iloc[0] if "pic" in _grp.columns else "-",
                "tanggal": _grp["so_date"].iloc[0] if "so_date" in _grp.columns else "-",
            })
        _list_rak.sort(key=lambda x: x["total"])

        # === CHART DATA (per hari) ===
        _chart_data = []
        for _tgl, _grp in _df.groupby("so_date"):
            _chart_data.append({
                "tanggal": _tgl,
                "nominal": float(_grp["nominal_adjust"].sum()),
                "jumlah_rak": int(_grp["rak_id"].nunique()),
            })
        _chart_data.sort(key=lambda x: x["tanggal"])

        # === SALES PERIODE ===
        _sales_periode = _get_sales_periode(_start, _end)

        # === RAK NAMES ===
        _rak_names = _get_rak_names()

        return {
            "success": True,
            "mode": mode,
            "periode": f"{_start} s/d {_end}",
            "tgl_start": _start.isoformat(),
            "tgl_end": _end.isoformat(),
            "total_rak": _total_rak,
            "total_item": _total_item,
            "total_nominal": _total_nominal,
            "list_rak": _list_rak,
            "items_by_rak": _items_by_rak,
            "chart_data": _chart_data,
            "sales_periode": _sales_periode,
            "rak_names": _rak_names,
        }

    except Exception as e:
        print(f"[REKAP_SO ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200]}


# =========================================================
# SALES PERIODE
# =========================================================
def _get_sales_periode(tgl_start, tgl_end):
    """Ambil total SPD (sales) pada rentang tanggal."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return 0

        _res = (
            _sb.table("spd_harian")
            .select("spd")
            .gte("tanggal", tgl_start.isoformat())
            .lte("tanggal", tgl_end.isoformat())
            .execute()
        )

        if _res.data:
            _total = sum(float(r.get("spd", 0) or 0) for r in _res.data)
            print(f"[SALES_PERIODE] {_total} ({len(_res.data)} hari)")
            return _total
        return 0
    except Exception as e:
        print(f"[SALES_PERIODE ERROR] {e}")
        return 0


# =========================================================
# RAK NAMES
# =========================================================
def _get_rak_names():
    """Ambil mapping rak_id -> rak_name dari rak_master."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {}

        _res = _sb.table("rak_master").select("rak_id, rak_name").execute()
        if _res.data:
            return {r["rak_id"]: r.get("rak_name", "") for r in _res.data}
        return {}
    except Exception as e:
        print(f"[RAK_NAMES ERROR] {e}")
        return {}


# =========================================================
# BULANAN (legacy, dipakai Dashboard)
# =========================================================
def _get_net_sales_bulan(bulan=None, tahun=None):
    """Hitung net sales bulanan dari spd_harian."""
    try:
        _now = _now_jkt()
        _bulan = bulan or _now.month
        _tahun = tahun or _now.year

        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - timedelta(days=1)

        return _get_sales_periode(_start, _end)
    except Exception as e:
        print(f"[NET_SALES ERROR] {e}")
        return 0


def _get_total_selisih_bulan(bulan=None, tahun=None):
    """Hitung total selisih (abs) 1 bulan dari so_rak_harian."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return 0

        _now = _now_jkt()
        _bulan = bulan or _now.month
        _tahun = tahun or _now.year

        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - timedelta(days=1)

        _res = (
            _sb.table("so_rak_harian")
            .select("nominal_adjust")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
            .execute()
        )

        if _res.data:
            _sum_raw = sum(float(r.get("nominal_adjust", 0) or 0) for r in _res.data)
            return abs(_sum_raw)
        return 0
    except Exception as e:
        print(f"[SELISIH_BULAN ERROR] {e}")
        return 0


def _get_total_rak_bulan(bulan=None, tahun=None):
    """Hitung jumlah rak unik yang di-SO bulan ini."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return 0

        _now = _now_jkt()
        _bulan = bulan or _now.month
        _tahun = tahun or _now.year

        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - timedelta(days=1)

        _res = (
            _sb.table("so_rak_harian")
            .select("rak_id")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
            .execute()
        )

        if _res.data:
            return len(set(r.get("rak_id", "") for r in _res.data))
        return 0
    except Exception as e:
        print(f"[RAK_BULAN ERROR] {e}")
        return 0


# =========================================================
# CEK RAK BELUM SO
# =========================================================
def cek_rak_belum_so(tanggal=None):
    """List rak yang belum di-SO pada tanggal tertentu."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return []

        _tgl = tanggal or _now_jkt().date()
        _tgl_str = _tgl.isoformat()[:10] if isinstance(_tgl, (date, datetime)) else str(_tgl)[:10]

        _res_all = _sb.table("rak_master").select("rak_id, rak_name").execute()
        _all_rak = {r["rak_id"]: r.get("rak_name", "") for r in (_res_all.data or [])}

        _res_so = (
            _sb.table("so_rak_harian")
            .select("rak_id")
            .eq("so_date", _tgl_str)
            .execute()
        )
        _sudah_so = set(r["rak_id"] for r in (_res_so.data or []))

        _belum = [
            {"rak_id": _r, "rak_name": _all_rak[_r]}
            for _r in _all_rak if _r not in _sudah_so
        ]
        _belum.sort(key=lambda x: x["rak_id"])
        return _belum
    except Exception as e:
        print(f"[CEK_RAK_BELUM ERROR] {e}")
        return []
    
import html  # ← TAMBAH di atas file


# =========================================================
# HELPER — Clean HTML entity
# =========================================================
def _clean_text(s):
    """Unescape HTML entity (&#39; → ', &amp; → &)."""
    if not s:
        return s
    try:
        return html.unescape(str(s))
    except Exception:
        return str(s)


def _clean_item(it):
    """Clean field nama_produk di item."""
    if isinstance(it, dict):
        if "nama_produk" in it:
            it["nama_produk"] = _clean_text(it["nama_produk"])
        if "pic" in it and it["pic"]:
            it["pic"] = _clean_text(it["pic"])
    return it


# =========================================================
# TOP ITEMS — FIX Bug #2 (HTML entity) + support show_all
# =========================================================
def get_top_items(
    tgl_start=None, tgl_end=None, mode="bulan_ini",
    limit=10, order="desc",
    only_minus=True,
    show_all=False,          # ✅ BARU: True = tampil semua (minus + plus)
    pic_filter=None, rak_filter=None,
):
    """
    Ambil top N item SO berdasarkan nominal_adjust.

    Args:
        only_minus:
            - True  → cuma item minus (qty_var < 0)
            - False → cuma item plus (qty_var > 0)
        show_all:
            - True  → SEMUA item (minus + plus), override only_minus
    """
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek", "items": []}

        if mode == "custom" and tgl_start and tgl_end:
            _start, _end = tgl_start, tgl_end
        else:
            _start, _end = get_periode_range(mode)

        _start_str = _start.isoformat()[:10] if isinstance(_start, (date, datetime)) else str(_start)[:10]
        _end_str = _end.isoformat()[:10] if isinstance(_end, (date, datetime)) else str(_end)[:10]

        _q = (
            _sb.table("so_hasil")
            .select("plu, nama_produk, rak_id, qty_var, nominal_adjust, pic, so_date")
            .gte("so_date", _start_str)
            .lte("so_date", _end_str)
        )

        # === FILTER ===
        if not show_all:
            if only_minus:
                _q = _q.lt("qty_var", 0)
            else:
                _q = _q.gt("qty_var", 0)
        # kalau show_all=True → no filter qty_var

        if pic_filter:
            _q = _q.eq("pic", pic_filter.upper())
        if rak_filter:
            _q = _q.eq("rak_id", rak_filter.upper())

        _q = _q.limit(2000)

        _res = _q.execute()
        _items = _res.data if _res.data else []

        # Konversi tipe + clean HTML
        for _it in _items:
            _it["qty_var"] = int(_it.get("qty_var") or 0)
            _it["nominal_adjust"] = float(_it.get("nominal_adjust") or 0)
            _clean_item(_it)   # ✅ FIX Bug #2

        # === SORT ===
        if show_all:
            # Sort by abs nominal (terbesar dulu)
            _items.sort(key=lambda x: abs(x["nominal_adjust"]), reverse=True)
        elif only_minus:
            _items.sort(key=lambda x: x["nominal_adjust"])   # minus terbesar dulu
        else:
            _items.sort(key=lambda x: x["nominal_adjust"], reverse=True)

        _items = _items[:limit]

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
            "tgl_start": _start_str,
            "tgl_end": _end_str,
            "items": _items,
            "total_item": len(_items),
            "total_nominal": sum(_it["nominal_adjust"] for _it in _items),
        }
    except Exception as e:
        print(f"[GET_TOP_ITEMS ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200], "items": []}


# =========================================================
# GET ITEMS BY RAK — FIX Bug #3
# =========================================================
def get_items_by_rak(rak_id, tgl_start=None, tgl_end=None,
                     mode="bulan_ini", show_all=True):
    """
    Ambil semua item SO di rak tertentu.
    Default show_all=True (minus + plus).
    """
    return get_top_items(
        tgl_start=tgl_start,
        tgl_end=tgl_end,
        mode=mode,
        limit=1000,
        order="desc",
        only_minus=False,
        show_all=show_all,          # ✅ FIX Bug #3
        rak_filter=rak_id,
    )

# =========================================================
# GET RAK STATUS — List semua rak: sudah/belum SO
# =========================================================
def get_rak_status(mode="bulan_ini", tgl_start=None, tgl_end=None):
    """
    Ambil status semua rak: sudah SO atau belum.
    
    Returns:
        {
            "success": bool,
            "total_rak": int,
            "sudah_so": int,
            "belum_so": int,
            "persen": float,
            "list_rak": [
                {
                    "rak_id": "Q51",
                    "rak_name": "...",
                    "status": "SUDAH" | "BELUM",
                    "tgl_so": "2026-10-14",
                    "nominal": -28000,
                    "pic": "PANDU"
                },
                ...
            ]
        }
    """
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek", "list_rak": []}

        # === 1. Ambil semua rak dari master ===
        _res_master = _sb.table("rak_master").select("rak_id, rak_name").execute()
        _all_rak = _res_master.data if _res_master.data else []

        if not _all_rak:
            return {"success": True, "total_rak": 0, "sudah_so": 0, "belum_so": 0, "persen": 0, "list_rak": []}

        # === 2. Tentukan periode ===
        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        # === 3. Ambil data SO ===
        _res_so = (
            _sb.table("so_rak_harian")
            .select("rak_id, so_date, nominal_adjust, pic")
            .gte("so_date", _start_str)
            .lte("so_date", _end_str)
            .execute()
        )
        _so_rows = _res_so.data if _res_so.data else []

        # === 4. Map rak → data SO (ambil tanggal terakhir kalau ada multiple) ===
        _so_map = {}
        for _row in _so_rows:
            _rak = _row.get("rak_id", "")
            if not _rak:
                continue
            # Ambil data dengan tanggal terbaru
            if _rak not in _so_map or _row.get("so_date", "") > _so_map[_rak].get("so_date", ""):
                _so_map[_rak] = _row

        # === 5. Build list ===
        _list_rak = []
        _sudah_so = 0
        _belum_so = 0

        for _rak in _all_rak:
            _rak_id = _rak.get("rak_id", "")
            _rak_name = _rak.get("rak_name", "")
            _so_data = _so_map.get(_rak_id)

            if _so_data:
                _sudah_so += 1
                _list_rak.append({
                    "rak_id": _rak_id,
                    "rak_name": _rak_name,
                    "status": "SUDAH",
                    "tgl_so": _so_data.get("so_date", ""),
                    "nominal": float(_so_data.get("nominal_adjust") or 0),
                    "pic": _so_data.get("pic") or "-",
                })
            else:
                _belum_so += 1
                _list_rak.append({
                    "rak_id": _rak_id,
                    "rak_name": _rak_name,
                    "status": "BELUM",
                    "tgl_so": None,
                    "nominal": 0,
                    "pic": None,
                })

        # === 6. Sort: yang BELUM dulu, terus yang SUDAH (minimal nominal) ===
        _list_rak.sort(key=lambda x: (
            0 if x["status"] == "BELUM" else 1,  # BELUM dulu
            x["rak_id"],                          # abjad
        ))

        _total_rak = len(_all_rak)
        _persen = (_sudah_so / _total_rak * 100) if _total_rak > 0 else 0

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
            "total_rak": _total_rak,
            "sudah_so": _sudah_so,
            "belum_so": _belum_so,
            "persen": round(_persen, 2),
            "list_rak": _list_rak,
        }

    except Exception as e:
        print(f"[GET_RAK_STATUS ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200], "list_rak": []}
        
# =========================================================
# GET SPD LIST — List Sales Per Day + delta
# =========================================================
def get_spd_list(mode="bulan_ini", tgl_start=None, tgl_end=None):
    """
    Ambil list SPD (Sales Per Day) + delta vs hari sebelumnya.
    
    Returns:
        {
            "success": bool,
            "periode": "...",
            "total_spd": float,
            "total_hari": int,
            "avg_spd": float,
            "list_spd": [
                {
                    "tanggal": "2026-10-01",
                    "spd": 16425771.0,
                    "delta_nominal": 0,
                    "delta_persen": 0,
                    "trend": "flat"  # "up" | "down" | "flat"
                },
                ...
            ]
        }
    """
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek", "list_spd": []}

        # Tentukan periode
        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        # Query spd_harian
        _res = (
            _sb.table("spd_harian")
            .select("tanggal, spd, keterangan, pic")
            .gte("tanggal", _start_str)
            .lte("tanggal", _end_str)
            .order("tanggal", desc=False)
            .execute()
        )
        _rows = _res.data if _res.data else []

        # Build list + delta
        _list_spd = []
        _prev_spd = None

        for _row in _rows:
            _spd = float(_row.get("spd") or 0)

            _delta_nominal = 0
            _delta_persen = 0
            _trend = "flat"

            if _prev_spd is not None and _prev_spd > 0:
                _delta_nominal = _spd - _prev_spd
                _delta_persen = (_delta_nominal / _prev_spd) * 100

                if _delta_nominal > 0:
                    _trend = "up"
                elif _delta_nominal < 0:
                    _trend = "down"
                else:
                    _trend = "flat"

            _list_spd.append({
                "tanggal": _row.get("tanggal", ""),
                "spd": _spd,
                "spd_formatted": f"Rp {_spd:,.0f}".replace(",", "."),
                "delta_nominal": _delta_nominal,
                "delta_persen": round(_delta_persen, 2),
                "trend": _trend,
                "keterangan": _row.get("keterangan") or "",
                "pic": _row.get("pic") or "-",
            })

            _prev_spd = _spd

        # Total & avg
        _total_spd = sum(it["spd"] for it in _list_spd)
        _total_hari = len(_list_spd)
        _avg_spd = _total_spd / _total_hari if _total_hari > 0 else 0

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
            "tgl_start": _start_str,
            "tgl_end": _end_str,
            "total_spd": _total_spd,
            "total_hari": _total_hari,
            "avg_spd": _avg_spd,
            "list_spd": _list_spd,
        }

    except Exception as e:
        print(f"[GET_SPD_LIST ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200], "list_spd": []}
        