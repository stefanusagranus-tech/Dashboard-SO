"""
OCR Handler v14
==============
- Fuzzy matching kode (fix OCR errors)
- Fix mapping tanggal (og→09, l1→11)
- Grid-based pairing (kelompok per baris)
- Tanpa filter Y
"""

import io
import re
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

try:
    import pytesseract
    from PIL import Image, ImageDraw
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError as e:
    print(f"[OCR] Library gak tersedia: {e}")
    TESSERACT_AVAILABLE = False


# =========================================================
# 🎨 FUZZY MAPPING KODE (OCR sering salah baca)
# =========================================================
HURUF_FUZZY_MAP = {
    "P": "P",   # Pagi
    "S": "S",   # Siang
    "M": "M",   # Malam
    "D": "D",   # Dini Hari
    "H": "HP",  # Hari Pendek
    "O": "O",   # Off
    "0": "O",   # OCR salah baca O jadi 0
    "Q": "O",   # OCR salah baca O jadi Q
    "C": "C",   # Cuti
    "L": "L",   # Libur / Long
    "I": "I",   # Izin
    "1": "I",   # OCR salah baca I jadi 1
    "A": "AO",  # Additional
    "R": "RO",  # Replace
    "E": "EO",  # Extra
    "K": "SK",  # Sakit
}

VALID_2_HURUF = ["HP", "AO", "RO", "EO", "LO", "SK"]


# =========================================================
# 🎨 FIX MAPPING TANGGAL (OCR errors)
# =========================================================
TANGGAL_FIX_MAP = {
    "og": "09",
    "o9": "09",
    "o0": "10",
    "l0": "10",
    "l1": "11",
    "ll": "11",
    "il": "11",
    "l2": "12",
    "l3": "13",
    "l4": "14",
    "l5": "15",
    "l6": "16",
    "l7": "17",
    "l8": "18",
    "l9": "19",
    "2o": "20",
    "2l": "21",
    "2z": "22",
    "2s": "25",
    "2b": "26",
    "2t": "27",
    "2g": "29",
    "3o": "30",
    "3l": "31",
    "3i": "31",
    "l": "1",
    "i": "1",
    "z": "2",
    "s": "5",
    "b": "6",
    "g": "9",
    "o": "0",
}


# =========================================================
# 🔤 EKSTRAK KODE DARI TEXT (FUZZY)
# =========================================================
def _extract_kode_from_text(text):
    """
    Ekstrak kode dari text dengan FUZZY matching.
    """
    if not text:
        return None
    
    _text = str(text).upper().strip()
    _text_clean = re.sub(r'[^A-Z0-9]', '', _text)
    
    if not _text_clean:
        return None
    
    # Cek 2 huruf dulu
    _first_2 = _text_clean[:2]
    if _first_2 in VALID_2_HURUF:
        return _first_2
    
    # Fuzzy: cek huruf pertama
    _first_1 = _text_clean[:1]
    if _first_1 in HURUF_FUZZY_MAP:
        return HURUF_FUZZY_MAP[_first_1]
    
    return None


# =========================================================
# 🔤 FIX TEXT TANGGAL
# =========================================================
def _fix_tanggal_text(text):
    """
    Fix OCR error di text tanggal.
    """
    if not text:
        return None
    
    _text = str(text).lower().strip()
    _text_clean = re.sub(r'[^a-z0-9]', '', _text)
    
    if not _text_clean:
        return None
    
    # Kalau udah angka valid
    if re.match(r'^\d{1,2}$', _text_clean):
        _tgl = int(_text_clean)
        if 1 <= _tgl <= 31:
            return _tgl
    
    # Cek fix map
    if _text_clean in TANGGAL_FIX_MAP:
        try:
            _tgl = int(TANGGAL_FIX_MAP[_text_clean])
            if 1 <= _tgl <= 31:
                return _tgl
        except:
            pass
    
    return None


# =========================================================
# 🔍 OCR WITH COORDINATES
# =========================================================
def _ocr_with_coords(image):
    """OCR gambar, return list of {text, x, y, w, h, conf}."""
    try:
        _data = pytesseract.image_to_data(
            image,
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )
    except Exception as e:
        print(f"[OCR COORDS ERROR] {e}")
        return []
    
    _items = []
    for _i in range(len(_data["text"])):
        _text = _data["text"][_i].strip()
        _conf = _data["conf"][_i]
        
        if not _text:
            continue
        try:
            _conf_int = int(float(_conf))
        except:
            _conf_int = 0
        
        if _conf_int < 20:
            continue
        
        _items.append({
            "text": _text,
            "x": int(_data["left"][_i]),
            "y": int(_data["top"][_i]),
            "w": int(_data["width"][_i]),
            "h": int(_data["height"][_i]),
            "conf": _conf_int,
            "x_center": int(_data["left"][_i]) + int(_data["width"][_i]) // 2,
            "y_center": int(_data["top"][_i]) + int(_data["height"][_i]) // 2,
        })
    
    return _items


# =========================================================
# 🔍 PISAHKAN TANGGAL & KODE
# =========================================================
def _separate_tanggal_kode(ocr_items):
    """Pisahkan tanggal & kode dengan fuzzy fix."""
    _tanggal_items = []
    _kode_items = []
    
    for _item in ocr_items:
        _text = _item["text"].strip()
        
        # Cek tanggal (fuzzy)
        _tgl = _fix_tanggal_text(_text)
        if _tgl:
            _tanggal_items.append({
                **_item,
                "tanggal": _tgl,
            })
            continue
        
        # Cek kode shift (fuzzy)
        _kode = _extract_kode_from_text(_text)
        if _kode:
            _kode_items.append({
                **_item,
                "kode": _kode,
            })
    
    # Sort by y, lalu x
    _tanggal_items = sorted(_tanggal_items, key=lambda x: (x["y_center"], x["x_center"]))
    _kode_items = sorted(_kode_items, key=lambda x: (x["y_center"], x["x_center"]))
    
    return _tanggal_items, _kode_items


# =========================================================
# 🔍 KELOMPOKKAN PER BARIS (ROW)
# =========================================================
def _group_by_row(items, tolerance=25):
    """Kelompokkan item berdasarkan Y (baris)."""
    _groups = {}
    
    for _item in items:
        _y = _item["y_center"]
        
        # Cari existing row
        _match_y = None
        for _existing_y in _groups.keys():
            if abs(_existing_y - _y) < tolerance:
                _match_y = _existing_y
                break
        
        if _match_y is None:
            _match_y = _y
            _groups[_match_y] = []
        
        _groups[_match_y].append(_item)
    
    # Sort by Y
    _sorted_y = sorted(_groups.keys())
    
    # Sort item dalam tiap row by X
    _rows = []
    for _y in _sorted_y:
        _row = sorted(_groups[_y], key=lambda x: x["x_center"])
        _rows.append(_row)
    
    return _rows


# =========================================================
# 🔍 PAIR TANGGAL & KODE (GRID-BASED)
# =========================================================
def _pair_tanggal_kode(tanggal_items, kode_items, mode="hp"):
    """
    Pair dengan grid logic:
    - Kelompokkan tanggal per baris (row)
    - Kelompokkan kode per baris (row)
    - Untuk tiap baris tanggal, cari baris kode di bawah
    - Pair by index (urutan X)
    """
    _pairs = []
    
    if not tanggal_items or not kode_items:
        return _pairs
    
    # Kelompokkan per baris
    _tgl_rows = _group_by_row(tanggal_items)
    _kode_rows = _group_by_row(kode_items)
    
    print(f"[PAIR] Tanggal rows: {len(_tgl_rows)}")
    print(f"[PAIR] Kode rows: {len(_kode_rows)}")
    
    # Untuk setiap baris tanggal, cari baris kode terdekat di bawahnya
    for _tgl_row in _tgl_rows:
        if not _tgl_row:
            continue
        
        _tgl_y = _tgl_row[0]["y_center"]
        
        # Cari kode row yang Y-nya > tgl_y (di bawah)
        _best_kode_row = None
        _best_dy = 999999
        
        for _kode_row in _kode_rows:
            if not _kode_row:
                continue
            _kode_y = _kode_row[0]["y_center"]
            _dy = _kode_y - _tgl_y
            
            if _dy > 5 and _dy < _best_dy:
                _best_dy = _dy
                _best_kode_row = _kode_row
        
        if _best_kode_row is None:
            continue
        
        # Pair by index
        for _i, _tgl_item in enumerate(_tgl_row):
            if _i < len(_best_kode_row):
                _pairs.append({
                    "tanggal": _tgl_item["tanggal"],
                    "kode": _best_kode_row[_i]["kode"],
                })
    
    # Deduplicate
    _unique = {}
    for _pair in _pairs:
        if _pair["tanggal"] not in _unique:
            _unique[_pair["tanggal"]] = _pair
    
    return list(_unique.values())


# === BAGIAN 2 MULAI ===

# =========================================================
# 🔍 DETEKSI MODE
# =========================================================
def _detect_mode(ocr_items):
    """Deteksi mode: desktop atau hp."""
    _full_text = " ".join([item["text"] for item in ocr_items]).upper()
    
    # Desktop: ada pattern "S15-SIANG", "M22-MALAM", dll
    if re.search(r'[A-Z]\d{1,2}[\-~][A-Z]{3,}', _full_text):
        return "desktop"
    
    # Desktop: ada keyword "SIANG"/"MALAM"/"PAGI"/"OFF"
    if any(kw in _full_text for kw in ["SIANG", "MALAM", "PAGI", "OFF", "CUTI"]):
        return "desktop"
    
    # Default: HP
    return "hp"


# =========================================================
# 🔍 OCR UTAMA v14
# =========================================================
def ocr_kalender_screenshot(image_bytes):
    """
    OCR v14 — Fuzzy matching + grid-based pairing.
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
        print(f"[OCR v14] Image: {_w}x{_h}")
        
        # OCR dengan koordinat
        _items = _ocr_with_coords(_img)
        print(f"[OCR v14] Items detected: {len(_items)}")
        
        # TANPA FILTER Y — ambil semua
        _kalender_items = _items
        
        # Deteksi mode
        _mode = _detect_mode(_kalender_items)
        print(f"[OCR v14] Mode: {_mode}")
        
        # Pisahkan tanggal & kode
        _tanggal_items, _kode_items = _separate_tanggal_kode(_kalender_items)
        print(f"[OCR v14] Tanggal items: {len(_tanggal_items)}")
        print(f"[OCR v14] Kode items: {len(_kode_items)}")
        
        # Pair
        _pairs = _pair_tanggal_kode(_tanggal_items, _kode_items, mode=_mode)
        print(f"[OCR v14] Pairs: {len(_pairs)}")
        
        # Build tanggal_list
        _tanggal_list = []
        _debug_items = []
        
        for _pair in _pairs:
            _tanggal_list.append({
                "tanggal_int": _pair["tanggal"],
                "kode": _pair["kode"],
                "confidence": "MEDIUM",
                "sumber": f"koordinat_{_mode}",
            })
        
        # Debug: semua item
        for _item in _kalender_items:
            _is_tgl = bool(re.match(r'^\d{1,2}$', _item["text"].strip()))
            _is_kode = _extract_kode_from_text(_item["text"]) is not None
            
            _debug_items.append({
                "text": _item["text"],
                "x": _item["x"],
                "y": _item["y"],
                "conf": _item["conf"],
                "jenis": "TANGGAL" if _is_tgl else ("KODE" if _is_kode else "NOISE"),
            })
        
        # Raw text
        _raw_text = "\n".join([item["text"] for item in _kalender_items])
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _debug_items,
            "mode": _mode,
            "kolom_detected": 0,
            "baris_detected": 0,
            "kalender_area": (0, _h),
            "raw_text": _raw_text,
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
# 🎨 OCR DEBUG VISUAL (ANNOTATED IMAGE)
# =========================================================
def ocr_debug_visual(image_bytes):
    """
    OCR + gambar annotated (kotak di tiap text).
    """
    if not TESSERACT_AVAILABLE:
        return None
    
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _items = _ocr_with_coords(_img)
        _draw = ImageDraw.Draw(_img)
        
        for _item in _items:
            _x1 = _item["x"]
            _y1 = _item["y"]
            _x2 = _x1 + _item["w"]
            _y2 = _y1 + _item["h"]
            _text = _item["text"]
            
            # Deteksi jenis
            _is_tgl = bool(re.match(r'^\d{1,2}$', _text.strip()))
            _kode = _extract_kode_from_text(_text)
            
            if _is_tgl:
                _color = (0, 255, 0)      # hijau: tanggal
            elif _kode:
                _color = (0, 150, 255)    # biru: kode
            else:
                _color = (255, 100, 100)  # merah: noise
            
            _draw.rectangle([_x1, _y1, _x2, _y2], outline=_color, width=2)
            _draw.text((_x1, max(0, _y1 - 12)), _text[:15], fill=_color)
        
        return _img
    
    except Exception as e:
        print(f"[DEBUG VISUAL ERROR] {e}")
        return None


# =========================================================
# 🧠 PARSER: KALENDER → SHIFT MAP
# =========================================================
def parse_kalender_ke_shift(tanggal_list, bulan, tahun, nama):
    """Convert hasil OCR ke shift_map."""
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
            _tgl_num = _item.get("tanggal_int")
            
            if not _kode or not _tgl_num:
                continue
            
            _tgl_num = int(_tgl_num)
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
# 🎨 HELPER
# =========================================================
def get_palette_info():
    """Return info fuzzy mapping."""
    _info = []
    for _kode, _val in HURUF_FUZZY_MAP.items():
        _info.append({
            "Karakter OCR": _kode,
            "Kode Hasil": _val,
        })
    return pd.DataFrame(_info)