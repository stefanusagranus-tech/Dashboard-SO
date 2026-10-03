"""
OCR Handler v9
==============
Handle OCR screenshot kalender shift web absen.

Perubahan v9:
- Palette warna ASLI dari CSV debug
- Grid detection merge (fix kolom ke-split)
- Auto-detect kalender area lebih fleksibel
- Debug print detail
"""

import io
import re
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError as e:
    print(f"[OCR] Library gak tersedia: {e}")
    TESSERACT_AVAILABLE = False


# =========================================================
# 🎨 COLOR PALETTE v9 — WARNA ASLI DARI CSV DEBUG
# =========================================================
COLOR_PALETTE = {
    # Dini Hari (Kuning)
    "D": {
        "label": "Dini Hari",
        "rgb": (230, 230, 100),
        "hex": "#E6E664",
        "tolerance": 80,
        "huruf": ["D"],
    },
    # Hari Pendek (Kuning)
    "HP": {
        "label": "Hari Pendek",
        "rgb": (230, 230, 100),
        "hex": "#E6E664",
        "tolerance": 80,
        "huruf": ["HP", "H"],
    },
    # Pagi (Hijau)
    "P": {
        "label": "Pagi",
        "rgb": (60, 220, 200),
        "hex": "#3CDCC8",
        "tolerance": 100,
        "huruf": ["P"],
    },
    # ✅ Siang — WARNA ASLI: RGB(0, 255, 173)
    "S": {
        "label": "Siang",
        "rgb": (0, 255, 173),
        "hex": "#00FFAD",
        "tolerance": 80,
        "huruf": ["S"],
    },
    # ✅ Malam — WARNA ASLI: RGB(100, 133, 255)
    "M": {
        "label": "Malam",
        "rgb": (100, 133, 255),
        "hex": "#6485FF",
        "tolerance": 80,
        "huruf": ["M"],
    },
    # ✅ Off — WARNA ASLI: RGB(13, 13, 13)
    "O": {
        "label": "Off",
        "rgb": (13, 13, 13),
        "hex": "#0D0D0D",
        "tolerance": 40,
        "huruf": ["O"],
    },
    "C": {
        "label": "Cuti",
        "rgb": (13, 13, 13),
        "hex": "#0D0D0D",
        "tolerance": 40,
        "huruf": ["C"],
    },
    "I": {
        "label": "Izin",
        "rgb": (13, 13, 13),
        "hex": "#0D0D0D",
        "tolerance": 40,
        "huruf": ["I"],
    },
    "SK": {
        "label": "Sakit",
        "rgb": (13, 13, 13),
        "hex": "#0D0D0D",
        "tolerance": 40,
        "huruf": ["SK"],
    },
    "AO": {
        "label": "Additional Off",
        "rgb": (13, 13, 13),
        "hex": "#0D0D0D",
        "tolerance": 40,
        "huruf": ["AO", "A"],
    },
    "EO": {
        "label": "Extra Off",
        "rgb": (13, 13, 13),
        "hex": "#0D0D0D",
        "tolerance": 40,
        "huruf": ["EO", "E"],
    },
    "RO": {
        "label": "Replace Off",
        "rgb": (13, 13, 13),
        "hex": "#0D0D0D",
        "tolerance": 40,
        "huruf": ["RO", "R"],
    },
    # Libur (Merah muda)
    "L": {
        "label": "Libur",
        "rgb": (250, 150, 150),
        "hex": "#FA9696",
        "tolerance": 80,
        "huruf": ["L"],
    },
    # Long Shift (Ungu)
    "LO": {
        "label": "Long Shift",
        "rgb": (150, 50, 200),
        "hex": "#9632C8",
        "tolerance": 80,
        "huruf": ["LO"],
    },
}


# =========================================================
# 🎨 DETEKSI WARNA → KODE
# =========================================================
def _rgb_to_kode_v2(r, g, b):
    """Deteksi kode shift dari warna RGB."""
    # Skip putih
    if r > 240 and g > 240 and b > 240:
        return None, 0, 999999
    
    # Skip abu netral
    _max_c = max(r, g, b)
    _min_c = min(r, g, b)
    if (_max_c - _min_c) < 15 and r > 150:
        return None, 0, 999999
    
    _best_match = None
    _best_distance = 999999
    
    for _kode, _info in COLOR_PALETTE.items():
        _pal_r, _pal_g, _pal_b = _info["rgb"]
        
        _distance = (
            (r - _pal_r) ** 2 +
            (g - _pal_g) ** 2 +
            (b - _pal_b) ** 2
        ) ** 0.5
        
        if _distance < _best_distance:
            _best_distance = _distance
            _best_match = _kode
    
    if _best_match:
        _tol = COLOR_PALETTE[_best_match]["tolerance"]
        if _best_distance <= _tol:
            _confidence = max(0, 100 - int((_best_distance / _tol) * 50))
            return _best_match, _confidence, _best_distance
    
    return None, 0, _best_distance


# =========================================================
# 🔤 DETEKSI HURUF AWAL → KODE
# =========================================================
def _huruf_to_kode(text):
    """Deteksi kode dari huruf awal text."""
    if not text:
        return None, 0
    
    _text_upper = str(text).upper().strip()
    _text_upper = re.sub(r'[^A-Z0-9]', '', _text_upper)
    
    if not _text_upper:
        return None, 0
    
    for _kode, _info in COLOR_PALETTE.items():
        for _huruf in _info["huruf"]:
            _huruf_upper = _huruf.upper()
            
            if _text_upper == _huruf_upper:
                return _kode, 100
            if _text_upper.startswith(_huruf_upper):
                return _kode, 90
    
    _first_2 = _text_upper[:2]
    _first_1 = _text_upper[:1]
    
    for _kode, _info in COLOR_PALETTE.items():
        for _huruf in _info["huruf"]:
            _h_up = _huruf.upper()
            if len(_h_up) == 2 and _first_2 == _h_up:
                return _kode, 85
            if len(_h_up) == 1 and _first_1 == _h_up:
                return _kode, 70
    
    return None, 0


# === BAGIAN 2 MULAI ===

# =========================================================
# 🔍 OCR UTAMA — v9 (Auto-detect Grid + Merge)
# =========================================================
def ocr_kalender_screenshot(image_bytes):
    """
    OCR screenshot v11 — Skip header, cari kalender dari warna solid.
    """
    if not TESSERACT_AVAILABLE:
        return {"success": False, "tanggal_list": [], "raw_text": "", "error": "Tesseract tidak tersedia"}
    
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        print(f"[OCR v11] Image: {_w}x{_h}")
        
        _text_full = pytesseract.image_to_string(_img, config="--psm 6")
        
        _np_img = np.array(_img)
        _grayscale = np.mean(_np_img, axis=2)
        
        # ============================================
        # 1. CARI AREA KALENDER: ABAIKAN HEADER PUTIH
        # ============================================
        # Baris dianggap "warna kalender" kalau:
        # - Ada warna SOLID (bukan putih) di 30-80% area (khas kalender grid)
        # - BUKAN baris full warna (khas header merah)
        
        _is_white = _grayscale > 240
        _colored_pct = 1 - np.mean(_is_white, axis=1)
        
        # Kalender: colored_pct antara 0.3-0.85 (warna sedang)
        # Header: colored_pct > 0.85 (warna full)
        # Info: colored_pct < 0.3 (putih semua)
        
        _kalender_mask = (_colored_pct > 0.25) & (_colored_pct < 0.80)
        
        print(f"[OCR v11] Baris berwarna sedang: {np.sum(_kalender_mask)}")
        
        # Cari KELOMPOK baris berwarna sedang (minimal 100 baris berturut-turut)
        _kalender_rows = np.where(_kalender_mask)[0]
        
        if len(_kalender_rows) < 20:
            print(f"[OCR v11] ERROR: gak cukup baris kalender")
            return {"success": False, "tanggal_list": [], "raw_text": _text_full, "error": "Kalender gak ke-detect"}
        
        # Cari cluster terbesar
        _clusters = []
        _cluster_start = _kalender_rows[0]
        _prev = _kalender_rows[0]
        
        for _r in _kalender_rows[1:]:
            if _r - _prev > 15:  # gap 15px → cluster baru
                _clusters.append((_cluster_start, _prev))
                _cluster_start = _r
            _prev = _r
        _clusters.append((_cluster_start, _prev))
        
        # Ambil cluster terbesar
        _clusters = sorted(_clusters, key=lambda x: x[1]-x[0], reverse=True)
        _kalender_start, _kalender_end = _clusters[0]
        
        print(f"[OCR v11] Kalender area: y={_kalender_start}-{_kalender_end} (h={_kalender_end - _kalender_start})")
        
        # ============================================
        # 2. AUTO-DETECT JUMLAH BARIS KALENDER
        # ============================================
        # Cari "dip" (jarak antar baris kalender) untuk deteksi jumlah baris
        _row_density_region = _colored_pct[_kalender_start:_kalender_end]
        
        # Smooth
        _kernel = np.ones(10) / 10
        _row_density_smooth = np.convolve(_row_density_region, _kernel, mode='same')
        
        # Cari gap (density < 0.2) → pemisah antar baris
        _gap_rows = np.where(_row_density_smooth < 0.15)[0]
        
        # Hitung jumlah baris kalender
        if len(_gap_rows) > 0:
            _gaps_grouped = []
            _gap_start = _gap_rows[0]
            _prev_gap = _gap_rows[0]
            for _g in _gap_rows[1:]:
                if _g - _prev_gap > 10:
                    _gaps_grouped.append((_gap_start, _prev_gap))
                    _gap_start = _g
                _prev_gap = _g
            _gaps_grouped.append((_gap_start, _prev_gap))
            
            _grid_rows = min(len(_gaps_grouped) + 1, 6)
        else:
            _grid_rows = 5
        
        # Kalau kurang dari 4, fallback
        if _grid_rows < 4:
            _grid_rows = 5
        
        _grid_cols = 7
        
        print(f"[OCR v11] Grid: {_grid_cols}×{_grid_rows}")
        
        _kalender_h = _kalender_end - _kalender_start
        _cell_w = _w // _grid_cols
        _cell_h = _kalender_h // _grid_rows
        
        # ============================================
        # 3. ANALISIS PER CELL
        # ============================================
        _tanggal_list = []
        _debug_info = []
        
        for _r_idx in range(_grid_rows):
            for _c_idx in range(_grid_cols):
                _y1 = _kalender_start + _r_idx * _cell_h
                _y2 = _y1 + _cell_h
                _x1 = _c_idx * _cell_w
                _x2 = _x1 + _cell_w
                
                _cell_img = _img.crop((_x1, _y1, _x2, _y2))
                _cell_np = np.array(_cell_img)
                
                if _cell_np.size == 0:
                    continue
                
                # Cek warna dominant
                _flat = _cell_np.reshape(-1, 3)
                # Skip pixel putih
                _non_white = _flat[~((_flat[:, 0] > 240) & (_flat[:, 1] > 240) & (_flat[:, 2] > 240))]
                
                if len(_non_white) == 0:
                    continue
                
                _r_val = int(np.median(_non_white[:, 0]))
                _g_val = int(np.median(_non_white[:, 1]))
                _b_val = int(np.median(_non_white[:, 2]))
                
                _kode_warna, _conf_warna, _dist = _rgb_to_kode_v2(_r_val, _g_val, _b_val)
                
                # OCR text
                _kode_huruf = None
                _text_cell = ""
                try:
                    _text_cell = pytesseract.image_to_string(_cell_img, config="--psm 7").strip()
                    if _text_cell:
                        _kode_huruf, _conf_huruf = _huruf_to_kode(_text_cell)
                except Exception:
                    pass
                
                # Voting
                _kode_final = None
                _confidence = "LOW"
                _sumber = ""
                
                if _kode_warna:
                    _kode_final = _kode_warna
                    _confidence = "HIGH" if _conf_warna > 70 else "MEDIUM"
                    _sumber = "warna"
                    if _kode_huruf and _kode_huruf == _kode_warna:
                        _confidence = "HIGH"
                        _sumber = "huruf+warna"
                elif _kode_huruf:
                    _kode_final = _kode_huruf
                    _confidence = "MEDIUM"
                    _sumber = "huruf"
                
                _debug_info.append({
                    "row": _r_idx,
                    "col": _c_idx,
                    "x": f"{_x1},{_x2}",
                    "y": f"{_y1},{_y2}",
                    "text_cell": _text_cell[:20],
                    "kode_huruf": _kode_huruf,
                    "kode_warna": _kode_warna,
                    "rgb": f"{_r_val},{_g_val},{_b_val}",
                    "final": _kode_final,
                })
                
                if _kode_final:
                    _tanggal_list.append({
                        "row": _r_idx,
                        "col": _c_idx,
                        "kode": _kode_final,
                        "confidence": _confidence,
                        "sumber": _sumber,
                    })
        
        print(f"[OCR v11] Cells analyzed: {len(_debug_info)}")
        print(f"[OCR v11] Detected: {len(_tanggal_list)} cells")
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _debug_info,
            "kolom_detected": _grid_cols,
            "baris_detected": _grid_rows,
            "kalender_area": (_kalender_start, _kalender_end),
            "raw_text": _text_full,
            "error": "",
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"success": False, "tanggal_list": [], "raw_text": "", "error": str(e)[:200]}

# =========================================================
# 🧠 PARSER: KALENDER → SHIFT MAP
# =========================================================
def parse_kalender_ke_shift(tanggal_list, bulan, tahun, nama):
    """
    Convert hasil OCR ke shift_map.
    
    Mapping tanggal dari posisi grid:
    - row 0, col 0-6 → tanggal 1-7
    - row 1, col 0-6 → tanggal 8-14
    - row 2, col 0-6 → tanggal 15-21
    - row 3, col 0-6 → tanggal 22-28
    - row 4, col 0-6 → tanggal 29-31
    """
    _shift_map = {}
    
    if not tanggal_list:
        return {
            "nama": str(nama).strip().upper(),
            "bulan": bulan,
            "tahun": tahun,
            "shift_map": {},
        }
    
    for _item in tanggal_list:
        try:
            if not isinstance(_item, dict):
                continue
            
            _kode = _item.get("kode")
            _row = _item.get("row")
            _col = _item.get("col")
            
            if not _kode or _row is None or _col is None:
                continue
            
            # Mapping: tanggal = row * 7 + col + 1
            _tgl_num = int(_row) * 7 + int(_col) + 1
            
            if _tgl_num < 1 or _tgl_num > 31:
                continue
            
            try:
                _tgl = date(tahun, bulan, _tgl_num)
            except ValueError:
                continue
            
            _shift_map[_tgl.isoformat()] = _kode
        
        except Exception as _e:
            print(f"[PARSE ERROR] {_e}")
            continue
    
    return {
        "nama": str(nama).strip().upper(),
        "bulan": bulan,
        "tahun": tahun,
        "shift_map": _shift_map,
    }


# =========================================================
# 💾 SIMPAN KE MASTER SHIFT
# =========================================================
def save_ocr_to_master_shift(nama, bulan, tahun, shift_map, sumber="ocr"):
    """Simpan hasil OCR ke master_shift."""
    try:
        from modules.supabase_client import get_supabase
        sb = get_supabase()
        
        if not shift_map:
            return False, "Tidak ada data"
        
        _now = datetime.now(ZoneInfo("Asia/Jakarta")).isoformat()
        _rows = []
        
        for _tgl_str, _kode in shift_map.items():
            _rows.append({
                "tanggal": _tgl_str,
                "nama": str(nama).strip().upper(),
                "kode_shift": str(_kode).strip().upper(),
                "sumber": str(sumber),
                "catatan": "",
                "updated_at": _now,
            })
        
        _res = sb.table("master_shift").upsert(
            _rows,
            on_conflict="tanggal,nama"
        ).execute()
        
        return True, f"{len(_res.data)} shift tersimpan untuk {nama}"
    
    except Exception as e:
        return False, f"{str(e)[:200]}"


# =========================================================
# 📝 LOG OCR
# =========================================================
def log_ocr_upload(nama, bulan, tahun, file_name, ocr_result, uploaded_by=""):
    """Catat log upload OCR."""
    try:
        from modules.supabase_client import get_supabase
        sb = get_supabase()
        
        _res = sb.table("screenshot_log").insert({
            "nama": str(nama).strip().upper(),
            "bulan": int(bulan),
            "tahun": int(tahun),
            "file_name": str(file_name)[:200],
            "ocr_result": ocr_result.get("tanggal_list", []),
            "jumlah_hari_terdeteksi": len(ocr_result.get("tanggal_list", [])),
            "status": "success" if ocr_result.get("success") else "failed",
            "error_message": ocr_result.get("error", "")[:500],
            "uploaded_by": str(uploaded_by),
        }).execute()
        
        return True, "Logged"
    except Exception as e:
        print(f"[LOG_OCR ERROR] {e}")
        return False, str(e)[:100]


# =========================================================
# 🎨 HELPER: PALETTE
# =========================================================
def update_palette_warna(kode, r, g, b):
    """Update sample warna palette."""
    if kode in COLOR_PALETTE:
        COLOR_PALETTE[kode]["rgb"] = (int(r), int(g), int(b))
        COLOR_PALETTE[kode]["hex"] = f"#{int(r):02X}{int(g):02X}{int(b):02X}"
        return True, f"Palette {kode} diupdate"
    return False, f"Kode {kode} tidak ditemukan"


def get_palette_info():
    """Ambil info palette."""
    _info = []
    for _kode, _data in COLOR_PALETTE.items():
        _info.append({
            "Kode": _kode,
            "Label": _data["label"],
            "Warna": _data["hex"],
            "RGB": f"({_data['rgb'][0]}, {_data['rgb'][1]}, {_data['rgb'][2]})",
            "Huruf": ", ".join(_data["huruf"]),
        })
    return pd.DataFrame(_info)