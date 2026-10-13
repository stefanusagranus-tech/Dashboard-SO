"""
Router Config — Static config untuk APK Android
=================================================
Endpoint ini buat kasih tau APK:
- URL Streamlit (buat shortcut PDF/PPT)
- Versi API (buat force update check)
- Feature flags (mana fitur yang di backend, mana di web)
- Metadata bot (nama, endpoint, emoji)
"""

import os
from fastapi import APIRouter


router = APIRouter(prefix="/api/config", tags=["Config"])


# =========================================================
# ENV-BASED CONFIG
# =========================================================
def _get_streamlit_url() -> str:
    """URL Streamlit untuk shortcut PDF/PPT."""
    return os.getenv(
        "STREAMLIT_URL",
        "https://dashboard-so.streamlit.app",
    )


def _get_api_version() -> str:
    """Versi API untuk force update check."""
    return os.getenv("API_VERSION", "1.0.0")


def _get_min_app_version() -> str:
    """Versi minimum APK yang di-support."""
    return os.getenv("MIN_APP_VERSION", "1.0.0")


# =========================================================
# ENDPOINTS
# =========================================================
@router.get("")
@router.get("/")
async def get_config():
    """Get konfigurasi untuk APK Android."""
    _streamlit_url = _get_streamlit_url()

    return {
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