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
}


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
        return NormalizedSignal(
            raw_text=raw,
            normalized_forms=forms,
            canonical_form=forms[-1] if forms else "",
            detected_scripts=scripts,
            noise_features={
                "emoji_count": emoji_count,
                "repeated_char_runs": len(repeated_runs),
                "leading_or_trailing_space": raw != raw.strip(),
            },
            transform_trace=[
                {"name": "nfkc", "value": nfkc},
                {"name": "diacritic_fold", "value": folded},
                {"name": "punctuation_strip", "value": collapsed},
                {"name": "lexical_noise_map", "value": lexical},
            ],
            confidence=0.7 if forms else 0.0,
        )
