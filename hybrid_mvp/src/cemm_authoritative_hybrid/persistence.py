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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_bytes, stable_ref, stable

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
]

_SCHEMA_VERSION = 1


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
        if expected_revision != self.revision:
            raise StaleRevisionError(f"focus: expected {expected_revision}, got {self.revision}")
        new_revision = self.revision + 1
        data = {**dict(payload), "focus_ref": focus_ref, "session_ref": session_ref}
        delta_hash = _payload_hash(data)
        transaction_ref = stable_ref("txn", {"store": "focus", "parent": expected_revision, "delta_hash": delta_hash})
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "INSERT INTO focus(focus_ref, session_ref, payload_json, payload_hash, revision) "
                "VALUES(?, ?, ?, ?, ?) "
                "ON CONFLICT(focus_ref) DO UPDATE SET payload_json=excluded.payload_json, "
                "payload_hash=excluded.payload_hash, revision=excluded.revision",
                (focus_ref, session_ref, json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False), delta_hash, new_revision),
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
CREATE TABLE IF NOT EXISTS obligations (
    obligation_ref TEXT PRIMARY KEY,
    session_ref TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    revision INTEGER NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0
);
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
"""


class SQLiteSemanticStore:
    """The SQLite reference persistent backend."""

    def __init__(self, conn: sqlite3.Connection, *, authority_generation: str, model_identity: str | None = None) -> None:
        self._conn = conn
        self._authority_generation = authority_generation
        self._model_identity = model_identity
        self._closed = False
        self._init_schema()
        self._activate()
        self.world = _SQLiteWorldStore(conn)
        self.sessions = _SQLiteSessionStore(conn)
        self.episodes = _SQLiteEpisodeStore(conn)
        self.effects = _SQLiteEffectStore(conn)
        self.models = _SQLiteModelStore(conn)
        self.focus = _SQLiteFocusStore(conn)
        self.obligations = _SQLiteObligationStore(conn)

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA_SQL)

    def _activate(self) -> None:
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
            return
        if int(row[0]) != _SCHEMA_VERSION:
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

        if all_corrupt:
            raise StoreActivationError(
                f"corruption detected in {len(all_corrupt)} rows",
                RecoveryReceipt(
                    last_verified_revision=last_verified,
                    corrupt_refs=tuple(all_corrupt),
                    recommended_action="restore from last verified backup; do not reset the database",
                ),
            )

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

    def commit(self, facts: Iterable[Fact], *, expected_revision: int) -> CommitReceipt:
        facts = tuple(facts)
        if expected_revision != self.revision:
            raise StaleRevisionError(f"world: expected {expected_revision}, got {self.revision}")
        delta_payload = [_fact_payload(f) for f in facts]
        delta_hash = _payload_hash(delta_payload)
        transaction_ref = stable_ref("txn", {"store": "world", "parent": expected_revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1
        for fact in facts:
            self._facts[fact.fact_ref] = fact
        self.revision = new_revision
        return CommitReceipt("world", expected_revision, new_revision, delta_hash, transaction_ref)

    def get(self, fact_ref: str) -> Fact | None:
        return self._facts.get(fact_ref)


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

    def commit(self, focus_ref: str, session_ref: str, payload: Mapping[str, Any], *, expected_revision: int) -> CommitReceipt:
        if expected_revision != self.revision:
            raise StaleRevisionError(f"focus: expected {expected_revision}, got {self.revision}")
        delta_hash = _payload_hash(payload)
        transaction_ref = stable_ref("txn", {"store": "focus", "parent": expected_revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1
        self._focus[focus_ref] = {**dict(payload), "focus_ref": focus_ref, "session_ref": session_ref}
        self.revision = new_revision
        return CommitReceipt("focus", expected_revision, new_revision, delta_hash, transaction_ref)

    def get(self, focus_ref: str) -> dict[str, Any] | None:
        return self._focus.get(focus_ref)


class _MemoryObligationStore:
    def __init__(self) -> None:
        self.revision = 0
        self._obligations: dict[str, dict[str, Any]] = {}

    def commit(self, obligation_ref: str, session_ref: str, payload: Mapping[str, Any], *, expected_revision: int, resolved: bool = False) -> CommitReceipt:
        if expected_revision != self.revision:
            raise StaleRevisionError(f"obligations: expected {expected_revision}, got {self.revision}")
        delta_hash = _payload_hash(payload)
        transaction_ref = stable_ref("txn", {"store": "obligations", "parent": expected_revision, "delta_hash": delta_hash})
        new_revision = self.revision + 1
        self._obligations[obligation_ref] = {**dict(payload), "obligation_ref": obligation_ref, "session_ref": session_ref, "resolved": resolved}
        self.revision = new_revision
        return CommitReceipt("obligations", expected_revision, new_revision, delta_hash, transaction_ref)

    def get(self, obligation_ref: str) -> dict[str, Any] | None:
        return self._obligations.get(obligation_ref)


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
                self._backend.world._facts[key]
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
            self._backend.world._facts[key]
            for key in sorted(self._backend.world._facts)
        )

    def r3_session_snapshot(self, session_ref: str) -> Mapping[str, Any]:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        session = self.sessions.get(session_ref)
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

    def r3_focus_snapshot(
        self, session_ref: str, *, maximum: int
    ) -> Mapping[str, Any]:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        if type(maximum) is not int or isinstance(maximum, bool) or maximum < 1:
            raise ValueError("maximum must be a positive exact int")
        refs: list[str] = []
        if isinstance(self._backend, SQLiteSemanticStore):
            rows = self._backend._conn.execute(
                "SELECT focus_ref, payload_json FROM focus WHERE session_ref=? "
                "ORDER BY revision DESC, focus_ref LIMIT ?",
                (session_ref, maximum + 1),
            ).fetchall()
            for row in rows:
                payload = json.loads(row[1])
                ref = payload.get("target_ref", payload.get("semantic_ref", row[0]))
                if type(ref) is str and ref and ref not in refs:
                    refs.append(ref)
        else:
            rows = sorted(
                (
                    (ref, payload)
                    for ref, payload in self._backend.focus._focus.items()
                    if payload.get("session_ref") == session_ref
                ),
                key=lambda row: row[0],
            )
            for ref, payload in rows[: maximum + 1]:
                value = payload.get("target_ref", payload.get("semantic_ref", ref))
                if type(value) is str and value and value not in refs:
                    refs.append(value)
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
            refs = sorted(
                ref
                for ref, payload in self._backend.obligations._obligations.items()
                if payload.get("session_ref") == session_ref
                and not payload.get("resolved", False)
            )[: maximum + 1]
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
    ) -> Mapping[str, Any]:
        from .r3_persistence import EffectJournalEntry, EffectJournalState

        existing = self.r3_effect_journal_get(idempotency_key)
        if existing is not None:
            entry = EffectJournalEntry.from_dict(existing["entry"])
            expected_request = json.loads(_r3_canonical_json(request_payload))
            if (
                entry.intent_ref != intent_ref
                or entry.decision_ref != decision_ref
                or dict(entry.request_payload) != expected_request
            ):
                raise ValueError("idempotency key is already bound to another request")
            return existing
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
        terminal = target.terminal
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
        else:
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
        session_ref, turn_index, phase = _r3_terminal_turn(entry)
        if isinstance(self._backend, SQLiteSemanticStore):
            conn = self._backend._conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                for key, expected in (
                    ("world_revision", expected_revision_pin.world_revision),
                    ("session_revision", expected_revision_pin.session_revision),
                    ("effect_revision", expected_revision_pin.effect_revision),
                ):
                    row = conn.execute(
                        "SELECT value FROM metadata WHERE key=?", (key,)
                    ).fetchone()
                    actual = int(row[0]) if row else 0
                    if actual != expected:
                        raise StaleRevisionError(
                            f"{key}: expected {expected}, got {actual}"
                        )
                for fact in facts:
                    row = _fact_to_row(fact)
                    payload = _fact_payload(fact)
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
                        {**row, "payload_hash": _payload_hash(payload), "revision": new_world},
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
                _r3_write_session_sqlite(
                    conn,
                    session_ref=session_ref,
                    turn_index=turn_index,
                    session_phase_ref=phase,
                    parent_revision=expected_revision_pin.session_revision,
                    new_revision=new_session,
                )
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
        else:
            for fact in facts:
                self._backend.world._facts[fact.fact_ref] = fact
            self.world.revision = new_world
            session, _payload = _r3_session_material(
                session_ref=session_ref,
                turn_index=turn_index,
                session_phase_ref=phase,
                revision=new_session,
            )
            self._backend.sessions._sessions[session_ref] = session
            self.sessions.revision = new_session
            self._backend._r3_effect_journals[idempotency_key] = stored
            self.effects.revision = new_effect
        pin = self.revision_pin()
        return {"journal": stored, "revision_pin": pin.as_dict()}

    def r3_commit_learning_outcome(
        self,
        *,
        session_ref: str,
        obligation_ref: str,
        obligation_payload: Mapping[str, Any],
        idempotency_key: str,
        intent_ref: str,
        decision_ref: str,
        receipt_payload: Mapping[str, Any],
        expected_revision_pin: RevisionPin,
    ) -> Mapping[str, Any]:
        from .r3_persistence import (
            EffectJournalEntry,
            EffectJournalState,
            StoredEffectJournal,
        )

        if expected_revision_pin != self.revision_pin():
            raise StaleRevisionError("learning outcome revision pin is stale")
        existing = self.r3_effect_journal_get(idempotency_key)
        if existing is None:
            raise ValueError("learning effect journal entry is absent")
        current_entry = EffectJournalEntry.from_dict(existing["entry"])
        if current_entry.state is not EffectJournalState.PLANNED:
            raise ValueError("learning journal is not planned")
        new_effect = expected_revision_pin.effect_revision + 1
        new_session = expected_revision_pin.session_revision + 1
        new_obligation = self.obligations.revision + 1
        outcome_ref = receipt_payload.get("receipt_ref")
        if type(outcome_ref) is not str or not outcome_ref:
            raise ValueError("learning receipt lacks receipt_ref")
        entry = EffectJournalEntry.create(
            idempotency_key=idempotency_key,
            state=EffectJournalState.NO_EFFECT,
            attempt_index=current_entry.attempt_index,
            intent_ref=intent_ref,
            decision_ref=decision_ref,
            request_payload=current_entry.request_payload,
            observation_payload=None,
            outcome_ref=outcome_ref,
            blocker_refs=(),
            parent_journal_ref=current_entry.journal_ref,
            effect_revision=new_effect,
        )
        stored = StoredEffectJournal(entry, receipt_payload).as_dict()
        _session_from_entry, turn_index, phase = _r3_terminal_turn(entry)
        obligation_data = {
            **dict(obligation_payload),
            "obligation_ref": obligation_ref,
            "session_ref": session_ref,
            "resolved": False,
        }
        if isinstance(self._backend, SQLiteSemanticStore):
            conn = self._backend._conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                _r3_write_session_sqlite(
                    conn,
                    session_ref=session_ref,
                    turn_index=turn_index,
                    session_phase_ref=phase,
                    parent_revision=expected_revision_pin.session_revision,
                    new_revision=new_session,
                )
                obligation_json = _r3_canonical_json(obligation_data)
                conn.execute(
                    "INSERT INTO obligations(obligation_ref, session_ref, payload_json, "
                    "payload_hash, revision, resolved) VALUES(?, ?, ?, ?, ?, 0) "
                    "ON CONFLICT(obligation_ref) DO UPDATE SET "
                    "payload_json=excluded.payload_json, payload_hash=excluded.payload_hash, "
                    "revision=excluded.revision, resolved=0",
                    (
                        obligation_ref,
                        session_ref,
                        obligation_json,
                        _payload_hash(obligation_data),
                        new_obligation,
                    ),
                )
                conn.execute(
                    "INSERT INTO metadata(key, value) VALUES('obligation_revision', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(new_obligation),),
                )
                _r3_insert_revision(
                    conn,
                    store="obligations",
                    parent_revision=self.obligations.revision,
                    new_revision=new_obligation,
                    delta_hash=_payload_hash(obligation_data),
                )
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
            self.sessions.revision = new_session
            self.obligations.revision = new_obligation
            self.effects.revision = new_effect
        else:
            session, _payload = _r3_session_material(
                session_ref=session_ref,
                turn_index=turn_index,
                session_phase_ref=phase,
                revision=new_session,
            )
            self._backend.sessions._sessions[session_ref] = session
            self.sessions.revision = new_session
            self._backend.obligations._obligations[obligation_ref] = obligation_data
            self.obligations.revision = new_obligation
            self._backend._r3_effect_journals[idempotency_key] = stored
            self.effects.revision = new_effect
        return {"journal": stored, "revision_pin": self.revision_pin().as_dict()}

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
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    backend = SQLiteSemanticStore(
        conn,
        authority_generation=authority_generation,
        model_identity=model_identity,
    )
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
