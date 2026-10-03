"""
Master Shift Handler
====================
Handle master shift: chat parsing, matrix, CRUD, Excel export.

Kode shift:
- P7  = Pagi jam 07:00
- S15 = Siang jam 15:00
- M22 = Malam jam 22:00
- O   = Off (Libur)
- C   = Cuti
- AO  = Additional Off (Pendingan libur)
"""

import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from modules.supabase_client import get_supabase


# =========================================================
# KONSTANTA KODE SHIFT
# =========================================================
KODE_SHIFT = {
    "P7":  {"label": "Pagi (07:00)",   "warna": "#7FB99B", "icon": "🌅"},
    "S15": {"label": "Siang (15:00)",  "warna": "#38bdf8", "icon": "☀️"},
    "M22": {"label": "Malam (22:00)",  "warna": "#a855f7", "icon": "🌙"},
    "O":   {"label": "Off (Libur)",    "warna": "#E88B8B", "icon": "❌"},
    "C":   {"label": "Cuti",           "warna": "#fbbf24", "icon": "🏖️"},
    "AO":  {"label": "Additional Off", "warna": "#94a3b8", "icon": "⏸️"},
}

KEYWORD_TO_KODE = {
    "pagi": "P7",
    "siang": "S15",
    "malam": "M22",
    "libur": "O",
    "off": "O",
    "cuti": "C",
    "ao": "AO",
    "additional off": "AO",
    "additional": "AO",
    "pendingan": "AO",
    "pending": "AO",
}


# =========================================================
# 📥 LOAD: PERSONIL MASTER
# =========================================================
def load_personil_master(only_active=True):
    """Load daftar personil dari Supabase."""
    try:
        sb = get_supabase()
        if sb is None:
            return pd.DataFrame(columns=["nama", "urutan", "aktif"])

        _q = sb.table("personil_master").select("*")
        if only_active:
            _q = _q.eq("aktif", True)
        _q = _q.order("urutan")

        _res = _q.execute()

        if not _res.data:
            return pd.DataFrame(columns=["nama", "urutan", "aktif"])

        return pd.DataFrame(_res.data)
    except Exception as e:
        print(f"[LOAD_PERSONIL ERROR] {e}")
        return pd.DataFrame(columns=["nama", "urutan", "aktif"])


def add_personil(nama, urutan=None):
    """Tambah personil baru."""
    try:
        sb = get_supabase()
        _nama = str(nama).strip().upper()
        if not _nama:
            return False, "❌ Nama kosong"

        # Auto urutan kalau gak dikasih
        if urutan is None:
            _all = load_personil_master(only_active=False)
            _urutan = int(_all["urutan"].max()) + 1 if not _all.empty else 1
        else:
            _urutan = int(urutan)

        _res = sb.table("personil_master").insert({
            "nama": _nama,
            "urutan": _urutan,
            "aktif": True,
        }).execute()

        if _res.data:
            return True, f"✅ {_nama} ditambahkan"
        return False, "❌ Gagal insert"
    except Exception as e:
        return False, f"❌ {str(e)[:150]}"


def update_personil_status(nama, aktif):
    """Aktifkan/nonaktifkan personil (soft delete)."""
    try:
        sb = get_supabase()
        _res = sb.table("personil_master") \
            .update({"aktif": bool(aktif), "updated_at": datetime.now(ZoneInfo("Asia/Jakarta")).isoformat()}) \
            .eq("nama", str(nama).strip().upper()) \
            .execute()

        if _res.data:
            _status = "diaktifkan" if aktif else "dinonaktifkan"
            return True, f"✅ {nama} {_status}"
        return False, "❌ Gagal update"
    except Exception as e:
        return False, f"❌ {str(e)[:150]}"


# =========================================================
# 🧠 PARSE: CHAT UPDATE
# =========================================================
def parse_chat_update(chat_text, tanggal_hari_ini=None):
    """
    Parse chat natural language jadi shift_map.

    Format yang didukung:
    1. Format utama (multi-shift):
       "Besok Tika libur, ganti jadi:
       - Pagi: Reza, Pandu
       - Siang: Zaki
       - Malam: Kusdewi
       - Libur: Tika, Adel"

    2. Format simple (1 shift):
       "Tika libur besok"

    3. Format tanggal eksplisit:
       "01/10: Tika libur"

    Returns:
        dict {
            "tanggal": date,
            "shift_map": {nama: kode_shift},
            "raw_text": str,
            "warning": str atau None,
        }
    """
    if tanggal_hari_ini is None:
        tanggal_hari_ini = datetime.now(ZoneInfo("Asia/Jakarta")).date()

    _text = str(chat_text).strip()
    _text_lower = _text.lower()

    # ============================================
    # 1. DETEKSI TANGGAL
    # ============================================
    _tanggal = tanggal_hari_ini
    _tanggal_detect = "hari ini"

    if "besok" in _text_lower or "bsk" in _text_lower:
        _tanggal = tanggal_hari_ini + timedelta(days=1)
        _tanggal_detect = "besok"

    # Cek format DD/MM atau DD-MM
    _match_tgl = re.search(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', _text)
    if _match_tgl:
        _d = int(_match_tgl.group(1))
        _m = int(_match_tgl.group(2))
        _y = _match_tgl.group(3)
        if _y:
            _y = int(_y)
            if _y < 100:
                _y += 2000
        else:
            _y = tanggal_hari_ini.year

        try:
            _tanggal = date(_y, _m, _d)
            _tanggal_detect = f"{_d:02d}/{_m:02d}/{_y}"
        except Exception:
            pass

    # ============================================
    # 2. PARSE SHIFT
    # ============================================
    _shift_map = {}

    # Strategi 1: Parse per baris "Kata: nama1, nama2"
    for _line in _text.split("\n"):
        _line_clean = _line.strip().lower()
        if not _line_clean:
            continue

        for _kw, _kode in KEYWORD_TO_KODE.items():
            # Cari pattern "kata: nama1, nama2, nama3" atau "- kata: ..."
            _pattern = rf'[-•\*]?\s*{re.escape(_kw)}\s*[:\-]\s*(.+)'
            _match = re.search(_pattern, _line_clean)

            if _match:
                _nama_str = _match.group(1)
                _nama_list = [
                    n.strip().upper()
                    for n in re.split(r'[,&;]+', _nama_str)
                    if n.strip() and len(n.strip()) >= 2
                ]
                for _nama in _nama_list:
                    _shift_map[_nama] = _kode
                break

    # Strategi 2: Kalau gak ada match, coba simple pattern
    if not _shift_map:
        # Cari "X libur", "X cuti", "X off"
        for _kw, _kode in [("libur", "O"), ("off", "O"), ("cuti", "C"), ("ao", "AO")]:
            _pattern_simple = rf'(\w+(?:\s+\w+)?)\s+(?:{_kw})'
            for _match in re.finditer(_pattern_simple, _text_lower):
                _nama = _match.group(1).strip().upper()
                if _nama and len(_nama) >= 2 and _nama not in KEYWORD_TO_KODE:
                    _shift_map[_nama] = _kode

    # ============================================
    # 3. VALIDASI
    # ============================================
    _warning = None
    if not _shift_map:
        _warning = "⚠️ Tidak ada data shift yang ke-detect. Cek format chat."

    # Filter nama yang ada di personil_master
    _personil_df = load_personil_master(only_active=True)
    if not _personil_df.empty:
        _valid_names = set(_personil_df["nama"].str.upper().tolist())
        _invalid = [n for n in _shift_map if n not in _valid_names]
        if _invalid:
            _warning = f"⚠️ Nama tidak dikenal: {', '.join(_invalid)}. Akan tetap disimpan."

    return {
        "tanggal": _tanggal,
        "tanggal_detect": _tanggal_detect,
        "shift_map": _shift_map,
        "raw_text": _text,
        "warning": _warning,
    }


# =========================================================
# 💾 SAVE: MASTER SHIFT
# =========================================================
def save_master_shift(tanggal, shift_map, sumber="chat", catatan=""):
    """
    Simpan/update master shift untuk tanggal tertentu.

    Args:
        tanggal: date
        shift_map: dict {nama: kode_shift}
        sumber: 'chat' / 'ocr' / 'manual'
        catatan: str
    """
    try:
        sb = get_supabase()

        if not shift_map:
            return False, "❌ Tidak ada data"

        _now = datetime.now(ZoneInfo("Asia/Jakarta")).isoformat()
        _tgl_str = tanggal.isoformat()[:10] if isinstance(tanggal, (date, datetime)) else str(tanggal)[:10]

        # Validasi kode
        _rows = []
        for _nama, _kode in shift_map.items():
            _kode_clean = str(_kode).strip().upper()
            if _kode_clean not in KODE_SHIFT:
                continue
            _rows.append({
                "tanggal": _tgl_str,
                "nama": str(_nama).strip().upper(),
                "kode_shift": _kode_clean,
                "sumber": str(sumber),
                "catatan": str(catatan),
                "updated_at": _now,
            })

        if not _rows:
            return False, "❌ Tidak ada baris valid"

        # Upsert (update kalau sudah ada, insert kalau belum)
        _res = sb.table("master_shift").upsert(
            _rows,
            on_conflict="tanggal,nama"
        ).execute()

        # Log
        try:
            sb.table("master_shift_log").insert({
                "tanggal": _tgl_str,
                "sumber": str(sumber),
                "chat_text": str(catatan)[:500],
                "jumlah_update": len(_rows),
                "updated_by": st.session_state.get("username", "admin"),
            }).execute()
        except Exception:
            pass

        return True, f"✅ {len(_rows)} shift tersimpan untuk {_tgl_str}"

    except Exception as e:
        return False, f"❌ {str(e)[:200]}"


def delete_master_shift_by_date(tanggal):
    """Hapus semua shift untuk tanggal tertentu."""
    try:
        sb = get_supabase()
        _tgl_str = tanggal.isoformat()[:10] if isinstance(tanggal, (date, datetime)) else str(tanggal)[:10]

        _res = sb.table("master_shift").delete().eq("tanggal", _tgl_str).execute()
        return True, f"🗑️ Shift tanggal {_tgl_str} dihapus"
    except Exception as e:
        return False, f"❌ {str(e)[:150]}"


# =========================================================
# 📊 LOAD: MATRIX BULANAN
# =========================================================
def load_master_shift_matrix(bulan=None, tahun=None):
    """
    Load master shift 1 bulan dalam format matrix.

    Returns:
        DataFrame dengan kolom: NAMA, 1, 2, 3, ..., 31
        (isinya kode shift: P7, S15, M22, O, C, AO)
    """
    try:
        sb = get_supabase()

        _now = datetime.now(ZoneInfo("Asia/Jakarta"))
        _bulan = bulan or _now.month
        _tahun = tahun or _now.year

        # Rentang tanggal
        _start = date(_tahun, _bulan, 1)
        if _bulan == 12:
            _end = date(_tahun + 1, 1, 1) - timedelta(days=1)
        else:
            _end = date(_tahun, _bulan + 1, 1) - timedelta(days=1)

        _total_hari = _end.day

        # Load data
        _res = sb.table("master_shift") \
            .select("tanggal, nama, kode_shift") \
            .gte("tanggal", _start.isoformat()) \
            .lte("tanggal", _end.isoformat()) \
            .execute()

        # Load personil
        _personil_df = load_personil_master(only_active=True)
        if _personil_df.empty:
            return pd.DataFrame()

        _personil_list = _personil_df.sort_values("urutan")["nama"].tolist()

        # Build matrix
        _matrix = {}
        for _r in (_res.data or []):
            _tgl_str = _r["tanggal"]
            _nama = _r["nama"]
            _kode = _r["kode_shift"]

            if _nama not in _matrix:
                _matrix[_nama] = {}
            _matrix[_nama][_tgl_str] = _kode

        # Build DataFrame
        _rows = []
        for _nama in _personil_list:
            _row = {"NAMA": _nama}
            for _day in range(1, _total_hari + 1):
                _tgl = date(_tahun, _bulan, _day)
                _row[str(_day)] = _matrix.get(_nama, {}).get(_tgl.isoformat(), "")
            _rows.append(_row)

        return pd.DataFrame(_rows)

    except Exception as e:
        print(f"[LOAD_MATRIX ERROR] {e}")
        return pd.DataFrame()


def get_shift_hari_ini(tanggal=None):
    """
    Ambil shift hari ini (untuk sync ke web SO).
    Returns: dict {nama: kode_shift}
    """
    try:
        sb = get_supabase()
        _tgl = tanggal or datetime.now(ZoneInfo("Asia/Jakarta")).date()
        _tgl_str = _tgl.isoformat()[:10]

        _res = sb.table("master_shift") \
            .select("nama, kode_shift") \
            .eq("tanggal", _tgl_str) \
            .execute()

        return {r["nama"]: r["kode_shift"] for r in (_res.data or [])}
    except Exception as e:
        print(f"[GET_SHIFT_TODAY ERROR] {e}")
        return {}


# =========================================================
# 📥 EXPORT: EXCEL
# =========================================================
def generate_master_shift_excel(matrix_df, bulan, tahun):
    """Generate Excel master shift dengan conditional formatting AUTO."""
    try:
        _output = io.BytesIO()

        with pd.ExcelWriter(_output, engine="xlsxwriter") as _writer:
            matrix_df.to_excel(_writer, sheet_name="Master Shift", index=False)

            _workbook = _writer.book
            _worksheet = _writer.sheets["Master Shift"]

            # Header
            _fmt_header = _workbook.add_format({
                "bold": True,
                "bg_color": "#FFD700",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            })

            _worksheet.set_column("A:A", 15, _fmt_header)
            _worksheet.set_column("B:AF", 5)

            # ✅ AUTO-GENERATE FORMAT dari KODE_SHIFT
            _last_col = chr(ord("A") + len(matrix_df.columns) - 1)
            _last_row = len(matrix_df) + 1

            for _kode, _info in KODE_SHIFT.items():
                _warna = _info.get("warna", "#CCCCCC")
                _fmt = _workbook.add_format({
                    "bg_color": _warna,
                    "bold": True,
                    "align": "center",
                    "border": 1,
                })

                _worksheet.conditional_format(
                    f"B2:{_last_col}{_last_row}",
                    {
                        "type": "cell",
                        "criteria": "==",
                        "value": f'"{_kode}"',
                        "format": _fmt,
                    }
                )

        return _output.getvalue()

    except Exception as e:
        print(f"[EXPORT_EXCEL ERROR] {e}")
        return None

# =========================================================
# 📅 HELPER: DAFTAR NAMA BULAN
# =========================================================
NAMA_BULAN_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}
