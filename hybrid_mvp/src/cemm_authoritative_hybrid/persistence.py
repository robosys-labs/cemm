"""Crash-consistent semantic persistence.

This module owns :class:`SemanticStores`, :class:`SQLiteSemanticStore` (the
reference persistent backend) and a test-only in-memory backend. SQLite uses
WAL mode, ``BEGIN IMMEDIATE`` write transactions, canonical payload hashes,
revision rows, immutable episode rows, unique effect keys and transaction
receipts. Startup activation checks schema version, row hashes, revision
continuity and unresolved effect records; corruption raises
:class:`StoreActivationError` with a :class:`RecoveryReceipt` and never resets
the database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence
from itertools import islice

from .canonical import canonical_bytes, stable_ref, stable

if TYPE_CHECKING:
    from .dialogue import DialogueObligation, VerifiedSemanticFocus

__all__ = [
    "StaleRevisionError",
    "StoreActivationError",
    "RevisionPin",
    "CommitReceipt",
    "RecoveryReceipt",
    "SemanticStores",
    "SQLiteSemanticStore",
    "InMemorySemanticStore",
    "open_stores",
    "memory_stores",
    "Fact",
    "Obligation",
    "Session",
    "NormalizedApplicationClaim",
]

_SCHEMA_VERSION = 1
_NORMALIZED_STORE_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Persistence record types (owned here)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Fact:
    fact_ref: str
    operator: str
    args: Mapping[str, Any]
    stance: str = "support"
    confidence: float = 1.0
    derived: bool = False
    proof: Mapping[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        return json.dumps(
            (self.operator, dict(self.args), self.stance),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )

    @classmethod
    def from_application(
        cls,
        application: Any,
        *,
        derived: bool = False,
        confidence: float = 1.0,
        proof: Mapping[str, Any] | None = None,
    ) -> "Fact":
        return cls(
            stable("fact", application.operator, dict(application.args), application.stance, proof),
            application.operator, dict(application.args), application.stance,
            confidence, derived, dict(proof or {}),
        )


@dataclass(frozen=True)
class NormalizedApplicationClaim:
    """One independently asserted claim plus its child-first application closure."""

    claim_ref: str
    application_ref: str
    stance: str
    fact_ref: str
    source_ref: str
    decision_ref: str
    occurrence_ref: str
    placement: str
    placement_ref: str
    proof_refs: tuple[str, ...]
    authority_generation: str
    confidence_micros: int
    asserted_world_revision: int
    commit_transaction_ref: str
    active: bool
    applications: tuple[Any, ...]


@dataclass(frozen=True)
class _PreparedNormalizedBatch:
    """Private write material; preparation is not publication authority."""

    applications: tuple[Any, ...]
    root_application_ref: str
    claim_ref: str
    claim_payload: Mapping[str, Any]
    authorization_payload: Mapping[str, Any] | None = None


def _normalized_filler_payload(filler: Any) -> dict[str, Any]:
    from .expressions import ApplicationFiller, GroundedReference, LiteralValue

    if type(filler) is GroundedReference:
        return {"kind": "grounded", "target_ref": filler.target_ref}
    if type(filler) is LiteralValue:
        return {"kind": "literal", "value_type": filler.value_type, "value": filler.value}
    if type(filler) is ApplicationFiller:
        return {"kind": "application", "application_ref": filler.node_ref}
    raise ValueError("normalized persistence rejects variable or unresolved fillers")


def _normalized_binding_payload(binding_kind: str, ordinal: int, binding: Any) -> dict[str, Any]:
    return {
        "binding_kind": binding_kind,
        "ordinal": ordinal,
        "role_ref": binding.role_ref,
        "filler": _normalized_filler_payload(binding.filler),
    }


def _normalized_application_payload(application: Any) -> dict[str, Any]:
    return {
        "operator": application.operator,
        "predicate_ref": application.predicate_ref,
        "roles": [
            _normalized_binding_payload("role", index, row)
            for index, row in enumerate(application.roles)
        ],
        "qualifiers": [
            _normalized_binding_payload("qualifier", index, row)
            for index, row in enumerate(application.qualifiers)
        ],
    }


def _normalized_projection_value(filler: Mapping[str, Any], *, alias_surface: bool = False) -> Any:
    kind = filler["kind"]
    if kind == "grounded":
        return filler["target_ref"]
    if kind == "application":
        return filler["application_ref"]
    if kind == "literal":
        if alias_surface and filler["value_type"] == "string":
            return filler["value"]
        return {"literal_type": filler["value_type"], "value": filler["value"]}
    raise ValueError("normalized projection received an invalid filler")


def _normalized_legacy_projection(payload: Mapping[str, Any], stance: str) -> tuple[str, dict[str, Any], str]:
    """Return the exact temporary Fact projection for one normalized root.

    This bridge is intentionally one-way: normalized rows are never rebuilt
    from the projection. Typed literals and qualifier ownership stay explicit,
    except the already-governed designation surface ABI remains a plain string.
    """
    args: dict[str, Any] = {"predicate_ref": payload["predicate_ref"]}
    for row in payload["roles"]:
        role_ref = row["role_ref"]
        args[role_ref] = _normalized_projection_value(
            row["filler"],
            alias_surface=payload["operator"] == "op:designation" and role_ref == "role:surface",
        )
    if payload["qualifiers"]:
        args["normalized_qualifiers"] = [
            {"role_ref": row["role_ref"], "filler": row["filler"]}
            for row in payload["qualifiers"]
        ]
    return payload["operator"], args, stance


def _normalized_fact_corresponds(fact: Fact, payload: Mapping[str, Any], stance: str) -> bool:
    operator, args, projected_stance = _normalized_legacy_projection(payload, stance)
    return (
        type(fact) is Fact
        and fact.operator == operator
        and dict(fact.args) == args
        and fact.stance == projected_stance
    )


def _normalized_retraction_fact_corresponds(
    fact: Fact, claim_ref: str, occurrence_ref: str, proof_refs: Sequence[str]
) -> bool:
    return (
        type(fact) is Fact
        and fact.operator == "op:event"
        and dict(fact.args) == {
            "predicate_ref": "event:retract",
            "role:object": claim_ref,
        }
        and fact.stance == "support"
        and fact.proof.get("occurrence_ref") == occurrence_ref
        and occurrence_ref in proof_refs
    )


def _normalized_generic_lineage_corresponds(
    fact: Fact, claim: Mapping[str, Any]
) -> bool:
    proof = fact.proof
    return (
        proof.get("source") == claim["source_ref"]
        and proof.get("decision_ref") == claim["decision_ref"]
        and proof.get("occurrence_ref") == claim["occurrence_ref"]
        and proof.get("placement") == claim["placement"]
        and proof.get("placement_ref") == claim["placement_ref"]
        and proof.get("proof_refs") == claim["proof_refs"]
        and round(fact.confidence * 1_000_000) == claim["confidence_micros"]
    )


def _prepare_normalized_application_claim(
    expression: Any,
    *,
    root_ref: str,
    stance: str,
    fact_ref: str,
    source_ref: str,
    decision_ref: str,
    occurrence_ref: str,
    placement: str,
    placement_ref: str,
    proof_refs: tuple[str, ...],
    authority_generation: str,
    confidence_micros: int,
    commit_transaction_ref: str,
    asserted_world_revision: int,
    authorization_payload: Mapping[str, Any] | None = None,
) -> _PreparedNormalizedBatch:
    """Privately normalize an already-settled expression and claim lineage.

    This first persistence slice is intentionally application-only. Scope
    operators, expression links, binders, unresolved fillers and non-application
    roots are rejected until a later substrate can preserve them losslessly.
    Calling this helper never authorizes or writes a claim.
    """
    from .expressions import (
        ApplicationFiller,
        BoundVariable,
        GroundedReference,
        LiteralValue,
        SemanticApplication,
        SemanticExpression,
        UnresolvedValue,
    )

    if type(expression) is not SemanticExpression:
        raise TypeError("normalized preparation requires exact SemanticExpression")
    if expression.scope_operators or expression.expression_links or expression.binders or expression.unresolved_fillers:
        raise ValueError("normalized application persistence cannot losslessly store non-application expression structure")
    if type(root_ref) is not str or not root_ref:
        raise TypeError("root_ref must be exact nonempty str")
    if expression.root_refs != (root_ref,):
        raise ValueError("normalized claim requires the expression's one exact application root")
    applications = {row.application_ref: row for row in expression.applications}
    if root_ref not in applications:
        raise ValueError("normalized claim root must be a semantic application")
    for name, value in (
        ("fact_ref", fact_ref), ("source_ref", source_ref), ("decision_ref", decision_ref),
        ("occurrence_ref", occurrence_ref), ("placement", placement),
        ("placement_ref", placement_ref), ("authority_generation", authority_generation),
        ("commit_transaction_ref", commit_transaction_ref),
    ):
        if type(value) is not str or not value:
            raise TypeError(f"{name} must be exact nonempty str")
    if stance not in {"support", "deny"}:
        raise ValueError("normalized claim stance must be support or deny")
    if type(proof_refs) is not tuple or not proof_refs or any(type(row) is not str or not row for row in proof_refs):
        raise TypeError("proof_refs must be a nonempty exact-ref tuple")
    if type(confidence_micros) is not int or isinstance(confidence_micros, bool) or not 0 <= confidence_micros <= 1_000_000:
        raise TypeError("confidence_micros must be an exact int in 0..1000000")
    if type(asserted_world_revision) is not int or isinstance(asserted_world_revision, bool) or asserted_world_revision < 0:
        raise TypeError("asserted_world_revision must be an exact nonnegative int")

    visiting: set[str] = set()
    persistent: dict[str, SemanticApplication] = {}
    ordered: list[SemanticApplication] = []

    def persist(local_ref: str) -> str:
        if local_ref in persistent:
            return persistent[local_ref].application_ref
        if local_ref in visiting:
            raise ValueError("normalized application graph is cyclic")
        source = applications.get(local_ref)
        if source is None:
            raise ValueError("application filler points to a missing semantic application")
        visiting.add(local_ref)

        def binding(row: Any) -> Any:
            filler = row.filler
            if type(filler) is ApplicationFiller:
                filler = ApplicationFiller(persist(filler.node_ref))
            elif type(filler) in {BoundVariable, UnresolvedValue}:
                raise ValueError("normalized persistence rejects variable or unresolved fillers")
            elif type(filler) not in {GroundedReference, LiteralValue}:
                raise ValueError("normalized persistence received an unknown filler category")
            return type(row)(row.role_ref, filler)

        roles = tuple(binding(row) for row in source.roles)
        qualifiers = tuple(binding(row) for row in source.qualifiers)
        provisional = SemanticApplication("application:pending", source.operator, source.predicate_ref, roles, qualifiers)
        application_ref = stable_ref("semantic_application", _normalized_application_payload(provisional))
        result = SemanticApplication(application_ref, source.operator, source.predicate_ref, roles, qualifiers)
        visiting.remove(local_ref)
        persistent[local_ref] = result
        ordered.append(result)
        return application_ref

    root_application_ref = persist(root_ref)
    claim_payload = {
        "application_ref": root_application_ref,
        "stance": stance,
        "fact_ref": fact_ref,
        "source_ref": source_ref,
        "decision_ref": decision_ref,
        "occurrence_ref": occurrence_ref,
        "placement": placement,
        "placement_ref": placement_ref,
        "proof_refs": list(proof_refs),
        "authority_generation": authority_generation,
        "confidence_micros": confidence_micros,
        "asserted_world_revision": asserted_world_revision,
        "commit_transaction_ref": commit_transaction_ref,
    }
    claim_ref = stable_ref("semantic_claim", claim_payload)
    if authorization_payload is not None and type(authorization_payload) is not dict:
        raise TypeError("authorization_payload must be an exact dict when present")
    detached_authorization = None if authorization_payload is None else json.loads(
        _r3_canonical_json(authorization_payload)
    )
    return _PreparedNormalizedBatch(
        tuple(ordered), root_application_ref, claim_ref, claim_payload, detached_authorization
    )


def _normalized_binding_rows(application: Any) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for binding_kind, bindings in (("role", application.roles), ("qualifier", application.qualifiers)):
        for ordinal, binding in enumerate(bindings):
            filler = _normalized_filler_payload(binding.filler)
            if filler["kind"] == "grounded":
                filler_value = filler["target_ref"]
            elif filler["kind"] == "application":
                filler_value = filler["application_ref"]
            else:
                filler_value = _r3_canonical_json(
                    {"value_type": filler["value_type"], "value": filler["value"]}
                )
            material = {
                "application_ref": application.application_ref,
                "binding_kind": binding_kind,
                "ordinal": ordinal,
                "role_ref": binding.role_ref,
                "filler_kind": filler["kind"],
                "filler_value": filler_value,
            }
            rows.append({
                "binding_ref": stable_ref("semantic_binding", material),
                **material,
                "payload_hash": _payload_hash(material),
            })
    return tuple(rows)


def _prepare_normalized_alias_publication(
    fact: Fact,
    *,
    request_payload: Mapping[str, Any],
    receipt_payload: Mapping[str, Any],
    authority_generation: str,
    asserted_world_revision: int,
    commit_transaction_ref: str,
) -> _PreparedNormalizedBatch:
    """Derive the normalized mirror only from authenticated publication material."""
    from .expressions import GroundedReference, LiteralValue, RoleBinding, SemanticApplication, SemanticExpression
    from .r3_codec import thaw_json
    from .r3_effects import EffectReceipt

    if type(fact) is not Fact or fact.operator != "op:designation":
        raise ValueError("normalized alias mirror requires the authenticated designation fact")
    args = dict(fact.args)
    if set(args) != {"predicate_ref", "role:label_type", "role:surface", "role:target"}:
        raise ValueError("normalized alias fact has a noncanonical role set")
    if any(type(args[name]) is not str or not args[name] for name in args):
        raise ValueError("normalized alias fact values must be exact strings")
    if args["predicate_ref"] != args["role:label_type"]:
        raise ValueError("normalized alias label type/predicate mismatch")
    request = thaw_json(request_payload)
    if type(request) is not dict:
        raise TypeError("normalized alias request must decode to an exact dict")
    review = request.get("review")
    if type(review) is not dict or type(review.get("grant")) is not dict:
        raise ValueError("normalized alias publication lacks authenticated review")
    grant = review["grant"]
    review_ref = stable_ref("authenticated_alias_review", review)
    if (fact.proof.get("source") != review_ref or fact.proof.get("decision_ref") is None
            or fact.proof.get("publication_key") != request.get("publication_key")
            or grant.get("policy_ref") is None):
        raise ValueError("normalized alias publication lineage mismatch")
    receipt = EffectReceipt.from_dict(dict(receipt_payload))
    if (receipt.committed_fact_refs != (fact.fact_ref,)
            or receipt.operation_receipt_ref != review_ref
            or len(receipt.observed_delta_refs) != 1):
        raise ValueError("normalized alias receipt does not authenticate the fact")
    if fact.confidence != 1.0 or fact.derived is not False or fact.stance != "support":
        raise ValueError("normalized alias fact has noncanonical confidence/stance")
    application = SemanticApplication(
        "application:alias",
        "op:designation",
        args["predicate_ref"],
        (
            RoleBinding("role:label_type", GroundedReference(args["role:label_type"])),
            RoleBinding("role:surface", LiteralValue("string", args["role:surface"])),
            RoleBinding("role:target", GroundedReference(args["role:target"])),
        ),
    )
    expression = SemanticExpression.create(applications=(application,), root_refs=(application.application_ref,))
    return _prepare_normalized_application_claim(
        expression,
        root_ref=expression.root_refs[0],
        stance="support",
        fact_ref=fact.fact_ref,
        source_ref=review_ref,
        decision_ref=fact.proof["decision_ref"],
        occurrence_ref=receipt.observed_delta_refs[0],
        placement="reviewed",
        placement_ref=grant["policy_ref"],
        proof_refs=receipt.proof_refs,
        authority_generation=authority_generation,
        confidence_micros=1_000_000,
        asserted_world_revision=asserted_world_revision,
        commit_transaction_ref=commit_transaction_ref,
        authorization_payload={
            "kind": "authenticated_alias_publication",
            "request_payload": request,
            "receipt_payload": receipt.as_dict(),
        },
    )



@dataclass
class Obligation:
    obligation_ref: str
    kind: str
    source_ref: str
    target_ref: str
    priority: float
    satisfied: bool = False
    blockers: tuple[str, ...] = ()


@dataclass
class Session:
    session_ref: str
    phase: str = "opening"
    turn_index: int = 0
    participant_user: str = "participant:user"
    participant_system: str = "participant:system"
    focus_refs: list[str] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    revision: int = 0


@dataclass(frozen=True)
class RevisionPin:
    authority_generation: str
    world_revision: int
    session_revision: int
    episode_revision: int
    effect_revision: int
    model_identity: str | None

    _FIELDS = frozenset(
        {
            "authority_generation",
            "world_revision",
            "session_revision",
            "episode_revision",
            "effect_revision",
            "model_identity",
        }
    )
    _MAX_TEXT_LENGTH = 256
    _MAX_REVISION = 2**63 - 1

    def __post_init__(self) -> None:
        if type(self.authority_generation) is not str:
            raise TypeError("authority_generation must be exact str")
        if not self.authority_generation:
            raise ValueError("authority_generation must be nonempty")
        if len(self.authority_generation) > self._MAX_TEXT_LENGTH:
            raise ValueError("authority_generation exceeds 256 characters")
        for name in (
            "world_revision",
            "session_revision",
            "episode_revision",
            "effect_revision",
        ):
            value = getattr(self, name)
            if type(value) is not int:
                raise TypeError(f"{name} must be exact int")
            if value < 0 or value > self._MAX_REVISION:
                raise ValueError(f"{name} must be between 0 and 2**63 - 1")
        if self.model_identity is not None:
            if type(self.model_identity) is not str:
                raise TypeError("model_identity must be exact str or None")
            if not self.model_identity:
                raise ValueError("model_identity must be nonempty when present")
            if len(self.model_identity) > self._MAX_TEXT_LENGTH:
                raise ValueError("model_identity exceeds 256 characters")

    def as_dict(self) -> dict[str, Any]:
        return {
            "authority_generation": self.authority_generation,
            "world_revision": self.world_revision,
            "session_revision": self.session_revision,
            "episode_revision": self.episode_revision,
            "effect_revision": self.effect_revision,
            "model_identity": self.model_identity,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RevisionPin":
        if type(value) is not dict:
            raise TypeError("revision pin payload must be an exact dict")
        if len(value) != len(cls._FIELDS):
            raise ValueError("revision pin payload must have exactly six fields")
        if any(type(key) is not str for key in value):
            raise TypeError("revision pin field names must be exact str")
        keys = frozenset(value)
        if keys != cls._FIELDS:
            missing = sorted(cls._FIELDS - keys)
            unknown = sorted(keys - cls._FIELDS)
            raise ValueError(
                f"revision pin fields mismatch: missing={missing}, unknown={unknown}"
            )
        return cls(
            authority_generation=value["authority_generation"],
            world_revision=value["world_revision"],
            session_revision=value["session_revision"],
            episode_revision=value["episode_revision"],
            effect_revision=value["effect_revision"],
            model_identity=value["model_identity"],
        )

    @property
    def revision_ref(self) -> str:
        return stable_ref("revision_pin", self.as_dict())


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StaleRevisionError(Exception):
    """Raised when a commit's expected_revision does not match the current revision."""


class StoreActivationError(Exception):
    """Raised when a store cannot be activated due to corruption."""

    def __init__(self, message: str, recovery_receipt: "RecoveryReceipt") -> None:
        super().__init__(message)
        self.recovery_receipt = recovery_receipt


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommitReceipt:
    store: str
    parent_revision: int
    new_revision: int
    delta_hash: str
    transaction_ref: str


@dataclass(frozen=True)
class RecoveryReceipt:
    last_verified_revision: int
    corrupt_refs: tuple[str, ...]
    recommended_action: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()



def _r3_canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _r3_revision_transaction_ref(
    store: str, parent_revision: int, delta_hash: str
) -> str:
    return stable_ref(
        "txn",
        {
            "store": store,
            "parent": parent_revision,
            "delta_hash": delta_hash,
        },
    )


def _r3_insert_revision(
    conn: sqlite3.Connection,
    *,
    store: str,
    parent_revision: int,
    new_revision: int,
    delta_hash: str,
) -> None:
    conn.execute(
        "INSERT INTO revisions(store, revision, parent_revision, delta_hash, transaction_ref) "
        "VALUES(?, ?, ?, ?, ?)",
        (
            store,
            new_revision,
            parent_revision,
            delta_hash,
            _r3_revision_transaction_ref(store, parent_revision, delta_hash),
        ),
    )


def _r3_session_material(
    *, session_ref: str, turn_index: int, session_phase_ref: str, revision: int
) -> tuple[Session, dict[str, Any]]:
    session = Session(
        session_ref=session_ref,
        phase=session_phase_ref,
        turn_index=turn_index,
        participant_user="participant:user",
        participant_system="participant:system",
        focus_refs=[],
    )
    session.revision = revision
    return session, _session_to_payload(session)


def _r3_write_session_sqlite(
    conn: sqlite3.Connection,
    *,
    session_ref: str,
    turn_index: int,
    session_phase_ref: str,
    parent_revision: int,
    new_revision: int,
) -> None:
    _session, payload = _r3_session_material(
        session_ref=session_ref,
        turn_index=turn_index,
        session_phase_ref=session_phase_ref,
        revision=new_revision,
    )
    payload_json = _r3_canonical_json(payload)
    conn.execute(
        "INSERT INTO sessions(session_ref, revision, payload_json, payload_hash) "
        "VALUES(?, ?, ?, ?) "
        "ON CONFLICT(session_ref) DO UPDATE SET "
        "revision=excluded.revision, payload_json=excluded.payload_json, "
        "payload_hash=excluded.payload_hash",
        (session_ref, new_revision, payload_json, _payload_hash(payload)),
    )
    conn.execute(
        "INSERT INTO metadata(key, value) VALUES('session_revision', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(new_revision),),
    )
    _r3_insert_revision(
        conn,
        store="session",
        parent_revision=parent_revision,
        new_revision=new_revision,
        delta_hash=_payload_hash(payload),
    )


def _r3_terminal_turn(entry: Any) -> tuple[str, int, str]:
    request = entry.request_payload
    session_ref = request.get("session_ref")
    turn_index = request.get("turn_index")
    session_phase_ref = request.get("session_phase_ref", "opening")
    if type(session_ref) is not str or not session_ref:
        raise ValueError("terminal effect journal lacks session_ref")
    if type(turn_index) is not int or isinstance(turn_index, bool) or turn_index < 1:
        raise ValueError("terminal effect journal lacks a positive turn_index")
    if type(session_phase_ref) is not str or not session_phase_ref:
        raise ValueError("terminal effect journal lacks session_phase_ref")
    return session_ref, turn_index, session_phase_ref


def _r3_verify_journal_row(
    entry_json: str,
    entry_hash: str,
    receipt_json: str | None,
    receipt_hash: str | None,
) -> dict[str, Any]:
    entry = json.loads(entry_json)
    if _payload_hash(entry) != entry_hash:
        raise StoreActivationError(
            "R3 effect journal entry hash mismatch",
            RecoveryReceipt(0, (), "restore the journal from a verified backup"),
        )
    try:
        from .r3_persistence import EffectJournalEntry
        if type(entry) is not dict:
            raise TypeError("entry must be an exact dict")
        EffectJournalEntry.from_dict(entry)
    except (TypeError, ValueError, KeyError) as exc:
        raise StoreActivationError(
            f"R3 effect journal entry ABI/content mismatch: {exc}",
            RecoveryReceipt(0, (), "restore a current-ABI verified backup; do not reset the database"),
        ) from exc
    receipt = None if receipt_json is None else json.loads(receipt_json)
    if (receipt is None) != (receipt_hash is None):
        raise StoreActivationError(
            "R3 effect journal receipt hash presence mismatch",
            RecoveryReceipt(0, (), "restore the journal from a verified backup"),
        )
    if receipt is not None and _payload_hash(receipt) != receipt_hash:
        raise StoreActivationError(
            "R3 effect journal receipt hash mismatch",
            RecoveryReceipt(0, (), "restore the journal from a verified backup"),
        )
    if receipt is not None:
        from .r3_effects import EffectReceipt, NoEffectReceipt
        try:
            if type(receipt) is not dict:
                raise TypeError("receipt must be an exact dict")
            decoder = NoEffectReceipt if "reason" in receipt else EffectReceipt
            decoder.from_dict(receipt)
        except (TypeError, ValueError, KeyError) as exc:
            raise StoreActivationError(
                f"R3 effect journal receipt ABI/content mismatch: {exc}",
                RecoveryReceipt(0, (), "restore a current-ABI verified backup; do not reset the database"),
            ) from exc
    return {"entry": entry, "receipt": receipt}

def _fact_to_row(fact: Fact) -> dict[str, Any]:
    return {
        "fact_ref": fact.fact_ref,
        "operator": fact.operator,
        "args_json": json.dumps(dict(fact.args), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        "stance": fact.stance,
        "confidence": fact.confidence,
        "derived": fact.derived,
        "proof_json": json.dumps(dict(fact.proof), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
    }


def _row_to_fact(row: Mapping[str, Any]) -> Fact:
    return Fact(
        fact_ref=row["fact_ref"],
        operator=row["operator"],
        args=json.loads(row["args_json"]),
        stance=row["stance"],
        confidence=row["confidence"],
        derived=bool(row["derived"]),
        proof=json.loads(row["proof_json"]),
    )


def _fact_payload(fact: Fact) -> dict[str, Any]:
    return {
        "fact_ref": fact.fact_ref,
        "operator": fact.operator,
        "args": dict(fact.args),
        "stance": fact.stance,
        "confidence": fact.confidence,
        "derived": fact.derived,
        "proof": dict(fact.proof),
    }


def _session_to_payload(session: Session) -> dict[str, Any]:
    return {
        "session_ref": session.session_ref,
        "phase": session.phase,
        "turn_index": session.turn_index,
        "participant_user": session.participant_user,
        "participant_system": session.participant_system,
        "focus_refs": list(session.focus_refs),
        "revision": session.revision,
    }


def _payload_to_session(payload: Mapping[str, Any]) -> Session:
    s = Session(
        session_ref=payload["session_ref"],
        phase=payload.get("phase", "opening"),
        turn_index=payload.get("turn_index", 0),
        participant_user=payload.get("participant_user", "participant:user"),
        participant_system=payload.get("participant_system", "participant:system"),
        focus_refs=list(payload.get("focus_refs", [])),
    )
    s.revision = payload.get("revision", 0)
    return s


# ---------------------------------------------------------------------------
# SQLite sub-stores
# ---------------------------------------------------------------------------


class _SQLiteWorldStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.revision = self._load_revision()

    def _load_revision(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'world_revision'"
        ).fetchone()
        return int(row[0]) if row else 0

    def _save_revision(self, rev: int) -> None:
        self._conn.execute(
            "INSERT INTO metadata(key, value) VALUES('world_revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(rev),),
        )

    def commit(self, facts: Iterable[Fact], *, expected_revision: int) -> CommitReceipt:
        facts = tuple(facts)
        if expected_revision != self.revision:
            raise StaleRevisionError(
                f"world: expected revision {expected_revision}, got {self.revision}"
            )
        delta_payload = [_fact_payload(f) for f in facts]
        delta_hash = _payload_hash(delta_payload)
        transaction_ref = stable_ref("txn", {"store": "world", "parent": expected_revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            for fact in facts:
                if self._conn.execute(
                    "SELECT 1 FROM semantic_application_claims WHERE fact_ref=? LIMIT 1",
                    (fact.fact_ref,),
                ).fetchone() is not None:
                    raise ValueError("a normalized claim projection fact is immutable")
                row = _fact_to_row(fact)
                payload = _fact_payload(fact)
                self._conn.execute(
                    "INSERT INTO world_facts(fact_ref, operator, args_json, stance, confidence, derived, proof_json, payload_hash, revision) "
                    "VALUES(:fact_ref, :operator, :args_json, :stance, :confidence, :derived, :proof_json, :payload_hash, :revision) "
                    "ON CONFLICT(fact_ref) DO UPDATE SET operator=excluded.operator, args_json=excluded.args_json, "
                    "stance=excluded.stance, confidence=excluded.confidence, derived=excluded.derived, "
                    "proof_json=excluded.proof_json, payload_hash=excluded.payload_hash, revision=excluded.revision",
                    {**row, "payload_hash": _payload_hash(payload), "revision": new_revision},
                )
            self._save_revision(new_revision)
            self._conn.execute(
                "INSERT INTO revisions(store, revision, parent_revision, delta_hash, transaction_ref) "
                "VALUES('world', ?, ?, ?, ?)",
                (new_revision, expected_revision, delta_hash, transaction_ref),
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision
        return CommitReceipt(
            store="world",
            parent_revision=expected_revision,
            new_revision=new_revision,
            delta_hash=delta_hash,
            transaction_ref=transaction_ref,
        )

    def get(self, fact_ref: str) -> Fact | None:
        row = self._conn.execute(
            "SELECT fact_ref, operator, args_json, stance, confidence, derived, proof_json FROM world_facts WHERE fact_ref = ?",
            (fact_ref,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_fact(row)

    def verify(self) -> tuple[str, ...]:
        """Return tuple of corrupt fact_refs (payload hash mismatch)."""
        corrupt: list[str] = []
        for row in self._conn.execute(
            "SELECT fact_ref, operator, args_json, stance, confidence, derived, proof_json, payload_hash FROM world_facts"
        ).fetchall():
            payload = {
                "fact_ref": row[0],
                "operator": row[1],
                "args": json.loads(row[2]),
                "stance": row[3],
                "confidence": row[4],
                "derived": bool(row[5]),
                "proof": json.loads(row[6]),
            }
            if _payload_hash(payload) != row[7]:
                corrupt.append(row[0])
        return tuple(corrupt)


class _SQLiteSessionStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.revision = self._load_revision()

    def _load_revision(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'session_revision'"
        ).fetchone()
        return int(row[0]) if row else 0

    def _save_revision(self, rev: int) -> None:
        self._conn.execute(
            "INSERT INTO metadata(key, value) VALUES('session_revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(rev),),
        )

    def create(self) -> Session:
        new_revision = self.revision + 1
        ref = stable("session", new_revision)
        session = Session(session_ref=ref)
        session.revision = new_revision
        payload = _session_to_payload(session)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "INSERT INTO sessions(session_ref, revision, payload_json, payload_hash) VALUES(?, ?, ?, ?)",
                (ref, new_revision, json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False), _payload_hash(payload)),
            )
            self._save_revision(new_revision)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision
        return session

    def get(self, session_ref: str) -> Session | None:
        row = self._conn.execute(
            "SELECT payload_json FROM sessions WHERE session_ref = ?", (session_ref,)
        ).fetchone()
        if row is None:
            return None
        return _payload_to_session(json.loads(row[0]))

    def verify(self) -> tuple[str, ...]:
        corrupt: list[str] = []
        for row in self._conn.execute(
            "SELECT session_ref, payload_json, payload_hash FROM sessions"
        ).fetchall():
            if _payload_hash(json.loads(row[1])) != row[2]:
                corrupt.append(row[0])
        return tuple(corrupt)


class _SQLiteEpisodeStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.revision = self._load_revision()

    def _load_revision(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'episode_revision'"
        ).fetchone()
        return int(row[0]) if row else 0

    def _save_revision(self, rev: int) -> None:
        self._conn.execute(
            "INSERT INTO metadata(key, value) VALUES('episode_revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(rev),),
        )

    def append(self, row: Mapping[str, Any]) -> None:
        new_revision = self.revision + 1
        episode_ref = stable("episode", new_revision)
        payload = dict(row)
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "INSERT INTO episodes(episode_ref, session_ref, payload_json, payload_hash, revision, immutable) "
                "VALUES(?, ?, ?, ?, ?, 1)",
                (episode_ref, payload.get("session_ref", ""), payload_json, _payload_hash(payload), new_revision),
            )
            self._save_revision(new_revision)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision

    def rows(self) -> tuple[dict[str, Any], ...]:
        result = []
        for row in self._conn.execute(
            "SELECT payload_json FROM episodes ORDER BY revision"
        ).fetchall():
            result.append(json.loads(row[0]))
        return tuple(result)

    def verify(self) -> tuple[str, ...]:
        corrupt: list[str] = []
        for row in self._conn.execute(
            "SELECT episode_ref, payload_json, payload_hash FROM episodes"
        ).fetchall():
            if _payload_hash(json.loads(row[1])) != row[2]:
                corrupt.append(row[0])
        return tuple(corrupt)


class _SQLiteEffectStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.revision = self._load_revision()

    def _load_revision(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'effect_revision'"
        ).fetchone()
        return int(row[0]) if row else 0

    def _save_revision(self, rev: int) -> None:
        self._conn.execute(
            "INSERT INTO metadata(key, value) VALUES('effect_revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(rev),),
        )

    def commit(self, effect: Mapping[str, Any]) -> CommitReceipt:
        effect_key = effect["effect_key"]
        payload = dict(effect.get("payload", {}))
        # Check for duplicate key — return original receipt
        existing = self._conn.execute(
            "SELECT receipt_json FROM effects WHERE effect_key = ?", (effect_key,)
        ).fetchone()
        if existing is not None:
            r = json.loads(existing[0])
            return CommitReceipt(
                store=r["store"],
                parent_revision=r["parent_revision"],
                new_revision=r["new_revision"],
                delta_hash=r["delta_hash"],
                transaction_ref=r["transaction_ref"],
            )

        new_revision = self.revision + 1
        delta_hash = _payload_hash(payload)
        transaction_ref = stable_ref("txn", {"store": "effects", "parent": self.revision, "delta_hash": delta_hash})
        receipt = CommitReceipt(
            store="effects",
            parent_revision=self.revision,
            new_revision=new_revision,
            delta_hash=delta_hash,
            transaction_ref=transaction_ref,
        )
        receipt_json = json.dumps({
            "store": receipt.store,
            "parent_revision": receipt.parent_revision,
            "new_revision": receipt.new_revision,
            "delta_hash": receipt.delta_hash,
            "transaction_ref": receipt.transaction_ref,
        }, sort_keys=True, separators=(",", ":"))
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "INSERT INTO effects(effect_key, payload_json, payload_hash, revision, receipt_json) "
                "VALUES(?, ?, ?, ?, ?)",
                (effect_key, json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False), delta_hash, new_revision, receipt_json),
            )
            self._save_revision(new_revision)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision
        return receipt

    def get(self, effect_key: str) -> dict[str, Any] | None:
        """Return the stored payload for ``effect_key``, or ``None``."""
        row = self._conn.execute(
            "SELECT payload_json FROM effects WHERE effect_key = ?", (effect_key,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def verify(self) -> tuple[str, ...]:
        corrupt: list[str] = []
        for row in self._conn.execute(
            "SELECT effect_key, payload_json, payload_hash FROM effects"
        ).fetchall():
            if _payload_hash(json.loads(row[1])) != row[2]:
                corrupt.append(row[0])
        return tuple(corrupt)


class _SQLiteModelStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.revision = self._load_revision()

    def _load_revision(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'model_revision'"
        ).fetchone()
        return int(row[0]) if row else 0

    def _save_revision(self, rev: int) -> None:
        self._conn.execute(
            "INSERT INTO metadata(key, value) VALUES('model_revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(rev),),
        )

    def register(self, model_identity: str, payload: Mapping[str, Any]) -> None:
        new_revision = self.revision + 1
        data = {**dict(payload), "model_identity": model_identity}
        payload_json = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "INSERT INTO models(model_identity, payload_json, payload_hash, revision) "
                "VALUES(?, ?, ?, ?) "
                "ON CONFLICT(model_identity) DO UPDATE SET payload_json=excluded.payload_json, "
                "payload_hash=excluded.payload_hash, revision=excluded.revision",
                (model_identity, payload_json, _payload_hash(data), new_revision),
            )
            self._save_revision(new_revision)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision

    def get(self, model_identity: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT payload_json FROM models WHERE model_identity = ?", (model_identity,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def verify(self) -> tuple[str, ...]:
        corrupt: list[str] = []
        for row in self._conn.execute(
            "SELECT model_identity, payload_json, payload_hash FROM models"
        ).fetchall():
            if _payload_hash(json.loads(row[1])) != row[2]:
                corrupt.append(row[0])
        return tuple(corrupt)


class _SQLiteFocusStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.revision = self._load_revision()

    def _load_revision(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'focus_revision'"
        ).fetchone()
        return int(row[0]) if row else 0

    def _save_revision(self, rev: int) -> None:
        self._conn.execute(
            "INSERT INTO metadata(key, value) VALUES('focus_revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(rev),),
        )

    def commit(self, focus_ref: str, session_ref: str, payload: Mapping[str, Any], *, expected_revision: int) -> CommitReceipt:
        if type(focus_ref) is not str or not focus_ref:
            raise TypeError("focus_ref must be exact nonempty str")
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        if expected_revision != self.revision:
            raise StaleRevisionError(f"focus: expected {expected_revision}, got {self.revision}")
        new_revision = self.revision + 1
        payload_json = json.dumps(
            {**dict(payload), "focus_ref": focus_ref, "session_ref": session_ref},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        # Hash the stored JSON value, including tuple-to-list normalization.
        delta_hash = _payload_hash(json.loads(payload_json))
        transaction_ref = stable_ref("txn", {"store": "focus", "parent": expected_revision, "delta_hash": delta_hash})
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "INSERT INTO focus(focus_ref, session_ref, payload_json, payload_hash, revision) "
                "VALUES(?, ?, ?, ?, ?) "
                "ON CONFLICT(focus_ref) DO UPDATE SET session_ref=excluded.session_ref, payload_json=excluded.payload_json, "
                "payload_hash=excluded.payload_hash, revision=excluded.revision",
                (focus_ref, session_ref, payload_json, delta_hash, new_revision),
            )
            self._save_revision(new_revision)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision
        return CommitReceipt("focus", expected_revision, new_revision, delta_hash, transaction_ref)

    def get(self, focus_ref: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT payload_json FROM focus WHERE focus_ref = ?", (focus_ref,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def recent_rows(self, maximum: int, session_ref: str | None) -> tuple:
        # Both orderings have physical indexes. Session selection precedes LIMIT.
        where = "" if session_ref is None else " WHERE session_ref=?"
        parameters = (maximum,) if session_ref is None else (session_ref, maximum)
        return tuple(
            (ref, session, json.loads(payload), payload_hash, revision)
            for ref, session, payload, payload_hash, revision in self._conn.execute(
                "SELECT focus_ref, session_ref, payload_json, payload_hash, revision "
                f"FROM focus{where} ORDER BY revision DESC, focus_ref LIMIT ?",
                parameters,
            )
        )

    def verify(self) -> tuple[str, ...]:
        corrupt: list[str] = []
        for row in self._conn.execute(
            "SELECT focus_ref, payload_json, payload_hash FROM focus"
        ).fetchall():
            if _payload_hash(json.loads(row[1])) != row[2]:
                corrupt.append(row[0])
        return tuple(corrupt)


class _SQLiteObligationStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.revision = self._load_revision()

    def _load_revision(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'obligation_revision'"
        ).fetchone()
        return int(row[0]) if row else 0

    def _save_revision(self, rev: int) -> None:
        self._conn.execute(
            "INSERT INTO metadata(key, value) VALUES('obligation_revision', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(rev),),
        )

    def commit(self, obligation_ref: str, session_ref: str, payload: Mapping[str, Any], *, expected_revision: int, resolved: bool = False) -> CommitReceipt:
        if expected_revision != self.revision:
            raise StaleRevisionError(f"obligations: expected {expected_revision}, got {self.revision}")
        new_revision = self.revision + 1
        data = {**dict(payload), "obligation_ref": obligation_ref, "session_ref": session_ref, "resolved": resolved}
        delta_hash = _payload_hash(data)
        transaction_ref = stable_ref("txn", {"store": "obligations", "parent": expected_revision, "delta_hash": delta_hash})
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "INSERT INTO obligations(obligation_ref, session_ref, payload_json, payload_hash, revision, resolved) "
                "VALUES(?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(obligation_ref) DO UPDATE SET payload_json=excluded.payload_json, "
                "payload_hash=excluded.payload_hash, revision=excluded.revision, resolved=excluded.resolved",
                (obligation_ref, session_ref, json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False), delta_hash, new_revision, int(resolved)),
            )
            self._save_revision(new_revision)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision
        return CommitReceipt("obligations", expected_revision, new_revision, delta_hash, transaction_ref)

    def complete(
        self,
        pending_ref: str,
        completed_ref: str,
        session_ref: str,
        completed_payload: Mapping[str, Any],
        *,
        expected_revision: int,
    ) -> CommitReceipt:
        """Atomically resolve one pending row and persist its completed record."""
        if expected_revision != self.revision:
            raise StaleRevisionError(
                f"obligations: expected {expected_revision}, got {self.revision}"
            )
        if pending_ref == completed_ref:
            raise ValueError("completed obligation ref must differ from pending ref")
        row = self._conn.execute(
            "SELECT session_ref, payload_json FROM obligations WHERE obligation_ref = ?",
            (pending_ref,),
        ).fetchone()
        if row is None:
            raise KeyError(pending_ref)
        if str(row[0]) != session_ref:
            raise ValueError("pending obligation session mismatch")
        pending_data = json.loads(row[1])
        if pending_data.get("resolved") is True:
            raise ValueError("pending obligation is already resolved")
        pending_data["resolved"] = True
        completed_data = {
            **dict(completed_payload),
            "obligation_ref": completed_ref,
            "session_ref": session_ref,
            "resolved": True,
        }
        new_revision = self.revision + 1
        delta_hash = _payload_hash({
            "pending_ref": pending_ref,
            "pending": pending_data,
            "completed_ref": completed_ref,
            "completed": completed_data,
        })
        transaction_ref = stable_ref(
            "txn",
            {"store": "obligations", "parent": expected_revision, "delta_hash": delta_hash},
        )
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "UPDATE obligations SET payload_json=?, payload_hash=?, revision=?, resolved=1 "
                "WHERE obligation_ref=? AND resolved=0",
                (
                    json.dumps(pending_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                    _payload_hash(pending_data),
                    new_revision,
                    pending_ref,
                ),
            )
            if self._conn.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValueError("pending obligation could not be resolved")
            self._conn.execute(
                "INSERT INTO obligations(obligation_ref, session_ref, payload_json, payload_hash, revision, resolved) "
                "VALUES(?, ?, ?, ?, ?, 1)",
                (
                    completed_ref,
                    session_ref,
                    json.dumps(completed_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                    _payload_hash(completed_data),
                    new_revision,
                ),
            )
            self._save_revision(new_revision)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.revision = new_revision
        return CommitReceipt(
            "obligations", expected_revision, new_revision, delta_hash, transaction_ref
        )

    def get(self, obligation_ref: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT payload_json FROM obligations WHERE obligation_ref = ?", (obligation_ref,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def verify(self) -> tuple[str, ...]:
        corrupt: list[str] = []
        for row in self._conn.execute(
            "SELECT obligation_ref, payload_json, payload_hash FROM obligations"
        ).fetchall():
            if _payload_hash(json.loads(row[1])) != row[2]:
                corrupt.append(row[0])
        return tuple(corrupt)

    def keyed_row(self, obligation_ref: str) -> tuple[Any, ...] | None:
        row = self._conn.execute(
            "SELECT obligation_ref, session_ref, payload_json, payload_hash, revision, resolved "
            "FROM obligations WHERE obligation_ref=?", (obligation_ref,),
        ).fetchone()
        if row is None:
            return None
        return (row[0], row[1], json.loads(row[2]), row[3], row[4], row[5])


# ---------------------------------------------------------------------------
# SQLite SemanticStores
# ---------------------------------------------------------------------------


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
    store TEXT NOT NULL,
    revision INTEGER NOT NULL,
    parent_revision INTEGER NOT NULL,
    delta_hash TEXT NOT NULL,
    transaction_ref TEXT NOT NULL,
    PRIMARY KEY(store, revision)
);
CREATE TABLE IF NOT EXISTS world_facts (
    fact_ref TEXT PRIMARY KEY,
    operator TEXT NOT NULL,
    args_json TEXT NOT NULL,
    stance TEXT NOT NULL,
    confidence REAL NOT NULL,
    derived INTEGER NOT NULL,
    proof_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    session_ref TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS focus (
    focus_ref TEXT PRIMARY KEY,
    session_ref TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS focus_session_recent ON focus(session_ref, revision DESC, focus_ref);
CREATE INDEX IF NOT EXISTS focus_recent ON focus(revision DESC, focus_ref);
CREATE TABLE IF NOT EXISTS obligations (
    obligation_ref TEXT PRIMARY KEY,
    session_ref TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS obligations_session_pending ON obligations(session_ref, resolved, revision, obligation_ref);
CREATE TABLE IF NOT EXISTS episodes (
    episode_ref TEXT PRIMARY KEY,
    session_ref TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL,
    immutable INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS effects (
    effect_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL,
    receipt_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS models (
    model_identity TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS r3_effect_journal (
    idempotency_key TEXT PRIMARY KEY,
    entry_json TEXT NOT NULL,
    entry_hash TEXT NOT NULL,
    receipt_json TEXT,
    receipt_hash TEXT,
    effect_revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS semantic_applications (
    application_ref TEXT PRIMARY KEY,
    operator TEXT NOT NULL,
    predicate_ref TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS semantic_application_bindings (
    binding_ref TEXT PRIMARY KEY,
    application_ref TEXT NOT NULL REFERENCES semantic_applications(application_ref),
    binding_kind TEXT NOT NULL CHECK(binding_kind IN ('role','qualifier')),
    ordinal INTEGER NOT NULL,
    role_ref TEXT NOT NULL,
    filler_kind TEXT NOT NULL CHECK(filler_kind IN ('grounded','literal','application')),
    filler_value TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    UNIQUE(application_ref,binding_kind,ordinal),
    UNIQUE(application_ref,binding_kind,role_ref)
);
CREATE INDEX IF NOT EXISTS semantic_application_bindings_child
    ON semantic_application_bindings(filler_kind,filler_value,application_ref);
CREATE TABLE IF NOT EXISTS semantic_application_claims (
    claim_ref TEXT PRIMARY KEY,
    application_ref TEXT NOT NULL REFERENCES semantic_applications(application_ref),
    stance TEXT NOT NULL CHECK(stance IN ('support','deny')),
    fact_ref TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    decision_ref TEXT NOT NULL,
    occurrence_ref TEXT NOT NULL,
    placement TEXT NOT NULL,
    placement_ref TEXT NOT NULL,
    proof_json TEXT NOT NULL,
    authority_generation TEXT NOT NULL,
    confidence_micros INTEGER NOT NULL,
    asserted_world_revision INTEGER NOT NULL,
    commit_transaction_ref TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS semantic_application_claims_app
    ON semantic_application_claims(application_ref,claim_ref);
CREATE UNIQUE INDEX IF NOT EXISTS semantic_application_claims_fact
    ON semantic_application_claims(fact_ref);
CREATE TABLE IF NOT EXISTS semantic_claim_target_postings (
    target_ref TEXT NOT NULL,
    claim_ref TEXT NOT NULL REFERENCES semantic_application_claims(claim_ref),
    PRIMARY KEY(target_ref,claim_ref)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS semantic_claim_retractions (
    retraction_ref TEXT PRIMARY KEY,
    claim_ref TEXT NOT NULL REFERENCES semantic_application_claims(claim_ref),
    source_ref TEXT NOT NULL,
    occurrence_ref TEXT NOT NULL,
    proof_json TEXT NOT NULL,
    asserted_world_revision INTEGER NOT NULL,
    commit_transaction_ref TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS semantic_claim_retractions_claim
    ON semantic_claim_retractions(claim_ref,retraction_ref);
"""

_NORMALIZED_SCHEMA_COLUMNS = {
    "semantic_applications": (
        "application_ref", "operator", "predicate_ref", "payload_hash",
    ),
    "semantic_application_bindings": (
        "binding_ref", "application_ref", "binding_kind", "ordinal", "role_ref",
        "filler_kind", "filler_value", "payload_hash",
    ),
    "semantic_application_claims": (
        "claim_ref", "application_ref", "stance", "fact_ref", "source_ref",
        "decision_ref", "occurrence_ref", "placement", "placement_ref", "proof_json",
        "authority_generation", "confidence_micros", "asserted_world_revision",
        "commit_transaction_ref", "payload_hash",
    ),
    "semantic_claim_target_postings": ("target_ref", "claim_ref"),
    "semantic_claim_retractions": (
        "retraction_ref", "claim_ref", "source_ref", "occurrence_ref", "proof_json",
        "asserted_world_revision", "commit_transaction_ref", "payload_hash",
    ),
}

_NORMALIZED_UNIQUE_INDEXES = {
    "semantic_applications": {("application_ref",)},
    "semantic_application_bindings": {
        ("binding_ref",),
        ("application_ref", "binding_kind", "ordinal"),
        ("application_ref", "binding_kind", "role_ref"),
    },
    "semantic_application_claims": {("claim_ref",), ("fact_ref",)},
    "semantic_claim_target_postings": {("target_ref", "claim_ref")},
    "semantic_claim_retractions": {("retraction_ref",)},
}

_NORMALIZED_FOREIGN_KEYS = {
    "semantic_applications": set(),
    "semantic_application_bindings": {("application_ref", "semantic_applications", "application_ref")},
    "semantic_application_claims": {("application_ref", "semantic_applications", "application_ref")},
    "semantic_claim_target_postings": {("claim_ref", "semantic_application_claims", "claim_ref")},
    "semantic_claim_retractions": {("claim_ref", "semantic_application_claims", "claim_ref")},
}

_NORMALIZED_TABLE_SIGNATURES = {
    "semantic_applications": """CREATE TABLE semantic_applications (
        application_ref TEXT PRIMARY KEY, operator TEXT NOT NULL,
        predicate_ref TEXT NOT NULL, payload_hash TEXT NOT NULL)""",
    "semantic_application_bindings": """CREATE TABLE semantic_application_bindings (
        binding_ref TEXT PRIMARY KEY,
        application_ref TEXT NOT NULL REFERENCES semantic_applications(application_ref),
        binding_kind TEXT NOT NULL CHECK(binding_kind IN ('role','qualifier')),
        ordinal INTEGER NOT NULL, role_ref TEXT NOT NULL,
        filler_kind TEXT NOT NULL CHECK(filler_kind IN ('grounded','literal','application')),
        filler_value TEXT NOT NULL, payload_hash TEXT NOT NULL,
        UNIQUE(application_ref,binding_kind,ordinal),
        UNIQUE(application_ref,binding_kind,role_ref))""",
    "semantic_application_claims": """CREATE TABLE semantic_application_claims (
        claim_ref TEXT PRIMARY KEY,
        application_ref TEXT NOT NULL REFERENCES semantic_applications(application_ref),
        stance TEXT NOT NULL CHECK(stance IN ('support','deny')),
        fact_ref TEXT NOT NULL, source_ref TEXT NOT NULL, decision_ref TEXT NOT NULL,
        occurrence_ref TEXT NOT NULL, placement TEXT NOT NULL, placement_ref TEXT NOT NULL,
        proof_json TEXT NOT NULL, authority_generation TEXT NOT NULL,
        confidence_micros INTEGER NOT NULL, asserted_world_revision INTEGER NOT NULL,
        commit_transaction_ref TEXT NOT NULL, payload_hash TEXT NOT NULL)""",
    "semantic_claim_target_postings": """CREATE TABLE semantic_claim_target_postings (
        target_ref TEXT NOT NULL,
        claim_ref TEXT NOT NULL REFERENCES semantic_application_claims(claim_ref),
        PRIMARY KEY(target_ref,claim_ref)) WITHOUT ROWID""",
    "semantic_claim_retractions": """CREATE TABLE semantic_claim_retractions (
        retraction_ref TEXT PRIMARY KEY,
        claim_ref TEXT NOT NULL REFERENCES semantic_application_claims(claim_ref),
        source_ref TEXT NOT NULL, occurrence_ref TEXT NOT NULL, proof_json TEXT NOT NULL,
        asserted_world_revision INTEGER NOT NULL, commit_transaction_ref TEXT NOT NULL,
        payload_hash TEXT NOT NULL)""",
}

_NORMALIZED_INDEX_SIGNATURES = {
    "semantic_application_bindings_child": """CREATE INDEX semantic_application_bindings_child
        ON semantic_application_bindings(filler_kind,filler_value,application_ref)""",
    "semantic_application_claims_app": """CREATE INDEX semantic_application_claims_app
        ON semantic_application_claims(application_ref,claim_ref)""",
    "semantic_application_claims_fact": """CREATE UNIQUE INDEX semantic_application_claims_fact
        ON semantic_application_claims(fact_ref)""",
    "semantic_claim_retractions_claim": """CREATE INDEX semantic_claim_retractions_claim
        ON semantic_claim_retractions(claim_ref,retraction_ref)""",
}


def _normalized_schema_manifest_errors(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Validate the one normalized-store schema manifest without per-cycle gates."""
    errors: list[str] = []
    def normalize(value: object) -> str:
        result = " ".join(value.split()) if type(value) is str else ""
        for old, new in ((" (", "("), ("( ", "("), (" )", ")"), (", ", ",")):
            result = result.replace(old, new)
        return result
    for table, expected_columns in _NORMALIZED_SCHEMA_COLUMNS.items():
        schema_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if schema_row is None or normalize(schema_row[0]) != normalize(_NORMALIZED_TABLE_SIGNATURES[table]):
            errors.append(f"{table}:definition")
        table_info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if tuple(row[1] for row in table_info) != expected_columns:
            errors.append(table)
            continue
        unique_columns = {
            tuple(index_row[2] for index_row in conn.execute(f"PRAGMA index_info({index[1]})"))
            for index in conn.execute(f"PRAGMA index_list({table})")
            if index[2] == 1
        }
        if not _NORMALIZED_UNIQUE_INDEXES[table] <= unique_columns:
            errors.append(f"{table}:unique")
        foreign_keys = {
            (row[3], row[2], row[4])
            for row in conn.execute(f"PRAGMA foreign_key_list({table})")
        }
        if foreign_keys != _NORMALIZED_FOREIGN_KEYS[table]:
            errors.append(f"{table}:foreign_keys")
    required_indexes = {
        "semantic_application_bindings_child": (0, ("filler_kind", "filler_value", "application_ref")),
        "semantic_application_claims_app": (0, ("application_ref", "claim_ref")),
        "semantic_application_claims_fact": (1, ("fact_ref",)),
        "semantic_claim_retractions_claim": (0, ("claim_ref", "retraction_ref")),
    }
    for name, (unique, columns) in required_indexes.items():
        row = conn.execute(
            "SELECT tbl_name FROM sqlite_master WHERE type='index' AND name=?", (name,)
        ).fetchone()
        if row is None:
            errors.append(name)
            continue
        listed = next((index for index in conn.execute(f"PRAGMA index_list({row[0]})") if index[1] == name), None)
        actual_columns = tuple(index[2] for index in conn.execute(f"PRAGMA index_info({name})"))
        if listed is None or listed[2] != unique or actual_columns != columns:
            errors.append(name)
        sql_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,)
        ).fetchone()
        if sql_row is None or normalize(sql_row[0]) != normalize(_NORMALIZED_INDEX_SIGNATURES[name]):
            errors.append(f"{name}:definition")
    explicit_indexes = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL "
            "AND tbl_name IN (?,?,?,?,?)",
            tuple(_NORMALIZED_SCHEMA_COLUMNS),
        )
    }
    if explicit_indexes != set(_NORMALIZED_INDEX_SIGNATURES):
        errors.append("normalized_explicit_indexes")
    return tuple(dict.fromkeys(errors))


_LEGACY_DESIGNATION_INDEXES = (
    "world_designation_surface_language", "world_designation_surface",
    "world_designation_folded", "world_designation_target",
)
_DESIGNATION_TEXT_INDEX_SQL = {
    "world_designation_surface_language_text_v2": """CREATE INDEX IF NOT EXISTS world_designation_surface_language_text_v2
        ON world_facts(operator, json_extract(args_json, '$."role:surface"'),
            json_extract(proof_json, '$.alias_language'), fact_ref)
        WHERE operator='op:designation' AND json_type(args_json, '$."role:surface"')='text'
            AND json_type(proof_json, '$.alias_language')='text'""",
    "world_designation_surface_text_v2": """CREATE INDEX IF NOT EXISTS world_designation_surface_text_v2
        ON world_facts(operator, json_extract(args_json, '$."role:surface"'), fact_ref)
        WHERE operator='op:designation' AND json_type(args_json, '$."role:surface"')='text'""",
    "world_designation_folded_text_v2": """CREATE INDEX IF NOT EXISTS world_designation_folded_text_v2
        ON world_facts(operator, unicode_casefold(json_extract(args_json, '$."role:surface"')),
            json_extract(proof_json, '$.alias_language'), fact_ref)
        WHERE operator='op:designation' AND json_type(args_json, '$."role:surface"')='text'
            AND json_type(proof_json, '$.alias_language')='text'""",
    "world_designation_target_text_v2": """CREATE INDEX IF NOT EXISTS world_designation_target_text_v2
        ON world_facts(operator, json_extract(args_json, '$."role:target"'),
            json_extract(proof_json, '$.alias_language'), fact_ref)
        WHERE operator='op:designation' AND json_type(args_json, '$."role:target"')='text'
            AND json_type(proof_json, '$.alias_language')='text'""",
}


def register_sqlite_functions(conn: sqlite3.Connection) -> None:
    """Install deterministic index functions on runtime or read-only connections."""
    conn.create_function("unicode_casefold", 1,
        lambda value: value.casefold() if type(value) is str else None, deterministic=True)
    conn.create_function("query_index_keys", 2, _query_index_keys_json, deterministic=True)


def _query_value(value: object) -> str:
    # Exactly the existing QUERY fact projection, including bool before int.
    return ("true" if value else "false") if type(value) is bool else str(value)


def _query_index_keys(operator: str, args: Mapping[str, Any]):
    predicate = str(args.get("predicate_ref", operator))
    return ((operator, predicate, "", ""), *(
        (operator, predicate, str(role), _query_value(value))
        for role, value in args.items() if role != "predicate_ref"))


def _query_index_keys_json(operator: str, args_json: str) -> str:
    return json.dumps(_query_index_keys(operator, json.loads(args_json)), ensure_ascii=False)


def _query_index_statements() -> dict[str, str]:
    insert = """INSERT INTO world_query_keys(operator,predicate,role,value,fact_ref)
        SELECT json_extract(j.value,'$[0]'),json_extract(j.value,'$[1]'),
            json_extract(j.value,'$[2]'),json_extract(j.value,'$[3]'),NEW.fact_ref
        FROM json_each(query_index_keys(NEW.operator,NEW.args_json)) AS j;"""
    return {
        "world_query_keys": """CREATE TABLE world_query_keys (
            operator TEXT NOT NULL, predicate TEXT NOT NULL, role TEXT NOT NULL,
            value TEXT NOT NULL, fact_ref TEXT NOT NULL,
            PRIMARY KEY(operator,predicate,role,value,fact_ref)) WITHOUT ROWID""",
        "world_query_keys_fact": "CREATE INDEX world_query_keys_fact ON world_query_keys(fact_ref)",
        "world_query_insert": "CREATE TRIGGER world_query_insert AFTER INSERT ON world_facts BEGIN " + insert + " END",
        "world_query_update": "CREATE TRIGGER world_query_update AFTER UPDATE OF fact_ref,operator,args_json ON world_facts BEGIN "
            "DELETE FROM world_query_keys WHERE fact_ref=OLD.fact_ref; " + insert + " END",
        "world_query_delete": "CREATE TRIGGER world_query_delete AFTER DELETE ON world_facts BEGIN "
            "DELETE FROM world_query_keys WHERE fact_ref=OLD.fact_ref; END",
    }


def _verify_normalized_sqlite(conn: sqlite3.Connection, authority_generation: str) -> tuple[str, ...]:
    """Verify normalized payload identity, categories, indexes and lineage."""
    from .expressions import (
        ApplicationFiller,
        ExpressionBounds,
        GroundedReference,
        LiteralValue,
        RoleBinding,
        SemanticApplication,
    )

    corrupt: list[str] = []
    headers: dict[str, tuple[str, str, str]] = {}
    for row in conn.execute(
        "SELECT application_ref,operator,predicate_ref,payload_hash FROM semantic_applications ORDER BY application_ref"
    ).fetchall():
        headers[row[0]] = (row[1], row[2], row[3])

    binding_rows: dict[str, list[tuple[str, int, str, str, str]]] = {}
    for row in conn.execute(
        "SELECT binding_ref,application_ref,binding_kind,ordinal,role_ref,filler_kind,filler_value,payload_hash "
        "FROM semantic_application_bindings ORDER BY application_ref,binding_kind,ordinal"
    ):
        material = {"application_ref": row[1], "binding_kind": row[2], "ordinal": row[3],
                    "role_ref": row[4], "filler_kind": row[5], "filler_value": row[6]}
        if (row[1] not in headers or stable_ref("semantic_binding", material) != row[0]
                or _payload_hash(material) != row[7]):
            corrupt.append(f"semantic_binding:{row[0]}")
            continue
        binding_rows.setdefault(row[1], []).append((row[2], row[3], row[4], row[5], row[6]))

    applications: dict[str, dict[str, Any]] = {}
    for app_ref, (operator, predicate_ref, payload_hash) in headers.items():
        try:
            roles: list[RoleBinding] = []
            qualifiers: list[RoleBinding] = []
            ordinals = {"role": [], "qualifier": []}
            for kind, ordinal, role_ref, filler_kind, filler_value in binding_rows.get(app_ref, ()):
                ordinals[kind].append(ordinal)
                if filler_kind == "grounded":
                    filler = GroundedReference(filler_value)
                elif filler_kind == "application":
                    if filler_value not in headers:
                        raise ValueError("missing normalized application child")
                    filler = ApplicationFiller(filler_value)
                elif filler_kind == "literal":
                    literal = json.loads(filler_value)
                    if type(literal) is not dict or set(literal) != {"value_type", "value"}:
                        raise ValueError("invalid normalized literal")
                    filler = LiteralValue(literal["value_type"], literal["value"])
                else:
                    raise ValueError("invalid normalized filler")
                (roles if kind == "role" else qualifiers).append(RoleBinding(role_ref, filler))
            if any(values != list(range(len(values))) for values in ordinals.values()):
                raise ValueError("normalized binding ordinals are not contiguous")
            application = SemanticApplication(app_ref, operator, predicate_ref, tuple(roles), tuple(qualifiers))
            payload = _normalized_application_payload(application)
            if stable_ref("semantic_application", payload) != app_ref or _payload_hash(payload) != payload_hash:
                raise ValueError("normalized application identity mismatch")
            applications[app_ref] = payload
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            corrupt.append(f"semantic_application:{app_ref}")

    bounds = ExpressionBounds()
    for root_ref in applications:
        seen: set[str] = set()
        visiting: set[str] = set()

        def validate_graph(app_ref: str, depth: int) -> None:
            if app_ref in visiting:
                raise ValueError("normalized application graph is cyclic")
            if app_ref in seen:
                return
            if depth > bounds.max_depth or len(seen) >= bounds.max_applications:
                raise ValueError("normalized application graph exceeds release bounds")
            visiting.add(app_ref)
            for binding in (*applications[app_ref]["roles"], *applications[app_ref]["qualifiers"]):
                filler = binding["filler"]
                if filler["kind"] == "application":
                    validate_graph(filler["application_ref"], depth + 1)
            visiting.remove(app_ref)
            seen.add(app_ref)

        try:
            validate_graph(root_ref, 1)
        except (KeyError, ValueError):
            corrupt.append(f"semantic_application:{root_ref}")

    claims: set[str] = set()
    claims_by_fact: dict[str, str] = {}
    expected_claim_postings: set[tuple[str, str]] = set()

    def closure_targets(root_ref: str) -> set[str]:
        targets: set[str] = set()
        pending = [root_ref]
        seen: set[str] = set()
        while pending:
            app_ref = pending.pop()
            if app_ref in seen:
                continue
            seen.add(app_ref)
            if len(seen) > 256:
                raise ValueError("normalized application closure exceeds hard bound")
            payload = applications[app_ref]
            targets.add(payload["predicate_ref"])
            for binding in (*payload["roles"], *payload["qualifiers"]):
                filler = binding["filler"]
                if filler["kind"] == "grounded":
                    targets.add(filler["target_ref"])
                elif filler["kind"] == "application":
                    pending.append(filler["application_ref"])
        return targets

    for row in conn.execute(
        "SELECT claim_ref,application_ref,stance,fact_ref,source_ref,decision_ref,occurrence_ref,placement,placement_ref,"
        "proof_json,authority_generation,confidence_micros,asserted_world_revision,commit_transaction_ref,payload_hash "
        "FROM semantic_application_claims ORDER BY claim_ref"
    ):
        ref = row[0]
        try:
            proof_refs = json.loads(row[9])
            payload = {"application_ref": row[1], "stance": row[2], "fact_ref": row[3], "source_ref": row[4],
                       "decision_ref": row[5], "occurrence_ref": row[6], "placement": row[7], "placement_ref": row[8],
                       "proof_refs": proof_refs, "authority_generation": row[10], "confidence_micros": row[11],
                       "asserted_world_revision": row[12], "commit_transaction_ref": row[13]}
            lineage = conn.execute(
                "SELECT w.revision,r.transaction_ref FROM world_facts w JOIN revisions r "
                "ON r.store='world' AND r.revision=w.revision WHERE w.fact_ref=?", (row[3],)
            ).fetchone()
            fact_row = conn.execute(
                "SELECT fact_ref,operator,args_json,stance,confidence,derived,proof_json "
                "FROM world_facts WHERE fact_ref=?", (row[3],)
            ).fetchone()
            fact = None if fact_row is None else _row_to_fact(fact_row)
            if (row[1] not in applications or row[2] not in {"support", "deny"}
                    or type(proof_refs) is not list or not proof_refs
                    or any(type(item) is not str or not item for item in proof_refs)
                    or row[10] != authority_generation or type(row[11]) is not int or not 0 <= row[11] <= 1_000_000
                    or lineage is None or tuple(lineage) != (row[12], row[13])
                    or fact is None
                    or not _normalized_fact_corresponds(fact, applications[row[1]], row[2])
                    or (
                        fact.proof.get("publication_key") is None
                        and not _normalized_generic_lineage_corresponds(fact, payload)
                    )
                    or _payload_hash(payload) != row[14] or stable_ref("semantic_claim", payload) != ref):
                raise ValueError
            claims.add(ref)
            if row[3] in claims_by_fact:
                raise ValueError("legacy fact owns multiple normalized claims")
            claims_by_fact[row[3]] = ref
            expected_claim_postings.update((target_ref, ref) for target_ref in closure_targets(row[1]))
        except (TypeError, ValueError, json.JSONDecodeError):
            corrupt.append(f"semantic_claim:{ref}")

    actual_claim_postings = {tuple(row) for row in conn.execute(
        "SELECT target_ref,claim_ref FROM semantic_claim_target_postings"
    )}
    if actual_claim_postings != expected_claim_postings:
        corrupt.append("semantic_claim_target_postings")

    for journal_row in conn.execute(
        "SELECT idempotency_key,entry_json,entry_hash,receipt_json,receipt_hash "
        "FROM r3_effect_journal WHERE receipt_json IS NOT NULL ORDER BY idempotency_key"
    ):
        try:
            stored = _r3_verify_journal_row(journal_row[1], journal_row[2], journal_row[3], journal_row[4])
            entry, receipt = stored["entry"], stored["receipt"]
            request = entry.get("request_payload")
            if type(request) is not dict or request.get("kind") != "learning_publication":
                continue
            fact_refs = receipt.get("committed_fact_refs") if type(receipt) is dict else None
            if type(fact_refs) is not list or len(fact_refs) != 1:
                raise ValueError("alias publication receipt has invalid committed facts")
            fact_row = conn.execute(
                "SELECT fact_ref,operator,args_json,stance,confidence,derived,proof_json,revision "
                "FROM world_facts WHERE fact_ref=?", (fact_refs[0],)
            ).fetchone()
            if fact_row is None:
                raise ValueError("alias publication fact is missing")
            revision_row = conn.execute(
                "SELECT transaction_ref FROM revisions WHERE store='world' AND revision=?", (fact_row[7],)
            ).fetchone()
            if revision_row is None:
                raise ValueError("alias publication world transaction is missing")
            batch = _prepare_normalized_alias_publication(
                _row_to_fact(fact_row), request_payload=request, receipt_payload=receipt,
                authority_generation=authority_generation, asserted_world_revision=fact_row[7],
                commit_transaction_ref=revision_row[0],
            )
            if claims_by_fact.get(fact_refs[0]) != batch.claim_ref:
                raise ValueError("authenticated alias publication lacks its exact normalized mirror")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, StoreActivationError):
            corrupt.append(f"normalized_alias_lineage:{journal_row[0]}")

    for row in conn.execute(
        "SELECT retraction_ref,claim_ref,source_ref,occurrence_ref,proof_json,asserted_world_revision,commit_transaction_ref,payload_hash "
        "FROM semantic_claim_retractions ORDER BY retraction_ref"
    ):
        ref = row[0]
        try:
            proof_refs = json.loads(row[4])
            payload = {"claim_ref": row[1], "source_ref": row[2], "occurrence_ref": row[3],
                       "proof_refs": proof_refs, "asserted_world_revision": row[5], "commit_transaction_ref": row[6]}
            revision = conn.execute(
                "SELECT transaction_ref FROM revisions WHERE store='world' AND revision=?", (row[5],)
            ).fetchone()
            fact_row = conn.execute(
                "SELECT fact_ref,operator,args_json,stance,confidence,derived,proof_json,revision "
                "FROM world_facts WHERE fact_ref=?", (row[2],)
            ).fetchone()
            fact = None if fact_row is None else _row_to_fact(fact_row)
            if (row[1] not in claims or type(proof_refs) is not list or not proof_refs
                    or revision is None or revision[0] != row[6]
                    or fact_row is None or fact_row[7] != row[5]
                    or not _normalized_retraction_fact_corresponds(
                        fact, row[1], row[3], proof_refs
                    )
                    or _payload_hash(payload) != row[7] or stable_ref("semantic_retraction", payload) != ref):
                raise ValueError
        except (TypeError, ValueError, json.JSONDecodeError):
            corrupt.append(f"semantic_retraction:{ref}")
    if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
        corrupt.append("semantic_foreign_keys")
    return tuple(dict.fromkeys(corrupt))


class SQLiteSemanticStore:
    """The SQLite reference persistent backend."""

    def __init__(self, conn: sqlite3.Connection, *, authority_generation: str, model_identity: str | None = None) -> None:
        self._conn = conn
        register_sqlite_functions(conn)
        self._authority_generation = authority_generation
        self._model_identity = model_identity
        self._closed = False
        self._preflight_schema()
        self._init_schema()
        self._activate()
        self.world = _SQLiteWorldStore(conn)
        self.sessions = _SQLiteSessionStore(conn)
        self.episodes = _SQLiteEpisodeStore(conn)
        self.effects = _SQLiteEffectStore(conn)
        self.models = _SQLiteModelStore(conn)
        self.focus = _SQLiteFocusStore(conn)
        self.obligations = _SQLiteObligationStore(conn)

    def _preflight_schema(self) -> None:
        """Reject partial or incompatible schemas before any activation DDL."""
        tables = {row[0] for row in self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )}
        if not tables:
            return
        if "metadata" not in tables:
            raise StoreActivationError(
                "database contains tables but no CEMM schema metadata",
                RecoveryReceipt(0, tuple(sorted(tables)), "restore a verified database; do not stamp or reset it"),
            )
        try:
            version = self._conn.execute(
                "SELECT value FROM metadata WHERE key='schema_version'"
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise StoreActivationError(
                "database metadata schema is incompatible",
                RecoveryReceipt(0, ("metadata",), "restore a verified database; do not stamp or reset it"),
            ) from exc
        if version is None:
            raise StoreActivationError(
                "nonempty database lacks a schema version",
                RecoveryReceipt(0, ("metadata",), "restore a verified database; do not stamp or reset it"),
            )
        if version[0] != str(_SCHEMA_VERSION):
            raise StoreActivationError(
                f"schema version mismatch: expected {_SCHEMA_VERSION}, got {version[0]}",
                RecoveryReceipt(0, (), "restore from backup with matching schema version"),
            )
        normalized_present = tables & (set(_NORMALIZED_SCHEMA_COLUMNS) | {"semantic_target_postings"})
        if normalized_present:
            if normalized_present != set(_NORMALIZED_SCHEMA_COLUMNS):
                raise StoreActivationError(
                    "normalized semantic store schema is partial or retired",
                    RecoveryReceipt(0, tuple(sorted(normalized_present)), "restore or migrate the normalized store"),
                )
            for table, expected in _NORMALIZED_SCHEMA_COLUMNS.items():
                actual = tuple(row[1] for row in self._conn.execute(f"PRAGMA table_info({table})"))
                if actual != expected:
                    raise StoreActivationError(
                        f"normalized semantic store table {table} has incompatible columns",
                        RecoveryReceipt(0, (table,), "restore or migrate the normalized store"),
                    )
            manifest_errors = _normalized_schema_manifest_errors(self._conn)
            if manifest_errors:
                raise StoreActivationError(
                    "normalized semantic store schema manifest is incompatible",
                    RecoveryReceipt(0, manifest_errors, "restore or migrate the normalized store"),
                )
        marker = self._conn.execute(
            "SELECT value FROM metadata WHERE key='normalized_store_schema_version'"
        ).fetchone()
        if marker is not None and marker[0] != str(_NORMALIZED_STORE_SCHEMA_VERSION):
            raise StoreActivationError(
                "normalized semantic store schema marker is incompatible",
                RecoveryReceipt(0, ("normalized_store_schema_version",), "restore or migrate the normalized store"),
            )
        if marker is not None and normalized_present != set(_NORMALIZED_SCHEMA_COLUMNS):
            raise StoreActivationError(
                "normalized semantic store marker has no complete schema",
                RecoveryReceipt(0, ("normalized_store_schema_version",), "restore or migrate the normalized store"),
            )
        if marker is None and normalized_present:
            raise StoreActivationError(
                "unversioned normalized semantic store schema is not admissible",
                RecoveryReceipt(0, tuple(sorted(normalized_present)), "restore or migrate the normalized store"),
            )
        if not normalized_present and "r3_effect_journal" in tables:
            try:
                journal_rows = self._conn.execute(
                    "SELECT entry_json,receipt_json FROM r3_effect_journal WHERE receipt_json IS NOT NULL"
                ).fetchall()
                has_published_alias = any(
                    type((entry := json.loads(row[0])).get("request_payload")) is dict
                    and entry["request_payload"].get("kind") == "learning_publication"
                    and bool(json.loads(row[1]).get("committed_fact_refs"))
                    for row in journal_rows
                )
            except (AttributeError, TypeError, json.JSONDecodeError, sqlite3.DatabaseError) as exc:
                raise StoreActivationError(
                    "effect journal cannot be checked before normalized-store migration",
                    RecoveryReceipt(0, ("r3_effect_journal",), "restore a verified database"),
                ) from exc
            if has_published_alias:
                raise StoreActivationError(
                    "authenticated aliases require an explicit normalized-store migration",
                    RecoveryReceipt(0, ("normalized_alias_mirror",),
                                    "run the reviewed alias migration before activation; do not infer generic meaning"),
                )

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA_SQL)
        self._migrate_designation_indexes()
        self._migrate_query_indexes()

    def _migrate_query_indexes(self) -> None:
        """One physical posting index, atomically backfilled once on activation.

        Triggers cover ordinary commits and the EFFECT atomic upsert owner;
        no semantic record, revision, or ABI is added by this derived index.
        """
        marker = self._conn.execute("SELECT value FROM metadata WHERE key='query_index_v1'").fetchone()
        if marker:
            if marker[0] != "1":
                raise StoreActivationError("query index migration marker is invalid",
                    RecoveryReceipt(0, ("world_query_keys",), "restore the verified physical query index"))
            return
        if self._conn.execute("SELECT 1 FROM sqlite_master WHERE name IN (?,?,?,?,?)",
                tuple(_query_index_statements())).fetchone():
            raise StoreActivationError("query index migration marker is missing",
                RecoveryReceipt(0, ("world_query_keys",), "restore the verified physical query index"))
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            for statement in _query_index_statements().values():
                self._conn.execute(statement)
            self._conn.execute("""INSERT INTO world_query_keys(operator,predicate,role,value,fact_ref)
                SELECT json_extract(j.value,'$[0]'),json_extract(j.value,'$[1]'),
                    json_extract(j.value,'$[2]'),json_extract(j.value,'$[3]'),w.fact_ref
                FROM world_facts AS w, json_each(query_index_keys(w.operator,w.args_json)) AS j""")
            self._conn.execute("INSERT INTO metadata(key,value) VALUES('query_index_v1','1')")
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise

    def _migrate_designation_indexes(self) -> None:
        """One-time physical index replacement; no fact, revision or ABI migration.

        JSON1 extracts objects/arrays as SQL strings. Text-only partial indexes
        must replace the original untyped indexes, not postfilter their results.
        Already migrated stores perform no index DDL or rebuilding on activation.
        """
        names = (*_LEGACY_DESIGNATION_INDEXES, *_DESIGNATION_TEXT_INDEX_SQL)
        present = {row[0] for row in self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IN (?,?,?,?,?,?,?,?)", names)}
        if set(_DESIGNATION_TEXT_INDEX_SQL) <= present and not set(_LEGACY_DESIGNATION_INDEXES) & present:
            return
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            for statement in _DESIGNATION_TEXT_INDEX_SQL.values():
                self._conn.execute(statement)
            for name in _LEGACY_DESIGNATION_INDEXES:
                self._conn.execute(f"DROP INDEX IF EXISTS {name}")
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise

    def _activate(self) -> None:
        manifest_errors = _normalized_schema_manifest_errors(self._conn)
        if manifest_errors:
            raise StoreActivationError(
                "normalized semantic store schema manifest is incompatible",
                RecoveryReceipt(0, manifest_errors, "restore or migrate the normalized store"),
            )
        self._verify_query_indexes()
        # Check schema version
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            # Fresh database — write schema version and authority generation
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "INSERT INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(_SCHEMA_VERSION),),
            )
            self._conn.execute(
                "INSERT INTO metadata(key, value) VALUES('authority_generation', ?)",
                (self._authority_generation,),
            )
            self._conn.commit()
        elif int(row[0]) != _SCHEMA_VERSION:
            raise StoreActivationError(
                f"schema version mismatch: expected {_SCHEMA_VERSION}, got {row[0]}",
                RecoveryReceipt(0, (), "restore from backup with matching schema version"),
            )

        # Check authority generation
        gen_row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'authority_generation'"
        ).fetchone()
        if gen_row and gen_row[0] != self._authority_generation:
            raise StoreActivationError(
                f"authority generation mismatch: expected {self._authority_generation}, got {gen_row[0]}",
                RecoveryReceipt(0, (), "reopen with the active authority generation"),
            )

        # Verify row hashes across all tables
        all_corrupt: list[str] = []
        last_verified = 0
        for store_obj in [
            _SQLiteWorldStore(self._conn),
            _SQLiteSessionStore(self._conn),
            _SQLiteEpisodeStore(self._conn),
            _SQLiteEffectStore(self._conn),
            _SQLiteModelStore(self._conn),
            _SQLiteFocusStore(self._conn),
            _SQLiteObligationStore(self._conn),
        ]:
            corrupt = store_obj.verify()
            all_corrupt.extend(corrupt)
            if store_obj.revision > last_verified:
                last_verified = store_obj.revision

        for row in self._conn.execute(
            "SELECT idempotency_key, entry_json, entry_hash, receipt_json, receipt_hash "
            "FROM r3_effect_journal ORDER BY idempotency_key"
        ).fetchall():
            try:
                _r3_verify_journal_row(row[1], row[2], row[3], row[4])
            except StoreActivationError:
                all_corrupt.append(f"r3_effect_journal:{row[0]}")

        all_corrupt.extend(
            _verify_normalized_sqlite(self._conn, self._authority_generation)
        )

        if all_corrupt:
            raise StoreActivationError(
                f"corruption detected in {len(all_corrupt)} rows",
                RecoveryReceipt(
                    last_verified_revision=last_verified,
                    corrupt_refs=tuple(all_corrupt),
                    recommended_action="restore from last verified backup; do not reset the database",
                ),
            )
        marker = self._conn.execute(
            "SELECT value FROM metadata WHERE key='normalized_store_schema_version'"
        ).fetchone()
        if marker is None:
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "INSERT INTO metadata(key,value) VALUES('normalized_store_schema_version',?)",
                (str(_NORMALIZED_STORE_SCHEMA_VERSION),),
            )
            self._conn.commit()

    def _verify_query_indexes(self) -> None:
        """Existing activation owner checks physical completeness, never QUERY."""
        expected = _query_index_statements()
        actual = dict(self._conn.execute("SELECT name,sql FROM sqlite_master WHERE name IN (?,?,?,?,?)", tuple(expected)))
        normalize = lambda value: " ".join(value.split())
        valid = set(actual) == set(expected) and all(
            normalize(actual[key]) == normalize(value) for key, value in expected.items())
        if valid:
            projected = """SELECT json_extract(j.value,'$[0]'),json_extract(j.value,'$[1]'),
                json_extract(j.value,'$[2]'),json_extract(j.value,'$[3]'),w.fact_ref
                FROM world_facts AS w, json_each(query_index_keys(w.operator,w.args_json)) AS j"""
            indexed = "SELECT operator,predicate,role,value,fact_ref FROM world_query_keys"
            valid = (self._conn.execute(projected + " EXCEPT " + indexed + " LIMIT 1").fetchone() is None
                and self._conn.execute(indexed + " EXCEPT " + projected + " LIMIT 1").fetchone() is None)
        if not valid:
            raise StoreActivationError("physical query index is incomplete or corrupt",
                RecoveryReceipt(0, ("world_query_keys",), "restore the verified physical query index"))

    def revision_pin(self) -> RevisionPin:
        return RevisionPin(
            authority_generation=self._authority_generation,
            world_revision=self.world.revision,
            session_revision=self.sessions.revision,
            episode_revision=self.episodes.revision,
            effect_revision=self.effects.revision,
            model_identity=self._model_identity,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._conn.close()


# ---------------------------------------------------------------------------
# In-memory sub-stores (test-only)
# ---------------------------------------------------------------------------


class _MemoryWorldStore:
    def __init__(self) -> None:
        self.revision = 0
        self._facts: dict[str, Fact] = {}
        self._designation_indexes: dict[tuple[str, str, str | None], dict[str, None]] = {}
        self._query_indexes: dict[tuple[str, str, str, str], dict[str, None]] = {}
        self._fact_revisions: dict[str, int] = {}
        self._revision_transactions: dict[int, str] = {}
        self._normalized_claim_by_fact: Mapping[str, str] = {}

    @staticmethod
    def _designation_keys(fact):
        if fact.operator != "op:designation":
            return ()
        surface, language, target = fact.args.get("role:surface"), fact.proof.get("alias_language"), fact.args.get("role:target")
        keys = []
        if type(surface) is str:
            keys.append(("exact", surface, None))
            if type(language) is str:
                keys.extend((("exact", surface, language), ("folded", surface.casefold(), language)))
        if type(target) is str and type(language) is str:
            keys.append(("target", target, language))
        return keys

    def _store_fact(self, fact):
        # Match SQLite's detached JSON boundary: caller mutation is not a write.
        fact = _row_to_fact(_fact_to_row(fact))
        previous = self._facts.get(fact.fact_ref)
        if previous is not None:
            for key in _query_index_keys(previous.operator, previous.args):
                index = self._query_indexes[key]
                index.pop(fact.fact_ref, None)
                if not index:
                    del self._query_indexes[key]
            for key in self._designation_keys(previous):
                index = self._designation_indexes[key]
                index.pop(fact.fact_ref, None)
                if not index:
                    del self._designation_indexes[key]
        self._facts[fact.fact_ref] = fact
        for key in _query_index_keys(fact.operator, fact.args):
            self._query_indexes.setdefault(key, {})[fact.fact_ref] = None
        for key in self._designation_keys(fact):
            self._designation_indexes.setdefault(key, {})[fact.fact_ref] = None

    def _remove_fact(self, fact_ref: str) -> Fact | None:
        fact = self._facts.pop(fact_ref, None)
        if fact is None:
            return None
        for key in _query_index_keys(fact.operator, fact.args):
            index = self._query_indexes.get(key)
            if index is not None:
                index.pop(fact_ref, None)
                if not index:
                    del self._query_indexes[key]
        for key in self._designation_keys(fact):
            index = self._designation_indexes.get(key)
            if index is not None:
                index.pop(fact_ref, None)
                if not index:
                    del self._designation_indexes[key]
        return fact

    def commit(self, facts: Iterable[Fact], *, expected_revision: int) -> CommitReceipt:
        facts = tuple(_row_to_fact(_fact_to_row(fact)) for fact in facts)
        if expected_revision != self.revision:
            raise StaleRevisionError(f"world: expected {expected_revision}, got {self.revision}")
        delta_payload = [_fact_payload(f) for f in facts]
        delta_hash = _payload_hash(delta_payload)
        transaction_ref = stable_ref("txn", {"store": "world", "parent": expected_revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1
        for fact in facts:
            if fact.fact_ref in self._normalized_claim_by_fact:
                raise ValueError("a normalized claim projection fact is immutable")
            self._store_fact(fact)
            self._fact_revisions[fact.fact_ref] = new_revision
        self._revision_transactions[new_revision] = transaction_ref
        self.revision = new_revision
        return CommitReceipt("world", expected_revision, new_revision, delta_hash, transaction_ref)

    def get(self, fact_ref: str) -> Fact | None:
        fact = self._facts.get(fact_ref)
        return None if fact is None else _row_to_fact(_fact_to_row(fact))


class _MemorySessionStore:
    def __init__(self) -> None:
        self.revision = 0
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        new_revision = self.revision + 1
        ref = stable("session", new_revision)
        session = Session(session_ref=ref)
        session.revision = new_revision
        self._sessions[ref] = session
        self.revision = new_revision
        return session

    def get(self, session_ref: str) -> Session | None:
        return self._sessions.get(session_ref)


class _MemoryEpisodeStore:
    def __init__(self) -> None:
        self.revision = 0
        self._rows: list[dict[str, Any]] = []

    def append(self, row: Mapping[str, Any]) -> None:
        self._rows.append(dict(row))
        self.revision += 1

    def rows(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._rows)


class _MemoryEffectStore:
    def __init__(self) -> None:
        self.revision = 0
        self._effects: dict[str, CommitReceipt] = {}
        self._payloads: dict[str, dict[str, Any]] = {}

    def commit(self, effect: Mapping[str, Any]) -> CommitReceipt:
        effect_key = effect["effect_key"]
        if effect_key in self._effects:
            return self._effects[effect_key]
        payload = dict(effect.get("payload", {}))
        delta_hash = _payload_hash(payload)
        transaction_ref = stable_ref("txn", {"store": "effects", "parent": self.revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1
        receipt = CommitReceipt("effects", self.revision, new_revision, delta_hash, transaction_ref)
        self._effects[effect_key] = receipt
        self._payloads[effect_key] = payload
        self.revision = new_revision
        return receipt

    def get(self, effect_key: str) -> dict[str, Any] | None:
        """Return the stored payload for ``effect_key``, or ``None``."""
        return self._payloads.get(effect_key)


class _MemoryModelStore:
    def __init__(self) -> None:
        self.revision = 0
        self._models: dict[str, dict[str, Any]] = {}

    def register(self, model_identity: str, payload: Mapping[str, Any]) -> None:
        self._models[model_identity] = {**dict(payload), "model_identity": model_identity}
        self.revision += 1

    def get(self, model_identity: str) -> dict[str, Any] | None:
        return self._models.get(model_identity)


class _MemoryFocusStore:
    def __init__(self) -> None:
        self.revision = 0
        self._focus: dict[str, dict[str, Any]] = {}
        self._recent: OrderedDict[str, tuple[str, str, int]] = OrderedDict()
        self._session_recent: dict[str, OrderedDict[str, None]] = {}

    def commit(self, focus_ref: str, session_ref: str, payload: Mapping[str, Any], *, expected_revision: int) -> CommitReceipt:
        if type(focus_ref) is not str or not focus_ref:
            raise TypeError("focus_ref must be exact nonempty str")
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        if expected_revision != self.revision:
            raise StaleRevisionError(f"focus: expected {expected_revision}, got {self.revision}")
        data = json.loads(json.dumps({**dict(payload), "focus_ref": focus_ref, "session_ref": session_ref}))
        delta_hash = _payload_hash(data)
        transaction_ref = stable_ref("txn", {"store": "focus", "parent": expected_revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1
        previous = self._recent.pop(focus_ref, None)
        if previous is not None:
            previous_session = previous[0]
            del self._session_recent[previous_session][focus_ref]
            if not self._session_recent[previous_session]:
                del self._session_recent[previous_session]
        self._focus[focus_ref] = data
        self._recent[focus_ref] = (session_ref, delta_hash, new_revision)
        self._session_recent.setdefault(session_ref, OrderedDict())[focus_ref] = None
        self.revision = new_revision
        return CommitReceipt("focus", expected_revision, new_revision, delta_hash, transaction_ref)

    def get(self, focus_ref: str) -> dict[str, Any] | None:
        return self._focus.get(focus_ref)

    def recent_rows(self, maximum: int, session_ref: str | None) -> tuple:
        index = self._recent if session_ref is None else self._session_recent.get(session_ref, {})
        return tuple(
            (ref, self._recent[ref][0], self._focus[ref], self._recent[ref][1], self._recent[ref][2])
            for ref in islice(reversed(index), maximum)
        )


class _MemoryObligationStore:
    def __init__(self) -> None:
        self.revision = 0
        self._obligations: dict[str, dict[str, Any]] = {}
        self._row_metadata: dict[str, tuple[str, str, int, int]] = {}
        self._pending_by_session: dict[str, dict[str, None]] = {}

    @staticmethod
    def _prepare_row(obligation_ref: str, session_ref: str, payload: Mapping[str, Any], revision: int, resolved: bool) -> tuple[dict[str, Any], tuple[str, str, int, int]]:
        # Detach nested values exactly as SQLite serialization does. Metadata is
        # independent of the payload, so keyed reads can authenticate both.
        from .r3_codec import exact_bool, exact_int
        if type(obligation_ref) is not str or not obligation_ref:
            raise TypeError("obligation_ref must be exact nonempty str")
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        exact_int(revision, "obligation commit revision", minimum=1)
        exact_bool(resolved, "resolved")
        data = json.loads(json.dumps(dict(payload), ensure_ascii=False))
        return data, (session_ref, _payload_hash(data), revision, int(resolved))

    def _store_row(self, obligation_ref: str, prepared: tuple[dict[str, Any], tuple[str, str, int, int]]) -> None:
        previous = self._row_metadata.get(obligation_ref)
        if previous is not None:
            prior_session = self._pending_by_session.get(previous[0])
            if prior_session is not None:
                prior_session.pop(obligation_ref, None)
                if not prior_session:
                    del self._pending_by_session[previous[0]]
        self._obligations[obligation_ref], self._row_metadata[obligation_ref] = prepared
        session, _digest, _revision, resolved = prepared[1]
        if resolved == 0:
            self._pending_by_session.setdefault(session, {})[obligation_ref] = None

    def pending_refs(self, session_ref: str, maximum: int) -> list[str]:
        return list(islice(self._pending_by_session.get(session_ref, {}), maximum))

    def commit(self, obligation_ref: str, session_ref: str, payload: Mapping[str, Any], *, expected_revision: int, resolved: bool = False) -> CommitReceipt:
        if expected_revision != self.revision:
            raise StaleRevisionError(f"obligations: expected {expected_revision}, got {self.revision}")
        delta_hash = _payload_hash(payload)
        transaction_ref = stable_ref("txn", {"store": "obligations", "parent": expected_revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1
        prepared = self._prepare_row(obligation_ref, session_ref, {**dict(payload), "obligation_ref": obligation_ref, "session_ref": session_ref, "resolved": resolved}, new_revision, resolved)
        self._store_row(obligation_ref, prepared)
        self.revision = new_revision
        return CommitReceipt("obligations", expected_revision, new_revision, delta_hash, transaction_ref)

    def complete(
        self,
        pending_ref: str,
        completed_ref: str,
        session_ref: str,
        completed_payload: Mapping[str, Any],
        *,
        expected_revision: int,
    ) -> CommitReceipt:
        if expected_revision != self.revision:
            raise StaleRevisionError(
                f"obligations: expected {expected_revision}, got {self.revision}"
            )
        if pending_ref == completed_ref:
            raise ValueError("completed obligation ref must differ from pending ref")
        pending = self._obligations.get(pending_ref)
        if pending is None:
            raise KeyError(pending_ref)
        if pending.get("session_ref") != session_ref:
            raise ValueError("pending obligation session mismatch")
        if pending.get("resolved") is True:
            raise ValueError("pending obligation is already resolved")
        pending_data = {**pending, "resolved": True}
        completed_data = {
            **dict(completed_payload),
            "obligation_ref": completed_ref,
            "session_ref": session_ref,
            "resolved": True,
        }
        delta_hash = _payload_hash({
            "pending_ref": pending_ref,
            "pending": pending_data,
            "completed_ref": completed_ref,
            "completed": completed_data,
        })
        transaction_ref = stable_ref(
            "txn",
            {"store": "obligations", "parent": expected_revision, "delta_hash": delta_hash},
        )
        new_revision = self.revision + 1
        prepared_pending = self._prepare_row(pending_ref, session_ref, pending_data, new_revision, True)
        prepared_completed = self._prepare_row(completed_ref, session_ref, completed_data, new_revision, True)
        self._store_row(pending_ref, prepared_pending)
        self._store_row(completed_ref, prepared_completed)
        self.revision = new_revision
        return CommitReceipt(
            "obligations", expected_revision, new_revision, delta_hash, transaction_ref
        )

    def get(self, obligation_ref: str) -> dict[str, Any] | None:
        payload = self._obligations.get(obligation_ref)
        return json.loads(json.dumps(payload, ensure_ascii=False)) if payload is not None else None

    def keyed_row(self, obligation_ref: str) -> tuple[Any, ...] | None:
        payload = self._obligations.get(obligation_ref)
        if payload is None:
            return None
        metadata = self._row_metadata.get(obligation_ref)
        if metadata is None:
            raise ValueError("obligation authentication metadata missing")
        session, digest, revision, resolved = metadata
        return (obligation_ref, session, json.loads(json.dumps(payload, ensure_ascii=False)), digest, revision, resolved)


class InMemorySemanticStore:
    """Test-only in-memory backend with the same API as SQLite."""

    def __init__(self, *, authority_generation: str, model_identity: str | None = None) -> None:
        self._authority_generation = authority_generation
        self._model_identity = model_identity
        self._closed = False
        self.world = _MemoryWorldStore()
        self.sessions = _MemorySessionStore()
        self.episodes = _MemoryEpisodeStore()
        self.effects = _MemoryEffectStore()
        self.models = _MemoryModelStore()
        self.focus = _MemoryFocusStore()
        self.obligations = _MemoryObligationStore()
        self._r3_effect_journals: dict[str, dict[str, Any]] = {}
        self._normalized_applications: dict[str, dict[str, Any]] = {}
        self._normalized_bindings: dict[str, tuple[dict[str, Any], ...]] = {}
        self._normalized_claims: dict[str, dict[str, Any]] = {}
        self._normalized_claim_by_fact: dict[str, str] = {}
        self.world._normalized_claim_by_fact = self._normalized_claim_by_fact
        self._normalized_claims_by_app: dict[str, OrderedDict[str, None]] = {}
        self._normalized_retractions: dict[str, dict[str, Any]] = {}
        self._normalized_retracted_claims: set[str] = set()
        self._normalized_target_index: dict[str, OrderedDict[str, None]] = {}

    def revision_pin(self) -> RevisionPin:
        return RevisionPin(
            authority_generation=self._authority_generation,
            world_revision=self.world.revision,
            session_revision=self.sessions.revision,
            episode_revision=self.episodes.revision,
            effect_revision=self.effects.revision,
            model_identity=self._model_identity,
        )

    def close(self) -> None:
        self._closed = True


# ---------------------------------------------------------------------------
# SemanticStores facade
# ---------------------------------------------------------------------------


class SemanticStores:
    """Facade holding all store backends.

    This is returned by both :func:`open_stores` (SQLite) and
    :func:`memory_stores` (in-memory). It delegates to the concrete backend.
    """

    def __init__(self, backend: SQLiteSemanticStore | InMemorySemanticStore) -> None:
        self._backend = backend

    @property
    def world(self):
        return self._backend.world

    @property
    def sessions(self):
        return self._backend.sessions

    @property
    def episodes(self):
        return self._backend.episodes

    @property
    def effects(self):
        return self._backend.effects

    @property
    def models(self):
        return self._backend.models

    @property
    def focus(self):
        return self._backend.focus

    @property
    def obligations(self):
        return self._backend.obligations

    def revision_pin(self) -> RevisionPin:
        return self._backend.revision_pin()

    def r3_assert_read_pin(self, expected: RevisionPin) -> None:
        """Compare fixed metadata in the caller's current snapshot, never rebase."""
        if type(expected) is not RevisionPin or self.revision_pin() != expected:
            raise StaleRevisionError("admitted read requires the captured store pin")
        if isinstance(self._backend, SQLiteSemanticStore):
            names = ("authority_generation", "world_revision", "session_revision", "episode_revision", "effect_revision")
            values = dict(self._backend._conn.execute(
                "SELECT key,value FROM metadata WHERE key IN (?,?,?,?,?)", names).fetchall())
            if (values.get("authority_generation") != expected.authority_generation
                    or any(int(values.get(name, 0)) != getattr(expected, name) for name in names[1:])):
                raise StaleRevisionError("admitted read snapshot revisions changed")

    def r3_obligation_revision(self) -> int:
        if isinstance(self._backend, SQLiteSemanticStore):
            row = self._backend._conn.execute("SELECT value FROM metadata WHERE key='obligation_revision'").fetchone()
            return int(row[0]) if row else 0
        return self.obligations.revision

    def r3_resolved_dialogue_obligation(self, ref: str, *, commit_revision: int):
        """Keyed canonical completed-publication evidence, not live eligibility."""
        from .dialogue import DialogueObligation
        row = self.obligations.keyed_row(ref)
        if row is None:
            raise ValueError("publication obligation row is missing")
        key, session, payload, digest, revision, resolved = row
        if (type(payload) is not dict or payload.get("resolved") is not True
                or type(resolved) is not int or resolved != 1 or _payload_hash(payload) != digest
                or revision != commit_revision or not 1 <= revision <= self.r3_obligation_revision()):
            raise ValueError("publication obligation metadata mismatch")
        obligation = DialogueObligation.from_dict({k: v for k, v in payload.items() if k != "resolved"})
        if key != ref or obligation.obligation_ref != ref or obligation.session_ref != session:
            raise ValueError("publication obligation key/session mismatch")
        return obligation

    @contextmanager
    def r3_read_snapshot(self, expected: RevisionPin):
        """One read snapshot for a bounded batch and all its keyed proof reads."""
        conn = self._backend._conn if isinstance(self._backend, SQLiteSemanticStore) else None
        own = conn is not None and not conn.in_transaction
        if own:
            conn.execute("BEGIN")
        try:
            self.r3_assert_read_pin(expected)
            yield
            self.r3_assert_read_pin(expected)
        finally:
            if own:
                conn.rollback()

    def r3_world_fact_lineage(
        self, fact_ref: str, *, expected_pin: RevisionPin
    ) -> tuple[Fact, int, str]:
        """Read one exact fact with its immutable world-commit lineage."""
        if type(fact_ref) is not str or not fact_ref:
            raise TypeError("fact_ref must be an exact nonempty str")
        self.r3_assert_read_pin(expected_pin)
        if isinstance(self._backend, SQLiteSemanticStore):
            row = self._backend._conn.execute(
                "SELECT w.fact_ref,w.operator,w.args_json,w.stance,w.confidence,"
                "w.derived,w.proof_json,w.revision,r.transaction_ref "
                "FROM world_facts w JOIN revisions r "
                "ON r.store='world' AND r.revision=w.revision "
                "WHERE w.fact_ref=?",
                (fact_ref,),
            ).fetchone()
            if row is None:
                raise ValueError("world fact lineage is missing")
            fact = _row_to_fact(row)
            revision, transaction_ref = row["revision"], row["transaction_ref"]
        else:
            fact = self._backend.world.get(fact_ref)
            revision = self._backend.world._fact_revisions.get(fact_ref)
            transaction_ref = (
                None
                if revision is None
                else self._backend.world._revision_transactions.get(revision)
            )
        if (
            type(fact) is not Fact
            or type(revision) is not int
            or revision < 1
            or type(transaction_ref) is not str
            or not transaction_ref
        ):
            raise ValueError("world fact lineage is incomplete")
        return fact, revision, transaction_ref

    def r3_designation_facts(self, mode: str, key: str, language: str | None, *, maximum: int) -> tuple[Fact, ...]:
        """Indexed raw evidence, max+1 sentinel; never an admission decision."""
        from .r3_codec import exact_int, exact_text
        exact_text(key, "designation key")
        if language is not None:
            exact_text(language, "designation language")
        exact_int(maximum, "designation maximum", minimum=1, maximum=16)
        expressions = {"exact": 'json_extract(args_json, \'$."role:surface"\')',
            "folded": 'unicode_casefold(json_extract(args_json, \'$."role:surface"\'))',
            "target": 'json_extract(args_json, \'$."role:target"\')'}
        if mode not in expressions or language is None and mode != "exact":
            raise ValueError("unsupported designation read")
        key = key.casefold() if mode == "folded" else key
        if isinstance(self._backend, SQLiteSemanticStore):
            role = "target" if mode == "target" else "surface"
            sql = ("SELECT fact_ref, operator, args_json, stance, confidence, derived, proof_json FROM world_facts "
                "WHERE operator='op:designation' AND " + expressions[mode] + "=?"
                + f" AND json_type(args_json, '$.\"role:{role}\"')='text'")
            params = [key]
            if language is not None:
                sql += " AND json_extract(proof_json, '$.alias_language')=? AND json_type(proof_json, '$.alias_language')='text'"
                params.append(language)
            rows = self._backend._conn.execute(sql + " ORDER BY fact_ref LIMIT ?", (*params, maximum + 1)).fetchall()
            return tuple(_row_to_fact(row) for row in rows)
        index = self.world._designation_indexes.get((mode, key, language), {})
        return tuple(self.world.get(ref) for ref in islice(index, maximum + 1))

    @property
    def learning_store_binding(self) -> str | None:
        """The actual named SQLite database, never a caller's convenient label."""
        if not isinstance(self._backend, SQLiteSemanticStore):
            return None
        rows = self._backend._conn.execute("PRAGMA database_list").fetchall()
        path = next((row[2] for row in rows if row[1] == "main"), None)
        return None if not path else str(Path(path).resolve())

    def r3_alias_facts(self, surface: str, language: str, *, maximum: int) -> tuple[Fact, ...]:
        """Bounded relevant world evidence; this read alone never admits an alias."""
        from .r3_codec import exact_int, exact_text
        exact_text(surface, "alias surface")
        exact_text(language, "alias language")
        exact_int(maximum, "alias maximum", minimum=1, maximum=512)
        if isinstance(self._backend, SQLiteSemanticStore):
            rows = self._backend._conn.execute(
                "SELECT fact_ref, operator, args_json, stance, confidence, derived, proof_json FROM world_facts "
                "WHERE operator='op:designation' AND json_extract(args_json, '$.\"role:surface\"')=? "
                "AND json_type(args_json, '$.\"role:surface\"')='text' "
                "AND json_extract(proof_json, '$.alias_language')=? "
                "AND json_type(proof_json, '$.alias_language')='text' ORDER BY fact_ref LIMIT ?",
                (surface, language, maximum + 1)).fetchall()
            facts = tuple(_row_to_fact(row) for row in rows)
        else:
            index = self._backend.world._designation_indexes.get(("exact", surface, language), {})
            facts = tuple(self._backend.world.get(ref) for ref in islice(index, maximum + 1))
        if len(facts) > maximum:
            raise ValueError("alias relevant evidence exceeds bound")
        return facts

    def _r3_write_normalized_batch(self, batch: _PreparedNormalizedBatch) -> None:
        """Private persistence primitive; callers must already own authority."""
        if type(batch) is not _PreparedNormalizedBatch:
            raise TypeError("normalized write requires private prepared material")
        application_rows = tuple(
            (
                application,
                _normalized_application_payload(application),
                _normalized_binding_rows(application),
            )
            for application in batch.applications
        )
        if batch.root_application_ref not in {row[0].application_ref for row in application_rows}:
            raise ValueError("normalized batch root is absent")
        claim = dict(batch.claim_payload)
        if stable_ref("semantic_claim", claim) != batch.claim_ref:
            raise ValueError("normalized claim identity mismatch")
        if claim["authority_generation"] != self.revision_pin().authority_generation:
            raise StaleRevisionError("normalized claim authority generation is stale")
        claim_hash = _payload_hash(claim)

        def validate_authorization(fact: Fact) -> None:
            authorization = batch.authorization_payload
            if authorization is None:
                if not _normalized_generic_lineage_corresponds(fact, claim):
                    raise ValueError("normalized claim lineage does not correspond to its fact proof")
                return
            if set(authorization) != {"kind", "request_payload", "receipt_payload"} or (
                authorization["kind"] != "authenticated_alias_publication"
            ):
                raise ValueError("normalized claim authorization envelope is invalid")
            expected = _prepare_normalized_alias_publication(
                fact,
                request_payload=authorization["request_payload"],
                receipt_payload=authorization["receipt_payload"],
                authority_generation=claim["authority_generation"],
                asserted_world_revision=claim["asserted_world_revision"],
                commit_transaction_ref=claim["commit_transaction_ref"],
            )
            if (
                expected.applications != batch.applications
                or expected.root_application_ref != batch.root_application_ref
                or expected.claim_ref != batch.claim_ref
                or dict(expected.claim_payload) != claim
            ):
                raise ValueError("normalized alias authorization does not bind this exact claim")

        if isinstance(self._backend, SQLiteSemanticStore):
            conn = self._backend._conn
            own = not conn.in_transaction
            if own:
                conn.execute("BEGIN IMMEDIATE")
            try:
                lineage = conn.execute(
                    "SELECT w.revision,r.transaction_ref FROM world_facts w "
                    "JOIN revisions r ON r.store='world' AND r.revision=w.revision WHERE w.fact_ref=?",
                    (claim["fact_ref"],),
                ).fetchone()
                if lineage is None or tuple(lineage) != (
                    claim["asserted_world_revision"], claim["commit_transaction_ref"]
                ):
                    raise ValueError("normalized claim is detached from its world commit")
                fact = self.world.get(claim["fact_ref"])
                root_payload = next(
                    payload for application, payload, _bindings in application_rows
                    if application.application_ref == batch.root_application_ref
                )
                if fact is None or not _normalized_fact_corresponds(fact, root_payload, claim["stance"]):
                    raise ValueError("normalized claim does not correspond to its legacy fact projection")
                validate_authorization(fact)
                for application, payload, bindings in application_rows:
                    conn.execute(
                        "INSERT OR IGNORE INTO semantic_applications(application_ref,operator,predicate_ref,payload_hash) "
                        "VALUES(?,?,?,?)",
                        (application.application_ref, application.operator, application.predicate_ref,
                         _payload_hash(payload)),
                    )
                    stored = conn.execute(
                        "SELECT operator,predicate_ref,payload_hash FROM semantic_applications WHERE application_ref=?",
                        (application.application_ref,),
                    ).fetchone()
                    if stored is None or tuple(stored) != (
                        application.operator, application.predicate_ref, _payload_hash(payload)
                    ):
                        raise ValueError("normalized application identity collision")
                    for binding in bindings:
                        conn.execute(
                            "INSERT OR IGNORE INTO semantic_application_bindings(binding_ref,application_ref,binding_kind,ordinal,role_ref,filler_kind,filler_value,payload_hash) "
                            "VALUES(:binding_ref,:application_ref,:binding_kind,:ordinal,:role_ref,:filler_kind,:filler_value,:payload_hash)",
                            binding,
                        )
                conn.execute(
                    "INSERT OR IGNORE INTO semantic_application_claims(claim_ref,application_ref,stance,fact_ref,source_ref,decision_ref,occurrence_ref,placement,placement_ref,proof_json,authority_generation,confidence_micros,asserted_world_revision,commit_transaction_ref,payload_hash) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (batch.claim_ref, claim["application_ref"], claim["stance"], claim["fact_ref"],
                     claim["source_ref"], claim["decision_ref"], claim["occurrence_ref"], claim["placement"],
                     claim["placement_ref"], _r3_canonical_json(claim["proof_refs"]), claim["authority_generation"],
                     claim["confidence_micros"], claim["asserted_world_revision"], claim["commit_transaction_ref"], claim_hash),
                )
                stored_claim = conn.execute(
                    "SELECT application_ref,stance,fact_ref,source_ref,decision_ref,occurrence_ref,placement,placement_ref,proof_json,authority_generation,confidence_micros,asserted_world_revision,commit_transaction_ref,payload_hash "
                    "FROM semantic_application_claims WHERE claim_ref=?", (batch.claim_ref,)
                ).fetchone()
                expected = (claim["application_ref"], claim["stance"], claim["fact_ref"], claim["source_ref"],
                            claim["decision_ref"], claim["occurrence_ref"], claim["placement"], claim["placement_ref"],
                            _r3_canonical_json(claim["proof_refs"]), claim["authority_generation"], claim["confidence_micros"],
                            claim["asserted_world_revision"], claim["commit_transaction_ref"], claim_hash)
                if stored_claim is None or tuple(stored_claim) != expected:
                    raise ValueError("normalized claim identity collision")
                target_refs = sorted({
                    binding["filler_value"]
                    for _application, _payload, bindings in application_rows
                    for binding in bindings
                    if binding["filler_kind"] == "grounded"
                } | {application.predicate_ref for application, _payload, _bindings in application_rows})
                conn.executemany(
                    "INSERT OR IGNORE INTO semantic_claim_target_postings(target_ref,claim_ref) VALUES(?,?)",
                    ((target_ref, batch.claim_ref) for target_ref in target_refs),
                )
                if own:
                    conn.commit()
            except BaseException:
                if own:
                    conn.rollback()
                raise
            return

        backend = self._backend
        if (backend.world._fact_revisions.get(claim["fact_ref"]) != claim["asserted_world_revision"]
                or backend.world._revision_transactions.get(claim["asserted_world_revision"])
                != claim["commit_transaction_ref"]):
            raise ValueError("normalized claim is detached from its world commit")
        fact = backend.world.get(claim["fact_ref"])
        root_payload = next(
            payload for application, payload, _bindings in application_rows
            if application.application_ref == batch.root_application_ref
        )
        if fact is None or not _normalized_fact_corresponds(fact, root_payload, claim["stance"]):
            raise ValueError("normalized claim does not correspond to its legacy fact projection")
        validate_authorization(fact)
        existing_claim_ref = backend._normalized_claim_by_fact.get(claim["fact_ref"])
        if existing_claim_ref is not None and existing_claim_ref != batch.claim_ref:
            raise ValueError("legacy fact already owns a different normalized claim")
        for application, payload, bindings in application_rows:
            header = {"operator": application.operator, "predicate_ref": application.predicate_ref,
                      "payload_hash": _payload_hash(payload)}
            previous = backend._normalized_applications.setdefault(application.application_ref, header)
            if previous != header:
                raise ValueError("normalized application identity collision")
            previous_bindings = backend._normalized_bindings.setdefault(application.application_ref, bindings)
            if previous_bindings != bindings:
                raise ValueError("normalized binding identity collision")
        previous_claim = backend._normalized_claims.setdefault(batch.claim_ref, claim)
        if previous_claim != claim:
            raise ValueError("normalized claim identity collision")
        backend._normalized_claim_by_fact[claim["fact_ref"]] = batch.claim_ref
        backend._normalized_claims_by_app.setdefault(batch.root_application_ref, OrderedDict())[batch.claim_ref] = None
        for target_ref in dict.fromkeys(
            target_ref
            for application, _payload, bindings in application_rows
            for target_ref in (
                application.predicate_ref,
                *(binding["filler_value"] for binding in bindings if binding["filler_kind"] == "grounded"),
            )
        ):
            backend._normalized_target_index.setdefault(target_ref, OrderedDict())[batch.claim_ref] = None

    def _r3_write_normalized_retraction(
        self,
        claim_ref: str,
        *,
        source_ref: str,
        occurrence_ref: str,
        proof_refs: tuple[str, ...],
        asserted_world_revision: int,
        commit_transaction_ref: str,
    ) -> str:
        """Private append-only retraction primitive; not an authority gateway."""
        if any(type(value) is not str or not value for value in (
            claim_ref, source_ref, occurrence_ref, commit_transaction_ref
        )):
            raise TypeError("normalized retraction refs must be exact nonempty str")
        if type(proof_refs) is not tuple or not proof_refs or any(type(row) is not str or not row for row in proof_refs):
            raise TypeError("normalized retraction proof must be a nonempty exact ref tuple")
        if type(asserted_world_revision) is not int or isinstance(asserted_world_revision, bool) or asserted_world_revision < 1:
            raise TypeError("normalized retraction revision must be a positive exact int")
        payload = {
            "claim_ref": claim_ref,
            "source_ref": source_ref,
            "occurrence_ref": occurrence_ref,
            "proof_refs": list(proof_refs),
            "asserted_world_revision": asserted_world_revision,
            "commit_transaction_ref": commit_transaction_ref,
        }
        retraction_ref = stable_ref("semantic_retraction", payload)
        if isinstance(self._backend, SQLiteSemanticStore):
            conn = self._backend._conn
            own = not conn.in_transaction
            if own:
                conn.execute("BEGIN IMMEDIATE")
            try:
                revision = conn.execute(
                    "SELECT transaction_ref FROM revisions WHERE store='world' AND revision=?",
                    (asserted_world_revision,),
                ).fetchone()
                fact_row = conn.execute(
                    "SELECT fact_ref,operator,args_json,stance,confidence,derived,proof_json,revision "
                    "FROM world_facts WHERE fact_ref=?", (source_ref,),
                ).fetchone()
                fact = None if fact_row is None else _row_to_fact(fact_row)
                if (revision is None or revision[0] != commit_transaction_ref
                        or fact_row is None or fact_row[7] != asserted_world_revision
                        or not _normalized_retraction_fact_corresponds(
                            fact, claim_ref, occurrence_ref, proof_refs
                        )):
                    raise ValueError("normalized retraction is detached from its world commit")
                conn.execute(
                    "INSERT OR IGNORE INTO semantic_claim_retractions(retraction_ref,claim_ref,source_ref,occurrence_ref,proof_json,asserted_world_revision,commit_transaction_ref,payload_hash) VALUES(?,?,?,?,?,?,?,?)",
                    (retraction_ref, claim_ref, source_ref, occurrence_ref, _r3_canonical_json(payload["proof_refs"]),
                     asserted_world_revision, commit_transaction_ref, _payload_hash(payload)),
                )
                if own:
                    conn.commit()
            except BaseException:
                if own:
                    conn.rollback()
                raise
        else:
            if claim_ref not in self._backend._normalized_claims:
                raise ValueError("normalized retraction claim is absent")
            fact = self._backend.world.get(source_ref)
            if (self._backend.world._revision_transactions.get(asserted_world_revision) != commit_transaction_ref
                    or self._backend.world._fact_revisions.get(source_ref) != asserted_world_revision
                    or not _normalized_retraction_fact_corresponds(
                        fact, claim_ref, occurrence_ref, proof_refs
                    )):
                raise ValueError("normalized retraction is detached from its world commit")
            previous = self._backend._normalized_retractions.setdefault(retraction_ref, payload)
            if previous != payload:
                raise ValueError("normalized retraction identity collision")
            self._backend._normalized_retracted_claims.add(claim_ref)
        return retraction_ref

    @staticmethod
    def _normalized_maximum(maximum: int) -> int:
        if type(maximum) is not int or isinstance(maximum, bool) or not 1 <= maximum <= 256:
            raise ValueError("normalized read maximum must be an exact int in 1..256")
        return maximum

    @staticmethod
    def _normalized_payload(
        header: Mapping[str, Any], rows: Sequence[Sequence[Any]]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operator": header["operator"], "predicate_ref": header["predicate_ref"],
            "roles": [], "qualifiers": [],
        }
        for binding_kind, ordinal, role_ref, filler_kind, filler_value in rows:
            if filler_kind == "grounded":
                filler = {"kind": "grounded", "target_ref": filler_value}
            elif filler_kind == "application":
                filler = {"kind": "application", "application_ref": filler_value}
            elif filler_kind == "literal":
                literal = json.loads(filler_value)
                if type(literal) is not dict or set(literal) != {"value_type", "value"}:
                    raise ValueError("stored normalized literal is invalid")
                filler = {"kind": "literal", **literal}
            else:
                raise ValueError("stored normalized filler category is invalid")
            key = "roles" if binding_kind == "role" else "qualifiers"
            if binding_kind not in {"role", "qualifier"} or ordinal != len(payload[key]):
                raise ValueError("stored normalized binding ordinal is invalid")
            payload[key].append({"binding_kind": binding_kind, "ordinal": ordinal,
                                 "role_ref": role_ref, "filler": filler})
        if _payload_hash(payload) != header["payload_hash"]:
            raise ValueError("stored normalized application hash mismatch")
        return payload

    def _normalized_application_payloads(self, root_refs: Sequence[str]) -> dict[str, dict[str, Any]]:
        """Load a bounded union of closures in depth batches, never per claim."""
        from .gaps import BudgetExhausted

        pending = set(root_refs)
        payloads: dict[str, dict[str, Any]] = {}
        while pending:
            if len(payloads) + len(pending) > 256:
                raise BudgetExhausted("normalized application read exceeds bound", 256)
            refs = tuple(sorted(pending))
            pending.clear()
            if isinstance(self._backend, SQLiteSemanticStore):
                placeholders = ",".join("?" for _ in refs)
                header_rows = self._backend._conn.execute(
                    f"SELECT application_ref,operator,predicate_ref,payload_hash FROM semantic_applications "
                    f"WHERE application_ref IN ({placeholders})", refs,
                ).fetchall()
                headers = {row[0]: {"operator": row[1], "predicate_ref": row[2], "payload_hash": row[3]}
                           for row in header_rows}
                raw_bindings = self._backend._conn.execute(
                    f"SELECT application_ref,binding_kind,ordinal,role_ref,filler_kind,filler_value "
                    f"FROM semantic_application_bindings WHERE application_ref IN ({placeholders}) "
                    "ORDER BY application_ref,binding_kind,ordinal", refs,
                ).fetchall()
                bindings: dict[str, list[Sequence[Any]]] = {}
                for row in raw_bindings:
                    bindings.setdefault(row[0], []).append(tuple(row[1:]))
            else:
                headers = {ref: self._backend._normalized_applications[ref]
                           for ref in refs if ref in self._backend._normalized_applications}
                bindings = {
                    ref: [(row["binding_kind"], row["ordinal"], row["role_ref"],
                           row["filler_kind"], row["filler_value"])
                          for row in self._backend._normalized_bindings.get(ref, ())]
                    for ref in refs
                }
            if set(headers) != set(refs):
                raise ValueError("normalized application is missing")
            for ref in refs:
                payload = self._normalized_payload(headers[ref], bindings.get(ref, ()))
                payloads[ref] = payload
                for row in (*payload["roles"], *payload["qualifiers"]):
                    filler = row["filler"]
                    if filler["kind"] == "application" and filler["application_ref"] not in payloads:
                        pending.add(filler["application_ref"])
        return payloads

    @staticmethod
    def _hydrate_normalized_closures(
        root_refs: Sequence[str], payloads: Mapping[str, Mapping[str, Any]]
    ) -> dict[str, tuple[Any, ...]]:
        from .expressions import ApplicationFiller, GroundedReference, LiteralValue, RoleBinding, SemanticApplication

        hydrated: dict[str, SemanticApplication] = {}
        visiting: set[str] = set()

        def visit(application_ref: str, ordered: list[SemanticApplication], local_seen: set[str]) -> SemanticApplication:
            if application_ref in visiting:
                raise ValueError("stored normalized application graph is cyclic")
            result = hydrated.get(application_ref)
            if result is None:
                visiting.add(application_ref)
                payload = payloads[application_ref]

                def decode(row: Mapping[str, Any]) -> RoleBinding:
                    filler = row["filler"]
                    if filler["kind"] == "grounded":
                        value = GroundedReference(filler["target_ref"])
                    elif filler["kind"] == "literal":
                        value = LiteralValue(filler["value_type"], filler["value"])
                    elif filler["kind"] == "application":
                        child = visit(filler["application_ref"], ordered, local_seen)
                        value = ApplicationFiller(child.application_ref)
                    else:
                        raise ValueError("stored normalized filler category is invalid")
                    return RoleBinding(row["role_ref"], value)

                result = SemanticApplication(
                    application_ref, payload["operator"], payload["predicate_ref"],
                    tuple(decode(row) for row in payload["roles"]),
                    tuple(decode(row) for row in payload["qualifiers"]),
                )
                if stable_ref("semantic_application", _normalized_application_payload(result)) != application_ref:
                    raise ValueError("stored normalized application identity mismatch")
                visiting.remove(application_ref)
                hydrated[application_ref] = result
            if application_ref not in local_seen:
                for row in (*payloads[application_ref]["roles"], *payloads[application_ref]["qualifiers"]):
                    if row["filler"]["kind"] == "application":
                        visit(row["filler"]["application_ref"], ordered, local_seen)
                local_seen.add(application_ref)
                ordered.append(result)
            return result

        closures: dict[str, tuple[Any, ...]] = {}
        for root_ref in root_refs:
            ordered: list[SemanticApplication] = []
            visit(root_ref, ordered, set())
            closures[root_ref] = tuple(ordered)
        return closures

    def _normalized_claims(self, claim_refs: Sequence[str]) -> tuple[NormalizedApplicationClaim, ...]:
        refs = tuple(sorted(dict.fromkeys(claim_refs)))
        if not refs:
            return ()
        rows_by_ref: dict[str, tuple[dict[str, Any], bool, str]] = {}
        if isinstance(self._backend, SQLiteSemanticStore):
            placeholders = ",".join("?" for _ in refs)
            rows = self._backend._conn.execute(
                "SELECT claim_ref,application_ref,stance,fact_ref,source_ref,decision_ref,occurrence_ref,placement,placement_ref,proof_json,"
                "authority_generation,confidence_micros,asserted_world_revision,commit_transaction_ref,payload_hash,"
                "NOT EXISTS(SELECT 1 FROM semantic_claim_retractions r WHERE r.claim_ref=c.claim_ref) "
                f"FROM semantic_application_claims c WHERE claim_ref IN ({placeholders})", refs,
            ).fetchall()
            for row in rows:
                payload = {"application_ref": row[1], "stance": row[2], "fact_ref": row[3], "source_ref": row[4],
                           "decision_ref": row[5], "occurrence_ref": row[6], "placement": row[7], "placement_ref": row[8],
                           "proof_refs": json.loads(row[9]), "authority_generation": row[10], "confidence_micros": row[11],
                           "asserted_world_revision": row[12], "commit_transaction_ref": row[13]}
                rows_by_ref[row[0]] = (payload, bool(row[15]), row[14])
        else:
            for ref in refs:
                payload = self._backend._normalized_claims.get(ref)
                if payload is not None:
                    detached = json.loads(json.dumps(payload, ensure_ascii=False))
                    rows_by_ref[ref] = (
                        detached, ref not in self._backend._normalized_retracted_claims, _payload_hash(detached)
                    )
        if set(rows_by_ref) != set(refs):
            raise ValueError("normalized claim is missing")
        payloads = self._normalized_application_payloads(
            tuple(rows_by_ref[ref][0]["application_ref"] for ref in refs)
        )
        closures = self._hydrate_normalized_closures(
            tuple(rows_by_ref[ref][0]["application_ref"] for ref in refs), payloads
        )
        result = []
        for ref in refs:
            payload, active, digest = rows_by_ref[ref]
            if stable_ref("semantic_claim", payload) != ref or _payload_hash(payload) != digest:
                raise ValueError("normalized claim identity/hash mismatch")
            result.append(NormalizedApplicationClaim(
                ref, payload["application_ref"], payload["stance"], payload["fact_ref"], payload["source_ref"],
                payload["decision_ref"], payload["occurrence_ref"], payload["placement"], payload["placement_ref"],
                tuple(payload["proof_refs"]), payload["authority_generation"], payload["confidence_micros"],
                payload["asserted_world_revision"], payload["commit_transaction_ref"], active,
                closures[payload["application_ref"]],
            ))
        return tuple(result)

    def _normalized_claim(self, claim_ref: str) -> NormalizedApplicationClaim:
        return self._normalized_claims((claim_ref,))[0]

    def r3_active_application_claims_for_target(
        self, target_ref: str, *, maximum: int, expected_pin: RevisionPin
    ) -> tuple[NormalizedApplicationClaim, ...]:
        """Read active exact-target claims through target/claim indexes only."""
        from .gaps import BudgetExhausted
        maximum = self._normalized_maximum(maximum)
        self.r3_assert_read_pin(expected_pin)
        if type(target_ref) is not str or not target_ref:
            raise TypeError("target_ref must be exact nonempty str")
        if isinstance(self._backend, SQLiteSemanticStore):
            refs = tuple(row[0] for row in self._backend._conn.execute(
                "SELECT c.claim_ref FROM semantic_claim_target_postings t "
                "JOIN semantic_application_claims c ON c.claim_ref=t.claim_ref "
                "WHERE t.target_ref=? AND NOT EXISTS(SELECT 1 FROM semantic_claim_retractions r WHERE r.claim_ref=c.claim_ref) "
                "ORDER BY c.claim_ref LIMIT ?", (target_ref, maximum + 1)
            ))
        else:
            claim_refs = self._backend._normalized_target_index.get(target_ref, {})
            refs = tuple(sorted(claim_ref for claim_ref in claim_refs
                if claim_ref not in self._backend._normalized_retracted_claims)[:maximum + 1])
        if len(refs) > maximum:
            raise BudgetExhausted("normalized target claims exceed bound", maximum)
        return self._normalized_claims(refs)

    def r3_application_claims(
        self, application_refs: tuple[str, ...], *, maximum: int, expected_pin: RevisionPin
    ) -> tuple[NormalizedApplicationClaim, ...]:
        """Read all claims for exact application identities through keyed indexes."""
        from .gaps import BudgetExhausted
        maximum = self._normalized_maximum(maximum)
        self.r3_assert_read_pin(expected_pin)
        if type(application_refs) is not tuple or not application_refs or len(application_refs) > 256:
            raise ValueError("application_refs must contain 1..256 exact refs")
        if any(type(row) is not str or not row for row in application_refs):
            raise TypeError("application_refs must be exact nonempty strings")
        if len(application_refs) != len(set(application_refs)):
            raise ValueError("application_refs must be unique")
        if isinstance(self._backend, SQLiteSemanticStore):
            placeholders = ",".join("?" for _ in application_refs)
            refs = tuple(row[0] for row in self._backend._conn.execute(
                f"SELECT claim_ref FROM semantic_application_claims WHERE application_ref IN ({placeholders}) ORDER BY claim_ref LIMIT ?",
                (*application_refs, maximum + 1),
            ))
        else:
            refs = tuple(sorted({claim_ref for app_ref in application_refs
                for claim_ref in self._backend._normalized_claims_by_app.get(app_ref, {})})[:maximum + 1])
        if len(refs) > maximum:
            raise BudgetExhausted("normalized application claims exceed bound", maximum)
        return self._normalized_claims(refs)

    def revisions(self) -> dict[str, int]:
        """Return a snapshot of all store revisions."""
        return {
            "world": self.world.revision,
            "session": self.sessions.revision,
            "episode": self.episodes.revision,
            "effect": self.effects.revision,
        }


    # ------------------------------------------------------------------
    # Canonical R3 persistence port
    # ------------------------------------------------------------------

    def r3_world_snapshot(self, *, maximum: int) -> tuple[Fact, ...]:
        if type(maximum) is not int or isinstance(maximum, bool) or maximum < 1:
            raise ValueError("maximum must be a positive exact int")
        if isinstance(self._backend, SQLiteSemanticStore):
            rows = self._backend._conn.execute(
                "SELECT fact_ref, operator, args_json, stance, confidence, "
                "derived, proof_json FROM world_facts ORDER BY fact_ref LIMIT ?",
                (maximum + 1,),
            ).fetchall()
            values = tuple(_row_to_fact(row) for row in rows)
        else:
            values = tuple(
                self._backend.world.get(key)
                for key in sorted(self._backend.world._facts)[: maximum + 1]
            )
        if len(values) > maximum:
            raise ValueError("world snapshot exceeds its configured bound")
        return values

    def r3_world_facts(self) -> tuple[Fact, ...]:
        if isinstance(self._backend, SQLiteSemanticStore):
            rows = self._backend._conn.execute(
                "SELECT fact_ref, operator, args_json, stance, confidence, "
                "derived, proof_json FROM world_facts ORDER BY fact_ref",
            ).fetchall()
            return tuple(_row_to_fact(row) for row in rows)
        return tuple(
            self._backend.world.get(key)
            for key in sorted(self._backend.world._facts)
        )

    def r3_query_facts(self, operator: str, predicate: str,
                       constraints: tuple[tuple[str, str], ...], *, maximum: int) -> tuple[Fact, ...]:
        """Bounded indexed QUERY evidence; caller owns one r3_read_snapshot.

        Every posting probe reads at most max+1 keys, not facts. Any complete
        posting can prove the exact conjunction by checking its bounded rows.
        If all postings overflow, their unseen intersection is unknown and the
        caller must abstain, even if the true intersection might be small.
        Unconstrained reads return the max+1 sentinel for the caller to reject.
        """
        from .gaps import BudgetExhausted
        if type(maximum) is not int or not 1 <= maximum <= 256:
            raise ValueError("query maximum must be an exact int in 1..256")
        if type(operator) is not str or type(predicate) is not str or type(constraints) is not tuple:
            raise TypeError("query keys must be exact strings and tuple constraints")
        if len(constraints) > 256:
            raise BudgetExhausted("query constraint bound", 256)
        exact: dict[str, str] = {}
        for row in constraints:
            if type(row) is not tuple or len(row) != 2 or any(type(v) is not str for v in row):
                raise TypeError("query constraints must be exact role/value pairs")
            role, value = row
            if role in exact and exact[role] != value:
                return ()
            exact[role] = value
        best: tuple[str, ...] | None = None
        for role, value in (tuple(exact.items()) or (("", ""),)):
            if isinstance(self._backend, SQLiteSemanticStore):
                refs = tuple(row[0] for row in self._backend._conn.execute(
                    "SELECT fact_ref FROM world_query_keys WHERE operator=? AND predicate=? AND role=? AND value=? LIMIT ?",
                    (operator, predicate, role, value, maximum + 1)))
            else:
                refs = tuple(islice(self.world._query_indexes.get((operator, predicate, role, value), {}), maximum + 1))
            if best is None or len(refs) < len(best):
                best = refs
            if not refs:
                return ()
        if exact and len(best) > maximum:
            raise BudgetExhausted("query argument postings exceed bound", maximum)
        facts = tuple(self.world.get(ref) for ref in sorted(best))
        return tuple(fact for fact in facts if all(
            role in fact.args and _query_value(fact.args[role]) == value for role, value in constraints))

    def r3_session_snapshot(self, session_ref: str) -> Mapping[str, Any]:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        session = self.sessions.get(session_ref)
        if session is not None and session.session_ref != session_ref:
            raise ValueError("session snapshot stored key/session mismatch")
        if session is None:
            phase = "opening"
            turn_index = 0
            revision = 0
        else:
            phase = session.phase
            turn_index = session.turn_index
            revision = session.revision
        material = {
            "session_ref": session_ref,
            "session_phase_ref": phase,
            "turn_index": turn_index,
            "session_record_revision": revision,
            "store_revision": self.sessions.revision,
        }
        return {
            "snapshot_ref": stable_ref("r3_session_snapshot", material),
            **material,
        }

    def r3_begin_turn(self, session_ref: str) -> Mapping[str, Any]:
        snapshot = self.r3_session_snapshot(session_ref)
        turn_index = int(snapshot["turn_index"]) + 1
        material = {
            "session_ref": session_ref,
            "turn_index": turn_index,
            "session_store_revision": self.sessions.revision,
        }
        return {
            "snapshot_ref": stable_ref("r3_turn_reservation", material),
            "turn_ref": stable_ref("turn", material),
            **material,
        }

    def _recent_focus_entries(
        self, maximum: int, *, session_ref: str | None = None
    ) -> tuple["VerifiedSemanticFocus", ...]:
        """Decode only a bounded recent window of trusted persisted records.

        Rows are newest commit first, independently of ref spelling. The upper
        bound includes the R3 wrapper's overflow sentinel; the dialogue API keeps
        its own smaller bound. Authentication here proves stored-record integrity
        and revision consistency, not existence of a realization-equivalence
        receipt or permission to create new semantic focus.
        """
        from .dialogue import VerifiedSemanticFocus
        from .r3_codec import exact_int, optional_text

        exact_int(maximum, "maximum", maximum=10_000 + 1)
        optional_text(session_ref, "session_ref")
        pin = self.revision_pin()
        focus_revision = self.focus.revision
        entries = []
        for ref, session, payload, payload_hash, revision in self.focus.recent_rows(maximum, session_ref):
            if _payload_hash(payload) != payload_hash:
                raise ValueError("focus payload hash mismatch")
            row = VerifiedSemanticFocus.from_dict(payload)
            if row.focus_ref != ref or row.session_ref != session or (session_ref is not None and session != session_ref):
                raise ValueError("focus stored key/session mismatch")
            exact_int(revision, "focus commit revision", minimum=1)
            if revision > focus_revision:
                raise ValueError("focus commit revision exceeds current store revision")
            if row.revision_pin.authority_generation != pin.authority_generation:
                raise ValueError("focus authority generation differs from active store")
            if any(getattr(row.revision_pin, name) > getattr(pin, name) for name in (
                "world_revision", "session_revision", "episode_revision", "effect_revision",
            )):
                raise ValueError("focus revision pin exceeds current store revision")
            entries.append(row)
        return tuple(entries)

    def r3_focus_snapshot(
        self, session_ref: str, *, maximum: int
    ) -> Mapping[str, Any]:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        if type(maximum) is not int or not 1 <= maximum <= 10_000:
            raise ValueError("maximum must be a positive exact int")
        # These remain record identities, not speech-content projection.
        refs = [row.focus_ref for row in self._recent_focus_entries(maximum + 1, session_ref=session_ref)]
        if len(refs) > maximum:
            raise ValueError("focus snapshot exceeds its configured bound")
        material = {
            "session_ref": session_ref,
            "focus_refs": refs,
            "focus_store_revision": self.focus.revision,
        }
        return {
            "snapshot_ref": stable_ref("r3_focus_snapshot", material),
            **material,
        }

    def pending_dialogue_obligations(
        self, session_ref: str, obligation_refs: tuple[str, ...], *, maximum: int, turn_index: int,
        include_expired: bool = False,
    ) -> tuple["DialogueObligation", ...]:
        """Authenticate only requested pending dialogue records, in input order.

        This is a keyed persistence read, not proof that these refs belong to a
        SituationContext or that an answer fills the source query's exact slot.
        Only the canonical generic dialogue wire shape is admitted.
        """
        from .dialogue import DialogueObligation
        from .r3_codec import exact_bool, exact_int, exact_refs, exact_text

        exact_text(session_ref, "session_ref")
        exact_int(maximum, "maximum", minimum=1, maximum=512)
        exact_refs(obligation_refs, "obligation_refs", maximum=maximum)
        exact_int(turn_index, "turn_index")
        exact_bool(include_expired, "include_expired")
        pin, store_revision = self.revision_pin(), self.obligations.revision
        entries = []
        for ref in obligation_refs:
            stored = self.obligations.keyed_row(ref)
            if stored is None:
                raise ValueError("requested obligation is missing")
            key, session, payload, digest, revision, resolved = stored
            if _payload_hash(payload) != digest:
                raise ValueError("obligation payload hash mismatch")
            if type(payload) is not dict or type(payload.get("resolved")) is not bool:
                raise ValueError("invalid obligation status envelope")
            if type(resolved) is not int or resolved != 0 or payload["resolved"] is not False:
                raise ValueError("obligation is not pending")
            data = {name: value for name, value in payload.items() if name != "resolved"}
            row = DialogueObligation.from_dict(data)
            if key != ref or row.obligation_ref != ref or session != session_ref or row.session_ref != session:
                raise ValueError("obligation stored key/session mismatch")
            exact_int(revision, "obligation commit revision", minimum=1)
            if revision > store_revision:
                raise ValueError("obligation commit revision exceeds current store revision")
            if row.revision_pin.authority_generation != pin.authority_generation:
                raise ValueError("obligation authority generation differs from active store")
            if any(getattr(row.revision_pin, name) > getattr(pin, name) for name in (
                "world_revision", "session_revision", "episode_revision", "effect_revision",
            )):
                raise ValueError("obligation revision pin exceeds current store revision")
            if (row.completion_receipt_ref is not None or row.created_turn_index > turn_index
                    or (not include_expired and turn_index >= row.expires_turn_index)):
                raise ValueError("obligation is completed, not yet active or expired")
            entries.append(row)
        return tuple(entries)

    def r3_obligation_snapshot(
        self, session_ref: str, *, maximum: int
    ) -> Mapping[str, Any]:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        if type(maximum) is not int or isinstance(maximum, bool) or maximum < 1:
            raise ValueError("maximum must be a positive exact int")
        refs: list[str] = []
        if isinstance(self._backend, SQLiteSemanticStore):
            rows = self._backend._conn.execute(
                "SELECT obligation_ref FROM obligations WHERE session_ref=? "
                "AND resolved=0 ORDER BY revision, obligation_ref LIMIT ?",
                (session_ref, maximum + 1),
            ).fetchall()
            refs = [str(row[0]) for row in rows]
        else:
            refs = self._backend.obligations.pending_refs(session_ref, maximum + 1)
        if len(refs) > maximum:
            raise ValueError("obligation snapshot exceeds its configured bound")
        material = {
            "session_ref": session_ref,
            "obligation_refs": refs,
            "obligation_store_revision": self.obligations.revision,
        }
        return {
            "snapshot_ref": stable_ref("r3_obligation_snapshot", material),
            **material,
        }

    def r3_effect_journal_get(
        self, idempotency_key: str
    ) -> Mapping[str, Any] | None:
        if type(idempotency_key) is not str or not idempotency_key:
            raise TypeError("idempotency_key must be exact nonempty str")
        if isinstance(self._backend, SQLiteSemanticStore):
            row = self._backend._conn.execute(
                "SELECT entry_json, entry_hash, receipt_json, receipt_hash "
                "FROM r3_effect_journal WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if row is None:
                return None
            return _r3_verify_journal_row(row[0], row[1], row[2], row[3])
        stored = self._backend._r3_effect_journals.get(idempotency_key)
        return None if stored is None else json.loads(_r3_canonical_json(stored))

    def r3_effect_journal_begin(
        self,
        *,
        idempotency_key: str,
        intent_ref: str,
        decision_ref: str,
        request_payload: Mapping[str, Any],
        expected_effect_revision: int,
        expected_revision_pin: RevisionPin | None = None,
    ) -> Mapping[str, Any]:
        from .r3_persistence import EffectJournalEntry, EffectJournalState
        from .r3_codec import thaw_json

        existing = self.r3_effect_journal_get(idempotency_key)
        if existing is not None:
            entry = EffectJournalEntry.from_dict(existing["entry"])
            expected_request = json.loads(_r3_canonical_json(request_payload))
            if (
                entry.intent_ref != intent_ref
                or entry.decision_ref != decision_ref
                or thaw_json(entry.request_payload) != expected_request
            ):
                raise ValueError("idempotency key is already bound to another request")
            return existing
        if expected_revision_pin is not None:
            if type(expected_revision_pin) is not RevisionPin:
                raise TypeError("expected_revision_pin must be exact RevisionPin or None")
            if expected_revision_pin != self.revision_pin():
                raise StaleRevisionError("effect request revision pin is stale")
            if expected_effect_revision != expected_revision_pin.effect_revision:
                raise ValueError("effect request effect revision does not match its pin")
        if expected_effect_revision != self.effects.revision:
            raise StaleRevisionError(
                f"effects: expected {expected_effect_revision}, got {self.effects.revision}"
            )
        new_revision = expected_effect_revision + 1
        entry = EffectJournalEntry.create(
            idempotency_key=idempotency_key,
            state=EffectJournalState.PLANNED,
            attempt_index=0,
            intent_ref=intent_ref,
            decision_ref=decision_ref,
            request_payload=request_payload,
            observation_payload=None,
            outcome_ref=None,
            blocker_refs=(),
            parent_journal_ref=None,
            effect_revision=new_revision,
        )
        stored = {"entry": entry.as_dict(), "receipt": None}
        # Serialize and authenticate proposal evidence before any memory write.
        _r3_canonical_json(stored)
        if "learning_plan" in entry.request_payload:
            from .r3_learning import validate_learning_proposal_request
            validate_learning_proposal_request(self, entry.request_payload, planned=False)
        publication = entry.request_payload.get("kind") == "learning_publication"
        if publication:
            from .r3_learning import validate_publication_snapshot
            validate_publication_snapshot(self, entry.request_payload, effect_increments=0)
        if isinstance(self._backend, SQLiteSemanticStore):
            conn = self._backend._conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT value FROM metadata WHERE key='effect_revision'"
                ).fetchone()
                current = int(row[0]) if row else 0
                if current != expected_effect_revision:
                    raise StaleRevisionError(
                        f"effects: expected {expected_effect_revision}, got {current}"
                    )
                if expected_revision_pin is not None:
                    for field in (
                        "world_revision",
                        "session_revision",
                        "episode_revision",
                    ):
                        row = conn.execute(
                            "SELECT value FROM metadata WHERE key=?", (field,)
                        ).fetchone()
                        current = int(row[0]) if row else 0
                        if current != getattr(expected_revision_pin, field):
                            raise StaleRevisionError(
                                f"effect request {field} changed concurrently"
                            )
                if "learning_plan" in entry.request_payload:
                    row = conn.execute("SELECT value FROM metadata WHERE key='obligation_revision'").fetchone()
                    if (int(row[0]) if row else 0) != self.obligations.revision:
                        raise StaleRevisionError("learning proposal obligation revision changed concurrently")
                    validate_learning_proposal_request(self, entry.request_payload, planned=False)
                if publication:
                    row = conn.execute("SELECT value FROM metadata WHERE key='obligation_revision'").fetchone()
                    if (int(row[0]) if row else 0) != self.obligations.revision:
                        raise StaleRevisionError("publication obligation revision changed concurrently")
                    validate_publication_snapshot(self, entry.request_payload, effect_increments=0)
                entry_json = _r3_canonical_json(entry.as_dict())
                conn.execute(
                    "INSERT INTO r3_effect_journal(idempotency_key, entry_json, "
                    "entry_hash, receipt_json, receipt_hash, effect_revision) "
                    "VALUES(?, ?, ?, NULL, NULL, ?)",
                    (
                        idempotency_key,
                        entry_json,
                        _payload_hash(entry.as_dict()),
                        new_revision,
                    ),
                )
                conn.execute(
                    "INSERT INTO metadata(key, value) VALUES('effect_revision', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(new_revision),),
                )
                _r3_insert_revision(
                    conn,
                    store="effects",
                    parent_revision=expected_effect_revision,
                    new_revision=new_revision,
                    delta_hash=_payload_hash(stored),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            self.effects.revision = new_revision
        else:
            self._backend._r3_effect_journals[idempotency_key] = stored
            self.effects.revision = new_revision
        return stored

    def _prepare_query_continuation_transition(self, entry, receipt_payload):
        """Authenticate journal-bound continuity and prepare every row before writes.

        The caller holds the SQLite transaction (or the synchronous memory
        transition). Obligation revision is deliberately not a RevisionPin field.
        """
        from .dialogue import query_continuation, query_continuation_request
        from .config import RuntimeConfig
        from .r3_artifacts import EvaluationBundle
        from .r3_codec import exact_int, thaw_json
        from .r3_effects import NoEffectReason, NoEffectReceipt, R3EffectGateway, _predicted_pin
        from .r3_persistence import EffectJournalState

        request = thaw_json(entry.request_payload)
        if "query_evaluation" not in request and "query_continuation" not in request:
            return ()
        evaluation = EvaluationBundle.from_dict(request.get("query_evaluation"))
        if "query_continuation" not in request:
            if query_continuation(evaluation) is not None:
                raise ValueError("query journal is missing its required continuation")
            return ()
        decision, source = evaluation.decision, evaluation.situation
        if entry.state is not EffectJournalState.NO_EFFECT:
            raise ValueError("query continuation requires terminal no-effect")
        receipt = NoEffectReceipt.from_dict(thaw_json(receipt_payload))
        origin = stable_ref("effect_journal_origin", {"decision_ref": decision.decision_ref, "kind": "no_effect:unknown"})
        if (entry.idempotency_key != R3EffectGateway._effect_key(decision.decision_ref, None, "no_effect:unknown")
                or entry.intent_ref != origin or entry.decision_ref != decision.decision_ref
                or request.get("journal_origin_ref") != origin or request.get("kind") != "no_effect"
                or request.get("reason") != "unknown" or request.get("decision_ref") != decision.decision_ref
                or any(request.get(name) != getattr(source, name) for name in
                       ("session_ref", "turn_ref", "turn_index", "session_phase_ref"))):
            raise ValueError("query continuation journal lineage mismatch")
        expected_receipt = NoEffectReceipt.create(reason=NoEffectReason.UNKNOWN,
            idempotency_key=entry.idempotency_key, journal_origin_ref=origin,
            journal_preterminal_ref=entry.parent_journal_ref, decision_ref=decision.decision_ref,
            verified_meaning_ref=decision.verified_meaning_ref, expression_ref=evaluation.expression.expression_ref,
            situation_ref=source.situation_ref, program_ref=decision.program_ref,
            learning_plan_ref=None, source_obligation_ref=None, proof_refs=decision.proof_refs,
            blocker_refs=decision.blocker_refs, input_revision_pin=evaluation.revision_pin,
            output_revision_pin=_predicted_pin(self.revision_pin(), session=1, effects=1))
        if (receipt != expected_receipt or entry.outcome_ref != receipt.receipt_ref
                or entry.blocker_refs != decision.blocker_refs):
            raise ValueError("query continuation terminal receipt mismatch")
        # Compare the snapshot before decoding rows: an intervening legitimate
        # revision is a stale request, never permission to refresh its meaning.
        maximum = exact_int(request.get("query_obligation_maximum"), "query obligation maximum",
            minimum=1, maximum=RuntimeConfig.max_orientation_alternatives)
        snapshot = self.r3_obligation_snapshot(source.session_ref, maximum=maximum)
        if snapshot != request.get("query_obligation_snapshot"):
            raise StaleRevisionError("query continuation obligation snapshot changed")
        expected = query_continuation_request(self, evaluation, maximum=maximum)
        if not expected or any(request.get(name) != value for name, value in expected.items()):
            raise ValueError("query continuation canonical rows changed")
        candidate = expected["query_continuation"]
        if candidate is None:
            return ()
        retired = set(expected["query_retired_obligation_refs"])
        data = [(row["obligation_ref"], {**row, "resolved": True})
                for row in expected["query_obligation_rows"] if row["obligation_ref"] in retired]
        data.append((candidate["obligation_ref"], {**candidate, "resolved": False}))
        return tuple((ref, _MemoryObligationStore._prepare_row(ref, source.session_ref, payload,
            self.obligations.revision + 1, payload["resolved"])) for ref, payload in data)

    def _validate_learning_proposal_transition(self, entry, receipt_payload):
        if "learning_plan" not in entry.request_payload:
            return
        from .r3_learning import validate_learning_proposal_request
        from .r3_effects import NoEffectReason, NoEffectReceipt, R3EffectGateway, _predicted_pin
        from .r3_persistence import EffectJournalState
        from .r3_codec import thaw_json
        meaning, evaluation, plan, source = validate_learning_proposal_request(self, entry.request_payload, planned=True)
        situation, decision = evaluation.situation, evaluation.decision
        reason = NoEffectReason.LEARNING_OBLIGATION_ONLY
        origin = stable_ref("effect_journal_origin", {"decision_ref": decision.decision_ref,
            "kind": f"no_effect:{reason.value}"})
        request = entry.request_payload
        if (entry.state is not EffectJournalState.NO_EFFECT or entry.attempt_index != 0
                or entry.idempotency_key != R3EffectGateway._effect_key(decision.decision_ref, None, f"no_effect:{reason.value}")
                or entry.intent_ref != origin or entry.decision_ref != decision.decision_ref
                or request.get("journal_origin_ref") != origin or request.get("reason") != reason.value
                or request.get("kind") != "no_effect" or request.get("decision_ref") != decision.decision_ref
                or any(request.get(name) != getattr(situation, name) for name in
                       ("session_ref", "turn_ref", "turn_index", "session_phase_ref"))):
            raise ValueError("learning proposal terminal journal lineage mismatch")
        receipt = NoEffectReceipt.from_dict(thaw_json(receipt_payload))
        expected = NoEffectReceipt.create(reason=reason, idempotency_key=entry.idempotency_key,
            journal_origin_ref=origin, journal_preterminal_ref=entry.parent_journal_ref,
            decision_ref=decision.decision_ref, verified_meaning_ref=meaning.verified_meaning_ref,
            expression_ref=meaning.expression.expression_ref, situation_ref=situation.situation_ref,
            program_ref=meaning.program_ref, learning_plan_ref=plan.plan_ref, source_obligation_ref=source.obligation_ref,
            proof_refs=decision.proof_refs, blocker_refs=decision.blocker_refs,
            input_revision_pin=situation.revision_pin,
            output_revision_pin=_predicted_pin(self.revision_pin(), session=1, effects=1))
        if (receipt != expected or entry.outcome_ref != receipt.receipt_ref
                or entry.blocker_refs != decision.blocker_refs):
            raise ValueError("learning proposal terminal receipt mismatch")

    def r3_effect_journal_transition(
        self,
        *,
        idempotency_key: str,
        expected_state: str,
        next_state: str,
        observation_payload: Mapping[str, Any] | None,
        outcome_ref: str | None,
        receipt_payload: Mapping[str, Any] | None,
        blocker_refs: tuple[str, ...],
        expected_effect_revision: int,
    ) -> Mapping[str, Any]:
        from .r3_persistence import (
            EffectJournalEntry,
            EffectJournalState,
            StoredEffectJournal,
            validate_journal_transition,
        )

        existing = self.r3_effect_journal_get(idempotency_key)
        if existing is None:
            raise ValueError("effect journal entry is absent")
        current_entry = EffectJournalEntry.from_dict(existing["entry"])
        source = EffectJournalState(expected_state)
        target = EffectJournalState(next_state)
        if current_entry.state is not source:
            raise ValueError(
                f"effect journal state mismatch: {current_entry.state.value}!={source.value}"
            )
        validate_journal_transition(source, target)
        if expected_effect_revision != self.effects.revision:
            raise StaleRevisionError(
                f"effects: expected {expected_effect_revision}, got {self.effects.revision}"
            )
        new_effect_revision = expected_effect_revision + 1
        attempt_index = current_entry.attempt_index
        if target is EffectJournalState.INVOCATION_STARTED or source is EffectJournalState.PENDING_RECONCILIATION:
            attempt_index += 1
        entry = EffectJournalEntry.create(
            idempotency_key=idempotency_key,
            state=target,
            attempt_index=attempt_index,
            intent_ref=current_entry.intent_ref,
            decision_ref=current_entry.decision_ref,
            request_payload=current_entry.request_payload,
            observation_payload=observation_payload,
            outcome_ref=outcome_ref,
            blocker_refs=blocker_refs,
            parent_journal_ref=current_entry.journal_ref,
            effect_revision=new_effect_revision,
        )
        stored = StoredEffectJournal(entry, receipt_payload).as_dict()
        _r3_canonical_json(stored)
        publication = entry.request_payload.get("kind") == "learning_publication"
        if publication and target.terminal:
            raise ValueError("publication terminal writes require atomic fact/completion commit")
        if publication:
            from .r3_effects import R3EffectGateway
            from .r3_codec import thaw_json
            expected_observation = (R3EffectGateway._publication_observation(entry.request_payload)[1]
                if target is EffectJournalState.OBSERVED else None)
            if thaw_json(entry.observation_payload) != expected_observation:
                raise ValueError("publication observation lineage mismatch")
        terminal = target.terminal
        obligation_parent = self.obligations.revision
        prepared_obligations = ()
        if isinstance(self._backend, SQLiteSemanticStore):
            conn = self._backend._conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT entry_json, entry_hash, receipt_json, receipt_hash "
                    "FROM r3_effect_journal WHERE idempotency_key=?",
                    (idempotency_key,),
                ).fetchone()
                if row is None:
                    raise ValueError("effect journal entry disappeared")
                observed = _r3_verify_journal_row(row[0], row[1], row[2], row[3])
                if observed["entry"]["journal_ref"] != current_entry.journal_ref:
                    raise StaleRevisionError("effect journal parent changed concurrently")
                # Recheck cached revisions against the locked database, including
                # the separate obligation revision. Another connection may have
                # committed since the gateway assembled this receipt.
                revision_fields = (("effect_revision", expected_effect_revision),)
                if "query_continuation" in entry.request_payload or "learning_plan" in entry.request_payload or publication:
                    pin = self.revision_pin()
                    revision_fields += (("session_revision", pin.session_revision),
                        ("world_revision", pin.world_revision), ("episode_revision", pin.episode_revision),
                        ("obligation_revision", obligation_parent))
                for name, expected_revision in revision_fields:
                    row = conn.execute("SELECT value FROM metadata WHERE key=?", (name,)).fetchone()
                    if (int(row[0]) if row else 0) != expected_revision:
                        raise StaleRevisionError(f"query/effect transition {name} changed concurrently")
                self._validate_learning_proposal_transition(entry, receipt_payload)
                if publication:
                    from .r3_learning import validate_publication_snapshot
                    validate_publication_snapshot(self, entry.request_payload,
                        effect_increments={"planned": 1, "authorized": 2}[source.value])
                prepared_obligations = self._prepare_query_continuation_transition(entry, receipt_payload)
                session_parent = self.sessions.revision
                session_new = session_parent
                if terminal:
                    session_ref, turn_index, phase = _r3_terminal_turn(entry)
                    session_new = session_parent + 1
                    _r3_write_session_sqlite(
                        conn,
                        session_ref=session_ref,
                        turn_index=turn_index,
                        session_phase_ref=phase,
                        parent_revision=session_parent,
                        new_revision=session_new,
                    )
                for ref, (payload, metadata) in prepared_obligations:
                    session, digest, revision, resolved = metadata
                    if resolved:
                        changed = conn.execute("UPDATE obligations SET payload_json=?, payload_hash=?, revision=?, resolved=1 "
                            "WHERE obligation_ref=? AND session_ref=? AND resolved=0",
                            (_r3_canonical_json(payload), digest, revision, ref, session)).rowcount
                        if changed != 1:
                            raise StaleRevisionError("expired continuation changed concurrently")
                    else:
                        conn.execute("INSERT INTO obligations(obligation_ref, session_ref, payload_json, payload_hash, revision, resolved) "
                            "VALUES(?, ?, ?, ?, ?, 0)", (ref, session, _r3_canonical_json(payload), digest, revision))
                if prepared_obligations:
                    conn.execute("INSERT INTO metadata(key, value) VALUES('obligation_revision', ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(obligation_parent + 1),))
                    _r3_insert_revision(conn, store="obligations", parent_revision=obligation_parent,
                        new_revision=obligation_parent + 1, delta_hash=_payload_hash([row[1][0] for row in prepared_obligations]))
                entry_json = _r3_canonical_json(entry.as_dict())
                receipt_json = (
                    None if receipt_payload is None else _r3_canonical_json(receipt_payload)
                )
                conn.execute(
                    "UPDATE r3_effect_journal SET entry_json=?, entry_hash=?, "
                    "receipt_json=?, receipt_hash=?, effect_revision=? "
                    "WHERE idempotency_key=?",
                    (
                        entry_json,
                        _payload_hash(entry.as_dict()),
                        receipt_json,
                        None if receipt_payload is None else _payload_hash(receipt_payload),
                        new_effect_revision,
                        idempotency_key,
                    ),
                )
                conn.execute(
                    "INSERT INTO metadata(key, value) VALUES('effect_revision', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(new_effect_revision),),
                )
                _r3_insert_revision(
                    conn,
                    store="effects",
                    parent_revision=expected_effect_revision,
                    new_revision=new_effect_revision,
                    delta_hash=_payload_hash(stored),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            self.effects.revision = new_effect_revision
            if terminal:
                self.sessions.revision = session_new
            if prepared_obligations:
                self.obligations.revision = obligation_parent + 1
        else:
            self._validate_learning_proposal_transition(entry, receipt_payload)
            if publication:
                from .r3_learning import validate_publication_snapshot
                validate_publication_snapshot(self, entry.request_payload,
                    effect_increments={"planned": 1, "authorized": 2}[source.value])
            prepared_obligations = self._prepare_query_continuation_transition(entry, receipt_payload)
            if terminal:
                session_ref, turn_index, phase = _r3_terminal_turn(entry)
                session_parent = self.sessions.revision
                session_new = session_parent + 1
                session, _payload = _r3_session_material(
                    session_ref=session_ref,
                    turn_index=turn_index,
                    session_phase_ref=phase,
                    revision=session_new,
                )
                self._backend.sessions._sessions[session_ref] = session
                self.sessions.revision = session_new
            for ref, prepared in prepared_obligations:
                self._backend.obligations._store_row(ref, prepared)
            if prepared_obligations:
                self.obligations.revision = obligation_parent + 1
            self._backend._r3_effect_journals[idempotency_key] = stored
            self.effects.revision = new_effect_revision
        return stored

    def r3_effect_journal_commit(
        self,
        *,
        idempotency_key: str,
        expected_state: str,
        observation_payload: Mapping[str, Any],
        outcome_ref: str,
        receipt_payload: Mapping[str, Any],
        facts: tuple[Fact, ...],
        expected_revision_pin: RevisionPin,
    ) -> Mapping[str, Any]:
        from .r3_persistence import (
            EffectJournalEntry,
            EffectJournalState,
            StoredEffectJournal,
            validate_journal_transition,
        )

        if type(facts) is not tuple or not facts or any(type(row) is not Fact for row in facts):
            raise TypeError("facts must be a nonempty exact Fact tuple")
        if expected_revision_pin != self.revision_pin():
            raise StaleRevisionError("atomic effect commit revision pin is stale")
        existing = self.r3_effect_journal_get(idempotency_key)
        if existing is None:
            raise ValueError("effect journal entry is absent")
        current_entry = EffectJournalEntry.from_dict(existing["entry"])
        source = EffectJournalState(expected_state)
        if current_entry.state is not source:
            raise ValueError("effect journal is not in the expected precommit state")
        validate_journal_transition(source, EffectJournalState.COMMITTED)
        new_world = expected_revision_pin.world_revision + 1
        new_effect = expected_revision_pin.effect_revision + 1
        new_session = expected_revision_pin.session_revision + 1
        entry = EffectJournalEntry.create(
            idempotency_key=idempotency_key,
            state=EffectJournalState.COMMITTED,
            attempt_index=current_entry.attempt_index,
            intent_ref=current_entry.intent_ref,
            decision_ref=current_entry.decision_ref,
            request_payload=current_entry.request_payload,
            observation_payload=observation_payload,
            outcome_ref=outcome_ref,
            blocker_refs=(),
            parent_journal_ref=current_entry.journal_ref,
            effect_revision=new_effect,
        )
        stored = StoredEffectJournal(entry, receipt_payload).as_dict()
        publication = entry.request_payload.get("kind") == "learning_publication"
        obligation_parent = self.obligations.revision
        prepared_obligations = ()
        # Complete all potentially failing serialization before mutating memory.
        entry_json = _r3_canonical_json(entry.as_dict())
        receipt_json = _r3_canonical_json(receipt_payload)
        prepared_facts = tuple({**_fact_to_row(fact), "payload_hash": _payload_hash(_fact_payload(fact)),
            "revision": new_world} for fact in facts)
        world_delta = [_fact_payload(row) for row in facts]
        _r3_canonical_json(world_delta)
        world_transaction_ref = _r3_revision_transaction_ref(
            "world", expected_revision_pin.world_revision, _payload_hash(world_delta)
        )
        normalized_batch = None
        if publication:
            new_session = expected_revision_pin.session_revision
            prepared_obligations = self._prepare_publication_commit(current_entry, entry, receipt_payload, facts)
            normalized_batch = _prepare_normalized_alias_publication(
                facts[0],
                request_payload=entry.request_payload,
                receipt_payload=receipt_payload,
                authority_generation=expected_revision_pin.authority_generation,
                asserted_world_revision=new_world,
                commit_transaction_ref=world_transaction_ref,
            )
        else:
            session_ref, turn_index, phase = _r3_terminal_turn(entry)
            session, _payload = _r3_session_material(session_ref=session_ref, turn_index=turn_index,
                session_phase_ref=phase, revision=new_session)
        if isinstance(self._backend, SQLiteSemanticStore):
            conn = self._backend._conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                for key, expected in (
                    ("world_revision", expected_revision_pin.world_revision),
                    ("session_revision", expected_revision_pin.session_revision),
                    ("effect_revision", expected_revision_pin.effect_revision),
                    ("episode_revision", expected_revision_pin.episode_revision),
                    *(((("obligation_revision", obligation_parent),) if publication else ())),
                ):
                    row = conn.execute(
                        "SELECT value FROM metadata WHERE key=?", (key,)
                    ).fetchone()
                    actual = int(row[0]) if row else 0
                    if actual != expected:
                        raise StaleRevisionError(
                            f"{key}: expected {expected}, got {actual}"
                        )
                locked = self.r3_effect_journal_get(idempotency_key)
                if locked is None or locked["entry"]["journal_ref"] != current_entry.journal_ref:
                    raise StaleRevisionError("effect journal parent changed concurrently")
                if publication:
                    prepared_obligations = self._prepare_publication_commit(current_entry, entry, receipt_payload, facts)
                for row in prepared_facts:
                    conn.execute(
                        "INSERT INTO world_facts(fact_ref, operator, args_json, "
                        "stance, confidence, derived, proof_json, payload_hash, revision) "
                        "VALUES(:fact_ref, :operator, :args_json, :stance, :confidence, "
                        ":derived, :proof_json, :payload_hash, :revision) "
                        "ON CONFLICT(fact_ref) DO UPDATE SET operator=excluded.operator, "
                        "args_json=excluded.args_json, stance=excluded.stance, "
                        "confidence=excluded.confidence, derived=excluded.derived, "
                        "proof_json=excluded.proof_json, payload_hash=excluded.payload_hash, "
                        "revision=excluded.revision",
                        row,
                    )
                world_delta = [_fact_payload(row) for row in facts]
                conn.execute(
                    "INSERT INTO metadata(key, value) VALUES('world_revision', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(new_world),),
                )
                _r3_insert_revision(
                    conn,
                    store="world",
                    parent_revision=expected_revision_pin.world_revision,
                    new_revision=new_world,
                    delta_hash=_payload_hash(world_delta),
                )
                if normalized_batch is not None:
                    self._r3_write_normalized_batch(normalized_batch)
                if not publication:
                    _r3_write_session_sqlite(conn, session_ref=session_ref, turn_index=turn_index,
                        session_phase_ref=phase, parent_revision=expected_revision_pin.session_revision,
                        new_revision=new_session)
                for index, (ref, (payload, metadata)) in enumerate(prepared_obligations):
                    owner_session, digest, revision, resolved = metadata
                    if index == 0:
                        changed = conn.execute("UPDATE obligations SET payload_json=?,payload_hash=?,revision=?,resolved=1 "
                            "WHERE obligation_ref=? AND session_ref=? AND resolved=0",
                            (_r3_canonical_json(payload), digest, revision, ref, owner_session)).rowcount
                        if changed != 1:
                            raise StaleRevisionError("publication pending row changed concurrently")
                    else:
                        conn.execute("INSERT INTO obligations(obligation_ref,session_ref,payload_json,payload_hash,revision,resolved) "
                            "VALUES(?,?,?,?,?,1)", (ref, owner_session, _r3_canonical_json(payload), digest, revision))
                if prepared_obligations:
                    conn.execute("INSERT INTO metadata(key,value) VALUES('obligation_revision',?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(obligation_parent + 1),))
                    _r3_insert_revision(conn, store="obligations", parent_revision=obligation_parent,
                        new_revision=obligation_parent + 1,
                        delta_hash=_payload_hash([row[1][0] for row in prepared_obligations]))
                entry_json = _r3_canonical_json(entry.as_dict())
                receipt_json = _r3_canonical_json(receipt_payload)
                conn.execute(
                    "UPDATE r3_effect_journal SET entry_json=?, entry_hash=?, "
                    "receipt_json=?, receipt_hash=?, effect_revision=? "
                    "WHERE idempotency_key=?",
                    (
                        entry_json,
                        _payload_hash(entry.as_dict()),
                        receipt_json,
                        _payload_hash(receipt_payload),
                        new_effect,
                        idempotency_key,
                    ),
                )
                conn.execute(
                    "INSERT INTO metadata(key, value) VALUES('effect_revision', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(new_effect),),
                )
                _r3_insert_revision(
                    conn,
                    store="effects",
                    parent_revision=expected_revision_pin.effect_revision,
                    new_revision=new_effect,
                    delta_hash=_payload_hash(stored),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            self.world.revision = new_world
            self.sessions.revision = new_session
            self.effects.revision = new_effect
            if prepared_obligations:
                self.obligations.revision = obligation_parent + 1
        else:
            missing = object()
            world_before = {
                fact.fact_ref: (
                    self._backend.world.get(fact.fact_ref),
                    self._backend.world._fact_revisions.get(fact.fact_ref, missing),
                )
                for fact in facts
            }
            transaction_before = self._backend.world._revision_transactions.get(new_world, missing)
            normalized_before = None
            if normalized_batch is not None:
                application_refs = tuple(row.application_ref for row in normalized_batch.applications)
                target_refs = tuple(dict.fromkeys(
                    target_ref
                    for application in normalized_batch.applications
                    for target_ref in (
                        application.predicate_ref,
                        *(
                            filler["target_ref"]
                            for binding in (*application.roles, *application.qualifiers)
                            for filler in (_normalized_filler_payload(binding.filler),)
                            if filler["kind"] == "grounded"
                        ),
                    )
                ))
                normalized_before = {
                    "applications": {ref: self._backend._normalized_applications.get(ref, missing) for ref in application_refs},
                    "bindings": {ref: self._backend._normalized_bindings.get(ref, missing) for ref in application_refs},
                    "claim": self._backend._normalized_claims.get(normalized_batch.claim_ref, missing),
                    "claim_by_fact": self._backend._normalized_claim_by_fact.get(
                        normalized_batch.claim_payload["fact_ref"], missing
                    ),
                    "claims_by_app": self._backend._normalized_claims_by_app.get(
                        normalized_batch.root_application_ref, missing
                    ),
                    "targets": {ref: self._backend._normalized_target_index.get(ref, missing) for ref in target_refs},
                }
                if normalized_before["claims_by_app"] is not missing:
                    normalized_before["claims_by_app"] = OrderedDict(normalized_before["claims_by_app"])
                normalized_before["targets"] = {
                    ref: (value if value is missing else OrderedDict(value))
                    for ref, value in normalized_before["targets"].items()
                }
            obligation_before = {
                ref: (
                    self._backend.obligations._obligations.get(ref, missing),
                    self._backend.obligations._row_metadata.get(ref, missing),
                )
                for ref, _prepared in prepared_obligations
            }
            affected_pending_sessions = {
                prepared[1][0] for _ref, prepared in prepared_obligations
            } | {
                metadata[0] for _payload, metadata in obligation_before.values()
                if metadata is not missing
            }
            pending_before = {
                session: (
                    missing if session not in self._backend.obligations._pending_by_session
                    else dict(self._backend.obligations._pending_by_session[session])
                )
                for session in affected_pending_sessions
            }
            session_before = missing if publication else self._backend.sessions._sessions.get(session_ref, missing)
            journal_before = self._backend._r3_effect_journals.get(idempotency_key, missing)
            try:
                for fact in facts:
                    self._backend.world._store_fact(fact)
                    self._backend.world._fact_revisions[fact.fact_ref] = new_world
                self._backend.world._revision_transactions[new_world] = world_transaction_ref
                if normalized_batch is not None:
                    self._r3_write_normalized_batch(normalized_batch)
                self.world.revision = new_world
                if not publication:
                    self._backend.sessions._sessions[session_ref] = session
                for ref, prepared in prepared_obligations:
                    self._backend.obligations._store_row(ref, prepared)
                if prepared_obligations:
                    self.obligations.revision = obligation_parent + 1
                self.sessions.revision = new_session
                self._backend._r3_effect_journals[idempotency_key] = stored
                self.effects.revision = new_effect
            except BaseException:
                for fact_ref, (prior_fact, prior_revision) in world_before.items():
                    self._backend.world._remove_fact(fact_ref)
                    if prior_fact is not None:
                        self._backend.world._store_fact(prior_fact)
                    if prior_revision is missing:
                        self._backend.world._fact_revisions.pop(fact_ref, None)
                    else:
                        self._backend.world._fact_revisions[fact_ref] = prior_revision
                if transaction_before is missing:
                    self._backend.world._revision_transactions.pop(new_world, None)
                else:
                    self._backend.world._revision_transactions[new_world] = transaction_before
                if normalized_before is not None:
                    for ref, prior in normalized_before["applications"].items():
                        if prior is missing:
                            self._backend._normalized_applications.pop(ref, None)
                        else:
                            self._backend._normalized_applications[ref] = prior
                    for ref, prior in normalized_before["bindings"].items():
                        if prior is missing:
                            self._backend._normalized_bindings.pop(ref, None)
                        else:
                            self._backend._normalized_bindings[ref] = prior
                    if normalized_before["claim"] is missing:
                        self._backend._normalized_claims.pop(normalized_batch.claim_ref, None)
                    else:
                        self._backend._normalized_claims[normalized_batch.claim_ref] = normalized_before["claim"]
                    fact_ref = normalized_batch.claim_payload["fact_ref"]
                    if normalized_before["claim_by_fact"] is missing:
                        self._backend._normalized_claim_by_fact.pop(fact_ref, None)
                    else:
                        self._backend._normalized_claim_by_fact[fact_ref] = normalized_before["claim_by_fact"]
                    prior = normalized_before["claims_by_app"]
                    if prior is missing:
                        self._backend._normalized_claims_by_app.pop(normalized_batch.root_application_ref, None)
                    else:
                        self._backend._normalized_claims_by_app[normalized_batch.root_application_ref] = prior
                    for ref, prior in normalized_before["targets"].items():
                        if prior is missing:
                            self._backend._normalized_target_index.pop(ref, None)
                        else:
                            self._backend._normalized_target_index[ref] = prior
                for ref, (payload, metadata) in obligation_before.items():
                    if payload is missing:
                        self._backend.obligations._obligations.pop(ref, None)
                    else:
                        self._backend.obligations._obligations[ref] = payload
                    if metadata is missing:
                        self._backend.obligations._row_metadata.pop(ref, None)
                    else:
                        self._backend.obligations._row_metadata[ref] = metadata
                for session, prior in pending_before.items():
                    if prior is missing:
                        self._backend.obligations._pending_by_session.pop(session, None)
                    else:
                        self._backend.obligations._pending_by_session[session] = prior
                if not publication:
                    if session_before is missing:
                        self._backend.sessions._sessions.pop(session_ref, None)
                    else:
                        self._backend.sessions._sessions[session_ref] = session_before
                if journal_before is missing:
                    self._backend._r3_effect_journals.pop(idempotency_key, None)
                else:
                    self._backend._r3_effect_journals[idempotency_key] = journal_before
                self.world.revision = expected_revision_pin.world_revision
                self.sessions.revision = expected_revision_pin.session_revision
                self.effects.revision = expected_revision_pin.effect_revision
                self.obligations.revision = obligation_parent
                raise
        pin = self.revision_pin()
        return {"journal": stored, "revision_pin": pin.as_dict()}

    def _prepare_publication_commit(self, parent, entry, receipt_payload, facts):
        from .r3_learning import validate_publication_snapshot
        from .r3_codec import thaw_json
        from .r3_effects import EffectReceipt, R3EffectGateway
        from .dialogue import DialogueObligation
        source = validate_publication_snapshot(self, entry.request_payload, effect_increments=3)
        receipt = EffectReceipt.from_dict(dict(receipt_payload))
        observation, expected_fact, expected_receipt = R3EffectGateway._publication_commit_material(parent, self.revision_pin())
        if (thaw_json(entry.observation_payload) != observation or thaw_json(parent.observation_payload) != observation
                or facts != (expected_fact,) or receipt != expected_receipt or entry.outcome_ref != expected_receipt.receipt_ref):
            raise ValueError("publication fact/receipt lineage mismatch")
        completed = DialogueObligation.create(kind=source.kind, session_ref=source.session_ref,
            source_query_ref=source.source_query_ref, expected_answer_contract_ref=source.expected_answer_contract_ref,
            created_turn_index=source.created_turn_index, expires_turn_index=source.expires_turn_index,
            source_decision_ref=source.source_decision_ref, completion_receipt_ref=receipt.receipt_ref,
            revision_pin=source.revision_pin)
        return tuple((row.obligation_ref, _MemoryObligationStore._prepare_row(row.obligation_ref,
            row.session_ref, {**row.as_dict(), "resolved": True}, self.obligations.revision + 1, True))
            for row in (source, completed))

    def close(self) -> None:
        self._backend.close()


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def open_stores(
    path: str | Path,
    *,
    authority_generation: str,
    model_identity: str | None = None,
) -> SemanticStores:
    """Open (or create) a SQLite-backed :class:`SemanticStores` at ``path``."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    db_path = path / "semantic.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        backend = SQLiteSemanticStore(
            conn,
            authority_generation=authority_generation,
            model_identity=model_identity,
        )
    except BaseException:
        # No store owns the connection until activation succeeds.
        conn.close()
        raise
    return SemanticStores(backend)


def memory_stores(
    *,
    authority_generation: str = "authority:generation-test",
    model_identity: str | None = None,
) -> SemanticStores:
    """Create a test-only in-memory :class:`SemanticStores`."""
    backend = InMemorySemanticStore(
        authority_generation=authority_generation,
        model_identity=model_identity,
    )
    return SemanticStores(backend)
