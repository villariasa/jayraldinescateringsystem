#!/usr/bin/env bash
# One-command Android APK build for THIS specific machine (litecloud's
# account) — reuses the toolchain already set up here (JDK, Android SDK/NDK,
# Android target wheels, patched buildozer, local zlib/autotools) instead of
# requiring them to be installed system-wide.
#
# Usage:
#   bash setup/build_android_here.sh
#
# Builds from the project's own Tablet/ folder in a local working copy
# (~/tablet-build/Tablet) since the native build needs real Unix symlinks/
# permissions that the SMB-mounted project folder doesn't support, then
# copies the finished .apk back into Tablet/dist/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_TABLET_DIR="$(dirname "$SCRIPT_DIR")"
WORK_DIR="$HOME/tablet-build/Tablet"

echo "==> Syncing latest source into $WORK_DIR"
mkdir -p "$HOME/tablet-build"
rsync -a --delete \
    --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.buildozer' --exclude='deployment' --exclude='build' \
    --exclude='dist' --exclude='installer_output' --exclude='.git' \
    "$PROJECT_TABLET_DIR/" "$WORK_DIR/"

if [ ! -x "$WORK_DIR/.venv/bin/python3" ]; then
    echo "==> No venv found at $WORK_DIR/.venv, creating one"
    python3.11 -m venv "$WORK_DIR/.venv"
    "$WORK_DIR/.venv/bin/pip" install --upgrade pip -q
    "$WORK_DIR/.venv/bin/pip" install -r "$WORK_DIR/requirements.txt" -q
fi

export JAVA_HOME="$HOME/android-toolchain/jdk17"
export PATH="$WORK_DIR/.venv/bin:$JAVA_HOME/bin:$HOME/android-toolchain/autotools-local/bin:$PATH"
export PYTHONPATH="$HOME/tablet-build/vendor"
export CPATH="$HOME/android-toolchain/zlib-local/include"
export LIBRARY_PATH="$HOME/android-toolchain/zlib-local/lib"
export ANDROID_SDK_ROOT="$HOME/Android/Sdk"
export ANDROID_NDK_ROOT="$HOME/Android/Sdk/ndk/25.2.9519653"
export PYSIDE6_ANDROID_WHEEL="$HOME/android-toolchain/wheels/pyside6-android-aarch64.whl"
export SHIBOKEN6_ANDROID_WHEEL="$HOME/android-toolchain/wheels/shiboken6-android-aarch64.whl"

for req in "$JAVA_HOME/bin/javac" "$ANDROID_NDK_ROOT/ndk-build" "$PYSIDE6_ANDROID_WHEEL" "$SHIBOKEN6_ANDROID_WHEEL"; do
    if [ ! -e "$req" ]; then
        echo "ERROR: expected toolchain file missing: $req" >&2
        echo "       This wrapper assumes the toolchain already set up on this" >&2
        echo "       machine earlier — on a different machine, use setup/build_android.sh" >&2
        echo "       directly and follow its prerequisites comment block instead." >&2
        exit 1
    fi
done

cd "$WORK_DIR"

# build_android.sh passes --keep-deployment-files, which makes the deploy
# tool relocate .buildozer (the native compile cache — OpenSSL/Python/
# libffi/etc built for Android, ~4GB) into deployment/.buildozer after
# every successful build instead of leaving it in place. Without restoring
# it first, every single run recompiles all of that from scratch (30-90+
# min) even though nothing native-level changed. Put it back before building
# so only what actually changed (app Python source, mainly) gets rebuilt.
if [ -d "$WORK_DIR/deployment/.buildozer" ] && [ ! -d "$WORK_DIR/.buildozer" ]; then
    echo "==> Restoring native compile cache from deployment/.buildozer (~4GB, avoids a from-scratch rebuild)"
    mv "$WORK_DIR/deployment/.buildozer" "$WORK_DIR/.buildozer"
fi

echo "==> Building APK (native compile step — can take a while on the first"
echo "    run after a cache wipe, much faster if .buildozer is still warm)"
bash setup/build_android.sh

APK_PATH="$(find "$WORK_DIR" -maxdepth 2 -iname '*.apk' | head -n 1)"
if [ -z "$APK_PATH" ]; then
    echo "ERROR: build finished but no .apk was found under $WORK_DIR." >&2
    exit 1
fi

mkdir -p "$PROJECT_TABLET_DIR/dist"
cp "$APK_PATH" "$PROJECT_TABLET_DIR/dist/"
echo "============================================================"
echo "  DONE: $PROJECT_TABLET_DIR/dist/$(basename "$APK_PATH")"
echo "============================================================"
