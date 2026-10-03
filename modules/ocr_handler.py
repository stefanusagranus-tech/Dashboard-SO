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
    OCR v12 — Regex text (balik ke metode v4 yang berhasil).
    
    Strategi:
    1. OCR full image
    2. Regex extract tanggal (1-31)
    3. Regex extract shift (S15, M22, O, dll)
    4. Match by urutan
    """
    if not TESSERACT_AVAILABLE:
        return {"success": False, "tanggal_list": [], "raw_text": "", "error": "Tesseract tidak tersedia"}
    
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        print(f"[OCR v12] Image: {_w}x{_h}")
        
        # ============================================
        # 1. OCR TEXT FULL (PSM 6 — konsisten)
        # ============================================
        _text = pytesseract.image_to_string(_img, config="--psm 6")
        print(f"[OCR v12] Text length: {len(_text)}")
        
        # ============================================
        # 2. EXTRACT SHIFT PATTERN (huruf awal + angka)
        # ============================================
        # Pattern shift: S15, M22, P7, O, C, L, HP3, DI2, DH1, dll
        # Match: 1-2 huruf + 0-2 angka
        _pattern_shift = r'\b([A-Z]{1,2})(\d{1,2})?\b'
        
        # Pattern tanggal: 1-31
        _pattern_tanggal = r'\b(0?[1-9]|[12][0-9]|3[01])\b'
        
        # Split per baris
        _lines = _text.split("\n")
        
        # ============================================
        # 3. EKSTRAK TANGGAL & SHIFT BERDASARKAN BARIS
        # ============================================
        # Karena layout: baris 1 = "04 05 06 07 08 09 10"
        #              baris 2 = "S15 O M22 M22 M22 S15 S15"
        # Kita cari pasangan (tanggal, shift) berurutan
        
        _tanggal_pairs = []  # list of (tanggal, kode)
        
        _buffer_tanggal = []
        
        for _line in _lines:
            _line_clean = _line.strip().upper()
            if not _line_clean:
                continue
            
            # Deteksi shift di baris ini (pattern "S15-SIANG", "M22-MALAM")
            _shifts = []
            
            # Pattern 1: S15-SIANG, M22-MALAM, O-OFF
            for _m in re.finditer(r'([A-Z]{1,2})(\d{1,2})?[\-\s~]*(SIANG|MALAM|PAGI|OFF|CUTI|LIBUR|SIONG|SIANG|MALOM)?', _line_clean):
                _kode_raw = _m.group(1)
                _angka = _m.group(2) or ""
                
                # Validasi: kode harus P, S, M, O, C, L, D, H, A, I, E, R
                if _kode_raw in ["P", "S", "M", "O", "C", "L", "D", "H", "A", "I", "E", "R", "HP", "DI", "DH", "PH", "PI", "SI", "MI", "SH", "MH", "AO", "EO", "RO", "LO", "SK"]:
                    _shifts.append(_kode_raw)
            
            # Deteksi tanggal di baris ini
            _tgl_matches = re.findall(_pattern_tanggal, _line_clean)
            _tgl_ints = []
            for _t in _tgl_matches:
                try:
                    _t_int = int(_t)
                    if 1 <= _t_int <= 31:
                        _tgl_ints.append(_t_int)
                except:
                    continue
            
            # Kalau ada shift & tanggal → langsung pair
            if _shifts and _tgl_ints:
                for _i, _tgl in enumerate(_tgl_ints):
                    if _i < len(_shifts):
                        _tanggal_pairs.append((_tgl, _shifts[_i]))
            elif _tgl_ints:
                # Cuma tanggal → masuk buffer
                _buffer_tanggal.extend(_tgl_ints)
            elif _shifts and _buffer_tanggal:
                # Ada shift, dan ada buffer tanggal dari baris sebelumnya
                for _i, _tgl in enumerate(_buffer_tanggal):
                    if _i < len(_shifts):
                        _tanggal_pairs.append((_tgl, _shifts[_i]))
                _buffer_tanggal = []
        
        print(f"[OCR v12] Tanggal-Shift pairs: {len(_tanggal_pairs)}")
        
        # ============================================
        # 4. KALAU PAIRS KOSONG, FALLBACK KE URUTAN
        # ============================================
        if not _tanggal_pairs:
            # Ambil semua tanggal & semua shift, pair by index
            _all_tgl = []
            _all_shift = []
            
            for _line in _lines:
                _line_clean = _line.strip().upper()
                _tgl_matches = re.findall(_pattern_tanggal, _line_clean)
                for _t in _tgl_matches:
                    try:
                        _t_int = int(_t)
                        if 1 <= _t_int <= 31:
                            _all_tgl.append(_t_int)
                    except:
                        continue
                
                for _m in re.finditer(r'\b([A-Z]{1,2})(\d{1,2})?\b', _line_clean):
                    _k = _m.group(1)
                    if _k in ["P", "S", "M", "O", "C", "L", "D", "H", "A", "I", "E", "R", "HP", "AO", "EO", "RO", "LO"]:
                        _all_shift.append(_k)
            
            # Deduplicate tanggal & sort
            _all_tgl = sorted(set(_all_tgl))
            
            # Pair by index
            for _i, _tgl in enumerate(_all_tgl):
                if _i < len(_all_shift):
                    _tanggal_pairs.append((_tgl, _all_shift[_i]))
        
        print(f"[OCR v12] Total pairs: {len(_tanggal_pairs)}")
        
        # ============================================
        # 5. BUILD TANGGAL_LIST
        # ============================================
        _tanggal_list = []
        _debug_info = []
        
        for _tgl, _kode in _tanggal_pairs:
            _tanggal_list.append({
                "tanggal_int": _tgl,
                "kode": _kode,
                "confidence": "MEDIUM",
                "sumber": "text_regex",
            })
            
            _debug_info.append({
                "tanggal": _tgl,
                "kode": _kode,
            })
        
        print(f"[OCR v12] Detected: {len(_tanggal_list)} days")
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _debug_info,
            "kolom_detected": 0,
            "baris_detected": 0,
            "kalender_area": (0, 0),
            "raw_text": _text,
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