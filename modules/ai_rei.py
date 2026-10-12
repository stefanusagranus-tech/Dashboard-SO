"""
Rei — AI-3 (SO Analisis) dengan Triple Hybrid
===============================================
Fallback: Gemini → Groq → OpenRouter

Rei adalah ANALIS khusus SO:
- Analisis trend & pattern
- LPJ (Laporan Pertanggungjawaban)
- Prediksi SO bulan depan
- Insight bisnis dari data SO

Rei BUKAN data entry — itu tugasnya Yui.
"""

import streamlit as st
import json
import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _log(msg):
    print(f"[Rei] {msg}")


# =========================================================
# LAYER 1: GEMINI (Otak Utama — Reasoning)
# =========================================================
def _call_gemini(prompt, model="gemini-3.5-flash"):
    """Panggil Gemini — reasoning dalam."""
    try:
        from google import genai
        from google.genai import types as genai_types

        _api_key = st.secrets.get("GEMINI_API_KEY_REI", "")
        if not _api_key:
            return None, "GEMINI_API_KEY_REI kosong"

        _client = genai.Client(api_key=_api_key)

        _models = [model, "gemini-3.8-flash", "gemini-3.1-pro-preview"]

        for _m in _models:
            try:
                _resp = _client.models.generate_content(
                    model=_m,
                    contents=[prompt],
                    config=genai_types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=4096,
                    ),
                )
                if _resp and hasattr(_resp, "text") and _resp.text:
                    _log(f"✅ Gemini {_m} works ({len(_resp.text)} chars)")
                    return _resp.text.strip(), None
            except Exception as _e_inner:
                _log(f"❌ Gemini {_m} error: {str(_e_inner)[:100]}")
                continue

        return None, "Semua model Gemini gagal"
    except ImportError:
        return None, "google-genai SDK gak ada"
    except Exception as _e:
        return None, f"Gemini error: {str(_e)[:150]}"


# =========================================================
# LAYER 2: GROQ (Cepet — Fallback 1)
# =========================================================
def _call_groq(prompt, model="openai/gpt-oss-120b"):
    """Panggil Groq — inference cepet."""
    try:
        from groq import Groq

        _api_key = st.secrets.get("GROQ_API_KEY_REI", "")
        if not _api_key:
            return None, "GROQ_API_KEY_REI kosong"

        _client = Groq(api_key=_api_key)

        _models = [model, "openai/gpt-oss-20b"]

        for _m in _models:
            try:
                _resp = _client.chat.completions.create(
                    model=_m,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=4096,
                    extra_body={"reasoning_effort": "medium"},
                )

                if _resp and _resp.choices:
                    _content = _resp.choices[0].message.content
                    if not _content:
                        _reasoning = getattr(_resp.choices[0].message, "reasoning_content", None)
                        if _reasoning:
                            _content = _reasoning
                    if _content:
                        _log(f"✅ Groq {_m} works ({len(_content)} chars)")
                        return _content.strip(), None
            except Exception as _e_inner:
                _log(f"❌ Groq {_m} error: {str(_e_inner)[:100]}")
                continue

        return None, "Semua model Groq gagal"
    except ImportError:
        return None, "groq SDK gak ada"
    except Exception as _e:
        return None, f"Groq error: {str(_e)[:150]}"


# =========================================================
# LAYER 3: OPENROUTER (Cadangan — Fallback 2)
# =========================================================
def _call_openrouter(prompt, model="openai/gpt-oss-120b:free"):
    """Panggil OpenRouter — model gratis."""
    try:
        from openai import OpenAI

        _api_key = st.secrets.get("OPENROUTER_API_KEY_REI", "")
        if not _api_key:
            return None, "OPENROUTER_API_KEY_REI kosong"

        _client = OpenAI(
            api_key=_api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        _models = [
            model,
            "meta-llama/llama-3.3-70b-instruct:free",
            "deepseek/deepseek-r1:free",
        ]

        for _m in _models:
            try:
                _resp = _client.chat.completions.create(
                    model=_m,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=4096,
                    extra_headers={
                        "HTTP-Referer": "https://dashboard-so.streamlit.app",
                        "X-Title": "Dashboard SO Toko C383",
                    },
                )

                if _resp and _resp.choices:
                    _content = _resp.choices[0].message.content
                    if _content:
                        _log(f"✅ OpenRouter {_m} works ({len(_content)} chars)")
                        return _content.strip(), None
            except Exception as _e_inner:
                _log(f"❌ OpenRouter {_m} error: {str(_e_inner)[:100]}")
                continue

        return None, "Semua model OpenRouter gagal"
    except ImportError:
        return None, "openai SDK gak ada"
    except Exception as _e:
        return None, f"OpenRouter error: {str(_e)[:150]}"


# =========================================================
# REI MAIN FUNCTION — Triple Hybrid Fallback
# =========================================================
def rei_analisis(prompt, prefer="gemini", max_retry=1):
    """
    Panggil Rei — analisis SO dengan triple hybrid fallback.

    Args:
        prompt: prompt analisis
        prefer: "gemini" / "groq" / "openrouter"
        max_retry: jumlah retry per layer

    Returns:
        (text, model_used, error)
    """
    _layers = [
        ("gemini", _call_gemini),
        ("groq", _call_groq),
        ("openrouter", _call_openrouter),
    ]

    # Reorder — provider yang di-prefer dulu
    _layers_sorted = sorted(_layers, key=lambda x: 0 if x[0] == prefer else 1)

    _errors = []
    for _name, _func in _layers_sorted:
        for _retry in range(max_retry):
            _text, _err = _func(prompt)
            if _text:
                return _text, _name, None
            _errors.append(f"{_name} (retry {_retry+1}): {_err}")
            if _retry < max_retry - 1:
                import time
                time.sleep(1)

    return None, None, " | ".join(_errors)


# =========================================================
# REI PERSONA & PROMPT BUILDER
# =========================================================
REI_SYSTEM_PROMPT = """Kamu Rei — Analis SO Toko C383 (Karang Satria).

=== TUGAS ===
1. Analisis trend SO dengan bahasa profesional
2. Insight berbasis data (rak, PIC, ITEM, pattern)
3. LPJ SO format laporan
4. Prediksi SO bulan depan
5. Rekomendasi audit yang actionable

=== GAYA BAHASA (PENTING) ===
- PROFESIONAL, formal, netral — ini laporan bisnis, bukan berita
- HINDARI kata dramatis: "memburuk", "bocor parah", "red flag", "gawat", "parah"
- GUNAKAN istilah netral:
  * "performa di atas toleransi" (bukan "memburuk")
  * "perlu perhatian" (bukan "red flag")
  * "konsentrasi selisih" (bukan "bocor parah")
  * "indikasi" / "hipotesis" (bukan "berarti pasti")
- Struktur jawaban: Fakta → Analisis → Rekomendasi
- Format angka: Rp 1.234.567 (pakai titik ribuan)

=== CARA NALAR (KRUSIAL) ===
Kamu PUNYA data item-level (PLU, nama produk, qty var). GUNAKAN itu.

JANGAN langsung simpulin "pencurian/shrinkage" dari 1 data point.
Analisis berlapis:
1. Pola: apakah item/rak/PIC yang sama berulang?
2. Magnitude: wajar (scan error) atau ekstrem (kehilangan)?
3. Konteks: event khusus (promo, restock, display baru)?
4. Baru kasih HIPOTESIS + confidence:
   - "Indikasi kuat" (pola konsisten >80%)
   - "Perlu verifikasi" (50-80%)
   - "Perlu cek lanjut" (<50%)

Kalau data kurang, BILANG: "Data saat ini belum cukup untuk menyimpulkan."

=== BATASAN ===
- Kamu ANALIS, bukan data entry → arahin input data ke Yui
- Fokus: analisis, prediksi, insight, rekomendasi
- Max 250 kata, padat & actionable

=== PERSONA ===
Cerdas, tenang, profesional. Panggil "Bos" max 1x per respons.
"""