"""stats command."""

import os
from pathlib import Path


def run(args) -> int:
    from ..logger import logger
    directory = args.directory
    
    if not os.path.isdir(directory):
        logger.error(f"Directory not found: {directory}")
        return 1

    dir_path = Path(directory).expanduser().resolve()
    from ..downloader.files import _AUDIO_EXTENSIONS
    
    files = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS]

    if not files:
        logger.warning(f"No audio files found in {directory}")
        return 0

    total_size = sum(f.stat().st_size for f in files)
    ext_counts: dict[str, int] = {}
    genres_detected: dict[str, int] = {}

    for f in files:
        ext_counts[f.suffix.lower()] = ext_counts.get(f.suffix.lower(), 0) + 1
        genre = _read_genre_from_file(f)
        if genre:
            genres_detected[genre] = genres_detected.get(genre, 0) + 1

    logger.heading("Library Statistics")
    logger.info(f"Directory: {dir_path}")
    
    logger.info("-" * 40)
    logger.info(f"{'Total files':<25} {len(files):>14}")
    logger.info(f"{'Total size':<25} {total_size / 1024 / 1024:>13.1f} MB")
    logger.info(f"{'Avg file size':<25} {total_size / len(files) / 1024:>13.1f} KB")
    logger.info(f"{'Genres detected':<25} {len(genres_detected):>14}")

    if genres_detected:
        logger.heading("Genre Breakdown")
        logger.info(f"{'Genre':<25} {'Count':>14}")
        logger.dim("-" * 40)
        for genre, count in sorted(genres_detected.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"{genre:<25} {count:>14}")

    logger.heading("Format Breakdown")
    logger.info(f"{'Format':<25} {'Count':>14}")
    logger.dim("-" * 40)
    for ext, count in sorted(ext_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"{ext:<25} {count:>14}")

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
