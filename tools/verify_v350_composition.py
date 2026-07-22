#!/usr/bin/env python3
"""Audit and execute the CEMM v3.5 Phase-9 composition contract."""
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

from cemm.v350.composition_pre_phase10_backup import CompositionPackageAuditor, MeaningComposer, load_composition_contract
from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.grounding import JointGrounder, MultimodalTrack
from cemm.v350.language import DependencyArc, DependencyParseEvidence, FormLatticeAnalyzer, SyntaxAdapterHub
from cemm.v350.storage import SemanticStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cemm" / "data" / "v350"


class CaseDependencyAdapter:
    adapter_ref = "verifier:phase9:case-dependency"

    def __init__(self, arcs):
        self.arcs = tuple(arcs)

    def analyze(self, request):
        lexical = [
            item for item in request.observations
            if item.category not in {"whitespace", "punctuation", "symbol"}
        ]
        if not lexical:
            return None
        built = []
        for head, dependent, relation in self.arcs:
            if head >= len(lexical) or dependent >= len(lexical):
                raise ValueError("competence dependency arc index is out of range")
            built.append(DependencyArc(
                lexical[head].observation_ref,
                lexical[dependent].observation_ref,
                str(relation),
                evidence_refs=(self.adapter_ref,),
            ))
        return DependencyParseEvidence(
            parse_ref=f"parse:phase9:{request.source_ref}",
            observation_refs=tuple(item.observation_ref for item in lexical),
            arcs=tuple(built),
            root_observation_refs=(lexical[0].observation_ref,),
            adapter_ref=self.adapter_ref,
            confidence=1.0,
        )


def _cases(path):
    return tuple(json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines() if raw.strip())


def _execute_case(store, case):
    analyzer = FormLatticeAnalyzer(
        store.repositories.language.registry(),
        syntax_adapters=SyntaxAdapterHub(
            dependency_adapters=(CaseDependencyAdapter(case.get("dependency_arcs", ())),)
        ),
    )
    grounder = JointGrounder(store, analyzer)
    composer = MeaningComposer(store)
    source_ref = f"competence-source:{case['case_ref']}"
    lattice, grounding = grounder.ground_text(
        case["content"], source_ref=source_ref, context_ref="actual",
        language_hints=tuple(case.get("language_hints", ())),
        multimodal_tracks=(MultimodalTrack(
            track_ref=f"track:{case['case_ref']}", modality="competence", context_ref="actual",
            referent_ref="referent:self", evidence_refs=(f"evidence:{case['case_ref']}:track",),
        ),),
    )
    first = composer.compose(lattice, grounding, context_ref="actual")
    second = composer.compose(lattice, grounding, context_ref="actual")
    expected = case["expected"]
    graph = first.bundle.uol_graph
    if graph is None:
        raise AssertionError("no materializable UOL graph")
    schema_refs = sorted({item.schema_ref for item in graph.applications.values()})
    for ref in expected.get("application_schema_refs", ()):
        if ref not in schema_refs:
            raise AssertionError(f"missing application schema {ref}; got {schema_refs}")
    if "minimum_application_count" in expected and len(graph.applications) < int(expected["minimum_application_count"]):
        raise AssertionError(f"application count {len(graph.applications)} below expected minimum")
    event_statuses = sorted({item.occurrence_status.value for item in graph.events.values()})
    for status in expected.get("event_statuses", ()):
        if status not in event_statuses:
            raise AssertionError(f"missing event status {status}; got {event_statuses}")
    scope_kinds = sorted({item.scope_kind.value for item in graph.scope_relations})
    for kind in expected.get("scope_kinds", ()):
        if kind not in scope_kinds:
            raise AssertionError(f"missing scope kind {kind}; got {scope_kinds}")
    if expected.get("no_admission") and any(item.admission_refs for item in graph.events.values()):
        raise AssertionError("Phase 9 produced event admission")
    if expected.get("no_deltas") and (graph.state_deltas or graph.capability_deltas):
        raise AssertionError("Phase 9 produced durable-effect deltas")
    if int(expected.get("minimum_open_variables", 0)) > len(graph.variables):
        raise AssertionError("expected open semantic variables")
    if expected.get("frontier_required") and not first.bundle.partial_understanding.frontier_refs:
        raise AssertionError("expected unresolved grounding frontier")
    if "decisive" in expected and first.bundle.selection.decisive is not bool(expected["decisive"]):
        raise AssertionError("unexpected decisiveness")
    if "realization_influenced_selection" in expected and first.bundle.metadata["realization_influenced_selection"] is not bool(expected["realization_influenced_selection"]):
        raise AssertionError("realization leaked into meaning selection")
    if expected.get("deterministic") and first.fingerprint != second.fingerprint:
        raise AssertionError("composition result is not deterministic")
    if expected.get("bounded") and not first.bundle.metadata.get("bounded"):
        raise AssertionError("search did not report bounded execution")
    if int(expected.get("minimum_hypotheses", 0)) > len(first.solve_result.hypotheses):
        raise AssertionError("insufficient meaning hypotheses")
    return {
        "case_ref": case["case_ref"],
        "result_fingerprint": first.fingerprint,
        "application_schema_refs": schema_refs,
        "scope_kinds": scope_kinds,
        "event_statuses": event_statuses,
        "hypotheses": len(first.solve_result.hypotheses),
        "expansions": first.solve_result.expansions,
        "decisive": first.bundle.selection.decisive,
        "unresolved": len(first.bundle.partial_understanding.unresolved_refs),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    contract = load_composition_contract(args.source / "composition_contract.json")
    audit = CompositionPackageAuditor(contract).audit(args.source)
    if not audit.valid:
        raise SystemExit("Phase 9 source audit failed:\n" + "\n".join(audit.issues))
    compiler = DeterministicSQLiteCompiler()
    with tempfile.TemporaryDirectory(prefix="cemm-v350-phase9-") as directory:
        directory = Path(directory)
        first = compiler.compile(args.source, directory / "a.sqlite", make_read_only=False)
        second = compiler.compile(args.source, directory / "b.sqlite", make_read_only=False)
        if first.output_path.read_bytes() != second.output_path.read_bytes():
            raise SystemExit("Phase 9 deterministic compilation failed")
        store = SemanticStore(":memory:", boot_path=first.output_path)
        try:
            results = tuple(
                _execute_case(store, case)
                for case in _cases(args.source / "competence" / "meaning_composition.jsonl")
            )
        finally:
            store.close()
    report = {
        "valid": True,
        "contract_ref": contract.contract_ref,
        "repository_base_commit": contract.repository_base_commit,
        "audit": asdict(audit),
        "compilation": {
            "record_count": first.record_count,
            "manifest_fingerprint": first.manifest_fingerprint,
            "record_set_fingerprint": first.record_set_fingerprint,
            "boot_fingerprint": first.boot_fingerprint,
            "byte_deterministic": True,
            "byte_size": first.byte_size,
        },
        "competence": {"passed": len(results), "cases": results},
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
