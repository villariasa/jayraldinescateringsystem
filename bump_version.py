#!/usr/bin/env python3
"""
bump_version.py - Office 3-Digit Versioning System with Auto-Detection.
Supports both Tablet Android APK and Desktop Windows App.

Rules:
  1st digit (Major):
    - System overhaul / breaking change.
    - Triggered by: commit with 'major:', 'breaking:', 'BREAKING CHANGE', or --major.
    - Result: (X + 1).0.0

  2nd digit (Module / Functionality):
    - New functionalities / modules added.
    - Triggered by: new .sql file added, commit with 'feat:' or 'module:', or --module.
    - Result: X.(Y + 1).0

  3rd digit (Bug Fix / DB Changes):
    - ODD  = Bug fix (utility / code only).
             Triggered by: fixes with NO database/SQL changes, or --odd / --fix.
             Result: Next odd number (e.g. 5 -> 7, 45 -> 47).
    - EVEN = Bug fix AND data model changes (tables, procedures, SQL changes).
             Triggered by: modified .sql files / DB schema changes, or --even / --db.
             Result: Next even number (e.g. 5 -> 6, 45 -> 46).

  versionCode (Tablet only):
    - Auto-increments strictly by +1 on every build for Android Package Manager.

Usage:
  python3 bump_version.py [--tablet] [--dry-run] [--major] [--module] [--odd|--fix] [--even|--db] [--same]
  python3 bump_version.py --desktop [--dry-run] [--major] [--module] [--odd|--fix] [--even|--db] [--same]
  python3 bump_version.py --all [--dry-run]
"""

import os
import re
import sys
import datetime
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GRADLE_FILE = ROOT / "Tablet_Android_APK" / "app" / "build.gradle"
PWA_API_JS = ROOT / "Tablet_PWA" / "frontend" / "js" / "api.js"
APK_API_JS = ROOT / "Tablet_Android_APK" / "app" / "src" / "main" / "assets" / "js" / "api.js"

DESKTOP_DIR = ROOT / "Catering_Present" / "jayraldines_catering"
DESKTOP_VERSION_FILE = DESKTOP_DIR / "version.py"
DESKTOP_ISS_FILE = DESKTOP_DIR / "installer.iss"


def run_git(cmd: list[str]) -> str:
    try:
        res = subprocess.run(["git"] + cmd, cwd=ROOT, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return ""


def get_current_tablet_version() -> tuple[str, int]:
    if not GRADLE_FILE.exists():
        return "2.1.5", 48
    content = GRADLE_FILE.read_text(encoding="utf-8")
    name_m = re.search(r'versionName\s+["\']([^"\']+)["\']', content)
    code_m = re.search(r'versionCode\s+(\d+)', content)
    name = name_m.group(1) if name_m else "2.1.5"
    code = int(code_m.group(1)) if code_m else 48
    return name, code


def get_current_desktop_version() -> str:
    if DESKTOP_VERSION_FILE.exists():
        content = DESKTOP_VERSION_FILE.read_text(encoding="utf-8")
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if m:
            return m.group(1)
    return "4.1.45"


def next_odd(val: int) -> int:
    return val + 2 if (val % 2 != 0) else val + 1


def next_even(val: int) -> int:
    return val + 2 if (val % 2 == 0) else val + 1


def detect_change_type(last_commit: str, path_filter: str = "") -> tuple[str, str]:
    """Inspects git commits and changed files since last_commit to determine bump category."""
    commit_range = f"{last_commit}..HEAD" if last_commit else "HEAD~10..HEAD"
    logs = run_git(["log", "--pretty=format:%s", commit_range]).lower()
    
    # 1. Check for major breaking changes
    if "breaking:" in logs or "breaking change" in logs or "major:" in logs:
        return "major", "Commit history contains breaking/major change"

    # 2. Check changed files (committed + staged + untracked)
    changed_files = []
    if last_commit:
        diff_names = run_git(["diff", "--name-only", f"{last_commit}..HEAD"])
        if diff_names:
            changed_files.extend(diff_names.splitlines())
    
    status_out = run_git(["status", "--porcelain"])
    added_files = []
    for line in status_out.splitlines():
        if len(line) >= 3:
            code = line[:2]
            filepath = line[3:].strip().strip('"')
            changed_files.append(filepath)
            if "A" in code or "??" in code:
                added_files.append(filepath)

    if path_filter:
        changed_files = [f for f in changed_files if path_filter in f or f.endswith(".sql")]
        added_files = [f for f in added_files if path_filter in f or f.endswith(".sql")]

    # 3. Check for newly added SQL files -> 2nd digit (Module / functionality)
    new_sql = [f for f in added_files if f.endswith(".sql")]
    if new_sql or "feat(" in logs or "module:" in logs:
        reason = f"New module/SQL file detected: {new_sql[0]}" if new_sql else "New feature module commit detected"
        return "module", reason

    # 4. Check for modified SQL / DB files -> 3rd digit (EVEN: bug fix + data model)
    modified_sql = [f for f in changed_files if f.endswith(".sql") or "migration" in f.lower() or "schema" in f.lower()]
    if modified_sql:
        return "even", f"DB schema / SQL changes detected in: {modified_sql[0]}"

    # 5. Default: pure code / utility / bug fixes -> 3rd digit (ODD)
    return "odd", "Code bug fix / utility refactor (no DB changes)"


def compute_new_version(curr_name: str, bump_type: str) -> str:
    parts = curr_name.split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 2
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "module":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "even":
        return f"{major}.{minor}.{next_even(patch)}"
    elif bump_type == "odd":
        return f"{major}.{minor}.{next_odd(patch)}"
    elif bump_type == "same":
        return curr_name
    else:
        return f"{major}.{minor}.{next_odd(patch)}"


def apply_tablet_version(new_name: str, new_code: int):
    if GRADLE_FILE.exists():
        content = GRADLE_FILE.read_text(encoding="utf-8")
        content = re.sub(r'versionName\s+["\'][^"\']+["\']', f'versionName "{new_name}"', content)
        content = re.sub(r'versionCode\s+\d+', f'versionCode {new_code}', content)
        GRADLE_FILE.write_text(content, encoding="utf-8")

    for js_path in [PWA_API_JS, APK_API_JS]:
        if js_path.exists():
            c = js_path.read_text(encoding="utf-8")
            c_new = re.sub(r'app_version:\s*["\']v?[^"\']+["\']', f'app_version: "v{new_name}"', c)
            if c_new != c:
                js_path.write_text(c_new, encoding="utf-8")


def apply_desktop_version(new_name: str):
    today_str = datetime.date.today().strftime("%Y.%m.%d")
    if DESKTOP_VERSION_FILE.exists():
        content = f'''"""\nCentralized Version and Application Metadata for Jayraldine's Catering.\n"""\n\n__version__ = "{new_name}"\nAPP_NAME = "Jayraldine's Catering"\nBUILD_ID = "{today_str}-v{new_name}"\n'''
        DESKTOP_VERSION_FILE.write_text(content, encoding="utf-8")

    if DESKTOP_ISS_FILE.exists():
        content = DESKTOP_ISS_FILE.read_text(encoding="utf-8")
        content = re.sub(r'AppVersion=.*', f'AppVersion={new_name}', content)
        content = re.sub(r'OutputBaseFilename=Jayraldines_Catering_Setup_v.*', f'OutputBaseFilename=Jayraldines_Catering_Setup_v{new_name}', content)
        DESKTOP_ISS_FILE.write_text(content, encoding="utf-8")


def main():
    dry_run = "--dry-run" in sys.argv
    target_desktop = "--desktop" in sys.argv
    target_all = "--all" in sys.argv
    target_tablet = "--tablet" in sys.argv or (not target_desktop and not target_all)

    # Check explicit flag overrides
    explicit_type = None
    if "--major" in sys.argv:
        explicit_type = "major"
    elif "--module" in sys.argv or "--feat" in sys.argv:
        explicit_type = "module"
    elif "--even" in sys.argv or "--db" in sys.argv:
        explicit_type = "even"
    elif "--odd" in sys.argv or "--fix" in sys.argv:
        explicit_type = "odd"
    elif "--same" in sys.argv:
        explicit_type = "same"

    type_labels = {
        "major": "1st digit * Major version overhaul",
        "module": "2nd digit * Functionality / module added",
        "even": "3rd digit (EVEN) * Bug fix & data model / SQL changes",
        "odd": "3rd digit (ODD) * Bug fix (utility / code only)",
        "same": "Keep versionName (code bump only)",
    }

    print("=======================================================")
    print("       Office 3-Digit Versioning Auto-Detector         ")
    print("=======================================================")

    # Handle Tablet
    if target_tablet or target_all:
        curr_name, curr_code = get_current_tablet_version()
        new_code = curr_code + 1
        if explicit_type:
            b_type = explicit_type
            reason = f"Explicit flag --{explicit_type} passed"
        else:
            last_commit = run_git(["log", "-n", "1", "--pretty=format:%H", "--", "Tablet_Android_APK/app/build.gradle"])
            b_type, reason = detect_change_type(last_commit, "Tablet")
        new_name = compute_new_version(curr_name, b_type)

        print(f" [TABLET APK]")
        print(f"   Detected Intent : {type_labels.get(b_type, b_type)}")
        print(f"   Reason          : {reason}")
        print(f"   versionName     : {curr_name} -> {new_name}")
        print(f"   versionCode     : {curr_code} -> {new_code}")
        if not dry_run:
            apply_tablet_version(new_name, new_code)
            print("   -> build.gradle & api.js updated.")
        else:
            print("   -> [DRY-RUN] No files modified.")
        print("-" * 55)

    # Handle Desktop
    if target_desktop or target_all:
        curr_desk = get_current_desktop_version()
        if explicit_type:
            d_type = explicit_type
            d_reason = f"Explicit flag --{explicit_type} passed"
        else:
            last_commit = run_git(["log", "-n", "1", "--pretty=format:%H", "--", "Catering_Present/jayraldines_catering/version.py"])
            d_type, d_reason = detect_change_type(last_commit, "Catering_Present")
        new_desk = compute_new_version(curr_desk, d_type)

        print(f" [DESKTOP PC APP]")
        print(f"   Detected Intent : {type_labels.get(d_type, d_type)}")
        print(f"   Reason          : {d_reason}")
        print(f"   __version__     : {curr_desk} -> {new_desk}")
        if not dry_run:
            apply_desktop_version(new_desk)
            print("   -> version.py & installer.iss updated.")
        else:
            print("   -> [DRY-RUN] No files modified.")
        print("-" * 55)

    print("=======================================================")


if __name__ == "__main__":
    main()
