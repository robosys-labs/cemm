"""MeaningPerceptor - assemble group-aware meaning atoms from a Signal.

The perceptor is the first semantic boundary after normalization. It should not
route responses or mutate memory. Its job is to preserve surface evidence and
emit CEMM-native structures that downstream stages can bind, rank, and learn
from.

Version 3.3 makes a key architectural correction: an utterance is not assumed
to have one meaning. The packet now carries probable meaning groups, predicate
phrases, and candidate atom outcomes so the core loop can reason over each
clause or predicate independently.
"""

from __future__ import annotations

from typing import Any, Iterable
import uuid

try:
    from ..learning.lexeme_memory import LexemeMemory, LexemeRole
except ModuleNotFoundError:  # pragma: no cover - partial scratch checkouts.
    class LexemeMemory:  # type: ignore[no-redef]
        pass

    class _LexemeRoleValue:
        def __init__(self, value: str) -> None:
            self.value = value

    class LexemeRole:  # type: ignore[no-redef]
        ENTITY = _LexemeRoleValue("entity")
        PROCESS = _LexemeRoleValue("process")
        COMMAND_ALIAS = _LexemeRoleValue("command_alias")
        STATE = _LexemeRoleValue("state")
        RELATION = _LexemeRoleValue("relation")

try:
    from ..learning.ner_tagger import NERTagger
except ModuleNotFoundError:  # pragma: no cover - partial scratch checkouts.
    class NERTagger:  # type: ignore[no-redef]
        pass

try:
    from ..learning.surface_tagger import SurfaceTagger
except ModuleNotFoundError:  # pragma: no cover - partial scratch checkouts.
    class SurfaceTagger:  # type: ignore[no-redef]
        pass

try:
    from ..types.context_kernel import ContextKernel
except ModuleNotFoundError:  # pragma: no cover - partial scratch checkouts.
    ContextKernel = Any  # type: ignore[misc,assignment]
from ..types.meaning_percept import (
    ActionAtom,
    AffordanceAtom,
    AtomEvidence,
    CandidateInterpretation,
    EvidenceAtom,
    IntentAtom,
    MeaningAtomOutcome,
    OutcomeAtom,
    ValenceAtom,
    MeaningGroup,
    MeaningHypothesis,
    MeaningPerceptPacket,
    ModalityAtom,
    NeedAtom,
    PermissionAtom,
    PlaceAtom,
    PredicatePhrase,
    ReferentAtom,
    RelationAtom,
    SelfAtom,
    SourceAtom,
    StateAtom,
    SurfaceSpan,
    TimeAtom,
)
try:
    from ..types.signal import Signal
except ModuleNotFoundError:  # pragma: no cover - partial scratch checkouts.
    Signal = Any  # type: ignore[misc,assignment]
from .language_adapter import EnglishLanguageAdapter, LanguageAdapter
from .meaning_graph_builder import MeaningGraphBuilder
from .predicate_phrase_extractor import PredicatePhraseExtractor
from .anaphora_resolver import AnaphoraResolver
from .entity_salience_tracker import EntitySalienceTracker
from .implicit_predicate_detector import ImplicitPredicateDetector


_ENTITY_ROLES = {"person", "place", "organization", "entity", "object", "time"}
_SURFACE_ACTION_ROLES = {"process", "command_alias"}
_GROUP_CONNECTIVES = {
    "and", "but", "or", "then", "because", "so", "while", "when", "if",
    "although", "though", "plus", "that", "since", "unless", "whereas", "nor",
}
_STRONG_SPLIT_CONNECTIVES = {"but", "then", "because", "so", "while", "when", "if", "although", "though", "plus", "since", "unless", "whereas"}
_SUBORDINATING_CONNECTIVES = {"because", "if", "when", "while", "although", "though", "that", "since", "unless", "whereas"}
_CONNECTIVE_RELATIONS = {
    "because": "cause",
    "so": "result",
    "if": "condition",
    "when": "temporal",
    "while": "temporal_or_contrast",
    "although": "concession",
    "though": "concession",
    "that": "complement",
    "since": "cause_or_time",
    "unless": "negative_condition",
    "whereas": "contrast",
    "but": "contrast",
    "then": "sequence",
    "and": "coordination",
    "or": "alternative",
    "nor": "negative_alternative",
    "plus": "addition",
}
_QUESTION_STARTERS = {"who", "what", "when", "where", "why", "how", "which", "can", "could", "would", "should", "do", "does", "did", "is", "are", "am", "was", "were"}
_COMMAND_CUES = {"please", "tell", "show", "remember", "forget", "explain", "define", "teach", "look", "find", "use", "make", "create", "give"}
_COMMON_PREDICATE_VERBS = {"know", "think", "feel", "like", "want", "need", "went", "go", "worked", "work", "have", "has", "had", "do", "does", "did"}
_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "this", "that"}
_REPAIR_CUES = {"what", "huh", "wait", "confused", "misunderstood", "mean", "unpack", "plainly", "again"}
_FRESH_WORLD_CUES = {"current", "latest", "today", "now"}
_EXIT_CUES = {"bye", "goodbye", "later", "farewell"}
_TEACHING_CUES = {"means", "mean", "called", "is", "are", "refers", "equals"}
_TIME_CUES = {"now", "today", "tonight", "tomorrow", "yesterday", "currently", "latest", "recent"}
_PLACE_CUES = {"here", "there", "where", "inside", "outside", "nearby"}
_MODAL_CUES = {
    "can": "possible",
    "could": "possible",
    "should": "recommended",
    "would": "hypothetical",
    "must": "required",
    "need": "required",
    "needs": "required",
    "want": "desired",
    "wants": "desired",
    "might": "possible",
    "may": "possible",
}
_NEGATIONS = {"not", "never", "no", "cannot", "can't", "dont", "don't", "wont", "won't"}
_AMBIGUOUS_LEXEMES: dict[str, list[dict[str, Any]]] = {
    "bank": [
        {"atom_kind": "entity", "atom_key": "financial_institution", "role": "institution", "confidence": 0.52},
        {"atom_kind": "place", "atom_key": "river_bank", "role": "place", "confidence": 0.48},
    ],
    "light": [
        {"atom_kind": "quality", "atom_key": "low_weight", "role": "quality", "confidence": 0.45},
        {"atom_kind": "state", "atom_key": "illumination", "role": "state", "confidence": 0.45},
        {"atom_kind": "process", "atom_key": "ignite", "role": "process", "confidence": 0.4},
    ],
    "run": [
        {"atom_kind": "process", "atom_key": "move_fast", "role": "process", "confidence": 0.44},
        {"atom_kind": "action", "atom_key": "execute_program", "role": "action", "confidence": 0.42},
        {"atom_kind": "process", "atom_key": "operate", "role": "process", "confidence": 0.4},
    ],
    "cold": [
        {"atom_kind": "state", "atom_key": "low_temperature", "role": "state", "confidence": 0.58},
        {"atom_kind": "quality", "atom_key": "unfriendly_affect", "role": "quality", "confidence": 0.35},
        {"atom_kind": "state", "atom_key": "illness_symptom", "role": "state", "confidence": 0.32},
    ],
}


class MeaningPerceptor:
    """Build MeaningPerceptPacket from normalized signal and semantic hints."""

    def __init__(
        self,
        ner_tagger: NERTagger | None = None,
        surface_tagger: SurfaceTagger | None = None,
        lexeme_memory: LexemeMemory | None = None,
        language_adapter: LanguageAdapter | None = None,
    ) -> None:
        self._ner_tagger = ner_tagger
        self._surface_tagger = surface_tagger
        self._lexeme_memory = lexeme_memory
        self._language = language_adapter or EnglishLanguageAdapter()
        self._graph_builder = MeaningGraphBuilder()
        self._predicate_extractor = PredicatePhraseExtractor()
        self._anaphora_resolver = AnaphoraResolver()
        self._salience_tracker = EntitySalienceTracker()
        self._implicit_detector = ImplicitPredicateDetector()

    def perceive(
        self,
        signal: Signal,
        kernel: ContextKernel,
    ) -> MeaningPerceptPacket:
        """Build a MeaningPerceptPacket without side effects."""
        raw_text = signal.content or ""
        tokens = self._language.tokenize(raw_text)
        normalized_tokens, repaired_tokens, normalized_forms, unknown_tokens = self._normalization(signal, tokens)
        semantic_tokens = repaired_tokens or normalized_tokens or tokens

        packet = MeaningPerceptPacket(
            id=uuid.uuid4().hex[:16],
            signal_id=signal.id,
            context_id=signal.context_id,
            raw_text=raw_text,
            tokens=tokens,
            normalized_tokens=normalized_tokens,
            repaired_tokens=repaired_tokens,
            normalized_forms=normalized_forms,
            punctuation_features=self._language.punctuation_features(raw_text),
            language=getattr(self._language, "language_code", "und"),
            language_confidence=1.0 if getattr(self._language, "language_code", "und") != "und" else 0.0,
            speaker_entity_id="user",
            listener_entity_id="self",
            perception_trace={
                "version": "3.3",
                "perceptor": "group_aware_deterministic_seed",
            },
        )
        packet.spans = self._surface_spans(raw_text, semantic_tokens)
        packet.meaning_groups = self._meaning_groups(raw_text, semantic_tokens)
        packet.sources.append(SourceAtom(
            source_role="user",
            surface=raw_text,
            reliability="speaker_asserted",
            permission_scope="conversation",
            confidence=0.7,
        ))
        packet.permissions.append(PermissionAtom(
            permission_key="conversation",
            scope="conversation",
            holder_role="user",
            target_role="source",
            confidence=0.75,
        ))
        packet.self_atoms.append(SelfAtom(
            self_key="self",
            role="listener",
            surface="self",
            confidence=0.9,
        ))

        known_words = self._known_words()
        ner_entities = self._extract_ner(semantic_tokens)
        semantic_spans = self._extract_surface_tags(semantic_tokens, unknown_tokens)

        self._add_ner_referents(packet, ner_entities)
        self._extend_referents(packet, self._language.map_pronouns(semantic_tokens))
        self._extend_referents(packet, self._language.map_deictics(semantic_tokens))
        self._add_capitalized_referents(packet, raw_text, known_words)

        self._apply_surface_tags(packet, semantic_spans)
        self._apply_lexeme_memory(packet, semantic_tokens)

        self._extend_actions(packet, self._language.map_actions(semantic_tokens))
        self._extend_states(packet, self._language.map_states(semantic_tokens))
        self._extend_needs(packet, self._language.map_needs(semantic_tokens))

        self._add_unknown_lexemes(packet, unknown_tokens, semantic_tokens, known_words, semantic_spans)
        self._add_idiom_candidates(packet, semantic_tokens, unknown_tokens)
        packet.affect_markers = self._dedupe_dicts(
            [*packet.affect_markers, *self._language.detect_affect(raw_text, semantic_tokens)],
            key_fields=("type", "surface"),
        )

        self._assign_atoms_to_groups(packet)
        self._anaphora_resolver.resolve(
            referents=packet.referents,
            groups=packet.meaning_groups,
            entities=ner_entities,
            language=self._language,
        )
        ranked_entities, _salience_map = self._salience_tracker.track(
            referents=packet.referents,
            groups=packet.meaning_groups,
        )
        packet.perception_trace["salience_ranked"] = [
            e["key"] for e in ranked_entities[:5]
        ]
        self._add_structural_atoms(packet)
        self._build_meaning_hypotheses(packet)
        packet.predicate_phrases = self._predicate_extractor.extract(
            groups=packet.meaning_groups,
            language=self._language,
        )
        implicit_predicates = self._implicit_detector.detect(
            groups=packet.meaning_groups,
            referents=packet.referents,
            predicates=packet.predicate_phrases,
        )
        packet.predicate_phrases.extend(implicit_predicates)
        packet.atom_outcomes = self._predicate_extractor.build_outcomes(
            predicates=packet.predicate_phrases,
            groups=packet.meaning_groups,
        )
        packet.core_loop_stage = "working_graph_built"
        packet.core_loop_trace = {
            "loop_version": "semantic_core_loop_v4_1_seed",
            "stages": [
                "normalize",
                "segment",
                "atomize",
                "build_working_graph",
                "seed_concept_resolution",
                "seed_port_resolution",
                "seed_affordance_prediction",
                "extract_graph_patch_candidates",
            ],
            "durable_write_policy": "graph_patch_only",
        }
        packet.uol_graph = self._graph_builder.build(packet)
        packet.uol_training_example = packet.uol_graph.to_training_example()
        packet.graph_patch_candidates = list(packet.uol_graph.patch_candidates)

        packet.affordances = [
            AffordanceAtom(
                entity_role_or_id=pred.affordance_key,
                affords=[pred.effect_type],
                condition=pred.reason,
                confidence=pred.confidence,
            )
            for pred in (packet.uol_graph.affordance_predictions if packet.uol_graph else [])
        ]
        packet.outcomes = [
            OutcomeAtom(
                affected_entity_role=outcome.affected_role,
                changed_dimension=outcome.expected_change,
                direction=outcome.valence or "unknown",
                event_key=outcome.atom_key,
                confidence=outcome.confidence,
            )
            for outcome in packet.atom_outcomes
        ]
        packet.valences = [
            ValenceAtom(
                target_role=outcome.affected_role,
                valence=outcome.valence,
                confidence=outcome.confidence,
            )
            for outcome in packet.atom_outcomes
        ]

        packet.attention_target = self._attention_target(packet, kernel)
        packet.confidence = self._confidence(packet)
        packet.perception_trace.update({
            "meaning_group_count": len(packet.meaning_groups),
            "meaning_hypothesis_count": len(packet.meaning_hypotheses),
            "predicate_phrase_count": len(packet.predicate_phrases),
            "atom_outcome_count": len(packet.atom_outcomes),
            "uol_atom_count": len(packet.uol_graph.atoms) if packet.uol_graph else 0,
            "uol_edge_count": len(packet.uol_graph.edges) if packet.uol_graph else 0,
            "port_binding_count": len(packet.uol_graph.port_bindings) if packet.uol_graph else 0,
            "affordance_prediction_count": len(packet.uol_graph.affordance_predictions) if packet.uol_graph else 0,
            "graph_patch_candidate_count": len(packet.graph_patch_candidates),
        })
        packet.core_loop_trace["counts"] = {
            "meaning_groups": len(packet.meaning_groups),
            "meaning_hypotheses": len(packet.meaning_hypotheses),
            "predicate_phrases": len(packet.predicate_phrases),
            "uol_atoms": len(packet.uol_graph.atoms) if packet.uol_graph else 0,
            "uol_edges": len(packet.uol_graph.edges) if packet.uol_graph else 0,
            "graph_patch_candidates": len(packet.graph_patch_candidates),
        }
        packet.core_loop_stage = "patch_candidates_ready"
        return packet

    def _normalization(
        self,
        signal: Signal,
        fallback_tokens: list[str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        normalized = getattr(signal, "normalized", None)
        if normalized is None:
            return fallback_tokens, fallback_tokens, [], []

        canonical = getattr(normalized, "canonical_form", "") or ""
        canonical_tokens = self._language.tokenize(canonical) if canonical else fallback_tokens
        surface_features = getattr(normalized, "surface_features", {}) or {}
        unknown_tokens = [str(t) for t in surface_features.get("unknown_tokens", []) if str(t).strip()]
        normalized_forms = [str(f) for f in getattr(normalized, "normalized_forms", [])]

        # Pick the shortest normalized form — this naturally collapses
        # "hiii" → "hi", "heyyy" → "hey", "noooo" → "no" etc.
        best_tokens = canonical_tokens
        for form in normalized_forms:
            form_tokens = self._language.tokenize(form) if form else []
            if not form_tokens or form_tokens == best_tokens:
                continue
            if len(form_tokens) < len(best_tokens):
                best_tokens = form_tokens

        return best_tokens, canonical_tokens, normalized_forms, unknown_tokens

    def _surface_spans(self, raw_text: str, tokens: list[str]) -> list[SurfaceSpan]:
        spans: list[SurfaceSpan] = []
        for index, token in enumerate(tokens):
            spans.append(SurfaceSpan(
                id=f"span_{index}",
                start_token=index,
                end_token=index + 1,
                surface=token,
                normalized=token,
                tokens=[token],
                language=getattr(self._language, "language_code", "und"),
                span_type="token",
                confidence=0.8,
            ))
        for index, (surface, start, end, separator, _trailing_sep) in enumerate(self._raw_clause_segments(raw_text, tokens)):
            clause_tokens = tokens[start:end]
            if not clause_tokens:
                continue
            spans.append(SurfaceSpan(
                id=f"clause_{index}",
                start_token=start,
                end_token=end,
                surface=surface,
                normalized=" ".join(clause_tokens),
                tokens=clause_tokens,
                language=getattr(self._language, "language_code", "und"),
                span_type="clause",
                source=f"separator:{separator}" if separator else "surface",
                confidence=0.72,
            ))
        return spans

    def _meaning_groups(self, raw_text: str, tokens: list[str]) -> list[MeaningGroup]:
        groups: list[MeaningGroup] = []
        for surface, start, end, separator, trailing_separator in self._raw_clause_segments(raw_text, tokens):
            clause_tokens = tokens[start:end]
            if not clause_tokens:
                continue
            pieces = self._split_on_connectives(clause_tokens)
            offset = 0
            for piece_tokens, connective_before, relation_to_previous in pieces:
                if connective_before:
                    while offset < len(clause_tokens) and clause_tokens[offset] in _GROUP_CONNECTIVES:
                        offset += 1
                piece_start = start + offset
                piece_end = piece_start + len(piece_tokens)
                offset += len(piece_tokens)
                if not piece_tokens:
                    continue
                group_surface = surface if len(pieces) == 1 else " ".join(piece_tokens)
                parent_group_id = ""
                relation_to_parent = ""
                if relation_to_previous in {"cause", "condition", "temporal", "temporal_or_contrast", "concession", "complement", "cause_or_time", "negative_condition"} and groups:
                    parent_group_id = groups[-1].id
                    relation_to_parent = relation_to_previous
                group_type = self._initial_group_type(group_surface, piece_tokens, trailing_separator=trailing_separator)
                groups.append(MeaningGroup(
                    id=f"group_{len(groups)}",
                    parent_group_id=parent_group_id,
                    relation_to_parent=relation_to_parent,
                    surface=group_surface.strip(),
                    start_token=piece_start,
                    end_token=piece_end,
                    tokens=piece_tokens,
                    connective_before=connective_before,
                    separator_before=separator,
                    separator_after=trailing_separator,
                    group_type=group_type,
                    confidence=self._group_confidence(piece_tokens, group_type, trailing_separator),
                ))
                if parent_group_id:
                    parent = self._group_by_id(groups, parent_group_id)
                    if parent is not None and groups[-1].id not in parent.child_group_ids:
                        parent.child_group_ids.append(groups[-1].id)

        if not groups and tokens:
            separator_after = "?" if raw_text.rstrip().endswith("?") else ""
            group_type = self._initial_group_type(raw_text, tokens, separator_after)
            groups.append(MeaningGroup(
                id="group_0",
                surface=raw_text,
                start_token=0,
                end_token=len(tokens),
                tokens=tokens,
                separator_after=separator_after,
                group_type=group_type,
                confidence=self._group_confidence(tokens, group_type, separator_after),
            ))
        return groups

    def _raw_clause_segments(
        self,
        raw_text: str,
        tokens: list[str],
    ) -> list[tuple[str, int, int, str, str]]:
        segments: list[tuple[str, int, int, str, str]] = []
        chunk = ""
        token_cursor = 0
        previous_separator = ""
        quote_char = ""
        paren_depth = 0

        def flush(surface: str, separator: str) -> None:
            nonlocal token_cursor, previous_separator
            clean = surface.strip()
            if not clean:
                previous_separator = separator or previous_separator
                return
            chunk_tokens = self._language.tokenize(clean)
            if not chunk_tokens:
                previous_separator = separator or previous_separator
                return
            start = token_cursor
            end = min(len(tokens), token_cursor + len(chunk_tokens))
            token_cursor = end
            segments.append((clean, start, end, previous_separator, separator))
            previous_separator = separator

        text = raw_text or ""
        index = 0
        while index < len(text):
            char = text[index]
            next_char = text[index + 1] if index + 1 < len(text) else ""
            next_two = text[index:index + 3]
            if char == "'" and index > 0 and index < len(text) - 1 and text[index - 1].isalpha() and text[index + 1].isalpha():
                chunk += char
                index += 1
                continue
            if char in {"'", '"'}:
                quote_char = "" if quote_char == char else char if not quote_char else quote_char
                chunk += char
                index += 1
                continue
            if char in "([{":
                paren_depth += 1
                chunk += char
                index += 1
                continue
            if char in ")]}" and paren_depth > 0:
                paren_depth -= 1
                chunk += char
                index += 1
                continue
            if next_two == "...":
                flush(chunk.strip(), "...")
                chunk = ""
                index += 3
                continue
            if char == "\n":
                flush(chunk.strip(), "newline")
                chunk = ""
                index += 1
                continue
            if not quote_char and paren_depth == 0 and char in ";.!?:":
                flush(chunk.strip(), char)
                chunk = ""
                index += 1
                continue
            if not quote_char and paren_depth == 0 and char in {"-", "—", "–"} and next_char in {" ", ""}:
                flush(chunk.strip(), char)
                chunk = ""
                index += 1
                continue
            if not quote_char and paren_depth == 0 and char == "," and self._comma_should_split(chunk, text[index + 1:]):
                flush(chunk.strip(), char)
                chunk = ""
                index += 1
                continue
            chunk += char
            index += 1
        flush(chunk, "")
        return segments

    def _split_on_connectives(self, tokens: list[str]) -> list[tuple[list[str], str, str]]:
        pieces: list[tuple[list[str], str, str]] = []
        current: list[str] = []
        connective_before = ""
        relation_before = ""
        index = 0
        while index < len(tokens):
            token = tokens[index]
            remaining = tokens[index + 1:]
            relation = _CONNECTIVE_RELATIONS.get(token, "")
            should_split = (
                token in _GROUP_CONNECTIVES
                and current
                and remaining
                and (
                    token in _STRONG_SPLIT_CONNECTIVES and self._looks_predicative(remaining)
                    or token in _SUBORDINATING_CONNECTIVES and self._looks_predicative(remaining)
                    or (self._looks_predicative(current) and self._looks_predicative(remaining))
                )
            )
            if should_split:
                pieces.append((current, connective_before, relation_before))
                current = []
                connective_before = token
                relation_before = relation
            else:
                current.append(token)
            index += 1
        if current:
            pieces.append((current, connective_before, relation_before))
        return pieces

    def _looks_predicative(self, tokens: list[str]) -> bool:
        if not tokens:
            return False
        token_set = set(tokens)
        if token_set & _QUESTION_STARTERS or token_set & _COMMAND_CUES:
            return True
        if token_set & set(getattr(self._language, "ACTIONS", {}).keys()):
            return True
        if token_set & set(getattr(self._language, "STATES", {}).keys()):
            return True
        if len(tokens) == 1:
            return bool(token_set & _COMMON_PREDICATE_VERBS)
        if len(tokens) == 2 and tokens[0] in _PRONOUNS and tokens[1] in {"is", "are", "am", "was", "were", "do", "does", "did", "have", "has", *_COMMON_PREDICATE_VERBS}:
            return True
        return bool(token_set & {"is", "are", "am", "was", "were", "do", "does", "did", "have", "has", *_COMMON_PREDICATE_VERBS})

    def _comma_should_split(self, left: str, right: str) -> bool:
        left_tokens = self._language.tokenize(left)
        right_tokens = self._language.tokenize(right)
        if not left_tokens or not right_tokens:
            return False
        if len(right_tokens) <= 2 and not self._looks_predicative(right_tokens):
            return False
        return self._looks_predicative(right_tokens)

    def _initial_group_type(self, surface: str, tokens: list[str], trailing_separator: str = "") -> str:
        token_set = set(tokens)
        stripped = surface.strip()
        if stripped.endswith("?") or trailing_separator == "?" or (tokens and tokens[0] in _QUESTION_STARTERS):
            return "question"
        if token_set & _REPAIR_CUES and ("?" in stripped or trailing_separator == "?" or "what" in token_set or "huh" in token_set):
            return "repair"
        if token_set & _TEACHING_CUES:
            if token_set & {"is", "are"}:
                if len(tokens) >= 3 and tokens[0] not in _QUESTION_STARTERS:
                    return "teaching"
            else:
                return "teaching"
        if tokens and tokens[0] in _COMMAND_CUES:
            return "command"
        if token_set <= {"yes", "yeah", "yup", "no", "nah", "ok", "okay", "sure", "right"}:
            return "answer"
        return "clause"

    def _group_confidence(self, tokens: list[str], group_type: str, trailing_separator: str) -> float:
        confidence = 0.50
        n = len(tokens)
        if n > 0:
            confidence += min(0.10, n * 0.02)
        if trailing_separator == "?":
            confidence += 0.08
        if group_type in ("greeting", "acknowledgment", "exit"):
            confidence += 0.10
        elif group_type in ("question", "command"):
            confidence += 0.06
        elif group_type == "teaching":
            confidence += 0.04
        if n <= 1:
            confidence -= 0.08
        return max(0.30, min(0.95, confidence))

    def _extract_ner(self, tokens: list[str]) -> list[dict[str, Any]]:
        if self._ner_tagger is None or not tokens:
            return []
        return self._ner_tagger.extract_entities(tokens)

    def _extract_surface_tags(
        self,
        tokens: list[str],
        unknown_tokens: list[str],
    ) -> list[dict[str, Any]]:
        if self._surface_tagger is None or not tokens:
            return []
        return self._surface_tagger.extract_all(tokens, unknown_tokens=unknown_tokens)

    def _known_words(self) -> set[str]:
        if self._surface_tagger is None:
            return set()
        return set(getattr(self._surface_tagger, "_known_words", set()))

    def _add_ner_referents(
        self,
        packet: MeaningPerceptPacket,
        entities: Iterable[dict[str, Any]],
    ) -> None:
        for entity in entities:
            role = str(entity.get("role", "entity") or "entity").lower()
            if role not in _ENTITY_ROLES:
                continue
            entity_type = {"time": "abstract", "entity": "unknown"}.get(role, role)
            self._extend_referents(packet, [ReferentAtom(
                surface=str(entity.get("text", "")),
                entity_type=entity_type,
                role="topic",
                known=float(entity.get("confidence", 0.0) or 0.0) > 0.5,
                source="ner",
                confidence=float(entity.get("confidence", 0.5) or 0.5),
            )])

    def _add_capitalized_referents(
        self,
        packet: MeaningPerceptPacket,
        raw_text: str,
        known_words: set[str],
    ) -> None:
        existing = {r.surface.lower() for r in packet.referents if r.surface}
        for index, surface in enumerate(self._language.surface_tokens(raw_text)):
            clean = surface.strip(".,!?;:\"'()[]{}")
            if not clean or not clean[0].isupper():
                continue
            lower = self._language.normalize_surface(clean)
            if lower in existing:
                continue
            if self._language.is_entity_surface_excluded(clean, known_words):
                continue
            if self._active_lexeme(lower) is not None:
                continue
            existing.add(lower)
            self._extend_referents(packet, [ReferentAtom(
                surface=clean,
                entity_type="person",
                role="topic",
                known=False,
                source="capitalization",
                confidence=self._language.capitalization_confidence(clean, index),
            )])

    def _apply_surface_tags(
        self,
        packet: MeaningPerceptPacket,
        spans: Iterable[dict[str, Any]],
    ) -> None:
        for span in spans:
            surface = str(span.get("text", "") or "").strip()
            role = str(span.get("role", "") or "").lower()
            confidence = float(span.get("confidence", 0.6) or 0.6)
            if not surface:
                continue
            if role in _SURFACE_ACTION_ROLES:
                self._extend_actions(packet, [ActionAtom(
                    surface=surface,
                    action_key=self._canonical_key(surface),
                    confidence=confidence,
                )])
            elif role == "state":
                self._extend_states(packet, [StateAtom(
                    surface=surface,
                    state_key=self._canonical_key(surface),
                    holder_role="user",
                    confidence=confidence,
                )])
            elif role == "relation":
                self._extend_relations(packet, [RelationAtom(
                    relation_key=self._canonical_key(surface),
                    surface=surface,
                    confidence=confidence,
                )])

    def _apply_lexeme_memory(
        self,
        packet: MeaningPerceptPacket,
        tokens: list[str],
    ) -> None:
        if self._lexeme_memory is None or not tokens:
            return

        covered: set[tuple[int, int]] = set()
        for surface, start, end in self._language.ngrams(tokens, max_size=4):
            if any(start < covered_end and end > covered_start for covered_start, covered_end in covered):
                continue
            lexeme = self._active_lexeme(surface)
            if lexeme is None:
                continue

            role = self._lexeme_role(lexeme)
            mapped = lexeme.maps_to or lexeme.canonical or surface
            confidence = max(0.45, min(0.95, float(lexeme.confidence or 0.5)))
            if role == LexemeRole.ENTITY.value:
                self._extend_referents(packet, [ReferentAtom(
                    surface=surface,
                    entity_id=mapped if mapped else None,
                    entity_type="unknown",
                    role="topic",
                    known=True,
                    source="lexeme_memory",
                    confidence=confidence,
                )])
            elif role in {LexemeRole.PROCESS.value, LexemeRole.COMMAND_ALIAS.value}:
                self._extend_actions(packet, [ActionAtom(
                    surface=surface,
                    action_key=mapped,
                    confidence=confidence,
                )])
            elif role == LexemeRole.STATE.value:
                self._extend_states(packet, [StateAtom(
                    surface=surface,
                    state_key=mapped,
                    holder_role="user",
                    confidence=confidence,
                )])
            elif role == LexemeRole.RELATION.value:
                self._extend_relations(packet, [RelationAtom(
                    relation_key=mapped,
                    surface=surface,
                    confidence=confidence,
                )])
            covered.add((start, end))

    def _assign_atoms_to_groups(self, packet: MeaningPerceptPacket) -> None:
        for atom in [*packet.referents, *packet.actions, *packet.states, *packet.relations, *packet.needs]:
            surface = self._atom_surface(atom)
            group = self._group_for_surface(packet.meaning_groups, surface)
            if group is None:
                continue
            atom.group_id = group.id
            atom.span_id = self._span_id_for_group(packet, group)
            atom.evidence.append(AtomEvidence(
                source="group_assignment",
                span_id=atom.span_id,
                group_id=group.id,
                surface=surface,
                confidence=0.65,
                rationale="surface overlap with meaning group",
            ))
            if isinstance(atom, ReferentAtom):
                group.referents.append(atom)
            elif isinstance(atom, ActionAtom):
                group.actions.append(atom)
            elif isinstance(atom, StateAtom):
                group.states.append(atom)
            elif isinstance(atom, RelationAtom):
                group.relations.append(atom)
            elif isinstance(atom, NeedAtom):
                group.needs.append(atom)

    def _add_structural_atoms(self, packet: MeaningPerceptPacket) -> None:
        for group in packet.meaning_groups:
            token_set = set(group.tokens)
            intent_key = self._intent_key_for_group(group, packet)
            target_role = self._target_for_intent(group, intent_key)
            intent = IntentAtom(
                surface=group.surface,
                intent_key=intent_key,
                target_role=target_role,
                is_question=intent_key.endswith("query") or group.group_type == "question",
                is_command=intent_key in {"command", "memory_command"},
                polarity="negated" if token_set & _NEGATIONS else "affirmed",
                source="meaning_group_heuristic",
                confidence=self._intent_confidence(group, intent_key),
                group_id=group.id,
                span_id=self._span_id_for_group(packet, group),
                evidence=[AtomEvidence(
                    source="meaning_group",
                    span_id=self._span_id_for_group(packet, group),
                    group_id=group.id,
                    surface=group.surface,
                    confidence=0.65,
                    rationale=f"group_type={group.group_type}",
                )],
            )
            packet.intents.append(intent)
            group.intents.append(intent)
            group.candidate_act_types = self._candidate_act_types(intent_key)
            group.group_type = self._group_type_from_intent(intent_key, group.group_type)

            for token in group.tokens:
                if token in _MODAL_CUES:
                    packet.modalities.append(ModalityAtom(
                        surface=token,
                        modality_key=_MODAL_CUES[token],
                        polarity="negated" if token_set & _NEGATIONS else "affirmed",
                        confidence=0.65,
                        group_id=group.id,
                        span_id=self._span_id_for_group(packet, group),
                    ))
                if token in _TIME_CUES:
                    time_relation = (
                        "present" if token in {"now", "today", "currently"}
                        else "past" if token in {"yesterday", "recent"}
                        else "future" if token in {"tomorrow", "tonight"}
                        else "relative"
                    )
                    packet.times.append(TimeAtom(
                        surface=token,
                        time_key=token,
                        relation=time_relation,
                        confidence=0.6,
                        group_id=group.id,
                        span_id=self._span_id_for_group(packet, group),
                    ))
                if token in _PLACE_CUES:
                    packet.places.append(PlaceAtom(
                        surface=token,
                        place_key=token,
                        relation="deictic",
                        confidence=0.55,
                        group_id=group.id,
                        span_id=self._span_id_for_group(packet, group),
                    ))

            if token_set & _FRESH_WORLD_CUES:
                packet.evidence.append(EvidenceAtom(
                    surface=group.surface,
                    evidence_key="fresh_or_external_world_required",
                    source_role="external_world",
                    freshness="fresh",
                    confidence=0.7,
                    group_id=group.id,
                    span_id=self._span_id_for_group(packet, group),
                ))

    def _build_meaning_hypotheses(self, packet: MeaningPerceptPacket) -> None:
        for group in packet.meaning_groups:
            self._add_act_hypothesis(packet, group)
            self._add_lexical_hypotheses(packet, group)

    def _add_act_hypothesis(self, packet: MeaningPerceptPacket, group: MeaningGroup) -> None:
        if not group.candidate_act_types:
            return
        span_id = self._span_id_for_group(packet, group)
        selected = group.intents[0].intent_key if group.intents else ""
        candidates: list[CandidateInterpretation] = []
        for index, act_type in enumerate(group.candidate_act_types):
            candidate_id = f"hyp_{len(packet.meaning_hypotheses)}_act_{index}"
            candidates.append(CandidateInterpretation(
                id=candidate_id,
                group_id=group.id,
                span_id=span_id,
                surface=group.surface,
                interpretation_kind="act",
                atom_kind="intent",
                atom_key=act_type,
                candidate_act_type=act_type,
                confidence=max(0.25, group.confidence - index * 0.08),
                selected=act_type == selected or (index == 0 and selected not in group.candidate_act_types),
                evidence=[AtomEvidence(
                    source="candidate_act_types",
                    span_id=span_id,
                    group_id=group.id,
                    surface=group.surface,
                    confidence=group.confidence,
                    rationale="group intent can realize multiple pragmatic acts",
                )],
            ))
        hypothesis = MeaningHypothesis(
            id=f"hyp_{len(packet.meaning_hypotheses)}",
            group_id=group.id,
            span_id=span_id,
            surface=group.surface,
            hypothesis_type="act",
            candidates=candidates,
            selected_candidate_ids=[candidate.id for candidate in candidates if candidate.selected],
            confidence=group.confidence,
            reason="candidate_act_types",
        )
        packet.meaning_hypotheses.append(hypothesis)
        group.hypothesis_ids.append(hypothesis.id)

    def _add_lexical_hypotheses(self, packet: MeaningPerceptPacket, group: MeaningGroup) -> None:
        for token_index, token in enumerate(group.tokens):
            candidates_spec = _AMBIGUOUS_LEXEMES.get(token)
            if not candidates_spec:
                continue
            absolute_index = group.start_token + token_index
            span_id = self._span_id_for_token(packet, absolute_index)
            candidates: list[CandidateInterpretation] = []
            for index, spec in enumerate(candidates_spec):
                candidate_id = f"hyp_{len(packet.meaning_hypotheses)}_lex_{index}"
                candidates.append(CandidateInterpretation(
                    id=candidate_id,
                    group_id=group.id,
                    span_id=span_id,
                    surface=token,
                    interpretation_kind="lexical",
                    atom_kind=str(spec["atom_kind"]),
                    atom_key=str(spec["atom_key"]),
                    role=str(spec.get("role", "")),
                    features={"surface_token_index": absolute_index, "seed_ambiguous_lexeme": True},
                    confidence=float(spec.get("confidence", 0.4)),
                    selected=index == 0,
                    evidence=[AtomEvidence(
                        source="ambiguous_lexeme_seed",
                        span_id=span_id,
                        group_id=group.id,
                        surface=token,
                        confidence=float(spec.get("confidence", 0.4)),
                        rationale="surface has multiple common interpretations",
                    )],
                ))
            hypothesis = MeaningHypothesis(
                id=f"hyp_{len(packet.meaning_hypotheses)}",
                group_id=group.id,
                span_id=span_id,
                surface=token,
                hypothesis_type="lexical",
                candidates=candidates,
                selected_candidate_ids=[candidate.id for candidate in candidates if candidate.selected],
                confidence=max(candidate.confidence for candidate in candidates),
                reason="ambiguous_lexeme_seed",
            )
            packet.meaning_hypotheses.append(hypothesis)
            group.hypothesis_ids.append(hypothesis.id)

    def _intent_key_for_group(self, group: MeaningGroup, packet: MeaningPerceptPacket) -> str:
        tokens = group.tokens
        token_set = set(tokens)
        surface = group.surface.strip().lower()
        ends_with_question = surface.endswith("?") or group.separator_after == "?"
        if token_set & _EXIT_CUES:
            return "session_exit"
        if self._is_repair_group(group, packet):
            return "repair"
        if (group.group_type == "teaching" or self._is_teaching_group(group)) and not ends_with_question:
            return "teaching"
        if token_set & _FRESH_WORLD_CUES and (group.group_type == "question" or token_set & _QUESTION_STARTERS):
            return "fresh_world_query"
        if self._is_capability_query(group):
            return "capability_query"
        if group.group_type == "question" or ends_with_question or (tokens and tokens[0] in _QUESTION_STARTERS):
            return "question"
        if tokens and tokens[0] in _COMMAND_CUES:
            return "command"
        if group.states and any(state.holder_role == "user" for state in group.states):
            return "user_state_report"
        if token_set & {"hi", "hello", "hey", "hellooo"}:
            return "greeting"
        _greeting_forms = {"hi", "hello", "hey", "hellooo"}
        for form in packet.normalized_forms:
            if set(self._language.tokenize(form)) & _greeting_forms:
                return "greeting"
        if token_set <= {"yes", "yeah", "yup", "no", "nah", "ok", "okay", "sure", "right", "good"}:
            return "acknowledgment"
        return "statement"

    def _is_repair_group(self, group: MeaningGroup, packet: MeaningPerceptPacket) -> bool:
        token_set = set(group.tokens)
        if group.group_type == "repair":
            return True
        has_question = packet.punctuation_features.get("has_question_mark")
        if "huh" in token_set:
            return True
        if {"mean", "that"} <= token_set or {"what", "mean"} <= token_set:
            return True
        if group.group_type == "question" and has_question and {"what", "that"} <= token_set:
            return True
        if "what" in token_set and len(group.tokens) <= 2 and has_question:
            return True
        return False

    def _is_teaching_group(self, group: MeaningGroup) -> bool:
        token_set = set(group.tokens)
        if "teach" in token_set:
            return True
        if token_set & {"means", "called", "refers", "equals"}:
            return True
        if len(group.tokens) >= 3 and token_set & {"is", "are"} and group.tokens[0] not in _QUESTION_STARTERS:
            return True
        return False

    def _is_capability_query(self, group: MeaningGroup) -> bool:
        token_set = set(group.tokens)
        return bool(
            {"what", "can", "you"} <= token_set
            or {"can", "you"} <= token_set and token_set & {"do", "tell", "remember", "learn"}
        )

    def _target_for_intent(self, group: MeaningGroup, intent_key: str) -> str:
        token_set = set(group.tokens)
        if "you" in token_set or "your" in token_set:
            return "self"
        if intent_key in {"fresh_world_query", "question"}:
            return "world"
        if intent_key == "teaching":
            return "memory"
        return "conversation"

    def _candidate_act_types(self, intent_key: str) -> list[str]:
        return {
            "session_exit": ["session_exit", "social_closing"],
            "repair": ["confusion_repair", "retrospective_repair"],
            "fresh_world_query": ["evidence_query", "open_domain_entity_query"],
            "capability_query": ["self_capability_query", "capability_query"],
            "teaching": ["definition_teaching", "claim_assertion"],
            "user_state_report": ["state_report", "claim_assertion"],
            "greeting": ["greeting"],
            "acknowledgment": ["acknowledgment"],
            "command": ["command_request"],
            "question": ["question"],
        }.get(intent_key, ["claim_assertion" if intent_key == "statement" else intent_key])

    def _group_type_from_intent(self, intent_key: str, fallback: str) -> str:
        return {
            "session_exit": "closing",
            "repair": "repair",
            "fresh_world_query": "question",
            "capability_query": "question",
            "teaching": "teaching",
            "user_state_report": "state_report",
            "greeting": "social",
            "acknowledgment": "answer",
        }.get(intent_key, fallback)

    def _intent_confidence(self, group: MeaningGroup, intent_key: str) -> float:
        confidence = 0.55
        if group.group_type in {"question", "repair", "teaching", "command"}:
            confidence += 0.15
        if intent_key in {"fresh_world_query", "capability_query", "session_exit", "greeting"}:
            confidence += 0.1
        if group.actions or group.states:
            confidence += 0.05
        return min(0.9, confidence)

    def _group_for_surface(self, groups: list[MeaningGroup], surface: str) -> MeaningGroup | None:
        normalized = self._language.tokenize(surface)
        if not normalized:
            return None
        for group in groups:
            group_text = " ".join(group.tokens)
            surface_text = " ".join(normalized)
            if surface_text and surface_text in group_text:
                return group
        return None

    def _span_id_for_token(self, packet: MeaningPerceptPacket, token_index: int) -> str:
        for span in packet.spans:
            if span.span_type == "token" and span.start_token == token_index:
                return span.id
        return f"span_{token_index}"

    def _span_id_for_group(self, packet: MeaningPerceptPacket, group: MeaningGroup) -> str:
        for span in packet.spans:
            if span.span_type == "clause" and span.start_token <= group.start_token and span.end_token >= group.end_token:
                return span.id
        return f"group_span:{group.id}"

    @staticmethod
    def _group_by_id(groups: list[MeaningGroup], group_id: str) -> MeaningGroup | None:
        for group in groups:
            if group.id == group_id:
                return group
        return None

    @staticmethod
    def _atom_surface(atom: Any) -> str:
        surface = getattr(atom, "surface", "")
        if surface:
            return str(surface)
        for attr in ("need_key", "relation_key", "state_key", "action_key"):
            value = getattr(atom, attr, "")
            if value:
                return str(value)
        return ""

    def _add_unknown_lexemes(
        self,
        packet: MeaningPerceptPacket,
        unknown_tokens: list[str],
        tokens: list[str],
        known_words: set[str],
        semantic_spans: Iterable[dict[str, Any]],
    ) -> None:
        candidates = [str(t) for t in unknown_tokens]
        candidates.extend(
            str(span.get("text", ""))
            for span in semantic_spans
            if str(span.get("role", "")).lower() == "unknown_lexeme"
        )
        unknowns: list[dict[str, Any]] = []
        for surface in candidates:
            normalized = self._language.normalize_surface(surface)
            if not normalized or normalized in known_words:
                continue
            if self._active_lexeme(normalized) is not None:
                continue
            position = tokens.index(normalized) if normalized in tokens else -1
            unknowns.append({
                "surface": surface,
                "role": self._unknown_role(surface, normalized, tokens, position),
                "position": position,
                "confidence": 0.5,
            })
        packet.unknown_lexemes = self._dedupe_dicts(
            [*packet.unknown_lexemes, *unknowns],
            key_fields=("surface", "position"),
        )

    def _add_idiom_candidates(
        self,
        packet: MeaningPerceptPacket,
        tokens: list[str],
        unknown_tokens: list[str],
    ) -> None:
        unknown_set = {self._language.normalize_surface(t) for t in unknown_tokens}
        candidates: list[dict[str, Any]] = []
        if len(tokens) >= 3 and unknown_set:
            for start in range(0, len(tokens) - 2):
                phrase_tokens = tokens[start:start + 3]
                unknown_count = sum(1 for token in phrase_tokens if token in unknown_set)
                if unknown_count >= 2:
                    candidates.append({
                        "surface": " ".join(phrase_tokens),
                        "start": start,
                        "end": start + 3,
                        "confidence": 0.4,
                        "source": "unknown_sequence",
                    })

        if self._lexeme_memory is not None:
            for surface, start, end in self._language.ngrams(tokens, max_size=5):
                lexeme = self._active_lexeme(surface)
                if lexeme and self._lexeme_role(lexeme) == LexemeRole.COMMAND_ALIAS.value and " " in surface:
                    candidates.append({
                        "surface": surface,
                        "start": start,
                        "end": end,
                        "confidence": max(0.5, float(lexeme.confidence or 0.5)),
                        "source": "lexeme_memory",
                    })

        packet.idiom_candidates = self._dedupe_dicts(
            [*packet.idiom_candidates, *candidates],
            key_fields=("surface", "start", "end"),
        )

    def _unknown_role(
        self,
        surface: str,
        normalized: str,
        tokens: list[str],
        position: int,
    ) -> str:
        if position > 0 and tokens[position - 1] in {"you", "your", "you're"}:
            return "self_evaluation"
        if surface[:1].isupper():
            return "person_candidate"
        if position >= 0 and tokens[max(0, position - 2):position] and "teach" in tokens:
            return "teachable_surface"
        return "unknown"

    def _attention_target(
        self,
        packet: MeaningPerceptPacket,
        kernel: ContextKernel,
    ) -> str | None:
        for role in ("target", "object", "topic", "place"):
            for ref in packet.referents:
                if ref.role == role and ref.source not in {"pronoun", "deixis"} and ref.surface:
                    return ref.surface
        topic = getattr(getattr(kernel, "topic", None), "active_topic_surface", "")
        if topic:
            return topic
        for ref in packet.referents:
            if ref.surface:
                return ref.surface
        return None

    def _confidence(self, packet: MeaningPerceptPacket) -> float:
        evidence_atoms = (
            len(packet.referents)
            + len(packet.actions)
            + len(packet.states)
            + len(packet.relations)
            + len(packet.needs)
            + len(packet.intents)
            + len(packet.predicate_phrases)
            + len(packet.affect_markers)
        )
        uncertainty_penalty = min(0.25, len(packet.unknown_lexemes) * 0.04)
        lexical_bonus = min(0.35, evidence_atoms * 0.035)
        structure_bonus = min(0.18, (len(packet.meaning_groups) + len(packet.atom_outcomes)) * 0.025)
        if packet.actions and packet.referents:
            lexical_bonus += 0.08
        return max(0.2, min(0.95, 0.35 + lexical_bonus + structure_bonus - uncertainty_penalty))

    def _active_lexeme(self, surface: str) -> Any | None:
        if self._lexeme_memory is None:
            return None
        return self._lexeme_memory.lookup_active(surface)

    @staticmethod
    def _lexeme_role(lexeme: Any) -> str:
        role = getattr(lexeme, "role", "")
        return str(getattr(role, "value", role))

    def _canonical_key(self, surface: str) -> str:
        return "_".join(self._language.tokenize(surface))

    def _extend_referents(self, packet: MeaningPerceptPacket, atoms: Iterable[ReferentAtom]) -> None:
        seen = {
            (r.surface.lower(), r.entity_id or "", r.entity_type, r.role, r.source)
            for r in packet.referents
        }
        for atom in atoms:
            if not atom.surface:
                continue
            key = (atom.surface.lower(), atom.entity_id or "", atom.entity_type, atom.role, atom.source)
            if key in seen:
                continue
            packet.referents.append(atom)
            seen.add(key)

    def _extend_actions(self, packet: MeaningPerceptPacket, atoms: Iterable[ActionAtom]) -> None:
        seen = {(a.surface.lower(), a.action_key, a.modality, a.polarity) for a in packet.actions}
        for atom in atoms:
            key = (atom.surface.lower(), atom.action_key, atom.modality, atom.polarity)
            if not atom.surface or key in seen:
                continue
            packet.actions.append(atom)
            seen.add(key)

    def _extend_states(self, packet: MeaningPerceptPacket, atoms: Iterable[StateAtom]) -> None:
        seen = {(s.surface.lower(), s.state_key, s.holder_role, s.dimension) for s in packet.states}
        for atom in atoms:
            key = (atom.surface.lower(), atom.state_key, atom.holder_role, atom.dimension)
            if not atom.surface or key in seen:
                continue
            packet.states.append(atom)
            seen.add(key)

    def _extend_relations(self, packet: MeaningPerceptPacket, atoms: Iterable[RelationAtom]) -> None:
        seen = {(r.relation_key, r.source_role, r.target_role) for r in packet.relations}
        for atom in atoms:
            key = (atom.relation_key, atom.source_role, atom.target_role)
            if not atom.relation_key or key in seen:
                continue
            packet.relations.append(atom)
            seen.add(key)

    def _extend_needs(self, packet: MeaningPerceptPacket, atoms: Iterable[NeedAtom]) -> None:
        seen = {(n.holder_role, n.need_key) for n in packet.needs}
        for atom in atoms:
            key = (atom.holder_role, atom.need_key)
            if not atom.need_key or key in seen:
                continue
            packet.needs.append(atom)
            seen.add(key)

    @staticmethod
    def _dedupe_dicts(
        values: Iterable[dict[str, Any]],
        key_fields: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for value in values:
            key = tuple(value.get(field) for field in key_fields)
            if key in seen:
                continue
            result.append(value)
            seen.add(key)
        return result
