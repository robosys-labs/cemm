from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable
import copy
import uuid

from .graph_patch import GraphPatch
from .uol_atom import UOLAtom, UOLEdge, CANONICAL_ATOM_KINDS, CANONICAL_EDGE_TYPES


@dataclass
class UOLMeaningGroup:
    id: str
    surface: str = ""
    parent_group_id: str = ""
    start_token: int = 0
    end_token: int = 0
    function: str = "unknown"
    atom_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    features: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "surface": self.surface,
            "parent_group_id": self.parent_group_id,
            "start_token": self.start_token,
            "end_token": self.end_token,
            "function": self.function,
            "atom_ids": list(self.atom_ids),
            "edge_ids": list(self.edge_ids),
            "confidence": self.confidence,
            "features": dict(self.features),
        }


@dataclass
class CandidateSet:
    id: str
    target_span_id: str = ""
    target_surface: str = ""
    group_id: str = ""
    hypothesis_id: str = ""
    candidate_atom_ids: list[str] = field(default_factory=list)
    candidate_interpretation_ids: list[str] = field(default_factory=list)
    candidate_subgraphs: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    selected_atom_id: str = ""
    selected_candidate_ids: list[str] = field(default_factory=list)
    rejected_candidate_ids: list[str] = field(default_factory=list)
    resolved: bool = False
    reason: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_span_id": self.target_span_id,
            "target_surface": self.target_surface,
            "group_id": self.group_id,
            "hypothesis_id": self.hypothesis_id,
            "candidate_atom_ids": list(self.candidate_atom_ids),
            "candidate_interpretation_ids": list(self.candidate_interpretation_ids),
            "candidate_subgraphs": {
                key: {
                    "atom_ids": list(value.get("atom_ids", [])),
                    "edge_ids": list(value.get("edge_ids", [])),
                }
                for key, value in self.candidate_subgraphs.items()
            },
            "selected_atom_id": self.selected_atom_id,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "rejected_candidate_ids": list(self.rejected_candidate_ids),
            "resolved": self.resolved,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class ConstructionMatch:
    id: str
    construction_key: str
    group_id: str = ""
    matched_span_ids: list[str] = field(default_factory=list)
    expected_ports: list[str] = field(default_factory=list)
    graph_patch_templates: list[dict[str, Any]] = field(default_factory=list)
    pragmatic_hints: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "construction_key": self.construction_key,
            "group_id": self.group_id,
            "matched_span_ids": list(self.matched_span_ids),
            "expected_ports": list(self.expected_ports),
            "graph_patch_templates": [dict(item) for item in self.graph_patch_templates],
            "pragmatic_hints": list(self.pragmatic_hints),
            "confidence": self.confidence,
        }


@dataclass
class ConceptResolution:
    atom_id: str
    concept_id: str = ""
    state: str = "unresolved"
    inherited_from: list[str] = field(default_factory=list)
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_id": self.atom_id,
            "concept_id": self.concept_id,
            "state": self.state,
            "inherited_from": list(self.inherited_from),
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
        }


@dataclass
class PortBinding:
    owner_atom_id: str
    port_key: str
    filler_atom_id: str = ""
    owner_concept_id: str = ""
    port_id: str = ""
    required: bool = False
    status: str = "bound"
    score: float = 0.5
    score_parts: dict[str, float] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    source_edge_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_atom_id": self.owner_atom_id,
            "owner_concept_id": self.owner_concept_id,
            "port_id": self.port_id,
            "port_key": self.port_key,
            "filler_atom_id": self.filler_atom_id,
            "required": self.required,
            "status": self.status,
            "score": self.score,
            "score_parts": dict(self.score_parts),
            "evidence_refs": list(self.evidence_refs),
            "source_edge_id": self.source_edge_id,
        }


@dataclass
class AffordancePrediction:
    id: str
    affordance_key: str
    trigger_atom_ids: list[str] = field(default_factory=list)
    required_binding_ids: list[str] = field(default_factory=list)
    predicted_patch_template: dict[str, Any] = field(default_factory=dict)
    effect_type: str = "state_change"
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "affordance_key": self.affordance_key,
            "trigger_atom_ids": list(self.trigger_atom_ids),
            "required_binding_ids": list(self.required_binding_ids),
            "predicted_patch_template": dict(self.predicted_patch_template),
            "effect_type": self.effect_type,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
        }


@dataclass
class UOLGraph:
    id: str = ""
    signal_id: str = ""
    context_id: str = ""
    raw_text: str = ""
    language: str = "und"
    atoms: dict[str, UOLAtom] = field(default_factory=dict)
    edges: list[UOLEdge] = field(default_factory=list)
    group_atom_ids: dict[str, list[str]] = field(default_factory=dict)
    groups: list[UOLMeaningGroup] = field(default_factory=list)
    candidate_sets: list[CandidateSet] = field(default_factory=list)
    construction_matches: list[ConstructionMatch] = field(default_factory=list)
    concept_resolutions: list[ConceptResolution] = field(default_factory=list)
    port_bindings: list[PortBinding] = field(default_factory=list)
    affordance_predictions: list[AffordancePrediction] = field(default_factory=list)
    patch_candidates: list[GraphPatch] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

    def add_atom(
        self,
        kind: str,
        key: str,
        *,
        surface: str = "",
        group_id: str = "",
        span_id: str = "",
        value: str | int | float | bool | None = None,
        features: dict[str, Any] | None = None,
        confidence: float = 0.5,
        source: str = "surface",
        evidence: Iterable[dict[str, Any]] | None = None,
        atom_id: str | None = None,
    ) -> UOLAtom:
        kind = self._canonical_atom_kind(kind)
        key = self._clean_key(key or surface or kind)
        atom_id = atom_id or self._atom_id(kind, key, group_id, span_id)
        existing = self.atoms.get(atom_id)
        if existing is not None:
            existing.confidence = max(existing.confidence, confidence)
            existing.features.update(features or {})
            for item in evidence or []:
                if item not in existing.evidence:
                    existing.evidence.append(dict(item))
            if surface and not existing.surface:
                existing.surface = surface
            self._index_atom_to_group(existing.id, group_id)
            return existing
        atom = UOLAtom(
            id=atom_id,
            kind=kind,
            key=key,
            surface=surface,
            group_id=group_id,
            span_id=span_id,
            value=value,
            features=dict(features or {}),
            confidence=confidence,
            source=source,
            evidence=[dict(item) for item in evidence or []],
        )
        self.atoms[atom.id] = atom
        self._index_atom_to_group(atom.id, group_id)
        return atom

    def add_edge(
        self,
        edge_type: str,
        source_id: str,
        target_id: str,
        *,
        group_id: str = "",
        predicate_id: str = "",
        confidence: float = 0.5,
        source: str = "uol_graph_builder",
        features: dict[str, Any] | None = None,
        evidence: Iterable[dict[str, Any]] | None = None,
        edge_id: str | None = None,
    ) -> UOLEdge:
        edge_type = self._canonical_edge_type(edge_type)
        if source_id not in self.atoms or target_id not in self.atoms:
            raise KeyError(f"edge references missing atom: {source_id!r}->{target_id!r}")
        edge_id = edge_id or self._edge_id(edge_type, source_id, target_id, group_id, predicate_id, features)
        for existing in self.edges:
            if existing.id == edge_id:
                existing.confidence = max(existing.confidence, confidence)
                existing.features.update(features or {})
                for item in evidence or []:
                    if item not in existing.evidence:
                        existing.evidence.append(dict(item))
                self._index_edge_to_group(existing.id, group_id)
                return existing
        edge = UOLEdge(
            id=edge_id,
            edge_type=edge_type,
            source_id=source_id,
            target_id=target_id,
            group_id=group_id,
            predicate_id=predicate_id,
            confidence=confidence,
            source=source,
            features=dict(features or {}),
            evidence=[dict(item) for item in evidence or []],
        )
        self.edges.append(edge)
        self._index_edge_to_group(edge.id, group_id)
        return edge

    def add_group(
        self,
        group_id: str,
        *,
        surface: str = "",
        parent_group_id: str = "",
        start_token: int = 0,
        end_token: int = 0,
        function: str = "unknown",
        confidence: float = 0.5,
        features: dict[str, Any] | None = None,
    ) -> UOLMeaningGroup:
        for group in self.groups:
            if group.id == group_id:
                group.surface = group.surface or surface
                group.parent_group_id = parent_group_id or group.parent_group_id
                group.start_token = start_token if start_token != 0 else group.start_token
                group.end_token = end_token if end_token != 0 else group.end_token
                group.function = function or group.function
                group.confidence = max(group.confidence, confidence)
                group.features.update(features or {})
                return group
        group = UOLMeaningGroup(
            id=group_id,
            surface=surface,
            parent_group_id=parent_group_id,
            start_token=start_token,
            end_token=end_token,
            function=function,
            confidence=confidence,
            features=dict(features or {}),
        )
        self.groups.append(group)
        self.group_atom_ids.setdefault(group_id, [])
        return group

    def add_candidate_set(self, candidate_set: CandidateSet) -> CandidateSet:
        self.candidate_sets.append(candidate_set)
        return candidate_set

    def add_construction_match(self, match: ConstructionMatch) -> ConstructionMatch:
        self.construction_matches.append(match)
        return match

    def add_concept_resolution(self, resolution: ConceptResolution) -> ConceptResolution:
        self.concept_resolutions.append(resolution)
        return resolution

    def add_port_binding(self, binding: PortBinding) -> PortBinding:
        self.port_bindings.append(binding)
        return binding

    def add_affordance_prediction(self, prediction: AffordancePrediction) -> AffordancePrediction:
        self.affordance_predictions.append(prediction)
        return prediction

    def add_patch_candidate(self, patch: GraphPatch) -> GraphPatch:
        self.patch_candidates.append(patch)
        return patch

    def clone(self, *, graph_id: str | None = None) -> UOLGraph:
        cloned = copy.deepcopy(self)
        cloned.id = graph_id or f"{self.id}_clone_{uuid.uuid4().hex[:8]}"
        cloned.trace = dict(cloned.trace)
        cloned.trace["cloned_from"] = self.id
        return cloned

    def merge_graph(self, other: UOLGraph, *, confidence_floor: float = 0.0) -> None:
        for group in other.groups:
            self.add_group(
                group.id,
                surface=group.surface,
                parent_group_id=group.parent_group_id,
                start_token=group.start_token,
                end_token=group.end_token,
                function=group.function,
                confidence=group.confidence,
                features=group.features,
            )
        for atom in other.atoms.values():
            if atom.confidence < confidence_floor:
                continue
            self.add_atom(
                atom.kind,
                atom.key,
                surface=atom.surface,
                group_id=atom.group_id,
                span_id=atom.span_id,
                value=atom.value,
                features=atom.features,
                confidence=atom.confidence,
                source=atom.source,
                evidence=atom.evidence,
                atom_id=atom.id,
            )
        for edge in other.edges:
            if edge.confidence < confidence_floor:
                continue
            if edge.source_id in self.atoms and edge.target_id in self.atoms:
                self.add_edge(
                    edge.edge_type,
                    edge.source_id,
                    edge.target_id,
                    group_id=edge.group_id,
                    predicate_id=edge.predicate_id,
                    confidence=edge.confidence,
                    source=edge.source,
                    features=edge.features,
                    evidence=edge.evidence,
                    edge_id=edge.id,
                )
        self.candidate_sets.extend(copy.deepcopy(other.candidate_sets))
        self.construction_matches.extend(copy.deepcopy(other.construction_matches))
        self.concept_resolutions.extend(copy.deepcopy(other.concept_resolutions))
        self.port_bindings.extend(copy.deepcopy(other.port_bindings))
        self.affordance_predictions.extend(copy.deepcopy(other.affordance_predictions))
        self.patch_candidates.extend(copy.deepcopy(other.patch_candidates))

    def prune(self, *, atom_threshold: float = 0.0, edge_threshold: float = 0.0) -> None:
        if atom_threshold > 0:
            keep_atom_ids = {
                atom_id for atom_id, atom in self.atoms.items()
                if atom.confidence >= atom_threshold
            }
            self.atoms = {
                atom_id: atom for atom_id, atom in self.atoms.items()
                if atom_id in keep_atom_ids
            }
            self.edges = [
                edge for edge in self.edges
                if edge.source_id in keep_atom_ids and edge.target_id in keep_atom_ids
            ]
            for group_id, atom_ids in list(self.group_atom_ids.items()):
                self.group_atom_ids[group_id] = [atom_id for atom_id in atom_ids if atom_id in keep_atom_ids]
            for group in self.groups:
                group.atom_ids = [atom_id for atom_id in group.atom_ids if atom_id in keep_atom_ids]
            for candidate_set in self.candidate_sets:
                candidate_set.candidate_atom_ids = [
                    atom_id for atom_id in candidate_set.candidate_atom_ids
                    if atom_id in keep_atom_ids
                ]
        if edge_threshold > 0:
            self.edges = [edge for edge in self.edges if edge.confidence >= edge_threshold]
            keep_edge_ids = {edge.id for edge in self.edges}
            for group in self.groups:
                group.edge_ids = [edge_id for edge_id in group.edge_ids if edge_id in keep_edge_ids]

    def select_candidate(
        self,
        candidate_set_id: str,
        selected_candidate_ids: Iterable[str],
        *,
        reject_rest: bool = True,
    ) -> CandidateSet | None:
        selected = list(selected_candidate_ids)
        for candidate_set in self.candidate_sets:
            if candidate_set.id != candidate_set_id:
                continue
            candidate_set.selected_candidate_ids = selected
            candidate_set.resolved = True
            if reject_rest:
                candidate_set.rejected_candidate_ids = [
                    candidate_id for candidate_id in candidate_set.candidate_interpretation_ids
                    if candidate_id not in selected
                ]
            return candidate_set
        return None

    def atoms_by_kind(self, kind: str, group_id: str | None = None) -> list[UOLAtom]:
        kind = self._canonical_atom_kind(kind)
        values = [atom for atom in self.atoms.values() if atom.kind == kind]
        if group_id is not None:
            values = [atom for atom in values if atom.group_id == group_id]
        return values

    def edges_by_type(self, edge_type: str, group_id: str | None = None) -> list[UOLEdge]:
        edge_type = self._canonical_edge_type(edge_type)
        values = [edge for edge in self.edges if edge.edge_type == edge_type]
        if group_id is not None:
            values = [edge for edge in values if edge.group_id == group_id]
        return values

    def outgoing(self, atom_id: str, edge_type: str | None = None) -> list[UOLEdge]:
        return [
            edge for edge in self.edges
            if edge.source_id == atom_id and (edge_type is None or edge.edge_type == edge_type)
        ]

    def incoming(self, atom_id: str, edge_type: str | None = None) -> list[UOLEdge]:
        return [
            edge for edge in self.edges
            if edge.target_id == atom_id and (edge_type is None or edge.edge_type == edge_type)
        ]

    def has_edge(
        self,
        edge_type: str,
        *,
        source_kind: str | None = None,
        target_kind: str | None = None,
        group_id: str | None = None,
    ) -> bool:
        edge_type = self._canonical_edge_type(edge_type)
        for edge in self.edges:
            if edge.edge_type != edge_type:
                continue
            if group_id is not None and edge.group_id != group_id:
                continue
            source_atom = self.atoms.get(edge.source_id)
            target_atom = self.atoms.get(edge.target_id)
            if source_atom is None or target_atom is None:
                continue
            if source_kind is not None and source_atom.kind != self._canonical_atom_kind(source_kind):
                continue
            if target_kind is not None and target_atom.kind != self._canonical_atom_kind(target_kind):
                continue
            return True
        return False

    def group_atoms(self, group_id: str) -> list[UOLAtom]:
        return [self.atoms[atom_id] for atom_id in self.group_atom_ids.get(group_id, []) if atom_id in self.atoms]

    def group_edges(self, group_id: str) -> list[UOLEdge]:
        return [edge for edge in self.edges if edge.group_id == group_id]

    def concept_resolution_for(self, atom_id: str) -> ConceptResolution | None:
        for resolution in self.concept_resolutions:
            if resolution.atom_id == atom_id:
                return resolution
        return None

    def bindings_for_owner(self, atom_id: str) -> list[PortBinding]:
        return [binding for binding in self.port_bindings if binding.owner_atom_id == atom_id]

    def to_training_example(self) -> dict[str, Any]:
        return {
            "graph_id": self.id,
            "signal_id": self.signal_id,
            "context_id": self.context_id,
            "raw_text": self.raw_text,
            "language": self.language,
            "atoms": [atom.to_dict() for atom in self.atoms.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "groups": [group.to_dict() for group in self.groups],
            "group_atom_ids": {
                group_id: list(atom_ids)
                for group_id, atom_ids in self.group_atom_ids.items()
            },
            "candidate_sets": [candidate_set.to_dict() for candidate_set in self.candidate_sets],
            "construction_matches": [match.to_dict() for match in self.construction_matches],
            "concept_resolutions": [resolution.to_dict() for resolution in self.concept_resolutions],
            "port_bindings": [binding.to_dict() for binding in self.port_bindings],
            "affordance_predictions": [
                prediction.to_dict()
                for prediction in self.affordance_predictions
            ],
            "graph_patch_candidates": [patch.to_dict() for patch in self.patch_candidates],
            "trace": dict(self.trace),
        }

    def _index_atom_to_group(self, atom_id: str, group_id: str) -> None:
        if not group_id:
            return
        self.group_atom_ids.setdefault(group_id, [])
        if atom_id not in self.group_atom_ids[group_id]:
            self.group_atom_ids[group_id].append(atom_id)
        for group in self.groups:
            if group.id == group_id and atom_id not in group.atom_ids:
                group.atom_ids.append(atom_id)

    def _index_edge_to_group(self, edge_id: str, group_id: str) -> None:
        if not group_id:
            return
        for group in self.groups:
            if group.id == group_id and edge_id not in group.edge_ids:
                group.edge_ids.append(edge_id)

    @staticmethod
    def _canonical_atom_kind(kind: str) -> str:
        normalized = (kind or "").strip().lower().replace("_atom", "")
        aliases = {
            "referent": "entity",
            "entityatom": "entity",
            "processatom": "process",
            "stateatom": "state",
            "relationatom": "relation",
            "qualityatom": "quality",
            "quantityatom": "quantity",
            "timeatom": "time",
            "placeatom": "place",
            "intentatom": "intent",
            "needatom": "need",
            "modalityatom": "modality",
            "evidenceatom": "evidence",
            "sourceatom": "source",
            "permissionatom": "permission",
            "actionatom": "action",
            "selfatom": "self",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized not in CANONICAL_ATOM_KINDS:
            raise ValueError(f"unknown UOL atom kind: {kind!r}")
        return normalized

    @staticmethod
    def _canonical_edge_type(edge_type: str) -> str:
        normalized = (edge_type or "").strip().lower()
        if normalized not in CANONICAL_EDGE_TYPES:
            raise ValueError(f"unknown UOL edge type: {edge_type!r}")
        return normalized

    @staticmethod
    def _clean_key(value: str) -> str:
        clean = "_".join(str(value or "").strip().lower().split())
        return clean or "unknown"

    def _atom_id(self, kind: str, key: str, group_id: str, span_id: str) -> str:
        stem = f"{kind}:{key}:{group_id}:{span_id}"
        return "uol_" + uuid.uuid5(uuid.NAMESPACE_URL, stem).hex[:16]

    def _edge_id(
        self,
        edge_type: str,
        source_id: str,
        target_id: str,
        group_id: str,
        predicate_id: str,
        features: dict[str, Any] | None,
    ) -> str:
        feature_key = ",".join(f"{key}={value}" for key, value in sorted((features or {}).items()))
        stem = f"{edge_type}:{source_id}:{target_id}:{group_id}:{predicate_id}:{feature_key}"
        return "uole_" + uuid.uuid5(uuid.NAMESPACE_URL, stem).hex[:16]
