"""
Ott-Bot Configuration
Edit these settings before running the bot
"""

import os
from pathlib import Path

# ===================================================================
# TELEGRAM BOT SETTINGS (Optional - leave empty for CLI-only mode)
# ===================================================================

# Get these from https://my.telegram.org
TG_API_ID = os.getenv("TG_API_ID", "33029767")          # e.g. "12345678"
TG_API_HASH = os.getenv("TG_API_HASH", "5d897bed11bc8b062a12f6c1c3c5360a")      # e.g. "abc123def456..."
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8719198691:AAEr0tXDu1TTK1LDzLPf-Ycv0EvzqXzzp7c")    # e.g. "123456:ABC-DEF..."

# Admin user IDs who can use the bot (get from @userinfobot)
TG_ADMINS = [
    int(x) for x in os.getenv("TG_ADMINS", "8729304171").split(",") if x
]

# ===================================================================
# FILE PATHS
# ===================================================================

# Root directory
ROOT_DIR = Path(__file__).parent.parent

# Data directory
DATA_DIR = ROOT_DIR / "data"

# Cookie file (Netscape format)
COOKIE_FILE = os.getenv("COOKIE_FILE", str(DATA_DIR / "cookies.txt"))

# Widevine device file
WVD_FILE = os.getenv("WVD_FILE", str(DATA_DIR / "my_device.wvd"))

# mp4decrypt binary
MP4DECRYPT_PATH = os.getenv(
    "MP4DECRYPT_PATH",
    str(DATA_DIR / "mp4decrypt.exe")
)

# Download directory
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", str(ROOT_DIR / "Downloads"))

# ===================================================================
# BROWSER SETTINGS
# ===================================================================

# Chrome executable path (auto-detected if empty)
CHROME_PATH = os.getenv("CHROME_PATH", "")

# Run browser headless (True for VPS, False for debugging)
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# Slow motion in ms (for debugging, 0 = normal speed)
SLOW_MO = int(os.getenv("SLOW_MO", "0"))

# ===================================================================
# SERVER SETTINGS
# ===================================================================

# Local server port (extension → Python communication)
SERVER_PORT = int(os.getenv("SERVER_PORT", "8765"))

# ===================================================================
# DOWNLOAD SETTINGS
# ===================================================================

# Preferred video quality
QUALITY = os.getenv("QUALITY", "1080")  # 1080, 720, 480, 360

# Preferred video codec
VCODEC = os.getenv("VCODEC", "h264")    # h264, h265

# Preferred audio language
ALANG = os.getenv("ALANG", "hi,en")     # Comma-separated

# Preferred subtitle language
SLANG = os.getenv("SLANG", "en,hi")     # Comma-separated

# Maximum file size for Telegram upload (MB)
TG_MAX_SIZE = int(os.getenv("TG_MAX_SIZE", "2000"))  # 2GB limit

# ===================================================================
# LOGGING
# ===================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR

# ===================================================================
# VALIDATION
# ===================================================================

def validate_config():
    """Check if essential files exist"""
    errors = []

    if not os.path.exists(COOKIE_FILE):
        errors.append(f"Cookie file not found: {COOKIE_FILE}")

    if not os.path.exists(WVD_FILE):
        errors.append(f"WVD file not found: {WVD_FILE}")

    if not os.path.exists(MP4DECRYPT_PATH):
        # Try system mp4decrypt
        import shutil
        if not shutil.which("mp4decrypt"):
            errors.append(f"mp4decrypt not found: {MP4DECRYPT_PATH}")

    return errors
