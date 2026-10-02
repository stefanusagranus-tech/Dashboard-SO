"""
Input Handler
=============
Handle input harian: SPD + SO rak + akumulasi.
"""

import streamlit as st
from datetime import datetime, date
from zoneinfo import ZoneInfo
from modules.supabase_client import get_supabase
from modules.spd_calculator import save_spd_harian


# =========================================================================
# 💾 SAVE: INPUT HARIAN (SPD + SO RAK)
# =========================================================================
def save_input_harian(
    tanggal,
    spd,
    rak_items=None,
    keterangan="",
    pic="",
    update_status_rak=True,
):
    """
    Simpan input harian: SPD + SO rak (multiple).
    
    Args:
        tanggal: date
        spd: float (boleh 0)
        rak_items: list of dict [{rak_id, nominal_adjust}]
        keterangan: str
        pic: str
        update_status_rak: bool
    
    Returns:
        (success, message, detail)
    """
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase", {}
        
        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _tgl_str = tanggal.isoformat()[:10] if isinstance(tanggal, (date, datetime)) else str(tanggal)[:10]
        
        _detail = {
            "spd_saved": False,
            "rak_saved": 0,
            "rak_updated": 0,
            "total_nominal": 0,
        }
        
        # ============================================================
        # STEP 1: SIMPAN SPD (kalau > 0)
        # ============================================================
        if spd > 0:
            _ok_spd, _msg_spd = save_spd_harian(tanggal, spd, keterangan)
            if not _ok_spd:
                return False, f"❌ Gagal simpan SPD: {_msg_spd}", _detail
            _detail["spd_saved"] = True
        
        # ============================================================
        # STEP 2: SIMPAN SO RAK (kalau ada)
        # ============================================================
        if rak_items and len(rak_items) > 0:
            _rows = []
            _total_nominal = 0
            
            for _item in rak_items:
                _rak_id = str(_item.get("rak_id", "")).strip().upper()
                if not _rak_id:
                    continue
                
                _nominal = float(_item.get("nominal_adjust", 0))
                _total_nominal += _nominal
                
                _rows.append({
                    "so_date": _tgl_str,
                    "rak_id": _rak_id,
                    "nominal_adjust": _nominal,
                    "keterangan": str(keterangan),
                    "pic": str(pic).upper(),
                    "updated_at": _now.isoformat(),
                })
            
            if _rows:
                # UPSERT — update kalau (so_date, rak_id) sudah ada, insert kalau belum
                _res = sb.table("so_rak_harian").upsert(
                    _rows,
                    on_conflict="so_date,rak_id"
                ).execute()
                
                if _res.data:
                    _detail["rak_saved"] = len(_res.data)
                    _detail["total_nominal"] = _total_nominal
                    
                    # Update status rak di rak_master
                    if update_status_rak:
                        for _row in _rows:
                            _upd = (
                                sb.table("rak_master")
                                .update({
                                    "status_so": "SELESAI",
                                    "last_so_date": _tgl_str,
                                    "updated_at": _now.isoformat(),
                                })
                                .eq("rak_id", _row["rak_id"])
                                .execute()
                            )
                            if _upd.data:
                                _detail["rak_updated"] += 1
                else:
                    return False, "❌ Gagal simpan SO rak", _detail
        
        # ============================================================
        # BUILD MESSAGE
        # ============================================================
        _msg_parts = []
        if _detail["spd_saved"]:
            _msg_parts.append(f"SPD tersimpan")
        if _detail["rak_saved"] > 0:
            _msg_parts.append(f"{_detail['rak_saved']} rak di-SO")
        if _detail["rak_updated"] > 0:
            _msg_parts.append(f"{_detail['rak_updated']} rak di-update status")
        
        _msg = "✅ " + " • ".join(_msg_parts) if _msg_parts else "✅ Tersimpan"
        
        return True, _msg, _detail
    
    except Exception as e:
        return False, f"❌ Error: {str(e)[:200]}", {}


# =========================================================================
# 📥 LOAD: SPD & SO RAK BY DATE
# =========================================================================
def load_spd_by_date(tanggal):
    """Load SPD untuk tanggal tertentu."""
    try:
        sb = get_supabase()
        if sb is None:
            return None
        
        _tgl = tanggal.isoformat()[:10] if isinstance(tanggal, (date, datetime)) else str(tanggal)[:10]
        _res = sb.table("spd_harian").select("*").eq("tanggal", _tgl).execute()
        
        if _res.data and len(_res.data) > 0:
            return _res.data[0]
        return None
    except Exception as e:
        print(f"[LOAD_SPD ERROR] {e}")
        return None


def load_so_rak_by_date(tanggal):
    """Load SO rak untuk tanggal tertentu."""
    try:
        sb = get_supabase()
        if sb is None:
            return []
        
        _tgl = tanggal.isoformat()[:10] if isinstance(tanggal, (date, datetime)) else str(tanggal)[:10]
        _res = (
            sb.table("so_rak_harian")
            .select("*")
            .eq("so_date", _tgl)
            .order("rak_id")
            .execute()
        )
        
        return _res.data if _res.data else []
    except Exception as e:
        print(f"[LOAD_SO_RAK ERROR] {e}")
        return []


# =========================================================================
# 🔍 SEARCH RAK
# =========================================================================
def search_rak(query, limit=20):
    """Cari rak berdasarkan kode atau nama."""
    try:
        sb = get_supabase()
        if sb is None:
            return []
        
        _q = str(query).strip().upper()
        if not _q:
            return []
        
        _res = (
            sb.table("rak_master")
            .select("rak_id, rak_name, status_so")
            .or_(f"rak_id.ilike.%{_q}%,rak_name.ilike.%{_q}%")
            .order("rak_id")
            .limit(limit)
            .execute()
        )
        
        if not _res.data:
            return []
        
        return list(_res.data)
    except Exception as e:
        print(f"[SEARCH_RAK ERROR] {e}")
        return []


# =========================================================================
# 📊 AKUMULASI & TREND
# =========================================================================
def get_akumulasi_nominal_bulan(bulan=None, tahun=None):
    """
    Hitung total nominal adjustment bulan ini.
    
    Returns:
        dict {
            total_nominal: float,
            total_rak: int,
            jumlah_hari: int,
        }
    """
    try:
        sb = get_supabase()
        if sb is None:
            return {"total_nominal": 0, "total_rak": 0, "jumlah_hari": 0}
        
        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _bulan = bulan if bulan else _now.month
        _tahun = tahun if tahun else _now.year
        
        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - __import__('datetime').timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - __import__('datetime').timedelta(days=1)
        
        _res = (
            sb.table("so_rak_harian")
            .select("nominal_adjust, rak_id, so_date")
            .gte("so_date", _start.isoformat())
            .lte("so_date", _end.isoformat())
            .execute()
        )
        
        if not _res.data:
            return {"total_nominal": 0, "total_rak": 0, "jumlah_hari": 0}
        
        _total = sum(float(r.get("nominal_adjust", 0)) for r in _res.data)
        _unique_rak = len(set(r.get("rak_id", "") for r in _res.data))
        _unique_hari = len(set(r.get("so_date", "") for r in _res.data))
        
        return {
            "total_nominal": _total,
            "total_rak": _unique_rak,
            "jumlah_hari": _unique_hari,
        }
    except Exception as e:
        print(f"[AKUMULASI ERROR] {e}")
        return {"total_nominal": 0, "total_rak": 0, "jumlah_hari": 0}


def get_nominal_per_hari(limit=None):
    """Ambil semua nominal SO per hari (tanpa batas)."""
    try:
        _sb = get_supabase()
        _res = _sb.table("so_rak_harian") \
            .select("so_date, nominal_adjust") \
            .order("so_date", desc=False) \
            .execute()
        
        if not _res.data:
            return []
        
        _df = pd.DataFrame(_res.data)
        _df["so_date"] = pd.to_datetime(_df["so_date"])
        _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
        
        _grp = _df.groupby("so_date")["nominal_adjust"].sum().reset_index()
        
        # ✅ FIX: Kalau limit ada, apply. Kalau None, ambil semua
        if limit is not None and limit > 0:
            _grp = _grp.tail(limit)
        
        return [
            {
                "tanggal": r["so_date"].strftime("%Y-%m-%d"),
                "nominal": float(r["nominal_adjust"]),
            }
            for _, r in _grp.iterrows()
        ]
    except Exception as e:
        print(f"[get_nominal_per_hari ERROR] {e}")
        return []


def get_so_rak_detail(limit=10):
    """Ambil detail SO rak terbaru."""
    try:
        sb = get_supabase()
        if sb is None:
            return []
        
        _res = (
            sb.table("so_rak_harian")
            .select("*")
            .order("so_date", desc=True)
            .order("rak_id")
            .limit(limit)
            .execute()
        )
        
        return _res.data if _res.data else []
    except Exception as e:
        print(f"[SO_RAK_DETAIL ERROR] {e}")
        return []


# =========================================================================
# 📋 GET RAK BELUM SO (untuk dropdown — semua rak)
# =========================================================================
def get_rak_belum_so():
    """Ambil semua rak (untuk search, gak filter status)."""
    try:
        sb = get_supabase()
        if sb is None:
            return []
        
        _res = (
            sb.table("rak_master")
            .select("rak_id, rak_name")
            .order("rak_id")
            .execute()
        )
        
        if not _res.data:
            return []
        
        return [f"{r['rak_id']} — {r['rak_name']}" for r in _res.data]
    except Exception as e:
        print(f"[GET_RAK_BELUM ERROR] {e}")
        return []


def get_so_hari_ini(tanggal=None):
    """Ambil SO hari ini."""
    try:
        sb = get_supabase()
        if sb is None:
            return []
        
        _tgl = tanggal or datetime.now(ZoneInfo("Asia/Jakarta")).date()
        _tgl_str = _tgl.isoformat()[:10] if isinstance(_tgl, (date, datetime)) else str(_tgl)[:10]
        
        _res = (
            sb.table("so_rak_harian")
            .select("*")
            .eq("so_date", _tgl_str)
            .order("rak_id")
            .execute()
        )
        
        return _res.data if _res.data else []
    except Exception as e:
        print(f"[GET_SO_TODAY ERROR] {e}")
        return []


def get_spd_hari_ini():
    """Ambil SPD hari ini."""
    try:
        sb = get_supabase()
        if sb is None:
            return 0
        
        _today = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
        _res = sb.table("spd_harian").select("spd").eq("tanggal", _today).execute()
        
        if _res.data and len(_res.data) > 0:
            return int(_res.data[0]["spd"])
        return 0
    except Exception as e:
        print(f"[GET_SPD_TODAY ERROR] {e}")
        return 0


def get_rak_by_kode_exact(rak_id):
    """Ambil rak by kode exact."""
    try:
        sb = get_supabase()
        if sb is None:
            return None
        
        _res = (
            sb.table("rak_master")
            .select("*")
            .eq("rak_id", str(rak_id).strip().upper())
            .execute()
        )
        
        if _res.data and len(_res.data) > 0:
            return _res.data[0]
        return None
    except Exception as e:
        print(f"[GET_RAK_EXACT ERROR] {e}")
        return None