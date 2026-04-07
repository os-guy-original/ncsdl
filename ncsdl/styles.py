"""NCS title style detection and genre classification."""

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

NCS_CHANNEL_URL = "https://www.youtube.com/@NoCopyrightSounds/videos"
_GENRE_CACHE = Path(__file__).parent / "genres.json"

# Regex to extract genre from modern titles: "Artist - Song | Genre | NCS..."
_RE_GENRE_TAG = re.compile(r"\|\s*([^|]+?)\s*\|\s*NCS", re.IGNORECASE)

# Patterns that indicate a "genre" is actually a song title or mix name
_FILTER_PATTERNS = frozenset({
    "feat", "mix", "album", "remix", "mashup",
    " x ", "vip", " ft.", " (",
    "except", "faster", "every", "seconds",
})


@dataclass
class ParsedTitle:
    """Result of parsing an NCS YouTube title."""
    artist: str
    song_title: str
    genre: Optional[str] = None
    featuring: Optional[str] = None
    suffix: Optional[str] = None
    style: str = "unknown"


# Genre lookup: lowercase -> canonical name (loaded dynamically)
_genre_lookup: dict[str, str] = {}
_known_genres: frozenset = frozenset()


def _build_genre_lookup(raw_genres: set[str]) -> None:
    """Build the global genre lookup table."""
    global _genre_lookup, _known_genres
    _genre_lookup = {g.lower(): g for g in raw_genres}
    _known_genres = frozenset(raw_genres)


def _load_cached_genres() -> Optional[set[str]]:
    """Load genres from cache file."""
    try:
        if _GENRE_CACHE.exists():
            data = json.loads(_GENRE_CACHE.read_text())
            genres = set(data.get("genres", []))
            if genres:
                return genres
    except Exception:
        pass
    return None


def _save_genres(genres: set[str]) -> None:
    """Save genres to cache file."""
    try:
        _GENRE_CACHE.write_text(json.dumps({"genres": sorted(genres)}, indent=2))
    except Exception:
        pass


def _is_valid_genre(raw: str) -> bool:
    """Check if a raw genre candidate is likely a real genre tag."""
    g_lower = raw.lower()
    if any(p in g_lower for p in _FILTER_PATTERNS):
        return False
    if len(raw) > 22 or len(raw.split()) > 3:
        return False
    if raw.replace(" ", "").isdigit():
        return False
    if raw[0].islower():
        return False
    return True


def detect_genres() -> set[str]:
    """Detect all genres from the NCS YouTube channel.

    Uses yt-dlp to scan the channel, extracts genre tags from titles,
    filters out non-genre noise, and caches the result.

    Returns a set of genre strings.
    """
    cached = _load_cached_genres()
    if cached is not None:
        return cached

    cmd = [
        "yt-dlp",
        NCS_CHANNEL_URL,
        "--flat-playlist",
        "--print",
        "%(title)s",
        "--no-download",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return set()

    genres = set()
    for line in result.stdout.splitlines():
        m = _RE_GENRE_TAG.search(line)
        if m:
            raw = m.group(1).strip()
            if _is_valid_genre(raw):
                genres.add(raw)

    if genres:
        _save_genres(genres)

    return genres


def get_genres() -> frozenset:
    """Get the current set of known NCS genres.

    Loads from cache or detects dynamically.
    """
    global _genre_lookup, _known_genres
    if _known_genres:
        return _known_genres

    genres = _load_cached_genres()
    if genres is None:
        genres = detect_genres()
        if not genres:
            return frozenset()

    _build_genre_lookup(genres)
    return _known_genres


def normalize_genre(raw: str) -> Optional[str]:
    """Look up a genre by case-insensitive name. Returns canonical form or None."""
    if not _genre_lookup:
        get_genres()  # lazy load
    return _genre_lookup.get(raw.lower())


# Title format patterns

# Modern format: "Artist - Song | Genre | NCS - Copyright Free Music"
# Also: "Artist - Song | Genre | NCS x Partner - Copyright Free Music"
# Also: en-dash (–), NCS13, NCS10 suffixes
RE_MODERN = re.compile(
    r"^(?P<artist>.+?)\s+[\-–]\s+"
    r"(?P<title>.+?)"
    r"\s*\|\s*(?P<genre>[^|]+?)"
    r"\s*\|\s*NCS\d*\b"
    r"(?:\s*x\s*[^|]+?)?"
    r"(?:\s*-\s*Copyright\s+Free\s+Music)?\s*$",
    re.IGNORECASE,
)

# Old format: "Artist - Song [NCS Release]"
RE_OLD = re.compile(
    r"^(?P<artist>.+?)\s+[\-–]\s+"
    r"(?P<title>.+?)"
    r"\s*\[NCS\s+Release\]\s*$",
    re.IGNORECASE,
)

# Collab format: "Artist - Song NCS - Copyright Free Music" (no genre pipes)
# Also: "Artist - Song Genre NCS13 - Copyright Free Music" (inline genre)
# Also accepts en-dash (\u2013), NCS10/NCS13 suffixes
# Genre is extracted from end of title in _finalize_title()
RE_COLLAB = re.compile(
    r"^(?P<artist>.+?)\s+[\u002d\u2013]\s+"
    r"(?P<title>.+?)"
    r"\s+NCS\d*\b"
    r"(?:\s*-\s*Copyright\s+Free\s+Music)?\s*$",
    re.IGNORECASE,
)

# Bare format: "Artist - Song" or "Artist - Song NCS - Copyright Free Music"
# The suffix is optional and gets stripped from the title group
RE_BARE = re.compile(
    r"^(?P<artist>[^-]+?)\s+-\s+"
    r"(?P<title>.+?)"
    r"(?:\s+NCS\s*-\s*Copyright\s+Free\s+Music)?\s*$"
)

# Mashup format: "Song A x Song B Mashup NCS - Copyright Free Music"
# or "Song A x Song B Mashup | NCS - Copyright Free Music"
RE_MASHUP = re.compile(
    r"^(?P<artist>.+?)\s+x\s+"
    r"(?P<title>.+?)"
    r"\s+Mashup"
    r"(?:\s*\|[^|]*)?"
    r"(?:\s+NCS\s*-\s*Copyright\s+Free\s+Music)?\s*$",
    re.IGNORECASE,
)

_TITLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (RE_MODERN, "modern"),
    (RE_MASHUP, "mashup"),
    (RE_COLLAB, "collab"),
    (RE_OLD, "old"),
    (RE_BARE, "bare"),
]

_SUFFIX_PATTERNS = [
    re.compile(r"\s*\(VIP\)\s*$", re.IGNORECASE),
    re.compile(r"\s*VIP\s*$", re.IGNORECASE),
    re.compile(r"\s*\(Remix\)\s*$", re.IGNORECASE),
    re.compile(r"\s*Mashup\s*$", re.IGNORECASE),
    re.compile(r"\s*\(Sped Up\)\s*$", re.IGNORECASE),
    re.compile(r"\s*\(\d{4}\s+Edit\)\s*$", re.IGNORECASE),
    re.compile(r"\s*\(Hindi\)\s*$", re.IGNORECASE),
    re.compile(r"\s*pt\.\s*II\s*$", re.IGNORECASE),
    re.compile(r"\s*pt\.\s*2\s*$", re.IGNORECASE),
]

_FEATURING_RE = re.compile(r"\(feat\.\s+(.+?)\)", re.IGNORECASE)


def _extract_featuring(title: str) -> tuple[str, Optional[str]]:
    """Extract featuring artist from title."""
    match = _FEATURING_RE.search(title)
    if match:
        return (title[:match.start()].strip() + title[match.end():].strip()), match.group(1).strip()
    return title, None


def _extract_suffix(title: str) -> tuple[str, Optional[str]]:
    """Extract suffix like VIP, Remix, pt.II, etc."""
    for pattern in _SUFFIX_PATTERNS:
        match = pattern.search(title)
        if match:
            return title[:match.start()].strip(), match.group().strip()
    return title, None


def _extract_genre_from_title(title: str) -> tuple[str, Optional[str]]:
    """Try to extract a known genre from the end of a title string."""
    if not title:
        return title, None
    parts = title.split()
    if len(parts) < 2:
        return title, None
    get_genres()  # ensure lookup is loaded
    # Check last two words first (matches multi-word genres like "Melodic Dubstep")
    if len(parts) >= 3:
        last2 = " ".join(parts[-2:]).lower()
        if last2 in _genre_lookup:
            return " ".join(parts[:-2]).strip(), _genre_lookup[last2]
    # Check last word
    last = parts[-1].lower()
    if last in _genre_lookup:
        return " ".join(parts[:-1]).strip(), _genre_lookup[last]
    return title, None


def _finalize_title(
    artist: str,
    song: str,
    genre: Optional[str],
    style: str,
) -> ParsedTitle:
    """Run shared post-processing and return ParsedTitle."""
    # For collab style, try to extract genre from end of title
    if style == "collab" and genre is None:
        song, inline_genre = _extract_genre_from_title(song)
        if inline_genre:
            genre = inline_genre

    song, featuring = _extract_featuring(song)
    song, suffix = _extract_suffix(song)
    return ParsedTitle(
        artist=artist.strip(),
        song_title=song.strip(),
        genre=genre,
        featuring=featuring,
        suffix=suffix,
        style=style,
    )


def parse_title(title: str) -> Optional[ParsedTitle]:
    """Parse an NCS YouTube video title."""
    title = title.strip()

    for pattern, style in _TITLE_PATTERNS:
        match = pattern.match(title)
        if match:
            artist = match.group("artist").strip()
            song = match.group("title").strip()

            # Reject if artist looks like a mix/compilation title
            artist_lower = artist.lower()
            if any(w in artist_lower for w in ("ncs", " mix", "mashup", "album")):
                continue

            genre = None
            if "genre" in match.groupdict():
                genre = normalize_genre(match.group("genre").strip())

            return _finalize_title(artist, song, genre, style)

    return None


def classify_by_genre(titles: list[str]) -> dict[str, int]:
    """Count songs by genre from a list of YouTube titles."""
    counts: dict[str, int] = {}
    unrecognized = 0

    for title in titles:
        parsed = parse_title(title)
        if parsed and parsed.genre:
            counts[parsed.genre] = counts.get(parsed.genre, 0) + 1
        else:
            unrecognized += 1

    sorted_counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
    if unrecognized > 0:
        sorted_counts["Unrecognized"] = unrecognized

    return sorted_counts


def format_genre_stats(genre_counts: dict[str, int]) -> str:
    """Format genre statistics as a clean table."""
    if not genre_counts:
        return "No genre data available."

    lines = [
        f"{'Genre':<25} {'Count':>5}",
        "-" * 32,
    ]

    total = 0
    for genre, count in genre_counts.items():
        lines.append(f"{genre:<25} {count:>5}")
        total += count

    lines.extend([
        "-" * 32,
        f"{'Total':<25} {total:>5}",
    ])

    return "\n".join(lines)


def build_tag_values(parsed: ParsedTitle) -> dict[str, str]:
    """Build a dict of cleaned tag values from a parsed title."""
    title = parsed.song_title
    if parsed.suffix:
        title = f"{title} {parsed.suffix}"

    artist = parsed.artist
    if parsed.featuring:
        artist = f"{artist} feat. {parsed.featuring}"

    return {
        "title": title,
        "artist": artist,
        "genre": parsed.genre or "Electronic",
        "album": "NCS - NoCopyrightSounds",
    }
