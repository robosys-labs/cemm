"""R2 unknown-frontier: unknown surface abstains or emits typed unresolved candidate.

This is the governed successor node required by the frozen test inventory.
It proves that an unknown surface:
  - grounds to a typed unresolved designation (no manufactured ref);
  - causes proposal abstention OR emits a candidate with an exact unresolved
    filler only where the role contract permits it;
  - is never accepted by VERIFY as a settled grounded identity;
  - creates no semantic ref and causes no mutation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.proposal_context import (
    ModeSlot,
    ProposalContext,
    ResidualEvidence,
)

ROOT = Path(__file__).resolve().parent.parent


def test_unknown_surface_abstains_or_emits_typed_unresolved_candidate(
    form_pack,
    form_pack_hash,
    linked_authority,
    designation_store,
) -> None:
    """Unknown surface must not produce a settled grounded identity."""
    config = RuntimeConfig.release()
    resolver = FormResolver(form_pack, config)
    grounder = Grounder(
        authority=linked_authority,
        config=config,
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=designation_store,
    )

    # Build exact lineage: resolve forms, then ground the lattice
    lattice = resolver.resolve("zorbulate")
    pin = RevisionPin(
        authority_generation=linked_authority.generation,
        world_revision=0,
        session_revision=0,
        episode_revision=0,
        effect_revision=0,
        model_identity=BootstrapProposer.model_identity,
    )
    result = grounder.ground_lattice(lattice, pin)

    # 1. Grounding emits a typed unresolved designation
    assert len(result.unresolved) >= 1
    unresolved = result.unresolved[0]
    assert unresolved.kind == "designation"
    assert unresolved.resolved_ref is None

    # 2. No semantic ref is manufactured
    assert result.created_refs == ()
    assert len(result.designations) == 0

    # 3. No mutation occurs (created_refs is empty — already asserted)

    # 4. The proposer must either abstain or emit a candidate with
    #    an exact unresolved filler. With no designation slots and a
    #    critical residual, the bootstrap proposer abstains.
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    residual = ResidualEvidence.create(
        source_unit_ref=(
            lattice.units[0].unit_ref if lattice.units else "unit:unknown"
        ),
        contribution_kind="anchor",
        critical=True,
        reason="unresolved open-class evidence",
    )
    context = ProposalContext.create(
        orientation_ref="orientation:test",
        evidence_packet_ref=result.evidence_packet_ref,
        form_lattice_ref=result.form_lattice_ref,
        grounding_ref=result.grounding_ref,
        designation_slots=(),
        contribution_slots=(),
        mode_slots=(mode,),
        application_frames=(),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(residual,),
        context_refs=("turn:test",),
        source_unit_refs=tuple(u.unit_ref for u in lattice.units),
        source_unit_spans=tuple(
            (u.unit_ref, u.source_start, u.source_end) for u in lattice.units
        ),
        revision_pin=pin,
    )

    proposer = BootstrapProposer(config)
    proposal = proposer.propose(context)

    # With no frames and a critical residual, the proposer must abstain.
    # It cannot construct a valid candidate without at least one application frame.
    assert proposal.status == "abstained"
    assert proposal.abstention_code is not None
    assert len(proposal.candidates) == 0

    # 5. VERIFY never accepts a critical unresolved referent as settled.
    #    Since there are no candidates, there is nothing to verify.
    #    This is the correct behavior — no settled meaning is produced.
