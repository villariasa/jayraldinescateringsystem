#!/usr/bin/env bash
# ==============================================================================
#  Jayraldine's Catering - Linux Setup Script (no sudo required)
#  Ubuntu 22.04 / 24.04
#
#  Usage:
#    chmod +x setup_linux.sh
#    ./setup_linux.sh
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PG_VERSION="16"
PG_DIR="$HOME/.local/pgsql"
PG_DATA="$HOME/.local/pgsql_data"
PG_PORT="5432"
PG_USER="$(whoami)"
DB_NAME="jayraldines_catering"
PG_TARBALL_URL="https://sbp.enterprisedb.com/getfile.jsp?fileid=1259018"
PG_TARBALL="$HOME/.local/pgsql16-linux.tar.gz"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  [OK]${NC} $1"; }
info() { echo -e "${YELLOW}  [..]${NC} $1"; }
fail() { echo -e "${RED}  [!!]${NC} $1"; }
skip() { echo -e "${GRAY}  [--]${NC} $1"; }
step() { echo -e "\n${CYAN}===================================================${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}===================================================${NC}"; }

echo ""
echo -e "${CYAN}  ============================================${NC}"
echo -e "${CYAN}   Jayraldines Catering - Linux Setup        ${NC}"
echo -e "${CYAN}  ============================================${NC}"
echo ""
echo "  This script will:"
echo "    1. Check Python 3.11+"
echo "    2. Set up Python virtual environment"
echo "    3. Install Python packages"
echo "    4. Install PostgreSQL 16 (user-local, no sudo)"
echo "    5. Initialize and start PostgreSQL"
echo "    6. Create and initialize the database"
echo "    7. Create run.sh launcher"
echo ""
echo -e "${YELLOW}  Press ENTER to continue or Ctrl+C to cancel...${NC}"
read -r

# ------------------------------------------------------------------------------
# STEP 1 - Python
# ------------------------------------------------------------------------------
step "Step 1 - Check Python 3.11+"

PYSTAND="$HOME/.local/pystand/bin/python3"
PYTHON_CMD=""

# Prefer standalone Python already downloaded by run.sh
if [ -f "$PYSTAND" ]; then
    PYTHON_CMD="$PYSTAND"
    ok "Found standalone Python: $($PYSTAND --version)"
else
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            ver=$("$cmd" --version 2>&1 | grep -oP '3\.\K[0-9]+' | head -1)
            if [ -n "$ver" ] && [ "$ver" -ge 11 ]; then
                if "$cmd" -c 'import ensurepip' &>/dev/null 2>&1; then
                    PYTHON_CMD="$cmd"
                    ok "Found: $($cmd --version)  (command: $cmd)"
                    break
                fi
            fi
        fi
    done
fi

if [ -z "$PYTHON_CMD" ]; then
    fail "No working Python 3.11+ found."
    echo "  Please run ./run.sh first to download standalone Python, then re-run this script."
    exit 1
fi

# ------------------------------------------------------------------------------
# STEP 2 - Virtual environment
# ------------------------------------------------------------------------------
step "Step 2 - Python Environment"

PYTHON="$PYTHON_CMD"
PIP="$PYTHON_CMD -m pip"
skip "Using standalone Python - no venv needed"

# Wrapper so we can call $PIP as a command
pip_install() { "$PYTHON" -m pip "$@"; }

# ------------------------------------------------------------------------------
# STEP 3 - Python packages
# ------------------------------------------------------------------------------
step "Step 3 - Installing Python Packages"

info "Upgrading pip..."
pip_install install --upgrade pip --quiet 2>/dev/null || true

info "Installing from requirements.txt..."
pip_install install -r "$SCRIPT_DIR/requirements.txt" --quiet

info "Ensuring Pillow is installed..."
pip_install install pillow --quiet

ok "All packages installed"

# ------------------------------------------------------------------------------
# STEP 4 - PostgreSQL (user-local, no sudo)
# ------------------------------------------------------------------------------
step "Step 4 - PostgreSQL 16 (user-local)"

mkdir -p "$HOME/.local"

PSQL="psql"
INITDB="initdb"
PG_CTL="pg_ctl"

# First check if PostgreSQL is already running and accessible
if psql -U "$PG_USER" -h localhost -p "$PG_PORT" -d postgres -c "SELECT 1;" &>/dev/null 2>&1; then
    ok "PostgreSQL already running and accessible on port $PG_PORT"
    PG_RUNNING=true
elif [ -f "$PG_DIR/bin/psql" ]; then
    PSQL="$PG_DIR/bin/psql"
    INITDB="$PG_DIR/bin/initdb"
    PG_CTL="$PG_DIR/bin/pg_ctl"
    skip "Using previously downloaded PostgreSQL at $PG_DIR"
elif command -v psql &>/dev/null; then
    ok "System PostgreSQL found: $(psql --version)"
else
    info "Downloading PostgreSQL $PG_VERSION binaries (~50MB)..."
    curl -fL "$PG_TARBALL_URL" -o "$PG_TARBALL" --progress-bar
    info "Extracting..."
    rm -rf "$PG_DIR"
    tar -xzf "$PG_TARBALL" -C "$HOME/.local/"
    mv "$HOME/.local/pgsql" "$PG_DIR" 2>/dev/null || true
    rm -f "$PG_TARBALL"
    PSQL="$PG_DIR/bin/psql"
    INITDB="$PG_DIR/bin/initdb"
    PG_CTL="$PG_DIR/bin/pg_ctl"
    ok "PostgreSQL downloaded to $PG_DIR"
fi

# ------------------------------------------------------------------------------
# STEP 5 - Initialize and start PostgreSQL cluster
# ------------------------------------------------------------------------------
step "Step 5 - Initialize PostgreSQL Data Directory"

if [ "${PG_RUNNING:-false}" = "true" ]; then
    skip "PostgreSQL already running - skipping init/start"
else
    if [ -f "$PG_DATA/PG_VERSION" ]; then
        skip "Data directory already initialized at $PG_DATA"
    else
        info "Initializing database cluster..."
        "$INITDB" -D "$PG_DATA" -U "$PG_USER" --auth=trust --no-instructions 2>&1 | tail -3
        ok "Cluster initialized"
    fi

    # Configure port in postgresql.conf
    if [ -f "$PG_DATA/postgresql.conf" ]; then
        sed -i "s/^#*port = .*/port = $PG_PORT/" "$PG_DATA/postgresql.conf" 2>/dev/null || true
    fi

    # Start PostgreSQL
    if "$PG_CTL" status -D "$PG_DATA" &>/dev/null; then
        ok "PostgreSQL is already running"
        PG_RUNNING=true
    else
        info "Starting PostgreSQL..."
        "$PG_CTL" start -D "$PG_DATA" -l "$PG_DATA/logfile.log" -w 2>&1 | tail -2
        sleep 1
        if "$PG_CTL" status -D "$PG_DATA" &>/dev/null; then
            ok "PostgreSQL started on port $PG_PORT"
            PG_RUNNING=true
        else
            if psql -U "$PG_USER" -h localhost -p "$PG_PORT" -d postgres -c "SELECT 1;" &>/dev/null 2>&1; then
                ok "PostgreSQL already running on port $PG_PORT (existing instance)"
                PSQL="psql"
                PG_CTL="true"
                PG_RUNNING=true
            else
                fail "Failed to start PostgreSQL. Check: $PG_DATA/logfile.log"
                cat "$PG_DATA/logfile.log" 2>/dev/null | tail -10
                exit 1
            fi
        fi
    fi
fi

# Add pg_ctl to shell startup so it auto-starts on login
SHELL_RC="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
PG_BIN_DIR="$(dirname "$PG_CTL")"
if ! grep -q "jayraldines_pgsql" "$SHELL_RC" 2>/dev/null; then
    cat >> "$SHELL_RC" << EOF

# jayraldines_pgsql - auto-start PostgreSQL for Jayraldines Catering
export PATH="$PG_BIN_DIR:\$PATH"
EOF
    ok "Added PostgreSQL to PATH in $SHELL_RC"
fi

# ------------------------------------------------------------------------------
# STEP 6 - Database password and SQL setup
# ------------------------------------------------------------------------------
step "Step 6 - Database Setup"

echo ""
echo -e "${YELLOW}  Enter a password for the database.${NC}"
echo -e "${YELLOW}  (This will be saved in run.sh to launch the app)${NC}"
read -rp "  Password (press ENTER to use '12345678'): " PG_PASS
[ -z "$PG_PASS" ] && PG_PASS="12345678"

export PGPASSWORD="$PG_PASS"

# Set the postgres user password
"$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" -d postgres \
    -c "ALTER USER \"$PG_USER\" WITH PASSWORD '$PG_PASS';" 2>/dev/null || true

# Update pg_hba.conf to use md5 auth
if [ -f "$PG_DATA/pg_hba.conf" ]; then
    sed -i 's/^local\s\+all\s\+all\s\+trust/local   all             all                                     md5/' "$PG_DATA/pg_hba.conf" 2>/dev/null || true
    sed -i 's/^host\s\+all\s\+all\s\+127.0.0.1\/32\s\+trust/host    all             all             127.0.0.1\/32            md5/' "$PG_DATA/pg_hba.conf" 2>/dev/null || true
    "$PG_CTL" reload -D "$PG_DATA" &>/dev/null || true
fi

MAIN_SQL="$SCRIPT_DIR/jayraldines_catering.sql"
MIG_SQL="$SCRIPT_DIR/cebu_address_migration.sql"
OCC_MIG_SQL="$SCRIPT_DIR/occasions_migration.sql"
VIEWS_MIG_SQL="$SCRIPT_DIR/confirmed_only_views_migration.sql"

info "Checking if database '$DB_NAME' already exists..."
DB_EXISTS=$("$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" -d postgres \
    -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" 2>/dev/null || echo "")

RUN_SQL=true
if [ "$DB_EXISTS" = "1" ]; then
    echo ""
    echo -e "${YELLOW}  Database '$DB_NAME' already exists.${NC}"
    read -rp "  Drop and recreate it? All data will be lost. (y/N): " CHOICE
    if [[ "$CHOICE" != "y" && "$CHOICE" != "Y" ]]; then
        skip "Keeping existing database"
        # Check if address tables exist
        ADDR_EXISTS=$("$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" -d "$DB_NAME" \
            -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='address_barangays';" 2>/dev/null || echo "")
        if [ "$ADDR_EXISTS" != "1" ]; then
            info "Running cebu address migration..."
            PGPASSWORD="$PG_PASS" "$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" \
                -d "$DB_NAME" -f "$MIG_SQL"
            ok "Cebu address migration done"
        else
            skip "Address tables already exist"
        fi
        # Check if occasions table exists
        OCC_EXISTS=$("$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" -d "$DB_NAME" \
            -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='occasions';" 2>/dev/null || echo "")
        if [ "$OCC_EXISTS" != "1" ]; then
            info "Running occasions migration..."
            PGPASSWORD="$PG_PASS" "$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" \
                -d "$DB_NAME" -f "$OCC_MIG_SQL" || info "Occasions migration had warnings (non-fatal)"
            ok "Occasions migration done"
        else
            skip "Occasions table already exists"
        fi
        # Apply confirmed-only views migration (always re-apply to update views)
        if [ -f "$VIEWS_MIG_SQL" ]; then
            info "Applying confirmed-only views migration..."
            PGPASSWORD="$PG_PASS" "$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" \
                -d "$DB_NAME" -f "$VIEWS_MIG_SQL" || info "Views migration had warnings (non-fatal)"
            ok "Views migration done"
        fi
        RUN_SQL=false
    fi
fi

if [ "$RUN_SQL" = true ]; then
    info "Running main schema (jayraldines_catering.sql)..."
    PGPASSWORD="$PG_PASS" "$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" \
        -d postgres -f "$MAIN_SQL"
    ok "Main schema applied"

    info "Running Cebu address migration..."
    PGPASSWORD="$PG_PASS" "$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" \
        -d "$DB_NAME" -f "$MIG_SQL" || info "Migration had warnings (non-fatal)"
    if [ -f "$VIEWS_MIG_SQL" ]; then
        info "Applying confirmed-only views migration..."
        PGPASSWORD="$PG_PASS" "$PSQL" -U "$PG_USER" -h localhost -p "$PG_PORT" \
            -d "$DB_NAME" -f "$VIEWS_MIG_SQL" || info "Views migration had warnings (non-fatal)"
    fi
    ok "Database '$DB_NAME' is ready"
fi

unset PGPASSWORD

# ------------------------------------------------------------------------------
# STEP 7 - Verify DB connection from Python
# ------------------------------------------------------------------------------
step "Step 7 - Verify Database Connection"

TEST_RESULT=$(DB_HOST=localhost DB_PORT=$PG_PORT DB_USER="$PG_USER" DB_PASSWORD="$PG_PASS" \
    "$PYTHON" -c "
import sys, os
sys.path.insert(0, '.')
import utils.db as db
ok = db.connect()
print('DB_OK' if ok else 'DB_FAIL')
" 2>&1)

if echo "$TEST_RESULT" | grep -q "DB_OK"; then
    ok "Database connection successful"
else
    fail "Database connection failed."
    echo "  Output: $TEST_RESULT"
    echo ""
    echo "  Check that PostgreSQL is running and the password is correct."
fi

# ------------------------------------------------------------------------------
# STEP 8 - Write run.sh launcher
# ------------------------------------------------------------------------------
step "Step 8 - Creating run.sh Launcher"

cat > "$SCRIPT_DIR/run.sh" << EOF
#!/usr/bin/env bash
cd "\$(dirname "\$(readlink -f "\$0")")"
SCRIPT_DIR="\$(cd "\$(dirname "\$(readlink -f "\$0")")" && pwd)"
PYSTAND="\$HOME/.local/pystand/bin/python3"
PYTHON="\$PYSTAND"

export DB_HOST=localhost
export DB_PORT=$PG_PORT
export DB_USER=$PG_USER
export DB_PASSWORD=$PG_PASS

# Start PostgreSQL if not running
PG_CTL_BIN="$PG_CTL"
PG_DATA_DIR="$PG_DATA"
if [ -f "\$PG_CTL_BIN" ] && ! "\$PG_CTL_BIN" status -D "\$PG_DATA_DIR" &>/dev/null; then
    echo "Starting PostgreSQL..."
    "\$PG_CTL_BIN" start -D "\$PG_DATA_DIR" -l "\$PG_DATA_DIR/logfile.log" -w &>/dev/null
    sleep 1
fi

# Set up xcb lib path
XCBCURSOR_DIR="\$HOME/.local/xcbcursor"
PYSIDE6_DIR="\$(\$PYTHON -c 'import PySide6,os; print(os.path.dirname(PySide6.__file__))' 2>/dev/null)"
export QT_QPA_PLATFORM=xcb
export LD_LIBRARY_PATH="\$XCBCURSOR_DIR:\$PYSIDE6_DIR:\$PYSIDE6_DIR/Qt/lib:\$LD_LIBRARY_PATH"
export QT_PLUGIN_PATH="\$PYSIDE6_DIR/Qt/plugins"

"\$PYTHON" main.py
EOF

chmod +x "$SCRIPT_DIR/run.sh"
ok "run.sh created"

# ------------------------------------------------------------------------------
# Done
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}  ============================================${NC}"
echo -e "${GREEN}   SETUP COMPLETE                            ${NC}"
echo -e "${GREEN}  ============================================${NC}"
echo ""
echo "  To start the app:"
echo -e "    ${CYAN}./run.sh${NC}"
echo "    OR: source venv/bin/activate && python main.py"
echo ""
echo -e "${YELLOW}  DB password saved in run.sh${NC}"
echo ""

read -rp "  Launch the app now? (y/N): " LAUNCH
if [[ "$LAUNCH" == "y" || "$LAUNCH" == "Y" ]]; then
    bash "$SCRIPT_DIR/run.sh"
fi
