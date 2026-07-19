#!/usr/bin/env python3
"""Audit and competence-test CEMM v3.5 Phases 7 and 8."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.grounding import (
    CandidateOrigin,
    ClaimGroundingCompiler,
    DiscourseAnchor,
    GroundingCandidateProvider,
    IdentityProposalEngine,
    JointGrounder,
    MentionHypothesis,
    MentionTargetClass,
    MultimodalTrack,
    ProvisionalReferentPlanner,
    Span,
    SystemOutputAnchor,
)
from cemm.v350.language import (
    DependencyArc,
    DependencyParseEvidence,
    FormLatticeAnalyzer,
    SyntaxAdapterHub,
)
from cemm.v350.language.contract import (
    load_language_grounding_contract,
    LanguageGroundingPackageAuditor,
)
from cemm.v350.schema.model import StorageKind
from cemm.v350.storage import (
    EvidenceRecord,
    GraphPatch,
    IdentityFacetRecord,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SemanticStore,
    encode_record,
    record_ref,
    record_revision,
)
from cemm.v350.uol.model import IdentityStatus, Referent


class DeclaredDependencyAdapter:
    adapter_ref = "competence-adapter:declared-dependency"

    def __init__(self, arcs):
        self._arcs = tuple(tuple(item) for item in arcs)

    def analyze(self, request):
        observations = tuple(
            item for item in request.observations
            if item.category not in {"whitespace", "punctuation", "symbol"}
        )
        arcs = tuple(
            DependencyArc(
                observations[int(head)].observation_ref,
                observations[int(dependent)].observation_ref,
                str(relation),
                evidence_refs=(self.adapter_ref,),
            )
            for head, dependent, relation in self._arcs
        )
        return DependencyParseEvidence(
            parse_ref=f"parse:competence:{request.source_ref}",
            observation_refs=tuple(item.observation_ref for item in observations),
            arcs=arcs,
            root_observation_refs=(observations[0].observation_ref,),
            adapter_ref=self.adapter_ref,
            confidence=1.0,
        )


def _load_cases(path: Path):
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _operation(kind, record):
    return PatchOperation(
        operation_ref=f"operation:competence:{kind.value}:{record_ref(kind, record)}",
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=kind,
        target_ref=record_ref(kind, record),
        record_revision=record_revision(kind, record),
        payload=encode_record(kind, record),
        reason="Phase-8 competence fixture",
    )


def _grounding_fixtures(store: SemanticStore) -> None:
    evidence = EvidenceRecord(
        "evidence:phase8:competence", "source:phase8:competence", 1.0,
        "lineage:phase8:competence",
    )
    referents = (
        Referent("referent:competence:alex:a", identity_status=IdentityStatus.RESOLVED,
                 type_refs=("type:software_agent",), identity_facet_refs=("identity:competence:alex:a",)),
        Referent("referent:competence:alex:b", identity_status=IdentityStatus.RESOLVED,
                 type_refs=("type:software_agent",), identity_facet_refs=("identity:competence:alex:b",)),
    )
    facets = (
        IdentityFacetRecord("identity:competence:alex:a", referents[0].referent_ref,
                            "facet:identity", "alex", evidence_refs=(evidence.evidence_ref,)),
        IdentityFacetRecord("identity:competence:alex:b", referents[1].referent_ref,
                            "facet:identity", "alex", evidence_refs=(evidence.evidence_ref,)),
    )
    result = store.apply_patch(GraphPatch(
        patch_ref="patch:phase8:competence-fixtures",
        context_ref="actual",
        scope_ref="competence",
        source_ref="source:phase8:competence",
        permission_ref="internal",
        operations=(
            _operation(RecordKind.EVIDENCE, evidence),
            *(_operation(RecordKind.REFERENT, item) for item in referents),
            *(_operation(RecordKind.IDENTITY_FACET, item) for item in facets),
        ),
        expected_store_revision=store.revision,
    ))
    if not result.committed:
        raise RuntimeError(f"grounding fixture patch rejected: {result.errors}")


def _run_composition(store, cases):
    passed = []
    for case in cases:
        analyzer = FormLatticeAnalyzer(
            store.repositories.language.registry(),
            syntax_adapters=SyntaxAdapterHub(
                dependency_adapters=(DeclaredDependencyAdapter(case.get("dependency_arcs", ())),)
            ),
        )
        lattice = analyzer.analyze(
            case["content"], source_ref=case["case_ref"],
            language_hints=tuple(case.get("language_hints", ())),
        )
        candidate = next(
            (item for item in lattice.construction_candidates
             if item.construction_ref == case["expected_construction_ref"]),
            None,
        )
        if candidate is None:
            raise RuntimeError(f"{case['case_ref']}: expected construction missing")
        if len(candidate.gap_refs) != int(case.get("expected_gap_count", 0)):
            raise RuntimeError(f"{case['case_ref']}: unexpected gap count")
        if not any(ref.startswith("parse:competence:") for ref in candidate.evidence_refs):
            raise RuntimeError(f"{case['case_ref']}: syntax evidence was not preserved")
        passed.append(case["case_ref"])
    return passed


def _targets(lattice):
    return {item.target_ref for item in lattice.sense_candidates}


def _run_multilingual(store, cases):
    analyzer = FormLatticeAnalyzer(store.repositories.language.registry())
    passed = []
    for case in cases:
        operation = case["operation"]
        if operation == "analyze":
            lattice = analyzer.analyze(
                case["content"], source_ref=case["case_ref"],
                language_hints=tuple(case.get("language_hints", ())),
            )
            languages = {item.language_tag for item in lattice.language_evidence}
            forms = {item.form_ref for item in lattice.form_candidates}
            if not set(case.get("expected_languages", ())).issubset(languages):
                raise RuntimeError(f"{case['case_ref']}: language evidence mismatch")
            if not set(case.get("expected_forms", ())).issubset(forms):
                raise RuntimeError(f"{case['case_ref']}: form evidence mismatch")
            if not set(case.get("expected_targets", ())).issubset(_targets(lattice)):
                raise RuntimeError(f"{case['case_ref']}: semantic target mismatch")
            if len(lattice.unresolved_spans) != int(case.get("expected_unresolved_count", len(lattice.unresolved_spans))):
                raise RuntimeError(f"{case['case_ref']}: unresolved span mismatch")
        elif operation == "normalization":
            lattice = analyzer.analyze(
                case["content"], source_ref=case["case_ref"],
                language_hints=tuple(case.get("language_hints", ())),
            )
            evidence = next((item for item in lattice.normalization_evidence
                             if item.original == case["expected_original"]), None)
            if evidence is None or evidence.proposed != case["expected_proposed"] \
                    or evidence.reversible is not bool(case["expected_reversible"]):
                raise RuntimeError(f"{case['case_ref']}: reversible normalization mismatch")
        elif operation == "target_equivalence":
            target_sets = []
            for index, variant in enumerate(case["variants"]):
                lattice = analyzer.analyze(
                    variant["content"], source_ref=f"{case['case_ref']}:{index}",
                    language_hints=tuple(variant.get("language_hints", ())),
                )
                target_sets.append(_targets(lattice))
            required = set(case["required_targets"])
            if not all(required.issubset(values) for values in target_sets):
                raise RuntimeError(f"{case['case_ref']}: cross-language target equivalence failed")
        else:
            raise RuntimeError(f"unknown multilingual competence operation: {operation}")
        passed.append(case["case_ref"])
    return passed


def _run_grounding(store, cases):
    analyzer = FormLatticeAnalyzer(store.repositories.language.registry())
    grounder = JointGrounder(store, analyzer)
    passed = []
    for case in cases:
        operation = case["operation"]
        if operation == "ground_text":
            anchors = tuple(DiscourseAnchor(**item) for item in case.get("discourse_anchors", ()))
            _, result = grounder.ground_text(
                case["content"], source_ref=case["case_ref"], context_ref="actual",
                discourse_anchors=anchors,
            )
            if bool(result.selected) is not bool(case["expected_selected"]):
                raise RuntimeError(f"{case['case_ref']}: selection status mismatch")
            if case.get("expected_target_ref") and (
                result.selected is None
                or case["expected_target_ref"] not in dict(result.selected.mention_to_target).values()
            ):
                raise RuntimeError(f"{case['case_ref']}: selected target mismatch")
            if case.get("expected_provisional") and not result.frontier_refs:
                raise RuntimeError(f"{case['case_ref']}: provisional frontier missing")
            if case.get("expected_storage_kind") and not any(
                item.storage_kind.value == case["expected_storage_kind"] and item.provisional
                for item in result.candidates
            ):
                raise RuntimeError(f"{case['case_ref']}: provisional storage mismatch")
        elif operation == "ambiguous_identity":
            _, result = grounder.ground_text(case["content"], source_ref=case["case_ref"], context_ref="actual")
            targets = {item.target_ref for item in result.candidates if item.origin == CandidateOrigin.STORE}
            if targets != set(case["expected_target_refs"]) or result.selected is not None:
                raise RuntimeError(f"{case['case_ref']}: ambiguity was not preserved")
        elif operation == "addressee":
            anchor = DiscourseAnchor(
                "anchor:phase8:addressee", "referent:competence:alex:a", "actual", 1.0, 1,
                role_refs=("addressee", "audience"), type_refs=("type:software_agent",),
                evidence_refs=("evidence:phase8:addressee",),
            )
            _, result = grounder.ground_text(
                case["content"], source_ref=case["case_ref"], context_ref="actual", discourse_anchors=(anchor,)
            )
            if result.selected is None or case["expected_target_ref"] not in dict(result.selected.mention_to_target).values():
                raise RuntimeError(f"{case['case_ref']}: addressee grounding failed")
        elif operation == "demonstrative":
            track = MultimodalTrack(
                "track:phase8:visible", "vision", "actual",
                type_refs=("type:physical_entity",), salience=1.0,
                evidence_refs=("evidence:phase8:vision",),
            )
            output = SystemOutputAnchor(
                "output:phase8:previous", "actual", ("referent:self",),
                turn_index=1, evidence_refs=("evidence:phase8:output",),
            )
            _, result = grounder.ground_text(
                case["content"], source_ref=case["case_ref"], context_ref="actual",
                multimodal_tracks=(track,), system_outputs=(output,),
            )
            origins = {item.origin.value for item in result.candidates}
            if not set(case["expected_origins"]).issubset(origins):
                raise RuntimeError(f"{case['case_ref']}: deictic candidate providers missing")
        elif operation == "schema_topic":
            mention = MentionHypothesis(
                "mention:phase8:schema", case["case_ref"], Span(0, len(case["schema_ref"])),
                case["schema_ref"], case["schema_ref"], MentionTargetClass.SCHEMA_TOPIC,
                expected_storage_kinds=(StorageKind.SCHEMA_TOPIC,), context_ref="actual",
                evidence_refs=("evidence:phase8:schema",),
                metadata={"schema_target_refs": (case["schema_ref"],)},
            )
            candidates = GroundingCandidateProvider(store).generate((mention,), allow_provisional=False)
            exact = next((item for item in candidates if item.target_ref == case["schema_ref"]), None)
            if exact is None or exact.metadata.get("schema_revision") != case["expected_revision"]:
                raise RuntimeError(f"{case['case_ref']}: schema topic revision mismatch")
        elif operation == "claim":
            anchor = DiscourseAnchor(
                "anchor:phase8:claim-audience", "referent:competence:alex:a", "actual", 1.0, 2,
                role_refs=("addressee", "audience"), type_refs=("type:software_agent",),
                evidence_refs=("evidence:phase8:claim-audience",),
            )
            self_anchor = DiscourseAnchor(
                "anchor:phase8:claim-self", "referent:self", "actual", 1.0, 2,
                role_refs=("self", "speaker"), evidence_refs=("evidence:phase8:claim-self",),
            )
            _, result = grounder.ground_text(
                case["content"], source_ref=case["case_ref"], context_ref="actual",
                discourse_anchors=(anchor, self_anchor),
            )
            claim = next(item for item in result.mentions if item.target_class == MentionTargetClass.EVENT)
            source = next(item for item in result.mentions if item.surface == "I")
            audience = next(item for item in result.mentions if item.target_class == MentionTargetClass.AUDIENCE)
            grounded = ClaimGroundingCompiler(store).compile(
                result,
                claim_mention_ref=claim.mention_ref,
                proposition_ref="referent:foundation:proposition-example",
                source_mention_ref=source.mention_ref,
                audience_mention_refs=(audience.mention_ref,),
                source_context_ref="actual",
                reported_context_ref="context:phase8:reported",
                assignment_ref=result.assignments[0].assignment_ref,
            )
            if grounded.source_ref != case["expected_source_ref"] \
                    or grounded.audience_refs != (case["expected_audience_ref"],) \
                    or len(grounded.admission_refs) != case["expected_admission_count"]:
                raise RuntimeError(f"{case['case_ref']}: claim attribution contract failed")
        elif operation == "provisional_patch":
            _, result = grounder.ground_text(case["content"], source_ref=case["case_ref"], context_ref="actual")
            mention = result.mentions[0]
            proposal = ProvisionalReferentPlanner().propose(
                mention, referent_ref=result.frontier_refs[0], type_refs=("type:referent",),
                storage_kind=StorageKind.ORDINARY,
            )
            patch = ProvisionalReferentPlanner().graph_patch(proposal, source_ref=case["case_ref"], store=store)
            kinds = sorted(item.record_kind.value for item in patch.operations)
            if kinds != sorted(case["expected_record_kinds"]):
                raise RuntimeError(f"{case['case_ref']}: provisional patch authority widened")
            if store.get_record(RecordKind.REFERENT, proposal.referent_ref) is not None:
                raise RuntimeError(f"{case['case_ref']}: proposal mutated the store")
        elif operation == "identity_proposals":
            _, result = grounder.ground_text(case["content"], source_ref=case["case_ref"], context_ref="actual")
            engine = IdentityProposalEngine()
            merges = engine.merge_proposals(result.candidates, context_ref="actual")
            split = engine.split_proposal(
                referent_ref="referent:competence:alex:a",
                partition_keys=("context:a", "context:b"), context_ref="actual",
                conflicting_factor_refs=("factor:conflict",), evidence_refs=("evidence:conflict",),
                confidence=0.8,
            )
            if bool(merges) is not bool(case["expected_merge"]) \
                    or split.requires_review is not bool(case["expected_split"]):
                raise RuntimeError(f"{case['case_ref']}: identity proposal contract failed")
        else:
            raise RuntimeError(f"unknown grounding competence operation: {operation}")
        passed.append(case["case_ref"])
    return passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("cemm/data/v350"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    contract = load_language_grounding_contract(source / "language_grounding_contract.json")
    audit = LanguageGroundingPackageAuditor(contract).audit(source)
    if not audit.valid:
        raise SystemExit("Phase 7-8 source audit failed:\n" + "\n".join(audit.issues))

    with tempfile.TemporaryDirectory(prefix="cemm-v350-phase78-") as directory:
        directory = Path(directory)
        first = DeterministicSQLiteCompiler().compile(source, directory / "a.sqlite", make_read_only=False)
        second = DeterministicSQLiteCompiler().compile(source, directory / "b.sqlite", make_read_only=False)
        if first.output_path.read_bytes() != second.output_path.read_bytes():
            raise SystemExit("Phase 7-8 compilation is not byte deterministic")
        store = SemanticStore(":memory:", boot_path=first.output_path)
        try:
            composition = _run_composition(store, _load_cases(source / "competence" / "composition.jsonl"))
            multilingual = _run_multilingual(store, _load_cases(source / "competence" / "multilingual.jsonl"))
            _grounding_fixtures(store)
            grounding = _run_grounding(store, _load_cases(source / "competence" / "grounding.jsonl"))
        finally:
            store.close()

    expected_cases = set(contract.required_competence_case_refs)
    passed_cases = set((*composition, *multilingual, *grounding))
    if passed_cases != expected_cases:
        raise SystemExit(
            f"Phase 7-8 competence set mismatch: missing={sorted(expected_cases-passed_cases)} "
            f"extra={sorted(passed_cases-expected_cases)}"
        )
    report = {
        "contract_ref": contract.contract_ref,
        "base_commit": contract.base_commit,
        "valid": True,
        "audit": asdict(audit),
        "compilation": {
            "record_count": first.record_count,
            "byte_size": first.byte_size,
            "manifest_fingerprint": first.manifest_fingerprint,
            "record_set_fingerprint": first.record_set_fingerprint,
            "boot_fingerprint": first.boot_fingerprint,
            "byte_deterministic": True,
        },
        "competence": {
            "composition": composition,
            "multilingual": multilingual,
            "grounding": grounding,
            "passed": len(passed_cases),
        },
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
