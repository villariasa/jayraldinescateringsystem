#!/usr/bin/env bash
# Quick shortcut script to build the Android APK for Jayraldine's Catering Tablet.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/setup/build_android.sh" "$@"
