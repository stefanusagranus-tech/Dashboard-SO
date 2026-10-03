"""
OCR Handler v13
==============
Handle 2 mode screenshot:
- MODE_DESKTOP: text full ("S15-SIANG")
- MODE_HP: text kepotong ("S15", "P7~F")

Approach: koordinat-based, auto-pair tanggal ↔ kode.
"""

import io
import re
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

try:
    import pytesseract
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError as e:
    print(f"[OCR] Library gak tersedia: {e}")
    TESSERACT_AVAILABLE = False


# =========================================================
# 🎨 HURUF AWAL → KODE KATEGORI
# =========================================================
# Ambil huruf awal saja, karena text sering kepotong
HURUF_TO_KODE = {
    "P": "P",       # Pagi
    "S": "S",       # Siang / Sakit (ambigu — prioritaskan Siang)
    "M": "M",       # Malam
    "D": "D",       # Dini Hari
    "H": "HP",      # Hari Pendek
    "O": "O",       # Off
    "C": "C",       # Cuti
    "L": "L",       # Libur / Long Shift
    "I": "I",       # Izin
    "A": "AO",      # Additional Off
    "R": "RO",      # Replace Off
    "E": "EO",      # Extra Off
    "K": "SK",      # Sakit
}

# Prioritas matching (lebih spesifik dulu)
KODE_PRIORITY = ["HP", "AO", "RO", "EO", "LO", "SK", "P", "S", "M", "D", "H", "O", "C", "L", "I", "A", "R", "E", "K"]

# Validasi kode yang valid
VALID_KODE = set(HURUF_TO_KODE.values())


# =========================================================
# 🔍 HELPER: EKSTRAK KODE DARI TEXT
# =========================================================
def _extract_kode_from_text(text):
    """
    Ekstrak kode dari text.
    
    Contoh:
    "S15-SIANG" → S
    "M22-MALAM" → M
    "O-OFF" → O
    "P7~F" → P
    "HP3" → HP
    "AO" → AO
    "SK" → SK
    """
    if not text:
        return None
    
    _text = str(text).upper().strip()
    # Bersihkan simbol
    _text = re.sub(r'[^A-Z0-9]', '', _text)
    
    if not _text:
        return None
    
    # Prioritas: cek 2 huruf dulu (HP, AO, RO, EO, LO, SK)
    _first_2 = _text[:2]
    if _first_2 in ["HP", "AO", "RO", "EO", "LO", "SK"]:
        return _first_2
    
    # Kalau bukan, cek 1 huruf pertama
    _first_1 = _text[:1]
    if _first_1 in HURUF_TO_KODE:
        return HURUF_TO_KODE[_first_1]
    
    return None


# =========================================================
# 🔍 HELPER: DETEKSI MODE
# =========================================================
def _detect_mode(ocr_items):
    """
    Deteksi mode berdasarkan text yang ada.
    
    Returns: "desktop" atau "hp"
    """
    _full_text = " ".join([item["text"] for item in ocr_items]).upper()
    
    # Kalau ada pattern "S15-SIANG" / "M22-MALAM" → desktop
    if re.search(r'[A-Z]\d{1,2}[\-~][A-Z]{3,}', _full_text):
        return "desktop"
    
    # Kalau ada keyword "SIANG"/"MALAM"/"PAGI"/"OFF" → desktop
    if any(kw in _full_text for kw in ["SIANG", "MALAM", "PAGI", "OFF", "CUTI"]):
        return "desktop"
    
    # Default: HP (text pendek)
    return "hp"


# =========================================================
# 🔍 HELPER: OCR + KOORDINAT
# =========================================================
def _ocr_with_coords(image):
    """
    OCR gambar, return list of {text, x, y, w, h}.
    """
    _data = pytesseract.image_to_data(
        image,
        config="--psm 6",
        output_type=pytesseract.Output.DICT,
    )
    
    _items = []
    for _i in range(len(_data["text"])):
        _text = _data["text"][_i].strip()
        _conf = _data["conf"][_i]
        
        if not _text:
            continue
        if _conf < 30:  # skip yang confidence rendah
            continue
        
        _items.append({
            "text": _text,
            "x": int(_data["left"][_i]),
            "y": int(_data["top"][_i]),
            "w": int(_data["width"][_i]),
            "h": int(_data["height"][_i]),
            "conf": int(_conf),
            "x_center": int(_data["left"][_i]) + int(_data["width"][_i]) // 2,
            "y_center": int(_data["top"][_i]) + int(_data["height"][_i]) // 2,
        })
    
    return _items


# =========================================================
# 🔍 HELPER: EKSTRAK TANGGAL & KODE
# =========================================================
def _separate_tanggal_kode(ocr_items):
    """
    Pisahkan item OCR jadi 2 grup:
    - tanggal_items: yang text-nya angka 1-31
    - kode_items: yang text-nya kode shift (P, S, M, dll)
    """
    _tanggal_items = []
    _kode_items = []
    
    for _item in ocr_items:
        _text = _item["text"].strip()
        
        # Cek tanggal (1-31)
        if re.match(r'^\d{1,2}$', _text):
            _tgl = int(_text)
            if 1 <= _tgl <= 31:
                _tanggal_items.append({
                    **_item,
                    "tanggal": _tgl,
                })
                continue
        
        # Cek kode shift
        _kode = _extract_kode_from_text(_text)
        if _kode:
            _kode_items.append({
                **_item,
                "kode": _kode,
            })
    
    return _tanggal_items, _kode_items


# =========================================================
# 🔍 HELPER: AUTO-PAIR
# =========================================================
def _pair_tanggal_kode(tanggal_items, kode_items, mode="hp"):
    """
    Pair tanggal dengan kode berdasarkan POSISI.
    
    Asumsi: tanggal di ATAS, kode di BAWAH.
    Jarak horizontal (x_center) < threshold.
    """
    _pairs = []
    
    # Threshold jarak horizontal (berdasarkan lebar gambar)
    _threshold_x = 80 if mode == "desktop" else 60
    # Threshold jarak vertical (tanggal harus di atas kode)
    _threshold_y_min = 5
    _threshold_y_max = 120 if mode == "desktop" else 150
    
    for _tgl_item in tanggal_items:
        _tgl = _tgl_item["tanggal"]
        _tgl_x = _tgl_item["x_center"]
        _tgl_y = _tgl_item["y_center"]
        
        _best_kode = None
        _best_distance = 999999
        
        for _kode_item in kode_items:
            _kode_x = _kode_item["x_center"]
            _kode_y = _kode_item["y_center"]
            
            # Kode harus di BAWAH tanggal
            _dy = _kode_y - _tgl_y
            if _dy < _threshold_y_min or _dy > _threshold_y_max:
                continue
            
            # Selisih X (horizontal alignment)
            _dx = abs(_kode_x - _tgl_x)
            if _dx > _threshold_x:
                continue
            
            _distance = _dy + _dx
            if _distance < _best_distance:
                _best_distance = _distance
                _best_kode = _kode_item["kode"]
        
        if _best_kode:
            _pairs.append({
                "tanggal": _tgl,
                "kode": _best_kode,
            })
    
    return _pairs


# === BAGIAN 2 MULAI ===

# =========================================================
# 🔍 OCR UTAMA — v13
# =========================================================
def ocr_kalender_screenshot(image_bytes):
    """
    OCR screenshot v13 — Handle 2 mode (Desktop & HP).
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
        print(f"[OCR v13] Image: {_w}x{_h}")
        
        # ============================================
        # 1. OCR WITH COORDINATES
        # ============================================
        _items = _ocr_with_coords(_img)
        print(f"[OCR v13] Items detected: {len(_items)}")
        
        # Filter: cuma ambil area kalender (bawah 30% - 95%)
        # karena header biasanya di atas
        _kalender_items = [
            item for item in _items
            if item["y"] > _h * 0.30 and item["y"] < _h * 0.95
        ]
        
        print(f"[OCR v13] Items in kalender area: {len(_kalender_items)}")
        
        # ============================================
        # 2. DETEKSI MODE
        # ============================================
        _mode = _detect_mode(_kalender_items)
        print(f"[OCR v13] Mode: {_mode}")
        
        # ============================================
        # 3. PISAHKAN TANGGAL & KODE
        # ============================================
        _tanggal_items, _kode_items = _separate_tanggal_kode(_kalender_items)
        
        print(f"[OCR v13] Tanggal items: {len(_tanggal_items)}")
        print(f"[OCR v13] Kode items: {len(_kode_items)}")
        
        # ============================================
        # 4. PAIR TANGGAL ↔ KODE
        # ============================================
        _pairs = _pair_tanggal_kode(_tanggal_items, _kode_items, mode=_mode)
        
        print(f"[OCR v13] Pairs: {len(_pairs)}")
        
        # ============================================
        # 5. BUILD TANGGAL_LIST
        # ============================================
        _tanggal_list = []
        _debug_items = []
        
        for _pair in _pairs:
            _tanggal_list.append({
                "tanggal_int": _pair["tanggal"],
                "kode": _pair["kode"],
                "confidence": "MEDIUM",
                "sumber": f"koordinat_{_mode}",
            })
        
        # Debug: tampilkan semua item
        for _item in _kalender_items:
            _debug_items.append({
                "text": _item["text"],
                "x": _item["x"],
                "y": _item["y"],
                "conf": _item["conf"],
            })
        
        # Build raw text
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
# 🎨 OCR DEBUG — WITH ANNOTATED IMAGE
# =========================================================
def ocr_debug_visual(image_bytes):
    """
    OCR + return gambar annotated (kotak di tiap text).
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
            _is_tanggal = bool(re.match(r'^\d{1,2}$', _text) and 1 <= int(_text) <= 31)
            _kode = _extract_kode_from_text(_text)
            
            # Warna border
            if _is_tanggal:
                _color = (0, 255, 0)  # hijau: tanggal
            elif _kode:
                _color = (0, 150, 255)  # biru: kode
            else:
                _color = (255, 100, 100)  # merah: noise
            
            _draw.rectangle([_x1, _y1, _x2, _y2], outline=_color, width=2)
            _draw.text((_x1, _y1 - 12), _text[:15], fill=_color)
        
        return _img
    
    except Exception as e:
        print(f"[DEBUG VISUAL ERROR] {e}")
        return None


# =========================================================
# 🧠 PARSER: KALENDER → SHIFT MAP
# =========================================================
def parse_kalender_ke_shift(tanggal_list, bulan, tahun, nama):
    """
    Convert hasil OCR ke shift_map.
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
    """Return info kategori kode."""
    _info = []
    for _kode in sorted(VALID_KODE):
        _info.append({
            "Kode": _kode,
            "Deskripsi": f"Kategori {_kode}",
        })
    return pd.DataFrame(_info)