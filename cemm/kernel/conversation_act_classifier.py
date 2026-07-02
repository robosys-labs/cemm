from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from ..types.conversation_act import ConversationAct, ConversationActPacket
from ..types.context_kernel import ContextKernel
from ..types.signal import Signal
from ..registry.semantic_matcher import SemanticMatcher
from ..registry.registry import Registry
from ..registry.act_type_policy import DISCOURSE_FRAMES as _DISCOURSE_FRAMES, is_social as _is_social_act
from .text_match import tokenize_surface
from .intent_parser import parse_intent, CompositionalIntent

_logger = logging.getLogger("cemm.classifier")
_DEBUG = os.environ.get("CEMM_DEBUG", "").lower() in ("1", "true", "yes")


_UOL_SEMANTICS_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load_uol_metadata() -> tuple[
    dict[str, list[str]],
    dict[str, str],
    dict[str, str],
    dict[str, float],
    dict[str, set[str]],
]:
    """Load all UOL semantic metadata from the JSON data file.

    Returns:
        frame_aliases: canonical_key -> [aliases]
        frame_to_act: canonical_key -> act_type
        frame_polarity: canonical_key -> polarity
        frame_intensity: canonical_key -> intensity
        cue_sets: cue_type -> set of canonical_keys belonging to that cue type
    """
    if not _UOL_SEMANTICS_PATH.exists():
        return {}, {}, {}, {}, {}
    data = json.loads(_UOL_SEMANTICS_PATH.read_text(encoding="utf-8"))
    entries = data.get("uol_semantics", [])
    frame_aliases: dict[str, list[str]] = {}
    frame_to_act: dict[str, str] = {}
    frame_polarity: dict[str, str] = {}
    frame_intensity: dict[str, float] = {}
    cue_sets: dict[str, set[str]] = {}
    for entry in entries:
        key = entry["canonical_key"]
        frame_aliases[key] = entry.get("aliases", [])
        act_type = entry.get("act_type", "unknown")
        if act_type != "unknown":
            frame_to_act[key] = act_type
        if "polarity" in entry:
            frame_polarity[key] = entry["polarity"]
        if "intensity" in entry:
            frame_intensity[key] = entry["intensity"]
        cue_type = entry.get("cue_type")
        if cue_type:
            cue_sets.setdefault(cue_type, set())
            cue_sets[cue_type].update(frame_aliases[key])
    if _DEBUG:
        _logger.debug(
            "UOL metadata loaded: %d frames, %d act_types, %d cue_sets [%s]",
            len(frame_aliases),
            len(frame_to_act),
            len(cue_sets),
            ", ".join(f"{k}={len(v)}" for k, v in sorted(cue_sets.items())),
        )
    return frame_aliases, frame_to_act, frame_polarity, frame_intensity, cue_sets


_FRAME_ALIASES, _FRAME_TO_ACT, _FRAME_POLARITY, _FRAME_INTENSITY, _CUE_SETS = _load_uol_metadata()


def _tokenize_surface(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _phrase_matches(alias: str, text: str) -> bool:
    alias_tokens = _tokenize_surface(alias)
    text_tokens = _tokenize_surface(text)
    if not alias_tokens or not text_tokens:
        return False

    # Short aliases are especially risky, so require exact token matches.
    if len(alias_tokens) == 1:
        return alias_tokens[0] in text_tokens

    window = len(alias_tokens)
    for i in range(0, len(text_tokens) - window + 1):
        if text_tokens[i:i + window] == alias_tokens:
            return True
    return False


def _normalize_surface(text: str) -> str:
    return " ".join(_tokenize_surface(text))


def _is_scoped_assistance_request(text: str) -> bool:
    normalized = _normalize_surface(text)
    assistance_cues = _CUE_SETS.get("assistance_marker", set())
    stopword_cues = _CUE_SETS.get("stopword", set())
    matched = False
    for marker in assistance_cues:
        marker_norm = _normalize_surface(marker)
        if marker_norm in normalized:
            tail = normalized[normalized.index(marker_norm) + len(marker_norm):]
            tail_tokens = [t for t in _tokenize_surface(tail) if t not in stopword_cues]
            if len(tail_tokens) >= 2:
                matched = True
                break
    return matched


def _is_fresh_world_query(text: str, frame_keys: set[str] | None = None) -> bool:
    normalized = _normalize_surface(text)
    tokens = set(_tokenize_surface(text))
    if frame_keys and "weather_query" in frame_keys:
        return True

    fresh_markers = _CUE_SETS.get("fresh_world_marker", set())
    question_starter_cues = _CUE_SETS.get("question_starter", set())
    if not (tokens & fresh_markers):
        return False
    # Check if text starts with a question starter
    text_tokens = _tokenize_surface(text)
    first_token = text_tokens[0] if text_tokens else ""
    return first_token in question_starter_cues or any(
        normalized.startswith(qs) for qs in question_starter_cues if len(qs) > 2
    )


# _FRAME_TO_ACT is now loaded from uol_semantics.json act_type metadata.
# Priority order for primary act selection — frames earlier in this list
# take priority when multiple frames match.
_FRAME_PRIORITY: list[str] = [
    "session_exit",
    "frustration_signal",
    "low_competence",
    "confusion_repair",
    "playful_repair",
    "phatic_checkin",
    "teaching_offer",
    "self_correction",
    "simplification_request",
    "self_capability_query",
    "self_identity_query",
    "self_knowledge_query",
    "user_identity_query",
    "user_name_query",
    "open_domain_entity_query",
    "story_request",
    "food_recommendation_request",
    "recommendation_request",
    "assistance_request",
    "meta_question_intent",
    "greeting",
    "acknowledgment",
    "playful_acknowledgment",
    "request_clarification",
    "command_remember",
    "ask_question",
    "assert_evaluation",
    "high_quality",
]


class ConversationActClassifier:
    """Classify a signal into a ConversationAct using UOL frames and surface features.

    This is the single authority for pragmatic turn classification.
    It must run before retrieval so the pipeline knows what kind of
    evidence (if any) to fetch.
    """

    def __init__(self, registry: Registry) -> None:
        self._matcher = SemanticMatcher(registry)
        self._frame_aliases = _FRAME_ALIASES

    def classify(
        self,
        signal: Signal,
        kernel: ContextKernel,
        uol_atoms: list | None = None,
    ) -> ConversationActPacket:
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
                for form in content_forms:
                    if _phrase_matches(alias, form):
                        frame_keys.add(frame_key)
                        break
                if frame_key in frame_keys:
                    break

        # Precision filter: discourse acts (acknowledgment, greeting, etc.) are
        # turn-level acts. Discard when matched only via embedded words in long
        # inputs — e.g. "okay" in "if it's okay to eat" is not an acknowledgment.
        ordered_tokens = _tokenize_surface(content_lower)
        if len(ordered_tokens) >= 4:
            first_token = ordered_tokens[0] if ordered_tokens else ""
            for df in _DISCOURSE_FRAMES:
                if df not in frame_keys:
                    continue
                # Keep if semantic matcher matched at position 0 or via phrase
                matches = grouped.get(df, [])
                if any(m.word_position == 0 or m.word_position == -1 for m in matches):
                    continue
                # Keep if first token is an exact alias
                if first_token in self._frame_aliases.get(df, []):
                    continue
                frame_keys.discard(df)

        # Distinguish content questions from clarification requests.
        # If the input starts with a question word and has more than 2 words,
        # it's likely a content question, not a confusion repair.
        question_starter_cues = _CUE_SETS.get("question_starter", set())
        first_word = content_lower.split()[0] if content_lower.split() else ""
        word_count = len(content_lower.split())
        is_content_question = (
            (content_lower.endswith("?") or (first_word in question_starter_cues and word_count > 2))
        )
        # Check if the text matches any alias of the request_clarification frame
        # (these are the clarification patterns, sourced from UOL metadata)
        clarification_aliases = _FRAME_ALIASES.get("request_clarification", [])
        is_pure_clarification = any(_phrase_matches(p, content_lower) for p in clarification_aliases)
        if is_content_question and not is_pure_clarification:
            frame_keys.discard("request_clarification")
            frame_keys.add("ask_question")
        elif is_pure_clarification:
            frame_keys.discard("ask_question")
            frame_keys.add("request_clarification")

        if _is_fresh_world_query(content_lower, frame_keys):
            frame_keys.discard("open_domain_entity_query")
            frame_keys.add("ask_question")

        if "self_correction" in frame_keys and content_lower.startswith("i mean "):
            if _is_scoped_assistance_request(content_lower) or is_content_question:
                frame_keys.discard("self_correction")

        if _is_scoped_assistance_request(content_lower):
            frame_keys.discard("self_capability_query")
            frame_keys.discard("assistance_request")

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

        # ── Collect all matched acts (multi-act) ──────────────────────
        # Iterate in priority order so the first matched frame becomes primary
        # after confidence sorting. All matched frames produce acts.
        acts: list[ConversationAct] = []
        neg_eval_cues = _CUE_SETS.get("negative_evaluation", set())
        text_tokens = set(_tokenize_surface(content_lower))
        for frame_key in _FRAME_PRIORITY:
            if frame_key not in frame_keys:
                continue
            mapped_act = _FRAME_TO_ACT.get(frame_key)
            if not mapped_act:
                continue
            matches = grouped.get(frame_key, [])
            conf = matches[0].probability if matches else 0.7
            # Derive polarity and intensity from frame metadata
            act_polarity = _FRAME_POLARITY.get(frame_key, "neutral")
            act_intensity = _FRAME_INTENSITY.get(frame_key, 0.5)
            # For assistant_evaluation, refine polarity using negative_evaluation cues
            if mapped_act == "assistant_evaluation" and act_polarity == "neutral":
                act_polarity = "negative" if (text_tokens & neg_eval_cues) else "positive"
            acts.append(ConversationAct(
                act_type=mapped_act,
                polarity=act_polarity,
                intensity=act_intensity,
                confidence=conf,
                entity_mentions=entity_mentions if mapped_act == "open_domain_entity_query" else [],
            ))

        # Fallback: use observation_semantics speech_act
        if not acts and signal.observation_semantics:
            sem = signal.observation_semantics
            # Discourse acts are turn-level: skip acknowledgment fallback for
            # long inputs where the word is embedded (e.g. "if it's okay to eat")
            _word_count = len(content_lower.split())
            if sem.speech_act == "acknowledgment" and _word_count >= 4:
                pass
            elif sem.speech_act == "greeting":
                acts.append(ConversationAct(act_type="greeting", confidence=sem.confidence))
            elif sem.speech_act == "acknowledgment":
                acts.append(ConversationAct(act_type="acknowledgment", confidence=sem.confidence))
            elif sem.speech_act == "exit":
                acts.append(ConversationAct(act_type="exit", confidence=sem.confidence))

        # If we have entity mentions but no specific act, check if it's a question
        if not acts and entity_mentions and content_lower.endswith("?"):
            acts.append(ConversationAct(
                act_type="open_domain_entity_query",
                confidence=0.6,
                entity_mentions=entity_mentions,
            ))

        # Detect claim/preference assertions when no conversational frame matched.
        if not acts and uol_atoms:
            claim_atom_keys = [
                getattr(a, "frame_key", "") for a in uol_atoms
                if hasattr(a, "frame_key") and a.frame_key.startswith("claim_")
            ]
            if claim_atom_keys:
                acts.append(ConversationAct(act_type="claim_assertion", confidence=0.65))

        # Surface-level preference detection using UOL metadata cue set
        if not acts:
            preference_cues = _CUE_SETS.get("preference_marker", set())
            if any(_phrase_matches(p, content_lower) for p in preference_cues):
                acts.append(ConversationAct(act_type="preference_assertion", confidence=0.65))

        # ── Pending-question resolution ────────────────────────────────
        pending_q = kernel.conversation.pending_assistant_question
        expected_type = kernel.conversation.expected_user_answer_type
        discourse_relation = "none"
        expected_response = ""
        if pending_q and acts:
            # If the user's turn is short and the assistant had a pending question,
            # interpret this as an answer to the pending question.
            word_count = len(content_lower.split())
            if word_count <= 6:
                if expected_type == "social_status":
                    # "I'm good", "fine", "not bad" → user_state_report
                    if not any(_is_social_act(a.act_type) for a in acts):
                        acts.insert(0, ConversationAct(
                            act_type="user_state_report",
                            confidence=0.7,
                            polarity="positive",
                            intensity=0.4,
                        ))
                    discourse_relation = "answer_to_pending"
                    expected_response = pending_q
                elif expected_type == "yes_no":
                    # Short yes/no answer — use cue sets from UOL metadata
                    yes_cues = _CUE_SETS.get("affirmative", set())
                    no_cues = _CUE_SETS.get("negative_answer", set())
                    text_tokens = set(_tokenize_surface(content_lower))
                    if text_tokens & yes_cues:
                        acts.insert(0, ConversationAct(
                            act_type="chat_mode_statement",
                            confidence=0.8,
                            polarity="positive",
                        ))
                        discourse_relation = "answer_to_pending"
                        expected_response = pending_q
                    elif text_tokens & no_cues:
                        acts.insert(0, ConversationAct(
                            act_type="chat_mode_statement",
                            confidence=0.8,
                            polarity="negative",
                        ))
                        discourse_relation = "answer_to_pending"
                        expected_response = pending_q
                elif expected_type == "preference":
                    if not any(a.act_type == "preference_assertion" for a in acts):
                        acts.insert(0, ConversationAct(
                            act_type="preference_assertion",
                            confidence=0.65,
                        ))
                    discourse_relation = "answer_to_pending"
                    expected_response = pending_q

        # ── Detect teachability_complaint ────────────────────────────
        # Uses grammatical cue sets from UOL metadata: self_target + negation + critique_process
        self_target_cues = _CUE_SETS.get("self_target", set())
        negation_cues = _CUE_SETS.get("negation", set())
        critique_cues = _CUE_SETS.get("critique_process", set())
        if (text_tokens & self_target_cues) and (text_tokens & negation_cues) and (text_tokens & critique_cues):
            acts.append(ConversationAct(
                act_type="teachability_complaint",
                confidence=0.7,
                polarity="negative",
                intensity=0.7,
            ))

        # ── Detect chat_mode_statement (short non-command, non-question) ──
        if not acts and word_count <= 4 and not content_lower.endswith("?"):
            text_tokens = set(_tokenize_surface(content_lower))
            # Exclude if it looks like a command — use cue set from UOL metadata
            command_cues = _CUE_SETS.get("command", set())
            if not (text_tokens & command_cues):
                acts.append(ConversationAct(
                    act_type="chat_mode_statement",
                    confidence=0.4,
                ))

        # ── Compositional intent parsing ──────────────────────────────
        # Use structural analysis to upgrade/refine acts that lexical matching
        # alone cannot disambiguate.
        intent = parse_intent(signal.content)

        # Upgrade self_capability_query to self_capability_skeptical_query
        # when the compositional parser detects skepticism
        if intent.is_skeptical and intent.is_capability_query:
            for i, act in enumerate(acts):
                if act.act_type == "self_capability_query":
                    acts[i] = ConversationAct(
                        act_type="self_capability_skeptical_query",
                        polarity="skeptical",
                        intensity=0.7,
                        confidence=act.confidence,
                        entity_mentions=act.entity_mentions,
                    )
                    break

        # Detect meta_critique: skeptical + self-directed + process is a critique_process cue
        if intent.is_skeptical and intent.is_self_directed:
            critique_cues = _CUE_SETS.get("critique_process", set())
            if intent.process in critique_cues:
                acts.append(ConversationAct(
                    act_type="meta_critique",
                    confidence=0.7,
                    polarity="skeptical",
                    intensity=0.7,
                ))

        # ── Build packet ──────────────────────────────────────────────
        if not acts:
            acts.append(ConversationAct(act_type="unknown", confidence=0.5))

        # Sort by confidence descending; highest is primary
        acts.sort(key=lambda a: a.confidence, reverse=True)
        primary = acts[0]
        secondary = acts[1:]

        # ── Collect diagnostics for tracing/debugging ────────────────
        diagnostics: dict[str, Any] = {
            "matched_frame_keys": sorted(frame_keys),
            "content_question": is_content_question,
            "pure_clarification": is_pure_clarification,
            "fresh_world_query": _is_fresh_world_query(content_lower, frame_keys),
            "scoped_assistance": _is_scoped_assistance_request(content_lower),
            "cue_set_sizes": {k: len(v) for k, v in _CUE_SETS.items()},
            "acts": [
                {"act_type": a.act_type, "polarity": a.polarity, "confidence": a.confidence}
                for a in acts
            ],
            "discourse_relation": discourse_relation,
        }

        return ConversationActPacket(
            primary=primary,
            secondary=secondary,
            discourse_relation=discourse_relation,
            expected_response_to_previous=expected_response,
            raw_text=signal.content,
            diagnostics=diagnostics,
        )
