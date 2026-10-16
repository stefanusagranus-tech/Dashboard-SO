"""
OCR AI Handler — Backend Version
=================================
- Baca gambar SO via Gemini
- Backend-compatible (no Streamlit)
"""

import io
import json
import os
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo

try:
    from google import genai
    from google.genai import types as genai_types
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


MODEL_PRIORITY = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-pro-preview",
]


def _get_api_key():
    """Ambil GEMINI_API_KEY dari env."""
    return os.getenv("GEMINI_API_KEY", "")


# =========================================================
# 📊 OCR SO TABLE
# =========================================================
def ocr_so_table(image_bytes):
    """OCR gambar tabel SO → text."""
    if not GEMINI_AVAILABLE:
        return {"success": False, "text": "", "error": "Gemini not available", "model": ""}

    try:
        _api_key = _get_api_key()
        if not _api_key:
            return {"success": False, "text": "", "error": "GEMINI_API_KEY belum diset", "model": ""}

        _client = genai.Client(api_key=_api_key)
        _img = Image.open(io.BytesIO(image_bytes))

        _prompt = """Baca SEMUA BARIS DATA dari tabel laporan Stock Opname di gambar ini.

TUGAS UTAMA:
Extract setiap baris produk dari tabel. Format: 1 baris = 1 produk.

Contoh format output (plain text, JANGAN ada header):
1 444756 WOW SPAGETI BOLOGNESE 76G 900 51 51 0 5333.58
2 443704 FIESTA RTG SOSIS SPICY KOREAN 60G 900 17 17 0 -5926.15

ATURAN:
1. Copy SEMUA baris yang ada
2. Nomor di awal — copy apa adanya
3. PLU = angka 6+ digit
4. Nama barang — copy persis
5. Rak = kode rak (angka 2-4 digit, atau Q61/QA1)
6. Stock = angka qty sistem
7. Fisik = angka qty fisik
8. Plus/Minus = qty var
9. Selisih Rupiah = nominal adjust

JANGAN tambah header, JANGAN tambah penjelasan apapun.
LANGSUNG baris data-nya aja, satu baris per produk.
"""

        _last_error = None
        _response = None
        _model_used = None

        for _model_name in MODEL_PRIORITY:
            try:
                print(f"[OCR SO] Trying {_model_name}...")
                _resp = _client.models.generate_content(
                    model=_model_name,
                    contents=[_prompt, _img],
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=8192,
                    ),
                )

                if _resp and hasattr(_resp, "text") and _resp.text:
                    _response = _resp
                    _model_used = _model_name
                    print(f"[OCR SO] Success: {_model_name}")
                    break
                else:
                    _last_error = f"Empty response dari {_model_name}"
                    continue
            except Exception as _e:
                _last_error = str(_e)[:200]
                print(f"[OCR SO] {_model_name} error: {_last_error}")
                continue

        if _response is None:
            _err_lower = (_last_error or "").lower()
            if "429" in _err_lower or "quota" in _err_lower:
                return {
                    "success": False,
                    "text": "",
                    "error": "Quota Gemini habis. Coba lagi nanti.",
                    "model": "",
                }
            return {"success": False, "text": "", "error": _last_error or "Unknown error", "model": ""}

        _text = _response.text.strip()
        _text = re.sub(r'^```\w*\s*', '', _text)
        _text = re.sub(r'\s*```$', '', _text)

        print(f"[OCR SO] Text length: {len(_text)}")

        return {
            "success": True,
            "text": _text,
            "error": "",
            "model": _model_used,
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"success": False, "text": "", "error": str(e)[:300], "model": ""}


# =========================================================
# 🔍 DETEKSI TIPE GAMBAR
# =========================================================
def ocr_auto_detect(image_bytes):
    """Auto-detect: kalender shift atau tabel SO?"""
    if not GEMINI_AVAILABLE:
        return {"success": False, "type": "unknown", "error": "Gemini not available"}

    try:
        _api_key = _get_api_key()
        if not _api_key:
            return {"success": False, "type": "unknown", "error": "GEMINI_API_KEY belum diset"}

        _client = genai.Client(api_key=_api_key)
        _img = Image.open(io.BytesIO(image_bytes))

        _prompt = """Lihat gambar ini. Apa isinya?

Jawab HANYA dengan 1 kata:
- "SO_TABLE" kalau ini tabel laporan Stock Opname
- "SHIFT" kalau ini kalender shift
- "UNKNOWN" kalau gak jelas

Jawab SATU KATA aja."""

        for _model_name in MODEL_PRIORITY:
            try:
                _resp = _client.models.generate_content(
                    model=_model_name,
                    contents=[_prompt, _img],
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=20,
                    ),
                )
                if _resp and hasattr(_resp, "text") and _resp.text:
                    _answer = _resp.text.strip().upper()
                    print(f"[OCR Detect] Answer: {_answer}")
                    if "SHIFT" in _answer:
                        return {"success": True, "type": "SHIFT"}
                    elif "SO" in _answer or "TABLE" in _answer:
                        return {"success": True, "type": "SO_TABLE"}
                    else:
                        return {"success": True, "type": "UNKNOWN"}
            except Exception as _e:
                print(f"[OCR Detect] {_model_name} error: {_e}")
                continue

        return {"success": False, "type": "unknown", "error": "Semua model gagal"}

    except Exception as e:
        return {"success": False, "type": "unknown", "error": str(e)[:200]}