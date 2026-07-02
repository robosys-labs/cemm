from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ..registry.uol_mapper import UOLMapper
from ..store.artifact_store import ArtifactStore
from ..store.store import Store
from ..types.semantic_event_graph import SemanticEventGraph, SemanticEdge
from ..types.signal import Signal
from ..types.context_kernel import ContextKernel
from ..types.meaning_percept import MeaningPerceptPacket, SituationFrame
from ..learning.surface_tagger import SurfaceTagger
from ..learning.lexeme_memory import LexemeMemory


_SEMANTIC_INTERPRETER_WORDS_PATH = Path(__file__).parents[1] / "data" / "semantic_interpreter_words.json"


def _load_semantic_interpreter_words() -> dict[str, Any]:
    if not _SEMANTIC_INTERPRETER_WORDS_PATH.exists():
        return {}
    return json.loads(_SEMANTIC_INTERPRETER_WORDS_PATH.read_text(encoding="utf-8"))


def _load_default_ner_tagger() -> "NERTagger | None":
    """Load the bundled learned NER tagger if available."""
    try:
        from ..learning.ner_tagger import NERTagger
    except ImportError:
        return None
    # Locate bundled weights relative to this source file.
    weights_path = Path(__file__).with_name("data") / "models" / "ner_tagger_weights.json"
    if weights_path.exists():
        return NERTagger.load(weights_path)
    # Fallback for development layout where data is under the package root.
    alt_path = Path(__file__).parents[1] / "data" / "models" / "ner_tagger_weights.json"
    if alt_path.exists():
        return NERTagger.load(alt_path)
    return None


class SemanticInterpreter:
    def __init__(
        self,
        uol_mapper: UOLMapper,
        artifact_store: ArtifactStore | None = None,
        store: Store | None = None,
        lexeme_memory: LexemeMemory | None = None,
        text_normalizer: Any | None = None,
    ) -> None:
        self._uol_mapper = uol_mapper
        self._artifact_store = artifact_store
        self._store = store
        self._lexeme_memory = lexeme_memory
        self._text_normalizer = text_normalizer
        self._ner_tagger = _load_default_ner_tagger()
        known_words = getattr(text_normalizer, "_known_words", None)
        semantic_role_cues = getattr(text_normalizer, "_semantic_role_cues", None)
        self._surface_tagger = SurfaceTagger(
            self._ner_tagger,
            known_words=known_words,
            lexeme_memory=lexeme_memory,
            semantic_role_cues=semantic_role_cues,
        )
        words = _load_semantic_interpreter_words()
        self._stop_words = set(words.get("stop_words", []))
        self._stop_words_caseful = {w.capitalize() for w in self._stop_words}
        self._command_words = set(words.get("command_words", []))
        self._causal_relations = {
            k: tuple(v) for k, v in words.get("causal_relations", {}).items()
        }
        self._temporal_relations = {
            k: tuple(v) for k, v in words.get("temporal_relations", {}).items()
        }
        self._causal_edge_relations = dict(words.get("causal_edge_relations", {}))
        self._target_prepositions = set(words.get("target_prepositions", []))

    def run(
        self,
        signal: Signal,
        kernel: ContextKernel,
        meaning_percept: MeaningPerceptPacket | None = None,
        situation_frame: SituationFrame | None = None,
    ) -> SemanticEventGraph:
        # When a MeaningPerceptPacket is available, use its pre-bound atoms
        # to enrich the graph and skip redundant NER/SurfaceTagger calls.
        if self._artifact_store:
            artifact = self._artifact_store.get_active_artifact("uol_semantic")
            if artifact:
                best = self._artifact_store.find_example(artifact, signal.content)
                if best:
                    output = best.get("output", {})
                    atoms_data: list[dict[str, Any]] = output.get("uol_atoms", [])
                    if atoms_data:
                        graph = self._build_graph(signal, kernel, atoms_data)
                        if meaning_percept:
                            graph = self._enrich_with_percept(graph, meaning_percept, situation_frame)
                        return graph

        atoms = self._uol_mapper.map_signal(signal.content, kernel)
        graph = self._build_graph(
            signal, kernel,
            [a.__dict__ for a in atoms],
        )
        if meaning_percept:
            graph = self._enrich_with_percept(graph, meaning_percept, situation_frame)
        return graph

    def _build_graph(
        self,
        signal: Signal,
        kernel: ContextKernel,
        atoms_data: list[dict[str, Any]],
    ) -> SemanticEventGraph:
        entity_refs = [a for a in atoms_data if a.get("kind") == "entity_ref"]
        processes = [a for a in atoms_data if a.get("kind") == "process"]
        states = [a for a in atoms_data if a.get("kind") == "state"]
        base_confidence = max(
            [a.get("confidence", 0.0) for a in atoms_data],
            default=0.5,
        )

        # Infer entity refs from causal/temporal processes when the UOL mapper
        # did not produce entity atoms. This keeps downstream causal inference
        # and simulation from operating on "unknown" cause/effect IDs.
        if not entity_refs and processes:
            entity_refs = self._infer_entity_refs_from_processes(signal.content, processes)
        # Fallback to rule-based named entity extraction when the UOL mapper and
        # process inference both fail to produce entity refs.
        if not entity_refs:
            entity_refs = self._extract_named_entities(signal.content)

        # Surface semantic layer: enrich entity refs with tagged spans, unknown
        # lexemes, and learned aliases from the surface tagger.
        entity_refs = self._merge_surface_semantics(signal, entity_refs)

        claim_refs = self._lookup_claim_refs(entity_refs, kernel)
        claim_candidates = self._extract_claim_candidates_from_atoms(signal.content, processes, entity_refs)
        model_refs = self._lookup_model_refs(processes, entity_refs, signal.content)
        action_refs = self._extract_action_refs(processes)
        temporal_edges = self._extract_temporal_edges_from_atoms(processes, entity_refs)
        causal_edges = self._extract_causal_edges_from_atoms(processes, entity_refs)

        return SemanticEventGraph(
            id=uuid.uuid4().hex[:16],
            source_signal_ids=[signal.id],
            context_id=kernel.id,
            entity_refs=entity_refs,
            processes=processes,
            states=states,
            claim_refs=claim_refs,
            claim_candidates=claim_candidates,
            model_refs=model_refs,
            action_refs=action_refs,
            temporal_edges=temporal_edges,
            causal_edges=causal_edges,
            permission_scope=kernel.permission.scope.value,
            confidence=base_confidence,
        )

    def _lookup_claim_refs(
        self, entity_refs: list[dict[str, Any]], kernel: ContextKernel,
    ) -> list[str]:
        if not self._store:
            return list(kernel.memory.working_claim_ids[:10])
        claim_ids: list[str] = []
        seen: set[str] = set()

        for ref in entity_refs:
            eid = ref.get("entity_id", "") or ref.get("entity", "")
            if not eid:
                continue
            claims = self._store.claims.find_by_subject(eid, limit=5)
            for c in claims:
                if c.id not in seen:
                    claim_ids.append(c.id)
                    seen.add(c.id)
                    if len(claim_ids) >= 20:
                        break
            if len(claim_ids) >= 20:
                break

        for cid in kernel.memory.working_claim_ids:
            if cid not in seen:
                claim_ids.append(cid)
                seen.add(cid)
                if len(claim_ids) >= 20:
                    break

        return claim_ids

    def _extract_claim_candidates_from_atoms(
        self, content: str, processes: list[dict[str, Any]], entity_refs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        content_lower = content.lower().strip()

        for proc in processes:
            frame_key = proc.get("frame_key", "")
            if not frame_key.startswith("claim_"):
                continue
            predicate = frame_key[len("claim_"):]
            subject = "user"
            for ref in entity_refs:
                if ref.get("role") == "actor":
                    subject = ref.get("entity_id", "") or ref.get("entity", "user")
                    break
            if subject == "user":
                for ref in entity_refs:
                    if ref.get("role") in ("cause", "source"):
                        subject = ref.get("entity_id", "") or ref.get("entity", "user")
                        break
            obj = ""
            words = content_lower.split()
            predicate_markers = {predicate}
            if predicate.endswith("s") and len(predicate) > 1:
                predicate_markers.add(predicate[:-1])
            predicate_markers.update(self._get_predicate_aliases(predicate))
            for i, w in enumerate(words):
                if w in predicate_markers:
                    if i + 1 < len(words):
                        obj = words[i + 1]
                    break
            candidates.append({
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "confidence": proc.get("confidence", 0.5),
            })
        return candidates

    def _get_predicate_aliases(self, canonical: str) -> list[str]:
        if not self._store:
            return []
        return []

    def _lookup_model_refs(
        self,
        processes: list[dict[str, Any]],
        entity_refs: list[dict[str, Any]],
        content: str,
    ) -> list[str]:
        if not self._store:
            return []
        from ..types.model import ModelKind, ModelStatus
        model_ids: list[str] = []
        seen: set[str] = set()
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            if not frame_key:
                continue
            # Prefer registry-key lookup first, then fall back to name search.
            model = self._store.models.find_by_registry_key(frame_key)
            if model and model.id not in seen:
                model_ids.append(model.id)
                seen.add(model.id)
                if len(model_ids) >= 10:
                    break
                continue
            models = self._store.models.find_by_name(frame_key)
            for m in models:
                if m.id not in seen:
                    model_ids.append(m.id)
                    seen.add(m.id)
                    if len(model_ids) >= 10:
                        break
            if len(model_ids) >= 10:
                break

        # Match entity phrases against model preconditions/effects so the
        # correct model is selected when many models share the same registry key.
        if self._store and len(model_ids) < 10:
            entity_phrases = {
                (ref.get("entity_id", "") or ref.get("entity", "")).lower()
                for ref in entity_refs
            }
            entity_phrases.discard("")
            # Also include individual words from the content to catch short keywords
            for word in content.lower().split():
                if len(word) > 3:
                    entity_phrases.add(word)
            if entity_phrases:
                for model in self._store.models.find_by_kind(
                    ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value, limit=100
                ):
                    for phrase in entity_phrases:
                        preconditions = [p.lower() for p in (model.preconditions or [])]
                        effects = [e.lower() for e in (model.effects or [])]
                        if any(phrase in pre or phrase in eff for pre in preconditions for eff in effects):
                            if model.id not in seen:
                                model_ids.append(model.id)
                                seen.add(model.id)
                            break
                    if len(model_ids) >= 10:
                        break
        return model_ids

    def _extract_action_refs(self, processes: list[dict[str, Any]]) -> list[str]:
        """Map actionable processes to action references for downstream routing."""
        action_keys = {
            "command_remember": "remember",
            "command_reflect": "reflect",
            "command_retrieve": "retrieve",
            "greeting": "greeting",
            "session_exit": "session_exit",
            "phatic_checkin": "phatic_checkin",
            "teaching_offer": "teaching_offer",
            "confusion_repair": "confusion_repair",
            "playful_repair": "playful_repair",
            "frustration_signal": "frustration_signal",
            "story_request": "story_request",
            "open_domain_entity_query": "open_domain_entity_query",
        }
        refs: list[str] = []
        seen: set[str] = set()
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            action = action_keys.get(frame_key)
            if action and action not in seen:
                refs.append(action)
                seen.add(action)
        return refs

    def _extract_temporal_edges_from_atoms(
        self, processes: list[dict[str, Any]], entity_refs: list[dict[str, Any]],
    ) -> list[SemanticEdge]:
        edges: list[SemanticEdge] = []
        entity_ids = [
            ref.get("entity_id", "") or ref.get("entity", "")
            for ref in entity_refs
        ]
        entity_ids = [e for e in entity_ids if e]
        if len(entity_ids) < 2:
            return edges
        temporal_map = {
            "temporal_before": "before",
            "temporal_after": "after",
            "temporal_during": "during",
            "temporal_overlaps": "overlaps",
            "temporal_starts": "starts",
            "temporal_finishes": "finishes",
        }
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            relation = temporal_map.get(frame_key)
            if relation:
                edges.append(SemanticEdge(
                    source_id=entity_ids[0],
                    target_id=entity_ids[1],
                    relation=relation,
                    confidence=proc.get("confidence", 0.6),
                    confidence_type="inferred",
                ))
                break
        return edges

    def _extract_causal_edges_from_atoms(
        self, processes: list[dict[str, Any]], entity_refs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]] = []
        entity_ids = [
            ref.get("entity_id", "") or ref.get("entity", "")
            for ref in entity_refs
        ]
        entity_ids = [e for e in entity_ids if e]
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            relation = self._causal_edge_relations.get(frame_key)
            if relation:
                cause_id = entity_ids[0] if entity_ids else "unknown"
                effect_id = entity_ids[1] if len(entity_ids) > 1 else "unknown"
                edges.append({
                    "cause_id": cause_id,
                    "effect_id": effect_id,
                    "relation": relation,
                    "confidence": proc.get("confidence", 0.6),
                    "confidence_type": "inferred",
                })
                break
        return edges

    def _infer_entity_refs_from_processes(
        self, content: str, processes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Infer entity refs from causal/temporal processes when no entity atoms are present."""
        inferred: list[dict[str, Any]] = []
        content_lower = content.lower().strip()
        words = content_lower.split()
        if len(words) < 3:
            return inferred

        is_causal = any(proc.get("frame_key", "").startswith("causal_") for proc in processes)
        relation_words: set[str] = set()
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            relation_words.update(self._causal_relations.get(frame_key, ()))
            relation_words.update(self._temporal_relations.get(frame_key, ()))

        if not relation_words:
            return inferred

        marker_index: int | None = None
        for i, w in enumerate(words):
            if w in relation_words:
                marker_index = i
                break
            if i + 1 < len(words):
                bigram = f"{w} {words[i + 1]}"
                if bigram in relation_words:
                    marker_index = i
                    break

        if marker_index is None:
            return inferred

        source_start = marker_index - 1
        while source_start >= 0 and words[source_start] in self._command_words:
            source_start -= 1
        source_phrase = self._expand_entity_phrase(words, source_start, -1) if source_start >= 0 else ""
        target_start = marker_index + 1
        if target_start < len(words) and words[target_start] in self._target_prepositions:
            target_start += 1
        target_phrase = self._expand_entity_phrase(words, target_start, 1)

        if source_phrase:
            inferred.append({
                "kind": "entity_ref",
                "entity_id": source_phrase,
                "role": "cause" if is_causal else "source",
                "confidence": 0.6,
            })
        if target_phrase:
            inferred.append({
                "kind": "entity_ref",
                "entity_id": target_phrase,
                "role": "effect" if is_causal else "target",
                "confidence": 0.6,
            })

        return inferred

    def _expand_entity_phrase(
        self, words: list[str], center_index: int, direction: int,
    ) -> str:
        """Expand a single-word entity into a short phrase by including adjacent modifiers.

        direction: -1 for left (source), +1 for right (target).
        """
        if not (0 <= center_index < len(words)):
            return ""
        phrase = [words[center_index]]
        i = center_index + direction
        while 0 <= i < len(words):
            w = words[i]
            if w in self._stop_words or w in self._command_words:
                break
            if direction < 0:
                phrase.insert(0, w)
            else:
                phrase.append(w)
            i += direction
        return " ".join(phrase)

    def _merge_surface_semantics(
        self, signal: Signal, entity_refs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enrich entity refs with surface-tagged semantic spans and unknown lexemes."""
        unknowns: list[str] = []
        if signal.normalized and signal.normalized.unknown_tokens:
            unknowns = signal.normalized.unknown_tokens
        words = signal.content.split()
        seen = {e.get("entity_id", "").lower() for e in entity_refs}
        seen.discard("")
        for span in self._surface_tagger.extract_semantic_spans(words, unknowns):
            text = span.get("text", "").lower()
            if not text or text in seen:
                continue
            seen.add(text)
            entity_refs.append({
                "kind": "entity_ref",
                "entity_id": text,
                "role": span.get("role", "entity"),
                "confidence": span.get("confidence", 0.6),
            })
        return entity_refs

    def _enrich_with_percept(
        self,
        graph: SemanticEventGraph,
        percept: MeaningPerceptPacket,
        situation: SituationFrame | None = None,
    ) -> SemanticEventGraph:
        """Enrich SemanticEventGraph with pre-bound atoms from MeaningPerceptPacket.

        Per §8.13: SemanticInterpreter should consume MeaningPerceptPacket +
        SituationFrame, not raw text only. When a percept is available, we use
        its pre-bound referents/actions/states to enrich entity_refs, processes,
        and states — skipping the redundant internal SurfaceTagger/NER calls
        that _build_graph would otherwise make.
        """
        seen_entities = {e.get("entity_id", "").lower() for e in graph.entity_refs}
        seen_entities.discard("")

        # Add referents from percept that aren't already in entity_refs
        for ref in percept.referents:
            text = ref.surface.lower()
            if text and text not in seen_entities:
                seen_entities.add(text)
                graph.entity_refs.append({
                    "kind": "entity_ref",
                    "entity_id": text,
                    "role": ref.role,
                    "entity_type": ref.entity_type,
                    "confidence": ref.confidence,
                    "source": ref.source,
                })

        # Add action atoms as processes
        seen_processes = {p.get("frame_key", "") for p in graph.processes}
        for action in percept.actions:
            if action.action_key and action.action_key not in seen_processes:
                seen_processes.add(action.action_key)
                graph.processes.append({
                    "kind": "process",
                    "frame_key": action.action_key,
                    "surface": action.surface,
                    "modality": action.modality,
                    "polarity": action.polarity,
                    "confidence": action.confidence,
                })

        # Add state atoms
        seen_states = {s.get("state_key", "") for s in graph.states}
        for state in percept.states:
            if state.state_key and state.state_key not in seen_states:
                seen_states.add(state.state_key)
                graph.states.append({
                    "kind": "state",
                    "state_key": state.state_key,
                    "surface": state.surface,
                    "holder_role": state.holder_role,
                    "dimension": state.dimension,
                    "polarity": state.polarity,
                    "confidence": state.confidence,
                })

        # Add unknown lexemes as entity_refs with role=unknown_lexeme
        for lex in percept.unknown_lexemes:
            surface = lex.get("surface", "").lower()
            if surface and surface not in seen_entities:
                seen_entities.add(surface)
                graph.entity_refs.append({
                    "kind": "entity_ref",
                    "entity_id": surface,
                    "role": "unknown_lexeme",
                    "confidence": lex.get("confidence", 0.5),
                })

        # Enrich with situation frame outcomes if available
        if situation and situation.expected_outcomes:
            for outcome in situation.expected_outcomes:
                if outcome.event_key and outcome.event_key not in seen_processes:
                    seen_processes.add(outcome.event_key)
                    graph.processes.append({
                        "kind": "process",
                        "frame_key": outcome.event_key,
                        "confidence": outcome.confidence,
                    })

        # Boost graph confidence if percept has high confidence
        if percept.confidence > graph.confidence:
            graph.confidence = percept.confidence

        return graph

    def _extract_named_entities(self, content: str) -> list[dict[str, Any]]:
        """Extract named entities from content when the UOL mapper provides none.

        Uses a learned NER tagger if available; otherwise falls back to a minimal
        rule-based extractor for capitalized phrases, temporal expressions, and numbers.
        """
        words = content.split()
        if self._ner_tagger is not None:
            entities: list[dict[str, Any]] = []
            seen: set[str] = set()
            for ent in self._ner_tagger.extract_entities(words):
                text = ent["text"].lower()
                if text in seen:
                    continue
                seen.add(text)
                entities.append({
                    "kind": "entity_ref",
                    "entity_id": text,
                    "role": ent["role"],
                    "confidence": 0.7,
                })
            if entities:
                return entities

        entities = []
        seen = set()

        # Capitalized proper-noun phrases (naive; stop words are loaded from
        # cemm/data/semantic_interpreter_words.json).
        i = 0
        while i < len(words):
            word = words[i].strip(".,!?;:\"'")
            if word and word[0].isupper() and word not in self._stop_words_caseful:
                phrase = [word]
                j = i + 1
                while j < len(words):
                    next_word = words[j].strip(".,!?;:\"'")
                    if not next_word or next_word in self._stop_words_caseful or not next_word[0].isupper():
                        break
                    phrase.append(next_word)
                    j += 1
                entity_text = " ".join(phrase).lower()
                if entity_text not in seen:
                    entities.append({
                        "kind": "entity_ref",
                        "entity_id": entity_text,
                        "role": "entity",
                        "confidence": 0.6,
                    })
                    seen.add(entity_text)
                i = j
            else:
                i += 1

        # Temporal expressions
        temporal_words = {
            "today", "tomorrow", "yesterday", "now", "later", "soon", "morning", "afternoon", "evening", "night",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        }
        for raw in words:
            w = raw.lower().strip(".,!?;:\"'")
            if w in temporal_words and w not in seen:
                entities.append({
                    "kind": "entity_ref",
                    "entity_id": w,
                    "role": "time",
                    "confidence": 0.5,
                })
                seen.add(w)

        # Numeric quantities (cardinals)
        for raw in words:
            w = raw.strip(".,!?;:\"'")
            if w.isdigit() and w not in seen:
                entities.append({
                    "kind": "entity_ref",
                    "entity_id": w,
                    "role": "quantity",
                    "confidence": 0.5,
                })
                seen.add(w)

        return entities
