from __future__ import annotations

import re
import unicodedata

from ..types.normalized_signal import NormalizedSignal


_NOISY_WORDS = {
    "heyyy": "hey",
    "heyy": "hey",
    "luv": "love",
    "luvv": "love",
    "luvvv": "love",
    "u": "you",
    "ur": "your",
    "pls": "please",
    "plz": "please",
    "whatchu": "what are you",
    "wat": "what",
    "goin": "going",
    "2day": "today",
    "2morrow": "tomorrow",
    "beautful": "beautiful",
    "thnx": "thanks",
    "ty": "thanks",
    "np": "no problem",
}

# Common typos with repair candidates
_TYPO_REPAIRS = {
    "beautful": "beautiful",
    "beautifull": "beautiful",
    "definately": "definitely",
    "recieve": "receive",
    "seperate": "separate",
    "occured": "occurred",
    "teh": "the",
    "adn": "and",
    "taht": "that",
    "wiht": "with",
}

# Very simple closed-vocabulary check for unknown-token detection
_COMMON_ENGLISH = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "to", "of", "in", "on", "at", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these",
    "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "what", "which",
    "who", "when", "where", "why", "how", "all", "each", "every", "some", "any", "no", "not", "only", "just",
    "my", "your", "his", "her", "its", "our", "their", "mine", "yours", "ours", "theirs", "myself", "yourself",
    "himself", "herself", "itself", "ourselves", "yourselves", "themselves", "am", "so", "very", "too", "also",
    "here", "there", "now", "later", "soon", "today", "tomorrow", "yesterday", "yes", "no", "yeah", "yup", "ok",
    "okay", "sure", "right", "good", "bad", "great", "nice", "cool", "fine", "thanks", "thank", "please", "hi", "hey",
    "hello", "bye", "goodbye", "oh", "well", "hmm", "uh", "um", "like", "know", "see", "go", "get", "make", "want",
    "think", "say", "come", "take", "use", "look", "work", "feel", "try", "ask", "need", "want", "love", "mean",
    "call", "remember", "save", "store", "note", "tell", "teach", "learn", "zibble", "zorp", "groovy", "moonlight",
    "nah", "lol", "haha", "ouch", "wow", "yay", "aww", "boo", "meh", "huh", "erm", "uhh", "ahh", "mmm", "tsk",
    "secretly", "privately", "quietly", "secret", "private", "quiet", "remember", "means", "thing", "stuff",
    "favorite", "snack", "mango", "baby", "restaurant", "there",
}


def _has_repeated_letters(word: str) -> bool:
    return bool(re.search(r"([a-z])\1{2,}", word.lower()))


def _normalize_elongation(word: str) -> str:
    """Collapse 3+ repeated letters to 2 letters (hiii -> hii)."""
    return re.sub(r"([a-z])\1{2,}", r"\1\1", word.lower())


def _detect_unknown_tokens(words: list[str]) -> list[str]:
    unknown = []
    for w in words:
        bare = w.strip(".,!?;:\"'()[]{}").lower()
        if not bare:
            continue
        if bare in _COMMON_ENGLISH or _normalize_elongation(bare) in _COMMON_ENGLISH:
            continue
        if bare.isdigit():
            continue
        # Allow capitalized proper nouns (teachable as entity)
        if bare[0].isupper() and len(bare) > 2:
            continue
        unknown.append(bare)
    return unknown


def _detect_repair_candidates(words: list[str]) -> dict[str, str]:
    candidates: dict[str, str] = {}
    for w in words:
        bare = w.strip(".,!?;:\"'()[]{}").lower()
        if bare in _TYPO_REPAIRS:
            candidates[bare] = _TYPO_REPAIRS[bare]
    return candidates


class TextNormalizer:
    def normalize(self, text: str) -> NormalizedSignal:
        raw = text
        nfkc = unicodedata.normalize("NFKC", raw)
        folded = "".join(
            c for c in unicodedata.normalize("NFKD", nfkc) if not unicodedata.combining(c)
        )
        lowered = folded.lower()
        emoji_count = sum(1 for c in lowered if unicodedata.category(c).startswith("So"))
        punctuation_stripped = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
        collapsed = re.sub(r"\s+", " ", punctuation_stripped).strip()
        repeated_runs = re.findall(r"([a-z])\1{2,}", collapsed)
        repeated_collapsed = re.sub(r"([a-z])\1{2,}", r"\1\1", collapsed)
        tokens = [_NOISY_WORDS.get(tok, tok) for tok in repeated_collapsed.split()]
        lexical = " ".join(tokens)
        forms = []
        for form in [collapsed, repeated_collapsed, lexical]:
            if form and form not in forms:
                forms.append(form)
        scripts = sorted(
            {unicodedata.name(c, "UNKNOWN").split()[0] for c in raw if c.isalpha()}
        )
        # Surface features: repeated chars, casual spelling, slang, unknowns
        repeated_chars = len(repeated_runs) > 0
        slang_used = any(tok != repeated_collapsed.split()[i] for i, tok in enumerate(tokens))
        unknown_tokens = _detect_unknown_tokens(lexical.split())
        repair_candidates = _detect_repair_candidates(lexical.split())
        return NormalizedSignal(
            raw_text=raw,
            normalized_forms=forms,
            canonical_form=forms[-1] if forms else "",
            detected_scripts=scripts,
            noise_features={
                "emoji_count": emoji_count,
                "repeated_char_runs": len(repeated_runs),
                "leading_or_trailing_space": raw != raw.strip(),
                "repeated_chars": repeated_chars,
                "casual_spelling": bool(repair_candidates),
                "likely_slang": slang_used,
                "unknown_tokens": len(unknown_tokens),
            },
            transform_trace=[
                {"name": "nfkc", "value": nfkc},
                {"name": "diacritic_fold", "value": folded},
                {"name": "punctuation_strip", "value": collapsed},
                {"name": "lexical_noise_map", "value": lexical},
            ],
            surface_features={
                "repeated_chars": repeated_chars,
                "casual_spelling": bool(repair_candidates),
                "likely_slang": slang_used,
                "unknown_tokens": unknown_tokens,
                "repair_candidates": repair_candidates,
            },
            unknown_tokens=unknown_tokens,
            repair_candidates=repair_candidates,
            confidence=0.7 if forms else 0.0,
        )
