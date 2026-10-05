"""
🎃 HALLOWEEN THEME v2
====================
Multi-time variant:
- 🌅 Pagi (04-10)
- ☀️ Siang (10-15)
- 🌇 Sore (15-18)
- 🌆 Malam (18-22)
- 🌙 Midnight (22-04)

Struktur:
- Potong 1: Setup + Theme Varian (INI)
- Potong 2: CSS Base
- Potong 3: CSS Header + Card
- Potong 4: CSS Button + Form
- Potong 5: CSS Animasi
- Potong 6: CSS Responsive
"""

# =========================================================
# 🎃 THEME INFO
# =========================================================
THEME_INFO = {
    "name": "Halloween",
    "emoji": "🎃",
    "primary": "#FF6B1A",
    "secondary": "#6B21A8",
    "dark": "#0F0A1E",
    "light": "#F8F5F0",
}


# =========================================================
# 🌅 TIME VARIANTS (5 varian warna)
# =========================================================
THEME_VARIANTS = {
    # 🌅 PAGI (04:00 - 10:00)
    "pagi": {
        "primary": "#FFA500",
        "primary_dark": "#E67E22",
        "primary_light": "#FFD180",
        "secondary": "#FFD700",
        "secondary_dark": "#F9A825",
        "accent": "#FFEB3B",
        "bg_top": "#1A1F3A",
        "bg_bot": "#4A2511",
        "bg_glow_1": "rgba(255, 215, 0, 0.30)",
        "bg_glow_2": "rgba(255, 165, 0, 0.25)",
        "text": "#FFF8E1",
        "text_dim": "#C9A961",
        "emoji": "🌅",
        "greeting": "Selamat Pagi",
    },
    
    # ☀️ SIANG (10:00 - 15:00)
    "siang": {
        "primary": "#FF6B1A",
        "primary_dark": "#D97706",
        "primary_light": "#FDBA74",
        "secondary": "#84CC16",
        "secondary_dark": "#65A30D",
        "accent": "#FB923C",
        "bg_top": "#0F0A1E",
        "bg_bot": "#1A2F1E",
        "bg_glow_1": "rgba(255, 107, 26, 0.30)",
        "bg_glow_2": "rgba(132, 204, 22, 0.20)",
        "text": "#F8F5F0",
        "text_dim": "#A89B8E",
        "emoji": "☀️",
        "greeting": "Selamat Siang",
    },
    
    # 🌇 SORE (15:00 - 18:00)
    "sore": {
        "primary": "#FF6B1A",
        "primary_dark": "#C2410C",
        "primary_light": "#FDBA74",
        "secondary": "#DC2626",
        "secondary_dark": "#991B1B",
        "accent": "#F97316",
        "bg_top": "#1A0D2E",
        "bg_bot": "#4A1810",
        "bg_glow_1": "rgba(255, 107, 26, 0.35)",
        "bg_glow_2": "rgba(220, 38, 38, 0.25)",
        "text": "#FEF2F2",
        "text_dim": "#B89B8E",
        "emoji": "🌇",
        "greeting": "Selamat Sore",
    },
    
    # 🌆 MALAM (18:00 - 22:00)
    "malam": {
        "primary": "#FF6B1A",
        "primary_dark": "#D97706",
        "primary_light": "#FDBA74",
        "secondary": "#6B21A8",
        "secondary_dark": "#4C1D95",
        "accent": "#FBBF24",
        "bg_top": "#0F0A1E",
        "bg_bot": "#1A0D2E",
        "bg_glow_1": "rgba(107, 33, 168, 0.35)",
        "bg_glow_2": "rgba(255, 107, 26, 0.25)",
        "text": "#F8F5F0",
        "text_dim": "#A89B8E",
        "emoji": "🌆",
        "greeting": "Selamat Malam",
    },
    
    # 🌙 MIDNIGHT (22:00 - 04:00)
    "midnight": {
        "primary": "#A855F7",
        "primary_dark": "#7C3AED",
        "primary_light": "#D8B4FE",
        "secondary": "#4C1D95",
        "secondary_dark": "#2E1065",
        "accent": "#C4B5FD",
        "bg_top": "#05030F",
        "bg_bot": "#0A0514",
        "bg_glow_1": "rgba(168, 85, 247, 0.35)",
        "bg_glow_2": "rgba(76, 29, 149, 0.30)",
        "text": "#E9D5FF",
        "text_dim": "#8B7BA8",
        "emoji": "🌙",
        "greeting": "Selamat Tidur",
    },
}


# =========================================================
# 🎯 GET VARIANT
# =========================================================
def get_variant(variant="malam"):
    """
    Get variant config. Fallback ke 'malam' kalau gak ada.
    """
    return THEME_VARIANTS.get(variant, THEME_VARIANTS["malam"])


# =========================================================
# 🎨 GET CSS (FUNGSI UTAMA)
# =========================================================
def get_css(variant="malam"):
    """
    Return CSS string dengan variant warna.
    
    Args:
        variant: 'pagi', 'siang', 'sore', 'malam', 'midnight'
    """
    _v = get_variant(variant)
    
    # Build CSS dengan f-string
    _css = f"""
<style>
    /* ============================================
    🎃 POTONG 2: CSS BASE
    ============================================ */
    
    /* IMPORT FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Creepster&family=Cinzel:wght@400;600;700;900&family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700;900&display=swap');

    /* ROOT VARIABLES — DYNAMIC BY VARIANT */
    :root {{
        --pumpkin: {_v['primary']};
        --pumpkin-dark: {_v['primary_dark']};
        --pumpkin-light: {_v['primary_light']};
        --witch: {_v['secondary']};
        --witch-dark: {_v['secondary_dark']};
        --candy: {_v['accent']};
        --midnight: {_v['bg_top']};
        --midnight-2: {_v['bg_bot']};
        --ghost: {_v['text']};
        --ghost-dim: {_v['text_dim']};
        --bg-glow-1: {_v['bg_glow_1']};
        --bg-glow-2: {_v['bg_glow_2']};
    }}

    /* BACKGROUND KABUT + BINTANG */
    .stApp {{
        background: 
            radial-gradient(circle at 15% 10%, var(--bg-glow-1) 0%, transparent 45%),
            radial-gradient(circle at 85% 90%, var(--bg-glow-2) 0%, transparent 45%),
            radial-gradient(circle at 50% 50%, var(--bg-glow-1) 0%, transparent 60%),
            linear-gradient(180deg, var(--midnight) 0%, var(--midnight-2) 50%, var(--midnight) 100%);
        background-attachment: fixed;
        color: var(--ghost);
        font-family: 'Quicksand', sans-serif;
        min-height: 100vh;
        overflow-x: hidden;
        transition: background 2s ease;
    }}

    /* 🌫️ KABUT BERGERAK (SLOW + GPU) */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: 
            radial-gradient(ellipse 800px 400px at 20% 30%, var(--bg-glow-1), transparent),
            radial-gradient(ellipse 600px 300px at 80% 70%, var(--bg-glow-2), transparent);
        animation: fogMove 40s infinite ease-in-out;
        pointer-events: none;
        z-index: 0;
        will-change: transform, opacity;
        transform: translateZ(0);
    }}

    @keyframes fogMove {{
        0%, 100% {{ transform: translate3d(0, 0, 0); opacity: 0.6; }}
        50% {{ transform: translate3d(30px, -20px, 0); opacity: 0.9; }}
    }}

    /* ⭐ BINTANG BERKEDIP (SLOW) */
    .stApp::after {{
        content: "";
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background-image: 
            radial-gradient(1px 1px at 20% 30%, rgba(255, 255, 255, 0.5), transparent),
            radial-gradient(1px 1px at 60% 70%, rgba(255, 255, 255, 0.4), transparent),
            radial-gradient(1px 1px at 40% 50%, rgba(255, 255, 255, 0.4), transparent),
            radial-gradient(1px 1px at 80% 20%, rgba(255, 255, 255, 0.4), transparent);
        animation: starsTwinkle 12s infinite alternate;
        pointer-events: none;
        z-index: 0;
        will-change: opacity;
    }}

    @keyframes starsTwinkle {{
        0% {{ opacity: 0.3; }}
        100% {{ opacity: 0.6; }}
    }}

    /* SCROLLBAR */
    ::-webkit-scrollbar {{ width: 12px; height: 12px; }}
    ::-webkit-scrollbar-track {{ background: var(--midnight); }}
    ::-webkit-scrollbar-thumb {{
        background: linear-gradient(180deg, var(--pumpkin), var(--pumpkin-dark));
        border-radius: 6px;
        border: 2px solid var(--midnight);
    }}

    /* 🦇 KELELAWAR TERBANG (1 AJA, GPU) */
    .bat-animation {{
        position: fixed;
        top: 15%;
        left: -50px;
        font-size: 25px;
        animation: batFly 20s infinite linear;
        z-index: 1;
        pointer-events: none;
        will-change: transform;
        transform: translateZ(0);
    }}

    .bat-animation:nth-child(2),
    .bat-animation:nth-child(3) {{
        display: none;
    }}

    @keyframes batFly {{
        0% {{ transform: translate3d(0, 0, 0); opacity: 0; }}
        10% {{ opacity: 1; }}
        90% {{ opacity: 1; }}
        100% {{ transform: translate3d(100vw, 20px, 0); opacity: 0; }}
    }}

    /* 🕸️ SPIDER WEB CORNER */
    .spider-web {{
        position: fixed;
        top: 0;
        right: 0;
        width: 150px;
        height: 150px;
        background-image: 
            radial-gradient(circle, var(--pumpkin) 1px, transparent 1px),
            linear-gradient(45deg, transparent 48%, var(--pumpkin-light) 49%, var(--pumpkin-light) 51%, transparent 52%),
            linear-gradient(-45deg, transparent 48%, var(--pumpkin-light) 49%, var(--pumpkin-light) 51%, transparent 52%);
        background-size: 20px 20px, 40px 40px, 40px 40px;
        clip-path: polygon(100% 0, 100% 100%, 0 0);
        opacity: 0.35;
        pointer-events: none;
        z-index: 1;
        animation: webShimmer 4s infinite;
    }}

    @keyframes webShimmer {{
        0%, 100% {{ opacity: 0.3; }}
        50% {{ opacity: 0.5; }}
    }}

    /* ============================================
    🎃 POTONG 3: HEADER + CARD + MENU CARD
    ============================================ */

    /* HEADER — ROYAL PUMPKIN */
    .royal-header {{
        position: relative;
        background: linear-gradient(135deg, var(--midnight) 0%, var(--witch-dark) 50%, var(--midnight) 100%);
        border: 3px double var(--pumpkin);
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 
            0 0 40px var(--bg-glow-1),
            0 0 80px var(--bg-glow-2),
            inset 0 0 30px rgba(0, 0, 0, 0.7);
        overflow: hidden;
        z-index: 1;
        animation: headerGlow 8s infinite ease-in-out;
        will-change: box-shadow;
    }}

    @keyframes headerGlow {{
        0%, 100% {{ 
            box-shadow: 0 0 40px var(--bg-glow-1), 0 0 80px var(--bg-glow-2), inset 0 0 30px rgba(0, 0, 0, 0.7);
        }}
        50% {{ 
            box-shadow: 0 0 60px var(--bg-glow-1), 0 0 100px var(--bg-glow-2), inset 0 0 30px rgba(0, 0, 0, 0.7);
        }}
    }}

    .royal-header::before {{
        content: "🎃 👻 🦇 🕷️ 🕸️ 🧙 💀";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        color: var(--pumpkin);
        font-size: 12px;
        letter-spacing: 30px;
        padding-left: 30px;
        animation: headerFlicker 3s infinite ease-in-out;
    }}

    @keyframes headerFlicker {{
        0%, 100% {{ opacity: 0.5; text-shadow: 0 0 5px var(--pumpkin); }}
        50% {{ opacity: 1; text-shadow: 0 0 15px var(--pumpkin), 0 0 25px var(--pumpkin); }}
    }}

    .royal-title {{
        font-family: 'Creepster', 'Cinzel', serif;
        font-size: 32px;
        font-weight: 900;
        color: var(--pumpkin);
        text-align: center;
        margin: 0;
        letter-spacing: 3px;
        text-shadow: 
            0 0 20px var(--pumpkin),
            0 0 40px var(--bg-glow-1),
            2px 2px 4px rgba(0, 0, 0, 0.9);
        animation: titleGlow 6s infinite ease-in-out;
    }}

    @keyframes titleGlow {{
        0%, 100% {{ text-shadow: 0 0 20px var(--pumpkin), 0 0 40px var(--bg-glow-1), 2px 2px 4px rgba(0, 0, 0, 0.9); }}
        50% {{ text-shadow: 0 0 30px var(--pumpkin), 0 0 60px var(--bg-glow-1), 2px 2px 4px rgba(0, 0, 0, 0.9); }}
    }}

    .royal-subtitle {{
        font-family: 'Quicksand', sans-serif;
        font-size: 12px;
        color: var(--pumpkin-light);
        text-align: center;
        margin-top: 6px;
        letter-spacing: 3px;
        text-transform: uppercase;
    }}

    .royal-ornament {{
        position: absolute;
        color: var(--pumpkin);
        font-size: 20px;
        filter: drop-shadow(0 0 8px var(--pumpkin));
        animation: ornamentFloat 3s infinite ease-in-out;
    }}

    @keyframes ornamentFloat {{
        0%, 100% {{ transform: translateY(0) rotate(0deg); }}
        50% {{ transform: translateY(-3px) rotate(5deg); }}
    }}

    .royal-orn-tl {{ top: 8px; left: 12px; }}
    .royal-orn-tr {{ top: 8px; right: 12px; animation-delay: 0.5s; }}
    .royal-orn-bl {{ bottom: 8px; left: 12px; animation-delay: 1s; }}
    .royal-orn-br {{ bottom: 8px; right: 12px; animation-delay: 1.5s; }}

    /* CLOCK */
    .header-clock {{
        text-align: center;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px dashed rgba(255, 107, 26, 0.4);
    }}

    .clock-time {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 900;
        color: var(--candy);
        letter-spacing: 3px;
        text-shadow: 0 0 15px var(--candy);
        animation: clockGlow 4s infinite ease-in-out;
    }}

    @keyframes clockGlow {{
        0%, 100% {{ text-shadow: 0 0 15px var(--candy); }}
        50% {{ text-shadow: 0 0 25px var(--candy), 0 0 40px var(--bg-glow-1); }}
    }}

    .clock-date {{
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--pumpkin-light);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 4px;
    }}

    /* METRIC CARD */
    .metric-card-v2 {{
        position: relative;
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border: 2px solid var(--pumpkin-dark);
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.7);
        overflow: hidden;
        transition: all 0.3s ease;
        z-index: 1;
    }}

    .metric-card-v2::before {{
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 5px; height: 100%;
        background: var(--accent-color, var(--pumpkin));
        box-shadow: 0 0 15px var(--accent-color, var(--pumpkin));
        animation: barPulse 2s infinite ease-in-out;
    }}

    @keyframes barPulse {{
        0%, 100% {{ opacity: 0.7; }}
        50% {{ opacity: 1; box-shadow: 0 0 25px var(--accent-color, var(--pumpkin)); }}
    }}

    .metric-card-v2:hover {{
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8), 0 0 30px var(--accent-color, var(--bg-glow-1));
    }}

    .metric-label-v2 {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 700;
        color: var(--ghost-dim);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }}

    .metric-value-v2 {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 900;
        color: var(--pumpkin);
        text-shadow: 0 0 15px var(--bg-glow-1);
        line-height: 1.1;
        word-wrap: break-word;
    }}

    .metric-sub-v2 {{
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
        margin-top: 6px;
        font-weight: 600;
    }}

    /* ============================================
    🎃 MENU CARD (FIX — yang tadi aneh)
    ============================================ */
    .menu-card-v2 {{
        position: relative;
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%);
        border: 2px solid var(--pumpkin-dark);
        border-radius: 16px;
        padding: 24px 18px;
        text-align: center;
        transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1);
        cursor: pointer;
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
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7), 0 0 30px var(--bg-glow-1);
        transform: translateY(-6px) scale(1.02);
    }}

    .menu-icon-v2 {{
        font-size: 48px;
        margin-bottom: 12px;
        filter: drop-shadow(0 0 15px var(--pumpkin));
        text-align: center;
        line-height: 1;
        display: block;
        width: 100%;
    }}

    .menu-title-v2 {{
        font-family: 'Cinzel', serif;
        font-size: 14px;
        font-weight: 900;
        color: var(--pumpkin-light);
        letter-spacing: 2px;
        margin-bottom: 6px;
        text-transform: uppercase;
        text-align: center;
        width: 100%;
    }}

    .menu-desc-v2 {{
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
        line-height: 1.5;
        text-align: center;
        width: 100%;
    }}

    /* ============================================
    🎃 POTONG 4: BUTTON + FORM + TABS + EXPANDER
    ============================================ */

    /* ============================================
    BUTTON — TOUCH FRIENDLY
    ============================================ */
    div.stButton > button,
    div.stFormSubmitButton > button,
    div.stDownloadButton > button {{
        background: linear-gradient(135deg, var(--midnight-2) 0%, var(--witch-dark) 100%) !important;
        color: var(--pumpkin-light) !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 14px 20px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6) !important;
        width: 100% !important;
        min-height: 52px !important;
        min-width: 48px !important;
        cursor: pointer !important;
        -webkit-tap-highlight-color: transparent !important;
        touch-action: manipulation !important;
    }}

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover,
    div.stDownloadButton > button:hover {{
        background: linear-gradient(135deg, var(--pumpkin-dark) 0%, var(--pumpkin) 100%) !important;
        color: #FFFFFF !important;
        border-color: var(--candy) !important;
        box-shadow: 
            0 0 25px var(--bg-glow-1),
            0 0 50px var(--bg-glow-2) !important;
        transform: translateY(-2px) !important;
    }}

    div.stButton > button:active,
    div.stFormSubmitButton > button:active {{
        transform: translateY(1px) scale(0.98) !important;
    }}

    /* ============================================
    INPUT FIELDS
    ============================================ */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {{
        background-color: var(--midnight) !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        min-height: 48px !important;
        transition: all 0.3s ease !important;
    }}

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {{
        border-color: var(--pumpkin) !important;
        box-shadow: 0 0 15px var(--bg-glow-1) !important;
    }}

    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span,
    div[data-baseweb="textarea"] textarea {{
        color: var(--pumpkin-light) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }}

    label,
    div[data-testid="stWidgetLabel"] label {{
        color: var(--pumpkin-light) !important;
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }}

    /* ============================================
    TABS
    ============================================ */
    div[data-baseweb="tab-list"] {{
        background: rgba(15, 10, 30, 0.8) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        border: 1px solid var(--pumpkin-dark) !important;
        gap: 4px !important;
    }}

    div[data-baseweb="tab-list"] button {{
        background: transparent !important;
        color: var(--ghost-dim) !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        min-height: 48px !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        -webkit-tap-highlight-color: transparent !important;
    }}

    div[data-baseweb="tab-list"] button:hover {{
        color: var(--pumpkin-light) !important;
        background: rgba(255, 107, 26, 0.1) !important;
    }}

    div[data-baseweb="tab-list"] button[aria-selected="true"] {{
        background: linear-gradient(135deg, var(--pumpkin-dark) 0%, var(--pumpkin) 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 15px var(--bg-glow-1) !important;
    }}

    div[data-baseweb="tab-highlight"] {{
        background-color: var(--pumpkin) !important;
        box-shadow: 0 0 15px var(--pumpkin) !important;
    }}

    /* ============================================
    EXPANDER
    ============================================ */
    div[data-testid="stExpander"] {{
        background: rgba(15, 10, 30, 0.8) !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        margin-bottom: 12px !important;
    }}

    div[data-testid="stExpander"] summary {{
        background: linear-gradient(90deg, var(--witch-dark) 0%, var(--bg-glow-2) 100%) !important;
        color: var(--pumpkin-light) !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 16px 18px !important;
        min-height: 52px !important;
        transition: all 0.3s ease !important;
        -webkit-tap-highlight-color: transparent !important;
        border-bottom: 1px dashed rgba(255, 107, 26, 0.3) !important;
    }}

    div[data-testid="stExpander"] summary:hover {{
        background: linear-gradient(90deg, var(--witch) 0%, var(--pumpkin-dark) 100%) !important;
    }}

    div[data-testid="stExpander"] summary svg {{
        fill: var(--pumpkin) !important;
        color: var(--pumpkin) !important;
    }}

    /* ============================================
    DATAFRAME
    ============================================ */
    div[data-testid="stDataFrame"] {{
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5) !important;
    }}

    /* ============================================
    ALERT
    ============================================ */
    div[data-testid="stAlert"] {{
        background: rgba(15, 10, 30, 0.95) !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.5) !important;
    }}

    /* ============================================
    SIDEBAR
    ============================================ */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, var(--midnight) 0%, var(--midnight-2) 100%) !important;
        border-right: 2px solid var(--pumpkin-dark) !important;
    }}

    [data-testid="stSidebar"] * {{
        color: var(--ghost) !important;
    }}

    /* ============================================
    METRIC (Streamlit native)
    ============================================ */
    div[data-testid="stMetric"] {{
        background: linear-gradient(135deg, var(--midnight) 0%, var(--midnight-2) 100%) !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        padding: 14px !important;
    }}

    div[data-testid="stMetric"] label {{
        color: var(--ghost-dim) !important;
    }}

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: var(--pumpkin) !important;
        text-shadow: 0 0 10px var(--bg-glow-1);
    }}

    /* ============================================
    FILE UPLOADER
    ============================================ */
    div[data-testid="stFileUploader"] {{
        background: rgba(15, 10, 30, 0.8) !important;
        border: 2px dashed var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }}

    div[data-testid="stFileUploader"]:hover {{
        border-color: var(--pumpkin) !important;
        background: rgba(255, 107, 26, 0.05) !important;
    }}

    /* ============================================
    🎃 POTONG 5: RESPONSIVE + MOBILE + iOS
    ============================================ */

    /* ============================================
    📱 MOBILE RESPONSIVE (max 768px)
    ============================================ */
    @media (max-width: 768px) {{
        .royal-header {{
            padding: 18px 16px;
            border-radius: 14px;
        }}

        .royal-title {{
            font-size: 22px;
            letter-spacing: 2px;
        }}

        .royal-subtitle {{
            font-size: 10px;
            letter-spacing: 2px;
        }}

        .clock-time {{
            font-size: 18px;
        }}

        .metric-value-v2 {{
            font-size: 22px;
        }}

        .main .block-container {{
            padding: 0.5rem 1rem 5rem 1rem !important;
        }}

        /* Touch-friendly buttons */
        div.stButton > button,
        div.stFormSubmitButton > button,
        div.stDownloadButton > button {{
            min-height: 56px !important;
            font-size: 15px !important;
            padding: 16px 20px !important;
        }}

        /* Animasi lebih lambat di mobile (hemat battery) */
        .stApp::before {{
            animation-duration: 60s !important;
        }}

        .stApp::after {{
            animation-duration: 20s !important;
        }}

        .bat-animation {{
            font-size: 20px !important;
            animation-duration: 30s !important;
        }}

        .royal-header {{
            animation-duration: 12s !important;
        }}

        /* Menu card smaller di mobile */
        .menu-card-v2 {{
            min-height: 150px;
            padding: 16px 12px;
        }}

        .menu-icon-v2 {{
            font-size: 38px;
        }}

        .menu-title-v2 {{
            font-size: 12px;
        }}
    }}

    /* ============================================
    📱 MOBILE KECIL (max 480px)
    ============================================ */
    @media (max-width: 480px) {{
        .royal-title {{
            font-size: 18px;
        }}

        .royal-subtitle {{
            font-size: 9px;
        }}

        .metric-value-v2 {{
            font-size: 20px;
        }}

        .main .block-container {{
            padding: 0.25rem 0.75rem 4rem 0.75rem !important;
        }}

        .menu-card-v2 {{
            min-height: 130px;
        }}

        .menu-icon-v2 {{
            font-size: 32px;
        }}
    }}

    /* ============================================
    📱 iPHONE KECIL (max 375px — iPhone SE)
    ============================================ */
    @media (max-width: 375px) {{
        .royal-title {{
            font-size: 16px !important;
            letter-spacing: 1px !important;
        }}

        .royal-subtitle {{
            font-size: 8px !important;
        }}

        .metric-value-v2 {{
            font-size: 18px !important;
        }}

        .main .block-container {{
            padding: 0.25rem 0.5rem 4rem 0.5rem !important;
        }}

        div.stButton > button {{
            font-size: 13px !important;
            padding: 12px 14px !important;
        }}
    }}

    /* ============================================
    📱 TABLET (768px - 1024px)
    ============================================ */
    @media (min-width: 768px) and (max-width: 1024px) {{
        .main .block-container {{
            padding-left: 20px !important;
            padding-right: 20px !important;
            max-width: 900px !important;
        }}
    }}

    /* ============================================
    💻 DESKTOP (min 1025px)
    ============================================ */
    @media (min-width: 1025px) {{
        .main .block-container {{
            max-width: 1400px !important;
            padding: 1rem 1.5rem 6rem 1.5rem !important;
        }}
    }}

    /* ============================================
    👆 TOUCH DEVICE (iOS + Android)
    ============================================ */
    @media (hover: none) and (pointer: coarse) {{
        /* Button minimum 48x48 */
        div.stButton > button,
        div.stFormSubmitButton > button,
        div.stDownloadButton > button {{
            min-height: 52px !important;
            min-width: 48px !important;
            font-size: 15px !important;
            padding: 14px 20px !important;
        }}

        /* Select */
        div[data-baseweb="select"] > div {{
            min-height: 48px !important;
        }}

        /* Input: font 16px biar iOS gak zoom */
        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea {{
            font-size: 16px !important;
            min-height: 48px !important;
        }}

        /* Radio & Checkbox touch target */
        div[data-testid="stRadio"] label,
        div[data-testid="stCheckbox"] label {{
            min-height: 48px !important;
            padding: 10px 12px !important;
        }}

        /* Prevent tap highlight */
        * {{
            -webkit-tap-highlight-color: transparent !important;
        }}
    }}

    /* ============================================
    📱 iOS SAFE AREA (notch + home indicator)
    ============================================ */
    body {{
        padding-top: env(safe-area-inset-top, 0);
        padding-bottom: env(safe-area-inset-bottom, 0);
        padding-left: env(safe-area-inset-left, 0);
        padding-right: env(safe-area-inset-right, 0);
    }}

    /* ============================================
    🎃 SCROLL NATURAL
    ============================================ */
    html {{
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
    }}

    body {{
        overscroll-behavior-y: contain;
    }}

    /* ============================================
    🎃 SWIPE GESTURE
    ============================================ */
    [data-testid="stAppViewContainer"] {{
        touch-action: pan-y pan-x !important;
    }}

    /* ============================================
    🎃 PREVENT HORIZONTAL SCROLL
    ============================================ */
    html, body, .stApp {{
        overflow-x: hidden !important;
        max-width: 100vw !important;
    }}

    /* ============================================
    🎃 IMAGE RESPONSIVE
    ============================================ */
    img {{
        max-width: 100% !important;
        height: auto !important;
    }}

    /* ============================================
    🎃 LANDSCAPE MODE MOBILE
    ============================================ */
    @media (max-height: 500px) and (orientation: landscape) {{
        .royal-header {{
            padding: 12px 16px !important;
        }}

        .royal-title {{
            font-size: 18px !important;
        }}

        .clock-time {{
            font-size: 16px !important;
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
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }}
    }}

    /* ============================================
    🎃 FADE IN ANIMATION
    ============================================ */
    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    .fade-in-up {{
        animation: fadeInUp 0.6s ease-out forwards;
    }}

    /* ============================================
    🎃 COPYRIGHT
    ============================================ */
    .copyright-footer {{
        text-align: center;
        margin-top: 60px;
        padding-top: 20px;
        border-top: 1px dashed rgba(255, 107, 26, 0.3);
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: var(--ghost-dim);
        letter-spacing: 1.5px;
    }}

    .copyright-footer::before {{
        content: "🎃 ";
    }}

    .copyright-footer::after {{
        content: " 👻";
    }}
</style>
"""
    
    return _css