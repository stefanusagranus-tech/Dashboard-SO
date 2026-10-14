"""
AI Shift Manager — Hana (AI-1) v3
====================================
Logic untuk master shift: parse, save, read, delete.
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
# STOPWORDS — kata yang BUKAN nama personil
# =========================================================
STOPWORDS = {
    # Shift
    "PAGI", "SIANG", "MALAM", "MALEM", "MLM", "SORE", "SOREMALEM",
    # Status
    "LIBUR", "OFF", "CUTI", "MASUK", "IZIN", "SAKIT",
    # Kata kerja
    "ATUR", "SET", "UBAH", "GANTI", "PINDAH", "PIND", "JADWAL", "SHIFT",
    # Waktu
    "BESOK", "ESOK", "LUSA", "KEMARIN", "HARI", "INI", "ITU", "SKRG",
    "SEKARANG", "TODAY", "TOMORROW", "NEXT", "DEPAN", "LALU", "NANTI",
    # Keterangan
    "KE", "DAN", "YANG", "DI", "PADA", "UNTUK", "DENGAN", "BUAT", "TO",
    # Hari
    "MINGGU", "SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "JUMAT",
    "SABTU", "AHAD", "JUMAAT",
    # Bulan
    "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
    "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER",
    "JAN", "FEB", "MAR", "APR", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES",
    # Nama bot
    "BOS", "HANA", "YUI", "REI", "KURUMI",
    # Keterangan tambahan
    "YA", "OKE", "OK", "BAIK", "SIAP", "MOHON", "TOLONG",
    "KALAU", "JIKA", "BILA", "APAKAH", "APA", "SIAPA", "BAGAIMANA", "GIMANA",
    "SEMUA", "SEMUANYA", "ORANG", "KARYAWAN", "TIM", "ANAK",
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
                _days_ahead = 7
            if "depan" in _text or "next" in _text:
                _days_ahead += 7
            return _today + timedelta(days=_days_ahead)

    # === TANGGAL ANGKA ===
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
        _bulan_str = _match.group(2)
        _month = _bulan_map.get(_bulan_str)
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
# PARSE SHIFT UPDATE — v3 (handle format kompleks)
# =========================================================
def parse_shift_update(text: str, today=None) -> dict:
    """
    Parse natural language jadi struktur shift.
    Versi v3 — handle format kompleks.
    
    Contoh input yang SUPPORTED:
    - "Atur Reza ke siang besok"
    - "Pagi: Pandu, Tika. Siang: Reza. Malam: Zaki"
    - "Atur Kusdewi shift siang, Atur zaki shift Malam dan reza libur"
    - "Besok Pandu dan Rizki libur"
    - "Hari ini Zaki cuti"
    """
    _today = today or _now_jkt().date()
    _tgl = parse_tanggal(text, _today)

    _items = []
    _text_lower = str(text).lower().strip()
    _text_upper = str(text).upper()

    # === AMBIL DAFTAR PERSONIL ===
    _personil_list = get_personil_aktif()
    _personil_names = [p["nama"].upper() for p in _personil_list]

    if not _personil_names:
        _log("Warning: personil list kosong")
        return {"tanggal": _tgl, "tanggal_list": [_tgl], "items": [], "raw": text}

    # === SHIFT KEYWORD → KODE ===
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

    # =========================================================
    # STRATEGI v3: SPLIT PER SEGMEN, LALU PARSE TIAP SEGMEN
    # =========================================================
    # Split text by separator kuat: "atur", "set", "ubah", "ganti", "pindah", koma, titik
    _separator_pattern = r'[,\.]|\batur\b|\bset\b|\bubah\b|\bganti\b|\bpindah\b|\bjadwal\b'
    _segments = re.split(_separator_pattern, _text_lower)
    _segments = [s.strip() for s in _segments if s.strip()]

    _found_any = False

    for _seg in _segments:
        if len(_seg) < 3:
            continue

        # Cari SEMUA keyword shift di segmen ini (bisa lebih dari 1)
        _shift_positions = []
        for _kw, _kode in _shift_kw_map:
            # Whole word match
            for _m in re.finditer(r'\b' + re.escape(_kw) + r'\b', _seg):
                _shift_positions.append({
                    "start": _m.start(),
                    "end": _m.end(),
                    "kode": _kode,
                    "kw": _kw,
                })

        if not _shift_positions:
            continue

        # Sort by position
        _shift_positions.sort(key=lambda x: x["start"])

        # === STRATEGI A: Kalau ada >1 shift keyword di segmen, split lagi ===
        if len(_shift_positions) > 1:
            # Split segmen berdasarkan posisi shift keyword
            for _idx, _pos in enumerate(_shift_positions):
                _content_start = _pos["end"]
                if _idx + 1 < len(_shift_positions):
                    _content_end = _shift_positions[_idx + 1]["start"]
                else:
                    _content_end = len(_seg)

                _content = _seg[_content_start:_content_end]
                _content = re.sub(r'^[\s:\.\,\-]+', '', _content)
                _content = re.sub(r'[\s:\.\,\-]+$', '', _content)

                # Cari nama personil di content
                for _nama_db in _personil_names:
                    if re.search(r'\b' + re.escape(_nama_db.lower()) + r'\b', _content):
                        if _nama_db not in [it["nama"] for it in _items]:
                            _items.append({
                                "nama": _nama_db,
                                "kode_shift": _pos["kode"],
                                "shift_nama": SHIFT_MAP[_pos["kode"]],
                            })
                            _found_any = True

        # === STRATEGI B: Kalau cuma 1 shift keyword ===
        else:
            _pos = _shift_positions[0]

            # Split segmen jadi: sebelum & sesudah keyword
            _before = _seg[:_pos["start"]]
            _after = _seg[_pos["end"]:]

            # Cari nama di SEBELUM keyword (misal: "atur reza ke siang")
            _nama_before = None
            for _nama_db in _personil_names:
                if re.search(r'\b' + re.escape(_nama_db.lower()) + r'\b', _before):
                    _nama_before = _nama_db
                    break

            # Kalau ada nama sebelum → masukkan
            if _nama_before and _nama_before not in [it["nama"] for it in _items]:
                _items.append({
                    "nama": _nama_before,
                    "kode_shift": _pos["kode"],
                    "shift_nama": SHIFT_MAP[_pos["kode"]],
                })
                _found_any = True

            # Cari nama di SESUDAH keyword (misal: "siang: pandu, tika")
            _after_clean = re.sub(r'^[\s:\.\,\-]+', '', _after)
            _after_clean = re.sub(r'[\s:\.\,\-]+$', '', _after_clean)

            # Split by "dan" atau "," atau spasi
            _after_parts = re.split(r'\bdan\b|[,\s]+', _after_clean)

            for _part in _after_parts:
                _part = _part.strip().lower()
                if not _part or len(_part) < 2:
                    continue

                for _nama_db in _personil_names:
                    if _part == _nama_db.lower() and _nama_db not in [it["nama"] for it in _items]:
                        _items.append({
                            "nama": _nama_db,
                            "kode_shift": _pos["kode"],
                            "shift_nama": SHIFT_MAP[_pos["kode"]],
                        })
                        _found_any = True

    # =========================================================
    # FALLBACK: KALAU STRATEGI v3 GAGAL
    # =========================================================
    if not _found_any:
        _log("Strategy v3 failed, using fallback")

        # Deteksi shift tunggal (cari yang muncul pertama)
        _shift_detected = "O"  # default libur
        for _kw, _kode in _shift_kw_map:
            if re.search(r'\b' + re.escape(_kw) + r'\b', _text_lower):
                _shift_detected = _kode
                break

        # Cari SEMUA nama personil di text
        for _nama_db in _personil_names:
            if re.search(r'\b' + re.escape(_nama_db) + r'\b', _text_upper):
                _items.append({
                    "nama": _nama_db,
                    "kode_shift": _shift_detected,
                    "shift_nama": SHIFT_MAP[_shift_detected],
                })

    # =========================================================
    # FILTER AKHIR — buang duplikat, stopwords, dll
    # =========================================================
    _final_items = []
    _seen_names = set()

    for _it in _items:
        _nama = _it.get("nama", "").upper().strip()

        # Skip kalau kosong, kepanjangan, stopword, atau duplikat
        if not _nama or len(_nama) < 2 or len(_nama) > 20:
            continue
        if _nama in STOPWORDS:
            continue
        if _nama in _seen_names:
            continue

        _final_items.append({
            "nama": _nama,
            "kode_shift": _it["kode_shift"],
            "shift_nama": _it["shift_nama"],
        })
        _seen_names.add(_nama)

    return {
        "tanggal": _tgl,
        "tanggal_list": [_tgl],
        "items": _final_items,
        "raw": text,
    }