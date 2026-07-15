"""Theme extraction from event descriptions.

Primary engine: DistilBERT zero-shot classification
(``typeform/distilbert-base-uncased-mnli``) via HuggingFace ``transformers``.

If ``transformers``/``torch`` are unavailable (or the model cannot be
downloaded), the service degrades gracefully to a keyword-based extractor so
the application remains usable offline and unit-testable without GPU/network.
"""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import List, Optional

from backend.models.schemas import ThemeResult

logger = logging.getLogger(__name__)

# Candidate labels the zero-shot classifier scores against.
CANDIDATE_THEMES: List[str] = [
    "artificial intelligence",
    "sustainability",
    "healthcare",
    "finance",
    "education",
    "urban planning",
    "climate change",
    "blockchain",
    "entrepreneurship",
    "software engineering",
    "data science",
    "marketing",
    "design",
    "policy and government",
    "social impact",
]

# Keyword map used by the offline fallback extractor.
_KEYWORDS = {
    "artificial intelligence": ["ai", "artificial intelligence", "machine learning", "ml", "neural", "llm", "gpt"],
    "sustainability": ["sustainable", "sustainability", "green", "renewable", "eco"],
    "healthcare": ["health", "healthcare", "medical", "medicine", "clinical", "patient"],
    "finance": ["finance", "financial", "fintech", "banking", "investment", "trading"],
    "education": ["education", "learning", "edtech", "school", "university", "teaching"],
    "urban planning": ["urban", "city", "cities", "smart city", "infrastructure", "transit"],
    "climate change": ["climate", "carbon", "emissions", "warming", "net zero"],
    "blockchain": ["blockchain", "crypto", "web3", "ledger", "defi", "nft"],
    "entrepreneurship": ["startup", "founder", "entrepreneur", "venture", "vc", "pitch"],
    "software engineering": ["software", "developer", "engineering", "code", "devops", "cloud"],
    "data science": ["data", "analytics", "statistics", "big data", "dataset"],
    "marketing": ["marketing", "brand", "growth", "seo", "advertising"],
    "design": ["design", "ux", "ui", "product design", "creative"],
    "policy and government": ["policy", "regulation", "government", "public sector", "law"],
    "social impact": ["nonprofit", "social impact", "community", "ngo", "equity"],
}


class ThemeExtractor:
    """Extracts the top themes from free text."""

    def __init__(self, use_model: bool | None = None):
        # DistilBERT zero-shot is OFF by default (slow to download/run on CPU).
        # The keyword extractor below is instant. Set PNA_USE_MODELS=1 to opt in.
        if use_model is None:
            use_model = os.environ.get("PNA_USE_MODELS", "0").lower() in ("1", "true", "yes")
        self._pipeline = None
        self._use_model = use_model

    # ------------------------------------------------------------------ #
    # Model loading
    # ------------------------------------------------------------------ #
    def _load_pipeline(self):
        """Lazily load the zero-shot classification pipeline."""
        if self._pipeline is not None or not self._use_model:
            return self._pipeline
        try:
            from transformers import pipeline  # heavy import, done lazily

            self._pipeline = pipeline(
                "zero-shot-classification",
                model="typeform/distilbert-base-uncased-mnli",
            )
            logger.info("Loaded DistilBERT zero-shot pipeline.")
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("DistilBERT unavailable (%s); using keyword fallback.", exc)
            self._use_model = False
        return self._pipeline

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def extract(
        self,
        text: str,
        extra_labels: Optional[List[str]] = None,
        top_k: int = 4,
        threshold: float = 0.10,
    ) -> List[ThemeResult]:
        """Return up to ``top_k`` themes with confidence scores (descending)."""
        if not text or not text.strip():
            return []

        labels = list(dict.fromkeys(CANDIDATE_THEMES + [l.lower() for l in (extra_labels or []) if l.strip()]))

        pipe = self._load_pipeline()
        if pipe is not None:
            result = pipe(text, candidate_labels=labels, multi_label=True)
            pairs = zip(result["labels"], result["scores"])
            themes = [ThemeResult(label=l, score=round(float(s), 4)) for l, s in pairs if s >= threshold]
            return themes[:top_k]

        return self._keyword_extract(text, labels, top_k)

    # ------------------------------------------------------------------ #
    # Batch API -- classify many texts in a single pipeline call instead of
    # looping (looping was the main cost behind slow starter generation,
    # since each call re-scores every candidate label from scratch).
    # ------------------------------------------------------------------ #
    def extract_batch(
        self,
        texts: List[str],
        extra_labels: Optional[List[str]] = None,
        top_k: int = 4,
        threshold: float = 0.10,
    ) -> List[List[ThemeResult]]:
        """Return themes for each text in ``texts``, preserving order."""
        if not texts:
            return []

        labels = list(dict.fromkeys(CANDIDATE_THEMES + [l.lower() for l in (extra_labels or []) if l.strip()]))

        pipe = self._load_pipeline()
        if pipe is not None:
            raw_results = pipe(texts, candidate_labels=labels, multi_label=True)
            if isinstance(raw_results, dict):  # a single-text batch still returns a dict
                raw_results = [raw_results]
            out: List[List[ThemeResult]] = []
            for result in raw_results:
                pairs = zip(result["labels"], result["scores"])
                themes = [ThemeResult(label=l, score=round(float(s), 4)) for l, s in pairs if s >= threshold]
                out.append(themes[:top_k])
            return out

        return [self._keyword_extract(t, labels, top_k) for t in texts]

    # ------------------------------------------------------------------ #
    # Offline fallback
    # ------------------------------------------------------------------ #
    @staticmethod
    def _keyword_extract(text: str, labels: List[str], top_k: int) -> List[ThemeResult]:
        lowered = f" {re.sub(r'[^a-z0-9 ]', ' ', text.lower())} "
        scored = []
        for label in labels:
            keywords = _KEYWORDS.get(label, [label])
            hits = sum(1 for kw in keywords if f" {kw} " in lowered or kw in lowered.split())
            if hits:
                scored.append(ThemeResult(label=label, score=round(min(0.99, 0.4 + 0.15 * hits), 4)))
        scored.sort(key=lambda t: t.score, reverse=True)
        return scored[:top_k]


@lru_cache(maxsize=1)
def get_theme_extractor() -> ThemeExtractor:
    """FastAPI dependency -- one shared instance per process."""
    return ThemeExtractor()
