"""metadata command."""

from ..metadata import embed_metadata_batch


def run(args) -> int:
    if not args.files:
        print("no files specified.")
        return 1

    success, fail, errors = embed_metadata_batch(args.files)

    print(f"metadata complete: {success} succeeded, {fail} failed")

    if errors:
        print()
        print("errors:")
        for err in errors:
            print(f"  - {err}")

    return 0 if fail == 0 else 1
