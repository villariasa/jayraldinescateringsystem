# PRD: Faster Startup After Build

Date: 2026-05-06
Project: Jayraldine's Catering Management System
Related file: `build.ps1`

## Problem

After building the desktop app, opening `JayraldinesCatering.exe` takes too long. The current build creates a single self-contained PyInstaller executable. For a PySide6 desktop app, this can be slow because the executable may need to unpack Python, Qt libraries, plugins, assets, and other bundled files before the app window appears.

The user experience should feel faster and more reliable after installation.

## Goal

Improve perceived and actual startup time for the built Windows app.

Primary goal:

- The app should show visible feedback quickly after the user double-clicks the icon.

Secondary goal:

- The installed app should open faster on repeated launches.

## Success Metrics

| Metric | Target |
|---|---:|
| Time until first visible window/splash | 1-3 seconds |
| Time until main dashboard is usable | 5-10 seconds on a normal laptop |
| Repeated launch time | Faster than first launch |
| Startup failure visibility | Clear error message instead of silent delay |

## Current Build Behavior

`build.ps1` writes a PyInstaller spec that builds:

```text
dist\JayraldinesCatering.exe
```

The spec places binaries, zip files, and data directly into `EXE(...)`, making it a single-file style distribution.

Current build also includes broad PySide6 data collection:

```python
*collect_data_files('PySide6')
```

This may increase bundle size and startup extraction work.

## Likely Causes Of Slow Open

### 1. Single-file PyInstaller startup cost

One-file executables usually extract bundled files to a temporary folder on launch. Large PySide6 apps are especially affected.

Recommendation:

- Use a one-folder build for installed versions.
- Keep one-file only as an optional portable build.

### 2. Large Qt/PySide6 bundle

The app uses PySide6, QtCharts, QtSvg, QtPrintSupport, and other Qt modules. Collecting all PySide6 data may include plugins and translations that are not needed.

Recommendation:

- Bundle only required Qt modules and plugins.
- Avoid collecting all PySide6 data unless required.

### 3. Startup imports and initialization

`main.py` already lazy-loads most pages through `ui.main_window`, which is good. However, startup still does:

- Theme load
- Database connection attempt
- Main window creation
- Dashboard page load
- Notification scheduler setup

Recommendation:

- Keep the splash screen immediate.
- Defer non-critical work until after the main window is visible.
- Avoid loading reports/charts/export modules at startup unless needed.

### 4. Database wait during startup

`main.py` waits up to 8 seconds for database connection:

```python
db_thread.join(timeout=8)
```

This is safer than blocking forever, but it can still make startup feel slow when PostgreSQL is not ready.

Recommendation:

- Show the splash immediately.
- Let the main window open in offline/loading mode.
- Continue DB connection in background and refresh pages once connected.

### 5. Antivirus scan on one-file exe

On Windows, a large newly built unsigned executable can be scanned every time it runs, especially if it extracts files to temp.

Recommendation:

- Prefer one-folder installer builds.
- Avoid UPX for release builds if it causes antivirus suspicion or launch delay.
- Consider code signing later if this will be distributed outside one machine.

## Product Requirements

### Requirement 1: Add build mode selection

`build.ps1` should support at least two build modes:

| Mode | Purpose |
|---|---|
| `onedir` | Recommended installed app, faster startup |
| `onefile` | Optional portable exe, slower but easy to copy |

Default should be `onedir`.

Example:

```powershell
.\build.ps1 -Mode onedir
.\build.ps1 -Mode onefile
```

### Requirement 2: Installer should install one-folder app

The installer should include the whole `dist\JayraldinesCatering\` folder instead of only `dist\JayraldinesCatering.exe`.

Expected installer layout:

```text
{app}\
  JayraldinesCatering.exe
  _internal\
  assets\
  styles\
  setup.ps1
  *.sql
```

### Requirement 3: Keep one-file build optional

The single exe is still useful for quick sharing, but it should be labeled as slower:

```text
dist\JayraldinesCatering.exe
```

Expected script message:

```text
Portable one-file build created. Note: first startup may be slower.
```

### Requirement 4: Add startup profiling logs

Add optional startup timing logs to help find real bottlenecks.

Example environment flag:

```text
JAYRALDINES_PROFILE_STARTUP=1
```

Example output:

```text
[startup] QApplication: 0.42s
[startup] splash shown: 0.58s
[startup] theme applied: 0.81s
[startup] main window created: 2.10s
[startup] db connected: 3.44s
```

### Requirement 5: First visible UI must appear early

The splash screen should appear before expensive imports or DB waiting.

Acceptance criteria:

- Double-click app.
- Splash appears within 1-3 seconds.
- Splash text updates while the app loads.
- If DB connection is slow, the splash or app clearly says it is connecting/offline.

### Requirement 6: Move non-critical startup tasks later

Non-critical tasks should run after the main window is visible.

Candidates:

- Notification polling
- Dashboard auto-refresh timer
- Expensive report/chart data refresh
- Backup prompt logic
- Any unused test/prototype modules

### Requirement 7: Clean stale modules before packaging

The build should not include removed or broken modules.

Known stale/broken file:

```text
ui/inventory_page.py
```

This file currently has a syntax error and references removed inventory repository functions. It should be deleted or fixed before release.

## Recommended Technical Plan

### Phase 1: Build script update

- Add `param([ValidateSet("onedir","onefile")] [string]$Mode = "onedir")`.
- Generate different PyInstaller specs depending on mode.
- For `onedir`, use `COLLECT(...)`.
- For `onefile`, keep current `EXE(...)` bundled behavior.
- Update installer.iss to package the onedir folder.

### Phase 2: Startup profiling

- Add a small helper in `main.py` for startup timestamps.
- Enable only when `JAYRALDINES_PROFILE_STARTUP=1`.
- Measure before and after build changes.

### Phase 3: Startup behavior improvement

- Keep splash creation as early as possible.
- Avoid waiting the full 8 seconds for DB before showing main window.
- Open app in offline/loading state if DB is slow.
- Refresh pages automatically after DB connects.

### Phase 4: Bundle trimming

- Replace broad PySide6 data collection with targeted Qt plugin/data collection.
- Exclude unused PySide6 modules.
- Remove prototype files from distribution if not used:
  - `test_reports.py`
  - `ui/test_report.py`
  - stale Inventory files, if removed from product scope

### Phase 5: Release validation

Test on a clean Windows machine:

- Fresh install
- First launch
- Second launch
- Launch without PostgreSQL running
- Launch with PostgreSQL running
- Launch after reboot

## Proposed Build Outputs

Recommended default:

```text
dist\
  JayraldinesCatering\
    JayraldinesCatering.exe
    _internal\
installer_output\
  JayraldinesSetup.exe
```

Optional portable output:

```text
dist\
  JayraldinesCatering.exe
```

## Acceptance Checklist

- [x] `build.ps1` supports `onedir` and `onefile`.
- [x] Default build mode is `onedir`.
- [x] Installer packages the full onedir output.
- [x] Startup profiling can be enabled with an environment variable.
- [x] Build excludes stale broken Inventory/test UI modules from packaged Python imports.
- [ ] Splash appears within 1-3 seconds after double-click on Windows build.
- [ ] Dashboard is usable within 5-10 seconds on a normal laptop.
- [ ] Slow/missing DB does not make the app look frozen.
- [ ] Final installer is tested on a clean Windows machine.

## Recommendation

Change the default release build from one-file to one-folder. This is the most important improvement because it directly addresses the common PyInstaller + PySide6 slow startup problem. Keep the one-file executable only as an optional portable build.
