"""File utilities: validation, sanitization, ncsdl_id tag read/write."""

import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

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

# KIO-supported protocols
_KIO_PROTOCOLS = frozenset({"mtp", "smb", "sftp", "fish", "ftp", "webdav", "archive"})


def is_kio_path(path: str) -> bool:
    """Check if path uses a KIO protocol."""
    return any(path.startswith(f"{p}:/") for p in _KIO_PROTOCOLS)


def encode_kio_path(path: str) -> str:
    """Encode special characters in a KIO path for use with kioclient."""
    if not is_kio_path(path):
        return path
    idx = path.find(":/")
    if idx == -1:
        return path
    prefix = path[: idx + 2]
    rest = path[idx + 2 :]
    encoded_rest = quote(rest, safe="/")
    return prefix + encoded_rest


def kio_list(path: str) -> list[str]:
    """List files in a KIO directory using kioclient."""
    encoded_path = encode_kio_path(path)
    result = subprocess.run(
        ["kioclient", "ls", encoded_path],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return []
    return [
        line.strip()
        for line in result.stdout.split("\n")
        if line.strip() and line.strip() != "."
    ]


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
        "-show_entries", "stream=duration,codec_type",
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
        streams = data.get("streams", [])
        if not streams:
            return False
        duration = float(streams[0].get("duration", 0))
        return duration > 5
    except Exception:
        return False


def get_ncsdl_id(filepath: str) -> str | None:
    """Read the ncsdl_id tag from an audio file. Returns the YouTube video ID or None."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".m4a":
        try:
            from mutagen.mp4 import MP4
            audio = MP4(filepath)
            tag = audio.tags
            if tag and "----:com.apple.iTunes:ncsdl_id" in tag:
                val = tag["----:com.apple.iTunes:ncsdl_id"]
                if val:
                    return val[0].decode("utf-8") if isinstance(val[0], bytes) else str(val[0])
        except Exception:
            pass

    elif ext == ".mp3":
        try:
            from mutagen.mp3 import MP3
            audio = MP3(filepath)
            if audio.tags:
                for frame in audio.tags.getall("TXXX"):
                    if frame.desc == "ncsdl_id":
                        return frame.text[0] if frame.text else None
        except Exception:
            pass

    elif ext in (".flac", ".ogg", ".opus"):
        try:
            from mutagen.flac import FLAC
            from mutagen.oggvorbis import OggVorbis
            from mutagen.oggopus import OggOpus
            if ext == ".flac": audio = FLAC(filepath)
            elif ext == ".opus": audio = OggOpus(filepath)
            else: audio = OggVorbis(filepath)
            tags = audio.get("ncsdl_id", [])
            if tags: return tags[0]
        except Exception:
            pass

    return None


def get_existing_songs(directory: str) -> set[str]:
    """Get a set of existing song names in a directory."""
    if is_kio_path(directory):
        files = kio_list(directory)
        return {Path(f).stem for f in files if Path(f).suffix.lower() in _AUDIO_EXTENSIONS}
    
    dir_path = Path(directory).expanduser().resolve()
    if not dir_path.is_dir():
        return set()
    return {f.stem for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS}
