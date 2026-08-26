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

EXTRA_ARGS=("-f" "--keep-deployment-files")

if [ -n "${PYSIDE6_ANDROID_WHEEL:-}" ]; then
    echo "==> Using PySide6 Android wheel: $PYSIDE6_ANDROID_WHEEL"
    EXTRA_ARGS+=("--wheel-pyside=$PYSIDE6_ANDROID_WHEEL")
fi

if [ -n "${SHIBOKEN6_ANDROID_WHEEL:-}" ]; then
    echo "==> Using Shiboken6 Android wheel: $SHIBOKEN6_ANDROID_WHEEL"
    EXTRA_ARGS+=("--wheel-shiboken=$SHIBOKEN6_ANDROID_WHEEL")
fi

if [ -n "${ANDROID_NDK_ROOT:-}" ]; then
    EXTRA_ARGS+=("--ndk-path=$ANDROID_NDK_ROOT")
else
    echo "INFO: ANDROID_NDK_ROOT not set. Using cached/default NDK if available."
fi

if [ -n "${ANDROID_SDK_ROOT:-}" ]; then
    EXTRA_ARGS+=("--sdk-path=$ANDROID_SDK_ROOT")
else
    echo "INFO: ANDROID_SDK_ROOT not set. Using cached/default SDK if available."
fi

echo "==> Installing Android-deploy Python dependencies"
ANDROID_REQS="$("$PY" -c 'import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), "scripts", "requirements-android.txt"))')"
"$PY" -m pip install -r "$ANDROID_REQS"

DEPLOY_EXE="$(dirname "$PY")/pyside6-android-deploy"
if [ ! -x "$DEPLOY_EXE" ]; then
    DEPLOY_EXE="pyside6-android-deploy"
fi

# Pre-clone & patch python-for-android hostpython3 recipe if needed
P4A_DIR="$APP_DIR/.buildozer/android/platform/python-for-android"
if [ ! -d "$P4A_DIR" ]; then
    mkdir -p "$APP_DIR/.buildozer/android/platform"
    git clone -b develop --single-branch https://github.com/kivy/python-for-android.git "$P4A_DIR"
fi

P4A_HOSTPYTHON_RECIPE="$P4A_DIR/pythonforandroid/recipes/hostpython3/__init__.py"
if [ -f "$P4A_HOSTPYTHON_RECIPE" ]; then
    "$PY" -c '
path = "'"$P4A_HOSTPYTHON_RECIPE"'"
with open(path, "r") as f:
    content = f.read()
modified = False
if "without-zstd" not in content:
    content = content.replace("self.local_dir,", "self.local_dir,\n                    \"--without-zstd\",")
    modified = True
if "jayraldines_tablet" not in content:
    target = "        return env"
    replacement = """        conda_dir = \"/home/villarias/miniconda3/envs/jayraldines_tablet\"
        if os.path.exists(join(conda_dir, \"include\", \"zlib.h\")):
            env[\"CPPFLAGS\"] = f\"-I{conda_dir}/include \" + env.get(\"CPPFLAGS\", \"\")
            env[\"CFLAGS\"] = f\"-I{conda_dir}/include \" + env.get(\"CFLAGS\", \"\")
            env[\"LDFLAGS\"] = f\"-L{conda_dir}/lib -lz -lzstd \" + env.get(\"LDFLAGS\", \"\")
            env[\"LD_LIBRARY_PATH\"] = f\"{conda_dir}/lib:\" + env.get(\"LD_LIBRARY_PATH\", \"\")
        return env"""
    content = content.replace(target, replacement, 1)
    modified = True
if modified:
    with open(path, "w") as f:
        f.write(content)
'
fi

echo "==> Building Android APK (this can take a long time on first run —"
echo "    it downloads/builds a Python-for-Android toolchain)"
"$DEPLOY_EXE" \
    --name "JayraldinesCateringTablet" \
    "${EXTRA_ARGS[@]}" \
    -c "$APP_DIR/pysidedeploy.spec"

echo "==> Done. Look for the generated .apk under $APP_DIR (path reported above)."
echo "    Install on a tablet with: adb install -r <path-to-apk>"
