"""Fail releases with inconsistent Home Invest version metadata."""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
version_src = (ROOT / "portfolio/app/version.py").read_text(encoding="utf-8")
module = ast.parse(version_src)
versions = [
    node.value.value
    for node in module.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "APP_VERSION" for target in node.targets)
    and isinstance(node.value, ast.Constant)
    and isinstance(node.value.value, str)
]
if len(versions) != 1:
    sys.exit("Expected exactly one static APP_VERSION in portfolio/app/version.py")
version = versions[0]
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    sys.exit(f"Invalid semantic version: {version}")
config = (ROOT / "portfolio/config.yaml").read_text(encoding="utf-8")
if not re.search(r'^version:\s*["\']?' + re.escape(version) + r'["\']?\s*$', config, flags=re.M):
    sys.exit(f"portfolio/config.yaml version must match {version}")
for name in ("CHANGELOG.md", "portfolio/CHANGELOG.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    first_header = re.search(r"^##\s+(.+)$", text, re.M)
    if not first_header or first_header.group(1).strip() != version:
        sys.exit(f"{name} must start with release ## {version}")
print(f"Home Invest {version}: version metadata and release notes consistent")
