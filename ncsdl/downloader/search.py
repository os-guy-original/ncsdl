"""YouTube search and channel scanning for NCS songs."""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from ..styles import ParsedTitle, parse_title

NCS_CHANNEL_URL = "https://www.youtube.com/@NoCopyrightSounds/videos"

# Compilation/mix/non-song detection patterns.
# These match titles that are NOT individual songs.
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
    "behind the scenes",
    "10 years",
    "thank you",
    "songs mix",
    "gauntlet mix",
    "geometry dash mix",
    "new years mix",
    "new years eve mix",
    "year end mix",
    "13 years",
    "10 year mix",
    "10 billion views",
    "heavy gaming",
    "halloween songs",
    "feels like summer",
    "3 hours",
    "1 hour mix",
    "best of ",
    "best of 20",
    "best of 201",
    "best of chill",
    "best of drum",
    "best of house",
    "best of electronic",
    "album mix",
    " : elevate ",
    " : reloaded ",
    " : alpha ",
    " : colors ",
    "is love, ncs is life",
    "halloween songs mix",
    "ncs mashup",
    "ncs 202",
    "biggest ncs",
    "biggest nocopyrightsounds",
})


def check_dependencies() -> list[str]:
    """Check if required CLI tools are installed."""
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


@dataclass
class VideoInfo:
    """Information about a YouTube video."""
    video_id: str
    title: str
    url: str
    duration: str
    parsed: Optional[ParsedTitle] = None


def _parse_ytdlp_line(line: str) -> Optional[tuple[str, str, str, str]]:
    """Parse a single yt-dlp output line into (id, title, url, duration)."""
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


def _is_compilation(title: str, duration: str) -> bool:
    """Check if a video is a compilation/mix rather than an individual song."""
    title_lower = title.lower()
    for pattern in _COMPILATION_PATTERNS:
        if pattern in title_lower:
            return True

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


def _parse_video_lines(
    lines: list[str],
    genre: Optional[str],
    max_results: int,
    include_mixes: bool = False,
) -> list[VideoInfo]:
    """Parse yt-dlp output lines into VideoInfo objects."""
    videos: list[VideoInfo] = []
    for line in lines:
        parsed_line = _parse_ytdlp_line(line)
        if parsed_line is None:
            continue

        video_id, title, url, duration = parsed_line

        if not include_mixes and _is_compilation(title, duration):
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


def _run_ytdlp(cmd: list[str], timeout: int) -> str:
    """Run a yt-dlp command and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print("search timed out. try reducing max_results.", file=sys.stderr)
        return ""


def search_ncs_videos(
    genre: Optional[str] = None,
    max_results: int = 0,
    include_mixes: bool = False,
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
    if not genre and max_results == 0:
        cmd = [
            "yt-dlp",
            NCS_CHANNEL_URL,
            "--flat-playlist",
            "--print",
            "%(id)s|%(title)s|%(url)s|%(duration_string)s",
            "--no-download",
        ]
        timeout = 180
    else:
        limit = max_results if max_results > 0 else 5000
        query = "NoCopyrightSounds"
        if genre:
            query = f"NoCopyrightSounds | {genre} |"
        cmd = [
            "yt-dlp",
            f"ytsearch{limit * 3}:{query}",
            "--flat-playlist",
            "--print",
            "%(id)s|%(title)s|%(url)s|%(duration_string)s",
            "--no-download",
        ]
        timeout = 120

    output = _run_ytdlp(cmd, timeout)
    if not output:
        return []

    return _parse_video_lines(output.splitlines(), genre, max_results, include_mixes)


def get_all_ncs_videos(max_results: int = 1000, include_mixes: bool = False) -> list[VideoInfo]:
    """Get all NCS videos by searching without genre filter."""
    return search_ncs_videos(max_results=max_results, include_mixes=include_mixes)


def count_ncs_videos() -> int:
    """Count total videos on the NCS YouTube channel."""
    cmd = [
        "yt-dlp",
        NCS_CHANNEL_URL,
        "--flat-playlist",
        "--print",
        "%(id)s",
        "--no-download",
    ]

    output = _run_ytdlp(cmd, 120)
    if not output:
        return 0

    return sum(
        1 for line in output.splitlines()
        if line.strip() and not line.startswith("ERROR") and not line.startswith("WARNING")
    )
