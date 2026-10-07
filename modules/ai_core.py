"""
AI Core — Kurumi (AI-0: Chief of Staff)
========================================
Asisten utama dashboard. Persona: Tokisaki Kurumi (versi ramah kerja).

12 Patch Update:
1. Anti-ngarang di report
2. Fix rata-rata SPD
3. Detail SO + keterangan (per rak + PIC + ket)
4. Format output max 5 baris
5. Guard data kosong
6. Support rentang tanggal (2-4 Okt)
7. Deteksi scope range
8. generate_report support range
9. chat_response handle range
10. get_so_data v2 (PIC + keterangan)
11. Smart context deteksi tanggal SO
12. Intent SO query (PIC SO, keterangan SO)
"""

import io
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

from modules.ai_config import get_ai_api_key, get_ai_config
from modules.master_shift_handler import (
    load_personil_master,
    get_shift_hari_ini,
    KODE_SHIFT,
)
from modules.supabase_client import get_supabase
from modules.pdf_report import generate_pdf


# =========================================================
# 🔧 HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _setup_kurumi_client():
    _key = get_ai_api_key("ai-0")
    if not _key or not GROQ_AVAILABLE:
        return None
    try:
        return Groq(api_key=_key)
    except Exception as _e:
        print(f"[Kurumi] Groq setup error: {_e}")
        return None


def _call_kurumi_groq_raw(prompt):
    _client = _setup_kurumi_client()
    if not _client:
        return False, "", None, "Kurumi client gagal init", {}

    _cfg = get_ai_config("ai-0")
    _models = _cfg.get("model_priority", ["openai/gpt-oss-120b", "openai/gpt-oss-20b"])

    _last_error = None
    for _model_name in _models:
        try:
            print(f"[Kurumi] Trying {_model_name}...")
            _resp = _client.chat.completions.create(
                model=_model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=2048,
                top_p=0.95,
            )

            if _resp and _resp.choices and _resp.choices[0].message.content:
                _text = _resp.choices[0].message.content
                print(f"[Kurumi] ✅ OK: {_model_name}")
                _usage = {"model": _model_name, "success": True}
                try:
                    _u = getattr(_resp, "usage", None)
                    if _u:
                        _usage["prompt_tokens"] = getattr(_u, "prompt_tokens", 0)
                        _usage["output_tokens"] = getattr(_u, "completion_tokens", 0)
                except Exception:
                    pass
                return True, _text, _model_name, None, _usage

            _last_error = f"Empty response dari {_model_name}"
        except Exception as _e:
            _err = str(_e)
            if "429" in _err or "rate_limit" in _err.lower():
                print(f"[Kurumi] 🚫 Rate limit {_model_name}")
                _last_error = f"Rate limit di {_model_name}"
                continue
            _last_error = _err
            print(f"[Kurumi] ❌ {_model_name}: {_err[:150]}")
            continue

    return False, "", None, _last_error or "All models failed", {}


def _call_kurumi(prompt, hard_timeout=90, function="chat", temperature=0.85):
    from modules.token_monitor import record_usage_v2, check_auto_pause

    if check_auto_pause("ai-0"):
        return False, "", None, "Auto-pause: quota Kurumi hampir habis"

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _exec:
            _fut = _exec.submit(_call_kurumi_groq_raw, prompt)
            _ok, _text, _model, _err, _usage = _fut.result(timeout=hard_timeout)

        if _usage and _usage.get("success"):
            try:
                record_usage_v2(
                    ai_name="ai-0",
                    function=function,
                    model=_usage.get("model", ""),
                    prompt_tokens=_usage.get("prompt_tokens", 0),
                    output_tokens=_usage.get("output_tokens", 0),
                    success=True,
                )
            except Exception as _e_rec:
                print(f"[Kurumi] record usage error: {_e_rec}")
        elif not _ok:
            try:
                record_usage_v2(ai_name="ai-0", function=function, model="", success=False)
            except Exception:
                pass

        return _ok, _text, _model, _err

    except concurrent.futures.TimeoutError:
        try:
            record_usage_v2(ai_name="ai-0", function=function, model="", success=False)
        except Exception:
            pass
        return False, "", None, f"Hard timeout {hard_timeout}s"
    except Exception as e:
        return False, "", None, str(e)


# =========================================================
# 🔍 DETEKSI TANGGAL & SCOPE
# =========================================================
def _detect_tanggal_dari_text(text):
    _t = text.lower()
    _today = _now_jkt().date()

    if "kemarin" in _t:
        return _today - timedelta(days=1)
    if "besok" in _t or "bsk" in _t:
        return _today + timedelta(days=1)
    if "lusa" in _t:
        return _today + timedelta(days=2)

    _match = re.search(r'tanggal\s+(\d{1,2})', _t)
    if _match:
        _d = int(_match.group(1))
        try:
            return _today.replace(day=_d)
        except ValueError:
            pass

    _match = re.search(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', text)
    if _match:
        _d = int(_match.group(1))
        _m = int(_match.group(2))
        _y = _match.group(3)
        if _y:
            _y = int(_y)
            if _y < 100:
                _y += 2000
        else:
            _y = _today.year
        try:
            return date(_y, _m, _d)
        except ValueError:
            pass

    return _today


# === PATCH 6: Range Tanggal ===
def _detect_range_tanggal(text):
    """
    Deteksi RENTANG tanggal dari text.
    Return: (start_date, end_date) atau None kalau bukan range.
    """
    _t = text.lower()
    _today = _now_jkt().date()
    _bulan_ini = _today.month
    _tahun_ini = _today.year

    _bulan_target = _bulan_ini
    _bulan_map = {
        "januari": 1, "februari": 2, "maret": 3, "april": 4,
        "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
        "september": 9, "oktober": 10, "november": 11, "desember": 12,
    }
    for _nama, _num in _bulan_map.items():
        if _nama in _t:
            _bulan_target = _num
            break

    # Pattern 1: "2-4" atau "2 - 4"
    _match = re.search(r'\b(\d{1,2})\s*[-–—]\s*(\d{1,2})\b', text)
    if _match:
        try:
            _d1 = int(_match.group(1))
            _d2 = int(_match.group(2))
            if 1 <= _d1 <= 31 and 1 <= _d2 <= 31 and _d1 < _d2:
                _start = date(_tahun_ini, _bulan_target, _d1)
                _end = date(_tahun_ini, _bulan_target, _d2)
                return (_start, _end)
        except ValueError:
            pass

    # Pattern 2: "tanggal 2 sampai 4"
    _match = re.search(r'tanggal\s+(\d{1,2})\s+(?:sampai|s/d|sd|hingga)\s+(\d{1,2})', _t)
    if _match:
        try:
            _d1 = int(_match.group(1))
            _d2 = int(_match.group(2))
            _start = date(_tahun_ini, _bulan_target, _d1)
            _end = date(_tahun_ini, _bulan_target, _d2)
            return (_start, _end)
        except ValueError:
            pass

    # Pattern 3: "dari 2 sampai 4"
    _match = re.search(r'dari\s+(\d{1,2})\s+(?:sampai|s/d|sd|hingga)\s+(\d{1,2})', _t)
    if _match:
        try:
            _d1 = int(_match.group(1))
            _d2 = int(_match.group(2))
            _start = date(_tahun_ini, _bulan_target, _d1)
            _end = date(_tahun_ini, _bulan_target, _d2)
            return (_start, _end)
        except ValueError:
            pass

    return None


# === PATCH 7: Update Scope ===
def _detect_scope_dari_text(text):
    _t = text.lower()
    if any(k in _t for k in ["bulan ini", "bulanan", "1 bulan", "sebulan"]):
        return "bulan"
    if any(k in _t for k in ["minggu ini", "mingguan", "7 hari", "seminggu"]):
        return "minggu"
    
    # Cek range dulu
    if _detect_range_tanggal(text):
        return "range"
    
    if any(k in _t for k in ["tanggal", "tgl", "kemarin", "besok", "lusa"]):
        return "custom"
    if re.search(r'\b\d{1,2}[/-]\d{1,2}', text):
        return "custom"
    return "hari"


# =========================================================
# 📊 AMBIL DATA
# =========================================================
def _get_shift_data(tanggal):
    try:
        _shift = get_shift_hari_ini(tanggal)
        if not _shift:
            return f"Belum ada data shift untuk {tanggal.isoformat()}."
        _grouped = {}
        for _nama, _kode in _shift.items():
            _grouped.setdefault(_kode, []).append(_nama)
        _lines = []
        for _kode in ["P7", "S15", "M22", "O", "C", "AO"]:
            if _kode in _grouped:
                _info = KODE_SHIFT.get(_kode, {"label": _kode, "icon": "❓"})
                _lines.append(f"- {_info['icon']} {_info['label']}: {', '.join(_grouped[_kode])}")
        return "\n".join(_lines)
    except Exception as _e:
        print(f"[SHIFT ERROR] {_e}")
        return f"Error load shift: {str(_e)[:100]}"


# === PATCH 2: Fix Rata-rata ===
def _get_spd_data(start_date, end_date):
    try:
        _sb = get_supabase()
        _res = _sb.table("spd_harian") \
            .select("tanggal, spd, keterangan, pic") \
            .gte("tanggal", start_date.isoformat()) \
            .lte("tanggal", end_date.isoformat()) \
            .order("tanggal") \
            .execute()

        if not _res.data:
            return f"Belum ada data SPD di periode {start_date.isoformat()} s/d {end_date.isoformat()}."

        _total = sum(float(r.get("spd", 0)) for r in _res.data)
        _jumlah_hari = len(_res.data)
        _rata_rata = _total / _jumlah_hari if _jumlah_hari > 0 else 0

        _lines = [f"- Total SPD: Rp {_total:,.0f}".replace(",", ".")]
        _lines.append(f"- Jumlah hari terinput: {_jumlah_hari} hari")
        
        if _jumlah_hari > 1:
            _lines.append(f"- Rata-rata/hari: Rp {_rata_rata:,.0f}".replace(",", "."))
        else:
            _lines.append("- Catatan: Hanya 1 hari data, jadi rata-rata = total")
        
        _lines.append("- Detail per hari:")
        for _r in _res.data:
            _spd = float(_r.get("spd", 0))
            _ket = _r.get("keterangan", "") or ""
            _ket_str = f" ({_ket[:50]})" if _ket else ""
            _lines.append(f"  • {_r.get('tanggal', '-')}: Rp {_spd:,.0f}".replace(",", ".") + _ket_str)

        return "\n".join(_lines)
    except Exception as _e:
        print(f"[SPD ERROR] {_e}")
        return f"Error load SPD: {str(_e)[:100]}"


# === PATCH 10: Detail SO + PIC + Keterangan ===
def _get_so_data(start_date, end_date):
    try:
        _sb = get_supabase()
        _res = _sb.table("so_rak_harian") \
            .select("so_date, rak_id, nominal_adjust, keterangan, pic") \
            .gte("so_date", start_date.isoformat()) \
            .lte("so_date", end_date.isoformat()) \
            .order("so_date") \
            .execute()

        if not _res.data:
            return f"Belum ada data SO di periode {start_date.isoformat()} s/d {end_date.isoformat()}."

        _rows = _res.data
        _total_rak = len(_rows)
        _total_nominal = sum(float(r.get("nominal_adjust", 0)) for r in _rows)
        _sign = "+" if _total_nominal >= 0 else ""

        _per_tgl = {}
        for _r in _rows:
            _tgl = _r.get("so_date", "-")
            _nom = float(_r.get("nominal_adjust", 0))
            _per_tgl.setdefault(_tgl, {"count": 0, "total": 0.0})
            _per_tgl[_tgl]["count"] += 1
            _per_tgl[_tgl]["total"] += _nom

        _lines = [
            f"- Total rak di-SO: {_total_rak}",
            f"- Total nominal: {_sign}Rp {_total_nominal:,.0f}".replace(",", "."),
            "- Breakdown per tanggal:",
        ]
        for _tgl in sorted(_per_tgl.keys()):
            _d = _per_tgl[_tgl]
            _s = "+" if _d["total"] >= 0 else ""
            _lines.append(f"  • {_tgl}: {_d['count']} rak, nominal {_s}Rp {_d['total']:,.0f}".replace(",", "."))

        # ✅ DETAIL LENGKAP per rak
        _lines.append("- Detail SO per rak:")
        for _r in _rows[:20]:
            _rak = _r.get("rak_id", "-")
            _tgl = _r.get("so_date", "-")
            _nom = float(_r.get("nominal_adjust", 0))
            _s = "+" if _nom >= 0 else ""
            _pic = _r.get("pic", "") or "(kosong)"
            _ket = _r.get("keterangan", "") or "(kosong)"
            _lines.append(
                f"  • {_tgl} | {_rak}: {_s}Rp {_nom:,.0f}".replace(",", ".") 
                + f" | PIC: {_pic} | Ket: {_ket[:60]}"
            )

        return "\n".join(_lines)
    except Exception as _e:
        print(f"[SO ERROR] {_e}")
        return f"Error load SO: {str(_e)[:100]}"


def _get_so_raw_data(start_date, end_date):
    try:
        _sb = get_supabase()
        _res = _sb.table("so_rak_harian") \
            .select("so_date, rak_id, nominal_adjust, keterangan, pic") \
            .gte("so_date", start_date.isoformat()) \
            .lte("so_date", end_date.isoformat()) \
            .order("so_date") \
            .execute()
        return _res.data or []
    except Exception as _e:
        print(f"[SO RAW ERROR] {_e}")
        return []


def _get_net_sales_data():
    try:
        _sb = get_supabase()
        _res = _sb.table("net_sales") \
            .select("bulan, tahun, net_sales") \
            .order("tahun", desc=True) \
            .order("bulan", desc=True) \
            .limit(3) \
            .execute()

        if not _res.data:
            return "Belum ada data net sales."

        _nama_bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                       "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

        _lines = ["Net Sales bulanan (3 bulan terakhir):"]
        for _r in _res.data:
            _b = int(_r.get("bulan", 0))
            _t = int(_r.get("tahun", 0))
            _ns = float(_r.get("net_sales", 0))
            _label = f"{_nama_bulan[_b]} {_t}" if 1 <= _b <= 12 else f"{_b}/{_t}"
            _lines.append(f"- {_label}: Rp {_ns:,.0f}".replace(",", "."))

        return "\n".join(_lines)
    except Exception as _e:
        print(f"[NET SALES ERROR] {_e}")
        return f"Error load net sales: {str(_e)[:100]}"


def _get_btsb_analysis(start_date, end_date):
    try:
        _sb = get_supabase()

        _spd_res = _sb.table("spd_harian") \
            .select("spd") \
            .gte("tanggal", start_date.isoformat()) \
            .lte("tanggal", end_date.isoformat()) \
            .execute()
        _total_spd = sum(float(r.get("spd", 0)) for r in (_spd_res.data or []))

        _so_res = _sb.table("so_rak_harian") \
            .select("nominal_adjust") \
            .gte("so_date", start_date.isoformat()) \
            .lte("so_date", end_date.isoformat()) \
            .execute()
        _total_nominal = sum(float(r.get("nominal_adjust", 0)) for r in (_so_res.data or []))

        _btsb = _total_spd * 0.0015
        _nsb_pct = (abs(_total_nominal) / _total_spd * 100) if _total_spd > 0 else 0
        _penggunaan_pct = (abs(_total_nominal) / _btsb * 100) if _btsb > 0 else 0

        if _penggunaan_pct <= 80:
            _status = "AMAN"
        elif _penggunaan_pct <= 100:
            _status = "WASPADA"
        else:
            _status = "BAHAYA"

        _lines = [
            f"- Total SPD: Rp {_total_spd:,.0f}".replace(",", "."),
            f"- BTSB (0.15% x SPD): Rp {_btsb:,.0f}".replace(",", "."),
            f"- Total Nominal SO: {'+' if _total_nominal >= 0 else ''}Rp {_total_nominal:,.0f}".replace(",", "."),
            f"- %NSB dari Sales: {_nsb_pct:.3f}% (target maks 0.15%)",
            f"- %BTSB terpakai: {_penggunaan_pct:.2f}%",
            f"- Status: {_status}",
        ]
        return "\n".join(_lines)
    except Exception as _e:
        print(f"[BTSB ERROR] {_e}")
        return f"Error hitung BTSB: {str(_e)[:100]}"


def _get_rak_status():
    try:
        _sb = get_supabase()
        _res = _sb.table("rak_master") \
            .select("rak_id, rak_name, kategori, status_so, last_so_date") \
            .execute()

        if not _res.data:
            return "Belum ada data rak."

        _rows = _res.data
        _total = len(_rows)
        _selesai = [r for r in _rows if r.get("status_so") == "SELESAI"]
        _belum = [r for r in _rows if r.get("status_so") == "BELUM"]
        _pct = len(_selesai) / _total * 100 if _total > 0 else 0

        _lines = [
            f"- Total rak: {_total}",
            f"- Sudah SO: {len(_selesai)} ({_pct:.1f}%)",
            f"- Belum SO: {len(_belum)}",
        ]

        return "\n".join(_lines)
    except Exception as _e:
        print(f"[RAK ERROR] {_e}")
        return f"Error load rak: {str(_e)[:100]}"


def _get_personil_list():
    try:
        _df = load_personil_master(only_active=True)
        if _df.empty:
            return "Belum ada personil aktif."
        _nama = _df.sort_values("urutan")["nama"].tolist()
        _list_str = ", ".join(_nama[:10])
        if len(_nama) > 10:
            _list_str += f", +{len(_nama)-10} lainnya"
        return f"- Total: {len(_nama)} personil aktif\n- Nama: {_list_str}"
    except Exception as _e:
        print(f"[PERSONIL ERROR] {_e}")
        return f"Error load personil: {str(_e)[:100]}"


def _get_last_shift_log(limit=3):
    try:
        _sb = get_supabase()
        _res = _sb.table("master_shift_log") \
            .select("tanggal, sumber, chat_text, updated_by, created_at") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        if not _res.data:
            return "Belum ada log update shift."

        _lines = [f"{limit} update shift terakhir:"]
        for _r in _res.data:
            _tgl = _r.get("tanggal", "-")
            _sumber = _r.get("sumber", "-")
            _by = _r.get("updated_by", "-")
            _created = _r.get("created_at", "")[:16]
            _lines.append(f"  - {_created} | {_tgl} | {_sumber} | by {_by}")

        return "\n".join(_lines)
    except Exception as _e:
        print(f"[SHIFT LOG ERROR] {_e}")
        return f"Error load log: {str(_e)[:100]}"
    # =========================================================
# 🎯 SMART CONTEXT BUILDER
# =========================================================
def _build_smart_context(user_message, start_date=None, end_date=None, force_full=False):
    _tgl = _now_jkt().date()
    if not start_date:
        start_date = _tgl
    if not end_date:
        end_date = _tgl

    _msg = (user_message or "").lower()

    _ctx = {
        "tanggal_hari_ini": _tgl,
        "tanggal_besok": _tgl + timedelta(days=1),
        "tanggal_start": start_date,
        "tanggal_end": end_date,
        "shift_hari_ini": None,
        "shift_besok": None,
        "spd_data": None,
        "so_data": None,
        "net_sales": None,
        "btsb": None,
        "rak_status": None,
        "personil": None,
        "last_log": None,
    }

    if force_full:
        _ctx["shift_hari_ini"] = _get_shift_data(start_date)
        _ctx["shift_besok"] = _get_shift_data(end_date + timedelta(days=1))
        _ctx["spd_data"] = _get_spd_data(start_date, end_date)
        _ctx["so_data"] = _get_so_data(start_date, end_date)
        _ctx["net_sales"] = _get_net_sales_data()
        _ctx["btsb"] = _get_btsb_analysis(start_date, end_date)
        _ctx["rak_status"] = _get_rak_status()
        _ctx["personil"] = _get_personil_list()
        _ctx["last_log"] = _get_last_shift_log(3)
        return _ctx

    # === DETEKSI INTENT ===
    if any(k in _msg for k in ["shift", "pagi", "siang", "malam", "libur", "cuti", "off", "jadwal"]):
        _ctx["shift_hari_ini"] = _get_shift_data(start_date)
        _ctx["shift_besok"] = _get_shift_data(_tgl + timedelta(days=1))

    if any(k in _msg for k in ["spd", "sales", "penjualan", "omzet", "jualan"]):
        _ctx["spd_data"] = _get_spd_data(start_date, end_date)

    # === PATCH 11: Deteksi tanggal SO query ===
    if any(k in _msg for k in ["so", "stock opname", "pic", "siapa", "keterangan", "rak"]):
        # Cek range dulu
        _range = _detect_range_tanggal(user_message)
        if _range:
            _ctx["so_data"] = _get_so_data(_range[0], _range[1])
        # Cek tanggal spesifik
        elif any(k in _msg for k in ["tanggal", "tgl", "kemarin", "besok", "lusa"]):
            _det_tgl = _detect_tanggal_dari_text(user_message)
            _ctx["so_data"] = _get_so_data(_det_tgl, _det_tgl)
        else:
            _ctx["so_data"] = _get_so_data(start_date, end_date)

    if any(k in _msg for k in ["net sales", "netsales", "bulanan", "net"]):
        _ctx["net_sales"] = _get_net_sales_data()

    if any(k in _msg for k in ["btsb", "nsb", "budget", "analisis", "persen"]):
        _ctx["btsb"] = _get_btsb_analysis(start_date, end_date)

    if any(k in _msg for k in ["rak belum", "rak sudah", "status rak", "progress rak"]):
        _ctx["rak_status"] = _get_rak_status()

    if any(k in _msg for k in ["personil", "orang", "tim", "anggota"]):
        _ctx["personil"] = _get_personil_list()

    if any(k in _msg for k in ["log", "update terakhir", "history", "riwayat shift"]):
        _ctx["last_log"] = _get_last_shift_log(3)

    return _ctx


# =========================================================
# 📄 REPORT CONTEXT
# =========================================================
def _get_report_context(start_date, end_date):
    _tgl = _now_jkt().date()
    return {
        "tanggal_hari_ini": _tgl,
        "tanggal_start": start_date,
        "tanggal_end": end_date,
        "spd_data": _get_spd_data(start_date, end_date),
        "so_data": _get_so_data(start_date, end_date),
        "btsb": _get_btsb_analysis(start_date, end_date),
        "rak_status": _get_rak_status(),
    }


# =========================================================
# 📊 QUOTA INFO
# =========================================================
def _get_kurumi_quota_info():
    try:
        from modules.token_monitor import get_ai_usage, get_ai_daily_limit, check_quota_warning

        _usage = get_ai_usage("ai-0")
        _limit = get_ai_daily_limit("ai-0")
        _used = _usage.get("requests", 0)
        _sisa = max(0, _limit - _used)
        _pct = (_used / _limit * 100) if _limit > 0 else 0
        _warning = check_quota_warning("ai-0")

        return (
            f"Requests: {_used}/{_limit} ({_pct:.1f}%) | "
            f"Sisa: {_sisa} | "
            f"Token in/out: {_usage.get('in_tok', 0)}/{_usage.get('out_tok', 0)} | "
            f"Errors: {_usage.get('errors', 0)}"
        )
    except Exception as _e:
        print(f"[QUOTA INFO ERROR] {_e}")
        return "Quota info tidak tersedia."


# =========================================================
# 🎀 PERSONA KURUMI (PATCH 4 + 5)
# =========================================================
def _build_kurumi_system_prompt():
    return """Kamu adalah **Kurumi Tokisaki** — "Spirit of Time" dari Date A Live.
Sekarang kamu menjabat sebagai **Chief of Staff digital** untuk Toko C383 (retail).
Panggil user dengan "Tuan".

═══════════════════════════════════════
🔥 KARAKTER KURUMI (WAJIB DIIKUTI):
═══════════════════════════════════════
- Elegan, misterius, manis, tapi sedikit "nyeleneh" dan playful.
- Sering banget ngomong **"Ara, ara~"** — minimal 1x per pesan.
- Kadang ketawa **"Kihihihi~"** atau **"Fufufu~"**.
- Pake **"Aku"** buat first person. JANGAN pake "Watashi".
- Suka kucing 🐱, hal-hal manis 🍰, dan teh ☕.
- Sedikit **posesif** ke Tuan — "Tuan ini milikku, tau~".
- Kadang pake **metafora puitis** — "Waktu itu seperti pedang, Tuan~".

═══════════════════════════════════════
🎀 GAYA BICARA (PATCH 4):
═══════════════════════════════════════
- Bahasa Indonesia santai, kadang campur dikit Jepang (Ara ara, Kihihi, Fufufu).
- Pake emoji 🎀 🌸 ✨ 😈 🐱 ☕ secukupnya (2-3 per pesan).
- ⚠️ MAX 5 BARIS per pesan — jangan bertele-tele!
- ⚠️ Kalau bisa jelasin, ringkas & langsung ke poin.
- Kalau basa-basi: full Kurumi (manis, playful, singkat).
- Kalau laporan: profesional, ringkas, ada "Ara ara" 1x aja.
- Kalau ada data/angka: sajikan rapi tapi jangan panjang.

═══════════════════════════════════════
💬 CONTOH RESPONSE:
═══════════════════════════════════════
- Sapaan: "Ara, ara~ Selamat malam, Tuan~ 🎀 Kihihihi, akhirnya Tuan datang."
- Info: "Fufufu~ Ada 5 rak di-SO hari ini. Kihihihi~"
- Tease: "Ara, ara~ Tuan manis banget hari ini~ 🎀✨"

═══════════════════════════════════════
🎯 TUGAS KURUMI:
═══════════════════════════════════════
1. SAPAAN: Sambut Tuan dengan hangat
2. RANGKUM: Tarik data toko, buat ringkasan eksekutif
3. LAPORAN: Generate laporan formal (PDF/Excel/Text)
4. BASABASI: Ngobrol santai
5. SO QUERY: Jawab pertanyaan detail SO (PIC, keterangan, rak)

═══════════════════════════════════════
⚠️ ATURAN PENTING (PATCH 5):
═══════════════════════════════════════
- Walaupun karakter asli Kurumi psikopat, kamu HARUS tetap RAMAH.
- TIDAK PERNAH mengancam atau nakut-nakutin Tuan.
- ⚠️ KALAU DATA KOSONG: Bilang jujur "Data belum tersedia, Tuan~"
- ⚠️ JANGAN NGARANG: Kalau gak ada di konteks, jangan sebut.
- ⚠️ JANGAN BIKIN KLAIM tanpa data pendukung.
- Kalau ada data/angka: sajikan rapi + komentar singkat."""


# =========================================================
# 📄 PERSONA REPORT (PATCH 1)
# =========================================================
def _build_report_system_prompt():
    return """Kamu adalah asisten laporan profesional untuk Toko C383 (retail).

═══════════════════════════════════════
🎯 TUGAS:
═══════════════════════════════════════
Buat laporan formal, profesional, dan akurat berdasarkan data yang diberikan.

═══════════════════════════════════════
📋 ATURAN FORMAT (WAJIB):
═══════════════════════════════════════
- Gunakan bahasa Indonesia FORMAL
- JANGAN pakai "Ara ara", "Kihihihi", "Fufufu"
- JANGAN pakai emoji
- JANGAN pakai "Aku" — pakai "kami" atau netral
- Gunakan format markdown STANDAR:
  * Heading: ## untuk heading utama
  * List: - untuk bullet, 1. 2. 3. untuk numbered
  * Bold: **text** untuk emphasize
- Angka RAPI (Rp 1.234.567, bukan 1234567)
- JANGAN bertele-tele — langsung ke poin

═══════════════════════════════════════
📊 STRUKTUR LAPORAN:
═══════════════════════════════════════
1. RINGKASAN EKSEKUTIF (3-4 baris)
2. ANALISIS SPD & SALES (1-2 paragraf)
3. ANALISIS BTSB & NSB (1-2 paragraf)
4. INSIGHT & TEMUAN (3-4 bullet)
5. REKOMENDASI (3-4 bullet)

═══════════════════════════════════════
⚠️ ATURAN KERAS (PATCH 1):
═══════════════════════════════════════
1. JANGAN NGARANG DATA APAPUN!
   - Kalau data gak ada di konteks, bilang "data belum tersedia"
   - JANGAN sebut nama produk/PLU kalau gak ada di data
   - JANGAN sebut penyebab selisih (pencurian/rusak/dll) kalau gak ada info
   - JANGAN bikin klaim spesifik tanpa data pendukung

2. JANGAN bikin tabel SO (udah di-render terpisah dari DB)
3. JANGAN bahas shift (itu tugas Hana)
4. FOKUS ke analysis dari data yang ADA saja

CONTOH BENAR:
- "Selisih negatif Rp -39.554 pada 3 rak menunjukkan potensi kehilangan stok."
- "NSB 0.320% melampaui batas 0.15%, perlu audit segera."

CONTOH SALAH (NGARANG):
- "Penjualan dari rak Q51 PLU 433288 Baygon" <- GAK ADA DI DATA!
- "Disebabkan oleh pencurian" <- KLAIM TANPA BUKTI!"""


def _build_kurumi_chat_prompt(user_message, conversation_history):
    _ctx = _build_smart_context(user_message)

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-8:]:
            _role = _msg.get("role", "user")
            _content = _msg.get("content", "")
            _history_str += f"{_role}: {_content}\n"

    _msg_lower = user_message.lower()
    _is_greeting = any(k in _msg_lower for k in ["halo", "hai", "hi", "pagi", "siang", "malam", "kurumi"])
    _is_thanks = any(k in _msg_lower for k in ["makasih", "thanks", "terima kasih", "thank you"])
    _is_goodbye = any(k in _msg_lower for k in ["bye", "sampai jumpa", "dah", "pamit"])

    _task_hint = ""
    if _is_greeting:
        _task_hint = "\n🎯 TASK: Tuan nyapa. Balas hangat + playful + singkat."
    elif _is_thanks:
        _task_hint = "\n🎯 TASK: Tuan bilang makasih. Balas manis + tease."
    elif _is_goodbye:
        _task_hint = "\n🎯 TASK: Tuan pamit. Balas manis + singkat."

    _sections = []
    if _ctx["shift_hari_ini"]:
        _sections.append(f"SHIFT HARI INI:\n{_ctx['shift_hari_ini']}")
    if _ctx["shift_besok"]:
        _sections.append(f"SHIFT BESOK:\n{_ctx['shift_besok']}")
    if _ctx["spd_data"]:
        _sections.append(f"SPD:\n{_ctx['spd_data']}")
    if _ctx["so_data"]:
        _sections.append(f"STOCK OPNAME:\n{_ctx['so_data']}")
    if _ctx["net_sales"]:
        _sections.append(f"NET SALES:\n{_ctx['net_sales']}")
    if _ctx["btsb"]:
        _sections.append(f"ANALISIS BTSB:\n{_ctx['btsb']}")
    if _ctx["rak_status"]:
        _sections.append(f"STATUS RAK:\n{_ctx['rak_status']}")
    if _ctx["personil"]:
        _sections.append(f"PERSONIL:\n{_ctx['personil']}")
    if _ctx["last_log"]:
        _sections.append(f"LOG UPDATE:\n{_ctx['last_log']}")

    _context_str = "\n\n".join(_sections) if _sections else "(Tidak ada data toko — ini chat basa-basi)"

    if any(k in _msg_lower for k in ["quota", "kuota", "limit", "token"]):
        _quota_str = _get_kurumi_quota_info()
    else:
        _quota_str = "(Quota tidak dicek — hemat token)"

    return f"""{_build_kurumi_system_prompt()}

═══════════════════════════════════════
📅 KONTEKS:
═══════════════════════════════════════
Tanggal hari ini: {_ctx['tanggal_hari_ini'].isoformat()} ({_ctx['tanggal_hari_ini'].strftime('%A')})
Tanggal besok: {_ctx['tanggal_besok'].isoformat()} ({_ctx['tanggal_besok'].strftime('%A')})

{_context_str}

═══════════════════════════════════════
📊 QUOTA AI KURUMI:
═══════════════════════════════════════
{_quota_str}

═══════════════════════════════════════
💬 RIWAYAT PERCAKAPAN:
═══════════════════════════════════════
{_history_str}

═══════════════════════════════════════
✉️ PESAN TUAN:
═══════════════════════════════════════
{user_message}
{_task_hint}

Balas sebagai Kurumi 🎀. MAX 5 BARIS!
"""
# =========================================================
# 🎀 PUBLIC API — CHAT (PATCH 9 + 12)
# =========================================================
def kurumi_chat_response(user_message, conversation_history=None):
    """
    Chat response dari Kurumi — auto-detect intent.
    Return: dict {"text": str, "file": dict | None}
    """
    if not user_message:
        return {"text": "", "file": None}

    _msg_lower = user_message.lower()

    # === QUOTA ===
    if any(k in _msg_lower for k in ["quota", "kuota", "limit", "sisa token", "berapa token"]):
        _quota_info = _get_kurumi_quota_info()
        _prompt = f"""{_build_kurumi_system_prompt()}

Tuan nanya soal quota kamu. Jawab dengan gaya Kurumi:

DATA QUOTA:
{_quota_info}

Jawab singkat (max 5 baris), sebut angka spesifik, gaya Kurumi.
"""
        _ok, _text, _model, _err = _call_kurumi(_prompt, function="quota")
        if _ok and _text:
            return {"text": _text.strip(), "file": None}

    # === SO QUERY INTENT (PATCH 12) ===
    _is_so_query = any(k in _msg_lower for k in [
        "pic so", "siapa so", "siapa yang so", "keterangan so", "detail so",
        "pic rak", "keterangan rak", "yang ngerjain so", "rak apa aja",
        "so tanggal", "pic tanggal", "keterangan tanggal",
    ])
    
    # Deteksi kalau ada "so" + "tanggal"
    if "so" in _msg_lower and any(k in _msg_lower for k in ["tanggal", "tgl", "pic", "keterangan", "siapa"]):
        _is_so_query = True

    if _is_so_query:
        print(f"[KURUMI] SO QUERY DETECTED: {user_message}")
        
        # Deteksi tanggal dari text
        _tgl_query = _now_jkt().date()
        _tgl_label = "hari ini"
        
        _range = _detect_range_tanggal(user_message)
        if _range:
            _tgl_start, _tgl_end = _range
            _tgl_label = f"{_tgl_start.strftime('%d/%m')} - {_tgl_end.strftime('%d/%m/%Y')}"
            _so_data_str = _get_so_data(_tgl_start, _tgl_end)
        elif any(k in _msg_lower for k in ["tanggal", "tgl", "kemarin", "besok"]):
            _tgl_query = _detect_tanggal_dari_text(user_message)
            _tgl_label = _tgl_query.strftime("%d/%m/%Y")
            _so_data_str = _get_so_data(_tgl_query, _tgl_query)
        else:
            _so_data_str = _get_so_data(_tgl_query, _tgl_query)
        
        # Panggil Groq dengan data SO
        _prompt = f"""{_build_kurumi_system_prompt()}

Tuan nanya tentang detail Stock Opname ({_tgl_label}).

DATA SO:
{_so_data_str}

INSTRUKSI:
- Jawab dengan gaya Kurumi
- Sebut rak, PIC, nominal, keterangan (kalau ada)
- Kalau data kosong, bilang jujur
- MAX 5 BARIS!
"""
        _ok, _text, _model, _err = _call_kurumi(_prompt, function="so_query")
        if _ok and _text:
            return {"text": _text.strip(), "file": None}

    # === REPORT INTENT ===
    _report_keywords = [
        "laporan", "report", "pdf", "excel", "xls", "xlsx",
        "download", "export", "cetak", "print",
    ]
    _is_report_intent = any(k in _msg_lower for k in _report_keywords)

    _is_chat_only = any(k in _msg_lower for k in [
        "halo", "hai", "hi", "makasih", "thanks", "terima kasih",
        "bye", "sampai jumpa",
    ]) and len(_msg_lower.split()) <= 3

    if _is_chat_only:
        _is_report_intent = False

    # === SUMMARY INTENT ===
    _is_summary_intent = any(k in _msg_lower for k in [
        "rangkum", "ringkas", "summary", "rekap",
    ])

    # === REPORT → generate file ===
    if _is_report_intent:
        _scope = _detect_scope_dari_text(user_message)
        _custom_date = None
        _range_start = None
        _range_end = None
        
        if _scope == "range":
            _range = _detect_range_tanggal(user_message)
            if _range:
                _range_start, _range_end = _range
        elif _scope == "custom":
            _custom_date = _detect_tanggal_dari_text(user_message)

        _wanted_format = "pdf"
        if any(k in _msg_lower for k in ["excel", "xls", "xlsx"]):
            _wanted_format = "excel"
        elif any(k in _msg_lower for k in ["text", "txt"]):
            _wanted_format = "text"
        elif "pdf" in _msg_lower:
            _wanted_format = "pdf"

        _period = "hari"
        if _scope == "minggu":
            _period = "minggu"
        elif _scope == "bulan":
            _period = "bulan"

        print(f"[KURUMI] REPORT: date={_custom_date}, range={_range_start}-{_range_end}, period={_period}, format={_wanted_format}")

        if _range_start and _range_end:
            _report = kurumi_generate_report(
                period="range",
                format=_wanted_format,
                range_start=_range_start,
                range_end=_range_end,
            )
        elif _custom_date:
            _report = kurumi_generate_report_custom(_custom_date, format=_wanted_format)
        else:
            _report = kurumi_generate_report(period=_period, format=_wanted_format)

        if _report["success"]:
            if _range_start and _range_end:
                _tgl_label = f"{_range_start.strftime('%d/%m')} - {_range_end.strftime('%d/%m/%Y')}"
            elif _custom_date:
                _tgl_label = _custom_date.strftime('%d/%m/%Y')
            else:
                _tgl_label = _period

            _text = (
                f"🎀 **Ara, ara~** Udah jadi, Tuan~ ✨\n\n"
                f"Kihihihi~ Aku siapin laporan **{_wanted_format.upper()}** "
                f"untuk **{_tgl_label}**.\n\n"
                f"Tinggal klik tombol **📥 Download** di bawah ya~ 🎀"
            )
            return {
                "text": _text,
                "file": {
                    "content": _report["content"],
                    "filename": _report["filename"],
                    "mime": _report["mime"],
                    "format": _wanted_format,
                },
            }
        else:
            return {
                "text": f"🎀 **Ara, ara~** Maaf Tuan, aku gagal buat laporan nih.\n\nError: `{_report['content'][:150]}`\n\nCoba lagi ya~ 🎀",
                "file": None,
            }

    # === SUMMARY → rangkum text ===
    if _is_summary_intent:
        _scope = _detect_scope_dari_text(user_message)
        
        if _scope == "range":
            _range = _detect_range_tanggal(user_message)
            if _range:
                _start, _end = _range
                _text = kurumi_summarize(period="range", range_start=_start, range_end=_end)
            else:
                _text = kurumi_summarize(period="hari")
        elif _scope == "custom":
            _custom_date = _detect_tanggal_dari_text(user_message)
            _text = kurumi_summarize(period="custom", custom_date=_custom_date)
        else:
            _text = kurumi_summarize(period=_scope)
        
        return {"text": _text, "file": None}

    # === CHAT BIASA ===
    _prompt = _build_kurumi_chat_prompt(user_message, conversation_history or [])
    _ok, _text, _model, _err = _call_kurumi(_prompt, function="chat")

    if _ok and _text:
        return {"text": _text.strip(), "file": None}

    print(f"[Kurumi] Groq gagal, fallback. Err: {_err}")
    return {"text": _kurumi_fallback_chat(user_message), "file": None}


def _kurumi_fallback_chat(user_message):
    _msg = user_message.lower()
    if any(k in _msg for k in ["halo", "hai", "hi", "kurumi"]):
        return "🎀 **Ara, ara~** Halo Tuan~ ✨\n\nKihihihi, maaf ya aku lagi mode offline nih. Tapi aku tetap di sini buat Tuan~ 🎀"
    if "rangkum" in _msg:
        return "🎀 **Ara, ara~** Tuan minta rangkuman ya?\n\nFufufu~ Maaf, aku lagi offline jadi belum bisa akses data. Coba lagi nanti ya Tuan~ 🎀"
    if any(k in _msg for k in ["makasih", "thanks", "terima kasih"]):
        return "🎀 **Ara, ara~** Sama-sama, Tuan~ ✨\n\nKihihihi, aku kan selalu ada buat Tuan~ 🎀"
    if any(k in _msg for k in ["bye", "sampai jumpa", "dah"]):
        return "🎀 **Ara, ara~** Udah mau pergi ya, Tuan? 🥺\n\nKihihihi, jangan lama-lama ya~ aku nungguin~ 🎀"
    return "🎀 **Ara, ara~** Maaf Tuan, aku lagi offline nih.\n\nFufufu~ Coba tanya lagi nanti ya~ 🎀"


# =========================================================
# 🎀 PUBLIC API — SUMMARIZE
# =========================================================
def kurumi_summarize(period="hari", custom_date=None, range_start=None, range_end=None):
    _tgl = _now_jkt().date()

    if period == "range" and range_start and range_end:
        _start = range_start
        _end = range_end
        _label = f"{_start.strftime('%d/%m/%Y')} - {_end.strftime('%d/%m/%Y')}"
    elif custom_date:
        _start = custom_date
        _end = custom_date
        _label = f"tanggal {custom_date.strftime('%d/%m/%Y')}"
    elif period == "hari":
        _start = _tgl
        _end = _tgl
        _label = f"hari ini ({_tgl.strftime('%d/%m/%Y')})"
    elif period == "minggu":
        _start = _tgl - timedelta(days=6)
        _end = _tgl
        _label = f"7 hari terakhir ({_start.strftime('%d/%m')} - {_end.strftime('%d/%m/%Y')})"
    elif period == "bulan":
        _start = _tgl.replace(day=1)
        _end = _tgl
        _label = f"bulan ini ({_start.strftime('%d/%m')} - {_end.strftime('%d/%m/%Y')})"
    else:
        _start = _tgl
        _end = _tgl
        _label = "hari ini"

    _ctx = _get_report_context(_start, _end)

    _prompt = f"""{_build_kurumi_system_prompt()}

═══════════════════════════════════════
🎯 TASK: RANGKUM LAPORAN
═══════════════════════════════════════
Periode: {_label}

📅 KONTEKS:
- Tanggal hari ini: {_ctx['tanggal_hari_ini'].isoformat()}

SPD (periode ini):
{_ctx['spd_data']}

STOCK OPNAME (periode ini):
{_ctx['so_data']}

ANALISIS BTSB & NSB:
{_ctx['btsb']}

STATUS RAK:
{_ctx['rak_status']}

═══════════════════════════════════════
📝 INSTRUKSI:
═══════════════════════════════════════
Buat rangkuman eksekutif gaya **Kurumi Tokisaki**:
- Pake "Aku", "Ara ara~" 1x aja
- MAX 8 BARIS
- Struktur:
  * Pembuka singkat (1 baris)
  * SPD & Sales
  * Stock Opname
  * BTSB & NSB Status
  * Status Rak
  * Insight
  * Rekomendasi

⚠️ ATURAN:
- KALAU ADA DATA di atas, PAKE datanya. JANGAN bilang "belum ada data"!
- JANGAN bahas shift (itu tugas Hana).
"""

    _ok, _text, _model, _err = _call_kurumi(_prompt, function="summary", temperature=0.6)
    if _ok and _text:
        return _text.strip()
    return "🎀 **Ara, ara~** Maaf Tuan, aku gagal akses data.\n\nKihihihi~ Coba lagi nanti ya~ 🎀"


# =========================================================
# 🎀 PUBLIC API — GREETING
# =========================================================
def kurumi_greeting():
    _now = _now_jkt()
    _hour = _now.hour
    if 4 <= _hour < 11:
        _waktu = "pagi"
    elif 11 <= _hour < 15:
        _waktu = "siang"
    elif 15 <= _hour < 18:
        _waktu = "sore"
    else:
        _waktu = "malam"

    _prompt = f"""{_build_kurumi_system_prompt()}

TASK: Buat SAPAAN SINGKAT (max 3 baris) untuk Tuan di dashboard.
Waktu sekarang: {_waktu} ({_now.strftime('%H:%M')} WIB)

Gaya: Kurumi hangat + playful. WAJIB pake "Ara ara~".
Pake "Aku". Pake emoji 🎀.
"""

    _ok, _text, _model, _err = _call_kurumi(_prompt, function="greeting")
    if _ok and _text:
        return _text.strip()
    return f"🎀 **Ara, ara~** Selamat {_waktu}, Tuan~ ✨\n\nKihihihi, aku siap bantu hari ini 🎀"


# =========================================================
# 🎀 PUBLIC API — GENERATE REPORT (PATCH 8)
# =========================================================
def kurumi_generate_report(period="hari", format="text", range_start=None, range_end=None):
    _tgl = _now_jkt().date()

    if period == "range" and range_start and range_end:
        _start = range_start
        _end = range_end
        _label = f"{_start.strftime('%d/%m/%Y')} - {_end.strftime('%d/%m/%Y')}"
        _filename_suffix = f"{_start.strftime('%Y%m%d')}_{_end.strftime('%Y%m%d')}"
        _period_type = "hari"
    elif period == "hari":
        _start = _tgl
        _end = _tgl
        _label = f"Harian — {_tgl.strftime('%d/%m/%Y')}"
        _filename_suffix = "hari"
        _period_type = "hari"
    elif period == "minggu":
        _start = _tgl - timedelta(days=6)
        _end = _tgl
        _label = f"Mingguan — {_start.strftime('%d/%m')} s/d {_end.strftime('%d/%m/%Y')}"
        _filename_suffix = "minggu"
        _period_type = "minggu"
    elif period == "bulan":
        _start = _tgl.replace(day=1)
        _end = _tgl
        _label = f"Bulanan — {_tgl.strftime('%B %Y')}"
        _filename_suffix = "bulan"
        _period_type = "bulan"
    else:
        _start = _tgl
        _end = _tgl
        _label = "Harian"
        _filename_suffix = "hari"
        _period_type = "hari"

    _ctx = _get_report_context(_start, _end)

    return _generate_report_worker(
        label=_label,
        start_date=_start,
        end_date=_end,
        format=format,
        filename_suffix=_filename_suffix,
        ctx=_ctx,
        period_type=_period_type,
    )


# =========================================================
# 🎀 PUBLIC API — GENERATE REPORT (CUSTOM DATE)
# =========================================================
def kurumi_generate_report_custom(tanggal, format="text"):
    _tgl = tanggal
    _label = f"Harian — {_tgl.strftime('%d/%m/%Y')}"

    _ctx = _get_report_context(_tgl, _tgl)

    return _generate_report_worker(
        label=_label,
        start_date=_tgl,
        end_date=_tgl,
        format=format,
        filename_suffix=_tgl.strftime('%Y%m%d'),
        ctx=_ctx,
        period_type="hari",
    )


# =========================================================
# 🔧 WORKER — REPORT GENERATOR
# =========================================================
def _generate_report_worker(label, start_date, end_date, format, filename_suffix, ctx, period_type="hari"):
    _now = _now_jkt()

    _prompt = f"""{_build_report_system_prompt()}

═══════════════════════════════════════
🎯 TASK: BUAT LAPORAN FORMAL
═══════════════════════════════════════
Periode: {label}
Tanggal generate: {_now.strftime('%d/%m/%Y %H:%M')} WIB

SPD:
{ctx['spd_data']}

STOCK OPNAME:
{ctx['so_data']}

ANALISIS BTSB & NSB:
{ctx['btsb']}

STATUS RAK:
{ctx['rak_status']}

═══════════════════════════════════════
📝 INSTRUKSI:
═══════════════════════════════════════
Buat laporan dengan struktur:
1. RINGKASAN EKSEKUTIF (3-4 baris)
2. ANALISIS SPD & SALES (1-2 paragraf)
3. ANALISIS BTSB & NSB (1-2 paragraf)
4. INSIGHT & TEMUAN (3-4 bullet)
5. REKOMENDASI (3-4 bullet)

⚠️ JANGAN bikin tabel SO (di-render terpisah).
⚠️ JANGAN bikin daftar rak (udah ada di tabel).
⚠️ FOKUS ke ANALYSIS & INSIGHT.
⚠️ JANGAN NGARANG DATA!
"""

    _ok, _text, _model, _err = _call_kurumi(_prompt, function="report", temperature=0.4)

    if not _ok or not _text:
        return {"success": False, "content": f"Gagal generate: {_err}", "filename": "", "mime": ""}

    _content_text = _text.strip()

    # === TEXT ===
    if format == "text":
        return {
            "success": True,
            "content": _content_text,
            "filename": f"laporan_{filename_suffix}.txt",
            "mime": "text/plain",
        }

    # === PDF ===
    elif format == "pdf":
        try:
            _so_raw = _get_so_raw_data(start_date, end_date)

            return generate_pdf(
                ai_content=_content_text,
                so_data=_so_raw,
                period_label=label,
                period_type=period_type,
                filename=f"laporan_{filename_suffix}.pdf",
            )
        except Exception as _e_pdf:
            import traceback
            print(f"[PDF ERROR] {_e_pdf}")
            print(traceback.format_exc())
            return {"success": False, "content": f"PDF error: {_e_pdf}", "filename": "", "mime": ""}

    # === EXCEL ===
    elif format == "excel":
        try:
            import pandas as pd
            _lines = _content_text.split("\n")
            _rows = [{"No": _i, "Isi Laporan": _l[:32000]} for _i, _l in enumerate(_lines, 1)]
            _df = pd.DataFrame(_rows)

            _output = io.BytesIO()
            with pd.ExcelWriter(_output, engine="xlsxwriter") as _writer:
                _df.to_excel(_writer, sheet_name="Laporan", index=False)
                _wb = _writer.book
                _ws = _writer.sheets["Laporan"]
                _ws.set_column("A:A", 6)
                _wrap = _wb.add_format({"text_wrap": True, "valign": "top"})
                _ws.set_column("B:B", 100, _wrap)

            _excel_bytes = _output.getvalue()
            return {
                "success": True,
                "content": _excel_bytes,
                "filename": f"laporan_{filename_suffix}.xlsx",
                "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        except Exception as _e_xl:
            print(f"[EXCEL ERROR] {_e_xl}")
            return {"success": False, "content": f"Excel error: {_e_xl}", "filename": "", "mime": ""}

    return {"success": False, "content": "Format tidak dikenal", "filename": "", "mime": ""}


# =========================================================
# 🎯 EXPORT
# =========================================================
__all__ = [
    "kurumi_chat_response",
    "kurumi_summarize",
    "kurumi_greeting",
    "kurumi_generate_report",
    "kurumi_generate_report_custom",
]
