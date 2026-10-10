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
    """
    Hitung rentang tanggal berdasarkan mode.
    
    mode: 'hari_ini', 'minggu_ini', 'bulan_ini', 'custom'
    """
    _today = _now_jkt().date()

    if mode == "hari_ini":
        return _today, _today

    if mode == "minggu_ini":
        # Senin - Minggu
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
    """
    Rekap SO: summary + detail per rak.
    
    Returns:
        dict {
            success, periode, total_rak, total_item, total_nominal,
            list_rak: [...], detail_df, chart_data
        }
    """
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"success": False, "error": "Supabase gak konek"}

        _start, _end = get_periode_range(mode, tgl_start, tgl_end)

        # Query so_rak_harian
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
                "periode": f"{_start} s/d {_end}",
                "total_rak": 0,
                "total_item": 0,
                "total_nominal": 0,
                "list_rak": [],
                "detail_df": pd.DataFrame(),
                "chart_data": [],
            }

        _df = pd.DataFrame(_rows)
        _df["nominal_adjust"] = pd.to_numeric(
            _df["nominal_adjust"], errors="coerce"
        ).fillna(0)

        _total_rak = int(_df["rak_id"].nunique())
        _total_nominal = float(_df["nominal_adjust"].sum())

        # Query so_hasil buat total item
        _q2 = (
            _sb.table("so_hasil")
            .select("id", count="exact")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
        )
        _res2 = _q2.execute()
        _total_item = _res2.count if hasattr(_res2, "count") and _res2.count else len(_res2.data or [])

        # List rak unik dengan total
        _list_rak = []
        for _rak, _grp in _df.groupby("rak_id"):
            _list_rak.append({
                "rak_id": _rak,
                "total": float(_grp["nominal_adjust"].sum()),
                "pic": _grp["pic"].iloc[0] if "pic" in _grp.columns else "-",
                "tanggal": _grp["so_date"].iloc[0] if "so_date" in _grp.columns else "-",
            })
        _list_rak.sort(key=lambda x: x["total"])

        # Chart data: nominal per hari
        _chart_data = []
        for _tgl, _grp in _df.groupby("so_date"):
            _chart_data.append({
                "tanggal": _tgl,
                "nominal": float(_grp["nominal_adjust"].sum()),
                "jumlah_rak": int(_grp["rak_id"].nunique()),
            })
        _chart_data.sort(key=lambda x: x["tanggal"])

        return {
            "success": True,
            "periode": f"{_start} s/d {_end}",
            "total_rak": _total_rak,
            "total_item": _total_item,
            "total_nominal": _total_nominal,
            "list_rak": _list_rak,
            "detail_df": _df,
            "chart_data": _chart_data,
        }

    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def cek_rak_belum_so(tanggal=None):
    """List rak yang belum di-SO pada tanggal tertentu."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return []

        _tgl = tanggal or _now_jkt().date()
        _tgl_str = _tgl.isoformat()[:10] if isinstance(_tgl, (date, datetime)) else str(_tgl)[:10]

        # Ambil semua rak
        _res_all = _sb.table("rak_master").select("rak_id, rak_name").execute()
        _all_rak = {r["rak_id"]: r.get("rak_name", "") for r in (_res_all.data or [])}

        # Ambil rak yang udah SO
        _res_so = (
            _sb.table("so_rak_harian")
            .select("rak_id")
            .eq("so_date", _tgl_str)
            .execute()
        )
        _sudah_so = set(r["rak_id"] for r in (_res_so.data or []))

        # Rak yang belum
        _belum = [
            {"rak_id": _r, "rak_name": _all_rak[_r]}
            for _r in _all_rak if _r not in _sudah_so
        ]
        _belum.sort(key=lambda x: x["rak_id"])
        return _belum

    except Exception as e:
        print(f"[CEK_RAK_BELUM ERROR] {e}")
        return []


def cek_duplikat(tanggal=None, rak_id=None):
    """Cek apakah ada input duplikat."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return []

        _tgl = tanggal or _now_jkt().date()
        _tgl_str = _tgl.isoformat()[:10] if isinstance(_tgl, (date, datetime)) else str(_tgl)[:10]

        _q = _sb.table("so_rak_harian").select("*").eq("so_date", _tgl_str)
        if rak_id:
            _q = _q.eq("rak_id", rak_id.upper())
        _res = _q.execute()

        return _res.data or []

    except Exception as e:
        print(f"[CEK_DUPLIKAT ERROR] {e}")
        return []

def export_rekap_image(hasil, filename="rekap_so.png"):
    """Export rekap SO jadi gambar PNG pakai df2img."""
    try:
        import df2img
        
        _df = pd.DataFrame(hasil.get("list_rak", []))
        if _df.empty:
            return None
        
        _df = _df.rename(columns={
            "rak_id": "Rak",
            "total": "Nominal",
            "pic": "PIC",
        })
        
        # Format nominal
        _df["Nominal"] = _df["Nominal"].apply(
            lambda x: f"Rp {int(x):,}".replace(",", ".")
        )
        
        _fig = df2img.plot_dataframe(
            _df,
            title={
                "text": f"Rekap SO — {hasil['periode']}",
                "font_color": "#7FB99B",
                "font_size": 16,
            },
            tbl_header=dict(
                fill_color="#7FB99B",
                font_color="white",
                font_size=12,
            ),
            row_fill_color=("#ffffff", "#f0f0f0"),
            fig_size=(600, 80 + len(_df) * 30),
        )
        
        df2img.save_dataframe(fig=_fig, filename=filename)
        return filename
    except Exception as e:
        print(f"[EXPORT_IMG ERROR] {e}")
        return None
        
def _get_net_sales_bulan(bulan=None, tahun=None):
    """
    Hitung net sales bulanan.
    Prioritas: SUM(spd_harian) bulan ini.
    Fallback: tabel net_sales (kolom 'net_sales').
    """
    try:
        _sb = get_supabase()
        if _sb is None:
            return 0

        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _bulan = bulan or _now.month
        _tahun = tahun or _now.year

        # Range tanggal
        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - timedelta(days=1)

        # Prioritas: SUM dari spd_harian
        try:
            _res = (
                _sb.table("spd_harian")
                .select("spd")
                .gte("tanggal", _start.isoformat())
                .lte("tanggal", _end.isoformat())
                .execute()
            )
            if _res.data:
                # ✅ Sum dulu, baru abs — biar minus & plus saling cancel
                _sum_raw = sum(float(r.get("nominal_adjust", 0) or 0) for r in _res.data)
                _total = abs(_sum_raw)
                print(f"[SELISIH_BULAN] raw={_sum_raw}, abs={_total} ({len(_res.data)} rows)")
                return _total
        except Exception as _e:
            print(f"[NET_SALES] spd_harian error: {_e}")

        # Fallback: tabel net_sales (kolom 'net_sales')
        try:
            _res2 = (
                _sb.table("net_sales")
                .select("net_sales")
                .eq("bulan", _bulan)
                .eq("tahun", _tahun)
                .execute()
            )
            if _res2.data:
                _total2 = sum(float(r.get("net_sales", 0) or 0) for r in _res2.data)
                print(f"[NET_SALES] Fallback ke tabel net_sales: {_total2}")
                return _total2
        except Exception as _e2:
            print(f"[NET_SALES] net_sales error: {_e2}")

        return 0
    except Exception as e:
        print(f"[NET_SALES ERROR] {e}")
        return 0

def _get_total_selisih_bulan(bulan=None, tahun=None):
    """Hitung total selisih (abs) 1 bulan dari so_rak_harian."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return 0

        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
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
            _total = sum(abs(float(r.get("nominal_adjust", 0) or 0)) for r in _res.data)
            print(f"[SELISIH_BULAN] {_total} ({len(_res.data)} rows)")
            return _total
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

        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
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
            _unique = len(set(r.get("rak_id", "") for r in _res.data))
            print(f"[RAK_BULAN] {_unique} rak unik dari {len(_res.data)} rows")
            return _unique
        return 0
    except Exception as e:
        print(f"[RAK_BULAN ERROR] {e}")
        return 0