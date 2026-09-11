"""
Standalone Tablet APK Installer Builder for Jayraldine's Catering System.
Builds the Android APK with Gradle, embeds the latest PWA frontend assets,
and produces versioned APK outputs (e.g. jayraldines_catering_v1.26.0.apk).

Usage:
  python build_tablet_installer.py [--version 1.26.0] [--non-interactive]
"""

import os
import re
import sys
import shutil
import datetime
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APK_DIR = ROOT / "Tablet_Android_APK"
GRADLE_BUILD = APK_DIR / "app" / "build.gradle"
FRONTEND_DIR = ROOT / "Tablet_PWA" / "frontend"
ASSETS_DIR = APK_DIR / "app" / "src" / "main" / "assets"


def get_current_tablet_version() -> tuple[str, int]:
    """Extracts (versionName, versionCode) from Tablet_Android_APK/app/build.gradle."""
    if not GRADLE_BUILD.exists():
        return "1.26.0", 26

    content = GRADLE_BUILD.read_text(encoding="utf-8")
    name_match = re.search(r'versionName\s+["\']([^"\']+)["\']', content)
    code_match = re.search(r'versionCode\s+(\d+)', content)

    ver_name = name_match.group(1) if name_match else "1.26.0"
    ver_code = int(code_match.group(1)) if code_match else 26
    return ver_name, ver_code


def update_tablet_version(new_version: str) -> str:
    """Updates versionName and auto-increments versionCode in build.gradle."""
    new_version = new_version.strip()
    curr_name, curr_code = get_current_tablet_version()

    if not new_version:
        new_version = curr_name

    new_code = curr_code + 1 if new_version != curr_name else curr_code

    content = GRADLE_BUILD.read_text(encoding="utf-8")
    content = re.sub(r'versionName\s+["\'][^"\']+["\']', f'versionName "{new_version}"', content)
    content = re.sub(r'versionCode\s+\d+', f'versionCode {new_code}', content)

    GRADLE_BUILD.write_text(content, encoding="utf-8")
    print(f"  [OK] Updated Tablet build.gradle -> versionName \"{new_version}\", versionCode {new_code}")
    return new_version


def find_android_sdk() -> str:
    """Finds Android SDK path from env or standard Windows locations."""
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk and Path(sdk).exists():
        return sdk

    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk"),
        r"C:\Android\Sdk",
    ]
    for c in candidates:
        if Path(c).exists():
            return c

    return ""


def main():
    print("=" * 65)
    print("   JAYRALDINE'S CATERING — TABLET APK INSTALLER BUILDER")
    print("=" * 65)

    curr_ver, curr_code = get_current_tablet_version()

    # Parse arguments or prompt
    target_ver = None
    interactive = True

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("--version", "-v") and i + 1 < len(args):
            target_ver = args[i + 1]
            interactive = False
            i += 2
        elif args[i] in ("--non-interactive", "--batch", "-y"):
            interactive = False
            i += 1
        elif not args[i].startswith("-"):
            target_ver = args[i]
            interactive = False
            i += 1
        else:
            i += 1

    if interactive:
        try:
            print(f"\n  Current Tablet Version : v{curr_ver} (code: {curr_code})")
            user_input = input(f"  Enter version to build [Press Enter for {curr_ver}]: ").strip()
            if user_input:
                target_ver = user_input
            else:
                target_ver = curr_ver
        except (KeyboardInterrupt, EOFError):
            print("\nBuild cancelled.")
            sys.exit(0)
    elif not target_ver:
        target_ver = curr_ver

    version = update_tablet_version(target_ver)

    # 1. Locate Android SDK
    sdk = find_android_sdk()
    if not sdk:
        print("\n[ERROR] Android SDK not found! Please set ANDROID_HOME or install Android Studio.")
        sys.exit(1)

    os.environ["ANDROID_HOME"] = sdk
    print(f"\n[1/4] Android SDK found at: {sdk}")

    # 2. Sync PWA frontend assets into APK
    print("[2/4] Syncing latest PWA frontend assets into APK...")
    if not FRONTEND_DIR.exists():
        print(f"[ERROR] Frontend directory not found: {FRONTEND_DIR}")
        sys.exit(1)

    if ASSETS_DIR.exists():
        shutil.rmtree(ASSETS_DIR, ignore_errors=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    for item in FRONTEND_DIR.glob("**/*"):
        if item.is_file():
            rel = item.relative_to(FRONTEND_DIR)
            target = ASSETS_DIR / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            copied += 1
    print(f"  [OK] Synchronized {copied} assets into APK.")

    # 3. Clean old APK build outputs to prevent stale files
    apk_out_dir = APK_DIR / "app" / "build" / "outputs" / "apk" / "debug"
    old_debug_apk = apk_out_dir / "app-debug.apk"
    if old_debug_apk.exists():
        try:
            old_debug_apk.unlink()
        except Exception:
            pass

    # 4. Compile APK with Gradle
    print("[3/4] Compiling fresh APK with Gradle (clean assembleDebug)...")
    gradlew = APK_DIR / "gradlew.bat"
    if not gradlew.exists():
        print(f"[ERROR] gradlew.bat not found in: {APK_DIR}")
        sys.exit(1)

    cmd = [str(gradlew), "clean", "assembleDebug", "--no-daemon"]
    build_start = datetime.datetime.now()
    res = subprocess.run(cmd, cwd=str(APK_DIR))

    if res.returncode != 0:
        print("\n[ERROR] Gradle APK build failed! Check errors above.")
        sys.exit(res.returncode)

    # 5. Verify and Copy Versioned APK
    print("[4/4] Finalizing APK package outputs...")
    if not old_debug_apk.exists():
        print(f"[ERROR] Build succeeded but APK was not found at: {old_debug_apk}")
        sys.exit(1)

    versioned_apk = ROOT / f"jayraldines_catering_v{version}.apk"
    universal_apk = ROOT / "jayraldines_catering.apk"

    shutil.copy2(old_debug_apk, versioned_apk)
    shutil.copy2(old_debug_apk, universal_apk)

    # Also copy to installer_output if it exists
    installer_out = ROOT / "Catering_Present" / "jayraldines_catering" / "installer_output"
    if installer_out.exists():
        shutil.copy2(old_debug_apk, installer_out / f"jayraldines_catering_v{version}.apk")

    # Touch modified time to current time so File Explorer reflects right now
    now_ts = datetime.datetime.now().timestamp()
    os.utime(versioned_apk, (now_ts, now_ts))
    os.utime(universal_apk, (now_ts, now_ts))

    size_mb = versioned_apk.stat().st_size / (1024 * 1024)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "=" * 65)
    print("  TABLET APK BUILD SUCCESSFUL!")
    print("=" * 65)
    print(f"  Versioned APK : {versioned_apk.name}")
    print(f"  Full Path     : {versioned_apk}")
    print(f"  Universal APK : {universal_apk.name}")
    print(f"  Version       : v{version}")
    print(f"  File Size     : {size_mb:.2f} MB")
    print(f"  Build Date    : {now_str}")
    print("=" * 65)
    print(f"\nDone! You can now install '{versioned_apk.name}' on your Android tablet.\n")


if __name__ == "__main__":
    main()
