"""One-way migration boundary from legacy records to CEMM v3.4.7.

The adapter deliberately rejects incomplete legacy records instead of claiming
semantic equivalence. No reverse adapter exists.
"""
from __future__ import annotations
from typing import Any, Mapping

from cemm.v347.model import (
    GraphPatch, KnowledgeRecord, PatchOperation, PatchOperationKind, Polarity,
    PortBinding, Predication, Referent, ReferentKind, TruthStatus, canonical_data,
    semantic_hash,
)


class LegacyMigrationError(ValueError):
    pass


_KIND_MAP = {
    "entity": ReferentKind.UNKNOWN,
    "person": ReferentKind.PERSON,
    "agent": ReferentKind.AGENT,
    "self": ReferentKind.SELF,
    "place": ReferentKind.PLACE,
    "event": ReferentKind.EVENT,
    "state": ReferentKind.STATE,
    "proposition": ReferentKind.PROPOSITION,
    "quantity": ReferentKind.QUANTITY,
    "unit": ReferentKind.UNIT,
    "time": ReferentKind.TIME,
    "value": ReferentKind.TEXT,
    "text": ReferentKind.TEXT,
}


def migrate_legacy_referent(value: Mapping[str, Any]) -> Referent:
    legacy_id = str(value.get("referent_id") or value.get("id") or value.get("key") or "")
    if not legacy_id:
        raise LegacyMigrationError("legacy referent has no stable identity")
    kind_name = str(value.get("kind") or value.get("atom_kind") or "unknown").casefold()
    kind = _KIND_MAP.get(kind_name)
    if kind is None:
        raise LegacyMigrationError(f"unsupported legacy referent kind: {kind_name}")
    payload = value.get("payload")
    if payload is None:
        payload = {
            key: value[key]
            for key in ("text", "name", "magnitude", "semantic_key")
            if value.get(key) is not None
        }
    if kind == ReferentKind.UNKNOWN and not value.get("type_refs"):
        raise LegacyMigrationError(
            "generic legacy entity cannot be migrated without a typed anchor"
        )
    return Referent(
        referent_id=legacy_id if legacy_id.startswith("referent:") else f"referent:legacy:{legacy_id}",
        kind=kind,
        type_refs=tuple(map(str, value.get("type_refs", ()))),
        payload=dict(payload or {}) or None,
        scope_ref=str(value.get("scope_ref", "migration")),
        context_ref=str(value.get("context_ref", "actual")),
        revision=int(value.get("revision", 1)),
        metadata={"legacy_source": dict(value)},
    )


def migrate_legacy_fact(
    value: Mapping[str, Any], *, expected_store_revision: int
) -> GraphPatch:
    predicate_ref = str(value.get("predicate_schema_ref") or value.get("predicate_key") or "")
    if not predicate_ref:
        raise LegacyMigrationError("legacy fact has no predicate")
    if not predicate_ref.startswith("predicate:"):
        predicate_ref = f"predicate:{predicate_ref}"
    raw_roles = value.get("bindings") or value.get("roles")
    if not raw_roles:
        raise LegacyMigrationError("legacy fact has no role/port bindings")
    bindings: list[PortBinding] = []
    operations: list[PatchOperation] = []
    if isinstance(raw_roles, Mapping):
        iterator = raw_roles.items()
    else:
        iterator = []
        for item in raw_roles:
            if not isinstance(item, Mapping):
                raise LegacyMigrationError("legacy role is not structured")
            port = item.get("port_id") or item.get("role") or item.get("role_key")
            ref = item.get("referent_ref") or item.get("value_ref") or item.get("value")
            iterator.append((port, ref))
    for port, raw_ref in iterator:
        if not port or raw_ref is None:
            raise LegacyMigrationError("legacy binding lacks port or referent")
        if isinstance(raw_ref, Mapping):
            referent = migrate_legacy_referent(raw_ref)
            operations.append(PatchOperation(
                operation_id=f"op:{referent.referent_id}",
                kind=PatchOperationKind.UPSERT_REFERENT,
                target_ref=referent.referent_id,
                payload=canonical_data(referent),
            ))
            referent_ref = referent.referent_id
        else:
            referent_ref = str(raw_ref)
            if not referent_ref.startswith("referent:"):
                raise LegacyMigrationError(
                    f"untyped raw legacy filler for {port}; migrate the referent first"
                )
        bindings.append(PortBinding(port_id=str(port), referent_refs=(referent_ref,)))
    context_ref = str(value.get("context_ref", "actual"))
    predication = Predication(
        predication_id=semantic_hash("legacy_predication", (predicate_ref, bindings, context_ref)),
        predicate_schema_ref=predicate_ref,
        bindings=tuple(bindings),
        context_ref=context_ref,
        source_evidence_refs=(str(value.get("fact_id") or "legacy:fact"),),
        confidence=float(value.get("confidence", 0.5)),
    )
    proposition = Referent(
        referent_id=semantic_hash("legacy_proposition", predication.predication_id),
        kind=ReferentKind.PROPOSITION,
        type_refs=("kind:proposition",),
        payload={
            "predication_refs": (predication.predication_id,),
            "context_ref": context_ref,
            "polarity": str(value.get("polarity", Polarity.POSITIVE.value)),
            "modality_refs": (),
            "attribution_ref": str(value.get("source_ref", "legacy:unknown")),
            "valid_time_ref": value.get("valid_time_ref"),
            "communicative_force": "assert",
        },
        scope_ref=str(value.get("scope_ref", "migration")),
        context_ref=context_ref,
        metadata={"migrated": True},
    )
    knowledge = KnowledgeRecord(
        knowledge_id=semantic_hash("legacy_knowledge", proposition.referent_id),
        proposition_ref=proposition.referent_id,
        truth_status=TruthStatus.SUPPORTED,
        context_ref=context_ref,
        source_refs=(str(value.get("source_ref", "legacy:unknown")),),
        evidence_refs=(str(value.get("fact_id") or "legacy:fact"),),
        confidence=float(value.get("confidence", 0.5)),
        scope_ref=str(value.get("scope_ref", "migration")),
        permission_ref=str(value.get("permission_ref", "private")),
        metadata={"migrated": True, "requires_review": True},
    )
    operations.extend((
        PatchOperation(f"op:{predication.predication_id}", PatchOperationKind.UPSERT_PREDICATION, predication.predication_id, canonical_data(predication)),
        PatchOperation(f"op:{proposition.referent_id}", PatchOperationKind.UPSERT_PROPOSITION, proposition.referent_id, canonical_data(proposition)),
        PatchOperation(f"op:{knowledge.knowledge_id}", PatchOperationKind.UPSERT_KNOWLEDGE, knowledge.knowledge_id, canonical_data(knowledge)),
    ))
    return GraphPatch(
        patch_id=semantic_hash("patch:legacy_migration", tuple(op.operation_id for op in operations)),
        context_ref=context_ref,
        scope_ref=str(value.get("scope_ref", "migration")),
        source_ref="migration:v347",
        evidence_refs=(str(value.get("fact_id") or "legacy:fact"),),
        operations=tuple(operations),
        expected_store_revision=expected_store_revision,
        permission_ref="migration_review",
        validation_requirements=("known_predicate_schema", "typed_referents", "human_or_policy_review"),
        rollback_hint="supersede migrated knowledge and remove migration-only referents",
        metadata={"one_way": True, "fail_closed": True},
    )
