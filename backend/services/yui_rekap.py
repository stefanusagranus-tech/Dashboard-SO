"""
Yui Rekap — Query & rekap data SO untuk Yui.
Semua fungsi di sini cuma baca data (read-only).
"""

import os
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _get_supabase_safe():
    """Ambil Supabase client, return None kalau gagal."""
    try:
        from services.supabase_client import get_supabase
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

    if mode == "bulan_lalu":
        _first_this = _today.replace(day=1)
        _last_prev = _first_this - timedelta(days=1)
        _start = _last_prev.replace(day=1)
        return _start, _last_prev

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

        # === QUERY so_hasil ===
        _res2 = (
            _sb.table("so_hasil")
            .select("*")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
            .execute()
        )
        _hasil_rows = _res2.data if _res2.data else []
        _total_item = len(_hasil_rows)

        _items_by_rak = {}
        for _r in _hasil_rows:
            _rak = _r.get("rak_id", "UNKNOWN")
            _items_by_rak.setdefault(_rak, []).append(_r)

        _list_rak = []
        for _rak, _grp in _df.groupby("rak_id"):
            _list_rak.append({
                "rak_id": _rak,
                "total": float(_grp["nominal_adjust"].sum()),
                "pic": _grp["pic"].iloc[0] if "pic" in _grp.columns else "-",
                "tanggal": _grp["so_date"].iloc[0] if "so_date" in _grp.columns else "-",
            })
        _list_rak.sort(key=lambda x: x["total"])

        _chart_data = []
        for _tgl, _grp in _df.groupby("so_date"):
            _chart_data.append({
                "tanggal": _tgl,
                "nominal": float(_grp["nominal_adjust"].sum()),
                "jumlah_rak": int(_grp["rak_id"].nunique()),
            })
        _chart_data.sort(key=lambda x: x["tanggal"])

        _sales_periode = _get_sales_periode(_start, _end)
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
            return sum(float(r.get("spd", 0) or 0) for r in _res.data)
        return 0
    except Exception as e:
        print(f"[SALES_PERIODE ERROR] {e}")
        return 0


# =========================================================
# RAK NAMES
# =========================================================
def _get_rak_names():
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
# LEGACY — BULANAN
# =========================================================
def _get_net_sales_bulan(bulan=None, tahun=None):
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


# =========================================================
# TOP ITEMS
# =========================================================
def get_top_items(
    tgl_start=None, tgl_end=None, mode="bulan_ini",
    limit=10, order="desc", only_minus=True,
    pic_filter=None, rak_filter=None,
):
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

        if only_minus:
            _q = _q.lt("qty_var", 0)
        else:
            _q = _q.gt("qty_var", 0)

        if pic_filter:
            _q = _q.eq("pic", pic_filter.upper())
        if rak_filter:
            _q = _q.eq("rak_id", rak_filter.upper())

        _q = _q.limit(2000)
        _res = _q.execute()
        _items = _res.data if _res.data else []

        for _it in _items:
            _it["qty_var"] = int(_it.get("qty_var") or 0)
            _it["nominal_adjust"] = float(_it.get("nominal_adjust") or 0)

        if only_minus:
            _items.sort(key=lambda x: x["nominal_adjust"])
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
# GET ITEMS BY RAK
# =========================================================
def get_items_by_rak(rak_id, tgl_start=None, tgl_end=None, mode="bulan_ini", show_all=True):
    return get_top_items(
        tgl_start=tgl_start,
        tgl_end=tgl_end,
        mode=mode,
        limit=1000,
        order="desc",
        only_minus=False,
        rak_filter=rak_id,
    )


# =========================================================
# GET RAK STATUS — Fitur #1
# =========================================================
def get_rak_status(mode="bulan_ini", tgl_start=None, tgl_end=None):
    """List semua rak: sudah/belum SO."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        # Master rak
        _res_master = _sb.table("rak_master").select("rak_id, rak_name").execute()
        _master = _res_master.data if _res_master.data else []
        _master_map = {r["rak_id"]: r.get("rak_name", "") for r in _master}

        # SO per rak dalam periode
        _res_so = (
            _sb.table("so_rak_harian")
            .select("rak_id, so_date, nominal_adjust, pic")
            .gte("so_date", _start_str)
            .lte("so_date", _end_str)
            .execute()
        )
        _so_rows = _res_so.data if _res_so.data else []

        _so_map = {}
        for r in _so_rows:
            _rid = r.get("rak_id")
            if _rid and _rid not in _so_map:
                _so_map[_rid] = {
                    "tgl_so": r.get("so_date"),
                    "nominal": float(r.get("nominal_adjust") or 0),
                    "pic": r.get("pic") or "-",
                }
            elif _rid:
                _so_map[_rid]["nominal"] += float(r.get("nominal_adjust") or 0)

        _list_rak = []
        _sudah = 0
        _belum = 0

        for r in _master:
            _rid = r["rak_id"]
            if _rid in _so_map:
                _info = _so_map[_rid]
                _list_rak.append({
                    "rak_id": _rid,
                    "rak_name": r.get("rak_name", ""),
                    "status": "SUDAH",
                    "tgl_so": _info["tgl_so"],
                    "nominal": _info["nominal"],
                    "pic": _info["pic"],
                })
                _sudah += 1
            else:
                _list_rak.append({
                    "rak_id": _rid,
                    "rak_name": r.get("rak_name", ""),
                    "status": "BELUM",
                    "tgl_so": None,
                    "nominal": 0,
                    "pic": None,
                })
                _belum += 1

        _list_rak.sort(key=lambda x: (x["status"] != "SUDAH", x["rak_id"]))

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
            "total_rak": len(_master),
            "sudah_so": _sudah,
            "belum_so": _belum,
            "list_rak": _list_rak,
        }
    except Exception as e:
        print(f"[GET_RAK_STATUS ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200]}


# =========================================================
# GET SPD LIST — Fitur #2
# =========================================================
def get_spd_list(mode="bulan_ini", tgl_start=None, tgl_end=None):
    """List SPD per hari + delta."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        _res = (
            _sb.table("spd_harian")
            .select("tanggal, spd, keterangan, pic")
            .gte("tanggal", _start_str)
            .lte("tanggal", _end_str)
            .order("tanggal")
            .execute()
        )
        _rows = _res.data if _res.data else []

        _list_spd = []
        _prev_spd = None

        for r in _rows:
            _spd = float(r.get("spd") or 0)
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

            _list_spd.append({
                "tanggal": r.get("tanggal"),
                "spd": _spd,
                "delta_nominal": _delta_nominal,
                "delta_persen": _delta_persen,
                "trend": _trend,
                "keterangan": r.get("keterangan") or "",
                "pic": r.get("pic") or "-",
            })
            _prev_spd = _spd

        _total_spd = sum(x["spd"] for x in _list_spd)
        _total_hari = len(_list_spd)
        _avg_spd = _total_spd / _total_hari if _total_hari > 0 else 0

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
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


# =========================================================
# GET TOP RAK — Fitur #3
# =========================================================
def get_top_rak(mode="bulan_ini", tgl_start=None, tgl_end=None, limit=500):
    """Ranking rak by nominal_adjust."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        _res = (
            _sb.table("so_rak_harian")
            .select("rak_id, so_date, nominal_adjust, pic")
            .gte("so_date", _start_str)
            .lte("so_date", _end_str)
            .execute()
        )
        _rows = _res.data if _res.data else []

        _rak_map = {}
        for r in _rows:
            _rid = r.get("rak_id")
            if not _rid:
                continue
            _nom = float(r.get("nominal_adjust") or 0)
            if _rid not in _rak_map:
                _rak_map[_rid] = {
                    "rak_id": _rid,
                    "nominal_adjust": _nom,
                    "tgl_so": r.get("so_date"),
                    "pic": r.get("pic") or "-",
                    "total_item": 0,
                }
            else:
                _rak_map[_rid]["nominal_adjust"] += _nom
                if r.get("so_date") and (not _rak_map[_rid]["tgl_so"] or r["so_date"] > _rak_map[_rid]["tgl_so"]):
                    _rak_map[_rid]["tgl_so"] = r["so_date"]

        _list_rak = list(_rak_map.values())
        _list_rak.sort(key=lambda x: x["nominal_adjust"])

        if limit:
            _list_rak = _list_rak[:limit]

        _total_nominal = sum(x["nominal_adjust"] for x in _list_rak)

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
            "total_rak": len(_list_rak),
            "total_nominal": _total_nominal,
            "list_rak": _list_rak,
        }
    except Exception as e:
        print(f"[GET_TOP_RAK ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200], "list_rak": []}


# =========================================================
# GET ITEMS BY RAK EXTENDED — Fitur #3 Detail
# =========================================================
def get_items_by_rak_extended(rak_id, mode="bulan_ini", tgl_start=None, tgl_end=None):
    """Detail item di rak tertentu (minus + plus)."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        _res = (
            _sb.table("so_hasil")
            .select("plu, nama_produk, rak_id, qty_var, nominal_adjust, pic, so_date")
            .eq("rak_id", rak_id.upper())
            .gte("so_date", _start_str)
            .lte("so_date", _end_str)
            .execute()
        )
        _items = _res.data if _res.data else []

        for _it in _items:
            _it["qty_var"] = int(_it.get("qty_var") or 0)
            _it["nominal_adjust"] = float(_it.get("nominal_adjust") or 0)

        _total_minus = sum(x["nominal_adjust"] for x in _items if x["nominal_adjust"] < 0)
        _total_plus = sum(x["nominal_adjust"] for x in _items if x["nominal_adjust"] > 0)
        _total_net = _total_minus + _total_plus

        _pic = _items[0]["pic"] if _items else "-"
        _tgl_so = _items[0]["so_date"] if _items else None

        return {
            "success": True,
            "rak_id": rak_id.upper(),
            "periode": f"{_start_str} s/d {_end_str}",
            "tgl_so": _tgl_so,
            "pic": _pic,
            "total_minus": _total_minus,
            "total_plus": _total_plus,
            "total_nominal": _total_net,
            "total_item": len(_items),
            "items": _items,
        }
    except Exception as e:
        print(f"[GET_ITEMS_BY_RAK_EXT ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200], "items": []}


# =========================================================
# GET TOP ITEMS EXTENDED — Fitur #3 Search + Sort
# =========================================================
def get_top_items_extended(
    mode="bulan_ini", tgl_start=None, tgl_end=None,
    limit=None, search="", order_by="nominal_desc",
):
    """Top items extended — search + sort."""
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek", "items": []}

        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        _q = (
            _sb.table("so_hasil")
            .select("plu, nama_produk, rak_id, qty_var, nominal_adjust, pic, so_date")
            .gte("so_date", _start_str)
            .lte("so_date", _end_str)
            .lt("qty_var", 0)  # default minus
        )

        _res = _q.limit(5000).execute()
        _items = _res.data if _res.data else []

        for _it in _items:
            _it["qty_var"] = int(_it.get("qty_var") or 0)
            _it["nominal_adjust"] = float(_it.get("nominal_adjust") or 0)

        # Search
        if search:
            _s = search.lower()
            _items = [
                it for it in _items
                if _s in (it.get("plu") or "").lower()
                or _s in (it.get("nama_produk") or "").lower()
            ]

        # Sort
        if order_by == "nominal_desc":
            # Descending — paling positif dulu
            _items.sort(key=lambda x: x["nominal_adjust"], reverse=True)
        elif order_by == "nominal_asc":
            # Ascending — paling negatif dulu
            _items.sort(key=lambda x: x["nominal_adjust"])
        elif order_by == "tanggal_desc":
            # Terbaru dulu
            _items.sort(key=lambda x: x.get("so_date") or "", reverse=True)
        elif order_by == "tanggal_asc":
            # Lama dulu
            _items.sort(key=lambda x: x.get("so_date") or "")

        if limit:
            _items = _items[:limit]

        _total_nominal = sum(x["nominal_adjust"] for x in _items)

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
            "total_items": len(_items),
            "total_nominal": _total_nominal,
            "items": _items,
        }
    except Exception as e:
        print(f"[GET_TOP_ITEMS_EXT ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200], "items": []}


# =========================================================
# GET STATUS ANALYSIS — Fitur #4
# =========================================================
def get_status_analysis(mode="bulan_ini", tgl_start=None, tgl_end=None):
    """
    Analisis status SO: NSB, BTSB, NSB Personil, Status.

    Returns:
        {
            "success": bool,
            "periode": "...",
            "net_sales": 185628812,
            "total_adjust": -399320,
            "btsb_persen": 0.15,
            "btsb_rupiah": 278443,
            "nsb_personil": 120877,
            "persen": 0.215,
            "status": "bahaya" | "waspada" | "aman",
            "status_label": "BAHAYA",
            "status_emoji": "🚨",
            "status_color": "merah",
            "rekomendasi": "...",
            "adjust_untuk_aman": 120877,
        }
    """
    try:
        _sb = _get_supabase_safe()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        # Tentukan periode
        if mode == "custom" and tgl_start and tgl_end:
            _start_str = tgl_start.isoformat() if isinstance(tgl_start, (date, datetime)) else str(tgl_start)[:10]
            _end_str = tgl_end.isoformat() if isinstance(tgl_end, (date, datetime)) else str(tgl_end)[:10]
        else:
            _start, _end = get_periode_range(mode)
            _start_str = _start.isoformat()[:10]
            _end_str = _end.isoformat()[:10]

        # 1. NET SALES
        _res_spd = (
            _sb.table("spd_harian")
            .select("spd")
            .gte("tanggal", _start_str)
            .lte("tanggal", _end_str)
            .execute()
        )
        _spd_rows = _res_spd.data if _res_spd.data else []
        _net_sales = sum(float(r.get("spd") or 0) for r in _spd_rows)

        # 2. TOTAL ADJUST
        _res_so = (
            _sb.table("so_rak_harian")
            .select("nominal_adjust")
            .gte("so_date", _start_str)
            .lte("so_date", _end_str)
            .execute()
        )
        _so_rows = _res_so.data if _res_so.data else []
        _total_adjust = sum(float(r.get("nominal_adjust") or 0) for r in _so_rows)

        # 3. BTSB & NSB PERSONIL
        _btsb_persen = 0.15
        _btsb_rupiah = (_net_sales * _btsb_persen) / 100 if _net_sales > 0 else 0

        _total_adjust_abs = abs(_total_adjust)
        _nsb_personil = _total_adjust_abs - _btsb_rupiah

        _persen = (_total_adjust_abs / _net_sales * 100) if _net_sales > 0 else 0

        # 4. STATUS
        _status_key = "aman"
        _status_label = "AMAN"
        _status_emoji = "✅"
        _status_color = "hijau"
        _persen_bahaya = 0.15
        _persen_waspada = 0.13

        if _persen > _persen_bahaya:
            _status_key = "bahaya"
            _status_label = "BAHAYA"
            _status_emoji = "🚨"
            _status_color = "merah"
        elif _persen >= _persen_waspada:
            _status_key = "waspada"
            _status_label = "WASPADA"
            _status_emoji = "⚠️"
            _status_color = "kuning"

        # 5. REKOMENDASI
        _rekomendasi = ""
        _adjust_untuk_aman = 0

        if _status_key == "bahaya":
            _target_persen = _persen_waspada
            _target_adjust_max = (_target_persen / 100) * _net_sales
            _adjust_untuk_aman = max(0, _total_adjust_abs - _target_adjust_max)

            if _adjust_untuk_aman > 0:
                _rekomendasi = (
                    f"Status BAHAYA. Beban NSB personil: Rp {_nsb_personil:,.0f}.\n"
                    f"Disarankan adjust plus minimal Rp {_adjust_untuk_aman:,.0f} "
                    f"agar status kembali ke WASPADA."
                )
            else:
                _rekomendasi = "Status BAHAYA. Segera lakukan adjust plus untuk menurunkan selisih."

        elif _status_key == "waspada":
            _target_persen = _persen_waspada
            _target_adjust_max = (_target_persen / 100) * _net_sales
            _adjust_untuk_aman = max(0, _total_adjust_abs - _target_adjust_max)

            _rekomendasi = (
                f"Status WASPADA. Beban NSB personil: Rp {_nsb_personil:,.0f}.\n"
                f"Disarankan adjust plus minimal Rp {_adjust_untuk_aman:,.0f} "
                f"agar status kembali ke AMAN."
            )

        else:
            _target_persen = _persen_bahaya
            _target_adjust_max = (_target_persen / 100) * _net_sales
            _sisa_ruang = max(0, _target_adjust_max - _total_adjust_abs)

            _rekomendasi = (
                f"Status AMAN. Selisih saat ini di bawah BTSB.\n"
                f"Masih bisa melakukan adjust selisih sebesar Rp {_sisa_ruang:,.0f} "
                f"sebelum masuk BAHAYA."
            )

        return {
            "success": True,
            "periode": f"{_start_str} s/d {_end_str}",
            "tgl_start": _start_str,
            "tgl_end": _end_str,
            "net_sales": _net_sales,
            "total_adjust": _total_adjust,
            "total_adjust_abs": _total_adjust_abs,
            "btsb_persen": _btsb_persen,
            "btsb_rupiah": _btsb_rupiah,
            "nsb_personil": _nsb_personil,
            "persen": round(_persen, 3),
            "status": _status_key,
            "status_label": _status_label,
            "status_emoji": _status_emoji,
            "status_color": _status_color,
            "rekomendasi": _rekomendasi,
            "adjust_untuk_aman": _adjust_untuk_aman,
        }

    except Exception as e:
        print(f"[GET_STATUS_ANALYSIS ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)[:200]}