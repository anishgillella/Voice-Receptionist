"""Simple in-memory session store for the MVP."""

from collections import defaultdict
from typing import DefaultDict, List


SessionHistory = List[dict]


class SessionStore:
    def __init__(self) -> None:
        self._history: DefaultDict[str, SessionHistory] = defaultdict(list)

    def append(self, session_id: str, role: str, content: str) -> None:
        self._history[session_id].append({"role": role, "content": content})

    def get(self, session_id: str) -> SessionHistory:
        return self._history.get(session_id, [])

    def clear(self, session_id: str) -> None:
        self._history.pop(session_id, None)


session_store = SessionStore()


