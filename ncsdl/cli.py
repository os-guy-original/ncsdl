"""CLI interface for ncsdl."""

import argparse
import os
import sys
from pathlib import Path

from .downloader import (
    check_dependencies,
    download_videos,
    get_all_ncs_videos,
    get_existing_songs,
    search_ncs_videos,
    SUPPORTED_FORMATS,
)
from .metadata import embed_metadata_batch
from .styles import classify_by_genre, format_genre_stats


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze NCS title styles from search results."""
    print("searching NCS YouTube channel...")

    if args.genre:
        videos = search_ncs_videos(genre=args.genre, max_results=args.limit)
    else:
        videos = get_all_ncs_videos(max_results=args.limit)

    if not videos:
        print("no videos found.")
        return 1

    titles = [v.title for v in videos]
    genre_counts = classify_by_genre(titles)

    print()
    print("Genre Statistics")
    print("=" * 40)
    print(format_genre_stats(genre_counts))

    # Show style breakdown
    styles = {"modern": 0, "old": 0, "bare": 0, "unknown": 0}
    for v in videos:
        if v.parsed:
            styles[v.parsed.style] = styles.get(v.parsed.style, 0) + 1
        else:
            styles["unknown"] += 1

    print()
    print("Title Style Breakdown")
    print("=" * 40)
    print(f"{'Style':<20} {'Count':>5}")
    print("-" * 27)
    for style, count in sorted(styles.items()):
        if count > 0:
            print(f"{style:<20} {count:>5}")

    print()
    print(f"Total videos analyzed: {len(videos)}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    """Download NCS songs."""
    output_dir = args.output or os.path.expanduser("~/ncs_downloads")
    audio_format = args.format or "m4a"
    embed_thumbnail = not args.no_thumbnail

    if audio_format not in SUPPORTED_FORMATS:
        print(f"unsupported format: {audio_format}", file=sys.stderr)
        print(f"supported: {', '.join(SUPPORTED_FORMATS)}", file=sys.stderr)
        return 1

    # Check for existing songs
    existing = set()
    if not args.no_check_dupes:
        existing = get_existing_songs(output_dir)
        if existing:
            print(f"found {len(existing)} existing song(s) in {output_dir}")

    # Search for videos
    if args.genre:
        if args.genre.lower() == "all":
            print("searching for all NCS videos...")
            videos = get_all_ncs_videos(max_results=args.limit)
        else:
            print(f"searching NCS {args.genre} tracks...")
            videos = search_ncs_videos(genre=args.genre, max_results=args.limit)
    else:
        print("searching NCS YouTube channel...")
        videos = search_ncs_videos(max_results=args.limit)

    if not videos:
        print("no videos found.")
        return 1

    print(f"found {len(videos)} video(s)")

    if args.list_only:
        print()
        for i, v in enumerate(videos, 1):
            genre = v.parsed.genre if v.parsed else "?"
            print(f"  {i:>4}. {v.title} [{genre}]")
        return 0

    # Download
    print()
    print(f"format: {audio_format}  |  thumbnails: {'yes' if embed_thumbnail else 'no'}")
    print(f"output: {output_dir}")
    print("-" * 40)

    success, skipped, fail, errors = download_videos(
        videos,
        output_dir,
        existing,
        audio_format=audio_format,
        embed_thumbnail=embed_thumbnail,
    )

    print()
    print(f"done: {success} downloaded, {skipped} skipped, {fail} failed")

    if errors:
        print()
        print("errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    return 0 if fail == 0 else 1


def cmd_metadata(args: argparse.Namespace) -> int:
    """Embed metadata into existing audio files."""
    if not args.files:
        print("no files specified.")
        return 1

    success, fail, errors = embed_metadata_batch(args.files)

    print(f"metadata complete: {success} succeeded, {fail} failed")

    if errors:
        print()
        print("errors:")
        for err in errors:
            print(f"  - {err}")

    return 0 if fail == 0 else 1


def cmd_check_dupes(args: argparse.Namespace) -> int:
    """Check for duplicate songs in a directory."""
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


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ncsdl",
        description="NCS YouTube Downloader - Download NoCopyrightSounds music",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze NCS title styles and genre distribution",
    )
    analyze_parser.add_argument(
        "--genre", "-g",
        help="Filter by genre (e.g. Trap, House, Dubstep)",
    )
    analyze_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=200,
        help="Max videos to analyze (default: 200)",
    )

    # download command
    dl_parser = subparsers.add_parser(
        "download",
        aliases=["dl"],
        help="Download NCS songs",
    )
    dl_parser.add_argument(
        "--genre", "-g",
        help="Genre to download, or 'all' for entire library",
    )
    dl_parser.add_argument(
        "--output", "-o",
        help="Output directory (default: ~/ncs_downloads)",
    )
    dl_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=100,
        help="Max videos to download (default: 100)",
    )
    dl_parser.add_argument(
        "--format", "-f",
        choices=list(SUPPORTED_FORMATS.keys()),
        default="m4a",
        help="Audio format (default: m4a)",
    )
    dl_parser.add_argument(
        "--no-thumbnail",
        action="store_true",
        help="Do not embed album thumbnail",
    )
    dl_parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list found videos without downloading",
    )
    dl_parser.add_argument(
        "--no-check-dupes",
        action="store_true",
        help="Skip duplicate checking",
    )

    # metadata command
    meta_parser = subparsers.add_parser(
        "metadata",
        aliases=["meta"],
        help="Embed metadata into audio files",
    )
    meta_parser.add_argument(
        "files",
        nargs="+",
        help="Audio files to embed metadata into",
    )

    # check-dupes command
    dupe_parser = subparsers.add_parser(
        "check-dupes",
        help="Check for duplicate songs in a directory",
    )
    dupe_parser.add_argument(
        "directory",
        help="Directory to check",
    )
    dupe_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="List all found songs",
    )

    return parser


def main() -> int:
    """Main entry point."""
    missing = check_dependencies()
    if missing:
        print("missing dependencies:", ", ".join(missing), file=sys.stderr)
        print("install:", file=sys.stderr)
        if "yt-dlp" in missing:
            print("  pip install yt-dlp", file=sys.stderr)
        if "ffprobe" in missing:
            print("  sudo apt install ffmpeg  (or equivalent)", file=sys.stderr)
        return 1

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "analyze": cmd_analyze,
        "download": cmd_download,
        "dl": cmd_download,
        "metadata": cmd_metadata,
        "meta": cmd_metadata,
        "check-dupes": cmd_check_dupes,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 0
