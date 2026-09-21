#!/usr/bin/env bash
cd "$(dirname "$(readlink -f "$0")")"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
if [ -x "$HOME/.local/pystand/bin/python3" ]; then
    PYTHON="$HOME/.local/pystand/bin/python3"
elif [ -x "$HOME/miniconda3/envs/catering_env/bin/python" ]; then
    PYTHON="$HOME/miniconda3/envs/catering_env/bin/python"
elif [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
    PYTHON="$CONDA_PREFIX/bin/python"
else
    PYTHON="$(command -v python3)"
fi

# Default to SQLite using the shared ~/.jayraldines_catering/data/catering.db database
export DB_ENGINE="${DB_ENGINE:-sqlite}"
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-jayraldines_catering}"
export DB_USER="${DB_USER:-villarias}"
export DB_PASSWORD="${DB_PASSWORD:-12345678}"

# Start PostgreSQL only if explicitly requested
if [ "$DB_ENGINE" = "postgres" ]; then
    PG_CTL_BIN="/home/villarias/pgsql/bin/pg_ctl"
    PG_DATA_DIR="/home/villarias/.local/pgsql_data"
    if [ -x "$PG_CTL_BIN" ] && ! "$PG_CTL_BIN" status -D "$PG_DATA_DIR" &>/dev/null; then
        echo "Starting PostgreSQL..."
        "$PG_CTL_BIN" start -D "$PG_DATA_DIR" -l "$PG_DATA_DIR/logfile.log" -w &>/dev/null
        sleep 1
    fi
fi

# Set up xcb lib path
XCBCURSOR_DIR="$HOME/.local/xcbcursor"
PYSIDE6_DIR="$($PYTHON -c 'import PySide6,os; print(os.path.dirname(PySide6.__file__))' 2>/dev/null)"
export QT_QPA_PLATFORM=xcb
export LD_LIBRARY_PATH="$XCBCURSOR_DIR:$PYSIDE6_DIR:$PYSIDE6_DIR/Qt/lib:$LD_LIBRARY_PATH"
export QT_PLUGIN_PATH="$PYSIDE6_DIR/Qt/plugins"

"$PYTHON" main.py
