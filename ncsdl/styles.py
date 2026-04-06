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
# or "Artist - Song | Genre | NCS"
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


def _extract_featuring(title: str) -> tuple[str, Optional[str]]:
    """Extract featuring artist from title.

    Returns (clean_title, featuring_artist) or (title, None).
    """
    match = re.search(r"\(feat\.\s+(.+?)\)", title, re.IGNORECASE)
    if match:
        featuring = match.group(1).strip()
        clean = title[: match.start()].strip() + title[match.end():].strip()
        return clean, featuring
    return title, None


def _extract_suffix(title: str) -> tuple[str, Optional[str]]:
    """Extract suffix like VIP, Remix, pt.II, Sped Up, etc.

    Returns (clean_title, suffix) or (title, None).
    """
    patterns = [
        r"\s*\(VIP\)\s*$",
        r"\s*VIP\s*$",
        r"\s*\(Remix\)\s*$",
        r"\s*\(Sped Up\)\s*$",
        r"\s*\(\d{4}\s+Edit\)\s*$",
        r"\s*\(Hindi\)\s*$",
        r"\s*pt\.\s*II\s*$",
        r"\s*pt\.\s*2\s*$",
        r"\s*Dead of Night \(VIP\)\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            suffix = match.group(0).strip()
            clean = title[: match.start()].strip()
            return clean, suffix
    return title, None


def parse_title(title: str) -> Optional[ParsedTitle]:
    """Parse an NCS YouTube video title.

    Returns a ParsedTitle with extracted fields, or None if not recognized.
    """
    title = title.strip()

    # Try modern format first
    match = RE_MODERN.match(title)
    if match:
        artist = match.group("artist").strip()
        song = match.group("title").strip()
        genre = match.group("genre").strip()

        # Normalize genre casing
        for known_genre in NCS_GENRES:
            if known_genre.lower() == genre.lower():
                genre = known_genre
                break

        song, featuring = _extract_featuring(song)
        song, suffix = _extract_suffix(song)

        return ParsedTitle(
            artist=artist,
            song_title=song.strip(),
            genre=genre,
            featuring=featuring,
            suffix=suffix,
            style="modern",
        )

    # Try old format
    match = RE_OLD.match(title)
    if match:
        artist = match.group("artist").strip()
        song = match.group("title").strip()

        song, featuring = _extract_featuring(song)
        song, suffix = _extract_suffix(song)

        return ParsedTitle(
            artist=artist,
            song_title=song.strip(),
            featuring=featuring,
            suffix=suffix,
            style="old",
        )

    # Try bare format
    match = RE_BARE.match(title)
    if match:
        artist = match.group("artist").strip()
        song = match.group("title").strip()

        song, featuring = _extract_featuring(song)
        song, suffix = _extract_suffix(song)

        return ParsedTitle(
            artist=artist,
            song_title=song.strip(),
            featuring=featuring,
            suffix=suffix,
            style="bare",
        )

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

    # Sort by count descending
    sorted_counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
    if unrecognized > 0:
        sorted_counts["Unrecognized"] = unrecognized

    return sorted_counts


def format_genre_stats(genre_counts: dict[str, int]) -> str:
    """Format genre statistics as a clean table."""
    if not genre_counts:
        return "No genre data available."

    lines = []
    lines.append(f"{'Genre':<25} {'Count':>5}")
    lines.append("-" * 32)

    total = 0
    for genre, count in genre_counts.items():
        lines.append(f"{genre:<25} {count:>5}")
        total += count

    lines.append("-" * 32)
    lines.append(f"{'Total':<25} {total:>5}")

    return "\n".join(lines)
