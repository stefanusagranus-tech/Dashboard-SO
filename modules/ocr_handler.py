"""
OCR Handler
===========
Handle OCR screenshot kalender shift dari web absen.
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
# 🎨 MAPPING WARNA → KODE SHIFT
# =========================================================
# Warna kode shift (dari screenshot):
# - Hijau gelap (#008B8B-ish) → P7 (Pagi)
# - Hijau terang (#00FFCC-ish) → S15 (Siang)  
# - Biru/Ungu (#6666FF-ish) → M22 (Malam)
# - Hitam (#000000-ish) → O/C (Off/Cuti)

def _rgb_to_kode(r, g, b):
    """Deteksi kode shift dari warna RGB."""
    # Hitam → Off
    if r < 80 and g < 80 and b < 80:
        return "O"
    
    # Biru/Ungu → Malam
    if b > 180 and r < 150 and g < 150:
        return "M22"
    
    # Hijau terang → Siang
    if g > 200 and r < 150 and b > 150 and b < 230:
        return "S15"
    
    # Hijau gelap → Pagi
    if g > 150 and r < 120 and b < 180:
        return "P7"
    
    # Default
    return None


# =========================================================
# 🔍 FUNGSI OCR UTAMA
# =========================================================
def ocr_kalender_screenshot(image_bytes):
    """
    OCR screenshot kalender shift.
    
    Args:
        image_bytes: bytes file gambar
    
    Returns:
        dict {
            "success": bool,
            "tanggal_list": [{tanggal: int, kode: str, warna: str}],
            "raw_text": str,
            "error": str
        }
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
        
        # Convert ke RGB
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        # Get image size
        _w, _h = _img.size
        
        # ============================================
        # 1. OCR TEXT (untuk dapat tanggal)
        # ============================================
        _text = pytesseract.image_to_string(
            _img,
            config="--psm 6 -c tessedit_char_whitelist=0123456789",
        )
        
        # Extract angka 1-31
        _angka_all = re.findall(r'\b([1-9]|[12][0-9]|3[01])\b', _text)
        _angka_list = sorted(set(int(a) for a in _angka_all))
        
        # ============================================
        # 2. ANALISIS WARNA (untuk deteksi kode shift)
        # ============================================
        _np_img = np.array(_img)
        _tanggal_list = []
        
        # Cari grid tanggal (asumsi 7 kolom × 5 baris)
        # Bagi area gambar jadi grid
        _grid_cols = 7
        _grid_rows = 5
        
        # Area grid (biasanya di tengah-bawah gambar)
        _grid_top = int(_h * 0.20)      # mulai 20% dari atas
        _grid_bottom = int(_h * 0.90)   # sampai 90% dari atas
        _grid_height = _grid_bottom - _grid_top
        _cell_height = _grid_height // _grid_rows
        
        _grid_left = int(_w * 0.05)
        _grid_right = int(_w * 0.95)
        _grid_width = _grid_right - _grid_left
        _cell_width = _grid_width // _grid_cols
        
        # Iterasi tiap cell
        for _row in range(_grid_rows):
            for _col in range(_grid_cols):
                _cell_y1 = _grid_top + _row * _cell_height
                _cell_y2 = _cell_y1 + _cell_height
                _cell_x1 = _grid_left + _col * _cell_width
                _cell_x2 = _cell_x1 + _cell_width
                
                # Crop cell (tengahnya aja, biar fokus di kode)
                _cx1 = _cell_x1 + int(_cell_width * 0.15)
                _cx2 = _cell_x2 - int(_cell_width * 0.15)
                _cy1 = _cell_y1 + int(_cell_height * 0.40)
                _cy2 = _cell_y2 - int(_cell_height * 0.10)
                
                _cell_img = _img.crop((_cx1, _cy1, _cx2, _cy2))
                _cell_np = np.array(_cell_img)
                
                if _cell_np.size == 0:
                    continue
                
                # Rata-rata warna cell
                _avg_r = int(np.mean(_cell_np[:, :, 0]))
                _avg_g = int(np.mean(_cell_np[:, :, 1]))
                _avg_b = int(np.mean(_cell_np[:, :, 2]))
                
                # Deteksi kode dari warna
                _kode = _rgb_to_kode(_avg_r, _avg_g, _avg_b)
                
                if _kode:
                    _warna_hex = f"#{_avg_r:02X}{_avg_g:02X}{_avg_b:02X}"
                    _tanggal_list.append({
                        "tanggal": len(_tanggal_list) + 1,  # placeholder
                        "kode": _kode,
                        "warna": _warna_hex,
                    })
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "raw_text": _text,
            "angka_detected": _angka_list,
            "error": "",
        }
    
    except Exception as e:
        return {
            "success": False,
            "tanggal_list": [],
            "raw_text": "",
            "error": str(e)[:200],
        }


# =========================================================
# 🧠 PARSER: MATCH TANGGAL + KODE
# =========================================================
def parse_kalender_ke_shift(tanggal_list, bulan, tahun, nama):
    """
    Convert hasil OCR ke shift_map.
    
    Returns:
        dict {
            "nama": str,
            "bulan": int,
            "tahun": int,
            "shift_map": {tanggal_str: kode},
        }
    """
    _shift_map = {}
    
    for _item in tanggal_list:
        try:
            _tgl_num = int(_item["tanggal"])
            _kode = _item["kode"]
            
            # Validasi tanggal
            if _tgl_num < 1 or _tgl_num > 31:
                continue
            
            # Build date
            try:
                _tgl = date(tahun, bulan, _tgl_num)
            except ValueError:
                continue
            
            _tgl_str = _tgl.isoformat()
            _shift_map[_tgl_str] = _kode
        except Exception:
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
    """
    Simpan hasil OCR ke tabel master_shift.
    
    Args:
        nama: str
        bulan: int
        tahun: int
        shift_map: dict {tanggal_str: kode}
        sumber: 'ocr'
    """
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
        
        # Upsert
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
