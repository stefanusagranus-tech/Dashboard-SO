"""
Input Handler
=============
Handle input harian: SPD + SO rak + akumulasi.
"""

import streamlit as st
import pandas as pd         
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
    Simpan input harian: SPD + SO rak (summary) + SO hasil (detail per PLU).
    
    Args:
        tanggal: date
        spd: float (boleh 0)
        rak_items: list of dict [
            {rak_id, plu, nama_produk, qty_sistem, qty_fisik, qty_var, nominal_adjust}
        ]
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
            "rak_saved": 0,      # rows di so_rak_harian
            "hasil_saved": 0,    # rows di so_hasil
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
        # STEP 2: SIMPAN SO RAK (summary) + SO HASIL (detail)
        # ============================================================
        if rak_items and len(rak_items) > 0:
            _rak_agg = {}
            _hasil_rows = []
            _total_nominal = 0

            for _item in rak_items:
                _rak_id = str(_item.get("rak_id", "")).strip().upper()
                if not _rak_id:
                    continue

                _nominal = float(_item.get("nominal_adjust", 0) or 0)
                _total_nominal += _nominal

                # ✅ Aggregate summary per rak
                if _rak_id not in _rak_agg:
                    _rak_agg[_rak_id] = 0
                _rak_agg[_rak_id] += _nominal

                # ✅ Detail per PLU → so_hasil
                _plu = str(_item.get("plu", "") or "").strip()
                if _plu:
                    _hasil_rows.append({
                        "so_date": _tgl_str,
                        "rak_id": _rak_id,
                        "plu": _plu,
                        "nama_produk": str(_item.get("nama_produk", "") or "")[:200],
                        "qty_sistem": int(_item.get("qty_sistem", 0) or 0),
                        "qty_fisik": int(_item.get("qty_fisik", 0) or 0),
                        "qty_var": int(_item.get("qty_var", 0) or 0),
                        "nominal_adjust": _nominal,
                        "pic": str(pic).upper(),
                        "keterangan": str(keterangan),
                        "updated_at": _now.isoformat(),
                    })

            if not _rak_agg:
                return False, "❌ Gak ada rak valid", _detail

            # --- 2A: UPSERT summary per rak ke so_rak_harian ---
            _summary_rows = []
            for _rak_id, _nominal in _rak_agg.items():
                _summary_rows.append({
                    "so_date": _tgl_str,
                    "rak_id": _rak_id,
                    "nominal_adjust": _nominal,
                    "keterangan": str(keterangan),
                    "pic": str(pic).upper(),
                    "updated_at": _now.isoformat(),
                })

            _res_summary = sb.table("so_rak_harian").upsert(
                _summary_rows,
                on_conflict="so_date,rak_id"
            ).execute()

            if _res_summary.data:
                _detail["rak_saved"] = len(_res_summary.data)
                _detail["total_nominal"] = _total_nominal
            else:
                return False, "❌ Gagal simpan SO rak (summary)", _detail

            # --- 2B: UPSERT detail per PLU ke so_hasil ---
            if _hasil_rows:
                # Cek duplikat (rak_id + plu) dalam 1 batch — upsert gak bisa handle duplikat
                _seen = {}
                _dedup_rows = []
                for _r in _hasil_rows:
                    _key = f"{_r['rak_id']}|{_r['plu']}"
                    if _key in _seen:
                        # Ambil yang terakhir (last-write-wins)
                        _dedup_rows[_seen[_key]] = _r
                        continue
                    _seen[_key] = len(_dedup_rows)
                    _dedup_rows.append(_r)

                try:
                    _res_hasil = sb.table("so_hasil").upsert(
                        _dedup_rows,
                        on_conflict="so_date,rak_id,plu"
                    ).execute()
                    if _res_hasil.data:
                        _detail["hasil_saved"] = len(_res_hasil.data)
                except Exception as _e_hasil:
                    # Jangan fail seluruh save — summary tetep ke-save
                    print(f"[SAVE_HASIL WARN] {_e_hasil}")
                    # Fallback: insert satu-satu (hindari duplikat batch)
                    _saved_one_by_one = 0
                    for _r in _dedup_rows:
                        try:
                            sb.table("so_hasil").upsert(
                                _r, on_conflict="so_date,rak_id,plu"
                            ).execute()
                            _saved_one_by_one += 1
                        except Exception:
                            continue
                    _detail["hasil_saved"] = _saved_one_by_one

            # --- 2C: Update status rak di rak_master ---
            if update_status_rak:
                for _rak_id in _rak_agg.keys():
                    try:
                        _upd = (
                            sb.table("rak_master")
                            .update({
                                "status_so": "SELESAI",
                                "last_so_date": _tgl_str,
                                "updated_at": _now.isoformat(),
                            })
                            .eq("rak_id", _rak_id)
                            .execute()
                        )
                        if _upd.data:
                            _detail["rak_updated"] += 1
                    except Exception:
                        pass
        
        # ============================================================
        # BUILD MESSAGE
        # ============================================================
        _msg_parts = []
        if _detail["spd_saved"]:
            _msg_parts.append("SPD tersimpan")
        if _detail["rak_saved"] > 0:
            _msg_parts.append(f"{_detail['rak_saved']} rak di-SO")
        if _detail["hasil_saved"] > 0:
            _msg_parts.append(f"{_detail['hasil_saved']} item detail")
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
        
        # ✅ FIX: Select * dulu (jangan spesifik kolom)
        _res = _sb.table("so_rak_harian").select("*").execute()
        
        # ✅ DEBUG (sementara)
        print(f"[DEBUG get_nominal_per_hari] Raw rows: {len(_res.data) if _res.data else 0}")
        
        if not _res.data:
            return []
        
        # ✅ FIX: Parse pakai try-except per row
        _df = pd.DataFrame(_res.data)
        print(f"[DEBUG] DataFrame shape: {_df.shape}")
        print(f"[DEBUG] Columns: {list(_df.columns)}")
        
        if "so_date" not in _df.columns or "nominal_adjust" not in _df.columns:
            print(f"[ERROR] Kolom tidak lengkap: {list(_df.columns)}")
            return []
        
        _df["so_date"] = pd.to_datetime(_df["so_date"], errors="coerce")
        _df["nominal_adjust"] = pd.to_numeric(_df["nominal_adjust"], errors="coerce").fillna(0)
        
        # Drop rows dengan so_date NaT
        _df = _df.dropna(subset=["so_date"])
        print(f"[DEBUG] After dropna: {len(_df)} rows")
        
        if _df.empty:
            return []
        
        _grp = _df.groupby("so_date")["nominal_adjust"].sum().reset_index()
        _grp = _grp.sort_values("so_date", ascending=True)
        
        # Apply limit
        if limit is not None and limit > 0:
            _grp = _grp.tail(limit)
        
        # ✅ Build result
        _result = []
        for _, r in _grp.iterrows():
            try:
                _tgl_str = r["so_date"].strftime("%Y-%m-%d")
                _nominal = float(r["nominal_adjust"])
                _result.append({
                    "tanggal": _tgl_str,
                    "nominal": _nominal,
                })
            except Exception as e_row:
                print(f"[ROW ERROR] {e_row} — row: {r.to_dict()}")
                continue
        
        print(f"[DEBUG] Result: {_result}")
        return _result
    
    except Exception as e:
        print(f"[get_nominal_per_hari ERROR] {e}")
        import traceback
        print(traceback.format_exc())
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