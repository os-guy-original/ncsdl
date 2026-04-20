"""detect-genres command."""

from ..styles import detect_genres, get_genres
from ..logger import logger


def run(args) -> int:
    if getattr(args, 'refresh', False):
        import os
        cache = os.path.join(os.path.dirname(os.path.dirname(__file__)), "genres.json")
        if os.path.exists(cache):
            os.remove(cache)
        logger.info("Detecting genres from NCS YouTube channel (this may take a moment)...")
    else:
        logger.info("Loading cached genres...")

    genres = get_genres()
    if not genres:
        genres = detect_genres()

    if not genres:
        logger.error("Failed to detect genres.")
        return 1

    logger.heading("Detected Genres")
    cols = 3
    col_width = 25
    current_line = []
    for i, genre in enumerate(sorted(genres, key=str.lower), 1):
        current_line.append(f"{genre:<{col_width}}")
        if i % cols == 0:
            logger.info("".join(current_line))
            current_line = []
    if current_line:
        logger.info("".join(current_line))

    logger.heading("Summary")
    logger.success(f"Total genres: {len(genres)}")
    return 0
