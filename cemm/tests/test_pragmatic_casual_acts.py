from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.context_kernel_builder import ContextKernelBuilder
from cemm.kernel.pragmatic_interpreter import interpret_signal
from cemm.kernel.semantic_clusters import SemanticClusterRegistry
from cemm.types.permission import Permission
from cemm.types.signal import Signal, SignalKind, SourceType


def _signal(text: str) -> Signal:
    return Signal(
        id="s1",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id="ctx",
        salience=0.5,
        trust=0.8,
        permission=Permission.public(),
    )


def test_casual_chat_speech_acts_are_semantic_clusters() -> None:
    reg = SemanticClusterRegistry()
    cases = {
        "lol nice": "playful_acknowledgment",
        "wait what": "confusion",
        "my bad": "self_correction",
        "can you explain that simpler": "simplification_request",
        "no worries": "reassurance",
    }
    for text, cluster in cases.items():
        matches = reg.match_ranked(text)
        assert matches
        assert matches[0].cluster_key == cluster


def test_pragmatic_interpreter_maps_casual_acts_to_frame_keys() -> None:
    kernel = ContextKernelBuilder.from_signal(_signal("lol nice"), turn_index=2)
    semantics = interpret_signal(_signal("lol nice"), kernel)
    assert semantics is not None
    assert semantics.speech_act == "playful_acknowledgment"
    assert semantics.frame_key == "playful_acknowledgment"
