"""
OCR Handler v19
==============
4 FIX:
- Double OCR (normal + inverted)
- Split bounding box multi-number
- Threshold 5
- Color fallback
"""

import io
import re
import json
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

try:
    import pytesseract
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError as e:
    print(f"[OCR] Library gak tersedia: {e}")
    TESSERACT_AVAILABLE = False


# =========================================================
# 🎨 COLOR PALETTE (fallback)
# =========================================================
COLOR_PALETTE = {
    "P": {"label": "Pagi", "rgb": (60, 220, 200), "tol": 100},
    "S": {"label": "Siang", "rgb": (0, 255, 173), "tol": 80},
    "M": {"label": "Malam", "rgb": (100, 133, 255), "tol": 80},
    "D": {"label": "Dini Hari", "rgb": (240, 240, 100), "tol": 80},
    "O": {"label": "Off", "rgb": (13, 13, 13), "tol": 40},
    "C": {"label": "Cuti", "rgb": (13, 13, 13), "tol": 40},
    "I": {"label": "Izin", "rgb": (13, 13, 13), "tol": 40},
    "L": {"label": "Libur", "rgb": (250, 150, 150), "tol": 80},
}


# =========================================================
# 🎨 FUZZY MAPPING
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
# 🔤 EKSTRAK KODE
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
# 🎨 WARNA → KODE
# =========================================================
def _warna_to_kode(r, g, b):
    if r > 240 and g > 240 and b > 240:
        return None
    _max_c = max(r, g, b)
    _min_c = min(r, g, b)
    if (_max_c - _min_c) < 15 and r > 150:
        return None
    
    _best = None
    _best_dist = 999999
    for _kode, _info in COLOR_PALETTE.items():
        _pr, _pg, _pb = _info["rgb"]
        _d = ((r - _pr)**2 + (g - _pg)**2 + (b - _pb)**2) ** 0.5
        if _d < _best_dist:
            _best_dist = _d
            _best = _kode
    if _best and _best_dist <= COLOR_PALETTE[_best]["tol"]:
        return _best
    return None


# =========================================================
# ✅ SPLIT BOUNDING BOX MULTI-NUMBER
# =========================================================
def _split_multi_number_box(item):
    """
    Split item dengan multiple angka ("08 09" → ["08", "09"]).
    """
    _text = item["text"].strip()
    _numbers = re.findall(r'\d{1,2}', _text)
    
    if len(_numbers) <= 1:
        return [item]
    
    print(f"[SPLIT] '{_text}' → {_numbers}")
    
    _x1 = item["x"]
    _x2 = item["x_end"]
    _y1 = item["y"]
    _y2 = item["y_end"]
    _w = _x2 - _x1
    _per_num = _w / len(_numbers)
    
    _results = []
    for _i, _num in enumerate(_numbers):
        _num_int = int(_num)
        if not (1 <= _num_int <= 31):
            continue
        
        _nx1 = int(_x1 + _i * _per_num)
        _nx2 = int(_x1 + (_i + 1) * _per_num)
        
        _results.append({
            **item,
            "text": _num,
            "x": _nx1,
            "x_end": _nx2,
            "x_center": (_nx1 + _nx2) // 2,
            "w": _nx2 - _nx1,
            "jenis": "TANGGAL",
            "tanggal": _num_int,
            "kode": None,
            "split": True,
        })
    
    return _results if _results else [item]


# =========================================================
# 🔍 OCR SINGLE PASS
# =========================================================
def _ocr_single(image, invert=False):
    """
    OCR 1x dengan optional invert.
    """
    try:
        _img = image.copy()
        if invert:
            _img = ImageOps.invert(_img.convert("RGB"))
        
        # Preprocessing
        _img_gray = _img.convert("L")
        _img_gray = ImageEnhance.Contrast(_img_gray).enhance(1.5)
        _img_gray = _img_gray.filter(ImageFilter.SHARPEN)
        _img_proc = _img_gray.convert("RGB")
        
        # OCR PSM 11
        _data = pytesseract.image_to_data(
            _img_proc,
            config="--psm 11",
            output_type=pytesseract.Output.DICT,
        )
    except Exception as e:
        print(f"[OCR SINGLE ERROR] {e}")
        return []
    
    _items = []
    for _i in range(len(_data["text"])):
        _text = _data["text"][_i].strip()
        try:
            _conf = int(float(_data["conf"][_i]))
        except:
            _conf = 0
        
        # ✅ Threshold 5
        if not _text or _conf < 5:
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
        
        _item = {
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
            "inverted": invert,
        }
        
        # ✅ Split kalau multiple angka
        if re.search(r'\d{1,2}\s+\d{1,2}', _text):
            _items.extend(_split_multi_number_box(_item))
        else:
            _items.append(_item)
    
    return _items


# =========================================================
# 🔍 OCR DOUBLE PASS + DEDUP
# =========================================================
def _dedup_items(items):
    """Deduplicate items by posisi (x,y) — ambil conf tertinggi."""
    _seen = {}
    for _item in items:
        # Key: posisi dalam grid 10x10 px
        _key = (_item["x_center"] // 15, _item["y_center"] // 15)
        
        if _key not in _seen:
            _seen[_key] = _item
        else:
            # Ambil yang conf lebih tinggi
            if _item["conf"] > _seen[_key]["conf"]:
                _seen[_key] = _item
    
    return list(_seen.values())


def _ocr_with_coords(image):
    """
    OCR ganda: normal + inverted, lalu dedup.
    """
    _items = []
    
    # Pass 1: NORMAL
    _items_normal = _ocr_single(image, invert=False)
    print(f"[OCR] Normal pass: {len(_items_normal)} items")
    _items.extend(_items_normal)
    
    # Pass 2: INVERTED
    _items_inv = _ocr_single(image, invert=True)
    print(f"[OCR] Inverted pass: {len(_items_inv)} items")
    _items.extend(_items_inv)
    
    # Dedup
    _items_dedup = _dedup_items(_items)
    print(f"[OCR] After dedup: {len(_items_dedup)} items")
    
    return _items_dedup


# === BAGIAN 2 MULAI ===

# =========================================================
# 🤖 AUTO-DETECT CALIBRATION
# =========================================================
def _auto_detect_calibration(items, image_w, image_h):
    """Auto-detect area kalender dari keyword header."""
    _y_start = int(image_h * 0.30)
    _y_end = int(image_h * 0.95)
    _x_start = 0
    _x_end = image_w
    
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
        "x_start": _x_start, "x_end": _x_end,
        "y_start": _y_start, "y_end": _y_end,
        "auto": True,
    }


# =========================================================
# 🎯 FILTER BY CALIB
# =========================================================
def filter_items_by_calib(items, calib):
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
# 🔍 GROUP BY ROW
# =========================================================
def _group_by_row(items, tolerance=25):
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
# 🔍 PAIR (BY X + COLOR FALLBACK)
# =========================================================
def _pair_tanggal_kode(tanggal_items, kode_items, image=None):
    _pairs = []
    if not tanggal_items:
        return _pairs
    
    _tgl_rows = _group_by_row(tanggal_items, tolerance=25)
    _kode_rows = _group_by_row(kode_items, tolerance=25) if kode_items else []
    
    print(f"[PAIR v19] Tgl rows: {len(_tgl_rows)}, Kode rows: {len(_kode_rows)}")
    
    for _tgl_row in _tgl_rows:
        if not _tgl_row:
            continue
        
        _tgl_y = _tgl_row[0]["y_center"]
        
        # Cari kode row di bawah
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
        
        for _tgl_item in _tgl_row:
            _tgl_x = _tgl_item["x_center"]
            _tgl_y_item = _tgl_item["y_center"]
            
            _best_kode = None
            _best_dx = 999999
            
            if _best_kode_row:
                for _kode_item in _best_kode_row:
                    _kode_x = _kode_item["x_center"]
                    _dx = abs(_kode_x - _tgl_x)
                    if _dx < 60 and _dx < _best_dx:
                        _best_dx = _dx
                        _best_kode = _kode_item["kode"]
            
            # FALLBACK WARNA
            if not _best_kode and image is not None:
                _cell_x1 = int(_tgl_x - 40)
                _cell_x2 = int(_tgl_x + 40)
                _cell_y1 = int(_tgl_y_item + 20)
                _cell_y2 = int(_tgl_y_item + 70)
                
                _rgb = _sample_cell_color(image, _cell_x1, _cell_y1, _cell_x2, _cell_y2)
                if _rgb:
                    _best_kode = _warna_to_kode(*_rgb)
                    if _best_kode:
                        print(f"[FALLBACK] Tgl {_tgl_item['tanggal']} → {_best_kode}")
            
            if _best_kode:
                _pairs.append({
                    "tanggal": _tgl_item["tanggal"],
                    "kode": _best_kode,
                })
    
    # Dedup
    _unique = {}
    for _pair in _pairs:
        if _pair["tanggal"] not in _unique:
            _unique[_pair["tanggal"]] = _pair
    
    return list(_unique.values())


# =========================================================
# 🎨 SAMPLE WARNA CELL
# =========================================================
def _sample_cell_color(image, x1, y1, x2, y2):
    try:
        _np_img = np.array(image)
        _h, _w = _np_img.shape[:2]
        _x1 = max(0, min(x1, _w))
        _x2 = max(0, min(x2, _w))
        _y1 = max(0, min(y1, _h))
        _y2 = max(0, min(y2, _h))
        
        if _x2 <= _x1 or _y2 <= _y1:
            return None
        
        _cell = _np_img[_y1:_y2, _x1:_x2]
        if _cell.size == 0:
            return None
        
        _flat = _cell.reshape(-1, 3)
        _non_white = _flat[~((_flat[:, 0] > 240) & (_flat[:, 1] > 240) & (_flat[:, 2] > 240))]
        
        if len(_non_white) == 0:
            return None
        
        return (
            int(np.median(_non_white[:, 0])),
            int(np.median(_non_white[:, 1])),
            int(np.median(_non_white[:, 2])),
        )
    except:
        return None


# =========================================================
# 🔍 OCR UTAMA v19
# =========================================================
def ocr_kalender_screenshot(image_bytes, calib=None):
    if not TESSERACT_AVAILABLE:
        return {"success": False, "tanggal_list": [], "raw_text": "", "error": "Tesseract tidak tersedia"}
    
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        print(f"[OCR v19] Image: {_w}x{_h}")
        
        # Double OCR
        _all_items = _ocr_with_coords(_img)
        print(f"[OCR v19] Total items: {len(_all_items)}")
        
        # Auto-detect
        _auto_applied = False
        if calib is None:
            calib = _auto_detect_calibration(_all_items, _w, _h)
            _auto_applied = True
            print(f"[OCR v19] Auto-calib: {calib}")
        
        # Filter
        _kalender_items = filter_items_by_calib(_all_items, calib)
        print(f"[OCR v19] After filter: {len(_kalender_items)}")
        
        _tanggal_items = [i for i in _kalender_items if i["jenis"] == "TANGGAL"]
        _kode_items = [i for i in _kalender_items if i["jenis"] == "KODE"]
        print(f"[OCR v19] Tanggal: {len(_tanggal_items)}, Kode: {len(_kode_items)}")
        
        # Pair
        _pairs = _pair_tanggal_kode(_tanggal_items, _kode_items, image=_img)
        print(f"[OCR v19] Pairs: {len(_pairs)}")
        
        # Build
        _tanggal_list = []
        for _pair in _pairs:
            _tanggal_list.append({
                "tanggal_int": _pair["tanggal"],
                "kode": _pair["kode"],
                "confidence": "MEDIUM",
                "sumber": "koordinat",
            })
        
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
        return {"success": False, "tanggal_list": [], "raw_text": "", "error": str(e)[:200]}


# =========================================================
# 🎨 ANNOTATED IMAGE
# =========================================================
def ocr_debug_visual(image_bytes, calib=None):
    if not TESSERACT_AVAILABLE:
        return None, []
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        _items = _ocr_with_coords(_img)
        _draw = ImageDraw.Draw(_img)
        
        if calib:
            _x1 = calib.get("x_start", 0)
            _x2 = calib.get("x_end", _w)
            _y1 = calib.get("y_start", 0)
            _y2 = calib.get("y_end", _h)
            _draw.rectangle([_x1, _y1, _x2, _y2], outline=(0, 255, 0), width=4)
        
        for _item in _items:
            _x1 = _item["x"]
            _y1 = _item["y"]
            _x2 = _item["x_end"]
            _y2 = _item["y_end"]
            
            if _item["jenis"] == "TANGGAL":
                _color = (0, 255, 0)
            elif _item["jenis"] == "KODE":
                _color = (0, 150, 255)
            else:
                _color = (255, 100, 100)
            
            _draw.rectangle([_x1, _y1, _x2, _y2], outline=_color, width=2)
            
            _label = f"{_item['text'][:8]}({_x1},{_y1})"
            try:
                _draw.text((_x1, max(0, _y1 - 12)), _label, fill=_color)
            except Exception:
                pass
        
        return _img, _items
    except Exception as e:
        print(f"[DEBUG VISUAL ERROR] {e}")
        return None, []


# =========================================================
# 🧠 PARSER + SAVE + LOG
# =========================================================
def parse_kalender_ke_shift(tanggal_list, bulan, tahun, nama):
    _shift_map = {}
    if not tanggal_list:
        return {"nama": str(nama).strip().upper(), "bulan": bulan, "tahun": tahun, "shift_map": {}}
    
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
    
    return {"nama": str(nama).strip().upper(), "bulan": bulan, "tahun": tahun, "shift_map": _shift_map}


def save_ocr_to_master_shift(nama, bulan, tahun, shift_map, sumber="ocr"):
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
        
        _res = sb.table("master_shift").upsert(_rows, on_conflict="tanggal,nama").execute()
        return True, f"{len(_res.data)} shift tersimpan untuk {nama}"
    except Exception as e:
        return False, f"{str(e)[:200]}"


def log_ocr_upload(nama, bulan, tahun, file_name, ocr_result, uploaded_by=""):
    try:
        from modules.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("screenshot_log").insert({
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


def get_palette_info():
    _info = []
    for _kode, _val in HURUF_FUZZY_MAP.items():
        _info.append({"OCR Char": _kode, "Kode": _val})
    return pd.DataFrame(_info)