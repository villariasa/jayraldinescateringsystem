#!/usr/bin/env bash
# ==============================================================================
#  Jayraldine's Catering - Linux Build Script
#
#  Usage:
#    chmod +x build.sh
#    ./build.sh
#    ./build.sh --mode onefile
#
#  Default mode is onedir because PySide6 apps start faster that way.
# ==============================================================================

set -euo pipefail

MODE="onedir"
SKIP_INSTALL=0
APP_NAME="JayraldinesCatering"
DISPLAY_NAME="Jayraldines Catering"
DESKTOP_ID="jayraldines-catering"
SPEC_FILE="jayraldines_linux.spec"
PACKAGE_DIR="installer_output"

while [ $# -gt 0 ]; do
    case "$1" in
        --mode)
            if [ $# -lt 2 ]; then
                echo "Missing value for --mode. Use onedir or onefile." >&2
                exit 1
            fi
            MODE="${2:-}"
            shift 2
            ;;
        --mode=*)
            MODE="${1#*=}"
            shift
            ;;
        --onefile)
            MODE="onefile"
            shift
            ;;
        --onedir)
            MODE="onedir"
            shift
            ;;
        --skip-install)
            SKIP_INSTALL=1
            shift
            ;;
        -h|--help)
            echo "Usage: ./build.sh [--mode onedir|onefile] [--skip-install]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [ "$MODE" != "onedir" ] && [ "$MODE" != "onefile" ]; then
    echo "Invalid mode: $MODE. Use onedir or onefile." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  [OK]${NC} $1"; }
info() { echo -e "${YELLOW}  [..]${NC} $1"; }
warn() { echo -e "${YELLOW}  [!!]${NC} $1"; }
fail() { echo -e "${RED}  [!!]${NC} $1"; }
step() {
    echo -e "\n${CYAN}===================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}===================================================${NC}"
}

strip_shell_value() {
    printf '%s' "$1" | sed -E "s/^[[:space:]]+//; s/[[:space:]]+$//; s/^\"//; s/\"$//; s/^'//; s/'$//"
}

read_run_value() {
    local key="$1"
    local fallback="$2"
    local value=""
    if [ -f "run.sh" ]; then
        value="$(grep -E "^(export[[:space:]]+)?${key}=" run.sh | tail -1 | sed -E "s/^(export[[:space:]]+)?${key}=//" || true)"
        value="$(strip_shell_value "$value")"
    fi
    if [ -n "$value" ]; then
        printf '%s' "$value"
    else
        printf '%s' "$fallback"
    fi
}

write_launcher() {
    local target_dir="$1"
    local exe_name="$2"
    local launcher="$target_dir/start-jayraldines.sh"
    local db_host db_port db_user db_password pg_ctl_bin

    db_host="$(read_run_value "DB_HOST" "localhost")"
    db_port="$(read_run_value "DB_PORT" "5432")"
    db_user="$(read_run_value "DB_USER" "$(whoami)")"
    db_password="$(read_run_value "DB_PASSWORD" "12345678")"
    pg_ctl_bin="$(read_run_value "PG_CTL_BIN" "pg_ctl")"

    cat > "$launcher" << EOF
#!/usr/bin/env bash
set -e

APP_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

export DB_HOST="\${DB_HOST:-$db_host}"
export DB_PORT="\${DB_PORT:-$db_port}"
export DB_USER="\${DB_USER:-$db_user}"
export DB_PASSWORD="\${DB_PASSWORD:-$db_password}"

PG_DATA_DIR="\${PG_DATA_DIR:-\$HOME/.local/pgsql_data}"
PG_CTL_BIN="\${PG_CTL_BIN:-$pg_ctl_bin}"
if [ "\$PG_CTL_BIN" = "pg_ctl" ]; then
    PG_CTL_BIN="\$(command -v pg_ctl || true)"
fi
if [ -z "\$PG_CTL_BIN" ] && [ -x "\$HOME/.local/pgsql/bin/pg_ctl" ]; then
    PG_CTL_BIN="\$HOME/.local/pgsql/bin/pg_ctl"
fi

if [ -n "\$PG_CTL_BIN" ] && [ -d "\$PG_DATA_DIR" ] && ! "\$PG_CTL_BIN" status -D "\$PG_DATA_DIR" >/dev/null 2>&1; then
    "\$PG_CTL_BIN" start -D "\$PG_DATA_DIR" -l "\$PG_DATA_DIR/logfile.log" >/dev/null 2>&1 &
fi

XCBCURSOR_DIR="\$HOME/.local/xcbcursor"
QT_LIB_DIRS=""
for candidate in \\
    "\$XCBCURSOR_DIR" \\
    "\$APP_DIR/_internal/PySide6/Qt/lib" \\
    "\$APP_DIR/_internal/PySide6" \\
    "\$APP_DIR/PySide6/Qt/lib" \\
    "\$APP_DIR/PySide6"; do
    if [ -d "\$candidate" ]; then
        QT_LIB_DIRS="\$candidate:\$QT_LIB_DIRS"
    fi
done
export QT_QPA_PLATFORM="\${QT_QPA_PLATFORM:-xcb}"
export LD_LIBRARY_PATH="\${QT_LIB_DIRS}\${LD_LIBRARY_PATH:-}"

for plugin_dir in "\$APP_DIR/_internal/PySide6/Qt/plugins" "\$APP_DIR/PySide6/Qt/plugins"; do
    if [ -d "\$plugin_dir" ]; then
        export QT_PLUGIN_PATH="\${QT_PLUGIN_PATH:-\$plugin_dir}"
        break
    fi
done

exec "\$APP_DIR/$exe_name"
EOF
    chmod +x "$launcher"
}

write_desktop_installer() {
    local target_dir="$1"
    local installer="$target_dir/install-desktop-entry.sh"

    cat > "$installer" << EOF
#!/usr/bin/env bash
set -e

APP_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="\$HOME/.local/share/applications"
DESKTOP_FILE="\$DESKTOP_DIR/$DESKTOP_ID.desktop"
ICON_PATH=""

for candidate in "\$APP_DIR/logo.png" "\$APP_DIR/_internal/assets/logo.png" "\$APP_DIR/assets/logo.png"; do
    if [ -f "\$candidate" ]; then
        ICON_PATH="\$candidate"
        break
    fi
done

mkdir -p "\$DESKTOP_DIR"
{
    printf '%s\n' "[Desktop Entry]"
    printf '%s\n' "Type=Application"
    printf '%s\n' "Name=$DISPLAY_NAME"
    printf '%s\n' "Exec=\$APP_DIR/start-jayraldines.sh"
    if [ -n "\$ICON_PATH" ]; then
        printf '%s\n' "Icon=\$ICON_PATH"
    fi
    printf '%s\n' "Terminal=false"
    printf '%s\n' "Categories=Office;Utility;"
    printf '%s\n' "StartupNotify=true"
} > "\$DESKTOP_FILE"

chmod +x "\$DESKTOP_FILE"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "\$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo "Desktop entry installed: \$DESKTOP_FILE"
EOF
    chmod +x "$installer"
}

write_readme() {
    local target_dir="$1"

    cat > "$target_dir/README_LINUX.txt" << EOF
$DISPLAY_NAME Linux Build

Run the app:
  ./start-jayraldines.sh

Install an application-menu shortcut:
  ./install-desktop-entry.sh

PostgreSQL must be installed and running on the target machine. The launcher
uses these defaults, and each one can be overridden at launch time:
  DB_HOST=localhost
  DB_PORT=5432
  DB_USER=$USER
  DB_PASSWORD=12345678

Example:
  DB_USER=postgres DB_PASSWORD=your_password ./start-jayraldines.sh
EOF
}

copy_optional_icon() {
    local target_dir="$1"
    if [ -f "assets/logo.png" ]; then
        cp "assets/logo.png" "$target_dir/logo.png"
    fi
}

create_package() {
    local package="$PACKAGE_DIR/${APP_NAME}-linux-${MODE}.tar.gz"

    mkdir -p "$PACKAGE_DIR"
    rm -f "$package"

    if ! command -v tar >/dev/null 2>&1; then
        warn "tar not found. Skipping portable package creation."
        return
    fi

    if [ "$MODE" = "onedir" ]; then
        tar -czf "$package" -C dist "$APP_NAME"
    else
        local items=("$APP_NAME" "start-jayraldines.sh" "install-desktop-entry.sh" "README_LINUX.txt")
        if [ -f "dist/logo.png" ]; then
            items+=("logo.png")
        fi
        (cd dist && tar -czf "../$package" "${items[@]}")
    fi

    ok "Portable package created: $package"
}

if [ ! -f "main.py" ]; then
    fail "main.py not found. Run this script from Catering/jayraldines_catering."
    exit 1
fi

echo ""
echo -e "${CYAN}  Jayraldines Catering - Linux Build Script${NC}"
echo -e "${YELLOW}  Build mode: $MODE${NC}"

step "Step 1 - Checking Python"

PYSTAND="$HOME/.local/pystand/bin/python3"
PYTHON_CMD=""

if [ -x "$PYSTAND" ]; then
    PYTHON_CMD="$PYSTAND"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python)"
fi

if [ -z "$PYTHON_CMD" ]; then
    fail "Python not found. Install Python 3.11+ or run setup_linux.sh first."
    exit 1
fi

ok "Found: $("$PYTHON_CMD" --version)"

step "Step 2 - Preparing Build Environment"

BUILD_VENV="$SCRIPT_DIR/.build_venv"
if [ ! -x "$BUILD_VENV/bin/python" ]; then
    info "Creating build virtual environment..."
    "$PYTHON_CMD" -m venv "$BUILD_VENV"
fi

PYTHON="$BUILD_VENV/bin/python"

if [ "$SKIP_INSTALL" -eq 0 ]; then
    info "Upgrading pip..."
    "$PYTHON" -m pip install --upgrade pip --quiet

    info "Installing app requirements..."
    "$PYTHON" -m pip install -r requirements.txt --quiet

    info "Installing PyInstaller and Pillow..."
    "$PYTHON" -m pip install pyinstaller pillow --quiet
else
    info "Skipping dependency install because --skip-install was provided."
fi

ok "Build environment ready"

step "Step 3 - Optional Icon Conversion"

if [ -f "assets/logo.png" ]; then
    "$PYTHON" - <<'PY'
from PIL import Image
img = Image.open("assets/logo.png").convert("RGBA")
img.save("assets/logo.ico", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
PY
    ok "assets/logo.ico created"
else
    info "assets/logo.png not found. Skipping icon conversion."
fi

step "Step 4 - Writing PyInstaller Spec"

cat > "$SPEC_FILE" << EOF
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
qt_data = collect_data_files("PySide6", includes=[
    "Qt/plugins/platforms/*",
    "Qt/plugins/imageformats/*",
    "Qt/plugins/iconengines/*",
    "Qt/plugins/styles/*",
    "Qt/translations/qtbase_*.qm",
])

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("assets", "assets"),
        ("styles", "styles"),
        ("jayraldines_catering_clean.sql", "."),
        ("cebu_address_migration.sql", "."),
        ("occasions_migration.sql", "."),
        ("confirmed_only_views_migration.sql", "."),
    ] + qt_data,
    hiddenimports=[
        "psycopg2",
        "psycopg2.extensions",
        "psycopg2.extras",
        "reportlab",
        "reportlab.graphics",
        "reportlab.platypus",
        "reportlab.lib",
        "openpyxl",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtXml",
        "PySide6.QtPrintSupport",
        "PySide6.QtCharts",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtNetwork",
        "ui.dashboard_page",
        "ui.booking_page",
        "ui.customers_page",
        "ui.menu_page",
        "ui.calendar_page",
        "ui.kitchen_page",
        "ui.billing_page",
        "ui.reports_page",
        "ui.settings_page",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "scipy", "numpy",
        "PySide6.QtWebEngine", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtLocation",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
        "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQml",
        "PySide6.QtRemoteObjects", "PySide6.QtSensors", "PySide6.QtSerialPort",
        "ui.inventory_page", "ui.test_report", "test_reports",
        "xmlrpc", "test", "unittest",
        "distutils", "setuptools", "pkg_resources",
    ],
    noarchive=False,
    cipher=block_cipher,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
EOF

if [ "$MODE" = "onedir" ]; then
    cat >> "$SPEC_FILE" << EOF

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="$APP_NAME",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="$APP_NAME",
)
EOF
else
    cat >> "$SPEC_FILE" << EOF

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="$APP_NAME",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
)
EOF
fi

ok "$SPEC_FILE written"

step "Step 5 - Building App"

rm -rf dist build
"$PYTHON" -m PyInstaller "$SPEC_FILE"

if [ "$MODE" = "onedir" ]; then
    TARGET_DIR="dist/$APP_NAME"
    BUILT_EXE="$TARGET_DIR/$APP_NAME"
    if [ ! -x "$BUILT_EXE" ]; then
        fail "Build failed - executable not found: $BUILT_EXE"
        exit 1
    fi
    write_launcher "$TARGET_DIR" "$APP_NAME"
    write_desktop_installer "$TARGET_DIR"
    write_readme "$TARGET_DIR"
    copy_optional_icon "$TARGET_DIR"
    ok "Build successful: $BUILT_EXE"
    ok "Launcher created: $TARGET_DIR/start-jayraldines.sh"
    ok "Desktop shortcut installer created: $TARGET_DIR/install-desktop-entry.sh"
    info "Use the launcher so DB and Qt environment variables are set correctly."
else
    TARGET_DIR="dist"
    BUILT_EXE="$TARGET_DIR/$APP_NAME"
    if [ ! -x "$BUILT_EXE" ]; then
        fail "Build failed - executable not found: $BUILT_EXE"
        exit 1
    fi
    write_launcher "$TARGET_DIR" "$APP_NAME"
    write_desktop_installer "$TARGET_DIR"
    write_readme "$TARGET_DIR"
    copy_optional_icon "$TARGET_DIR"
    ok "Build successful: $BUILT_EXE"
    ok "Launcher created: $TARGET_DIR/start-jayraldines.sh"
    ok "Desktop shortcut installer created: $TARGET_DIR/install-desktop-entry.sh"
    info "Portable one-file build created. First startup may be slower."
fi

step "Step 6 - Packaging Linux Artifact"

create_package

echo ""
echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}  BUILD COMPLETE${NC}"
echo -e "${GREEN}===================================================${NC}"
echo ""
if [ "$MODE" = "onedir" ]; then
    echo "  App folder : dist/$APP_NAME/"
    echo "  Run app    : dist/$APP_NAME/start-jayraldines.sh"
else
    echo "  Single exe : dist/$APP_NAME"
    echo "  Run app    : dist/start-jayraldines.sh"
fi
if [ -f "$PACKAGE_DIR/${APP_NAME}-linux-${MODE}.tar.gz" ]; then
    echo "  Package    : $PACKAGE_DIR/${APP_NAME}-linux-${MODE}.tar.gz"
fi
echo ""
echo "  Tip: for startup timing logs, run with:"
echo "    JAYRALDINES_PROFILE_STARTUP=1 <launcher>"
echo ""
