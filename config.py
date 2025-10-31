import os
from os import environ

class Config:
    # Bot Configuration
    API_ID = int(environ.get("API_ID", "12345678"))
    API_HASH = environ.get("API_HASH", "your_api_hash_here")
    BOT_TOKEN = environ.get("BOT_TOKEN", "your_bot_token_here")
    
    # Database
    MONGODB_URI = environ.get("MONGODB_URI", "mongodb://localhost:27017")
    DB_NAME = environ.get("DB_NAME", "video_encoder_bot")
    
    # Admin Configuration
    ADMIN_ID = list(set(int(x) for x in environ.get("ADMIN_ID", "0").split()))
    
    # Channel Configuration
    FORCE_SUB_CHANNELS = environ.get("FORCE_SUB_CHANNELS", "").split()
    LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "0"))
    
    # URLs
    OWNER_URL = environ.get("OWNER_URL", "https://t.me/YourUsername")
    UPDATES_CHANNEL = environ.get("UPDATES_CHANNEL", "https://t.me/YourChannel")
    SUPPORT_GROUP = environ.get("SUPPORT_GROUP", "https://t.me/YourGroup")
    
    # Encoding Settings
    DEFAULT_PRESET = environ.get("DEFAULT_PRESET", "medium")
    DEFAULT_CRF = int(environ.get("DEFAULT_CRF", "28"))
    DEFAULT_AUDIO_BITRATE = environ.get("DEFAULT_AUDIO_BITRATE", "128k")
    DEFAULT_VIDEO_CODEC = environ.get("DEFAULT_VIDEO_CODEC", "libx264")
    
    # Quality Settings
    QUALITIES = {
        "144p": {"resolution": "256x144", "bitrate": "100k"},
        "240p": {"resolution": "426x240", "bitrate": "250k"},
        "360p": {"resolution": "640x360", "bitrate": "500k"},
        "480p": {"resolution": "854x480", "bitrate": "1000k"},
        "720p": {"resolution": "1280x720", "bitrate": "2500k"},
        "1080p": {"resolution": "1920x1080", "bitrate": "5000k"},
        "2160p": {"resolution": "3840x2160", "bitrate": "15000k"}
    }
    
    # File Paths
    DOWNLOAD_DIR = environ.get("DOWNLOAD_DIR", "downloads")
    ENCODE_DIR = environ.get("ENCODE_DIR", "encoded")
    THUMB_DIR = environ.get("THUMB_DIR", "thumbnails")
    
    # Limits
    MAX_FILE_SIZE = int(environ.get("MAX_FILE_SIZE", "4294967296"))  # 4GB
    MAX_QUEUE_SIZE = int(environ.get("MAX_QUEUE_SIZE", "10"))
    FREE_USER_LIMIT = int(environ.get("FREE_USER_LIMIT", "5"))  # Per day
    
    # Watermark
    DEFAULT_WATERMARK_TEXT = environ.get("DEFAULT_WATERMARK_TEXT", "")
    WATERMARK_POSITION = environ.get("WATERMARK_POSITION", "bottom_right")
    
    # Shortener (Optional)
    SHORTENER_API_1 = environ.get("SHORTENER_API_1", "")
    SHORTENER_URL_1 = environ.get("SHORTENER_URL_1", "")
    TUTORIAL_URL_1 = environ.get("TUTORIAL_URL_1", "")
    
    SHORTENER_API_2 = environ.get("SHORTENER_API_2", "")
    SHORTENER_URL_2 = environ.get("SHORTENER_URL_2", "")
    TUTORIAL_URL_2 = environ.get("TUTORIAL_URL_2", "")
    
    # Misc
    MAX_CONCURRENT_TASKS = int(environ.get("MAX_CONCURRENT_TASKS", "3"))
    PROGRESS_UPDATE_DELAY = int(environ.get("PROGRESS_UPDATE_DELAY", "5"))  # seconds
    
    # Create directories
    for directory in [DOWNLOAD_DIR, ENCODE_DIR, THUMB_DIR]:
        os.makedirs(directory, exist_ok=True)
