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
    save_queue,
    load_queue,
    clear_queue,
    filter_downloaded,
)
from .metadata import embed_metadata_batch
from .styles import classify_by_genre, format_genre_stats, NCS_GENRES


def _print_table(videos: list, *, include_index: bool = False) -> None:
    """Print a list of videos in a clean table format."""
    for i, v in enumerate(videos, 1):
        genre = v.parsed.genre if v.parsed else "?"
        prefix = f"  {i:>4}. " if include_index else "  "
        print(f"{prefix}{v.title} [{genre}]")


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze NCS title styles from search results."""
    print("searching NCS YouTube channel...")

    videos = (
        search_ncs_videos(genre=args.genre, max_results=args.limit)
        if args.genre
        else get_all_ncs_videos(max_results=args.limit)
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

    # Show style breakdown
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


def cmd_search(args: argparse.Namespace) -> int:
    """Search for specific NCS songs by pattern."""
    pattern = args.pattern.lower()
    limit = args.limit or 50

    print(f"searching for '{args.pattern}'...")

    # Search by genre if pattern matches a known genre
    genre_match = None
    for genre in NCS_GENRES:
        if genre.lower() == pattern:
            genre_match = genre
            break

    if genre_match:
        videos = search_ncs_videos(genre=genre_match, max_results=limit)
    else:
        # Search broadly and filter client-side
        videos = get_all_ncs_videos(max_results=limit * 3)
        videos = [
            v for v in videos
            if pattern in v.title.lower()
            or (v.parsed and pattern in v.parsed.artist.lower())
            or (v.parsed and pattern in v.parsed.song_title.lower())
        ][:limit]

    if not videos:
        print("no results found.")
        return 1

    print(f"found {len(videos)} result(s)\n")
    _print_table(videos, include_index=True)
    return 0


def cmd_list_genres(args: argparse.Namespace) -> int:
    """List all supported NCS genres."""
    genres = sorted(NCS_GENRES)

    if args.verbose:
        # Show genres with search counts
        print("fetching genre statistics (this may take a moment)...")
        videos = search_ncs_videos(max_results=200)
        counts = classify_by_genre([v.title for v in videos])

        # Build a complete list showing all genres, even those with 0 results
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
        # Simple list
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


def cmd_stats(args: argparse.Namespace) -> int:
    """Show download statistics for a directory."""
    directory = args.directory
    if not os.path.isdir(directory):
        print(f"directory not found: {directory}")
        return 1

    dir_path = Path(directory)
    audio_exts = {".mp3", ".m4a", ".flac", ".opus", ".ogg", ".wav"}

    files = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in audio_exts]

    if not files:
        print(f"no audio files found in {directory}")
        return 0

    # Gather stats
    total_size = sum(f.stat().st_size for f in files)
    ext_counts: dict[str, int] = {}
    genres_detected: dict[str, int] = {}

    for f in files:
        ext_counts[f.suffix.lower()] = ext_counts.get(f.suffix.lower(), 0) + 1
        # Try to read genre from file metadata via mutagen
        genre = _read_genre_from_file(f)
        if genre:
            genres_detected[genre] = genres_detected.get(genre, 0) + 1

    print(f"Directory: {directory}")
    print()
    print(f"{'Metric':<20} {'Value':>15}")
    print("-" * 37)
    print(f"{'Total files':<20} {len(files):>15}")
    print(f"{'Total size':<20} {total_size / 1024 / 1024:>14.1f} MB")
    print(f"{'Avg file size':<20} {total_size / len(files) / 1024:>14.1f} KB")
    print(f"{'Genres detected':<20} {sum(genres_detected.values()):>15}")

    if genres_detected:
        print()
        print("Genre Breakdown")
        print(f"{'Genre':<20} {'Count':>5}")
        print("-" * 27)
        for genre, count in sorted(genres_detected.items(), key=lambda x: x[1], reverse=True):
            print(f"{genre:<20} {count:>5}")

    print()
    print("Format Breakdown")
    print(f"{'Format':<20} {'Count':>5}")
    print("-" * 27)
    for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{ext:<20} {count:>5}")

    return 0


def _read_genre_from_file(filepath: Path) -> str:
    """Read genre tag from an audio file using mutagen."""
    try:
        ext = filepath.suffix.lower()
        if ext == ".mp3":
            from mutagen.mp3 import MP3
            audio = MP3(str(filepath))
            if audio.tags and "TCON" in audio.tags:
                return str(audio.tags["TCON"])
        elif ext == ".m4a":
            from mutagen.mp4 import MP4
            audio = MP4(str(filepath))
            if audio.tags and "\xa9gen" in audio.tags:
                return str(audio.tags["\xa9gen"][0])
        elif ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(str(filepath))
            if "genre" in audio:
                return audio["genre"][0]
        elif ext in (".opus", ".ogg"):
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(str(filepath))
            if "genre" in audio:
                return audio["genre"][0]
    except Exception:
        pass
    return ""


def _resolve_search(args: argparse.Namespace) -> tuple[list, str]:
    """Resolve which search function to use and return (videos, search_label)."""
    if not args.genre:
        return search_ncs_videos(max_results=args.limit), "NCS YouTube channel"

    genre = args.genre.lower()
    if genre == "all":
        return get_all_ncs_videos(max_results=args.limit), "all NCS videos"

    return search_ncs_videos(genre=args.genre, max_results=args.limit), f"NCS {args.genre} tracks"


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
    print(f"searching {_resolve_search(args)[1]}...")
    videos, _ = _resolve_search(args)

    if not videos:
        print("no videos found.")
        return 1

    print(f"found {len(videos)} video(s)")

    if args.list_only:
        print()
        _print_table(videos, include_index=True)
        return 0

    # Save queue for potential resume
    save_queue(videos, output_dir)

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
        max_retries=args.retries,
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


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume an interrupted download."""
    output_dir = args.output or os.path.expanduser("~/ncs_downloads")
    audio_format = args.format or "m4a"
    embed_thumbnail = not args.no_thumbnail

    if audio_format not in SUPPORTED_FORMATS:
        print(f"unsupported format: {audio_format}", file=sys.stderr)
        return 1

    # Load saved queue
    queue = load_queue(output_dir)
    if not queue:
        print(f"no saved queue found in {output_dir}")
        print("run 'ncsdl download' first to create a queue.")
        return 1

    print(f"loaded {len(queue)} video(s) from queue")

    # Check existing
    existing = get_existing_songs(output_dir)
    remaining = filter_downloaded(queue, existing)

    if not remaining:
        print("all videos already downloaded.")
        clear_queue(output_dir)
        return 0

    print(f"{len(remaining)} video(s) remaining to download")

    # Download
    print()
    print(f"format: {audio_format}  |  thumbnails: {'yes' if embed_thumbnail else 'no'}")
    print(f"output: {output_dir}")
    print("-" * 40)

    success, skipped, fail, errors = download_videos(
        remaining,
        output_dir,
        existing,
        audio_format=audio_format,
        embed_thumbnail=embed_thumbnail,
        max_retries=args.retries,
    )

    # Clear queue on success
    if fail == 0:
        clear_queue(output_dir)

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

    # search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search for specific NCS songs",
    )
    search_parser.add_argument(
        "pattern",
        help="Search pattern (artist name, song title, or genre)",
    )
    search_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=50,
        help="Max results (default: 50)",
    )

    # list-genres command
    genres_parser = subparsers.add_parser(
        "list-genres",
        aliases=["genres", "lg"],
        help="List all supported NCS genres",
    )
    genres_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show genre counts from search",
    )
    genres_parser.add_argument(
        "--show-empty",
        action="store_true",
        help="Show genres with zero results (requires -v)",
    )

    # stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show download statistics for a directory",
    )
    stats_parser.add_argument(
        "directory",
        help="Directory to analyze",
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
    dl_parser.add_argument(
        "--retries", "-r",
        type=int,
        default=2,
        help="Retry attempts per failed download (default: 2)",
    )

    # resume command
    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume an interrupted download",
    )
    resume_parser.add_argument(
        "--output", "-o",
        help="Output directory (default: ~/ncs_downloads)",
    )
    resume_parser.add_argument(
        "--format", "-f",
        choices=list(SUPPORTED_FORMATS.keys()),
        default="m4a",
        help="Audio format (default: m4a)",
    )
    resume_parser.add_argument(
        "--no-thumbnail",
        action="store_true",
        help="Do not embed album thumbnail",
    )
    resume_parser.add_argument(
        "--retries", "-r",
        type=int,
        default=2,
        help="Retry attempts per failed download (default: 2)",
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
        "search": cmd_search,
        "list-genres": cmd_list_genres,
        "genres": cmd_list_genres,
        "lg": cmd_list_genres,
        "stats": cmd_stats,
        "resume": cmd_resume,
        "metadata": cmd_metadata,
        "meta": cmd_metadata,
        "check-dupes": cmd_check_dupes,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 0
