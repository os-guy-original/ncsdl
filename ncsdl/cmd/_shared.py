"""Shared CLI helpers."""

import os

from ..downloader import (
    SUPPORTED_FORMATS,
    download_videos,
    get_all_ncs_videos,
    get_existing_songs,
    search_ncs_videos,
)


def _resolve_search(genre: str | None, limit: int) -> tuple[list, str]:
    """Resolve which search function to use and return (videos, label)."""
    if not genre:
        return search_ncs_videos(max_results=limit), "NCS YouTube channel"

    g = genre.lower()
    if g == "all":
        return get_all_ncs_videos(max_results=limit), "all NCS videos"

    return search_ncs_videos(genre=genre, max_results=limit), f"NCS {genre} tracks"


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
) -> int:
    """Run download and print summary. Returns exit code."""
    print()
    print(f"format: {audio_format}  |  thumbnails: {'yes' if embed_thumbnail else 'no'}")
    print(f"output: {output_dir}")
    print("-" * 40)

    downloaded, renamed, redownloaded, skipped, fail, errors = download_videos(
        videos,
        output_dir,
        existing,
        audio_format=audio_format,
        embed_thumbnail=embed_thumbnail,
        max_retries=max_retries,
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
