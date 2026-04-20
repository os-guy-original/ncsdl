"""check-dupes command."""

import os

from ..downloader import get_existing_songs


def run(args) -> int:
    from ..logger import logger
    directory = args.directory
    
    if not os.path.isdir(directory):
        logger.error(f"Directory not found: {directory}")
        return 1

    existing = get_existing_songs(directory)

    if not existing:
        logger.warning(f"No audio files found in {directory}")
        return 0

    songs = sorted(existing)
    logger.info(f"Found {len(songs)} unique song(s) in {directory}")

    if args.verbose:
        logger.heading("Song List")
        for name in songs:
            logger.info(f"  {name}")

    return 0
