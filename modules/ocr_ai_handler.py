"""
OCR AI Handler
=============
Pakai Google Gemini untuk baca screenshot kalender shift.
Jauh lebih akurat dari Tesseract.
"""

import io
import json
import re
import streamlit as st
from datetime import datetime, date
from zoneinfo import ZoneInfo

try:
    import google.generativeai as genai
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# =========================================================
# 🤖 OCR VIA GEMINI
# =========================================================
def ocr_via_gemini(image_bytes, nama_personil="", bulan=1, tahun=2026):
    """
    Kirim gambar ke Gemini, minta baca kalender shift.
    """
    if not GEMINI_AVAILABLE:
        return {"success": False, "shift_map": {}, "error": "google-generativeai belum install"}
    
    try:
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not _api_key:
            return {"success": False, "shift_map": {}, "error": "GEMINI_API_KEY belum diset di secrets"}
        
        genai.configure(api_key=_api_key)
        
        # Coba model terbaru
        _model_names = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
        ]
        
        _model = None
        _last_error = None
        for _name in _model_names:
            try:
                _model = genai.GenerativeModel(_name)
                # Test aja
                break
            except Exception as _e:
                _last_error = str(_e)
                continue
        
        if _model is None:
            return {"success": False, "shift_map": {}, "error": f"Model gak bisa di-load: {_last_error}"}
        
        # Open image
        _img = Image.open(io.BytesIO(image_bytes))
        
        # Prompt
        _nama_bulan = ["Januari","Februari","Maret","April","Mei","Juni",
                       "Juli","Agustus","September","Oktober","November","Desember"][bulan-1]
        
        _prompt = f"""Baca kalender shift ini dengan SANGAT TELITI.

Konteks:
- Nama: {nama_personil}
- Bulan: {_nama_bulan} {tahun}

Kode shift yang mungkin ada di kalender:
- P7/P8/P9 = Pagi (hijau terang)
- S12/S15/S17 = Siang (hijau muda)
- M18/M22/M23 = Malam (biru/ungu)
- O = Off/Libur (hitam)
- C = Cuti
- L = Libur (merah muda)
- HP = Hari Pendek
- D = Dini Hari (kuning)
- AO = Additional Off
- I = Izin
- SK = Sakit
- LO = Long Shift (ungu)

TUGAS:
Lihat setiap kotak tanggal 1-31 pada kalender. 
Untuk tiap tanggal yang ADA kotak shift-nya, tulis kode shift-nya.

FORMAT OUTPUT (JSON valid, TANPA markdown backtick):
{{
  "shift_map": {{
    "1": "M22",
    "2": "M22",
    "3": "S15",
    "4": "S15",
    "5": "O",
    "...": "..."
  }}
}}

ATURAN PENTING:
1. HANYA tulis tanggal yang ada shift-nya (ada warna)
2. Kalau tanggal kosong/tidak ada kotak, SKIP
3. Kode harus SINGKAT: ambil huruf depan + angka (contoh: "M22-MALAM" → "M22")
4. Output HANYA JSON, gak ada penjelasan
5. Tanggal dalam string angka ("1", "2", "3", dst)
"""
        
        # Generate
        _response = _model.generate_content([_prompt, _img])
        _text = _response.text.strip()
        
        print(f"[GEMINI] Response length: {len(_text)}")
        print(f"[GEMINI] First 300 chars: {_text[:300]}")
        
        # Clean JSON
        _json_match = re.search(r'\{[\s\S]*\}', _text)
        if not _json_match:
            return {"success": False, "shift_map": {}, "error": f"Response gak ada JSON", "raw_response": _text}
        
        _json_str = _json_match.group(0)
        _data = json.loads(_json_str)
        
        # Build shift_map
        _shift_map = {}
        for _tgl_str, _kode in _data.get("shift_map", {}).items():
            try:
                _tgl_int = int(str(_tgl_str).strip())
                if 1 <= _tgl_int <= 31:
                    _tgl = date(tahun, bulan, _tgl_int)
                    _shift_map[_tgl.isoformat()] = str(_kode).strip().upper()
            except Exception:
                continue
        
        return {
            "success": True,
            "shift_map": _shift_map,
            "raw_response": _text,
            "error": "",
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"success": False, "shift_map": {}, "error": str(e)[:300], "raw_response": ""}


# =========================================================
# 🎯 WRAPPER
# =========================================================
def ocr_ai_smart(image_bytes, nama_personil="", bulan=1, tahun=2026):
    """
    Wrapper utama — pakai Gemini.
    """
    _result = ocr_via_gemini(image_bytes, nama_personil, bulan, tahun)
    
    if _result["success"] and _result["shift_map"]:
        _result["provider"] = "gemini"
        return _result
    
    return {
        "success": False,
        "shift_map": {},
        "error": _result.get("error", "Unknown error"),
        "raw_response": _result.get("raw_response", ""),
        "provider": None,
    }
