"""
Theme Loader
============
Loader untuk multi-tema. Ganti tema = ganti 1 baris.
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
    """Render CSS ke Streamlit."""
    _css = load_theme(theme_name)
    if _css:
        st.markdown(_css, unsafe_allow_html=True)
    return _css


# =========================================================
# 🎯 AUTO THEME BY MONTH
# =========================================================
def get_theme_by_month():
    """
    Auto-pick theme berdasarkan bulan.
    - Oktober: Halloween 🎃
    - Desember: Christmas 🎄
    - Januari: New Year 🎆
    - April-Mei: Lebaran 🌙
    - Bulan lain: Default ⚜️
    """
    _month = datetime.now(ZoneInfo("Asia/Jakarta")).month
    
    _theme_map = {
        1: "newyear",    # Januari — New Year
        2: "default",    # Februari
        3: "default",    # Maret
        4: "lebaran",    # April — Lebaran (kadang)
        5: "lebaran",    # Mei — Lebaran (kadang)
        6: "default",    # Juni
        7: "default",    # Juli
        8: "default",    # Agustus — Kemerdekaan
        9: "default",    # September
        10: "halloween", # Oktober — Halloween 🎃
        11: "default",   # November
        12: "christmas", # Desember — Natal 🎄
    }
    
    return _theme_map.get(_month, "default")


def render_theme_auto():
    """Render theme otomatis by month."""
    _theme = get_theme_by_month()
    return render_theme(_theme)


# =========================================================
# 🎨 ANIMATION HELPERS
# =========================================================
def render_halloween_animations():
    """Render animasi khusus Halloween (kelelawar, spider web)."""
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
    # Nanti bisa tambah animasi tema lain
