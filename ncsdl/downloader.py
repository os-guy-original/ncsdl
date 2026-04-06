"""YouTube search and download functionality for NCS songs."""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .styles import ParsedTitle, parse_title


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

    for pattern in _COMPILATION_PATTERNS:
        if pattern in title_lower:
            return True

    # Compilations are usually longer than 10 minutes
    if ":" in duration:
        parts = duration.split(":")
        try:
            if len(parts) == 3:
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
        url_start = line.find("|https://")
        if url_start == -1:
            continue

        # Split into: id|title|url|duration
        before_url = line[:url_start]
        after_url = line[url_start + 1:]

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
    """Get all NCS videos by searching without genre filter."""
    return search_ncs_videos(max_results=max_results)


def download_video(
    video: VideoInfo,
    output_dir: str,
    existing_files: set[str],
    audio_format: str = "m4a",
    embed_thumbnail: bool = True,
) -> tuple[str, str]:
    """Download a single video as an audio file.

    Args:
        video: VideoInfo to download.
        output_dir: Directory to save the file.
        existing_files: Set of existing filenames for duplicate check.
        audio_format: Output audio format (m4a, flac, opus, mp3).
        embed_thumbnail: Whether to embed album art.

    Returns:
        Tuple of (status, message) where status is 'ok', 'skip', or 'fail'.
    """
    os.makedirs(output_dir, exist_ok=True)

    fmt = SUPPORTED_FORMATS.get(audio_format, SUPPORTED_FORMATS["m4a"])
    ext = fmt["ext"]

    # Determine output filename
    if video.parsed:
        safe_name = _sanitize_filename(
            f"{video.parsed.artist} - {video.parsed.song_title}"
        )
    else:
        safe_name = _sanitize_filename(video.title)

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

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return "fail", f"timeout: {safe_name}"

    if result.returncode == 0 and os.path.exists(output_path):
        # Embed clean metadata via mutagen
        if video.parsed:
            _embed_metadata_post(output_path, video.parsed)
        return "ok", f"ok: {safe_name}.{ext}"

    error = result.stderr.strip() if result.stderr else "unknown error"
    return "fail", f"fail: {safe_name} ({error})"


def _embed_metadata_post(filepath: str, parsed: ParsedTitle) -> None:
    """Embed clean metadata into a downloaded file using mutagen."""
    try:
        ext = Path(filepath).suffix.lower()
        title = parsed.song_title
        if parsed.suffix:
            title = f"{title} {parsed.suffix}"

        artist = parsed.artist
        if parsed.featuring:
            artist = f"{artist} feat. {parsed.featuring}"

        genre = parsed.genre or "Electronic"
        album = "NCS - NoCopyrightSounds"

        if ext == ".mp3":
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, ID3NoHeaderError
            try:
                audio = MP3(filepath, ID3=ID3)
            except ID3NoHeaderError:
                audio = MP3(filepath)
                audio.add_tags()
            audio["TIT2"] = ID3(encoding=3, text=[title])
            audio["TPE1"] = ID3(encoding=3, text=[artist])
            audio["TALB"] = ID3(encoding=3, text=[album])
            audio["TCON"] = ID3(encoding=3, text=[genre])
            audio.save()
        elif ext == ".m4a":
            from mutagen.mp4 import MP4
            audio = MP4(filepath)
            audio.tags = audio.tags or {}
            audio["\xa9nam"] = title
            audio["\xa9ART"] = artist
            audio["\xa9alb"] = album
            audio["\xa9gen"] = genre
            audio.save()
        elif ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(filepath)
            audio["title"] = title
            audio["artist"] = artist
            audio["album"] = album
            audio["genre"] = genre
            audio.save()
        elif ext == ".opus":
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(filepath)
            audio["title"] = title
            audio["artist"] = artist
            audio["album"] = album
            audio["genre"] = genre
            audio.save()
        elif ext == ".ogg":
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(filepath)
            audio["title"] = title
            audio["artist"] = artist
            audio["album"] = album
            audio["genre"] = genre
            audio.save()
    except Exception:
        pass  # Metadata embedding is non-critical


def download_videos(
    videos: list[VideoInfo],
    output_dir: str,
    existing_files: set[str],
    audio_format: str = "m4a",
    embed_thumbnail: bool = True,
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
        status, msg = download_video(
            video, output_dir, existing_files,
            audio_format=audio_format,
            embed_thumbnail=embed_thumbnail,
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
    existing = set()
    dir_path = Path(directory)

    if not dir_path.exists():
        return existing

    for f in dir_path.iterdir():
        if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS:
            existing.add(f.stem)

    return existing
