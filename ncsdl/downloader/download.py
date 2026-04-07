"""Download logic with video ID tagging and rename detection.

Each downloaded file gets a custom tag: `ncsdl_id` (YouTube video ID).
This is the single source of truth for matching files to videos.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from ..styles import build_tag_values
from .files import (
    SUPPORTED_FORMATS,
    get_ncsdl_id,
    is_audio_valid,
    sanitize_filename,
)
from .search import VideoInfo
from .track import (
    load_track,
    record_download,
    remove_entry,
    save_track,
)


# --- Metadata tag writers ---

def _tag_mp3(path: str, tags: dict[str, str], video_id: str) -> None:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, ID3NoHeaderError, TXXX

    try:
        audio = MP3(path, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(path)
        audio.add_tags()

    audio["TIT2"] = ID3(encoding=3, text=[tags["title"]])
    audio["TPE1"] = ID3(encoding=3, text=[tags["artist"]])
    audio["TALB"] = ID3(encoding=3, text=[tags["album"]])
    audio["TCON"] = ID3(encoding=3, text=[tags["genre"]])
    audio["ncsdl_id"] = TXXX(encoding=3, desc="ncsdl_id", text=[video_id])
    audio.save()


def _tag_m4a(path: str, tags: dict[str, str], video_id: str) -> None:
    from mutagen.mp4 import MP4

    audio = MP4(path)
    audio.tags = audio.tags or {}
    audio["\xa9nam"] = tags["title"]
    audio["\xa9ART"] = tags["artist"]
    audio["\xa9alb"] = tags["album"]
    audio["\xa9gen"] = tags["genre"]
    audio["----:com.apple.iTunes:ncsdl_id"] = [video_id.encode("utf-8")]
    audio.save()


def _tag_vorbis(path: str, tags: dict[str, str], video_id: str) -> None:
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.oggopus import OggOpus

    ext = os.path.splitext(path)[1].lower()
    if ext == ".flac":
        audio = FLAC(path)
    elif ext == ".opus":
        audio = OggOpus(path)
    else:
        audio = OggVorbis(path)
    audio["title"] = tags["title"]
    audio["artist"] = tags["artist"]
    audio["album"] = tags["album"]
    audio["genre"] = tags["genre"]
    audio["ncsdl_id"] = video_id
    audio.save()


_TAG_HANDLERS: dict[str, tuple[callable, str]] = {
    ".mp3": (_tag_mp3, "mp3 tag error"),
    ".m4a": (_tag_m4a, "m4a tag error"),
    ".flac": (_tag_vorbis, "flac tag error"),
    ".opus": (_tag_vorbis, "opus tag error"),
    ".ogg": (_tag_vorbis, "ogg tag error"),
}


def _embed_metadata(filepath: str, parsed, video_id: str) -> bool:
    """Embed clean metadata + video ID tag into an audio file."""
    ext = os.path.splitext(filepath)[1].lower()
    handler = _TAG_HANDLERS.get(ext)
    if handler is None:
        return False

    tag_func, _ = handler
    tags = build_tag_values(parsed)

    try:
        tag_func(filepath, tags, video_id)
        return True
    except Exception as exc:
        print(f"metadata embed warning: {exc}", file=sys.stderr)
        return False


# --- Rename logic ---

def _scan_for_misnamed(
    output_dir: str,
    safe_name: str,
    ext: str,
) -> dict[str, str]:
    """Scan directory for audio files and read their ncsdl_id tags.

    Returns {video_id: filepath} for files whose expected name doesn't match.
    Excludes the correctly-named file for the current video.
    """
    dir_path = Path(output_dir)
    if not dir_path.is_dir():
        return {}

    result = {}
    correct_path = os.path.join(output_dir, f"{safe_name}.{ext}")

    for f in dir_path.iterdir():
        if not f.is_file() or f.suffix.lower() not in {".mp3", ".m4a", ".flac", ".opus", ".ogg"}:
            continue
        if str(f) == correct_path:
            continue

        vid = get_ncsdl_id(str(f))
        if vid:
            result[vid] = str(f)

    return result


def _check_by_id(
    output_dir: str,
    video: VideoInfo,
    safe_name: str,
    ext: str,
    track_data: dict[str, dict],
    misnamed: dict[str, str],
) -> tuple[bool, str]:
    """Check if this video's file already exists (correctly named or misnamed).

    Uses ncsdl_id tags on disk files as the primary match.
    Falls back to tracking data.

    Returns (should_skip, message).
    """
    vid = video.video_id
    expected_path = os.path.join(output_dir, f"{safe_name}.{ext}")

    # 1. Check if correctly named file exists
    if os.path.exists(expected_path):
        file_id = get_ncsdl_id(expected_path)
        if file_id == vid:
            if is_audio_valid(expected_path):
                return True, "skip"
            os.remove(expected_path)
            remove_entry(output_dir, vid)
            return False, "deleted-corrupted"

    # 2. Check if a misnamed file has this video's ID tag
    if vid in misnamed:
        old_path = misnamed[vid]
        if is_audio_valid(old_path):
            Path(old_path).rename(expected_path)
            return True, f"renamed: {Path(old_path).name}"
        else:
            os.remove(old_path)
            remove_entry(output_dir, vid)
            return False, f"deleted-corrupted: {Path(old_path).name}"

    # 3. Fallback: check tracking data
    entry = track_data.get(vid)
    if entry:
        tracked_expected = entry.get("expected", "")
        tracked_path = os.path.join(output_dir, f"{tracked_expected}.{ext}")

        if tracked_expected == safe_name:
            # Tracking says it should be correctly named, but file isn't there
            remove_entry(output_dir, vid)
            return False, ""

        if os.path.exists(tracked_path) and is_audio_valid(tracked_path):
            Path(tracked_path).rename(expected_path)
            entry["expected"] = safe_name
            save_track(output_dir, track_data)
            return True, f"renamed: {Path(tracked_path).name}"
        else:
            if os.path.exists(tracked_path):
                os.remove(tracked_path)
            remove_entry(output_dir, vid)
            return False, f"deleted-corrupted: {Path(tracked_path).name}"

    return False, ""


# Global fallback mode: "ask" | "always" | "stop"
_fallback_mode: str = "ask"


def set_fallback_mode(value: str) -> None:
    """Set fallback mode: 'ask', 'always', or 'stop'."""
    global _fallback_mode
    _fallback_mode = value


def get_fallback_mode() -> str:
    """Get current fallback mode."""
    return _fallback_mode


def _format_unavailable_error(stderr: str) -> bool:
    """Check if stderr indicates format not available."""
    return "Requested format is not available" in stderr


def _try_download(
    cmd: list[str],
    expected_path: str,
    timeout: int = 300,
) -> tuple[bool, str]:
    """Run a yt-dlp command. Returns (success, error_msg)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"

    if result.returncode == 0 and os.path.exists(expected_path):
        return True, ""

    return False, result.stderr.strip() if result.stderr else "unknown error"


def download_video(
    video: VideoInfo,
    output_dir: str,
    existing_files: set[str],
    audio_format: str = "m4a",
    embed_thumbnail: bool = True,
    max_retries: int = 2,
    track_data: dict | None = None,
    misnamed: dict | None = None,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    fallback_handler: callable | None = None,
) -> tuple[str, str, bool, bool]:
    """Download a single video as an audio file.

    Tries the requested format first. If unavailable, uses fallback_handler
    to decide whether to accept an alternative format.

    Returns (status, message, was_redownloaded, should_stop).
    """
    output_dir = str(Path(output_dir).expanduser().resolve())
    os.makedirs(output_dir, exist_ok=True)

    fmt = SUPPORTED_FORMATS[audio_format]
    ext = fmt["ext"]

    name_source = f"{video.parsed.artist} - {video.parsed.song_title}" if video.parsed else video.title
    safe_name = sanitize_filename(name_source)

    redownloading = False

    # Check existing
    if track_data is not None and misnamed is not None:
        found, msg = _check_by_id(output_dir, video, safe_name, ext, track_data, misnamed)
        if found:
            if "renamed" in msg:
                return "skip", f"skip ({msg}): {safe_name}", False, False
            return "skip", f"skip: {safe_name}", False, False

    # Corrupted file with correct name: delete before re-downloading
    expected_path = os.path.join(output_dir, f"{safe_name}.{ext}")
    if os.path.exists(expected_path) and not is_audio_valid(expected_path):
        os.remove(expected_path)
        redownloading = True

    # Fast path: raw filename set
    if safe_name in existing_files and os.path.exists(expected_path) and is_audio_valid(expected_path):
        return "skip", f"skip: {safe_name}", False, False

    # Build base command parts
    base_cmd = [
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
        base_cmd.append("--embed-thumbnail")
    if cookies_from_browser:
        base_cmd.extend(["--cookies-from-browser", cookies_from_browser])
    if cookies_file:
        base_cmd.extend(["--cookies", cookies_file])

    # Strategy 1: Try exact format first
    exact_cmd = base_cmd.copy()
    exact_cmd.insert(2, f"ba[ext={audio_format}]")

    success, err = _try_download(exact_cmd, expected_path)
    used_fallback = False

    if not success and _format_unavailable_error(err):
        # Format not available - check fallback mode
        mode = get_fallback_mode()

        if mode == "always":
            used_fallback = True
        elif mode == "ask" and fallback_handler:
            choice = fallback_handler(safe_name, video.title)  # (filename, youtube_title)
            if choice == "stop":
                return "stop", f"stop (format unavailable): {safe_name}", False, True
            if choice == "always":
                set_fallback_mode("always")
                used_fallback = True
            elif choice == "now":
                used_fallback = True

        if used_fallback:
            # Fallback: let yt-dlp pick best available audio and convert
            fallback_cmd = base_cmd.copy()
            # Insert -f bestaudio/ba BEFORE -x
            idx = fallback_cmd.index("-x")
            fallback_cmd[idx:idx] = ["-f", "bestaudio/ba"]
            success, err = _try_download(fallback_cmd, expected_path)

    last_error = err
    for attempt in range(1, max_retries + 2):
        if success:
            break

        if "timeout" in last_error:
            last_error = "timeout"
            continue

        # Try again (for network errors, not format issues)
        if used_fallback:
            fallback_cmd = base_cmd.copy()
            idx = fallback_cmd.index("-x")
            fallback_cmd[idx:idx] = ["-f", "bestaudio/ba"]
            success, last_error = _try_download(fallback_cmd, expected_path)
        else:
            success, last_error = _try_download(base_cmd, expected_path)

    if success and os.path.exists(expected_path):
        if not is_audio_valid(expected_path):
            os.remove(expected_path)
            return "fail", f"fail: {safe_name} (corrupted file)", False, False

        if video.parsed:
            _embed_metadata(expected_path, video.parsed, video.video_id)

        if track_data is not None:
            record_download(output_dir, video.video_id, safe_name, video.title)

        if used_fallback or redownloading:
            return "ok", f"ok*: {safe_name}.{ext}", redownloading, False
        return "ok", f"ok: {safe_name}.{ext}", False, False

    return "fail", f"fail: {safe_name} ({last_error})", False, False


def download_videos(
    videos: list[VideoInfo],
    output_dir: str,
    existing_files: set[str],
    audio_format: str = "m4a",
    embed_thumbnail: bool = True,
    max_retries: int = 2,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    fallback_handler: callable | None = None,
) -> tuple[int, int, int, int, int, list[str]]:
    """Download multiple videos.

    Returns:
        Tuple of (downloaded, renamed, re-downloaded, skipped, failed, errors).
    """
    output_dir = str(Path(output_dir).expanduser().resolve())
    track_data = load_track(output_dir)

    downloaded = 0
    renamed = 0
    redownloaded = 0
    skipped = 0
    fail = 0
    errors: list[str] = []

    for i, video in enumerate(videos, 1):
        fmt = SUPPORTED_FORMATS[audio_format]
        name_source = f"{video.parsed.artist} - {video.parsed.song_title}" if video.parsed else video.title
        safe_name = sanitize_filename(name_source)

        # Scan for misnamed files once per video (keeps it fresh as files get renamed)
        misnamed = _scan_for_misnamed(output_dir, safe_name, fmt["ext"])

        status, msg, was_redownloaded, should_stop = download_video(
            video, output_dir, existing_files,
            audio_format=audio_format,
            embed_thumbnail=embed_thumbnail,
            max_retries=max_retries,
            track_data=track_data,
            misnamed=misnamed,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
            fallback_handler=fallback_handler,
        )
        if status == "ok":
            if was_redownloaded:
                redownloaded += 1
            elif "renamed" not in msg:
                downloaded += 1
        elif status == "skip":
            if "renamed" in msg:
                renamed += 1
            else:
                skipped += 1
        elif status == "stop":
            skipped += 1
            print(f"[{i}/{len(videos)}] {msg}")
            break
        else:
            fail += 1
            errors.append(msg)
            print(f"[{i}/{len(videos)}] {msg}")
            continue

        print(f"[{i}/{len(videos)}] {msg}")

    return downloaded, renamed, redownloaded, skipped, fail, errors
