"""Simple in-memory session store for the MVP."""

from collections import defaultdict
from datetime import datetime
from typing import Any, DefaultDict, Dict, List

from .config import get_settings


SessionHistory = List[dict]


class SessionStore:
    def __init__(self) -> None:
        self._history: DefaultDict[str, SessionHistory] = defaultdict(list)

    def append(
        self, session_id: str, role: str, content: str, metadata: Dict[str, Any] | None = None
    ) -> None:
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            entry["metadata"] = metadata
        self._history[session_id].append(entry)

        if get_settings().transcript_debug:
            print(f"[{session_id}][{role}] {content}")

    def get(self, session_id: str) -> SessionHistory:
        return self._history.get(session_id, [])

    def clear(self, session_id: str) -> None:
        self._history.pop(session_id, None)


session_store = SessionStore()


