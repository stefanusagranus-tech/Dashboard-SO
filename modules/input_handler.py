"""
Input Handler
=============
Handle input harian: SPD + SO + update status rak.
"""

import streamlit as st
from datetime import datetime, date
from zoneinfo import ZoneInfo
from modules.supabase_client import get_supabase
from modules.spd_calculator import save_spd_harian


def save_input_harian(
    tanggal,
    spd,
    rak_id=None,
    items_so=None,
    keterangan="",
    update_status_rak=True,
):
    """
    Simpan input harian: SPD + SO (opsional).
    
    Args:
        tanggal: date — tanggal input
        spd: float — Sales Per Day
        rak_id: str — kode rak (opsional, kalau ada SO)
        items_so: list of dict — [{plu, item_name, qty_system, qty_actual, harga}]
        keterangan: str — catatan
        update_status_rak: bool — auto update status rak jadi SELESAI
    
    Returns:
        (success, message, detail)
    """
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase", {}
        
        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _detail = {
            "spd_saved": False,
            "so_saved": False,
            "rak_updated": False,
            "total_so_items": 0,
            "total_selisih": 0,
        }
        
        # ============================================================
        # STEP 1: SIMPAN SPD
        # ============================================================
        _ok_spd, _msg_spd = save_spd_harian(tanggal, spd, keterangan)
        if not _ok_spd:
            return False, f"❌ Gagal simpan SPD: {_msg_spd}", _detail
        _detail["spd_saved"] = True
        
        # ============================================================
        # STEP 2: SIMPAN SO (kalau ada)
        # ============================================================
        if rak_id and items_so and len(items_so) > 0:
            _tgl_str = tanggal.isoformat()[:10] if isinstance(tanggal, (date, datetime)) else str(tanggal)[:10]
            
            _rows = []
            _total_selisih = 0
            
            for _item in items_so:
                _qty_sys = int(_item.get("qty_system", 0))
                _qty_act = int(_item.get("qty_actual", 0))
                _selisih = _qty_act - _qty_sys
                _total_selisih += _selisih
                
                _rows.append({
                    "so_date": _tgl_str,
                    "rak_id": str(rak_id).upper(),
                    "plu": str(_item.get("plu", "")),
                    "item_name": str(_item.get("item_name", "")).upper(),
                    "qty_system": _qty_sys,
                    "qty_actual": _qty_act,
                    "selisih": _selisih,
                    "harga": float(_item.get("harga", 0)),
                })
            
            _res = sb.table("so_hasil").insert(_rows).execute()
            
            if _res.data:
                _detail["so_saved"] = True
                _detail["total_so_items"] = len(_rows)
                _detail["total_selisih"] = _total_selisih
            else:
                return False, "❌ Gagal simpan SO", _detail
            
            # ============================================================
            # STEP 3: UPDATE STATUS RAK → SELESAI
            # ============================================================
            if update_status_rak:
                _update_data = {
                    "status_so": "SELESAI",
                    "last_so_date": _tgl_str,
                    "updated_at": _now.isoformat(),
                }
                _res_upd = (
                    sb.table("rak_master")
                    .update(_update_data)
                    .eq("rak_id", str(rak_id).upper())
                    .execute()
                )
                if _res_upd.data:
                    _detail["rak_updated"] = True
        
        # ============================================================
        # BUILD MESSAGE
        # ============================================================
        _msg_parts = []
        if _detail["spd_saved"]:
            _msg_parts.append(f"SPD tersimpan")
        if _detail["so_saved"]:
            _msg_parts.append(f"{_detail['total_so_items']} item SO tersimpan")
        if _detail["rak_updated"]:
            _msg_parts.append(f"Rak {rak_id} → SELESAI")
        
        _msg = "✅ " + " • ".join(_msg_parts) if _msg_parts else "✅ Tersimpan"
        
        return True, _msg, _detail
    
    except Exception as e:
        return False, f"❌ Error: {str(e)[:150]}", {}


def get_spd_hari_ini():
    """Ambil SPD hari ini (kalau ada)."""
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


def get_rak_belum_so():
    """Ambil daftar rak yang belum SO (untuk dropdown)."""
    try:
        sb = get_supabase()
        if sb is None:
            return []
        
        _res = (
            sb.table("rak_master")
            .select("rak_id, rak_name")
            .eq("status_so", "BELUM")
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
    """Ambil SO hari ini (untuk preview)."""
    try:
        sb = get_supabase()
        if sb is None:
            return []
        
        _tgl = tanggal or datetime.now(ZoneInfo("Asia/Jakarta")).date()
        _tgl_str = _tgl.isoformat()[:10] if isinstance(_tgl, (date, datetime)) else str(_tgl)[:10]
        
        _res = (
            sb.table("so_hasil")
            .select("*")
            .eq("so_date", _tgl_str)
            .order("rak_id")
            .execute()
        )
        
        return _res.data if _res.data else []
    except Exception as e:
        print(f"[GET_SO_TODAY ERROR] {e}")
        return []
