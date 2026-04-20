"""resume command."""

import os

from ..cmd._shared import _download_and_report
from ..downloader import (
    clear_queue,
    filter_downloaded,
    get_existing_songs,
    load_queue,
)
from ..logger import logger


def run(args) -> int:
    output_dir = args.output or os.path.expanduser("~/ncs_downloads")
    embed_thumbnail = not args.no_thumbnail

    queue = load_queue(output_dir)
    if not queue:
        logger.error(f"No saved queue found in {output_dir}")
        logger.info("Run 'ncsdl download' first to create a queue.")
        return 1

    logger.info(f"Loaded {len(queue)} video(s) from queue")

    existing = get_existing_songs(output_dir)
    remaining = filter_downloaded(queue, existing)

    if not remaining:
        logger.success("All videos already downloaded.")
        clear_queue(output_dir)
        return 0

    logger.info(f"{len(remaining)} video(s) remaining to download")

    result = _download_and_report(
        remaining, output_dir, existing,
        embed_thumbnail, args.retries,
        cookies_from_browser=args.cookies_from_browser,
        cookies_file=args.cookies_file,
    )

    if result == 0:
        clear_queue(output_dir)

    return result
