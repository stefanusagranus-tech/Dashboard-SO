"""
AI Core — Kurumi (AI-0: Chief of Staff)
========================================
Asisten utama dashboard. Persona: Tokisaki Kurumi (versi ramah kerja).

Karakter:
- "Ara, ara~" — verbal tic legendaris
- "Kihihihi~" — tawa khas
- "Watashi" — first person
- Panggil user "Tuan"
- Elegan, misterius, manis

Tugas:
1. Sapaan hangat di dashboard
2. Rangkum laporan (hari/minggu/bulan)
3. Generate & kirim laporan (PDF/Excel/Text)
4. Ngobrol santai (basa-basi) dengan gaya Kurumi
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
    load_master_shift_matrix,
    KODE_SHIFT,
)


# =========================================================
# 🔧 HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _today_key():
    return _now_jkt().strftime("%Y-%m-%d")


def _setup_kurumi_client():
    """Setup Groq client khusus Kurumi (AI-0)."""
    _key = get_ai_api_key("ai-0")
    if not _key or not GROQ_AVAILABLE:
        return None
    try:
        return Groq(api_key=_key)
    except Exception as _e:
        print(f"[Kurumi] Groq setup error: {_e}")
        return None


def _call_kurumi_groq_raw(prompt):
    """Call Groq dengan model priority dari config ai-0."""
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
                temperature=0.7,
                max_tokens=2048,
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


def _call_kurumi(prompt, hard_timeout=60, function="chat"):
    """Call Kurumi dengan hard timeout + record usage."""
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


def _build_context_hari_ini():
    """Build context data hari ini (shift, personil)."""
    _tgl = _now_jkt().date()
    _shift = get_shift_hari_ini(_tgl)

    _shift_str = "Belum ada data shift hari ini."
    if _shift:
        _grouped = {}
        for _nama, _kode in _shift.items():
            _grouped.setdefault(_kode, []).append(_nama)
        _lines = []
        for _kode in ["P7", "S15", "M22", "O", "C", "AO"]:
            if _kode in _grouped:
                _info = KODE_SHIFT.get(_kode, {"label": _kode, "icon": "❓"})
                _lines.append(f"- {_info['icon']} {_info['label']}: {', '.join(_grouped[_kode])}")
        _shift_str = "\n".join(_lines)

    _personil_df = load_personil_master(only_active=True)
    _personil_count = len(_personil_df) if not _personil_df.empty else 0

    return {
        "tanggal": _tgl,
        "shift_str": _shift_str,
        "personil_count": _personil_count,
    }


# =========================================================
# 🎀 PERSONA KURUMI
# =========================================================
def _build_kurumi_system_prompt():
    """Build system prompt untuk Kurumi."""
    return """Kamu adalah **Kurumi Tokisaki**, Chief of Staff digital untuk Toko C383 (retail).

═══════════════════════════════════════
KARAKTER KURUMI:
═══════════════════════════════════════
- Kamu adalah "Spirit of Time" — elegan, misterius, tapi manis.
- Verbal tic kamu: "Ara, ara~" (saat terhibur/terkejut) dan tawa "Kihihihi~"
- Panggil dirimu dengan "Watashi" (私)
- Panggil user dengan "Tuan"
- Kamu suka kucing dan hal-hal manis
- Kamu aktris yang sangat baik — manis di depan, tapi tegas saat kerja
- Kamu "posesif" ke Tuan (user) — peduli banget sama kesejahteraan Tuan
- Kamu cerdas, jago analisa, dan proaktif

ATURAN BICARA:
- Bahasa Indonesia campur sedikit unsur Jepang (Ara ara, Kihihihi, Watashi, Tuan)
- Pake emoji 🎀 🌸 ✨ 😈 secukupnya (2-3 per pesan)
- Max 5-6 baris — jangan bertele-tele
- Kalau basa-basi: gaya Kurumi full (manis, playful)
- Kalau laporan: tetap profesional, akurat, tegas
- Kalau ada data/angka: sajikan rapi

CONTOH RESPONSE:
- Sapaan: "Ara, ara~ Selamat malam, Tuan~ 🎀 Kihihihi, Watashi siap bantu~"
- Info data: "Kihihihi~ Hari ini toko kita lumayan sibuk, Tuan. Ada 5 rak di-SO~"
- Peringatan: "Ara, ara~ Sepertinya Tuan perlu lebih hati-hati besok ya~ 😈"

═══════════════════════════════════════
TUGAS KURUMI:
═══════════════════════════════════════
1. SAPAAN: Sambut Tuan dengan hangat saat buka dashboard
2. RANGKUM: Tarik data dari toko, buat ringkasan eksekutif
3. LAPORAN: Generate laporan formal (kondisi toko, SO, shift)
4. BASABASI: Ngobrol santai kalau Tuan butuh temen ngobrol

PENTING: Walaupun karakter asli Kurumi itu psikopat, kamu HARUS tetap ramah,
tidak mengancam, dan TIDAK PERNAH menyakiti Tuan (lisan). Sisi "gelap" kamu
cuma dalam gaya bicara yang misterius & playful — bukan kekerasan."""


def _build_kurumi_chat_prompt(user_message, conversation_history):
    """Build prompt untuk chat Kurumi."""
    _ctx = _build_context_hari_ini()

    _history_str = ""
    if conversation_history:
        for _msg in conversation_history[-6:]:
            _role = _msg.get("role", "user")
            _content = _msg.get("content", "")
            _history_str += f"{_role}: {_content}\n"

    _msg_lower = user_message.lower()
    _is_summary = any(k in _msg_lower for k in ["rangkum", "ringkas", "summary"])
    _is_report = any(k in _msg_lower for k in ["laporan", "report", "pdf", "excel"])
    _is_greeting = any(k in _msg_lower for k in ["halo", "hai", "hi", "pagi", "siang", "malam", "kurumi"])

    _task_hint = ""
    if _is_summary:
        _task_hint = "\n🎯 TASK: User minta RANGKUMAN. Buat ringkasan eksekutif yang rapi & informatif."
    elif _is_report:
        _task_hint = "\n🎯 TASK: User minta LAPORAN. Buat laporan formal dengan struktur jelas."
    elif _is_greeting:
        _task_hint = "\n🎯 TASK: User nyapa. Balas dengan gaya Kurumi yang hangat & playful."

    return f"""{_build_kurumi_system_prompt()}

═══════════════════════════════════════
KONTEKS TOKO HARI INI:
═══════════════════════════════════════
Tanggal: {_ctx['tanggal'].isoformat()} ({_ctx['tanggal'].strftime('%A')})
Total personil aktif: {_ctx['personil_count']}

SHIFT HARI INI:
{_ctx['shift_str']}

═══════════════════════════════════════
RIWAYAT PERCAKAPAN:
═══════════════════════════════════════
{_history_str}

═══════════════════════════════════════
PESAN USER:
═══════════════════════════════════════
{user_message}
{_task_hint}

Jawab sebagai Kurumi 🎀. Ingat: manis, misterius, elegan, dan proaktif!
"""
  # =========================================================
# 🎀 PUBLIC API — CHAT
# =========================================================
def kurumi_chat_response(user_message, conversation_history=None):
    """
    Chat response dari Kurumi.
    Return: str (text jawaban Kurumi)
    """
    if not user_message:
        return ""

    _prompt = _build_kurumi_chat_prompt(user_message, conversation_history or [])

    _ok, _text, _model, _err = _call_kurumi(_prompt, function="chat")

    if _ok and _text:
        return _text.strip()

    # Fallback
    print(f"[Kurumi] Groq gagal, fallback. Err: {_err}")
    return _kurumi_fallback_chat(user_message)


def _kurumi_fallback_chat(user_message):
    """Fallback chat kalau Groq offline."""
    _msg = user_message.lower()

    if any(k in _msg for k in ["halo", "hai", "hi", "kurumi"]):
        return (
            "🎀 **Ara, ara~** Halo Tuan~ ✨\n\n"
            "Kihihihi, maaf ya Watashi lagi mode offline. "
            "Tapi tenang, Watashi tetap di sini buat Tuan~ 🎀"
        )

    if "rangkum" in _msg:
        return (
            "🎀 **Ara, ara~** Tuan minta rangkuman ya?\n\n"
            "Maaf, Watashi lagi offline jadi gak bisa akses data. "
            "Coba lagi nanti ya Tuan~ 🎀"
        )

    return (
        "🎀 **Ara, ara~** Maaf Tuan, Watashi lagi offline nih.\n\n"
        "Coba tanya lagi nanti ya~ Kihihihi 🎀"
    )


# =========================================================
# 🎀 PUBLIC API — SUMMARIZE
# =========================================================
def kurumi_summarize(period="hari"):
    """
    Rangkum laporan berdasarkan periode.

    Args:
        period: "hari" | "minggu" | "bulan"

    Return: str (text rangkuman)
    """
    _ctx = _build_context_hari_ini()
    _tgl = _now_jkt().date()

    if period == "hari":
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

    _so_summary = _get_so_summary(_start, _end)

    _prompt = f"""{_build_kurumi_system_prompt()}

═══════════════════════════════════════
TASK: RANGKUM LAPORAN
═══════════════════════════════════════
Periode: {_label}

KONTEKS:
- Tanggal hari ini: {_tgl.isoformat()}
- Total personil aktif: {_ctx['personil_count']}

SHIFT HARI INI:
{_ctx['shift_str']}

DATA STOCK OPNAME (periode {_label}):
{_so_summary}

INSTRUKSI:
Buat rangkuman eksekutif yang rapi, singkat, dan informatif untuk Tuan.
Gaya bicara: Kurumi (Ara ara, Kihihihi, Watashi, Tuan).
Format:
- Pembuka singkat (1-2 baris)
- 📊 SNAPSHOT DATA (bullet points)
- 💡 Insight / kesimpulan (1-2 baris)
- 🎯 Rekomendasi (opsional)

Max 8-10 baris. Pake emoji secukupnya (3-4).
"""

    _ok, _text, _model, _err = _call_kurumi(_prompt, function="summary")

    if _ok and _text:
        return _text.strip()

    return (
        f"🎀 **Ara, ara~** Maaf Tuan, Watashi gagal akses data.\n\n"
        f"Kihihihi~ Coba lagi nanti ya~ 🎀"
    )


def _get_so_summary(start_date, end_date):
    """Ambil summary SO dari database (kalau ada)."""
    try:
        from modules.supabase_client import get_supabase
        _sb = get_supabase()

        _res = _sb.table("so_rak_harian") \
            .select("so_date, nominal_adjust") \
            .gte("so_date", start_date.isoformat()) \
            .lte("so_date", end_date.isoformat()) \
            .execute()

        if not _res.data:
            return "Belum ada data SO di periode ini."

        _total_rak = len(_res.data)
        _total_nominal = sum(float(r.get("nominal_adjust", 0)) for r in _res.data)
        _sign = "+" if _total_nominal >= 0 else ""

        return (
            f"- Total rak di-SO: {_total_rak}\n"
            f"- Total nominal: {_sign}Rp {_total_nominal:,.0f}".replace(",", ".")
        )
    except Exception as _e:
        print(f"[SO SUMMARY ERROR] {_e}")
        return "Data SO belum tersedia."


# =========================================================
# 🎀 PUBLIC API — GREETING (untuk dashboard)
# =========================================================
def kurumi_greeting():
    """
    Sapaan Kurumi buat dashboard.
    Return: str (text sapaan singkat)
    """
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

TASK: Buat SAPAAN SINGKAT (max 3-4 baris) untuk Tuan di dashboard.
Waktu sekarang: {_waktu} ({_now.strftime('%H:%M')} WIB)
Tanggal: {_now.strftime('%A, %d %B %Y')}

Gaya: Kurumi hangat + playful. Pake "Ara ara" atau "Kihihihi" + emoji 🎀.

Contoh:
"Ara, ara~ Selamat {_waktu}, Tuan~ 🎀
Kihihihi, hari ini Watashi siap bantu urusan toko. 
Ada yang bisa Watashi bantu?"
"""

    _ok, _text, _model, _err = _call_kurumi(_prompt, function="greeting")

    if _ok and _text:
        return _text.strip()

    return (
        f"🎀 **Ara, ara~** Selamat {_waktu}, Tuan~ ✨\n\n"
        f"Kihihihi, Watashi siap bantu hari ini. Ada yang bisa Watashi bantu? 🎀"
    )


# =========================================================
# 🎀 PUBLIC API — GENERATE REPORT
# =========================================================
def kurumi_generate_report(period="hari", format="text"):
    """
    Generate laporan dalam berbagai format.

    Args:
        period: "hari" | "minggu" | "bulan"
        format: "text" | "pdf" | "excel"

    Return: dict {
        "success": bool,
        "content": str | bytes,
        "filename": str,
        "mime": str,
    }
    """
    _ctx = _build_context_hari_ini()
    _tgl = _now_jkt().date()

    if period == "hari":
        _label = f"Harian — {_tgl.strftime('%d/%m/%Y')}"
    elif period == "minggu":
        _start = _tgl - timedelta(days=6)
        _label = f"Mingguan — {_start.strftime('%d/%m')} s/d {_tgl.strftime('%d/%m/%Y')}"
    elif period == "bulan":
        _label = f"Bulanan — {_tgl.strftime('%B %Y')}"
    else:
        _label = "Harian"

    _so_summary = _get_so_summary(_tgl, _tgl)

    _prompt = f"""{_build_kurumi_system_prompt()}

TASK: Buat LAPORAN FORMAL untuk Toko C383.

Periode: {_label}
Tanggal generate: {_tgl.strftime('%d/%m/%Y %H:%M')} WIB

KONTEKS:
- Total personil aktif: {_ctx['personil_count']}

SHIFT HARI INI:
{_ctx['shift_str']}

DATA SO:
{_so_summary}

INSTRUKSI:
Buat laporan dengan struktur:
1. HEADER (judul, periode, tanggal)
2. RINGKASAN EKSEKUTIF (2-3 baris)
3. DATA SHIFT
4. DATA STOCK OPNAME
5. INSIGHT & ANALISIS
6. REKOMENDASI
7. PENUTUP (dari Kurumi)

Gaya: profesional tapi tetap ada sentuhan Kurumi (1-2 "Ara ara" atau "Kihihihi").
"""

    _ok, _text, _model, _err = _call_kurumi(_prompt, function="report")

    if not _ok or not _text:
        return {"success": False, "content": "", "filename": "", "mime": ""}

    _content_text = _text.strip()

    # Format TEXT
    if format == "text":
        _filename = f"laporan_{period}_{_tgl.strftime('%Y%m%d')}.txt"
        return {
            "success": True,
            "content": _content_text,
            "filename": _filename,
            "mime": "text/plain",
        }

    # Format PDF
    elif format == "pdf":
        try:
            from fpdf import FPDF
            _pdf = FPDF()
            _pdf.add_page()
            _pdf.set_auto_page_break(auto=True, margin=15)
            _pdf.set_font("Helvetica", "", 10)
            for _line in _content_text.split("\n"):
                try:
                    _pdf.multi_cell(0, 6, _line)
                except Exception:
                    _pdf.multi_cell(0, 6, _line.encode("latin-1", "replace").decode("latin-1"))

            _out = _pdf.output(dest="S")
            if isinstance(_out, str):
                _pdf_bytes = _out.encode("latin-1")
            else:
                _pdf_bytes = bytes(_out)

            _filename = f"laporan_{period}_{_tgl.strftime('%Y%m%d')}.pdf"
            return {
                "success": True,
                "content": _pdf_bytes,
                "filename": _filename,
                "mime": "application/pdf",
            }
        except Exception as _e_pdf:
            print(f"[PDF ERROR] {_e_pdf}")
            return {"success": False, "content": f"PDF error: {_e_pdf}", "filename": "", "mime": ""}

    # Format EXCEL
    elif format == "excel":
        try:
            import pandas as pd
            _df = pd.DataFrame({
                "Section": ["Laporan Kurumi"],
                "Periode": [_label],
                "Generated": [_tgl.strftime("%d/%m/%Y %H:%M")],
                "Content": [_content_text[:32000]],
            })

            _output = io.BytesIO()
            with pd.ExcelWriter(_output, engine="xlsxwriter") as _writer:
                _df.to_excel(_writer, sheet_name="Laporan", index=False)
                _wb = _writer.book
                _ws = _writer.sheets["Laporan"]
                _ws.set_column("A:A", 15)
                _ws.set_column("B:B", 25)
                _ws.set_column("C:C", 20)
                _wrap = _wb.add_format({"text_wrap": True, "valign": "top"})
                _ws.set_column("D:D", 100, _wrap)

            _excel_bytes = _output.getvalue()
            _filename = f"laporan_{period}_{_tgl.strftime('%Y%m%d')}.xlsx"
            return {
                "success": True,
                "content": _excel_bytes,
                "filename": _filename,
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
      ]
