"""count command."""

from ..downloader import count_ncs_videos


def run(args) -> int:
    from ..logger import logger
    
    logger.info("Counting NCS videos on YouTube...")
    count = count_ncs_videos()

    if count == 0:
        logger.error("Failed to retrieve video count.")
        return 1

    logger.heading("Statistics")
    logger.success(f"{'Total NCS videos on YouTube':<30} {count:>8}")
    return 0
