"""
Yui Rekap — Query & rekap data SO untuk Yui.
Semua fungsi di sini cuma baca data (read-only).
"""

import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from modules.supabase_client import get_supabase


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


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


def rekap_so(mode="hari_ini", tgl_start=None, tgl_end=None, pic_filter=None):
    """Rekap SO: summary + detail per rak + items per rak."""
    try:
        _sb = get_supabase()
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
        _q2 = (
            _sb.table("so_hasil")
            .select("*")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
        )
        _res2 = _q2.execute()
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


def _get_sales_periode(tgl_start, tgl_end):
    """Ambil total SPD (sales) pada rentang tanggal."""
    try:
        _sb = get_supabase()
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


def _get_rak_names():
    """Ambil mapping rak_id -> rak_name dari rak_master."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return {}

        _res = _sb.table("rak_master").select("rak_id, rak_name").execute()
        if _res.data:
            return {r["rak_id"]: r.get("rak_name", "") for r in _res.data}
        return {}
    except Exception as e:
        print(f"[RAK_NAMES ERROR] {e}")
        return {}


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
        _sb = get_supabase()
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
        _sb = get_supabase()
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


def get_top_items(bulan=None, tahun=None, limit=5):
    """Ambil top N item minus & plus dari so_hasil."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"top_minus": [], "top_plus": []}

        _now = _now_jkt()
        _bulan = bulan or _now.month
        _tahun = tahun or _now.year

        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - timedelta(days=1)

        _res = (
            _sb.table("so_hasil")
            .select("rak_id, plu, nama_produk, qty_var, nominal_adjust, pic, so_date")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
            .execute()
        )

        if not _res.data:
            return {"top_minus": [], "top_plus": []}

        _df = pd.DataFrame(_res.data)
        _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)

        _top_minus = _df.nsmallest(limit, "nominal_adjust").to_dict("records")
        _top_plus = _df.nlargest(limit, "nominal_adjust").to_dict("records")

        return {"top_minus": _top_minus, "top_plus": _top_plus}
    except Exception as e:
        print(f"[TOP_ITEMS ERROR] {e}")
        return {"top_minus": [], "top_plus": []}


def cek_rak_belum_so(tanggal=None):
    """List rak yang belum di-SO pada tanggal tertentu."""
    try:
        _sb = get_supabase()
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
        