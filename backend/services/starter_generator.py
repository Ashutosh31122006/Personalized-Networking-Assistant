"""Conversation-starter generation.

Primary engine: GPT-2 text generation via HuggingFace ``transformers``.
Fallback: curated templates filled with the extracted themes, so the app
still produces useful starters when the model isn't available.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from functools import lru_cache
from typing import List
import random

from backend.models.schemas import Starter, ThemeResult

logger = logging.getLogger(__name__)

_TEMPLATES = {
    "thought_provoking": [
        "What's a bold prediction you have about {a} that most people would disagree with?",
        "If {a} didn't exist today, what problem would be the hardest to solve?",
        "What's the most counterintuitive lesson you've learned working in {a}?",
        "If you had unlimited resources, what's the first thing you'd change about {a}?",
        "What question about {a} keeps you up at night?",
    ],
    "experience_sharing": [
        "What's a 'behind the scenes' moment in {a} that outsiders rarely hear about?",
        "Can you share a time when {b} completely changed your perspective on something?",
        "What's the best piece of advice you've received about working in {a}?",
        "What was your 'aha moment' that made you passionate about {b}?",
        "What failure in {a} taught you the most valuable lesson?",
    ],
    "future_oriented": [
        "What emerging trend in {a} do you think is being underestimated right now?",
        "How do you see {a} and {b} converging in the next few years?",
        "What's one technology or idea in {a} that could be a complete game-changer?",
        "If you were starting fresh in {a} today, what would you do differently?",
        "What skill related to {b} do you think will be most valuable in five years?",
    ],
    "personal_connection": [
        "I noticed this event focuses on {a} -- what first drew you to that space?",
        "What project involving {a} are you most excited about right now?",
        "How has your thinking about {b} evolved since you first got involved?",
        "What's something about {a} you wish you'd known when you started out?",
        "Who in the {b} space has influenced your thinking the most, and why?",
    ],
    "contrarian_debate": [
        "What's a popular opinion about {a} that you actually disagree with?",
        "Do you think {b} is overhyped, underhyped, or just right -- and why?",
        "If you had to argue against {a}, what would your strongest point be?",
        "What's the biggest risk everyone in {b} seems to be ignoring?",
        "What's an unpopular take on {a} that you think deserves more attention?",
    ],
}

# Two worked examples that prime GPT-2 to continue with a single, on-topic,
# well-formed question instead of rambling off into unrelated text. Small,
# non-instruction-tuned models like GPT-2 are much more reliable when the
# prompt already shows the exact pattern we want repeated (few-shot priming)
# than when asked cold to "write a question about X".
_FEW_SHOT = (
    'Event: Green Fintech Forum -- a conference on sustainable investment technology.\n'
    'Key themes: finance, sustainability\n'
    'Great conversation-starter question: "What is the biggest hurdle you have seen in '
    'getting sustainable investing tools adopted at scale?"\n'
    "\n"
    'Event: Frontiers in Robotics -- an expo on next-generation automation.\n'
    'Key themes: software engineering, artificial intelligence\n'
    'Great conversation-starter question: "What robotics application do you think is '
    'still years away from being practical?"\n'
    "\n"
)

# Signs the model has looped back into repeating the prompt structure instead
# of producing a real answer -- a common small-LM failure mode. Any candidate
# containing one of these is discarded outright rather than trimmed.
_LEAK_MARKERS = ("event:", "key themes:", "attendee background:", "great conversation")

# Words/phrases that signal the text is phrased as a question even if it got
# truncated before picking up its own "?".
_QUESTION_STARTERS = (
    "what", "how", "why", "when", "who", "which", "would", "could", "can",
    "do you", "does", "did", "is", "are", "was", "were", "should", "will",
    "have you", "has", "if you",
)


class StarterGenerator:
    """Generates 1-5 context-aware conversation starters."""

    def __init__(self, use_model: bool | None = None):
        # Heavy GPT-2 generation is OFF by default: downloading + running it on
        # CPU took many seconds per request. The curated templates below are
        # instant and produce clean, on-topic questions. Set PNA_USE_MODELS=1
        # to opt back into GPT-2.
        if use_model is None:
            use_model = os.environ.get("PNA_USE_MODELS", "0").lower() in ("1", "true", "yes")
        self._generator = None
        self._use_model = use_model
        self.engine = "template-fallback"

    # ------------------------------------------------------------------ #
    def _load_pipeline(self):
        if self._generator is not None or not self._use_model:
            return self._generator
        try:
            from transformers import pipeline

            self._generator = pipeline("text-generation", model="gpt2")
            self.engine = "gpt2"
            logger.info("Loaded GPT-2 generation pipeline.")
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("GPT-2 unavailable (%s); using template fallback.", exc)
            self._use_model = False
        return self._generator

    # ------------------------------------------------------------------ #
    def generate(
        self,
        event_description: str,
        user_bio: str,
        themes: List[ThemeResult],
        num_starters: int = 3,
    ) -> List[Starter]:
        theme_labels = [t.label for t in themes] or ["this field"]
        gen = self._load_pipeline()

        texts: List[str]
        if gen is not None:
            texts = self._model_generate(gen, event_description, user_bio, theme_labels, num_starters)
        else:
            texts = self._template_generate(theme_labels, num_starters)

        return [
            Starter(id=uuid.uuid4().hex[:12], text=t, themes=theme_labels)
            for t in texts[:num_starters]
        ]

    # ------------------------------------------------------------------ #
    def _model_generate(self, gen, event: str, bio: str, themes: List[str], n: int) -> List[str]:
        prompt = (
            _FEW_SHOT +
            f"Event: {event}\n"
            f"Attendee background: {bio or 'a curious professional'}\n"
            f"Key themes: {', '.join(themes)}\n"
            f'Great conversation-starter question: "'
        )
        # Oversample just enough to survive cleaning/validation, capped so a
        # single request never triggers a large batch of GPT-2 samples (the
        # previous max(n*2, 4) could balloon to 14 sequences and dominate
        # generation latency).
        num_return_sequences = min(n + 2, 6)
        outputs = gen(
            prompt,
            max_new_tokens=40,
            num_return_sequences=num_return_sequences,
            do_sample=True,
            top_p=0.9,
            temperature=0.75,
            repetition_penalty=1.3,
            no_repeat_ngram_size=3,
            pad_token_id=50256,
        )
        cleaned = []
        for out in outputs:
            text = out["generated_text"][len(prompt):]
            text = self._clean(text)
            if text and text not in cleaned:
                cleaned.append(text)
            if len(cleaned) >= n:
                break
        # Top up with templates if the model output was too noisy.
        if len(cleaned) < n:
            cleaned += self._template_generate(themes, n - len(cleaned))
        return cleaned

    @staticmethod
    def _clean(text: str) -> str:
        """Keep the first well-formed question and normalise whitespace.

        Cuts off at the first closing quote or newline (the prompt asks the
        model to answer inside a quoted string, so anything past that is
        either rambling continuation or the model starting a new example),
        discards output that leaked the prompt's own scaffolding, discards
        degenerate/repetitive text, and discards plain statements dressed up
        as questions (a period/no-punctuation ramble that doesn't read like
        an interrogative is a common GPT-2 failure mode -- forcing a "?" on
        the end of it just hides the problem instead of fixing it).
        """
        cut_points = [i for i in (text.find("\n"), text.find('"')) if i != -1]
        if cut_points:
            text = text[:min(cut_points)]

        text = re.sub(r"\s+", " ", text).strip().strip('"').strip()
        if not text:
            return ""

        if any(marker in text.lower() for marker in _LEAK_MARKERS):
            return ""

        match = re.search(r"^(.{15,180}?[.?!])", text)
        if match:
            text = match.group(1).strip()

        looks_like_question = "?" in text or text.lower().startswith(_QUESTION_STARTERS)

        if not text.endswith(("?", ".", "!")):
            if not looks_like_question:
                return ""  # truncated and doesn't read like a question -- discard rather than fake it
            text = text.rstrip(",;: ") + "?"
        elif not text.endswith("?") and not looks_like_question:
            return ""  # a declarative statement, not a conversation-starter question

        if len(text) < 15:
            return ""

        # Reject degenerate/repetitive output (e.g. "the the the the ...").
        words = [w for w in re.sub(r"[^a-z0-9' ]", " ", text.lower()).split() if w]
        if len(words) > 4 and len(set(words)) / len(words) < 0.5:
            return ""

        return text

    @staticmethod
    def _template_generate(themes: List[str], n: int) -> List[str]:
        a = themes[0]
        b = themes[1] if len(themes) > 1 else themes[0]
        all_templates = [tpl for category in _TEMPLATES.values() for tpl in category]

        # Guarantee the primary theme ({a}) shows up at least once, then fill
        # the rest at random for variety. Sampling blindly could otherwise pick
        # only {b}-based templates and never mention the main theme.
        primary = [t for t in all_templates if "{a}" in t]
        rest = [t for t in all_templates if "{a}" not in t]

        selected: List[str] = []
        if primary and n > 0:
            selected.append(random.choice(primary))
        pool = [t for t in all_templates if t not in selected]
        random.shuffle(pool)
        selected += pool[: max(0, n - len(selected))]
        random.shuffle(selected)
        return [tpl.format(a=a, b=b) for tpl in selected[:n]]


@lru_cache(maxsize=1)
def get_starter_generator() -> StarterGenerator:
    return StarterGenerator()
