"""Renamer logic: fixing corrupted filenames in-place."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..logger import logger
from .files import (
    _AUDIO_EXTENSIONS,
    get_ncsdl_id,
    is_audio_valid,
    sanitize_filename,
)
from .migration import _load_title_cache


def rename_songs(
    directory: str,
    max_workers: int = 10,
    validate: bool = False,
) -> tuple[int, int, int, list[str]]:
    """Scan directory and rename songs with corrupted names in-place.

    Args:
        directory: Directory to scan.
        max_workers: Number of parallel threads.
        validate: Whether to run slow ffprobe validation on each file.

    Returns:
        Tuple of (processed, renamed, skipped, errors).
    """
    from ..styles import parse_title
    from .search import fetch_video_info

    path = Path(directory).expanduser().resolve()
    if not path.is_dir():
        return 0, 0, 0, [f"directory not found: {directory}"]

    files = [
        f for f in path.iterdir()
        if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS
    ]
    
    total_files = len(files)
    if total_files == 0:
        return 0, 0, 0, []

    logger.info(f"Scanning {total_files} file(s) in {path}")
    title_cache = _load_title_cache()

    results = {"processed": 0, "renamed": 0, "skipped": 0, "errors": []}

    def process_file(file_path: Path, idx: int):
        filename = file_path.name
        stem = file_path.stem
        ext = file_path.suffix.lower()

        # 1. Identity detection
        video_id = get_ncsdl_id(str(file_path))
        
        # 2. Lazy Validation
        if validate and not is_audio_valid(str(file_path)):
            return "error", f"fail: {filename} (corrupted file)"

        correct_name = stem
        if video_id:
            cached_title = title_cache.get(video_id)
            if cached_title:
                info_parsed = parse_title(cached_title)
                if info_parsed: correct_name = sanitize_filename(f"{info_parsed.artist} - {info_parsed.song_title}")
            else:
                info = fetch_video_info(video_id)
                if info and info.parsed: correct_name = sanitize_filename(f"{info.parsed.artist} - {info.parsed.song_title}")
        else:
            parsed = parse_title(stem)
            if parsed: correct_name = sanitize_filename(f"{parsed.artist} - {parsed.song_title}")

        # 3. Rename if needed
        if stem != correct_name:
            target_path = file_path.parent / f"{correct_name}{ext}"
            
            if target_path.exists():
                try:
                    if target_path.samefile(file_path):
                        temp_name = file_path.parent / f"{correct_name}.tmp_{os.getpid()}{ext}"
                        file_path.rename(temp_name)
                        temp_name.rename(target_path)
                        logger.progress(idx, total_files, "fixed (case)", f"'{filename}' -> '{correct_name}{ext}'")
                        return "renamed", None
                except Exception: pass
                
                logger.progress(idx, total_files, "skip", f"'{filename}' -> '{correct_name}{ext}' (collision)")
                return "skip", f"skip: '{filename}' -> '{correct_name}' (target already exists)"
            
            try:
                file_path.rename(target_path)
                logger.progress(idx, total_files, "fixed", f"'{filename}' -> '{correct_name}{ext}'")
                return "renamed", None
            except Exception as e:
                return "error", f"fail: {filename} (rename error: {e})"
        else:
            logger.progress(idx, total_files, "ok", filename)
            return "ok", None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_file, f, i) for i, f in enumerate(files, 1)]
        for future in futures:
            status, data = future.result()
            results["processed"] += 1
            if status == "renamed": results["renamed"] += 1
            elif status == "skip": results["skipped"] += 1
            elif status == "error": results["errors"].append(data)

    return results["processed"], results["renamed"], results["skipped"], results["errors"]
