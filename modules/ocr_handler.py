"""
OCR Handler v6
==============
Handle OCR screenshot kalender shift web absen.

Mode:
- Full palette (semua kode)
- Deteksi huruf awal (P, S, M, D, H, O, C, I, A, L, R, E)
- Warna sebagai fallback
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
# 🎨 COLOR PALETTE — Berdasarkan Screenshot Web Absen
# =========================================================
# Setiap kode dipetakan ke WARNA RGB + HURUF AWAL
COLOR_PALETTE = {
    # ═══════════════════════════════════════════
    # 🟡 DINI HARI & HARI PENDEK (Kuning Terang)
    # ═══════════════════════════════════════════
    "D": {
        "label": "Dini Hari",
        "rgb": (240, 240, 100),      # Kuning terang
        "hex": "#F0F064",
        "tolerance": 80,
        "huruf": ["D"],
    },
    "HP": {
        "label": "Hari Pendek",
        "rgb": (240, 240, 100),      # Kuning terang (sama dengan D)
        "hex": "#F0F064",
        "tolerance": 80,
        "huruf": ["HP", "H"],
    },
    
    # ═══════════════════════════════════════════
    # 🟢 PAGI (Hijau Sedang)
    # ═══════════════════════════════════════════
    "P": {
        "label": "Pagi",
        "rgb": (100, 230, 180),      # Hijau medium
        "hex": "#64E6B4",
        "tolerance": 70,
        "huruf": ["P"],
    },
    
    # ═══════════════════════════════════════════
    # 💚 SIANG (Hijau Sangat Terang)
    # ═══════════════════════════════════════════
    "S": {
        "label": "Siang",
        "rgb": (100, 250, 210),      # Hijau sangat terang
        "hex": "#64FAD2",
        "tolerance": 70,
        "huruf": ["S"],
    },
    
    # ═══════════════════════════════════════════
    # 🟣 MALAM (Biru/Ungu)
    # ═══════════════════════════════════════════
    "M": {
        "label": "Malam",
        "rgb": (130, 130, 240),      # Biru/ungu
        "hex": "#8282F0",
        "tolerance": 70,
        "huruf": ["M"],
    },
    
    # ═══════════════════════════════════════════
    # ⚫ OFF / CUTI / IZIN (Hitam)
    # ═══════════════════════════════════════════
    "O": {
        "label": "Off",
        "rgb": (20, 20, 20),
        "hex": "#141414",
        "tolerance": 50,
        "huruf": ["O"],
    },
    "C": {
        "label": "Cuti",
        "rgb": (20, 20, 20),
        "hex": "#141414",
        "tolerance": 50,
        "huruf": ["C"],
    },
    "I": {
        "label": "Izin",
        "rgb": (20, 20, 20),
        "hex": "#141414",
        "tolerance": 50,
        "huruf": ["I"],
    },
    "SK": {
        "label": "Sakit",
        "rgb": (20, 20, 20),
        "hex": "#141414",
        "tolerance": 50,
        "huruf": ["S"],
    },
    "AO": {
        "label": "Additional Off",
        "rgb": (20, 20, 20),
        "hex": "#141414",
        "tolerance": 50,
        "huruf": ["AO", "A"],
    },
    "EO": {
        "label": "Extra Off",
        "rgb": (20, 20, 20),
        "hex": "#141414",
        "tolerance": 50,
        "huruf": ["EO", "E"],
    },
    "RO": {
        "label": "Replace Off",
        "rgb": (20, 20, 20),
        "hex": "#141414",
        "tolerance": 50,
        "huruf": ["RO", "R"],
    },
    
    # ═══════════════════════════════════════════
    # 🔴 LIBUR (Merah Muda)
    # ═══════════════════════════════════════════
    "L": {
        "label": "Libur",
        "rgb": (250, 150, 150),
        "hex": "#FA9696",
        "tolerance": 70,
        "huruf": ["L"],
    },
    
    # ═══════════════════════════════════════════
    # 🟣 LONG SHIFT (Ungu)
    # ═══════════════════════════════════════════
    "LO": {
        "label": "Long Shift",
        "rgb": (150, 50, 200),
        "hex": "#9632C8",
        "tolerance": 70,
        "huruf": ["LO"],
    },
}


# =========================================================
# 🎨 DETEKSI WARNA → KODE
# =========================================================
def _rgb_to_kode_v2(r, g, b):
    """
    Deteksi kode shift dari warna RGB.
    Return: (kode, confidence, distance)
    """
    # Skip background putih
    if r > 230 and g > 230 and b > 230:
        return None, 0, 999999
    
    # Skip abu-abu netral (border/background)
    _max_c = max(r, g, b)
    _min_c = min(r, g, b)
    if (_max_c - _min_c) < 20 and r > 150:
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
    """
    Deteksi kode dari huruf awal text.
    
    Contoh:
        "M22-MALAM" → M22 (kategori M)
        "S15-SIANG" → S15 (kategori S)
        "O-OFF" → O
        "P7" → P7
        "HP3" → HP
    """
    if not text:
        return None, 0
    
    _text_upper = str(text).upper().strip()
    
    # Bersihkan whitespace & simbol
    _text_upper = re.sub(r'[^A-Z0-9]', '', _text_upper)
    
    if not _text_upper:
        return None, 0
    
    # Cek exact match dengan huruf di palette
    for _kode, _info in COLOR_PALETTE.items():
        for _huruf in _info["huruf"]:
            _huruf_upper = _huruf.upper()
            
            if _text_upper == _huruf_upper:
                return _kode, 100
            if _text_upper.startswith(_huruf_upper):
                return _kode, 90
    
    # Fallback: cek 2 huruf pertama
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


# =========================================================
# 🔍 OCR UTAMA — v6 (Priority Huruf Awal)
# =========================================================
def ocr_kalender_screenshot(image_bytes):
    """
    OCR screenshot v6 — Deteksi via HURUF AWAL.
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
        print(f"[OCR v6] Image: {_w}x{_h}")
        
        # ============================================
        # OCR TEXT FULL
        # ============================================
        _text_full = pytesseract.image_to_string(_img, config="--psm 6")
        
        # ============================================
        # DETEKSI KALENDER AREA
        # ============================================
        _np_img = np.array(_img)
        
        # Cari area kalender (bagian bawah biasanya)
        _kalender_top = int(_h * 0.60)
        _kalender_bottom = int(_h * 0.95)
        _kalender_height = _kalender_bottom - _kalender_top
        
        _grid_cols = 7
        _grid_rows = 5
        _cell_h = _kalender_height // _grid_rows
        _cell_w = _w // _grid_cols
        
        print(f"[OCR v6] Grid: {_grid_cols}×{_grid_rows}, cell: {_cell_w}×{_cell_h}")
        
        # ============================================
        # ASUNSI: Tanggal 1 di kolom ke-4 (Kamis)
        # Sesuaikan kalau perlu
        # ============================================
        _tanggal_1_col = 3
        _tanggal_1_row = 0
        
        # ============================================
        # ANALISIS PER CELL
        # ============================================
        _tanggal_list = []
        _debug_info = []
        
        for _row in range(_grid_rows):
            for _col in range(_grid_cols):
                _y1 = _kalender_top + _row * _cell_h
                _y2 = _y1 + _cell_h
                _x1 = _col * _cell_w
                _x2 = _x1 + _cell_w
                
                # Crop cell (fokus di bagian atas-tengah cell)
                _cx1 = max(0, _x1 + int(_cell_w * 0.05))
                _cx2 = min(_w, _x2 - int(_cell_w * 0.05))
                _cy1 = max(0, _y1 + int(_cell_h * 0.15))
                _cy2 = min(_h, _y2 - int(_cell_h * 0.15))
                
                if _cx2 <= _cx1 or _cy2 <= _cy1:
                    continue
                
                _cell_img = _img.crop((_cx1, _cy1, _cx2, _cy2))
                _cell_np = np.array(_cell_img)
                
                if _cell_np.size == 0:
                    continue
                
                # ============================================
                # METODE 1: OCR TEXT CELL (PRIORITAS)
                # ============================================
                _kode_huruf = None
                _conf_huruf = 0
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
                
                # ============================================
                # METODE 2: WARNA (FALLBACK)
                # ============================================
                # Sample multiple pixel points
                _h_cell, _w_cell = _cell_np.shape[:2]
                _points = [
                    _cell_np[_h_cell // 2, _w_cell // 2],
                    _cell_np[_h_cell // 3, _w_cell // 3],
                    _cell_np[_h_cell // 3, 2 * _w_cell // 3],
                ]
                
                _r = int(np.median([p[0] for p in _points]))
                _g = int(np.median([p[1] for p in _points]))
                _b = int(np.median([p[2] for p in _points]))
                
                _warna_hex = f"#{_r:02X}{_g:02X}{_b:02X}"
                
                _kode_warna, _conf_warna, _dist = _rgb_to_kode_v2(_r, _g, _b)
                
                # ============================================
                # VOTING
                # ============================================
                _kode_final = None
                _confidence = "LOW"
                _sumber = ""
                
                if _kode_huruf and _kode_warna:
                    if _kode_huruf == _kode_warna:
                        _kode_final = _kode_huruf
                        _confidence = "HIGH"
                        _sumber = "huruf+warna"
                    else:
                        # Prioritaskan huruf (text lebih akurat)
                        _kode_final = _kode_huruf
                        _confidence = "MEDIUM"
                        _sumber = f"huruf({_kode_huruf}) vs warna({_kode_warna})"
                elif _kode_huruf:
                    _kode_final = _kode_huruf
                    _confidence = "MEDIUM"
                    _sumber = "huruf"
                elif _kode_warna:
                    _kode_final = _kode_warna
                    _confidence = "MEDIUM"
                    _sumber = "warna"
                
                # Hitung tanggal
                _tanggal_int = (
                    (_row - _tanggal_1_row) * 7 +
                    (_col - _tanggal_1_col) + 1
                )
                
                # Skip kalau di luar 1-31
                if _tanggal_int < 1 or _tanggal_int > 31:
                    continue
                
                # Debug info
                _debug_info.append({
                    "tanggal": _tanggal_int,
                    "row": _row,
                    "col": _col,
                    "text_cell": _text_cell,
                    "kode_huruf": _kode_huruf,
                    "kode_warna": _kode_warna,
                    "final": _kode_final,
                    "rgb": (_r, _g, _b),
                })
                
                if _kode_final:
                    _tanggal_list.append({
                        "tanggal_int": _tanggal_int,
                        "kode": _kode_final,
                        "confidence": _confidence,
                        "sumber": _sumber,
                        "rgb": (_r, _g, _b),
                        "hex": _warna_hex,
                    })
        
        print(f"[OCR v6] Detected: {len(_tanggal_list)} cells")
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _debug_info,
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
# 💾 SIMPAN & LOG
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
# 🎨 HELPER: UPDATE PALETTE
# =========================================================
def update_palette_warna(kode, r, g, b):
    """Update sample warna palette."""
    if kode in COLOR_PALETTE:
        COLOR_PALETTE[kode]["rgb"] = (int(r), int(g), int(b))
        COLOR_PALETTE[kode]["hex"] = f"#{int(r):02X}{int(g):02X}{int(b):02X}"
        return True, f"✅ Palette {kode} diupdate"
    return False, f"❌ Kode {kode} tidak ditemukan"


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