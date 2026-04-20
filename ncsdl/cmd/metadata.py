"""metadata command."""

from ..metadata import embed_metadata_batch
from ..logger import logger


def run(args) -> int:
    if not args.files:
        logger.error("No files specified.")
        return 1

    logger.info(f"Embedding metadata into {len(args.files)} file(s)...")
    success, fail, errors = embed_metadata_batch(args.files)

    logger.heading("Metadata Summary")
    summary = f"{success} succeeded, {fail} failed"
    if fail == 0:
        logger.success(summary)
    else:
        logger.warning(summary)

    if errors:
        logger.heading("Errors")
        for err in errors[:10]:
            logger.error(err)
        if len(errors) > 10:
            logger.dim(f"... and {len(errors) - 10} more")

    return 0 if fail == 0 else 1
