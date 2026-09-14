from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None
qt_data = collect_data_files("PySide6", includes=[
    "Qt/plugins/platforms/*",
    "Qt/plugins/imageformats/*",
    "Qt/plugins/iconengines/*",
    "Qt/plugins/styles/*",
    "Qt/translations/qtbase_*.qm",
])

qt_binaries = []
try:
    import os
    libs = collect_dynamic_libs("PySide6")
    qt_binaries = [b for b in libs if "python" not in os.path.basename(b[0]).lower()]
except Exception as e:
    print(f"[spec] Warning: collect_dynamic_libs(PySide6) failed: {e}")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=qt_binaries,
    datas=[
        ("assets", "assets"),
        ("styles", "styles"),
        ("jayraldines_catering_clean.sql", "."),
        ("cebu_address_migration.sql", "."),
        ("occasions_migration.sql", "."),
        ("confirmed_only_views_migration.sql", "."),
        ("analytics_functions_migration.sql", "."),
        ("fix_customer_ledger_view.sql", "."),
    ] + qt_data,
    hiddenimports=[
        "shiboken6",
        "psycopg2",
        "psycopg2.extensions",
        "psycopg2.extras",
        "reportlab",
        "reportlab.graphics",
        "reportlab.platypus",
        "reportlab.lib",
        "reportlab.pdfgen",
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
        # UI Pages
        "ui.dashboard_page",
        "ui.booking_page",
        "ui.customers_page",
        "ui.menu_page",
        "ui.calendar_page",
        "ui.cash_flow_page",
        "ui.kitchen_page",
        "ui.billing_page",
        "ui.reports_page",
        "ui.expenses_page",
        "ui.inventory_page",
        "ui.ai_page",
        "ui.settings_page",
        # Components
        "components.sidebar",
        "components.topbar",
        "components.notifications_panel",
        "components.toast",
        "components.global_ai_floating",
        "components.mascot",
        "components.splash",
        "utils.db",
        "utils.repository",
        "utils.theme",
        "utils.accent",
        "utils.signals",
        "utils.paths",
        "utils.icons",
        "utils.exporter",
        "utils.notif_scheduler",
        "utils.ai_client",
        "utils.reminder_manager",
        "pypdf",
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JayraldinesCatering",
    icon="assets/logo.ico",
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
    name="JayraldinesCatering",
)
