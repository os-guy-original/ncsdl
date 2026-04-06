"""Download queue persistence."""

import json
import os
from dataclasses import asdict

from .files import sanitize_filename
from .search import VideoInfo

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
                from ..styles import ParsedTitle
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
            name = sanitize_filename(f"{v.parsed.artist} - {v.parsed.song_title}")
        else:
            name = sanitize_filename(v.title)
        if name not in existing:
            result.append(v)
    return result
