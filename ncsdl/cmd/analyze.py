"""analyze command."""

from ..downloader import get_all_ncs_videos, search_ncs_videos
from ..styles import classify_by_genre, format_genre_stats
from ..logger import logger


def run(args) -> int:
    logger.info("Searching NCS YouTube channel...")

    videos = (
        search_ncs_videos(genre=args.genre, max_results=args.limit, include_mixes=args.include_mixes)
        if args.genre
        else get_all_ncs_videos(max_results=args.limit, include_mixes=args.include_mixes)
    )

    if not videos:
        logger.warning("No videos found.")
        return 1

    titles = [v.title for v in videos]
    genre_counts = classify_by_genre(titles)

    logger.heading("Genre Statistics")
    logger.info(format_genre_stats(genre_counts))

    styles: dict[str, int] = {}
    for v in videos:
        key = v.parsed.style if v.parsed else "unknown"
        styles[key] = styles.get(key, 0) + 1

    logger.heading("Title Style Breakdown")
    logger.info(f"{'Style':<25} {'Count':>14}")
    logger.dim("-" * 40)
    for style, count in sorted(styles.items()):
        logger.info(f"{style:<25} {count:>14}")

    logger.heading("Summary")
    logger.success(f"Total videos analyzed: {len(videos)}")
    return 0
