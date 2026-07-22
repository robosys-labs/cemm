from types import SimpleNamespace
from dataclasses import replace

import pytest

from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351
from cemm.v350.csir.canonical import semantic_fingerprint as csir_semantic_fingerprint
from cemm.v350.csir.model import CSIRGraph, CSIRNodeKind, CSIRRef, SemanticTerm, TermKind
from cemm.v350.dynamics.model_v351 import (
    ActivationNodeKind, CompetitionGroup, EdgePolarity, HardConstraintMask, HardMaskReason,
    MessageFamily, REQUIRED_MESSAGE_FAMILIES, SemanticActivationNode, TypedActivationPayload,
    TypedMessageEdge,
)
from cemm.v350.dynamics.parameters_v351 import (
    CORE_PARAMETER_FAMILY, MESSAGE_PARAMETER_PREFIX, compile_parameter_set,
    compile_reviewed_phase13_parameter_artifacts,
)
from cemm.v350.dynamics.solver_v351 import RecurrentSemanticDynamicsV351
from cemm.v350.dynamics.stabilizer_v351 import RecurrentAttractorStabilizerV351
from cemm.v350.runtime_abi import ActivationGraph, ActivationTrace


def _graph(ref: str, value: str) -> CSIRGraph:
    term = SemanticTerm(ref, TermKind.LITERAL, literal_value=value)
    return CSIRGraph(terms=(term,), root_refs=(CSIRRef(CSIRNodeKind.TERM, ref),))


def _parameter_context():
    artifacts = compile_reviewed_phase13_parameter_artifacts()
    snapshot = AuthoritySnapshotV351(1, "authority:test", dynamics_parameters=artifacts)
    return artifacts, snapshot, compile_parameter_set(artifacts, authority_snapshot=snapshot)


def test_reviewed_parameter_inventory_is_exact_and_covers_every_message_family():
    artifacts, snapshot, params = _parameter_context()
    assert {item.parameter_family for item in artifacts} == {
        CORE_PARAMETER_FAMILY,
        *(MESSAGE_PARAMETER_PREFIX + family.value for family in REQUIRED_MESSAGE_FAMILIES),
    }
    assert set(dict(params.family_gains)) == set(REQUIRED_MESSAGE_FAMILIES)
    assert tuple(pin.key for pin in params.parameter_pins) == tuple(
        item.parameter_pin.key for item in sorted(artifacts, key=lambda item: item.parameter_family)
    )

    with pytest.raises(ValueError):
        compile_parameter_set(artifacts[:-1], authority_snapshot=snapshot)


def test_hard_constraint_mask_is_not_overridden_by_recurrence_and_budget_remains_partial():
    _, _, params = _parameter_context()
    g1, g2 = _graph("term:a", "a"), _graph("term:b", "b")
    n1 = SemanticActivationNode("node:a", ActivationNodeKind.SEMANTIC_CLASS, csir_semantic_fingerprint(g1), "c1", .55, .55)
    n2 = SemanticActivationNode("node:b", ActivationNodeKind.SEMANTIC_CLASS, csir_semantic_fingerprint(g2), "c2", .95, .95)
    edge = TypedMessageEdge("edge:a-b", MessageFamily.CONSTRUCTION, "node:a", "node:b", EdgePolarity.EXCITATORY, 10.0)
    mask = HardConstraintMask("mask:b", "node:b", False, HardMaskReason.HARD_CONSTRAINT, ("proof:reject-b",))
    group = CompetitionGroup("group:ab", ("node:a", "node:b"), ("candidate-set:test",))
    payload = TypedActivationPayload(
        "payload:test", (n1, n2), (edge,), (mask,), (group,), params,
        (("c1", "node:a"), ("c2", "node:b")),
        (("c1", g1), ("c2", g2)),
        (("c1", 0.0), ("c2", 0.0)),
        (("c1", ("e1",)), ("c2", ("e2",))),
        (("c1", ("d1",)), ("c2", ("d2",))),
        (), (), family_edge_counts=tuple((family, int(family == MessageFamily.CONSTRUCTION)) for family in REQUIRED_MESSAGE_FAMILIES),
    )
    solved, status, _ = RecurrentSemanticDynamicsV351()._iterate(payload, budgets=SimpleNamespace(inference_steps=1))
    solved_nodes = solved.node_map()
    assert solved_nodes["node:b"].current_activation == 0.0
    assert status.value == "budget_exhausted_partial"


def test_stabilizer_preserves_absolute_support_instead_of_manufacturing_single_candidate_certainty():
    artifacts, snapshot, params = _parameter_context()
    graph = _graph("term:weak", "weak")
    node = SemanticActivationNode(
        "node:weak", ActivationNodeKind.SEMANTIC_CLASS, csir_semantic_fingerprint(graph), "c1", .20, .20
    )
    payload = TypedActivationPayload(
        "payload:weak", (node,), (), (), (), params,
        (("c1", "node:weak"),), (("c1", graph),), (("c1", -1.4),),
        (("c1", ("e1",)),), (("c1", ("derivation:1",)),), (), (),
        family_edge_counts=tuple((family, 0) for family in REQUIRED_MESSAGE_FAMILIES),
    )
    activation = ActivationGraph(
        "activation:weak", payload, 1, "authority:test",
        semantic_authority_snapshot_fingerprint=snapshot.snapshot_fingerprint,
        dynamics_parameter_pins=tuple(item.parameter_pin for item in sorted(artifacts, key=lambda x: x.parameter_family)),
    )
    trace = ActivationTrace("trace:weak", 1, .1, ("convergence-status:budget_exhausted_partial",))
    result = RecurrentAttractorStabilizerV351().stabilize(
        activation_graph=activation, activation_trace=trace, authority_snapshot=None,
        semantic_authority_snapshot_v351=snapshot, budgets=SimpleNamespace(inference_steps=1),
    )
    assert len(result.attractors) == 1
    assert result.attractors[0].support == pytest.approx(.20)
    assert result.attractors[0].support != 1.0
    assert result.partial_meaning == graph
    assert not result.convergence.converged
