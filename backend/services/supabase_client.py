"""
Supabase Client
===============
Koneksi ke Supabase (PostgreSQL) untuk Dashboard SO.
"""

import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo


@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """
    Bikin koneksi Supabase (cached).
    Baca dari st.secrets["supabase"].
    """
    try:
        _url = st.secrets["supabase"]["url"]
        _key = st.secrets["supabase"]["key"]
        return create_client(_url, _key)
    except Exception as e:
        print(f"[SUPABASE CONN ERROR] {e}")
        return None


# =========================================================================
# 📥 READ FUNCTIONS
# =========================================================================
def load_rak_master():
    """Load semua rak dari Supabase."""
    try:
        sb = get_supabase()
        if sb is None:
            return pd.DataFrame()
        
        _res = sb.table("rak_master").select("*").order("rak_id").execute()
        
        if not _res.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(_res.data)
        return df
    except Exception as e:
        print(f"[LOAD_RAK ERROR] {e}")
        return pd.DataFrame()


def load_so_hasil():
    """Load semua hasil SO dari Supabase."""
    try:
        sb = get_supabase()
        if sb is None:
            return pd.DataFrame()
        
        _res = sb.table("so_hasil").select("*").order("so_date", desc=True).execute()
        
        if not _res.data:
            return pd.DataFrame()
        
        return pd.DataFrame(_res.data)
    except Exception as e:
        print(f"[LOAD_SO ERROR] {e}")
        return pd.DataFrame()


def load_net_sales():
    """Load net sales dari Supabase."""
    try:
        sb = get_supabase()
        if sb is None:
            return pd.DataFrame()
        
        _res = sb.table("net_sales").select("*").order("tahun", desc=True).order("bulan", desc=True).execute()
        
        if not _res.data:
            return pd.DataFrame()
        
        return pd.DataFrame(_res.data)
    except Exception as e:
        print(f"[LOAD_NET_SALES ERROR] {e}")
        return pd.DataFrame()


# =========================================================================
# 📝 WRITE FUNCTIONS
# =========================================================================
def update_status_rak(rak_id: str, status: str, pic: str = None):
    """
    Update status SO rak.
    
    Args:
        rak_id: Kode rak
        status: "BELUM" / "SELESAI"
        pic: Nama PIC (opsional)
    """
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase"
        
        _update_data = {
            "status_so": status.upper(),
            "updated_at": datetime.now(ZoneInfo("Asia/Jakarta")).isoformat(),
        }
        
        if status.upper() == "SELESAI":
            _update_data["last_so_date"] = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
        
        if pic:
            _update_data["pic"] = pic.upper()
        
        _res = sb.table("rak_master").update(_update_data).eq("rak_id", rak_id).execute()
        
        if _res.data:
            return True, f"✅ Status rak {rak_id} diupdate"
        else:
            return False, f"❌ Rak {rak_id} tidak ditemukan"
    except Exception as e:
        return False, f"❌ Gagal: {str(e)[:150]}"


def insert_so_hasil(rak_id: str, plu: str, nama_produk: str,
                    qty_sistem: int, qty_fisik: int, nominal_adjust: float,
                    pic: str = "", so_date: str = None):
    """
    Insert 1 baris hasil SO (schema baru 11 kolom).
    
    Args:
        rak_id: Kode rak
        plu: Kode PLU produk
        nama_produk: Nama produk
        qty_sistem: Stok di sistem
        qty_fisik: Stok fisik hasil hitung
        nominal_adjust: Nominal selisih (boleh +/-)
        pic: Nama PIC
        so_date: Tanggal SO (default: hari ini)
    """
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase"
        
        if so_date is None:
            so_date = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
        
        # ✅ Hitung qty_var otomatis
        _qty_var = int(qty_fisik) - int(qty_sistem)
        
        _data = {
            "so_date": so_date,
            "rak_id": rak_id.upper(),
            "plu": str(plu),
            "nama_produk": nama_produk.upper(),
            "qty_sistem": int(qty_sistem),
            "qty_fisik": int(qty_fisik),
            "qty_var": _qty_var,
            "nominal_adjust": float(nominal_adjust),
            "pic": str(pic).upper(),
        }
        
        _res = sb.table("so_hasil").insert(_data).execute()
        
        if _res.data:
            return True, f"✅ SO hasil disimpan (var: {_qty_var})"
        else:
            return False, "❌ Gagal insert"
    except Exception as e:
        return False, f"❌ Gagal: {str(e)[:150]}"


def insert_bulk_so_hasil(rows: list):
    """Insert banyak baris SO sekaligus."""
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase"
        
        if not rows:
            return False, "❌ Data kosong"
        
        _res = sb.table("so_hasil").insert(rows).execute()
        
        if _res.data:
            return True, f"✅ {len(_res.data)} baris tersimpan"
        else:
            return False, "❌ Gagal insert bulk"
    except Exception as e:
        return False, f"❌ Gagal: {str(e)[:150]}"


def upsert_net_sales(bulan: int, tahun: int, net_sales: float):
    """Insert/update net sales."""
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase"
        
        _data = {
            "bulan": int(bulan),
            "tahun": int(tahun),
            "net_sales": float(net_sales),
        }
        
        _res = sb.table("net_sales").upsert(_data, on_conflict="bulan,tahun").execute()
        
        if _res.data:
            return True, f"✅ Net sales {bulan}/{tahun} disimpan"
        else:
            return False, "❌ Gagal upsert"
    except Exception as e:
        return False, f"❌ Gagal: {str(e)[:150]}"


# =========================================================================
# 📊 AGGREGATE / ANALYTICS
# =========================================================================
def get_progress_summary():
    """Ambil ringkasan progres SO langsung dari Supabase."""
    try:
        sb = get_supabase()
        if sb is None:
            return {}
        
        # Total rak
        _total = sb.table("rak_master").select("rak_id", count="exact").execute()
        _total_count = _total.count or 0
        
        # Rak selesai
        _selesai = sb.table("rak_master").select("rak_id", count="exact").eq("status_so", "SELESAI").execute()
        _selesai_count = _selesai.count or 0
        
        _belum_count = _total_count - _selesai_count
        _persen = (_selesai_count / _total_count * 100) if _total_count > 0 else 0
        
        return {
            "total_rak": _total_count,
            "rak_selesai": _selesai_count,
            "rak_belum": _belum_count,
            "persen_selesai": round(_persen, 2),
        }
    except Exception as e:
        print(f"[PROGRESS SUMMARY ERROR] {e}")
        return {}
