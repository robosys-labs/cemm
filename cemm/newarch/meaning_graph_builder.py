"""Build UOL graphs from MeaningPerceptPacket objects.

This is the bridge from the compatibility packet layer into the working graph:

    utterance -> meaning groups -> UOL atoms/edges -> concept resolutions
    -> dynamic port bindings -> affordance predictions -> graph patches

The builder is conservative. It does not try to solve all parsing problems. It
turns already-perceived atoms into a graph with enough role, evidence, time,
source, permission, self, and causal structure for planning and training.
It does not mutate durable memory.
"""

from __future__ import annotations

from typing import Any, Iterable
import uuid

from ..types.meaning_percept import (
    ActionAtom,
    EvidenceAtom,
    IntentAtom,
    MeaningAtomOutcome,
    MeaningGroup,
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
    TimeAtom,
)
from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.uol_graph import (
    AffordancePrediction,
    CandidateSet,
    ConceptResolution,
    ConstructionMatch,
    PortBinding,
    UOLAtom,
    UOLEdge,
    UOLGraph,
)


class MeaningGraphBuilder:
    """Construct the canonical UOL graph for one meaning packet."""

    def __init__(
        self,
        concept_lattice: Any | None = None,
        port_resolver: Any | None = None,
        affordance_lattice: Any | None = None,
        construction_lattice: Any | None = None,
    ) -> None:
        self._concept_lattice = concept_lattice
        self._port_resolver = port_resolver
        self._affordance_lattice = affordance_lattice
        self._construction_lattice = construction_lattice

    def build(self, packet: MeaningPerceptPacket) -> UOLGraph:
        graph = UOLGraph(
            id=uuid.uuid4().hex[:16],
            signal_id=packet.signal_id,
            context_id=packet.context_id,
            raw_text=packet.raw_text,
            language=packet.language,
            trace={
                "builder": "meaning_graph_builder_v1",
                "packet_id": packet.id,
                "packet_version": packet.version,
            },
        )

        self_atom = graph.add_atom(
            "self",
            packet.listener_entity_id or "self",
            surface="self",
            confidence=0.9,
            source="context",
            features={"role": "listener"},
        )
        user_atom = graph.add_atom(
            "entity",
            packet.speaker_entity_id or "user",
            surface="user",
            confidence=0.9,
            source="context",
            features={"entity_type": "user", "role": "speaker"},
        )
        source_atom = self._source_atom(graph, SourceAtom(
            source_role="user",
            surface=packet.raw_text,
            reliability="speaker_asserted",
            permission_scope="conversation",
            confidence=0.7,
        ))
        permission_atom = graph.add_atom(
            "permission",
            "conversation",
            surface="conversation",
            confidence=0.75,
            source="context",
            features={"scope": "conversation"},
        )
        graph.add_edge("refers_to", source_atom.id, user_atom.id, confidence=0.75, features={"role": "speaker"})
        graph.add_edge("enables", permission_atom.id, source_atom.id, confidence=0.65, features={"scope": "conversation"})
        graph.add_edge("refers_to", self_atom.id, self_atom.id, confidence=0.5, features={"reflexive": True})

        for item in getattr(packet, "self_atoms", []):
            self._self_atom(graph, item)

        for item in getattr(packet, "permissions", []):
            permission = self._permission_atom(graph, item)
            target_sources = graph.atoms_by_kind("source", item.group_id or None)
            for target in target_sources:
                graph.add_edge(
                    "enables",
                    permission.id,
                    target.id,
                    group_id=item.group_id,
                    confidence=min(item.confidence, target.confidence),
                    features={"scope": item.scope, "target_role": item.target_role},
                )

        for source in packet.sources:
            atom = self._source_atom(graph, source)
            permission = graph.add_atom(
                "permission",
                source.permission_scope or "public",
                surface=source.permission_scope or "public",
                group_id=source.group_id,
                span_id=source.span_id,
                confidence=source.confidence,
                source="source_atom",
                features={"scope": source.permission_scope or "public"},
            )
            graph.add_edge(
                "enables",
                permission.id,
                atom.id,
                group_id=source.group_id,
                confidence=min(source.confidence, 0.75),
                features={"permission_scope": source.permission_scope or "public"},
            )

        self._add_group_structures(graph, packet)
        self._add_referents(graph, packet.referents)
        self._add_actions(graph, packet.actions, packet.meaning_groups)
        self._add_states(graph, packet.states)
        self._add_relations(graph, packet.relations)
        self._add_needs(graph, packet.needs)
        self._add_times(graph, packet.times)
        self._add_places(graph, packet.places)
        self._add_modalities(graph, packet.modalities)
        self._add_evidence(graph, packet.evidence)
        self._add_surface_teaching_relations(graph, packet.meaning_groups)
        self._add_intents(graph, packet.intents, packet.meaning_groups)
        self._add_predicates(graph, packet.predicate_phrases)
        self._add_outcomes(graph, packet.atom_outcomes)
        self._add_group_temporal_place_edges(graph, packet.meaning_groups)
        self._add_candidate_sets(graph, packet)
        self._add_construction_matches(graph, packet)
        self._resolve_concepts(graph)
        self._resolve_ports(graph)
        self._predict_affordances(graph)
        self._extract_graph_patches(graph)

        graph.trace.update({
            "atom_count": len(graph.atoms),
            "edge_count": len(graph.edges),
            "group_count": len(packet.meaning_groups),
            "candidate_set_count": len(graph.candidate_sets),
            "construction_match_count": len(graph.construction_matches),
            "concept_resolution_count": len(graph.concept_resolutions),
            "port_binding_count": len(graph.port_bindings),
            "affordance_prediction_count": len(graph.affordance_predictions),
            "graph_patch_candidate_count": len(graph.patch_candidates),
        })
        return graph

    def _add_group_structures(self, graph: UOLGraph, packet: MeaningPerceptPacket) -> None:
        for group in packet.meaning_groups:
            if not group.tokens:
                continue
            graph.add_group(
                group.id,
                surface=group.surface,
                parent_group_id=group.parent_group_id,
                start_token=group.start_token,
                end_token=group.end_token,
                function=group.group_type,
                confidence=group.confidence,
                features={
                    "connective_before": group.connective_before,
                    "separator_before": group.separator_before,
                    "relation_to_parent": group.relation_to_parent,
                    "child_group_ids": list(group.child_group_ids),
                    "candidate_act_types": list(group.candidate_act_types),
                    "predicate_ids": list(group.predicate_ids),
                    "outcome_ids": list(group.outcome_ids),
                },
            )

    def _add_referents(self, graph: UOLGraph, referents: Iterable[ReferentAtom]) -> None:
        for ref in referents:
            kind = "self" if ref.entity_type == "self" else "entity"
            atom = graph.add_atom(
                kind,
                ref.entity_id or ref.surface or ref.role,
                surface=ref.surface,
                group_id=ref.group_id,
                span_id=ref.span_id,
                confidence=ref.confidence,
                source=ref.source,
                features={
                    "entity_type": ref.entity_type,
                    "role": ref.role,
                    "known": ref.known,
                },
                evidence=self._evidence(ref.evidence),
            )
            role_atom = graph.add_atom(
                "relation",
                f"role:{ref.role or 'topic'}",
                surface=ref.role or "topic",
                group_id=ref.group_id,
                span_id=ref.span_id,
                confidence=ref.confidence,
                source="role_binding",
                features={"role": ref.role or "topic"},
            )
            graph.add_edge(
                "has_role",
                atom.id,
                role_atom.id,
                group_id=ref.group_id,
                confidence=ref.confidence,
                features={"role": ref.role or "topic"},
            )

    def _add_actions(
        self,
        graph: UOLGraph,
        actions: Iterable[ActionAtom],
        groups: Iterable[MeaningGroup],
    ) -> None:
        group_index = {group.id: group for group in groups}
        for action in actions:
            action_key = action.action_key or action.surface or "action"
            action_atom = graph.add_atom(
                "action",
                action_key,
                surface=action.surface,
                group_id=action.group_id,
                span_id=action.span_id,
                confidence=action.confidence,
                source=action.source,
                features={
                    "modality": action.modality,
                    "polarity": action.polarity,
                    "actor_role": action.actor_role,
                    "object_role": action.object_role,
                    "target_role": action.target_role,
                    "place_role": action.place_role,
                },
                evidence=self._evidence(action.evidence),
            )
            process_atom = graph.add_atom(
                "process",
                action_key,
                surface=action.surface,
                group_id=action.group_id,
                span_id=action.span_id,
                confidence=max(0.45, action.confidence - 0.05),
                source=action.source,
                features={"derived_from": "action_atom"},
                evidence=self._evidence(action.evidence),
            )
            graph.add_edge("same_as", action_atom.id, process_atom.id, group_id=action.group_id, confidence=0.7)
            self._connect_action_roles(graph, action_atom, action, group_index.get(action.group_id))

    def _connect_action_roles(
        self,
        graph: UOLGraph,
        action_atom: UOLAtom,
        action: ActionAtom,
        group: MeaningGroup | None,
    ) -> None:
        for role_name in ("actor", "object", "target", "place"):
            role_value = getattr(action, f"{role_name}_role", None)
            if not role_value:
                continue
            target = self._resolve_role_atom(graph, role_value, action.group_id, group)
            graph.add_edge(
                "has_role",
                action_atom.id,
                target.id,
                group_id=action.group_id,
                confidence=action.confidence,
                features={"role": role_name, "role_value": role_value},
            )

    def _add_states(self, graph: UOLGraph, states: Iterable[StateAtom]) -> None:
        for state in states:
            atom = graph.add_atom(
                "state",
                state.state_key or state.surface or state.dimension,
                surface=state.surface,
                group_id=state.group_id,
                span_id=state.span_id,
                value=state.value,
                confidence=state.confidence,
                source=state.source,
                features={
                    "holder_role": state.holder_role,
                    "dimension": state.dimension,
                    "polarity": state.polarity,
                    "intensity": state.intensity,
                },
                evidence=self._evidence(state.evidence),
            )
            holder = self._resolve_role_atom(graph, state.holder_role, state.group_id, None)
            graph.add_edge(
                "has_role",
                atom.id,
                holder.id,
                group_id=state.group_id,
                confidence=state.confidence,
                features={"role": "holder", "role_value": state.holder_role},
            )

    def _add_relations(self, graph: UOLGraph, relations: Iterable[RelationAtom]) -> None:
        for relation in relations:
            atom = graph.add_atom(
                "relation",
                relation.relation_key,
                surface=relation.surface or relation.relation_key,
                group_id=relation.group_id,
                span_id=relation.span_id,
                confidence=relation.confidence,
                source=relation.source,
                features={"source_role": relation.source_role, "target_role": relation.target_role},
                evidence=self._evidence(relation.evidence),
            )
            source = self._resolve_role_atom(graph, relation.source_role, relation.group_id, None) if relation.source_role else None
            target = self._resolve_role_atom(graph, relation.target_role, relation.group_id, None) if relation.target_role else None
            if source is not None:
                graph.add_edge("has_role", atom.id, source.id, group_id=relation.group_id, confidence=relation.confidence, features={"role": "source"})
            if target is not None:
                graph.add_edge("has_role", atom.id, target.id, group_id=relation.group_id, confidence=relation.confidence, features={"role": "target"})
            self._typed_relation_edge(graph, relation, atom, source, target)

    def _typed_relation_edge(
        self,
        graph: UOLGraph,
        relation: RelationAtom,
        relation_atom: UOLAtom,
        source: UOLAtom | None,
        target: UOLAtom | None,
    ) -> None:
        edge_type = {
            "same_as": "same_as",
            "is_a": "is_a",
            "type_of": "is_a",
            "kind_of": "is_a",
            "part_of": "part_of",
            "used_for": "used_for",
            "has_property": "has_property",
            "causes": "causes",
            "enables": "enables",
            "prevents": "prevents",
            "before": "before",
            "after": "after",
        }.get(relation.relation_key)
        if edge_type and source is not None and target is not None:
            graph.add_edge(
                edge_type,
                source.id,
                target.id,
                group_id=relation.group_id,
                confidence=relation.confidence,
                features={"relation_atom_id": relation_atom.id},
            )

    def _add_needs(self, graph: UOLGraph, needs: Iterable[NeedAtom]) -> None:
        for need in needs:
            atom = graph.add_atom(
                "need",
                need.need_key,
                surface=need.need_key,
                group_id=need.group_id,
                span_id=need.span_id,
                confidence=need.confidence,
                source=need.source,
                features={"holder_role": need.holder_role, "intensity": need.intensity},
                evidence=self._evidence(need.evidence),
            )
            holder = self._resolve_role_atom(graph, need.holder_role, need.group_id, None)
            graph.add_edge("has_role", atom.id, holder.id, group_id=need.group_id, confidence=need.confidence, features={"role": "holder"})

    def _add_times(self, graph: UOLGraph, times: Iterable[TimeAtom]) -> None:
        for item in times:
            graph.add_atom(
                "time",
                item.time_key or item.surface,
                surface=item.surface,
                group_id=item.group_id,
                span_id=item.span_id,
                value=item.value or None,
                confidence=item.confidence,
                source=item.source,
                features={"relation": item.relation},
                evidence=self._evidence(item.evidence),
            )

    def _add_places(self, graph: UOLGraph, places: Iterable[PlaceAtom]) -> None:
        for item in places:
            graph.add_atom(
                "place",
                item.place_key or item.surface,
                surface=item.surface,
                group_id=item.group_id,
                span_id=item.span_id,
                confidence=item.confidence,
                source=item.source,
                features={"relation": item.relation},
                evidence=self._evidence(item.evidence),
            )

    def _add_modalities(self, graph: UOLGraph, modalities: Iterable[ModalityAtom]) -> None:
        for modality in modalities:
            atom = graph.add_atom(
                "modality",
                modality.modality_key,
                surface=modality.surface,
                group_id=modality.group_id,
                span_id=modality.span_id,
                confidence=modality.confidence,
                source=modality.source,
                features={"scope": modality.scope, "polarity": modality.polarity},
                evidence=self._evidence(modality.evidence),
            )
            for target in self._group_targets(graph, modality.group_id, {"action", "process", "intent", "state"}):
                graph.add_edge(
                    "modifies",
                    atom.id,
                    target.id,
                    group_id=modality.group_id,
                    confidence=modality.confidence,
                    features={"scope": modality.scope},
                )

    def _add_evidence(self, graph: UOLGraph, evidence_atoms: Iterable[EvidenceAtom]) -> None:
        for evidence in evidence_atoms:
            atom = graph.add_atom(
                "evidence",
                evidence.evidence_key,
                surface=evidence.surface,
                group_id=evidence.group_id,
                span_id=evidence.span_id,
                confidence=evidence.confidence,
                source="evidence_atom",
                features={"source_role": evidence.source_role, "freshness": evidence.freshness},
            )
            source = graph.add_atom(
                "source",
                evidence.source_role or "unknown_source",
                surface=evidence.source_role or "unknown_source",
                group_id=evidence.group_id,
                span_id=evidence.span_id,
                confidence=evidence.confidence,
                source="evidence_atom",
                features={"freshness": evidence.freshness},
            )
            graph.add_edge("refers_to", atom.id, source.id, group_id=evidence.group_id, confidence=evidence.confidence)

    def _add_surface_teaching_relations(self, graph: UOLGraph, groups: Iterable[MeaningGroup]) -> None:
        for group in groups:
            if group.group_type != "teaching" and not any(intent.intent_key == "teaching" for intent in group.intents):
                continue
            parsed = self._parse_surface_relation(group.tokens)
            if parsed is None:
                continue
            subject_text, relation_key, object_text = parsed
            object_head, domain_text = self._split_domain_phrase(object_text)
            subject = graph.add_atom(
                "entity",
                subject_text,
                surface=subject_text,
                group_id=group.id,
                confidence=min(0.72, group.confidence + 0.1),
                source="surface_teaching_relation",
                features={"role": "subject", "from_tokens": True},
            )
            obj = graph.add_atom(
                "entity",
                object_head,
                surface=object_head,
                group_id=group.id,
                confidence=min(0.72, group.confidence + 0.1),
                source="surface_teaching_relation",
                features={"role": "object", "from_tokens": True},
            )
            relation = graph.add_atom(
                "relation",
                relation_key,
                surface=" ".join(group.tokens),
                group_id=group.id,
                confidence=min(0.74, group.confidence + 0.12),
                source="surface_teaching_relation",
                features={"subject": subject_text, "object": object_head},
            )
            graph.add_edge("has_role", relation.id, subject.id, group_id=group.id, confidence=relation.confidence, features={"role": "source"})
            graph.add_edge("has_role", relation.id, obj.id, group_id=group.id, confidence=relation.confidence, features={"role": "target"})
            graph.add_edge(relation_key, subject.id, obj.id, group_id=group.id, confidence=relation.confidence, features={"relation_atom_id": relation.id})
            if domain_text:
                domain = graph.add_atom(
                    "entity",
                    domain_text,
                    surface=domain_text,
                    group_id=group.id,
                    confidence=min(0.68, group.confidence + 0.08),
                    source="surface_teaching_relation",
                    features={"role": "domain", "from_domain_phrase": object_text},
                )
                domain_relation = graph.add_atom(
                    "relation",
                    "domain",
                    surface="of",
                    group_id=group.id,
                    confidence=min(0.66, group.confidence + 0.06),
                    source="surface_teaching_relation",
                    features={"source": object_head, "target": domain_text},
                )
                graph.add_edge("has_role", obj.id, domain.id, group_id=group.id, confidence=domain.confidence, features={"role": "domain", "relation_atom_id": domain_relation.id})
                graph.add_edge("has_role", domain_relation.id, obj.id, group_id=group.id, confidence=domain_relation.confidence, features={"role": "source"})
                graph.add_edge("has_role", domain_relation.id, domain.id, group_id=group.id, confidence=domain_relation.confidence, features={"role": "target"})
            source = self._group_source(graph, group.id)
            graph.add_edge("teaches", source.id, relation.id, group_id=group.id, confidence=relation.confidence)

    def _parse_surface_relation(self, tokens: list[str]) -> tuple[str, str, str] | None:
        if not tokens:
            return None
        cues = ("means", "mean", "equals", "called", "refers", "is", "are")
        for cue in cues:
            if cue not in tokens:
                continue
            index = tokens.index(cue)
            left = self._clean_relation_side(tokens[:index])
            right = self._clean_relation_side(tokens[index + 1:])
            if not left or not right:
                return None
            relation_key = "same_as" if cue in {"means", "mean", "equals", "called", "refers"} else "is_a"
            return left, relation_key, right
        return None

    @staticmethod
    def _clean_relation_side(tokens: list[str]) -> str:
        stop = {"a", "an", "the", "to", "as"}
        clean = [token for token in tokens if token not in stop]
        return " ".join(clean).strip()

    @staticmethod
    def _split_domain_phrase(surface: str) -> tuple[str, str]:
        if " of " not in surface:
            return surface, ""
        head, domain = surface.split(" of ", 1)
        return head.strip() or surface, domain.strip()

    def _add_intents(
        self,
        graph: UOLGraph,
        intents: Iterable[IntentAtom],
        groups: Iterable[MeaningGroup],
    ) -> None:
        group_index = {group.id: group for group in groups}
        for intent in intents:
            atom = graph.add_atom(
                "intent",
                intent.intent_key,
                surface=intent.surface,
                group_id=intent.group_id,
                span_id=intent.span_id,
                confidence=intent.confidence,
                source=intent.source,
                features={
                    "target_role": intent.target_role,
                    "is_question": intent.is_question,
                    "is_command": intent.is_command,
                    "polarity": intent.polarity,
                },
                evidence=self._evidence(intent.evidence),
            )
            actor = self._resolve_role_atom(graph, "user", intent.group_id, group_index.get(intent.group_id))
            graph.add_edge("has_role", atom.id, actor.id, group_id=intent.group_id, confidence=intent.confidence, features={"role": "actor"})
            if intent.target_role:
                target = self._resolve_role_atom(graph, intent.target_role, intent.group_id, group_index.get(intent.group_id))
                graph.add_edge("has_role", atom.id, target.id, group_id=intent.group_id, confidence=intent.confidence, features={"role": "target"})
            if intent.is_question or intent.intent_key.endswith("query"):
                self._connect_asks_about(graph, atom, intent)
            if intent.intent_key == "teaching":
                self._connect_teaches(graph, atom, intent)

    def _connect_asks_about(self, graph: UOLGraph, intent_atom: UOLAtom, intent: IntentAtom) -> None:
        targets = self._group_targets(graph, intent.group_id, {"entity", "self", "time", "place", "state", "relation", "evidence"})
        if not targets:
            targets = [graph.add_atom(
                "entity",
                "world",
                surface="world",
                group_id=intent.group_id,
                span_id=intent.span_id,
                confidence=0.55,
                source="inferred_world_target",
                features={"entity_type": "world"},
            )]
        for target in targets:
            if target.id == intent_atom.id:
                continue
            graph.add_edge("asks_about", intent_atom.id, target.id, group_id=intent.group_id, confidence=intent.confidence)

    def _connect_teaches(self, graph: UOLGraph, intent_atom: UOLAtom, intent: IntentAtom) -> None:
        source = self._group_source(graph, intent.group_id)
        targets = self._group_targets(graph, intent.group_id, {"relation", "state", "entity", "process", "action"})
        for target in targets:
            if target.id == intent_atom.id:
                continue
            graph.add_edge("teaches", source.id, target.id, group_id=intent.group_id, confidence=intent.confidence)

    def _add_predicates(self, graph: UOLGraph, predicates: Iterable[PredicatePhrase]) -> None:
        for predicate in predicates:
            predicate_atom = graph.add_atom(
                "process" if not predicate.predicate_key.startswith("intent:") else "intent",
                predicate.predicate_key.replace("intent:", ""),
                surface=predicate.predicate_surface or predicate.surface,
                group_id=predicate.group_id,
                confidence=predicate.confidence,
                source="predicate_phrase",
                features={
                    "predicate_id": predicate.id,
                    "modality": predicate.modality,
                    "polarity": predicate.polarity,
                    "actor_role": predicate.actor_role,
                    "object_role": predicate.object_role,
                    "target_role": predicate.target_role,
                    "place_role": predicate.place_role,
                },
                evidence=self._evidence(predicate.evidence),
            )
            for role_name in ("actor", "object", "target", "place"):
                role_value = getattr(predicate, f"{role_name}_role", None)
                if not role_value:
                    continue
                target = self._resolve_role_atom(graph, role_value, predicate.group_id, None)
                graph.add_edge(
                    "has_role",
                    predicate_atom.id,
                    target.id,
                    group_id=predicate.group_id,
                    predicate_id=predicate.id,
                    confidence=predicate.confidence,
                    features={"role": role_name, "role_value": role_value},
                )

    def _add_outcomes(self, graph: UOLGraph, outcomes: Iterable[MeaningAtomOutcome]) -> None:
        for outcome in outcomes:
            predicate = self._predicate_atom_for_outcome(graph, outcome)
            if predicate is None:
                continue
            if outcome.expected_change == "fresh_evidence_required":
                evidence = graph.add_atom(
                    "evidence",
                    "fresh_external_evidence_required",
                    surface=outcome.expected_change,
                    group_id=outcome.group_id,
                    confidence=outcome.confidence,
                    source="meaning_outcome",
                    features={"freshness": "fresh"},
                    evidence=self._evidence(outcome.evidence),
                )
                graph.add_edge("asks_about", predicate.id, evidence.id, group_id=outcome.group_id, predicate_id=outcome.predicate_id, confidence=outcome.confidence)
                continue
            if outcome.expected_change == "candidate_memory_update":
                memory = graph.add_atom(
                    "entity",
                    "memory",
                    surface="memory",
                    group_id=outcome.group_id,
                    confidence=outcome.confidence,
                    source="meaning_outcome",
                    features={"entity_type": "memory"},
                )
                graph.add_edge("enables", predicate.id, memory.id, group_id=outcome.group_id, predicate_id=outcome.predicate_id, confidence=outcome.confidence)
                continue
            if outcome.expected_change:
                state = graph.add_atom(
                    "state",
                    outcome.expected_change,
                    surface=outcome.expected_change,
                    group_id=outcome.group_id,
                    confidence=outcome.confidence,
                    source="meaning_outcome",
                    features={
                        "atom_kind": outcome.atom_kind,
                        "atom_key": outcome.atom_key,
                        "affected_role": outcome.affected_role,
                        "valence": outcome.valence,
                    },
                    evidence=self._evidence(outcome.evidence),
                )
                graph.add_edge("causes", predicate.id, state.id, group_id=outcome.group_id, predicate_id=outcome.predicate_id, confidence=outcome.confidence)

    def _add_group_temporal_place_edges(self, graph: UOLGraph, groups: Iterable[MeaningGroup]) -> None:
        for group in groups:
            times = graph.atoms_by_kind("time", group.id)
            places = graph.atoms_by_kind("place", group.id)
            targets = self._group_targets(graph, group.id, {"intent", "action", "process", "state", "relation"})
            for time in times:
                edge_type = "before" if time.features.get("relation") == "past" else "after" if time.features.get("relation") == "future" else "modifies"
                for target in targets:
                    graph.add_edge(edge_type, time.id, target.id, group_id=group.id, confidence=min(time.confidence, target.confidence))
            for place in places:
                for target in targets:
                    graph.add_edge("modifies", place.id, target.id, group_id=group.id, confidence=min(place.confidence, target.confidence))

    def _add_candidate_sets(self, graph: UOLGraph, packet: MeaningPerceptPacket) -> None:
        for hypothesis in getattr(packet, "meaning_hypotheses", []):
            candidate_atom_ids: list[str] = []
            selected_atom_id = ""
            selected_candidate_ids = list(hypothesis.selected_candidate_ids)
            for candidate in hypothesis.candidates:
                atom_kind = candidate.atom_kind or "entity"
                atom_key = candidate.atom_key or candidate.surface or candidate.interpretation_kind
                atom_id = self._candidate_atom_id(graph.id, hypothesis.id, candidate.id, atom_kind, atom_key)
                atom = graph.add_atom(
                    atom_kind,
                    atom_key,
                    surface=candidate.surface,
                    group_id=candidate.group_id,
                    span_id=candidate.span_id,
                    confidence=candidate.confidence,
                    source="meaning_hypothesis",
                    features={
                        "hypothesis_id": hypothesis.id,
                        "candidate_interpretation_id": candidate.id,
                        "interpretation_kind": candidate.interpretation_kind,
                        "candidate_act_type": candidate.candidate_act_type,
                        "role": candidate.role,
                        "selected": candidate.selected,
                        **dict(candidate.features),
                    },
                    evidence=self._evidence(candidate.evidence),
                    atom_id=atom_id,
                )
                candidate_atom_ids.append(atom.id)
                if candidate.selected and not selected_atom_id:
                    selected_atom_id = atom.id

            graph.add_candidate_set(CandidateSet(
                id=f"cand_{len(graph.candidate_sets)}",
                target_span_id=hypothesis.span_id,
                target_surface=hypothesis.surface,
                group_id=hypothesis.group_id,
                hypothesis_id=hypothesis.id,
                candidate_atom_ids=candidate_atom_ids,
                candidate_interpretation_ids=[candidate.id for candidate in hypothesis.candidates],
                candidate_subgraphs={
                    candidate.id: {
                        "atom_ids": [
                            atom_id for atom_id in candidate_atom_ids
                            if graph.atoms.get(atom_id) is not None
                            and graph.atoms[atom_id].features.get("candidate_interpretation_id") == candidate.id
                        ],
                        "edge_ids": [],
                    }
                    for candidate in hypothesis.candidates
                },
                selected_atom_id=selected_atom_id,
                selected_candidate_ids=selected_candidate_ids,
                reason=hypothesis.reason,
                confidence=hypothesis.confidence,
            ))

        for item in packet.unknown_lexemes:
            surface = str(item.get("surface", "") or "").strip()
            if not surface:
                continue
            if any(candidate_set.target_surface == surface for candidate_set in graph.candidate_sets):
                continue
            group = self._group_for_surface(packet.meaning_groups, surface)
            group_id = group.id if group is not None else ""
            atom = graph.add_atom(
                "entity",
                surface,
                surface=surface,
                group_id=group_id,
                confidence=float(item.get("confidence", 0.45) or 0.45),
                source="unknown_lexeme",
                features={
                    "candidate_role": item.get("role", "unknown"),
                    "position": item.get("position", -1),
                    "concept_state": "candidate_atom",
                },
            )
            graph.add_candidate_set(CandidateSet(
                id=f"cand_{len(graph.candidate_sets)}",
                target_span_id=atom.span_id,
                target_surface=surface,
                group_id=group_id,
                candidate_atom_ids=[atom.id],
                selected_atom_id=atom.id,
                reason="unknown_surface_candidate",
                confidence=atom.confidence,
            ))

    def _add_construction_matches(self, graph: UOLGraph, packet: MeaningPerceptPacket) -> None:
        if self._construction_lattice is not None and hasattr(self._construction_lattice, "match"):
            for match in self._construction_lattice.match(packet, graph) or []:
                graph.add_construction_match(match)
            return
        for group in packet.meaning_groups:
            key = self._construction_key_for_group(group)
            if not key:
                continue
            hints = list(group.candidate_act_types)
            expected_ports = self._expected_ports_for_construction(key)
            graph.add_construction_match(ConstructionMatch(
                id=f"cx_{group.id}_{len(graph.construction_matches)}",
                construction_key=key,
                group_id=group.id,
                matched_span_ids=[self._span_id_for_group(packet, group)],
                expected_ports=expected_ports,
                graph_patch_templates=[{
                    "target": "construction_lattice",
                    "operation": "strengthen_construction",
                    "construction_key": key,
                }],
                pragmatic_hints=hints,
                confidence=max(0.45, group.confidence),
            ))

    def _resolve_concepts(self, graph: UOLGraph) -> None:
        for atom in graph.atoms.values():
            if self._concept_lattice is not None and hasattr(self._concept_lattice, "resolve"):
                resolved = self._concept_lattice.resolve(atom, graph)
                if resolved is not None:
                    graph.add_concept_resolution(resolved)
                    continue
            if atom.kind in {"source", "permission", "evidence"}:
                state = "operational_context"
                confidence = max(0.55, atom.confidence)
                reason = f"{atom.kind}_context_atom"
            elif atom.source in {"lexeme_memory", "context", "source_atom"} or atom.features.get("known"):
                state = "exact_alias"
                confidence = max(0.65, atom.confidence)
                reason = "known_runtime_alias"
            elif atom.source in {"unknown_lexeme", "role_placeholder"} or atom.features.get("concept_state") == "candidate_atom":
                state = "new_candidate"
                confidence = min(0.6, atom.confidence)
                reason = "surface_candidate"
            else:
                state = "typed_candidate"
                confidence = max(0.45, atom.confidence)
                reason = "typed_by_uol_kind"
            graph.add_concept_resolution(ConceptResolution(
                atom_id=atom.id,
                concept_id=f"concept:{atom.key}",
                state=state,
                confidence=confidence,
                evidence_refs=self._evidence_refs(atom.evidence),
                reason=reason,
            ))

    def _resolve_ports(self, graph: UOLGraph) -> None:
        if self._port_resolver is not None and hasattr(self._port_resolver, "resolve_graph"):
            for binding in self._port_resolver.resolve_graph(graph) or []:
                graph.add_port_binding(binding)
            return
        for edge in graph.edges_by_type("has_role"):
            owner = graph.atoms.get(edge.source_id)
            filler = graph.atoms.get(edge.target_id)
            if owner is None or filler is None:
                continue
            port_key = str(edge.features.get("role") or edge.features.get("role_value") or "role")
            if port_key == "role" and filler.kind == "relation" and filler.features.get("role"):
                port_key = str(filler.features["role"])
            score_parts = self._port_score_parts(owner, filler, edge)
            score = max(0.0, min(1.0, sum(score_parts.values())))
            status = "bound" if score >= 0.55 else "placeholder"
            graph.add_port_binding(PortBinding(
                owner_atom_id=owner.id,
                owner_concept_id=f"concept:{owner.key}",
                port_id=f"port:{owner.key}:{port_key}",
                port_key=port_key,
                filler_atom_id=filler.id if status == "bound" else "",
                required=False,
                status=status,
                score=score,
                score_parts=score_parts,
                evidence_refs=self._evidence_refs([*owner.evidence, *edge.evidence, *filler.evidence]),
                source_edge_id=edge.id,
            ))

    def _predict_affordances(self, graph: UOLGraph) -> None:
        if self._affordance_lattice is not None and hasattr(self._affordance_lattice, "predict"):
            for prediction in self._affordance_lattice.predict(graph) or []:
                graph.add_affordance_prediction(prediction)
            return
        for atom in graph.atoms.values():
            if atom.kind == "evidence" and atom.features.get("freshness") == "fresh":
                graph.add_affordance_prediction(AffordancePrediction(
                    id=f"aff_{len(graph.affordance_predictions)}",
                    affordance_key="fresh_source_requirement",
                    trigger_atom_ids=[atom.id],
                    predicted_patch_template={
                        "target": "source_policy",
                        "operation": "require_fresh_source",
                        "evidence_atom_id": atom.id,
                    },
                    effect_type="action_enablement",
                    confidence=max(0.65, atom.confidence),
                    evidence_refs=self._evidence_refs(atom.evidence),
                    reason="fresh_evidence_atom",
                ))
            if atom.kind == "intent" and atom.key == "repair":
                graph.add_affordance_prediction(AffordancePrediction(
                    id=f"aff_{len(graph.affordance_predictions)}",
                    affordance_key="clarity_need",
                    trigger_atom_ids=[atom.id],
                    predicted_patch_template={
                        "target": "episodic_trace",
                        "operation": "activate_need",
                        "need_key": "clarity",
                    },
                    effect_type="need_activation",
                    confidence=max(0.6, atom.confidence),
                    evidence_refs=self._evidence_refs(atom.evidence),
                    reason="repair_intent",
                ))
            if atom.kind == "state" and self._is_cold_state_candidate(atom):
                bindings = graph.bindings_for_owner(atom.id)
                graph.add_affordance_prediction(AffordancePrediction(
                    id=f"aff_{len(graph.affordance_predictions)}",
                    affordance_key="cold_context_comfort_relevance",
                    trigger_atom_ids=[atom.id],
                    required_binding_ids=[binding.source_edge_id for binding in bindings if binding.source_edge_id],
                    predicted_patch_template={
                        "target": "causal_affordance",
                        "operation": "predict_possible_need",
                        "need_key": "comfort_or_warmth_may_be_relevant",
                    },
                    effect_type="need_activation",
                    confidence=min(0.78, max(0.5, atom.confidence)),
                    evidence_refs=self._evidence_refs(atom.evidence),
                    reason="seed_affordance_candidate_not_static_port",
                ))

    def _extract_graph_patches(self, graph: UOLGraph) -> None:
        for group in graph.groups:
            teaching_edges = [
                edge for edge in graph.group_edges(group.id)
                if edge.edge_type in {"is_a", "same_as", "has_property", "used_for", "part_of"}
            ]
            if teaching_edges and graph.has_edge("teaches", source_kind="source", group_id=group.id):
                operations = []
                for edge in teaching_edges:
                    source = graph.atoms.get(edge.source_id)
                    target = graph.atoms.get(edge.target_id)
                    if source is None or target is None:
                        continue
                    operations.append(PatchOperation(
                        operation="upsert_relation_candidate",
                        target_id=f"relation:{edge.edge_type}:{source.key}:{target.key}",
                        fields={
                            "relation": edge.edge_type,
                            "source_concept_key": source.key,
                            "target_concept_key": target.key,
                            "group_id": group.id,
                        },
                        confidence=edge.confidence,
                        reason="user_teaching_graph_relation",
                    ))
                if operations:
                    graph.add_patch_candidate(GraphPatch(
                        source_graph_id=graph.id,
                        target="concept_lattice",
                        operations=operations,
                        source_refs=self._source_refs_for_group(graph, group.id),
                        permission_refs=self._permission_refs_for_group(graph, group.id),
                        confidence=max(operation.confidence for operation in operations),
                        reason="teaching_group_relation_candidates",
                    ))

        concept_operations = []
        for resolution in graph.concept_resolutions:
            if resolution.state != "new_candidate":
                continue
            atom = graph.atoms.get(resolution.atom_id)
            if atom is None:
                continue
            concept_operations.append(PatchOperation(
                operation="upsert_concept_candidate",
                target_id=resolution.concept_id,
                fields={
                    "key": atom.key,
                    "atom_kind": atom.kind,
                    "surface": atom.surface,
                    "state": "candidate_atom",
                },
                confidence=resolution.confidence,
                reason=resolution.reason,
            ))
        if concept_operations:
            graph.add_patch_candidate(GraphPatch(
                source_graph_id=graph.id,
                target="concept_lattice",
                operations=concept_operations,
                source_refs=self._source_refs_for_group(graph, ""),
                permission_refs=self._permission_refs_for_group(graph, ""),
                confidence=max(operation.confidence for operation in concept_operations),
                reason="new_surface_concept_candidates",
            ))

        if graph.port_bindings:
            operations = [
                PatchOperation(
                    operation="observe_port_binding",
                    target_id=binding.port_id,
                    fields={
                        "owner_concept_id": binding.owner_concept_id,
                        "port_key": binding.port_key,
                        "filler_atom_id": binding.filler_atom_id,
                        "status": binding.status,
                    },
                    confidence=binding.score,
                    reason="runtime_port_binding_observation",
                )
                for binding in graph.port_bindings
                if binding.score >= 0.55
            ]
            if operations:
                graph.add_patch_candidate(GraphPatch(
                    source_graph_id=graph.id,
                    target="concept_lattice",
                    operations=operations,
                    source_refs=self._source_refs_for_group(graph, ""),
                    permission_refs=self._permission_refs_for_group(graph, ""),
                    confidence=max(operation.confidence for operation in operations),
                    reason="port_binding_observations",
                ))

        if graph.construction_matches:
            graph.add_patch_candidate(GraphPatch(
                source_graph_id=graph.id,
                target="construction_lattice",
                operations=[
                    PatchOperation(
                        operation="observe_construction_match",
                        target_id=f"construction:{match.construction_key}",
                        fields=match.to_dict(),
                        confidence=match.confidence,
                        reason="runtime_construction_match",
                    )
                    for match in graph.construction_matches
                ],
                source_refs=self._source_refs_for_group(graph, ""),
                permission_refs=self._permission_refs_for_group(graph, ""),
                confidence=max(match.confidence for match in graph.construction_matches),
                reason="construction_observations",
            ))

    def _construction_key_for_group(self, group: MeaningGroup) -> str:
        if group.group_type == "teaching":
            return "definition_or_claim_teaching"
        if group.group_type == "question":
            return "question"
        if group.group_type == "command":
            return "command_request"
        if group.group_type == "state_report":
            return "state_report"
        if group.group_type == "repair":
            return "repair"
        if group.group_type == "social":
            return "social_turn"
        return ""

    def _expected_ports_for_construction(self, construction_key: str) -> list[str]:
        return {
            "definition_or_claim_teaching": ["source", "target", "relation"],
            "question": ["speaker", "topic", "evidence"],
            "command_request": ["actor", "action", "target"],
            "state_report": ["holder", "state", "time", "place"],
            "repair": ["speaker", "repair_target"],
            "social_turn": ["speaker", "listener"],
        }.get(construction_key, [])

    def _port_score_parts(self, owner: UOLAtom, filler: UOLAtom, edge: UOLEdge) -> dict[str, float]:
        role_present = 0.25 if edge.features.get("role") or edge.features.get("role_value") else 0.0
        kind_compatible = 0.2 if filler.kind in {"entity", "self", "place", "time", "state", "quality", "quantity", "relation"} else 0.05
        edge_support = 0.2 if edge.edge_type == "has_role" else 0.0
        source_support = 0.1 if owner.source != "role_placeholder" and filler.source != "role_placeholder" else 0.0
        confidence_support = min(owner.confidence, filler.confidence, edge.confidence) * 0.25
        return {
            "role_present": role_present,
            "kind_compatible": kind_compatible,
            "edge_support": edge_support,
            "source_support": source_support,
            "confidence_support": confidence_support,
        }

    def _is_cold_state_candidate(self, atom: UOLAtom) -> bool:
        if atom.kind != "state":
            return False
        key = atom.key.lower()
        surface = atom.surface.lower()
        return "cold" in {key, surface} or atom.features.get("dimension") == "temperature"

    @staticmethod
    def _evidence_refs(evidence: Iterable[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        for item in evidence:
            span_id = str(item.get("span_id", "") or "")
            group_id = str(item.get("group_id", "") or "")
            source = str(item.get("source", "") or "")
            ref = ":".join(part for part in (source, group_id, span_id) if part)
            if ref and ref not in refs:
                refs.append(ref)
        return refs

    def _source_refs_for_group(self, graph: UOLGraph, group_id: str) -> list[str]:
        sources = graph.atoms_by_kind("source", group_id) if group_id else graph.atoms_by_kind("source")
        return [atom.id for atom in sources]

    def _permission_refs_for_group(self, graph: UOLGraph, group_id: str) -> list[str]:
        permissions = graph.atoms_by_kind("permission", group_id) if group_id else graph.atoms_by_kind("permission")
        return [atom.id for atom in permissions]

    @staticmethod
    def _group_for_surface(groups: Iterable[MeaningGroup], surface: str) -> MeaningGroup | None:
        normalized = surface.lower().strip()
        if not normalized:
            return None
        for group in groups:
            if normalized in group.surface.lower():
                return group
        return None

    @staticmethod
    def _candidate_atom_id(
        graph_id: str,
        hypothesis_id: str,
        candidate_id: str,
        atom_kind: str,
        atom_key: str,
    ) -> str:
        stem = f"{graph_id}:{hypothesis_id}:{candidate_id}:{atom_kind}:{atom_key}"
        return "uolcand_" + uuid.uuid5(uuid.NAMESPACE_URL, stem).hex[:16]

    @staticmethod
    def _span_id_for_group(packet: MeaningPerceptPacket, group: MeaningGroup) -> str:
        for span in packet.spans:
            if span.span_type == "clause" and span.start_token <= group.start_token and span.end_token >= group.end_token:
                return span.id
        return f"group_span:{group.id}"

    def _source_atom(self, graph: UOLGraph, source: SourceAtom) -> UOLAtom:
        return graph.add_atom(
            "source",
            source.source_role or "unknown_source",
            surface=source.surface or source.source_role,
            group_id=source.group_id,
            span_id=source.span_id,
            confidence=source.confidence,
            source="source_atom",
            features={
                "source_role": source.source_role,
                "reliability": source.reliability,
                "permission_scope": source.permission_scope,
            },
        )

    def _permission_atom(self, graph: UOLGraph, permission: PermissionAtom) -> UOLAtom:
        return graph.add_atom(
            "permission",
            permission.permission_key or permission.scope or "conversation",
            surface=permission.scope or permission.permission_key,
            group_id=permission.group_id,
            span_id=permission.span_id,
            confidence=permission.confidence,
            source="permission_atom",
            features={
                "scope": permission.scope,
                "holder_role": permission.holder_role,
                "target_role": permission.target_role,
            },
        )

    def _self_atom(self, graph: UOLGraph, item: SelfAtom) -> UOLAtom:
        return graph.add_atom(
            "self",
            item.self_key or "self",
            surface=item.surface or "self",
            group_id=item.group_id,
            span_id=item.span_id,
            confidence=item.confidence,
            source="self_atom",
            features={"role": item.role},
        )

    def _resolve_role_atom(
        self,
        graph: UOLGraph,
        role_value: str,
        group_id: str,
        group: MeaningGroup | None,
    ) -> UOLAtom:
        role_value = role_value or "unknown"
        if role_value in {"self", "listener"}:
            return graph.add_atom("self", "self", surface="self", group_id=group_id, confidence=0.8, source="role_resolution")
        if role_value in {"user", "speaker", "actor"}:
            return graph.add_atom("entity", "user", surface="user", group_id=group_id, confidence=0.8, source="role_resolution", features={"entity_type": "user"})
        if role_value in {"world", "external_world"}:
            return graph.add_atom("entity", "world", surface="world", group_id=group_id, confidence=0.65, source="role_resolution", features={"entity_type": "world"})
        if role_value in {"memory"}:
            return graph.add_atom("entity", "memory", surface="memory", group_id=group_id, confidence=0.65, source="role_resolution", features={"entity_type": "memory"})
        if group is not None:
            for ref in group.referents:
                if ref.role == role_value or ref.entity_id == role_value or ref.surface == role_value:
                    return graph.add_atom(
                        "self" if ref.entity_type == "self" else "entity",
                        ref.entity_id or ref.surface or role_value,
                        surface=ref.surface,
                        group_id=group_id,
                        span_id=ref.span_id,
                        confidence=ref.confidence,
                        source="role_resolution",
                        features={"entity_type": ref.entity_type, "role": ref.role},
                    )
        return graph.add_atom(
            "entity",
            role_value,
            surface=role_value,
            group_id=group_id,
            confidence=0.45,
            source="role_placeholder",
            features={"role_value": role_value},
        )

    def _group_targets(self, graph: UOLGraph, group_id: str, kinds: set[str]) -> list[UOLAtom]:
        return [
            atom for atom in graph.group_atoms(group_id)
            if atom.kind in kinds
        ]

    def _group_source(self, graph: UOLGraph, group_id: str) -> UOLAtom:
        sources = graph.atoms_by_kind("source", group_id)
        if sources:
            return sources[0]
        return graph.add_atom(
            "source",
            "user",
            surface="user",
            group_id=group_id,
            confidence=0.7,
            source="inferred_group_source",
            features={"source_role": "user", "reliability": "speaker_asserted"},
        )

    def _predicate_atom_for_outcome(self, graph: UOLGraph, outcome: MeaningAtomOutcome) -> UOLAtom | None:
        for atom in graph.group_atoms(outcome.group_id):
            if atom.features.get("predicate_id") == outcome.predicate_id:
                return atom
        candidates = [
            atom for atom in graph.group_atoms(outcome.group_id)
            if atom.key == outcome.atom_key or atom.key == outcome.atom_key.replace("intent:", "")
        ]
        if candidates:
            return candidates[0]
        return None

    @staticmethod
    def _evidence(values: Iterable[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for value in values:
            if hasattr(value, "__dict__"):
                result.append(dict(value.__dict__))
            elif isinstance(value, dict):
                result.append(dict(value))
        return result
