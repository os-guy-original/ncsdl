"""Command registry."""

from .analyze import run as cmd_analyze
from .check_dupes import run as cmd_check_dupes
from .count import run as cmd_count
from .download import run as cmd_download
from .list_genres import run as cmd_list_genres
from .metadata import run as cmd_metadata
from .resume import run as cmd_resume
from .search import run as cmd_search
from .stats import run as cmd_stats

COMMANDS = {
    "analyze": cmd_analyze,
    "count": cmd_count,
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
