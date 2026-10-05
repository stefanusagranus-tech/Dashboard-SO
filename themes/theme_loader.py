"""
Theme Loader v2
==============
Loader multi-tema + auto-time variant.

Fitur:
- Load tema by name (halloween, default, dll)
- Auto-pick variant by time (pagi/siang/sore/malam/midnight)
- Render greeting by time
- Debug info
"""

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# 🎨 AVAILABLE THEMES
# =========================================================
AVAILABLE_THEMES = {
    "halloween": "🎃 Halloween",
    "default": "⚜️ Default (Emerald)",
    "christmas": "🎄 Christmas",
    "lebaran": "🌙 Lebaran",
    "newyear": "🎆 New Year",
    "ramadan": "🌙 Ramadan",
}


# =========================================================
# ⏰ TIME VARIANTS
# =========================================================
TIME_VARIANTS = {
    "pagi": {
        "start_hour": 4,
        "end_hour": 10,
        "emoji": "🌅",
        "greeting": "Selamat Pagi",
    },
    "siang": {
        "start_hour": 10,
        "end_hour": 15,
        "emoji": "☀️",
        "greeting": "Selamat Siang",
    },
    "sore": {
        "start_hour": 15,
        "end_hour": 18,
        "emoji": "🌇",
        "greeting": "Selamat Sore",
    },
    "malam": {
        "start_hour": 18,
        "end_hour": 22,
        "emoji": "🌆",
        "greeting": "Selamat Malam",
    },
    "midnight": {
        "start_hour": 22,
        "end_hour": 4,
        "emoji": "🌙",
        "greeting": "Selamat Tidur",
    },
}


def get_current_time_variant():
    """
    Detect current time variant.
    Return: 'pagi', 'siang', 'sore', 'malam', 'midnight'
    """
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _hour = _now.hour
    
    for _variant, _info in TIME_VARIANTS.items():
        _start = _info["start_hour"]
        _end = _info["end_hour"]
        
        # Handle midnight (22-04 — wrap around)
        if _start > _end:
            if _hour >= _start or _hour < _end:
                return _variant
        else:
            if _start <= _hour < _end:
                return _variant
    
    return "malam"  # fallback


def get_greeting():
    """
    Return greeting text by time.
    Contoh: "Selamat Malam 🌆"
    """
    _variant = get_current_time_variant()
    _info = TIME_VARIANTS.get(_variant, TIME_VARIANTS["malam"])
    return f"{_info['greeting']} {_info['emoji']}"


def get_time_emoji():
    """Return emoji waktu sekarang."""
    _variant = get_current_time_variant()
    return TIME_VARIANTS.get(_variant, {}).get("emoji", "🎃")


# =========================================================
# 🎯 LOAD THEME
# =========================================================
def load_theme(theme_name="halloween"):
    """
    Load theme by name. Return CSS string.
    """
    try:
        if theme_name == "halloween":
            from themes import halloween as theme
        elif theme_name == "default":
            from themes import default as theme
        elif theme_name == "christmas":
            from themes import christmas as theme
        elif theme_name == "lebaran":
            from themes import lebaran as theme
        elif theme_name == "newyear":
            from themes import newyear as theme
        elif theme_name == "ramadan":
            from themes import ramadan as theme
        else:
            from themes import halloween as theme
        
        # Try get_css with variant (v2)
        _variant = get_current_time_variant()
        try:
            return theme.get_css(variant=_variant)
        except TypeError:
            # Fallback: get_css without variant (v1)
            return theme.get_css()
    
    except ImportError as e:
        print(f"[THEME LOAD ERROR] {e}")
        return ""
    except Exception as e:
        print(f"[THEME ERROR] {e}")
        return ""


def get_theme_info(theme_name="halloween"):
    """Get theme metadata."""
    try:
        if theme_name == "halloween":
            from themes import halloween as theme
            return theme.THEME_INFO
        elif theme_name == "default":
            from themes import default as theme
            return theme.THEME_INFO
        else:
            from themes import halloween as theme
            return theme.THEME_INFO
    except Exception:
        return {"name": "Unknown", "emoji": "❓"}


def render_theme(theme_name="halloween"):
    """
    Render CSS ke Streamlit.
    Auto-pick variant by time.
    """
    _css = load_theme(theme_name)
    if _css:
        st.markdown(_css, unsafe_allow_html=True)
    return _css


# =========================================================
# 🎯 AUTO THEME BY MONTH
# =========================================================
def get_theme_by_month():
    """Auto-pick theme by month."""
    _month = datetime.now(ZoneInfo("Asia/Jakarta")).month
    
    _theme_map = {
        1: "newyear",
        2: "default",
        3: "default",
        4: "lebaran",
        5: "lebaran",
        6: "default",
        7: "default",
        8: "default",
        9: "default",
        10: "halloween",
        11: "default",
        12: "christmas",
    }
    
    return _theme_map.get(_month, "default")


def render_theme_auto():
    """Render theme by month + time variant."""
    _theme = get_theme_by_month()
    return render_theme(_theme)


# =========================================================
# 🎨 ANIMATION HELPERS
# =========================================================
def render_halloween_animations():
    """Render animasi Halloween."""
    st.markdown("""
    <div class="bat-animation">🦇</div>
    <div class="bat-animation">🦇</div>
    <div class="bat-animation">🦇</div>
    <div class="spider-web"></div>
    """, unsafe_allow_html=True)


def render_theme_animations(theme_name="halloween"):
    """Render animasi sesuai tema."""
    if theme_name == "halloween":
        render_halloween_animations()


# =========================================================
# 🎯 GREETING COMPONENT
# =========================================================
def render_greeting():
    """
    Render greeting element (selamat pagi/siang/...).
    Bisa dipanggil di header atau sidebar.
    """
    _greeting = get_greeting()
    _variant = get_current_time_variant()
    
    st.markdown(f"""
    <div style='
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 9999;
        background: linear-gradient(135deg, rgba(15, 10, 30, 0.95) 0%, rgba(76, 29, 149, 0.95) 100%);
        border: 1.5px solid #FF6B1A;
        border-radius: 20px;
        padding: 6px 14px;
        font-family: "Quicksand", sans-serif;
        font-size: 11px;
        font-weight: 700;
        color: #FDBA74;
        letter-spacing: 1px;
        box-shadow: 0 0 15px rgba(255, 107, 26, 0.4);
        animation: greetingPulse 3s infinite ease-in-out;
    '>
        {_greeting}
    </div>
    <style>
        @keyframes greetingPulse {{
            0%, 100% {{ box-shadow: 0 0 15px rgba(255, 107, 26, 0.4); }}
            50% {{ box-shadow: 0 0 25px rgba(255, 107, 26, 0.7); }}
        }}
    </style>
    """, unsafe_allow_html=True)


# =========================================================
# 🎯 DEBUG INFO
# =========================================================
def debug_theme():
    """
    Return debug info. Bisa dipanggil di Streamlit.
    """
    _theme_name = get_theme_by_month()
    _variant = get_current_time_variant()
    _greeting = get_greeting()
    _info = get_theme_info(_theme_name)
    
    return {
        "theme": _theme_name,
        "variant": _variant,
        "greeting": _greeting,
        "primary": _info.get("primary", "?"),
        "emoji": _info.get("emoji", "?"),
    }


def render_debug_panel():
    """Render debug panel untuk admin."""
    _debug = debug_theme()
    
    st.markdown(f"""
    <div style='
        background: rgba(15, 10, 30, 0.9);
        border: 1.5px solid #FF6B1A;
        border-radius: 12px;
        padding: 12px 16px;
        font-family: monospace;
        font-size: 11px;
        color: #FDBA74;
        margin: 10px 0;
    '>
        <div style='font-weight: 900; margin-bottom: 6px;'>🔍 DEBUG THEME</div>
        <div>🎨 Theme: <b>{_debug['theme']}</b></div>
        <div>⏰ Variant: <b>{_debug['variant']}</b></div>
        <div>👋 Greeting: <b>{_debug['greeting']}</b></div>
        <div>🎯 Primary: <b>{_debug['primary']}</b></div>
    </div>
    """, unsafe_allow_html=True)