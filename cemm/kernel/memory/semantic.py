"""Canonical semantic fact memory with exact roles and provenance."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib, json
from threading import RLock
from typing import Any

@dataclass(frozen=True, slots=True)
class FactRole:
    role_key: str
    value_ref: str
    value_kind: str = "referent"
    semantic_key: str = ""
    surface: str = ""

@dataclass(frozen=True, slots=True)
class SemanticFact:
    fact_id: str
    predicate_key: str
    roles: tuple[FactRole, ...]
    context_ref: str = "actual"
    polarity: str = "positive"
    modality: str = "actual"
    confidence: float = 0.5
    evidence_refs: tuple[str, ...] = ()
    source_ref: str = ""
    valid_from: str = ""
    valid_until: str = ""
    status: str = "active"
    derivation_rule_ref: str = ""
    derivation_depth: int = 0
    causal_warrant: str = "none"
    sensitivity: str = "ordinary"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def role(self, role_key: str) -> FactRole | None:
        return next(
            (role for role in self.roles if role.role_key == role_key),
            None,
        )

    @property
    def semantic_identity(self) -> str:
        role_part = "|".join(
            f"{role.role_key}={role.value_ref}"
            for role in sorted(self.roles, key=lambda item: item.role_key)
        )
        raw = (
            f"{self.predicate_key}|{role_part}|{self.context_ref}|"
            f"{self.polarity}|{self.modality}|{self.valid_from}|"
            f"{self.valid_until}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@dataclass(frozen=True, slots=True)
class FactQuery:
    predicate_key: str = ""
    role_constraints: dict[str, str] = field(default_factory=dict)
    context_refs: tuple[str, ...] = ()
    polarity: str = ""
    active_only: bool = True

class MutationPayloadRegistry:
    def __init__(self):
        self._payloads = {}
        self._lock = RLock()

    def put(self, payload_ref: str, payload: Any):
        with self._lock:
            self._payloads[payload_ref] = payload
        return payload_ref

    def get(self, payload_ref: str):
        with self._lock:
            return self._payloads.get(payload_ref)

class SemanticMemoryStore:
    def __init__(self):
        self._facts = {}
        self._identity_index = {}
        self._predicate_index = {}
        self._revision = 0
        self._lock = RLock()
        self._snapshot = None

    @property
    def revision(self):
        return self._revision

    @property
    def store_revision(self):
        return self._revision

    def add(self, fact: SemanticFact):
        with self._lock:
            existing_ref = self._identity_index.get(
                fact.semantic_identity
            )
            if existing_ref:
                existing = self._facts[existing_ref]
                self._facts[existing_ref] = replace(
                    existing,
                    status="active",
                    confidence=max(
                        existing.confidence, fact.confidence
                    ),
                    evidence_refs=tuple(dict.fromkeys(
                        (*existing.evidence_refs, *fact.evidence_refs)
                    )),
                    source_ref=fact.source_ref or existing.source_ref,
                    created_at=fact.created_at,
                )
                self._revision += 1
                return existing_ref, False
            self._facts[fact.fact_id] = fact
            self._identity_index[fact.semantic_identity] = fact.fact_id
            self._predicate_index.setdefault(
                fact.predicate_key, set()
            ).add(fact.fact_id)
            self._revision += 1
            return fact.fact_id, True

    def get(self, fact_id):
        return self._facts.get(fact_id)

    def query(self, query: FactQuery):
        with self._lock:
            refs = (
                set(self._predicate_index.get(
                    query.predicate_key, set()
                ))
                if query.predicate_key else set(self._facts)
            )
            result = []
            for ref in refs:
                fact = self._facts[ref]
                if query.active_only and fact.status != "active":
                    continue
                if (
                    query.context_refs
                    and fact.context_ref not in query.context_refs
                ):
                    continue
                if query.polarity and fact.polarity != query.polarity:
                    continue
                roles = {
                    role.role_key: role.value_ref
                    for role in fact.roles
                }
                if any(
                    roles.get(key) != value
                    for key, value in query.role_constraints.items()
                ):
                    continue
                result.append(fact)
            return tuple(
                sorted(result, key=lambda item: item.created_at)
            )

    def all_facts(
        self, *, active_only: bool = True
    ) -> tuple[SemanticFact, ...]:
        values = tuple(self._facts.values())
        if not active_only:
            return values
        return tuple(fact for fact in values if fact.status == "active")

    def supersede(self, fact_id):
        with self._lock:
            fact = self._facts.get(fact_id)
            if fact is None:
                return False
            self._facts[fact_id] = replace(
                fact, status="superseded"
            )
            self._revision += 1
            return True

    @contextmanager
    def transaction(self):
        with self._lock:
            if self._snapshot is not None:
                yield self
                return
            self._snapshot = (
                dict(self._facts),
                dict(self._identity_index),
                {
                    key: set(value)
                    for key, value in self._predicate_index.items()
                },
                self._revision,
            )
            try:
                yield self
                self._snapshot = None
            except Exception:
                (
                    self._facts,
                    self._identity_index,
                    self._predicate_index,
                    self._revision,
                ) = self._snapshot
                self._snapshot = None
                raise

    def dump_json(self, path):
        rows = []
        for fact in self._facts.values():
            row = {
                "fact_id": fact.fact_id,
                "predicate_key": fact.predicate_key,
                "roles": [
                    {
                        "role_key": role.role_key,
                        "value_ref": role.value_ref,
                        "value_kind": role.value_kind,
                        "semantic_key": role.semantic_key,
                        "surface": role.surface,
                    }
                    for role in fact.roles
                ],
                "context_ref": fact.context_ref,
                "polarity": fact.polarity,
                "modality": fact.modality,
                "confidence": fact.confidence,
                "evidence_refs": fact.evidence_refs,
                "source_ref": fact.source_ref,
                "status": fact.status,
            }
            rows.append(row)
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
