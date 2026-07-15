"""Quick fact verification backed by the public Wikipedia REST APIs.

Design goals (why the flow looks the way it does):

* **Resolve the entity, not the sentence.** A claim like "newton was a
  scientist" must land on the *Isaac Newton* article. Feeding the whole
  sentence to full-text search lets unrelated articles that happen to contain
  "scientist" outrank the real subject. So we first pull the *subject* out of
  the claim ("newton") and resolve that as a Wikipedia title.
* **Pick the candidate that actually fits.** Short entity names are ambiguous
  ("Newton" the unit vs. Isaac Newton). We fetch a few candidate summaries and
  score them against the claim, skipping disambiguation pages.
* **Never cry wolf.** A red "Not Supported" is only ever returned when the
  reference *contradicts* the claim (an explicit negation mismatch or a
  conflicting number/date). If we simply can't find a matching reference we say
  so ("couldn't confirm") instead of falsely calling a true statement false.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import List, Optional

import requests

from backend.models.schemas import VerifyResponse

logger = logging.getLogger(__name__)

SEARCH_URL = "https://en.wikipedia.org/w/api.php"
SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
_HEADERS = {"User-Agent": "PersonalizedNetworkingAssistant/1.0 (educational project)"}
_TIMEOUT = 8
_MAX_CANDIDATES = 5     # titles to consider
_MAX_SUMMARIES = 4      # summaries to actually fetch/score

_STOPWORDS = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "on",
              "and", "or", "to", "for", "with", "by", "that", "this", "it",
              "be", "been", "as", "at", "from", "has", "have", "used", "using",
              "who", "whom", "which", "what", "s"}

# Verbs/auxiliaries that separate a claim's subject from its predicate.
_AUX = (r"\b(is|was|are|were|be|been|being|am|has|have|had|will|would|shall|"
        r"does|did|do|can|could|should|becomes|became|remains|remained)\b")

# Common descriptor synonyms so "X was a scientist" matches a reference that
# describes X as a "physicist/mathematician/astronomer", etc. This is a small,
# transparent lexical aid -- not a substitute for a real entailment model, but
# it covers the everyday "is-a" claims people actually try first.
_SYNONYMS = {
    "scientist": {"scientist", "physicist", "mathematician", "chemist", "biologist",
                  "astronomer", "researcher", "philosopher", "polymath", "scholar",
                  "naturalist", "geologist"},
    "writer": {"writer", "author", "poet", "playwright", "novelist", "dramatist",
               "essayist", "journalist"},
    "politician": {"politician", "statesman", "stateswoman", "president", "senator",
                   "minister", "governor", "congressman", "congresswoman", "diplomat"},
    "artist": {"artist", "painter", "sculptor", "musician", "composer", "illustrator"},
    "actor": {"actor", "actress", "performer"},
    "athlete": {"athlete", "player", "footballer", "sportsman", "sportsperson",
                "cricketer", "boxer", "swimmer"},
    "inventor": {"inventor", "engineer", "pioneer", "innovator"},
    "leader": {"leader", "ruler", "king", "queen", "emperor", "president", "chief",
               "founder", "ceo"},
    "company": {"company", "corporation", "firm", "business", "enterprise",
                "manufacturer", "startup"},
    "country": {"country", "nation", "state", "republic", "kingdom"},
    "city": {"city", "town", "capital", "municipality", "metropolis"},
}


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("es") and not word.endswith(("ss", "us")):
        return word[:-2]
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _terms(text: str) -> set:
    return {_stem(w) for w in re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split()
            if len(w) > 2 and w not in _STOPWORDS}


def _expand(term: str) -> set:
    """Return ``term`` plus any descriptor synonyms it belongs to (all stemmed)."""
    for canon, syns in _SYNONYMS.items():
        if term == canon or term in syns:
            return {_stem(s) for s in syns} | {term}
    return {term}


def _subject(claim: str) -> str:
    """The subject of the claim -- the text before its first verb.

    "newton was a scientist"             -> "newton"
    "GPT-2 was released by OpenAI 2019"  -> "GPT-2"
    "Python programming language"        -> "Python programming language"
    """
    parts = re.split(_AUX, claim, maxsplit=1, flags=re.IGNORECASE)
    subj = parts[0].strip(" ,.-") if parts else claim
    return subj if subj else claim


def _first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.?!])(\s|$)", text or "")
    return m.group(1) if m else (text or "")


class FactChecker:
    """Looks up a topic on Wikipedia and returns a summarized, sanity-checked
    reference plus a conservative verdict."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(_HEADERS)

    # ------------------------------------------------------------------ #
    def verify(self, query: str) -> VerifyResponse:
        query = (query or "").strip()
        if not query:
            return VerifyResponse(query=query, found=False, verdict="not_found",
                                  explanation="No claim was provided.")

        subject = _subject(query)
        candidates = self._candidate_titles(query, subject)
        if not candidates:
            return VerifyResponse(query=query, found=False, verdict="not_found",
                                  explanation="No reference article was found for this claim.")

        # Fetch summaries for the top candidates and choose the one that best
        # fits the claim -- this is what "check it before showing the user"
        # means: we don't trust the first search hit blindly.
        summary = self._best_reference(query, subject, candidates)
        if summary is None:
            return VerifyResponse(query=query, found=False, verdict="not_found",
                                  explanation="A reference matched but no usable summary could be retrieved.")

        extract = summary.get("extract", "")
        verdict, explanation, correct_info, confidence = self._judge(query, subject, extract)

        return VerifyResponse(
            query=query,
            found=True,
            verdict=verdict,
            explanation=explanation,
            correct_info=correct_info,
            confidence=confidence,
            title=summary.get("title"),
            summary=extract,
            url=summary.get("content_urls", {}).get("desktop", {}).get("page"),
        )

    # ------------------------------------------------------------------ #
    # Candidate resolution
    # ------------------------------------------------------------------ #
    def _candidate_titles(self, query: str, subject: str) -> List[str]:
        """Ordered, de-duplicated candidate article titles.

        Title/prefix search on the *subject* comes first (best for resolving a
        named entity like "Isaac Newton"); full-text search on the whole claim
        is a fallback that catches non-entity or descriptive claims.
        """
        titles: List[str] = []
        for t in list(self._opensearch(subject)) + list(self._fulltext(query)):
            if t and t not in titles:
                titles.append(t)
        return titles[:_MAX_CANDIDATES]

    def _best_reference(self, query: str, subject: str, titles: List[str]) -> Optional[dict]:
        claim_terms = _terms(query)
        subj_terms = _terms(subject)

        best_summary, best_score = None, float("-inf")
        first_ok = None
        for title in titles[:_MAX_SUMMARIES]:
            summary = self._fetch_summary(title)
            if not summary or not summary.get("extract"):
                continue
            if first_ok is None:
                first_ok = summary
            if (summary.get("type") or "").lower() == "disambiguation":
                continue  # never adjudicate against a disambiguation stub

            title_terms = _terms(summary.get("title", ""))
            first_terms = _terms(_first_sentence(summary.get("extract", "")))

            # Subject must be recognisable in the article for it to count as a
            # real match. Score also rewards predicate/claim overlap so that,
            # among "Newton" candidates, the one the claim is really about wins.
            subj_hits = len(subj_terms & (title_terms | first_terms))
            claim_hits = len(claim_terms & _terms(summary.get("extract", "")))
            score = subj_hits * 3 + claim_hits
            if score > best_score:
                best_summary, best_score = summary, score

        # If nothing cleanly matched the subject, still return the first usable
        # summary so the user sees the closest reference (the verdict layer will
        # correctly mark it "uncertain" rather than confidently wrong).
        return best_summary if best_summary is not None else first_ok

    # ------------------------------------------------------------------ #
    # Verdict
    # ------------------------------------------------------------------ #
    @staticmethod
    def _judge(claim: str, subject: str, reference: str) -> tuple:
        """Conservative adjudication. Returns (verdict, explanation, correct_info, confidence).

        Verdicts:
          valid     - the reference supports the claim.
          invalid   - the reference *contradicts* the claim (negation mismatch
                      or conflicting number/date). This is the ONLY path to a
                      red result, so we never call a true statement false just
                      because wording didn't overlap.
          uncertain - right subject but the specific detail isn't confirmed, OR
                      we couldn't find a reference clearly about the subject.
        """
        claim_terms = _terms(claim)
        ref_terms = _terms(reference)
        subj_terms = _terms(subject)
        if not claim_terms:
            return "uncertain", "The claim was too short to evaluate.", "", 0.0

        overlap = claim_terms & ref_terms
        confidence = round(len(overlap) / len(claim_terms), 2)
        correction = f"According to the reference: {reference[:280]}"

        subject_matched = bool(subj_terms & ref_terms) or not subj_terms

        # Predicate = what the claim asserts about the subject.
        predicate_terms = claim_terms - subj_terms
        if predicate_terms:
            supported = {t for t in predicate_terms if _expand(t) & ref_terms}
            pred_ratio = len(supported) / len(predicate_terms)
        else:
            pred_ratio = 1.0 if subject_matched else 0.0

        negated = bool(re.search(r"\b(not|never|no|isn't|aren't|wasn't|weren't|"
                                 r"doesn't|didn't|false|untrue)\b", claim.lower()))

        claim_numbers = set(re.findall(r"\b\d{3,4}\b", claim))
        ref_numbers = set(re.findall(r"\b\d{3,4}\b", reference))
        number_conflict = bool(claim_numbers) and bool(ref_numbers) and not (claim_numbers & ref_numbers)

        # ---- contradiction paths (the only way to a red verdict) ---------- #
        if subject_matched and negated and pred_ratio >= 0.5:
            return ("invalid",
                    "The reference confirms what the claim denies -- the source supports "
                    "the very fact the claim negates.",
                    correction, confidence)
        if subject_matched and number_conflict:
            return ("invalid",
                    f"The claim cites {', '.join(sorted(claim_numbers))}, but the reference "
                    f"cites {', '.join(sorted(ref_numbers))} instead.",
                    correction, confidence)

        # ---- couldn't confirm the right subject --------------------------- #
        if not subject_matched:
            return ("uncertain",
                    "Couldn't find a reference clearly about this claim's subject. "
                    "The closest match is shown below -- please verify it yourself.",
                    correction, confidence)

        # ---- subject matched: judge the predicate ------------------------- #
        if pred_ratio >= 0.5:
            if negated:  # negating something the source does NOT support -> can't confirm
                return ("uncertain",
                        "The reference is about the right subject but doesn't clearly settle "
                        "this negative claim. Review the source below.",
                        correction, confidence)
            return ("valid",
                    "The reference supports the claim.",
                    "", confidence)

        return ("uncertain",
                "The reference is about the right subject but doesn't clearly confirm this "
                "specific detail. Review the source below to judge it.",
                correction, confidence)

    # ------------------------------------------------------------------ #
    # HTTP helpers
    # ------------------------------------------------------------------ #
    @lru_cache(maxsize=256)
    def _opensearch(self, subject: str) -> tuple:
        """Title/prefix search -- excellent at resolving a named entity."""
        subject = (subject or "").strip()
        if not subject:
            return tuple()
        try:
            resp = self.session.get(
                SEARCH_URL,
                params={"action": "opensearch", "search": subject,
                        "limit": _MAX_CANDIDATES, "namespace": 0, "format": "json"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return tuple(data[1]) if len(data) > 1 and data[1] else tuple()
        except Exception as exc:
            logger.warning("Wikipedia opensearch failed: %s", exc)
            return tuple()

    @lru_cache(maxsize=256)
    def _fulltext(self, query: str) -> tuple:
        """Full-text search -- fallback for descriptive / non-entity claims."""
        try:
            resp = self.session.get(
                SEARCH_URL,
                params={"action": "query", "list": "search", "srsearch": query,
                        "srlimit": _MAX_CANDIDATES, "srnamespace": 0,
                        "srprop": "snippet", "format": "json"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = (data.get("query", {}) or {}).get("search", []) or []
            return tuple(h.get("title") for h in hits if h.get("title"))
        except Exception as exc:
            logger.warning("Wikipedia search failed: %s", exc)
            return tuple()

    @lru_cache(maxsize=256)
    def _fetch_summary(self, title: str) -> Optional[dict]:
        try:
            resp = self.session.get(SUMMARY_URL.format(title=title.replace(" ", "_")), timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Wikipedia summary failed: %s", exc)
            return None


@lru_cache(maxsize=1)
def get_fact_checker() -> FactChecker:
    return FactChecker()
