"""SemanticModelStore — learned surface-to-meaning bindings with lifecycle.

Wraps LexemeMemory as the hot cache for word-level lookups, adding:
- Binding lifecycle: observed → candidate → reinforced → active → corrected → superseded
- Atom pattern matching (structural signatures, not just surface strings)
- Confidence with diminishing returns reinforcement
- Correction tracking with supersession

The store is the bridge between observed language and structural act inference.
It enables the system to learn that "do the glass thing" maps to a command
action, without hardcoding that alias.

Resolution cascade (in ConversationActClassifier and UOLMapper):
    1. SemanticModelStore.lookup_surface() → active/reinforced bindings
    2. Atom-graph structural inference
    3. Seed aliases from uol_semantics.json
    4. Current semantic matcher (last resort)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..learning.lexeme_memory import LexemeMemory
from ..types.graph_patch import GraphPatch, PatchOperation


class BindingStatus(str, Enum):
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    REINFORCED = "reinforced"
    ACTIVE = "active"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"


# Statuses that should be used in resolution (highest priority first)
_USABLE_STATUSES = {BindingStatus.ACTIVE.value, BindingStatus.REINFORCED.value}


@dataclass
class SurfaceBinding:
    """A learned mapping from a surface expression to a structural meaning."""

    id: str
    surface: str
    language: str
    normalized_surface: str
    maps_to_act_type: str = ""
    maps_to_frame_key: str = ""
    maps_to_atom_pattern: dict[str, Any] = field(default_factory=dict)
    source: str = "seed"  # seed, observed, corrected
    scope: str = "session"  # session, user, global
    status: str = BindingStatus.CANDIDATE.value
    confidence: float = 0.3
    trust: float = 0.5
    evidence_signal_ids: list[str] = field(default_factory=list)
    correction_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "surface": self.surface,
            "language": self.language,
            "normalized_surface": self.normalized_surface,
            "maps_to_act_type": self.maps_to_act_type,
            "maps_to_frame_key": self.maps_to_frame_key,
            "maps_to_atom_pattern": dict(self.maps_to_atom_pattern),
            "source": self.source,
            "scope": self.scope,
            "status": self.status,
            "confidence": self.confidence,
            "trust": self.trust,
            "evidence_signal_ids": list(self.evidence_signal_ids),
            "correction_count": self.correction_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SurfaceBinding:
        return cls(
            id=data.get("id", ""),
            surface=data.get("surface", ""),
            language=data.get("language", "en"),
            normalized_surface=data.get("normalized_surface", ""),
            maps_to_act_type=data.get("maps_to_act_type", ""),
            maps_to_frame_key=data.get("maps_to_frame_key", ""),
            maps_to_atom_pattern=dict(data.get("maps_to_atom_pattern", {})),
            source=data.get("source", "seed"),
            scope=data.get("scope", "session"),
            status=data.get("status", BindingStatus.CANDIDATE.value),
            confidence=float(data.get("confidence", 0.3)),
            trust=float(data.get("trust", 0.5)),
            evidence_signal_ids=list(data.get("evidence_signal_ids", [])),
            correction_count=int(data.get("correction_count", 0)),
            created_at=float(data.get("created_at", 0.0)),
            updated_at=float(data.get("updated_at", 0.0)),
        )


def _normalize_surface(surface: str) -> str:
    """Normalize a surface string for indexing: lowercase, strip extra whitespace."""
    return " ".join(surface.lower().split())


class SemanticModelStore:
    """Wraps LexemeMemory and adds binding lifecycle management.

    LexemeMemory is the hot cache for word-level surface→canonical mappings.
    SemanticModelStore adds higher-order surface→act_type/frame_key bindings
    with confidence tracking, correction, and promotion lifecycle.
    """

    def __init__(self, lexeme_memory: LexemeMemory | None = None) -> None:
        self._lexeme_memory = lexeme_memory or LexemeMemory()
        self._bindings: dict[str, SurfaceBinding] = {}
        self._surface_index: dict[str, list[str]] = {}  # normalized_surface → [binding_id]
        self._pattern_index: dict[str, list[str]] = {}  # pattern_hash → [binding_id]
        self._deltas: list[dict[str, Any]] = []  # v3.3 Phase 10: per-turn binding deltas
        self._promotion_patches: list = []  # v4.2: pending GraphPatches for PatchPipeline

    @property
    def lexeme_memory(self) -> LexemeMemory:
        return self._lexeme_memory

    def lookup_surface(
        self,
        surface: str,
        language: str = "en",
    ) -> list[SurfaceBinding]:
        """Look up bindings by surface string.

        Returns only active/reinforced bindings, sorted by confidence (highest first).
        """
        norm = _normalize_surface(surface)
        binding_ids = self._surface_index.get(norm, [])
        results = []
        for bid in binding_ids:
            binding = self._bindings.get(bid)
            if binding is None:
                continue
            if binding.language != language:
                continue
            if binding.status in _USABLE_STATUSES:
                results.append(binding)
        results.sort(key=lambda b: b.confidence, reverse=True)
        return results

    def lookup_pattern(
        self,
        atom_pattern: dict[str, Any],
        language: str = "en",
    ) -> list[SurfaceBinding]:
        """Look up bindings by atom pattern.

        Matches bindings whose maps_to_atom_pattern is a subset of the query pattern.
        Returns only active/reinforced bindings, sorted by confidence.
        """
        results = []
        for binding in self._bindings.values():
            if binding.language != language:
                continue
            if binding.status not in _USABLE_STATUSES:
                continue
            if not binding.maps_to_atom_pattern:
                continue
            if _pattern_matches(binding.maps_to_atom_pattern, atom_pattern):
                results.append(binding)
        results.sort(key=lambda b: b.confidence, reverse=True)
        return results

    def observe_candidate(
        self,
        binding: SurfaceBinding,
        signal_id: str = "",
    ) -> SurfaceBinding:
        """Record a new candidate binding or reinforce an existing one.

        If a binding for the same surface + mapping already exists, reinforce it.
        Otherwise, create a new candidate binding.
        """
        norm = binding.normalized_surface or _normalize_surface(binding.surface)
        binding.normalized_surface = norm

        # Check for existing binding with same surface + mapping
        existing = self._find_existing(norm, binding.maps_to_act_type, binding.maps_to_frame_key)
        if existing:
            return self.reinforce(existing.id, signal_id)

        # Create new binding
        now = time.time()
        binding.id = binding.id or uuid.uuid4().hex[:16]
        binding.created_at = now
        binding.updated_at = now
        binding.status = BindingStatus.OBSERVED.value
        binding.confidence = 0.3
        if signal_id:
            binding.evidence_signal_ids.append(signal_id)

        self._bindings[binding.id] = binding
        self._surface_index.setdefault(norm, []).append(binding.id)
        if binding.maps_to_atom_pattern:
            pk = _pattern_hash(binding.maps_to_atom_pattern)
            self._pattern_index.setdefault(pk, []).append(binding.id)

        self._deltas.append({
            "action": "observed", "binding_id": binding.id,
            "surface": binding.surface, "maps_to": binding.maps_to_frame_key,
            "signal_id": signal_id,
        })
        return binding

    def reinforce(self, binding_id: str, signal_id: str = "") -> SurfaceBinding:
        """Reinforce an existing binding, increasing its confidence.

        Uses diminishing returns: confidence += 0.15 * (1 - confidence)
        """
        binding = self._bindings.get(binding_id)
        if binding is None:
            raise KeyError(f"Binding {binding_id} not found")

        # Diminishing returns reinforcement
        binding.confidence = min(1.0, binding.confidence + 0.15 * (1.0 - binding.confidence))
        binding.updated_at = time.time()

        if signal_id and signal_id not in binding.evidence_signal_ids:
            binding.evidence_signal_ids.append(signal_id)

        # Status transitions
        if binding.status == BindingStatus.OBSERVED.value:
            binding.status = BindingStatus.CANDIDATE.value
        elif binding.status == BindingStatus.CANDIDATE.value:
            if binding.confidence >= 0.5:
                binding.status = BindingStatus.REINFORCED.value

        self._deltas.append({
            "action": "reinforced", "binding_id": binding.id,
            "surface": binding.surface, "confidence": binding.confidence,
            "status": binding.status, "signal_id": signal_id,
        })
        return binding

    def correct(
        self,
        binding_id: str,
        corrected_mapping: dict[str, Any],
        signal_id: str = "",
    ) -> SurfaceBinding:
        """Correct a binding's mapping, decreasing confidence.

        If correction_count >= 2, the binding is superseded.
        A new candidate binding is created with the corrected mapping.
        """
        binding = self._bindings.get(binding_id)
        if binding is None:
            raise KeyError(f"Binding {binding_id} not found")

        # Penalize the existing binding
        binding.confidence = max(0.0, binding.confidence - 0.3)
        binding.correction_count += 1
        binding.updated_at = time.time()

        if binding.correction_count >= 2:
            binding.status = BindingStatus.SUPERSEDED.value
        else:
            binding.status = BindingStatus.CORRECTED.value

        # Create a new candidate binding with the corrected mapping
        now = time.time()
        new_binding = SurfaceBinding(
            id=uuid.uuid4().hex[:16],
            surface=binding.surface,
            language=binding.language,
            normalized_surface=binding.normalized_surface,
            maps_to_act_type=corrected_mapping.get("act_type", ""),
            maps_to_frame_key=corrected_mapping.get("frame_key", ""),
            maps_to_atom_pattern=corrected_mapping.get("atom_pattern", {}),
            source="corrected",
            scope=binding.scope,
            status=BindingStatus.CANDIDATE.value,
            confidence=0.4,
            trust=0.6,
            evidence_signal_ids=[signal_id] if signal_id else [],
            created_at=now,
            updated_at=now,
        )
        self._bindings[new_binding.id] = new_binding
        self._surface_index.setdefault(new_binding.normalized_surface, []).append(new_binding.id)
        if new_binding.maps_to_atom_pattern:
            pk = _pattern_hash(new_binding.maps_to_atom_pattern)
            self._pattern_index.setdefault(pk, []).append(new_binding.id)

        self._deltas.append({
            "action": "corrected", "binding_id": binding.id,
            "new_binding_id": new_binding.id,
            "surface": binding.surface, "old_mapping": binding.maps_to_frame_key,
            "new_mapping": new_binding.maps_to_frame_key,
            "correction_count": binding.correction_count, "signal_id": signal_id,
        })
        return new_binding

    def promote_ready(self, threshold: float = 0.75) -> list[SurfaceBinding]:
        """Promote candidate/reinforced bindings to active when ready.

        A binding is promoted when:
        - confidence >= threshold
        - evidence_signal_ids >= 2
        - status is candidate or reinforced
        """
        promoted: list[SurfaceBinding] = []
        for binding in self._bindings.values():
            if binding.status not in (BindingStatus.CANDIDATE.value, BindingStatus.REINFORCED.value):
                continue
            if binding.confidence >= threshold and len(binding.evidence_signal_ids) >= 2:
                binding.status = BindingStatus.ACTIVE.value
                binding.updated_at = time.time()
                promoted.append(binding)
                self._deltas.append({
                    "action": "promoted", "binding_id": binding.id,
                    "surface": binding.surface, "maps_to": binding.maps_to_frame_key,
                    "confidence": binding.confidence,
                })
                self._promotion_patches.append(GraphPatch(
                    target="concept_lattice",
                    operations=[PatchOperation(
                        operation="custom",
                        target_id=f"binding:{binding.id}",
                        fields={
                            "action": "promote_binding",
                            "surface": binding.surface,
                            "maps_to": binding.maps_to_frame_key or "",
                            "confidence": binding.confidence,
                            "status": BindingStatus.ACTIVE.value,
                        },
                        confidence=binding.confidence,
                        reason=f"binding_promotion:{binding.id}",
                    )],
                    confidence=binding.confidence,
                    reason=f"binding_promotion:{binding.surface}->{binding.maps_to_frame_key}",
                ))
        return promoted

    def get_promotion_patches(self) -> list:
        """Return pending promotion patches for the PatchPipeline."""
        patches = list(self._promotion_patches)
        self._promotion_patches.clear()
        return patches

    def all_bindings(self) -> list[SurfaceBinding]:
        return list(self._bindings.values())

    def get_deltas(self) -> list[dict[str, Any]]:
        """Return per-turn binding deltas for training export."""
        return list(self._deltas)

    def clear_deltas(self) -> None:
        """Clear per-turn binding deltas after export."""
        self._deltas.clear()

    def lookup_word(self, surface: str) -> Any:
        """Delegate word-level lookup to LexemeMemory."""
        return self._lexeme_memory.lookup(surface)

    def lookup_active_word(self, surface: str) -> Any:
        """Delegate active word-level lookup to LexemeMemory."""
        return self._lexeme_memory.lookup_active(surface)

    def _find_existing(
        self,
        normalized_surface: str,
        act_type: str,
        frame_key: str,
    ) -> SurfaceBinding | None:
        """Find an existing binding with the same surface and mapping."""
        for bid in self._surface_index.get(normalized_surface, []):
            binding = self._bindings.get(bid)
            if binding is None:
                continue
            if binding.maps_to_act_type == act_type and binding.maps_to_frame_key == frame_key:
                return binding
        return None


def _pattern_hash(pattern: dict[str, Any]) -> str:
    """Create a stable hash key for an atom pattern dict."""
    items = sorted(pattern.items())
    return "|".join(f"{k}={v}" for k, v in items)


def _pattern_matches(binding_pattern: dict[str, Any], query_pattern: dict[str, Any]) -> bool:
    """Check if binding_pattern is a subset of query_pattern.

    A binding matches when all its pattern keys are present in the query
    with matching values. This allows partial pattern matching.
    """
    for key, value in binding_pattern.items():
        if key not in query_pattern:
            return False
        if query_pattern[key] != value:
            return False
    return True
