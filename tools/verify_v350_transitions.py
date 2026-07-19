#!/usr/bin/env python3
"""Audit and competence-test Phase-11 generic event transitions."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cemm.v350.data import DeterministicSQLiteCompiler, SourcePackageLoader
from cemm.v350.schema.model import (
    ActionSchema, Cardinality, CompetenceHook, EventSchema, LocalPortSchema,
    ReferentTypeSchema, SchemaLifecycleStatus, StateDimensionSchema, StateValueSchema,
    StorageKind, UseOperation, UseProfile,
)
from cemm.v350.schema.registry import SchemaRegistry
from cemm.v350.storage import (
    AdmissionDecision, AssignmentStatus, EpistemicAdmissionRecord, EvidenceRecord,
    KnowledgeStatus, RecordKind, StateAssignment, StoredRecord,
)
from cemm.v350.transitions import (
    CapabilityDependencyEngine, CapabilityDependencyRecord, ConditionOperator,
    EventAdmissionGate, StateConditionSpec, StateEffectSpec, StateTimelineProjector,
    TransitionContractCompiler, TransitionContractRecord, TransitionPreviewEngine,
)
from cemm.v350.transitions.contract import TransitionPackageAuditor, load_transition_contract
from cemm.v350.uol.model import (
    ApplicationBinding, CapabilityStatus, ChangeOperation, EventOccurrence, FillerRef,
    IdentityStatus, OccurrenceStatus, Polarity, PortFillerClass, PropositionReferent,
    Referent, SemanticApplication,
)


def _profile(**values: str) -> UseProfile:
    return UseProfile.from_mapping(values)


def _stored(kind, ref, payload, revision=1):
    return StoredRecord(kind, ref, revision, payload, f"content:{ref}:{revision}", f"record:{ref}:{revision}", "competence", 1)


class _Resolver:
    def __init__(self, *items): self.items = list(items)
    def resolve(self, kind, ref, revision=None):
        matches = [i for i in self.items if i.record_kind == kind and i.record_ref == ref and (revision is None or i.revision == revision)]
        return max(matches, key=lambda i: i.revision) if matches else None
    def records(self, kind): return tuple(i for i in self.items if i.record_kind == kind)
    def resolve_any(self, ref): return tuple(i for i in self.items if i.record_ref == ref)


def _fixture(*, polarity=Polarity.POSITIVE, status=OccurrenceStatus.ADMITTED, include_state=True):
    type_schema = ReferentTypeSchema(
        "type:competence:holder", "competence_holder", lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        storage_kinds=frozenset({StorageKind.ORDINARY}),
        use_profile=_profile(mention="allow", ground="allow", compose="allow", query="allow"),
    )
    contract_ref = "transition-contract:competence:generic"
    event_schema = EventSchema(
        "event:competence:generic", "competence_generic_event",
        local_ports=(LocalPortSchema("affected", accepted_type_refs=(type_schema.schema_ref,), cardinality=Cardinality(1,1)),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE, transition_contract_refs=(contract_ref,),
        use_profile=_profile(compose="allow", query="allow", transition="allow"),
        competence_hooks=(CompetenceHook("competence:phase11:event", UseOperation.TRANSITION),),
    )
    dimension = StateDimensionSchema(
        "state:competence:mode", "competence_mode", holder_type_refs=(type_schema.schema_ref,),
        value_schema_refs=("state-value:competence:a", "state-value:competence:b"),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE, transition_contract_refs=(contract_ref,),
        use_profile=_profile(compose="allow", query="allow", transition="allow"),
        competence_hooks=(CompetenceHook("competence:phase11:state", UseOperation.TRANSITION),),
    )
    a = StateValueSchema("state-value:competence:a", "competence_a", dimension_ref=dimension.schema_ref,
                         lifecycle_status=SchemaLifecycleStatus.ACTIVE, use_profile=_profile(compose="allow", query="allow"))
    b = StateValueSchema("state-value:competence:b", "competence_b", dimension_ref=dimension.schema_ref,
                         lifecycle_status=SchemaLifecycleStatus.ACTIVE, use_profile=_profile(compose="allow", query="allow"))
    action = ActionSchema(
        "action:competence:generic", "competence_action",
        local_ports=(LocalPortSchema("actor", accepted_type_refs=(type_schema.schema_ref,), cardinality=Cardinality(1,1)),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE, use_profile=_profile(compose="allow", query="allow"),
    )
    schemas = SchemaRegistry((type_schema, event_schema, dimension, a, b, action))
    contract = TransitionContractRecord(
        contract_ref, event_schema.schema_ref, 1,
        (StateConditionSpec("condition:competence:a", "affected", dimension.schema_ref, 1, ConditionOperator.EQUALS, a.schema_ref, 1),),
        (StateEffectSpec("effect:competence:b", "affected", dimension.schema_ref, 1, ChangeOperation.SET,
                         from_value_ref=a.schema_ref, from_value_revision=1, to_value_ref=b.schema_ref, to_value_revision=1),),
        ("evidence:competence:contract",), SchemaLifecycleStatus.ACTIVE,
    )
    dependency = CapabilityDependencyRecord(
        "capability-dependency:competence", (type_schema.schema_ref,), action.schema_ref, 1,
        (StateConditionSpec("condition:competence:cap", "holder", dimension.schema_ref, 1, ConditionOperator.EQUALS, b.schema_ref, 1),),
        CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE, CapabilityStatus.UNKNOWN,
        ("evidence:competence:dependency",), SchemaLifecycleStatus.ACTIVE,
    )
    subject = Referent("referent:competence:subject", StorageKind.ORDINARY, IdentityStatus.RESOLVED,
                       type_refs=(type_schema.schema_ref,), context_refs=("actual",), provenance_refs=("evidence:competence:subject",))
    source_app = SemanticApplication(
        "application:competence:source", event_schema.schema_ref, 1,
        (ApplicationBinding("affected", (FillerRef(PortFillerClass.REFERENT, subject.referent_ref),)),),
        "context:competence:attributed", evidence_refs=("evidence:competence:claim",),
    )
    target_app = replace(source_app, application_ref="application:competence:target", context_ref="actual")
    proposition_ref = "referent:competence:proposition"
    proposition = PropositionReferent(
        Referent(proposition_ref, StorageKind.PROPOSITION, IdentityStatus.CANDIDATE,
                 context_refs=("context:competence:attributed",), provenance_refs=("evidence:competence:claim",)),
        (FillerRef(PortFillerClass.SEMANTIC_APPLICATION, source_app.application_ref),),
        "context:competence:attributed", polarity=polarity, evidence_refs=("evidence:competence:claim",),
    )
    admission = EpistemicAdmissionRecord(
        "admission:competence", proposition_ref, "context:competence:attributed", "actual",
        AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 1.0, ("source:competence",),
        ("evidence:competence:claim",), ("proof:competence:admission",), "policy:competence",
        source_assessment_pins=(("source-assessment:competence",1),), authorization_ref="authorization:competence",
    )
    event = EventOccurrence(
        Referent("referent:competence:event", StorageKind.EVENT_OCCURRENCE, IdentityStatus.RESOLVED,
                 context_refs=("actual",), provenance_refs=("evidence:competence:event",)),
        event_schema.schema_ref, 1, target_app.application_ref, "actual", occurrence_status=status,
        admission_refs=(admission.admission_ref,),
    )
    assignment = StateAssignment(
        "assignment:competence", subject.referent_ref, dimension.schema_ref, 1, a.schema_ref, 1,
        AssignmentStatus.ACTIVE, "actual", 1.0, valid_from="2026-01-01T00:00:00Z",
        evidence_refs=("evidence:competence:state",),
    )
    evidence_refs = ("evidence:competence:contract","evidence:competence:dependency","evidence:competence:subject",
                     "evidence:competence:claim","evidence:competence:event","evidence:competence:state")
    items = [
        _stored(RecordKind.REFERENT, subject.referent_ref, subject),
        _stored(RecordKind.SEMANTIC_APPLICATION, source_app.application_ref, source_app),
        _stored(RecordKind.SEMANTIC_APPLICATION, target_app.application_ref, target_app),
        _stored(RecordKind.PROPOSITION, proposition_ref, proposition),
        _stored(RecordKind.EPISTEMIC_ADMISSION, admission.admission_ref, admission),
        _stored(RecordKind.EVENT_OCCURRENCE, event.event_ref, event),
    ]
    if include_state: items.append(_stored(RecordKind.STATE_ASSIGNMENT, assignment.assignment_ref, assignment))
    items.extend(_stored(RecordKind.EVIDENCE, ref, EvidenceRecord(ref,"source:competence",1.0,f"lineage:{ref}",context_ref="actual")) for ref in evidence_refs)
    return schemas, _Resolver(*items), contract, dependency, event, subject, a, b


def _execute(case, source_root: Path, runtime_root: Path):
    op = case["operation"]
    if op == "no_domain_transition_seed":
        records = SourcePackageLoader(source_root).load()
        count = sum(i.record_kind in {RecordKind.TRANSITION_CONTRACT, RecordKind.CAPABILITY_DEPENDENCY} for i in records)
        assert count == 0
        return {"seed_count": count}
    if op == "no_named_kernel_authority":
        contract = load_transition_contract(source_root / "transition_contract.json")
        audit = TransitionPackageAuditor(contract).audit(source_root, runtime_root=runtime_root)
        assert not any("named_kernel_semantic_refs" in item for item in audit.issues)
        return {"named_kernel_refs": 0}
    polarity = Polarity.NEGATIVE if op == "negative_proposition_block" else Polarity.POSITIVE
    status = OccurrenceStatus(case.get("status", OccurrenceStatus.ADMITTED.value))
    include_state = op != "unknown_frontier"
    schemas, resolver, contract, dependency, event, subject, a, b = _fixture(polarity=polarity, status=status, include_state=include_state)
    if op == "contract_compile":
        result = TransitionContractCompiler(schemas).compile(contract)
        return {"ports": sorted(result.trigger_port_refs)}
    if op == "admission_context_bridge":
        result = EventAdmissionGate(resolver).assess(event); assert result.admitted
        return {"admission_pins": result.admission_pins}
    preview = TransitionPreviewEngine(schemas, resolver).preview(event, contract, effective_time_ref="2026-07-18T12:00:00Z")
    if op in {"negative_proposition_block", "nontransitioning_status_block"}:
        assert not preview.authorized and not preview.state_deltas
        return {"blocked": preview.blocked_reasons}
    if op == "unknown_frontier":
        assert not preview.authorized and preview.frontiers
        return {"frontiers": [item.reason for item in preview.frontiers]}
    if op == "admitted_preview":
        assert preview.authorized and len(preview.state_deltas) == 1
        return {"delta_count": 1}
    if op == "revision_pinned_proof":
        assert preview.proof and preview.proof.admission_pins == (("admission:competence",1),)
        assert preview.proof.input_assignment_pins == (("assignment:competence",1),)
        return {"admission_pins": preview.proof.admission_pins, "assignment_pins": preview.proof.input_assignment_pins}
    projection = StateTimelineProjector(schemas, resolver).project(preview.state_deltas[0])
    if op == "immutable_timeline":
        assert len(projection.mutations) == 2
        return {"mutation_count": len(projection.mutations)}
    if op == "capability_dependency":
        projected = CapabilityDependencyEngine(schemas, resolver).evaluate(
            dependency, holder_ref=subject.referent_ref, context_ref="actual",
            effective_time_ref="2026-07-18T12:00:00Z", trigger_ref=event.event_ref,
            proof_refs=(preview.proof.proof_ref,), state_projections=(projection,),
        )
        assert projected and projected.delta.new_status == CapabilityStatus.AVAILABLE
        return {"status": projected.delta.new_status.value}
    raise AssertionError(f"unknown competence operation: {op}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1] / "cemm" / "data" / "v350"))
    parser.add_argument("--report")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    runtime_root = Path(__file__).resolve().parents[1] / "cemm" / "v350"
    contract = load_transition_contract(source / "transition_contract.json")
    audit = TransitionPackageAuditor(contract).audit(source, runtime_root=runtime_root)
    with tempfile.TemporaryDirectory() as directory:
        a = DeterministicSQLiteCompiler().compile(source, Path(directory)/"a.sqlite", make_read_only=False)
        b = DeterministicSQLiteCompiler().compile(source, Path(directory)/"b.sqlite", make_read_only=False)
        deterministic = a.output_path.read_bytes() == b.output_path.read_bytes()
        cases = [json.loads(line) for line in (source/"competence"/"transitions.jsonl").read_text().splitlines() if line.strip()]
        results = [{"case_ref": case["case_ref"], **_execute(case, source, runtime_root)} for case in cases]
        report = {
            "valid": audit.valid and deterministic and len(results) == len(contract.required_competence_case_refs),
            "contract_ref": contract.contract_ref,
            "repository_base_commit": contract.repository_base_commit,
            "audit": {"valid": audit.valid, "issues": audit.issues, "manifest_fingerprint": audit.manifest_fingerprint},
            "compilation": {"byte_deterministic": deterministic, "record_count": a.record_count,
                            "manifest_fingerprint": a.manifest_fingerprint, "record_set_fingerprint": a.record_set_fingerprint,
                            "boot_fingerprint": a.boot_fingerprint, "byte_size": a.byte_size},
            "competence": {"passed": len(results), "cases": results},
        }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.report: Path(args.report).write_text(rendered+"\n", encoding="utf-8")
    print(rendered)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
