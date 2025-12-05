"""
Gemini Ultra Gateway - Configuration Module
Centralized configuration management for the entire application
"""

import os
from pathlib import Path
from typing import Optional, List
from datetime import timedelta, timezone

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Timezone configuration (Beijing UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# Load environment variables from .env file
def _load_env_file(path: str = ".env") -> None:
    env_path = PROJECT_ROOT / path
    if not env_path.exists():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass

_load_env_file()


class Config:
    """Application configuration"""
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/geminibusiness.db")
    
    # Proxy settings
    PROXY: Optional[str] = os.getenv("PROXY") or None
    if PROXY:
        PROXY = PROXY.strip().strip('"').strip("'")
        PROXY = PROXY if PROXY else None
    
    # Timeout settings
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "600"))
    JWT_TTL_SECONDS: int = int(os.getenv("JWT_TTL_SECONDS", "270"))
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "gemini-ultra-gateway-secret-key-change-me")
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123456")
    API_KEY_ENCRYPTION_KEY: str = os.getenv("API_KEY_ENCRYPTION_KEY", "")
    
    # Account pool settings
    ACCOUNT_COOLDOWN_SECONDS: int = int(os.getenv("ACCOUNT_COOLDOWN_SECONDS", "300"))
    AUTH_ERROR_COOLDOWN_SECONDS: int = int(os.getenv("AUTH_ERROR_COOLDOWN_SECONDS", "900"))
    RATE_LIMIT_COOLDOWN_SECONDS: int = int(os.getenv("RATE_LIMIT_COOLDOWN_SECONDS", "300"))
    
    # Keep-alive settings
    KEEPALIVE_ENABLED: bool = os.getenv("KEEPALIVE_ENABLED", "true").lower() == "true"
    KEEPALIVE_INTERVAL_MINUTES: int = int(os.getenv("KEEPALIVE_INTERVAL_MINUTES", "30"))
    
    # Media settings
    IMAGE_SAVE_DIR: Path = BASE_DIR / "generated_images"
    VIDEO_SAVE_DIR: Path = BASE_DIR / "generated_videos"
    IMAGE_CACHE_HOURS: int = int(os.getenv("IMAGE_CACHE_HOURS", "24"))
    VIDEO_CACHE_HOURS: int = int(os.getenv("VIDEO_CACHE_HOURS", "24"))
    
    # Auto-login settings (for cookie refresh)
    AUTO_LOGIN_ENABLED: bool = os.getenv("AUTO_LOGIN_ENABLED", "false").lower() == "true"
    TEMPMAIL_WORKER_URL: Optional[str] = os.getenv("TEMPMAIL_WORKER_URL")
    
    # Model mappings
    MODEL_MAPPING = {
        # Text models
        "gemini-auto": None,
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-2.5-pro": "gemini-2.5-pro",
        "gemini-3-pro-preview": "gemini-3-pro-preview",
        "gemini-3-pro": "gemini-3-pro",
        # Image models
        "gemini-2.5-flash-image": "gemini-2.5-flash",
        "gemini-2.5-pro-image": "gemini-2.5-pro",
        "gemini-3-pro-preview-image": "gemini-3-pro-preview",
        "gemini-3-pro-image": "gemini-3-pro",
        # Video models
        "gemini-2.5-flash-video": "gemini-2.5-flash",
        "gemini-2.5-pro-video": "gemini-2.5-pro",
        "gemini-3-pro-preview-video": "gemini-3-pro-preview",
        "gemini-3-pro-video": "gemini-3-pro",
        # Search models (web grounding)
        "gemini-2.5-flash-search": "gemini-2.5-flash",
        "gemini-2.5-pro-search": "gemini-2.5-pro",
        "gemini-3-pro-preview-search": "gemini-3-pro-preview",
        "gemini-3-pro-search": "gemini-3-pro",
    }
    
    # All supported models list
    SUPPORTED_MODELS: List[str] = list(MODEL_MAPPING.keys())
    
    @classmethod
    def get_model_id(cls, model_name: str) -> Optional[str]:
        """Get the actual model ID for a given model name"""
        return cls.MODEL_MAPPING.get(model_name, model_name)
    
    @classmethod
    def is_image_model(cls, model_name: str) -> bool:
        """Check if the model is an image generation model"""
        return "-image" in model_name
    
    @classmethod
    def is_video_model(cls, model_name: str) -> bool:
        """Check if the model is a video generation model"""
        return "-video" in model_name
    
    @classmethod
    def is_search_model(cls, model_name: str) -> bool:
        """Check if the model is a search/grounding model"""
        return "-search" in model_name


# Gemini Business API endpoints
class GeminiEndpoints:
    BASE_URL = "https://biz-discoveryengine.googleapis.com/v1alpha/locations/global"
    AUTH_URL = "https://business.gemini.google"
    
    CREATE_SESSION = f"{BASE_URL}/widgetCreateSession"
    STREAM_ASSIST = f"{BASE_URL}/widgetStreamAssist"
    LIST_FILE_METADATA = f"{BASE_URL}/widgetListSessionFileMetadata"
    ADD_CONTEXT_FILE = f"{BASE_URL}/widgetAddContextFile"
    DOWNLOAD_FILE = f"{BASE_URL}" + "/{session}:downloadFile"
    GETOXSRF = f"{AUTH_URL}/auth/getoxsrf"


# Create directories if they don't exist
Config.IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)
Config.VIDEO_SAVE_DIR.mkdir(parents=True, exist_ok=True)
