Refactor only the icon system of my existing PySide6 application.

Goal:
Replace all default Qt icons with a modern, consistent icon system using SVG-based icons (prefer Lucide or Tabler).

Constraints:
- Do not modify UI layout, styling, or business logic.
- Only modify icon handling and icon assignment.

Requirements:
- Create a centralized IconManager class or module.
- Store all icons in a structured /icons directory.
- Replace all icons in QPushButton, QAction, menus, toolbars.
- Ensure consistent sizing and stroke style across all icons.
- Use only one icon library (no mixing libraries).
- Ensure icons are scalable and look sharp in high DPI displays.
- Ensure compatibility with dark mode.

Deliverables:
- Updated Python code (PySide6)
- IconManager implementation
- Clean mapping of old → new icons
- Suggested icon file structure



