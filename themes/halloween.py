"""
🎃 HALLOWEEN THEME v5 — Gothic Atmospheric
============================================
- Deep purple + inky black + eerie orange
- Fog + stars (GPU-friendly: opacity only)
- Flying icons (transform + opacity)
- Variant by time (pagi/siang/sore/malam/midnight)
"""

# =========================================================
# 🎃 THEME INFO
# =========================================================
THEME_INFO = {
    "name": "Halloween",
    "emoji": "🎃",
    "primary": "#FF6B1A",
    "secondary": "#7FB99B",
    "dark": "#0F0A1E",
    "light": "#F8F5F0",
}


# =========================================================
# 🌅 TIME VARIANTS
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
        "bg_glow": "rgba(255, 215, 0, 0.18)",
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
        "bg_glow": "rgba(255, 107, 26, 0.20)",
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
        "bg_glow": "rgba(107, 33, 168, 0.20)",
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
        "bg_glow": "rgba(168, 85, 247, 0.22)",
        "text": "#E9D5FF",
        "text_dim": "#8B7BA8",
        "emoji": "🌙",
        "greeting": "Selamat Tidur",
    },
}


def get_variant(variant="malam"):
    return THEME_VARIANTS.get(variant, THEME_VARIANTS["malam"])


# =========================================================
# 🎨 GET CSS
# =========================================================
def get_css(variant="malam"):
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
    🎃 BASE — DEEP PURPLE + INKY BLACK
    ============================================ */
    .stApp {{
        background:
            radial-gradient(circle at 15% 10%, var(--bg-glow) 0%, transparent 40%),
            radial-gradient(circle at 85% 90%, var(--bg-glow) 0%, transparent 40%),
            radial-gradient(circle at 50% 50%, rgba(76, 29, 149, 0.15) 0%, transparent 60%),
            linear-gradient(180deg, var(--midnight) 0%, var(--midnight-2) 50%, var(--midnight) 100%);
        background-attachment: fixed;
        color: var(--ghost);
        font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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

    /* ============================================
    🎃 HEADER ROYAL — GOTHIC ATMOSPHERIC
    ============================================ */
    .royal-header {{
        position: relative;
        background: linear-gradient(135deg, #0F0A1E 0%, #2E1065 40%, #4C1D95 70%, #0F0A1E 100%);
        border: 2px solid var(--pumpkin);
        border-radius: 18px;
        padding: 28px 24px 24px 24px;
        margin-bottom: 20px;
        box-shadow:
            0 0 40px rgba(107, 33, 168, 0.35),
            0 0 80px rgba(255, 107, 26, 0.15),
            inset 0 0 60px rgba(0, 0, 0, 0.7);
        overflow: hidden;
    }}

    /* Fog effect pakai radial gradient (GPU-friendly) */
    .royal-header::before {{
        content: "";
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background:
            radial-gradient(ellipse at 20% 30%, rgba(255, 107, 26, 0.12), transparent 50%),
            radial-gradient(ellipse at 80% 70%, rgba(168, 85, 247, 0.10), transparent 50%);
        animation: headerFogDrift 25s infinite ease-in-out;
        pointer-events: none;
        z-index: 0;
        will-change: transform, opacity;
    }}

    @keyframes headerFogDrift {{
        0%, 100% {{ transform: translate3d(0, 0, 0); opacity: 0.6; }}
        50% {{ transform: translate3d(30px, -20px, 0); opacity: 1; }}
    }}

    /* Ornamen pojok */
    .royal-ornament {{
        position: absolute;
        color: var(--pumpkin);
        font-size: 22px;
        z-index: 2;
        filter: drop-shadow(0 0 8px var(--pumpkin));
    }}

    .royal-orn-tl {{ top: 10px; left: 14px; }}
    .royal-orn-tr {{ top: 10px; right: 14px; }}
    .royal-orn-bl {{ bottom: 10px; left: 14px; }}
    .royal-orn-br {{ bottom: 10px; right: 14px; }}

    .royal-title {{
        position: relative;
        font-family: 'Creepster', 'Cinzel', -apple-system, serif;
        font-size: 32px;
        font-weight: 900;
        color: var(--pumpkin);
        text-align: center;
        margin: 0;
        letter-spacing: 4px;
        text-shadow:
            0 0 20px var(--pumpkin),
            0 0 40px rgba(255, 107, 26, 0.6),
            0 0 60px rgba(255, 107, 26, 0.4),
            2px 2px 4px rgba(0, 0, 0, 0.95);
        z-index: 2;
    }}

    .royal-subtitle {{
        position: relative;
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 11px;
        color: var(--pumpkin-light);
        text-align: center;
        margin-top: 8px;
        letter-spacing: 4px;
        text-transform: uppercase;
        z-index: 2;
        text-shadow: 0 0 8px rgba(255, 107, 26, 0.5);
    }}

    .header-clock {{
        position: relative;
        text-align: center;
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px dashed rgba(255, 107, 26, 0.4);
        z-index: 2;
    }}

    .clock-time {{
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 22px;
        font-weight: 900;
        color: var(--candy);
        letter-spacing: 3px;
        text-shadow: 0 0 15px var(--candy), 0 0 30px rgba(255, 107, 26, 0.5);
    }}

    .clock-date {{
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 10px;
        color: var(--pumpkin-light);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 4px;
    }}

    /* ============================================
    🎃 PROFILE HEADER (Halaman SO, dll)
    ============================================ */
    .profile-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 20px;
        background: linear-gradient(135deg, #0F0A1E 0%, #2E1065 100%);
        border: 1px solid rgba(232, 177, 137, 0.3);
        border-radius: 14px;
        margin-bottom: 20px;
        box-shadow: 0 0 20px rgba(107, 33, 168, 0.2);
    }}

    .profile-title {{
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 16px;
        font-weight: 900;
        color: var(--pumpkin);
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(255, 107, 26, 0.4);
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
    🎃 METRIC CARD
    ============================================ */
    .metric-clean,
    .metric-card-v2 {{
        background: linear-gradient(135deg, #0F0A1E 0%, #1A0D2E 100%);
        border: 1px solid rgba(232, 177, 137, 0.25);
        border-left: 3px solid var(--pumpkin);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .metric-clean:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5), 0 0 20px rgba(255, 107, 26, 0.2);
    }}

    .metric-clean .label {{
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 10px;
        color: var(--ghost-dim);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}

    .metric-clean .value {{
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 24px;
        font-weight: 900;
        color: var(--pumpkin);
        line-height: 1.1;
        word-break: break-all;
        text-shadow: 0 0 10px rgba(255, 107, 26, 0.4);
    }}

    .metric-clean .sub {{
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
        background: linear-gradient(135deg, #0F0A1E 0%, #1A0D2E 100%);
        border: 2px solid var(--pumpkin-dark);
        border-radius: 16px;
        padding: 24px 18px;
        text-align: center;
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        overflow: hidden;
        margin-bottom: 10px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.6);
    }}
    
    .menu-card-v2:hover {{
        border-color: var(--pumpkin);
        box-shadow:
            0 15px 40px rgba(0, 0, 0, 0.8),
            0 0 30px rgba(255, 107, 26, 0.4);
        transform: translateY(-4px);
    }}
    
    .menu-icon-v2 {{
        font-size: 48px;
        margin-bottom: 12px;
        line-height: 1;
        display: block;
        filter: drop-shadow(0 0 12px var(--pumpkin));
    }}
    
    .menu-title-v2 {{
        font-family: 'Cinzel', -apple-system, serif;
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
        background: linear-gradient(135deg, #0F0A1E 0%, #1A0D2E 100%);
        border-radius: 10px;
        border: 1px solid rgba(168, 85, 247, 0.25);
        overflow: hidden;
    }}
    
    .so-table thead th {{
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 10px;
        font-weight: 700;
        color: var(--ghost-dim);
        letter-spacing: 1.2px;
        text-transform: uppercase;
        text-align: left;
        padding: 12px 14px;
        border-bottom: 2px solid rgba(255, 107, 26, 0.4);
        background: rgba(45, 25, 75, 0.6);
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
        text-shadow: 0 0 6px rgba(255, 107, 26, 0.3);
    }}
    
    .so-table td.nominal {{
        text-align: right;
        font-weight: 700;
    }}
    
    .so-table td.nominal.neg {{
        color: #E88B8B;
        text-shadow: 0 0 6px rgba(232, 139, 139, 0.3);
    }}
    
    .so-table td.nominal.pos {{
        color: var(--secondary);
        text-shadow: 0 0 6px rgba(127, 185, 155, 0.3);
    }}
    
    /* ============================================
    🎃 KETERANGAN PANEL
    ============================================ */
    .keterangan-panel {{
        background: linear-gradient(135deg, #0F0A1E 0%, #1A0D2E 100%);
        border: 1px solid rgba(232, 177, 137, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}
    
    .keterangan-panel .panel-label {{
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 10px;
        font-weight: 700;
        color: var(--secondary);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }}
    
    .keterangan-panel .panel-value {{
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 26px;
        font-weight: 900;
        color: var(--pumpkin);
        line-height: 1.1;
        text-shadow: 0 0 10px rgba(255, 107, 26, 0.4);
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
        background: #0F0A1E;
        border: 1px solid rgba(168, 85, 247, 0.3);
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
        background: #0F0A1E;
        border: 1px solid rgba(127, 185, 155, 0.35);
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
        filter: drop-shadow(0 0 25px rgba(127, 185, 155, 0.8));
    }}
    
    .success-title {{
        font-family: 'Cinzel', -apple-system, serif;
        font-size: 28px;
        font-weight: 900;
        color: var(--secondary);
        letter-spacing: 3px;
        text-align: center;
        text-shadow: 0 0 20px rgba(127, 185, 155, 0.6);
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
        background: linear-gradient(135deg, #0F0A1E 0%, #1A0D2E 100%);
        border: 1px solid var(--pumpkin);
        border-radius: 16px;
        box-shadow: 0 0 40px rgba(107, 33, 168, 0.5);
    }}

    [data-testid="stDialog"] h2 {{
        color: var(--pumpkin);
        font-family: 'Cinzel', -apple-system, serif;
        letter-spacing: 2px;
    }}

    [data-testid="stDialogBackdrop"] {{
        background: rgba(10, 5, 20, 0.8);
    }}

    /* ============================================
    🎃 BUTTONS
    ============================================ */
    div.stButton > button,
    div.stFormSubmitButton > button,
    div.stDownloadButton > button {{
        background: linear-gradient(135deg, #1A0D2E 0%, #4C1D95 100%);
        color: var(--pumpkin-light);
        border: 2px solid var(--pumpkin-dark);
        border-radius: 12px;
        font-family: 'Cinzel', -apple-system, serif;
        font-weight: 700;
        font-size: 13px;
        padding: 12px 20px;
        letter-spacing: 1px;
        min-height: 48px;
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }}

    div.stButton > button:hover {{
        background: linear-gradient(135deg, var(--pumpkin-dark) 0%, var(--pumpkin) 100%);
        color: #FFFFFF;
        border-color: var(--candy);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 26, 0.4);
    }}

    /* ============================================
    🎃 INPUT FIELDS
    ============================================ */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {{
        background-color: #0F0A1E;
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
        font-family: 'Cinzel', -apple-system, serif;
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 1px;
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
        font-family: 'Cinzel', -apple-system, serif;
        font-weight: 700;
        font-size: 12px;
        min-height: 44px;
        padding: 10px 16px;
        border-radius: 8px;
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
        background: linear-gradient(90deg, #2E1065 0%, rgba(255, 107, 26, 0.1) 100%);
        color: var(--pumpkin-light);
        font-family: 'Cinzel', -apple-system, serif;
        font-weight: 700;
        font-size: 13px;
        padding: 14px 16px;
        min-height: 48px;
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
        background: linear-gradient(180deg, #0F0A1E 0%, #1A0D2E 100%);
        border-right: 1px solid var(--pumpkin-dark);
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
    🎃 ANIMASI — FOG + STARS + FLYERS + WEB
    ============================================ */

    /* === FOG BACKGROUND === */
    .hw-fog {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
        background:
            radial-gradient(ellipse 800px 400px at 20% 30%, rgba(107, 33, 168, 0.15), transparent),
            radial-gradient(ellipse 600px 300px at 80% 70%, rgba(255, 107, 26, 0.10), transparent);
        animation: hwFogDrift 40s infinite ease-in-out;
        will-change: transform, opacity;
    }}

    @keyframes hwFogDrift {{
        0%, 100% {{ transform: translate3d(0, 0, 0); opacity: 0.6; }}
        50% {{ transform: translate3d(40px, -30px, 0); opacity: 1; }}
    }}

    /* === STARS === */
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
        50% {{ opacity: 0.85; }}
    }}

    /* === SPIDER WEB === */
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
            linear-gradient(-45deg, transparent 48%, rgba(232, 177, 137, 0.4) 49%, rgba(232, 177, 137, 0.4) 51%, transparent 52%);
        background-size: 40px 40px, 40px 40px;
        clip-path: polygon(100% 0, 100% 100%, 0 0);
        opacity: 0.5;
    }}

    /* === FLYERS (6 icon) === */
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

    .hw-flyer-1 {{
        top: 6%;
        font-size: 26px;
        animation: hwSweep1 18s infinite linear;
        animation-delay: 0s;
    }}

    .hw-flyer-2 {{
        top: 10%;
        font-size: 24px;
        animation: hwSweep2 24s infinite linear;
        animation-delay: 3s;
    }}

    .hw-flyer-3 {{
        top: 20%;
        font-size: 28px;
        animation: hwSweep1 26s infinite linear;
        animation-delay: 6s;
    }}

    .hw-flyer-4 {{
        top: 30%;
        font-size: 20px;
        animation: hwSweep2 30s infinite linear;
        animation-delay: 10s;
    }}

    .hw-flyer-5 {{
        top: 70%;
        font-size: 22px;
        animation: hwSweep1 28s infinite linear;
        animation-delay: 14s;
    }}

    .hw-flyer-6 {{
        top: 82%;
        font-size: 20px;
        animation: hwSweep2 34s infinite linear;
        animation-delay: 18s;
    }}

    @keyframes hwSweep1 {{
        0% {{ transform: translate3d(0, 0, 0); opacity: 0; }}
        8% {{ opacity: 0.9; }}
        50% {{ transform: translate3d(55vw, -25px, 0); }}
        92% {{ opacity: 0.9; }}
        100% {{ transform: translate3d(110vw, -40px, 0); opacity: 0; }}
    }}

    @keyframes hwSweep2 {{
        0% {{ transform: translate3d(0, 0, 0); opacity: 0; }}
        8% {{ opacity: 0.9; }}
        50% {{ transform: translate3d(55vw, 20px, 0); }}
        92% {{ opacity: 0.9; }}
        100% {{ transform: translate3d(110vw, 35px, 0); opacity: 0; }}
    }}

    /* ============================================
    📱 MOBILE OPTIMIZATION
    ============================================ */
    @media (max-width: 1024px) {{
        .hw-flyer-4,
        .hw-flyer-5,
        .hw-flyer-6 {{
            display: none !important;
        }}
    }}

    @media (max-width: 768px) {{
        .royal-header {{
            padding: 20px 16px 16px 16px;
            border-radius: 14px;
        }}

        .royal-title {{
            font-size: 22px;
            letter-spacing: 2px;
        }}

        .royal-subtitle {{
            font-size: 9px;
            letter-spacing: 2px;
        }}

        .clock-time {{
            font-size: 18px;
        }}

        .metric-clean .value {{
            font-size: 20px;
        }}

        /* Mobile: cuma 2 flyer */
        .hw-flyer-2,
        .hw-flyer-4,
        .hw-flyer-5,
        .hw-flyer-6 {{
            display: none !important;
        }}

        /* Sembunyiin bintang & jaring di mobile */
        .hw-stars,
        .hw-spider-web {{
            display: none !important;
        }}

        /* Fog lebih subtle di mobile */
        .hw-fog {{
            animation-duration: 60s;
            opacity: 0.5;
        }}

        /* Flyer lebih lambat di mobile */
        .hw-flyer-1 {{
            animation-duration: 26s;
            font-size: 22px;
        }}

        .hw-flyer-3 {{
            animation-duration: 32s;
            font-size: 24px;
        }}

        .main .block-container {{
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 0.5rem;
        }}

        div.stButton > button {{
            min-height: 52px;
            font-size: 14px;
        }}

        .so-table thead th {{
            padding: 8px 10px;
            font-size: 9px;
        }}

        .so-table tbody td {{
            padding: 8px 10px;
            font-size: 11px;
        }}
    }}

    @media (max-width: 480px) {{
        .royal-title {{
            font-size: 18px;
        }}

        /* Mobile kecil: cuma 1 flyer */
        .hw-flyer-3 {{
            display: none !important;
        }}

        .hw-flyer-1 {{
            font-size: 20px;
            animation-duration: 30s;
        }}

        .main .block-container {{
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }}
    }}

    /* Accessibility */
    @media (prefers-reduced-motion: reduce) {{
        .hw-flyer,
        .hw-stars,
        .hw-fog,
        .hw-spider-web {{
            display: none !important;
        }}

        *,
        *::before,
        *::after {{
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
        }}
    }}

    /* iOS: pake GPU layer */
    @media (hover: none) and (pointer: coarse) {{
        .hw-flyer {{
            transform: translateZ(0);
            backface-visibility: hidden;
        }}
    }}

    /* Utility */
    .fade-in-up {{
        animation: fadeInUp 0.4s ease-out;
    }}

    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
</style>
"""

    return _css