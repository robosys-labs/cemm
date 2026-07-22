from __future__ import annotations

from types import SimpleNamespace

from cemm.v350.csir import (
    CURRENT_KERNEL_ABI, CSIRCandidateFragment, CSIRGraph, CSIRNodeKind, CSIRRef,
    ExactAuthorityPin, ExactCSIRCompiler, PortBinding, SemanticApplication, SemanticTerm, TermKind,
)
from cemm.v350.orchestration import StageExecutionStatus
from cemm.v350.runtime_abi import CSIRCandidateSet
from cemm.v350.runtime_v351 import RuntimeServices, V351RuntimeCoordinator


def graph():
    predicate = ExactAuthorityPin("schema", "test", "p", 1, "p-hash")
    port = ExactAuthorityPin("port", "test", "arg", 1, "port-hash")
    term = SemanticTerm("x", TermKind.REFERENT, identity_ref="r:1")
    app = SemanticApplication("a", predicate)
    return CSIRGraph(
        terms=(term,), applications=(app,),
        bindings=(PortBinding("b", "a", port, (term.node_ref,)),),
        root_refs=(app.node_ref,),
    )


def coordinator(service=None):
    value = object.__new__(V351RuntimeCoordinator)
    value.services = RuntimeServices(csir_compiler=service)
    value.exact_csir_compiler = ExactCSIRCompiler()
    return value


def cycle(closure):
    return SimpleNamespace(
        cycle_ref="cycle:test", context_ref="conversation", permission_ref="conversation",
        artifacts={
            "kernel_semantic_abi": CURRENT_KERNEL_ABI,
            "evidence_lattice": object(), "grounding_candidates": object(),
            "referent_projections": {}, "state_space_projections": {},
            "semantic_closure_candidates": tuple(closure),
            "authority_snapshot": object(), "read_generation": object(),
        },
    )


def capability():
    return SimpleNamespace(stage=5, authority_generation=3, authority_fingerprint="authority:3")


def test_stage5_never_falls_back_to_opaque_uol_or_legacy_closure_objects():
    result = coordinator().stage_05_compile_candidates_to_csir(cycle((object(),)), capability())
    assert result.status is StageExecutionStatus.DEFERRED
    assert "csir_candidates" not in result.artifacts
    assert "frontier:csir:opaque-candidate-input" in result.frontier_refs


def test_stage5_kernel_recomputes_candidate_identity_from_exact_fragment():
    fragment = CSIRCandidateFragment("f", graph(), closure_proof_refs=("closure:exact",))
    result = coordinator().stage_05_compile_candidates_to_csir(cycle((fragment,)), capability())
    assert result.status is StageExecutionStatus.PERFORMED
    candidate_set = result.artifacts["csir_candidates"]
    assert isinstance(candidate_set, CSIRCandidateSet)
    assert candidate_set.kernel_abi_fingerprint == CURRENT_KERNEL_ABI.fingerprint
    assert candidate_set.authority_generation == 3
    assert len(candidate_set.candidates) == 1


def test_signed_candidate_provider_is_still_revalidated_by_kernel():
    class Provider:
        def compile(self, **_kwargs):
            return {"candidate_fragments": (CSIRCandidateFragment("f", graph(), closure_proof_refs=("closure:exact",)),)}
    result = coordinator(Provider()).stage_05_compile_candidates_to_csir(cycle(()), capability())
    assert result.status is StageExecutionStatus.PERFORMED
    candidate = result.artifacts["csir_candidates"].candidates[0]
    assert candidate.kernel_abi_fingerprint == CURRENT_KERNEL_ABI.fingerprint
