"""
SPD Calculator — Backend Version
=================================
Hitung BTSB berdasarkan SPD (Sales Per Day).
"""

import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from services.supabase_client import get_supabase


def load_spd_harian(bulan=None, tahun=None):
    """Load data SPD harian."""
    try:
        sb = get_supabase()
        if sb is None:
            return pd.DataFrame(columns=["tanggal", "spd", "keterangan"])

        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _bulan = bulan if bulan else _now.month
        _tahun = tahun if tahun else _now.year

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


def save_spd_harian(tanggal, spd, keterangan=""):
    """Simpan / update SPD harian."""
    try:
        sb = get_supabase()
        if sb is None:
            return False, "❌ Gagal koneksi Supabase"

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

        _res = sb.table("spd_harian").upsert(_data, on_conflict="tanggal").execute()

        if _res.data:
            return True, f"✅ SPD {_tgl_str} tersimpan"
        else:
            return False, "❌ Gagal simpan"

    except Exception as e:
        return False, f"❌ Gagal: {str(e)[:150]}"


def hitung_btsb_harian(spd, persen=0.15):
    """Hitung BTSB Harian = persen% × SPD."""
    try:
        return float(spd) * (persen / 100)
    except Exception:
        return 0.0


def hitung_btsb_akumulatif(bulan=None, tahun=None, persen=0.15):
    """Hitung BTSB Akumulatif."""
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


def get_spd_hari_ini():
    """Ambil SPD hari ini."""
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


def get_total_spd_bulan_ini():
    """Ambil total SPD bulan ini."""
    try:
        result = hitung_btsb_akumulatif()
        return int(result["total_spd"])
    except Exception as e:
        print(f"[GET_TOTAL_SPD ERROR] {e}")
        return 0