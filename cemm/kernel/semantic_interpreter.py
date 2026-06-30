from __future__ import annotations

import uuid
from typing import Any

from ..registry.uol_mapper import UOLMapper
from ..store.artifact_store import ArtifactStore
from ..store.store import Store
from ..types.semantic_event_graph import SemanticEventGraph, SemanticEdge
from ..types.signal import Signal
from ..types.context_kernel import ContextKernel


class SemanticInterpreter:
    def __init__(
        self,
        uol_mapper: UOLMapper,
        artifact_store: ArtifactStore | None = None,
        store: Store | None = None,
    ) -> None:
        self._uol_mapper = uol_mapper
        self._artifact_store = artifact_store
        self._store = store

    def run(self, signal: Signal, kernel: ContextKernel) -> SemanticEventGraph:
        if self._artifact_store:
            artifact = self._artifact_store.get_active_artifact("uol_semantic")
            if artifact:
                best = self._artifact_store.find_example(artifact, signal.content)
                if best:
                    output = best.get("output", {})
                    atoms_data: list[dict[str, Any]] = output.get("uol_atoms", [])
                    if atoms_data:
                        return self._build_graph(signal, kernel, atoms_data)

        atoms = self._uol_mapper.map_signal(signal.content, kernel)
        return self._build_graph(
            signal, kernel,
            [a.__dict__ for a in atoms],
        )

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

        claim_refs = self._lookup_claim_refs(entity_refs, kernel)
        claim_candidates = self._extract_claim_candidates_from_atoms(signal.content, processes, entity_refs)
        model_refs = self._lookup_model_refs(processes)
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
            for i, w in enumerate(words):
                if w in (predicate, ) or any(
                    w == alias for alias in self._get_predicate_aliases(predicate)
                ):
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

    def _lookup_model_refs(self, processes: list[dict[str, Any]]) -> list[str]:
        if not self._store:
            return []
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
        return model_ids

    def _extract_action_refs(self, processes: list[dict[str, Any]]) -> list[str]:
        """Map actionable processes to action references for downstream routing."""
        action_keys = {
            "command_remember": "remember",
            "command_reflect": "reflect",
            "command_retrieve": "retrieve",
            "greeting": "greeting",
            "session_exit": "session_exit",
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
        causal_map = {
            "causal_causes": "causes",
            "causal_caused_by": "caused_by",
            "causal_leads_to": "leads_to",
            "causal_because": "because",
            "causal_so": "so",
        }
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            relation = causal_map.get(frame_key)
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

        causal_map = {
            "causal_causes": ("causes", "caused", "cause"),
            "causal_caused_by": ("caused by", "caused", "by"),
            "causal_leads_to": ("leads to", "leads", "lead to"),
            "causal_because": ("because",),
            "causal_so": ("so",),
        }
        temporal_map = {
            "temporal_before": ("before",),
            "temporal_after": ("after",),
            "temporal_during": ("during",),
            "temporal_overlaps": ("overlaps", "while"),
            "temporal_starts": ("starts", "begins"),
            "temporal_finishes": ("finishes", "ends"),
        }

        is_causal = any(proc.get("frame_key", "").startswith("causal_") for proc in processes)
        relation_words: set[str] = set()
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            relation_words.update(causal_map.get(frame_key, ()))
            relation_words.update(temporal_map.get(frame_key, ()))

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

        source_phrase = self._expand_entity_phrase(words, marker_index - 1, -1)
        target_start = marker_index + 1
        if target_start < len(words) and words[target_start] in ("by", "to", "with"):
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
        stop_words = {
            "the", "a", "an", "and", "or", "but", "if", "then", "than", "to", "of", "in", "on", "at", "for",
            "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these",
            "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "what", "which",
            "who", "when", "where", "why", "how", "all", "each", "every", "some", "any", "no", "not", "only", "just",
        }
        phrase = [words[center_index]]
        i = center_index + direction
        while 0 <= i < len(words):
            w = words[i]
            if w in stop_words:
                break
            if direction < 0:
                phrase.insert(0, w)
            else:
                phrase.append(w)
            i += direction
        return " ".join(phrase)
