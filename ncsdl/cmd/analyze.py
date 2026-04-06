"""analyze command."""

from ..downloader import get_all_ncs_videos, search_ncs_videos
from ..styles import classify_by_genre, format_genre_stats


def run(args) -> int:
    print("searching NCS YouTube channel...")

    videos = (
        search_ncs_videos(genre=args.genre, max_results=args.limit, include_mixes=args.include_mixes)
        if args.genre
        else get_all_ncs_videos(max_results=args.limit, include_mixes=args.include_mixes)
    )

    if not videos:
        print("no videos found.")
        return 1

    titles = [v.title for v in videos]
    genre_counts = classify_by_genre(titles)

    print()
    print("Genre Statistics")
    print("=" * 40)
    print(format_genre_stats(genre_counts))

    styles: dict[str, int] = {}
    for v in videos:
        key = v.parsed.style if v.parsed else "unknown"
        styles[key] = styles.get(key, 0) + 1

    print()
    print("Title Style Breakdown")
    print("=" * 40)
    print(f"{'Style':<20} {'Count':>5}")
    print("-" * 27)
    for style, count in sorted(styles.items()):
        print(f"{style:<20} {count:>5}")

    print()
    print(f"Total videos analyzed: {len(videos)}")
    return 0
