"""Resolve paths to bundled resources for both source and frozen builds.

resource_path() returns an absolute path that works whether the app runs from
source or from a PyInstaller-frozen executable, where data files live under a
temporary extraction dir (sys._MEIPASS).
"""
import os
import sys


def resource_path(*parts: str) -> str:
    """Return the absolute path to a bundled resource given path components.

    Chooses the correct base directory depending on whether the app is running
    frozen (PyInstaller) or from source, then joins the given path parts to it.
    """
    if getattr(sys, "frozen", False):
        # Frozen: prefer PyInstaller's extraction dir, else the exe's folder.
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        # Source: project root, one level up from this utils/ package.
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)
