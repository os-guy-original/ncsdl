"""download command."""

import os
import re

from ..cmd._shared import _download_and_report, _print_table, _resolve_search
from ..downloader import (
    fetch_video_info,
    get_existing_songs,
    save_queue,
)
from ..downloader.search import NCS_CHANNEL_ID

_YT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def run(args) -> int:
    output_dir = args.output or os.path.expanduser("~/ncs_downloads")
    embed_thumbnail = not args.no_thumbnail

    # Download specific video by ID
    if args.video_id:
        if not _YT_ID_RE.match(args.video_id):
            print(f"invalid video ID: {args.video_id} (must be 11 characters, alphanumeric/dash/underscore)")
            return 1

        print(f"fetching info for {args.video_id}...")
        video = fetch_video_info(args.video_id)
        if not video:
            print(f"could not find video: {args.video_id}")
            return 1

        print(f"found: {video.title}")

        if video.channel_id and video.channel_id != NCS_CHANNEL_ID:
            print(f"error: video {args.video_id} is not from the NCS YouTube channel (NoCopyrightSounds).")
            print("This tool is designed for downloading songs from the NCS channel only.")
            return 1

        existing = get_existing_songs(output_dir)
        save_queue([video], output_dir)

        return _download_and_report(
            [video], output_dir, existing,
            embed_thumbnail, args.retries,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies_file,
        )

    # Download by genre (existing flow)
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
        _print_table(videos)
        return 0

    save_queue(videos, output_dir)

    return _download_and_report(
        videos, output_dir, existing,
        embed_thumbnail, args.retries,
        cookies_from_browser=args.cookies_from_browser,
        cookies_file=args.cookies_file,
    )
