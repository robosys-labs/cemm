from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..types.conversation_act import ConversationAct
from ..types.context_kernel import ContextKernel
from ..types.signal import Signal
from ..registry.semantic_matcher import SemanticMatcher
from ..registry.registry import Registry


_UOL_SEMANTICS_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load_frame_aliases() -> dict[str, list[str]]:
    if not _UOL_SEMANTICS_PATH.exists():
        return {}
    data = json.loads(_UOL_SEMANTICS_PATH.read_text(encoding="utf-8"))
    return {
        entry["canonical_key"]: entry.get("aliases", [])
        for entry in data.get("uol_semantics", [])
    }


# Maps UOL frame keys to conversation act types.
# Order matters: earlier entries take priority when multiple frames match.
_FRAME_TO_ACT: list[tuple[str, str]] = [
    ("session_exit", "exit"),
    ("story_request", "story_request"),
    ("food_recommendation_request", "creative_request"),
    ("recommendation_request", "creative_request"),
    ("frustration_signal", "frustration_signal"),
    ("low_competence", "frustration_signal"),
    ("confusion_repair", "confusion_repair"),
    ("playful_repair", "playful_repair"),
    ("phatic_checkin", "phatic_checkin"),
    ("teaching_offer", "teaching_offer"),
    ("command_alias_teaching", "command_alias_teaching"),
    ("definition_teaching", "definition_teaching"),
    ("correction", "self_correction"),
    ("self_correction", "self_correction"),
    ("simplification_request", "simplification_request"),
    ("self_capability_query", "self_capability_query"),
    ("self_identity_query", "self_identity_query"),
    ("self_knowledge_query", "self_knowledge_query"),
    ("user_identity_query", "user_identity_query"),
    ("user_name_query", "user_name_query"),
    ("open_domain_entity_query", "open_domain_entity_query"),
    ("assistance_request", "capability_query"),
    ("greeting", "greeting"),
    ("acknowledgment", "acknowledgment"),
    ("playful_acknowledgment", "playful_acknowledgment"),
    ("request_clarification", "confusion_repair"),
    ("command_remember", "explicit_remember"),
    ("ask_question", "evidence_query"),
]


class ConversationActClassifier:
    """Classify a signal into a ConversationAct using UOL frames and surface features.

    This is the single authority for pragmatic turn classification.
    It must run before retrieval so the pipeline knows what kind of
    evidence (if any) to fetch.
    """

    def __init__(self, registry: Registry) -> None:
        self._matcher = SemanticMatcher(registry)
        self._frame_aliases = _load_frame_aliases()

    def classify(
        self,
        signal: Signal,
        kernel: ContextKernel,
        uol_atoms: list | None = None,
    ) -> ConversationAct:
        content_lower = signal.content.lower().strip()
        extra_forms = []
        if signal.normalized:
            extra_forms = signal.normalized.normalized_forms
        content_forms = [content_lower] + [f.lower().strip() for f in extra_forms if f]

        # Collect matched frame keys from UOL atoms
        frame_keys: set[str] = set()
        if uol_atoms:
            for atom in uol_atoms:
                fk = getattr(atom, "frame_key", "")
                if fk:
                    frame_keys.add(fk)

        # Also match via semantic matcher for frames not in atoms
        grouped = self._matcher.match_grouped(
            signal.content, kinds=["uol_semantic"], extra_forms=extra_forms,
        )
        for canonical_key, matches in grouped.items():
            if matches and matches[0].probability >= 0.3:
                frame_keys.add(canonical_key)

        # Direct phrase matching from JSON aliases (works even when registry
        # doesn't have uol_semantic entries seeded)
        for frame_key, aliases in self._frame_aliases.items():
            if frame_key in frame_keys:
                continue
            for alias in aliases:
                alias_lower = alias.lower()
                for form in content_forms:
                    if alias_lower in form:
                        frame_keys.add(frame_key)
                        break
                if frame_key in frame_keys:
                    break

        # Distinguish content questions from clarification requests.
        # If the input starts with a question word and has more than 2 words,
        # it's likely a content question, not a confusion repair.
        question_starters = {"what", "who", "where", "when", "why", "how", "which", "do", "does", "is", "are", "can", "could"}
        first_word = content_lower.split()[0] if content_lower.split() else ""
        word_count = len(content_lower.split())
        is_content_question = (
            (content_lower.endswith("?") or (first_word in question_starters and word_count > 2))
        )
        # More precise: if it starts with "what do you mean" or "what the" etc., it's clarification
        clarification_patterns = (
            "what do you mean", "what in the world", "what the", "what on earth",
            "what the heck", "what the hell", "how do you mean", "come again",
            "confused", "don't understand", "don't get it", "lost", "not following",
        )
        is_pure_clarification = any(p in content_lower for p in clarification_patterns)
        if is_content_question and not is_pure_clarification:
            frame_keys.discard("request_clarification")
            frame_keys.add("ask_question")
        elif is_pure_clarification:
            frame_keys.discard("ask_question")
            frame_keys.add("request_clarification")

        # Map frames to act types in priority order
        act_type = "unknown"
        confidence = 0.5
        for frame_key, mapped_act in _FRAME_TO_ACT:
            if frame_key in frame_keys:
                act_type = mapped_act
                # Use match probability if available
                matches = grouped.get(frame_key, [])
                if matches:
                    confidence = max(confidence, matches[0].probability)
                else:
                    confidence = max(confidence, 0.7)
                break

        # Fallback: use observation_semantics speech_act
        if act_type == "unknown" and signal.observation_semantics:
            sem = signal.observation_semantics
            if sem.speech_act == "greeting":
                act_type = "greeting"
                confidence = max(confidence, sem.confidence)
            elif sem.speech_act == "acknowledgment":
                act_type = "acknowledgment"
                confidence = max(confidence, sem.confidence)
            elif sem.speech_act == "exit":
                act_type = "exit"
                confidence = max(confidence, sem.confidence)

        # Entity mentions for open_domain_entity_query
        entity_mentions: list[dict[str, Any]] = []
        if uol_atoms:
            for atom in uol_atoms:
                if hasattr(atom, "entity_id") and atom.entity_id:
                    entity_mentions.append({
                        "entity_id": atom.entity_id,
                        "role": getattr(atom, "role", "entity"),
                        "confidence": getattr(atom, "confidence", 0.6),
                    })

        # If we have entity mentions but no specific act, check if it's a question
        if act_type == "unknown" and entity_mentions and content_lower.endswith("?"):
            act_type = "open_domain_entity_query"
            confidence = 0.6

        # Detect claim/preference assertions when no conversational frame matched.
        # Predicate matches produce claim_* frame keys in UOL atoms.
        if act_type == "unknown" and uol_atoms:
            claim_atom_keys = [
                getattr(a, "frame_key", "") for a in uol_atoms
                if hasattr(a, "frame_key") and a.frame_key.startswith("claim_")
            ]
            if claim_atom_keys:
                act_type = "claim_assertion"
                confidence = max(confidence, 0.65)

        # Surface-level preference detection: "I like/love/prefer X"
        if act_type == "unknown":
            preference_patterns = (
                "i like ", "i love ", "i prefer ", "i enjoy ",
                "i'm into ", "my favorite ", "i fancy ", "i'm a fan of ",
            )
            if any(p in content_lower for p in preference_patterns):
                act_type = "preference_assertion"
                confidence = max(confidence, 0.65)

        # Determine polarity and intensity
        polarity = "neutral"
        intensity = 0.5
        if act_type == "frustration_signal":
            polarity = "negative"
            intensity = 0.8
        elif act_type in ("greeting", "phatic_checkin", "playful_acknowledgment"):
            polarity = "positive"
            intensity = 0.6
        elif act_type in ("confusion_repair", "playful_repair"):
            polarity = "neutral"
            intensity = 0.6

        return ConversationAct(
            act_type=act_type,
            polarity=polarity,
            intensity=intensity,
            confidence=confidence,
            entity_mentions=entity_mentions,
        )
