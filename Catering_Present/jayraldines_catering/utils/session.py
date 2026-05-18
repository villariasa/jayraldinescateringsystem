"""
App session singleton — stores the current logged-in actor name.
Import get_actor() wherever audit logging needs a username.
"""

_current_actor: str = "staff"


def get_actor() -> str:
    return _current_actor


def set_actor(name: str) -> None:
    global _current_actor
    _current_actor = name if name and name.strip() else "staff"
