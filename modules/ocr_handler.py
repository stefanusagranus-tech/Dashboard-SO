"""
OCR Handler v15
==============
FULL SCRIPT dengan:
- Auto-detect calibration (dari keyword header)
- Fuzzy matching kode & tanggal
- Grid-based pairing
- Fix font error di annotated image
"""

import io
import re
import json
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
# 🎨 FUZZY MAPPING (OCR ERROR FIX)
# =========================================================
HURUF_FUZZY_MAP = {
    "P": "P", "S": "S", "M": "M", "D": "D",
    "H": "HP", "O": "O", "0": "O", "Q": "O",
    "C": "C", "L": "L", "I": "I", "1": "I",
    "A": "AO", "R": "RO", "E": "EO", "K": "SK",
}
VALID_2_HURUF = ["HP", "AO", "RO", "EO", "LO", "SK"]

TANGGAL_FIX_MAP = {
    "og": "09", "o9": "09", "o0": "10", "l0": "10",
    "l1": "11", "ll": "11", "il": "11", "l2": "12",
    "l3": "13", "l4": "14", "l5": "15", "l6": "16",
    "l7": "17", "l8": "18", "l9": "19", "2o": "20",
    "2l": "21", "2z": "22", "2s": "25", "2b": "26",
    "2t": "27", "2g": "29", "3o": "30", "3l": "31",
    "l": "1", "i": "1", "z": "2", "s": "5",
    "b": "6", "g": "9", "o": "0",
}


# =========================================================
# 🔤 EKSTRAK KODE DARI TEXT
# =========================================================
def _extract_kode_from_text(text):
    if not text:
        return None
    _text_clean = re.sub(r'[^A-Z0-9]', '', str(text).upper())
    if not _text_clean:
        return None
    _first_2 = _text_clean[:2]
    if _first_2 in VALID_2_HURUF:
        return _first_2
    _first_1 = _text_clean[:1]
    if _first_1 in HURUF_FUZZY_MAP:
        return HURUF_FUZZY_MAP[_first_1]
    return None


def _fix_tanggal_text(text):
    if not text:
        return None
    _text_clean = re.sub(r'[^a-z0-9]', '', str(text).lower())
    if not _text_clean:
        return None
    if re.match(r'^\d{1,2}$', _text_clean):
        _tgl = int(_text_clean)
        if 1 <= _tgl <= 31:
            return _tgl
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
    """OCR gambar, return list of {text, x, y, w, h, conf, jenis, ...}."""
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
        try:
            _conf = int(float(_data["conf"][_i]))
        except:
            _conf = 0
        
        if not _text or _conf < 20:
            continue
        
        _x = int(_data["left"][_i])
        _y = int(_data["top"][_i])
        _w = int(_data["width"][_i])
        _h = int(_data["height"][_i])
        
        _tgl = _fix_tanggal_text(_text)
        _kode = _extract_kode_from_text(_text)
        
        if _tgl:
            _jenis = "TANGGAL"
        elif _kode:
            _jenis = "KODE"
        else:
            _jenis = "NOISE"
        
        _items.append({
            "text": _text,
            "x": _x, "y": _y, "w": _w, "h": _h,
            "conf": _conf,
            "x_center": _x + _w // 2,
            "y_center": _y + _h // 2,
            "x_end": _x + _w,
            "y_end": _y + _h,
            "jenis": _jenis,
            "tanggal": _tgl,
            "kode": _kode,
        })
    
    return _items


# =========================================================
# 🤖 AUTO-DETECT CALIBRATION
# =========================================================
def _auto_detect_calibration(items, image_w, image_h):
    """
    Auto-detect area kalender dari keyword header.
    """
    _y_start = int(image_h * 0.30)
    _y_end = int(image_h * 0.95)
    _x_start = 0
    _x_end = image_w
    
    # Cari header keyword (untuk Y_START)
    _header_keywords = [
        "TAMBAH", "PERIODE", "NIK", "JABATAN",
        "STATUS", "KARYAWAN", "HAK", "TOTAL",
    ]
    _header_y_list = []
    
    for _item in items:
        _text_upper = _item["text"].upper().strip()
        for _kw in _header_keywords:
            if _kw in _text_upper:
                _header_y_list.append(_item["y_end"])
                break
    
    if _header_y_list:
        _y_start = max(_header_y_list) + 40
    
    # Cari footer keyword (untuk Y_END)
    _footer_keywords = ["KEMBALI", "SIMPAN", "JADWAL", "SIMPAN JADWAL"]
    _footer_y_list = []
    
    for _item in items:
        _text_upper = _item["text"].upper().strip()
        for _kw in _footer_keywords:
            if _kw in _text_upper and _item["y"] > _y_start:
                _footer_y_list.append(_item["y"])
                break
    
    if _footer_y_list:
        _y_end = min(_footer_y_list) - 30
    
    # Cari X dari kalender
    _kalender_items = [
        i for i in items
        if _y_start <= i["y"] <= _y_end and i["jenis"] in ["TANGGAL", "KODE"]
    ]
    
    if _kalender_items:
        _x_list = [i["x"] for i in _kalender_items]
        _x_end_list = [i["x_end"] for i in _kalender_items]
        
        _x_start = max(0, min(_x_list) - 30)
        _x_end = min(image_w, max(_x_end_list) + 30)
    
    return {
        "x_start": _x_start,
        "x_end": _x_end,
        "y_start": _y_start,
        "y_end": _y_end,
        "auto": True,
    }


# =========================================================
# 🎯 FILTER BERDASARKAN KALIBRASI
# =========================================================
def filter_items_by_calib(items, calib):
    """Filter items berdasarkan kalibrasi X/Y."""
    if not calib:
        return items
    
    _x_start = calib.get("x_start", 0)
    _x_end = calib.get("x_end", 99999)
    _y_start = calib.get("y_start", 0)
    _y_end = calib.get("y_end", 99999)
    
    _filtered = []
    for _item in items:
        _xc = _item["x_center"]
        _yc = _item["y_center"]
        
        if _x_start <= _xc <= _x_end and _y_start <= _yc <= _y_end:
            _filtered.append(_item)
    
    return _filtered


# =========================================================
# 🔍 KELOMPOKKAN PER BARIS
# =========================================================
def _group_by_row(items, tolerance=25):
    """Kelompokkan item berdasarkan Y (baris)."""
    _groups = {}
    
    for _item in items:
        _y = _item["y_center"]
        _match_y = None
        for _existing_y in _groups.keys():
            if abs(_existing_y - _y) < tolerance:
                _match_y = _existing_y
                break
        if _match_y is None:
            _match_y = _y
            _groups[_match_y] = []
        _groups[_match_y].append(_item)
    
    _sorted_y = sorted(_groups.keys())
    _rows = []
    for _y in _sorted_y:
        _row = sorted(_groups[_y], key=lambda x: x["x_center"])
        _rows.append(_row)
    
    return _rows


# =========================================================
# 🔍 PAIR TANGGAL & KODE
# =========================================================
def _pair_tanggal_kode(tanggal_items, kode_items):
    """Pair tanggal & kode via grid logic."""
    _pairs = []
    
    if not tanggal_items or not kode_items:
        return _pairs
    
    _tgl_rows = _group_by_row(tanggal_items)
    _kode_rows = _group_by_row(kode_items)
    
    print(f"[PAIR] Tgl rows: {len(_tgl_rows)}, Kode rows: {len(_kode_rows)}")
    
    for _tgl_row in _tgl_rows:
        if not _tgl_row:
            continue
        
        _tgl_y = _tgl_row[0]["y_center"]
        
        _best_kode_row = None
        _best_dy = 999999
        
        for _kode_row in _kode_rows:
            if not _kode_row:
                continue
            _kode_y = _kode_row[0]["y_center"]
            _dy = _kode_y - _tgl_y
            
            if 5 < _dy < 150 and _dy < _best_dy:
                _best_dy = _dy
                _best_kode_row = _kode_row
        
        if _best_kode_row is None:
            continue
        
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
# 🔍 OCR UTAMA v15
# =========================================================
def ocr_kalender_screenshot(image_bytes, calib=None):
    """
    OCR v15 — Auto-detect + kalibrasi.
    
    Args:
        image_bytes: bytes gambar
        calib: dict {x_start, x_end, y_start, y_end} atau None (auto-detect)
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
        print(f"[OCR v15] Image: {_w}x{_h}")
        
        # OCR
        _all_items = _ocr_with_coords(_img)
        print(f"[OCR v15] Total items: {len(_all_items)}")
        
        # AUTO-DETECT kalau gak ada kalibrasi
        _auto_applied = False
        if calib is None:
            calib = _auto_detect_calibration(_all_items, _w, _h)
            _auto_applied = True
            print(f"[OCR v15] Auto-calib: {calib}")
        
        # Filter
        _kalender_items = filter_items_by_calib(_all_items, calib)
        print(f"[OCR v15] After filter: {len(_kalender_items)}")
        
        # Pisahkan
        _tanggal_items = [i for i in _kalender_items if i["jenis"] == "TANGGAL"]
        _kode_items = [i for i in _kalender_items if i["jenis"] == "KODE"]
        
        print(f"[OCR v15] Tanggal: {len(_tanggal_items)}, Kode: {len(_kode_items)}")
        
        # Pair
        _pairs = _pair_tanggal_kode(_tanggal_items, _kode_items)
        print(f"[OCR v15] Pairs: {len(_pairs)}")
        
        # Build tanggal_list
        _tanggal_list = []
        for _pair in _pairs:
            _tanggal_list.append({
                "tanggal_int": _pair["tanggal"],
                "kode": _pair["kode"],
                "confidence": "MEDIUM",
                "sumber": "koordinat",
            })
        
        # Raw text
        _raw_text = "\n".join([i["text"] for i in _kalender_items])
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _kalender_items,
            "all_items": _all_items,
            "image_size": (_w, _h),
            "calib_used": calib,
            "auto_applied": _auto_applied,
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
# 🎨 ANNOTATED IMAGE (VISUAL KALIBRASI)
# =========================================================
def ocr_debug_visual(image_bytes, calib=None):
    """
    Gambar annotated dengan kotak warna + info X,Y.
    
    Returns: (PIL.Image, list_items)
    """
    if not TESSERACT_AVAILABLE:
        return None, []
    
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        _items = _ocr_with_coords(_img)
        _draw = ImageDraw.Draw(_img)
        
        # Highlight area kalibrasi (kalau ada)
        if calib:
            _x1 = calib.get("x_start", 0)
            _x2 = calib.get("x_end", _w)
            _y1 = calib.get("y_start", 0)
            _y2 = calib.get("y_end", _h)
            
            # Border hijau area terpilih
            _draw.rectangle([_x1, _y1, _x2, _y2], outline=(0, 255, 0), width=4)
        
        # Draw tiap item
        for _item in _items:
            _x1 = _item["x"]
            _y1 = _item["y"]
            _x2 = _item["x_end"]
            _y2 = _item["y_end"]
            
            # Warna per jenis
            if _item["jenis"] == "TANGGAL":
                _color = (0, 255, 0)
            elif _item["jenis"] == "KODE":
                _color = (0, 150, 255)
            else:
                _color = (255, 100, 100)
            
            _draw.rectangle([_x1, _y1, _x2, _y2], outline=_color, width=2)
            
            # Label dengan X,Y (try-except)
            _label = f"{_item['text'][:8]}({_x1},{_y1})"
            try:
                _draw.text((_x1, max(0, _y1 - 12)), _label, fill=_color)
            except Exception:
                pass
        
        return _img, _items
    
    except Exception as e:
        print(f"[DEBUG VISUAL ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return None, []


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
        _info.append({"OCR Char": _kode, "Kode": _val})
    return pd.DataFrame(_info)