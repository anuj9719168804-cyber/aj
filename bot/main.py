"""
Ott-Bot - Main Entry Point
Supports both CLI and Telegram bot modes
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import validate_config, LOG_LEVEL, TG_BOT_TOKEN, TG_ADMINS

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ott-bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("  🎬 Ott-Bot - Complete OTT Downloader")
    print("=" * 60)

    # Validate config
    errors = validate_config()
    if errors:
        print("\n❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        print("\n📝 Fix these before running:")
        print("   1. Copy cookies.txt to data/")
        print("   2. Copy my_device.wvd to data/")
        print("   3. Copy mp4decrypt.exe to data/ (or install system-wide)")
        sys.exit(1)

    print("\n✅ Configuration valid")

    # Check if URL provided (CLI mode)
    if len(sys.argv) > 1:
        url = sys.argv[1]
        logger.info(f"CLI mode: Processing {url}")

        # Import and run CLI
        from bot.cli import process_url
        asyncio.run(process_url(url))
    else:
        # Check if Telegram configured
        if TG_BOT_TOKEN and TG_ADMINS:
            logger.info("Telegram bot mode")
            print("\n🤖 Starting Telegram bot...")

            # Import and run bot
            from bot.tg_bot import run_bot
            asyncio.run(run_bot())
        else:
            # CLI interactive mode
            logger.info("Interactive CLI mode")
            print("\n📝 Interactive mode")
            print("   Send Hotstar URL or type 'exit' to quit")

            from bot.cli import interactive_mode
            asyncio.run(interactive_mode())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
