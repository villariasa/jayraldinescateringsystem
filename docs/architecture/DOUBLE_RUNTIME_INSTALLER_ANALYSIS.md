# Standalone Installer Packaging & Footprint Analysis

## 1. The 205MB Package Size Breakdown
1. **Embedded App Package (`app_package.zip`, ~125MB)**:
   - Qt6 Core, GUI, Widgets, Charts, and OpenGL DLLs (~50MB+).
   - `opengl32sw.dll` software OpenGL fallback renderer (19.7MB).
   - Python 3.13 standard libraries and C-extensions (~25MB).
   - Bundled Android Tablet APK (`jayraldines_catering.apk`, 8.5MB).
   - High-resolution menu asset images (~18MB).
2. **Installer Wizard Executable (~85MB)**:
   - Contains a second PySide6/Qt6 runtime to render the 5-step graphical setup wizard.
