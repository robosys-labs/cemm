from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.text_normalizer import TextNormalizer


def test_normalizer_preserves_raw_text_and_expands_noise() -> None:
    packet = TextNormalizer().normalize("  Héyyy!!!   I luvvv CEMM 😂  ")
    assert packet.raw_text == "  Héyyy!!!   I luvvv CEMM 😂  "
    assert any("hey" in form for form in packet.normalized_forms)
    assert any("love" in form for form in packet.normalized_forms)
    assert packet.noise_features["emoji_count"] == 1
    assert packet.noise_features["repeated_char_runs"] >= 2


def test_normalizer_keeps_multilingual_alias_forms() -> None:
    packet = TextNormalizer().normalize("hola, ¿qué haces?")
    assert "hola que haces" in packet.normalized_forms
    assert packet.detected_scripts
    assert packet.confidence >= 0.5
