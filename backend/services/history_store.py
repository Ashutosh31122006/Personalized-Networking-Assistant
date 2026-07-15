"""Local data store for conversation history and feedback.

A simple, thread-safe JSON file store (``data/history.json``). Each generated
starter becomes one history entry; feedback (thumbs up/down) is attached to
the entry by starter id. Doubles as the interaction log for auditing.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.models.schemas import HistoryEntry, Starter

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "history.json"


class HistoryStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write([])

    # ------------------------------------------------------------------ #
    # Low-level helpers
    # ------------------------------------------------------------------ #
    def _read(self) -> List[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, entries: List[dict]) -> None:
        self.path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def log_starters(self, event_description: str, interests: List[str], starters: List[Starter]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            entries = self._read()
            for starter in starters:
                entries.append(
                    HistoryEntry(
                        id=starter.id,
                        timestamp=now,
                        event_description=event_description,
                        interests=interests,
                        themes=starter.themes,
                        starter_text=starter.text,
                        useful=None,
                    ).model_dump()
                )
            self._write(entries)

    def record_feedback(self, starter_id: str, useful: bool) -> bool:
        """Attach feedback to an entry. Returns True if the entry existed."""
        with self._lock:
            entries = self._read()
            for entry in entries:
                if entry["id"] == starter_id:
                    entry["useful"] = useful
                    self._write(entries)
                    return True
        return False

    def delete_entry(self, starter_id: str) -> bool:
        """Remove a single entry by its starter ID. Returns True if found."""
        with self._lock:
            entries = self._read()
            filtered = [e for e in entries if e["id"] != starter_id]
            if len(filtered) < len(entries):
                self._write(filtered)
                return True
        return False

    def list_entries(self, only_useful: bool = False) -> List[HistoryEntry]:
        entries = [HistoryEntry(**e) for e in self._read()]
        if only_useful:
            entries = [e for e in entries if e.useful is True]
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)

    def stats(self) -> dict:
        entries = self._read()
        return {
            "total": len(entries),
            "useful_count": sum(1 for e in entries if e.get("useful") is True),
        }

    def clear(self) -> None:
        with self._lock:
            self._write([])


_store: Optional[HistoryStore] = None


def get_history_store() -> HistoryStore:
    global _store
    if _store is None:
        _store = HistoryStore()
    return _store
