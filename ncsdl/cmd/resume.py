"""resume command."""

import os

from ..cmd._shared import _download_and_report
from ..downloader import (
    SUPPORTED_FORMATS,
    clear_queue,
    filter_downloaded,
    get_existing_songs,
    load_queue,
)


def run(args) -> int:
    output_dir = args.output or os.path.expanduser("~/ncs_downloads")
    audio_format = args.format or "m4a"
    embed_thumbnail = not args.no_thumbnail

    if audio_format not in SUPPORTED_FORMATS:
        print(f"unsupported format: {audio_format}")
        return 1

    queue = load_queue(output_dir)
    if not queue:
        print(f"no saved queue found in {output_dir}")
        print("run 'ncsdl download' first to create a queue.")
        return 1

    print(f"loaded {len(queue)} video(s) from queue")

    existing = get_existing_songs(output_dir)
    remaining = filter_downloaded(queue, existing)

    if not remaining:
        print("all videos already downloaded.")
        clear_queue(output_dir)
        return 0

    print(f"{len(remaining)} video(s) remaining to download")

    result = _download_and_report(
        remaining, output_dir, existing,
        audio_format, embed_thumbnail, args.retries,
    )

    if result == 0:
        clear_queue(output_dir)

    return result
