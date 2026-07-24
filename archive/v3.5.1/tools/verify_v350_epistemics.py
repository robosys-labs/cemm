#!/usr/bin/env python3
"""Audit and competence-test Phase-10 attributed claims and epistemic admission."""
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

from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.epistemics import (
    AdmissionPolicy, AdmissionRequest, AdmissionThresholds,
    ClaimHistoryProjector, ClaimOccurrenceCompiler, EpistemicAdmissionEngine,
    EpistemicPatchPlanner, FourStateTruthProjector, SourceAssessment,
)
from cemm.v350.epistemics.claims import ClaimCompilationError
from cemm.v350.epistemics.contract import EpistemicPackageAuditor, load_epistemic_contract
from cemm.v350.schema.model import EventSchema, PortFillerClass, StorageKind, UseOperation
from cemm.v350.storage import (
    AdmissionDecision, ClaimHistoryAction, ClaimHistoryRecord, ClaimRecord,
    EpistemicAdmissionRecord, KnowledgeStatus, RecordKind, SemanticStore,
)
from cemm.v350.uol.model import (
    ApplicationBinding, ClaimForce, EventOccurrence, FillerRef, IdentityStatus,
    OccurrenceStatus, PropositionReferent, Referent, SemanticApplication, UOLGraph,
)


def _source(ref: str, *, reliability=0.95, authority=0.95, access=0.95, bias=0.05):
    return SourceAssessment(ref, authority, reliability, access, bias, (f"evidence:{ref}:assessment",))


def _policy():
    return AdmissionPolicy("policy:phase10:verified", AdmissionThresholds(0.5, 0.5, 0.5, 0.5, 0.5, 1))


def _request(*, status=KnowledgeStatus.SUPPORTED, source="referent:self", authorization="authorization:phase10"):
    return AdmissionRequest(
        request_ref=f"request:phase10:{status.value}:{source}", proposition_ref="referent:phase10:proposition",
        source_context_ref="context:phase10:attributed", target_context_ref="actual",
        requested_truth_status=status, source_refs=(source,),
        evidence_confidences=((f"evidence:{source}:claim", 0.95),),
        proof_refs=(f"proof:{source}:admission",), source_assessments=(_source(source),),
        policy_ref=_policy().policy_ref, authorization_ref=authorization,
    )


def _claim_graph(store: SemanticStore, *, same_context=False):
    registry = store.repositories.schemas.registry()
    candidates = []
    for item in registry.iter_schemas():
        if not isinstance(item, EventSchema) or not item.use_profile.permits(UseOperation.COMPOSE):
            continue
        content_ports = tuple(
            port for port in item.local_ports if StorageKind.PROPOSITION in port.accepted_storage_kinds
        )
        source_ports = tuple(
            port for port in item.local_ports
            if port.identity_contribution and port.cardinality.minimum > 0
            and PortFillerClass.REFERENT in port.filler_classes
            and port not in content_ports
        )
        if len(content_ports) == 1 and len(source_ports) == 1:
            candidates.append((item, source_ports[0], content_ports[0]))
    if len(candidates) != 1:
        raise AssertionError(f"expected one structurally declared claim schema, found {len(candidates)}")
    schema, source_port, content_port = candidates[0]
    other_ports = tuple(item for item in schema.local_ports if item.port_ref not in {source_port.port_ref, content_port.port_ref})
    claimant = store.repositories.referents.require("referent:self").payload
    attributed = "actual" if same_context else "context:phase10:attributed"
    content_app = SemanticApplication(application_ref="application:phase10:content", schema_ref=schema.schema_ref, schema_revision=schema.revision, use_operation=UseOperation.COMPOSE, bindings=(), context_ref=attributed, evidence_refs=("evidence:phase10:content",))
    proposition_ref = "referent:phase10:proposition"
    proposition_referent = Referent(referent_ref=proposition_ref, storage_kind=StorageKind.PROPOSITION, identity_status=IdentityStatus.CANDIDATE, context_refs=(attributed,), provenance_refs=("evidence:phase10:proposition",))
    proposition = PropositionReferent(referent=proposition_referent, content_refs=(FillerRef(PortFillerClass.SEMANTIC_APPLICATION, content_app.application_ref),), context_ref=attributed, evidence_refs=("evidence:phase10:proposition",))
    bindings = [
        ApplicationBinding(source_port.port_ref, (FillerRef(PortFillerClass.REFERENT, claimant.referent_ref),), evidence_refs=("evidence:phase10:claim",)),
        ApplicationBinding(content_port.port_ref, (FillerRef(PortFillerClass.REFERENT, proposition_ref),), evidence_refs=("evidence:phase10:claim",)),
    ]
    for port in other_ports:
        bindings.append(ApplicationBinding(port.port_ref, (FillerRef(PortFillerClass.REFERENT, claimant.referent_ref),), evidence_refs=("evidence:phase10:claim",)))
    claim_app = SemanticApplication(application_ref="application:phase10:claim", schema_ref=schema.schema_ref, schema_revision=schema.revision, use_operation=UseOperation.COMPOSE, bindings=tuple(bindings), context_ref="actual", evidence_refs=("evidence:phase10:claim",))
    event_ref = "referent:phase10:claim-event"
    event_referent = Referent(referent_ref=event_ref, storage_kind=StorageKind.EVENT_OCCURRENCE, identity_status=IdentityStatus.CANDIDATE, context_refs=("actual",), provenance_refs=("evidence:phase10:claim",))
    event = EventOccurrence(referent=event_referent, event_schema_ref=schema.schema_ref, event_schema_revision=schema.revision, participant_application_ref=claim_app.application_ref, context_ref="actual", occurrence_status=OccurrenceStatus.MENTIONED, provenance_refs=("evidence:phase10:claim",), admission_refs=())
    graph = UOLGraph(
        "uol:phase10:claim",
        referents={claimant.referent_ref: claimant, proposition_ref: proposition_referent, event_ref: event_referent},
        applications={content_app.application_ref: content_app, claim_app.application_ref: claim_app},
        propositions={proposition_ref: proposition}, events={event_ref: event},
        evidence_refs=("evidence:phase10:claim",), root_refs=(claim_app.application_ref,),
    )
    return graph, claim_app.application_ref


def _execute(case, store):
    op = case["operation"]
    engine = EpistemicAdmissionEngine()
    projector = FourStateTruthProjector()
    if op == "claim_attributed":
        graph, app = _claim_graph(store)
        compiled = ClaimOccurrenceCompiler(store).compile(graph, app, claim_force=ClaimForce.ASSERTED, commitment_strength=0.9, evidence_refs=("evidence:phase10:claim",))
        assert compiled.claim_occurrence.reported_context_ref != compiled.claim_occurrence.source_context_ref
        return {"claim_ref": compiled.claim_occurrence.claim_ref, "admission_refs": []}
    if op == "claim_same_context_rejected":
        graph, app = _claim_graph(store, same_context=True)
        try:
            ClaimOccurrenceCompiler(store).compile(graph, app, claim_force=ClaimForce.ASSERTED, commitment_strength=0.9, evidence_refs=("evidence:phase10:claim",))
        except ClaimCompilationError:
            return {"rejected": True}
        raise AssertionError("unattributed same-context claim was accepted")
    if op == "grammar_not_admission":
        req = _request(authorization=None)
        assessment = engine.assess(req, _policy())
        assert assessment.decision == AdmissionDecision.PRESERVE_ATTRIBUTED and assessment.truth_status == KnowledgeStatus.UNDETERMINED
        return {"decision": assessment.decision.value}
    if op in {"support_admission", "opposition_admission"}:
        status = KnowledgeStatus.SUPPORTED if op == "support_admission" else KnowledgeStatus.OPPOSED
        req = _request(status=status)
        record = engine.record(req, engine.assess(req, _policy()))
        source_records = engine.source_assessment_records(req)
        assert record.truth_status == status and record.proof_refs
        assert set(record.source_assessment_pins) == {(item.assessment_ref, item.revision) for item in source_records}
        return {"decision": record.decision.value, "truth_status": record.truth_status.value}
    if op == "durable_source_assessment":
        req = _request()
        assessment = engine.assess(req, _policy())
        admission = engine.record(req, assessment)
        records = engine.source_assessment_records(req)
        patch = EpistemicPatchPlanner().admission_patch(admission, source_assessments=records)
        kinds = tuple(item.record_kind.value for item in patch.operations)
        assert kinds.count(RecordKind.SOURCE_ASSESSMENT.value) == len(req.source_refs)
        assert RecordKind.EPISTEMIC_ADMISSION.value in kinds
        assert set(admission.source_assessment_pins) == {(item.assessment_ref, item.revision) for item in records}
        return {"source_assessment_pins": admission.source_assessment_pins, "record_kinds": kinds}
    if op == "source_dimension_gate":
        req = _request()
        req = replace(req, source_assessments=(_source("referent:self", reliability=0.1, authority=1.0, access=1.0, bias=0.0),))
        result = engine.assess(req, _policy())
        assert result.decision == AdmissionDecision.DEFER
        return {"failed": result.failed_requirements}
    if op == "four_state_both":
        a_req = _request(status=KnowledgeStatus.SUPPORTED, source="source:a")
        b_req = _request(status=KnowledgeStatus.OPPOSED, source="source:b")
        a = engine.record(a_req, engine.assess(a_req, _policy()))
        b = engine.record(b_req, engine.assess(b_req, _policy()))
        result = projector.assess(a.proposition_ref, "actual", (a, b))
        assert result.truth_status == KnowledgeStatus.BOTH
        return {"truth_status": result.truth_status.value}
    if op == "source_local_retraction":
        a_req = _request(source="source:a"); b_req = _request(source="source:b")
        a = engine.record(a_req, engine.assess(a_req, _policy())); b = engine.record(b_req, engine.assess(b_req, _policy()))
        retract = EpistemicAdmissionRecord("admission:retract:a", a.proposition_ref, a.source_context_ref, a.target_context_ref, AdmissionDecision.RETRACT, KnowledgeStatus.UNDETERMINED, 1.0, ("source:a",), ("evidence:retract:a",), ("proof:retract:a",), _policy().policy_ref, authorization_ref="authorization:retract:a", retracts_admission_ref=a.admission_ref)
        result = projector.assess(a.proposition_ref, "actual", (a, b, retract))
        assert result.support_admission_refs == (b.admission_ref,)
        return {"remaining": result.support_admission_refs}
    if op == "knowledge_needs_admission":
        req = _request(); admission = engine.record(req, engine.assess(req, _policy()))
        assessment = projector.assess(admission.proposition_ref, "actual", (admission,))
        knowledge = projector.project_knowledge(assessment, (admission,)).knowledge_record
        assert knowledge is not None and admission.admission_ref in knowledge.support_lineage_refs
        assert projector.project_knowledge(projector.assess(admission.proposition_ref, "actual", ()), ()).knowledge_record is None
        return {"knowledge": knowledge.knowledge_ref}
    if op == "append_only_correction":
        old = ClaimRecord("claim:old", "occ:old", "prop:old", "source:a", "actual", "reported:old", 1.0, evidence_refs=("e:old",))
        new = ClaimRecord("claim:new", "occ:new", "prop:new", "source:a", "actual", "reported:new", 1.0, evidence_refs=("e:new",))
        history = (ClaimHistoryRecord("hist:new", "claim:new", ClaimHistoryAction.CORRECT, "source:a", "actual", ("e:new",), target_claim_record_ref="claim:old"),)
        effective = ClaimHistoryProjector().effective_claims((old, new), history)
        assert [item.claim_record_ref for item in effective] == ["claim:new"]
        return {"stored_claims": 2, "effective_claims": 1}
    if op == "patch_no_state_effect":
        graph, app = _claim_graph(store)
        compiled = ClaimOccurrenceCompiler(store).compile(graph, app, claim_force=ClaimForce.ASSERTED, commitment_strength=0.9, evidence_refs=("evidence:phase10:claim",))
        kinds = {item.record_kind for item in EpistemicPatchPlanner().claim_patch(compiled).operations}
        assert RecordKind.STATE_DELTA not in kinds and RecordKind.CAPABILITY_DELTA not in kinds
        return {"record_kinds": sorted(item.value for item in kinds)}
    if op == "single_admission_not_both":
        try:
            EpistemicAdmissionRecord("admission:bad", "prop:bad", "reported", "actual", AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.BOTH, 1.0, ("source:a",), ("e:a",), ("proof:a",), _policy().policy_ref, source_assessment_pins=(("source-assessment:a", 1),))
        except ValueError:
            return {"rejected": True}
        raise AssertionError("single admission encoded BOTH")
    if op == "durable_authorization_required":
        try:
            EpistemicAdmissionRecord(
                "admission:no-auth", "prop:test", "reported", "actual",
                AdmissionDecision.ADMIT_SUPPORT, KnowledgeStatus.SUPPORTED, 1.0,
                ("source:a",), ("e:a",), ("proof:a",), _policy().policy_ref,
                source_assessment_pins=(("source-assessment:a", 1),),
            )
        except ValueError:
            return {"rejected": True}
        raise AssertionError("actual-world admission accepted without durable authorization")
    if op == "retraction_authorization_required":
        try:
            EpistemicAdmissionRecord(
                "admission:retract:no-auth", "prop:test", "reported", "actual",
                AdmissionDecision.RETRACT, KnowledgeStatus.UNDETERMINED, 1.0,
                ("source:a",), ("e:a",), ("proof:a",), _policy().policy_ref,
                retracts_admission_ref="admission:target",
            )
        except ValueError:
            return {"rejected": True}
        raise AssertionError("actual-world retraction accepted without durable authorization")
    if op == "cross_source_retraction_ignored":
        req = _request(source="source:a")
        admission = engine.record(req, engine.assess(req, _policy()))
        malicious = EpistemicAdmissionRecord(
            "admission:retract:other", admission.proposition_ref,
            admission.source_context_ref, admission.target_context_ref,
            AdmissionDecision.RETRACT, KnowledgeStatus.UNDETERMINED, 1.0,
            ("source:b",), ("evidence:retract:b",), ("proof:retract:b",),
            _policy().policy_ref, authorization_ref="authorization:retract:b",
            retracts_admission_ref=admission.admission_ref,
        )
        result = projector.assess(admission.proposition_ref, "actual", (admission, malicious))
        assert result.support_admission_refs == (admission.admission_ref,)
        return {"remaining": result.support_admission_refs}
    if op == "append_only_retraction":
        claim = ClaimRecord("claim:keep", "occ:keep", "prop:keep", "source:a", "actual", "reported:keep", 1.0, evidence_refs=("e:keep",))
        history = (ClaimHistoryRecord("hist:retract", "claim:keep", ClaimHistoryAction.RETRACT, "source:a", "actual", ("e:retract",), target_claim_record_ref="claim:keep"),)
        effective = ClaimHistoryProjector().effective_claims((claim,), history)
        assert not effective
        return {"stored_claims": 1, "effective_claims": 0}
    raise AssertionError(f"unknown operation: {op}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="cemm/data/v350")
    parser.add_argument("--report")
    args = parser.parse_args()
    root = Path(args.source).resolve()
    contract = load_epistemic_contract(root / "epistemic_contract.json")
    audit = EpistemicPackageAuditor(contract).audit(root)
    with tempfile.TemporaryDirectory(prefix="cemm-v350-phase10-") as directory:
        first = DeterministicSQLiteCompiler().compile(root, Path(directory) / "a.sqlite", make_read_only=False)
        second = DeterministicSQLiteCompiler().compile(root, Path(directory) / "b.sqlite", make_read_only=False)
        deterministic = first.output_path.read_bytes() == second.output_path.read_bytes()
        store = SemanticStore(":memory:", boot_path=first.output_path)
        try:
            cases = [json.loads(line) for line in (root / "competence" / "epistemics.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
            results = [{"case_ref": case["case_ref"], **_execute(case, store)} for case in cases]
        finally:
            store.close()
        report = {
            "valid": audit.valid and deterministic and len(results) == len(contract.required_competence_case_refs),
            "contract_ref": contract.contract_ref,
            "repository_base_commit": contract.repository_base_commit,
            "audit": {"valid": audit.valid, "issues": audit.issues, "manifest_fingerprint": audit.manifest_fingerprint},
            "compilation": {
                "byte_deterministic": deterministic, "record_count": first.record_count,
                "manifest_fingerprint": first.manifest_fingerprint,
                "record_set_fingerprint": first.record_set_fingerprint,
                "boot_fingerprint": first.boot_fingerprint,
                "byte_size": first.output_path.stat().st_size,
            },
            "competence": {"passed": len(results), "cases": results},
        }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        Path(args.report).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
