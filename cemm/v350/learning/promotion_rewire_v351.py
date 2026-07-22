"""Phase-14 promotion graph planning for exact intra-package candidate dependencies.

Promotion is a graph transition, not independent record flipping. When several candidate
records reference one another by exact revision (for example form -> sense -> link, a sense
-> learned schema, or nested schema parent/dependency records), promoted authority must be
planned together, rewritten to the new active revisions, and dependency-linked in the same
CAS transaction.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import Mapping

from ..schema.model import UseDecision
from ..storage.codec import record_fingerprints
from ..storage.model import RecordDependency


def plan_promoted_revisions(store, candidate_pins, decision) -> dict[tuple[str, str, int], int]:
    """Return exact candidate-key -> future active revision for positively granted pins."""
    result = {}
    for pin in candidate_pins:
        grants = tuple(decision.grants_for(pin))
        if not any(grant.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL} for grant in grants):
            continue
        revisions = [
            item.revision for item in store.records(pin.record_kind, all_revisions=True)
            if item.record_ref == pin.record_ref
        ]
        latest = max(revisions, default=pin.revision)
        result[pin.key] = max(latest, pin.revision) + 1
    return result


def _pin_match(candidate_pins, ref_value, revision_value):
    if not isinstance(ref_value, str) or not isinstance(revision_value, int):
        return ()
    return tuple(
        pin for pin in candidate_pins
        if pin.record_ref == ref_value and pin.revision == revision_value
    )


def _planned_revision_for(candidate_pins, revision_map, ref_value, revision_value):
    matches = _pin_match(candidate_pins, ref_value, revision_value)
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(f"ambiguous intra-package candidate reference:{ref_value}@{revision_value}")
    pin = matches[0]
    planned = revision_map.get(pin.key)
    if planned is None:
        raise ValueError(
            "promoted authority would retain exact dependency on an unpromoted candidate:"
            f"{pin.record_kind.value}:{pin.record_ref}@{pin.revision}"
        )
    return planned


def _rewire_value(value, *, candidate_pins, revision_map):
    if is_dataclass(value):
        names = {item.name for item in fields(value)}
        updates = {}
        consumed = set()
        # Canonical direct exact-ref pairs such as form_ref/form_revision,
        # target_ref/target_revision, pack_ref/pack_revision, etc.
        for item in fields(value):
            if not item.name.endswith("_ref"):
                continue
            revision_name = item.name[:-4] + "_revision"
            if revision_name not in names:
                continue
            ref_value = getattr(value, item.name)
            revision_value = getattr(value, revision_name)
            planned = _planned_revision_for(candidate_pins, revision_map, ref_value, revision_value)
            if planned is not None:
                updates[revision_name] = planned
            consumed.add(revision_name)
        # Nested authority selectors use structural names rather than `<name>_revision`.
        if "parent_ref" in names and "revision" in names:
            planned = _planned_revision_for(
                candidate_pins, revision_map, getattr(value, "parent_ref"), getattr(value, "revision")
            )
            if planned is not None:
                updates["revision"] = planned
                consumed.add("revision")
        if "dependency_ref" in names and "exact_revision" in names:
            exact_revision = getattr(value, "exact_revision")
            if exact_revision is not None:
                planned = _planned_revision_for(
                    candidate_pins, revision_map, getattr(value, "dependency_ref"), exact_revision
                )
                if planned is not None:
                    updates["exact_revision"] = planned
                    consumed.add("exact_revision")
        # Recurse into nested structural records/collections. Never reinterpret strings;
        # only exact ref+revision structural pairs can trigger a revision rewrite.
        for item in fields(value):
            if item.name in consumed or item.name in updates:
                continue
            current = getattr(value, item.name)
            rewritten = _rewire_value(current, candidate_pins=candidate_pins, revision_map=revision_map)
            if rewritten is not current and rewritten != current:
                updates[item.name] = rewritten
        return replace(value, **updates) if updates else value
    if isinstance(value, tuple):
        rewritten = tuple(_rewire_value(item, candidate_pins=candidate_pins, revision_map=revision_map) for item in value)
        return rewritten if rewritten != value else value
    if isinstance(value, list):
        rewritten = [_rewire_value(item, candidate_pins=candidate_pins, revision_map=revision_map) for item in value]
        return rewritten if rewritten != value else value
    if isinstance(value, Mapping):
        rewritten = {
            key: _rewire_value(item, candidate_pins=candidate_pins, revision_map=revision_map)
            for key, item in value.items()
        }
        return rewritten if rewritten != value else value
    return value


def rewire_promoted_record(record, *, candidate_pins, revision_map):
    """Rewrite exact candidate-revision references to planned active revisions recursively."""
    return _rewire_value(record, candidate_pins=candidate_pins, revision_map=revision_map)


def _collect_promoted_refs(value, *, promoted_by_ref_revision, candidate_refs, output):
    if is_dataclass(value):
        names = {item.name for item in fields(value)}
        for item in fields(value):
            if item.name.endswith("_ref"):
                revision_name = item.name[:-4] + "_revision"
                if revision_name in names:
                    ref_value = getattr(value, item.name)
                    revision_value = getattr(value, revision_name)
                    if (ref_value, revision_value) in promoted_by_ref_revision:
                        output.add((ref_value, revision_value))
        if "parent_ref" in names and "revision" in names:
            pair = (getattr(value, "parent_ref"), getattr(value, "revision"))
            if pair in promoted_by_ref_revision:
                output.add(pair)
        if "dependency_ref" in names and "exact_revision" in names:
            pair = (getattr(value, "dependency_ref"), getattr(value, "exact_revision"))
            if pair in promoted_by_ref_revision:
                output.add(pair)
        # Ref-only tuple/list fields (e.g. construction trigger refs) resolve effective
        # authority by ref. Pin them to the unique promoted revision in dependency edges.
        for item in fields(value):
            if not item.name.endswith("_refs"):
                continue
            sequence = getattr(value, item.name)
            if not isinstance(sequence, (tuple, list)):
                continue
            for ref in sequence:
                if not isinstance(ref, str) or ref not in candidate_refs:
                    continue
                matches = [pair for pair in promoted_by_ref_revision if pair[0] == ref]
                if len(matches) == 1:
                    output.add(matches[0])
                elif len(matches) > 1:
                    raise ValueError(f"ambiguous ref-only intra-package promoted dependency:{ref}")
        for item in fields(value):
            _collect_promoted_refs(
                getattr(value, item.name),
                promoted_by_ref_revision=promoted_by_ref_revision,
                candidate_refs=candidate_refs,
                output=output,
            )
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            _collect_promoted_refs(
                item, promoted_by_ref_revision=promoted_by_ref_revision,
                candidate_refs=candidate_refs, output=output,
            )
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _collect_promoted_refs(
                item, promoted_by_ref_revision=promoted_by_ref_revision,
                candidate_refs=candidate_refs, output=output,
            )


def promoted_internal_dependencies(*, record, candidate_pins, revision_map, promoted_payloads):
    """Build durable edges to active intra-package dependencies referenced by ``record``."""
    promoted_by_ref_revision = {}
    for pin in candidate_pins:
        new_revision = revision_map.get(pin.key)
        payload = promoted_payloads.get(pin.key)
        if new_revision is None or payload is None:
            continue
        promoted_by_ref_revision.setdefault((pin.record_ref, new_revision), []).append((pin, payload))
    candidate_refs = {pin.record_ref for pin in candidate_pins}
    refs = set()
    _collect_promoted_refs(
        record,
        promoted_by_ref_revision=promoted_by_ref_revision,
        candidate_refs=candidate_refs,
        output=refs,
    )
    dependencies = []
    for ref_revision in sorted(refs):
        matches = promoted_by_ref_revision.get(ref_revision, ())
        if len(matches) != 1:
            if matches:
                raise ValueError(f"ambiguous promoted dependency:{ref_revision}")
            continue
        pin, payload = matches[0]
        dependencies.append(RecordDependency(
            pin.record_kind,
            pin.record_ref,
            ref_revision[1],
            record_fingerprints(pin.record_kind, payload)[1],
            "promotion_internal_active_dependency",
        ))
    return tuple(dependencies)


__all__ = [
    "plan_promoted_revisions", "promoted_internal_dependencies", "rewire_promoted_record",
]
