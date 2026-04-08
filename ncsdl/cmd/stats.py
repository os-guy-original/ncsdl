"""stats command."""

import os
from pathlib import Path


def run(args) -> int:
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

    total_size = sum(f.stat().st_size for f in files)
    ext_counts: dict[str, int] = {}
    genres_detected: dict[str, int] = {}

    for f in files:
        ext_counts[f.suffix.lower()] = ext_counts.get(f.suffix.lower(), 0) + 1
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
    print(f"{'Genres detected':<20} {len(genres_detected):>15}")

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
