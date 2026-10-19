"""
Yui Rekap — Query & rekap data SO untuk Yui (OPTIMIZED v7.0)
Tanpa pandas. Query ringan. Anti-blocking.
"""

import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))

def _get_supabase_safe():
    try:
        from services.supabase_client import get_supabase
        return get_supabase()
    except Exception as e:
        print(f"[YUI_REKAP] Gagal ambil Supabase: {e}")
        return None

def get_periode_range(mode="hari_ini", tgl_start=None, tgl_end=None):
    _today = _now_jkt().date()
    if mode == "hari_ini": return _today, _today
    if mode == "minggu_ini":
        _start = _today - timedelta(days=_today.weekday()); return _start, _start + timedelta(days=6)
    if mode == "bulan_ini":
        _start = _today.replace(day=1)
        _end = (_start.replace(month=_start.month + 1, day=1) if _start.month < 12 else _start.replace(year=_start.year + 1, month=1, day=1)) - timedelta(days=1)
        return _start, _end
    if mode == "bulan_lalu":
        _first_this = _today.replace(day=1); _last_prev = _first_this - timedelta(days=1)
        return _last_prev.replace(day=1), _last_prev
    if mode == "custom" and tgl_start and tgl_end: return tgl_start, tgl_end
    return _today, _today

# =========================================================
# REKAP SO — OPTIMIZED
# =========================================================
def rekap_so(mode="hari_ini", tgl_start=None, tgl_end=None, pic_filter=None):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {"success": False, "error": "Supabase gak konek"}
        _start, _end = get_periode_range(mode, tgl_start, tgl_end)
        _start_str, _end_str = _start.isoformat(), _end.isoformat()

        # Query ringan: cuma kolom yang dibutuhin
        _q = _sb.table("so_rak_harian").select("rak_id, so_date, nominal_adjust, pic").gte("so_date", _start_str).lte("so_date", _end_str)
        if pic_filter: _q = _q.eq("pic", pic_filter.upper())
        _rows = _q.execute().data or []

        if not _rows:
            return {"success": True, "mode": mode, "periode": f"{_start} s/d {_end}", "tgl_start": _start_str, "tgl_end": _end_str, "total_rak": 0, "total_item": 0, "total_nominal": 0, "list_rak": [], "items_by_rak": {}, "chart_data": [], "sales_periode": 0, "rak_names": {}}

        # Agregasi manual (lebih cepat dari pandas buat data kecil)
        _rak_data = defaultdict(lambda: {"nominal": 0.0, "pic": "-", "tgl": None})
        _chart_data = defaultdict(lambda: {"nominal": 0.0, "rak": set()})
        for r in _rows:
            _rid = r.get("rak_id")
            if not _rid: continue
            _nom = float(r.get("nominal_adjust") or 0)
            _tgl = r.get("so_date")
            _rak_data[_rid]["nominal"] += _nom
            _rak_data[_rid]["pic"] = r.get("pic") or "-"
            _rak_data[_rid]["tgl"] = _tgl
            _chart_data[_tgl]["nominal"] += _nom
            _chart_data[_tgl]["rak"].add(_rid)

        _list_rak = [{"rak_id": k, "total": v["nominal"], "pic": v["pic"], "tanggal": v["tgl"]} for k, v in _rak_data.items()]
        _list_rak.sort(key=lambda x: x["total"])

        # Query so_hasil (cuma kolom rak_id buat hitung total item)
        _res2 = _sb.table("so_hasil").select("rak_id").gte("so_date", _start_str).lte("so_date", _end_str).execute()
        _item_rows = _res2.data or []
        _items_by_rak = defaultdict(list)
        for r in _item_rows: _items_by_rak[r.get("rak_id", "UNKNOWN")].append(r)

        _chart = [{"tanggal": k, "nominal": v["nominal"], "jumlah_rak": len(v["rak"])} for k, v in _chart_data.items()]
        _chart.sort(key=lambda x: x["tanggal"])

        return {
            "success": True, "mode": mode, "periode": f"{_start} s/d {_end}", "tgl_start": _start_str, "tgl_end": _end_str,
            "total_rak": len(_rak_data), "total_item": len(_item_rows), "total_nominal": sum(v["nominal"] for v in _rak_data.values()),
            "list_rak": _list_rak, "items_by_rak": dict(_items_by_rak), "chart_data": _chart,
            "sales_periode": _get_sales_periode(_start, _end), "rak_names": _get_rak_names()
        }
    except Exception as e:
        print(f"[REKAP_SO ERROR] {e}")
        return {"success": False, "error": str(e)[:200]}

# =========================================================
# TOP RAK — OPTIMIZED (Fix order_by)
# =========================================================
def get_top_rak(mode="bulan_ini", tgl_start=None, tgl_end=None, limit=500, order_by="nominal_desc"):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {"success": False, "error": "Supabase gak konek"}
        _start, _end = get_periode_range(mode, tgl_start, tgl_end)
        _start_str, _end_str = _start.isoformat()[:10], _end.isoformat()[:10]

        _rows = _sb.table("so_rak_harian").select("rak_id, so_date, nominal_adjust, pic").gte("so_date", _start_str).lte("so_date", _end_str).execute().data or []
        
        _rak_map = {}
        for r in _rows:
            _rid = r.get("rak_id")
            if not _rid: continue
            _nom = float(r.get("nominal_adjust") or 0)
            if _rid not in _rak_map:
                _rak_map[_rid] = {"rak_id": _rid, "nominal_adjust": _nom, "tgl_so": r.get("so_date"), "pic": r.get("pic") or "-", "total_item": 0}
            else:
                _rak_map[_rid]["nominal_adjust"] += _nom
                if r.get("so_date") and (not _rak_map[_rid]["tgl_so"] or r["so_date"] > _rak_map[_rid]["tgl_so"]):
                    _rak_map[_rid]["tgl_so"] = r["so_date"]

        # Hitung total item
        if _rak_map:
            _res_items = _sb.table("so_hasil").select("rak_id").in_("rak_id", list(_rak_map.keys())).gte("so_date", _start_str).lte("so_date", _end_str).execute()
            _counts = defaultdict(int)
            for r in (_res_items.data or []): _counts[r.get("rak_id")] += 1
            for _rid in _rak_map: _rak_map[_rid]["total_item"] = _counts.get(_rid, 0)

        _list_rak = list(_rak_map.values())
        
        # ✅ FIX ORDER BY
        if order_by == "tanggal_asc": _list_rak.sort(key=lambda x: (x.get("tgl_so") or "", x["nominal_adjust"]))
        elif order_by == "tanggal_desc": _list_rak.sort(key=lambda x: (x.get("tgl_so") or "", x["nominal_adjust"]), reverse=True)
        elif order_by == "nominal_asc": _list_rak.sort(key=lambda x: x["nominal_adjust"])
        else: _list_rak.sort(key=lambda x: x["nominal_adjust"])  # nominal_desc default

        if limit: _list_rak = _list_rak[:limit]
        return {"success": True, "periode": f"{_start_str} s/d {_end_str}", "total_rak": len(_list_rak), "total_nominal": sum(x["nominal_adjust"] for x in _list_rak), "list_rak": _list_rak}
    except Exception as e:
        print(f"[GET_TOP_RAK ERROR] {e}")
        return {"success": False, "error": str(e)[:200], "list_rak": []}

# =========================================================
# SPD LIST — OPTIMIZED
# =========================================================
def get_spd_list(mode="bulan_ini", tgl_start=None, tgl_end=None):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {"success": False, "error": "Supabase gak konek"}
        _start, _end = get_periode_range(mode, tgl_start, tgl_end)
        _start_str, _end_str = _start.isoformat()[:10], _end.isoformat()[:10]

        _rows = _sb.table("spd_harian").select("tanggal, spd, keterangan, pic").gte("tanggal", _start_str).lte("tanggal", _end_str).order("tanggal").execute().data or []
        
        _list_spd = []; _prev = None
        for r in _rows:
            _spd = float(r.get("spd") or 0)
            _delta = 0; _persen = 0; _trend = "flat"
            if _prev is not None and _prev > 0:
                _delta = _spd - _prev; _persen = (_delta / _prev) * 100
                _trend = "up" if _delta > 0 else ("down" if _delta < 0 else "flat")
            _list_spd.append({"tanggal": r.get("tanggal"), "spd": _spd, "delta_nominal": _delta, "delta_persen": _persen, "trend": _trend, "keterangan": r.get("keterangan") or "", "pic": r.get("pic") or "-"})
            _prev = _spd

        _total = sum(x["spd"] for x in _list_spd)
        return {"success": True, "periode": f"{_start_str} s/d {_end_str}", "total_spd": _total, "total_hari": len(_list_spd), "avg_spd": _total / len(_list_spd) if _list_spd else 0, "list_spd": _list_spd}
    except Exception as e:
        print(f"[GET_SPD_LIST ERROR] {e}")
        return {"success": False, "error": str(e)[:200], "list_spd": []}

# =========================================================
# STATUS ANALYSIS — OPTIMIZED
# =========================================================
def get_status_analysis(mode="bulan_ini", tgl_start=None, tgl_end=None):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {"success": False, "error": "Supabase gak konek"}
        _start, _end = get_periode_range(mode, tgl_start, tgl_end)
        _start_str, _end_str = _start.isoformat()[:10], _end.isoformat()[:10]

        _net_sales = sum(float(r.get("spd") or 0) for r in (_sb.table("spd_harian").select("spd").gte("tanggal", _start_str).lte("tanggal", _end_str).execute().data or []))
        _total_adjust = sum(float(r.get("nominal_adjust") or 0) for r in (_sb.table("so_rak_harian").select("nominal_adjust").gte("so_date", _start_str).lte("so_date", _end_str).execute().data or []))
        
        _btsb_persen = 0.15; _btsb_rupiah = (_net_sales * _btsb_persen) / 100 if _net_sales > 0 else 0
        _total_abs = abs(_total_adjust); _nsb_personil = _total_abs - _btsb_rupiah
        _persen = (_total_abs / _net_sales * 100) if _net_sales > 0 else 0

        _status_key, _label, _emoji, _color = "aman", "AMAN", "✅", "hijau"
        if _persen > 0.15: _status_key, _label, _emoji, _color = "bahaya", "BAHAYA", "🚨", "merah"
        elif _persen >= 0.13: _status_key, _label, _emoji, _color = "waspada", "WASPADA", "⚠️", "kuning"

        _rekomendasi = ""; _adjust_aman = 0
        if _status_key == "bahaya":
            _target = (0.13 / 100) * _net_sales; _adjust_aman = max(0, _total_abs - _target)
            _rekomendasi = f"Status BAHAYA. Beban NSB personil: Rp {_nsb_personil:,.0f}.\nDisarankan adjust plus minimal Rp {_adjust_aman:,.0f} agar status kembali ke WASPADA."
        elif _status_key == "waspada":
            _target = (0.13 / 100) * _net_sales; _adjust_aman = max(0, _total_abs - _target)
            _rekomendasi = f"Status WASPADA. Beban NSB personil: Rp {_nsb_personil:,.0f}.\nDisarankan adjust plus minimal Rp {_adjust_aman:,.0f} agar status kembali ke AMAN."
        else:
            _target = (0.15 / 100) * _net_sales; _sisa = max(0, _target - _total_abs)
            _rekomendasi = f"Status AMAN. Selisih saat ini di bawah BTSB.\nMasih bisa melakukan adjust selisih sebesar Rp {_sisa:,.0f} sebelum masuk BAHAYA."

        return {"success": True, "periode": f"{_start_str} s/d {_end_str}", "net_sales": _net_sales, "total_adjust": _total_adjust, "total_adjust_abs": _total_abs, "btsb_persen": _btsb_persen, "btsb_rupiah": _btsb_rupiah, "nsb_personil": _nsb_personil, "persen": round(_persen, 3), "status": _status_key, "status_label": _label, "status_emoji": _emoji, "status_color": _color, "rekomendasi": _rekomendasi, "adjust_untuk_aman": _adjust_aman}
    except Exception as e:
        print(f"[GET_STATUS_ANALYSIS ERROR] {e}")
        return {"success": False, "error": str(e)[:200]}

# =========================================================
# FUNGSI LAIN (sama kayak sebelumnya, tapi tanpa pandas)
# =========================================================
def _get_sales_periode(tgl_start, tgl_end):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return 0
        _res = _sb.table("spd_harian").select("spd").gte("tanggal", tgl_start.isoformat()).lte("tanggal", tgl_end.isoformat()).execute()
        return sum(float(r.get("spd", 0) or 0) for r in (_res.data or []))
    except Exception as e: return 0

def _get_rak_names():
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {}
        _res = _sb.table("rak_master").select("rak_id, rak_name").execute()
        return {r["rak_id"]: r.get("rak_name", "") for r in (_res.data or [])}
    except Exception as e: return {}

def get_rak_status(mode="bulan_ini", tgl_start=None, tgl_end=None):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {"success": False, "error": "Supabase gak konek"}
        _start, _end = get_periode_range(mode, tgl_start, tgl_end)
        _start_str, _end_str = _start.isoformat()[:10], _end.isoformat()[:10]
        
        _master = _sb.table("rak_master").select("rak_id, rak_name").execute().data or []
        _so_rows = _sb.table("so_rak_harian").select("rak_id, so_date, nominal_adjust, pic").gte("so_date", _start_str).lte("so_date", _end_str).execute().data or []
        
        _so_map = {}
        for r in _so_rows:
            _rid = r.get("rak_id")
            if _rid:
                if _rid not in _so_map: _so_map[_rid] = {"tgl_so": r.get("so_date"), "nominal": float(r.get("nominal_adjust") or 0), "pic": r.get("pic") or "-"}
                else: _so_map[_rid]["nominal"] += float(r.get("nominal_adjust") or 0)

        _list = []; _sudah = 0; _belum = 0
        for r in _master:
            _rid = r["rak_id"]
            if _rid in _so_map:
                _info = _so_map[_rid]; _list.append({"rak_id": _rid, "rak_name": r.get("rak_name", ""), "status": "SUDAH", "tgl_so": _info["tgl_so"], "nominal": _info["nominal"], "pic": _info["pic"]}); _sudah += 1
            else:
                _list.append({"rak_id": _rid, "rak_name": r.get("rak_name", ""), "status": "BELUM", "tgl_so": None, "nominal": 0, "pic": None}); _belum += 1
        _list.sort(key=lambda x: (x["status"] != "SUDAH", x["rak_id"]))
        return {"success": True, "periode": f"{_start_str} s/d {_end_str}", "total_rak": len(_master), "sudah_so": _sudah, "belum_so": _belum, "list_rak": _list}
    except Exception as e: return {"success": False, "error": str(e)[:200]}

def get_items_by_rak_extended(rak_id, mode="bulan_ini", tgl_start=None, tgl_end=None):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {"success": False, "error": "Supabase gak konek"}
        _start, _end = get_periode_range(mode, tgl_start, tgl_end)
        _start_str, _end_str = _start.isoformat()[:10], _end.isoformat()[:10]
        _items = _sb.table("so_hasil").select("plu, nama_produk, rak_id, qty_var, nominal_adjust, pic, so_date").eq("rak_id", rak_id.upper()).gte("so_date", _start_str).lte("so_date", _end_str).execute().data or []
        for it in _items: it["qty_var"] = int(it.get("qty_var") or 0); it["nominal_adjust"] = float(it.get("nominal_adjust") or 0)
        _minus = sum(x["nominal_adjust"] for x in _items if x["nominal_adjust"] < 0)
        _plus = sum(x["nominal_adjust"] for x in _items if x["nominal_adjust"] > 0)
        return {"success": True, "rak_id": rak_id.upper(), "periode": f"{_start_str} s/d {_end_str}", "tgl_so": _items[0]["so_date"] if _items else None, "pic": _items[0]["pic"] if _items else "-", "total_minus": _minus, "total_plus": _plus, "total_nominal": _minus + _plus, "total_item": len(_items), "items": _items}
    except Exception as e: return {"success": False, "error": str(e)[:200], "items": []}

def get_top_items_extended(mode="bulan_ini", tgl_start=None, tgl_end=None, limit=None, search="", order_by="nominal_desc", sign="minus"):
    try:
        _sb = _get_supabase_safe()
        if _sb is None: return {"success": False, "error": "Supabase gak konek", "items": []}
        _start, _end = get_periode_range(mode, tgl_start, tgl_end)
        _start_str, _end_str = _start.isoformat()[:10], _end.isoformat()[:10]
        _q = _sb.table("so_hasil").select("plu, nama_produk, rak_id, qty_var, nominal_adjust, pic, so_date").gte("so_date", _start_str).lte("so_date", _end_str)
        if sign == "minus": _q = _q.lt("nominal_adjust", 0)
        elif sign == "plus": _q = _q.gt("nominal_adjust", 0)
        _items = _q.limit(5000).execute().data or []
        for it in _items: it["qty_var"] = int(it.get("qty_var") or 0); it["nominal_adjust"] = float(it.get("nominal_adjust") or 0)
        if search:
            _s = search.lower(); _items = [it for it in _items if _s in (it.get("plu") or "").lower() or _s in (it.get("nama_produk") or "").lower()]
        if order_by == "nominal_desc": _items.sort(key=lambda x: x["nominal_adjust"], reverse=True)
        elif order_by == "nominal_asc": _items.sort(key=lambda x: x["nominal_adjust"])
        elif order_by == "tanggal_desc": _items.sort(key=lambda x: x.get("so_date") or "", reverse=True)
        elif order_by == "tanggal_asc": _items.sort(key=lambda x: x.get("so_date") or "")
        if limit: _items = _items[:limit]
        return {"success": True, "periode": f"{_start_str} s/d {_end_str}", "total_items": len(_items), "total_nominal": sum(x["nominal_adjust"] for x in _items), "items": _items}
    except Exception as e: return {"success": False, "error": str(e)[:200], "items": []}