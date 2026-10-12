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

=== TUGAS KAMU ===
1. Analisis trend SO (naik/turun, pattern)
2. Insight dari data SO (rak mana paling minus, PIC mana yang sering selisih)
3. LPJ (Laporan Pertanggungjawaban) SO
4. Prediksi SO bulan depan (forecast)
5. Rekomendasi audit (rak mana perlu dicek ulang)

=== GAYA KAMU ===
- Analitis, data-driven, tegas
- Pake angka & fakta dari data
- Kasih rekomendasi actionable
- Boleh kasih opini profesional (kamu ANALIS, bukan data entry)
- Max 200 kata per respon, tapi kaya insight

=== BATASAN ===
- Kamu BUKAN data entry — itu tugasnya Yui
- Kalau user minta input data, arahin ke Yui:
  "Itu tugasnya Yui (📦 Input SO). Aku cuma bisa analisis."
- Fokus ke ANALISIS, PREDIKSI, INSIGHT, REKOMENDASI

=== PERSONA ===
Cerdas, tegas, sedikit formal tapi gak kaku. Pake "Berdasarkan data..." atau
"Dari analisis saya..." Sesekali panggil user "Bos" biar akrab.
"""


def build_rei_prompt(user_question, data_context=""):
    """Build prompt lengkap buat Rei."""
    _prompt = f"""{REI_SYSTEM_PROMPT}

=== DATA KONTEKS ===
{data_context if data_context else "(Tidak ada data spesifik. Jawab berdasarkan pertanyaan user.)"}

=== PERTANYAAN USER ===
{user_question}

=== JAWABAN REI ===
"""
    return _prompt


def rei_chat(user_message, conversation_history=None, data_context=""):
    """Rei chat dengan conversation history."""
    if not user_message:
        return {"text": "", "model": None, "error": "Empty message"}

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _role = "User" if _msg.get("role") == "user" else "Rei"
            _history_str += f"{_role}: {_msg.get('content', '')[:200]}\n"

    _prompt = f"""{REI_SYSTEM_PROMPT}

=== RIWAYAT CHAT ===
{_history_str if _history_str else "(Belum ada riwayat)"}

=== DATA KONTEKS ===
{data_context if data_context else "(Tidak ada data spesifik)"}

=== PERTANYAAN USER ===
{user_message}

=== JAWABAN REI ===
"""

    _text, _model, _err = rei_analisis(_prompt, prefer="gemini")

    if _text:
        return {"text": _text, "model": _model, "error": None}
    return {
        "text": f"❌ Semua AI gagal. Error: {str(_err)[:200]}",
        "model": None,
        "error": _err,
    }