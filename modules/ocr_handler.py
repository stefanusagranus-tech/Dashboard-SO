"""
OCR Handler v3
==============
Handle OCR screenshot kalender shift dari web absen.

Fitur:
- 2 metode deteksi: warna + huruf
- Voting system untuk akurasi
- Color palette dari sample warna
- Auto-extract text huruf
"""

import io
import re
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# Pytesseract & PIL
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError as e:
    print(f"[OCR] Library gak tersedia: {e}")
    TESSERACT_AVAILABLE = False


# =========================================================
# 🎨 COLOR PALETTE — Sample Warna Resmi Web Absen
# =========================================================
# Update manual kalau warna web berubah
COLOR_PALETTE = {
    "P7": {
        "label": "Pagi (07:00)",
        "rgb": (15, 138, 114),        # Hijau tua
        "hex": "#0F8A72",
        "tolerance": 50,
        "huruf": ["P", "P7", "P7-F", "P7~F"],
    },
    "S15": {
        "label": "Siang (15:00)",
        "rgb": (0, 255, 204),          # Hijau muda
        "hex": "#00FFCC",
        "tolerance": 60,
        "huruf": ["S", "S15", "S15-"],
    },
    "M22": {
        "label": "Malam (22:00)",
        "rgb": (102, 102, 255),        # Biru/ungu
        "hex": "#6666FF",
        "tolerance": 50,
        "huruf": ["M", "M22", "M2"],
    },
    "O": {
        "label": "Off (Libur)",
        "rgb": (0, 0, 0),              # Hitam
        "hex": "#000000",
        "tolerance": 40,
        "huruf": ["O", "O-C", "OFF"],
    },
    "C": {
        "label": "Cuti",
        "rgb": (255, 200, 0),          # Kuning (kalau ada)
        "hex": "#FFC800",
        "tolerance": 50,
        "huruf": ["C", "CUTI"],
    },
    "AO": {
        "label": "Additional Off",
        "rgb": (150, 150, 150),        # Abu
        "hex": "#969696",
        "tolerance": 50,
        "huruf": ["A", "AO"],
    },
}


# =========================================================
# 🎨 DETEKSI WARNA → KODE
# =========================================================
def _rgb_to_kode_v2(r, g, b):
    """
    Deteksi kode shift dari warna RGB dengan palette matching.
    
    Return:
        (kode, confidence, distance)
    """
    # Skip putih/abu terang (background)
    if r > 220 and g > 220 and b > 220:
        return None, 0, 999999
    
    # Skip abu netral (mungkin background atau border)
    if abs(r - g) < 10 and abs(g - b) < 10 and 100 < r < 220:
        return None, 0, 999999
    
    _best_match = None
    _best_distance = 999999
    
    for _kode, _info in COLOR_PALETTE.items():
        _pal_r, _pal_g, _pal_b = _info["rgb"]
        
        # Euclidean distance
        _distance = (
            (r - _pal_r) ** 2 +
            (g - _pal_g) ** 2 +
            (b - _pal_b) ** 2
        ) ** 0.5
        
        if _distance < _best_distance:
            _best_distance = _distance
            _best_match = _kode
    
    # Cek toleransi
    if _best_match:
        _tol = COLOR_PALETTE[_best_match]["tolerance"]
        if _best_distance <= _tol:
            _confidence = max(0, 100 - int((_best_distance / _tol) * 50))
            return _best_match, _confidence, _best_distance
    
    return None, 0, _best_distance


# =========================================================
# 🔤 DETEKSI HURUF → KODE
# =========================================================
def _huruf_to_kode(text):
    """
    Deteksi kode dari text huruf.
    
    Contoh:
        "P7~F" → P7
        "S15" → S15
        "M22" → M22
        "O-C" → O
        "OFF" → O
    """
    if not text:
        return None, 0
    
    _text_upper = str(text).upper().strip()
    
    # Cari match dengan huruf di palette
    for _kode, _info in COLOR_PALETTE.items():
        for _huruf in _info["huruf"]:
            _huruf_upper = _huruf.upper()
            
            # Exact match
            if _text_upper == _huruf_upper:
                return _kode, 100
            
            # Starts with
            if _text_upper.startswith(_huruf_upper):
                return _kode, 90
    
    # Fallback: cek 1 huruf pertama
    _first_char = _text_upper[:1] if _text_upper else ""
    
    if _first_char == "P":
        return "P7", 70
    if _first_char == "S":
        return "S15", 70
    if _first_char == "M":
        return "M22", 70
    if _first_char == "O":
        return "O", 70
    if _first_char == "C":
        return "C", 70
    if _first_char == "A":
        return "AO", 70
    
    return None, 0


# =========================================================
# 🔍 OCR UTAMA — VERSI 3 (2 METODE)
# =========================================================
def ocr_kalender_screenshot(image_bytes):
    """
    OCR screenshot v4 — Deteksi via TEXT CELL.
    
    Karena web desktop punya text jelas:
    - "S15-SIANG" → S15
    - "M22-MALAM" → M22
    - "O-OFF" → O
    - "P7-F" → P7
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
        print(f"[OCR v4] Image: {_w}x{_h}")
        
        # ============================================
        # OCR TEXT FULL
        # ============================================
        _text_full = pytesseract.image_to_string(_img, config="--psm 6")
        
        # ============================================
        # DETEKSI KODE DARI TEXT
        # ============================================
        # Pattern shift text
        _pattern_shift = r'(S15|M22|P7|O|C|AO)[\-~]?(?:SIANG|MALAM|PAGI|OFF|CUTI)?'
        
        # Deteksi angka tanggal pattern
        _pattern_tanggal = r'\b([1-9]|[12][0-9]|3[01])\b'
        
        # Split per line
        _lines = _text_full.split("\n")
        
        # Tracking
        _tanggal_list = []
        _tanggal_found = []
        _shift_per_baris = []
        
        for _line in _lines:
            _line_clean = _line.strip()
            if not _line_clean:
                continue
            
            # Cari shift di baris ini
            _shift_matches = re.findall(
                r'(S15|M22|P7|O|C|AO)',
                _line_clean,
                re.IGNORECASE
            )
            
            # Cari tanggal di baris ini
            _tgl_matches = re.findall(_pattern_tanggal, _line_clean)
            
            if _shift_matches:
                _shift_per_baris.append(_shift_matches)
            
            if _tgl_matches:
                for _t in _tgl_matches:
                    _t_int = int(_t)
                    if 1 <= _t_int <= 31:
                        _tanggal_found.append(_t_int)
        
        # Deduplicate & sort tanggal
        _tanggal_found = sorted(set(_tanggal_found))
        print(f"[OCR v4] Tanggal: {_tanggal_found}")
        print(f"[OCR v4] Shift per baris: {_shift_per_baris}")
        
        # ============================================
        # MATCHING TANGGAL + SHIFT
        # ============================================
        # Asumsi: shift_per_baris dalam urutan
        # Baris 1: tgl 1-7, Baris 2: 8-14, dst.
        
        # Flatten semua shift
        _all_shift = []
        for _shifts in _shift_per_baris:
            _all_shift.extend([s.upper() for s in _shifts])
        
        # Map tiap shift ke tanggal
        for _idx, _kode in enumerate(_all_shift):
            if _idx < len(_tanggal_found):
                _tanggal_list.append({
                    "tanggal_int": _tanggal_found[_idx],
                    "kode": _kode,
                    "confidence": "MEDIUM",
                    "sumber": "text",
                })
        
        print(f"[OCR v4] Result: {len(_tanggal_list)} shifts")
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "tanggal_detected": _tanggal_found,
            "all_shift": _all_shift,
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
    
    Args:
        tanggal_list: list dict dari OCR
        bulan: int
        tahun: int
        nama: str
    
    Returns:
        dict {nama, bulan, tahun, shift_map}
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
            # Ambil tanggal
            if isinstance(_item, dict):
                _kode = _item.get("kode")
                
                # Coba ambil tanggal dari berbagai field
                _tgl_num = None
                if "tanggal_int" in _item:
                    _tgl_num = int(_item["tanggal_int"])
                elif "tanggal" in _item:
                    _tgl_num = int(_item["tanggal"])
                
                if not _kode or not _tgl_num:
                    continue
            else:
                continue
            
            # Validasi
            if _tgl_num < 1 or _tgl_num > 31:
                continue
            
            # Build date
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
# 💾 SIMPAN HASIL OCR
# =========================================================
def save_ocr_to_master_shift(nama, bulan, tahun, shift_map, sumber="ocr"):
    """Simpan hasil OCR ke master_shift."""
    try:
        from modules.supabase_client import get_supabase
        sb = get_supabase()
        
        if not shift_map:
            return False, "❌ Tidak ada data"
        
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
        
        return True, f"✅ {len(_res.data)} shift tersimpan untuk {nama}"
    
    except Exception as e:
        return False, f"❌ {str(e)[:200]}"


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
# 🎨 HELPER: UPDATE PALETTE (untuk admin)
# =========================================================
def update_palette_warna(kode, r, g, b):
    """
    Update sample warna palette.
    
    Args:
        kode: "P7", "S15", "M22", "O", "C", "AO"
        r, g, b: int (0-255)
    """
    if kode in COLOR_PALETTE:
        COLOR_PALETTE[kode]["rgb"] = (int(r), int(g), int(b))
        COLOR_PALETTE[kode]["hex"] = f"#{int(r):02X}{int(g):02X}{int(b):02X}"
        return True, f"✅ Palette {kode} diupdate ke RGB({r}, {g}, {b})"
    return False, f"❌ Kode {kode} tidak ditemukan"


def get_palette_info():
    """Ambil info palette untuk display."""
    _info = []
    for _kode, _data in COLOR_PALETTE.items():
        _info.append({
            "Kode": _kode,
            "Label": _data["label"],
            "Warna": _data["hex"],
            "RGB": f"({_data['rgb'][0]}, {_data['rgb'][1]}, {_data['rgb'][2]})",
            "Tolerance": _data["tolerance"],
        })
    return pd.DataFrame(_info)