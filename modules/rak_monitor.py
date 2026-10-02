"""
Rak Monitor
===========
Logic monitoring progres SO per rak.
"""

import pandas as pd


def hitung_progress_so(rak_master, so_hasil):
    """
    Hitung progres SO.
    
    Returns:
        dict {
            total_rak, rak_selesai, rak_belum,
            persen_selesai, list_rak_belum
        }
    """
    try:
        if rak_master is None or rak_master.empty:
            return {
                "total_rak": 0,
                "rak_selesai": 0,
                "rak_belum": 0,
                "persen_selesai": 0.0,
                "list_rak_belum": [],
            }
        
        total_rak = len(rak_master)
        
        # Rak yang sudah SO
        _selesai = rak_master[
            rak_master["status_so"].astype(str).str.upper() == "SELESAI"
        ]
        rak_selesai = len(_selesai)
        rak_belum = total_rak - rak_selesai
        
        # Persentase
        persen_selesai = (rak_selesai / total_rak * 100) if total_rak > 0 else 0
        
        # List rak belum
        _belum = rak_master[
            rak_master["status_so"].astype(str).str.upper() == "BELUM"
        ]
        list_rak_belum = _belum["rak_id"].tolist() if "rak_id" in _belum.columns else []
        
        return {
            "total_rak": total_rak,
            "rak_selesai": rak_selesai,
            "rak_belum": rak_belum,
            "persen_selesai": round(persen_selesai, 2),
            "list_rak_belum": list_rak_belum,
        }
    
    except Exception as e:
        print(f"[HITUNG_PROGRESS ERROR] {e}")
        return {
            "total_rak": 0,
            "rak_selesai": 0,
            "rak_belum": 0,
            "persen_selesai": 0.0,
            "list_rak_belum": [],
        }


def get_rak_belum_so(rak_master):
    """Ambil daftar rak yang BELUM di-SO."""
    if rak_master is None or rak_master.empty:
        return pd.DataFrame()
    return rak_master[
        rak_master["status_so"].astype(str).str.upper() == "BELUM"
    ].copy()


def get_rak_selesai_so(rak_master):
    """Ambil daftar rak yang SUDAH di-SO."""
    if rak_master is None or rak_master.empty:
        return pd.DataFrame()
    return rak_master[
        rak_master["status_so"].astype(str).str.upper() == "SELESAI"
    ].copy()


def status_pencapaian(persen_selesai, target=80):
    """
    Cek status pencapaian.
    
    Returns:
        str: "✅ TERCAPAI" / "⚠️ MENDEKATI" / "🔴 BELUM"
    """
    if persen_selesai >= target:
        return "✅ TERCAPAI"
    elif persen_selesai >= target * 0.8:
        return "⚠️ MENDEKATI"
    else:
        return "🔴 BELUM"
