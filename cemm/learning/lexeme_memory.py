from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import uuid


@dataclass(frozen=True, slots=True)
class LexemeLookupResult:
    """A candidate lexeme lookup result — not an authoritative meaning."""
    lexeme: LexemeModel
    match_type: str = "exact"
    score: float = 0.0


class LexemeRole(str, Enum):
    ENTITY = "entity"
    PROCESS = "process"
    STATE = "state"
    MODIFIER = "modifier"
    RELATION = "relation"
    COMMAND_ALIAS = "command_alias"


class LexemeScope(str, Enum):
    USER = "user"
    SESSION = "session"
    GLOBAL = "global"


class LexemeStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    REJECTED = "rejected"


@dataclass
class LexemeModel:
    id: str
    surface: str
    canonical: str
    role: str
    maps_to: str
    examples: list[str] = field(default_factory=list)
    source_id: str = ""
    scope: str = LexemeScope.USER.value
    confidence: float = 0.5
    trust: float = 0.5
    status: str = LexemeStatus.CANDIDATE.value
    created_at: float = 0.0
    updated_at: float = 0.0
    evidence_signal_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "surface": self.surface,
            "canonical": self.canonical,
            "role": self.role,
            "maps_to": self.maps_to,
            "examples": list(self.examples),
            "source_id": self.source_id,
            "scope": self.scope,
            "confidence": self.confidence,
            "trust": self.trust,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "evidence_signal_ids": list(self.evidence_signal_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LexemeModel":
        return cls(
            id=data.get("id", ""),
            surface=data.get("surface", ""),
            canonical=data.get("canonical", ""),
            role=data.get("role", LexemeRole.PROCESS.value),
            maps_to=data.get("maps_to", ""),
            examples=list(data.get("examples", [])),
            source_id=data.get("source_id", ""),
            scope=data.get("scope", LexemeScope.USER.value),
            confidence=float(data.get("confidence", 0.5)),
            trust=float(data.get("trust", 0.5)),
            status=data.get("status", LexemeStatus.CANDIDATE.value),
            created_at=float(data.get("created_at", 0.0)),
            updated_at=float(data.get("updated_at", 0.0)),
            evidence_signal_ids=list(data.get("evidence_signal_ids", [])),
        )


class LexemeMemory:
    """In-memory store for learned surface-to-meaning mappings.

    These are user-taught words, slang, secret commands, aliases, and temporary
    context mappings. They are intentionally lightweight and scoped to avoid
    polluting the long-term claim store with unconfirmed casual language.
    """

    def __init__(self) -> None:
        self._lexemes: dict[str, list[LexemeModel]] = {}
        self._surface_index: dict[str, list[LexemeModel]] = {}

    def record(
        self,
        surface: str,
        canonical: str,
        role: str,
        maps_to: str,
        source_id: str = "",
        scope: str = LexemeScope.USER.value,
        confidence: float = 0.5,
        trust: float = 0.5,
        status: str = LexemeStatus.CANDIDATE.value,
        evidence_signal_id: str = "",
    ) -> LexemeModel:
        now = time.time()
        lex = LexemeModel(
            id=uuid.uuid4().hex[:16],
            surface=surface,
            canonical=canonical,
            role=role,
            maps_to=maps_to,
            source_id=source_id,
            scope=scope,
            confidence=confidence,
            trust=trust,
            status=status,
            created_at=now,
            updated_at=now,
            evidence_signal_ids=[evidence_signal_id] if evidence_signal_id else [],
        )
        self._lexemes.setdefault(lex.id, [])
        self._lexemes[lex.id].append(lex)
        self._surface_index.setdefault(surface.lower(), [])
        self._surface_index[surface.lower()].append(lex)
        return lex

    def learn(
        self,
        surface: str,
        role: str,
        maps_to: str = "",
        confidence: float = 0.5,
        scope: str = LexemeScope.USER.value,
    ) -> LexemeModel:
        return self.record(
            surface=surface,
            canonical=surface.lower(),
            role=role,
            maps_to=maps_to,
            scope=scope,
            confidence=confidence,
            trust=confidence,
            status=LexemeStatus.ACTIVE.value,
        )

    def lookup(self, surface: str) -> LexemeModel | None:
        lexes = self._surface_index.get(surface.lower(), [])
        return lexes[-1] if lexes else None

    def lookup_active(self, surface: str) -> LexemeModel | None:
        for lex in self._surface_index.get(surface.lower(), []):
            if lex.status == LexemeStatus.ACTIVE.value:
                return lex
        return None

    def lookup_by_role(self, role: str, status: str | None = None) -> list[LexemeModel]:
        result = []
        for lexes in self._surface_index.values():
            for lex in lexes:
                if lex.role == role and (status is None or lex.status == status):
                    result.append(lex)
        return result

    def activate(self, surface: str) -> LexemeModel | None:
        for lex in self._surface_index.get(surface.lower(), []):
            if lex.status == LexemeStatus.CANDIDATE.value:
                lex.status = LexemeStatus.ACTIVE.value
                lex.updated_at = time.time()
                return lex
        return None

    def reject(self, surface: str) -> LexemeModel | None:
        for lex in self._surface_index.get(surface.lower(), []):
            if lex.status != LexemeStatus.REJECTED.value:
                lex.status = LexemeStatus.REJECTED.value
                lex.updated_at = time.time()
                return lex
        return None

    def suspend(self, surface: str) -> LexemeModel | None:
        for lex in self._surface_index.get(surface.lower(), []):
            if lex.status == LexemeStatus.ACTIVE.value:
                lex.status = LexemeStatus.CANDIDATE.value
                lex.updated_at = time.time()
                return lex
        return None

    def update_trust(self, surface: str, delta: float) -> LexemeModel | None:
        lex = self.lookup_active(surface)
        if lex is None:
            return None
        lex.trust = max(0.0, min(1.0, lex.trust + delta))
        lex.updated_at = time.time()
        return lex

    def lookup_candidates(self, surface: str) -> list[LexemeModel]:
        """Return candidate lexeme models for a surface form.
        
        These are candidates, not authoritative meanings.
        Returns empty list if no candidates found.
        """
        norm = surface.strip().lower()
        results = []
        for lexeme in self._lexemes.values():
            if any(l.surface.lower() == norm for l in lexeme):
                results.extend(l for l in lexeme if l.surface.lower() == norm)
        results.extend(self._surface_index.get(norm, []))
        return results

    def all(self) -> list[LexemeModel]:
        seen: set[str] = set()
        result: list[LexemeModel] = []
        for lexes in self._surface_index.values():
            for lex in lexes:
                if lex.id not in seen:
                    seen.add(lex.id)
                    result.append(lex)
        return result
