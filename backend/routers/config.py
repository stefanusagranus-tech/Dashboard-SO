"""
Router Config — Konfigurasi untuk APK Android.
================================================
Endpoint untuk:
- Info versi app (buat sistem update)
- Streamlit URL & paths
- Features flag
- List bots
"""

import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["Config"])


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def _get_api_version():
    """Ambil versi API dari env."""
    return os.getenv("API_VERSION", "1.0.0")


def _get_min_app_version():
    """Ambil minimum versi app yang didukung."""
    return os.getenv("MIN_APP_VERSION", "1.0.0")


def _get_streamlit_url():
    """Ambil Streamlit URL dari env."""
    return os.getenv("STREAMLIT_URL", "https://dashboard-so-uxrzpnjkudht2nvy8bwfnh.streamlit.app/")


def _get_latest_app_version():
    """Ambil versi terbaru app dari env."""
    return os.getenv("LATEST_APP_VERSION", "1.0.0")


def _get_download_url():
    """Ambil URL download APK dari env."""
    return os.getenv(
        "APP_DOWNLOAD_URL",
        "https://github.com/stefanusagranus-tech/Dashboard-SO/releases/tag/V1.0"
    )


def _get_changelog():
    """Ambil changelog dari env."""
    return os.getenv(
        "APP_CHANGELOG",
        "• 12 fitur dashboard\n• Fix widget kepotong\n• Splash + login fix"
    )


def _get_force_update():
    """Ambil flag force update dari env."""
    return os.getenv("APP_FORCE_UPDATE", "false").lower() == "true"


# =========================================================
# ENDPOINT: GET /api/config
# =========================================================
@router.get("")
@router.get("/")
async def get_config():
    """
    Get konfigurasi untuk APK Android.
    
    Response fields:
    - app: Info versi & sistem update
    - api_version: Versi backend API
    - min_app_version: Min versi app yang didukung
    - streamlit_url: URL Streamlit
    - streamlit_paths: Path ke berbagai fitur Streamlit
    - features: Flag fitur yang tersedia
    - bots: List AI bots
    """
    _streamlit_url = _get_streamlit_url()

    return {
        # =========================================================
        # APP INFO — Buat sistem update
        # =========================================================
        "app": {
            "name": "Dashboard SO C383",
            "current_version": "1.0.0",
            "latest_version": _get_latest_app_version(),
            "min_version": _get_min_app_version(),
            "download_url": _get_download_url(),
            "changelog": _get_changelog(),
            "force_update": _get_force_update(),
        },

        # =========================================================
        # BACKEND INFO — Existing
        # =========================================================
        "api_version": _get_api_version(),
        "min_app_version": _get_min_app_version(),
        "streamlit_url": _streamlit_url,
        "streamlit_paths": {
            "rei_pdf": f"{_streamlit_url}/ai_chat_rei",
            "rei_ppt": f"{_streamlit_url}/ai_chat_rei",
            "kurumi_report": f"{_streamlit_url}/ai_chat_kurumi",
            "yui_export": f"{_streamlit_url}/ai_chat_yui",
            "master_shift": f"{_streamlit_url}/master_shift",
        },

        # =========================================================
        # FEATURES — Existing
        # =========================================================
        "features": {
            "backend_pdf": False,
            "backend_ppt": False,
            "backend_excel": False,
            "backend_ocr": False,
            "web_pdf": True,
            "web_ppt": True,
            "web_excel": True,
            "auth_required": True,
        },

        # =========================================================
        # BOTS — Existing
        # =========================================================
        "bots": [
            {
                "id": "kurumi",
                "name": "Kurumi",
                "emoji": "🎀",
                "role": "Chief of Staff",
                "description": "Laporan & rangkuman",
                "endpoint": "/api/kurumi/chat",
                "color": "#7B2CBF",
            },
            {
                "id": "hana",
                "name": "Hana",
                "emoji": "🌸",
                "role": "Master Shift",
                "description": "Jadwal shift",
                "endpoint": "/api/hana/chat",
                "color": "#E91E63",
            },
            {
                "id": "yui",
                "name": "Yui",
                "emoji": "📦",
                "role": "Data Entry",
                "description": "Input & rekap SO",
                "endpoint": "/api/yui/chat",
                "color": "#00BCD4",
            },
            {
                "id": "rei",
                "name": "Rei",
                "emoji": "📊",
                "role": "Analisis SO",
                "description": "Analisis & LPJ",
                "endpoint": "/api/rei/chat",
                "color": "#FF6B00",
            },
        ],
    }