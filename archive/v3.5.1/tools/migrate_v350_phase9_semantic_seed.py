#!/usr/bin/env python3
"""Migrate legacy form_sense_link data to the canonical lexeme/contribution path.

This tool converts old-style direct ``form -> sense`` links into the durable
lexeme / lexical_sense / form_lexeme_link / lexeme_sense_link architecture
described in AGENTS.md section 14 (Language authority law).

It is idempotent: running it twice produces identical output.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records),
        encoding="utf-8",
    )


def _load_manifest(root: Path) -> dict:
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def _save_manifest(root: Path, manifest: dict) -> None:
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _find_module(manifest: dict, record_kind: str) -> dict | None:
    for module in manifest["modules"]:
        if module["record_kind"] == record_kind:
            return module
    return None


def migrate(root: Path) -> None:
    """Migrate legacy form_sense_link records to the canonical lexeme path."""
    manifest = _load_manifest(root)

    fsl_module = _find_module(manifest, "form_sense_link")
    if fsl_module is None:
        return

    fsl_path = root / fsl_module["path"]
    links = _read_jsonl(fsl_path)
    if not links:
        return

    # Check if already migrated (all links superseded)
    if all(link.get("lifecycle_status") == "superseded" for link in links):
        return

    # Load existing lexeme-related data
    lexeme_module = _find_module(manifest, "lexeme")
    fll_module = _find_module(manifest, "form_lexeme_link")
    lsl_module = _find_module(manifest, "lexeme_sense_link")
    sense_module = _find_module(manifest, "lexical_sense")

    lexemes = _read_jsonl(root / lexeme_module["path"]) if lexeme_module else []
    form_lexeme_links = _read_jsonl(root / fll_module["path"]) if fll_module else []
    lexeme_sense_links = _read_jsonl(root / lsl_module["path"]) if lsl_module else []
    senses = _read_jsonl(root / sense_module["path"]) if sense_module else []

    existing_lexeme_refs = {lex["lexeme_ref"] for lex in lexemes}
    existing_fll_refs = {fll["link_ref"] for fll in form_lexeme_links}
    existing_lsl_refs = {lsl["link_ref"] for lsl in lexeme_sense_links}

    for link in links:
        if link.get("lifecycle_status") == "superseded":
            continue

        form_ref = link["form_ref"]
        form_revision = link.get("form_revision", 1)
        sense_ref = link["sense_ref"]
        sense_revision = link.get("sense_revision", 1)
        pack_ref = link.get("pack_ref", "")
        source_refs = link.get("source_refs", [])
        evidence_refs = link.get("evidence_refs", [])
        competence_refs = link.get("competence_case_refs", [])
        permission_ref = link.get("permission_ref", "public")

        # Derive lexeme ref from sense ref (one lexeme per sense family)
        # Use the sense_ref to create a stable lexeme identity
        lexeme_ref = f"lexeme:{sense_ref.split(':')[1]}:{sense_ref.split(':')[-1]}" if ":" in sense_ref else f"lexeme:{form_ref}"
        lexeme_revision = 1

        # Create lexeme if it doesn't exist
        if lexeme_ref not in existing_lexeme_refs:
            # Determine lexical category from linked sense
            sense = next((s for s in senses if s["sense_ref"] == sense_ref), None)
            lexical_category = sense.get("lexical_category", "unknown") if sense else "unknown"
            lemma_form_ref = form_ref
            lemma_form_revision = form_revision

            lexemes.append({
                "competence_case_refs": competence_refs,
                "evidence_refs": evidence_refs,
                "feature_defaults": [],
                "inflection_class_ref": "",
                "lemma_form_ref": lemma_form_ref,
                "lemma_form_revision": lemma_form_revision,
                "lexeme_ref": lexeme_ref,
                "lexical_category": lexical_category,
                "lifecycle_status": "active",
                "metadata": {"phase9_migrated": True},
                "pack_ref": pack_ref,
                "pack_revision": 1,
                "permission_ref": permission_ref,
                "revision": lexeme_revision,
                "source_refs": source_refs,
                "supersedes_revision": None,
            })
            existing_lexeme_refs.add(lexeme_ref)

        # Create form_lexeme_link (lemma relation)
        fll_ref = f"form-lexeme-link:{form_ref}:{lexeme_ref}"
        if fll_ref not in existing_fll_refs:
            form_lexeme_links.append({
                "condition_refs": [],
                "evidence_refs": evidence_refs,
                "feature_values": [],
                "form_ref": form_ref,
                "form_revision": form_revision,
                "lexeme_ref": lexeme_ref,
                "lexeme_revision": lexeme_revision,
                "lifecycle_status": "active",
                "link_ref": fll_ref,
                "metadata": {"phase9_migrated": True},
                "permission_ref": permission_ref,
                "prior_weight": link.get("prior_weight", 1.0),
                "relation_kind": "lemma",
                "revision": 1,
                "source_refs": source_refs,
                "supersedes_revision": None,
            })
            existing_fll_refs.add(fll_ref)

        # Create lexeme_sense_link
        lsl_ref = f"lexeme-sense-link:{lexeme_ref}:{sense_ref}"
        if lsl_ref not in existing_lsl_refs:
            lexeme_sense_links.append({
                "condition_refs": [],
                "evidence_refs": evidence_refs,
                "lexeme_ref": lexeme_ref,
                "lexeme_revision": lexeme_revision,
                "lifecycle_status": "active",
                "link_ref": lsl_ref,
                "metadata": {"phase9_migrated": True},
                "permission_ref": permission_ref,
                "prior_weight": 1.0,
                "revision": 1,
                "sense_ref": sense_ref,
                "sense_revision": sense_revision,
                "source_refs": source_refs,
                "supersedes_revision": None,
            })
            existing_lsl_refs.add(lsl_ref)

        # Supersede the original form_sense_link
        link["lifecycle_status"] = "superseded"

    # Write back all data
    _write_jsonl(fsl_path, links)
    if lexeme_module:
        _write_jsonl(root / lexeme_module["path"], lexemes)
    if fll_module:
        _write_jsonl(root / fll_module["path"], form_lexeme_links)
    if lsl_module:
        _write_jsonl(root / lsl_module["path"], lexeme_sense_links)

    # Migrate construction metadata: remove interpretation_enabled
    construction_module = _find_module(manifest, "construction")
    if construction_module:
        constructions = _read_jsonl(root / construction_module["path"])
        for construction in constructions:
            meta = construction.get("metadata", {})
            if "interpretation_enabled" in meta:
                del meta["interpretation_enabled"]
                construction["metadata"] = meta
            # Add explicit use authority if not present
            if "use_authority_explicit" not in construction:
                construction["use_authority_explicit"] = True
            if "authorized_use_operations" not in construction:
                construction["authorized_use_operations"] = ["ground"]
        _write_jsonl(root / construction_module["path"], constructions)

    # Migrate lexical_sense: ensure explicit use authority, remove phase9 competence refs
    if sense_module:
        for sense in senses:
            # Query markers must not directly target a discourse act — that
            # fabricates matrix question force. The query contribution is
            # decomposed per AGENTS.md section 5 (Query Separation Law).
            if sense.get("lexical_category") == "query_marker":
                sense["target_ref"] = None
                sense["target_kind"] = None
                sense["target_schema_class"] = None
                sense["target_revision"] = None
            if "use_authority_explicit" not in sense:
                sense["use_authority_explicit"] = True
            if "authorized_use_operations" not in sense:
                sense["authorized_use_operations"] = ["ground"]
            # Remove phase9 competence case refs
            if "competence_case_refs" in sense:
                sense["competence_case_refs"] = [
                    ref for ref in sense["competence_case_refs"]
                    if not str(ref).startswith("competence:phase9:")
                ]
            # Remove phase9 matrix question force metadata
            meta = sense.get("metadata", {})
            if "phase9_matrix_question_force" in meta:
                del meta["phase9_matrix_question_force"]
                sense["metadata"] = meta
        _write_jsonl(root / sense_module["path"], senses)


def verify_invariants(root: Path) -> tuple:
    """Verify post-migration invariants. Returns tuple of violation strings."""
    violations = []
    manifest = _load_manifest(root)

    # Check form_sense_links are superseded
    fsl_module = _find_module(manifest, "form_sense_link")
    if fsl_module:
        links = _read_jsonl(root / fsl_module["path"])
        for link in links:
            if link.get("lifecycle_status") != "superseded":
                violations.append(f"form_sense_link {link.get('link_ref')} is not superseded")

    # Check no phase9 matrix question force in sense metadata
    sense_module = _find_module(manifest, "lexical_sense")
    if sense_module:
        senses = _read_jsonl(root / sense_module["path"])
        for sense in senses:
            if sense.get("metadata", {}).get("phase9_matrix_question_force"):
                violations.append(f"sense {sense['sense_ref']} has phase9_matrix_question_force")
            for ref in sense.get("competence_case_refs", []):
                if str(ref).startswith("competence:phase9:"):
                    violations.append(f"sense {sense['sense_ref']} has phase9 competence ref")

    # Check no interpretation_enabled in construction metadata
    construction_module = _find_module(manifest, "construction")
    if construction_module:
        constructions = _read_jsonl(root / construction_module["path"])
        for construction in constructions:
            if "interpretation_enabled" in construction.get("metadata", {}):
                violations.append(f"construction {construction['construction_ref']} still has interpretation_enabled")

    return tuple(violations)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <source_root>", file=sys.stderr)
        raise SystemExit(1)
    root = Path(sys.argv[1])
    migrate(root)
    violations = verify_invariants(root)
    if violations:
        print("Invariant violations:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        raise SystemExit(1)
    print("Migration complete, all invariants verified.")
