"""YouTube search and download functionality for NCS songs."""

from .download import (
    download_video,
    download_videos,
)
from .files import (
    SUPPORTED_FORMATS,
    get_existing_songs,
    get_ncsdl_id,
    sanitize_filename,
)
from .queue import (
    clear_queue,
    filter_downloaded,
    load_queue,
    save_queue,
)
from .search import (
    VideoInfo,
    check_dependencies,
    count_ncs_videos,
    fetch_video_info,
    get_all_ncs_videos,
    search_ncs_videos,
)
from .track import (
    load_track,
    record_download,
    remove_entry,
    save_track,
)

__all__ = [
    "VideoInfo",
    "SUPPORTED_FORMATS",
    "check_dependencies",
    "download_video",
    "download_videos",
    "get_existing_songs",
    "get_ncsdl_id",
    "sanitize_filename",
    "search_ncs_videos",
    "fetch_video_info",
    "get_all_ncs_videos",
    "count_ncs_videos",
    "save_queue",
    "load_queue",
    "clear_queue",
    "filter_downloaded",
    "load_track",
    "save_track",
    "record_download",
    "remove_entry",
]
