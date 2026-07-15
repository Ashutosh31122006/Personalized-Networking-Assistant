"""History & feedback endpoints (Scenario 3: Reviewing Past Strategies).

The History Logger records what was generated; the Feedback Logger keeps an
immutable audit trail of user reactions. Posting feedback updates the history
entry's ``useful`` flag AND appends an event to the feedback log.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.schemas import (
    FeedbackRequest,
    FeedbackStats,
    HistoryResponse,
)
from backend.services.history_store import HistoryStore, get_history_store
from backend.services.feedback_logger import FeedbackLogger, get_feedback_logger

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoryResponse)
def get_history(
    only_useful: bool = Query(default=False),
    store: HistoryStore = Depends(get_history_store),
) -> HistoryResponse:
    entries = store.list_entries(only_useful=only_useful)
    stats = store.stats()
    return HistoryResponse(entries=entries, total=stats["total"], useful_count=stats["useful_count"])


@router.delete("/history", status_code=200)
def clear_history(
    store: HistoryStore = Depends(get_history_store),
) -> dict:
    """Permanently delete every logged history entry.

    Deliberately does NOT touch the feedback audit log: the Feedback Logger
    is designed to be an immutable event stream that survives even if the
    history it originated from is pruned (see feedback_logger.py).
    """
    store.clear()
    return {"ok": True, "message": "History cleared."}


@router.delete("/history/{starter_id}", status_code=200)
def delete_history_entry(
    starter_id: str,
    store: HistoryStore = Depends(get_history_store),
) -> dict:
    """Delete a single history entry by its starter ID."""
    removed = store.delete_entry(starter_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"No history entry with id '{starter_id}'")
    return {"ok": True, "message": f"Entry '{starter_id}' deleted."}


@router.post("/feedback", status_code=200)
def post_feedback(
    payload: FeedbackRequest,
    store: HistoryStore = Depends(get_history_store),
    feedback_log: FeedbackLogger = Depends(get_feedback_logger),
) -> dict:
    updated = store.record_feedback(payload.starter_id, payload.useful)
    if not updated:
        raise HTTPException(status_code=404, detail=f"No starter with id '{payload.starter_id}'")
    event = feedback_log.log(payload.starter_id, payload.useful)  # audit trail
    return {"ok": True, "starter_id": payload.starter_id, "useful": payload.useful,
            "logged_at": event.timestamp}


@router.get("/feedback/stats", response_model=FeedbackStats)
def feedback_stats(
    feedback_log: FeedbackLogger = Depends(get_feedback_logger),
) -> FeedbackStats:
    return feedback_log.stats()
