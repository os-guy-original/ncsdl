"""YouTube search and download functionality for NCS songs."""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from .styles import ParsedTitle, parse_title, build_tag_values

# Unsafe characters for filenames (regex pattern)
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]')

# Supported audio formats with their yt-dlp codec settings
SUPPORTED_FORMATS = {
    "m4a": {"ext": "m4a", "codec": "aac", "quality": "0"},
    "flac": {"ext": "flac", "codec": "flac", "quality": "0"},
    "opus": {"ext": "opus", "codec": "opus", "quality": "0"},
    "mp3": {"ext": "mp3", "codec": "mp3", "quality": "0"},
}

# Audio file extensions for duplicate detection
_AUDIO_EXTENSIONS = frozenset({".mp3", ".m4a", ".flac", ".opus", ".ogg", ".wav"})

# Metadata tag handlers keyed by file extension
# Each handler receives (path, title, artist, album, genre) and writes tags.
# Imports are deferred to avoid loading all mutagen modules upfront.


@dataclass
class VideoInfo:
    """Information about a YouTube video."""
    video_id: str
    title: str
    url: str
    duration: str
    parsed: Optional[ParsedTitle] = None


def check_dependencies() -> list[str]:
    """Check if required CLI tools are installed.

    Returns a list of missing dependencies.
    """
    missing = []
    for tool in ("yt-dlp", "ffprobe"):
        result = subprocess.run(
            ["which", tool],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            missing.append(tool)
    return missing


# Title patterns that indicate compilation/mix videos, not individual songs.
# Kept minimal — duration (>10 min) catches most mixes.
# Avoid patterns like "live", "mashup", "radio", "best of" which match real song titles.
_COMPILATION_PATTERNS = frozenset({
    "top 50",
    "top 20",
    "top 100",
    "top 90",
    "top 30",
    "top 10",
    "subscriber mix",
    "most viewed",
    "all time",
    "popular songs by",
})


def _validate_output_dir(directory: str) -> str:
    """Resolve and validate output directory path.

    Expands user home directory and resolves any '..' sequences
    to produce a canonical absolute path.
    """
    resolved = Path(directory).expanduser().resolve()
    return str(resolved)


def _is_compilation(title: str, duration: str) -> bool:
    """Check if a video is a compilation/mix rather than an individual song."""
    title_lower = title.lower()

    for pattern in _COMPILATION_PATTERNS:
        if pattern in title_lower:
            return True

    # Compilations are usually longer than 10 minutes
    if ":" in duration:
        parts = duration.split(":")
        try:
            if len(parts) == 3:
                return True
            if len(parts) == 2 and int(parts[0]) > 10:
                return True
        except ValueError:
            pass

    return False


def _parse_ytdlp_line(line: str) -> Optional[tuple[str, str, str, str]]:
    """Parse a single yt-dlp output line into (id, title, url, duration).

    Returns None if the line cannot be parsed.
    """
    url_start = line.find("|https://")
    if url_start == -1:
        return None

    before_url = line[:url_start]
    after_url = line[url_start + 1:]

    first_pipe = before_url.find("|")
    if first_pipe == -1:
        return None

    video_id = before_url[:first_pipe].strip()
    title = before_url[first_pipe + 1:].strip()

    parts = after_url.split("|", 1)
    url = parts[0].strip()
    duration = parts[1].strip() if len(parts) > 1 else "0:00"

    return video_id, title, url, duration


def _build_search_cmd(query: str, count: int) -> list[str]:
    """Build yt-dlp command for searching."""
    return [
        "yt-dlp",
        f"ytsearch{count}:{query}",
        "--flat-playlist",
        "--print",
        "%(id)s|%(title)s|%(url)s|%(duration_string)s",
        "--no-download",
    ]


def _build_channel_cmd() -> list[str]:
    """Build yt-dlp command for the NCS channel uploads playlist."""
    return [
        "yt-dlp",
        NCS_CHANNEL_URL,
        "--flat-playlist",
        "--print",
        "%(id)s|%(title)s|%(url)s|%(duration_string)s",
        "--no-download",
    ]


def _parse_video_lines(
    lines: list[str],
    genre: Optional[str],
    max_results: int,
) -> list[VideoInfo]:
    """Parse yt-dlp output lines into VideoInfo objects."""
    videos: list[VideoInfo] = []
    for line in lines:
        parsed_line = _parse_ytdlp_line(line)
        if parsed_line is None:
            continue

        video_id, title, url, duration = parsed_line

        if _is_compilation(title, duration):
            continue

        parsed = parse_title(title)

        if genre and parsed:
            if not parsed.genre or parsed.genre.lower() != genre.lower():
                continue

        if max_results > 0 and len(videos) >= max_results:
            break

        videos.append(VideoInfo(
            video_id=video_id,
            title=title,
            url=url,
            duration=duration,
            parsed=parsed,
        ))

    return videos


def search_ncs_videos(
    genre: Optional[str] = None,
    max_results: int = 0,
) -> list[VideoInfo]:
    """Search NCS YouTube channel for videos.

    Uses the channel uploads playlist for full-library scans,
    and yt-dlp search for genre-filtered queries.

    Args:
        genre: If provided, only return videos matching this genre.
        max_results: Maximum number of results to return. 0 = no limit.

    Returns:
        List of VideoInfo objects.
    """
    # Use channel URL directly when no genre filter + unlimited
    if not genre and max_results == 0:
        cmd = _build_channel_cmd()
        timeout = 180
    else:
        limit = max_results if max_results > 0 else 5000
        query = "NoCopyrightSounds"
        if genre:
            query = f"NoCopyrightSounds | {genre} |"
        cmd = _build_search_cmd(query, limit * 3)
        timeout = 120

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        print("search timed out. try reducing max_results.", file=sys.stderr)
        return []

    return _parse_video_lines(result.stdout.splitlines(), genre, max_results)


NCS_CHANNEL_URL = "https://www.youtube.com/@NoCopyrightSounds/videos"


def count_ncs_videos() -> int:
    """Count total videos on the NCS YouTube channel.

    Returns 0 on failure or timeout.
    """
    cmd = [
        "yt-dlp",
        NCS_CHANNEL_URL,
        "--flat-playlist",
        "--print",
        "%(id)s",
        "--no-download",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return 0

    count = 0
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("ERROR") and not line.startswith("WARNING"):
            count += 1

    return count


def get_all_ncs_videos(max_results: int = 1000) -> list[VideoInfo]:
    """Get all NCS videos by searching without genre filter."""
    return search_ncs_videos(max_results=max_results)


# --- Metadata embedding helpers (dispatcher pattern) ---


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

    ext = Path(path).suffix.lower()
    audio = FLAC(path) if ext == ".flac" else OggVorbis(path)
    audio["title"] = tags["title"]
    audio["artist"] = tags["artist"]
    audio["album"] = tags["album"]
    audio["genre"] = tags["genre"]
    audio.save()


# Dispatcher: extension -> (tag_func, error_message)
_TAG_HANDLERS: dict[str, tuple[callable, str]] = {
    ".mp3": (_tag_mp3, "mp3 tag error"),
    ".m4a": (_tag_m4a, "m4a tag error"),
    ".flac": (_tag_vorbis, "flac tag error"),
    ".opus": (_tag_vorbis, "opus tag error"),
    ".ogg": (_tag_vorbis, "ogg tag error"),
}


def _embed_metadata_post(filepath: str, parsed: ParsedTitle) -> bool:
    """Embed clean metadata into a downloaded file using mutagen.

    Returns True on success, False on failure.
    """
    ext = Path(filepath).suffix.lower()
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


# --- Download functions ---


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
    output_dir = _validate_output_dir(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    fmt = SUPPORTED_FORMATS[audio_format]
    ext = fmt["ext"]

    # Determine output filename
    name_source = f"{video.parsed.artist} - {video.parsed.song_title}" if video.parsed else video.title
    safe_name = _sanitize_filename(name_source)

    output_path = os.path.join(output_dir, f"{safe_name}.{ext}")

    # Duplicate check
    if safe_name in existing_files:
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

        if result.returncode == 0 and os.path.exists(output_path):
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


def _sanitize_filename(name: str) -> str:
    """Remove unsafe characters from filename."""
    name = _UNSAFE_CHARS.sub("", name)
    name = " ".join(name.split())
    return name.strip()


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


# --- Download queue persistence ---

_QUEUE_FILENAME = ".ncsdl_queue.json"


def _queue_path(output_dir: str) -> str:
    """Get the queue file path for an output directory."""
    return os.path.join(output_dir, _QUEUE_FILENAME)


def save_queue(videos: list[VideoInfo], output_dir: str) -> None:
    """Save a download queue to disk for resuming later."""
    path = _queue_path(output_dir)
    data = [asdict(v) for v in videos]
    with open(path, "w") as f:
        json.dump(data, f)


def load_queue(output_dir: str) -> list[VideoInfo]:
    """Load a saved download queue. Returns empty list if none exists."""
    path = _queue_path(output_dir)
    if not os.path.exists(path):
        return []

    try:
        with open(path) as f:
            data = json.load(f)

        videos = []
        for item in data:
            # Reconstruct ParsedTitle from dict if present
            if "parsed" in item and item["parsed"] is not None:
                item["parsed"] = ParsedTitle(**item["parsed"])
            videos.append(VideoInfo(**item))
        return videos
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def clear_queue(output_dir: str) -> None:
    """Remove a saved download queue file."""
    path = _queue_path(output_dir)
    if os.path.exists(path):
        os.remove(path)


def filter_downloaded(videos: list[VideoInfo], existing: set[str]) -> list[VideoInfo]:
    """Remove already-downloaded videos from a queue.

    Returns only videos that aren't in the existing files set.
    """
    result = []
    for v in videos:
        if v.parsed:
            name = _sanitize_filename(f"{v.parsed.artist} - {v.parsed.song_title}")
        else:
            name = _sanitize_filename(v.title)
        if name not in existing:
            result.append(v)
    return result
