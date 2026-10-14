"""
AI Shift Manager — Hana (AI-1) v2
====================================
Logic untuk master shift: parse, save, read, delete.
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
# HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _log(msg):
    print(f"[Hana] {msg}")


# Mapping kode shift
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
# PARSE TANGGAL NATURAL
# =========================================================
def parse_tanggal(text: str, today=None) -> date:
    """
    Parse teks tanggal natural jadi `date`.
    
    Support:
    - "hari ini", "today"
    - "besok", "esok", "tomorrow"
    - "lusa"
    - "kemarin"
    - "senin", "selasa", ..., "minggu" (hari terdekat ke depan)
    - "senin depan"
    - "20 okt", "20 oktober", "20-10", "20/10", "20/10/2026"
    - "oktober", "okt" (bulan ini)
    - Default: hari ini kalau gak ada tanggal
    """
    _today = today or _now_jkt().date()
    _text = str(text).lower().strip()

    # === HARI INI ===
    if any(k in _text for k in ["hari ini", "today", "skrg", "sekarang"]):
        return _today

    # === BESOK ===
    if any(k in _text for k in ["besok", "esok", "tomorrow", "bsk"]):
        return _today + timedelta(days=1)

    # === LUSA ===
    if "lusa" in _text:
        return _today + timedelta(days=2)

    # === KEMARIN ===
    if "kemarin" in _text:
        return _today - timedelta(days=1)

    # === NAMA HARI ===
    _hari_map = {
        "senin": 0, "selasa": 1, "rabu": 2, "kamis": 3,
        "jumat": 4, "jum'at": 4, "sabtu": 5, "minggu": 6, "ahad": 6,
    }
    for _nama, _idx in _hari_map.items():
        if _nama in _text:
            _days_ahead = (_idx - _today.weekday()) % 7
            if _days_ahead == 0:
                _days_ahead = 7  # kalau hari ini sama, ambil minggu depan
            if "depan" in _text or "next" in _text:
                _days_ahead += 7
            return _today + timedelta(days=_days_ahead)

    # === TANGGAL ANGKA ===
    # "20 okt", "20 oktober"
    _bulan_map = {
        "jan": 1, "januari": 1,
        "feb": 2, "februari": 2,
        "mar": 3, "maret": 3,
        "apr": 4, "april": 4,
        "mei": 5, "may": 5,
        "jun": 6, "juni": 6,
        "jul": 7, "juli": 7,
        "agu": 8, "agustus": 8, "aug": 8,
        "sep": 9, "september": 9,
        "okt": 10, "oktober": 10, "oct": 10,
        "nov": 11, "november": 11,
        "des": 12, "desember": 12, "dec": 12,
    }

    _match = re.search(r'(\d{1,2})\s+([a-z]+)', _text)
    if _match:
        _day = int(_match.group(1))
        _bulan_str = _match.group(2)
        _month = _bulan_map.get(_bulan_str)
        if _month:
            _year = _today.year
            # Kalau bulan udah lewat, tahun depan
            if _month < _today.month:
                _year += 1
            try:
                return date(_year, _month, _day)
            except ValueError:
                pass

    # "20-10", "20/10", "20-10-2026", "20/10/2026"
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

    # === DEFAULT: HARI INI ===
    return _today


# =========================================================
# PARSE NAMA & SHIFT DARI TEKS
# =========================================================
def parse_shift_update(text: str, today=None) -> dict:
    """
    Parse natural language jadi struktur shift.
    
    Contoh input:
    - "Atur Reza ke siang besok"
    - "Besok Pandu dan Rizki libur"
    - "Pagi : Kusdewi, Tika, Aris"
    - "Hari ini Zaki cuti"
    
    Returns:
    {
        "tanggal": date,
        "tanggal_list": [date, ...],
        "items": [
            {"nama": "REZA", "kode_shift": "S15", "shift_nama": "Siang"},
            ...
        ],
        "raw": str,
    }
    """
    _today = today or _now_jkt().date()
    _tgl = parse_tanggal(text, _today)

    _items = []
    _text_lower = str(text).lower()

    # === DETEKSI MULTI-SHIFT (pagi/siang/malam sekaligus) ===
    _multi_patterns = [
        (r'pagi\s*:?\s*([^\n]+?)(?=\s*(?:siang|malam|$))', "P7"),
        (r'siang\s*:?\s*([^\n]+?)(?=\s*(?:pagi|malam|$))', "S15"),
        (r'malam\s*:?\s*([^\n]+?)(?=\s*(?:pagi|siang|$))', "M22"),
    ]

    _found_multi = False
    for _pattern, _kode in _multi_patterns:
        _match = re.search(_pattern, _text_lower)
        if _match:
            _names_str = _match.group(1)
            _names = re.split(r'[,\s]+dan\s+|,\s*|\s+dan\s+', _names_str)
            for _nama in _names:
                _nama = _nama.strip().upper()
                _nama = re.sub(r'[^A-Z\s]', '', _nama).strip()
                if _nama and len(_nama) > 1:
                    _items.append({
                        "nama": _nama,
                        "kode_shift": _kode,
                        "shift_nama": SHIFT_MAP[_kode],
                    })
            _found_multi = True

    # === KALAU BUKAN MULTI, DETEKSI SATU-SATU ===
    if not _found_multi:
        # Cari nama personil dari personil_master
        _personil_list = get_personil_aktif()
        _personil_names = [p["nama"].upper() for p in _personil_list]

        # Deteksi shift
        _shift_detected = None
        for _key, _kode in SHIFT_MAP_REVERSE.items():
            if _key in _text_lower:
                _shift_detected = _kode
                break

        if not _shift_detected:
            _shift_detected = "O"  # default: libur

        # Cari nama yang ada di teks
        for _nama in _personil_names:
            if _nama in _text_lower.upper():
                _items.append({
                    "nama": _nama,
                    "kode_shift": _shift_detected,
                    "shift_nama": SHIFT_MAP[_shift_detected],
                })

        # Kalau gak ada nama di DB, tapi ada nama "umum" di teks
        if not _items:
            _match = re.search(r'(?:atur|set|ubah|ganti)\s+([a-z\s,]+?)\s+(?:ke|jadi|masuk|libur|cuti|off)', _text_lower)
            if _match:
                _names_str = _match.group(1)
                _names = re.split(r'[,\s]+dan\s+|,\s*|\s+dan\s+', _names_str)
                for _nama in _names:
                    _nama = _nama.strip().upper()
                    _nama = re.sub(r'[^A-Z\s]', '', _nama).strip()
                    if _nama and len(_nama) > 1:
                        _items.append({
                            "nama": _nama,
                            "kode_shift": _shift_detected,
                            "shift_nama": SHIFT_MAP[_shift_detected],
                        })

    return {
        "tanggal": _tgl,
        "tanggal_list": [_tgl],
        "items": _items,
        "raw": text,
    }


# =========================================================
# GET PERSONIL AKTIF
# =========================================================
def get_personil_aktif() -> list:
    """Ambil semua personil aktif dari Supabase."""
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
# SAVE SHIFT — dengan deteksi konflik
# =========================================================
def save_shift(tanggal, nama, kode_shift, action="update", force=False):
    """
    Simpan/update/hapus shift.
    
    Args:
        tanggal: date atau str YYYY-MM-DD
        nama: str
        kode_shift: "P7" | "S15" | "M22" | "O" | "CUTI"
        action: "update" (insert/update) | "delete"
        force: True kalau mau hapus history (force delete personil)
    
    Returns:
        {"success": bool, "message": str, "data": dict}
    """
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"success": False, "message": "Supabase gak konek"}

        # Normalize tanggal
        if isinstance(tanggal, date):
            _tgl_str = tanggal.isoformat()
        else:
            _tgl_str = str(tanggal)[:10]

        _nama = str(nama).upper().strip()

        # === ACTION: DELETE ===
        if action == "delete":
            _res = _sb.table("master_shift").delete().eq("tanggal", _tgl_str).eq("nama", _nama).execute()
            return {
                "success": True,
                "message": f"✅ Shift {_nama} tanggal {_tgl_str} dihapus",
                "data": {"nama": _nama, "tanggal": _tgl_str, "action": "delete"},
            }

        # === ACTION: UPDATE/INSERT ===
        _kode = str(kode_shift).upper().strip()
        if _kode not in SHIFT_MAP:
            return {"success": False, "message": f"Kode shift '{_kode}' tidak valid"}

        # Cek apakah udah ada
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
            "catatan": f" | Update via Hana",
            "updated_at": _now_jkt().isoformat(),
        }

        if _existing.data and len(_existing.data) > 0:
            # UPDATE
            _row_id = _existing.data[0]["id"]
            _old_kode = _existing.data[0]["kode_shift"]

            # Kalau kode sama, gak perlu update
            if _old_kode == _kode:
                return {
                    "success": True,
                    "message": f"ℹ️ Shift {_nama} tanggal {_tgl_str} sudah {SHIFT_MAP[_kode]}",
                    "data": {"nama": _nama, "tanggal": _tgl_str, "kode_shift": _kode, "status": "no_change"},
                }

            _res = _sb.table("master_shift").update(_row_data).eq("id", _row_id).execute()
            _msg = f"✅ Shift {_nama} diupdate: {SHIFT_MAP.get(_old_kode, _old_kode)} → {SHIFT_MAP[_kode]}"

        else:
            # INSERT
            _row_data["created_at"] = _now_jkt().isoformat()
            _res = _sb.table("master_shift").insert(_row_data).execute()
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
# SAVE BATCH — simpan banyak shift sekaligus
# =========================================================
def save_batch(items, tanggal):
    """
    Simpan banyak shift sekaligus.
    
    Args:
        items: [{"nama": "REZA", "kode_shift": "S15"}, ...]
        tanggal: date atau str
    
    Returns:
        {"success": bool, "saved": int, "message": str}
    """
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
    """
    Ambil daftar shift dari Supabase.
    
    Args:
        tgl_start: date / str — default: hari ini
        tgl_end: date / str — default: hari ini
        nama_filter: str — filter 1 personil
        limit: int
    
    Returns:
        {"success": bool, "data": [...]}
    """
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

        # Enrich dengan shift_nama + emoji
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
    """
    Cek konflik: personil udah punya shift lain di tanggal sama.
    
    Returns:
        {"ada_konflik": bool, "kode_lama": str, "shift_lama": str, "message": str}
    """
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
                    "message": f"⚠️ {_nama} udah shift {SHIFT_MAP.get(_kode_lama, '?')}, ganti ke {SHIFT_MAP.get(kode_shift_baru, '?')}?",
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

        # Cek udah ada
        _existing = _sb.table("personil_master").select("*").eq("nama", _nama).execute()
        if _existing.data and len(_existing.data) > 0:
            _row = _existing.data[0]
            if _row.get("aktif"):
                return {"success": False, "message": f"{_nama} udah ada di daftar aktif"}
            else:
                # Reactivate
                _sb.table("personil_master").update({"aktif": True}).eq("id", _row["id"]).execute()
                return {"success": True, "message": f"✅ {_nama} diaktifkan kembali"}

        # Urutan auto
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
        _res = _sb.table("personil_master").insert(_data).execute()

        return {"success": True, "message": f"✅ {_nama} ditambahkan"}

    except Exception as e:
        _log(f"add_personil error: {e}")
        return {"success": False, "message": f"Gagal: {str(e)[:150]}"}


def delete_personil(nama, force=False):
    """
    Hapus personil.
    
    Args:
        nama: str
        force: 
            - False → soft delete (aktif=false), history tetap ada
            - True  → hard delete (hapus dari master_shift juga)
    """
    try:
        _sb = get_supabase()
        if _sb is None:
            return {"success": False, "message": "Supabase gak konek"}

        _nama = str(nama).upper().strip()

        # Cari personil
        _existing = _sb.table("personil_master").select("id").eq("nama", _nama).execute()
        if not _existing.data:
            return {"success": False, "message": f"{_nama} gak ada di daftar"}

        _row_id = _existing.data[0]["id"]

        if force:
            # HARD DELETE
            _sb.table("personil_master").delete().eq("id", _row_id).execute()
            _sb.table("master_shift").delete().eq("nama", _nama).execute()
            return {"success": True, "message": f"🗑️ {_nama} + history dihapus permanent"}
        else:
            # SOFT DELETE
            _sb.table("personil_master").update({
                "aktif": False,
                "updated_at": _now_jkt().isoformat(),
            }).eq("id", _row_id).execute()
            return {"success": True, "message": f"✅ {_nama} dinonaktifkan (history tetap tersimpan)"}

    except Exception as e:
        _log(f"delete_personil error: {e}")
        return {"success": False, "message": f"Gagal: {str(e)[:150]}"}


# =========================================================
# AMBIL SHIFT HARI INI — untuk running text
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
# CHAT HANA — fungsi lama yang HARUS di-restore
# =========================================================
def chat_response(user_message, conversation_history=None):
    """
    Hana chat response dengan intent detection.
    Fokus: master shift.
    """
    if not user_message:
        return {"text": "", "intent": "chat", "parsed": None, "engine": None}

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _history_str += f"{_msg.get('role', 'user')}: {_msg.get('content', '')}\n"

    _prompt = f"""Kamu Hana — Master Shift Specialist Toko C383.

=== TUGAS KAMU ===
1. Cek jadwal shift (hari ini, besok, minggu ini)
2. Update / pindah / hapus shift
3. Saran pengganti kalau ada yang libur
4. Cek konflik jadwal

=== PERSONA ===
Personal yang profesional tapi santai. Panggil user "Bos".
Pakai emoji 🌸 secukupnya. Bales singkat, max 6 baris.

Riwayat:
{_history_str}

Bos: "{user_message}"

Balas sebagai Hana.
"""

    # Pakai Groq
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


def suggest_pengganti(nama_libur, tanggal=None):
    """Saran pengganti terstruktur (bukan AI)."""
    try:
        _sb = get_supabase()
        if _sb is None:
            return []

        _tgl = tanggal or _now_jkt().date()
        _tgl_str = _tgl.isoformat() if isinstance(_tgl, date) else str(_tgl)[:10]

        # Ambil semua personil aktif
        _personil = get_personil_aktif()

        # Ambil shift tanggal itu
        _shift_res = get_master_shift(tgl_start=_tgl_str, tgl_end=_tgl_str)
        _sudah_shift = {}
        if _shift_res.get("success"):
            for _row in _shift_res.get("data", []):
                _sudah_shift[_row["nama"]] = _row.get("kode_shift", "O")

        # Kandidat = personil yang OFF / belum shift / belum di-set
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
    """Saran pengganti versi AI (text natural)."""
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


def check_conflict(tanggal, shift_map):
    """
    Cek konflik shift (versi lama, struktur return list).
    
    Args:
        tanggal: date
        shift_map: {"NAMA": "kode", ...}
    
    Returns:
        list of dict: [{"type": "...", "message": "..."}]
    """
    _issues = []
    try:
        _tgl_str = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]

        # Cek duplikat nama
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

        # Cek semua personil punya shift
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
    """Cek konflik versi AI (text natural)."""
    _issues = check_conflict(tanggal, shift_map)
    _tgl = tanggal.isoformat() if isinstance(tanggal, date) else str(tanggal)[:10]

    if not _issues:
        return f"🌸 Cek selesai Bos! Gak ada konflik di tanggal {_tgl}. Aman ✅"

    _issues_str = "\n".join([f"- {i['message']}" for i in _issues])
    return f"""🌸 Hmm, ada {len(_issues)} hal yang perlu dicek di tanggal {_tgl}:

{_issues_str}

Mau aku bantu fix?"""


# =========================================================
# HELPER — Call Groq untuk Hana
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

                # Record usage
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