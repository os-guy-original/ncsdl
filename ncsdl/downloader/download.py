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

    Returns {video_id: filepath} for files whose expected name didn't match.
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


def _find_downloaded_file(safe_name: str, output_dir: str, target_ext: str) -> str | None:
    """Find a downloaded audio file matching safe_name with any extension.

    Checks target_ext first, then other audio extensions.
    Returns the path if found and valid, None otherwise.
    """
    target_path = os.path.join(output_dir, f"{safe_name}.{target_ext}")
    if os.path.exists(target_path) and is_audio_valid(target_path):
        return target_path

    for alt_ext in ("webm", "m4a", "mp3", "opus", "flac", "ogg"):
        if alt_ext == target_ext:
            continue
        alt_path = os.path.join(output_dir, f"{safe_name}.{alt_ext}")
        if os.path.exists(alt_path) and is_audio_valid(alt_path):
            return alt_path

    return None


def _convert_audio(input_path: str, output_path: str) -> bool:
    """Convert an audio file to a different format using ffmpeg."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-vn", output_path],
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0 and os.path.exists(output_path):
            os.remove(input_path)
            return True
    except (subprocess.TimeoutExpired, OSError):
        pass
    return False


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
) -> tuple[str, str, bool, bool]:
    """Download a single video as an audio file.

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
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
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

    base_cmd.append("--no-continue")

    def _clean_partial_files(path: str) -> None:
        """Remove partial/temp download files that may interfere."""
        base = os.path.splitext(path)[0]
        for suffix in (".part", ".tmp", ".ytdl", ".webm", ".m4a", ".mp3", ".opus", ".flac", ".ogg"):
            p = base + suffix
            if os.path.exists(p) and p != path:
                try:
                    os.remove(p)
                except OSError:
                    pass

    def _try_with_cleanup(cmd: list[str], path: str, timeout: int = 300) -> tuple[bool, str]:
        """Try download, and if it fails with range error, clean and retry once."""
        success, err = _try_download(cmd, path, timeout)
        if not success and ("416" in err or "range" in err.lower()):
            _clean_partial_files(path)
            success, err = _try_download(cmd, path, timeout)
        return success, err

    # --- Download ---

    # Strategy 1: Auto-select best format, convert to m4a via --audio-format
    auto_cmd = base_cmd.copy()
    success, err = _try_with_cleanup(auto_cmd, expected_path)

    # Strategy 2 (nuclear): Download raw audio in any format, convert manually
    if not success:
        _clean_partial_files(expected_path)
        raw_cmd = base_cmd.copy()
        # Replace --audio-format <format> with --audio-format best
        af_idx = raw_cmd.index("--audio-format")
        raw_cmd[af_idx + 1] = "best"
        # Remove --audio-quality (not applicable with --audio-format best)
        aq_idx = raw_cmd.index("--audio-quality")
        del raw_cmd[aq_idx:aq_idx + 2]

        try:
            result = subprocess.run(
                raw_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            result = None
            err = "timeout"

        if result is not None and result.returncode == 0:
            raw_path = _find_downloaded_file(safe_name, output_dir, ext)
            if raw_path:
                raw_ext = os.path.splitext(raw_path)[1].lower()
                if raw_ext != f".{ext}":
                    if _convert_audio(raw_path, expected_path):
                        success = True
                    else:
                        for p in (raw_path, expected_path):
                            if os.path.exists(p):
                                try:
                                    os.remove(p)
                                except OSError:
                                    pass
                else:
                    success = True
        elif result is not None:
            err = result.stderr.strip() if result.stderr else "unknown error"

    # Retry loop — only for transient errors (timeouts, network)
    last_error = err
    for attempt in range(1, max_retries + 2):
        if success:
            break

        _clean_partial_files(expected_path)

        if "timeout" in last_error:
            last_error = "timeout"
            continue

        auto_cmd = base_cmd.copy()
        success, last_error = _try_with_cleanup(auto_cmd, expected_path)

    # Validate and finalize
    final_path = _find_downloaded_file(safe_name, output_dir, ext)

    if success and final_path:
        # Convert if the file is in a different format than requested
        actual_ext = os.path.splitext(final_path)[1].lower()
        if actual_ext != f".{ext}":
            if _convert_audio(final_path, expected_path):
                final_path = expected_path
            else:
                for p in (final_path, expected_path):
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass
                return "fail", f"fail: {safe_name} (conversion error)", False, False

        if not is_audio_valid(final_path):
            os.remove(final_path)
            return "fail", f"fail: {safe_name} (corrupted file)", False, False

        if video.parsed:
            _embed_metadata(final_path, video.parsed, video.video_id)

        if track_data is not None:
            record_download(output_dir, video.video_id, safe_name, video.title)

        if redownloading:
            return "ok", f"ok: {safe_name}.{ext}", True, False
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
        else:
            fail += 1
            errors.append(msg)
            print(f"[{i}/{len(videos)}] {msg}")
            continue

        print(f"[{i}/{len(videos)}] {msg}")

    return downloaded, renamed, redownloaded, skipped, fail, errors
