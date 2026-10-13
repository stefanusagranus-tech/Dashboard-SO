"""
Token Monitor — Advanced Usage Tracking v2 (Backend Edition)
==============================================================
Monitoring token per AI, per fungsi, per model.

Changelog v2:
- Hapus dependency streamlit (st.session_state → in-memory global dict)
- Hapus render_usage_dashboard() — UI dipindah ke Streamlit page
- Cocok buat FastAPI backend

Fitur:
- record_usage_v2()      → Catat detail per AI & fungsi
- get_usage_breakdown()  → Breakdown per AI, fungsi, model
- check_quota_warning()  → Warning kalau >80%
- check_auto_pause()     → Auto-pause kalau >90%
- export_usage_csv()     → Export history ke CSV
"""

import csv
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.ai_config import (
    AI_CONFIG,
    GROQ_LIMITS,
    QUOTA_WARNING_THRESHOLD,
    QUOTA_PAUSE_THRESHOLD,
    get_ai_config,
    get_model_limit,
    get_ai_name_display,
)


# =========================================================
# 🌐 GLOBAL STORAGE (pengganti st.session_state)
# =========================================================
_USAGE_TRACKER = {}


# =========================================================
# 🔧 HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _today_key():
    return _now_jkt().strftime("%Y-%m-%d")


def _ensure_tracker():
    global _USAGE_TRACKER
    return _USAGE_TRACKER


def _ensure_day_entry(today=None):
    _t = _ensure_tracker()
    _key = today or _today_key()
    if _key not in _t:
        _t[_key] = {
            "ais": {},
            "models": {},
            "total": {"requests": 0, "in_tok": 0, "out_tok": 0, "errors": 0},
        }
    return _t[_key]
    
# =========================================================
# 📝 RECORD USAGE
# =========================================================
def record_usage_v2(
    ai_name: str,
    function: str,
    model: str,
    prompt_tokens: int = 0,
    output_tokens: int = 0,
    success: bool = True,
):
    """Catat usage detail per AI + fungsi + model."""
    _day = _ensure_day_entry()

    # Per AI
    if ai_name not in _day["ais"]:
        _day["ais"][ai_name] = {
            "requests": 0, "in_tok": 0, "out_tok": 0, "errors": 0, "functions": {},
        }
    _ai = _day["ais"][ai_name]
    if success:
        _ai["requests"] += 1
        _ai["in_tok"] += prompt_tokens
        _ai["out_tok"] += output_tokens
    else:
        _ai["errors"] += 1

    # Per fungsi
    if function not in _ai["functions"]:
        _ai["functions"][function] = {"requests": 0, "in_tok": 0, "out_tok": 0}
    if success:
        _ai["functions"][function]["requests"] += 1
        _ai["functions"][function]["in_tok"] += prompt_tokens
        _ai["functions"][function]["out_tok"] += output_tokens

    # Per model
    if model:
        if model not in _day["models"]:
            _day["models"][model] = {"requests": 0, "in_tok": 0, "out_tok": 0}
        _day["models"][model]["requests"] += 1
        _day["models"][model]["in_tok"] += prompt_tokens
        _day["models"][model]["out_tok"] += output_tokens

    # Total
    _day["total"]["requests"] += 1
    _day["total"]["in_tok"] += prompt_tokens
    _day["total"]["out_tok"] += output_tokens
    if not success:
        _day["total"]["errors"] += 1

# =========================================================
# 📊 GET USAGE
# =========================================================
def get_usage_today():
    return _ensure_day_entry()


def get_usage_by_date(tanggal_str):
    _t = _ensure_tracker()
    return _t.get(tanggal_str, None)


def get_usage_history(days=7):
    _t = _ensure_tracker()
    _today = _now_jkt().date()
    _result = []
    for _i in range(days - 1, -1, -1):
        _d = _today - timedelta(days=_i)
        _key = _d.isoformat()
        _result.append({"tanggal": _key, "data": _t.get(_key, None)})
    return _result


def get_ai_usage(ai_name):
    _day = _ensure_day_entry()
    return _day["ais"].get(ai_name, {
        "requests": 0, "in_tok": 0, "out_tok": 0, "errors": 0, "functions": {},
    })


def get_ai_daily_limit(ai_name):
    _cfg = get_ai_config(ai_name)
    return _cfg.get("daily_limit", 1000)


def get_ai_quota_pct(ai_name):
    _used = get_ai_usage(ai_name).get("requests", 0)
    _limit = get_ai_daily_limit(ai_name)
    return min(100.0, (_used / _limit * 100) if _limit > 0 else 0)


# =========================================================
# ⚠️ QUOTA CHECK
# =========================================================
def check_quota_warning(ai_name):
    _pct = get_ai_quota_pct(ai_name)
    _used = get_ai_usage(ai_name).get("requests", 0)
    _limit = get_ai_daily_limit(ai_name)
    _sisa = max(0, _limit - _used)

    if _pct >= QUOTA_PAUSE_THRESHOLD:
        return {"level": "paused", "message": f"🚫 QUOTA KRITIS ({_pct:.1f}%). Auto-pause. Sisa {_sisa} req.", "pct": _pct}
    elif _pct >= QUOTA_WARNING_THRESHOLD:
        return {"level": "warning", "message": f"⚠️ Quota hampir habis ({_pct:.1f}%). Sisa {_sisa} req.", "pct": _pct}
    elif _pct >= 50:
        return {"level": "moderate", "message": f"ℹ️ Quota setengah ({_pct:.1f}%). Sisa {_sisa} req.", "pct": _pct}
    return {"level": "safe", "message": f"✅ Quota aman ({_pct:.1f}%). Sisa {_sisa} req.", "pct": _pct}


def check_auto_pause(ai_name):
    return get_ai_quota_pct(ai_name) >= QUOTA_PAUSE_THRESHOLD

# =========================================================
# 📤 EXPORT CSV
# =========================================================
def export_usage_csv(days=30):
    _t = _ensure_tracker()
    _today = _now_jkt().date()

    _rows = []
    for _i in range(days - 1, -1, -1):
        _d = _today - timedelta(days=_i)
        _key = _d.isoformat()
        _data = _t.get(_key, None)

        if not _data:
            _rows.append({
                "tanggal": _key, "ai": "-", "function": "-", "model": "-",
                "requests": 0, "input_tokens": 0, "output_tokens": 0, "errors": 0,
            })
            continue

        for _ai_name, _ai_data in _data["ais"].items():
            for _fn_name, _fn_data in _ai_data.get("functions", {}).items():
                _rows.append({
                    "tanggal": _key, "ai": _ai_name, "function": _fn_name, "model": "-",
                    "requests": _fn_data.get("requests", 0),
                    "input_tokens": _fn_data.get("in_tok", 0),
                    "output_tokens": _fn_data.get("out_tok", 0),
                    "errors": 0,
                })

    _output = io.StringIO()
    _writer = csv.DictWriter(_output, fieldnames=[
        "tanggal", "ai", "function", "model",
        "requests", "input_tokens", "output_tokens", "errors",
    ])
    _writer.writeheader()
    _writer.writerows(_rows)

    return _output.getvalue().encode("utf-8")


# =========================================================
# 📊 GET ALL USAGE (buat Streamlit dashboard)
# =========================================================
def get_all_usage_data():
    """
    Return semua data usage tracker.
    Dipake Streamlit page buat render dashboard.
    """
    return _ensure_tracker()

# =========================================================
# EXPORT
# =========================================================
__all__ = [
    "record_usage_v2",
    "get_usage_today",
    "get_usage_by_date",
    "get_usage_history",
    "get_ai_usage",
    "get_ai_daily_limit",
    "get_ai_quota_pct",
    "check_quota_warning",
    "check_auto_pause",
    "export_usage_csv",
    "get_all_usage_data",
]