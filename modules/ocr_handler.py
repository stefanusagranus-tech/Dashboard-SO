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
    OCR screenshot v9 — Auto-detect grid dengan merge.
    """
    if not TESSERACT_AVAILABLE:
        return {
            "success": False,
            "tanggal_list": [],
            "raw_text": "",
            "error": "Tesseract tidak tersedia",
        }
    
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        print(f"[OCR v9] Image: {_w}x{_h}")
        
        # OCR TEXT FULL
        _text_full = pytesseract.image_to_string(_img, config="--psm 6")
        print(f"[OCR v9] Text length: {len(_text_full)}")
        
        _np_img = np.array(_img)
        
        # ============================================
        # 1. AUTO-DETECT AREA KALENDER
        # ============================================
        _grayscale = np.mean(_np_img, axis=2)
        _is_white = _grayscale > 240
        _row_color_density = 1 - np.mean(_is_white, axis=1)
        
        print(f"[OCR v9] Row density max: {_row_color_density.max():.3f}")
        
        _kalender_start = None
        _kalender_end = None
        
        for _i in range(int(_h * 0.20), _h - 5):
            if _row_color_density[_i] > 0.05:
                if _kalender_start is None:
                    _kalender_start = _i
                _kalender_end = _i
        
        if _kalender_start is None:
            print(f"[OCR v9] WARNING: Kalender gak ke-detect, pakai fallback 50-95%")
            _kalender_start = int(_h * 0.50)
            _kalender_end = int(_h * 0.95)
        
        print(f"[OCR v9] Kalender area: y={_kalender_start}-{_kalender_end}")
        
        # ============================================
        # 2. AUTO-DETECT KOLOM DENGAN MERGE
        # ============================================
        _kalender_region = _np_img[_kalender_start:_kalender_end, :]
        _region_gray = np.mean(_kalender_region, axis=2)
        _region_white = _region_gray > 240
        _col_color_density = 1 - np.mean(_region_white, axis=0)
        
        # Deteksi kolom dengan gap threshold
        _col_raw = []
        _in_col = False
        _start = 0
        _gap = 0
        _gap_threshold = 5
        
        for _i in range(_w):
            if _col_color_density[_i] > 0.05:
                if not _in_col:
                    _start = _i
                    _in_col = True
                _gap = 0
            else:
                if _in_col:
                    _gap += 1
                    if _gap >= _gap_threshold:
                        _col_raw.append((_start, _i - _gap + 1))
                        _in_col = False
                        _gap = 0
        
        if _in_col:
            _col_raw.append((_start, _w))
        
        # Filter kolom sempit (< 15px)
        _col_filtered = [(s, e) for s, e in _col_raw if (e - s) >= 15]
        
        print(f"[OCR v9] Kolom raw: {len(_col_raw)}, filtered: {len(_col_filtered)}")
        
        # Kalau masih > 7, ambil 7 terbesar
        if len(_col_filtered) > 7:
            _col_filtered = sorted(_col_filtered, key=lambda x: x[1]-x[0], reverse=True)[:7]
            _col_filtered = sorted(_col_filtered, key=lambda x: x[0])
        
        _col_starts = [_s for _s, _e in _col_filtered]
        _col_ends = [_e for _s, _e in _col_filtered]
        
        print(f"[OCR v9] Kolom final: {len(_col_starts)}")
        
        # ============================================
        # 3. AUTO-DETECT ROW DENGAN MERGE
        # ============================================
        _row_color_density_kal = _row_color_density[_kalender_start:_kalender_end]
        
        _row_raw = []
        _in_row = False
        _start_row = 0
        _gap_row = 0
        _gap_threshold_row = 8
        
        for _i in range(len(_row_color_density_kal)):
            if _row_color_density_kal[_i] > 0.03:
                if not _in_row:
                    _start_row = _i
                    _in_row = True
                _gap_row = 0
            else:
                if _in_row:
                    _gap_row += 1
                    if _gap_row >= _gap_threshold_row:
                        _row_raw.append((_start_row, _i - _gap_row + 1))
                        _in_row = False
                        _gap_row = 0
        
        if _in_row:
            _row_raw.append((_start_row, len(_row_color_density_kal)))
        
        # Filter row sempit
        _row_filtered = [(s, e) for s, e in _row_raw if (e - s) >= 20]
        
        print(f"[OCR v9] Row raw: {len(_row_raw)}, filtered: {len(_row_filtered)}")
        
        # Kalau > 5, ambil 5 terbesar
        if len(_row_filtered) > 5:
            _row_filtered = sorted(_row_filtered, key=lambda x: x[1]-x[0], reverse=True)[:5]
            _row_filtered = sorted(_row_filtered, key=lambda x: x[0])
        
        _row_starts = [_s for _s, _e in _row_filtered]
        _row_ends = [_e for _s, _e in _row_filtered]
        
        print(f"[OCR v9] Row final: {len(_row_starts)}")
        
        # ============================================
        # 4. FALLBACK KALAU AUTO-DETECT GAGAL
        # ============================================
        if len(_col_starts) < 5 or len(_row_starts) < 4:
            print(f"[OCR v9] Fallback: pakai grid fixed 7x5")
            _grid_cols = 7
            _grid_rows = 5
            _cell_h = (_kalender_end - _kalender_start) // _grid_rows
            _cell_w = _w // _grid_cols
            
            _col_starts = [_c * _cell_w for _c in range(_grid_cols)]
            _col_ends = [(_c + 1) * _cell_w for _c in range(_grid_cols)]
            _row_starts = [_r * _cell_h for _r in range(_grid_rows)]
            _row_ends = [(_r + 1) * _cell_h for _r in range(_grid_rows)]
        
        # ============================================
        # 5. ANALISIS PER CELL
        # ============================================
        _tanggal_list = []
        _debug_info = []
        
        for _r_idx, (_y_start, _y_end) in enumerate(zip(_row_starts, _row_ends)):
            for _c_idx, (_x_start, _x_end) in enumerate(zip(_col_starts, _col_ends)):
                if (_x_end - _x_start) < 15 or (_y_end - _y_start) < 10:
                    continue
                
                _y1 = _kalender_start + _y_start
                _y2 = _kalender_start + _y_end
                _x1 = _x_start
                _x2 = _x_end
                
                _cell_img = _img.crop((_x1, _y1, _x2, _y2))
                _cell_np = np.array(_cell_img)
                
                if _cell_np.size == 0:
                    continue
                
                _cell_gray = np.mean(_cell_np, axis=2)
                _cell_white_pct = np.mean(_cell_gray > 240)
                
                # Skip kalau terlalu putih
                if _cell_white_pct > 0.90:
                    continue
                
                # Deteksi warna (sample 5 titik)
                _h_cell, _w_cell = _cell_np.shape[:2]
                _points = [
                    _cell_np[_h_cell // 2, _w_cell // 2],
                    _cell_np[_h_cell // 4, _w_cell // 4],
                    _cell_np[_h_cell // 4, 3 * _w_cell // 4],
                    _cell_np[3 * _h_cell // 4, _w_cell // 4],
                    _cell_np[3 * _h_cell // 4, 3 * _w_cell // 4],
                ]
                
                _r_val = int(np.median([p[0] for p in _points]))
                _g_val = int(np.median([p[1] for p in _points]))
                _b_val = int(np.median([p[2] for p in _points]))
                
                _kode_warna, _conf_warna, _dist = _rgb_to_kode_v2(_r_val, _g_val, _b_val)
                
                # Deteksi text
                _kode_huruf = None
                _text_cell = ""
                
                try:
                    _text_cell = pytesseract.image_to_string(
                        _cell_img,
                        config="--psm 7",
                    ).strip()
                    
                    if _text_cell:
                        _kode_huruf, _conf_huruf = _huruf_to_kode(_text_cell)
                except Exception:
                    pass
                
                # Voting
                _kode_final = None
                _confidence = "LOW"
                _sumber = ""
                
                if _kode_huruf and _kode_warna:
                    if _kode_huruf == _kode_warna:
                        _kode_final = _kode_huruf
                        _confidence = "HIGH"
                        _sumber = "huruf+warna"
                    else:
                        _kode_final = _kode_warna
                        _confidence = "MEDIUM"
                        _sumber = f"warna({_kode_warna}) vs huruf({_kode_huruf})"
                elif _kode_warna:
                    _kode_final = _kode_warna
                    _confidence = "MEDIUM"
                    _sumber = "warna"
                elif _kode_huruf:
                    _kode_final = _kode_huruf
                    _confidence = "MEDIUM"
                    _sumber = "huruf"
                
                _debug_info.append({
                    "row": _r_idx,
                    "col": _c_idx,
                    "x": f"{_x1},{_x2}",
                    "y": f"{_y1},{_y2}",
                    "text_cell": _text_cell,
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
        
        print(f"[OCR v9] Cells analyzed: {len(_debug_info)}")
        print(f"[OCR v9] Detected: {len(_tanggal_list)} cells")
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _debug_info,
            "kolom_detected": len(_col_starts),
            "baris_detected": len(_row_starts),
            "kalender_area": (_kalender_start, _kalender_end),
            "raw_text": _text_full,
            "error": "",
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {
            "success": False,
            "tanggal_list": [],
            "raw_text": "",
            "error": str(e)[:200],
        }


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