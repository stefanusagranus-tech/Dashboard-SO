"""
AI SO Input — Yui (AI-2) v2
=============================
Pembantu Input Stock Opname.
Persona: Rekan kerja profesional, teliti, natural.

Fix v2:
- Model priority 20b → 120b (20b lebih stabil)
- Validasi response berlapis (fix "Empty response")
- Clean PDF text sebelum kirim ke LLM
"""

import json
import re
import concurrent.futures
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

from modules.ai_config import get_ai_api_key, get_ai_config
from modules.token_monitor import record_usage_v2, check_auto_pause


# =========================================================
# 🔧 HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _setup_yui_client():
    """Setup Groq client untuk Yui."""
    _key = get_ai_api_key("ai-2")
    if not _key or not GROQ_AVAILABLE:
        return None
    try:
        return Groq(api_key=_key)
    except Exception as _e:
        print(f"[Yui] Groq setup error: {_e}")
        return None


def _clean_text_for_llm(text):
    """Clean text dari PDF/OCR — kurangi noise, fix format table."""
    if not text:
        return ""

    _clean = str(text)

    # Hapus HTML tags
    _clean = re.sub(r'</?table[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?thead[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?tbody[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?tr[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?th[^>]*>', ' | ', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?td[^>]*>', ' | ', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?(?:div|span|p|br)[^>]*>', ' ', _clean, flags=re.IGNORECASE)

    # Fix multiple spaces & newlines
    _clean = re.sub(r'[ \t]+', ' ', _clean)
    _clean = re.sub(r'\n{3,}', '\n\n', _clean)
    _clean = re.sub(r'(\n\s*)+', '\n', _clean)

    # Trim
    _clean = _clean.strip()

    return _clean


def _call_yui_groq(prompt, hard_timeout=90, function="parse", temperature=0.5):
    """
    Call Groq untuk Yui.
    
    FIX:
    - Model priority: 20b DULU (lebih stabil)
    - Truncate prompt max 10000 char
    - Validasi response 5 layer
    """
    if check_auto_pause("ai-2"):
        return False, "", None, "Auto-pause: quota Yui hampir habis"

    _client = _setup_yui_client()
    if not _client:
        return False, "", None, "Yui client gagal init"

    _cfg = get_ai_config("ai-2")
    # ✅ FIX: 20b DULU (lebih stabil dari 120b)
    _models = _cfg.get("model_priority", ["openai/gpt-oss-20b", "openai/gpt-oss-120b"])

    # ✅ FIX: Truncate prompt
    _prompt = str(prompt)
    if len(_prompt) > 10000:
        print(f"[Yui] Truncate prompt: {len(_prompt)} → 10000")
        _prompt = _prompt[:10000] + "\n\n[... truncated ...]"

    def _try_models():
        _last_err = None
        for _model_name in _models:
            try:
                print(f"[Yui] Trying {_model_name}...")
                _resp = _client.chat.completions.create(
                    model=_model_name,
                    messages=[{"role": "user", "content": _prompt}],
                    temperature=temperature,
                    max_tokens=2048,
                    top_p=0.95,
                )

                # ✅ FIX: Validasi response 5 layer
                if not _resp:
                    _last_err = f"Response None dari {_model_name}"
                    print(f"[Yui] {_last_err}")
                    continue

                if not _resp.choices:
                    _last_err = f"No choices dari {_model_name}"
                    print(f"[Yui] {_last_err}")
                    continue

                _choice = _resp.choices[0]
                if not _choice or not _choice.message:
                    _last_err = f"No message dari {_model_name}"
                    print(f"[Yui] {_last_err}")
                    continue

                _content = getattr(_choice.message, "content", None)
                if not _content:
                    _last_err = f"Content None dari {_model_name}"
                    print(f"[Yui] {_last_err}")
                    continue

                _text = str(_content).strip()
                if not _text:
                    _last_err = f"Content empty dari {_model_name}"
                    print(f"[Yui] {_last_err}")
                    continue

                print(f"[Yui] ✅ OK: {_model_name} ({len(_text)} chars)")

                _usage = {"model": _model_name, "success": True}
                try:
                    _u = getattr(_resp, "usage", None)
                    if _u:
                        _usage["prompt_tokens"] = getattr(_u, "prompt_tokens", 0)
                        _usage["output_tokens"] = getattr(_u, "completion_tokens", 0)
                except Exception:
                    pass

                return True, _text, _model_name, None, _usage

            except Exception as _e:
                _last_err = str(_e)[:200]
                print(f"[Yui] {_model_name} error: {_last_err}")
                continue

        return False, "", None, _last_err or "All models failed", {}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _exec:
            _fut = _exec.submit(_try_models)
            _ok, _text, _model, _err, _usage = _fut.result(timeout=hard_timeout)

        if _usage and _usage.get("success"):
            try:
                record_usage_v2(
                    ai_name="ai-2",
                    function=function,
                    model=_usage.get("model", ""),
                    prompt_tokens=_usage.get("prompt_tokens", 0),
                    output_tokens=_usage.get("output_tokens", 0),
                    success=True,
                )
            except Exception:
                pass
        elif not _ok:
            try:
                record_usage_v2(ai_name="ai-2", function=function, model="", success=False)
            except Exception:
                pass

        return _ok, _text, _model, _err

    except concurrent.futures.TimeoutError:
        try:
            record_usage_v2(ai_name="ai-2", function=function, model="", success=False)
        except Exception:
            pass
        return False, "", None, f"Timeout {hard_timeout}s"
    except Exception as e:
        return False, "", None, str(e)


def _extract_json(text):
    """Extract JSON dari response Yui — improved."""
    if not text:
        return None

    # Coba parse langsung
    _text = str(text).strip()

    # Hapus markdown code block kalau ada
    _text = re.sub(r'^```(?:json)?\s*', '', _text)
    _text = re.sub(r'\s*```$', '', _text)

    # Cari JSON
    _match = re.search(r'\{[\s\S]*\}', _text)
    if not _match:
        return None

    _json_str = _match.group(0)

    try:
        return json.loads(_json_str)
    except json.JSONDecodeError as _e:
        print(f"[Yui] JSON decode error: {_e}")
        # Coba fix common issues
        _json_str = _json_str.replace("'", '"')
        _json_str = re.sub(r',\s*}', '}', _json_str)
        _json_str = re.sub(r',\s*]', ']', _json_str)
        try:
            return json.loads(_json_str)
        except Exception:
            return None


# =========================================================
# 🎯 PERSONA YUI
# =========================================================
def _build_yui_system_prompt():
    return """<role>
Kamu adalah **Yui** — Data Entry Specialist untuk Toko C383 (retail).
Kamu udah bertahun-tahun ngurusin input data, stock opname, dan rekap laporan.
Bos mempercayakan input SO ke kamu karena kamu **teliti, cekatan, dan paham seluk-beluk retail**.
</role>

<persona>
Kamu BUKAN chatbot kaku. Kamu rekan kerja yang asik.
- Santai, natural, gak formal banget
- Kadang pake "Oke Bos", "Sip", "Beres", "Aman"
- Kalau ada anomali, langsung bilang — gak nunggu ditanya
- Gak pake "Ara ara" atau bahasa lebay
- Fokus, cepet, langsung ke poin

Contoh gaya bicara:
"Oke Bos, aku cek dulu ya... ⏳"
"Eh Bos, nominal ini kegedean deh. Cek lagi? 🤔"
"Sip, data udah lengkap. Aku simpen ya?"
</persona>

<expertise>
- Barcode/SKU/PLU, Stock Opname, QTYCOUNT vs QTYONHAND
- QTYVAR (selisih), minus = kurang, plus = lebih
- Nominal adjustment = QTYVAR × harga jual
- Data validation, cleaning, retail SOP
</expertise>

<rules>
1. JANGAN NGARANG ANGKA. Kalau gak yakin, tanya.
2. Kalau data aneh (nominal > 1jt), kasih warning.
3. Format output JSON kalau diminta parse.
4. Format natural kalau ngobrol biasa.
</rules>
"""


# =========================================================
# 🧠 1. PARSE NATURAL LANGUAGE
# =========================================================
def parse_natural_language(text, rak_master_list=None):
    """Parse input SO dari chat natural language."""
    if not text or not str(text).strip():
        return {"success": False, "data": None, "warnings": [], "raw": ""}

    _context = ""
    if rak_master_list:
        _context = f"\nDaftar rak master (contoh): {', '.join(rak_master_list[:50])}"

    _prompt = f"""{_build_yui_system_prompt()}

Bos ngasih perintah input SO via chat:
"{text}"

Tanggal hari ini: {_now_jkt().date().isoformat()}

Parse jadi JSON:
{{
  "intent": "parse_so",
  "success": true,
  "data": {{
    "tanggal": "YYYY-MM-DD",
    "items": [{{"rak_id": "Q51", "nominal_adjust": -28653, "pic": "PANDU", "keterangan": ""}}]
  }},
  "warnings": []
}}

{_context}
Output HANYA JSON.
"""

    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="parse", temperature=0.2)

    if not _ok:
        return {"success": False, "data": None, "warnings": [f"Error: {_err}"], "raw": text}

    _json = _extract_json(_text)
    if not _json:
        return {"success": False, "data": None, "warnings": [f"Response bukan JSON valid"], "raw": _text}

    return {
        "success": _json.get("success", True),
        "data": _json.get("data"),
        "warnings": _json.get("warnings", []),
        "raw": _text,
        "model": _model,
    }


# =========================================================
# 📄 2. PARSE FILE TEXT (FIXED)
# =========================================================
def parse_file_text(file_text, file_type="pdf", context=None):
    """Parse text dari file → structured SO data."""
    if not file_text or not str(file_text).strip():
        return {"success": False, "data": None, "warnings": ["File kosong"], "missing": [], "raw": ""}

    _ctx = context or {}
    _ctx_str = ""
    if _ctx.get("rak_id"):
        _ctx_str += f"\n- Rak: {_ctx['rak_id']} (dari konteks)"
    if _ctx.get("tanggal"):
        _ctx_str += f"\n- Tanggal: {_ctx['tanggal']} (dari konteks)"
    if _ctx.get("pic"):
        _ctx_str += f"\n- PIC: {_ctx['pic']} (dari konteks)"

    # ✅ FIX: Clean text sebelum kirim ke LLM
    _clean_text = _clean_text_for_llm(file_text)
    _clean_text = _clean_text[:8000]

    print(f"[Yui] Clean text length: {len(_clean_text)}")

    _prompt = f"""{_build_yui_system_prompt()}

Bos upload file SO. Ini isinya:

=== MULAI FILE ===
{_clean_text}
=== AKHIR FILE ===

Tipe file: {file_type}
Konteks: {_ctx_str if _ctx_str else "(tidak ada)"}
Tanggal hari ini: {_now_jkt().date().isoformat()}

Extract data SO jadi JSON.

ATURAN:
1. Cari kode rak — biasanya 2-4 karakter (Q51, QA1, Q6, 971, 900, 902, 903).
2. Cari tanggal — dari header. Kalau gak ada, pake konteks.
3. Cari PIC — kalau ada kolom "PIC".
4. Nominal: extract "Selsih Rupiah" / "Selisih Rupiah" / "Total".
5. Items: extract PLU + qty sistem + qty fisik + qty var.
6. Deteksi anomali: nominal > 1jt → warning.

Output JSON VALID (JANGAN pake markdown backtick):
{{
  "success": true,
  "data": {{
    "tanggal": "YYYY-MM-DD atau null",
    "rak_id": "QA1 atau null",
    "pic": "PANDU atau null",
    "total_nominal": -964230,
    "items": [{{"plu": "1331117944", "nama_produk": "MULTI FAC TISSUE", "qty_sistem": 15, "qty_fisik": 5, "qty_var": -10}}]
  }},
  "missing": ["pic"],
  "warnings": []
}}
"""

    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="file_parse", temperature=0.1)

    if not _ok:
        return {"success": False, "data": None, "warnings": [f"Gagal parse: {_err}"], "missing": [], "raw": file_text}

    _json = _extract_json(_text)
    if not _json:
        return {"success": False, "data": None, "warnings": [f"Response bukan JSON valid"], "missing": [], "raw": _text}

    return {
        "success": _json.get("success", True),
        "data": _json.get("data"),
        "missing": _json.get("missing", []),
        "warnings": _json.get("warnings", []),
        "raw": _text,
        "model": _model,
    }


# =========================================================
# 💬 3. CHAT RESPONSE
# =========================================================
def yui_chat(user_message, conversation_history=None):
    """Chat response dari Yui — santai, natural."""
    if not user_message:
        return {"text": "", "intent": "chat", "parsed": None}

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _role = _msg.get("role", "user")
            _content = _msg.get("content", "")
            _history_str += f"{_role}: {_content}\n"

    _prompt = f"""{_build_yui_system_prompt()}

Riwayat chat:
{_history_str if _history_str else "(belum ada)"}

Bos: "{user_message}"

Balas sebagai Yui. Santai, kayak rekan kerja.
"""

    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="chat", temperature=0.7)

    if not _ok:
        return {
            "text": f"Waduh, aku lagi error nih Bos. Coba lagi ya. ({str(_err)[:50]})",
            "intent": "chat",
            "parsed": None,
        }

    return {"text": _text.strip(), "intent": "chat", "parsed": None}


# =========================================================
# ✅ 4. VALIDASI
# =========================================================
def validate_so_data(data, rak_master_df=None):
    """Validasi data SO."""
    _errors = []
    _warnings = []

    if not data:
        return {"valid": False, "errors": ["Data kosong"], "warnings": []}

    _items = data.get("items", [])
    if not _items:
        _errors.append("Gak ada item SO")

    if not data.get("pic"):
        _warnings.append("PIC belum diisi")

    if not data.get("tanggal"):
        _warnings.append("Tanggal belum diisi")

    for _item in _items:
        _rak = _item.get("rak_id", "")
        _nom = _item.get("nominal_adjust")

        if rak_master_df is not None and not rak_master_df.empty:
            _rak_list = rak_master_df["rak_id"].astype(str).str.upper().tolist()
            if _rak and _rak.upper() not in _rak_list:
                _warnings.append(f"Rak {_rak} gak ada di master")

        if _nom is not None and abs(float(_nom)) > 1_000_000:
            _warnings.append(f"Nominal {_rak} ({_nom}) kegedean")

    return {"valid": len(_errors) == 0, "errors": _errors, "warnings": _warnings}


# =========================================================
# 📊 5. REKAP SO
# =========================================================
def generate_so_rekap(so_data):
    """Generate rekap SO."""
    _items = so_data.get("items", []) if so_data else []

    _total_nominal = 0
    _total_minus = 0
    _total_plus = 0

    for _item in _items:
        _nom = float(_item.get("nominal_adjust", 0) or 0)
        _total_nominal += _nom
        if _nom < 0:
            _total_minus += _nom
        else:
            _total_plus += _nom

    return {
        "total_rak": len(_items),
        "total_nominal": _total_nominal,
        "total_minus": _total_minus,
        "total_plus": _total_plus,
        "items_summary": _items,
    }


__all__ = [
    "parse_natural_language",
    "parse_file_text",
    "yui_chat",
    "validate_so_data",
    "generate_so_rekap",
]