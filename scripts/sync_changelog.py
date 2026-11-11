"""Synchronize the add-on changelog from the repository's canonical changelog.

Run without flags before committing release notes. CI uses --check to ensure the
Home Assistant add-on's copy is current without modifying the checkout.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CHANGELOG.md"
MIRROR = ROOT / "portfolio" / "CHANGELOG.md"


def sync(check=False):
    canonical = SOURCE.read_bytes()
    if check:
        if not MIRROR.is_file() or MIRROR.read_bytes() != canonical:
            raise SystemExit(
                "portfolio/CHANGELOG.md differs from CHANGELOG.md; "
                "run: python scripts/sync_changelog.py"
            )
        print("Home Assistant changelog matches canonical CHANGELOG.md")
        return
    MIRROR.write_bytes(canonical)
    print("Updated portfolio/CHANGELOG.md from CHANGELOG.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without writing")
    args = parser.parse_args()
    sync(check=args.check)
