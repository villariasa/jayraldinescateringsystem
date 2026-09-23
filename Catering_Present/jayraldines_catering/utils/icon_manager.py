"""Backward-compatibility shim.

Re-exports everything from utils.icons so existing imports of
`utils.icon_manager` keep working after the icon helpers moved to utils.icons.
Prefer importing from utils.icons directly in new code.
"""
# Star-import purely to re-expose utils.icons' public API under this old name.
from utils.icons import *  # noqa: F401,F403
