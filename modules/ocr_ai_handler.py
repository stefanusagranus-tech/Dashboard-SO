"""
OCR AI Handler v21
==============
Pakai Google Gemini 3.8 Flash + Auto-Fallback.
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
# 📋 MODEL PRIORITY (urut dari paling baru)
# =========================================================
MODEL_PRIORITY = [
    "gemini-3.8-flash",         # ← PALING BARU (rekomendasi Google)
    "gemini-3-flash",            # ← Fallback 1
    "gemini-2.0-flash",          # ← Fallback 2
    "gemini-2.0-flash-exp",      # ← Fallback 3
    "gemini-1.5-flash-latest",   # ← Fallback 4
    "gemini-1.5-pro-latest",     # ← Fallback 5
]


# =========================================================
# 🤖 LIST MODEL YANG TERSEDIA
# =========================================================
def list_available_models(api_key=None):
    """Ambil daftar model yang tersedia untuk API key ini."""
    if not GEMINI_AVAILABLE:
        return []
    
    try:
        _api_key = api_key or st.secrets.get("GEMINI_API_KEY", "")
        if not _api_key:
            return []
        
        genai.configure(api_key=_api_key)
        
        _models = []
        for _m in genai.list_models():
            if "generateContent" in _m.supported_generation_methods:
                _models.append(_m.name.replace("models/", ""))
        
        return _models
    except Exception as e:
        print(f"[LIST MODEL ERROR] {e}")
        return []


# =========================================================
# 🤖 OCR VIA GEMINI (v21)
# =========================================================
def ocr_via_gemini(image_bytes, nama_personil="", bulan=1, tahun=2026):
    """
    Kirim gambar ke Gemini, minta baca kalender shift.
    Auto-fallback ke model lain kalau error.
    """
    if not GEMINI_AVAILABLE:
        return {"success": False, "shift_map": {}, "error": "google-generativeai belum install"}
    
    try:
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        print(f"[GEMINI v21] API key length: {len(_api_key)}")
        print(f"[GEMINI v21] API key prefix: {_api_key[:15]}...")
        
        if not _api_key:
            return {"success": False, "shift_map": {}, "error": "GEMINI_API_KEY belum diset di secrets"}
        
        genai.configure(api_key=_api_key)
        print(f"[GEMINI v21] Configured OK")
        
        # ============================================
        # OPEN IMAGE
        # ============================================
        _img = Image.open(io.BytesIO(image_bytes))
        print(f"[GEMINI v21] Image: {_img.size}")
        
        # ============================================
        # BUILD PROMPT
        # ============================================
        _nama_bulan = ["Januari","Februari","Maret","April","Mei","Juni",
                       "Juli","Agustus","September","Oktober","November","Desember"][bulan-1]
        
        _prompt = f"""Baca kalender shift ini dengan SANGAT TELITI.

Konteks:
- Nama Personil: {nama_personil}
- Bulan: {_nama_bulan} {tahun}

Kode shift yang mungkin:
- P7/P8/P9 = Pagi (hijau)
- S12/S15/S17 = Siang (hijau terang)
- M18/M22/M23 = Malam (biru/ungu)
- O = Off/Libur (hitam)
- C = Cuti
- L = Libur (merah muda)
- HP = Hari Pendek
- D = Dini Hari (kuning)
- AO = Additional Off
- I = Izin
- SK = Sakit

TUGAS:
1. Lihat setiap kotak tanggal 1-31 pada kalender
2. Untuk tiap tanggal yang ADA kotak shift-nya, tulis kodenya
3. Ambil huruf depan + angka (contoh: "M22-MALAM" → "M22")
4. Kalau kotak kosong, SKIP

FORMAT OUTPUT (JSON valid, TANPA markdown):
{{
  "shift_map": {{
    "1": "M22",
    "2": "M22",
    "3": "S15"
  }}
}}

Output HANYA JSON, tidak ada penjelasan.
"""
        
        # ============================================
        # COBA MODEL SATU-SATU (AUTO-FALLBACK)
        # ============================================
        _last_error = None
        _response = None
        _model_used = None
        
        for _model_name in MODEL_PRIORITY:
            try:
                print(f"[GEMINI v21] Trying model: {_model_name}")
                _model = genai.GenerativeModel(_model_name)
                
                _response = _model.generate_content([_prompt, _img])
                _model_used = _model_name
                print(f"[GEMINI v21] ✅ Success with: {_model_name}")
                break
            
            except Exception as _e:
                _last_error = str(_e)
                print(f"[GEMINI v21] ❌ {_model_name} gagal: {_last_error[:150]}")
                continue
        
        if _response is None:
            return {
                "success": False,
                "shift_map": {},
                "error": f"Semua model gagal. Last error: {_last_error[:200]}",
            }
        
        # ============================================
        # PARSE RESPONSE
        # ============================================
        _text = _response.text.strip()
        print(f"[GEMINI v21] Response length: {len(_text)}")
        print(f"[GEMINI v21] First 300: {_text[:300]}")
        
        # Clean JSON
        _json_match = re.search(r'\{[\s\S]*\}', _text)
        if not _json_match:
            return {
                "success": False,
                "shift_map": {},
                "error": "Response gak ada JSON",
                "raw_response": _text,
            }
        
        _json_str = _json_match.group(0)
        _data = json.loads(_json_str)
        
        # ============================================
        # BUILD SHIFT MAP
        # ============================================
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
            "model_used": _model_used,
            "error": "",
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"success": False, "shift_map": {}, "error": str(e)[:300], "raw_response": ""}


# =========================================================
# 🎯 WRAPPER — v21
# =========================================================
def ocr_ai_smart(image_bytes, nama_personil="", bulan=1, tahun=2026):
    """
    Wrapper utama — pakai Gemini 3.8 Flash + auto-fallback.
    """
    _result = ocr_via_gemini(image_bytes, nama_personil, bulan, tahun)
    
    if _result["success"] and _result["shift_map"]:
        _result["provider"] = f"gemini ({_result.get('model_used', '?')})"
        return _result
    
    return {
        "success": False,
        "shift_map": {},
        "error": _result.get("error", "Unknown error"),
        "raw_response": _result.get("raw_response", ""),
        "provider": None,
    }


# === BAGIAN 2 MULAI ===

# =========================================================
# 🔍 HELPER: DEBUG INFO
# =========================================================
def get_debug_info():
    """
    Return info debug: model tersedia, API status.
    """
    _info = {
        "gemini_available": GEMINI_AVAILABLE,
        "api_key_set": False,
        "api_key_length": 0,
        "available_models": [],
        "priority_models": MODEL_PRIORITY,
        "error": "",
    }
    
    try:
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        _info["api_key_set"] = bool(_api_key)
        _info["api_key_length"] = len(_api_key)
        
        if _api_key and GEMINI_AVAILABLE:
            _models = list_available_models(_api_key)
            _info["available_models"] = _models
            
            # Cek model prioritas mana yang tersedia
            _available_priority = [m for m in MODEL_PRIORITY if m in _models]
            _info["available_priority"] = _available_priority
    
    except Exception as e:
        _info["error"] = str(e)[:200]
    
    return _info


# =========================================================
# 🧪 TEST: QUICK TEST GEMINI
# =========================================================
def quick_test_gemini():
    """
    Test koneksi Gemini dengan prompt simple.
    Return: (success, message, model_used)
    """
    if not GEMINI_AVAILABLE:
        return False, "Library google-generativeai belum install", None
    
    try:
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not _api_key:
            return False, "GEMINI_API_KEY belum diset", None
        
        genai.configure(api_key=_api_key)
        
        # Test dengan model prioritas
        for _model_name in MODEL_PRIORITY:
            try:
                print(f"[QUICK TEST] Trying: {_model_name}")
                _model = genai.GenerativeModel(_model_name)
                _response = _model.generate_content("Jawab hanya: OK")
                
                if _response and _response.text:
                    return True, f"✅ Model {_model_name} works!", _model_name
            except Exception as _e:
                print(f"[QUICK TEST] {_model_name} error: {_e}")
                continue
        
        return False, "Semua model gagal", None
    
    except Exception as e:
        return False, f"Error: {str(e)[:200]}", None


# =========================================================
# 📋 LIST MODEL UNTUK UI
# =========================================================
def get_model_info_df():
    """
    Return DataFrame info model untuk display.
    """
    import pandas as pd
    
    _debug = get_debug_info()
    _rows = []
    
    for _model in MODEL_PRIORITY:
        _available = _model in _debug.get("available_models", [])
        _rows.append({
            "Model": _model,
            "Priority": MODEL_PRIORITY.index(_model) + 1,
            "Available": "✅" if _available else "❌",
            "Note": "Paling baru" if MODEL_PRIORITY.index(_model) == 0 else "-",
        })
    
    return pd.DataFrame(_rows)

# =========================================================
# 📊 API USAGE TRACKING
# =========================================================
def get_api_usage_summary():
    """
    Return ringkasan usage dari session state.
    """
    _today = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d")
    
    if "api_usage_tracker" not in st.session_state:
        st.session_state["api_usage_tracker"] = {}
    
    _tracker = st.session_state["api_usage_tracker"]
    
    if _today not in _tracker:
        _tracker[_today] = {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model_used": [],
            "errors": 0,
        }
    
    return _tracker[_today]


def record_api_usage(prompt_tokens=0, output_tokens=0, model_name="", success=True):
    """Catat usage ke session state."""
    _today = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d")
    
    if "api_usage_tracker" not in st.session_state:
        st.session_state["api_usage_tracker"] = {}
    
    if _today not in st.session_state["api_usage_tracker"]:
        st.session_state["api_usage_tracker"][_today] = {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model_used": [],
            "errors": 0,
        }
    
    _t = st.session_state["api_usage_tracker"][_today]
    
    if success:
        _t["requests"] += 1
        _t["input_tokens"] += prompt_tokens
        _t["output_tokens"] += output_tokens
        _t["total_tokens"] += (prompt_tokens + output_tokens)
        if model_name:
            _t["model_used"].append(model_name)
    else:
        _t["errors"] += 1
    
    return _t


# =========================================================
# UPDATE: OCR VIA GEMINI — DENGAN USAGE TRACKING
# =========================================================
def ocr_via_gemini(image_bytes, nama_personil="", bulan=1, tahun=2026):
    # ... (kode sama seperti v21) ...
    
    try:
        # ... (sampai response sukses) ...
        
        _response = _model.generate_content([_prompt, _img])
        _model_used = _model_name
        
        # ✅ RECORD USAGE
        try:
            _usage = getattr(_response, "usage_metadata", None)
            if _usage:
                record_api_usage(
                    prompt_tokens=getattr(_usage, "prompt_token_count", 0),
                    output_tokens=getattr(_usage, "candidates_token_count", 0),
                    model_name=_model_used,
                    success=True,
                )
            else:
                record_api_usage(model_name=_model_used, success=True)
        except Exception as _e_usage:
            print(f"[USAGE TRACK ERROR] {_e_usage}")
        
        # ... (parse response) ...
    
    except Exception as e:
        # ✅ RECORD ERROR
        try:
            record_api_usage(success=False)
        except:
            pass
        return {"success": False, "shift_map": {}, "error": str(e)[:300]}