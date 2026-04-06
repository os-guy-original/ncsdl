"""detect-genres command."""

from ..styles import detect_genres, get_genres


def run(args) -> int:
    if getattr(args, 'refresh', False):
        import os
        cache = os.path.join(os.path.dirname(os.path.dirname(__file__)), "genres.json")
        if os.path.exists(cache):
            os.remove(cache)
        print("detecting genres from NCS YouTube channel (this may take a moment)...")
    else:
        print("loading cached genres...")

    genres = get_genres()
    if not genres:
        genres = detect_genres()

    if not genres:
        print("failed to detect genres.")
        return 1

    cols = 3
    col_width = 25
    for i, genre in enumerate(sorted(genres, key=str.lower), 1):
        print(f"{genre:<{col_width}}", end="")
        if i % cols == 0:
            print()
    if len(genres) % cols:
        print()

    print(f"\ntotal genres: {len(genres)}")
    return 0
