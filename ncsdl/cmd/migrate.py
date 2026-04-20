"""Migrate command: move or copy songs between directories."""

import argparse


def run(args: argparse.Namespace) -> int:
    from ..downloader.migration import migrate_songs
    from ..logger import logger

    if not args.quiet:
        logger.heading("Migration Session")
        logger.info(f"Source: {args.source}")
        logger.info(f"Target: {args.target}")
        logger.info(f"Mode:   {args.mode}")
        from ..logger import CLR_DIM, CLR_RESET
        logger.dim("-" * 40)

    processed, renamed, skipped, errors = migrate_songs(
        args.source,
        args.target,
        args.format,
        args.mode,
        validate=args.validate,
    )

    logger.heading("Migration Summary")
    summary = f"{processed} transferred, {renamed} renamed, {skipped} skipped, {len(errors)} errors"
    if not errors:
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
