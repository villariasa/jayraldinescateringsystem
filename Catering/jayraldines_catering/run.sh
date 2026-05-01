#!/usr/bin/env bash
cd "$(dirname "$(readlink -f "$0")")"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PYSTAND="$HOME/.local/pystand/bin/python3"
PYTHON="$PYSTAND"

export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=villarias
export DB_PASSWORD=12345678

# Start PostgreSQL if not running (in background so app starts faster)
PG_CTL_BIN="pg_ctl"
PG_DATA_DIR="/home/villarias/.local/pgsql_data"
if [ -f "$PG_CTL_BIN" ] && ! "$PG_CTL_BIN" status -D "$PG_DATA_DIR" &>/dev/null; then
    "$PG_CTL_BIN" start -D "$PG_DATA_DIR" -l "$PG_DATA_DIR/logfile.log" &>/dev/null &
fi

# Cache PYSIDE6_DIR to avoid subprocess on every launch
PYSIDE6_CACHE="$SCRIPT_DIR/.pyside6_dir_cache"
if [ -f "$PYSIDE6_CACHE" ]; then
    PYSIDE6_DIR="$(cat "$PYSIDE6_CACHE")"
fi
if [ -z "$PYSIDE6_DIR" ] || [ ! -d "$PYSIDE6_DIR" ]; then
    PYSIDE6_DIR="$("$PYTHON" -c 'import PySide6,os; print(os.path.dirname(PySide6.__file__))' 2>/dev/null)"
    [ -n "$PYSIDE6_DIR" ] && echo "$PYSIDE6_DIR" > "$PYSIDE6_CACHE"
fi

XCBCURSOR_DIR="$HOME/.local/xcbcursor"
export QT_QPA_PLATFORM=xcb
export LD_LIBRARY_PATH="$XCBCURSOR_DIR:$PYSIDE6_DIR:$PYSIDE6_DIR/Qt/lib:$LD_LIBRARY_PATH"
export QT_PLUGIN_PATH="$PYSIDE6_DIR/Qt/plugins"

exec "$PYTHON" main.py
