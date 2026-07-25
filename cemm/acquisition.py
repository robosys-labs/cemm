#!/usr/bin/env python3
"""Explicit reviewed lexical acquisition for CEMM v1.

Unknown-form detection in normal cognition is pure and opens typed frontiers.
This module is a separate reviewed authority workflow: every newly created
semantic identity has an explicit kind supplied by a reviewer/training system.
It never guesses ``concept`` and never retries parsing from inside the parser.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cemm.model import lit, stable
from cemm.runtime import MODE_NORMAL, MODE_REVIEWED_TEACH, Runtime
from cemm.store import Store

# Kernel ABI and state-space authority require dedicated reviewed data changes,
# not lexical mention acquisition.
_FORBIDDEN_NEW_KINDS = {"operator", "role", "state_dimension"}


def _validated_kind(value: Any) -> str:
    kind = str(value or "").strip()
    if not kind:
        raise ValueError("reviewed acquisition requires an explicit semantic kind for each new mention")
    if kind in _FORBIDDEN_NEW_KINDS:
        raise ValueError(f"reviewed lexical acquisition cannot create ABI/state-space kind: {kind}")
    return kind


def acquire_reviewed(store: Store, runtime: Runtime, document: dict[str, Any]) -> dict[str, Any]:
    """Publish reviewed identities/designations, then optionally process text.

    The designation commit is one Stage-13 authority/world generation with an
    incremental receipt. The runtime is explicitly re-pinned afterward. Text is
    then processed by the ordinary normal cycle or reviewed teaching cycle; no
    acquisition-specific semantic parser exists.
    """
    language = str(document.get("language") or runtime.lang)
    document_ref = str(document.get("document_ref") or stable("reviewed-document", document))
    mentions = list(document.get("mentions") or ())
    if not mentions:
        raise ValueError("reviewed acquisition requires at least one mention")

    expected_world_revision = store.revisions()["world_revision"]
    created: dict[str, str] = {}
    designation_apps: list[str] = []
    with store.db:
        generation = store.begin(
            f"reviewed_acquisition:{document_ref}",
            expected_world_revision=expected_world_revision,
        )
        for index, mention in enumerate(mentions):
            surface = str(mention.get("surface") or "").strip()
            if not surface:
                raise ValueError(f"mention {index} requires a non-empty surface")
            supplied_ref = mention.get("ref")
            supplied_kind = mention.get("kind")
            ref = str(supplied_ref) if supplied_ref else None
            atom = store.atom(ref) if ref else None
            if atom:
                if supplied_kind and str(atom["kind"]) != str(supplied_kind):
                    raise ValueError(
                        f"mention {surface!r} kind conflicts with existing identity {ref}: "
                        f"{supplied_kind} != {atom['kind']}"
                    )
            else:
                if ref is None and supplied_kind:
                    ref = store.resolve_label(surface, language, str(supplied_kind))
                    atom = store.atom(ref) if ref else None
                if not atom:
                    kind = _validated_kind(supplied_kind)
                    ref = ref or stable("atom", kind, document_ref, index)
                    store.exact(
                        "atoms",
                        ["ref", "kind", "metadata", "generation", "authority_scope"],
                        [ref, kind, json.dumps(mention.get("metadata", {}), sort_keys=True, separators=(",", ":")), generation, "authority"],
                        ["ref"],
                        {"generation"},
                    )
            assert ref is not None
            args = {
                "role:target": ref,
                "role:label_type": str(mention.get("label_type") or "label:lexical"),
                "role:surface": lit(surface),
                "role:language": lit(language),
                "role:script": lit(str(mention.get("script") or "Latn")),
                "role:prior": lit(float(mention.get("prior", 1.2)), "float"),
                "role:preferred": lit(bool(mention.get("preferred", True)), "bool"),
            }
            if mention.get("context_ref"):
                args["role:context"] = str(mention["context_ref"])
            observation = store.add_observation(
                surface,
                {"designation": ref, "document_ref": document_ref},
                language,
                "reviewed_acquisition",
                generation,
                occurrence_ref=f"{document_ref}:designation:{index}",
            )
            designation_apps.append(
                store.insert_app(
                    "op:designation",
                    args,
                    generation,
                    observation,
                    "support",
                    1.0,
                    "reviewed",
                )
            )
            created[surface] = ref
        receipt = store.finish(
            generation,
            cycle_ref=f"acquisition:{document_ref}",
            stage=13,
            expected_world_revision=expected_world_revision,
            world_delta=True,
            observation_delta=True,
            payload={
                "document_ref": document_ref,
                "created_or_resolved": created,
                "designation_apps": designation_apps,
            },
        )

    runtime.reload_authority()
    text = str(document.get("text") or "").strip()
    result = None
    if text:
        result = runtime.process(
            text,
            mode=MODE_REVIEWED_TEACH if document.get("teach_rule") else MODE_NORMAL,
        )
    return {
        "status": "reviewed_acquisition_committed",
        "document_ref": document_ref,
        "generation": generation,
        "created_or_resolved": created,
        "designation_apps": designation_apps,
        "commit_receipt": receipt,
        "result": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicit reviewed CEMM lexical acquisition")
    parser.add_argument("document")
    parser.add_argument("--db", required=True)
    parser.add_argument("--pack", required=True)
    parser.add_argument("--data", action="append", default=[])
    args = parser.parse_args()
    store = Store(args.db)
    for source in args.data:
        store.import_data(source)
    runtime = Runtime(store, args.pack)
    document = json.loads(Path(args.document).read_text(encoding="utf-8"))
    print(json.dumps(acquire_reviewed(store, runtime, document), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
