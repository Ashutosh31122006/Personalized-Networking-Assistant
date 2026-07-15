"""Feedback Logger Service.

Separate from the History Logger: while the History Logger owns the record of
*what was generated*, the Feedback Logger owns an append-only audit trail of
*how users reacted* (thumbs up / down). Keeping them apart means feedback is an
immutable event stream — useful for auditing, analytics, and (later) retraining
personalization — even if history entries are edited or pruned.

Storage: ``data/feedback_log.json`` — a list of append-only feedback events.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.models.schemas import FeedbackEvent, FeedbackStats

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "feedback_log.json"


class FeedbackLogger:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write([])

    # ------------------------------------------------------------------ #
    def _read(self) -> List[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, events: List[dict]) -> None:
        self.path.write_text(json.dumps(events, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    def log(self, starter_id: str, useful: bool) -> FeedbackEvent:
        """Append one feedback event and return it."""
        event = FeedbackEvent(
            starter_id=starter_id,
            useful=useful,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            events = self._read()
            events.append(event.model_dump())
            self._write(events)
        return event

    def events(self, starter_id: Optional[str] = None) -> List[FeedbackEvent]:
        events = [FeedbackEvent(**e) for e in self._read()]
        if starter_id is not None:
            events = [e for e in events if e.starter_id == starter_id]
        return events

    def stats(self) -> FeedbackStats:
        events = self._read()
        total = len(events)
        useful = sum(1 for e in events if e.get("useful") is True)
        return FeedbackStats(
            total_feedback=total,
            useful=useful,
            not_useful=total - useful,
            useful_rate=round(useful / total, 4) if total else 0.0,
        )

    def clear(self) -> None:
        with self._lock:
            self._write([])


_logger: Optional[FeedbackLogger] = None


def get_feedback_logger() -> FeedbackLogger:
    global _logger
    if _logger is None:
        _logger = FeedbackLogger()
    return _logger
