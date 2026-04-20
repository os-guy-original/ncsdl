"""Migration logic: moving and copying songs with name fixing and KIO support."""

import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..logger import logger
from .files import (
    _AUDIO_EXTENSIONS,
    encode_kio_path,
    get_existing_songs,
    get_ncsdl_id,
    is_audio_valid,
    is_kio_path,
    kio_list,
    sanitize_filename,
)


def _kio_copy(src: str, dst: str) -> bool:
    """Copy file using kioclient."""
    encoded_src = encode_kio_path(src)
    encoded_dst = encode_kio_path(dst)
    result = subprocess.run(
        ["kioclient", "copy", encoded_src, encoded_dst],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode == 0


def _kio_move(src: str, dst: str) -> bool:
    """Move file using kioclient."""
    encoded_src = encode_kio_path(src)
    encoded_dst = encode_kio_path(dst)
    result = subprocess.run(
        ["kioclient", "move", encoded_src, encoded_dst],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode == 0


def _kio_stat(path: str) -> bool:
    """Check if file exists using kioclient."""
    encoded_path = encode_kio_path(path)
    result = subprocess.run(
        ["kioclient", "stat", encoded_path],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


def _kio_download_to_temp(kio_path: str) -> str | None:
    """Download a KIO file to a temp location."""
    fd, local_path = tempfile.mkstemp(suffix=Path(kio_path).suffix)
    os.close(fd)
    os.unlink(local_path)
    if _kio_copy(kio_path, local_path):
        return local_path
    return None


def _load_title_cache() -> dict[str, str]:
    """Load video titles from local ncs_titles.json."""
    root = Path(__file__).resolve().parent.parent.parent
    cache_path = root / "ncs_titles.json"
    if not cache_path.exists():
        return {}
    try:
        data = json.loads(cache_path.read_text())
        return {item["id"]: item["title"] for item in data if "id" in item and "title" in item}
    except Exception:
        return {}


def migrate_songs(
    source_dir: str,
    target_dir: str,
    audio_format: str = "m4a",
    mode: str = "move",
    max_workers: int = 10,
    validate: bool = False,
) -> tuple[int, int, int, list[str]]:
    """Safely move or copy songs from source to target with unified logging."""
    from ..styles import parse_title
    from .search import fetch_video_info

    if mode not in ("move", "copy"):
        return 0, 0, 0, [f"invalid mode: {mode}"]

    src_is_kio = is_kio_path(source_dir)
    dst_is_kio = is_kio_path(target_dir)

    # Get source files
    if src_is_kio:
        logger.info(f"Listing source files: {source_dir}")
        src_files = kio_list(source_dir)
        src_files = [f for f in src_files if Path(f).suffix.lower() in _AUDIO_EXTENSIONS]
    else:
        src_path = Path(source_dir).expanduser().resolve()
        if not src_path.is_dir():
            return 0, 0, 0, [f"source not found: {source_dir}"]
        src_files = [f.name for f in src_path.iterdir() if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS]

    total_files = len(src_files)
    logger.info(f"Found {total_files} audio file(s)")

    title_cache = _load_title_cache()
    dst_existing_stems = get_existing_songs(target_dir)

    if dst_is_kio and not _kio_stat(target_dir):
        return 0, 0, 0, [f"target not found: {target_dir}"]
    elif not dst_is_kio:
        dst_path = Path(target_dir).expanduser().resolve()
        dst_path.mkdir(parents=True, exist_ok=True)

    results = {"transferred": 0, "renamed": 0, "skipped": 0, "errors": []}

    def process_file(filename: str, idx: int):
        ext = Path(filename).suffix.lower()
        stem = Path(filename).stem
        src_file = f"{source_dir.rstrip('/')}/{filename}" if src_is_kio else src_path / filename

        # 1. Fast existence check
        if stem in dst_existing_stems:
            logger.progress(idx, total_files, "skip", filename)
            return "skip", None

        # 2. Identity detection
        local_temp = None
        if src_is_kio:
            local_temp = _kio_download_to_temp(src_file)
            if not local_temp: return "error", f"fail: {filename} (download failed)"
            validate_path = local_temp
        else:
            validate_path = str(src_file)

        if validate and not is_audio_valid(validate_path):
            if local_temp: os.unlink(local_temp)
            return "error", f"fail: {filename} (corrupted file)"

        video_id = get_ncsdl_id(validate_path)
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

        # 3. Final existence check
        if correct_name in dst_existing_stems:
            if local_temp: os.unlink(local_temp)
            logger.progress(idx, total_files, "skip", f"{correct_name}{ext}")
            return "skip", None

        # 4. Transfer
        target_name = f"{correct_name}{ext}"
        success = False
        
        if dst_is_kio:
            target_full = f"{target_dir.rstrip('/')}/{target_name}"
            success = (_kio_move(str(src_file), target_full) if mode == "move" else _kio_copy(str(src_file), target_full))
        else:
            final_target = dst_path / target_name
            if src_is_kio and local_temp:
                shutil.move(local_temp, str(final_target))
                local_temp = None
                if mode == "move": _kio_move(src_file, "/tmp/.ncsdl_trash")
                success = True
            elif not src_is_kio:
                if mode == "move": src_file.rename(final_target)
                else: shutil.copy2(str(src_file), str(final_target))
                success = True

        if local_temp: os.unlink(local_temp)

        if success:
            status = "ok (fixed name)" if stem != correct_name else "ok"
            logger.progress(idx, total_files, status, target_name)
            return "ok", (stem != correct_name)
        else:
            return "error", f"fail: {filename} (transfer error)"

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_file, f, i) for i, f in enumerate(src_files, 1)]
        for future in futures:
            status, data = future.result()
            if status == "ok":
                results["transferred"] += 1
                if data: results["renamed"] += 1
            elif status == "skip": results["skipped"] += 1
            else: results["errors"].append(data)

    return results["transferred"], results["renamed"], results["skipped"], results["errors"]
