#!/usr/bin/env bash
cd "$(dirname "$(readlink -f "$0")")"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PYSTAND="$HOME/.local/pystand/bin/python3"
PYTHON="$PYSTAND"

export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=villarias
export DB_PASSWORD=12345678

# Start PostgreSQL if not running
PG_CTL_BIN="pg_ctl"
PG_DATA_DIR="/home/villarias/.local/pgsql_data"
if [ -f "$PG_CTL_BIN" ] && ! "$PG_CTL_BIN" status -D "$PG_DATA_DIR" &>/dev/null; then
    echo "Starting PostgreSQL..."
    "$PG_CTL_BIN" start -D "$PG_DATA_DIR" -l "$PG_DATA_DIR/logfile.log" -w &>/dev/null
    sleep 1
fi

# Set up xcb lib path
XCBCURSOR_DIR="$HOME/.local/xcbcursor"
PYSIDE6_DIR="$($PYTHON -c 'import PySide6,os; print(os.path.dirname(PySide6.__file__))' 2>/dev/null)"
export QT_QPA_PLATFORM=xcb
export LD_LIBRARY_PATH="$XCBCURSOR_DIR:$PYSIDE6_DIR:$PYSIDE6_DIR/Qt/lib:$LD_LIBRARY_PATH"
export QT_PLUGIN_PATH="$PYSIDE6_DIR/Qt/plugins"

"$PYTHON" main.py
