# Standalone Windows Executable Asset Extraction Lifecycle

## 1. Runtime Directory Hierarchy
During execution, PyInstaller one-dir or one-file wrappers unpack runtime components into isolated temporary staging trees:
$$\text{Target Dir} = \text{sys.\_MEIPASS} \lor \text{Directory of } \text{sys.executable}$$

## 2. Resource Path Resolution
Static logos, fonts, templates, and sounds are resolved through `utils.resource_path()` ensuring deterministic lookups regardless of launch method.
