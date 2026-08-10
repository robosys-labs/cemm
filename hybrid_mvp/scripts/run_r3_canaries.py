#!/usr/bin/env python3
"""Execute deterministic post-VERIFY R3 activation canaries.

The admission seam starts from canonical VerifiedMeaning plus authenticated
predecessor context. It deliberately does not invoke ORIENT/PROPOSE/VERIFY and
never invokes R5 realization. The R3 structural gate separately proves the
exact typed R5 handoff.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import Orientation, SemanticMode
from cemm_authoritative_hybrid.expressions import (
    GroundedReference, RoleBinding, SemanticApplication, SemanticExpression,
    VerifiedMeaning,
)
from cemm_authoritative_hybrid.forms import EvidenceItem, EvidencePacket, FormResolver
from cemm_authoritative_hybrid.persistence import open_stores
from cemm_authoritative_hybrid.proposal_context import ModeSlot, ProposalContext, ResidualEvidence
from cemm_authoritative_hybrid.r3_effects import AdapterRegistry, EffectReceipt, NoEffectReceipt
from cemm_authoritative_hybrid.r3_kernel import R3Kernel
from cemm_authoritative_hybrid.r3_persistence import begin_turn, focus_snapshot, obligation_snapshot, session_snapshot
from cemm_authoritative_hybrid.situation import SituationInputBundle

MODEL_IDENTITY = "r3-boundary-canary"
CASES = (
    ("observe", SemanticMode.OBSERVE),
    ("query", SemanticMode.QUERY),
    ("request", SemanticMode.REQUEST),
    ("simulate", SemanticMode.SIMULATE),
)


def _relation_expression() -> SemanticExpression:
    return SemanticExpression.create(
        applications=(SemanticApplication(
            application_ref="application:relation", operator="op:relation",
            predicate_ref="rel:likes",
            roles=(
                RoleBinding("role:subject", GroundedReference("entity:alice")),
                RoleBinding("role:object", GroundedReference("entity:book")),
            ),
        ),),
        root_refs=("application:relation",),
    )


def _state_event_expression() -> SemanticExpression:
    return SemanticExpression.create(
        applications=(SemanticApplication(
            application_ref="application:set-state", operator="op:event",
            predicate_ref="event:set_state",
            roles=(
                RoleBinding("role:actor", GroundedReference("participant:system")),
                RoleBinding("role:target", GroundedReference("entity:lamp")),
                RoleBinding("role:dimension", GroundedReference("dim:power")),
                RoleBinding("role:value", GroundedReference("value:on")),
            ),
        ),),
        root_refs=("application:set-state",),
    )


def _expression(mode: SemanticMode) -> SemanticExpression:
    return _state_event_expression() if mode in {SemanticMode.REQUEST, SemanticMode.SIMULATE} else _relation_expression()


def _grounding_refs(expression: SemanticExpression) -> tuple[str, ...]:
    refs = {
        binding.filler.target_ref
        for app in expression.applications
        for binding in (*app.roles, *app.qualifiers)
        if isinstance(binding.filler, GroundedReference)
    }
    if not refs:
        raise ValueError("R3 canary expression lacks grounded refs")
    return tuple(sorted(refs))


def _permission_refs(authority) -> tuple[str, ...]:
    refs: list[str] = []
    for row in authority.permissions:
        if type(row) in {tuple, list} and len(row) == 3 and row[0] == "participant:system":
            ref = row[1]
            if type(ref) is str and ref and ref not in refs:
                refs.append(ref)
    return tuple(refs)


def _case(root: Path, store_path: Path, case_ref: str, mode: SemanticMode) -> dict[str, object]:
    authority = AuthorityLinker().link_path(root / "data" / "authority" / "manifest.json")
    config = RuntimeConfig.release()
    form_pack = json.loads((root / "data" / "languages" / "en" / "forms.json").read_text(encoding="utf-8"))
    resolver = FormResolver(form_pack, config)
    stores = open_stores(store_path, authority_generation=authority.generation, model_identity=MODEL_IDENTITY)
    adapters = AdapterRegistry()
    try:
        session_ref = f"session:r3-canary:{case_ref}"
        turn = begin_turn(stores, session_ref)
        session = session_snapshot(stores, session_ref)
        focus = focus_snapshot(stores, session_ref, maximum=config.max_orientation_alternatives)
        obligations = obligation_snapshot(stores, session_ref, maximum=config.max_orientation_alternatives)
        pin = stores.revision_pin()

        source_text = "."
        item = EvidenceItem.create(
            source="text", content=source_text,
            source_ref=stable_ref("r3_canary_source", {"case_ref": case_ref}),
            provenance_refs=(), adapter_receipt_ref=None,
        )
        evidence = EvidencePacket.create(items=(item,), source_text=source_text, form_pack_hash=resolver.form_pack_hash)
        lattice = resolver.resolve_evidence(evidence)
        if len(lattice.units) != 1:
            raise ValueError("R3 canary sentinel must resolve to one source unit")
        unit = lattice.units[0]
        residual = ResidualEvidence.create(
            source_unit_ref=unit.unit_ref, contribution_kind="discourse", critical=False,
            reason="reviewed noncritical orthographic predecessor evidence",
        )
        requested_effect = {
            SemanticMode.OBSERVE: "admission", SemanticMode.QUERY: "query",
            SemanticMode.REQUEST: "effect", SemanticMode.SIMULATE: "simulation",
        }[mode]
        mode_slot = ModeSlot.create(
            mode=mode.value, source_unit_refs=(), construction_ref=None,
            requested_effect=requested_effect,
        )
        participants = tuple(sorted(authority.by_kind("participant")))
        if not {"participant:user", "participant:system"} <= set(participants):
            raise ValueError("R3 canary authority lacks required participants")
        capabilities = tuple(authority.capabilities.get("participant:system", ()))
        permissions = _permission_refs(authority)
        turn_ref = str(turn["turn_ref"])
        event_refs = (stable_ref("session_event", {"session_ref": session_ref}), turn_ref)
        orientation = Orientation.create(
            session_ref=session_ref, turn_ref=turn_ref, source_text=source_text,
            mode=mode, participant_frame="participant:user", temporal_frame="time:now",
            participants=participants, active_turn_ref=turn_ref, event_refs=event_refs,
            focus_refs=tuple(focus.get("focus_refs", ())),
            obligation_refs=tuple(obligations.get("obligation_refs", ())),
            capability_summary=capabilities, permission_summary=permissions,
            budgets={"input_tokens": config.max_input_tokens}, scanned_atom_count=0,
            index_probes=("r3-canary:post-verify-boundary",),
            visited_refs=tuple(dict.fromkeys((*participants, *event_refs))), revision_pin=pin,
        )
        context = ProposalContext.create(
            orientation_ref=orientation.orientation_ref,
            evidence_packet_ref=evidence.packet_ref, form_lattice_ref=lattice.lattice_ref,
            grounding_ref=stable_ref("r3_canary_grounding", {"case_ref": case_ref}),
            designation_slots=(), contribution_slots=(), mode_slots=(mode_slot,),
            application_frames=(), reference_slots=(), scope_slots=(),
            expression_link_slots=(), variable_slots=(), transition_slots=(),
            residual_evidence=(residual,), context_refs=(turn_ref,),
            source_unit_refs=(unit.unit_ref,),
            source_unit_spans=((unit.unit_ref, unit.source_start, unit.source_end),),
            revision_pin=pin, config=config,
        )
        expression = _expression(mode)
        meaning = VerifiedMeaning.create(
            program_ref=stable_ref("r3_canary_program", {"case_ref": case_ref}),
            expression=expression, grounding_refs=_grounding_refs(expression),
            coverage_receipt_ref=stable_ref("r3_canary_coverage", {"case_ref": case_ref}),
            compilation_proof_ref=stable_ref("r3_canary_compilation", {"case_ref": case_ref}),
            verification_receipt_ref=stable_ref("r3_canary_verification", {"case_ref": case_ref}),
            revision_pin=pin,
        )
        inputs = SituationInputBundle.create(
            evidence=evidence, turn_index=int(turn["turn_index"]),
            session_phase_ref=str(session["session_phase_ref"]),
            focus_snapshot_ref=str(focus["snapshot_ref"]), focus_refs=tuple(focus.get("focus_refs", ())),
            obligation_snapshot_ref=str(obligations["snapshot_ref"]),
            obligation_refs=tuple(obligations.get("obligation_refs", ())),
            permission_snapshot_ref=stable_ref("permission_snapshot", {"permission_refs": list(permissions), "revision_pin": pin.as_dict()}),
            resource_snapshot_ref=stable_ref("resource_snapshot", {"resource_refs": [], "revision_pin": pin.as_dict()}),
            resource_refs=(),
            adapter_snapshot_ref=stable_ref("adapter_snapshot", {"adapter_refs": [], "revision_pin": pin.as_dict()}),
            adapter_refs=(), evidence_policy_refs=("policy:evidence:text_attributed",),
        )
        artifacts = R3Kernel(
            authority=authority, stores=stores, config=config, adapters=adapters, resource_refs=(),
        ).run(meaning=meaning, orientation=orientation, context=context, situation_inputs=inputs)
        if artifacts.situation.mode is not mode:
            raise ValueError(f"{case_ref}: R3 situation mode mismatch")
        if artifacts.evaluation.decision.situation.situation_ref != artifacts.situation.situation_ref:
            raise ValueError(f"{case_ref}: R3 decision does not bind situation")
        if type(artifacts.effect) not in {EffectReceipt, NoEffectReceipt}:
            raise TypeError(f"{case_ref}: R3 emitted non-canonical effect outcome")
        if artifacts.response_meaning.decision_ref != artifacts.evaluation.decision.decision_ref:
            raise ValueError(f"{case_ref}: response does not bind Decision")
        response_wire = artifacts.response_meaning.as_dict()
        if "surface" in response_wire or "surface_text" in response_wire:
            raise ValueError(f"{case_ref}: R3 crossed into R5 surface realization")
        input_pin = artifacts.input_revision_pin
        output_pin = artifacts.output_revision_pin
        if input_pin != pin or output_pin != stores.revision_pin():
            raise ValueError(f"{case_ref}: R3 revision lineage is inconsistent")
        world_delta = output_pin.world_revision - input_pin.world_revision
        effect_delta = output_pin.effect_revision - input_pin.effect_revision
        if world_delta < 0 or effect_delta <= 0:
            raise ValueError(f"{case_ref}: R3 revision deltas are invalid")
        effect = artifacts.effect
        return {
            "case_ref": case_ref, "semantic_mode": mode.value,
            "verified_meaning_ref": meaning.verified_meaning_ref,
            "expression_ref": meaning.expression.expression_ref,
            "situation_ref": artifacts.situation.situation_ref,
            "evaluation_ref": artifacts.evaluation.evaluation_ref,
            "decision_ref": artifacts.evaluation.decision.decision_ref,
            "decision_status": artifacts.evaluation.decision.status.value,
            "decision_action": artifacts.evaluation.decision.action.value,
            "effect_receipt_ref": effect.receipt_ref, "effect_kind": type(effect).__name__,
            "effect_status_or_reason": effect.status.value if type(effect) is EffectReceipt else effect.reason.value,
            "response_meaning_ref": artifacts.response_meaning.response_meaning_ref,
            "r3_artifacts_ref": artifacts.artifacts_ref,
            "input_revision_pin": input_pin.as_dict(), "final_revision_pin": output_pin.as_dict(),
            "world_revision_delta": world_delta, "effect_revision_delta": effect_delta,
        }
    finally:
        stores.close()


def execute_canaries(root: Path, store: Path, *, cases_path: Path | None = None) -> tuple[dict[str, object], ...]:
    if cases_path is not None:
        raise ValueError("R3 admission canaries use the fixed reviewed post-VERIFY case set")
    project = root.resolve(strict=True)
    base = store.resolve()
    base.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_ref, mode in CASES:
        case_store = base.parent / f"{base.name}-{case_ref}.sqlite3"
        case_store.unlink(missing_ok=True)
        rows.append(_case(project, case_store, case_ref, mode))
    if {row["semantic_mode"] for row in rows} != {mode.value for _, mode in CASES}:
        raise ValueError("R3 canaries did not cover the exact four-mode set")
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = execute_canaries(args.root, args.store, cases_path=None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"schema": "cemm-r3-activation-canaries-v1", "cases": list(rows)}, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
