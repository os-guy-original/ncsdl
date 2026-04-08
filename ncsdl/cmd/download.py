"""download command."""

import os

from ..cmd._shared import _download_and_report, _print_table, _resolve_search
from ..downloader import (
    get_existing_songs,
    save_queue,
)


def run(args) -> int:
    output_dir = args.output or os.path.expanduser("~/ncs_downloads")
    embed_thumbnail = not args.no_thumbnail

    existing = set()
    if not args.no_check_dupes:
        existing = get_existing_songs(output_dir)
        if existing:
            print(f"found {len(existing)} existing song(s) in {output_dir}")

    print(f"searching {_resolve_search(args.genre, args.limit, args.include_mixes)[1]}...")
    videos, _ = _resolve_search(args.genre, args.limit, args.include_mixes)

    if not videos:
        print("no videos found.")
        return 1

    print(f"found {len(videos)} video(s)")

    if args.list_only:
        print()
        _print_table(videos, index=True)
        return 0

    save_queue(videos, output_dir)

    return _download_and_report(
        videos, output_dir, existing,
        embed_thumbnail, args.retries,
        cookies_from_browser=args.cookies_from_browser,
        cookies_file=args.cookies_file,
    )
