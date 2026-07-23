from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from cemm.v350.composition.deterministic_v351 import (
    DeterministicAttractorStabilizer,
    DeterministicCSIRComposer,
    DeterministicMeaningDynamics,
)
from cemm.v350.csir import (
    CURRENT_KERNEL_ABI, CSIRCandidate, CSIRGraph, SemanticTerm, SemanticVariable,
    TermKind, exact_fingerprint, semantic_fingerprint,
)
from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351, SemanticDefinition
from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.runtime_abi import CSIRCandidateSet


class _Language:
    def registry(self, *, snapshot=None):
        return SimpleNamespace()


class _Repositories:
    language = _Language()


class _Store:
    repositories = _Repositories()
    def __init__(self, generation): self.generation = generation
    @contextmanager
    def snapshot(self): yield SimpleNamespace(read_generation=self.generation)
    def assert_snapshot(self, snapshot): return None


def _semantic_snapshot():
    pin = ExactAuthorityPin("semantic_definition", "test", "definition:atom", 1, "sha:def")
    term = SemanticTerm("atom", TermKind.LITERAL, literal_value="same-semantic-atom")
    definition = SemanticDefinition(pin, CSIRGraph(terms=(term,), root_refs=(term.node_ref,)))
    snapshot = AuthoritySnapshotV351(1, "authority:1", semantic_definitions=(definition,))
    return snapshot, definition


def test_deterministic_baseline_preserves_exact_classes_and_partial_open_variables():
    variable = SemanticVariable("open", open_purpose="query")
    graph = CSIRGraph(variables=(variable,), root_refs=(variable.node_ref,))
    candidate = CSIRCandidate(
        "candidate:1", graph, semantic_fingerprint(graph), exact_fingerprint(graph),
        1, "authority:1", CURRENT_KERNEL_ABI.fingerprint, prior_score=0.5,
    )
    candidate_set = CSIRCandidateSet(
        "set:1", (candidate,), 1, "authority:1", CURRENT_KERNEL_ABI.fingerprint, (), (),
    )
    semantic_snapshot = AuthoritySnapshotV351(1, "authority:1")
    dynamics = DeterministicMeaningDynamics()
    activation, trace = dynamics.run(
        csir_candidates=candidate_set, authority_snapshot=SimpleNamespace(),
        semantic_authority_snapshot_v351=semantic_snapshot, dynamics_parameters=(),
        read_generation=SimpleNamespace(), budgets=SimpleNamespace(),
    )
    result = DeterministicAttractorStabilizer().stabilize(
        activation_graph=activation, activation_trace=trace,
        authority_snapshot=SimpleNamespace(), semantic_authority_snapshot_v351=semantic_snapshot,
        budgets=SimpleNamespace(),
    )
    assert result.attractors[0].semantic_fingerprint == semantic_fingerprint(graph)
    assert result.partial_meaning is not None
    assert result.open_variables == (variable.node_ref,)
