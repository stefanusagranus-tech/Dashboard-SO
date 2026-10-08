"""
🎃 HALLOWEEN THEME v3 — Performance-First
==========================================
- Ringan di PC, Android, iOS
- Animate transform & opacity only (GPU)
- No backdrop-filter, no blur
- Mobile responsive
"""

# =========================================================
# 🎃 THEME INFO
# =========================================================
THEME_INFO = {
    "name": "Halloween",
    "emoji": "🎃",
    "primary": "#E8B189",
    "secondary": "#7FB99B",
    "dark": "#0F0A1E",
    "light": "#F8F5F0",
}


# =========================================================
# 🌅 TIME VARIANTS (5 varian)
# =========================================================
THEME_VARIANTS = {
    "pagi": {
        "primary": "#FFA500",
        "primary_dark": "#E67E22",
        "primary_light": "#FFD180",
        "secondary": "#FFD700",
        "secondary_dark": "#F9A825",
        "accent": "#FFEB3B",
        "bg_top": "#1A1F3A",
        "bg_bot": "#4A2511",
        "bg_glow": "rgba(255, 215, 0, 0.15)",
        "text": "#FFF8E1",
        "text_dim": "#C9A961",
        "emoji": "🌅",
        "greeting": "Selamat Pagi",
    },
    "siang": {
        "primary": "#FF6B1A",
        "primary_dark": "#D97706",
        "primary_light": "#FDBA74",
        "secondary": "#84CC16",
        "secondary_dark": "#65A30D",
        "accent": "#FB923C",
        "bg_top": "#0F0A1E",
        "bg_bot": "#1A2F1E",
        "bg_glow": "rgba(255, 107, 26, 0.15)",
        "text": "#F8F5F0",
        "text_dim": "#A89B8E",
        "emoji": "☀️",
        "greeting": "Selamat Siang",
    },
    "sore": {
        "primary": "#FF6B1A",
        "primary_dark": "#C2410C",
        "primary_light": "#FDBA74",
        "secondary": "#DC2626",
        "secondary_dark": "#991B1B",
        "accent": "#F97316",
        "bg_top": "#1A0D2E",
        "bg_bot": "#4A1810",
        "bg_glow": "rgba(255, 107, 26, 0.18)",
        "text": "#FEF2F2",
        "text_dim": "#B89B8E",
        "emoji": "🌇",
        "greeting": "Selamat Sore",
    },
    "malam": {
        "primary": "#FF6B1A",
        "primary_dark": "#D97706",
        "primary_light": "#FDBA74",
        "secondary": "#6B21A8",
        "secondary_dark": "#4C1D95",
        "accent": "#FBBF24",
        "bg_top": "#0F0A1E",
        "bg_bot": "#1A0D2E",
        "bg_glow": "rgba(107, 33, 168, 0.15)",
        "text": "#F8F5F0",
        "text_dim": "#A89B8E",
        "emoji": "🌆",
        "greeting": "Selamat Malam",
    },
    "midnight": {
        "primary": "#A855F7",
        "primary_dark": "#7C3AED",
        "primary_light": "#D8B4FE",
        "secondary": "#4C1D95",
        "secondary_dark": "#2E1065",
        "accent": "#C4B5FD",
        "bg_top": "#05030F",
        "bg_bot": "#0A0514",
        "bg_glow": "rgba(168, 85, 247, 0.18)",
        "text": "#E9D5FF",
        "text_dim": "#8B7BA8",
        "emoji": "🌙",
        "greeting": "Selamat Tidur",
    },
}


def get_variant(variant="malam"):
    """Get variant config."""
    return THEME_VARIANTS.get(variant, THEME_VARIANTS["malam"])


# =========================================================
# 🎨 GET CSS
# =========================================================
def get_css(variant="malam"):
    """Return CSS dengan variant warna."""
    _v = get_variant(variant)

    _css = f"""
<style>
    /* ============================================
    🎃 CSS VARIABLES
    ============================================ */
    :root {{
        --pumpkin: {_v['primary']};
        --pumpkin-dark: {_v['primary_dark']};
        --pumpkin-light: {_v['primary_light']};
        --witch: {_v['secondary']};
        --witch-dark: {_v['secondary_dark']};
        --candy: {_v['accent']};
        --midnight: {_v['bg_top']};
        --midnight-2: {_v['bg_bot']};
        --bg-glow: {_v['bg_glow']};
        --ghost: {_v['text']};
        --ghost-dim: {_v['text_dim']};
    }}

    /* ============================================
    🎃 BASE — BACKGROUND (RINGAN, NO BLUR)
    ============================================ */
    .stApp {{
        background: 
            radial-gradient(circle at 15% 10%, var(--bg-glow) 0%, transparent 40%),
            radial-gradient(circle at 85% 90%, var(--bg-glow) 0%, transparent 40%),
            linear-gradient(180deg, var(--midnight) 0%, var(--midnight-2) 50%, var(--midnight) 100%);
        background-attachment: fixed;
        color: var(--ghost);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Quicksand', sans-serif;
        min-height: 100vh;
    }}

    @media (max-width: 768px) {{
        .stApp {{
            background-attachment: scroll;
        }}
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: var(--midnight); }}
    ::-webkit-scrollbar-thumb {{
        background: var(--pumpkin-dark);
        border-radius: 5px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--pumpkin);
    }}

    /* ============================================
    🎃 HEADER
    ============================================ */
    .royal-header {{
        position: relative;
        background: linear-gradient(135deg, var(--midnight) 0%, var(--witch-dark) 50%, var(--midnight) 100%);
        border: 2px solid var(--pumpkin);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 0 30px var(--bg-glow);
    }}

    .royal-title {{
        font-family: 'Cinzel', -apple-system, sans-serif;
        font-size: 28px;
        font-weight: 900;
        color: var(--pumpkin);
        text-align: center;
        margin: 0;
        letter-spacing: 3px;
        text-shadow: 0 0 15px var(--pumpkin);
    }}

    .royal-subtitle {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 11px;
        color: var(--pumpkin-light);
        text-align: center;
        margin-top: 6px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }}

    .header-clock {{
        text-align: center;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px dashed rgba(255, 107, 26, 0.3);
    }}

    .clock-time {{
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 20px;
        font-weight: 900;
        color: var(--candy);
        letter-spacing: 2px;
    }}

    .clock-date {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--pumpkin-light);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 4px;
    }}

    /* ============================================
    🎃 METRIC CARD
    ============================================ */
    .metric-clean,
    .metric-card-v2 {{
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border: 1px solid rgba(232, 177, 137, 0.25);
        border-left: 3px solid var(--pumpkin);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .metric-clean:hover,
    .metric-card-v2:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }}

    .metric-clean .label,
    .metric-label-v2 {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}

    .metric-clean .value,
    .metric-value-v2 {{
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 24px;
        font-weight: 900;
        color: var(--pumpkin);
        line-height: 1.1;
        word-break: break-all;
    }}

    .metric-clean .sub,
    .metric-sub-v2 {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
        margin-top: 4px;
    }}

    /* ============================================
    🎃 SO TABLE (CUSTOM)
    ============================================ */
    .so-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 12px;
        margin-top: 8px;
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border-radius: 10px;
        border: 1px solid rgba(168, 85, 247, 0.2);
        overflow: hidden;
    }}

    .so-table thead th {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        font-weight: 700;
        color: var(--ghost-dim);
        letter-spacing: 1px;
        text-transform: uppercase;
        text-align: left;
        padding: 12px 14px;
        border-bottom: 2px solid rgba(232, 177, 137, 0.3);
        background: rgba(45, 25, 75, 0.5);
    }}

    .so-table tbody td {{
        padding: 10px 14px;
        border-bottom: 1px solid rgba(168, 85, 247, 0.1);
        color: var(--ghost);
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 12px;
    }}

    .so-table tbody tr:last-child td {{
        border-bottom: none;
    }}

    .so-table tbody tr:nth-child(even) {{
        background: rgba(45, 25, 75, 0.3);
    }}

    .so-table td.rak-id {{
        color: var(--pumpkin);
        font-weight: 900;
    }}

    .so-table td.nominal {{
        text-align: right;
        font-weight: 700;
    }}

    .so-table td.nominal.neg {{
        color: #E88B8B;
    }}

    .so-table td.nominal.pos {{
        color: var(--secondary);
    }}

    /* ============================================
    🎃 KETERANGAN PANEL
    ============================================ */
    .keterangan-panel {{
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border: 1px solid rgba(232, 177, 137, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}

    .keterangan-panel .panel-label {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        font-weight: 700;
        color: var(--secondary);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }}

    .keterangan-panel .panel-value {{
        font-family: 'Cinzel', -apple-system, sans-serif;
        font-size: 26px;
        font-weight: 900;
        color: var(--pumpkin);
        line-height: 1.1;
    }}

    .keterangan-panel .panel-sub {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 11px;
        color: var(--ghost-dim);
        margin-top: 6px;
    }}

    .keterangan-panel.danger {{
        border-left: 4px solid #E88B8B;
    }}

    .keterangan-panel.danger .panel-value {{
        color: #E88B8B;
    }}

    .keterangan-panel.safe {{
        border-left: 4px solid var(--secondary);
    }}

    .keterangan-panel.safe .panel-value {{
        color: var(--secondary);
    }}

    /* ============================================
    🎃 RAK RESULT / SELECTED
    ============================================ */
    .rak-result {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        background: var(--midnight);
        border: 1px solid rgba(168, 85, 247, 0.25);
        border-radius: 8px;
        margin-bottom: 4px;
    }}

    .rak-result-id {{
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 12px;
        font-weight: 700;
        color: var(--pumpkin);
    }}

    .rak-result-name {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
    }}

    .rak-selected {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        background: var(--midnight);
        border: 1px solid rgba(127, 185, 155, 0.3);
        border-left: 3px solid var(--secondary);
        border-radius: 8px;
        margin-bottom: 6px;
    }}

    .rak-selected-id {{
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 13px;
        font-weight: 900;
        color: var(--pumpkin);
        min-width: 70px;
    }}

    .rak-selected-name {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
        flex: 1;
    }}

    /* ============================================
    🎃 SECTION DIVIDER
    ============================================ */
    .section-divider {{
        margin: 20px 0 14px 0;
        border: none;
        border-top: 1px solid rgba(168, 85, 247, 0.15);
    }}

    /* ============================================
    🎃 FOOTER
    ============================================ */
    .copyright-footer {{
        text-align: center;
        margin-top: 40px;
        padding-top: 16px;
        border-top: 1px dashed rgba(255, 107, 26, 0.3);
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 10px;
        color: var(--ghost-dim);
        letter-spacing: 1.5px;
    }}

    /* ============================================
    🎃 DIALOG / MODAL
    ============================================ */
    [data-testid="stDialog"] div[role="dialog"] {{
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border: 1px solid var(--pumpkin);
        border-radius: 16px;
        box-shadow: 0 0 30px var(--bg-glow);
    }}

    [data-testid="stDialog"] header {{
        background: transparent;
        border-bottom: 1px solid rgba(232, 177, 137, 0.3);
    }}

    [data-testid="stDialog"] h2 {{
        color: var(--pumpkin);
        font-family: 'Cinzel', -apple-system, sans-serif;
        letter-spacing: 2px;
    }}

    [data-testid="stDialogBackdrop"] {{
        background: rgba(10, 5, 20, 0.75);
    }}
    
    /* ============================================
    🎃 BUTTONS
    ============================================ */
    div.stButton > button,
    div.stFormSubmitButton > button,
    div.stDownloadButton > button {{
        background: linear-gradient(135deg, var(--midnight-2) 0%, var(--witch-dark) 100%);
        color: var(--pumpkin-light);
        border: 2px solid var(--pumpkin-dark);
        border-radius: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-weight: 700;
        font-size: 13px;
        padding: 12px 20px;
        letter-spacing: 0.5px;
        min-height: 48px;
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }}

    div.stButton > button:hover {{
        background: linear-gradient(135deg, var(--pumpkin-dark) 0%, var(--pumpkin) 100%);
        color: #FFFFFF;
        border-color: var(--candy);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px var(--bg-glow);
    }}

    div.stButton > button:active {{
        transform: translateY(0);
    }}

    /* ============================================
    🎃 INPUT FIELDS
    ============================================ */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {{
        background-color: var(--midnight);
        border: 1px solid rgba(168, 85, 247, 0.3);
        border-radius: 10px;
        min-height: 44px;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span,
    div[data-baseweb="textarea"] textarea {{
        color: var(--ghost);
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 13px;
    }}

    label,
    div[data-testid="stWidgetLabel"] label {{
        color: var(--pumpkin-light);
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }}

    /* ============================================
    🎃 TABS
    ============================================ */
    div[data-baseweb="tab-list"] {{
        background: rgba(15, 10, 30, 0.8);
        border-radius: 10px;
        padding: 4px;
        border: 1px solid var(--pumpkin-dark);
        gap: 4px;
    }}

    div[data-baseweb="tab-list"] button {{
        background: transparent;
        color: var(--ghost-dim);
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-weight: 700;
        font-size: 12px;
        min-height: 44px;
        padding: 10px 16px;
        border-radius: 8px;
        transition: background 0.2s ease, color 0.2s ease;
    }}

    div[data-baseweb="tab-list"] button[aria-selected="true"] {{
        background: linear-gradient(135deg, var(--pumpkin-dark) 0%, var(--pumpkin) 100%);
        color: #FFFFFF;
    }}

    /* ============================================
    🎃 EXPANDER
    ============================================ */
    div[data-testid="stExpander"] {{
        background: rgba(15, 10, 30, 0.8);
        border: 1px solid var(--pumpkin-dark);
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 10px;
    }}

    div[data-testid="stExpander"] summary {{
        background: linear-gradient(90deg, var(--witch-dark) 0%, var(--bg-glow) 100%);
        color: var(--pumpkin-light);
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-weight: 700;
        font-size: 13px;
        padding: 14px 16px;
        min-height: 48px;
        border-bottom: 1px dashed rgba(255, 107, 26, 0.2);
    }}

    /* ============================================
    🎃 DATAFRAME
    ============================================ */
    div[data-testid="stDataFrame"] {{
        border: 1px solid var(--pumpkin-dark);
        border-radius: 10px;
        overflow: hidden;
    }}

    /* ============================================
    🎃 SIDEBAR
    ============================================ */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border-right: 1px solid var(--pumpkin-dark);
    }}

    [data-testid="stSidebar"] * {{
        color: var(--ghost);
    }}

    /* ============================================
    🎃 ALERT
    ============================================ */
    div[data-testid="stAlert"] {{
        background: rgba(15, 10, 30, 0.95);
        border: 1px solid var(--pumpkin-dark);
        border-radius: 10px;
    }}

    /* ============================================
    🎃 MOBILE RESPONSIVE
    ============================================ */
    @media (max-width: 768px) {{
        .royal-header {{
            padding: 16px;
            border-radius: 12px;
        }}

        .royal-title {{
            font-size: 20px;
            letter-spacing: 2px;
        }}

        .royal-subtitle {{
            font-size: 9px;
        }}

        .metric-clean .value,
        .metric-value-v2 {{
            font-size: 20px;
        }}

        .so-table thead th {{
            padding: 8px 10px;
            font-size: 9px;
        }}

        .so-table tbody td {{
            padding: 8px 10px;
            font-size: 11px;
        }}

        div.stButton > button,
        div.stFormSubmitButton > button,
        div.stDownloadButton > button {{
            min-height: 52px;
            font-size: 14px;
        }}

        .main .block-container {{
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 0.5rem;
        }}
    }}

    @media (max-width: 480px) {{
        .royal-title {{
            font-size: 16px;
        }}

        .metric-clean .value {{
            font-size: 18px;
        }}

        .main .block-container {{
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }}
    }}

    /* ============================================
    ♿ REDUCED MOTION (accessibility)
    ============================================ */
    @media (prefers-reduced-motion: reduce) {{
        *,
        *::before,
        *::after {{
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
        }}
    }}

    /* ============================================
    🎃 UTILITY
    ============================================ */
    .fade-in-up {{
        animation: fadeInUp 0.4s ease-out;
    }}

    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(10px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
</style>
"""

    return _css