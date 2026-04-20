"""download command."""

import os
import re

from ..cmd._shared import _download_and_report, _print_table, _resolve_search
from ..downloader import (
    fetch_video_info,
    get_existing_songs,
    save_queue,
)
from ..downloader.search import NCS_CHANNEL_ID
from ..logger import logger

_YT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def run(args) -> int:
    output_dir = args.output or os.path.expanduser("~/ncs_downloads")
    embed_thumbnail = not args.no_thumbnail

    # Download specific video by ID
    if args.video_id:
        if not _YT_ID_RE.match(args.video_id):
            logger.error(f"Invalid video ID: {args.video_id} (must be 11 characters, alphanumeric/dash/underscore)")
            return 1

        logger.info(f"Fetching info for {args.video_id}...")
        video = fetch_video_info(args.video_id)
        if not video:
            logger.error(f"Could not find video: {args.video_id}")
            return 1

        logger.info(f"Found: {video.title}")

        if video.channel_id and video.channel_id != NCS_CHANNEL_ID:
            logger.error(f"Video {args.video_id} is not from the NCS YouTube channel.")
            logger.info("This tool is designed for downloading songs from the NCS channel only.")
            return 1

        existing = get_existing_songs(output_dir)
        save_queue([video], output_dir)

        return _download_and_report(
            [video], output_dir, existing,
            embed_thumbnail, args.retries,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies_file,
        )

    # Download by genre (existing flow)
    existing = set()
    if not args.no_check_dupes:
        existing = get_existing_songs(output_dir)
        if existing:
            logger.info(f"Found {len(existing)} existing song(s) in {output_dir}")

    search_desc = _resolve_search(args.genre, args.limit, args.include_mixes)[1]
    logger.info(f"Searching {search_desc}...")
    videos, _ = _resolve_search(args.genre, args.limit, args.include_mixes)

    if not videos:
        logger.warning("No videos found.")
        return 1

    logger.info(f"Found {len(videos)} video(s)")

    if args.list_only:
        logger.heading("Video List")
        _print_table(videos)
        return 0

    save_queue(videos, output_dir)

    return _download_and_report(
        videos, output_dir, existing,
        embed_thumbnail, args.retries,
        cookies_from_browser=args.cookies_from_browser,
        cookies_file=args.cookies_file,
    )
