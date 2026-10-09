"""
AI SO Input — Yui (AI-2) v5
=============================
Pembantu Input Stock Opname.
Persona: Rekan kerja profesional, teliti, natural.

Fitur:
- Parse natural language
- Parse file (PDF/Excel/Screenshot) → DataFrame
- Logger ke buffer (buat debug UI)
- Fallback regex multi-pattern
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
        _log(f"[Yui] Groq setup error: {_e}")
        return None


def _clean_text_for_llm(text):
    """Clean text dari PDF/OCR."""
    if not text:
        return ""

    _clean = str(text)

    _clean = re.sub(r'</?table[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?thead[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?tbody[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?tr[^>]*>', '\n', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?th[^>]*>', ' | ', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?td[^>]*>', ' | ', _clean, flags=re.IGNORECASE)
    _clean = re.sub(r'</?(?:div|span|p|br)[^>]*>', ' ', _clean, flags=re.IGNORECASE)

    _clean = re.sub(r'[ \t]+', ' ', _clean)
    _clean = re.sub(r'\n{3,}', '\n\n', _clean)
    _clean = re.sub(r'(\n\s*)+', '\n', _clean)

    return _clean.strip()


def _call_yui_groq(prompt, hard_timeout=90, function="parse", temperature=0.5):
    """Call Groq untuk Yui."""
    if check_auto_pause("ai-2"):
        return False, "", None, "Auto-pause: quota Yui hampir habis"

    _client = _setup_yui_client()
    if not _client:
        return False, "", None, "Yui client gagal init"

    _cfg = get_ai_config("ai-2")
    _models = _cfg.get("model_priority", ["openai/gpt-oss-20b"])

    _prompt = str(prompt)
    if len(_prompt) > 10000:
        _log(f"[Yui] Truncate prompt: {len(_prompt)} → 10000")
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

                if not _resp:
                    _last_err = f"Response None dari {_model_name}"
                    _log(f"[Yui] {_last_err}")
                    continue

                if not _resp.choices:
                    _last_err = f"No choices dari {_model_name}"
                    _log(f"[Yui] {_last_err}")
                    continue

                _choice = _resp.choices[0]
                if not _choice or not _choice.message:
                    _last_err = f"No message dari {_model_name}"
                    _log(f"[Yui] {_last_err}")
                    continue

                _content = getattr(_choice.message, "content", None)
                if not _content:
                    _last_err = f"Content None dari {_model_name}"
                    _log(f"[Yui] {_last_err}")
                    continue

                _text = str(_content).strip()
                if not _text:
                    _last_err = f"Content empty dari {_model_name}"
                    _log(f"[Yui] {_last_err}")
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
    """Extract JSON dari response Yui."""
    if not text:
        return None

    _text = str(text).strip()

    _text = re.sub(r'^```(?:json)?\s*', '', _text)
    _text = re.sub(r'\s*```$', '', _text)

    _match = re.search(r'\{[\s\S]*\}', _text)
    if not _match:
        return None

    _json_str = _match.group(0)

    try:
        return json.loads(_json_str)
    except json.JSONDecodeError as _e:
        _log(f"[Yui] JSON decode error: {_e}")
        _json_str = _json_str.replace("'", '"')
        _json_str = re.sub(r',\s*}', '}', _json_str)
        _json_str = re.sub(r',\s*]', ']', _json_str)
        try:
            return json.loads(_json_str)
        except Exception:
            return None


# =========================================================
# 🔧 FALLBACK REGEX
# =========================================================
def _fallback_regex_extract(text):
    """Fallback: extract data SO via regex."""
    if not text:
        return None

    _items = []
    _text = str(text)

    _log(f"[Yui Fallback] Text len: {len(_text)}, lines: {len(_text.splitlines())}")

    _pattern1 = re.compile(
        r'^\s*(\d{1,3})\s+'
        r'(\d{6,})\s+'
        r'([A-Z][A-Z0-9\s\.\-/&\'\(\)]+?)\s{2,}'
        r'(Q\d{1,3}|QA\d{1,3}|O[A-Z]\d{1,2}|\d{2,4})\s+'
        r'(-?\d+)\s+'
        r'(-|\d+)\s+'
        r'([-+]?\d+)\s+'
        r'([-+]?[\d,]+\.?\d*)\s*$',
        re.MULTILINE
    )

    for _match in _pattern1.finditer(_text):
        try:
            _rows_data = {
                "rak_id": _match.group(4).strip().upper(),
                "plu": _match.group(2).strip(),
                "nama_produk": _match.group(3).strip()[:120],
                "qty_sistem": int(_match.group(5)),
                "qty_fisik": int(_match.group(6)) if _match.group(6) != "-" else 0,
                "qty_var": int(_match.group(7)),
                "nominal_adjust": float(_match.group(8).replace(",", "")),
                "pic": None,
            }
            _items.append(_rows_data)
        except Exception as _e:
            _log(f"[Yui Fallback] Pattern1 error: {_e}")
            continue

    if not _items:
        _log("[Yui Fallback] Pattern 1 kosong, coba Pattern 2...")
        _pattern2 = re.compile(
            r'\b(\d{6,})\s+'
            r'([A-Z][A-Z0-9\s\.\-/&\']+?)\s+'
            r'(Q\d{1,3}|QA\d{1,3}|O[A-Z]\d{1,2}|\d{2,4})\s+'
            r'(-?\d+)\s+'
            r'(-|\d+)\s+'
            r'([-+]?\d+)\s+'
            r'([-+]?[\d,]+\.?\d*)',
            re.MULTILINE
        )

        for _match in _pattern2.finditer(_text):
            try:
                _items.append({
                    "rak_id": _match.group(3).strip().upper(),
                    "plu": _match.group(1).strip(),
                    "nama_produk": _match.group(2).strip()[:120],
                    "qty_sistem": int(_match.group(4)),
                    "qty_fisik": int(_match.group(5)) if _match.group(5) != "-" else 0,
                    "qty_var": int(_match.group(6)),
                    "nominal_adjust": float(_match.group(7).replace(",", "")),
                    "pic": None,
                })
            except Exception:
                continue

    if not _items:
        _log("[Yui Fallback] 0 items found")
        return None

    _log(f"[Yui Fallback] {len(_items)} items extracted")

    _tanggal = None
    _bulan_map = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }

    _tgl_match = re.search(r'(\d{1,2})-(\w{3})-(\d{4})', _text)
    if _tgl_match:
        try:
            _tgl = _tgl_match.group(1).zfill(2)
            _bln = _bulan_map.get(_tgl_match.group(2), "01")
            _thn = _tgl_match.group(3)
            _tanggal = f"{_thn}-{_bln}-{_tgl}"
        except Exception:
            pass

    _total_nominal = sum(i["nominal_adjust"] for i in _items)

    return {
        "tanggal": _tanggal,
        "items": _items,
        "total_nominal": _total_nominal,
        "rak_id": None,
        "pic": None,
    }


# =========================================================
# 📊 EXTRACT DARI DATAFRAME
# =========================================================
def _extract_from_dataframe(df, context=None):
    """Extract SO data dari DataFrame — handle multi-format kolom."""
    if df is None or df.empty:
        return None

    _ctx = context or {}
    _items = []

    _log(f"[Yui Excel] DataFrame columns: {list(df.columns)}")
    _log(f"[Yui Excel] DataFrame shape: {df.shape}")

    _df = df.copy()
    _df.columns = [
        str(c).strip().lower().replace(" ", "_").replace(".", "").replace("/", "_")
        for c in _df.columns
    ]

    def _find_col(candidates):
        for _cand in candidates:
            for _col in _df.columns:
                if _cand in _col:
                    return _col
        return None

    _col_plu = _find_col(["plu", "kode", "barcode", "sku", "col_1"])
    _col_nama = _find_col(["nama", "produk", "barang", "deskripsi", "item", "col_2"])
    _col_rak = _find_col(["rak", "rack", "kode_rak", "sub_dept", "col_3"])
    _col_stock = _find_col(["stock_fisik", "stok_fisik", "fisik", "qtycount", "col_4"])
    _col_onhand = _find_col(["stock_onhand", "onhand", "stok_sistem", "col_5"])
    _col_var = _find_col(["plus_minus", "var", "selisih_qty", "col_6"])
    _col_nominal = _find_col(["selisih_rupiah", "nominal", "rupiah", "adjust", "col_7", "col_8"])

    _log(f"[Yui Excel] Mapping: plu={_col_plu}, nama={_col_nama}, rak={_col_rak}, stock={_col_stock}, onhand={_col_onhand}, var={_col_var}, nominal={_col_nominal}")

    def _safe_int(val):
        try:
            if val is None:
                return 0
            _s = str(val).strip().replace(",", "")
            if _s in ("", "-", "nan", "none", "total"):
                return 0
            return int(float(_s))
        except Exception:
            return 0

    def _safe_float(val):
        try:
            if val is None:
                return 0.0
            _s = str(val).strip()
            if _s in ("", "-", "nan", "none", "total"):
                return 0.0
            _s = re.sub(r'[^\d\.\-+]', '', _s)
            return float(_s)
        except Exception:
            return 0.0

    for _idx, _row in _df.iterrows():
        try:
            _plu = str(_row[_col_plu]).strip() if _col_plu else ""
            _nama = str(_row[_col_nama]).strip()[:120] if _col_nama else ""
            _rak = str(_row[_col_rak]).strip().upper() if _col_rak else _ctx.get("rak_id", "")

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
            _log(f"[Yui Excel] Row error: {_e}")
            continue

    if not _items:
        return None

    _log(f"[Yui Excel] Extracted {len(_items)} items")

    _total_nominal = sum(i["nominal_adjust"] for i in _items)

    return {
        "tanggal": _ctx.get("tanggal"),
        "items": _items,
        "total_nominal": _total_nominal,
        "rak_id": _ctx.get("rak_id"),
        "pic": None,
    }


# =========================================================
# 🎯 PERSONA YUI
# =========================================================
def _build_yui_system_prompt():
    return """<role>
Kamu **Yui** — Data Entry Specialist Toko C383 (retail).
Berpengalaman input data, stock opname, rekap laporan. Teliti, cekatan, paham retail.
</role>

<persona>
Rekan kerja asik, bukan chatbot kaku.
- Santai, natural, gak formal
- Kadang pake "Oke Bos", "Sip", "Beres", "Aman"
- Kalau ada anomali, langsung bilang
- Gak pake "Ara ara" atau bahasa lebay
- Fokus, cepet, to-the-point
</persona>

<expertise>
- Barcode/SKU/PLU, Stock Opname, QTYCOUNT vs QTYONHAND
- QTYVAR (selisih), minus = kurang, plus = lebih
- Nominal adjustment = QTYVAR × harga jual
- Data validation, cleaning, retail SOP
</expertise>

<rules>
1. JANGAN NGARANG ANGKA. Kalau gak yakin, tanya.
2. Anomali (nominal > 1jt) → warning.
3. JSON output kalau diminta parse.
4. Natural output kalau ngobrol.
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
        return {"success": False, "data": None, "warnings": ["Response bukan JSON valid"], "raw": _text}

    return {
        "success": _json.get("success", True),
        "data": _json.get("data"),
        "warnings": _json.get("warnings", []),
        "raw": _text,
        "model": _model,
    }


# =========================================================
# 📄 2. PARSE FILE TEXT
# =========================================================
def parse_file_text(file_text, file_type="pdf", context=None, primary_df=None):
    """Parse text dari file → structured SO data."""
    if not file_text or not str(file_text).strip():
        return {"success": False, "data": None, "warnings": ["File kosong"], "missing": [], "raw": ""}

    _ctx = context or {}

    # ✅ PRIORITAS 1: Kalau ada DataFrame — extract langsung pake pandas
    if primary_df is not None:
        _log(f"[Yui] DataFrame mode — extract from DataFrame ({primary_df.shape})")
        _df_data = _extract_from_dataframe(primary_df, context=_ctx)

        if _df_data and _df_data.get("items"):
            _log(f"[Yui] DataFrame extract OK: {len(_df_data['items'])} items")
            return {
                "success": True,
                "data": _df_data,
                "missing": ["pic"],
                "warnings": [],
                "raw": file_text,
                "model": "dataframe_extract",
            }
        else:
            _log(f"[Yui] DataFrame extract failed, lanjut text-based...")

    # ✅ PRIORITAS 2: Text-based (LLM Groq)
    _ctx_str = ""
    if _ctx.get("rak_id"):
        _ctx_str += f"\n- Rak: {_ctx['rak_id']} (dari konteks)"
    if _ctx.get("tanggal"):
        _ctx_str += f"\n- Tanggal: {_ctx['tanggal']} (dari konteks)"
    if _ctx.get("pic"):
        _ctx_str += f"\n- PIC: {_ctx['pic']} (dari konteks)"

    _clean_text = _clean_text_for_llm(file_text)
    _clean_text = _clean_text[:6000]

    _log(f"[Yui] Clean text length: {len(_clean_text)}")

    _prompt = f"""Kamu Yui, asisten input SO. Baca text di bawah, extract data per BARIS TABEL.

=== MULAI TEXT ===
{_clean_text}
=== AKHIR TEXT ===

Tipe: {file_type}
Konteks: {_ctx_str if _ctx_str else "(tidak ada)"}
Tanggal hari ini: {_now_jkt().date().isoformat()}

TASK: Extract data SO jadi JSON.

PENTING:
- Setiap BARIS tabel = 1 item produk
- Cari kolom: No | PLU | Nama | Rak | Stock | Fisik | Plus/Minus | Selisih
- PERHATIKAN tanda minus (-) — jangan sampai hilang!
- Extract SEMUA baris (bisa 30-50+ baris)

OUTPUT JSON (JANGAN pakai markdown):
{{
  "success": true,
  "data": {{
    "tanggal": "2026-10-08",
    "items": [
      {{"rak_id": "900", "plu": "444756", "nama_produk": "WOW SPAGETI", "qty_sistem": 51, "qty_fisik": 51, "qty_var": 0, "nominal_adjust": 5333.58, "pic": null}}
    ],
    "total_nominal": 9948.14
  }},
  "missing": ["pic"],
  "warnings": []
}}

Output HANYA JSON.
"""

    _log(f"[Yui] Calling Groq...")
    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="file_parse", temperature=0.05)
    _log(f"[Yui] Groq result: ok={_ok}, model={_model}, err={_err}, text_len={len(_text) if _text else 0}")

    if not _ok:
        _log(f"[Yui] LLM gagal, coba fallback regex...")
        _fallback_data = _fallback_regex_extract(file_text)

        if _fallback_data and _fallback_data.get("items"):
            _log(f"[Yui] Fallback OK: {len(_fallback_data['items'])} items")
            return {
                "success": True,
                "data": _fallback_data,
                "missing": ["pic"],
                "warnings": [f"Extracted via regex: {len(_fallback_data['items'])} items"],
                "raw": file_text,
                "model": "regex_fallback",
            }

        return {
            "success": False,
            "data": None,
            "warnings": [f"Gagal parse: {_err}"],
            "missing": [],
            "raw": file_text,
        }

    _json = _extract_json(_text)
    _log(f"[Yui] JSON valid: {bool(_json)}")

    if _json and isinstance(_json, dict):
        _data = _json.get("data") or {}
        if isinstance(_data, dict):
            _items = _data.get("items", []) or []
            if _items:
                _log(f"[Yui] LLM sukses: {len(_items)} items")
                return {
                    "success": _json.get("success", True),
                    "data": _data,
                    "missing": _json.get("missing", []),
                    "warnings": _json.get("warnings", []),
                    "raw": _text,
                    "model": _model,
                }

    _log(f"[Yui] LLM gagal, coba fallback regex...")
    _fallback_data = _fallback_regex_extract(file_text)

    if _fallback_data and _fallback_data.get("items"):
        _log(f"[Yui] Fallback OK: {len(_fallback_data['items'])} items")
        return {
            "success": True,
            "data": _fallback_data,
            "missing": ["pic"],
            "warnings": [f"Extracted via regex: {len(_fallback_data['items'])} items"],
            "raw": _text,
            "model": "regex_fallback",
        }

    return {
        "success": False,
        "data": None,
        "warnings": ["Response bukan JSON valid"],
        "missing": [],
        "raw": _text,
    }


# =========================================================
# 💬 3. CHAT RESPONSE
# =========================================================
def yui_chat(user_message, conversation_history=None):
    """Chat response dari Yui."""
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
    "set_log_buffer",
]