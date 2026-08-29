#!/usr/bin/env bash
# ============================================================================
# Jayraldine's Catering — Kiosk PWA — Installer / Package Builder (Linux/macOS)
# Automatically increments version and builds the server package.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================================"
echo "  JAYRALDINE'S CATERING KIOSK SERVER - AUTO-INCREMENT BUILDER"
echo "============================================================================"

# Locate Python interpreter (prefer Conda environment or active Python)
PY=""
if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
    PY="$CONDA_PREFIX/bin/python"
elif [ -x "$HOME/miniconda3/envs/jayraldines_tablet/bin/python" ]; then
    PY="$HOME/miniconda3/envs/jayraldines_tablet/bin/python"
elif [ -x "$HOME/miniconda3/bin/python" ]; then
    PY="$HOME/miniconda3/bin/python"
elif [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PY="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
fi

if [ -z "$PY" ]; then
    echo "[ERROR] python3 not found." >&2
    exit 1
fi

echo "==> Using Python: $PY"

# Ensure dependencies are installed
echo "==> Checking dependencies..."
"$PY" -m pip install -r "$SCRIPT_DIR/backend/requirements.txt" -q 2>/dev/null || "$PY" -m pip install -r "$SCRIPT_DIR/backend/requirements.txt"
"$PY" -m pip install pyinstaller -q 2>/dev/null || "$PY" -m pip install pyinstaller

echo ""
echo "==> Running installer build..."
"$PY" "$SCRIPT_DIR/build_installer.py" "$@"
