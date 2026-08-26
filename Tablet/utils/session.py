"""Tablet session — which staff member is currently operating the tablet."""
from PySide6.QtCore import QSettings

_ORG, _APP = "Jayraldines", "CateringTablet"
_KEY_ACTOR = "session/actor_name"

_current_actor: str = ""


def get_actor() -> str:
    global _current_actor
    if not _current_actor:
        stored = QSettings(_ORG, _APP).value(_KEY_ACTOR, "")
        _current_actor = stored.strip() if stored and stored.strip() else "Tablet Staff"
    return _current_actor


def set_actor(name: str) -> None:
    global _current_actor
    _current_actor = name if name and name.strip() else "Tablet Staff"
    QSettings(_ORG, _APP).setValue(_KEY_ACTOR, _current_actor)
