"""count command."""

from ..downloader import count_ncs_videos


def run(args) -> int:
    print("counting NCS videos on YouTube...")
    count = count_ncs_videos()

    if count == 0:
        print("failed to retrieve video count.")
        return 1

    print()
    print(f"{'Total NCS videos on YouTube':<30} {count:>8}")
    return 0
