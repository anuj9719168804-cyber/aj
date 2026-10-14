"""
Ott-Bot - CLI Interface
Handles user interaction via command line
"""

import sys
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def process_url(url: str) -> dict:
    """
    Process a Hotstar URL - complete pipeline
    Returns dict with result info
    """
    from bot.browser import capture_mpd
    from bot.extractor import extract_key
    from bot.downloader import download_and_decrypt

    result = {
        "success": False,
        "url": url,
        "mpd_url": None,
        "key": None,
        "output_file": None,
        "error": None
    }

    try:
        # Step 1: Capture MPD URL via browser
        logger.info("📡 Step 1: Capturing MPD URL...")
        mpd_data = await capture_mpd(url)

        if not mpd_data or not mpd_data.get("mpd_url"):
            result["error"] = "Failed to capture MPD URL"
            return result

        result["mpd_url"] = mpd_data["mpd_url"]
        result["license_url"] = mpd_data.get("license_url")
        logger.info(f"✅ MPD URL captured")

        # Step 2: Extract decryption key
        logger.info("🔑 Step 2: Extracting decryption key...")
        key = await extract_key(
            mpd_data["mpd_url"],
            mpd_data.get("license_url")
        )

        if not key:
            result["error"] = "Failed to extract decryption key"
            return result

        result["key"] = key
        logger.info(f"✅ Key extracted")

        # Step 3: Download and decrypt
        logger.info("⬇️  Step 3: Downloading and decrypting...")
        output_file = await download_and_decrypt(
            mpd_data["mpd_url"],
            key
        )

        if not output_file:
            result["error"] = "Download/decrypt failed"
            return result

        result["output_file"] = output_file
        result["success"] = True

        logger.info(f"✅ Done! Saved to: {output_file}")
        return result

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error processing URL: {e}", exc_info=True)
        return result


async def interactive_mode():
    """Interactive CLI mode"""
    from bot.browser import capture_mpd
    from bot.extractor import extract_key
    from bot.downloader import download_and_decrypt

    print("\n📝 Enter Hotstar URLs to download")
    print("   Commands:")
    print("   - Send URL: Start download")
    print("   - exit: Quit")
    print("   - help: Show help")

    while True:
        try:
            url = input("\n🔗 URL: ").strip()

            if not url:
                continue
            elif url.lower() in ["exit", "quit", "q"]:
                print("👋 Bye!")
                break
            elif url.lower() == "help":
                print("\n📖 Help:")
                print("   - Send a Hotstar URL to start download")
                print("   - Browser will open automatically")
                print("   - MPD URL will be captured")
                print("   - Video will be downloaded and decrypted")
                continue

            if not url.startswith("https://www.hotstar.com"):
                print("❌ Invalid Hotstar URL")
                continue

            # Process URL
            result = await process_url(url)

            if result["success"]:
                print(f"\n✅ Success!")
                print(f"   📁 Output: {result['output_file']}")
            else:
                print(f"\n❌ Failed: {result['error']}")

        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"❌ Error: {e}")
