#!/usr/bin/env bash
# Jayraldine's Catering — Standalone Kiosk PWA — Local Launcher
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PY=""
if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
    PY="$CONDA_PREFIX/bin/python"
elif [ -x "$HOME/miniconda3/bin/python" ]; then
    PY="$HOME/miniconda3/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")"

echo "============================================================================"
echo "  JAYRALDINE'S CATERING — STANDALONE KIOSK PWA"
echo "============================================================================"
echo "  Local PC URL:   http://localhost:$PORT"
echo "  Tablet LAN URL: http://$LAN_IP:$PORT"
echo "============================================================================"
echo "  Open http://localhost:$PORT in any web browser to use it."
echo "  Press Ctrl+C to stop."
echo "============================================================================"

exec "$PY" -m http.server "$PORT" --bind "$HOST" --directory "$SCRIPT_DIR/frontend"
