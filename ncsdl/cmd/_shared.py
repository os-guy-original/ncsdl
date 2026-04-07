"""Shared CLI helpers."""

import os
import sys

from ..downloader import (
    SUPPORTED_FORMATS,
    download_videos,
    get_all_ncs_videos,
    get_existing_songs,
    search_ncs_videos,
)

# Session state for format fallback decisions
# "ask"     - prompt user each time
# "always"  - always accept alternative, no more prompts
# "stop"    - stop downloading, skip remaining videos
_fallback_mode: str = "ask"


def _ask_fallback(audio_format: str) -> str:
    """Ask user what to do when the requested format is unavailable.

    Returns "always", "now", or "stop".
    """
    global _fallback_mode

    print()
    print(f"format '{audio_format}' not available for this video.")
    print("  [a] always  - accept alternative format for all remaining videos")
    print("  [n] now     - accept alternative format for this video only")
    print("  [s] stop    - stop downloading")
    print()

    while True:
        try:
            choice = input("choice [a/n/s]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "stop"

        if choice in ("a", "always"):
            _fallback_mode = "always"
            return "always"
        if choice in ("n", "now"):
            return "now"
        if choice in ("s", "stop"):
            _fallback_mode = "stop"
            return "stop"


def get_fallback_mode() -> str:
    """Get current fallback mode."""
    global _fallback_mode
    return _fallback_mode


def reset_fallback() -> None:
    """Reset fallback mode for a new session."""
    global _fallback_mode
    _fallback_mode = "ask"


def _resolve_search(genre: str | None, limit: int, include_mixes: bool = False) -> tuple[list, str]:
    """Resolve which search function to use and return (videos, label)."""
    if not genre:
        return search_ncs_videos(max_results=limit, include_mixes=include_mixes), "NCS YouTube channel"

    g = genre.lower()
    if g == "all":
        return get_all_ncs_videos(max_results=limit, include_mixes=include_mixes), "all NCS videos"

    return search_ncs_videos(genre=genre, max_results=limit, include_mixes=include_mixes), f"NCS {genre} tracks"


def _print_table(videos: list, *, index: bool = False) -> None:
    """Print videos in a clean table."""
    for i, v in enumerate(videos, 1):
        genre = v.parsed.genre if v.parsed else "?"
        prefix = f"  {i:>4}. " if index else "  "
        print(f"{prefix}{v.title} [{genre}]")


def _download_and_report(
    videos,
    output_dir: str,
    existing: set[str],
    audio_format: str,
    embed_thumbnail: bool,
    max_retries: int,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    download_unwanted_formats: bool = False,
) -> int:
    """Run download and print summary. Returns exit code."""
    print()
    print(f"format: {audio_format}  |  thumbnails: {'yes' if embed_thumbnail else 'no'}")
    print(f"output: {output_dir}")
    if cookies_from_browser:
        print(f"cookies: from {cookies_from_browser} browser")
    if cookies_file:
        print(f"cookies: from {cookies_file}")
    if download_unwanted_formats:
        print("unwanted formats: auto-accept alternative")
    print("-" * 40)

    # Reset session state
    reset_fallback()
    if download_unwanted_formats:
        set_fallback_mode("always")

    # Fallback handler: returns ("always"|"now"|"stop")
    fallback_handler = None
    if not download_unwanted_formats:
        def fallback_handler() -> str:
            return _ask_fallback(audio_format)

    downloaded, renamed, redownloaded, skipped, fail, errors = download_videos(
        videos,
        output_dir,
        existing,
        audio_format=audio_format,
        embed_thumbnail=embed_thumbnail,
        max_retries=max_retries,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
        fallback_handler=fallback_handler,
    )

    print()
    print(f"done: {downloaded} downloaded, {renamed} renamed, {redownloaded} re-downloaded, {skipped} skipped, {fail} failed")

    if errors:
        print()
        print("errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    return 0 if fail == 0 else 1
