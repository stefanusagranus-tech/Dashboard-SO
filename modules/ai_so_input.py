"""
AI SO Input — Yui (AI-2)
==========================
Pembantu Input Stock Opname.

Persona: Rekan kerja profesional yang udah biasa ngurus SO.
- Ngobrol natural, gak kaku
- Fokus ke akurasi data
- Proaktif koreksi kalau ada anomali
- Paham konteks retail (barcode, SKU, selisih, dll)
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


def _call_yui_groq(prompt, hard_timeout=60, function="parse", temperature=0.7):
    """Call Groq untuk Yui dengan auto-pause check."""
    if check_auto_pause("ai-2"):
        return False, "", None, "Auto-pause: quota Yui hampir habis"

    _client = _setup_yui_client()
    if not _client:
        return False, "", None, "Yui client gagal init"

    _cfg = get_ai_config("ai-2")
    _models = _cfg.get("model_priority", ["openai/gpt-oss-20b", "openai/gpt-oss-120b"])

    def _try_models():
        _last_err = None
        for _model_name in _models:
            try:
                _resp = _client.chat.completions.create(
                    model=_model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=2048,
                )
                if _resp and _resp.choices and _resp.choices[0].message.content:
                    _text = _resp.choices[0].message.content
                    _usage = {"model": _model_name, "success": True}
                    try:
                        _u = getattr(_resp, "usage", None)
                        if _u:
                            _usage["prompt_tokens"] = getattr(_u, "prompt_tokens", 0)
                            _usage["output_tokens"] = getattr(_u, "completion_tokens", 0)
                    except Exception:
                        pass
                    return True, _text, _model_name, None, _usage
                _last_err = f"Empty response dari {_model_name}"
            except Exception as _e:
                _last_err = str(_e)
                if "429" in _last_err or "rate_limit" in _last_err.lower():
                    continue
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
    _match = re.search(r'\{[\s\S]*\}', text)
    if not _match:
        return None
    try:
        return json.loads(_match.group(0))
    except Exception:
        return None


# =========================================================
# 🎯 PERSONA YUI — PROFESIONAL & NATURAL
# =========================================================
def _build_yui_system_prompt():
    return """<role>
Kamu adalah **Yui** — Data Entry Specialist untuk Toko C383 (retail).
Kamu udah bertahun-tahun ngurusin input data, stock opname, dan rekap laporan.
User (Bos) mempercayakan input SO ke kamu karena kamu **teliti, cekatan, dan paham seluk-beluk retail**.
</role>

<persona>
Kamu BUKAN chatbot kaku. Kamu rekan kerja yang asik.
Gaya ngobrol:
- Santai, natural, gak formal banget
- Kadang pake "Oke Bos", "Sip", "Beres", "Aman", "Siap"
- Kalau ada yang aneh, langsung bilang — gak nunggu ditanya
- Gak pake "Ara ara" atau bahasa lebay kayak Kurumi
- Gak pake "Fufufu" atau ketawa aneh-aneh
- Fokus, cepet, langsung ke poin
- Kalau ada data yang perlu diklarifikasi, tanya singkat & jelas
- Proaktif: kasih warning kalau ada anomali data

Contoh gaya bicara:
"Oke Bos, aku cek dulu ya... ⏳"
"Hmm, ada yang perlu diklarifikasi nih"
"Sip, data udah lengkap. Aku simpen ya?"
"Eh Bos, nominal ini kayaknya kegedean deh. Cek lagi? 🤔"
"Beres! Data SO udah masuk sistem."
</persona>

<expertise>
Kamu PAHAM banget soal:
- **Barcode/SKU/PLU**: Kode unik produk, penting buat tracking
- **Stock Opname (SO)**: Audit fisik vs sistem
- **QTYCOUNT vs QTYONHAND**: Fisik vs catatan sistem
- **QTYVAR**: Selisih (fisik - sistem), bisa + atau -
- **Selisih minus**: Barang kurang → input usage/kredit memo
- **Selisih plus**: Barang lebih → verifikasi purchase receipt
- **Nominal adjustment**: QTYVAR × harga jual
- **Data validation**: Cek format, konsistensi, anomali [citation:3]
- **Data cleaning**: Normalisasi, deduplikasi, validasi range [citation:18]
- **Retail SOP**: SO per rak, PIC, H+2 input, 2x SO per bulan
- **3-second check**: Setelah input, cek lagi nama/rak/nominal/PIC sebelum save [citation:16]
</expertise>

<task>
Kamu bantu Bos input SO via:
1. Parse natural language → structured data
2. Parse file text (PDF/OCR/Excel) → structured data
3. Validasi input (nominal aneh, rak gak wajar, dll)
4. Generate rekap SO
5. Generate PDF SO
</task>

<rules>
1. **JANGAN NGARANG ANGKA**. Kalau gak yakin, tanya.
2. **Kalau data aneh** (nominal > 1jt per rak, atau rak gak ada di master), kasih warning.
3. **Selalu konfirmasi** sebelum save — minimal tampilin preview.
4. **PIC wajib**. Kalau gak ada di file/chat, tanya.
5. **Format output JSON** kalau diminta parse — jangan tambah teks lain.
6. **Format output natural** kalau lagi ngobrol biasa — santai aja.
7. **Cek kosistensi**: Kalau input Q51 minus 28rb tapi tanggal 5 hari lalu, warning.
8. **Gak pake emoji berlebihan**. Cukup 1-2 kalau perlu.
9. **Jawab singkat**. Bos gak suka bertele-tele.
10. **Kalau ada error parsing**, bilang jujur + tanya Bos.
</rules>

<output_format_parse>
Kalau diminta parse, WAJIB output JSON VALID:
{
  "intent": "parse_so",
  "success": true,
  "data": {
    "tanggal": "YYYY-MM-DD",
    "items": [
      {"rak_id": "Q51", "nominal_adjust": -28653, "pic": "PANDU", "keterangan": ""}
    ]
  },
  "warnings": ["Nominal Q51 cukup besar, cek lagi"]
}
</output_format_parse>

<output_format_chat>
Kalau lagi ngobrol biasa:
- Santai, kayak temen kerja
- Max 5-6 baris
- Kalau kasih info, pake bullet biar rapi
- Jangan pake "Ara ara" atau "Kihihihi"
</output_format_chat>
"""


# =========================================================
# 🧠 1. PARSE NATURAL LANGUAGE
# =========================================================
def parse_natural_language(text, rak_master_list=None):
    """
    Parse input SO dari chat natural language.

    Contoh:
        "Q51 minus 28rb, Q52 minus 5rb, PIC Pandu"
        "Rak Q51 selisih -28.653 PIC PANDU"
        "Input SO: Q51 -28653 PANDU, Q52 -5075 PANDU"

    Returns:
        dict {
            success: bool,
            data: {tanggal, items: [...]},
            warnings: [...],
            raw: str,
        }
    """
    if not text or not str(text).strip():
        return {"success": False, "data": None, "warnings": [], "raw": ""}

    _context = ""
    if rak_master_list:
        _context = f"\n\nDaftar rak master (contoh): {', '.join(rak_master_list[:50])}"

    _prompt = f"""{_build_yui_system_prompt()}

Bos ngasih perintah input SO via chat:

"{text}"

Tanggal hari ini: {_now_jkt().date().isoformat()}

TASK: Parse jadi JSON.

ATURAN:
1. Kalau tanggal gak disebut, pake hari ini.
2. Kalau PIC gak disebut, set null (nanti ditanya).
3. Nominal bisa "-28rb", "-28.653", "minus 28653", dll — konversi ke integer.
4. Kalau rak gak jelas, skip + kasih warning.
5. Deteksi anomali: nominal > 1jt per rak → warning.

{_context}

OUTPUT JSON VALID (jangan tambah teks lain):
{{
  "intent": "parse_so",
  "success": true,
  "data": {{
    "tanggal": "YYYY-MM-DD",
    "items": [
      {{"rak_id": "Q51", "nominal_adjust": -28653, "pic": "PANDU", "keterangan": ""}}
    ]
  }},
  "warnings": []
}}
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
# 📄 2. PARSE FILE TEXT (PDF/OCR/Excel)
# =========================================================
def parse_file_text(file_text, file_type="pdf", context=None):
    """
    Parse text dari file (PDF/OCR/Excel) → structured SO data.

    Args:
        file_text: text content dari file
        file_type: 'pdf' / 'image_ocr' / 'excel' / 'csv'
        context: dict {tanggal, rak_id, pic} — kalau ada

    Returns:
        dict {
            success: bool,
            data: {tanggal, items: [...]},
            warnings: [...],
            missing: [...],  # field yang belum ada (tanggal/pic/rak)
            raw: str,
        }
    """
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

    _prompt = f"""{_build_yui_system_prompt()}

Bos upload file SO. Ini isinya:

=== MULAI FILE ===
{str(file_text)[:4000]}
=== AKHIR FILE ===

Tipe file: {file_type}
Konteks tambahan: {_ctx_str if _ctx_str else "(tidak ada)"}

Tanggal hari ini: {_now_jkt().date().isoformat()}

TASK: Extract data SO dari file ini jadi JSON.

ATURAN:
1. **Cari kode rak** — bisa ada di header file, atau di kolom "Rak", atau di nama file.
   Kalau gak ada, set null (nanti ditanya Bos).
2. **Cari tanggal** — dari header / tanggal di file.
   Kalau gak ada, pake konteks atau hari ini.
3. **Cari PIC** — kalau ada di file, extract.
   Kalau gak ada, set null (nanti ditanya Bos).
4. **Nominal adjust**: 
   - Kalau ada kolom "Selisih" / "QTYVAR" → butuh harga jual buat hitung nominal.
   - Kalau gak ada harga jual, set nominal = null + warning "Butuh nominal manual".
   - Kalau ada langsung nominal Rp, extract.
5. **Deteksi anomali**: 
   - Nominal > 1jt → warning
   - QTYVAR > 10 per item → warning
6. **Items** — minimal 1 produk. Kalau file berisi banyak produk, masukkan semua.

OUTPUT JSON VALID (jangan tambah teks lain):
{{
  "success": true,
  "data": {{
    "tanggal": "YYYY-MM-DD atau null",
    "rak_id": "Q51 atau null",
    "pic": "PANDU atau null",
    "total_nominal": -28653,
    "items": [
      {{"plu": "433288", "nama_produk": "BAYGON", "qty_sistem": 5, "qty_fisik": 3, "qty_var": -2}}
    ]
  }},
  "missing": ["pic"],
  "warnings": []
}}
"""

    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="file_parse", temperature=0.2)

    if not _ok:
        return {"success": False, "data": None, "warnings": [f"Error: {_err}"], "missing": [], "raw": file_text}

    _json = _extract_json(_text)
    if not _json:
        return {"success": False, "data": None, "warnings": ["Response bukan JSON valid"], "missing": [], "raw": _text}

    return {
        "success": _json.get("success", True),
        "data": _json.get("data"),
        "missing": _json.get("missing", []),
        "warnings": _json.get("warnings", []),
        "raw": _text,
        "model": _model,
    }


# =========================================================
# 💬 3. CHAT RESPONSE — NGOBROL SANTAI
# =========================================================
def yui_chat(user_message, conversation_history=None):
    """
    Chat response dari Yui — santai, natural, profesional.

    Returns:
        dict {text, intent, parsed}
    """
    if not user_message:
        return {"text": "", "intent": "chat", "parsed": None}

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _role = _msg.get("role", "user")
            _content = _msg.get("content", "")
            _history_str += f"{_role}: {_content}\n"

    _prompt = f"""{_build_yui_system_prompt()}

Riwayat chat terakhir:
{_history_str if _history_str else "(belum ada)"}

Bos: "{user_message}"

Balas sebagai Yui. Santai, kayak rekan kerja. Kalau Bos ngasih perintah input SO, bilang "oke aku catat" / "siap" — jangan langsung parse (nanti ada step parse terpisah).
"""

    _ok, _text, _model, _err = _call_yui_groq(_prompt, function="chat", temperature=0.7)

    if not _ok:
        return {
            "text": f"Waduh, aku lagi error nih Bos. Coba lagi ya. ({str(_err)[:50]})",
            "intent": "chat",
            "parsed": None,
        }

    return {
        "text": _text.strip(),
        "intent": "chat",
        "parsed": None,
    }


# =========================================================
# ✅ 4. VALIDASI INPUT
# =========================================================
def validate_so_data(data, rak_master_df=None):
    """
    Validasi data SO — cek anomali.

    Returns:
        dict {valid: bool, errors: [], warnings: []}
    """
    _errors = []
    _warnings = []

    if not data:
        return {"valid": False, "errors": ["Data kosong"], "warnings": []}

    # Cek items
    _items = data.get("items", [])
    if not _items:
        _errors.append("Gak ada item SO")

    # Cek PIC
    if not data.get("pic"):
        _warnings.append("PIC belum diisi")

    # Cek tanggal
    if not data.get("tanggal"):
        _warnings.append("Tanggal belum diisi")

    # Cek tiap item
    for _item in _items:
        _rak = _item.get("rak_id", "")
        _nom = _item.get("nominal_adjust")

        # Cek rak ada di master
        if rak_master_df is not None and not rak_master_df.empty:
            _rak_list = rak_master_df["rak_id"].astype(str).str.upper().tolist()
            if _rak and _rak.upper() not in _rak_list:
                _warnings.append(f"Rak {_rak} gak ada di master")

        # Cek nominal wajar
        if _nom is not None and abs(float(_nom)) > 1_000_000:
            _warnings.append(f"Nominal {_rak} ({_nom}) kegedean, cek lagi")

    return {
        "valid": len(_errors) == 0,
        "errors": _errors,
        "warnings": _warnings,
    }


# =========================================================
# 📊 5. REKAP SO
# =========================================================
def generate_so_rekap(so_data):
    """
    Generate rekap SO dari data.

    Returns:
        dict {
            total_rak, total_nominal, total_minus, total_plus,
            items_summary: [...]
        }
    """
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


# =========================================================
# EXPORT
# =========================================================
__all__ = [
    "parse_natural_language",
    "parse_file_text",
    "yui_chat",
    "validate_so_data",
    "generate_so_rekap",
]
