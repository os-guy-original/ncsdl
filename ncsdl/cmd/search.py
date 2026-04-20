"""search command."""

from ..downloader import get_all_ncs_videos, search_ncs_videos
from ..cmd._shared import _print_table
from ..styles import get_genres
from ..logger import logger


def run(args) -> int:
    pattern = args.pattern.lower()
    limit = args.limit

    logger.info(f"Searching for '{args.pattern}'...")

    genres = get_genres()
    genre_match = None
    for genre in genres:
        if genre.lower() == pattern:
            genre_match = genre
            break

    if genre_match:
        videos = search_ncs_videos(genre=genre_match, max_results=limit, include_mixes=args.include_mixes)
    else:
        search_count = limit * 3 if limit > 0 else 5000
        videos = get_all_ncs_videos(max_results=search_count, include_mixes=args.include_mixes)
        videos = [
            v for v in videos
            if pattern in v.title.lower()
            or (v.parsed and pattern in v.parsed.artist.lower())
            or (v.parsed and pattern in v.parsed.song_title.lower())
        ][:limit]

    if not videos:
        logger.warning("No results found.")
        return 1

    logger.info(f"Found {len(videos)} result(s)")
    logger.heading("Search Results")
    _print_table(videos)
    return 0
