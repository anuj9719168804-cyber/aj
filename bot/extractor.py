"""
Ott-Bot - PSSH & Decryption Key Extraction
Uses pywidevine to extract decryption keys from MPD manifest
"""

import re
import logging
import requests
from pathlib import Path

from bot.config import WVD_FILE

logger = logging.getLogger(__name__)


async def extract_key(mpd_url: str, license_url: str = None) -> str:
    """
    Extract decryption key from MPD manifest

    Returns: "KID:KEY" string or None
    """
    try:
        from pywidevine.cdm import Cdm
        from pywidevine.device import Device
        from pywidevine.pssh import PSSH
    except ImportError:
        logger.error("pywidevine not installed! Run: pip install pywidevine")
        return None

    # Check WVD file
    if not Path(WVD_FILE).exists():
        logger.error(f"WVD file not found: {WVD_FILE}")
        return None

    # Download MPD manifest
    logger.info("Downloading MPD manifest...")
    try:
        response = requests.get(mpd_url, timeout=30)
        response.raise_for_status()
        mpd_text = response.text
    except Exception as e:
        logger.error(f"Failed to download MPD: {e}")
        return None

    logger.info(f"Manifest size: {len(mpd_text)} bytes")

    # Extract PSSH
    logger.info("Extracting PSSH...")
    pssh_match = re.search(r'<cenc:pssh>(.*?)</cenc:pssh>', mpd_text)
    if not pssh_match:
        pssh_match = re.search(r'<PSSH>(.*?)</PSSH>', mpd_text)

    if not pssh_match:
        logger.error("PSSH not found in MPD!")
        # Save MPD for debugging
        with open("debug_mpd.mpd", "w") as f:
            f.write(mpd_text)
        logger.info("Saved MPD to debug_mpd.mpd for inspection")
        return None

    pssh = pssh_match.group(1)
    logger.info(f"PSSH: {pssh[:60]}...")

    # Find license URL
    if not license_url:
        logger.info("Searching for license URL in MPD...")
        lic_patterns = [
            r'(https://apix\.hotstar\.com/v2/fetch/license\?token=[^"\s]+)',
            r'(https://[^"\s]+license[^"\s]*)',
            r'<laurl[^>]*value="([^"]+)"',
        ]

        for pattern in lic_patterns:
            match = re.search(pattern, mpd_text, re.IGNORECASE)
            if match:
                license_url = match.group(1)
                logger.info(f"License URL: {license_url[:100]}...")
                break

    if not license_url:
        logger.error("License URL not found!")
        return None

    # Load Widevine device
    logger.info("Loading Widevine device...")
    try:
        device = Device.load(WVD_FILE)
        cdm = Cdm.from_device(device)
        session_id = cdm.open()
        logger.info("✅ Device loaded, session opened")
    except Exception as e:
        logger.error(f"Failed to load device: {e}")
        return None

    # Generate license challenge
    logger.info("Generating license challenge...")
    try:
        challenge = cdm.get_license_challenge(session_id, PSSH(pssh))
        logger.info("✅ Challenge generated")
    except Exception as e:
        logger.error(f"Challenge generation failed: {e}")
        cdm.close(session_id)
        return None

    # Request license
    logger.info("Requesting license from server...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.hotstar.com/',
        }
        response = requests.post(license_url, data=challenge, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"✅ License received ({len(response.content)} bytes)")
    except Exception as e:
        logger.error(f"License request failed: {e}")
        cdm.close(session_id)
        return None

    # Parse license
    logger.info("Parsing license...")
    try:
        cdm.parse_license(session_id, response.content)
        logger.info("✅ License parsed")
    except Exception as e:
        logger.error(f"License parsing failed: {e}")
        cdm.close(session_id)
        return None

    # Extract keys
    logger.info("Extracting decryption key...")
    decryption_key = None

    for key in cdm.get_keys(session_id):
        if key.type == 'CONTENT':
            kid = key.kid.hex()
            key_hex = key.key.hex()
            decryption_key = f"{kid}:{key_hex}"
            logger.info(f"✅ Key found: {kid}:{key_hex[:20]}...")
            break

    cdm.close(session_id)

    if not decryption_key:
        logger.error("No CONTENT key found in license!")
        return None

    return decryption_key
