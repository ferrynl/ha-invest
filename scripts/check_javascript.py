"""Discover JavaScript syntax checks and standalone test scripts."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = sorted(
        path for path in (ROOT / "portfolio/app/static").rglob("*")
        if path.is_file() and path.suffix in {".js", ".mjs", ".cjs"}
    )
    tests = sorted(
        path for path in (ROOT / "tests").rglob("test_*")
        if path.is_file() and path.suffix in {".js", ".mjs", ".cjs"}
    )
    if not sources or not tests:
        raise SystemExit("No JavaScript sources or tests found")
    for path in sources + tests:
        subprocess.run(["node", "--check", str(path)], cwd=ROOT, check=True)
    for path in tests:
        subprocess.run(["node", str(path)], cwd=ROOT, check=True)
    print(f"Checked {len(sources)} sources and ran {len(tests)} tests")


if __name__ == "__main__":
    main()
