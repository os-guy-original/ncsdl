"""Rename command: fix corrupted filenames in-place."""

import argparse
from ..logger import logger


def run(args: argparse.Namespace) -> int:
    from ..downloader.renamer import rename_songs

    logger.heading("Renaming Session")
    logger.info(f"Directory: {args.directory}")
    logger.dim("-" * 40)

    processed, renamed, skipped, errors = rename_songs(
        args.directory,
        max_workers=args.max_workers,
        validate=args.validate,
    )

    logger.heading("Renaming Summary")
    summary = f"{processed} files checked, {renamed} fixed, {skipped} skipped, {len(errors)} errors"
    if not errors and not skipped:
        logger.success(summary)
    else:
        logger.warning(summary)

    if errors:
        logger.heading("Errors")
        for err in errors[:10]:
            logger.error(err)
        if len(errors) > 10:
            logger.dim(f"... and {len(errors) - 10} more")

    return 0 if not errors else 1


def setup_parser(subparsers):
    parser = subparsers.add_parser(
        "rename",
        help="fix corrupted filenames in a directory in-place",
        description="Reads metadata from audio files and renames them to the correct 'Artist - Song' format."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to scan (default: current directory)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="number of parallel workers (default: 10)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="run slow ffprobe validation on each file"
    )
    return parser
