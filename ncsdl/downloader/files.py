"""File utilities: validation, sanitization, broken name detection."""

import json
import os
import re
import subprocess
from pathlib import Path

# Supported audio formats with their yt-dlp codec settings
SUPPORTED_FORMATS = {
    "m4a": {"ext": "m4a", "codec": "aac", "quality": "0"},
    "flac": {"ext": "flac", "codec": "flac", "quality": "0"},
    "opus": {"ext": "opus", "codec": "opus", "quality": "0"},
    "mp3": {"ext": "mp3", "codec": "mp3", "quality": "0"},
}

# Audio file extensions for duplicate detection
_AUDIO_EXTENSIONS = frozenset({".mp3", ".m4a", ".flac", ".opus", ".ogg", ".wav"})

# Unsafe characters for filenames (regex pattern)
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    """Remove unsafe characters from filename."""
    name = _UNSAFE_CHARS.sub("", name)
    name = " ".join(name.split())
    return name.strip()


def is_audio_valid(filepath: str) -> bool:
    """Check if an audio file is valid (has audio stream, > 5 seconds)."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries",
        "stream=duration,codec_type",
        "-of", "json",
        filepath,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return False

    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return False
        duration = float(streams[0].get("duration", 0))
        return duration > 5
    except (json.JSONDecodeError, ValueError, KeyError):
        return False


def _read_file_tags(filepath: str) -> dict[str, str]:
    """Read all metadata tags from an audio file."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format_tags",
        "-of", "json",
        filepath,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        data = json.loads(result.stdout)
        return data.get("format", {}).get("tags", {})
    except Exception:
        return {}


def file_matches_video(filepath: str, video_id: str, title: str) -> bool:
    """Check if a file matches the expected video.

    Matches by:
    1. Video ID in comment/metadata (if present)
    2. Title match in metadata (fuzzy — checks if file's title is a substring)
    """
    tags = _read_file_tags(filepath)

    # Check comment field for video ID (from yt-dlp source URL)
    comment = tags.get("comment", "")
    if video_id in comment:
        return True

    # Check if file's metadata title matches the video title
    file_title = tags.get("title", "")
    file_artist = tags.get("artist", "")
    if file_title and file_title.lower() in title.lower():
        return True
    if file_artist and file_title:
        combined = f"{file_artist} - {file_title}".lower()
        if combined in title.lower():
            return True

    return False


def find_and_fix_broken_name(
    output_dir: str,
    video_id: str,
    video_title: str,
    expected_name: str,
    ext: str,
) -> tuple[bool, str]:
    """Find a file matching this video, fix its name, or delete if corrupted.

    Returns (found, action) where action describes what was done:
    - "valid" — file had correct name and is valid
    - "renamed: oldname.ext" — file was renamed to correct name
    - "deleted: oldname.ext" — corrupted file deleted
    - "" — no matching file found
    """
    dir_path = Path(output_dir)
    if not dir_path.is_dir():
        return False, ""

    target = dir_path / f"{expected_name}.{ext}"

    # Check if correctly named file exists
    if target.exists():
        if is_audio_valid(str(target)):
            return True, "valid"
        # Corrupted - delete
        target.unlink()
        return True, f"deleted: {expected_name}.{ext}"

    # Scan for files matching this video
    for f in dir_path.iterdir():
        if not f.is_file() or f.suffix.lower() not in _AUDIO_EXTENSIONS:
            continue

        if file_matches_video(str(f), video_id, video_title):
            old_name = f.name
            if is_audio_valid(str(f)):
                # Rename to correct name
                f.rename(target)
                return True, f"renamed: {old_name}"
            else:
                # Corrupted - delete
                f.unlink()
                return True, f"deleted: {old_name}"

    return False, ""


def get_existing_songs(directory: str) -> set[str]:
    """Get a set of existing song names in a directory.

    Returns filenames without extension for duplicate checking.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return set()

    return {
        f.stem
        for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS
    }
