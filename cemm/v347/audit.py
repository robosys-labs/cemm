"""Public semantic audit and cycle-explanation tooling for CEMM v3.4.7."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .model import CycleResult, canonical_data
from .runtime import Runtime


def explain_cycle(result: CycleResult) -> Mapping[str, Any]:
    bundle = result.selected_bundle
    predicates = ()
    proposition_refs = ()
    selection = None
    if bundle is not None:
        predicates = tuple(sorted({
            predication.predicate_schema_ref
            for predication in bundle.graph.predications.values()
        }))
        proposition_refs = bundle.proposition_refs
        selection = canonical_data(bundle.assessment)
    proof = result.emission_proof
    return {
        "cycle_id": result.cycle_id,
        "context_id": result.context_id,
        "target_language": result.target_language,
        "output_text": result.output_text,
        "selected_predicate_refs": predicates,
        "selected_proposition_refs": proposition_refs,
        "selection_assessment": selection,
        "gaps": tuple(canonical_data(item) for item in result.gaps),
        "truth_assessments": tuple(canonical_data(item) for item in result.truth_assessments),
        "response_plan_ref": result.response_plan.plan_id if result.response_plan else None,
        "emission_proof": canonical_data(proof) if proof else None,
        "committed_patch_refs": result.committed_patch_refs,
        "trace_stages": tuple(result.trace.stages),
        "trace_errors": tuple(result.trace.errors),
    }


def runtime_audit(runtime: Runtime) -> Mapping[str, Any]:
    return {
        "version": runtime.VERSION,
        "foundation_fingerprint": runtime.foundation.fingerprint,
        "foundation_counts": {
            "referents": len(runtime.foundation.referents),
            "predicates": len(runtime.foundation.predicates),
            "operations": len(runtime.foundation.operations),
            "rules": len(runtime.foundation.rules),
            "languages": len(runtime.language_packs),
        },
        "store_revision": runtime.semantic_store.revision,
        "record_counts": dict(runtime.semantic_store.audit_counts()),
        "active_predicate_count": len(runtime.schema_store.active_predicates()),
        "active_rule_count": len(runtime.schema_store.active_rules()),
        "schema_revision_count": len(runtime.semantic_store.all_schema_revisions()),
        "rule_revision_count": len(runtime.semantic_store.latest_rule_revisions()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect CEMM v3.4.7 semantic authority")
    parser.add_argument("--database", default=":memory:")
    parser.add_argument("--eval", dest="text")
    parser.add_argument("--language")
    parser.add_argument("--context-id", default="audit")
    args = parser.parse_args(argv)
    runtime = Runtime(database_path=Path(args.database) if args.database != ":memory:" else ":memory:")
    try:
        payload: dict[str, Any] = {"runtime": runtime_audit(runtime)}
        if args.text:
            result = runtime.run_text(
                args.text,
                context_id=args.context_id,
                language_hint=args.language,
            )
            payload["cycle"] = explain_cycle(result)
            payload["runtime_after"] = runtime_audit(runtime)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
