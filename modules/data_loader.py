"""
Data Loader
===========
Load data dari Supabase (PostgreSQL) untuk Dashboard Stock Opname.

Semua fungsi read-only — untuk write/update, lihat modules/supabase_client.py
"""

import streamlit as st
import pandas as pd
from modules.supabase_client import get_supabase


# =========================================================================
# 📥 LOAD RAK MASTER
# =========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def load_rak_master():
    """
    Load semua rak dari Supabase.
    
    Returns:
        DataFrame dengan kolom:
        id, rak_id, rak_name, kategori, pic, nominal_adjust,
        catatan, status_so, last_so_date, created_at, updated_at
    """
    try:
        sb = get_supabase()
        if sb is None:
            print("[LOAD_RAK] ❌ Supabase client None")
            return pd.DataFrame()
        
        # Query ke tabel rak_master
        _res = sb.table("rak_master").select("*").order("rak_id").execute()
        
        if not _res.data:
            print("[LOAD_RAK] ⚠️ Data kosong")
            return pd.DataFrame()
        
        df = pd.DataFrame(_res.data)
        
        # Normalisasi kolom
        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        # Pastikan kolom wajib ada
        _required = [
            "rak_id", "rak_name", "kategori", "pic",
            "nominal_adjust", "catatan", "status_so", "last_so_date"
        ]
        for _col in _required:
            if _col not in df.columns:
                df[_col] = ""
        
        # Normalisasi tipe data
        df["rak_id"] = df["rak_id"].astype(str).str.strip().str.upper()
        df["rak_name"] = df["rak_name"].astype(str).str.strip()
        df["kategori"] = df["kategori"].astype(str).str.strip().str.upper().replace("NAN", "FOOD")
        df["pic"] = df["pic"].fillna("").astype(str).str.strip().str.upper()
        df["catatan"] = df["catatan"].fillna("").astype(str).str.strip()
        df["status_so"] = df["status_so"].fillna("BELUM").astype(str).str.strip().str.upper()
        df["nominal_adjust"] = pd.to_numeric(df["nominal_adjust"], errors="coerce").fillna(0)
        
        print(f"[LOAD_RAK] ✅ {len(df)} rak dimuat")
        return df
    
    except Exception as e:
        print(f"[LOAD_RAK ERROR] {e}")
        return pd.DataFrame()


# =========================================================================
# 📥 LOAD SO HASIL
# =========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def load_so_hasil():
    """
    Load semua hasil SO dari Supabase.
    
    Returns:
        DataFrame dengan kolom:
        id, so_date, rak_id, plu, item_name,
        qty_system, qty_actual, selisih, harga, created_at
    """
    try:
        sb = get_supabase()
        if sb is None:
            print("[LOAD_SO] ❌ Supabase client None")
            return pd.DataFrame(columns=[
                "so_date", "rak_id", "plu", "item_name",
                "qty_system", "qty_actual", "selisih", "harga"
            ])
        
        # Query ke tabel so_hasil, urut tanggal terbaru
        _res = (
            sb.table("so_hasil")
            .select("*")
            .order("so_date", desc=True)
            .limit(10000)
            .execute()
        )
        
        if not _res.data:
            print("[LOAD_SO] ⚠️ Data kosong")
            return pd.DataFrame(columns=[
                "so_date", "rak_id", "plu", "item_name",
                "qty_system", "qty_actual", "selisih", "harga"
            ])
        
        df = pd.DataFrame(_res.data)
        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        # Normalisasi
        if "rak_id" in df.columns:
            df["rak_id"] = df["rak_id"].astype(str).str.strip().str.upper()
        
        for _col in ["qty_system", "qty_actual", "selisih", "harga"]:
            if _col in df.columns:
                df[_col] = pd.to_numeric(df[_col], errors="coerce").fillna(0)
            else:
                df[_col] = 0
        
        print(f"[LOAD_SO] ✅ {len(df)} baris SO dimuat")
        return df
    
    except Exception as e:
        print(f"[LOAD_SO ERROR] {e}")
        return pd.DataFrame(columns=[
            "so_date", "rak_id", "plu", "item_name",
            "qty_system", "qty_actual", "selisih", "harga"
        ])


# =========================================================================
# 📥 LOAD NET SALES
# =========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def load_net_sales():
    """
    Load data net sales dari Supabase.
    
    Returns:
        DataFrame dengan kolom: id, bulan, tahun, net_sales
    """
    try:
        sb = get_supabase()
        if sb is None:
            print("[LOAD_NS] ❌ Supabase client None")
            return pd.DataFrame(columns=["bulan", "tahun", "net_sales"])
        
        _res = (
            sb.table("net_sales")
            .select("*")
            .order("tahun", desc=True)
            .order("bulan", desc=True)
            .execute()
        )
        
        if not _res.data:
            print("[LOAD_NS] ⚠️ Data kosong")
            return pd.DataFrame(columns=["bulan", "tahun", "net_sales"])
        
        df = pd.DataFrame(_res.data)
        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        # Normalisasi
        if "net_sales" in df.columns:
            df["net_sales"] = pd.to_numeric(df["net_sales"], errors="coerce").fillna(0)
        
        if "bulan" in df.columns:
            df["bulan"] = pd.to_numeric(df["bulan"], errors="coerce").fillna(0).astype(int)
        
        if "tahun" in df.columns:
            df["tahun"] = pd.to_numeric(df["tahun"], errors="coerce").fillna(0).astype(int)
        
        print(f"[LOAD_NS] ✅ {len(df)} baris net sales dimuat")
        return df
    
    except Exception as e:
        print(f"[LOAD_NS ERROR] {e}")
        return pd.DataFrame(columns=["bulan", "tahun", "net_sales"])


# =========================================================================
# 🔍 HELPER: GET NET SALES BULAN INI
# =========================================================================
def get_net_sales_bulan_ini(bulan=None, tahun=None):
    """
    Ambil net sales bulan ini.
    
    Args:
        bulan: 1-12 (default: bulan sekarang)
        tahun: 2026 dst (default: tahun sekarang)
    
    Returns:
        int: Nilai net sales, atau 0 kalau tidak ada
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    try:
        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _bulan = bulan if bulan else _now.month
        _tahun = tahun if tahun else _now.year
        
        df = load_net_sales()
        if df.empty:
            return 0
        
        _match = df[(df["bulan"] == _bulan) & (df["tahun"] == _tahun)]
        if _match.empty:
            return 0
        
        return int(_match.iloc[0]["net_sales"])
    
    except Exception as e:
        print(f"[GET_NS ERROR] {e}")
        return 0


# =========================================================================
# 🔍 HELPER: GET RAK BY ID
# =========================================================================
def get_rak_by_id(rak_id):
    """
    Ambil 1 rak berdasarkan rak_id.
    
    Returns:
        dict atau None
    """
    try:
        df = load_rak_master()
        if df.empty:
            return None
        
        _match = df[df["rak_id"].str.upper() == str(rak_id).upper()]
        if _match.empty:
            return None
        
        return _match.iloc[0].to_dict()
    
    except Exception as e:
        print(f"[GET_RAK ERROR] {e}")
        return None


# =========================================================================
# 🔍 HELPER: LIST KATEGORI UNIK
# =========================================================================
def get_list_kategori():
    """Ambil daftar kategori unik dari rak_master."""
    try:
        df = load_rak_master()
        if df.empty:
            return []
        
        return sorted(df["kategori"].dropna().unique().tolist())
    
    except Exception as e:
        print(f"[GET_KATEGORI ERROR] {e}")
        return []


# =========================================================================
# 🔍 HELPER: LIST PIC UNIK
# =========================================================================
def get_list_pic():
    """Ambil daftar PIC unik dari rak_master."""
    try:
        df = load_rak_master()
        if df.empty:
            return []
        
        _pic = df[df["pic"] != ""]["pic"].dropna().unique().tolist()
        return sorted(_pic)
    
    except Exception as e:
        print(f"[GET_PIC ERROR] {e}")
        return []


# =========================================================================
# 🔄 CLEAR CACHE (untuk refresh manual)
# =========================================================================
def clear_cache():
    """Clear semua cache data loader."""
    try:
        load_rak_master.clear()
        load_so_hasil.clear()
        load_net_sales.clear()
        print("[CACHE] ✅ Cache dibersihkan")
    except Exception as e:
        print(f"[CACHE ERROR] {e}")
