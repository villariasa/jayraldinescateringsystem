# High-Performance Isolated Theme Engine Specification

## Architecture Problem & Solution
### The Bottleneck
Compiling massive Qt QSS stylesheets (1,800+ lines) in PySide6 blocks the Python GIL and C++ GUI thread for ~250ms.

### The Solution (Option B: Isolated OS Process)
- A lightweight secondary process (`components/standalone_loader.py`) is spawned.
- It creates a frameless transparent window with pure PySide6 QPainter animations at 60 FPS.
- The main application compiles stylesheets in parallel without freezing the animation.
