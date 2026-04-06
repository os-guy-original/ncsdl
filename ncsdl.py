#!/usr/bin/env python3
"""ncsdl - NCS YouTube Downloader.

Download NoCopyrightSounds music from YouTube with style detection,
duplicate checking, and metadata embedding.

Usage:
    ncsdl analyze [--genre GENRE] [--limit N]
    ncsdl download [--genre GENRE|--all] [--output PATH] [--limit N]
    ncsdl metadata FILE [FILE ...]
    ncsdl check-dupes DIRECTORY
    ncsdl --help
"""

import sys
from pathlib import Path

# Add parent directory to path for development runs
if __name__ == "__main__" and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ncsdl.cli import main

sys.exit(main())
