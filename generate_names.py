#!/usr/bin/env python3
"""Analyze ncs_titles.json and generate expected filenames.

Outputs generated_names.json with parse results for each video.
Run: python generate_names.py
"""

import json
import re
import sys

# === Copy of our title patterns from styles.py ===

RE_MODERN = re.compile(
    r"^(?P<artist>.+?)\s+-\s+"
    r"(?P<title>.+?)"
    r"\s*\|\s*(?P<genre>[^|]+?)"
    r"\s*\|\s*NCS"
    r"(?:\s*x\s*[^|]+?)?"
    r"(?:\s*-\s*Copyright\s+Free\s+Music)?\s*$",
    re.IGNORECASE,
)

RE_COLLAB = re.compile(
    r"^(?P<artist>.+?)\s+-\s+"
    r"(?P<title>.+?)"
    r"\s+NCS\s*-\s*Copyright\s+Free\s+Music\s*$",
    re.IGNORECASE,
)

RE_OLD = re.compile(
    r"^(?P<artist>.+?)\s+-\s+"
    r"(?P<title>.+?)"
    r"\s*\[NCS\s+Release\]\s*$",
    re.IGNORECASE,
)

RE_BARE = re.compile(
    r"^(?P<artist>.+?)\s+-\s+(?P<title>.+?)\s*$"
)

_TITLE_PATTERNS = [
    (RE_MODERN, "modern"),
    (RE_COLLAB, "collab"),
    (RE_OLD, "old"),
    (RE_BARE, "bare"),
]

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

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    name = _UNSAFE_CHARS.sub("", name)
    name = " ".join(name.split())
    return name.strip()


def extract_featuring(title: str):
    match = _FEATURING_RE.search(title)
    if match:
        return (title[:match.start()].strip() + title[match.end():].strip()), match.group(1).strip()
    return title, None


def extract_suffix(title: str):
    for pattern in _SUFFIX_PATTERNS:
        match = pattern.search(title)
        if match:
            return title[:match.start()].strip(), match.group().strip()
    return title, None


def parse_title(title: str):
    title = title.strip()
    for pattern, style in _TITLE_PATTERNS:
        match = pattern.match(title)
        if match:
            artist = match.group("artist").strip()
            song = match.group("title").strip()
            genre = None
            if "genre" in match.groupdict():
                genre = match.group("genre").strip()
            song, featuring = extract_featuring(song)
            song, suffix = extract_suffix(song)
            return {
                "artist": artist,
                "song_title": song.strip(),
                "genre": genre,
                "featuring": featuring,
                "suffix": suffix,
                "style": style,
            }
    return None


def main():
    with open("ncs_titles.json") as f:
        videos = json.load(f)

    results = []
    unmatched = 0

    for v in videos:
        parsed = parse_title(v["title"])
        if parsed:
            filename = sanitize_filename(f"{parsed['artist']} - {parsed['song_title']}")
            if parsed["suffix"]:
                filename = sanitize_filename(f"{filename} {parsed['suffix']}")
            results.append({
                "id": v["id"],
                "title": v["title"],
                "parsed": True,
                "style": parsed["style"],
                "genre": parsed["genre"],
                "filename": filename,
            })
        else:
            results.append({
                "id": v["id"],
                "title": v["title"],
                "parsed": False,
            })
            unmatched += 1

    with open("generated_names.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Total: {len(videos)}")
    print(f"Parsed: {len(videos) - unmatched}")
    print(f"Unparsed: {unmatched}")
    print(f"Output: generated_names.json")

    if unmatched:
        print()
        print("Unparsed titles:")
        for r in results:
            if not r["parsed"]:
                print(f"  {r['title']}")


if __name__ == "__main__":
    main()
