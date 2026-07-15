"""Starter Validation Service.

Implements the "validate before showing" step: a generated conversation
starter is only surfaced to the user if it is genuinely *related to the event
topic*. This guards against the language model drifting off-topic or producing
a generic question that ignores the event.

Mechanism (offline, deterministic): re-run theme extraction on each candidate
starter and confirm it shares at least one theme (or a meaningful keyword) with
the event's themes. This mirrors how the diagram's Fact Verification / logic
layer checks output against the analyzed themes before it reaches the UI.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from backend.models.schemas import Starter, ThemeResult
from backend.services.theme_extractor import ThemeExtractor

_STOP = {
    "what", "whats", "your", "you", "the", "that", "this", "with", "from", "about",
    "have", "has", "how", "why", "when", "who", "into", "most", "will", "would",
    "think", "space", "field", "work", "right", "now", "one", "and", "for", "are",
}


class StarterValidator:
    def __init__(self, extractor: ThemeExtractor):
        self.extractor = extractor

    # ------------------------------------------------------------------ #
    @staticmethod
    def _keywords(text: str) -> set:
        words = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
        return {w for w in words if len(w) > 3 and w not in _STOP}

    def is_on_topic(self, starter_text: str, event_themes: List[ThemeResult], event_description: str) -> bool:
        """True if the starter is related to the event's themes/topic."""
        theme_labels = {t.label.lower() for t in event_themes}
        text_lower = starter_text.lower()

        # (1) direct theme-label mention
        if any(label in text_lower for label in theme_labels):
            return True

        # (2) shared theme after re-classifying the starter itself
        starter_themes = {t.label.lower() for t in self.extractor.extract(starter_text, top_k=4)}
        if starter_themes & theme_labels:
            return True

        # (3) keyword overlap with the event description
        overlap = self._keywords(starter_text) & self._keywords(event_description)
        return len(overlap) >= 1

    def validate(
        self,
        starters: List[Starter],
        event_themes: List[ThemeResult],
        event_description: str,
    ) -> Tuple[List[Starter], int]:
        """Return (on_topic_starters, rejected_count).

        Performance note: the cheap checks (direct theme mention, keyword
        overlap) are tried first for every candidate. Only candidates that
        fail both are sent to the classifier -- and all of them go together
        in a single batched call, rather than one classifier call per
        candidate. Re-running zero-shot classification once per starter was
        the dominant cost in `/generate` requests.
        """
        theme_labels = {t.label.lower() for t in event_themes}
        event_keywords = self._keywords(event_description)

        verdicts: List[Optional[bool]] = [None] * len(starters)
        ambiguous_idx: List[int] = []
        ambiguous_text: List[str] = []

        for i, s in enumerate(starters):
            text_lower = s.text.lower()
            if any(label in text_lower for label in theme_labels):
                verdicts[i] = True
                continue
            if self._keywords(s.text) & event_keywords:
                verdicts[i] = True
                continue
            ambiguous_idx.append(i)
            ambiguous_text.append(s.text)

        if ambiguous_text:
            batch_themes = self.extractor.extract_batch(ambiguous_text, top_k=4)
            for idx, themes in zip(ambiguous_idx, batch_themes):
                starter_themes = {t.label.lower() for t in themes}
                verdicts[idx] = bool(starter_themes & theme_labels)

        kept: List[Starter] = []
        rejected = 0
        for s, ok in zip(starters, verdicts):
            s.on_topic = bool(ok)
            if ok:
                kept.append(s)
            else:
                rejected += 1

        # Never return an empty list solely due to validation -- fall back to
        # the original candidates (flagged) so the user always gets something.
        if not kept and starters:
            for s in starters:
                s.on_topic = False
            return starters, rejected
        return kept, rejected


def get_starter_validator(extractor: ThemeExtractor) -> StarterValidator:
    return StarterValidator(extractor)
