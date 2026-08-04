"""R1 composition-root integration contracts."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import cemm_authoritative_hybrid.bootstrap as bootstrap_module
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.contributions import ContributionExpander
from cemm_authoritative_hybrid.cycle import CycleResult, CycleStatus, SemanticPhase
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.gaps import MissingOwner
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.proposal_context import ProposalContextBuilder


ROOT = Path(__file__).parents[1]


def test_r1_composition_root_runs_each_orient_transform_once(monkeypatch):
    counts = {"form": 0, "ground": 0, "expand": 0, "context": 0}
    originals = {
        "form": FormResolver.resolve_evidence,
        "ground": Grounder.ground_lattice,
        "expand": ContributionExpander.expand,
        "context": ProposalContextBuilder.build,
    }

    def form(self, packet):
        counts["form"] += 1
        return originals["form"](self, packet)

    def ground(self, lattice, revision_pin):
        counts["ground"] += 1
        return originals["ground"](self, lattice, revision_pin)

    def expand(self, grounding_result, form_lattice):
        counts["expand"] += 1
        return originals["expand"](self, grounding_result, form_lattice)

    def context(self, **kwargs):
        counts["context"] += 1
        return originals["context"](self, **kwargs)

    monkeypatch.setattr(FormResolver, "resolve_evidence", form)
    monkeypatch.setattr(Grounder, "ground_lattice", ground)
    monkeypatch.setattr(ContributionExpander, "expand", expand)
    monkeypatch.setattr(ProposalContextBuilder, "build", context)
    monkeypatch.setattr(
        bootstrap_module,
        "open_stores",
        lambda _path, *, authority_generation, model_identity: memory_stores(
            authority_generation=authority_generation,
            model_identity=model_identity,
        ),
    )

    runtime = load_runtime(
        ROOT,
        profile="development",
        store_path=ROOT / "unused-in-memory-store",
    )
    try:
        result = runtime.process("session:r1-integration", "hello", trace=True)
    finally:
        runtime.stores.close()

    assert type(result) is CycleResult
    assert counts == {"form": 1, "ground": 1, "expand": 1, "context": 1}
    assert result.status is CycleStatus.UNSUPPORTED
    assert result.verification.status == "abstained"
    assert tuple(row.phase for row in result.phase_material) == (
        SemanticPhase.ORIENT,
        SemanticPhase.PROPOSE,
        SemanticPhase.VERIFY,
    )
    assert result.response_meaning is None
    assert result.gap_receipt.status == "proposal_abstained"


def test_r1_bootstrap_requires_profile_and_fails_later_profiles_closed():
    signature = inspect.signature(load_runtime)
    assert "proposal_fixture" not in signature.parameters
    assert signature.parameters["profile"].default is inspect.Parameter.empty
    with pytest.raises(MissingOwner, match="program_abi_2_proposal_owner"):
        load_runtime(Path("does-not-exist"), profile="neural")
    with pytest.raises(MissingOwner, match="program_abi_2_proposal_owner"):
        load_runtime(Path("does-not-exist"), profile="release")


__cemm_test_inventory__ = {
    "tests/test_r1_phase_integration.py::test_r1_composition_root_runs_each_orient_transform_once": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-one-orient-transform-pass",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "0b947de0b37a1038e17d4cfb2af830088c08eadccd0f197225da5d2e6d09e167",
    },
    "tests/test_r1_phase_integration.py::test_r1_bootstrap_requires_profile_and_fails_later_profiles_closed": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-bootstrap-fails-later-profiles-closed",
        "diagnostic_role": "phase",
        "introduced_by_task": "R1-Task-9",
        "source_ast_sha256": "1808f0fa44cc4a95f54f6b8ef899c591bb9928d710df4e1e2f0441a849f07047",
    },
}
