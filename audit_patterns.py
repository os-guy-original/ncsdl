#!/usr/bin/env python3
"""Audit regex patterns against all NCS titles."""

import json
import re
from pathlib import Path

# Patterns (copied from styles.py)
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
    r"(?P<title>[^|]+?)"
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
    r"^(?P<artist>[^-|]+?)\s+-\s+"
    r"(?P<title>[^|]+?)"
    r"\s*$"
)

PATTERNS = [
    ("RE_MODERN", RE_MODERN),
    ("RE_COLLAB", RE_COLLAB),
    ("RE_OLD", RE_OLD),
    ("RE_BARE", RE_BARE),
]


def main():
    titles_path = Path(__file__).parent / "ncs_titles.json"
    entries = json.loads(titles_path.read_text())
    print(f"Loaded {len(entries)} titles.\n")

    pattern_counts = {name: 0 for name, _ in PATTERNS}
    pattern_examples = {name: [] for name, _ in PATTERNS}
    unmatched = []
    bad_parses = []
    bare_with_pipe = []

    for entry in entries:
        title = entry["title"]
        vid_id = entry["id"]
        matched_any = False

        for pname, pattern in PATTERNS:
            m = pattern.match(title)
            if m:
                matched_any = True
                pattern_counts[pname] += 1
                groups = m.groupdict()
                example = {
                    "id": vid_id,
                    "title": title,
                    "artist": groups.get("artist", "").strip(),
                    "song": groups.get("title", "").strip(),
                    "genre": groups.get("genre", "").strip() if "genre" in groups else None,
                }
                if len(pattern_examples[pname]) < 5:
                    pattern_examples[pname].append(example)

                # Check for bare with pipe bug
                if pname == "RE_BARE" and "|" in title:
                    bare_with_pipe.append({
                        "id": vid_id,
                        "title": title,
                        "artist": groups.get("artist", "").strip(),
                        "song": groups.get("title", "").strip(),
                    })

                # Check for collab bad parse
                if pname == "RE_COLLAB":
                    artist = groups.get("artist", "").strip()
                    if "copyright" in artist.lower() or "ncs" in artist.lower():
                        bad_parses.append({
                            "id": vid_id,
                            "title": title,
                            "reason": f"artist contains 'Copyright' or 'NCS': '{artist}'",
                            "artist": artist,
                            "song": groups.get("title", "").strip(),
                        })

        if not matched_any:
            unmatched.append({"id": vid_id, "title": title})

    # Print report
    print("=" * 70)
    print("PATTERN MATCH COUNTS")
    print("=" * 70)
    for pname, count in pattern_counts.items():
        print(f"  {pname:15s}: {count}")
    total_matched = sum(pattern_counts.values())
    print(f"  {'TOTAL MATCHES':15s}: {total_matched} (may exceed {len(entries)} if multi-match)")
    print(f"  {'UNMATCHED':15s}: {len(unmatched)}")

    print("\n" + "=" * 70)
    print("FIRST 5 EXAMPLES PER PATTERN")
    print("=" * 70)
    for pname in [n for n, _ in PATTERNS]:
        examples = pattern_examples[pname]
        print(f"\n--- {pname} ({pattern_counts[pname]} total matches) ---")
        for i, ex in enumerate(examples, 1):
            print(f"  {i}. [{ex['id']}] {ex['title']}")
            print(f"     artist='{ex['artist']}'  song='{ex['song']}'  genre={ex['genre']}")

    print("\n" + "=" * 70)
    print(f"UNMATCHED TITLES ({len(unmatched)})")
    print("=" * 70)
    for u in unmatched:
        print(f"  [{u['id']}] {u['title']}")

    print("\n" + "=" * 70)
    print(f"BARE WITH PIPE BUG ({len(bare_with_pipe)})")
    print("=" * 70)
    for b in bare_with_pipe:
        print(f"  [{b['id']}] {b['title']}")
        print(f"     => artist='{b['artist']}'  song='{b['song']}'")

    print("\n" + "=" * 70)
    print(f"BAD COLLAB PARSES ({len(bad_parses)})")
    print("=" * 70)
    for bp in bad_parses:
        print(f"  [{bp['id']}] {bp['title']}")
        print(f"     => {bp['reason']}")

    # Save results
    results = {
        "pattern_counts": pattern_counts,
        "total_entries": len(entries),
        "total_matched": total_matched,
        "unmatched_count": len(unmatched),
        "unmatched": unmatched,
        "bare_with_pipe": bare_with_pipe,
        "bad_parses": bad_parses,
        "examples": pattern_examples,
    }
    output_path = Path(__file__).parent / "pattern_audit.json"
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
