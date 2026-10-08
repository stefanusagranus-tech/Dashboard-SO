"""
🎃 HALLOWEEN THEME v4 — Performance-First + Complete
======================================================
- Ringan (GPU-friendly: transform + opacity only)
- Native PC / Android / iOS
- Variant by time (pagi/siang/sore/malam/midnight)
- LENGKAP: header, metric, menu card, table, dialog, dll
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
        "secondary": "#7FB99B",
        "secondary_dark": "#4C9B7F",
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
        "secondary": "#7FB99B",
        "secondary_dark": "#4C9B7F",
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
        "secondary": "#7FB99B",
        "secondary_dark": "#4C9B7F",
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
        "secondary": "#7FB99B",
        "secondary_dark": "#4C9B7F",
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
        "secondary": "#7FB99B",
        "secondary_dark": "#4C9B7F",
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
    🎃 BASE — BACKGROUND (RINGAN)
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
    🎃 HEADER ROYAL (Dashboard)
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

    .royal-ornament {{
        position: absolute;
        color: var(--pumpkin);
        font-size: 20px;
    }}

    .royal-orn-tl {{ top: 8px; left: 12px; }}
    .royal-orn-tr {{ top: 8px; right: 12px; }}
    .royal-orn-bl {{ bottom: 8px; left: 12px; }}
    .royal-orn-br {{ bottom: 8px; right: 12px; }}

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
    🎃 PROFILE HEADER (Halaman SO / Master Shift)
    ============================================ */
    .profile-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 20px;
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border: 1px solid rgba(232, 177, 137, 0.25);
        border-radius: 14px;
        margin-bottom: 20px;
    }}

    .profile-title {{
        font-family: 'Cinzel', -apple-system, sans-serif;
        font-size: 16px;
        font-weight: 900;
        color: var(--pumpkin);
        letter-spacing: 2px;
    }}

    .profile-sub {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--secondary);
        letter-spacing: 1px;
        margin-top: 2px;
    }}

    .profile-status {{
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 10px;
        color: var(--secondary);
        text-align: right;
    }}
    
    /* ============================================
    🎃 METRIC CARD (clean)
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
    🎃 MENU CARD (Homepage)
    ============================================ */
    .menu-card-v2 {{
        position: relative;
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border: 2px solid var(--pumpkin-dark);
        border-radius: 16px;
        padding: 24px 18px;
        text-align: center;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        margin-bottom: 10px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.5);
    }}
    
    .menu-card-v2:hover {{
        border-color: var(--pumpkin);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7), 0 0 30px var(--bg-glow);
        transform: translateY(-4px);
    }}
    
    .menu-icon-v2 {{
        font-size: 48px;
        margin-bottom: 12px;
        line-height: 1;
        display: block;
        filter: drop-shadow(0 0 10px var(--pumpkin));
    }}
    
    .menu-title-v2 {{
        font-family: 'Cinzel', -apple-system, sans-serif;
        font-size: 14px;
        font-weight: 900;
        color: var(--pumpkin-light);
        letter-spacing: 2px;
        margin-bottom: 6px;
        text-transform: uppercase;
    }}
    
    .menu-desc-v2 {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
        line-height: 1.5;
    }}
    
    /* ============================================
    🎃 SO TABLE
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
    🎃 SUCCESS SCREEN
    ============================================ */
    .success-icon {{
        font-size: 72px;
        margin-bottom: 16px;
        text-align: center;
    }}
    
    .success-title {{
        font-family: 'Cinzel', -apple-system, sans-serif;
        font-size: 28px;
        font-weight: 900;
        color: var(--secondary);
        letter-spacing: 3px;
        text-align: center;
    }}
    
    .success-sub {{
        font-family: -apple-system, BlinkMacSystemFont, 'Quicksand', sans-serif;
        font-size: 13px;
        color: var(--ghost-dim);
        margin-top: 12px;
        letter-spacing: 1px;
        text-align: center;
    }}
    
    /* ============================================
    🎃 COPYRIGHT FOOTER
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
    🎃 FADE IN UP (utility)
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
    /* ============================================
    🎃 ANIMASI HALOWEEN — 6 FLYER + BINTANG + JARING
    Ringan: cuma transform & opacity (GPU)
    ============================================ */
    
    /* === BASE FLYER === */
    .hw-flyer {{
        position: fixed;
        left: -60px;
        z-index: 999;
        pointer-events: none;
        opacity: 0;
        will-change: transform, opacity;
        transform: translate3d(0, 0, 0);
        line-height: 1;
    }}
    
    /* === FLYER 1: KELELAWAR ATAS (cepat) === */
    .hw-flyer-1 {{
        top: 6%;
        font-size: 26px;
        animation: hwSweep1 18s infinite linear;
        animation-delay: 0s;
    }}
    
    /* === FLYER 2: LABU ATAS (sedang) === */
    .hw-flyer-2 {{
        top: 10%;
        font-size: 24px;
        animation: hwSweep2 24s infinite linear;
        animation-delay: 3s;
    }}
    
    /* === FLYER 3: HANTU TENGAH (sedang) === */
    .hw-flyer-3 {{
        top: 20%;
        font-size: 28px;
        animation: hwSweep1 26s infinite linear;
        animation-delay: 6s;
    }}
    
    /* === FLYER 4: LABA-LABA TENGAH (lambat) === */
    .hw-flyer-4 {{
        top: 30%;
        font-size: 20px;
        animation: hwSweep2 30s infinite linear;
        animation-delay: 10s;
    }}
    
    /* === FLYER 5: KELELAWAR BAWAH (sedang) === */
    .hw-flyer-5 {{
        top: 70%;
        font-size: 22px;
        animation: hwSweep1 28s infinite linear;
        animation-delay: 14s;
    }}
    
    /* === FLYER 6: LABU BAWAH (lambat) === */
    .hw-flyer-6 {{
        top: 82%;
        font-size: 20px;
        animation: hwSweep2 34s infinite linear;
        animation-delay: 18s;
    }}
    
    /* === KEYFRAMES SWEEP 1: horizontal + naik === */
    @keyframes hwSweep1 {{
        0% {{
            transform: translate3d(0, 0, 0);
            opacity: 0;
        }}
        8% {{
            opacity: 0.9;
        }}
        50% {{
            transform: translate3d(55vw, -25px, 0);
        }}
        92% {{
            opacity: 0.9;
        }}
        100% {{
            transform: translate3d(110vw, -40px, 0);
            opacity: 0;
        }}
    }}
    
    /* === KEYFRAMES SWEEP 2: horizontal + turun === */
    @keyframes hwSweep2 {{
        0% {{
            transform: translate3d(0, 0, 0);
            opacity: 0;
        }}
        8% {{
            opacity: 0.9;
        }}
        50% {{
            transform: translate3d(55vw, 20px, 0);
        }}
        92% {{
            opacity: 0.9;
        }}
        100% {{
            transform: translate3d(110vw, 35px, 0);
            opacity: 0;
        }}
    }}
    
    /* === BINTANG BERKEDIP (background) === */
    .hw-stars {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
        background-image:
            radial-gradient(1.5px 1.5px at 12% 18%, rgba(255, 255, 255, 0.6), transparent),
            radial-gradient(1px 1px at 35% 42%, rgba(255, 255, 255, 0.5), transparent),
            radial-gradient(1.5px 1.5px at 58% 28%, rgba(255, 255, 255, 0.6), transparent),
            radial-gradient(1px 1px at 75% 55%, rgba(255, 255, 255, 0.4), transparent),
            radial-gradient(1.5px 1.5px at 88% 15%, rgba(255, 255, 255, 0.5), transparent),
            radial-gradient(1px 1px at 22% 72%, rgba(255, 255, 255, 0.4), transparent),
            radial-gradient(1.5px 1.5px at 45% 85%, rgba(255, 255, 255, 0.5), transparent),
            radial-gradient(1px 1px at 92% 78%, rgba(255, 255, 255, 0.4), transparent);
        opacity: 0.6;
        animation: hwStarsTwinkle 6s infinite ease-in-out;
        will-change: opacity;
    }}
    
    @keyframes hwStarsTwinkle {{
        0%, 100% {{ opacity: 0.5; }}
        50% {{ opacity: 0.8; }}
    }}
    
    /* === JARING LABA-LABA (pojok kanan atas, static) === */
    .hw-spider-web {{
        position: fixed;
        top: 0;
        right: 0;
        width: 120px;
        height: 120px;
        pointer-events: none;
        z-index: 1;
        background-image:
            linear-gradient(45deg, transparent 48%, rgba(232, 177, 137, 0.4) 49%, rgba(232, 177, 137, 0.4) 51%, transparent 52%),
            linear-gradient(-45deg, transparent 48%, rgba(232, 177, 137, 0.4) 49%, rgba(232, 177, 137, 0.4) 51%, transparent 52%),
            radial-gradient(circle, rgba(232, 177, 137, 0.5) 1px, transparent 1px);
        background-size: 40px 40px, 40px 40px, 20px 20px;
        clip-path: polygon(100% 0, 100% 100%, 0 0);
        opacity: 0.5;
        animation: hwWebPulse 8s infinite ease-in-out;
        will-change: opacity;
    }}
    
    @keyframes hwWebPulse {{
        0%, 100% {{ opacity: 0.4; }}
        50% {{ opacity: 0.7; }}
    }}
    
    /* ============================================
    📱 MOBILE OPTIMIZATION — Kurangi animasi
    ============================================ */
    
    /* Tablet & mobile besar: kurangi flyer, hide sebagian */
    @media (max-width: 1024px) {{
        .hw-flyer-4,
        .hw-flyer-5,
        .hw-flyer-6 {{
            display: none !important;
        }}
        .hw-spider-web {{
            width: 80px;
            height: 80px;
        }}
    }}
    
    /* Mobile & HP: cuma 2 flyer, matikan bintang & jaring */
    @media (max-width: 768px) {{
        .hw-flyer-2,
        .hw-flyer-4,
        .hw-flyer-5,
        .hw-flyer-6 {{
            display: none !important;
        }}
        .hw-stars {{
            display: none !important;
        }}
        .hw-spider-web {{
            display: none !important;
        }}
        /* Sisa: flyer-1 (🦇) & flyer-3 (👻) */
        .hw-flyer-1,
        .hw-flyer-3 {{
            font-size: 22px;
            animation-duration: 26s;
        }}
    }}
    
    /* HP kecil (iPhone SE): cuma 1 flyer */
    @media (max-width: 480px) {{
        .hw-flyer-3 {{
            display: none !important;
        }}
        .hw-flyer-1 {{
            font-size: 20px;
            animation-duration: 30s;
        }}
    }}
    
    /* iOS: hindari render ulang terus-menerus */
    @media (hover: none) and (pointer: coarse) {{
        .hw-flyer {{
            /* Pastikan pake GPU layer */
            transform: translateZ(0);
            backface-visibility: hidden;
        }}
    }}
    
    /* Accessibility: hormati prefers-reduced-motion */
    @media (prefers-reduced-motion: reduce) {{
        .hw-flyer,
        .hw-stars,
        .hw-spider-web {{
            display: none !important;
        }}
    }}
</style>
"""

    return _css