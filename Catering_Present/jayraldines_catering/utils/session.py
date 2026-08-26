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
    if not _current_actor:
        stored = QSettings(_ORG, _APP).value(_KEY_ACTOR, "")
        _current_actor = stored.strip() if stored and stored.strip() else "staff"
    return _current_actor


def set_actor(name: str) -> None:
    global _current_actor
    _current_actor = name if name and name.strip() else "staff"
    QSettings(_ORG, _APP).setValue(_KEY_ACTOR, _current_actor)
