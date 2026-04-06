"""Metadata embedding for downloaded NCS songs.

Uses mutagen for tag editing without re-encoding.
Supports MP3, M4A, FLAC, and OGG formats.
"""

import os
from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3, ID3NoHeaderError

from .styles import ParsedTitle, build_tag_values


# --- Tag writing helpers ---


def _tag_mp3(path: str, tags: dict[str, str]) -> None:
    """Set ID3 tags on an MP3 file."""
    try:
        audio = MP3(path, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(path)
        audio.add_tags()

    audio["TIT2"] = ID3(encoding=3, text=[tags["title"]])
    audio["TPE1"] = ID3(encoding=3, text=[tags["artist"]])
    audio["TALB"] = ID3(encoding=3, text=[tags["album"]])
    audio["TCON"] = ID3(encoding=3, text=[tags["genre"]])
    audio["COMM"] = ID3(encoding=3, lang="eng", desc="ncsdl", text=[tags["comment"]])
    audio.save()


def _tag_m4a(path: str, tags: dict[str, str]) -> None:
    """Set tags on an M4A file."""
    audio = MP4(path)
    audio.tags = audio.tags or {}
    audio["\xa9nam"] = tags["title"]
    audio["\xa9ART"] = tags["artist"]
    audio["\xa9alb"] = tags["album"]
    audio["\xa9gen"] = tags["genre"]
    audio["\xa9cmt"] = tags["comment"]
    audio.save()


def _tag_vorbis(path: str, tags: dict[str, str]) -> None:
    """Set tags on a FLAC or OGG file (both use Vorbis comments)."""
    ext = Path(path).suffix.lower()
    audio = FLAC(path) if ext == ".flac" else OggVorbis(path)
    audio["title"] = tags["title"]
    audio["artist"] = tags["artist"]
    audio["album"] = tags["album"]
    audio["genre"] = tags["genre"]
    audio["comment"] = tags["comment"]
    audio.save()


# Dispatcher: extension -> (tag_func, error_label)
_TAG_HANDLERS: dict[str, tuple[callable, str]] = {
    ".mp3": (_tag_mp3, "mp3"),
    ".m4a": (_tag_m4a, "m4a"),
    ".flac": (_tag_vorbis, "flac"),
    ".ogg": (_tag_vorbis, "ogg"),
}


def _build_full_tags(parsed: ParsedTitle) -> dict[str, str]:
    """Build tag values including the ncsdl comment field."""
    tags = build_tag_values(parsed)
    tags["comment"] = f"Downloaded via ncsdl | style: {parsed.style}"
    return tags


# --- Public API ---


def embed_metadata(
    filepath: str,
    parsed: Optional[ParsedTitle] = None,
) -> tuple[bool, str]:
    """Embed metadata into an audio file without re-encoding.

    Args:
        filepath: Path to the audio file.
        parsed: ParsedTitle from style detection.

    Returns:
        Tuple of (success, message).
    """
    if not os.path.exists(filepath):
        return False, f"file not found: {filepath}"

    if parsed is None:
        return False, "no metadata to embed"

    ext = Path(filepath).suffix.lower()
    handler_info = _TAG_HANDLERS.get(ext)
    if handler_info is None:
        return False, f"unsupported format: {ext}"

    tag_func, label = handler_info
    tags = _build_full_tags(parsed)

    try:
        tag_func(filepath, tags)
    except Exception as exc:
        return False, f"{label} tag error: {exc}"

    return True, f"ok: {tags['title']} - {tags['artist']}"


def _parse_from_filename(filename: str) -> Optional[ParsedTitle]:
    """Try to extract artist and title from a filename like 'Artist - Song'."""
    if " - " not in filename:
        return None

    parts = filename.split(" - ", 1)
    if len(parts) != 2:
        return None

    artist, song = (p.strip() for p in parts)
    if not artist or not song:
        return None

    return ParsedTitle(
        artist=artist,
        song_title=song,
        genre="Electronic",
        style="filename",
    )


def embed_metadata_batch(
    filepaths: list[str],
) -> tuple[int, int, list[str]]:
    """Embed metadata into multiple files.

    Returns:
        Tuple of (success_count, fail_count, error_messages).
    """
    success = 0
    fail = 0
    errors: list[str] = []

    for filepath in filepaths:
        path = Path(filepath)
        if not path.exists():
            fail += 1
            errors.append(f"file not found: {filepath}")
            continue

        parsed = _parse_from_filename(path.stem)
        if parsed is None:
            fail += 1
            errors.append(f"could not parse: {path.stem}")
            continue

        ok, msg = embed_metadata(filepath, parsed=parsed)
        if ok:
            success += 1
        else:
            fail += 1
            errors.append(msg)

    return success, fail, errors
