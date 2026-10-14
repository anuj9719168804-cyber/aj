"""
Ott-Bot - Download and Decrypt Pipeline
Downloads encrypted video/audio, decrypts, and merges
"""

import os
import re
import glob
import shutil
import subprocess
import logging
from pathlib import Path

from bot.config import DOWNLOAD_DIR, MP4DECRYPT_PATH, COOKIE_FILE

logger = logging.getLogger(__name__)


def get_tool_path(tool_name: str, fallback_path: str = None) -> str:
    """Find tool in PATH or use fallback"""
    if fallback_path and os.path.exists(fallback_path):
        return f'"{fallback_path}"'
    if shutil.which(tool_name):
        return tool_name
    if shutil.which(f"{tool_name}.exe"):
        return f"{tool_name}.exe"
    return tool_name


def run_command(cmd: str, description: str = "", timeout: int = 600) -> tuple:
    """Run shell command"""
    logger.info(f"🔄 {description}...")
    logger.debug(f"Command: {cmd[:200]}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout
        )
        if result.stdout:
            logger.debug(f"Output: {result.stdout[-500:]}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr[-300:] if e.stderr else str(e)}")
        return False, e.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s")
        return False, "Timeout"


def find_best_formats(mpd_url: str) -> tuple:
    """Find best video and audio format IDs"""
    logger.info("Finding best formats...")

    cmd = (
        f'yt-dlp --cookies "{COOKIE_FILE}" '
        f'--allow-unplayable-formats '
        f'-F "{mpd_url}"'
    )

    success, output = run_command(cmd, "Listing formats")
    if not success:
        return None, None

    # Parse formats
    video_pattern = re.compile(r"^([\w-]+)\s+\d+x\d+\s+.*?video only\b", re.MULTILINE)
    audio_pattern = re.compile(r"^([\w-]+)\s+.*?audio only\b", re.MULTILINE)

    video_matches = video_pattern.findall(output)
    audio_matches = audio_pattern.findall(output)

    video_fmt = video_matches[-1] if video_matches else None
    audio_fmt = audio_matches[0] if audio_matches else None

    if video_fmt:
        logger.info(f"Video format: {video_fmt}")
    if audio_fmt:
        logger.info(f"Audio format: {audio_fmt}")

    return video_fmt, audio_fmt


def download_track(mpd_url: str, fmt_id: str, track_type: str) -> str:
    """Download a single track (video or audio)"""
    logger.info(f"Downloading {track_type}...")

    out_template = os.path.join(
        DOWNLOAD_DIR,
        f"encrypted_{track_type}.%(ext)s"
    )

    cmd = (
        f'yt-dlp --cookies "{COOKIE_FILE}" '
        f'--allow-unplayable-formats '
        f'-f "{fmt_id}" '
        f'--output "{out_template}" '
        f'"{mpd_url}"'
    )

    success, _ = run_command(cmd, f"Downloading {track_type}", timeout=600)
    if not success:
        return None

    # Find downloaded file
    files = glob.glob(os.path.join(DOWNLOAD_DIR, f"encrypted_{track_type}.*"))
    if not files:
        logger.error(f"{track_type.capitalize()} file not found after download")
        return None

    return files[0]


def decrypt_file(input_file: str, track_type: str, key: str) -> str:
    """Decrypt a single file"""
    logger.info(f"Decrypting {track_type}...")

    output_file = os.path.join(DOWNLOAD_DIR, f"decrypted_{track_type}.mp4")

    mp4decrypt = get_tool_path("mp4decrypt", MP4DECRYPT_PATH)
    cmd = f'{mp4decrypt} --key "{key}" "{input_file}" "{output_file}"'

    success, _ = run_command(cmd, f"Decrypting {track_type}", timeout=300)
    if not success:
        return None

    # Delete encrypted file
    if os.path.exists(input_file):
        os.remove(input_file)
        logger.debug(f"Deleted: {input_file}")

    return output_file


def merge_files(video_file: str, audio_file: str, output_name: str) -> str:
    """Merge video and audio into final file"""
    logger.info("Merging video + audio...")

    output_path = os.path.join(DOWNLOAD_DIR, output_name)

    if audio_file and os.path.exists(audio_file):
        cmd = f'ffmpeg -y -i "{video_file}" -i "{audio_file}" -c copy "{output_path}"'
    else:
        cmd = f'ffmpeg -y -i "{video_file}" -c copy "{output_path}"'

    success, _ = run_command(cmd, "Merging", timeout=300)
    if not success:
        # Fallback - just copy video
        shutil.copy(video_file, output_path)
        logger.warning("Merge failed, using video only")

    # Cleanup
    if os.path.exists(video_file):
        os.remove(video_file)
    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)

    return output_path if os.path.exists(output_path) else None


async def download_and_decrypt(mpd_url: str, key: str) -> str:
    """
    Complete download + decrypt pipeline

    Returns: Path to final video file or None
    """

    # Create download directory
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Find formats
    video_fmt, audio_fmt = find_best_formats(mpd_url)
    if not video_fmt:
        logger.error("No video format found!")
        return None

    # Download video
    video_file = download_track(mpd_url, video_fmt, "video")
    if not video_file:
        logger.error("Video download failed!")
        return None

    # Download audio (if available)
    audio_file = None
    if audio_fmt:
        audio_file = download_track(mpd_url, audio_fmt, "audio")

    # Decrypt video
    video_decrypted = decrypt_file(video_file, "video", key)
    if not video_decrypted:
        logger.error("Video decryption failed!")
        return None

    # Decrypt audio (if available)
    audio_decrypted = None
    if audio_file:
        audio_decrypted = decrypt_file(audio_file, "audio", key)

    # Generate output filename
    import time
    output_name = f"output_{time.strftime('%Y%m%d_%H%M%S')}.mkv"

    # Merge
    final_file = merge_files(video_decrypted, audio_decrypted, output_name)

    if final_file:
        file_size = os.path.getsize(final_file) / (1024 * 1024)
        logger.info(f"✅ Final file: {final_file} ({file_size:.1f} MB)")

    return final_file
