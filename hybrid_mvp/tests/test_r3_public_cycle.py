"""Minimal behavioral successors for frozen R3 rewrite obligations.

Simulation exercises the R3-owned post-VERIFY kernel canary. Unknown lexical
grounding remains an R2 predecessor regression rather than R3 cognition.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.proposal_context import ModeSlot, ProposalContext, ResidualEvidence

__cemm_test_inventory__ = {'tests/test_r3_public_cycle.py::test_simulate_cycle_emits_no_effect_and_preserves_world_revision': {'activation_phase': 'R3',
                                                                                                     'assertion_ref': 'assertion:simulation-public-cycle-does-not-mutate',
                                                                                                     'contributes_to_rewrite_refs': ['rewrite_obligation:667dbd3b551a4a4a1fa34eeb'],
                                                                                                     'diagnostic_role': 'phase',
                                                                                                     'introduced_by_task': 'R3-Self-Close',
                                                                                                     'source_ast_sha256': 'c24b3075385ad40eaff36a70d7ddeb7d4f786ad410442fda3bc9d45c33df0752'},
 'tests/test_r3_public_cycle.py::test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation': {'activation_phase': 'R3',
                                                                                                               'assertion_ref': 'assertion:unknown-surface-public-cycle-is-safe',
                                                                                                               'contributes_to_rewrite_refs': ['rewrite_obligation:a5d394543db7da318941a99f'],
                                                                                                               'diagnostic_role': 'phase',
                                                                                                               'introduced_by_task': 'R3-Self-Close',
                                                                                                               'source_ast_sha256': '6baa1e39a874ceca96101d0406676739d2de3ce17c12ae69149736afa6daaa27'}}

ROOT = Path(__file__).resolve().parents[1]


def _canary_runner():
    path = ROOT / "scripts" / "run_r3_canaries.py"
    spec = importlib.util.spec_from_file_location("r3_boundary_canaries", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_simulate_cycle_emits_no_effect_and_preserves_world_revision(tmp_path) -> None:
    rows = _canary_runner().execute_canaries(ROOT, tmp_path / "canary", cases_path=None)
    row = next(item for item in rows if item["semantic_mode"] == "SIMULATE")
    assert row["effect_kind"] == "NoEffectReceipt"
    assert row["world_revision_delta"] == 0
    assert row["effect_revision_delta"] > 0
    assert row["response_meaning_ref"].startswith("response_meaning:")


def test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation(
    form_pack, form_pack_hash, linked_authority, designation_store,
) -> None:
    config = RuntimeConfig.release()
    resolver = FormResolver(form_pack, config)
    grounder = Grounder(
        authority=linked_authority, config=config, form_pack=form_pack,
        form_pack_hash=form_pack_hash, designation_store=designation_store,
    )
    lattice = resolver.resolve("zorbulate")
    pin = RevisionPin(linked_authority.generation, 0, 0, 0, 0, BootstrapProposer.model_identity)
    grounding = grounder.ground_lattice(lattice, pin)
    assert grounding.created_refs == ()
    assert grounding.designations == ()
    assert grounding.unresolved and grounding.unresolved[0].resolved_ref is None
    mode = ModeSlot.create(mode="OBSERVE", source_unit_refs=(), construction_ref=None, requested_effect="admission")
    residuals = tuple(
        ResidualEvidence.create(
            source_unit_ref=unit.unit_ref, contribution_kind="anchor", critical=True,
            reason="unresolved open-class predecessor evidence",
        )
        for unit in lattice.units
    )
    context = ProposalContext.create(
        orientation_ref="orientation:r3-rewrite-frontier",
        evidence_packet_ref=grounding.evidence_packet_ref,
        form_lattice_ref=grounding.form_lattice_ref, grounding_ref=grounding.grounding_ref,
        designation_slots=(), contribution_slots=(), mode_slots=(mode,), application_frames=(),
        reference_slots=(), scope_slots=(), expression_link_slots=(), variable_slots=(),
        transition_slots=(), residual_evidence=residuals,
        context_refs=("turn:r3-rewrite-frontier",),
        source_unit_refs=tuple(unit.unit_ref for unit in lattice.units),
        source_unit_spans=tuple((unit.unit_ref, unit.source_start, unit.source_end) for unit in lattice.units),
        revision_pin=pin, config=config,
    )
    proposal = BootstrapProposer(config).propose(context)
    assert proposal.status == "abstained"
    assert proposal.abstention_code == "proposal:critical_residual"
    assert proposal.candidates == ()
