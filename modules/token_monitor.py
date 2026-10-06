"""
Token Monitor — Advanced Usage Tracking
========================================
Monitoring token per AI, per fungsi, per model.

Fitur:
- record_usage_v2()      → Catat detail per AI & fungsi
- get_usage_breakdown()  → Breakdown per AI, fungsi, model
- check_quota_warning()  → Warning kalau >80%
- check_auto_pause()     → Auto-pause kalau >90%
- export_usage_csv()     → Export history ke CSV
- render_usage_dashboard() → UI monitoring lengkap + trend chart
"""

import csv
import io
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from modules.ai_config import (
    AI_CONFIG,
    GROQ_LIMITS,
    QUOTA_WARNING_THRESHOLD,
    QUOTA_PAUSE_THRESHOLD,
    get_ai_config,
    get_model_limit,
    get_ai_name_display,
)


# =========================================================
# 🔧 HELPER
# =========================================================
def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def _today_key():
    return _now_jkt().strftime("%Y-%m-%d")


def _ensure_tracker():
    """Pastiin tracker ada di session_state."""
    if "usage_tracker_v2" not in st.session_state:
        st.session_state["usage_tracker_v2"] = {}
    return st.session_state["usage_tracker_v2"]


def _ensure_day_entry(today=None):
    """Pastiin entry hari ini ada."""
    _t = _ensure_tracker()
    _key = today or _today_key()
    if _key not in _t:
        _t[_key] = {
            "ais": {},       # per AI: {ai_name: {requests, in_tok, out_tok, errors, functions}}
            "models": {},    # per model: {model: {requests, in_tok, out_tok}}
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
    """
    Catat usage detail per AI + fungsi + model.

    Args:
        ai_name: "ai-1", "ai-2", dst
        function: "parse", "chat", "suggest", dst
        model: nama model Groq
        prompt_tokens: token input
        output_tokens: token output
        success: True/False
    """
    _day = _ensure_day_entry()

    # === PER AI ===
    if ai_name not in _day["ais"]:
        _day["ais"][ai_name] = {
            "requests": 0, "in_tok": 0, "out_tok": 0, "errors": 0,
            "functions": {},
        }

    _ai = _day["ais"][ai_name]
    if success:
        _ai["requests"] += 1
        _ai["in_tok"] += prompt_tokens
        _ai["out_tok"] += output_tokens
    else:
        _ai["errors"] += 1

    # === PER FUNGSI ===
    if function not in _ai["functions"]:
        _ai["functions"][function] = {
            "requests": 0, "in_tok": 0, "out_tok": 0,
        }
    if success:
        _ai["functions"][function]["requests"] += 1
        _ai["functions"][function]["in_tok"] += prompt_tokens
        _ai["functions"][function]["out_tok"] += output_tokens

    # === PER MODEL ===
    if model:
        if model not in _day["models"]:
            _day["models"][model] = {
                "requests": 0, "in_tok": 0, "out_tok": 0,
            }
        _day["models"][model]["requests"] += 1
        _day["models"][model]["in_tok"] += prompt_tokens
        _day["models"][model]["out_tok"] += output_tokens

    # === TOTAL ===
    _day["total"]["requests"] += 1
    _day["total"]["in_tok"] += prompt_tokens
    _day["total"]["out_tok"] += output_tokens
    if not success:
        _day["total"]["errors"] += 1


# =========================================================
# 📊 GET USAGE
# =========================================================
def get_usage_today():
    """Ambil usage hari ini."""
    return _ensure_day_entry()


def get_usage_by_date(tanggal_str):
    """Ambil usage untuk tanggal tertentu (YYYY-MM-DD)."""
    _t = _ensure_tracker()
    return _t.get(tanggal_str, None)


def get_usage_history(days=7):
    """Ambil history N hari terakhir."""
    _t = _ensure_tracker()
    _today = _now_jkt().date()
    _result = []
    for _i in range(days - 1, -1, -1):
        _d = _today - timedelta(days=_i)
        _key = _d.isoformat()
        _data = _t.get(_key, None)
        _result.append({
            "tanggal": _key,
            "data": _data,
        })
    return _result


def get_ai_usage(ai_name):
    """Ambil usage AI tertentu hari ini."""
    _day = _ensure_day_entry()
    return _day["ais"].get(ai_name, {
        "requests": 0, "in_tok": 0, "out_tok": 0, "errors": 0, "functions": {},
    })


def get_ai_daily_limit(ai_name):
    """Ambil daily limit AI dari config."""
    _cfg = get_ai_config(ai_name)
    return _cfg.get("daily_limit", 1000)


def get_ai_quota_pct(ai_name):
    """Persentase quota AI yang udah kepake."""
    _used = get_ai_usage(ai_name).get("requests", 0)
    _limit = get_ai_daily_limit(ai_name)
    return min(100.0, (_used / _limit * 100) if _limit > 0 else 0)


# =========================================================
# ⚠️ QUOTA CHECK
# =========================================================
def check_quota_warning(ai_name):
    """
    Cek warning quota AI.
    Return: dict {
        "level": "safe" | "warning" | "critical" | "paused",
        "message": str,
        "pct": float,
    }
    """
    _pct = get_ai_quota_pct(ai_name)
    _used = get_ai_usage(ai_name).get("requests", 0)
    _limit = get_ai_daily_limit(ai_name)
    _sisa = max(0, _limit - _used)

    if _pct >= QUOTA_PAUSE_THRESHOLD:
        return {
            "level": "paused",
            "message": f"🚫 QUOTA KRITIS ({_pct:.1f}%). Auto-pause aktif. Sisa {_sisa} req.",
            "pct": _pct,
        }
    elif _pct >= QUOTA_WARNING_THRESHOLD:
        return {
            "level": "warning",
            "message": f"⚠️ Quota hampir habis ({_pct:.1f}%). Sisa {_sisa} req.",
            "pct": _pct,
        }
    elif _pct >= 50:
        return {
            "level": "moderate",
            "message": f"ℹ️ Quota setengah terpakai ({_pct:.1f}%). Sisa {_sisa} req.",
            "pct": _pct,
        }
    return {
        "level": "safe",
        "message": f"✅ Quota aman ({_pct:.1f}%). Sisa {_sisa} req.",
        "pct": _pct,
    }


def check_auto_pause(ai_name):
    """
    Cek apakah AI harus di-pause (fallback ke rule-based).
    Return: bool
    """
    _pct = get_ai_quota_pct(ai_name)
    return _pct >= QUOTA_PAUSE_THRESHOLD


# =========================================================
# 📤 EXPORT CSV
# =========================================================
def export_usage_csv(days=30):
    """
    Export usage history ke CSV.
    Return: bytes (siap download)
    """
    _t = _ensure_tracker()
    _today = _now_jkt().date()

    _rows = []
    for _i in range(days - 1, -1, -1):
        _d = _today - timedelta(days=_i)
        _key = _d.isoformat()
        _data = _t.get(_key, None)

        if not _data:
            _rows.append({
                "tanggal": _key,
                "ai": "-", "function": "-", "model": "-",
                "requests": 0, "input_tokens": 0, "output_tokens": 0, "errors": 0,
            })
            continue

        for _ai_name, _ai_data in _data["ais"].items():
            for _fn_name, _fn_data in _ai_data.get("functions", {}).items():
                _rows.append({
                    "tanggal": _key,
                    "ai": _ai_name,
                    "function": _fn_name,
                    "model": "-",
                    "requests": _fn_data.get("requests", 0),
                    "input_tokens": _fn_data.get("in_tok", 0),
                    "output_tokens": _fn_data.get("out_tok", 0),
                    "errors": 0,
                })

    # Build CSV
    _output = io.StringIO()
    _writer = csv.DictWriter(_output, fieldnames=[
        "tanggal", "ai", "function", "model",
        "requests", "input_tokens", "output_tokens", "errors",
    ])
    _writer.writeheader()
    _writer.writerows(_rows)

    return _output.getvalue().encode("utf-8")


# =========================================================
# 🎨 RENDER DASHBOARD
# =========================================================
def render_usage_dashboard():
    """Render dashboard monitoring token lengkap."""
    st.markdown("### 📊 Token Monitor")

    _day = get_usage_today()
    _total = _day["total"]

    # ============================================
    # OVERVIEW
    # ============================================
    _col1, _col2, _col3, _col4 = st.columns(4)
    with _col1:
        st.metric("📤 Total Requests", _total["requests"])
    with _col2:
        st.metric("📥 Input Tokens", f"{_total['in_tok']:,}".replace(",", "."))
    with _col3:
        st.metric("📤 Output Tokens", f"{_total['out_tok']:,}".replace(",", "."))
    with _col4:
        st.metric("❌ Errors", _total["errors"])

    st.markdown("---")

    # ============================================
    # PER AI BREAKDOWN
    # ============================================
    st.markdown("#### 🤖 Per AI")

    _enabled_ais = [k for k in AI_CONFIG.keys()]
    _has_data = False

    for _ai_name in _enabled_ais:
        _cfg = get_ai_config(_ai_name)
        if not _cfg.get("enabled", False) and _ai_name not in _day["ais"]:
            continue

        _has_data = True
        _usage = get_ai_usage(_ai_name)
        _pct = get_ai_quota_pct(_ai_name)
        _warning = check_quota_warning(_ai_name)
        _display = get_ai_name_display(_ai_name)

        with st.expander(f"{_display} — {_pct:.1f}% quota", expanded=True):
            _c1, _c2, _c3, _c4 = st.columns(4)
            with _c1:
                st.metric("Requests", f"{_usage['requests']} / {get_ai_daily_limit(_ai_name)}")
            with _c2:
                st.metric("Input Tokens", f"{_usage['in_tok']:,}".replace(",", "."))
            with _c3:
                st.metric("Output Tokens", f"{_usage['out_tok']:,}".replace(",", "."))
            with _c4:
                st.metric("Errors", _usage["errors"])

            # Progress bar
            st.progress(min(1.0, _pct / 100))

            # Status
            _level = _warning["level"]
            _msg = _warning["message"]
            if _level == "paused":
                st.error(_msg)
            elif _level == "warning":
                st.warning(_msg)
            elif _level == "moderate":
                st.info(_msg)
            else:
                st.success(_msg)

            # Breakdown per fungsi
            _fns = _usage.get("functions", {})
            if _fns:
                st.markdown("**📋 Breakdown per Fungsi:**")
                for _fn, _data in _fns.items():
                    st.write(
                        f"- `{_fn}`: {_data['requests']} req, "
                        f"{_data['in_tok']} in, {_data['out_tok']} out"
                    )

    if not _has_data:
        st.info("📭 Belum ada data usage hari ini.")

    st.markdown("---")

    # ============================================
    # PER MODEL BREAKDOWN
    # ============================================
    st.markdown("#### 🤖 Per Model")

    if _day["models"]:
        for _model, _data in _day["models"].items():
            _limit = get_model_limit(_model)
            _pct_model = min(100.0, (_data["requests"] / _limit["rpd"] * 100) if _limit["rpd"] > 0 else 0)
            st.write(
                f"**`{_model}`** — {_data['requests']} req "
                f"({_pct_model:.1f}% dari {_limit['rpd']})"
            )
    else:
        st.info("📭 Belum ada data model hari ini.")

    st.markdown("---")

    # ============================================
    # TREND 7 HARI (CHART)
    # ============================================
    st.markdown("#### 📈 Trend 7 Hari Terakhir")

    _history = get_usage_history(days=7)
    _dates = []
    _reqs = []
    _errors = []

    _history = get_usage_history(days=7)
    _dates = []
    _reqs = []
    _err_counts = []   # ✅ GANTI NAMA
    
    for _h in _history:
        _tgl = _h["tanggal"]
        _dt = _h["data"]
        _dates.append(_tgl[5:])
        if _dt:
            _reqs.append(_dt["total"]["requests"])
            _err_counts.append(_dt["total"]["errors"])
        else:
            _reqs.append(0)
            _err_counts.append(0)
    
    try:
        import plotly.graph_objects as go
    
        _fig = go.Figure()
        _fig.add_trace(go.Bar(
            x=_dates, y=_reqs,
            name="Requests",
            marker_color="#7FB99B",
            text=_reqs,
            textposition="outside",
        ))
        _fig.add_trace(go.Bar(
            x=_dates, y=_err_counts,   # ✅ PAKE NAMA BARU
            name="Errors",
            marker_color="#E88B8B",
            text=_err_counts,
            textposition="outside",
        ))
        _fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=10, r=10, t=30, b=30),
        plot_bgcolor="rgba(10, 22, 18, 0.4)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E8B189", family="JetBrains Mono", size=10),
        xaxis=dict(
            gridcolor="rgba(232, 177, 137, 0.15)",
            type="category",       # ✅ Paksa kategori (biar gak auto-scale)
            tickmode="array",
            tickvals=_dates,
            ticktext=_dates,
        ),
        yaxis=dict(
            gridcolor="rgba(232, 177, 137, 0.15)",
            rangemode="tozero",     # ✅ Mulai dari 0
            dtick=1,                # ✅ Step 1 (biar integer)
        ),
        legend=dict(font=dict(color="#E8B189")),
    )

    st.markdown("---")

    # ============================================
    # RESET INFO
    # ============================================
    _now = _now_jkt()
    _tomorrow_7 = (_now + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
    _delta = _tomorrow_7 - _now
    _hours = int(_delta.total_seconds() // 3600)
    _mins = int((_delta.total_seconds() % 3600) // 60)

    st.info(f"⏰ **Reset quota dalam:** {_hours} jam {_mins} menit (07:00 WIB besok)")

    st.markdown("---")

    # ============================================
    # EXPORT CSV
    # ============================================
    st.markdown("#### 📥 Export Usage")
    _csv_bytes = export_usage_csv(days=30)

    st.download_button(
        label="📥 Download Usage (CSV, 30 hari)",
        data=_csv_bytes,
        file_name=f"usage_{_today_key()}.csv",
        mime="text/csv",
        use_container_width=True,
        key="btn_export_usage_csv",
    )
