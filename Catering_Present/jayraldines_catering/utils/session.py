"""
App session singleton — stores the current logged-in actor name.
Import get_actor() wherever audit logging needs a username.

The name is persisted locally via QSettings (per-machine, not shared business
data) so it survives app restarts - staff set it once in Settings and every
subsequent audit log entry / notification is correctly attributed to them.
"""
from PySide6.QtCore import QSettings

_ORG, _APP = "Jayraldines", "CateringSystem"
_KEY_ACTOR = "session/actor_name"

_current_actor: str = ""


def get_actor() -> str:
    global _current_actor
    # 1. Prioritize currently authenticated user in SessionManager
    try:
        user = SessionManager.get_current_user()
        if user:
            name = (user.get("display_name") or user.get("username") or "").strip()
            if name:
                return name
    except Exception:
        pass

    # 2. Check explicitly set actor in memory
    if _current_actor and _current_actor.strip():
        return _current_actor.strip()

    # 3. Fallback to QSettings local actor
    try:
        stored = QSettings(_ORG, _APP).value(_KEY_ACTOR, "")
        if stored and str(stored).strip():
            _current_actor = str(stored).strip()
            return _current_actor
    except Exception:
        pass

    return "staff"


def set_actor(name: str) -> None:
    global _current_actor
    _current_actor = name if name and name.strip() else "staff"
    QSettings(_ORG, _APP).setValue(_KEY_ACTOR, _current_actor)


# Re-export SessionManager from auth for convenience
from utils.auth import SessionManager  # noqa: E402


