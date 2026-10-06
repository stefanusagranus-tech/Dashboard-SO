AI_CONFIG = {
    # ============================================
    # AI-0: Kurumi — Chief of Staff
    # ============================================
    "ai-0": {
        "name": "Kurumi",
        "emoji": "🎀",
        "description": "Chief of Staff — sapaan, rangkum & kirim laporan",
        "model_priority": [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["greeting", "summary", "send_report"],
        "enabled": False,  # Aktifkan setelah API key siap
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
            "openai/gpt-oss-120b",
        ],
        "daily_limit": 1000,
        "max_tpm": 8000,
        "functions": ["input", "validate", "anomaly"],
        "enabled": False,
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
        "enabled": False,
    },
}
