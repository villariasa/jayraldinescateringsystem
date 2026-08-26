"""
Auto-increment version manager for Jayraldine's Catering Tablet & Mobile app.
Synchronizes version across Tablet/version.py, pysidedeploy.spec, and installer configs.

Usage:
  python bump_version.py                  # Auto-increments patch version (e.g. 0.1.0 -> 0.1.1)
  python bump_version.py --minor          # Increments minor version (e.g. 0.1.0 -> 0.2.0)
  python bump_version.py --major          # Increments major version (e.g. 0.1.0 -> 1.0.0)
  python bump_version.py --set 1.2.3      # Sets explicit version
"""

import sys
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def get_current_version() -> tuple[int, int, int]:
    version_file = ROOT / "version.py"
    if not version_file.exists():
        return (0, 1, 0)

    content = version_file.read_text(encoding="utf-8")
    major_m = re.search(r"VERSION_MAJOR\s*=\s*(\d+)", content)
    minor_m = re.search(r"VERSION_MINOR\s*=\s*(\d+)", content)
    patch_m = re.search(r"VERSION_PATCH\s*=\s*(\d+)", content)

    major = int(major_m.group(1)) if major_m else 0
    minor = int(minor_m.group(1)) if minor_m else 1
    patch = int(patch_m.group(1)) if patch_m else 0
    return (major, minor, patch)


def update_version(major: int, minor: int, patch: int) -> str:
    ver_str = f"{major}.{minor}.{patch}"
    version_code = major * 10000 + minor * 100 + patch

    # 1. Update Tablet/version.py
    version_py_content = f'''"""
Version metadata for Jayraldine's Catering - Tablet App.

Semantic versioning: MAJOR.MINOR.PATCH
- MAJOR: breaking schema/export-format changes that require a matching PC update.
- MINOR: new tablet features, backward-compatible.
- PATCH: bug fixes only.
"""

APP_NAME = "Jayraldine's Catering - Tablet"
APP_ID = "com.jayraldines.catering.tablet"

VERSION_MAJOR = {major}
VERSION_MINOR = {minor}
VERSION_PATCH = {patch}

VERSION = f"{{VERSION_MAJOR}}.{{VERSION_MINOR}}.{{VERSION_PATCH}}"
BUILD_CODE = {version_code}

# Bumped whenever the local SQLite schema changes shape in a way that affects
# compatibility with the PC's merge_database_file() import.
SCHEMA_VERSION = 1

# Terms & Conditions version currently bundled with this build.
TERMS_VERSION = "1.0"


def get_version_string() -> str:
    return f"{{APP_NAME}} v{{VERSION}} (schema v{{SCHEMA_VERSION}})"
'''
    (ROOT / "version.py").write_text(version_py_content, encoding="utf-8")
    print(f"  [OK] Updated Tablet/version.py -> v{ver_str} (Build {version_code})")

    # 2. Update pysidedeploy.spec if present
    spec_file = ROOT / "pysidedeploy.spec"
    if spec_file.exists():
        spec_text = spec_file.read_text(encoding="utf-8")
        if "version = " in spec_text:
            spec_text = re.sub(r"version\s*=.*", f"version = {ver_str}", spec_text)
        if "version_code = " in spec_text:
            spec_text = re.sub(r"version_code\s*=.*", f"version_code = {version_code}", spec_text)
        spec_file.write_text(spec_text, encoding="utf-8")
        print(f"  [OK] Updated pysidedeploy.spec -> v{ver_str}")

    return ver_str


def bump(mode: str = "patch", explicit: str = None) -> str:
    if explicit:
        parts = [int(p) for p in explicit.strip().split(".")]
        while len(parts) < 3:
            parts.append(0)
        return update_version(parts[0], parts[1], parts[2])

    major, minor, patch = get_current_version()
    if mode == "major":
        major += 1
        minor = 0
        patch = 0
    elif mode == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return update_version(major, minor, patch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-increment version for Tablet / Mobile Catering")
    parser.add_argument("--minor", action="store_true", help="Bump minor version")
    parser.add_argument("--major", action="store_true", help="Bump major version")
    parser.add_argument("--set", type=str, default=None, help="Set explicit version (e.g. 1.0.0)")
    args = parser.parse_args()

    mode = "major" if args.major else ("minor" if args.minor else "patch")
    new_v = bump(mode=mode, explicit=args.set)
    print(f"New Tablet Version: v{new_v}")
