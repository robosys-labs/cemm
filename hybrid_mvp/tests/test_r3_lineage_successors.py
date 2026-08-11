"""Exact R3 successors for predecessor contracts whose semantics changed at R3."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import cemm_authoritative_hybrid.bootstrap as bootstrap_module
import cemm_authoritative_hybrid.cycle as cycle_module
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.contributions import ContributionExpander
from cemm_authoritative_hybrid.cycle import CycleStatus, PhaseDisposition, SemanticPhase
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.persistence import RevisionPin, memory_stores
from cemm_authoritative_hybrid.proposal_context import ProposalContextBuilder
from cemm_authoritative_hybrid.r3_cycle import CycleResult

ROOT = Path(__file__).parents[1]


def test_r3_effect_revision_dimensions_preserve_fixed_identity_and_allow_persisted_learning() -> None:
    """Supersede the R1 EFFECT-pin contract with the complete R3 invariant."""

    source = RevisionPin("authority:generation-1", 2, 2, 2, 2, "model:test")
    persisted = replace(source, session_revision=3, effect_revision=3)
    material = cycle_module._PhaseMaterial(
        SemanticPhase.EFFECT,
        ("decision:r3",),
        ("effect:r3",),
        source,
        persisted,
        PhaseDisposition.NO_EFFECT,
        (),
        {},
    )
    assert material.output_revision_pin.session_revision > source.session_revision
    assert material.output_revision_pin.effect_revision > source.effect_revision
    assert material.output_revision_pin.world_revision == source.world_revision

    invalid_outputs = (
        replace(persisted, authority_generation="authority:other"),
        replace(persisted, episode_revision=3),
        replace(persisted, model_identity="model:other"),
        replace(persisted, world_revision=3),
        replace(persisted, session_revision=1),
        replace(persisted, effect_revision=1),
    )
    for output in invalid_outputs:
        with pytest.raises(ValueError, match="EFFECT|revision|NO_EFFECT"):
            cycle_module._PhaseMaterial(
                SemanticPhase.EFFECT,
                ("decision:r3",),
                ("effect:r3",),
                source,
                output,
                PhaseDisposition.NO_EFFECT,
                (),
                {},
            )

    assert not hasattr(CycleResult, "_from_canonical")


def test_r3_composition_root_runs_each_orient_transform_once_and_continues_past_verify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve the one-pass R1 ORIENT invariant on the complete R3 path."""

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
        store_path=ROOT / "unused-r3-lineage-store",
    )
    try:
        result = runtime.process("session:r3-lineage", "hello", trace=True)
    finally:
        runtime.stores.close()

    assert type(result) is CycleResult
    assert counts == {"form": 1, "ground": 1, "expand": 1, "context": 1}
    assert result.status is CycleStatus.PARTIAL
    assert result.proposal.status == "candidates"
    assert result.verification.status == "selected"
    assert result.evaluation is not None
    assert result.effect_receipt is not None
    assert result.response_meaning is not None
    assert result.realization_receipt is None
    assert result.gap_receipt is not None
    assert result.gap_receipt.missing_contract_refs == ("contract:r5:realize_surface",)
    assert tuple(row.phase for row in result.phase_material) == (
        SemanticPhase.ORIENT,
        SemanticPhase.PROPOSE,
        SemanticPhase.VERIFY,
        SemanticPhase.EVALUATE,
        SemanticPhase.EFFECT,
        SemanticPhase.REALIZE,
    )


__cemm_test_inventory__ = {'tests/test_r3_lineage_successors.py::test_r3_effect_revision_dimensions_preserve_fixed_identity_and_allow_persisted_learning': {'activation_phase': 'R3',
                                                                                                                                  'assertion_ref': 'assertion:r1-c1-effect-pin-dimensions',
                                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                                  'introduced_by_task': 'R3-Lineage-Closeout',
                                                                                                                                  'owner_ref': 'effect-learning-response',
                                                                                                                                  'source_ast_sha256': '16d051edacf8f2be2e4a4a0c4422e71fe72d1e62d4d385efac0e44e367ff2312',
                                                                                                                                  'supersedes_node_id': 'tests/test_phase_receipts.py::test_c1_effect_pin_changes_are_dimension_constrained_and_no_unchecked_builder_exists'},
 'tests/test_r3_lineage_successors.py::test_r3_composition_root_runs_each_orient_transform_once_and_continues_past_verify': {'activation_phase': 'R3',
                                                                                                                             'assertion_ref': 'assertion:r1-one-orient-transform-pass',
                                                                                                                             'diagnostic_role': 'phase',
                                                                                                                             'introduced_by_task': 'R3-Lineage-Closeout',
                                                                                                                             'source_ast_sha256': '2fd87bb35f1fef86655bd2370556fb5dca1a886a72c97f4e2c0c2192790e6cae',
                                                                                                                             'supersedes_node_id': 'tests/test_r1_phase_integration.py::test_r1_composition_root_runs_each_orient_transform_once'}}
