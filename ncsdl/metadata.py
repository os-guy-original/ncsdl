"""Metadata embedding for downloaded NCS songs.

Embeds song information (artist, title, genre, etc.) as ID3/MP3 tags.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .styles import ParsedTitle, parse_title


def check_mutagen() -> bool:
    """Check if mutagen (eyeD3 alternative) is available."""
    try:
        import mutagen

        return True
    except ImportError:
        return False


def embed_metadata(
    filepath: str,
    parsed: Optional[ParsedTitle] = None,
    title: Optional[str] = None,
) -> tuple[bool, str]:
    """Embed metadata into an audio file.

    Uses ffmpeg for broad format support.

    Args:
        filepath: Path to the audio file.
        parsed: ParsedTitle from style detection.
        title: Raw video title (fallback if parsed is None).

    Returns:
        Tuple of (success, message).
    """
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"

    # Parse title if not provided
    if parsed is None and title:
        parsed = parse_title(title)

    if parsed is None:
        return False, "Could not parse title for metadata"

    # Build metadata tags
    tags = {
        "title": parsed.song_title,
        "artist": parsed.artist,
        "genre": parsed.genre or "Electronic",
        "album": "NCS - NoCopyrightSounds",
        "comment": f"Downloaded via ncsdl | Style: {parsed.style}",
    }

    if parsed.featuring:
        tags["artist"] = f"{parsed.artist} feat. {parsed.featuring}"

    if parsed.suffix:
        tags["title"] = f"{parsed.song_title} {parsed.suffix}"

    # Use ffmpeg to embed metadata
    # Use temp file in same directory to preserve filesystem for atomic replace
    dir_path = os.path.dirname(os.path.abspath(filepath))
    fd, temp_path = tempfile.mkstemp(suffix=".mp3", dir=dir_path)
    os.close(fd)

    cmd = [
        "ffmpeg",
        "-i",
        filepath,
        "-map",
        "0:a",
        "-c:a",
        "copy",
        "-metadata",
        f"title={tags['title']}",
        "-metadata",
        f"artist={tags['artist']}",
        "-metadata",
        f"genre={tags['genre']}",
        "-metadata",
        f"album={tags['album']}",
        "-metadata",
        f"comment={tags['comment']}",
        "-y",
        temp_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Metadata embed timed out: {filepath}"

    if result.returncode == 0 and os.path.exists(temp_path):
        os.replace(temp_path, filepath)
        return True, f"Metadata embedded: {tags['title']} - {tags['artist']}"

    # Cleanup temp file if it exists
    if os.path.exists(temp_path):
        os.remove(temp_path)

    error = result.stderr.strip() if result.stderr else "Unknown error"
    return False, f"Metadata failed: {filepath} ({error})"


def _parse_from_filename(filename: str) -> Optional[ParsedTitle]:
    """Try to extract artist and title from a filename like 'Artist - Song'."""
    if " - " not in filename:
        return None

    parts = filename.split(" - ", 1)
    if len(parts) != 2:
        return None

    artist = parts[0].strip()
    song = parts[1].strip()

    if not artist or not song:
        return None

    return ParsedTitle(
        artist=artist,
        song_title=song,
        genre="Electronic",  # Default fallback
        style="filename",
    )


def embed_metadata_batch(
    filepaths: list[str],
    parse_from_filename: bool = True,
) -> tuple[int, int, list[str]]:
    """Embed metadata into multiple files.

    Args:
        filepaths: List of audio file paths.
        parse_from_filename: If True, try to parse artist/title from filename.

    Returns:
        Tuple of (success_count, fail_count, error_messages).
    """
    success = 0
    fail = 0
    errors = []

    for filepath in filepaths:
        path = Path(filepath)
        if not path.exists():
            fail += 1
            errors.append(f"File not found: {filepath}")
            continue

        # Try to parse from filename
        filename = path.stem
        parsed = _parse_from_filename(filename)

        if parsed is None:
            fail += 1
            errors.append(f"Could not parse filename: {filename}")
            continue

        ok, msg = embed_metadata(filepath, parsed=parsed)
        if ok:
            success += 1
        else:
            fail += 1
            errors.append(msg)

    return success, fail, errors
