"""check-dupes command."""

import os

from ..downloader import get_existing_songs


def run(args) -> int:
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"directory not found: {directory}")
        return 1

    existing = get_existing_songs(directory)

    if not existing:
        print(f"no audio files found in {directory}")
        return 0

    songs = sorted(existing)
    print(f"found {len(songs)} unique song(s) in {directory}")

    if args.verbose:
        print()
        for name in songs:
            print(f"  {name}")

    return 0
