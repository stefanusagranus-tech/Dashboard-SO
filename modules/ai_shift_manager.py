"""
AI Shift Manager (AI-1) v3 — Groq Edition
==========================================
Asisten cerdas untuk handle Master Shift.
Engine: Groq (Llama 3.1 8B) — 14.400 req/hari free.

Fitur:
1. parse_shift_update()      → Parse natural language (multi-nama + multi-hari)
2. suggest_pengganti()        → Saran pengganti kalau ada libur
3. check_conflict()           → Cek bentrok shift
4. chat_response()            → Q&A bebas tentang shift
"""

import json
import re
import concurrent.futures
import streamlit as st
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

from modules.master_shift_handler import (
    KODE_SHIFT,
    KEYWORD_TO_KODE,
    load_personil_master,
    load_master_shift_matrix,
    get_shift_hari_ini,
    parse_chat_update,
)
from modules.supabase_client import get_supabase


# =========================================================
# 🔧 MODEL PRIORITY — GROQ
# =========================================================
MODEL_PRIORITY = [
    "llama-3.1-8b-instant",        # 14.400 req/hari — paling banyak
    "llama-3.3-70b-versatile",     # 1.000 req/hari — lebih pinter
]


# =========================================================
# 🔧 HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _get_api_key():
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return ""


def _setup_genai():
    """Setup Groq client. Return: client atau None."""
    _key = _get_api_key()
    if not _key:
        print("[AI-1] Groq setup: API key kosong")
        return None
    if not GROQ_AVAILABLE:
        print("[AI-1] Groq setup: GROQ_AVAILABLE = False (import gagal?)")
        return None
    try:
        _client = Groq(api_key=_key)
        print("[AI-1] Groq client BERHASIL dibuat")
        return _client
    except Exception as _e:
        import traceback
        print(f"[AI-1] Groq setup error: {_e}")
        print(traceback.format_exc())
        return None


def _call_groq_raw(prompt):
    """
    Call Groq dengan auto-fallback model.
    Return: (ok, text, model, err, usage_dict)
    """
    _client = _setup_genai()
    if not _client:
        return False, "", None, "Groq client gagal init / API key missing", {}

    _last_error = None
    for _model_name in MODEL_PRIORITY:
        try:
            print(f"[AI-1] Trying {_model_name}...")

            _resp = _client.chat.completions.create(
                model=_model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )

            if _resp and _resp.choices and _resp.choices[0].message.content:
                _text = _resp.choices[0].message.content
                print(f"[AI-1] ✅ OK: {_model_name}")

                _usage_dict = {"model": _model_name, "success": True}
                try:
                    _usage = getattr(_resp, "usage", None)
                    if _usage:
                        _usage_dict["prompt_tokens"] = getattr(_usage, "prompt_tokens", 0)
                        _usage_dict["output_tokens"] = getattr(_usage, "completion_tokens", 0)
                except Exception:
                    pass

                return True, _text, _model_name, None, _usage_dict
            else:
                _last_error = f"Empty response dari {_model_name}"
                print(f"[AI-1] ⚠️ Empty: {_model_name}")

        except Exception as _e:
            _err_str = str(_e)

            if "429" in _err_str or "rate_limit" in _err_str.lower():
                print(f"[AI-1] 🚫 RATE LIMIT di {_model_name}")
                _last_error = f"Rate limit di {_model_name}"
                continue

            _last_error = _err_str
            print(f"[AI-1] ❌ {_model_name}: {_last_error[:150]}")
            continue

    return False, "", None, _last_error or "All models failed", {}


def _call_groq(prompt, hard_timeout=60):
    """Call Groq dengan hard timeout (thread-based). Record usage di main thread."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _exec:
            _fut = _exec.submit(_call_groq_raw, prompt)
            _ok, _text, _model, _err, _usage = _fut.result(timeout=hard_timeout)

        if _usage and _usage.get("success"):
            try:
                from modules.ocr_ai_handler import record_api_usage
                record_api_usage(
                    prompt_tokens=_usage.get("prompt_tokens", 0),
                    output_tokens=_usage.get("output_tokens", 0),
                    model_name=_usage.get("model", ""),
                    success=True,
                )
            except Exception as _e_rec:
                print(f"[AI-1] record usage error: {_e_rec}")
        elif not _ok:
            try:
                from modules.ocr_ai_handler import record_api_usage
                record_api_usage(success=False)
            except Exception:
                pass

        return _ok, _text, _model, _err

    except concurrent.futures.TimeoutError:
        print(f"[AI-1] HARD TIMEOUT {hard_timeout}s")
        try:
            from modules.ocr_ai_handler import record_api_usage
            record_api_usage(success=False)
        except Exception:
            pass
        return False, "", None, f"Hard timeout {hard_timeout}s"
    except Exception as e:
        return False, "", None, str(e)


def _extract_json(text):
    if not text:
        return None
    _match = re.search(r'\{[\s\S]*\}', text)
    if not _match:
        return None
    try:
        return json.loads(_match.group(0))
    except Exception:
        return None


def _build_personil_context():
    try:
        _df = load_personil_master(only_active=True)
        if _df.empty:
            return "Belum ada personil aktif."
        _list = _df.sort_values("urutan")["nama"].tolist()
        return "Personil aktif: " + ", ".join(_list)
    except Exception:
        return "Gagal load personil."


def _build_shift_today_context(tanggal=None):
    try:
        _tgl = tanggal or _now_jkt().date()
        _shift = get_shift_hari_ini(_tgl)
        if not _shift:
            return f"Belum ada shift untuk {_tgl.isoformat()}."
        _grouped = {}
        for _nama, _kode in _shift.items():
            _grouped.setdefault(_kode, []).append(_nama)
        _lines = [f"Shift {_tgl.isoformat()}:"]
        for _kode in ["P7", "S15", "M22", "O", "C", "AO"]:
            if _kode in _grouped:
                _lines.append(f"- {_kode}: {', '.join(_grouped[_kode])}")
        return "\n".join(_lines)
    except Exception as e:
        return f"Gagal load shift: {e}"


# =========================================================
# 📅 PARSE TANGGAL (MULTI-HARI)
# =========================================================
_HARI_MAP = {
    "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
    "jumat": 4, "sabtu": 5, "minggu": 6,
}


def _parse_tanggal_list(text, tanggal_hari_ini):
    _t = text.lower()
    _result = []

    if "besok" in _t and "lusa" in _t:
        _result.append(tanggal_hari_ini + timedelta(days=1))
        _result.append(tanggal_hari_ini + timedelta(days=2))
    elif "lusa" in _t:
        _result.append(tanggal_hari_ini + timedelta(days=2))
    elif "besok" in _t or "bsk" in _t:
        _result.append(tanggal_hari_ini + timedelta(days=1))

    if not _result and ("hari ini" in _t or re.search(r'\bini\b', _t)):
        _result.append(tanggal_hari_ini)

    for _match in re.finditer(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', text):
        try:
            _d, _m = int(_match.group(1)), int(_match.group(2))
            _y = _match.group(3)
            _y = int(_y) + 2000 if _y and int(_y) < 100 else (int(_y) if _y else tanggal_hari_ini.year)
            _result.append(date(_y, _m, _d))
        except Exception:
            pass

    _tgl_match = re.search(r'tanggal\s+([\d,\s&]+)', _t)
    if _tgl_match:
        _nums = re.findall(r'\d{1,2}', _tgl_match.group(1))
        for _n in _nums:
            try:
                _result.append(date(tanggal_hari_ini.year, tanggal_hari_ini.month, int(_n)))
            except Exception:
                pass

    for _hari, _idx in _HARI_MAP.items():
        if re.search(rf'\b{_hari}\b', _t):
            _days_ahead = (_idx - tanggal_hari_ini.weekday()) % 7
            if _days_ahead == 0:
                _days_ahead = 7
            _result.append(tanggal_hari_ini + timedelta(days=_days_ahead))

    if not _result:
        _result = [tanggal_hari_ini]

    _seen = set()
    _unique = []
    for _d in _result:
        if _d not in _seen:
            _seen.add(_d)
            _unique.append(_d)

    return sorted(_unique)


def _parse_tanggal_detect_label(text):
    _t = text.lower()
    _labels = []
    if "hari ini" in _t or re.search(r'\bini\b', _t):
        _labels.append("hari ini")
    if "besok" in _t or "bsk" in _t:
        _labels.append("besok")
    if "lusa" in _t:
        _labels.append("lusa")
    return " & ".join(_labels) if _labels else "hari ini"


# =========================================================
# 🧠 1. PARSE SHIFT UPDATE
# =========================================================
def parse_shift_update(chat_text, tanggal_hari_ini=None):
    if tanggal_hari_ini is None:
        tanggal_hari_ini = _now_jkt().date()

    _text = str(chat_text).strip()
    if not _text:
        return _empty_result(tanggal_hari_ini, _text, "Chat kosong")

    # STEP 1: COBA GROQ
    if _setup_genai():
        _groq_result = _parse_with_groq(_text, tanggal_hari_ini)
        if _groq_result and _groq_result.get("success"):
            return _groq_result["data"]

    # STEP 2: FALLBACK RULE-BASED
    _rule_result = parse_chat_update(_text, tanggal_hari_ini)

    if not _rule_result.get("shift_map") and not _rule_result.get("delete_targets"):
        _enhanced = _parse_enhanced(_text, tanggal_hari_ini)
        if _enhanced.get("shift_map") or _enhanced.get("delete_targets"):
            _rule_result = _enhanced

    _tgl_list = _parse_tanggal_list(_text, tanggal_hari_ini)
    _rule_result["tanggal_list"] = _tgl_list
    _rule_result["tanggal"] = _tgl_list[0] if _tgl_list else tanggal_hari_ini
    _rule_result["tanggal_detect"] = _parse_tanggal_detect_label(_text)
    _rule_result["engine"] = "rule-enhanced"
    _rule_result["ai_reasoning"] = "Parsed pakai rule-based enhanced (offline)"
    return _rule_result


def _empty_result(tanggal, raw_text, warning):
    return {
        "tanggal": tanggal,
        "tanggal_list": [tanggal],
        "tanggal_detect": "hari ini",
        "shift_map": {},
        "mode": "update",
        "delete_targets": [],
        "delete_all_dates": False,
        "raw_text": raw_text,
        "warning": warning,
        "engine": "rule-enhanced",
        "ai_reasoning": "",
    }


def _parse_with_groq(text, tanggal_hari_ini):
    _personil_ctx = _build_personil_context()
    _shift_today = _build_shift_today_context(tanggal_hari_ini)

    _prompt = f"""Kamu asisten HR cerdas untuk Toko C383.
Tugas: parse pesan user jadi struktur JSON.

KONTEKS HARI INI:
- Tanggal: {tanggal_hari_ini.isoformat()} ({tanggal_hari_ini.strftime('%A')})
- {_personil_ctx}

{_shift_today}

KODE SHIFT VALID:
- P7=Pagi(07:00), S15=Siang(15:00), M22=Malam(22:00), O=Libur, C=Cuti, AO=Additional Off

PESAN USER:
\"\"\"{text}\"\"\"

ATURAN PENTING:
1. Deteksi mode: "update" (default) atau "delete" (kalau ada kata hapus/delete/buang)
2. Deteksi tanggal — BISA MULTIPLE:
   - "hari ini" / "ini" → hari ini
   - "besok" → besok
   - "lusa" → lusa
   - "besok dan lusa" → 2 tanggal
   - "senin, selasa" → hari-hari tersebut
   - "DD/MM" atau "DD-MM" → tanggal eksplisit
3. Parse SEMUA nama yang disebutkan (bisa multi-nama pakai "dan"/","/"&")
4. STRIP kata umum dari nama: "hari", "ini", "besok", "lusa", "tanggal", "dan", "atau", "yang", "mau", "ganti", "jadi", "shift"
5. Nama personil di-UPPERCASE
6. Kalau nama gak match personil aktif, TETAP masukkan tapi kasih warning

FORMAT OUTPUT (JSON ONLY):
{{
  "mode": "update",
  "tanggal_list": ["2026-10-06", "2026-10-07"],
  "tanggal_detect": "hari ini dan besok",
  "shift_map": {{
    "KUSDEWI": "O",
    "ZAKI": "O"
  }},
  "delete_targets": [],
  "delete_all_dates": false,
  "reasoning": "User minta Kusdewi & Zaki libur hari ini dan besok"
}}

Kalau mode=delete, isi "delete_targets" (list nama) & "shift_map" kosong.
Output HANYA JSON.
"""

    _ok, _resp_text, _model, _err = _call_groq(_prompt)

    if not _ok:
        return {"success": False, "error": _err}

    _data = _extract_json(_resp_text)
    if not _data:
        return {"success": False, "error": "AI response bukan JSON valid"}

    _tgl_list = []
    for _tgl_str in (_data.get("tanggal_list") or []):
        try:
            _tgl_list.append(datetime.strptime(str(_tgl_str), "%Y-%m-%d").date())
        except Exception:
            pass

    if not _tgl_list:
        try:
            _tgl_str = _data.get("tanggal", tanggal_hari_ini.isoformat())
            _tgl_list = [datetime.strptime(_tgl_str, "%Y-%m-%d").date()]
        except Exception:
            _tgl_list = [tanggal_hari_ini]

    _mode = str(_data.get("mode", "update")).lower()
    if _mode not in ("update", "delete"):
        _mode = "update"

    _shift_map = {}
    for _nama, _kode in (_data.get("shift_map") or {}).items():
        _nama_clean = str(_nama).strip().upper()
        for _sw in ["HARI", "INI", "BESOK", "LUSA", "TANGGAL", "DAN", "ATAU"]:
            _nama_clean = _nama_clean.replace(_sw, "").strip()
        _kode_clean = str(_kode).strip().upper()
        if _kode_clean in KODE_SHIFT and _nama_clean:
            _shift_map[_nama_clean] = _kode_clean

    _warning = None
    try:
        _df_p = load_personil_master(only_active=True)
        if not _df_p.empty:
            _valid = set(_df_p["nama"].str.upper().tolist())
            _invalid = [n for n in _shift_map if n not in _valid]
            if _invalid:
                _warning = f"⚠️ Nama tidak dikenal: {', '.join(_invalid)}"
    except Exception:
        pass

    return {
        "success": True,
        "data": {
            "tanggal": _tgl_list[0],
            "tanggal_list": _tgl_list,
            "tanggal_detect": _data.get("tanggal_detect", "-"),
            "shift_map": _shift_map,
            "mode": _mode,
            "delete_targets": [
                str(n).strip().upper()
                for n in (_data.get("delete_targets") or [])
            ],
            "delete_all_dates": bool(_data.get("delete_all_dates", False)),
            "raw_text": text,
            "warning": _warning,
            "engine": f"groq ({_model})",
            "ai_reasoning": _data.get("reasoning", ""),
        },
    } 
# =========================================================
# 🔧 ENHANCED RULE-BASED PARSER
# =========================================================
_STOPWORDS = {
    "hari", "ini", "besok", "bsk", "lusa", "tanggal", "tgl",
    "dan", "serta", "atau", "yang", "akan", "mau", "ganti", "jadi",
    "shift", "ada", "untuk", "dengan", "di", "ke", "dari", "sama",
    "semua", "pada", "juga", "aja", "saja", "dong", "ya", "nih",
    "adalah", "itu", "the", "a", "an",
}

_HARI_NAMES = set(_HARI_MAP.keys())


def _is_valid_nama(w):
    _w = w.strip().upper()
    if len(_w) < 2:
        return False
    if _w.lower() in _STOPWORDS:
        return False
    if _w.lower() in _HARI_NAMES:
        return False
    if _w in KEYWORD_TO_KODE:
        return False
    return True


def _parse_enhanced(text, tanggal_hari_ini):
    """
    Enhanced parser: multi-nama + multi-hari.
    Handle: "Hari ini kusdewi dan zaki libur"
    """
    _t = text.lower()

    # === DETEKSI MODE ===
    _mode = "update"
    _delete_targets = []
    _delete_all_dates = False

    _kw_hapus = ["hapus", "delete", "hilangkan", "buang", "remove"]
    _kw_semua = ["semua", "seluruh", "all"]

    if any(_kw in _t for _kw in _kw_hapus):
        _mode = "delete"
        if any(_kw in _t for _kw in _kw_semua):
            _delete_all_dates = True

    # === DETEKSI TANGGAL LIST ===
    _tgl_list = _parse_tanggal_list(text, tanggal_hari_ini)

    # === DETEKSI KODE SHIFT ===
    _kode_ditemukan = None
    for _kw, _kode in KEYWORD_TO_KODE.items():
        if re.search(rf'\b{re.escape(_kw)}\b', _t):
            _kode_ditemukan = _kode
            break

    # === LOAD PERSONIL AKTIF ===
    _valid_names = []
    try:
        _df_p = load_personil_master(only_active=True)
        if not _df_p.empty:
            _valid_names = _df_p["nama"].str.upper().tolist()
    except Exception:
        pass

    # === EKSTRAK NAMA: MATCHING LANGSUNG KE PERSONIL ===
    _text_upper = text.upper()
    _kandidat = []
    for _nama in _valid_names:
        if re.search(rf'\b{re.escape(_nama)}\b', _text_upper):
            _kandidat.append(_nama)

    # Fallback kalau gak ada yang match
    if not _kandidat:
        _text_clean = text
        for _kw in KEYWORD_TO_KODE.keys():
            _text_clean = re.sub(rf'\b{re.escape(_kw)}\b', ' ', _text_clean, flags=re.IGNORECASE)
        for _sw in _STOPWORDS:
            _text_clean = re.sub(rf'\b{re.escape(_sw)}\b', ' ', _text_clean, flags=re.IGNORECASE)
        _text_clean = re.sub(r'[0-9:/,\-\.\!\?\&]', ' ', _text_clean)

        _kandidat_raw = [
            w.strip().upper()
            for w in re.findall(r'\b[A-Za-z]{2,}\b', _text_clean)
        ]
        _kandidat = [n for n in _kandidat_raw if n in _valid_names]

    _kandidat = list(dict.fromkeys(_kandidat))

    # === BUILD RESULT ===
    if _mode == "delete":
        return {
            "tanggal": _tgl_list[0],
            "tanggal_list": _tgl_list,
            "tanggal_detect": _parse_tanggal_detect_label(text),
            "shift_map": {},
            "mode": "delete",
            "delete_targets": _kandidat,
            "delete_all_dates": _delete_all_dates,
            "raw_text": text,
            "warning": None if _kandidat else "⚠️ Tidak ada nama terdeteksi",
        }

    if not _kode_ditemukan:
        return {
            "tanggal": _tgl_list[0],
            "tanggal_list": _tgl_list,
            "tanggal_detect": _parse_tanggal_detect_label(text),
            "shift_map": {},
            "mode": "update",
            "delete_targets": [],
            "delete_all_dates": False,
            "raw_text": text,
            "warning": "⚠️ Tidak ada kode shift yang dikenali",
        }

    _shift_map = {n: _kode_ditemukan for n in _kandidat}

    _warning = None
    if not _shift_map:
        _warning = f"⚠️ Tidak ada nama personil aktif yang terdeteksi."

    return {
        "tanggal": _tgl_list[0],
        "tanggal_list": _tgl_list,
        "tanggal_detect": _parse_tanggal_detect_label(text),
        "shift_map": _shift_map,
        "mode": "update",
        "delete_targets": [],
        "delete_all_dates": False,
        "raw_text": text,
        "warning": _warning,
    }


# =========================================================
# 💡 2. SUGGEST PENGGANTI
# =========================================================
def suggest_pengganti(nama_libur, tanggal=None, jumlah_saran=3):
    if tanggal is None:
        tanggal = _now_jkt().date()

    try:
        _df_personil = load_personil_master(only_active=True)
        if _df_personil.empty:
            return []

        _all_nama = _df_personil.sort_values("urutan")["nama"].tolist()
        _nama_libur_clean = str(nama_libur).strip().upper()

        _matrix = load_master_shift_matrix(tanggal.month, tanggal.year)

        if _matrix.empty:
            return [
                {"nama": n, "alasan": "Belum ada data shift bulan ini", "skor": 50}
                for n in _all_nama
                if n != _nama_libur_clean
            ][:jumlah_saran]

        _beban = {}
        _kolom_hari = [str(c) for c in range(1, 32) if str(c) in _matrix.columns]

        for _, _row in _matrix.iterrows():
            _nama = str(_row["NAMA"]).strip().upper()
            if _nama == _nama_libur_clean:
                continue
            _count = 0
            for _d in _kolom_hari:
                _kode = str(_row[_d]).strip().upper()
                if _kode in ("P7", "S15", "M22"):
                    _count += 1
            _beban[_nama] = _count

        _sorted = sorted(_beban.items(), key=lambda x: x[1])

        _saran = []
        for _nama, _beban_val in _sorted[:jumlah_saran]:
            _saran.append({
                "nama": _nama,
                "alasan": f"Baru {_beban_val} shift bulan ini",
                "skor": max(0, 100 - _beban_val * 5),
            })

        return _saran
    except Exception as e:
        print(f"[SUGGEST ERROR] {e}")
        return []


def ai_suggest_pengganti_text(nama_libur, tanggal=None):
    _rule_saran = suggest_pengganti(nama_libur, tanggal)

    if not _setup_genai() or not _rule_saran:
        return _format_saran_text(nama_libur, _rule_saran, "rule")

    _personil_ctx = _build_personil_context()
    _tgl = tanggal or _now_jkt().date()

    _saran_rule_str = "\n".join([
        f"- {s['nama']} ({s['alasan']}, skor {s['skor']})"
        for s in _rule_saran
    ])

    _prompt = f"""Kamu asisten HR. Ada personil libur: {nama_libur}
Tanggal: {_tgl.isoformat()}

{_personil_ctx}

Kandidat pengganti:
{_saran_rule_str}

Pilih 1-3 pengganti TERBAIK, jelaskan singkat.

FORMAT OUTPUT (JSON ONLY):
{{
  "rekomendasi": [
    {{"nama": "REZA", "alasan": "..."}},
    {{"nama": "PANDU", "alasan": "..."}}
  ],
  "catatan": "Ringkasan singkat"
}}
"""

    _ok, _resp_text, _model, _err = _call_groq(_prompt)
    if not _ok:
        return _format_saran_text(nama_libur, _rule_saran, "rule")

    _data = _extract_json(_resp_text)
    if not _data or "rekomendasi" not in _data:
        return _format_saran_text(nama_libur, _rule_saran, "rule")

    _lines = [f"💡 **Saran pengganti untuk {nama_libur}** ({_tgl.strftime('%d/%m/%Y')}):"]
    for _i, _r in enumerate(_data["rekomendasi"], 1):
        _lines.append(f"{_i}. **{_r.get('nama', '?')}** — {_r.get('alasan', '-')}")
    if _data.get("catatan"):
        _lines.append(f"\n📝 _{_data['catatan']}_")
    _lines.append(f"\n_Engine: groq ({_model})_")

    return "\n".join(_lines)


def _format_saran_text(nama_libur, saran_list, engine):
    _lines = [f"💡 **Saran pengganti untuk {nama_libur}**:"]
    for _i, _s in enumerate(saran_list, 1):
        _lines.append(f"{_i}. **{_s['nama']}** — {_s['alasan']}")
    _lines.append(f"\n_Engine: {engine}_")
    return "\n".join(_lines)


# =========================================================
# ⚠️ 3. CHECK CONFLICT
# =========================================================
def check_conflict(tanggal, shift_map):
    _issues = []
    if not shift_map:
        return _issues

    try:
        _df_personil = load_personil_master(only_active=True)
        if not _df_personil.empty:
            _valid = set(_df_personil["nama"].str.upper().tolist())
            for _nama, _kode in shift_map.items():
                if _nama not in _valid:
                    _issues.append({
                        "level": "warning",
                        "pesan": f"⚠️ **{_nama}** bukan personil aktif",
                    })
    except Exception:
        pass

    _shift_utama = {"P7", "S15", "M22"}
    _kode_di_map = set(shift_map.values())
    _kurang = _shift_utama - _kode_di_map

    if _kurang:
        _label = ", ".join(
            f"{KODE_SHIFT[k]['icon']} {KODE_SHIFT[k]['label']}"
            for k in sorted(_kurang)
        )
        _issues.append({
            "level": "warning",
            "pesan": f"⚠️ Shift berikut belum ada yang jaga: **{_label}**",
        })

    try:
        _existing = get_shift_hari_ini(tanggal)
        if _existing:
            _overlap = set(_existing.keys()) & set(shift_map.keys())
            if _overlap:
                _issues.append({
                    "level": "info",
                    "pesan": (
                        f"ℹ️ **{len(_overlap)}** personil akan di-update shiftnya: "
                        f"{', '.join(sorted(_overlap))}"
                    ),
                })
    except Exception:
        pass

    return _issues


def ai_check_conflict_text(tanggal, shift_map):
    _issues = check_conflict(tanggal, shift_map)
    if not _issues:
        return "✅ **Tidak ada konflik** — jadwal aman!"
    return "\n".join([f"- {i['pesan']}" for i in _issues])


# =========================================================
# 💬 4. CHAT RESPONSE
# =========================================================
def chat_response(user_message, conversation_history=None):
    if not user_message:
        return ""

    if _setup_genai():
        _history_str = ""
        if conversation_history:
            for _msg in conversation_history[-5:]:
                _role = _msg.get("role", "user")
                _content = _msg.get("content", "")
                _history_str += f"{_role}: {_content}\n"

        _personil_ctx = _build_personil_context()
        _tgl = _now_jkt().date()
        _shift_today = _build_shift_today_context(_tgl)
        _shift_besok = _build_shift_today_context(_tgl + timedelta(days=1))

        _prompt = f"""Kamu asisten HR untuk Toko C383 (retail).
Jawab pertanyaan user tentang jadwal shift dengan ramah & singkat.

KONTEKS:
- Hari ini: {_tgl.isoformat()} ({_tgl.strftime('%A')})
- {_personil_ctx}

{_shift_today}

{_shift_besok}

KODE SHIFT:
P7=Pagi(07:00), S15=Siang(15:00), M22=Malam(22:00), O=Libur, C=Cuti, AO=Additional Off

RIWAYAT:
{_history_str}

PERTANYAAN USER:
{user_message}

Jawab bahasa Indonesia santai, singkat (max 3 kalimat), pakai emoji kalau perlu.
"""

        _ok, _resp_text, _model, _err = _call_groq(_prompt)
        if _ok and _resp_text:
            return _resp_text.strip()
        print(f"[AI-1] Groq gagal, fallback rule. Err: {_err}")

    return _fallback_chat(user_message)


def _fallback_chat(user_message):
    _msg = user_message.lower()

    if "shift" in _msg and any(k in _msg for k in ["pagi", "siang", "malam"]):
        _tgl = _now_jkt().date()
        _shift = get_shift_hari_ini(_tgl)
        if not _shift:
            return "📭 Belum ada data shift hari ini."

        _kode_target = None
        if "pagi" in _msg:
            _kode_target = "P7"
        elif "siang" in _msg:
            _kode_target = "S15"
        elif "malam" in _msg:
            _kode_target = "M22"

        _nama_list = [n for n, k in _shift.items() if k == _kode_target]
        if _nama_list:
            _label = KODE_SHIFT[_kode_target]["label"]
            return f"👥 **{_label}** hari ini: {', '.join(_nama_list)}"
        else:
            return f"📭 Tidak ada yang shift {_kode_target} hari ini."

    if "personil" in _msg or "orang" in _msg:
        try:
            _df = load_personil_master(only_active=True)
            return f"👥 Ada **{len(_df)} personil aktif** saat ini."
        except Exception:
            return "❌ Gagal load data personil."

    return (
        "🤖 Maaf, aku belum bisa jawab itu. Coba tanya:\n"
        "- \"Siapa shift pagi hari ini?\"\n"
        "- \"Ada berapa personil aktif?\""
    )


__all__ = [
    "parse_shift_update",
    "suggest_pengganti",
    "ai_suggest_pengganti_text",
    "check_conflict",
    "ai_check_conflict_text",
    "chat_response",
]