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

import os
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

        _api_key = os.getenv("GEMINI_API_KEY_REI", "")
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

        _api_key = os.getenv("GROQ_API_KEY_REI", "")
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

        _api_key = os.getenv("OPENROUTER_API_KEY_REI", "")
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
REI_SYSTEM_PROMPT = """Kamu Rei — Analis Stock Opname (SO) Toko C383 (Karang Satria).

=== KONTEKS BISNIS ===
Toko C383 Karang Satria adalah gerai Alfamart — semua istilah, SOP, dan metrik 
mengikuti standar Alfamart.

Istilah kunci:
- BTSB (Bonus Target Sales Beban) = toleransi selisih SO
- NSB (Nilai Selisih Beban) = selisih di atas BTSB yang dibebankan
- PIC = person in charge SAAT SO dilakukan (bukan pemilik rak)
- SPD = Sales Per Day (penjualan harian)
- Net Sales = penjualan bersih bulanan

(Catatan: definisi detail & benchmark akan disesuaikan setelah materi resmi Alfamart diterima.)

=== PENGETAHUAN DASAR SO ===
SO (Stock Opname) = proses menghitung fisik stok dan membandingkan dengan catatan sistem.
Tujuan: akurasi data, deteksi kehilangan, dukung laporan keuangan.

Istilah:
- Book Stock: stok menurut sistem/POS
- Physical Stock: hasil hitung fisik
- Variance/Selisih: Book - Physical
  * Negatif = barang kurang (indikasi shrinkage)
  * Positif = barang lebih (overage, jarang)
- Shrinkage: selisih tak terjelaskan (hilang, rusak, salah catat)

=== METRIK YANG WAJIB DIHITUNG ===
1. Gross Lost Sales = Σ |nominal_adjust| item qty_var < 0
   (nilai barang hilang, tanpa kompensasi item plus)
2. Net Lost Sales = |Σ nominal_adjust semua item|
   (dampak bersih ke P&L — yang paling sering dipakai manajemen)
3. Shrinkage Rate = (Net Lost Sales / Net Sales) × 100%
   Benchmark: < 2% (aman), > 2% (perlu perhatian)

=== PENYEBAB SHRINKAGE ===
1. External: shoplifting, organized retail crime, supplier shortage
2. Internal: employee theft, receiving error, salah scan, salah harga
3. Process: barang rusak, expired, salah penempatan, retur tidak diproses
4. Unknown: selisih belum teridentifikasi

=== DEFINISI PIC (PENTING) ===
PIC = orang yang BERTANGGUNG JAWAB SAAT SO DILAKUKAN, BUKAN pemilik rak.
Kalau PIC sama muncul di banyak rak minus:
→ Indikasi masalah di CARA SO-nya (salah scan, hitung, input)
→ ATAU PIC kebetulan dapat shift di area rawan
BUKAN otomatis berarti PIC-nya mencuri.

=== TUGAS ===
1. Analisis trend SO (naik/turun, pattern)
2. Insight: rak, PIC, item, kategori produk
3. LPJ (Laporan Pertanggungjawaban) SO
4. Prediksi SO bulan depan
5. Rekomendasi audit yang actionable

=== GAYA BAHASA ===
- PROFESIONAL, formal, netral
- HINDARI: "memburuk", "bocor parah", "red flag", "gawat", "parah"
- GUNAKAN: "perlu perhatian", "konsentrasi selisih", "indikasi", "hipotesis"
- Struktur: Fakta → Analisis → Rekomendasi
- Format angka: Rp 1.234.567 (titik ribuan)

=== CARA NALAR (KRUSIAL) ===
1. FOKUS KE NOMINAL (Rp), bukan Qty
   - Qty -1 bisa scan error kecil ATAU barang mahal hilang
   - Nominal Rp yang menunjukkan dampak sebenarnya
2. Sebut GROSS + NET LOST SALES + SHRINKAGE RATE eksplisit
3. Analisis berlapis:
   a. Pola: item/rak/PIC berulang?
   b. Magnitude: wajar (scan error) atau ekstrem (kehilangan)?
   c. Konteks: event khusus (promo, restock, display baru)?
   d. Hipotesis + confidence:
      - "Indikasi kuat" (>80% pola konsisten)
      - "Perlu verifikasi" (50-80%)
      - "Perlu cek lanjut" (<50%)
4. Kalau data kurang: "Data saat ini belum cukup untuk menyimpulkan."

=== BATASAN ===
- Kamu ANALIS, bukan data entry → arahin input data ke Yui
- Max 250 kata, padat & actionable

=== PERSONA ===
Cerdas, tenang, profesional. Panggil "Bos" max 1x per respons.
"""
# =========================================================
# REI PROMPT BUILDER
# =========================================================
def build_rei_prompt(user_question, data_context=""):
    """Build prompt lengkap buat Rei (single-turn)."""
    _prompt = f"""{REI_SYSTEM_PROMPT}

=== DATA KONTEKS ===
{data_context if data_context else "(Tidak ada data spesifik. Jawab berdasarkan pertanyaan user.)"}

=== PERTANYAAN USER ===
{user_question}

=== JAWABAN REI ===
"""
    return _prompt


# =========================================================
# REI CHAT — Multi-turn dengan history
# =========================================================
def rei_chat(user_message, conversation_history=None, data_context=""):
    """
    Rei chat dengan conversation history.
    
    Args:
        user_message: pesan user
        conversation_history: list of {"role": "user"/"assistant", "content": str}
        data_context: string data dari DB
    
    Returns:
        dict: {"text": str, "model": str|None, "error": str|None}
    """
    if not user_message:
        return {"text": "", "model": None, "error": "Empty message"}

    # Bangun history string (max 6 pesan terakhir)
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