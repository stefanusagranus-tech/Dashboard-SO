"""
AI Shift Manager — Hana (AI-1) v4
====================================
Logic untuk master shift: parse (Groq AI + fallback), save, read, delete.
Fungsi lengkap untuk Hana — Master Shift Specialist.
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

from services.ai_config import get_ai_api_key, get_ai_config
from services.token_monitor import record_usage_v2, check_auto_pause
from services.supabase_client import get_supabase


# =========================================================
# HELPER — Waktu & Log
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _log(msg):
    print(f"[Hana] {msg}")


# =========================================================
# MAPPING KODE SHIFT
# =========================================================
SHIFT_MAP = {
    "P7": "Pagi",
    "S15": "Siang",
    "M22": "Malam",
    "O": "Libur",
    "CUTI": "Cuti",
}

SHIFT_MAP_REVERSE = {
    "pagi": "P7",
    "siang": "S15",
    "malam": "M22",
    "libur": "O",
    "off": "O",
    "cuti": "CUTI",
}

SHIFT_EMOJI = {
    "P7": "🟢",
    "S15": "🟡",
    "M22": "🔴",
    "O": "⚪",
    "CUTI": "⚫",
}


# =========================================================
# STOPWORDS
# =========================================================
STOPWORDS = {
    "PAGI", "SIANG", "MALAM", "MALEM", "MLM", "SORE", "SOREMALEM",
    "LIBUR", "OFF", "CUTI", "MASUK", "IZIN", "SAKIT",
    "ATUR", "SET", "UBAH", "GANTI", "PINDAH", "PIND", "JADWAL", "SHIFT",
    "BESOK", "ESOK", "LUSA", "KEMARIN", "HARI", "INI", "ITU", "SKRG",
    "SEKARANG", "TODAY", "TOMORROW", "NEXT", "DEPAN", "LALU", "NANTI",
    "KE", "DAN", "YANG", "DI", "PADA", "UNTUK", "DENGAN", "BUAT", "TO",
    "MINGGU", "SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "SABTU", "AHAD", "JUMAAT",
    "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
    "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER",
    "JAN", "FEB", "MAR", "APR", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES",
    "BOS", "HANA", "YUI", "REI", "KURUMI",
    "YA", "OKE", "OK", "BAIK", "SIAP", "MOHON", "TOLONG",
    "KALAU", "JIKA", "BILA", "APAKAH", "APA", "SIAPA", "BAGAIMANA", "GIMANA",
    "SEMUA", "SEMUANYA", "ORANG", "KARYAWAN", "TIM", "ANAK",
}


# =========================================================
# PARSE TANGGAL NATURAL
# =========================================================
def parse_tanggal(text: str, today=None) -> date:
    """Parse teks tanggal natural jadi date."""
    _today = today or _now_jkt().date()
    _text = str(text).lower().strip()

    if any(k in _text for k in ["hari ini", "today", "skrg", "sekarang"]):
        return _today

    if any(k in _text for k in ["besok", "esok", "tomorrow", "bsk"]):
        return _today + timedelta(days=1)

    if "lusa" in _text:
        return _today + timedelta(days=2)

    if "kemarin" in _text:
        return _today - timedelta(days=1)

    _hari_map = {
        "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
        "jumat": 4, "jum'at": 4, "sabtu": 5, "minggu": 6, "ahad": 6,
    }
    for _nama, _idx in _hari_map.items():
        if _nama in _text:
            _days_ahead = (_idx - _today.weekday()) % 7
            if _days_ahead == 0:
                _days_ahead = 7
            if "depan" in _text or "next" in _text:
                _days_ahead += 7
            return _today + timedelta(days=_days_ahead)

    _bulan_map = {
        "jan": 1, "januari": 1, "feb": 2, "februari": 2,
        "mar": 3, "maret": 3, "apr": 4, "april": 4,
        "mei": 5, "may": 5, "jun": 6, "juni": 6,
        "jul": 7, "juli": 7, "agu": 8, "agustus": 8, "aug": 8,
        "sep": 9, "september": 9, "okt": 10, "oktober": 10, "oct": 10,
        "nov": 11, "november": 11, "des": 12, "desember": 12, "dec": 12,
    }

    _match = re.search(r'(\d{1,2})\s+([a-z]+)', _text)
    if _match:
        _day = int(_match.group(1))
        _month = _bulan_map.get(_match.group(2))
        if _month:
            _year = _today.year
            if _month < _today.month:
                _year += 1
            try:
                return date(_year, _month, _day)
            except ValueError:
                pass

    _match = re.search(r'(\d{1,2})[\-\/](\d{1,2})(?:[\-\/](\d{2,4}))?', _text)
    if _match:
        _day = int(_match.group(1))
        _month = int(_match.group(2))
        _year = int(_match.group(3)) if _match.group(3) else _today.year
        if _year < 100:
            _year += 2000
        try:
            return date(_year, _month, _day)
        except ValueError:
            pass

    return _today


def _parse_tanggal_list(text, today):
    """Parse multi-hari: 'besok dan lusa', 'senin, selasa'."""
    _t = text.lower()
    _result = []

    if "besok" in _t and "lusa" in _t:
        _result = [today + timedelta(days=1), today + timedelta(days=2)]
    elif "lusa" in _t:
        _result = [today + timedelta(days=2)]
    elif "besok" in _t or "bsk" in _t:
        _result = [today + timedelta(days=1)]
    elif "hari ini" in _t or re.search(r'\bini\b', _t):
        _result = [today]

    # Match DD/MM/YYYY
    for _m in re.finditer(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', text):
        try:
            _d, _mo = int(_m.group(1)), int(_m.group(2))
            _y = _m.group(3)
            _y = int(_y) + 2000 if _y and int(_y) < 100 else (int(_y) if _y else today.year)
            _result.append(date(_y, _mo, _d))
        except Exception:
            pass

    # Nama hari
    _hari_map = {
        "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
        "jumat": 4, "sabtu": 5, "minggu": 6,
    }
    for _hari, _idx in _hari_map.items():
        if re.search(rf'\b{_hari}\b', _t):
            _days_ahead = (_idx - today.weekday()) % 7
            if _days_ahead == 0:
                _days_ahead = 7
            _result.append(today + timedelta(days=_days_ahead))

    if not _result:
        _result = [today]

    # Dedupe & sort
    _seen = set()
    _unique = []
    for _d in sorted(_result):
        if _d not in _seen:
            _seen.add(_d)
            _unique.append(_d)

    return _unique


def _parse_tanggal_detect_label(text):
    """Label tanggal untuk display."""
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
# HELPER — JSON Extract
# =========================================================
def _extract_json(text):
    """Extract JSON dari response AI."""
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
# GET PERSONIL AKTIF
# =========================================================
def get_personil_aktif() -> list:
    """Ambil semua personil aktif."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return []
        _res = _sb.table("personil_master").select("*").eq("aktif", True).order("urutan").execute()
        return _res.data if _res.data else []
    except Exception as e:
        _log(f"get_personil_aktif error: {e}")
        return []


# =========================================================
# HELPER — Build Context
# =========================================================
def _build_personil_context():
    """Konteks daftar personil aktif."""
    try:
        _personil = get_personil_aktif()
        if not _personil:
            return "Belum ada personil aktif."
        _list = [p["nama"] for p in _personil]
        return "Personil aktif: " + ", ".join(_list)
    except Exception:
        return "Gagal load personil."

# =========================================================
# SAVE SHIFT — dengan deteksi konflik
# =========================================================
def save_shift(tanggal, nama, kode_shift, action="update", force=False):
    """Simpan/update/hapus shift."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"success": False, "message": "Supabase gak konek"}

        if isinstance(tanggal, date):
            _tgl_str = tanggal.isoformat()
        else:
            _tgl_str = str(tanggal)[:10]

        _nama = str(nama).upper().strip()

        if action == "delete":
            _sb.table("master_shift").delete().eq("tanggal", _tgl_str).eq("nama", _nama).execute()
            return {
                "success": True,
                "message": f"✅ Shift {_nama} tanggal {_tgl_str} dihapus",
                "data": {"nama": _nama, "tanggal": _tgl_str, "action": "delete"},
            }

        _kode = str(kode_shift).upper().strip()
        if _kode not in SHIFT_MAP:
            return {"success": False, "message": f"Kode shift '{_kode}' tidak valid"}

        _existing = (
            _sb.table("master_shift")
            .select("id, kode_shift")
            .eq("tanggal", _tgl_str)
            .eq("nama", _nama)
            .execute()
        )

        _row_data = {
            "tanggal": _tgl_str,
            "nama": _nama,
            "kode_shift": _kode,
            "sumber": "hana_chat",
            "catatan": " | Update via Hana",
            "updated_at": _now_jkt().isoformat(),
        }

        if _existing.data and len(_existing.data) > 0:
            _row_id = _existing.data[0]["id"]
            _old_kode = _existing.data[0]["kode_shift"]

            if _old_kode == _kode:
                return {
                    "success": True,
                    "message": f"ℹ️ Shift {_nama} tanggal {_tgl_str} sudah {SHIFT_MAP[_kode]}",
                    "data": {"nama": _nama, "tanggal": _tgl_str, "kode_shift": _kode, "status": "no_change"},
                }

            _sb.table("master_shift").update(_row_data).eq("id", _row_id).execute()
            _msg = f"✅ Shift {_nama} diupdate: {SHIFT_MAP.get(_old_kode, _old_kode)} → {SHIFT_MAP[_kode]}"
        else:
            _row_data["created_at"] = _now_jkt().isoformat()
            _sb.table("master_shift").insert(_row_data).execute()
            _msg = f"✅ Shift {_nama} disimpan: {SHIFT_MAP[_kode]}"

        return {
            "success": True,
            "message": _msg,
            "data": {
                "nama": _nama,
                "tanggal": _tgl_str,
                "kode_shift": _kode,
                "shift_nama": SHIFT_MAP[_kode],
                "action": "update",
            },
        }

    except Exception as e:
        _log(f"save_shift error: {e}")
        return {"success": False, "message": f"Gagal: {str(e)[:150]}"}


# =========================================================
# SAVE BATCH
# =========================================================
def save_batch(items, tanggal):
    """Simpan banyak shift sekaligus."""
    _saved = 0
    _errors = []

    for _item in items:
        _res = save_shift(
            tanggal=tanggal,
            nama=_item.get("nama"),
            kode_shift=_item.get("kode_shift"),
            action="update",
        )
        if _res.get("success"):
            _saved += 1
        else:
            _errors.append(_item.get("nama"))

    _msg = f"✅ {_saved} shift tersimpan"
    if _errors:
        _msg += f" | ⚠️ Gagal: {', '.join(_errors)}"

    return {
        "success": _saved > 0,
        "saved": _saved,
        "message": _msg,
    }


# =========================================================
# GET MASTER SHIFT — list dengan filter
# =========================================================
def get_master_shift(tgl_start=None, tgl_end=None, nama_filter=None, limit=500):
    """Ambil daftar shift dari Supabase."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"success": False, "data": [], "error": "Supabase gak konek"}

        _today = _now_jkt().date()
        _start = tgl_start or _today
        _end = tgl_end or _today

        _start_str = _start.isoformat() if isinstance(_start, date) else str(_start)[:10]
        _end_str = _end.isoformat() if isinstance(_end, date) else str(_end)[:10]

        _q = (
            _sb.table("master_shift")
            .select("*")
            .gte("tanggal", _start_str)
            .lte("tanggal", _end_str)
        )

        if nama_filter:
            _q = _q.eq("nama", str(nama_filter).upper())

        _q = _q.order("tanggal", desc=False).order("nama", desc=False).limit(limit)

        _res = _q.execute()
        _rows = _res.data if _res.data else []

        for _r in _rows:
            _kode = _r.get("kode_shift", "O")
            _r["shift_nama"] = SHIFT_MAP.get(_kode, "Unknown")
            _r["shift_emoji"] = SHIFT_EMOJI.get(_kode, "❓")

        return {
            "success": True,
            "data": _rows,
            "total": len(_rows),
            "periode": f"{_start_str} s/d {_end_str}",
        }

    except Exception as e:
        _log(f"get_master_shift error: {e}")
        return {"success": False, "data": [], "error": str(e)[:150]}


# =========================================================
# CHECK KONFLIK
# =========================================================
def check_konflik(nama, tanggal, kode_shift_baru):
    """Cek konflik: personil udah punya shift lain di tanggal sama."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"ada_konflik": False}

        _tgl_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]
        _nama = str(nama).upper()

        _res = (
            _sb.table("master_shift")
            .select("kode_shift")
            .eq("tanggal", _tgl_str)
            .eq("nama", _nama)
            .execute()
        )

        if _res.data and len(_res.data) > 0:
            _kode_lama = _res.data[0]["kode_shift"]
            if _kode_lama != kode_shift_baru:
                return {
                    "ada_konflik": True,
                    "kode_lama": _kode_lama,
                    "shift_lama": SHIFT_MAP.get(_kode_lama, "?"),
                    "shift_baru": SHIFT_MAP.get(kode_shift_baru, "?"),
                }

        return {"ada_konflik": False}

    except Exception as e:
        _log(f"check_konflik error: {e}")
        return {"ada_konflik": False}


# =========================================================
# CRUD PERSONIL
# =========================================================
def add_personil(nama, urutan=None):
    """Tambah personil baru."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"success": False, "message": "Supabase gak konek"}

        _nama = str(nama).upper().strip()
        if len(_nama) < 2:
            return {"success": False, "message": "Nama terlalu pendek"}

        _existing = _sb.table("personil_master").select("*").eq("nama", _nama).execute()
        if _existing.data and len(_existing.data) > 0:
            _row = _existing.data[0]
            if _row.get("aktif"):
                return {"success": False, "message": f"{_nama} udah ada di daftar aktif"}
            else:
                _sb.table("personil_master").update({"aktif": True}).eq("id", _row["id"]).execute()
                return {"success": True, "message": f"✅ {_nama} diaktifkan kembali"}

        if urutan is None:
            _all = _sb.table("personil_master").select("urutan").order("urutan", desc=True).limit(1).execute()
            if _all.data:
                urutan = (_all.data[0].get("urutan") or 0) + 1
            else:
                urutan = 1

        _data = {
            "nama": _nama,
            "aktif": True,
            "urutan": urutan,
            "created_at": _now_jkt().isoformat(),
            "updated_at": _now_jkt().isoformat(),
        }
        _sb.table("personil_master").insert(_data).execute()

        return {"success": True, "message": f"✅ {_nama} ditambahkan"}

    except Exception as e:
        _log(f"add_personil error: {e}")
        return {"success": False, "message": f"Gagal: {str(e)[:150]}"}


def delete_personil(nama, force=False):
    """Hapus personil (soft/hard delete)."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"success": False, "message": "Supabase gak konek"}

        _nama = str(nama).upper().strip()

        _existing = _sb.table("personil_master").select("id").eq("nama", _nama).execute()
        if not _existing.data:
            return {"success": False, "message": f"{_nama} gak ada di daftar"}

        _row_id = _existing.data[0]["id"]

        if force:
            _sb.table("personil_master").delete().eq("id", _row_id).execute()
            _sb.table("master_shift").delete().eq("nama", _nama).execute()
            return {"success": True, "message": f"🗑️ {_nama} + history dihapus permanent"}
        else:
            _sb.table("personil_master").update({
                "aktif": False,
                "updated_at": _now_jkt().isoformat(),
            }).eq("id", _row_id).execute()
            return {"success": True, "message": f"✅ {_nama} dinonaktifkan (history tetap tersimpan)"}

    except Exception as e:
        _log(f"delete_personil error: {e}")
        return {"success": False, "message": f"Gagal: {str(e)[:150]}"}


# =========================================================
# GET SHIFT HARI INI — untuk running text
# =========================================================
def get_shift_hari_ini(tanggal=None):
    """Ambil ringkasan shift hari ini, grouped by kode."""
    _today = tanggal or _now_jkt().date()
    _res = get_master_shift(tgl_start=_today, tgl_end=_today)

    if not _res.get("success"):
        return {"success": False, "data": {}}

    _grouped = {}
    for _row in _res.get("data", []):
        _kode = _row.get("kode_shift", "O")
        _grouped.setdefault(_kode, []).append(_row["nama"])

    return {
        "success": True,
        "tanggal": _today.isoformat(),
        "grouped": _grouped,
        "total": len(_res.get("data", [])),
    }

# =========================================================
# PARSE SHIFT UPDATE — v4 (Groq AI + Fallback)
# =========================================================
def parse_shift_update(text: str, today=None) -> dict:
    """
    Parse natural language jadi struktur shift.
    STRATEGI: Groq AI dulu → fallback rule-based.
    
    Return:
    {
        "tanggal": date,
        "tanggal_list": [date, ...],
        "items": [{"nama", "kode_shift", "shift_nama"}, ...],
        "raw": str,
    }
    """
    _today = today or _now_jkt().date()

    if not text or not str(text).strip():
        return {
            "tanggal": _today,
            "tanggal_list": [_today],
            "items": [],
            "raw": str(text),
        }

    # =========================================================
    # STEP 1: COBA GROQ AI
    # =========================================================
    if GROQ_AVAILABLE:
        _ai_result = _parse_with_groq(str(text), _today)
        if _ai_result and _ai_result.get("success"):
            return _ai_result["data"]

    # =========================================================
    # STEP 2: FALLBACK RULE-BASED
    # =========================================================
    _log("Groq failed, using rule-based fallback")
    return _parse_rule_based(str(text), _today)


# =========================================================
# PARSE DENGAN GROQ AI
# =========================================================
def _parse_with_groq(text, today):
    """Parse pakai Groq AI."""
    try:
        # Build context
        _personil = get_personil_aktif()
        if not _personil:
            return {"success": False, "error": "Tidak ada personil aktif"}

        _personil_names = [p["nama"] for p in _personil]
        _personil_str = ", ".join(_personil_names)

        # Shift context hari ini
        _shift_ctx = _build_shift_context(today)

        # Prompt
        _prompt = f"""Kamu Hana 🌸, asisten HR untuk Toko C383.
Tugasmu: parse pesan user jadi JSON (BUKAN ngobrol).

KONTEKS HARI INI:
- Tanggal: {today.isoformat()} ({today.strftime('%A')})
- Personil aktif: {_personil_str}

{_shift_ctx}

KODE SHIFT VALID:
- P7 = Pagi
- S15 = Siang
- M22 = Malam
- O = Libur
- CUTI = Cuti

PESAN USER:
\"\"\"{text}\"\"\"

ATURAN PARSING:
1. Deteksi mode: "update" (default) atau "delete" (kalau ada kata hapus/delete/buang)
2. Deteksi tanggal (BISA MULTIPLE):
   - "hari ini" / "ini" → hari ini
   - "besok" → besok
   - "lusa" → lusa
   - "besok dan lusa" → 2 tanggal
   - "senin, selasa" → hari-hari itu
   - "DD/MM" atau "DD-MM" → tanggal eksplisit
   - Kalau gak ada tanggal → hari ini
3. Parse SEMUA nama personil yang disebutkan (multi-nama pakai "dan", ",", "&")
4. Assign kode shift yang sesuai:
   - "pagi" → P7
   - "siang" → S15
   - "malam" → M22
   - "libur"/"off" → O
   - "cuti" → CUTI
5. STRIP kata umum dari nama: "hari", "ini", "besok", "lusa", "tanggal", "dan", "atau", "yang", "mau", "ganti", "jadi", "shift", "atur", "set", "ubah"
6. Nama personil di-UPPERCASE
7. Kalau nama gak match personil aktif, TETAP masukkan tapi kasih warning

CONTOH INPUT → OUTPUT:

Input: "Atur Kusdewi dan Adel siang, Atur Ilham dan Reza libur"
Output:
{{
  "mode": "update",
  "tanggal_list": ["{today.isoformat()}"],
  "tanggal_detect": "hari ini",
  "shift_map": {{
    "KUSDEWI": "S15",
    "ADEL": "S15",
    "ILHAM": "O",
    "REZA": "O"
  }},
  "reasoning": "Kusdewi & Adel shift siang, Ilham & Reza libur"
}}

Input: "Pagi: Pandu, Tika. Siang: Reza"
Output:
{{
  "mode": "update",
  "tanggal_list": ["{today.isoformat()}"],
  "tanggal_detect": "hari ini",
  "shift_map": {{
    "PANDU": "P7",
    "TIKA": "P7",
    "REZA": "S15"
  }},
  "reasoning": "Pandu & Tika pagi, Reza siang"
}}

Input: "Besok Zaki cuti"
Output:
{{
  "mode": "update",
  "tanggal_list": ["{(today + timedelta(days=1)).isoformat()}"],
  "tanggal_detect": "besok",
  "shift_map": {{"ZAKI": "CUTI"}},
  "reasoning": "Zaki cuti besok"
}}

Kalau mode=delete, "shift_map" kosong & isi "delete_targets" (list nama).
Output HANYA JSON, gak ada text lain.
"""

        # Call Groq
        _ok, _resp_text, _model, _err = _call_hana_groq(
            _prompt,
            function="parse",
            temperature=0.1,  # low temperature — lebih akurat
        )

        if not _ok:
            return {"success": False, "error": f"Groq error: {_err}"}

        # Extract JSON
        _data = _extract_json(_resp_text)
        if not _data:
            _log(f"AI response bukan JSON: {_resp_text[:200]}")
            return {"success": False, "error": "AI response bukan JSON valid"}

        # Parse tanggal list
        _tgl_list = _parse_tanggal_list_from_response(
            _data.get("tanggal_list"),
            today,
        )

        # Parse shift_map → items
        _shift_map = _data.get("shift_map") or {}
        _items = []

        for _nama, _kode in _shift_map.items():
            _nama_clean = str(_nama).strip().upper()

            # Strip stopwords dari nama
            for _sw in ["HARI", "INI", "BESOK", "LUSA", "TANGGAL", "DAN", "ATAU", "YANG", "SHIFT"]:
                _nama_clean = _nama_clean.replace(_sw, "").strip()

            _kode_clean = str(_kode).strip().upper()
            if _kode_clean not in SHIFT_MAP:
                continue
            if not _nama_clean or _nama_clean in STOPWORDS:
                continue

            _items.append({
                "nama": _nama_clean,
                "kode_shift": _kode_clean,
                "shift_nama": SHIFT_MAP[_kode_clean],
            })

        return {
            "success": True,
            "data": {
                "tanggal": _tgl_list[0],
                "tanggal_list": _tgl_list,
                "tanggal_detect": _data.get("tanggal_detect", "hari ini"),
                "items": _items,
                "raw": text,
                "engine": f"groq ({_model})",
                "ai_reasoning": _data.get("reasoning", ""),
            },
        }

    except Exception as e:
        _log(f"_parse_with_groq error: {e}")
        return {"success": False, "error": str(e)[:150]}


# =========================================================
# PARSE TANGGAL LIST — dari AI response
# =========================================================
def _parse_tanggal_list_from_response(tgl_list_str, fallback):
    """Convert list string ISO tanggal jadi list date."""
    _result = []
    if tgl_list_str:
        for _tgl_str in tgl_list_str:
            try:
                _result.append(datetime.strptime(str(_tgl_str), "%Y-%m-%d").date())
            except Exception:
                pass

    if not _result:
        return [fallback]

    # Dedupe & sort
    _seen = set()
    _unique = []
    for _d in sorted(_result):
        if _d not in _seen:
            _seen.add(_d)
            _unique.append(_d)

    return _unique


# =========================================================
# BUILD SHIFT CONTEXT — buat prompt
# =========================================================
def _build_shift_context(today):
    """Buat context shift hari ini."""
    try:
        _tgl_str = today.isoformat() if hasattr(today, "isoformat") else str(today)[:10]
        _res = get_master_shift(tgl_start=_tgl_str, tgl_end=_tgl_str)

        if not _res.get("success") or not _res.get("data"):
            return f"Belum ada shift untuk {_tgl_str}."

        _grouped = {}
        for _row in _res["data"]:
            _kode = _row.get("kode_shift", "O")
            _grouped.setdefault(_kode, []).append(_row["nama"])

        _lines = [f"SHIFT HARI INI ({_tgl_str}):"]
        for _kode in ["P7", "S15", "M22", "O", "CUTI"]:
            if _kode in _grouped:
                _label = SHIFT_MAP.get(_kode, _kode)
                _lines.append(f"- {_label} ({_kode}): {', '.join(_grouped[_kode])}")
        return "\n".join(_lines)
    except Exception as e:
        return f"Gagal load shift: {e}"


# =========================================================
# FALLBACK — RULE-BASED PARSER
# =========================================================
def _parse_rule_based(text, today):
    """Fallback parser pakai regex."""
    _tgl_list = _parse_tanggal_list(text, today)
    _tgl = _tgl_list[0]

    _items = []
    _text_lower = str(text).lower()
    _text_upper = str(text).upper()

    _personil_list = get_personil_aktif()
    _personil_names = [p["nama"].upper() for p in _personil_list]

    if not _personil_names:
        return {
            "tanggal": _tgl,
            "tanggal_list": _tgl_list,
            "items": [],
            "raw": text,
        }

    # Mapping keyword shift
    _shift_kw_map = [
        ("pagi", "P7"),
        ("siang", "S15"),
        ("malam", "M22"),
        ("malem", "M22"),
        ("mlm", "M22"),
        ("sore", "S15"),
        ("libur", "O"),
        ("off", "O"),
        ("cuti", "CUTI"),
    ]

    # Split by "atur/set/ubah" + koma
    _clauses = re.split(
        r'[,\.]|\batur\b|\bset\b|\bubah\b|\bganti\b|\bpindah\b|\bjadwal\b',
        _text_lower
    )
    _clauses = [c.strip() for c in _clauses if c.strip()]

    _found_any = False

    for _clause in _clauses:
        if len(_clause) < 3:
            continue

        # Cari keyword shift
        _kode_detected = None
        for _kw, _kode in _shift_kw_map:
            if re.search(r'\b' + re.escape(_kw) + r'\b', _clause):
                _kode_detected = _kode
                break

        if not _kode_detected:
            continue

        # Cari SEMUA nama di klausa
        _names_in_clause = []
        for _nama_db in _personil_names:
            if re.search(r'\b' + re.escape(_nama_db.lower()) + r'\b', _clause):
                _names_in_clause.append(_nama_db)

        if not _names_in_clause:
            continue

        # Apply ke semua nama
        for _nama in _names_in_clause:
            if _nama not in [it["nama"] for it in _items]:
                _items.append({
                    "nama": _nama,
                    "kode_shift": _kode_detected,
                    "shift_nama": SHIFT_MAP[_kode_detected],
                })
                _found_any = True

    # Fallback terakhir
    if not _found_any:
        _shift_detected = "O"
        for _kw, _kode in _shift_kw_map:
            if re.search(r'\b' + re.escape(_kw) + r'\b', _text_lower):
                _shift_detected = _kode
                break

        for _nama_db in _personil_names:
            if re.search(r'\b' + re.escape(_nama_db) + r'\b', _text_upper):
                _items.append({
                    "nama": _nama_db,
                    "kode_shift": _shift_detected,
                    "shift_nama": SHIFT_MAP[_shift_detected],
                })

    # Filter duplikat
    _final = []
    _seen = set()
    for _it in _items:
        _n = _it.get("nama", "").upper().strip()
        if not _n or _n in STOPWORDS or _n in _seen:
            continue
        _final.append(_it)
        _seen.add(_n)

    return {
        "tanggal": _tgl,
        "tanggal_list": _tgl_list,
        "items": _final,
        "raw": text,
        "engine": "rule-based-fallback",
    }

# =========================================================
# CHAT HANA — fungsi utama
# =========================================================
def chat_response(user_message, conversation_history=None):
    """
    Hana chat response dengan intent detection.
    
    Intent:
    - confirm_shift: update shift → return preview + data konfirmasi
    - query_shift: tanya jadwal → return data jadwal
    - chat: fallback LLM (chat biasa)
    """
    if not user_message:
        return {"text": "", "intent": "chat", "parsed": None, "engine": None}

    _text_lower = str(user_message).lower().strip()

    # ============================================================
    # INTENT 1 — UPDATE SHIFT
    # ============================================================
    _update_keywords = [
        "atur", "set", "ubah", "ganti", "pindah", "masuk",
        "libur", "cuti", "off",
    ]
    _shift_keywords = ["pagi", "siang", "malam", "malem", "libur", "off", "cuti"]

    _is_update = (
        any(k in _text_lower for k in _update_keywords)
        or any(k in _text_lower for k in _shift_keywords)
    )

    if _is_update:
        try:
            _parsed = parse_shift_update(user_message)

            if _parsed.get("items") and len(_parsed["items"]) > 0:
                _items = _parsed["items"]
                _tgl = _parsed["tanggal"]
                _engine = _parsed.get("engine", "unknown")

                _tgl_str = _tgl.strftime("%d %b %Y") if hasattr(_tgl, "strftime") else str(_tgl)

                # Build text preview (short)
                _count = len(_items)
                _text = f"Oke Bos, aku catat {_count} perubahan shift. Cek detailnya ya! 🌸"

                # Extract kode shift untuk loadMiniDashboard compatibility
                _shift_map = {it["nama"]: it["kode_shift"] for it in _items}

                return {
                    "text": _text,
                    "intent": "confirm_shift",
                    "parsed": {
                        "tanggal": _tgl.isoformat() if hasattr(_tgl, "isoformat") else str(_tgl)[:10],
                        "tanggal_list": [
                            t.isoformat() if hasattr(t, "isoformat") else str(t)[:10]
                            for t in _parsed.get("tanggal_list", [_tgl])
                        ],
                        "items": _items,
                        "shift_map": _shift_map,
                        "raw": user_message,
                    },
                    "engine": _engine,
                    "needs_confirm": True,
                }
        except Exception as _e:
            _log(f"Intent update parse error: {_e}")

    # ============================================================
    # INTENT 2 — QUERY SHIFT
    # ============================================================
    _query_keywords = [
        "jadwal", "shift", "piket", "siapa masuk", "siapa shift",
        "hari ini", "besok", "minggu ini",
    ]
    _is_query = any(k in _text_lower for k in _query_keywords)
    _is_question = any(k in _text_lower for k in ["?", "apa", "siapa", "gimana", "cek", "lihat", "tampil"])

    if _is_query and (_is_question or "jadwal" in _text_lower or "shift" in _text_lower):
        try:
            _tgl = parse_tanggal(user_message)
            _tgl_str = _tgl.isoformat() if hasattr(_tgl, "isoformat") else str(_tgl)[:10]

            _res = get_master_shift(tgl_start=_tgl_str, tgl_end=_tgl_str)

            if _res.get("success") and _res.get("data"):
                _grouped = {"P7": [], "S15": [], "M22": [], "O": [], "CUTI": []}
                for _row in _res["data"]:
                    _kode = _row.get("kode_shift", "O")
                    _grouped.setdefault(_kode, []).append(_row["nama"])

                _lines = [f"🌸 Jadwal shift {_tgl_str}:"]
                if _grouped.get("P7"):
                    _lines.append(f"🟢 Pagi: {', '.join(_grouped['P7'])}")
                if _grouped.get("S15"):
                    _lines.append(f"🟡 Siang: {', '.join(_grouped['S15'])}")
                if _grouped.get("M22"):
                    _lines.append(f"🔴 Malam: {', '.join(_grouped['M22'])}")
                if _grouped.get("O"):
                    _lines.append(f"⚪ Libur: {', '.join(_grouped['O'])}")
                if _grouped.get("CUTI"):
                    _lines.append(f"⚫ Cuti: {', '.join(_grouped['CUTI'])}")

                return {
                    "text": "\n".join(_lines),
                    "intent": "query_shift",
                    "parsed": {"tanggal": _tgl_str, "grouped": _grouped},
                    "engine": "query",
                }
            else:
                return {
                    "text": f"🌸 Hmm, gak ada jadwal shift buat {_tgl_str} Bos. Mau aku atur?",
                    "intent": "query_shift",
                    "parsed": {"tanggal": _tgl_str},
                    "engine": "query",
                }
        except Exception as _e:
            _log(f"Intent query error: {_e}")

    # ============================================================
    # FALLBACK — CHAT BIASA (Groq)
    # ============================================================
    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _history_str += f"{_msg.get('role', 'user')}: {_msg.get('content', '')}\n"

    _personil_ctx = _build_personil_context()

    _prompt = f"""Kamu Hana 🌸 — Master Shift Specialist Toko C383.

=== TUGAS ===
1. Cek jadwal shift
2. Update / hapus shift
3. Saran pengganti
4. Cek konflik

=== PERSONA ===
Ceria, ramah, profesional. Panggil user "Bos".
Pakai emoji 🌸 secukupnya. Max 6 baris.

{_personil_ctx}

Riwayat:
{_history_str}

Bos: "{user_message}"

Balas sebagai Hana.
"""

    _ok, _text, _model, _err = _call_hana_groq(_prompt, function="chat", temperature=0.7)

    if not _ok:
        return {
            "text": f"Waduh error Bos. ({str(_err)[:50]})",
            "intent": "chat",
            "parsed": None,
            "engine": None,
        }

    return {
        "text": _text.strip(),
        "intent": "chat",
        "parsed": None,
        "engine": _model,
    }


# =========================================================
# SUGGEST PENGGANTI
# =========================================================
def suggest_pengganti(nama_libur, tanggal=None):
    """Saran pengganti terstruktur."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return []

        _tgl = tanggal or _now_jkt().date()
        _tgl_str = _tgl.isoformat() if isinstance(_tgl, date) else str(_tgl)[:10]

        _personil = get_personil_aktif()

        _shift_res = get_master_shift(tgl_start=_tgl_str, tgl_end=_tgl_str)
        _sudah_shift = {}
        if _shift_res.get("success"):
            for _row in _shift_res.get("data", []):
                _sudah_shift[_row["nama"]] = _row.get("kode_shift", "O")

        _kandidat = []
        for _p in _personil:
            _nama = _p["nama"].upper()
            if _nama == str(nama_libur).upper():
                continue
            _kode = _sudah_shift.get(_nama)
            if _kode is None or _kode == "O":
                _kandidat.append({
                    "nama": _nama,
                    "status": "Bebas" if _kode is None else "Sedang OFF",
                    "kode_shift": _kode,
                })

        return _kandidat

    except Exception as e:
        _log(f"suggest_pengganti error: {e}")
        return []


def ai_suggest_pengganti_text(nama_libur, tanggal=None):
    """Saran pengganti versi AI."""
    _kandidat = suggest_pengganti(nama_libur, tanggal)
    _tgl = tanggal or _now_jkt().date()

    if not _kandidat:
        return f"🌸 Hmm, gak ada kandidat pengganti buat {nama_libur} tanggal {_tgl}. Semua udah ada shift."

    _kandidat_str = "\n".join([
        f"- {k['nama']} ({k['status']})" for k in _kandidat[:5]
    ])

    return f"""🌸 Oke Bos, buat gantiin {nama_libur} tanggal {_tgl}, aku saranin:

{_kandidat_str}

Mau aku atur salah satu buat gantiin?"""


# =========================================================
# CHECK CONFLICT
# =========================================================
def check_conflict(tanggal, shift_map):
    """Cek konflik shift, return list of issues."""
    _issues = []
    try:
        _tgl_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]

        _nama_count = {}
        for _nama in shift_map.keys():
            _nama_upper = str(_nama).upper()
            _nama_count[_nama_upper] = _nama_count.get(_nama_upper, 0) + 1

        for _nama, _count in _nama_count.items():
            if _count > 1:
                _issues.append({
                    "type": "duplikat",
                    "message": f"{_nama} muncul {_count}x",
                })

        _personil = get_personil_aktif()
        _sudah_ada = [str(n).upper() for n in shift_map.keys()]
        for _p in _personil:
            _nama = _p["nama"].upper()
            if _nama not in _sudah_ada:
                _issues.append({
                    "type": "belum_ada_shift",
                    "message": f"{_nama} belum ada shift",
                })

        return _issues

    except Exception as e:
        _log(f"check_conflict error: {e}")
        return _issues


def ai_check_conflict_text(tanggal, shift_map):
    """Cek konflik versi AI."""
    _issues = check_conflict(tanggal, shift_map)
    _tgl = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]

    if not _issues:
        return f"🌸 Cek selesai Bos! Gak ada konflik di tanggal {_tgl}. Aman ✅"

    _issues_str = "\n".join([f"- {i['message']}" for i in _issues])
    return f"""🌸 Hmm, ada {len(_issues)} hal yang perlu dicek di tanggal {_tgl}:

{_issues_str}

Mau aku bantu fix?"""


# =========================================================
# HELPER — Call Groq (TETAP)
# =========================================================
def _call_hana_groq(prompt, hard_timeout=90, function="chat", temperature=0.7):
    """Call Groq API untuk Hana."""
    if not GROQ_AVAILABLE:
        return False, "", None, "Groq not available"

    if check_auto_pause("ai-1"):
        return False, "", None, "Auto-pause"

    try:
        _key = get_ai_api_key("ai-1")
        if not _key:
            return False, "", None, "API key Hana gak ada"

        _client = Groq(api_key=_key)
        _cfg = get_ai_config("ai-1")
        _models = _cfg.get("model_priority", ["openai/gpt-oss-20b"])

        _last_err = None
        for _model_name in _models:
            try:
                _log(f"Trying {_model_name}...")
                _resp = _client.chat.completions.create(
                    model=_model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=2048,
                    top_p=0.95,
                    extra_body={"reasoning_effort": "low"},
                )

                if not _resp or not _resp.choices:
                    _last_err = "No response"
                    continue

                _choice = _resp.choices[0]
                _msg = _choice.message if _choice else None
                if not _msg:
                    _last_err = "No message"
                    continue

                _content = getattr(_msg, "content", None)
                if not _content:
                    _reasoning = getattr(_msg, "reasoning_content", None)
                    if _reasoning:
                        _content = _reasoning

                if not _content:
                    _last_err = "Content kosong"
                    continue

                _text = str(_content).strip()
                _log(f"OK: {_model_name} ({len(_text)} chars)")

                try:
                    _u = getattr(_resp, "usage", None)
                    record_usage_v2(
                        ai_name="ai-1",
                        function=function,
                        model=_model_name,
                        prompt_tokens=getattr(_u, "prompt_tokens", 0) if _u else 0,
                        output_tokens=getattr(_u, "completion_tokens", 0) if _u else 0,
                        success=True,
                    )
                except Exception:
                    pass

                return True, _text, _model_name, None

            except Exception as _e:
                _last_err = str(_e)[:200]
                _log(f"{_model_name} error: {_last_err}")
                continue

        return False, "", None, _last_err or "All models failed"

    except Exception as e:
        _log(f"_call_hana_groq error: {e}")
        return False, "", None, str(e)[:200]

# =========================================================
# EXPORT
# =========================================================
__all__ = [
    # Konstanta
    "SHIFT_MAP",
    "SHIFT_MAP_REVERSE",
    "SHIFT_EMOJI",
    "STOPWORDS",

    # Parser
    "parse_tanggal",
    "parse_shift_update",

    # Personil
    "get_personil_aktif",
    "add_personil",
    "delete_personil",

    # Shift CRUD
    "save_shift",
    "save_batch",
    "get_master_shift",
    "check_konflik",
    "get_shift_hari_ini",

    # Chat
    "chat_response",

    # Suggest & Conflict
    "suggest_pengganti",
    "ai_suggest_pengganti_text",
    "check_conflict",
    "ai_check_conflict_text",
]


# =========================================================
# END OF FILE
# =========================================================
_log("✅ AI Shift Manager v4 loaded")