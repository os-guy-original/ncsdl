"""File tracking keyed by YouTube video ID.

actual_names.json structure:
{
  "VIDEO_ID": {"expected": "Artist - Song", "actual": "Full YouTube Title | Genre | NCS..."}
}

- expected: the filename we saved the file as (without extension)
- actual: the full YouTube video title
"""

import json
import os

_TRACK_FILENAME = "actual_names.json"


def _track_path(output_dir: str) -> str:
    return os.path.join(output_dir, _TRACK_FILENAME)


def load_track(output_dir: str) -> dict[str, dict]:
    """Load tracking data. Returns {video_id: {expected, actual}}."""
    path = _track_path(output_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError, ValueError):
        pass
    return {}


def save_track(output_dir: str, data: dict[str, dict]) -> None:
    """Save tracking data."""
    path = _track_path(output_dir)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def record_download(output_dir: str, video_id: str, expected: str, actual: str) -> None:
    """Record a download. If video_id already tracked, updates the entry."""
    data = load_track(output_dir)
    data[video_id] = {"expected": expected, "actual": actual}
    save_track(output_dir, data)


def find_by_id(data: dict[str, dict], video_id: str) -> dict | None:
    """Find tracking entry for a video ID."""
    return data.get(video_id)


def remove_entry(output_dir: str, video_id: str) -> None:
    """Remove a tracking entry."""
    data = load_track(output_dir)
    data.pop(video_id, None)
    save_track(output_dir, data)
