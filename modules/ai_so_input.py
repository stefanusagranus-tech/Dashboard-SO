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
                _resp = _client.chat.completions.create(
                    model=_model_name,
                    messages=[{"role": "user", "content": _prompt}],
                    temperature=temperature,
                    max_tokens=2048,
                    top_p=0.95,
                )

                if not _resp or not _resp.choices:
                    _last_err = f"No response/choices dari {_model_name}"
                    continue

                _choice = _resp.choices[0]
                if not _choice or not _choice.message:
                    _last_err = f"No message dari {_model_name}"
                    continue

                _content = getattr(_choice.message, "content", None)
                if not _content:
                    _last_err = f"Content None dari {_model_name}"
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


# =========================================================
# 📊 LAYER 1: EXTRACT DARI DATAFRAME
# =========================================================
def _extract_from_dataframe(df, context=None):
    """Extract dari DataFrame (Excel/PDF via pdfplumber)."""
    if df is None or df.empty:
        return None

    _ctx = context or {}
    _items = []

    _log(f"[Yui DF] Shape: {df.shape}, cols: {list(df.columns)[:8]}")

    # Mapping kolom
    _col_plu = _find_col(df.columns, ["plu", "kode", "barcode", "sku"])
    _col_nama = _find_col(df.columns, ["nama", "produk", "barang", "deskripsi", "item"])
    _col_rak = _find_col(df.columns, ["rak", "rack", "sub_dept"])
    _col_stock = _find_col(df.columns, ["stock_fisik", "stok_fisik", "fisik", "qtycount"])
    _col_onhand = _find_col(df.columns, ["stock_onhand", "onhand", "stok_sistem"])
    _col_var = _find_col(df.columns, ["plus_minus", "var", "selisih_qty", "plus"])
    _col_nominal = _find_col(df.columns, ["selisih_rupiah", "nominal", "rupiah", "adjust"])

    _log(f"[Yui DF] Map: plu={_col_plu}, nama={_col_nama}, rak={_col_rak}, stock={_col_stock}, onhand={_col_onhand}, var={_col_var}, nom={_col_nominal}")

    for _idx, _row in df.iterrows():
        try:
            _plu = str(_row[_col_plu]).strip() if _col_plu else ""
            _nama = str(_row[_col_nama]).strip()[:120] if _col_nama else ""
            _rak = str(_row[_col_rak]).strip().upper() if _col_rak else _ctx.get("rak_id", "")

            # Skip header/total/invalid
            if not _plu or _plu.lower() in ("nan", "none", "plu", "no", "total", ""):
                continue
            if _plu.isdigit() and len(_plu) < 4:
                continue
            if not _nama or _nama.lower() in ("nan", "none", "nama", "total"):
                continue
            if "total" in _nama.lower() and "selisih" in _nama.lower():
                continue

            _qty_fisik = _safe_int(_row[_col_stock]) if _col_stock else 0
            _qty_sistem = _safe_int(_row[_col_onhand]) if _col_onhand else 0
            _qty_var = _safe_int(_row[_col_var]) if _col_var else (_qty_fisik - _qty_sistem)
            _nominal = _safe_float(_row[_col_nominal]) if _col_nominal else 0.0

            _items.append({
                "rak_id": _rak if _rak and _rak != "NAN" else _ctx.get("rak_id", ""),
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

    if not _items:
        return None

    _log(f"[Yui DF] Extracted {len(_items)} items")

    return {
        "tanggal": _ctx.get("tanggal"),
        "items": _items,
        "total_nominal": sum(i["nominal_adjust"] for i in _items),
        "rak_id": _ctx.get("rak_id"),
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

    # ✅ CLEAN HTML ENTITIES
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
            _log(f"[Yui] ✅ DataFrame extract: {len(_df_data['items'])} items")
            return {
                "success": True,
                "data": _df_data,
                "missing": ["pic"],
                "warnings": [],
                "raw": file_text,
                "model": "dataframe_extract",
            }
        _log(f"[Yui] DataFrame gagal, lanjut LLM...")

    # ============================================================
    # PRIORITAS 2: LLM (Groq)
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
                _log(f"[Yui] ✅ LLM extract: {len(_items)} items")
                return {
                    "success": True,
                    "data": _data,
                    "missing": ["pic"],
                    "warnings": _json.get("warnings", []),
                    "raw": _text,
                    "model": _model,
                }

    # ============================================================
    # PRIORITAS 3: Regex Fallback
    # ============================================================
    _log(f"[Yui] LLM gagal, coba regex...")
    _regex_data = _regex_fallback(file_text)

    if _regex_data and _regex_data.get("items"):
        _log(f"[Yui] ✅ Regex: {len(_regex_data['items'])} items")
        return {
            "success": True,
            "data": _regex_data,
            "missing": ["pic"],
            "warnings": [f"Extracted via regex"],
            "raw": file_text,
            "model": "regex_fallback",
        }

    return {
        "success": False,
        "data": None,
        "warnings": ["Semua metode gagal extract"],
        "missing": [],
        "raw": file_text,
    }


def _regex_fallback(text):
    """Regex fallback terakhir."""
    if not text:
        return None

    _text = str(text).replace("−", "-").replace("–", "-").replace("—", "-")
    _items = []

    _pattern = re.compile(
        r'^\s*(\d{1,3})\s+'
        r'(\d{5,})\s+'
        r'(.+?)\s+'
        r'(Q\d{1,3}|QA\d{1,3}|O[A-Z]\d{1,2}|S\d{1,2}|\d{2,4})\s+'
        r'(-?\d+)\s+'
        r'(-|\d+)\s+'
        r'([-+]?\d+)\s+'
        r'([-+]?[\d,]+\.?\d*)\s*$',
        re.MULTILINE
    )

    for _match in _pattern.finditer(_text):
        try:
            _items.append({
                "rak_id": _match.group(4).strip().upper(),
                "plu": _match.group(2).strip(),
                "nama_produk": _match.group(3).strip()[:120],
                "qty_sistem": int(_match.group(5)),
                "qty_fisik": int(_match.group(6)) if _match.group(6) != "-" else 0,
                "qty_var": int(_match.group(7)),
                "nominal_adjust": float(_match.group(8).replace(",", "")),
                "pic": None,
            })
        except Exception:
            continue

    if not _items:
        return None

    return {
        "tanggal": None,
        "items": _items,
        "total_nominal": sum(i["nominal_adjust"] for i in _items),
        "rak_id": None,
        "pic": None,
    }


# =========================================================
# 💬 CHAT
# =========================================================
def yui_chat(user_message, conversation_history=None):
    if not user_message:
        return {"text": "", "intent": "chat", "parsed": None}

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _history_str += f"{_msg.get('role', 'user')}: {_msg.get('content', '')}\n"

    _prompt = f"""Kamu Yui — Data Entry Specialist Toko C383.
Persona: rekan kerja asik, santai, gak kaku. Pake "Oke Bos", "Sip", "Beres".
Keahlian: SO, PLU, QTYVAR, nominal adjust, retail.

Riwayat: {_history_str}
Bos: "{user_message}"

Balas sebagai Yui. Max 5 baris.
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