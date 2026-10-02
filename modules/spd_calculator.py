"""
SPD Calculator
==============
Hitung BTSB berdasarkan SPD (Sales Per Day).

Konsep:
- BTSB Harian = 0,15% × SPD hari ini
- BTSB Akumulatif = 0,15% × Total SPD (tanggal 1 s/d hari ini)
"""

import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from modules.supabase_client import get_supabase


# =========================================================================
# 📥 LOAD SPD HARIAN
# =========================================================================
def load_spd_harian(bulan=None, tahun=None):
    """
    Load data SPD harian.
    
    Args:
        bulan: 1-12 (default: bulan ini)
        tahun: 2026 (default: tahun ini)
    
    Returns:
        DataFrame dengan kolom: id, tanggal, spd, keterangan
    """
    try:
        sb = get_supabase()
        if sb is None:
            return pd.DataFrame(columns=["tanggal", "spd", "keterangan"])
        
        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _bulan = bulan if bulan else _now.month
        _tahun = tahun if tahun else _now.year
        
        # Range tanggal
        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - timedelta(days=1)
        
        _res = (
            sb.table("spd_harian")
            .select("*")
            .gte("tanggal", _start.isoformat())
            .lte("tanggal", _end.isoformat())
            .order("tanggal")
            .execute()
        )
        
        if not _res.data:
            return pd.DataFrame(columns=["tanggal", "spd", "keterangan"])
        
        df = pd.DataFrame(_res.data)
        df.columns = df.columns.astype(str).str.strip().str.lower()
        df["spd"] = pd.to_numeric(df["spd"], errors="coerce").fillna(0)
        df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce").dt.date
        
        return df
    
    except Exception as e:
        print(f"[LOAD_SPD ERROR] {e}")
        return pd.DataFrame(columns=["tanggal", "spd", "keterangan"])


# =========================================================================
# 📝 SAVE SPD HARIAN (Upsert)
# =========================================================================
def save_spd_harian(tanggal, spd, keterangan=""):
    """
    Simpan / update SPD harian.
    
    Args:
        tanggal: date atau string "YYYY-MM-DD"
        spd: nilai SPD (int/float)
        keterangan: catatan opsional
    """
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase"
        
        # Konversi tanggal ke string ISO
        if isinstance(tanggal, (date, datetime)):
            _tgl_str = tanggal.isoformat()[:10]
        else:
            _tgl_str = str(tanggal)[:10]
        
        _data = {
            "tanggal": _tgl_str,
            "spd": float(spd),
            "keterangan": str(keterangan),
            "updated_at": datetime.now(ZoneInfo("Asia/Jakarta")).isoformat(),
        }
        
        # Upsert (insert/update berdasarkan tanggal)
        _res = sb.table("spd_harian").upsert(_data, on_conflict="tanggal").execute()
        
        if _res.data:
            return True, f"✅ SPD {_tgl_str} tersimpan"
        else:
            return False, "❌ Gagal simpan"
    
    except Exception as e:
        return False, f"❌ Gagal: {str(e)[:150]}"


# =========================================================================
# 🧮 HITUNG BTSB BERDASARKAN SPD
# =========================================================================
def hitung_btsb_harian(spd, persen=0.15):
    """
    Hitung BTSB Harian = persen% × SPD.
    
    Args:
        spd: SPD hari ini
        persen: persentase BTSB (default 0,15%)
    
    Returns:
        float: nilai BTSB harian
    """
    try:
        return float(spd) * (persen / 100)
    except Exception:
        return 0.0


def hitung_btsb_akumulatif(bulan=None, tahun=None, persen=0.15):
    """
    Hitung BTSB Akumulatif = persen% × Total SPD bulan ini.
    
    Returns:
        dict {
            total_spd: float,
            btsb_akumulatif: float,
            jumlah_hari: int,
            spd_harian: DataFrame,
        }
    """
    try:
        df = load_spd_harian(bulan, tahun)
        
        if df.empty:
            return {
                "total_spd": 0,
                "btsb_akumulatif": 0,
                "jumlah_hari": 0,
                "spd_harian": df,
            }
        
        total_spd = float(df["spd"].sum())
        btsb_akumulatif = total_spd * (persen / 100)
        jumlah_hari = len(df)
        
        return {
            "total_spd": total_spd,
            "btsb_akumulatif": btsb_akumulatif,
            "jumlah_hari": jumlah_hari,
            "spd_harian": df,
        }
    
    except Exception as e:
        print(f"[HITUNG_BTSB_ERROR] {e}")
        return {
            "total_spd": 0,
            "btsb_akumulatif": 0,
            "jumlah_hari": 0,
            "spd_harian": pd.DataFrame(),
        }


# =========================================================================
# 📊 ANALISIS STATUS BTSB vs SELISIH
# =========================================================================
def analisis_btsb_vs_selisih(total_selisih, btsb):
    """
    Bandingkan total selisih SO dengan BTSB.
    
    Args:
        total_selisih: total selisih dari SO (bisa +/-)
        btsb: nilai BTSB (harian/akumulatif)
    
    Returns:
        dict {
            total_selisih, btsb, gap, persen_penggunaan,
            status, warna, icon
        }
    """
    try:
        _selisih_abs = abs(float(total_selisih))
        _btsb = float(btsb)
        
        _gap = _btsb - _selisih_abs
        _persen = (_selisih_abs / _btsb * 100) if _btsb > 0 else 0
        
        if _persen <= 100:
            _status = "AMAN"
            _warna = "#34d399"
            _icon = "🟢"
        elif _persen <= 150:
            _status = "WARNING"
            _warna = "#fbbf24"
            _icon = "🟡"
        else:
            _status = "OVER"
            _warna = "#fca5a5"
            _icon = "🔴"
        
        return {
            "total_selisih": float(total_selisih),
            "btsb": _btsb,
            "gap": _gap,
            "persen_penggunaan": round(_persen, 2),
            "status": _status,
            "warna": _warna,
            "icon": _icon,
        }
    
    except Exception as e:
        print(f"[ANALISIS_BTSB ERROR] {e}")
        return {
            "total_selisih": 0,
            "btsb": 0,
            "gap": 0,
            "persen_penggunaan": 0,
            "status": "N/A",
            "warna": "#64748b",
            "icon": "⚪",
        }


# =========================================================================
# 📅 HELPER: SPD HARI INI
# =========================================================================
def get_spd_hari_ini():
    """Ambil SPD hari ini (kalau ada)."""
    try:
        _today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
        df = load_spd_harian()
        
        if df.empty:
            return 0
        
        _match = df[df["tanggal"] == _today]
        if _match.empty:
            return 0
        
        return int(_match.iloc[0]["spd"])
    
    except Exception as e:
        print(f"[GET_SPD_TODAY ERROR] {e}")
        return 0


# =========================================================================
# 📊 HELPER: TOTAL SPD BULAN INI
# =========================================================================
def get_total_spd_bulan_ini():
    """Ambil total SPD bulan ini."""
    try:
        result = hitung_btsb_akumulatif()
        return int(result["total_spd"])
    except Exception as e:
        print(f"[GET_TOTAL_SPD ERROR] {e}")
        return 0
