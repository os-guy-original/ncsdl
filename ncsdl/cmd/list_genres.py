"""list-genres command."""

from ..cmd._shared import _resolve_search
from ..downloader import search_ncs_videos
from ..styles import classify_by_genre, get_genres


def run(args) -> int:
    genres = sorted(get_genres(), key=str.lower)
    if not genres:
        print("no genres detected. run 'ncsdl detect-genres' first.")
        return 1

    if args.verbose:
        print("fetching genre statistics (this may take a moment)...")
        videos = search_ncs_videos(max_results=200)
        counts = classify_by_genre([v.title for v in videos])

        print()
        print(f"{'Genre':<25} {'Count':>5}")
        print("-" * 32)
        for genre in genres:
            count = counts.get(genre, 0)
            if count > 0 or args.show_empty:
                print(f"{genre:<25} {count:>5}")
        print("-" * 32)
        print(f"{'Total':<25} {sum(counts.values()):>5}")
        print()
        print(f"genres with results: {sum(1 for c in counts.values() if c > 0)}")
    else:
        cols = 3
        col_width = 25
        for i, genre in enumerate(genres, 1):
            print(f"{genre:<{col_width}}", end="")
            if i % cols == 0:
                print()
        if len(genres) % cols:
            print()

    print(f"\ntotal genres: {len(genres)}")
    return 0
