# PySide6 Memory Leak Prevention & Lifecycle Rules

## 1. Best Practices
- Always pass `parent` to QWidget constructors to guarantee clean C++ object destruction.
- Explicitly call `deleteLater()` on dismissed modal dialogs.
- Avoid persistent closures referencing large UI frames in long-running background threads.
