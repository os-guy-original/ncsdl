"""CLI interface for ncsdl.

Thin dispatcher — all command logic lives in ncsdl.cmd.*
"""

import argparse
import os
import sys

from .cmd import COMMANDS
from .downloader import check_dependencies


def _add_common_limit(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=0,
        help="Max results (default: 0 = entire library)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ncsdl",
        description="NCS YouTube Downloader - Download NoCopyrightSounds music",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    p = subparsers.add_parser(
        "analyze", help="Analyze NCS title styles and genre distribution"
    )
    p.add_argument("--genre", "-g", help="Filter by genre (e.g. Trap, House, Dubstep)")
    _add_common_limit(p)
    p.add_argument(
        "--include-mixes",
        "-m",
        action="store_true",
        help="Include mixes and compilations",
    )

    # search
    p = subparsers.add_parser("search", help="Search for specific NCS songs")
    p.add_argument("pattern", help="Search pattern (artist, title, or genre)")
    _add_common_limit(p)
    p.add_argument(
        "--include-mixes",
        "-m",
        action="store_true",
        help="Include mixes and compilations",
    )

    # count
    subparsers.add_parser("count", help="Count total NCS videos on YouTube")

    # detect-genres
    p = subparsers.add_parser(
        "detect-genres", aliases=["dg"], help="Detect genres from NCS YouTube channel"
    )
    p.add_argument(
        "--refresh", action="store_true", help="Re-scan channel and update cache"
    )

    # list-genres
    p = subparsers.add_parser(
        "list-genres", aliases=["genres", "lg"], help="List all supported NCS genres"
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Show genre counts from search"
    )
    p.add_argument(
        "--show-empty",
        action="store_true",
        help="Show genres with zero results (requires -v)",
    )

    # stats
    p = subparsers.add_parser("stats", help="Show download statistics for a directory")
    p.add_argument("directory", help="Directory to analyze")

    # download
    p = subparsers.add_parser("download", aliases=["dl"], help="Download NCS songs")
    p.add_argument(
        "--genre", "-g", help="Genre to download, or 'all' for entire library"
    )
    p.add_argument("--output", "-o", help="Output directory (default: ~/ncs_downloads)")
    _add_common_limit(p)
    p.add_argument(
        "--no-thumbnail", action="store_true", help="Do not embed album thumbnail"
    )
    p.add_argument(
        "--list-only",
        action="store_true",
        help="Only list found videos without downloading",
    )
    p.add_argument(
        "--no-check-dupes", action="store_true", help="Skip duplicate checking"
    )
    p.add_argument(
        "--retries",
        "-r",
        type=int,
        default=2,
        help="Retry attempts per failed download (default: 2)",
    )
    p.add_argument(
        "--include-mixes",
        "-m",
        action="store_true",
        help="Include mixes and compilations",
    )
    p.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Browser to extract cookies from (e.g. firefox, chrome)",
    )
    p.add_argument(
        "--cookies-file", metavar="FILE", help="Path to a netscape cookies file"
    )
    p.add_argument(
        "video_id", nargs="?", help="YouTube video ID to download (e.g. cj-HnSUqx3w)"
    )

    # resume
    p = subparsers.add_parser("resume", help="Resume an interrupted download")
    p.add_argument("--output", "-o", help="Output directory (default: ~/ncs_downloads)")
    p.add_argument(
        "--no-thumbnail", action="store_true", help="Do not embed album thumbnail"
    )
    p.add_argument(
        "--retries",
        "-r",
        type=int,
        default=2,
        help="Retry attempts per failed download (default: 2)",
    )
    p.add_argument(
        "--include-mixes",
        "-m",
        action="store_true",
        help="Include mixes and compilations",
    )
    p.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Browser to extract cookies from (e.g. firefox, chrome)",
    )
    p.add_argument(
        "--cookies-file", metavar="FILE", help="Path to a netscape cookies file"
    )

    # metadata
    p = subparsers.add_parser(
        "metadata", aliases=["meta"], help="Embed metadata into audio files"
    )
    p.add_argument("files", nargs="+", help="Audio files to embed metadata into")

    # check-dupes
    p = subparsers.add_parser(
        "check-dupes", help="Check for duplicate songs in a directory"
    )
    p.add_argument("directory", help="Directory to check")
    p.add_argument("--verbose", "-v", action="store_true", help="List all found songs")

    # migrate
    p = subparsers.add_parser("migrate", help="Move or copy songs between directories")
    p.add_argument("source", help="Source directory")
    p.add_argument("target", help="Target directory")
    p.add_argument(
        "--mode",
        "-m",
        choices=["move", "copy"],
        default="move",
        help="Transfer mode (default: move)",
    )
    p.add_argument(
        "--format", "-f", default="m4a", help="Target audio format (default: m4a)"
    )
    p.add_argument(
        "--progress", action="store_true", help="Show progress during migration"
    )
    p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all output except final summary",
    )
    p.add_argument(
        "--validate",
        action="store_true",
        help="Run slow ffprobe validation on each file",
    )

    # rename
    from .cmd.rename import setup_parser as setup_rename_parser
    setup_rename_parser(subparsers)

    return parser


def main() -> int:
    from .logger import logger
    
    missing = check_dependencies()
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.info("Please install them:")
        if "yt-dlp" in missing:
            logger.info("  pip install yt-dlp")
        if "ffprobe" in missing or "ffmpeg" in missing:
            logger.info("  sudo apt install ffmpeg  (or equivalent)")
        return 1

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    handler = COMMANDS.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 0
