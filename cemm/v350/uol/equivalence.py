"""Semantic equivalence and canonical graph fingerprints for CEMM v3.5 UOL.

Record fingerprints preserve every field. Semantic fingerprints intentionally
ignore generated local identifiers, evidence/proof identifiers, and record
revision metadata while preserving meaning-bearing schema revisions, scope,
context, time, polarity, modality, admission, ordering, and graph topology.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from .model import (
    CoordinationKind,
    FillerRef,
    IdentityStatus,
    PortFillerClass,
    QuotedLiteral,
    UOLGraph,
    canonical_data,
)


@dataclass(frozen=True, slots=True)
class EquivalenceAssessment:
    equivalent: bool
    left_fingerprint: str
    right_fingerprint: str
    left_node_count: int
    right_node_count: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Node:
    kind: str
    intrinsic: Mapping[str, Any]
    edges: tuple[tuple[str, str], ...]


def semantic_graph_fingerprint(graph: UOLGraph, *, rounds: int = 24) -> str:
    """Return an identifier-independent semantic graph fingerprint.

    The refinement is Weisfeiler-Lehman-like: each node is initially hashed from
    intrinsic semantics and then repeatedly from the hashes of labelled targets.
    This gives alpha-equivalence for variables and generated occurrence IDs while
    retaining resolved ordinary identity as a semantic distinction.
    """

    nodes = _nodes(graph)
    hashes = {key: _hash((node.kind, node.intrinsic)) for key, node in nodes.items()}
    for _ in range(max(1, rounds)):
        updated: dict[str, str] = {}
        for key, node in nodes.items():
            refined_edges = tuple(sorted(
                (label, hashes.get(target, target)) for label, target in node.edges
            ))
            updated[key] = _hash((node.kind, node.intrinsic, refined_edges))
        if updated == hashes:
            break
        hashes = updated

    root_signatures = tuple(sorted(
        (root.filler_class.value, hashes.get(_local_key(graph, root), f"external:{root.ref}"))
        for root in graph.root_refs
    ))
    unresolved_signatures = tuple(sorted(
        hashes.get(_any_local_key(graph, ref), f"external:{ref}")
        for ref in graph.unresolved_refs
    ))
    payload = {
        "nodes": sorted(hashes.values()),
        "roots": root_signatures,
        "unresolved": unresolved_signatures,
        "assumptions": sorted(graph.assumptions),
    }
    return f"uol-semantic:{_hash(payload, 64)}"


def compare_uol_graphs(left: UOLGraph, right: UOLGraph) -> EquivalenceAssessment:
    left_fp = semantic_graph_fingerprint(left)
    right_fp = semantic_graph_fingerprint(right)
    left_count = len(_nodes(left))
    right_count = len(_nodes(right))
    reasons: list[str] = []
    if left_count != right_count:
        reasons.append(f"node_count:{left_count}!={right_count}")
    if len(left.root_refs) != len(right.root_refs):
        reasons.append(f"root_count:{len(left.root_refs)}!={len(right.root_refs)}")
    if left_fp != right_fp and not reasons:
        reasons.append("semantic_structure_differs")
    return EquivalenceAssessment(
        equivalent=left_fp == right_fp,
        left_fingerprint=left_fp,
        right_fingerprint=right_fp,
        left_node_count=left_count,
        right_node_count=right_count,
        reasons=tuple(reasons),
    )


def semantically_equivalent(left: UOLGraph, right: UOLGraph) -> bool:
    return semantic_graph_fingerprint(left) == semantic_graph_fingerprint(right)


def _nodes(graph: UOLGraph) -> dict[str, _Node]:
    nodes: dict[str, _Node] = {}

    # Base referents. Specialized records below replace their base node with a
    # richer node but keep base storage/type semantics.
    for ref, referent in graph.referents.items():
        stable_identity = (
            referent.identity_status
            in {
                IdentityStatus.RESOLVED,
                IdentityStatus.DISPUTED,
                IdentityStatus.MERGED,
                IdentityStatus.SPLIT,
                IdentityStatus.RETIRED,
            }
            and referent.storage_kind.value == "ordinary"
        )
        edges: list[tuple[str, str]] = []
        for facet_ref in referent.identity_facet_refs:
            edges.append(("identity_facet", _any_local_key(graph, facet_ref)))
        for index, context_ref in enumerate(referent.context_refs):
            edges.append((f"context:{index}", _any_local_key(graph, context_ref)))
        if referent.valid_time_ref:
            edges.append(("valid_time", _any_local_key(graph, referent.valid_time_ref)))
        nodes[f"r:{ref}"] = _Node(
            "referent",
            {
                "storage_kind": referent.storage_kind.value,
                "identity_status": referent.identity_status.value,
                "type_refs": sorted(referent.type_refs),
                "scope_ref": _external_semantic_ref(graph, referent.scope_ref),
                "context_count": len(referent.context_refs),
                "stable_identity_ref": ref if stable_identity else None,
            },
            tuple(edges),
        )

    for ref, variable in graph.variables.items():
        edges = [
            ("restriction", _any_local_key(graph, item))
            for item in variable.restriction_refs
        ]
        if variable.projection_ref:
            edges.append(("projection", _any_local_key(graph, variable.projection_ref)))
        for proj_ref, proj_rev in variable.projection_candidates:
            edges.append(("projection_candidate", _any_local_key(graph, proj_ref)))
        nodes[f"v:{ref}"] = _Node(
            "variable",
            {
                "expected_schema_classes": sorted(item.value for item in variable.expected_schema_classes),
                "expected_filler_classes": sorted(item.value for item in variable.expected_filler_classes),
                "expected_type_refs": sorted(variable.expected_type_refs),
                "scope_ref": _external_semantic_ref(graph, variable.scope_ref),
                "restriction_count": len(variable.restriction_refs),
                "has_projection": bool(variable.projection_ref),
                "projection_revision": variable.projection_revision,
                "projection_candidate_count": len(variable.projection_candidates),
                "open_binding_purpose": None if variable.open_binding_purpose is None else variable.open_binding_purpose.value,
            },
            tuple(edges),
        )

    for ref, application in graph.applications.items():
        edges: list[tuple[str, str]] = []
        binding_shapes: list[tuple[Any, ...]] = []
        for binding in application.bindings:
            binding_shapes.append((
                binding.port_ref,
                len(binding.fillers),
                binding.ordered,
                binding.open_binding_purpose.value if binding.open_binding_purpose else None,
                sorted(binding.assumptions),
            ))
            for index, filler in enumerate(binding.fillers):
                order = f":{index}" if binding.ordered else ""
                if isinstance(filler, FillerRef):
                    label = f"port:{binding.port_ref}:{filler.filler_class.value}{order}"
                    edges.append((label, _local_key(graph, filler)))
                else:
                    label = f"port:{binding.port_ref}:quoted_literal{order}"
                    edges.append((label, _literal_key(filler)))
        if application.valid_time_ref:
            edges.append(("valid_time", _any_local_key(graph, application.valid_time_ref)))
        edges.append(("context", _any_local_key(graph, application.context_ref)))
        nodes[f"a:{ref}"] = _Node(
            "application",
            {
                "schema_ref": application.schema_ref,
                "schema_revision": application.schema_revision,
                "use_operation": application.use_operation.value,
                "polarity": application.polarity.value,
                "binding_shapes": sorted(binding_shapes),
                "assumptions": sorted(application.assumptions),
            },
            tuple(edges),
        )

    for ref, group in graph.coordination_groups.items():
        ordered = group.coordination_kind == CoordinationKind.LIST
        edges = tuple(
            (f"member:{index}" if ordered else "member", _local_key(graph, item))
            for index, item in enumerate(group.members)
        )
        nodes[f"g:{ref}"] = _Node(
            "coordination",
            {
                "kind": group.coordination_kind.value,
                "scope_ref": _external_semantic_ref(graph, group.scope_ref),
                "ordered": ordered,
            },
            edges,
        )

    for ref, proposition in graph.propositions.items():
        base = graph.referents.get(ref, proposition.referent)
        edges: list[tuple[str, str]] = [
            ("content", _local_key(graph, item)) for item in proposition.content_refs
        ]
        edges.extend(("modality", f"a:{item}") for item in proposition.modality_application_refs)
        edges.extend(("attribution", _any_local_key(graph, item)) for item in proposition.attribution_refs)
        edges.append(("context", _any_local_key(graph, proposition.context_ref)))
        if proposition.valid_time_ref:
            edges.append(("valid_time", _any_local_key(graph, proposition.valid_time_ref)))
        nodes[f"r:{ref}"] = _Node(
            "proposition",
            {
                "storage_kind": base.storage_kind.value,
                "identity_status": base.identity_status.value,
                "type_refs": sorted(base.type_refs),
                "polarity": proposition.polarity.value,
                "content_count": len(proposition.content_refs),
            },
            tuple(edges),
        )

    for ref, claim in graph.claims.items():
        base = graph.referents.get(ref, claim.referent)
        edges: list[tuple[str, str]] = [
            ("claimant", _any_local_key(graph, claim.claimant_ref)),
            ("proposition", f"r:{claim.proposition_ref}"),
            ("source_context", _any_local_key(graph, claim.source_context_ref)),
            ("reported_context", _any_local_key(graph, claim.reported_context_ref)),
        ]
        edges.extend(("audience", _any_local_key(graph, item)) for item in claim.audience_refs)
        edges.extend(("evidence_offered", _any_local_key(graph, item)) for item in claim.evidence_offered_refs)
        if claim.time_ref:
            edges.append(("time", _any_local_key(graph, claim.time_ref)))
        if claim.certainty_expression_ref:
            edges.append(("certainty_expression", _any_local_key(graph, claim.certainty_expression_ref)))
        nodes[f"r:{ref}"] = _Node(
            "claim_occurrence",
            {
                "storage_kind": base.storage_kind.value,
                "type_refs": sorted(base.type_refs),
                "claim_force": claim.claim_force.value,
                "audience_count": len(claim.audience_refs),
            },
            tuple(edges),
        )

    for ref, event in graph.events.items():
        base = graph.referents.get(ref, event.referent)
        edges: list[tuple[str, str]] = [
            ("participants", f"a:{event.participant_application_ref}"),
            ("context", _any_local_key(graph, event.context_ref)),
        ]
        edges.extend(("cause", _any_local_key(graph, item)) for item in event.cause_refs)
        edges.extend(("result", _any_local_key(graph, item)) for item in event.result_refs)
        if event.time_ref:
            edges.append(("time", _any_local_key(graph, event.time_ref)))
        if event.place_ref:
            edges.append(("place", _any_local_key(graph, event.place_ref)))
        nodes[f"r:{ref}"] = _Node(
            "event_occurrence",
            {
                "storage_kind": base.storage_kind.value,
                "type_refs": sorted(base.type_refs),
                "event_schema_ref": event.event_schema_ref,
                "event_schema_revision": event.event_schema_revision,
                "occurrence_status": event.occurrence_status.value,
                # Admission evidence identity is provenance, but its presence is
                # semantically required before transition authorization.
                "has_admission": bool(event.admission_refs),
            },
            tuple(edges),
        )

    for relation in graph.scope_relations:
        nodes[f"s:{relation.scope_relation_ref}"] = _Node(
            "scope_relation",
            {"scope_kind": relation.scope_kind.value, "order": relation.order},
            (
                ("operator", f"a:{relation.operator_application_ref}"),
                ("scoped", _local_key(graph, relation.scoped_ref)),
            ),
        )

    for delta in graph.state_deltas:
        edges: list[tuple[str, str]] = [
            ("trigger", _any_local_key(graph, delta.trigger_ref)),
            ("holder", f"r:{delta.holder_ref}"),
            ("effective_time", _any_local_key(graph, delta.effective_time_ref)),
        ]
        if delta.magnitude_ref:
            edges.append(("magnitude", _any_local_key(graph, delta.magnitude_ref)))
        if delta.duration_ref:
            edges.append(("duration", _any_local_key(graph, delta.duration_ref)))
        nodes[f"sd:{delta.delta_ref}"] = _Node(
            "state_delta",
            {
                "dimension_ref": delta.dimension_ref,
                "dimension_revision": delta.dimension_revision,
                "operation": delta.operation.value,
                "context_ref": _external_semantic_ref(graph, delta.context_ref),
                "from_value_ref": delta.from_value_ref,
                "from_value_revision": delta.from_value_revision,
                "to_value_ref": delta.to_value_ref,
                "to_value_revision": delta.to_value_revision,
            },
            tuple(edges),
        )

    for delta in graph.capability_deltas:
        nodes[f"cd:{delta.delta_ref}"] = _Node(
            "capability_delta",
            {
                "action_schema_ref": delta.action_schema_ref,
                "action_schema_revision": delta.action_schema_revision,
                "prior_status": delta.prior_status.value,
                "new_status": delta.new_status.value,
                "context_ref": _external_semantic_ref(graph, delta.context_ref),
                "dependency_ref": delta.dependency_ref,
            },
            (
                ("trigger", _any_local_key(graph, delta.trigger_ref)),
                ("holder", f"r:{delta.holder_ref}"),
                ("effective_time", _any_local_key(graph, delta.effective_time_ref)),
            ),
        )

    for item in graph.impact_assessments:
        edges: list[tuple[str, str]] = [
            ("source", _any_local_key(graph, item.source_event_or_state_ref)),
            ("affected", f"r:{item.affected_ref}"),
            ("stakeholder", f"r:{item.stakeholder_ref}"),
        ]
        if item.magnitude_ref:
            edges.append(("magnitude", _any_local_key(graph, item.magnitude_ref)))
        if item.duration_ref:
            edges.append(("duration", _any_local_key(graph, item.duration_ref)))
        if item.importance_ref:
            edges.append(("importance", _any_local_key(graph, item.importance_ref)))
        nodes[f"ia:{item.assessment_ref}"] = _Node(
            "impact_assessment",
            {
                "affected_facet_refs": sorted(item.affected_facet_refs),
                "direction": item.direction.value,
                "valence": item.valence.value,
                "context_ref": _external_semantic_ref(graph, item.context_ref),
                "reversibility": item.reversibility.value,
            },
            tuple(edges),
        )

    for item in graph.importance_assessments:
        edges: list[tuple[str, str]] = [
            ("subject", _any_local_key(graph, item.subject_ref)),
            ("stakeholder", f"r:{item.stakeholder_ref}"),
        ]
        if item.valid_time_ref:
            edges.append(("valid_time", _any_local_key(graph, item.valid_time_ref)))
        nodes[f"im:{item.assessment_ref}"] = _Node(
            "importance_assessment",
            {
                "score": item.score,
                "importance_class": item.importance_class.value,
                "context_ref": _external_semantic_ref(graph, item.context_ref),
                "reasons": sorted(item.reasons),
            },
            tuple(edges),
        )

    return nodes


def _local_key(graph: UOLGraph, filler: FillerRef) -> str:
    prefixes = {
        PortFillerClass.REFERENT: "r",
        PortFillerClass.SEMANTIC_APPLICATION: "a",
        PortFillerClass.SEMANTIC_VARIABLE: "v",
        PortFillerClass.COORDINATION_GROUP: "g",
    }
    return f"{prefixes[filler.filler_class]}:{filler.ref}"


def _any_local_key(graph: UOLGraph, ref: str) -> str:
    if ref in graph.referents or ref in graph.propositions or ref in graph.events or ref in graph.claims:
        return f"r:{ref}"
    if ref in graph.applications:
        return f"a:{ref}"
    if ref in graph.variables:
        return f"v:{ref}"
    if ref in graph.coordination_groups:
        return f"g:{ref}"
    if any(item.scope_relation_ref == ref for item in graph.scope_relations):
        return f"s:{ref}"
    if any(item.delta_ref == ref for item in graph.state_deltas):
        return f"sd:{ref}"
    if any(item.delta_ref == ref for item in graph.capability_deltas):
        return f"cd:{ref}"
    if any(item.assessment_ref == ref for item in graph.impact_assessments):
        return f"ia:{ref}"
    if any(item.assessment_ref == ref for item in graph.importance_assessments):
        return f"im:{ref}"
    return f"external:{ref}"


def _external_semantic_ref(graph: UOLGraph, ref: str) -> str:
    local = _any_local_key(graph, ref)
    return local if not local.startswith("external:") else ref


def _literal_key(value: QuotedLiteral) -> str:
    return f"literal:{_hash((value.surface, value.language_tag), 32)}"


def _hash(value: Any, length: int = 32) -> str:
    payload = json.dumps(
        canonical_data(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]
