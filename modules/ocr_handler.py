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
    OCR screenshot kalender shift v3.
    
    Metode:
    1. 🎨 Warna — sample dari tengah cell
    2. 🔤 Huruf — OCR text per cell
    
    Voting System:
    - 2 vote (warna + huruf): HIGH confidence
    - 1 vote: MEDIUM confidence
    - 0 vote: skip
    """
    if not TESSERACT_AVAILABLE:
        return {
            "success": False,
            "tanggal_list": [],
            "raw_text": "",
            "error": "Tesseract library tidak tersedia",
        }
    
    try:
        # Load image
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        print(f"[OCR v3] Image size: {_w}x{_h}")
        
        # ============================================
        # 1. OCR TEXT FULL (untuk tanggal & huruf)
        # ============================================
        _text_full = pytesseract.image_to_string(
            _img,
            config="--psm 6",
        )
        
        # ============================================
        # 2. GRID ANALYSIS
        # ============================================
        _np_img = np.array(_img)
        
        # Area kalender (kasar)
        _kalender_top = int(_h * 0.20)
        _kalender_bottom = int(_h * 0.85)
        _kalender_height = _kalender_bottom - _kalender_top
        
        # Grid 7 kolom × 6 baris (max)
        _grid_cols = 7
        _grid_rows = 6
        
        _cell_h = _kalender_height // _grid_rows
        _cell_w = _w // _grid_cols
        
        print(f"[OCR v3] Grid: {_grid_cols}x{_grid_rows}, cell: {_cell_w}x{_cell_h}")
        
        # ============================================
        # 3. ANALISIS PER CELL
        # ============================================
        _tanggal_list = []
        _debug_cells = []
        
        for _row in range(_grid_rows):
            for _col in range(_grid_cols):
                # Posisi cell
                _y1 = _kalender_top + _row * _cell_h
                _y2 = _y1 + _cell_h
                _x1 = _col * _cell_w
                _x2 = _x1 + _cell_w
                
                # Crop cell (tengah aja)
                _cx1 = max(0, _x1 + int(_cell_w * 0.10))
                _cx2 = min(_w, _x2 - int(_cell_w * 0.10))
                _cy1 = max(0, _y1 + int(_cell_h * 0.25))
                _cy2 = min(_h, _y2 - int(_cell_h * 0.10))
                
                if _cx2 <= _cx1 or _cy2 <= _cy1:
                    continue
                
                _cell_img = _img.crop((_cx1, _cy1, _cx2, _cy2))
                _cell_np = np.array(_cell_img)
                
                if _cell_np.size == 0:
                    continue
                
                # ============================================
                # METODE 1: WARNA
                # ============================================
                # Sample warna median
                _median_r = int(np.median(_cell_np[:, :, 0]))
                _median_g = int(np.median(_cell_np[:, :, 1]))
                _median_b = int(np.median(_cell_np[:, :, 2]))
                
                _kode_warna, _conf_warna, _dist = _rgb_to_kode_v2(
                    _median_r, _median_g, _median_b
                )
                
                # ============================================
                # METODE 2: HURUF (OCR cell)
                # ============================================
                _kode_huruf = None
                _conf_huruf = 0
                
                try:
                    _cell_text = pytesseract.image_to_string(
                        _cell_img,
                        config="--psm 7 -c tessedit_char_whitelist=PSMOCA0123456789-~fF",
                    ).strip()
                    
                    if _cell_text:
                        _kode_huruf, _conf_huruf = _huruf_to_kode(_cell_text)
                except Exception:
                    pass
                
                # ============================================
                # VOTING SYSTEM
                # ============================================
                _kode_final = None
                _confidence = "LOW"
                _sumber = ""
                
                if _kode_warna and _kode_huruf:
                    if _kode_warna == _kode_huruf:
                        # ✅ 2 vote SAMA — HIGH confidence
                        _kode_final = _kode_warna
                        _confidence = "HIGH"
                        _sumber = "warna+huruf"
                    else:
                        # ⚠️ 2 vote BEDA — pilih warna (biasanya lebih akurat)
                        _kode_final = _kode_warna
                        _confidence = "MEDIUM"
                        _sumber = f"warna ({_kode_warna}) vs huruf ({_kode_huruf})"
                elif _kode_warna:
                    # 1 vote — warna aja
                    _kode_final = _kode_warna
                    _confidence = "MEDIUM"
                    _sumber = "warna"
                elif _kode_huruf:
                    # 1 vote — huruf aja
                    _kode_final = _kode_huruf
                    _confidence = "MEDIUM"
                    _sumber = "huruf"
                
                # Debug info
                _debug_info = {
                    "row": _row,
                    "col": _col,
                    "rgb": (_median_r, _median_g, _median_b),
                    "warna_detect": _kode_warna,
                    "huruf_detect": _kode_huruf,
                    "final": _kode_final,
                    "confidence": _confidence,
                    "sumber": _sumber,
                }
                _debug_cells.append(_debug_info)
                
                # Add ke result kalau ada kode
                if _kode_final:
                    _tanggal_list.append({
                        "row": _row,
                        "col": _col,
                        "kode": _kode_final,
                        "confidence": _confidence,
                        "sumber": _sumber,
                        "rgb": (_median_r, _median_g, _median_b),
                    })
        
        print(f"[OCR v3] Cells analyzed: {len(_debug_cells)}")
        print(f"[OCR v3] Cells with kode: {len(_tanggal_list)}")
        
        # ============================================
        # 4. POST-PROCESSING: AUTO-FILL TANGGAL
        # ============================================
        # Sekarang kita perlu mapping row/col → tanggal
        
        # Untuk sementara, kasih "tanggal" sequential berdasarkan urutan
        # Nanti user bisa koreksi manual
        for _idx, _item in enumerate(_tanggal_list):
            _item["tanggal_int"] = _idx + 1
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _debug_cells,
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