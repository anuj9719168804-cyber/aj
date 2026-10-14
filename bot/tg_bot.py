"""
Ott-Bot - Telegram Bot (Pyrogram)
Optional Telegram integration - leave config empty for CLI-only mode
"""

import os
import asyncio
import logging
from pathlib import Path

from bot.config import (
    TG_API_ID, TG_API_HASH, TG_BOT_TOKEN, TG_ADMINS,
    TG_MAX_SIZE, DOWNLOAD_DIR
)
from bot.cli import process_url

logger = logging.getLogger(__name__)


async def run_bot():
    """Start Telegram bot"""

    if not TG_BOT_TOKEN:
        logger.error("TG_BOT_TOKEN not set! Cannot start bot.")
        return

    try:
        from pyrogram import Client, filters
        from pyrogram.types import Message
    except ImportError:
        logger.error("Pyrogram not installed! Run: pip install pyrogram tgcrypto")
        return

    # Create bot client
    bot = Client(
        "ott_bot",
        api_id=int(TG_API_ID) if TG_API_ID else None,
        api_hash=TG_API_HASH if TG_API_HASH else None,
        bot_token=TG_BOT_TOKEN,
        workdir=Path(__file__).parent.parent / "sessions"
    )

    # Create sessions directory
    (Path(__file__).parent.parent / "sessions").mkdir(exist_ok=True)

    @bot.on_message(filters.command("start"))
    async def cmd_start(client, message: Message):
        """Handle /start command"""
        if TG_ADMINS and message.from_user.id not in TG_ADMINS:
            await message.reply_text("❌ Unauthorized! Only admins can use this bot.")
            return

        await message.reply_text(
            "🎬 **Ott-Bot - OTT Downloader**\n\n"
            "✅ Features:\n"
            "• Send Hotstar URL → Get video\n"
            "• Auto MPD capture\n"
            "• Auto key extraction\n"
            "• Download + decrypt + merge\n\n"
            "📝 Usage:\n"
            "• Send: `https://www.hotstar.com/in/movies/...`\n\n"
            "⚙️ Commands:\n"
            "/start - Show this message\n"
            "/status - Check bot status\n"
            "/help - Show help"
        )

    @bot.on_message(filters.command("status"))
    async def cmd_status(client, message: Message):
        """Check bot status"""
        if TG_ADMINS and message.from_user.id not in TG_ADMINS:
            return

        # Check requirements
        from bot.config import validate_config, COOKIE_FILE, WVD_FILE
        errors = validate_config()

        status = "✅ **Bot Status**\n\n"
        status += f"📁 Cookies: {'✅' if os.path.exists(COOKIE_FILE) else '❌'}\n"
        status += f"🔑 WVD: {'✅' if os.path.exists(WVD_FILE) else '❌'}\n"

        if errors:
            status += "\n❌ Errors:\n"
            for error in errors:
                status += f"• {error}\n"
        else:
            status += "\n✅ All requirements met!"

        await message.reply_text(status)

    @bot.on_message(filters.command("help"))
    async def cmd_help(client, message: Message):
        """Show help"""
        if TG_ADMINS and message.from_user.id not in TG_ADMINS:
            return

        await message.reply_text(
            "📖 **Help Guide**\n\n"
            "**How to use:**\n"
            "1. Send a Hotstar URL\n"
            "2. Bot opens browser automatically\n"
            "3. MPD URL is captured\n"
            "4. Video is downloaded & decrypted\n"
            "5. Video is sent to you\n\n"
            "**Supported URLs:**\n"
            "• Movies: `https://www.hotstar.com/in/movies/...`\n"
            "• Shows: `https://www.hotstar.com/in/tv/...`\n"
            "• Sports: `https://www.hotstar.com/in/sports/...`\n\n"
            "**Notes:**\n"
            "• Videos > 2GB will be uploaded as document\n"
            "• Processing takes 2-5 minutes\n"
            "• You'll get progress updates"
        )

    @bot.on_message(filters.text & ~filters.command)
    async def handle_url(client, message: Message):
        """Handle incoming URLs"""
        if TG_ADMINS and message.from_user.id not in TG_ADMINS:
            return

        url = message.text.strip()

        if not url.startswith("https://www.hotstar.com"):
            await message.reply_text(
                "❌ Invalid URL! Please send a valid Hotstar URL.\n\n"
                "Example: `https://www.hotstar.com/in/movies/zootopia-2/1271418481/watch`"
            )
            return

        # Send processing message
        status_msg = await message.reply_text(
            "🔄 **Processing...**\n\n"
            "⏳ Step 1/4: Opening browser..."
        )

        try:
            # Process URL
            result = await process_url(url)

            if result["success"]:
                # Send success message
                await status_msg.edit_text(
                    "✅ **Success!**\n\n"
                    "⏳ Uploading video..."
                )

                # Upload file
                output_file = result["output_file"]
                file_size = os.path.getsize(output_file)
                file_size_mb = file_size / (1024 * 1024)

                if file_size_mb > TG_MAX_SIZE:
                    await status_msg.edit_text(
                        f"✅ **Download Complete!**\n\n"
                        f"📁 Size: {file_size_mb:.1f} MB\n"
                        f"⚠️ File too large for Telegram (> {TG_MAX_SIZE}MB)\n\n"
                        f"📂 Saved to: `{output_file}`"
                    )
                else:
                    # Send as video or document
                    if file_size_mb < 50:
                        await bot.send_video(
                            chat_id=message.chat.id,
                            video=output_file,
                            caption=f"🎬 **Downloaded!**\n\n📁 Size: {file_size_mb:.1f} MB",
                            progress=lambda current, total: status_msg.edit_text(
                                f"✅ **Success!**\n\n"
                                f"📤 Uploading: {current/1024/1024:.1f}/{total/1024/1024:.1f} MB"
                            )
                        )
                    else:
                        await bot.send_document(
                            chat_id=message.chat.id,
                            document=output_file,
                            caption=f"🎬 **Downloaded!**\n\n📁 Size: {file_size_mb:.1f} MB",
                            progress=lambda current, total: status_msg.edit_text(
                                f"✅ **Success!**\n\n"
                                f"📤 Uploading: {current/1024/1024:.1f}/{total/1024/1024:.1f} MB"
                            )
                        )

                    await status_msg.delete()

                # Cleanup file after upload
                try:
                    os.remove(output_file)
                except:
                    pass
            else:
                # Send error message
                await status_msg.edit_text(
                    f"❌ **Failed!**\n\n"
                    f"Error: {result['error']}"
                )

        except Exception as e:
            logger.error(f"Error processing URL: {e}", exc_info=True)
            await status_msg.edit_text(
                f"❌ **Error!**\n\n"
                f"```\n{str(e)[:500]}\n```"
            )

    # Start bot
    logger.info("Starting Telegram bot...")
    await bot.start()
    logger.info(f"Bot started! Logged in as @{(await bot.get_me()).username}")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        await bot.stop()
