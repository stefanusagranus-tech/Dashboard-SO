"""
OCR AI Handler v23
==================
- Migrate ke google-genai (SDK baru)
- Fix bug: _model is not defined
- Auto-fallback 5 model
- API usage tracking
- Debug panel support
"""

import io
import json
import re
import streamlit as st
from datetime import datetime, date
from zoneinfo import ZoneInfo

try:
    from google import genai
    from google.genai import types as genai_types
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# =========================================================
# 📋 MODEL PRIORITY (urut dari paling baru)
# =========================================================
MODEL_PRIORITY = [
    "gemini-3.8-flash",              # ✅ Model terbaru (recommended)
    "gemini-3.5-flash-lite",         # ✅ Cepat, hemat
    "gemini-3.1-pro-preview",        # ✅ Fallback pro
]


# =========================================================
# 📊 API USAGE TRACKING
# =========================================================
def get_api_usage_summary():
    """Return ringkasan usage dari session state."""
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
# 🤖 LIST AVAILABLE MODELS
# =========================================================
def list_available_models(api_key=None):
    """Ambil daftar model yang tersedia untuk API key ini."""
    if not GEMINI_AVAILABLE:
        return []

    try:
        _api_key = api_key or st.secrets.get("GEMINI_API_KEY", "")
        if not _api_key:
            return []

        _client = genai.Client(api_key=_api_key)

        _models = []
        for _m in _client.models.list():
            _name = _m.name.replace("models/", "") if hasattr(_m, "name") else ""
            if _name:
                _models.append(_name)

        return _models
    except Exception as e:
        print(f"[LIST MODEL ERROR] {e}")
        return []


# =========================================================
# 🤖 OCR VIA GEMINI (v23 — SDK BARU)
# =========================================================
def ocr_via_gemini(image_bytes, nama_personil="", bulan=1, tahun=2026):
    """
    OCR via Gemini dengan auto-fallback.
    Pake SDK baru: google-genai.
    """
    if not GEMINI_AVAILABLE:
        return {"success": False, "shift_map": {}, "error": "Library google-genai belum install"}

    try:
        # ============================================
        # 1. GET API KEY
        # ============================================
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        print(f"[GEMINI v23] API key length: {len(_api_key)}")
        print(f"[GEMINI v23] API key prefix: {_api_key[:15]}...")

        if not _api_key:
            return {"success": False, "shift_map": {}, "error": "GEMINI_API_KEY belum diset di secrets"}

        _client = genai.Client(api_key=_api_key)
        print(f"[GEMINI v23] Client configured OK")

        # ============================================
        # 2. OPEN IMAGE
        # ============================================
        _img = Image.open(io.BytesIO(image_bytes))
        print(f"[GEMINI v23] Image size: {_img.size}")

        # ============================================
        # 3. BUILD PROMPT
        # ============================================
        _nama_bulan = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        ][bulan - 1]

        _prompt = f"""Baca kalender shift ini dengan SANGAT TELITI.

Konteks:
- Nama Personil: {nama_personil}
- Bulan: {_nama_bulan} {tahun}

Kode shift yang mungkin:
- P7/P8/P9 = Pagi (hijau)
- S12/S13/S14/S15/S16/S17 = Siang (hijau terang)
- M18/M19/M20/M21/M22/M23 = Malam (biru/ungu)
- O = Off/Libur (hitam)
- C = Cuti
- L = Libur (merah muda)
- HP = Hari Pendek
- D = Dini Hari (kuning)
- AO = Additional Off
- I = Izin
- SK = Sakit
- LO = Long Shift

TUGAS:
1. Lihat SETIAP kotak tanggal 1-31 pada kalender
2. Untuk tiap tanggal yang ADA kotak shift-nya, tulis kodenya
3. Ambil HURUF DEPAN + ANGKA (contoh: "M22-MALAM" → "M22", "S15-SIANG" → "S15")
4. Kalau kotak kosong/tidak ada, SKIP

FORMAT OUTPUT (JSON valid, TANPA markdown backtick):
{{
  "shift_map": {{
    "1": "M22",
    "2": "M22",
    "3": "S15",
    "4": "S15",
    "5": "O"
  }}
}}

Output HANYA JSON, tidak ada teks lain di luar JSON.
"""

        # ============================================
        # 4. LOOP MODEL DENGAN AUTO-FALLBACK
        # ============================================
        _last_error = None
        _response = None
        _model_used = None

        for _model_name in MODEL_PRIORITY:
            try:
                print(f"[GEMINI v23] Trying model: {_model_name}")

                _resp = _client.models.generate_content(
                    model=_model_name,
                    contents=[_prompt, _img],
                    config=genai_types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=2048,
                    ),
                )

                if _resp and hasattr(_resp, "text") and _resp.text:
                    _response = _resp
                    _model_used = _model_name
                    print(f"[GEMINI v23] ✅ Success with: {_model_name}")
                    break
                else:
                    _last_error = f"Response kosong dari {_model_name}"
                    print(f"[GEMINI v23] ⚠️ {_model_name}: empty response")
                    continue

            except Exception as _e:
                _last_error = str(_e)
                print(f"[GEMINI v23] ❌ {_model_name} gagal: {_last_error[:150]}")
                continue

        if _response is None:
            # ✅ Deteksi quota habis
            _err_lower = (_last_error or "").lower()
            if "429" in _err_lower or "resource_exhausted" in _err_lower or "quota" in _err_lower:
                return {
                    "success": False,
                    "shift_map": {},
                    "error": (
                        "🚫 QUOTA GEMINI HABIS\n\n"
                        "Free tier Gemini cuma 20 request/hari.\n"
                        "Quota reset jam 14:00-15:00 WIB besok.\n\n"
                        "Alternatif: input manual via Chat Update."
                    ),
                    "raw_response": _last_error or "",
                }
        
            return {
                "success": False,
                "shift_map": {},
                "error": f"Semua model gagal. Last: {_last_error[:200]}",
                "raw_response": _last_error or "",
            }

        # ============================================
        # 5. RECORD API USAGE
        # ============================================
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

        # ============================================
        # 6. PARSE RESPONSE
        # ============================================
        _text = _response.text.strip()
        print(f"[GEMINI v23] Response length: {len(_text)}")
        print(f"[GEMINI v23] First 300: {_text[:300]}")

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
        # 7. BUILD SHIFT MAP
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
        try:
            record_api_usage(success=False)
        except Exception:
            pass
        return {"success": False, "shift_map": {}, "error": str(e)[:300], "raw_response": ""}


# =========================================================
# 🎯 WRAPPER v23
# =========================================================
def ocr_ai_smart(image_bytes, nama_personil="", bulan=1, tahun=2026):
    """Wrapper utama."""
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


# =========================================================
# 🔍 DEBUG INFO
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
        "available_priority": [],
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
            _info["available_priority"] = [m for m in MODEL_PRIORITY if m in _models]

    except Exception as e:
        _info["error"] = str(e)[:200]

    return _info


# =========================================================
# 🧪 QUICK TEST GEMINI
# =========================================================
def quick_test_gemini():
    """
    Test koneksi Gemini dengan prompt simple.
    Return: (success, message, model_used)
    """
    if not GEMINI_AVAILABLE:
        return False, "Library google-genai belum install", None

    try:
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not _api_key:
            return False, "GEMINI_API_KEY belum diset", None

        _client = genai.Client(api_key=_api_key)

        _last_error = None
        for _model_name in MODEL_PRIORITY:
            try:
                print(f"[QUICK TEST] Trying: {_model_name}")

                _response = _client.models.generate_content(
                    model=_model_name,
                    contents="Jawab hanya: OK",
                )

                if _response and hasattr(_response, "text") and _response.text:
                    return True, f"✅ Model {_model_name} works!", _model_name
            except Exception as _e:
                _last_error = str(_e)
                print(f"[QUICK TEST] {_model_name} error: {_e}")
                continue

        return False, f"Semua model gagal. Last: {_last_error[:150]}", None

    except Exception as e:
        return False, f"Error: {str(e)[:200]}", None


# =========================================================
# 📋 MODEL INFO DATAFRAME
# =========================================================
def get_model_info_df():
    """
    Return DataFrame info model untuk display.
    """
    import pandas as pd

    _debug = get_debug_info()
    _rows = []

    for _i, _model in enumerate(MODEL_PRIORITY):
        _available = _model in _debug.get("available_models", [])
        _rows.append({
            "Prioritas": _i + 1,
            "Model": _model,
            "Available": "✅" if _available else "❌",
            "Note": "Paling baru" if _i == 0 else "-",
        })

    return pd.DataFrame(_rows)


# =========================================================
# 📊 GET USAGE DATAFRAME
# =========================================================
def get_usage_df():
    """Return DataFrame usage history."""
    import pandas as pd

    if "api_usage_tracker" not in st.session_state:
        return pd.DataFrame()

    _tracker = st.session_state["api_usage_tracker"]

    if not _tracker:
        return pd.DataFrame()

    _rows = []
    for _tgl, _data in sorted(_tracker.items(), reverse=True):
        _rows.append({
            "Tanggal": _tgl,
            "Requests": _data.get("requests", 0),
            "Input Tokens": _data.get("input_tokens", 0),
            "Output Tokens": _data.get("output_tokens", 0),
            "Total Tokens": _data.get("total_tokens", 0),
            "Errors": _data.get("errors", 0),
        })

    return pd.DataFrame(_rows)


# =========================================================
# 🎨 HELPER: FORMAT NUMBER
# =========================================================
def fmt_num(n):
    """Format number dengan koma."""
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)
