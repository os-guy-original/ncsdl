"""Shared CLI helpers."""

import os
import sys

from ..downloader import (
    download_videos,
    get_all_ncs_videos,
    search_ncs_videos,
)


def _resolve_search(genre: str | None, limit: int, include_mixes: bool = False) -> tuple[list, str]:
    """Resolve which search function to use and return (videos, label)."""
    if not genre:
        return search_ncs_videos(max_results=limit, include_mixes=include_mixes), "NCS YouTube channel"

    g = genre.lower()
    if g == "all":
        return get_all_ncs_videos(max_results=limit, include_mixes=include_mixes), "all NCS videos"

    return search_ncs_videos(genre=genre, max_results=limit, include_mixes=include_mixes), f"NCS {genre} tracks"


def _print_table(videos: list) -> None:
    """Print videos in a clean table with video IDs."""
    for v in videos:
        genre = v.parsed.genre if v.parsed else "?"
        print(f"  {v.video_id}  {v.title} [{genre}]")


def _download_and_report(
    videos,
    output_dir: str,
    existing: set[str],
    embed_thumbnail: bool,
    max_retries: int,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> int:
    """Run download and print summary. Returns exit code."""
    from ..logger import logger, CLR_BOLD, CLR_RESET

    logger.heading("Download Session")
    logger.info(f"Format: {CLR_BOLD}m4a{CLR_RESET}  |  Thumbnails: {CLR_BOLD}{'yes' if embed_thumbnail else 'no'}{CLR_RESET}")
    logger.info(f"Output: {CLR_BOLD}{output_dir}{CLR_RESET}")
    if cookies_from_browser:
        logger.info(f"Cookies: from {cookies_from_browser} browser")
    if cookies_file:
        logger.info(f"Cookies: from {cookies_file}")
    logger.dim("-" * 40)

    downloaded, renamed, redownloaded, skipped, fail, errors = download_videos(
        videos,
        output_dir,
        existing,
        embed_thumbnail=embed_thumbnail,
        max_retries=max_retries,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
    )

    logger.heading("Session Summary")
    summary = f"{downloaded} downloaded, {renamed} renamed, {redownloaded} re-downloaded, {skipped} skipped, {fail} failed"
    if fail == 0:
        logger.success(summary)
    else:
        logger.warning(summary)

    if errors:
        logger.heading("Errors")
        for err in errors[:10]:
            logger.error(err)
        if len(errors) > 10:
            logger.dim(f"  ... and {len(errors) - 10} more")

    return 0 if fail == 0 else 1
