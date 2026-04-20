"""list-genres command."""

from ..cmd._shared import _resolve_search
from ..downloader import search_ncs_videos
from ..styles import classify_by_genre, get_genres
from ..logger import logger


def run(args) -> int:
    genres = sorted(get_genres(), key=str.lower)
    if not genres:
        logger.error("No genres detected. Run 'ncsdl detect-genres' first.")
        return 1

    if args.verbose:
        logger.info("Fetching genre statistics (this may take a moment)...")
        videos = search_ncs_videos(max_results=200)
        counts = classify_by_genre([v.title for v in videos])

        logger.heading("Genre Statistics")
        logger.info(f"{'Genre':<25} {'Count':>14}")
        logger.dim("-" * 40)
        for genre in genres:
            count = counts.get(genre, 0)
            if count > 0 or args.show_empty:
                logger.info(f"{genre:<25} {count:>14}")
        logger.dim("-" * 40)
        logger.success(f"{'Total':<25} {sum(counts.values()):>14}")
        logger.info(f"Genres with results: {sum(1 for c in counts.values() if c > 0)}")
    else:
        logger.heading("Available Genres")
        cols = 3
        col_width = 25
        current_line = []
        for i, genre in enumerate(genres, 1):
            current_line.append(f"{genre:<{col_width}}")
            if i % cols == 0:
                logger.info("".join(current_line))
                current_line = []
        if current_line:
            logger.info("".join(current_line))

    logger.heading("Summary")
    logger.success(f"Total genres: {len(genres)}")
    return 0
