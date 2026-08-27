#!/usr/bin/env bash
# Jayraldine's Catering — Tablet App — Android APK build script.
#
# Wraps PySide6's official `pyside6-android-deploy` tool. This produces an
# installable .apk you can side-load onto an Android tablet.
#
# ── One-time prerequisites (outside this script, on the build machine) ──
#   1. Android SDK + NDK installed (Android Studio's SDK Manager is the
#      easiest way, or the standalone `sdkmanager` command-line tools).
#   2. A JDK (Java 17 recommended for recent Android Gradle Plugin versions).
#   3. Environment variables set before running this script:
#        export ANDROID_SDK_ROOT=/path/to/Android/sdk
#        export ANDROID_NDK_ROOT=/path/to/Android/sdk/ndk/<version>
#        export JAVA_HOME=/path/to/jdk-17
#   4. The Python venv from setup_linux.sh already created (this script
#      reuses it), with the extra Android deploy dependencies installed:
#        pip install -r "$(python3 -c 'import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), "scripts", "requirements-android.txt"))')"
#
# Consult Qt's official "Deploying to Android" documentation for the exact
# PySide6 version you have installed — the deploy tool's CLI flags have
# changed between minor Qt releases, so treat the flags below as a
# starting point and adjust to match `pyside6-android-deploy --help` output
# for your installed version.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$APP_DIR/.venv"
CONDA_ENV_NAME="jayraldines_tablet"

cd "$APP_DIR"

# Locate the same interpreter setup_linux.sh creates (prefer conda env if present, else .venv)
PY=""
if command -v conda >/dev/null 2>&1; then
    CONDA_BASE="$(conda info --base 2>/dev/null || true)"
    if [ -n "$CONDA_BASE" ] && [ -x "$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python3" ]; then
        PY="$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python3"
    fi
fi
if [ -z "$PY" ]; then
    if [ -x "$VENV_DIR/bin/python3" ]; then
        PY="$VENV_DIR/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        PY="$(command -v python3)"
    fi
fi

if [ -z "$PY" ]; then
    echo "ERROR: no suitable Python environment found. Run setup/setup_linux.sh first." >&2
    exit 1
fi

echo "==> Using interpreter: $PY"
export PATH="$(dirname "$PY"):$PATH"

# python-for-android/buildozer refuses to run on Python 3.12+ ("Android
# deployment requires Python version 3.11 or lower"). setup_linux.sh's venv
# is created from whatever python3 resolves to, which may already be 3.12+
# on a newer distro — check here with a clear error instead of failing deep
# inside a buildozer stack trace after the SDK/NDK download has run.
PYVER_CHECK=$("$PY" -c 'import sys; print(1 if sys.version_info[:2] <= (3, 11) else 0)')
if [ "$PYVER_CHECK" != "1" ]; then
    echo "ERROR: this environment's Python is too new for the Android build" >&2
    echo "       (python-for-android requires Python 3.11 or lower). Install" >&2
    echo "       Python 3.11, recreate the venv with it (e.g. python3.11 -m venv .venv)," >&2
    echo "       and re-run this script." >&2
    exit 1
fi

# Auto-detect Android SDK & NDK if not manually set
if [ -z "${ANDROID_SDK_ROOT:-}" ]; then
    for candidate in "$HOME/.buildozer/android/platform/android-sdk" "$HOME/Android/Sdk" "$HOME/Android/sdk" "/usr/lib/android-sdk" "/opt/android-sdk"; do
        if [ -d "$candidate" ]; then
            export ANDROID_SDK_ROOT="$candidate"
            export ANDROIDSDK="$candidate"
            break
        fi
    done
fi

if [ -z "${ANDROID_NDK_ROOT:-}" ]; then
    if [ -n "${ANDROID_SDK_ROOT:-}" ]; then
        for candidate in "$ANDROID_SDK_ROOT/ndk"/* "$ANDROID_SDK_ROOT/ndk-bundle"; do
            if [ -d "$candidate" ]; then
                export ANDROID_NDK_ROOT="$candidate"
                break
            fi
        done
    fi
    if [ -z "${ANDROID_NDK_ROOT:-}" ]; then
        CACHE_NDK=$(find "$HOME/.pyside6_android_deploy/android-ndk" -maxdepth 2 -name "android-ndk-r*" -type d 2>/dev/null | head -n 1 || true)
        if [ -n "$CACHE_NDK" ]; then
            export ANDROID_NDK_ROOT="$CACHE_NDK"
        fi
    fi
    if [ -z "${ANDROID_NDK_ROOT:-}" ]; then
        echo "==> ANDROID_NDK_ROOT not found. Auto-downloading Android NDK r25b (~600MB)..."
        NDK_DIR="$HOME/Android/Sdk/ndk/25.2.9519653"
        mkdir -p "$HOME/Android/Sdk/ndk"
        if curl -sL --fail -o /tmp/ndk.zip "https://dl.google.com/android/repository/android-ndk-r25b-linux.zip"; then
            unzip -q -o /tmp/ndk.zip -d "$HOME/Android/Sdk/ndk"
            [ -d "$HOME/Android/Sdk/ndk/android-ndk-r25b" ] && mv "$HOME/Android/Sdk/ndk/android-ndk-r25b" "$NDK_DIR"
            rm -f /tmp/ndk.zip
            export ANDROID_NDK_ROOT="$NDK_DIR"
            echo "==> Android NDK r25b installed to $NDK_DIR"
        fi
    fi
fi

# Auto-detect PySide6 & Shiboken6 Android wheels if not explicitly set
WHEEL_CACHE_DIR="$HOME/.cache/pyside6_wheels"
if [ -z "${PYSIDE6_ANDROID_WHEEL:-}" ]; then
    PYSIDE_MATCH=$(find "$WHEEL_CACHE_DIR" "$APP_DIR" -name "PySide6*android*.whl" 2>/dev/null | head -n 1 || true)
    if [ -n "$PYSIDE_MATCH" ]; then
        export PYSIDE6_ANDROID_WHEEL="$PYSIDE_MATCH"
    fi
fi

if [ -z "${SHIBOKEN6_ANDROID_WHEEL:-}" ]; then
    SHIBOKEN_MATCH=$(find "$WHEEL_CACHE_DIR" "$APP_DIR" -name "shiboken6*android*.whl" 2>/dev/null | head -n 1 || true)
    if [ -n "$SHIBOKEN_MATCH" ]; then
        export SHIBOKEN6_ANDROID_WHEEL="$SHIBOKEN_MATCH"
    fi
fi

PYSIDE_VER="$("$PY" -c 'import PySide6; print(PySide6.__version__)')"
WHEEL_ARCH="${TABLET_TARGET_ARCH:-android_aarch64}"
[ "$WHEEL_ARCH" = "x86_64" ] && WHEEL_ARCH="android_x86_64"

# Auto-download the two Android target wheels if not already cached — these
# are cross-compiled wheels (same file regardless of host OS), safe to fetch
# automatically instead of making the user run curl by hand.
if [ -z "${PYSIDE6_ANDROID_WHEEL:-}" ]; then
    mkdir -p "$WHEEL_CACHE_DIR"
    PYSIDE6_ANDROID_WHEEL="$WHEEL_CACHE_DIR/pyside6-$PYSIDE_VER-$WHEEL_ARCH.whl"
    echo "==> Downloading PySide6 $PYSIDE_VER Android wheel (~80MB, one-time)..."
    if ! curl -sL --fail -o "$PYSIDE6_ANDROID_WHEEL" \
        "https://download.qt.io/official_releases/QtForPython/pyside6/pyside6-$PYSIDE_VER-$PYSIDE_VER-cp311-cp311-$WHEEL_ARCH.whl"; then
        rm -f "$PYSIDE6_ANDROID_WHEEL"
        echo "ERROR: download failed. Check your internet connection, or manually grab it" >&2
        echo "       from https://download.qt.io/official_releases/QtForPython/pyside6/" >&2
        echo "       and save it into $WHEEL_CACHE_DIR." >&2
        exit 1
    fi
    export PYSIDE6_ANDROID_WHEEL
fi
if [ -z "${SHIBOKEN6_ANDROID_WHEEL:-}" ]; then
    mkdir -p "$WHEEL_CACHE_DIR"
    SHIBOKEN6_ANDROID_WHEEL="$WHEEL_CACHE_DIR/shiboken6-$PYSIDE_VER-$WHEEL_ARCH.whl"
    echo "==> Downloading shiboken6 $PYSIDE_VER Android wheel (one-time)..."
    if ! curl -sL --fail -o "$SHIBOKEN6_ANDROID_WHEEL" \
        "https://download.qt.io/official_releases/QtForPython/shiboken6/shiboken6-$PYSIDE_VER-$PYSIDE_VER-cp311-cp311-$WHEEL_ARCH.whl"; then
        rm -f "$SHIBOKEN6_ANDROID_WHEEL"
        echo "ERROR: download failed. Check your internet connection, or manually grab it" >&2
        echo "       from https://download.qt.io/official_releases/QtForPython/shiboken6/" >&2
        echo "       and save it into $WHEEL_CACHE_DIR." >&2
        exit 1
    fi
    export SHIBOKEN6_ANDROID_WHEEL
fi

EXTRA_ARGS=("-f" "--keep-deployment-files")
echo "==> Using PySide6 Android wheel: $PYSIDE6_ANDROID_WHEEL"
EXTRA_ARGS+=("--wheel-pyside=$PYSIDE6_ANDROID_WHEEL")
echo "==> Using Shiboken6 Android wheel: $SHIBOKEN6_ANDROID_WHEEL"
EXTRA_ARGS+=("--wheel-shiboken=$SHIBOKEN6_ANDROID_WHEEL")

if [ -z "${ANDROID_NDK_ROOT:-}" ]; then
    echo "ERROR: ANDROID_NDK_ROOT must be set. See the prerequisites comment" >&2
    echo "       block at the top of this script." >&2
    exit 1
fi
EXTRA_ARGS+=("--ndk-path=$ANDROID_NDK_ROOT")

if [ -z "${ANDROID_SDK_ROOT:-}" ]; then
    echo "ERROR: ANDROID_SDK_ROOT must be set. See the prerequisites comment" >&2
    echo "       block at the top of this script." >&2
    exit 1
fi
EXTRA_ARGS+=("--sdk-path=$ANDROID_SDK_ROOT")

# buildozer still expects the legacy "tools/bin/sdkmanager" layout that
# Google dropped from newer cmdline-tools distributions (which only ship
# "cmdline-tools/latest/bin/sdkmanager"). Shim it if missing.
if [ ! -f "$ANDROID_SDK_ROOT/tools/bin/sdkmanager" ] && [ -f "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]; then
    mkdir -p "$ANDROID_SDK_ROOT/tools/bin"
    ln -sf "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" "$ANDROID_SDK_ROOT/tools/bin/sdkmanager"
    ln -sf "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/avdmanager" "$ANDROID_SDK_ROOT/tools/bin/avdmanager" 2>/dev/null || true
fi

# Ensure pip inside buildozer/p4a does not fail with --user in virtual environment
unset PIP_USER || true
unset PIP_NO_USER || true
VENV_DIR_ROOT="$(dirname "$(dirname "$PY")")"
export VIRTUAL_ENV="$VENV_DIR_ROOT"
if [ -f "$VENV_DIR_ROOT/pyvenv.cfg" ]; then
    if grep -q "include-system-site-packages = false" "$VENV_DIR_ROOT/pyvenv.cfg"; then
        sed -i 's/include-system-site-packages = false/include-system-site-packages = true/' "$VENV_DIR_ROOT/pyvenv.cfg" || true
    fi
fi

echo "==> Installing Android-deploy Python dependencies"
ANDROID_REQS="$("$PY" -c 'import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), "scripts", "requirements-android.txt"))' 2>/dev/null || true)"
if [ -n "$ANDROID_REQS" ] && [ -f "$ANDROID_REQS" ]; then
    "$PY" -m pip install -r "$ANDROID_REQS" || true
else
    "$PY" -m pip install "buildozer>=1.5.0" "cython<3.0.0" || true
fi

DEPLOY_EXE="$(dirname "$PY")/pyside6-android-deploy"
if [ ! -x "$DEPLOY_EXE" ]; then
    DEPLOY_EXE="pyside6-android-deploy"
fi

# Pre-clone & patch python-for-android hostpython3 recipe if needed: some
# distros/hosts don't ship a system zstd, which the hostpython3 recipe's
# default config assumes. --without-zstd is always safe to add. The zlib
# include/lib path injection below only kicks in if zlib.h isn't already
# on the system include path (e.g. a rootless build machine using a local
# zlib build via CPATH/LIBRARY_PATH) — on a normal machine with
# zlib1g-dev/zlib-devel installed this is a no-op.
P4A_DIR="$APP_DIR/.buildozer/android/platform/python-for-android"
if [ ! -d "$P4A_DIR" ]; then
    mkdir -p "$APP_DIR/.buildozer/android/platform"
    git clone -b develop --single-branch https://github.com/kivy/python-for-android.git "$P4A_DIR"
fi

P4A_HOSTPYTHON_RECIPE="$P4A_DIR/pythonforandroid/recipes/hostpython3/__init__.py"
if [ -f "$P4A_HOSTPYTHON_RECIPE" ]; then
    ZLIB_INCLUDE_DIR="" ZLIB_LIB_DIR=""
    if [ ! -f "/usr/include/zlib.h" ]; then
        for p in ${CPATH:-} ""; do
            if [ -n "$p" ] && [ -f "$p/zlib.h" ]; then ZLIB_INCLUDE_DIR="$p"; break; fi
        done
        for p in ${LIBRARY_PATH:-} ""; do
            if [ -n "$p" ] && ls "$p"/libz.* >/dev/null 2>&1; then ZLIB_LIB_DIR="$p"; break; fi
        done
    fi
    ZLIB_INCLUDE_DIR="$ZLIB_INCLUDE_DIR" ZLIB_LIB_DIR="$ZLIB_LIB_DIR" "$PY" -c '
import os
path = "'"$P4A_HOSTPYTHON_RECIPE"'"
zlib_include = os.environ.get("ZLIB_INCLUDE_DIR", "")
zlib_lib = os.environ.get("ZLIB_LIB_DIR", "")
with open(path, "r") as f:
    content = f.read()
modified = False
if "without-zstd" not in content:
    content = content.replace("self.local_dir,", "self.local_dir,\n                    \"--without-zstd\",")
    modified = True
if zlib_include and zlib_lib and "JAYRALDINES_LOCAL_ZLIB" not in content:
    target = "        return env"
    replacement = f"""        # JAYRALDINES_LOCAL_ZLIB: rootless build machine without system zlib headers
        zlib_include, zlib_lib = {zlib_include!r}, {zlib_lib!r}
        env["CPPFLAGS"] = f"-I{{zlib_include}} " + env.get("CPPFLAGS", "")
        env["CFLAGS"] = f"-I{{zlib_include}} " + env.get("CFLAGS", "")
        env["LDFLAGS"] = f"-L{{zlib_lib}} -lz " + env.get("LDFLAGS", "")
        env["LD_LIBRARY_PATH"] = f"{{zlib_lib}}:" + env.get("LD_LIBRARY_PATH", "")
        return env"""
    content = content.replace(target, replacement, 1)
    modified = True
if modified:
    with open(path, "w") as f:
        f.write(content)
'
fi

# Deliberately NOT passing -c pysidedeploy.spec here: that file in this
# project was hand-edited with another developer's machine-specific
# absolute paths (wheel locations, a conda env path) that don't exist on
# other machines. Passing all values explicitly via CLI flags (EXTRA_ARGS,
# built up above) avoids silently falling back to those stale paths.
echo "==> Building Android APK (this can take a long time on first run —"
echo "    it downloads/builds a Python-for-Android toolchain)"
"$DEPLOY_EXE" \
    --name "Jayraldines Catering" \
    "${EXTRA_ARGS[@]}"

echo "==> Done. Look for the generated .apk under $APP_DIR (path reported above)."
echo "    Install on a tablet with: adb install -r <path-to-apk>"
