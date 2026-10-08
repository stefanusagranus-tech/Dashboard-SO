"""
AI Config — Centralized Configuration
======================================
Config terpusat semua AI (Kurumi, Hana, Yui, Rei, Takumi, Rin).

Fitur:
- Multi-API-key support (tiap AI punya key sendiri)
- Persona per AI
- Model priority per AI
- Daily limit tracking

Karakter:
- AI-0: Kurumi (Chief of Staff) 🎀
- AI-1: Hana (Master Shift) 🌸
- AI-2: Yui (SO Input) 📦
- AI-3: Rei (SO Analisis) 📊
- AI-4: Takumi (IKT Input) 🛠️
- AI-5: Rin (IKT Analisis) ⚔️
"""

# =========================================================
# 🎯 KONFIGURASI SETIAP AI
# =========================================================
AI_CONFIG = {
    # ============================================
    # AI-0: Kurumi — Chief of Staff
    # ============================================
    "ai-0": {
        "name": "Kurumi",
        "emoji": "🎀",
        "description": "Chief of Staff — sapaan, rangkum & kirim laporan",
        "persona": "tokisaki_kurumi",
        "model_priority": [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["greeting", "summary", "send_report"],
        "api_key_secret": "GROQ_API_KEY_KURUMI",  # ✅ Key dari akun 2
        "enabled": True,
    },

    # ============================================
    # AI-1: Hana — Master Shift
    # ============================================
    "ai-1": {
        "name": "Hana",
        "emoji": "🌸",
        "description": "Master Shift — kelola jadwal shift & saran pengganti",
        "model_priority": [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["parse", "chat", "suggest", "conflict"],
        "api_key_secret": "GROQ_API_KEY",  # ✅ Key utama
        "enabled": True,
    },

    # ============================================
    # AI-2: Yui — Stock Opname (Input)
    # ============================================
    "ai-2": {
        "name": "Yui",
        "emoji": "📦",
        "description": "Stock Opname — input data & validasi SO",
        "model_priority": [
            "openai/gpt-oss-20b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["input", "validate", "anomaly"],
        "api_key_secret": "GROQ_API_KEY_YUI",
        "enabled": True,
    },

    # ============================================
    # AI-3: Rei — Stock Opname (Analisis)
    # ============================================
    "ai-3": {
        "name": "Rei",
        "emoji": "📊",
        "description": "Stock Opname — analisis BTSB & laporan",
        "model_priority": [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["analysis", "report", "trend"],
        "api_key_secret": "GROQ_API_KEY",
        "enabled": False,
    },

    # ============================================
    # AI-4: Takumi — IKT Project (Input)
    # ============================================
    "ai-4": {
        "name": "Takumi",
        "emoji": "🛠️",
        "description": "IKT Project — input data & tracking proyek",
        "model_priority": [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["input", "tracking"],
        "api_key_secret": "GROQ_API_KEY",
        "enabled": False,
    },

    # ============================================
    # AI-5: Rin — IKT Project (Analisis)
    # ============================================
    "ai-5": {
        "name": "Rin",
        "emoji": "⚔️",
        "description": "IKT Project — analisis & estimasi proyek",
        "model_priority": [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["analysis", "estimation", "report"],
        "api_key_secret": "GROQ_API_KEY",
        "enabled": False,
    },
}


# =========================================================
# 🎯 LIMIT MODEL GROQ (FREE TIER)
# =========================================================
GROQ_LIMITS = {
    "allam-2-7b": {"rpm": 30, "rpd": 7000, "tpm": 6000},
    "meta-llama/llama-prompt-guard-2-22m": {"rpm": 30, "rpd": 14400, "tpm": 15000},
    "meta-llama/llama-prompt-guard-2-86m": {"rpm": 30, "rpd": 14400, "tpm": 15000},
    "openai/gpt-oss-120b": {"rpm": 30, "rpd": 1000, "tpm": 8000},
    "openai/gpt-oss-20b": {"rpm": 30, "rpd": 1000, "tpm": 8000},
    "openai/gpt-oss-safeguard-20b": {"rpm": 3, "rpd": 1000, "tpm": 2000},
    "qwen/qwen3.8-27b": {"rpm": 30, "rpd": 1000, "tpm": 8000},
    "_default": {"rpm": 30, "rpd": 1000, "tpm": 8000},
}


# =========================================================
# 🎯 THRESHOLD WARNING
# =========================================================
QUOTA_WARNING_THRESHOLD = 80   # Warning kalau >80%
QUOTA_PAUSE_THRESHOLD = 90     # Auto-pause kalau >90%


# =========================================================
# 🔧 HELPER FUNCTIONS
# =========================================================
def get_ai_config(ai_name):
    """Ambil config AI berdasarkan nama."""
    return AI_CONFIG.get(ai_name, {})


def get_model_limit(model_name):
    """Ambil limit model dari Groq."""
    return GROQ_LIMITS.get(model_name, GROQ_LIMITS["_default"])


def get_all_ai_names():
    """List semua AI yang terdaftar."""
    return list(AI_CONFIG.keys())


def get_enabled_ai_names():
    """List AI yang aktif (enabled=True)."""
    return [k for k, v in AI_CONFIG.items() if v.get("enabled")]


def get_ai_name_display(ai_name):
    """Ambil display name + emoji buat UI."""
    _cfg = AI_CONFIG.get(ai_name, {})
    return f"{_cfg.get('emoji', '🤖')} {_cfg.get('name', ai_name)}"


def get_ai_api_key(ai_name):
    """
    ✅ Ambil API key dari Streamlit secrets berdasarkan ai_name.
    Kalau key spesifik gak ada, fallback ke GROQ_API_KEY.
    """
    import streamlit as st

    _cfg = get_ai_config(ai_name)
    _secret_name = _cfg.get("api_key_secret", "GROQ_API_KEY")

    try:
        _key = st.secrets.get(_secret_name, "")
        if _key:
            return _key
    except Exception:
        pass

    # Fallback ke key utama
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        return ""