"""NCS title style detection and genre classification."""

import re
from dataclasses import dataclass
from typing import Optional


# All NCS genre tags as of 2024-2026
NCS_GENRES = frozenset({
    "Alternative Dance",
    "Alternative Hip-Hop",
    "Alternative Pop",
    "Ambient",
    "Anti-Pop",
    "Bass",
    "Bass House",
    "Bass Music",
    "Brazilian Phonk",
    "Breakbeat",
    "Chill",
    "Chill Bass",
    "Chill Pop",
    "Colour Bass",
    "Complextro",
    "Dance-Pop",
    "Deep House",
    "Disco",
    "Disco House",
    "Drum & Bass",
    "Drumstep",
    "Dubstep",
    "EDM",
    "Electro",
    "Electro House",
    "Electronic",
    "Electronic Pop",
    "Electronic Rock",
    "Future Bass",
    "Future Bounce",
    "Future Funk",
    "Future House",
    "Future Rave",
    "Future Trap",
    "Futurepop",
    "Garage",
    "Glitch Hop",
    "Hardcore",
    "Hardstyle",
    "House",
    "Hyperpop",
    "Indie Dance",
    "J-Pop",
    "Jersey Club",
    "Jump-Up",
    "Liquid DnB",
    "Lofi Hip-Hop",
    "Melodic Dubstep",
    "Melodic House",
    "Midtempo Bass",
    "Neurofunk",
    "Nu-Jazz",
    "Phonk",
    "Pluggnb",
    "Pop",
    "Progressive House",
    "RnB",
    "Speed Garage",
    "Tech House",
    "Techno",
    "Trance",
    "Trap",
    "Tribal House",
    "UKG",
    "Wave",
    "Witch House",
})

# Genre lookup: lowercase -> canonical name (built once at import)
_GENRE_LOOKUP: dict[str, str] = {g.lower(): g for g in NCS_GENRES}


@dataclass
class ParsedTitle:
    """Result of parsing an NCS YouTube title."""
    artist: str
    song_title: str
    genre: Optional[str] = None
    featuring: Optional[str] = None
    suffix: Optional[str] = None  # e.g. "VIP", "Remix", "pt. II"
    style: str = "unknown"  # Which title format was matched


# Title format patterns (ordered by priority - most specific first)

# Modern format: "Artist - Song | Genre | NCS - Copyright Free Music"
RE_MODERN = re.compile(
    r"^(?P<artist>.+?)\s+-\s+"
    r"(?P<title>.+?)"
    r"\s*\|\s*(?P<genre>[^|]+?)"
    r"\s*\|\s*NCS"
    r"(?:\s*-\s*Copyright\s+Free\s+Music)?\s*$",
    re.IGNORECASE,
)

# Old format: "Artist - Song [NCS Release]"
RE_OLD = re.compile(
    r"^(?P<artist>.+?)\s+-\s+"
    r"(?P<title>.+?)"
    r"\s*\[NCS\s+Release\]\s*$",
    re.IGNORECASE,
)

# Bare format: "Artist - Song" (no NCS tag, no genre)
RE_BARE = re.compile(
    r"^(?P<artist>.+?)\s+-\s+(?P<title>.+?)\s*$"
)

# Dispatch table: (regex, style_name) tuples tried in order
_TITLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (RE_MODERN, "modern"),
    (RE_OLD, "old"),
    (RE_BARE, "bare"),
]

# Suffix patterns for extracting things like VIP, Remix, pt.II, etc.
_SUFFIX_PATTERNS = [
    re.compile(r"\s*\(VIP\)\s*$", re.IGNORECASE),
    re.compile(r"\s*VIP\s*$", re.IGNORECASE),
    re.compile(r"\s*\(Remix\)\s*$", re.IGNORECASE),
    re.compile(r"\s*\(Sped Up\)\s*$", re.IGNORECASE),
    re.compile(r"\s*\(\d{4}\s+Edit\)\s*$", re.IGNORECASE),
    re.compile(r"\s*\(Hindi\)\s*$", re.IGNORECASE),
    re.compile(r"\s*pt\.\s*II\s*$", re.IGNORECASE),
    re.compile(r"\s*pt\.\s*2\s*$", re.IGNORECASE),
]

_FEATURING_RE = re.compile(r"\(feat\.\s+(.+?)\)", re.IGNORECASE)


def _normalize_genre(raw: str) -> Optional[str]:
    """Look up a genre by case-insensitive name. Returns canonical form or None."""
    return _GENRE_LOOKUP.get(raw.lower())


def _extract_featuring(title: str) -> tuple[str, Optional[str]]:
    """Extract featuring artist from title.

    Returns (clean_title, featuring_artist) or (title, None).
    """
    match = _FEATURING_RE.search(title)
    if match:
        return (title[:match.start()].strip() + title[match.end():].strip()), match.group(1).strip()
    return title, None


def _extract_suffix(title: str) -> tuple[str, Optional[str]]:
    """Extract suffix like VIP, Remix, pt.II, Sped Up, etc.

    Returns (clean_title, suffix) or (title, None).
    """
    for pattern in _SUFFIX_PATTERNS:
        match = pattern.search(title)
        if match:
            return title[:match.start()].strip(), match.group().strip()
    return title, None


def _finalize_title(
    artist: str,
    song: str,
    genre: Optional[str],
    style: str,
) -> ParsedTitle:
    """Run shared post-processing (featuring, suffix) and return ParsedTitle."""
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
    """Parse an NCS YouTube video title.

    Returns a ParsedTitle with extracted fields, or None if not recognized.
    """
    title = title.strip()

    for pattern, style in _TITLE_PATTERNS:
        match = pattern.match(title)
        if match:
            artist = match.group("artist").strip()
            song = match.group("title").strip()

            # Only the modern format has a genre group
            genre = None
            if "genre" in match.groupdict():
                genre = _normalize_genre(match.group("genre").strip())

            return _finalize_title(artist, song, genre, style)

    return None


def classify_by_genre(titles: list[str]) -> dict[str, int]:
    """Count songs by genre from a list of YouTube titles.

    Returns a dict of {genre: count} sorted by count descending.
    """
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
