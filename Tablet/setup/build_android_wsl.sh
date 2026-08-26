#!/usr/bin/env bash
# Jayraldine's Catering — Tablet App — ONE-SHOT Android APK builder for WSL2.
#
# Run this from inside a WSL2 Ubuntu terminal (not native Windows cmd/
# PowerShell — the Android build toolchain needs a real Linux environment).
# It installs every prerequisite (JDK, Android SDK/NDK, build tools, the
# PySide6 Android wheels) and produces the .apk, with no other manual steps.
#
# Usage (from anywhere, including a /mnt/c/... Windows path):
#   bash build_android_wsl.sh
#
# Needs your sudo password once (for apt installs) — that's the only prompt.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TABLET_SRC_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "  Jayraldine's Catering — Tablet — Android APK one-shot build"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. If we're running from a Windows-mounted path (/mnt/c/...), the Android
#    build needs real Unix symlinks/permissions that drvfs doesn't support —
#    copy the project into WSL2's native filesystem first and re-run there.
# ---------------------------------------------------------------------------
case "$TABLET_SRC_DIR" in
    /mnt/*)
        WORK_DIR="$HOME/tablet-build/Tablet"
        echo "==> Running from a Windows-mounted path ($TABLET_SRC_DIR)."
        echo "    Copying to $WORK_DIR (native Linux filesystem) first —"
        echo "    the Android build needs real Unix symlinks/permissions."
        mkdir -p "$HOME/tablet-build"
        rsync -a --delete \
            --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
            --exclude='.buildozer' --exclude='deployment' --exclude='build' \
            --exclude='dist' --exclude='installer_output' \
            "$TABLET_SRC_DIR/" "$WORK_DIR/"
        echo "==> Re-running from $WORK_DIR"
        exec bash "$WORK_DIR/setup/build_android_wsl.sh" "$@"
        ;;
esac

APP_DIR="$TABLET_SRC_DIR"
cd "$APP_DIR"

# ---------------------------------------------------------------------------
# 2. System packages (needs sudo — the one password prompt in this script).
# ---------------------------------------------------------------------------
echo "==> Installing system build dependencies (sudo password needed once)"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    openjdk-17-jdk build-essential autoconf automake libtool \
    pkg-config zlib1g-dev unzip git python3.11 python3.11-venv curl >/dev/null

JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")"
export JAVA_HOME
echo "==> JAVA_HOME=$JAVA_HOME"

# ---------------------------------------------------------------------------
# 3. Android SDK (cmdline-tools + platform-tools) + NDK r26b.
# ---------------------------------------------------------------------------
ANDROID_SDK_ROOT="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT
NDK_VERSION="26.1.10909125"
ANDROID_NDK_ROOT="$ANDROID_SDK_ROOT/ndk/$NDK_VERSION"
export ANDROID_NDK_ROOT

if [ ! -f "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]; then
    echo "==> Downloading Android SDK command-line tools"
    mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools"
    TMP_ZIP="$(mktemp)"
    curl -sL -o "$TMP_ZIP" "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
    unzip -q "$TMP_ZIP" -d "$ANDROID_SDK_ROOT/cmdline-tools"
    mv "$ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools" "$ANDROID_SDK_ROOT/cmdline-tools/latest"
    rm -f "$TMP_ZIP"
fi
SDKMGR="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager"

if [ ! -d "$ANDROID_NDK_ROOT" ] || [ ! -f "$ANDROID_SDK_ROOT/platform-tools/adb" ]; then
    echo "==> Installing Android SDK platform-tools + NDK $NDK_VERSION (accepting licenses)"
    yes | "$SDKMGR" --sdk_root="$ANDROID_SDK_ROOT" --licenses >/dev/null 2>&1 || true
    "$SDKMGR" --sdk_root="$ANDROID_SDK_ROOT" "platform-tools" "ndk;$NDK_VERSION"
fi

# Legacy path buildozer still expects.
if [ ! -f "$ANDROID_SDK_ROOT/tools/bin/sdkmanager" ]; then
    mkdir -p "$ANDROID_SDK_ROOT/tools/bin"
    ln -sf "$SDKMGR" "$ANDROID_SDK_ROOT/tools/bin/sdkmanager"
fi

# ---------------------------------------------------------------------------
# 4. Python 3.11 venv + app requirements.
# ---------------------------------------------------------------------------
if [ ! -x "$APP_DIR/.venv/bin/python3" ]; then
    echo "==> Creating Python 3.11 venv"
    python3.11 -m venv "$APP_DIR/.venv"
fi
PY="$APP_DIR/.venv/bin/python3"
echo "==> Installing app + PySide6 requirements"
"$PY" -m pip install --upgrade pip -q
"$PY" -m pip install -r requirements.txt -q
"$PY" -c "import PySide6" 2>/dev/null || "$PY" -m pip install -q PySide6

# ---------------------------------------------------------------------------
# 5. PySide6/shiboken6 Android target wheels (cross-compiled, same file
#    regardless of host OS — matches whatever PySide6 version just installed).
# ---------------------------------------------------------------------------
WHEEL_CACHE_DIR="$HOME/.cache/pyside6_wheels"
mkdir -p "$WHEEL_CACHE_DIR"
PYSIDE_VER="$("$PY" -c 'import PySide6; print(PySide6.__version__)')"
PYSIDE6_ANDROID_WHEEL="$WHEEL_CACHE_DIR/pyside6-$PYSIDE_VER-android_aarch64.whl"
SHIBOKEN6_ANDROID_WHEEL="$WHEEL_CACHE_DIR/shiboken6-$PYSIDE_VER-android_aarch64.whl"

if [ ! -f "$PYSIDE6_ANDROID_WHEEL" ]; then
    echo "==> Downloading PySide6 $PYSIDE_VER Android wheel"
    curl -sL -o "$PYSIDE6_ANDROID_WHEEL" \
        "https://download.qt.io/official_releases/QtForPython/pyside6/pyside6-$PYSIDE_VER-$PYSIDE_VER-cp311-cp311-android_aarch64.whl"
fi
if [ ! -f "$SHIBOKEN6_ANDROID_WHEEL" ]; then
    echo "==> Downloading shiboken6 $PYSIDE_VER Android wheel"
    curl -sL -o "$SHIBOKEN6_ANDROID_WHEEL" \
        "https://download.qt.io/official_releases/QtForPython/shiboken6/shiboken6-$PYSIDE_VER-$PYSIDE_VER-cp311-cp311-android_aarch64.whl"
fi
export PYSIDE6_ANDROID_WHEEL SHIBOKEN6_ANDROID_WHEEL

# ---------------------------------------------------------------------------
# 6. Hand off to the actual build (does the real compile — long step).
# ---------------------------------------------------------------------------
echo "==> Handing off to setup/build_android.sh for the actual APK build"
echo "    (first run compiles a full Python-for-Android toolchain — this"
echo "    can take 30-90+ minutes)"
bash "$APP_DIR/setup/build_android.sh"

APK="$(find "$APP_DIR" -maxdepth 1 -iname '*.apk' | head -n 1)"
if [ -n "$APK" ]; then
    echo "============================================================"
    echo "  DONE. APK: $APK"
    echo "============================================================"
    if command -v "$ANDROID_SDK_ROOT/platform-tools/adb" >/dev/null 2>&1 || [ -x "$ANDROID_SDK_ROOT/platform-tools/adb" ]; then
        if "$ANDROID_SDK_ROOT/platform-tools/adb" get-state >/dev/null 2>&1; then
            echo "==> Tablet detected over adb — installing now"
            "$ANDROID_SDK_ROOT/platform-tools/adb" install -r "$APK"
        else
            echo "    No tablet detected via adb yet. Plug it in (USB debugging"
            echo "    enabled), then run:"
            echo "      $ANDROID_SDK_ROOT/platform-tools/adb install -r \"$APK\""
        fi
    fi
fi
