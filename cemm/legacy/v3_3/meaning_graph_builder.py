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

from ...types.meaning_percept import (
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
from ...learning.learning_types import StructuralObservation
from ...types.graph_patch import GraphPatch, PatchOperation
from ...types.uol_atom import UOLAtom, UOLEdge
from ...types.uol_graph import (
    AffordancePrediction,
    CandidateSet,
    ConceptResolution,
    ConstructionMatch,
    PortBinding,
    UOLGraph,
)
from .semantic_schema_kernel import SemanticSchemaKernel, get_kernel
from .proposition_semantics import can_materialize_domain_edge, is_role_placeholder, open_roles, proposition_mode
from .semantic_integrity import SemanticIntegrityValidator


class MeaningGraphBuilder:
    """Construct the canonical UOL graph for one meaning packet."""

    def __init__(
        self,
        concept_lattice: Any | None = None,
        port_resolver: Any | None = None,
        affordance_lattice: Any | None = None,
        construction_lattice: Any | None = None,
        schema_kernel: SemanticSchemaKernel | None = None,
        predicate_schema_store: Any | None = None,
    ) -> None:
        self._concept_lattice = concept_lattice
        self._port_resolver = port_resolver
        self._affordance_lattice = affordance_lattice
        self._construction_lattice = construction_lattice
        self._schema_kernel = schema_kernel or get_kernel()
        self._predicate_schema_store = predicate_schema_store

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
        all_actions = (packet.actions or []) + (getattr(packet, 'candidate_actions', None) or [])
        self._add_actions(graph, all_actions, packet.meaning_groups)
        self._add_emotional_evaluations(graph, packet)
        self._add_states(graph, packet.states)
        self._add_relations(graph, packet.relations)
        self._add_needs(graph, packet.needs)
        self._add_times(graph, packet.times)
        self._add_places(graph, packet.places)
        self._add_modalities(graph, packet.modalities)
        self._add_evidence(graph, packet.evidence)
        self._add_intents(graph, packet.intents, packet.meaning_groups)
        self._add_predicates(graph, packet.predicate_phrases)
        self._add_outcomes(graph, packet.atom_outcomes)
        self._add_group_temporal_place_edges(graph, packet.meaning_groups)
        self._add_discourse_edges(graph, packet)
        self._add_cross_group_anaphora(graph, packet)
        self._add_candidate_sets(graph, packet)
        self._add_construction_matches(graph, packet)
        self._resolve_concepts(graph)
        self._resolve_ports(graph)
        self._predict_affordances(graph)
        self._extract_graph_patches(graph)
        SemanticIntegrityValidator().validate_graph(graph)

        graph.trace.update({
            "atom_count": len(graph.atoms),
            "edge_count": len(graph.edges),
            "group_count": len(packet.meaning_groups),
            "candidate_set_count": len(graph.candidate_sets),
            "construction_match_count": len(graph.construction_matches),
            "concept_resolution_count": len(graph.concept_resolutions),
            "port_binding_count": len(graph.port_bindings),
            "affordance_prediction_count": len(graph.affordance_predictions),
            "graph_patch_candidate_count": len(graph.structural_observations),
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

    def _add_discourse_edges(self, graph: UOLGraph, packet: MeaningPerceptPacket) -> None:
        for group in packet.meaning_groups:
            if not group.parent_group_id or not group.relation_to_parent:
                continue
            parent_atoms = self._discourse_anchor_atoms(graph, group.parent_group_id)
            child_atoms = self._discourse_anchor_atoms(graph, group.id)
            if not parent_atoms or not child_atoms:
                continue
            edge_type = self._discourse_edge_type(group.relation_to_parent)
            for parent in parent_atoms:
                for child in child_atoms:
                    source_atom, target_atom = self._discourse_edge_direction(
                        edge_type, group.relation_to_parent, parent, child
                    )
                    graph.add_edge(
                        edge_type,
                        source_atom.id,
                        target_atom.id,
                        group_id=group.parent_group_id,
                        confidence=group.confidence,
                        features={
                            "discourse_relation": group.relation_to_parent,
                            "connective": group.connective_before,
                            "parent_group_id": group.parent_group_id,
                            "child_group_id": group.id,
                        },
                    )

    def _discourse_anchor_atoms(self, graph: UOLGraph, group_id: str) -> list[UOLAtom]:
        atoms = graph.group_atoms(group_id)
        preferred = [
            atom for atom in atoms
            if atom.kind in {"process", "action", "state", "relation"}
        ]
        return preferred or atoms

    @staticmethod
    def _discourse_edge_type(relation: str) -> str:
        return {
            "cause": "causes",
            "result": "causes",
            "condition": "enables",
            "negative_condition": "prevents",
            "temporal": "before",
            "sequence": "before",
            "concession": "evaluates",
            "contrast": "evaluates",
            "complement": "refers_to",
            "coordination": "modifies",
        }.get(relation, "modifies")

    @staticmethod
    def _discourse_edge_direction(
        edge_type: str,
        relation: str,
        parent: UOLAtom,
        child: UOLAtom,
    ) -> tuple[UOLAtom, UOLAtom]:
        if relation == "cause" and edge_type == "causes":
            return child, parent
        return parent, child

    def _add_cross_group_anaphora(self, graph: UOLGraph, packet: MeaningPerceptPacket) -> None:
        pronoun_atoms: list[UOLAtom] = []
        entity_atoms: list[UOLAtom] = []
        for atom in graph.atoms.values():
            if atom.kind == "entity":
                entity_type = atom.features.get("entity_type", "")
                if entity_type == "pronoun" or atom.key in ("i", "you", "he", "she", "it", "they", "we", "me", "him", "her", "them", "us"):
                    pronoun_atoms.append(atom)
                else:
                    entity_atoms.append(atom)
        for pronoun in pronoun_atoms:
            if not pronoun.group_id:
                continue
            for entity in entity_atoms:
                if entity.group_id == pronoun.group_id:
                    continue
                if not entity.group_id:
                    continue
                pronoun_group = next((g for g in packet.meaning_groups if g.id == pronoun.group_id), None)
                entity_group = next((g for g in packet.meaning_groups if g.id == entity.group_id), None)
                if pronoun_group and entity_group:
                    is_pronoun_after = pronoun_group.start_token >= entity_group.end_token
                    is_entity_before = entity_group.end_token <= pronoun_group.start_token
                    if is_entity_before and is_pronoun_after:
                        graph.add_edge(
                            "refers_to",
                            pronoun.id,
                            entity.id,
                            group_id=pronoun.group_id,
                            confidence=0.6,
                            features={"anaphoric": True, "antecedent_group": entity.group_id},
                        )
                        break

    def _add_referents(self, graph: UOLGraph, referents: Iterable[ReferentAtom]) -> None:
        for ref in referents:
            kind = "self" if ref.entity_type == "self" else "entity"
            graph.add_atom(
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

    def _add_actions(
        self,
        graph: UOLGraph,
        actions: Iterable[ActionAtom],
        groups: Iterable[MeaningGroup],
    ) -> None:
        group_index = {group.id: group for group in groups}
        for action in actions:
            action_key = action.action_key or action.surface or "action"
            schema = self._schema_kernel.action_operators.get(action_key)
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
                    "schema_slots": action.schema_slots if action.schema_slots else {},
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
            if schema is not None:
                self._compile_state_deltas(graph, action_atom, action, schema)

    def _compile_state_deltas(
        self,
        graph: UOLGraph,
        action_atom: UOLAtom,
        action: ActionAtom,
        schema: Any,
    ) -> None:
        """Compile schema state_deltas into state atoms + causes + has_property edges.

        Uses only existing UOL primitives: state atoms, causes edges, has_property edges.
        No new edge types are introduced.
        """
        for delta in schema.state_deltas:
            target_role = delta.get("target", "actor")
            dimension = delta.get("dimension", "")
            direction = delta.get("direction", "unknown")
            delta_confidence = float(delta.get("confidence", 0.7))

            target_entity = self._find_role_atom(graph, action_atom, target_role)
            if target_entity is None:
                if "skipped_state_deltas" not in graph.trace:
                    graph.trace["skipped_state_deltas"] = []
                graph.trace["skipped_state_deltas"].append({
                    "action_key": action.action_key,
                    "target_role": target_role,
                    "dimension": dimension,
                    "reason": "role_atom_not_found",
                })
                continue

            state_key = f"{dimension}:{direction}"
            state_atom = graph.add_atom(
                "state",
                state_key,
                surface=f"{dimension.split('.')[-1]}:{direction}",
                group_id=action.group_id,
                confidence=delta_confidence,
                source="schema_state_delta",
                features={
                    "dimension": dimension,
                    "direction": direction,
                    "target_role": target_role,
                    "action_key": action.action_key,
                },
            )
            graph.add_edge(
                "causes",
                action_atom.id,
                state_atom.id,
                group_id=action.group_id,
                confidence=delta_confidence,
                features={
                    "dimension": dimension,
                    "direction": direction,
                    "schema_source": "state_delta",
                },
            )
            graph.add_edge(
                "has_property",
                target_entity.id,
                state_atom.id,
                group_id=action.group_id,
                confidence=delta_confidence,
                features={
                    "dimension": dimension,
                    "direction": direction,
                    "schema_source": "state_delta",
                },
            )

    def _connect_action_roles(
        self,
        graph: UOLGraph,
        action_atom: UOLAtom,
        action: ActionAtom,
        group: MeaningGroup | None,
    ) -> None:
        import dataclasses as _dc
        schema_slots = action.schema_slots or {}
        action_role_fields = [
            f.name for f in _dc.fields(ActionAtom)
            if f.name.endswith("_role")
        ]
        for field_name in action_role_fields:
            role_value = getattr(action, field_name, None)
            if not role_value:
                continue
            role_name = field_name[:-5]  # strip "_role" suffix
            target = self._resolve_role_atom(graph, role_value, action.group_id, group)
            slot_def = schema_slots.get(role_name, {})
            allowed_kinds = slot_def.get("allowed_entity_kinds", [])
            entity_kind = self._infer_entity_kind(target)
            kind_valid = True
            if allowed_kinds and entity_kind:
                kind_valid = any(
                    self._schema_kernel.entity_kinds.is_subclass_of(entity_kind, allowed)
                    or entity_kind == allowed
                    for allowed in allowed_kinds
                )
            graph.add_edge(
                "has_role",
                action_atom.id,
                target.id,
                group_id=action.group_id,
                confidence=action.confidence if kind_valid else action.confidence * 0.5,
                features={
                    "role": role_name,
                    "role_value": role_value,
                    "allowed_entity_kinds": allowed_kinds,
                    "entity_kind": entity_kind,
                    "kind_valid": kind_valid,
                },
            )

    @staticmethod
    def _infer_entity_kind(atom: UOLAtom) -> str:
        """Infer the schema entity kind from an atom's features.

        Maps runtime entity types to canonical EntityKindRegistry kinds:
        - 'user' → 'person' (the speaker is a person)
        - 'self' atom → 'autonomous_agent' (or 'self' if entity_type says so)
        - role_placeholder → 'object' (safe default for unknown referents)
        """
        entity_type = atom.features.get("entity_type", "")
        if entity_type == "user":
            return "person"
        if entity_type:
            return entity_type
        if atom.kind == "self":
            return "autonomous_agent"
        if atom.kind == "entity":
            key = atom.key.replace("entity:", "")
            if key in ("user", "speaker"):
                return "person"
            if key in ("world", "external_world", "memory"):
                return "concept"
            if atom.source == "role_placeholder":
                return "object"
            return "object"
        return ""

    def _find_role_atom(self, graph: UOLGraph, atom: UOLAtom, role: str) -> UOLAtom | None:
        for edge in graph.outgoing(atom.id, "has_role"):
            if edge.features.get("role") == role:
                target = graph.atoms.get(edge.target_id)
                if target:
                    return target
        return None

    def _add_emotional_evaluations(self, graph: UOLGraph, packet: MeaningPerceptPacket) -> None:
        actions = (packet.actions or []) + (getattr(packet, 'candidate_actions', None) or [])
        for action in actions:
            action_key = action.action_key or ""
            schema = self._schema_kernel.action_operators.get(action_key)
            if schema is None or schema.operator_family != "evaluate":
                continue
            relation_deltas = self._schema_kernel.action_operators.relation_deltas_for(action_key)
            if relation_deltas:
                relation_key = relation_deltas[0].get("relation_key", "evaluates")
            elif schema.emotional_valence == "positive":
                relation_key = "likes"
            elif schema.emotional_valence == "negative":
                relation_key = "dislikes"
            else:
                relation_key = "evaluates"
            action_atoms = [
                a for a in graph.atoms.values()
                if a.kind == "action" and a.group_id == action.group_id
                and a.key == (action.action_key or action.surface or "action")
            ]
            if not action_atoms:
                continue
            action_atom = action_atoms[0]
            subject_atom = self._find_role_atom(graph, action_atom, "actor")
            object_atom = self._find_role_atom(graph, action_atom, "object")
            if object_atom is None:
                object_atom = self._find_role_atom(graph, action_atom, "target")
            if subject_atom is None or object_atom is None:
                continue
            valence = schema.emotional_valence
            verb = (action.surface or action_key).lower()
            relation_atom = graph.add_atom(
                "relation",
                relation_key,
                surface=verb,
                group_id=action.group_id,
                confidence=action.confidence,
                source="emotional_predicate",
                features={"valence": valence, "predicate": relation_key},
            )
            graph.add_edge(
                "evaluates",
                subject_atom.id,
                object_atom.id,
                group_id=action.group_id,
                confidence=action.confidence,
                features={
                    "valence": valence,
                    "predicate": relation_key,
                    "emotional_verb": verb,
                },
            )
            graph.add_edge(
                "has_role",
                relation_atom.id,
                subject_atom.id,
                group_id=action.group_id,
                confidence=action.confidence,
                features={"role": "subject"},
            )
            graph.add_edge(
                "has_role",
                relation_atom.id,
                object_atom.id,
                group_id=action.group_id,
                confidence=action.confidence,
                features={"role": "object"},
            )

    def _extract_emotional_evaluation_observations(self, graph: UOLGraph) -> None:
        for edge in graph.edges_by_type("evaluates"):
            source = graph.atoms.get(edge.source_id)
            target = graph.atoms.get(edge.target_id)
            if source is None or target is None:
                continue
            relation_key = edge.features.get("predicate", "evaluates")
            relation_family = self._EDGE_TYPE_TO_RELATION_FAMILY.get(relation_key, "property")
            evidence = self._collect_evidence(graph, edge, source, target)
            if not evidence:
                evidence = [f"emotional_evaluation:{edge.id}"]
            graph.add_structural_observation(StructuralObservation(
                obs_type="relation_candidate",
                target="concept_lattice",
                operation="upsert_relation_candidate",
                target_id=f"relation:{relation_key}:{source.key}:{target.key}",
                fields={
                    "relation_key": relation_key,
                    "relation_family": relation_family,
                    "subject_concept_id": self._concept_key_for(source),
                    "subject_entity_id": source.key if source.kind in ("entity", "self") and source.key in ("user", "self", "world", "conversation", "memory") else "",
                    "subject_surface": source.surface,
                    "object_concept_id": self._concept_key_for(target),
                    "object_entity_id": target.key if target.kind in ("entity", "self") and target.key in ("user", "self", "world", "conversation", "memory") else "",
                    "object_surface": target.surface,
                    "source_atom_ids": [source.id, target.id],
                    "inverse_keys": [],
                    "group_id": edge.group_id or "",
                    "evidence_refs": evidence,
                    "features": dict(edge.features) if edge.features else {},
                    "relation_scope": edge.features.get("relation_scope", "") if edge.features else "",
                    "dimension": edge.features.get("dimension", "") if edge.features else "",
                    "qualifiers": self._extract_qualifier_fields(graph, source.id, target.id, edge.group_id or ""),
                },
                confidence=edge.confidence,
                reason="emotional_evaluation_relation",
                source_group_id=edge.group_id or "",
                source_refs=self._source_refs_for_group(graph, edge.group_id or ""),
                permission_refs=self._permission_refs_for_group(graph, edge.group_id or ""),
                evidence_refs=evidence,
            ))

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
            feats = dict(relation.features) if relation.features else {}
            mode = proposition_mode(relation)
            unresolved = list(open_roles(relation))
            feats.update({"proposition_mode": mode, "open_roles": unresolved})
            atom = graph.add_atom(
                "relation",
                relation.relation_key,
                surface=relation.surface or relation.relation_key,
                group_id=relation.group_id,
                span_id=relation.span_id,
                confidence=relation.confidence,
                source=relation.source,
                features={
                    "source_role": relation.source_role,
                    "target_role": relation.target_role,
                    **feats,
                },
                evidence=self._evidence(relation.evidence),
            )
            subject_surface = str(feats.get("subject_surface", "") or "")
            object_surface = str(feats.get("object_surface", "") or "")
            source = (
                self._entity_from_surface(graph, subject_surface, relation.group_id, relation.confidence)
                if subject_surface
                else self._resolve_role_atom(graph, relation.source_role, relation.group_id, None)
                if relation.source_role else None
            )
            target = None
            if object_surface:
                target = self._entity_from_surface(graph, object_surface, relation.group_id, relation.confidence)
            elif "object" not in unresolved and relation.target_role:
                target = self._resolve_role_atom(graph, relation.target_role, relation.group_id, None)

            if source is not None:
                graph.add_edge(
                    "has_role", atom.id, source.id,
                    group_id=relation.group_id,
                    confidence=relation.confidence,
                    features={"role": "subject", "role_value": relation.source_role},
                )
            if target is not None:
                graph.add_edge(
                    "has_role", atom.id, target.id,
                    group_id=relation.group_id,
                    confidence=relation.confidence,
                    features={"role": "object", "role_value": relation.target_role},
                )
            for role in unresolved:
                graph.add_port_binding(PortBinding(
                    owner_atom_id=atom.id,
                    owner_concept_id=f"concept:{atom.key}",
                    port_id=f"port:{atom.id}:{role}",
                    port_key=role,
                    required=True,
                    status="open_query_port",
                    score=1.0,
                    score_parts={"explicit_open_role": 1.0},
                    evidence_refs=self._evidence_refs(atom.evidence),
                ))

            self._typed_relation_edge(graph, relation, atom, source, target)
            if target is not None:
                self._add_relation_domain(graph, atom, target, feats, relation)
            if feats.get("is_teaching") and can_materialize_domain_edge(relation):
                src = self._group_source(graph, relation.group_id)
                graph.add_edge("teaches", src.id, atom.id, group_id=relation.group_id, confidence=relation.confidence)
            if feats.get("is_remember_command") and can_materialize_domain_edge(relation):
                self._add_remember_observation(graph, relation, source, target, feats)

    def _entity_from_surface(self, graph: UOLGraph, surface: str, group_id: str, confidence: float) -> UOLAtom:
        if surface in ("user", "self", "world", "memory"):
            return self._resolve_role_atom(graph, surface, group_id, None)
        return graph.add_atom(
            "entity",
            surface,
            surface=surface,
            group_id=group_id,
            confidence=min(0.72, confidence),
            source="relation_atom",
            features={"from_relation_atom": True},
        )

    def _add_relation_domain(
        self, graph: UOLGraph, relation_atom: UOLAtom, obj_atom: UOLAtom | None,
        feats: dict[str, Any], relation: RelationAtom,
    ) -> None:
        domain_text = feats.get("domain_surface", "")
        if not domain_text or obj_atom is None:
            return
        domain = graph.add_atom(
            "entity",
            domain_text,
            surface=domain_text,
            group_id=relation.group_id,
            confidence=min(0.68, relation.confidence - 0.04),
            source="relation_atom",
            features={"role": "domain", "from_domain_phrase": True},
        )
        domain_relation = graph.add_atom(
            "relation",
            "domain",
            surface="of",
            group_id=relation.group_id,
            confidence=min(0.66, relation.confidence - 0.06),
            source="relation_atom",
            features={"source": obj_atom.key, "target": domain_text},
        )
        graph.add_edge("has_role", obj_atom.id, domain.id, group_id=relation.group_id, confidence=domain.confidence, features={"role": "domain", "relation_atom_id": domain_relation.id})
        graph.add_edge("has_role", domain_relation.id, obj_atom.id, group_id=relation.group_id, confidence=domain_relation.confidence, features={"role": "source"})
        graph.add_edge("has_role", domain_relation.id, domain.id, group_id=relation.group_id, confidence=domain_relation.confidence, features={"role": "target"})

    def _add_remember_observation(
        self, graph: UOLGraph, relation: RelationAtom,
        source: UOLAtom | None, target: UOLAtom | None, feats: dict[str, Any],
    ) -> None:
        if source is None or target is None:
            return
        relation_family = self._relation_family_for_edge(relation.relation_key)
        evidence = [f"remember_command:{relation.group_id}"]
        graph.add_structural_observation(StructuralObservation(
            obs_type="relation_candidate",
            target="concept_lattice",
            operation="upsert_relation_candidate",
            target_id=f"relation:{relation.relation_key}:{source.key}:{target.key}",
            fields={
                "relation_key": relation.relation_key,
                "relation_family": relation_family,
                "subject_concept_id": self._concept_key_for(source),
                "subject_entity_id": source.key,
                "subject_surface": source.key if source.kind == "entity" else source.surface,
                "object_concept_id": self._concept_key_for(target),
                "object_entity_id": "",
                "object_surface": target.surface,
                "source_atom_ids": [source.id, target.id],
                "inverse_keys": [],
                "group_id": relation.group_id,
                "evidence_refs": evidence,
                "features": {},
                "qualifiers": self._extract_qualifier_fields(graph, source.id, target.id, relation.group_id),
            },
            confidence=relation.confidence,
            reason="remember_command_relation",
            source_group_id=relation.group_id,
            source_refs=self._source_refs_for_group(graph, relation.group_id),
            permission_refs=self._permission_refs_for_group(graph, relation.group_id),
            evidence_refs=evidence,
        ))

    def _typed_relation_edge(
        self,
        graph: UOLGraph,
        relation: RelationAtom,
        relation_atom: UOLAtom,
        source: UOLAtom | None,
        target: UOLAtom | None,
    ) -> None:
        if not can_materialize_domain_edge(relation):
            return
        edge_type = {
            "same_as": "same_as", "is_a": "is_a", "type_of": "is_a",
            "kind_of": "is_a", "part_of": "part_of", "used_for": "used_for",
            "has_property": "has_property", "causes": "causes",
            "enables": "enables", "prevents": "prevents",
            "before": "before", "after": "after",
        }.get(relation.relation_key)
        if edge_type is None or source is None or target is None:
            return
        features = {
            "relation_atom_id": relation_atom.id,
            "proposition_mode": proposition_mode(relation),
            "open_roles": list(open_roles(relation)),
        }
        for key in ("property_dimension", "dimension", "relation_scope", "cardinality", "update_policy"):
            value = (relation.features or {}).get(key)
            if value not in (None, "", [], {}):
                features[key] = value
        graph.add_edge(
            edge_type, source.id, target.id,
            group_id=relation.group_id,
            confidence=relation.confidence,
            features=features,
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
            if (intent.is_question or intent.intent_key.endswith("query")) and intent.intent_key not in ("phatic_checkin", "reciprocal_phatic"):
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
        import dataclasses as _dc
        predicate_role_fields = [
            f.name for f in _dc.fields(PredicatePhrase)
            if f.name.endswith("_role")
        ]
        for predicate in predicates:
            role_features = {}
            for field_name in predicate_role_fields:
                val = getattr(predicate, field_name, None)
                if val is not None:
                    role_features[field_name] = val
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
                    **role_features,
                },
                evidence=self._evidence(predicate.evidence),
            )
            for field_name in predicate_role_fields:
                role_value = getattr(predicate, field_name, None)
                if not role_value:
                    continue
                role_name = field_name[:-5]  # strip "_role" suffix
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
                time_relation = time.features.get("relation", "")
                edge_type = "before" if time_relation == "past" else "after" if time_relation == "future" else "modifies"
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
                if candidate.selected:
                    if not selected_atom_id:
                        selected_atom_id = atom.id
                    atom.features["selected_candidate"] = True

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
            if is_role_placeholder(atom):
                continue
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
            elif atom.source == "unknown_lexeme" or atom.features.get("concept_state") == "candidate_atom":
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
            if self._affordance_lattice is not None and hasattr(self._affordance_lattice, 'predict'):
                for prediction in self._affordance_lattice.predict([atom]) or []:
                    graph.add_affordance_prediction(prediction)

    _EDGE_TYPE_TO_RELATION_FAMILY: dict[str, str] = {
        "is_a": "taxonomy",
        "same_as": "identity",
        "has_property": "property",
        "used_for": "affordance",
        "part_of": "membership",
    }

    def _extract_state_delta_observations(self, graph: UOLGraph) -> None:
        """Extract state delta structural observations from schema-driven state delta atoms.

        State atoms created by _compile_state_deltas have source='schema_state_delta'.
        For each, we produce a structural observation for downstream patch compilation.
        """
        state_atoms = [
            a for a in graph.atoms.values()
            if a.kind == "state" and a.source == "schema_state_delta"
        ]
        if not state_atoms:
            return

        operations: list[PatchOperation] = []
        for state_atom in state_atoms:
            dimension = state_atom.features.get("dimension", "")
            direction = state_atom.features.get("direction", "unknown")
            target_role = state_atom.features.get("target_role", "actor")
            action_key = state_atom.features.get("action_key", "")
            group_id = state_atom.group_id

            entity_atom = None
            for edge in graph.incoming(state_atom.id, "has_property"):
                entity_atom = graph.atoms.get(edge.source_id)
                break

            if entity_atom is None:
                continue

            entity_id = entity_atom.key.replace("entity:", "").replace("self:", "")
            family = dimension.split(".")[0] if "." in dimension else dimension

            operations.append(PatchOperation(
                operation="upsert_state",
                target_id=f"state:{entity_id}:{dimension}",
                fields={
                    "entity_id": entity_id,
                    "state_family": family,
                    "dimension": dimension,
                    "direction": direction,
                    "action_key": action_key,
                    "target_role": target_role,
                    "source_atom_ids": [entity_atom.id, state_atom.id],
                    "group_id": group_id,
                },
                confidence=state_atom.confidence,
                reason="schema_state_delta",
            ))

        if operations:
            for op in operations:
                graph.add_structural_observation(StructuralObservation(
                    obs_type="state_delta",
                    target="concept_lattice",
                    operation=op.operation,
                    target_id=op.target_id,
                    fields=op.fields,
                    confidence=op.confidence,
                    reason=op.reason,
                    source_group_id="",
                    source_refs=self._source_refs_for_group(graph, ""),
                    permission_refs=self._permission_refs_for_group(graph, ""),
                    evidence_refs=[f"state_delta:{a.id}" for a in state_atoms],
                ))

    _TEACHING_EDGE_TYPES: frozenset = frozenset({"is_a", "same_as", "has_property", "used_for", "part_of"})

    def _is_teaching_edge_type(self, edge_type: str) -> bool:
        if edge_type in self._TEACHING_EDGE_TYPES:
            return True
        if self._predicate_schema_store is not None:
            schema = self._predicate_schema_store.get(edge_type)
            if schema is not None:
                return True
        return False

    def _relation_family_for_edge(self, edge_type: str) -> str:
        family = self._EDGE_TYPE_TO_RELATION_FAMILY.get(edge_type, "")
        if family:
            return family
        if self._predicate_schema_store is not None:
            schema = self._predicate_schema_store.get(edge_type)
            if schema is not None:
                return schema.relation_family
        return "definition"

    def _extract_graph_patches(self, graph: UOLGraph) -> None:
        for group in graph.groups:
            teaching_edges = [
                edge for edge in graph.group_edges(group.id)
                if self._is_teaching_edge_type(edge.edge_type)
            ]
            if teaching_edges and graph.has_edge("teaches", source_kind="source", group_id=group.id):
                operations = []
                for edge in teaching_edges:
                    source = graph.atoms.get(edge.source_id)
                    target = graph.atoms.get(edge.target_id)
                    if source is None or target is None:
                        continue
                    evidence = self._collect_evidence(graph, edge, source, target)
                    if not evidence:
                        evidence = [f"surface_teaching_relation:{group.id}"]
                    edge_features = dict(edge.features) if edge.features else {}
                    operations.append(PatchOperation(
                        operation="upsert_relation_candidate",
                        target_id=f"relation:{edge.edge_type}:{source.key}:{target.key}",
                        fields={
                            "relation_key": edge.edge_type,
                            "relation_family": self._relation_family_for_edge(edge.edge_type),
                            "subject_concept_id": self._concept_key_for(source),
                            "subject_entity_id": source.key if source.kind in ("entity", "self") and source.key in ("user", "self", "world", "conversation", "memory") else "",
                            "subject_surface": source.surface,
                            "object_concept_id": self._concept_key_for(target),
                            "object_entity_id": target.key if target.kind in ("entity", "self") and target.key in ("user", "self", "world", "conversation", "memory") else "",
                            "object_surface": target.surface,
                            "source_atom_ids": [source.id, target.id],
                            "inverse_keys": [],
                            "group_id": group.id,
                            "evidence_refs": evidence,
                            "features": edge_features,
                            "relation_scope": edge_features.get("relation_scope", ""),
                            "dimension": edge_features.get("dimension", "") or edge_features.get("property_dimension", ""),
                            "qualifiers": self._extract_qualifier_fields(graph, source.id, target.id, group.id),
                        },
                        confidence=edge.confidence,
                        reason="user_teaching_graph_relation",
                    ))
                if operations:
                    for op in operations:
                        graph.add_structural_observation(StructuralObservation(
                            obs_type="teaching_edge",
                            target="concept_lattice",
                            operation=op.operation,
                            target_id=op.target_id,
                            fields=op.fields,
                            confidence=op.confidence,
                            reason=op.reason,
                            source_group_id=group.id,
                            source_refs=self._source_refs_for_group(graph, group.id),
                            permission_refs=self._permission_refs_for_group(graph, group.id),
                            evidence_refs=self._collect_all_evidence(graph, [op]) or [f"teaching_group:{group.id}"],
                        ))

        self._extract_emotional_evaluation_observations(graph)
        self._extract_state_delta_observations(graph)

        concept_operations = []
        for resolution in graph.concept_resolutions:
            if resolution.state != "new_candidate":
                continue
            atom = graph.atoms.get(resolution.atom_id)
            if atom is None:
                continue
            evidence = self._evidence_refs(atom.evidence) if hasattr(atom, "evidence") else []
            if not evidence:
                evidence = [f"concept_resolution:{resolution.atom_id}"]
            concept_operations.append(PatchOperation(
                operation="upsert_concept_candidate",
                target_id=resolution.concept_id,
                fields={
                    "concept_key": atom.key,
                    "atom_kind": atom.kind,
                    "surface": atom.surface,
                    "state": "candidate_atom",
                    "evidence_refs": evidence,
                },
                confidence=resolution.confidence,
                reason=resolution.reason,
            ))
        if concept_operations:
            for op in concept_operations:
                graph.add_structural_observation(StructuralObservation(
                    obs_type="concept_candidate",
                    target="concept_lattice",
                    operation=op.operation,
                    target_id=op.target_id,
                    fields=op.fields,
                    confidence=op.confidence,
                    reason=op.reason,
                    source_group_id="",
                    source_refs=self._source_refs_for_group(graph, ""),
                    permission_refs=self._permission_refs_for_group(graph, ""),
                    evidence_refs=self._collect_all_evidence(graph, [op]) or ["concept_candidates"],
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
                for op in operations:
                    graph.add_structural_observation(StructuralObservation(
                        obs_type="port_binding",
                        target="concept_lattice",
                        operation=op.operation,
                        target_id=op.target_id,
                        fields=op.fields,
                        confidence=op.confidence,
                        reason=op.reason,
                        source_group_id="",
                        source_refs=self._source_refs_for_group(graph, ""),
                        permission_refs=self._permission_refs_for_group(graph, ""),
                        evidence_refs=[],
                    ))

        if graph.construction_matches:
            for match in graph.construction_matches:
                graph.add_structural_observation(StructuralObservation(
                    obs_type="construction_match",
                    target="construction_lattice",
                    operation="observe_construction_match",
                    target_id=f"construction:{match.construction_key}",
                    fields=match.to_dict(),
                    confidence=match.confidence,
                    reason="runtime_construction_match",
                    source_group_id="",
                    source_refs=self._source_refs_for_group(graph, ""),
                    permission_refs=self._permission_refs_for_group(graph, ""),
                    evidence_refs=[],
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
        if self._affordance_lattice is not None and hasattr(self._affordance_lattice, 'predict'):
            return True
        return False

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

    @staticmethod
    def _collect_evidence(graph: UOLGraph, edge: Any, source: Any, target: Any) -> list[str]:
        refs: list[str] = []
        for item in (edge, source, target):
            ev = getattr(item, "evidence", [])
            if isinstance(ev, list):
                for e in ev:
                    span_id = str(e.get("span_id", "") if isinstance(e, dict) else "")
                    group_id = str(e.get("group_id", "") if isinstance(e, dict) else "")
                    source_str = str(e.get("source", "") if isinstance(e, dict) else "")
                    ref = ":".join(p for p in (source_str, group_id, span_id) if p)
                    if ref and ref not in refs:
                        refs.append(ref)
            elif isinstance(ev, dict):
                span_id = str(ev.get("span_id", ""))
                group_id = str(ev.get("group_id", ""))
                source_str = str(ev.get("source", ""))
                ref = ":".join(p for p in (source_str, group_id, span_id) if p)
                if ref and ref not in refs:
                    refs.append(ref)
        return refs

    @staticmethod
    def _collect_all_evidence(graph: UOLGraph, operations: list[Any]) -> list[str]:
        refs: list[str] = []
        for op in operations:
            ev = op.fields.get("evidence_refs", [])
            if isinstance(ev, list):
                for r in ev:
                    if r and r not in refs:
                        refs.append(r)
        return refs

    @staticmethod
    def _concept_key_for(atom: Any) -> str:
        key = getattr(atom, "key", "") or ""
        if key.startswith("entity:") or key.startswith("concept:"):
            return key
        if key:
            return f"concept:{key}"
        return key

    @staticmethod
    def _extract_qualifier_fields(
        graph: UOLGraph, source_atom_id: str, target_atom_id: str = "", group_id: str = "",
    ) -> dict[str, dict[str, str]]:
        """Extract qualifier role data for a relation between source and target atoms.

        Qualifiers can appear in two ways:
        1. Non-subject/object/source/target roles on relation atoms connected
           to the source entity via has_role edges.
        2. Direct has_role edges on the object entity with qualifier roles
           (e.g. "domain" from "just between us" domain phrases).

        Both paths are scanned and merged.
        """
        _CORE_ROLES = frozenset({"subject", "object", "source", "target"})
        qualifiers: dict[str, dict[str, str]] = {}

        # 1. Find relation atoms where source_atom_id is a role-filler.
        relation_atom_ids: set[str] = set()
        for edge in graph.edges:
            if edge.edge_type != "has_role":
                continue
            if edge.target_id != source_atom_id:
                continue
            if group_id and edge.group_id and edge.group_id != group_id:
                continue
            relation_atom_ids.add(edge.source_id)

        # 2. If a target atom is given, narrow to relation atoms that also
        #    contain the target as a role-filler (disambiguation).
        if target_atom_id and relation_atom_ids:
            narrowed: set[str] = set()
            for edge in graph.edges:
                if edge.edge_type != "has_role":
                    continue
                if edge.target_id != target_atom_id:
                    continue
                if edge.source_id in relation_atom_ids:
                    narrowed.add(edge.source_id)
            if narrowed:
                relation_atom_ids = narrowed

        # 3. Extract non-core roles from the matched relation atoms.
        for rel_atom_id in relation_atom_ids:
            for edge in graph.edges:
                if edge.edge_type != "has_role":
                    continue
                if edge.source_id != rel_atom_id:
                    continue
                role = edge.features.get("role", "")
                if not role or role in _CORE_ROLES:
                    continue
                target = graph.atoms.get(edge.target_id)
                if target is None:
                    continue
                qualifiers[role] = {
                    "concept_id": MeaningGraphBuilder._concept_key_for(target),
                    "entity_id": target.key if target.kind in ("entity", "self") and target.key in ("user", "self", "world", "conversation", "memory") else "",
                    "surface": target.surface or "",
                }

        # 4. Scan for direct has_role edges on the object entity that carry
        #    qualifier roles (e.g. "domain" from domain phrases).
        if target_atom_id:
            for edge in graph.edges:
                if edge.edge_type != "has_role":
                    continue
                if edge.source_id != target_atom_id:
                    continue
                if group_id and edge.group_id and edge.group_id != group_id:
                    continue
                role = edge.features.get("role", "")
                if not role or role in _CORE_ROLES:
                    continue
                target = graph.atoms.get(edge.target_id)
                if target is None:
                    continue
                qualifiers[role] = {
                    "concept_id": MeaningGraphBuilder._concept_key_for(target),
                    "entity_id": target.key if target.kind in ("entity", "self") and target.key in ("user", "self", "world", "conversation", "memory") else "",
                    "surface": target.surface or "",
                }

        return qualifiers

    def _source_refs_for_group(self, graph: UOLGraph, group_id: str) -> list[str]:
        sources = graph.atoms_by_kind("source", group_id) if group_id else []
        if not sources:
            sources = graph.atoms_by_kind("source")
        return [atom.id for atom in sources]

    def _permission_refs_for_group(self, graph: UOLGraph, group_id: str) -> list[str]:
        permissions = graph.atoms_by_kind("permission", group_id) if group_id else []
        if not permissions:
            permissions = graph.atoms_by_kind("permission")
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
        for atom in graph.group_atoms(group_id):
            if atom.surface and atom.surface.lower() == role_value.lower() and atom.kind in ("entity", "concept", "self"):
                return atom
        return graph.add_atom(
            "entity",
            role_value,
            surface=role_value,
            group_id=group_id,
            confidence=0.45,
            source="role_resolution",
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
