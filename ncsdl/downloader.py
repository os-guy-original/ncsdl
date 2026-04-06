"""YouTube search and download functionality for NCS songs."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .styles import NCS_GENRES, ParsedTitle, parse_title


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


# Title patterns that indicate compilation/mix videos, not individual songs
_COMPILATION_PATTERNS = [
    "top 50",
    "top 20",
    "top 100",
    "top 90",
    "top 30",
    "top 10",
    "best of",
    "most popular",
    "subscriber mix",
    "mashup",
    "live ",
    "radio",
    "hours",
    "most viewed",
    "all time",
    "year (",
    "popular songs by",
]


def _is_compilation(title: str, duration: str) -> bool:
    """Check if a video is a compilation/mix rather than an individual song."""
    title_lower = title.lower()

    # Check for compilation patterns
    for pattern in _COMPILATION_PATTERNS:
        if pattern in title_lower:
            return True

    # Compilations are usually longer than 10 minutes
    # Duration format is like "3:08" or "1:23:45"
    if ":" in duration:
        parts = duration.split(":")
        try:
            if len(parts) == 3:
                # Has hours - definitely a compilation
                return True
            elif len(parts) == 2:
                minutes = int(parts[0])
                if minutes > 10:
                    return True
        except ValueError:
            pass

    return False


def search_ncs_videos(
    genre: Optional[str] = None,
    max_results: int = 100,
) -> list[VideoInfo]:
    """Search NCS YouTube channel for videos.

    Args:
        genre: If provided, only return videos matching this genre.
        max_results: Maximum number of results to return.

    Returns:
        List of VideoInfo objects.
    """
    query = "NoCopyrightSounds"
    if genre:
        query = f"NoCopyrightSounds | {genre} |"

    # Request more results to account for compilation filtering
    search_count = max_results * 3

    cmd = [
        "yt-dlp",
        f"ytsearch{search_count}:{query}",
        "--flat-playlist",
        "--print",
        "%(id)s|%(title)s|%(url)s|%(duration_string)s",
        "--no-download",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("Search timed out. Try reducing max_results.", file=sys.stderr)
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        # The URL always starts with "https://" - use this to split
        url_match = None
        url_start = line.find("|https://")
        if url_start == -1:
            continue

        # Split into: id|title|url|duration
        before_url = line[:url_start]
        after_url = line[url_start + 1:]  # Remove leading |

        parts = after_url.split("|", 2)
        if len(parts) < 2:
            continue

        url = parts[0]
        duration = parts[1] if len(parts) > 1 else "0:00"

        # The before_url part is: id|title
        first_pipe = before_url.find("|")
        if first_pipe == -1:
            continue

        video_id = before_url[:first_pipe]
        title = before_url[first_pipe + 1:]

        title = title.strip()
        duration = duration.strip()

        # Skip compilations
        if _is_compilation(title, duration):
            continue

        parsed = parse_title(title)

        # Filter by genre if specified
        if genre and parsed:
            if not parsed.genre or parsed.genre.lower() != genre.lower():
                continue

        # Stop if we have enough results
        if len(videos) >= max_results:
            break

        videos.append(
            VideoInfo(
                video_id=video_id.strip(),
                title=title,
                url=url.strip(),
                duration=duration,
                parsed=parsed,
            )
        )

    return videos


def get_all_ncs_videos(max_results: int = 1000) -> list[VideoInfo]:
    """Get all NCS videos by searching without genre filter.

    Returns:
        List of all found VideoInfo objects.
    """
    return search_ncs_videos(max_results=max_results)


def download_video(
    video: VideoInfo,
    output_dir: str,
    existing_files: Optional[set[str]] = None,
) -> tuple[str, str]:
    """Download a single video as an audio file.

    Args:
        video: VideoInfo to download.
        output_dir: Directory to save the file.
        existing_files: Set of existing filenames for duplicate check.

    Returns:
        Tuple of (status, message) where status is 'ok', 'skip', or 'fail'.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Determine output filename
    if video.parsed:
        safe_name = _sanitize_filename(
            f"{video.parsed.artist} - {video.parsed.song_title}"
        )
    else:
        safe_name = _sanitize_filename(video.title)

    output_path = os.path.join(output_dir, f"{safe_name}.mp3")

    # Duplicate check
    if existing_files and safe_name in existing_files:
        return "skip", f"Skip duplicate: {safe_name}"

    cmd = [
        "yt-dlp",
        video.url,
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "-o",
        os.path.join(output_dir, f"{safe_name}.%(ext)s"),
        "--no-playlist",
        "--quiet",
        "--no-warnings",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return "fail", f"Timeout: {safe_name}"

    if result.returncode == 0 and os.path.exists(output_path):
        return "ok", f"Downloaded: {safe_name}"

    # Try to get error message
    error = result.stderr.strip() if result.stderr else "Unknown error"
    return "fail", f"Failed: {safe_name} ({error})"


def download_videos(
    videos: list[VideoInfo],
    output_dir: str,
    existing_files: Optional[set[str]] = None,
) -> tuple[int, int, int, list[str]]:
    """Download multiple videos.

    Returns:
        Tuple of (success_count, skipped_count, fail_count, error_messages).
    """
    success = 0
    skipped = 0
    fail = 0
    errors = []

    for i, video in enumerate(videos, 1):
        status, msg = download_video(video, output_dir, existing_files)
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
    # Remove or replace unsafe characters
    unsafe = '<>:"/\\|?*'
    for char in unsafe:
        name = name.replace(char, "")
    # Collapse multiple spaces
    name = " ".join(name.split())
    # Trim
    name = name.strip()
    return name


def get_existing_songs(directory: str) -> set[str]:
    """Get a set of existing song names in a directory.

    Returns filenames without extension for duplicate checking.
    """
    existing = set()
    dir_path = Path(directory)

    if not dir_path.exists():
        return existing

    for f in dir_path.iterdir():
        if f.is_file() and f.suffix.lower() in (".mp3", ".m4a", ".flac", ".ogg", ".wav"):
            existing.add(f.stem)

    return existing
