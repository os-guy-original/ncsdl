"""Metadata embedding for downloaded NCS songs.

Uses mutagen for tag editing without re-encoding.
Supports MP3, M4A, FLAC, and OGG formats.
"""

import os
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3, ID3NoHeaderError

from .styles import ParsedTitle


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

    # Build tag values
    title = parsed.song_title
    if parsed.suffix:
        title = f"{title} {parsed.suffix}"

    artist = parsed.artist
    if parsed.featuring:
        artist = f"{artist} feat. {parsed.featuring}"

    genre = parsed.genre or "Electronic"
    album = "NCS - NoCopyrightSounds"
    comment = f"Downloaded via ncsdl | style: {parsed.style}"

    try:
        if ext == ".mp3":
            _tag_mp3(filepath, title, artist, genre, album, comment)
        elif ext == ".m4a":
            _tag_m4a(filepath, title, artist, genre, album, comment)
        elif ext == ".flac":
            _tag_flac(filepath, title, artist, genre, album, comment)
        elif ext == ".ogg":
            _tag_ogg(filepath, title, artist, genre, album, comment)
        else:
            return False, f"unsupported format: {ext}"
    except Exception as exc:
        return False, f"tag error: {exc}"

    return True, f"ok: {title} - {artist}"


def _tag_mp3(
    path: str,
    title: str,
    artist: str,
    genre: str,
    album: str,
    comment: str,
) -> None:
    """Set ID3 tags on an MP3 file."""
    try:
        audio = MP3(path, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(path)
        audio.add_tags()

    audio["TIT2"] = ID3(encoding=3, text=[title])
    audio["TPE1"] = ID3(encoding=3, text=[artist])
    audio["TALB"] = ID3(encoding=3, text=[album])
    audio["TCON"] = ID3(encoding=3, text=[genre])
    audio["COMM"] = ID3(encoding=3, lang="eng", desc="ncsdl", text=[comment])
    audio.save()


def _tag_m4a(
    path: str,
    title: str,
    artist: str,
    genre: str,
    album: str,
    comment: str,
) -> None:
    """Set tags on an M4A file."""
    audio = MP4(path)
    audio.tags = audio.tags or {}
    audio["\xa9nam"] = title      # title
    audio["\xa9ART"] = artist     # artist
    audio["\xa9alb"] = album      # album
    audio["\xa9gen"] = genre      # genre
    audio["\xa9cmt"] = comment    # comment
    audio.save()


def _tag_flac(
    path: str,
    title: str,
    artist: str,
    genre: str,
    album: str,
    comment: str,
) -> None:
    """Set tags on a FLAC file."""
    audio = FLAC(path)
    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    audio["genre"] = genre
    audio["comment"] = comment
    audio.save()


def _tag_ogg(
    path: str,
    title: str,
    artist: str,
    genre: str,
    album: str,
    comment: str,
) -> None:
    """Set tags on an OGG file."""
    audio = OggVorbis(path)
    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    audio["genre"] = genre
    audio["comment"] = comment
    audio.save()


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
    errors = []

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
