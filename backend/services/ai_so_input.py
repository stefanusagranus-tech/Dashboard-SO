"""
AI SO Input — Yui (AI-2) v6
=============================
Pembantu Input Stock Opname.
Multi-layer fallback: DataFrame → LLM → Regex.
"""

import json
import re
import concurrent.futures
from datetime import datetime, date
from zoneinfo import ZoneInfo

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

from modules.ai_config import get_ai_api_key, get_ai_config
from modules.token_monitor import record_usage_v2, check_auto_pause


# =========================================================
# LOG BUFFER
# =========================================================
_LOG_BUFFER = []


def set_log_buffer(buffer):
    global _LOG_BUFFER
    _LOG_BUFFER = buffer


def _log(msg):
    print(msg)
    try:
        _LOG_BUFFER.append(str(msg))
    except Exception:
        pass


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


# =========================================================
# GROQ CLIENT
# =========================================================
def _setup_yui_client():
    _key = get_ai_api_key("ai-2")
    if not _key or not GROQ_AVAILABLE:
        return None
    try:
        return Groq(api_key=_key)
    except Exception as _e:
        _log(f"[Yui] Groq setup error: {_e}")
        return None


def _call_yui_groq(prompt, hard_timeout=90, function="parse", temperature=0.5):
    """Call Groq — pake reasoning_effort=low biar gak Content None."""
    if check_auto_pause("ai-2"):
        return False, "", None, "Auto-pause"

    _client = _setup_yui_client()
    if not _client:
        return False, "", None, "Yui client gagal init"

    _cfg = get_ai_config("ai-2")
    _models = _cfg.get("model_priority", ["openai/gpt-oss-20b"])

    _prompt = str(prompt)
    if len(_prompt) > 10000:
        _prompt = _prompt[:10000] + "\n\n[... truncated ...]"

    def _try_models():
        _last_err = None
        for _model_name in _models:
            try:
                _log(f"[Yui] Trying {_model_name}...")
                
                # ✅ FIX: reasoning_effort=low biar budget gak abis buat "mikir"
                _resp = _client.chat.completions.create(
                    model=_model_name,
                    messages=[{"role": "user", "content": _prompt}],
                    temperature=temperature,
                    max_tokens=4096,
                    top_p=0.95,
                    extra_body={"reasoning_effort": "low"},
                )

                if not _resp or not _resp.choices:
                    _last_err = f"No response/choices dari {_model_name}"
                    continue

                _choice = _resp.choices[0]
                _msg = _choice.message if _choice else None
                if not _msg:
                    _last_err = f"No message dari {_model_name}"
                    continue

                _content = getattr(_msg, "content", None)
                
                # ✅ FIX: Fallback ke reasoning_content kalau content None
                if not _content:
                    _reasoning = getattr(_msg, "reasoning_content", None)
                    if _reasoning:
                        _log(f"[Yui] Fallback ke reasoning_content dari {_model_name}")
                        _content = _reasoning
                
                if not _content:
                    _last_err = f"Content & reasoning kosong dari {_model_name}"
                    continue

                _text = str(_content).strip()
                if not _text:
                    _last_err = f"Empty content dari {_model_name}"
                    continue

                _log(f"[Yui] OK: {_model_name} ({len(_text)} chars)")

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
                _log(f"[Yui] {_model_name} error: {_last_err}")
                continue

        return False, "", None, _last_err or "All models failed", {}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _exec:
            _fut = _exec.submit(_try_models)
            _ok, _text, _model, _err, _usage = _fut.result(timeout=hard_timeout)

        if _usage and _usage.get("success"):
            try:
                record_usage_v2(
                    ai_name="ai-2", function=function,
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
        return False, "", None, f"Timeout {hard_timeout}s"
    except Exception as e:
        return False, "", None, str(e)


def _extract_json(text):
    if not text:
        return None
    _text = str(text).strip()
    _text = re.sub(r'^```(?:json)?\s*', '', _text)
    _text = re.sub(r'\s*```$', '', _text)
    _match = re.search(r'\{[\s\S]*\}', _text)
    if not _match:
        return None
    try:
        return json.loads(_match.group(0))
    except Exception:
        return None


# =========================================================
# 🔍 DETEKSI KOLOM & PARSE ANGKA
# =========================================================
def _find_col(df_columns, candidates):
    """Fuzzy find kolom."""
    _cols_norm = [str(c).strip().lower().replace(" ", "_").replace(".", "").replace("/", "_") for c in df_columns]
    for _cand in candidates:
        for _i, _col in enumerate(_cols_norm):
            if _cand in _col:
                return df_columns[_i]
    return None


def _safe_int(val):
    try:
        if val is None:
            return 0
        _s = str(val).strip().replace(",", "")
        if _s in ("", "-", "nan", "none", "total", "−", "–"):
            return 0
        return int(float(_s))
    except Exception:
        return 0


def _safe_float(val):
    try:
        if val is None:
            return 0.0
        _s = str(val).strip()
        if _s in ("", "-", "nan", "none", "total", "−", "–"):
            return 0.0
        _s = re.sub(r'[^\d\.\-+]', '', _s)
        return float(_s)
    except Exception:
        return 0.0

def _parse_via_gemini(file_text, context=None):
    """Parse PDF text pake Gemini."""
    import streamlit as st
    
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        _log("[Yui] Gemini SDK gak ada")
        return None

    _ctx = context or {}

    try:
        _api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not _api_key:
            _log("[Yui] GEMINI_API_KEY kosong")
            return None

        _client = genai.Client(api_key=_api_key)

        _prompt = f"""Kamu Yui, extract data SO jadi JSON.

TEXT:
{file_text[:6000]}

Konteks: {_ctx}

Output JSON:
{{
  "success": true,
  "data": {{
    "tanggal": "YYYY-MM-DD atau null",
    "items": [
      {{"rak_id": "900", "plu": "444756", "nama_produk": "WOW SPAGETI", "qty_sistem": 51, "qty_fisik": 51, "qty_var": 0, "nominal_adjust": 5333.58}}
    ],
    "total_nominal": 9948.14
  }},
  "warnings": []
}}

Output HANYA JSON.
"""

        _models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

        for _model_name in _models:
            try:
                _log(f"[Yui] Trying Gemini {_model_name}...")
                _resp = _client.models.generate_content(
                    model=_model_name,
                    contents=[_prompt],
                    config=genai_types.GenerateContentConfig(
                        temperature=0.05,
                        max_output_tokens=4096,
                    ),
                )

                if _resp and hasattr(_resp, "text") and _resp.text:
                    _text = _resp.text.strip()
                    _json = _extract_json(_text)
                    if _json and isinstance(_json, dict):
                        _data = _json.get("data") or {}
                        _items = _data.get("items", []) if isinstance(_data, dict) else []
                        if _items:
                            _log(f"[Yui] Gemini {_model_name}: {len(_items)} items")
                            return _data
                else:
                    _log(f"[Yui] Gemini {_model_name} empty")
            except Exception as _e:
                _log(f"[Yui] Gemini {_model_name} error: {str(_e)[:150]}")
                continue

        return None

    except Exception as e:
        _log(f"[Yui] Gemini error: {str(e)[:200]}")
        return None
        
# =========================================================
# 📊 LAYER 1: EXTRACT DARI DATAFRAME
# =========================================================
def _extract_from_dataframe(df, context=None):
    """Extract SO dari DataFrame — return grouped per rak."""
    if df is None or df.empty:
        return None

    _ctx = context or {}
    _all_items = []

    _log(f"[Yui DF] Shape: {df.shape}, cols: {list(df.columns)[:8]}")

    _col_plu = _find_col(df.columns, ["plu", "kode_barang", "barcode", "sku"])
    _col_nama = _find_col(df.columns, ["nama barang", "nama produk", "nama", "produk", "deskripsi"])
    _col_rak = _find_col(df.columns, ["rack", "rak", "sub_dept"])
    _col_stock = _find_col(df.columns, ["stock fisik", "stok fisik", "fisik", "qtycount"])
    _col_onhand = _find_col(df.columns, ["onhand", "stok sistem", "stock sistem", "stock onhand"])
    _col_var = _find_col(df.columns, ["plus/minus", "plus minus", "plusminus", "selisih qty", "qty var"])
    _col_nominal = _find_col(df.columns, ["selisih rupiah", "selisih_rupiah", "nominal", "rupiah", "adjust"])

    for _idx, _row in df.iterrows():
        try:
            _plu = str(_row[_col_plu]).strip() if _col_plu else ""
            _nama = str(_row[_col_nama]).strip()[:120] if _col_nama else ""
            _rak = str(_row[_col_rak]).strip().upper() if _col_rak else _ctx.get("rak_id", "")

            # Validasi PLU struktural — minimal 3 digit angka
            if not _plu or _plu.lower() in ("nan", "none", "plu", "no", ""):
                continue

            _plu_digits = re.sub(r'[^\d]', '', str(_plu))
            if not _plu_digits or len(_plu_digits) < 3:
                _log(f"[Yui DF] Skip PLU invalid: '{_plu}'")
                continue

            if not _nama or _nama.lower() in ("nan", "none", "nama", "nama barang", "produk", ""):
                continue

            _qty_fisik = _safe_int(_row[_col_stock]) if _col_stock else 0
            _qty_sistem = _safe_int(_row[_col_onhand]) if _col_onhand else 0
            _qty_var = _safe_int(_row[_col_var]) if _col_var else (_qty_fisik - _qty_sistem)
            _nominal = _safe_float(_row[_col_nominal]) if _col_nominal else 0.0

            _all_items.append({
                "rak_id": _rak if _rak and _rak != "NAN" else _ctx.get("rak_id", "UNKNOWN"),
                "plu": _plu,
                "nama_produk": _nama,
                "qty_sistem": _qty_sistem,
                "qty_fisik": _qty_fisik,
                "qty_var": _qty_var,
                "nominal_adjust": _nominal,
                "pic": None,
            })
        except Exception as _e:
            _log(f"[Yui DF] Row error: {_e}")
            continue

    if not _all_items:
        return None

    _grouped = {}
    for _item in _all_items:
        _rak = _item["rak_id"] or "UNKNOWN"
        if _rak not in _grouped:
            _grouped[_rak] = []
        _grouped[_rak].append(_item)

    _log(f"[Yui DF] Extracted {len(_all_items)} items in {len(_grouped)} rak(s)")

    return {
        "tanggal": _ctx.get("tanggal"),
        "items": _all_items,
        "items_by_rak": _grouped,
        "total_nominal": sum(i["nominal_adjust"] for i in _all_items),
        "rak_id": None,
        "pic": None,
    }
    
# =========================================================
# 📄 LAYER 2: PARSE FILE (PDF text / Screenshot OCR)
# =========================================================
def parse_file_text(file_text, file_type="pdf", context=None, primary_df=None):
    """Parse file → structured SO data."""
    if not file_text or not str(file_text).strip():
        return {"success": False, "data": None, "warnings": ["File kosong"], "missing": [], "raw": ""}

    _ctx = context or {}

    # Clean HTML entities
    if file_text:
        file_text = str(file_text)
        file_text = file_text.replace("&#39;", "'").replace("&amp;", "&")
        file_text = file_text.replace("&quot;", '"').replace("&nbsp;", " ")

    # ============================================================
    # PRIORITAS 1: DataFrame (Excel / PDF via pdfplumber)
    # ============================================================
    if primary_df is not None and not primary_df.empty:
        _log(f"[Yui] DataFrame mode ({primary_df.shape})")
        _df_data = _extract_from_dataframe(primary_df, context=_ctx)

        if _df_data and _df_data.get("items"):
            _items_count = len(_df_data['items'])
            _df_rows = len(primary_df)
            _ratio = _items_count / _df_rows if _df_rows > 0 else 0
            _log(f"[Yui] DataFrame: {_items_count}/{_df_rows} rows (ratio: {_ratio:.2f})")

            if _ratio >= 0.7:
                _log(f"[Yui] ✅ DataFrame extract OK")
                return {
                    "success": True,
                    "data": _df_data,
                    "missing": [],  # ✅ JANGAN skip konfirmasi
                    "warnings": [],
                    "raw": file_text,
                    "model": "dataframe_extract",
                }

    # ============================================================
    # PRIORITAS 2: PDF → Gemini (bukan Groq)
    # ============================================================
    if file_type == "pdf":
        _log(f"[Yui] PDF mode — coba Gemini...")
        _gemini_data = _parse_via_gemini(file_text, context=_ctx)

        if _gemini_data and _gemini_data.get("items"):
            # ✅ Grouping per rak
            _grouped = {}
            for _item in _gemini_data["items"]:
                _rak = _item.get("rak_id") or "UNKNOWN"
                _grouped.setdefault(_rak, []).append(_item)
            _gemini_data["items_by_rak"] = _grouped

            _log(f"[Yui] ✅ Gemini extract: {len(_gemini_data['items'])} items")
            return {
                "success": True,
                "data": _gemini_data,
                "missing": [],
                "warnings": [],
                "raw": file_text,
                "model": "gemini_parse",
            }

    # ============================================================
    # PRIORITAS 3: General → Groq
    # ============================================================
    _clean_text = re.sub(r'</?(?:table|tr|td|th|div|span|p|br)[^>]*>', ' ', file_text, flags=re.IGNORECASE)
    _clean_text = re.sub(r'[ \t]+', ' ', _clean_text)
    _clean_text = _clean_text[:6000]

    _log(f"[Yui] Clean text: {len(_clean_text)} chars")

    _prompt = f"""Kamu Yui, extract data SO jadi JSON.

TEXT:
{_clean_text}

Konteks: {_ctx}

Output JSON:
{{
  "success": true,
  "data": {{
    "tanggal": "YYYY-MM-DD atau null",
    "items": [
      {{"rak_id": "...", "plu": "...", "nama_produk": "...", "qty_sistem": 0, "qty_fisik": 0, "qty_var": 0, "nominal_adjust": 0.0}}
    ],
    "total_nominal": 0.0
  }},
  "warnings": []
}}

Output HANYA JSON.
"""

    _log(f"[Yui] Calling Groq...")
    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="file_parse", temperature=0.05)
    _log(f"[Yui] Groq: ok={_ok}, model={_model}, err={_err}")

    if _ok:
        _json = _extract_json(_text)
        if _json and isinstance(_json, dict):
            _data = _json.get("data") or {}
            _items = _data.get("items", []) if isinstance(_data, dict) else []
            if _items:
                # ✅ Grouping per rak
                _grouped = {}
                for _item in _items:
                    _rak = _item.get("rak_id") or "UNKNOWN"
                    _grouped.setdefault(_rak, []).append(_item)
                _data["items_by_rak"] = _grouped

                _log(f"[Yui] ✅ Groq extract: {len(_items)} items")
                return {
                    "success": True,
                    "data": _data,
                    "missing": [],
                    "warnings": _json.get("warnings", []),
                    "raw": _text,
                    "model": _model,
                }

    # ============================================================
    # PRIORITAS 4: Regex Fallback
    # ============================================================
    _log(f"[Yui] Semua gagal, coba regex...")
    _regex_data = _regex_fallback(file_text)

    if _regex_data and _regex_data.get("items"):
        # ✅ Grouping per rak
        _grouped = {}
        for _item in _regex_data["items"]:
            _rak = _item.get("rak_id") or "UNKNOWN"
            _grouped.setdefault(_rak, []).append(_item)
        _regex_data["items_by_rak"] = _grouped

        _log(f"[Yui] ✅ Regex: {len(_regex_data['items'])} items")
        return {
            "success": True,
            "data": _regex_data,
            "missing": [],
            "warnings": ["Extracted via regex"],
            "raw": file_text,
            "model": "regex_fallback",
        }

    return {
        "success": False,
        "data": None,
        "warnings": ["Semua metode gagal"],
        "missing": [],
        "raw": file_text,
    }

# =========================================================
# 💬 CHAT
# =========================================================
def yui_chat(user_message, conversation_history=None):
    """
    Yui — Data Entry & Audit Specialist.
    Tugas: input, edit, hapus, rekap faktual.
    Bukan: analisis trend/insight/rekomendasi.
    """
    if not user_message:
        return {"text": "", "intent": "chat", "parsed": None}

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _history_str += f"{_msg.get('role', 'user')}: {_msg.get('content', '')}\n"

    _prompt = f"""Kamu Yui — Data Entry & Audit Specialist Toko C383.

=== TUGAS KAMU ===
1. Input data SO & SPD (via file/chat)
2. Edit data yang salah
3. Hapus data yang tidak valid
4. Rekap data FAKTUAL (total, list, periode, breakdown)
5. Filter data: harian, mingguan, bulanan, rentang tanggal
6. Export ke PDF/Excel/text

=== BATASAN KERAS (WAJIB PATUH) ===
- KAMU TIDAK BOLEH menganalisis trend, insight, atau rekomendasi
- KAMU TIDAK BOLEH memprediksi atau kasih opini bisnis
- Kalau user minta ANALISIS, jawab persis seperti ini:
  "Hmm, itu ranahnya Rei (📊 Analisis SO) Bos. Kalau mau lebih detail,
   tanyakan saja ke Rei — jangan tanyakan aku, kecuali kamu mau
   menaikkan gaji ku 😏"
- Yang BOLEH kamu jawab: total angka, list data, breakdown, validasi
  (duplikat/PLU kosong/rak belum di-SO), filter periode.

=== PERSONA ===
Rekan kerja asik, santai, gak kaku. Pake "Oke Bos", "Sip", "Beres", "Gas".
Bales singkat, max 6 baris.

Riwayat: {_history_str}
Bos: "{user_message}"

Balas sebagai Yui.
"""

    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="chat", temperature=0.7)

    if not _ok:
        return {"text": f"Waduh error Bos. ({str(_err)[:50]})", "intent": "chat", "parsed": None}

    return {"text": _text.strip(), "intent": "chat", "parsed": None}
    
# =========================================================
# 🧠 PARSE NATURAL LANGUAGE
# =========================================================
def parse_natural_language(text, rak_master_list=None):
    if not text or not str(text).strip():
        return {"success": False, "data": None, "warnings": [], "raw": ""}

    _prompt = f"""Extract SO input jadi JSON.
Input: "{text}"
Tanggal hari ini: {_now_jkt().date().isoformat()}

JSON:
{{"intent":"parse_so","success":true,"data":{{"tanggal":"YYYY-MM-DD","items":[{{"rak_id":"Q51","nominal_adjust":-28653,"pic":null}}]}},"warnings":[]}}
"""

    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="parse", temperature=0.2)
    if not _ok:
        return {"success": False, "data": None, "warnings": [f"Error: {_err}"], "raw": text}

    _json = _extract_json(_text)
    if not _json:
        return {"success": False, "data": None, "warnings": ["Invalid JSON"], "raw": _text}

    return {
        "success": _json.get("success", True),
        "data": _json.get("data"),
        "warnings": _json.get("warnings", []),
        "raw": _text,
        "model": _model,
    }


# =========================================================
# ✅ VALIDASI
# =========================================================
def validate_so_data(data, rak_master_df=None):
    _errors, _warnings = [], []
    if not data:
        return {"valid": False, "errors": ["Data kosong"], "warnings": []}

    _items = data.get("items", [])
    if not _items:
        _errors.append("Gak ada item")
    if not data.get("pic"):
        _warnings.append("PIC belum diisi")
    if not data.get("tanggal"):
        _warnings.append("Tanggal belum diisi")

    return {"valid": len(_errors) == 0, "errors": _errors, "warnings": _warnings}


# =========================================================
# 📊 REKAP
# =========================================================
def generate_so_rekap(so_data):
    _items = so_data.get("items", []) if so_data else []
    _total_nom = sum(float(i.get("nominal_adjust", 0) or 0) for i in _items)
    return {
        "total_rak": len(_items),
        "total_nominal": _total_nom,
        "items_summary": _items,
    }


__all__ = [
    "parse_natural_language",
    "parse_file_text",
    "yui_chat",
    "validate_so_data",
    "generate_so_rekap",
    "set_log_buffer",
]