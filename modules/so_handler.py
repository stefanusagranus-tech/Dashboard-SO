"""
SO Handler — Handle Stock Opname
==================================
Input multi-produk per rak, auto-save ke 2 tabel.

Fitur:
- save_so_input()     → Simpan SO (detail + summary)
- load_so_by_date()   → Load SO per tanggal
- delete_so_by_date() → Hapus SO per tanggal
- get_so_summary()    → Ambil summary
"""

import streamlit as st
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from modules.supabase_client import get_supabase


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


# =========================================================
# 💾 SAVE SO INPUT
# =========================================================
def save_so_input(tanggal, rak_id, pic, produk_list, keterangan=""):
    """
    Simpan SO untuk 1 rak dengan multiple produk.
    
    Args:
        tanggal: date
        rak_id: str — kode rak (contoh: Q51)
        pic: str — nama PIC
        produk_list: list of dict {
            "plu": str,
            "nama_produk": str,
            "qty_sistem": int,
            "qty_fisik": int,
            "nominal_adjust": float,  # nominal selisih
        }
        keterangan: str — notes umum
    
    Returns:
        (success, message, detail)
    """
    try:
        _sb = get_supabase()
        
        if not produk_list:
            return False, "❌ Tidak ada produk yang diinput", {}
        
        _tgl_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]
        _now = _now_jkt().isoformat()
        
        # === 1. HITUNG SUMMARY ===
        _total_item = len(produk_list)
        _total_qty_var = sum(int(p.get("qty_var", 0)) for p in produk_list)
        _total_nominal = sum(float(p.get("nominal_adjust", 0)) for p in produk_list)
        
        # === 2. SIMPAN DETAIL KE so_hasil ===
        _detail_rows = []
        for _p in produk_list:
            _qty_sistem = int(_p.get("qty_sistem", 0))
            _qty_fisik = int(_p.get("qty_fisik", 0))
            _qty_var = _qty_fisik - _qty_sistem
            
            _detail_rows.append({
                "so_date": _tgl_str,
                "rak_id": rak_id,
                "plu": str(_p.get("plu", "")),
                "nama_produk": str(_p.get("nama_produk", "")),
                "qty_sistem": _qty_sistem,
                "qty_fisik": _qty_fisik,
                "qty_var": _qty_var,
                "nominal_adjust": float(_p.get("nominal_adjust", 0)),
                "pic": pic,
                "created_at": _now,
            })
        
        # Insert ke so_hasil
        _res_detail = _sb.table("so_hasil").insert(_detail_rows).execute()
        
        if not _res_detail.data:
            return False, "❌ Gagal insert detail SO", {}
        
        # === 3. SIMPAN SUMMARY KE so_rak_harian ===
        # Cek dulu apakah udah ada entry untuk tanggal + rak ini
        _existing = _sb.table("so_rak_harian") \
            .select("id") \
            .eq("so_date", _tgl_str) \
            .eq("rak_id", rak_id) \
            .execute()
        
        _summary_data = {
            "so_date": _tgl_str,
            "rak_id": rak_id,
            "nominal_adjust": _total_nominal,
            "keterangan": keterangan,
            "pic": pic,
            "updated_at": _now,
            "total_item": _total_item,
            "total_qty_var": _total_qty_var,
        }
        
        if _existing.data:
            # UPDATE
            _summary_data["created_at"] = _existing.data[0].get("created_at", _now)
            _res_summary = _sb.table("so_rak_harian") \
                .update(_summary_data) \
                .eq("id", _existing.data[0]["id"]) \
                .execute()
        else:
            # INSERT
            _summary_data["created_at"] = _now
            _res_summary = _sb.table("so_rak_harian") \
                .insert(_summary_data) \
                .execute()
        
        # === 4. UPDATE STATUS RAK ===
        try:
            _sb.table("rak_master") \
                .update({
                    "status_so": "SELESAI",
                    "last_so_date": _tgl_str,
                }) \
                .eq("rak_id", rak_id) \
                .execute()
        except Exception as _e_rak:
            print(f"[RAK UPDATE ERROR] {_e_rak}")
        
        return True, f"✅ SO rak **{rak_id}** tersimpan ({_total_item} produk)", {
            "total_item": _total_item,
            "total_qty_var": _total_qty_var,
            "total_nominal": _total_nominal,
            "detail_count": len(_detail_rows),
        }
    
    except Exception as _e:
        import traceback
        print(f"[SO INPUT ERROR] {_e}")
        print(traceback.format_exc())
        return False, f"❌ Error: {str(_e)[:200]}", {}


# =========================================================
# 📖 LOAD SO BY DATE
# =========================================================
def load_so_detail_by_date(tanggal, rak_id=None):
    """
    Load detail SO per tanggal (dari so_hasil).
    """
    try:
        _sb = get_supabase()
        _tgl_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]
        
        _query = _sb.table("so_hasil") \
            .select("*") \
            .eq("so_date", _tgl_str)
        
        if rak_id:
            _query = _query.eq("rak_id", rak_id)
        
        _res = _query.order("created_at").execute()
        return _res.data or []
    except Exception as _e:
        print(f"[LOAD SO DETAIL ERROR] {_e}")
        return []


def load_so_summary_by_date(tanggal):
    """
    Load summary SO per tanggal (dari so_rak_harian).
    """
    try:
        _sb = get_supabase()
        _tgl_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]
        
        _res = _sb.table("so_rak_harian") \
            .select("*") \
            .eq("so_date", _tgl_str) \
            .order("created_at") \
            .execute()
        return _res.data or []
    except Exception as _e:
        print(f"[LOAD SO SUMMARY ERROR] {_e}")
        return []


# =========================================================
# 🗑️ DELETE SO BY DATE
# =========================================================
def delete_so_by_date(tanggal, rak_id=None):
    """
    Hapus SO per tanggal (detail + summary).
    """
    try:
        _sb = get_supabase()
        _tgl_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]
        
        _deleted_detail = 0
        _deleted_summary = 0
        
        # Delete so_hasil
        _q_detail = _sb.table("so_hasil").delete().eq("so_date", _tgl_str)
        if rak_id:
            _q_detail = _q_detail.eq("rak_id", rak_id)
        _res_detail = _q_detail.execute()
        _deleted_detail = len(_res_detail.data or [])
        
        # Delete so_rak_harian
        _q_summary = _sb.table("so_rak_harian").delete().eq("so_date", _tgl_str)
        if rak_id:
            _q_summary = _q_summary.eq("rak_id", rak_id)
        _res_summary = _q_summary.execute()
        _deleted_summary = len(_res_summary.data or [])
        
        return True, f"🗑️ Hapus: {_deleted_detail} detail + {_deleted_summary} summary", {
            "detail": _deleted_detail,
            "summary": _deleted_summary,
        }
    
    except Exception as _e:
        return False, f"❌ Error: {str(_e)[:150]}", {}


# =========================================================
# 📊 GET SO SUMMARY (buat analytics)
# =========================================================
def get_so_analytics(start_date, end_date):
    """
    Ambil analytics SO: top produk minus, per kategori, dll.
    """
    try:
        _sb = get_supabase()
        _start_str = start_date.isoformat() if isinstance(start_date, date) else str(start_date)[:10]
        _end_str = end_date.isoformat() if isinstance(end_date, date) else str(end_date)[:10]
        
        _res = _sb.table("so_hasil") \
            .select("*") \
            .gte("so_date", _start_str) \
            .lte("so_date", _end_str) \
            .execute()
        
        _rows = _res.data or []
        
        if not _rows:
            return {"total_produk": 0, "top_minus": [], "top_plus": []}
        
        # Sort by qty_var (ascending = minus terbesar dulu)
        _sorted_minus = sorted(_rows, key=lambda x: int(x.get("qty_var", 0)))
        _sorted_plus = sorted(_rows, key=lambda x: int(x.get("qty_var", 0)), reverse=True)
        
        # Top 5 minus
        _top_minus = [
            {
                "plu": r.get("plu"),
                "nama_produk": r.get("nama_produk"),
                "qty_var": r.get("qty_var"),
                "nominal": r.get("nominal_adjust"),
                "rak_id": r.get("rak_id"),
                "pic": r.get("pic"),
            }
            for r in _sorted_minus[:5] if int(r.get("qty_var", 0)) < 0
        ]
        
        # Top 5 plus
        _top_plus = [
            {
                "plu": r.get("plu"),
                "nama_produk": r.get("nama_produk"),
                "qty_var": r.get("qty_var"),
                "nominal": r.get("nominal_adjust"),
                "rak_id": r.get("rak_id"),
                "pic": r.get("pic"),
            }
            for r in _sorted_plus[:5] if int(r.get("qty_var", 0)) > 0
        ]
        
        return {
            "total_produk": len(_rows),
            "top_minus": _top_minus,
            "top_plus": _top_plus,
        }
    
    except Exception as _e:
        print(f"[SO ANALYTICS ERROR] {_e}")
        return {"total_produk": 0, "top_minus": [], "top_plus": []}
