"""Download logic with corruption detection and automatic name fixing."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..styles import ParsedTitle, build_tag_values
from .files import (
    SUPPORTED_FORMATS,
    find_and_fix_broken_name,
    is_audio_valid,
    sanitize_filename,
)
from .search import VideoInfo


# Tag handlers keyed by file extension
def _tag_mp3(path: str, tags: dict[str, str]) -> None:
    """Set ID3 tags on an MP3 file."""
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, ID3NoHeaderError

    try:
        audio = MP3(path, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(path)
        audio.add_tags()

    audio["TIT2"] = ID3(encoding=3, text=[tags["title"]])
    audio["TPE1"] = ID3(encoding=3, text=[tags["artist"]])
    audio["TALB"] = ID3(encoding=3, text=[tags["album"]])
    audio["TCON"] = ID3(encoding=3, text=[tags["genre"]])
    audio.save()


def _tag_m4a(path: str, tags: dict[str, str]) -> None:
    """Set tags on an M4A file."""
    from mutagen.mp4 import MP4

    audio = MP4(path)
    audio.tags = audio.tags or {}
    audio["\xa9nam"] = tags["title"]
    audio["\xa9ART"] = tags["artist"]
    audio["\xa9alb"] = tags["album"]
    audio["\xa9gen"] = tags["genre"]
    audio.save()


def _tag_vorbis(path: str, tags: dict[str, str]) -> None:
    """Set tags on a FLAC or OGG file (both use Vorbis comments)."""
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis

    ext = os.path.splitext(path)[1].lower()
    audio = FLAC(path) if ext == ".flac" else OggVorbis(path)
    audio["title"] = tags["title"]
    audio["artist"] = tags["artist"]
    audio["album"] = tags["album"]
    audio["genre"] = tags["genre"]
    audio.save()


_TAG_HANDLERS: dict[str, tuple[callable, str]] = {
    ".mp3": (_tag_mp3, "mp3 tag error"),
    ".m4a": (_tag_m4a, "m4a tag error"),
    ".flac": (_tag_vorbis, "flac tag error"),
    ".opus": (_tag_vorbis, "opus tag error"),
    ".ogg": (_tag_vorbis, "ogg tag error"),
}


def _embed_metadata_post(filepath: str, parsed: ParsedTitle) -> bool:
    """Embed clean metadata into a downloaded file using mutagen."""
    ext = os.path.splitext(filepath)[1].lower()
    handler_info = _TAG_HANDLERS.get(ext)
    if handler_info is None:
        return False

    tag_func, _ = handler_info
    tags = build_tag_values(parsed)

    try:
        tag_func(filepath, tags)
        return True
    except Exception as exc:
        print(f"metadata embed warning: {exc}", file=sys.stderr)
        return False


def _resolve_existing(
    output_dir: str,
    video: VideoInfo,
    safe_name: str,
    ext: str,
) -> tuple[bool, Optional[str]]:
    """Check if a valid copy of this video already exists.

    Handles:
    - Correctly named file exists and is valid -> skip
    - Correctly named file exists but corrupted -> delete
    - File exists with old/broken name but valid -> rename to correct name
    - No file found -> return False

    Returns (should_skip, message).
    """
    expected_path = os.path.join(output_dir, f"{safe_name}.{ext}")

    # Check correctly named file
    if os.path.exists(expected_path):
        if is_audio_valid(expected_path):
            return True, None  # Valid, skip
        # Corrupted - delete
        os.remove(expected_path)

    # Scan for matching file by video title
    found, action = find_and_fix_broken_name(
        output_dir, video.video_id, video.title, safe_name, ext
    )
    if found:
        if action == "valid":
            return True, None
        return True, action  # "renamed: ..." or "deleted: ..."

    return False, None


def download_video(
    video: VideoInfo,
    output_dir: str,
    existing_files: set[str],
    audio_format: str = "m4a",
    embed_thumbnail: bool = True,
    max_retries: int = 2,
) -> tuple[str, str]:
    """Download a single video as an audio file.

    Args:
        video: VideoInfo to download.
        output_dir: Directory to save the file.
        existing_files: Set of existing filenames for duplicate check.
        audio_format: Output audio format (m4a, flac, opus, mp3).
        embed_thumbnail: Whether to embed album art.
        max_retries: Number of retry attempts on failure.

    Returns:
        Tuple of (status, message) where status is 'ok', 'skip', or 'fail'.
    """
    import subprocess

    # Resolve and validate output directory
    output_dir = str(Path(output_dir).expanduser().resolve())
    os.makedirs(output_dir, exist_ok=True)

    fmt = SUPPORTED_FORMATS[audio_format]
    ext = fmt["ext"]

    # Determine output filename
    name_source = f"{video.parsed.artist} - {video.parsed.song_title}" if video.parsed else video.title
    safe_name = sanitize_filename(name_source)

    # Check for existing valid copy (handles corruption and broken names)
    should_skip, fix_msg = _resolve_existing(output_dir, video, safe_name, ext)
    if should_skip:
        if fix_msg and fix_msg.startswith("renamed"):
            return "skip", f"skip ({fix_msg}): {safe_name}"
        if fix_msg and fix_msg.startswith("deleted"):
            pass  # Will re-download
        if fix_msg and fix_msg == "valid":
            return "skip", f"skip: {safe_name}"

    # Fast path: check raw filename set
    if safe_name in existing_files:
        output_path = os.path.join(output_dir, f"{safe_name}.{ext}")
        if os.path.exists(output_path) and is_audio_valid(output_path):
            return "skip", f"skip: {safe_name}"

    cmd = [
        "yt-dlp",
        video.url,
        "-x",
        "--audio-format",
        audio_format,
        "--audio-quality",
        fmt["quality"],
        "-o",
        os.path.join(output_dir, f"{safe_name}.%(ext)s"),
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--no-embed-metadata",
    ]

    if embed_thumbnail:
        cmd.append("--embed-thumbnail")

    last_error = ""
    for attempt in range(1, max_retries + 2):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            last_error = "timeout"
            continue

        output_path = os.path.join(output_dir, f"{safe_name}.{ext}")
        if result.returncode == 0 and os.path.exists(output_path):
            # Validate downloaded file
            if not is_audio_valid(output_path):
                last_error = "corrupted file"
                os.remove(output_path)
                continue

            # Embed metadata
            if video.parsed:
                _embed_metadata_post(output_path, video.parsed)
            return "ok", f"ok: {safe_name}.{ext}"

        last_error = result.stderr.strip() if result.stderr else "unknown error"

    return "fail", f"fail: {safe_name} ({last_error})"


def download_videos(
    videos: list[VideoInfo],
    output_dir: str,
    existing_files: set[str],
    audio_format: str = "m4a",
    embed_thumbnail: bool = True,
    max_retries: int = 2,
) -> tuple[int, int, int, list[str]]:
    """Download multiple videos.

    Returns:
        Tuple of (success_count, skipped_count, fail_count, error_messages).
    """
    success = 0
    skipped = 0
    fail = 0
    errors: list[str] = []

    for i, video in enumerate(videos, 1):
        status, msg = download_video(
            video, output_dir, existing_files,
            audio_format=audio_format,
            embed_thumbnail=embed_thumbnail,
            max_retries=max_retries,
        )
        if status == "ok":
            success += 1
        elif status == "skip":
            skipped += 1
        else:
            fail += 1
            errors.append(msg)
        print(f"[{i}/{len(videos)}] {msg}")

    return success, skipped, fail, errors
