"""
🎃 HALLOWEEN THEME
=================
Tema Halloween dengan animasi:
- Background: kabut bergerak + bintang + kelelawar terbang
- Header: pumpkin glow + flicker
- Card: pulse + glow
- Button: hover effects
- Ornamen: spider web
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
# 🎃 CSS FULL
# =========================================================
def get_css():
    return """
<style>
    /* ============================================
    🎃 IMPORT FONTS
    ============================================ */
    @import url('https://fonts.googleapis.com/css2?family=Creepster&family=Cinzel:wght@400;600;700;900&family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700;900&display=swap');

    /* ============================================
    🎃 ROOT VARIABLES
    ============================================ */
    :root {
        --pumpkin: #FF6B1A;
        --pumpkin-dark: #D97706;
        --pumpkin-light: #FDBA74;
        --witch: #6B21A8;
        --witch-dark: #4C1D95;
        --witch-light: #A855F7;
        --midnight: #0F0A1E;
        --midnight-2: #1A0D2E;
        --slime: #84CC16;
        --blood: #DC2626;
        --candy: #FBBF24;
        --ghost: #F8F5F0;
        --ghost-dim: #A89B8E;
    }

    /* ============================================
    🎃 BACKGROUND KABUT + BINTANG
    ============================================ */
    .stApp {
        background: 
            radial-gradient(circle at 15% 10%, rgba(107, 33, 168, 0.35) 0%, transparent 45%),
            radial-gradient(circle at 85% 90%, rgba(255, 107, 26, 0.25) 0%, transparent 45%),
            radial-gradient(circle at 50% 50%, rgba(76, 29, 149, 0.2) 0%, transparent 60%),
            linear-gradient(180deg, #05030F 0%, #0F0A1E 30%, #1A0D2E 60%, #05030F 100%);
        background-attachment: fixed;
        color: var(--ghost);
        font-family: 'Quicksand', sans-serif;
        min-height: 100vh;
        overflow-x: hidden;
    }

    /* 🌫️ KABUT BERGERAK */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: 
            radial-gradient(ellipse 800px 400px at 20% 30%, rgba(107, 33, 168, 0.15), transparent),
            radial-gradient(ellipse 600px 300px at 80% 70%, rgba(255, 107, 26, 0.1), transparent);
        animation: fogMove 20s infinite ease-in-out;
        pointer-events: none;
        z-index: 0;
    }

    @keyframes fogMove {
        0%, 100% { transform: translateX(0) translateY(0); opacity: 0.6; }
        50% { transform: translateX(30px) translateY(-20px); opacity: 1; }
    }

    /* ⭐ BINTANG BERKEDIP */
    .stApp::after {
        content: "";
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background-image: 
            radial-gradient(2px 2px at 20% 30%, rgba(255, 255, 255, 0.6), transparent),
            radial-gradient(2px 2px at 60% 70%, rgba(255, 255, 255, 0.4), transparent),
            radial-gradient(1px 1px at 40% 50%, rgba(255, 255, 255, 0.5), transparent),
            radial-gradient(1px 1px at 80% 20%, rgba(255, 255, 255, 0.5), transparent),
            radial-gradient(2px 2px at 10% 80%, rgba(255, 255, 255, 0.4), transparent),
            radial-gradient(1px 1px at 90% 60%, rgba(255, 255, 255, 0.5), transparent);
        background-size: 200% 200%;
        animation: starsTwinkle 8s infinite alternate;
        pointer-events: none;
        z-index: 0;
    }

    @keyframes starsTwinkle {
        0% { opacity: 0.4; transform: scale(1); }
        100% { opacity: 0.8; transform: scale(1.05); }
    }

    /* 🦇 KELELAWAR TERBANG */
    .bat-animation {
        position: fixed;
        top: 15%;
        left: -50px;
        font-size: 30px;
        animation: batFly 15s infinite linear;
        z-index: 1;
        pointer-events: none;
        filter: drop-shadow(0 0 10px rgba(255, 107, 26, 0.5));
    }

    .bat-animation:nth-child(2) {
        top: 40%;
        font-size: 20px;
        animation-duration: 20s;
        animation-delay: 3s;
    }

    .bat-animation:nth-child(3) {
        top: 70%;
        font-size: 25px;
        animation-duration: 25s;
        animation-delay: 6s;
    }

    @keyframes batFly {
        0% { transform: translateX(0) translateY(0) rotate(0deg); opacity: 0; }
        10% { opacity: 1; }
        50% { transform: translateX(50vw) translateY(-50px) rotate(10deg); }
        90% { opacity: 1; }
        100% { transform: translateX(100vw) translateY(20px) rotate(-10deg); opacity: 0; }
    }

    /* 🕸️ SPIDER WEB CORNER */
    .spider-web {
        position: fixed;
        top: 0;
        right: 0;
        width: 150px;
        height: 150px;
        background-image: 
            radial-gradient(circle, rgba(255, 107, 26, 0.4) 1px, transparent 1px),
            linear-gradient(45deg, transparent 48%, rgba(255, 107, 26, 0.3) 49%, rgba(255, 107, 26, 0.3) 51%, transparent 52%),
            linear-gradient(-45deg, transparent 48%, rgba(255, 107, 26, 0.3) 49%, rgba(255, 107, 26, 0.3) 51%, transparent 52%);
        background-size: 20px 20px, 40px 40px, 40px 40px;
        clip-path: polygon(100% 0, 100% 100%, 0 0);
        opacity: 0.4;
        pointer-events: none;
        z-index: 1;
        animation: webShimmer 3s infinite;
    }

    @keyframes webShimmer {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.6; }
    }

    /* ============================================
    🎃 SCROLLBAR
    ============================================ */
    ::-webkit-scrollbar { width: 12px; height: 12px; }
    ::-webkit-scrollbar-track { background: #05030F; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--pumpkin), var(--pumpkin-dark));
        border-radius: 6px;
        border: 2px solid #05030F;
    }

    /* ============================================
    🎃 HEADER
    ============================================ */
    .royal-header {
        position: relative;
        background: linear-gradient(135deg, #0F0A1E 0%, #4C1D95 50%, #0F0A1E 100%);
        border: 3px double var(--pumpkin);
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 
            0 0 40px rgba(255, 107, 26, 0.4),
            0 0 80px rgba(107, 33, 168, 0.3),
            inset 0 0 30px rgba(0, 0, 0, 0.7);
        overflow: hidden;
        z-index: 1;
        animation: headerPulse 4s infinite ease-in-out;
    }

    @keyframes headerPulse {
        0%, 100% { box-shadow: 0 0 40px rgba(255, 107, 26, 0.4), 0 0 80px rgba(107, 33, 168, 0.3), inset 0 0 30px rgba(0, 0, 0, 0.7); }
        50% { box-shadow: 0 0 60px rgba(255, 107, 26, 0.7), 0 0 100px rgba(107, 33, 168, 0.5), inset 0 0 30px rgba(0, 0, 0, 0.7); }
    }

    .royal-header::before {
        content: "🎃 👻 🦇 🕷️ 🕸️ 🧙 💀";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        color: var(--pumpkin);
        font-size: 12px;
        letter-spacing: 30px;
        padding-left: 30px;
        animation: headerFlicker 3s infinite ease-in-out;
    }

    @keyframes headerFlicker {
        0%, 100% { opacity: 0.5; text-shadow: 0 0 5px var(--pumpkin); }
        50% { opacity: 1; text-shadow: 0 0 15px var(--pumpkin), 0 0 25px var(--pumpkin); }
    }

    .royal-title {
        font-family: 'Creepster', 'Cinzel', serif;
        font-size: 32px;
        font-weight: 900;
        color: var(--pumpkin);
        text-align: center;
        margin: 0;
        letter-spacing: 3px;
        text-shadow: 
            0 0 20px rgba(255, 107, 26, 0.9),
            0 0 40px rgba(255, 107, 26, 0.5),
            2px 2px 4px rgba(0, 0, 0, 0.9);
        animation: titleGlow 4s infinite ease-in-out;
    }

    @keyframes titleGlow {
        0%, 100% { text-shadow: 0 0 20px rgba(255, 107, 26, 0.9), 0 0 40px rgba(255, 107, 26, 0.5), 2px 2px 4px rgba(0, 0, 0, 0.9); }
        50% { text-shadow: 0 0 30px rgba(255, 107, 26, 1), 0 0 60px rgba(255, 107, 26, 0.7), 2px 2px 4px rgba(0, 0, 0, 0.9); }
    }

    .royal-subtitle {
        font-family: 'Quicksand', sans-serif;
        font-size: 12px;
        color: var(--pumpkin-light);
        text-align: center;
        margin-top: 6px;
        letter-spacing: 3px;
        text-transform: uppercase;
    }

    .royal-ornament {
        position: absolute;
        color: var(--pumpkin);
        font-size: 20px;
        filter: drop-shadow(0 0 8px var(--pumpkin));
        animation: ornamentFloat 3s infinite ease-in-out;
    }

    @keyframes ornamentFloat {
        0%, 100% { transform: translateY(0) rotate(0deg); }
        50% { transform: translateY(-3px) rotate(5deg); }
    }

    .royal-orn-tl { top: 8px; left: 12px; }
    .royal-orn-tr { top: 8px; right: 12px; animation-delay: 0.5s; }
    .royal-orn-bl { bottom: 8px; left: 12px; animation-delay: 1s; }
    .royal-orn-br { bottom: 8px; right: 12px; animation-delay: 1.5s; }

    /* ============================================
    🎃 CLOCK
    ============================================ */
    .header-clock {
        text-align: center;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px dashed rgba(255, 107, 26, 0.4);
    }

    .clock-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 900;
        color: var(--candy);
        letter-spacing: 3px;
        text-shadow: 0 0 15px rgba(251, 191, 36, 0.8);
        animation: clockGlow 3s infinite ease-in-out;
    }

    @keyframes clockGlow {
        0%, 100% { text-shadow: 0 0 15px rgba(251, 191, 36, 0.8); }
        50% { text-shadow: 0 0 25px rgba(251, 191, 36, 1), 0 0 40px rgba(251, 191, 36, 0.6); }
    }

    .clock-date {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--pumpkin-light);
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 4px;
    }

    /* ============================================
    🎃 METRIC CARD
    ============================================ */
    .metric-card-v2 {
        position: relative;
        background: linear-gradient(135deg, #0F0A1E 0%, #1A0D2E 100%);
        border: 2px solid var(--pumpkin-dark);
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.7);
        overflow: hidden;
        transition: all 0.3s ease;
        z-index: 1;
        animation: cardFloat 6s infinite ease-in-out;
    }

    @keyframes cardFloat {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-3px); }
    }

    .metric-card-v2::before {
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 5px; height: 100%;
        background: var(--accent-color, var(--pumpkin));
        box-shadow: 0 0 15px var(--accent-color, var(--pumpkin));
        animation: barPulse 2s infinite ease-in-out;
    }

    @keyframes barPulse {
        0%, 100% { opacity: 0.7; }
        50% { opacity: 1; box-shadow: 0 0 25px var(--accent-color, var(--pumpkin)); }
    }

    .metric-card-v2:hover {
        transform: translateY(-6px) scale(1.02);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8), 0 0 30px var(--accent-color, rgba(255, 107, 26, 0.4));
    }

    .metric-label-v2 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        font-weight: 700;
        color: var(--ghost-dim);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .metric-value-v2 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 900;
        color: var(--pumpkin);
        text-shadow: 0 0 15px rgba(255, 107, 26, 0.6);
        line-height: 1.1;
        word-wrap: break-word;
    }

    .metric-sub-v2 {
        font-family: 'Quicksand', sans-serif;
        font-size: 10px;
        color: var(--ghost-dim);
        margin-top: 6px;
        font-weight: 600;
    }

    /* ============================================
    🎃 BUTTONS
    ============================================ */
    div.stButton > button,
    div.stFormSubmitButton > button,
    div.stDownloadButton > button {
        background: linear-gradient(135deg, #1A0D2E 0%, #4C1D95 100%) !important;
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
    }

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover,
    div.stDownloadButton > button:hover {
        background: linear-gradient(135deg, var(--pumpkin-dark) 0%, var(--pumpkin) 100%) !important;
        color: #FFFFFF !important;
        border-color: var(--candy) !important;
        box-shadow: 0 0 25px rgba(255, 107, 26, 0.8), 0 0 50px rgba(255, 107, 26, 0.4) !important;
        transform: translateY(-2px) !important;
    }

    div.stButton > button:active,
    div.stFormSubmitButton > button:active {
        transform: translateY(1px) scale(0.98) !important;
    }

    /* ============================================
    🎃 INPUT FIELDS
    ============================================ */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: #0F0A1E !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        min-height: 48px !important;
        transition: all 0.3s ease !important;
    }

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        border-color: var(--pumpkin) !important;
        box-shadow: 0 0 15px rgba(255, 107, 26, 0.5) !important;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="select"] span,
    div[data-baseweb="textarea"] textarea {
        color: var(--pumpkin-light) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }

    label,
    div[data-testid="stWidgetLabel"] label {
        color: var(--pumpkin-light) !important;
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    /* ============================================
    🎃 TABS
    ============================================ */
    div[data-baseweb="tab-list"] {
        background: rgba(15, 10, 30, 0.8) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        border: 1px solid var(--pumpkin-dark) !important;
    }

    div[data-baseweb="tab-list"] button {
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
    }

    div[data-baseweb="tab-list"] button[aria-selected="true"] {
        background: linear-gradient(135deg, var(--pumpkin-dark) 0%, var(--pumpkin) 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 15px rgba(255, 107, 26, 0.6) !important;
    }

    /* ============================================
    🎃 EXPANDER
    ============================================ */
    div[data-testid="stExpander"] {
        background: rgba(15, 10, 30, 0.8) !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        margin-bottom: 12px !important;
    }

    div[data-testid="stExpander"] summary {
        background: linear-gradient(90deg, rgba(76, 29, 149, 0.5) 0%, rgba(255, 107, 26, 0.3) 100%) !important;
        color: var(--pumpkin-light) !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 16px 18px !important;
        min-height: 52px !important;
        transition: all 0.3s ease !important;
        -webkit-tap-highlight-color: transparent !important;
    }

    div[data-testid="stExpander"] summary:hover {
        background: linear-gradient(90deg, rgba(76, 29, 149, 0.7) 0%, rgba(255, 107, 26, 0.5) 100%) !important;
    }

    /* ============================================
    🎃 DATAFRAME
    ============================================ */
    div[data-testid="stDataFrame"] {
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    /* ============================================
    🎃 ALERT
    ============================================ */
    div[data-testid="stAlert"] {
        background: rgba(15, 10, 30, 0.95) !important;
        border: 2px solid var(--pumpkin-dark) !important;
        border-radius: 12px !important;
    }

    /* ============================================
    🎃 SIDEBAR
    ============================================ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #05030F 0%, #1A0D2E 100%) !important;
        border-right: 2px solid var(--pumpkin-dark) !important;
    }

    /* ============================================
    🎃 FADE IN
    ============================================ */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in-up {
        animation: fadeInUp 0.6s ease-out forwards;
    }

    /* ============================================
    🎃 COPYRIGHT
    ============================================ */
    .copyright-footer {
        text-align: center;
        margin-top: 60px;
        padding-top: 20px;
        border-top: 1px dashed rgba(255, 107, 26, 0.3);
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: var(--ghost-dim);
        letter-spacing: 1.5px;
    }

    /* ============================================
    🎃 MOBILE RESPONSIVE
    ============================================ */
    @media (max-width: 768px) {
        .royal-header { padding: 18px 16px; border-radius: 14px; }
        .royal-title { font-size: 22px; letter-spacing: 2px; }
        .royal-subtitle { font-size: 10px; }
        .clock-time { font-size: 18px; }
        .metric-value-v2 { font-size: 22px; }
        
        .main .block-container {
            padding: 0.5rem 1rem 5rem 1rem !important;
        }
        
        div.stButton > button,
        div.stFormSubmitButton > button {
            min-height: 56px !important;
            font-size: 15px !important;
            padding: 16px 20px !important;
        }
    }

    @media (max-width: 480px) {
        .royal-title { font-size: 18px; }
        .metric-value-v2 { font-size: 20px; }
        .main .block-container {
            padding: 0.25rem 0.75rem 4rem 0.75rem !important;
        }
    }

    /* ============================================
    🎃 iOS SAFE AREA + SCROLL NATURAL
    ============================================ */
    body {
        padding-top: env(safe-area-inset-top, 0);
        padding-bottom: env(safe-area-inset-bottom, 0);
    }

    html {
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
    }

    body {
        overscroll-behavior-y: contain;
    }
</style>
"""