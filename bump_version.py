#!/usr/bin/env python3
"""
bump_version.py - Office 3-Digit Versioning System with Auto-Detection.

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
             Result: Next odd number (e.g. 5 -> 7, 4 -> 5).
    - EVEN = Bug fix AND data model changes (tables, procedures, SQL changes).
             Triggered by: modified .sql files / DB schema changes, or --even / --db.
             Result: Next even number (e.g. 5 -> 6, 4 -> 6).

  versionCode:
    - Auto-increments strictly by +1 on every build for Android Package Manager.

Usage:
  python3 bump_version.py [--dry-run] [--major] [--module] [--odd|--fix] [--even|--db] [--same]
"""

import os
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GRADLE_FILE = ROOT / "Tablet_Android_APK" / "app" / "build.gradle"
PWA_API_JS = ROOT / "Tablet_PWA" / "frontend" / "js" / "api.js"
APK_API_JS = ROOT / "Tablet_Android_APK" / "app" / "src" / "main" / "assets" / "js" / "api.js"


def run_git(cmd: list[str]) -> str:
    try:
        res = subprocess.run(["git"] + cmd, cwd=ROOT, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return ""


def get_current_gradle_version() -> tuple[str, int]:
    if not GRADLE_FILE.exists():
        return "2.1.5", 48
    content = GRADLE_FILE.read_text(encoding="utf-8")
    name_m = re.search(r'versionName\s+["\']([^"\']+)["\']', content)
    code_m = re.search(r'versionCode\s+(\d+)', content)
    name = name_m.group(1) if name_m else "2.1.5"
    code = int(code_m.group(1)) if code_m else 48
    return name, code


def next_odd(val: int) -> int:
    return val + 2 if (val % 2 != 0) else val + 1


def next_even(val: int) -> int:
    return val + 2 if (val % 2 == 0) else val + 1


def detect_change_type(last_commit: str) -> tuple[str, str]:
    """Inspects git commits and changed files since last_commit to determine bump category."""
    # 1. Commit messages
    commit_range = f"{last_commit}..HEAD" if last_commit else "HEAD~10..HEAD"
    logs = run_git(["log", "--pretty=format:%s", commit_range]).lower()
    
    # 2. Check for major breaking changes
    if "breaking:" in logs or "breaking change" in logs or "major:" in logs:
        return "major", "Commit history contains breaking/major change"

    # 3. Check changed files (committed + staged + untracked)
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

    # 4. Check for newly added SQL files -> 2nd digit (Module / functionality)
    new_sql = [f for f in added_files if f.endswith(".sql")]
    if new_sql or "feat(" in logs or "module:" in logs:
        reason = f"New module/SQL file detected: {new_sql[0]}" if new_sql else "New feature module commit detected"
        return "module", reason

    # 5. Check for modified SQL / DB files -> 3rd digit (EVEN: bug fix + data model)
    modified_sql = [f for f in changed_files if f.endswith(".sql") or "migration" in f.lower() or "schema" in f.lower()]
    if modified_sql:
        return "even", f"DB schema / SQL changes detected in: {modified_sql[0]}"

    # 6. Default: pure code / utility / bug fixes -> 3rd digit (ODD)
    return "odd", "Code bug fix / utility refactor (no DB changes)"


def compute_new_version(curr_name: str, bump_type: str) -> str:
    parts = curr_name.split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 2
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 5

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


def apply_version(new_name: str, new_code: int):
    # 1. Update Tablet_Android_APK/app/build.gradle
    if GRADLE_FILE.exists():
        content = GRADLE_FILE.read_text(encoding="utf-8")
        content = re.sub(r'versionName\s+["\'][^"\']+["\']', f'versionName "{new_name}"', content)
        content = re.sub(r'versionCode\s+\d+', f'versionCode {new_code}', content)
        GRADLE_FILE.write_text(content, encoding="utf-8")

    # 2. Update Tablet_PWA/frontend/js/api.js app_version if present
    for js_path in [PWA_API_JS, APK_API_JS]:
        if js_path.exists():
            c = js_path.read_text(encoding="utf-8")
            c_new = re.sub(r'app_version:\s*["\']v?[^"\']+["\']', f'app_version: "v{new_name}"', c)
            if c_new != c:
                js_path.write_text(c_new, encoding="utf-8")


def main():
    dry_run = "--dry-run" in sys.argv
    curr_name, curr_code = get_current_gradle_version()
    new_code = curr_code + 1

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

    if explicit_type:
        bump_type = explicit_type
        reason = f"Explicit flag --{explicit_type} passed"
    else:
        last_commit = run_git(["log", "-n", "1", "--pretty=format:%H", "--", "Tablet_Android_APK/app/build.gradle"])
        bump_type, reason = detect_change_type(last_commit)

    new_name = compute_new_version(curr_name, bump_type)

    type_labels = {
        "major": "1st digit * Major version overhaul",
        "module": "2nd digit * Functionality / module added",
        "even": "3rd digit (EVEN) * Bug fix & data model / SQL changes",
        "odd": "3rd digit (ODD) * Bug fix (utility / code only)",
        "same": "Keep versionName (versionCode bump only)",
    }

    print("=======================================================")
    print("       Office 3-Digit Versioning Auto-Detector         ")
    print("=======================================================")
    print(f" Detected Intent:  {type_labels.get(bump_type, bump_type)}")
    print(f" Reason:           {reason}")
    print(f" Version Name:     {curr_name} -> {new_name}")
    print(f" Version Code:     {curr_code} -> {new_code}")
    print("=======================================================")

    if not dry_run:
        apply_version(new_name, new_code)
        print(" [OK] build.gradle and api.js updated successfully.")
    else:
        print(" [DRY-RUN] No files were modified.")


if __name__ == "__main__":
    main()
