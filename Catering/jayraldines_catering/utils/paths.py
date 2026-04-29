import os
import sys


def resource_path(*parts: str) -> str:
    """
    Resolve a path relative to the app root.
    Works correctly both when running as:
      - python main.py        (dev mode)
      - a PyInstaller .exe    (frozen mode)
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)
