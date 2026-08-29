#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APK_PROJECT_DIR="$SCRIPT_DIR/Tablet_Android_APK"
PWA_FRONTEND_DIR="$SCRIPT_DIR/Tablet_PWA/frontend"
OUTPUT_APK="$SCRIPT_DIR/jayraldines_catering.apk"

echo "======================================================="
echo "   Jayraldine's Catering — Standalone APK Builder     "
echo "======================================================="

# 1. Setup Android SDK Environment
if [ -z "$ANDROID_HOME" ]; then
    if [ -d "$HOME/.android-sdk" ]; then
        export ANDROID_HOME="$HOME/.android-sdk"
    elif [ -d "$HOME/Android/Sdk" ]; then
        export ANDROID_HOME="$HOME/Android/Sdk"
    else
        echo "Error: Android SDK not found in \$HOME/.android-sdk or \$HOME/Android/Sdk"
        exit 1
    fi
fi

export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
echo "==> Using Android SDK: $ANDROID_HOME"

# 2. Sync latest frontend files to APK assets
echo "==> Syncing latest PWA frontend assets into APK..."
rm -rf "$APK_PROJECT_DIR/app/src/main/assets"/*
mkdir -p "$APK_PROJECT_DIR/app/src/main/assets"
cp -r "$PWA_FRONTEND_DIR"/* "$APK_PROJECT_DIR/app/src/main/assets/"

# 3. Build APK with Gradle
echo "==> Compiling APK with Gradle..."
cd "$APK_PROJECT_DIR"
chmod +x ./gradlew
./gradlew assembleDebug --no-daemon

# 4. Copy output APK to project root
if [ -f "$APK_PROJECT_DIR/app/build/outputs/apk/debug/app-debug.apk" ]; then
    cp "$APK_PROJECT_DIR/app/build/outputs/apk/debug/app-debug.apk" "$OUTPUT_APK"
    echo ""
    echo "======================================================="
    echo "  SUCCESS! APK Generated Successfully: "
    echo "  File: $OUTPUT_APK"
    ls -lh "$OUTPUT_APK"
    echo "======================================================="
else
    echo "Error: APK compilation failed."
    exit 1
fi
