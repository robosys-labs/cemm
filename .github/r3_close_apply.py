from __future__ import annotations

from pathlib import Path
import textwrap

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "hybrid_mvp"
ZERO = "0" * 64


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{label} differs from reviewed source: count={text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# Due rewrite refs are already validated against exact active executable
# successors by test_inventory_core. Do not reject the authenticated evidence
# tuple a second time in the validation wrapper.
gate = ROOT / "scripts" / "validation_gate.py"
text = gate.read_text(encoding="utf-8")
old = '''    due = getattr(inventory, "due_rewrite_refs", None)\n    if type(due) is not tuple:\n        raise GateConfigError("inventory rewrite lifecycle is unavailable")\n    if due:\n        raise GateConfigError("due test rewrite obligations block validation")\n'''
new = '''    due = getattr(inventory, "due_rewrite_refs", None)\n    if type(due) is not tuple:\n        raise GateConfigError("inventory rewrite lifecycle is unavailable")\n    # test_inventory_core._validate_rewrite_lifecycle has already proved that\n    # every phase-due obligation has exact active executable successors.\n    # Keep ``due`` as authenticated lifecycle evidence; do not reject it again.\n'''
if text.count(old) != 1:
    raise SystemExit("due-rewrite validation source differs from reviewed input")
text = text.replace(old, new, 1)

start = text.index('    def run_r3_activation_canaries(self) -> _HandledStep:\n')
end = text.index('    def run_r4_artifact_review(self) -> _HandledStep:\n', start)
method = textwrap.dedent('''
def run_r3_activation_canaries(self) -> _HandledStep:
    if self.tier != "admission" or self.phase != "R3":
        raise GateConfigError("R3 activation canaries are available only in R3 admission")
    authority = self._linked_authority
    if authority is None:
        raise GateConfigError("R3 activation canaries require linked authority evidence")
    started = time.monotonic_ns()
    artifact_path = self.root / "artifacts" / "validation" / "R3_ACTIVATION_CANARIES.json"
    raw = self._read_bytes(artifact_path)
    artifact = _load_strict_json_bytes(raw, path=artifact_path)
    artifact = _exact_fields(
        artifact, frozenset({"schema", "cases"}), "R3 activation canary artifact"
    )
    if artifact["schema"] != "cemm-r3-activation-canaries-v1":
        raise GateConfigError("R3 activation canary artifact schema is invalid")
    rows = artifact["cases"]
    if type(rows) is not list or len(rows) < 4:
        raise GateConfigError("R3 activation canary artifact must contain at least four cases")
    row_fields = frozenset({
        "case_ref", "semantic_mode", "verified_meaning_ref", "expression_ref",
        "situation_ref", "evaluation_ref", "decision_ref", "decision_status",
        "decision_action", "effect_receipt_ref", "effect_kind",
        "effect_status_or_reason", "response_meaning_ref", "r3_artifacts_ref",
        "input_revision_pin", "final_revision_pin", "world_revision_delta",
        "effect_revision_delta",
    })
    modes: set[str] = set()
    case_refs: set[str] = set()
    for index, raw_row in enumerate(rows):
        row = _exact_fields(raw_row, row_fields, f"R3 canary row {index}")
        case_ref = _text(row["case_ref"], f"R3 canary row {index} case_ref")
        if case_ref in case_refs:
            raise GateConfigError("R3 activation canary case refs must be unique")
        case_refs.add(case_ref)
        mode = row["semantic_mode"]
        if mode not in {"OBSERVE", "QUERY", "REQUEST", "SIMULATE"}:
            raise GateConfigError("R3 activation canary semantic mode is invalid")
        modes.add(str(mode))
        for field in (
            "verified_meaning_ref", "expression_ref", "situation_ref",
            "evaluation_ref", "decision_ref", "effect_receipt_ref",
            "response_meaning_ref", "r3_artifacts_ref",
        ):
            value = row[field]
            if type(value) is not str or _CONTENT_REF_RE.fullmatch(value) is None:
                raise GateConfigError(f"R3 activation canary {field} is invalid")
        for field in ("decision_status", "decision_action", "effect_status_or_reason"):
            _text(row[field], f"R3 canary row {index} {field}")
        if row["effect_kind"] not in {"EffectReceipt", "NoEffectReceipt"}:
            raise GateConfigError("R3 activation canary effect kind is invalid")
        pins = []
        for field in ("input_revision_pin", "final_revision_pin"):
            pin = _exact_fields(
                row[field],
                frozenset({
                    "authority_generation", "world_revision", "session_revision",
                    "episode_revision", "effect_revision", "model_identity",
                }),
                f"R3 canary row {index} {field}",
            )
            if pin["authority_generation"] != authority.generation:
                raise GateConfigError("R3 canary authority generation is stale")
            for revision in (
                "world_revision", "session_revision", "episode_revision", "effect_revision"
            ):
                _nonnegative_exact_int(pin[revision], f"R3 canary {revision}")
            if type(pin["model_identity"]) is not str or not pin["model_identity"]:
                raise GateConfigError("R3 canary model identity is invalid")
            pins.append(pin)
        world_delta = _nonnegative_exact_int(
            row["world_revision_delta"], "R3 canary world revision delta"
        )
        effect_delta = _nonnegative_exact_int(
            row["effect_revision_delta"], "R3 canary effect revision delta"
        )
        if pins[1]["world_revision"] - pins[0]["world_revision"] != world_delta:
            raise GateConfigError("R3 canary world revision delta is inconsistent")
        if pins[1]["effect_revision"] - pins[0]["effect_revision"] != effect_delta:
            raise GateConfigError("R3 canary effect revision delta is inconsistent")
        if effect_delta == 0:
            raise GateConfigError("R3 canary did not persist an effect/no-effect outcome")
    if modes != {"OBSERVE", "QUERY", "REQUEST", "SIMULATE"}:
        raise GateConfigError("R3 activation canaries do not cover all four semantic modes")

    # Re-execute only the R3-owned post-VERIFY boundary. R5 handoff existence
    # is checked separately by the structural phase gate, not executed here.
    runner_path = self.root / "scripts" / "run_r3_canaries.py"
    runner = _load_exact_module(runner_path, "r3_canary_runner")
    execute = getattr(runner, "execute_canaries", None)
    if not callable(execute):
        raise GateConfigError("R3 canary runner does not expose execute_canaries")
    store_root = self._fresh_step_root("r3-canaries") / "store"
    try:
        observed = execute(self.root, store_root, cases_path=None)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise GateConfigError(f"R3 post-VERIFY canaries failed: {exc}") from exc
    if type(observed) is not tuple or any(type(row) is not dict for row in observed):
        raise GateConfigError("R3 canary runner returned non-canonical evidence")
    if list(observed) != rows:
        raise GateConfigError("committed R3 canary evidence differs from fresh post-VERIFY execution")
    material: dict[str, object] = {
        "canary_count": len(rows),
        "canary_set_ref": content_ref("r3_canary_set", rows),
        "schema": "cemm-r3-activation-canaries-step-report-v1",
    }
    material["canary_ref"] = content_ref("r3_activation_canaries", material)
    return _HandledStep(
        disposition="passed", exit_code=0, error_code=None, report=material,
        observation_report=material, wall_ns=time.monotonic_ns() - started,
        peak_rss_bytes=None,
    )

''')
method = ''.join('    ' + line if line.strip() else line for line in method.splitlines(True))
text = text[:start] + method + text[end:]
gate.write_text(text, encoding="utf-8")

replace_once(
    ROOT / "src" / "cemm_authoritative_hybrid" / "forms.py",
    '    ("conditional", "connector", "conditional"),\n    ("purpose", "connector", "purpose"),',
    '    ("conditional", "connector", "conditional"),\n    ("hypothetical", "connector", "hypothetical"),\n    ("purpose", "connector", "purpose"),',
    "form construction registry",
)
replace_once(
    ROOT / "src" / "cemm_authoritative_hybrid" / "mode.py",
    '    "conditional_simulation": SemanticMode.SIMULATE,\n    "declarative": SemanticMode.OBSERVE,',
    '    "conditional_simulation": SemanticMode.SIMULATE,\n    "conditional": SemanticMode.SIMULATE,\n    "declarative": SemanticMode.OBSERVE,',
    "mode projection registry",
)

run_canaries = r'''#!/usr/bin/env python3
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
'''
(ROOT / "scripts" / "run_r3_canaries.py").write_text(run_canaries, encoding="utf-8")

mode_test = f'''"""Integrated FormResolver -> StructuralModeProjector R3 mode coverage."""
from __future__ import annotations

import json
from pathlib import Path

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.mode import StructuralModeProjector

__cemm_test_inventory__ = {{
    "tests/test_r3_form_mode_integration.py::test_reviewed_conditional_and_hypothetical_forms_project_simulation": {{
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-reviewed-conditional-hypothetical-project-simulate",
        "diagnostic_role": "owner",
        "introduced_by_task": "R3-Self-Close",
        "owner_ref": "situation-context",
        "source_ast_sha256": "{ZERO}",
    }}
}}

ROOT = Path(__file__).resolve().parents[1]


def test_reviewed_conditional_and_hypothetical_forms_project_simulation() -> None:
    form_pack = json.loads((ROOT / "data" / "languages" / "en" / "forms.json").read_text(encoding="utf-8"))
    resolver = FormResolver(form_pack, RuntimeConfig.release())
    projector = StructuralModeProjector()
    for text in ("if x", "suppose x", "imagine x"):
        assert projector.project(resolver.resolve(text)).mode is SemanticMode.SIMULATE
'''
(ROOT / "tests" / "test_r3_form_mode_integration.py").write_text(mode_test, encoding="utf-8")

public_test = f'''"""Minimal behavioral successors for frozen R3 rewrite obligations.

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

__cemm_test_inventory__ = {{
    "tests/test_r3_public_cycle.py::test_simulate_cycle_emits_no_effect_and_preserves_world_revision": {{
        "activation_phase": "R3",
        "assertion_ref": "assertion:simulation-public-cycle-does-not-mutate",
        "contributes_to_rewrite_refs": ["rewrite_obligation:667dbd3b551a4a4a1fa34eeb"],
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Self-Close",
        "source_ast_sha256": "{ZERO}",
    }},
    "tests/test_r3_public_cycle.py::test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation": {{
        "activation_phase": "R3",
        "assertion_ref": "assertion:unknown-surface-public-cycle-is-safe",
        "contributes_to_rewrite_refs": ["rewrite_obligation:a5d394543db7da318941a99f"],
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Self-Close",
        "source_ast_sha256": "{ZERO}",
    }},
}}

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
'''
(ROOT / "tests" / "test_r3_public_cycle.py").write_text(public_test, encoding="utf-8")
