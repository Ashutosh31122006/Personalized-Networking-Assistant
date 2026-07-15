"""Pydantic schemas shared by all API routes."""
from typing import List, Optional
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Payload for POST /api/v1/generate."""
    event_description: str = Field(..., min_length=3, max_length=2000)
    user_bio: Optional[str] = Field(default="", max_length=2000)
    interests: List[str] = Field(default_factory=list)
    num_starters: int = Field(default=3, ge=1, le=5)


class ThemeResult(BaseModel):
    """A single theme extracted by the zero-shot classifier."""
    label: str
    score: float


class Starter(BaseModel):
    """One generated conversation starter."""
    id: str
    text: str
    themes: List[str]
    on_topic: bool = True  # set by the validation pass before display


class GenerateResponse(BaseModel):
    themes: List[ThemeResult]
    starters: List[Starter]
    engine: str  # "gpt2" or "template-fallback"
    rejected: int = 0  # candidates dropped by validation for being off-topic


class VerifyResponse(BaseModel):
    """Payload for GET /api/v1/verify.

    ``verdict`` is the claim-checking result:
      - "valid"      : the claim is supported by the reference
      - "invalid"    : the claim contradicts / is unsupported by the reference
      - "uncertain"  : not enough evidence to decide
      - "not_found"  : no reference located
    """
    query: str
    found: bool
    verdict: str = "not_found"
    explanation: str = ""
    correct_info: str = ""
    confidence: float = 0.0  # term-overlap ratio behind the verdict, 0.0-1.0
    title: Optional[str] = None
    summary: Optional[str] = None
    url: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Thumbs up / down on a starter."""
    starter_id: str
    useful: bool


class HistoryEntry(BaseModel):
    id: str
    timestamp: str
    event_description: str
    interests: List[str]
    themes: List[str]
    starter_text: str
    useful: Optional[bool] = None  # None = no feedback yet


class HistoryResponse(BaseModel):
    entries: List[HistoryEntry]
    total: int
    useful_count: int


class FeedbackEvent(BaseModel):
    """One immutable feedback record written by the Feedback Logger Service."""
    starter_id: str
    useful: bool
    timestamp: str


class FeedbackStats(BaseModel):
    total_feedback: int
    useful: int
    not_useful: int
    useful_rate: float  # useful / total_feedback, 0.0 when no feedback yet
