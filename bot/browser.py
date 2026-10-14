"""
Ott-Bot - Browser Automation
Opens Chrome with extension, captures MPD URL
"""

import os
import time
import json
import asyncio
import logging
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright

from bot.config import (
    CHROME_PATH, HEADLESS, SLOW_MO, COOKIE_FILE, SERVER_PORT
)

logger = logging.getLogger(__name__)

# Chrome paths to try
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


def find_chrome():
    """Find Chrome executable"""
    if CHROME_PATH and os.path.exists(CHROME_PATH):
        return CHROME_PATH

    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path

    return None


async def capture_mpd(url: str, timeout: int = 120) -> dict:
    """
    Open Chrome with extension, capture MPD URL

    Returns dict with:
    - mpd_url: The MPD URL
    - license_url: License URL (if found)
    - title: Video title (if found)
    """

    chrome_path = find_chrome()
    if not chrome_path:
        logger.error("Chrome not found!")
        return None

    logger.info(f"Using Chrome: {chrome_path}")

    captured = {
        "mpd_url": None,
        "license_url": None,
        "title": None
    }

    # Close existing Chrome instances
    logger.info("Closing existing Chrome instances...")
    subprocess.run(
        'taskkill /F /IM chrome.exe 2>nul',
        shell=True,
        capture_output=True
    )
    time.sleep(2)

    # Create temp profile
    import tempfile
    profile_dir = os.path.join(
        tempfile.gettempdir(),
        'ott_bot_chrome_profile'
    )
    os.makedirs(profile_dir, exist_ok=True)

    # Load extension path
    ext_dir = str(Path(__file__).parent.parent / "extension")

    async with async_playwright() as p:
        logger.info("Launching Chrome...")

        try:
            browser = await p.chromium.launch(
                headless=HEADLESS,
                executable_path=chrome_path,
                slow_mo=SLOW_MO,
                args=[
                    f'--load-extension={ext_dir}',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--remote-allow-origins=*',
                    '--window-size=1280,720',
                ]
            )
        except Exception as e:
            # Fallback without extension
            logger.warning(f"Failed to load extension: {e}")
            logger.info("Launching without extension, will use network intercept...")

            browser = await p.chromium.launch(
                headless=HEADLESS,
                executable_path=chrome_path,
                slow_mo=SLOW_MO,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--remote-allow-origins=*',
                    '--window-size=1280,720',
                ]
            )

        # Load cookies
        if os.path.exists(COOKIE_FILE):
            cookies = []
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        domain = parts[0].lstrip('.')
                        try:
                            cookies.append({
                                'domain': domain,
                                'path': parts[2],
                                'secure': (parts[3] == 'TRUE'),
                                'expires': int(parts[4]) if parts[4].isdigit() else 0,
                                'name': parts[5],
                                'value': parts[6],
                            })
                        except:
                            continue

            if cookies:
                context = await browser.new_context()
                await context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies")
            else:
                context = await browser.new_context()
        else:
            context = await browser.new_context()

        # Network interceptor
        async def on_request(request):
            req_url = request.url
            if '.mpd' in req_url and ('hses' in req_url.lower() or 'hotstar' in req_url.lower()):
                logger.info(f"🎯 MPD URL captured: {req_url[:100]}...")
                captured["mpd_url"] = req_url

            if 'license' in req_url.lower() and 'hotstar' in req_url.lower():
                logger.info(f"🔑 License URL captured: {req_url[:100]}...")
                captured["license_url"] = req_url

        context.on("request", on_request)

        # Bot detection bypass
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)

        page = await context.new_page()

        logger.info(f"Opening: {url}")
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            logger.info("✅ Page loaded")
        except Exception as e:
            logger.warning(f"Page load warning: {e}")

        # Wait for page to settle
        try:
            await page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass

        # Try to click play button
        logger.info("Attempting to play video...")
        play_selectors = [
            '[data-testid="player-play-button"]',
            '.player-play-button',
            'video',
            '[class*="play-btn"]',
        ]

        for selector in play_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    await element.click()
                    logger.info(f"Clicked play button")
                    break
            except:
                continue

        # Wait for MPD capture
        logger.info(f"Waiting for MPD URL (timeout: {timeout}s)...")
        start = time.time()

        while not captured["mpd_url"]:
            await asyncio.sleep(0.5)
            elapsed = int(time.time() - start)

            if elapsed >= timeout:
                logger.error(f"Timeout! MPD URL not captured")
                await browser.close()
                return None

            if elapsed % 10 == 0 and elapsed > 0:
                logger.info(f"Still waiting... ({elapsed}s)")

        # Get page title
        try:
            captured["title"] = await page.title()
        except:
            pass

        await browser.close()

    logger.info("✅ Browser closed")
    return captured
