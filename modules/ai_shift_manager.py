"""
AI Shift Manager (AI-1)
=======================
Asisten cerdas untuk handle Master Shift.

Fitur:
1. parse_shift_update()      → Parse natural language jadi shift_map
2. suggest_pengganti()        → Saran pengganti kalau ada libur
3. check_conflict()           → Cek bentrok shift
4. chat_response()            → Q&A bebas tentang shift

Hybrid mode:
- Coba Gemini dulu (akurat, natural)
- Fallback ke rule-based (offline, unlimited)
"""

import io
import json
import re
import streamlit as st
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

try:
    import google.generativeai as genai
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from modules.master_shift_handler import (
    KODE_SHIFT,
    KEYWORD_TO_KODE,
    load_personil_master,
    load_master_shift_matrix,
    get_shift_hari_ini,
    parse_chat_update,
)
from modules.supabase_client import get_supabase
from modules.ocr_ai_handler import MODEL_PRIORITY, record_api_usage


# =========================================================
# 🔧 HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


def _setup_genai():
    _key = _get_api_key()
    if not _key or not GEMINI_AVAILABLE:
        return False
    try:
        genai.configure(api_key=_key)
        return True
    except Exception:
        return False


def _call_gemini(prompt, image_bytes=None):
    """
    Call Gemini dengan auto-fallback model.
    Return: (success, text, model_used, error)
    """
    if not _setup_genai():
        return False, "", None, "Gemini not available / API key missing"

    _contents = [prompt]
    if image_bytes:
        try:
            _img = Image.open(io.BytesIO(image_bytes))
            _contents.append(_img)
        except Exception as e:
            return False, "", None, f"Image error: {e}"

    _last_error = None
    for _model_name in MODEL_PRIORITY:
        try:
            _m = genai.GenerativeModel(_model_name)
            _resp = _m.generate_content(_contents)

            if _resp and hasattr(_resp, "text") and _resp.text:
                # Record usage
                try:
                    _usage = getattr(_resp, "usage_metadata", None)
                    if _usage:
                        record_api_usage(
                            prompt_tokens=getattr(_usage, "prompt_token_count", 0),
                            output_tokens=getattr(_usage, "candidates_token_count", 0),
                            model_name=_model_name,
                            success=True,
                        )
                    else:
                        record_api_usage(model_name=_model_name, success=True)
                except Exception:
                    pass

                return True, _resp.text, _model_name, None
            else:
                _last_error = f"Empty response dari {_model_name}"
        except Exception as _e:
            _last_error = str(_e)
            continue

    try:
        record_api_usage(success=False)
    except Exception:
        pass

    return False, "", None, _last_error or "All models failed"


def _extract_json(text):
    """Extract JSON block dari response AI."""
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
    """Build context personil untuk prompt AI."""
    try:
        _df = load_personil_master(only_active=True)
        if _df.empty:
            return "Belum ada personil aktif."
        _list = _df.sort_values("urutan")["nama"].tolist()
        return "Personil aktif: " + ", ".join(_list)
    except Exception:
        return "Gagal load personil."


def _build_shift_today_context(tanggal=None):
    """Build context shift hari ini."""
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
# 🧠 1. PARSE SHIFT UPDATE
# =========================================================
def parse_shift_update(chat_text, tanggal_hari_ini=None):
    """
    Parse natural language → shift_map.
    Hybrid: Gemini dulu, fallback ke rule-based.

    Returns:
        dict {
            "tanggal": date,
            "tanggal_detect": str,
            "shift_map": {nama: kode},
            "mode": "update" | "delete",
            "delete_targets": [],
            "delete_all_dates": bool,
            "raw_text": str,
            "warning": str | None,
            "engine": "gemini" | "rule",
            "ai_reasoning": str,
        }
    """
    if tanggal_hari_ini is None:
        tanggal_hari_ini = _now_jkt().date()

    _text = str(chat_text).strip()
    if not _text:
        return _empty_result(tanggal_hari_ini, _text, "Chat kosong")

    # ============================================
    # STEP 1: COBA GEMINI
    # ============================================
    if _setup_genai():
        _gemini_result = _parse_with_gemini(_text, tanggal_hari_ini)
        if _gemini_result and _gemini_result.get("success"):
            return _gemini_result["data"]

    # ============================================
    # STEP 2: FALLBACK RULE-BASED
    # ============================================
    _rule_result = parse_chat_update(_text, tanggal_hari_ini)
    _rule_result["engine"] = "rule"
    _rule_result["ai_reasoning"] = "Parsed pakai rule-based (offline)"
    return _rule_result


def _empty_result(tanggal, raw_text, warning):
    return {
        "tanggal": tanggal,
        "tanggal_detect": "hari ini",
        "shift_map": {},
        "mode": "update",
        "delete_targets": [],
        "delete_all_dates": False,
        "raw_text": raw_text,
        "warning": warning,
        "engine": "rule",
        "ai_reasoning": "",
    }


def _parse_with_gemini(text, tanggal_hari_ini):
    """Parse pakai Gemini."""
    _personil_ctx = _build_personil_context()
    _shift_today = _build_shift_today_context(tanggal_hari_ini)

    _prompt = f"""Kamu adalah asisten HR cerdas untuk Toko C383.
Tugasmu: parse pesan user jadi struktur JSON.

KONTEKS HARI INI:
- Tanggal: {tanggal_hari_ini.isoformat()} ({tanggal_hari_ini.strftime('%A')})
- {_personil_ctx}

{_shift_today}

KODE SHIFT YANG VALID:
- P7  = Pagi (07:00)
- S15 = Siang (15:00)
- M22 = Malam (22:00)
- O   = Off/Libur
- C   = Cuti
- AO  = Additional Off

PESAN USER:
\"\"\"{text}\"\"\"

TUGAS:
1. Deteksi apakah user mau UPDATE shift atau DELETE shift
2. Deteksi tanggal (hari ini / besok / DD/MM/YYYY)
3. Parse nama + kode shift

FORMAT OUTPUT (JSON ONLY, NO MARKDOWN):
{{
  "mode": "update",
  "tanggal": "2026-10-06",
  "tanggal_detect": "hari ini",
  "shift_map": {{
    "REZA": "P7",
    "PANDU": "P7",
    "ZAKI": "S15"
  }},
  "delete_targets": [],
  "delete_all_dates": false,
  "reasoning": "User minta ganti shift besok..."
}}

Jika mode=delete, isi "delete_targets" dengan list nama, dan "shift_map" kosong.
Nama personil HARUS di-uppercase dan match dengan personil aktif.
Jika nama tidak dikenal, tetap masukkan tapi kasih warning di reasoning.

Output HANYA JSON.
"""

    _ok, _resp_text, _model, _err = _call_gemini(_prompt)

    if not _ok:
        return {"success": False, "error": _err}

    _data = _extract_json(_resp_text)
    if not _data:
        return {"success": False, "error": "AI response bukan JSON valid"}

    # Parse tanggal
    try:
        _tgl_str = _data.get("tanggal", tanggal_hari_ini.isoformat())
        _tanggal = datetime.strptime(_tgl_str, "%Y-%m-%d").date()
    except Exception:
        _tanggal = tanggal_hari_ini

    # Validasi mode
    _mode = str(_data.get("mode", "update")).lower()
    if _mode not in ("update", "delete"):
        _mode = "update"

    # Bersihin shift_map
    _shift_map = {}
    for _nama, _kode in (_data.get("shift_map") or {}).items():
        _nama_clean = str(_nama).strip().upper()
        _kode_clean = str(_kode).strip().upper()
        if _kode_clean in KODE_SHIFT:
            _shift_map[_nama_clean] = _kode_clean

    # Validasi nama vs personil
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
            "tanggal": _tanggal,
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
            "engine": f"gemini ({_model})",
            "ai_reasoning": _data.get("reasoning", ""),
        },
    }


# =========================================================
# 💡 2. SUGGEST PENGGANTI
# =========================================================
def suggest_pengganti(nama_libur, tanggal=None, jumlah_saran=3):
    """
    Saran pengganti kalau ada yang libur.
    Basis: rotasi shift terakhir + beban shift.

    Returns:
        list of dict {
            "nama": str,
            "alasan": str,
            "skor": int,
        }
    """
    if tanggal is None:
        tanggal = _now_jkt().date()

    try:
        _df_personil = load_personil_master(only_active=True)
        if _df_personil.empty:
            return []

        _all_nama = _df_personil.sort_values("urutan")["nama"].tolist()
        _nama_libur_clean = str(nama_libur).strip().upper()

        # Load shift minggu ini
        _start = tanggal - timedelta(days=7)
        _matrix = load_master_shift_matrix(tanggal.month, tanggal.year)

        if _matrix.empty:
            # Fallback: saran random tapi urut
            return [
                {
                    "nama": n,
                    "alasan": "Belum ada data shift minggu ini",
                    "skor": 50,
                }
                for n in _all_nama
                if n != _nama_libur_clean
            ][:jumlah_saran]

        # Hitung beban shift 7 hari terakhir
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

        # Sort by beban ascending (yang paling sedikit dapet shift = prioritas)
        _sorted = sorted(_beban.items(), key=lambda x: x[1])

        _saran = []
        for _nama, _beban_val in _sorted[:jumlah_saran]:
            _alasan = f"Baru {_beban_val} shift minggu ini"
            _skor = max(0, 100 - _beban_val * 5)
            _saran.append({
                "nama": _nama,
                "alasan": _alasan,
                "skor": _skor,
            })

        return _saran

    except Exception as e:
        print(f"[SUGGEST ERROR] {e}")
        return []


def ai_suggest_pengganti_text(nama_libur, tanggal=None):
    """
    Versi text: pakai Gemini kalau tersedia, fallback rule-based.
    """
    _rule_saran = suggest_pengganti(nama_libur, tanggal)

    if not _setup_genai() or not _rule_saran:
        return _format_saran_text(nama_libur, _rule_saran, "rule")

    _personil_ctx = _build_personil_context()
    _tgl = tanggal or _now_jkt().date()
    _shift_ctx = _build_shift_today_context(_tgl)

    _saran_rule_str = "\n".join([
        f"- {s['nama']} ({s['alasan']}, skor {s['skor']})"
        for s in _rule_saran
    ])

    _prompt = f"""Kamu asisten HR. Ada personil libur: {nama_libur}
Tanggal: {_tgl.isoformat()}

{_personil_ctx}
{_shift_ctx}

Kandidat pengganti (dari analisa beban shift):
{_saran_rule_str}

Tugas: Pilih 1-3 pengganti TERBAIK dan jelaskan alasan singkat (max 1 kalimat).

FORMAT OUTPUT:
{{
  "rekomendasi": [
    {{"nama": "REZA", "alasan": "..."}},
    {{"nama": "PANDU", "alasan": "..."}}
  ],
  "catatan": "Ringkasan singkat"
}}

Output HANYA JSON.
"""

    _ok, _resp_text, _model, _err = _call_gemini(_prompt)
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
    _lines.append(f"\n_Engine: gemini ({_model})_")

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
    """
    Cek konflik:
    - Personil ada di 2 shift berbeda di tanggal yang sama
    - Personil libur tapi dapet shift
    - Shift kosong (tidak ada yang jaga P7/S15/M22)

    Returns:
        list of dict {
            "level": "error" | "warning" | "info",
            "pesan": str,
        }
    """
    _issues = []

    if not shift_map:
        return _issues

    # Cek duplikat nama (dalam shift_map, gak mungkin karena dict)
    # Cek personil libur tapi dapet shift
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

    # Cek shift utama kosong
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

    # Cek tgl yang sama udah ada data
    try:
        _existing = get_shift_hari_ini(tanggal)
        if _existing:
            _overlap = set(_existing.keys()) & set(shift_map.keys())
            if _overlap:
                _issues.append({
                    "level": "info",
                    "pesan": (
                        f"ℹ️ **{len(_overlap)}** personil akan di-update shiftnya "
                        f"(sebelumnya sudah ada jadwal): {', '.join(sorted(_overlap))}"
                    ),
                })
    except Exception:
        pass

    return _issues


def ai_check_conflict_text(tanggal, shift_map):
    """Versi text dari check_conflict."""
    _issues = check_conflict(tanggal, shift_map)
    if not _issues:
        return "✅ **Tidak ada konflik** — jadwal aman!"
    return "\n".join([f"- {i['pesan']}" for i in _issues])


# =========================================================
# 💬 4. CHAT RESPONSE (Q&A BEBAS)
# =========================================================
def chat_response(user_message, conversation_history=None):
    """
    Q&A bebas tentang shift.
    Contoh: "Siapa yang shift pagi besok?", "Berapa kali Tika libur bulan ini?"

    Returns:
        str (response text)
    """
    if not user_message:
        return ""

    # Bangun context
    _personil_ctx = _build_personil_context()
    _tgl = _now_jkt().date()
    _shift_today = _build_shift_today_context(_tgl)
    _shift_besok = _build_shift_today_context(_tgl + timedelta(days=1))

    # Coba Gemini dulu
    if _setup_genai():
        _history_str = ""
        if conversation_history:
            for _msg in conversation_history[-5:]:
                _role = _msg.get("role", "user")
                _content = _msg.get("content", "")
                _history_str += f"{_role}: {_content}\n"

        _prompt = f"""Kamu asisten HR untuk Toko C383 (retail).
Jawab pertanyaan user tentang jadwal shift dengan ramah & singkat.

KONTEKS:
- Hari ini: {_tgl.isoformat()} ({_tgl.strftime('%A')})
- {_personil_ctx}

{_shift_today}

{_shift_besok}

KODE SHIFT:
P7=Pagi(07:00), S15=Siang(15:00), M22=Malam(22:00), O=Libur, C=Cuti, AO=Additional Off

RIWAYAT PERCAKAPAN:
{_history_str}

PERTANYAAN USER:
{user_message}

Jawab dengan bahasa Indonesia santai, singkat (max 3 kalimat), pakai emoji kalau perlu.
Jika tidak tahu jawabannya, bilang tidak tahu dan sarankan fitur yang sesuai.
"""

        _ok, _resp_text, _model, _err = _call_gemini(_prompt)
        if _ok and _resp_text:
            return _resp_text.strip()

    # Fallback: rule-based simple
    return _fallback_chat(user_message)


def _fallback_chat(user_message):
    """Fallback rule-based untuk chat."""
    _msg = user_message.lower()

    # Siapa shift pagi/siang/malam?
    if "shift" in _msg and any(k in _msg for k in ["pagi", "siang", "malam"]):
        _tgl = _now_jkt().date()
        _shift = get_shift_hari_ini(_tgl)
        if not _shift:
            return "📭 Belum ada data shift hari ini. Coba input dulu via tab 💬 Chat Update."

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

    # Berapa personil aktif?
    if "personil" in _msg or "orang" in _msg:
        try:
            _df = load_personil_master(only_active=True)
            return f"👥 Ada **{len(_df)} personil aktif** saat ini."
        except Exception:
            return "❌ Gagal load data personil."

    return (
        "🤖 Maaf, aku belum bisa jawab itu. Coba tanya:\n"
        "- \"Siapa shift pagi hari ini?\"\n"
        "- \"Ada berapa personil aktif?\"\n"
        "- \"Besok siapa yang libur?\""
    )


# =========================================================
# 🎯 PUBLIC API
# =========================================================
__all__ = [
    "parse_shift_update",
    "suggest_pengganti",
    "ai_suggest_pengganti_text",
    "check_conflict",
    "ai_check_conflict_text",
    "chat_response",
]
