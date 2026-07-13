"""SchemaResolver — sense candidate clusters, scope-aware resolution.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7, §7.2):
- Schema identity/version resolution authority is SemanticSchemaStore / resolver.
- Lexical form, sense, schema revision, access scope, and epistemic context are distinct.
- One lexical form may map to multiple senses. One schema may have multiple lexicalizations.
- Opaque uses of one spelling may remain separate candidate sense clusters until evidence supports merge.
- Narrower access scope does not blindly replace wider meaning.
- Resolution considers: sense, context/world, applicability domain and valid time,
  scope/access, structural usability, epistemic admissibility, requested semantic operation.
- Schema merge or identity equivalence is explicit, reversible, journaled.
- A structurally executable revision is not automatically actual-world knowledge.
- EpistemicEvaluator decides admissibility; GroundingResolver derives use profile.
  Neither may activate a revision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .envelope import SchemaEnvelope
from .store import SemanticSchemaStore
from ..model.identity import Scope, ScopeLevel, TimeExtent


@dataclass(frozen=True, slots=True)
class SenseCandidate:
    """A candidate sense for a lexical form or semantic key.

    A candidate is not yet a resolved schema — it is a pointer
    to a possible sense that may need grounding assessment.
    """
    semantic_key: str
    record_id: str
    schema_kind: str
    status: str  # candidate, provisional, active
    scope: Scope
    version: int
    confidence: float = 0.0
    applicability_context_refs: tuple[str, ...] = ()
    valid_time: TimeExtent | None = None


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    """Result of resolving a lexical form or semantic key.

    The resolver produces candidates — it does not activate or
    decide epistemic admissibility. Those are separate authorities.
    """
    query: str
    candidates: tuple[SenseCandidate, ...] = ()
    active_candidate: SenseCandidate | None = None
    opaque_candidates: tuple[SenseCandidate, ...] = ()
    detail: str = ""


class SchemaResolver:
    """Resolves lexical forms and semantic keys to candidate schema revisions.

    The resolver is NOT the activation authority — it produces candidates.
    The resolver is NOT the epistemic authority — it does not decide admissibility.
    The resolver does NOT derive use profiles — that is GroundingResolver's job.

    The resolver's job is:
    1. Map lexical forms to candidate sense clusters
    2. Filter by context/time applicability
    3. Filter by scope/access (without blind shadowing)
    4. Rank candidates by structural usability and confidence
    5. Return the best candidates for downstream assessment
    """

    def __init__(self, store: SemanticSchemaStore) -> None:
        self._store = store

    def resolve_lexical(
        self,
        surface: str,
        language_tag: str = "und",
        context_ref: str | None = None,
        scope: Scope | None = None,
        valid_at: datetime | None = None,
    ) -> ResolutionResult:
        """Resolve a lexical surface form to candidate senses.

        One lexical form may map to multiple senses. Opaque uses
        of one spelling may remain separate candidate sense clusters
        until evidence supports merge.
        """
        semantic_keys = self._store.lookup_lexical_form(surface, language_tag)
        if not semantic_keys:
            return ResolutionResult(
                query=f"{surface}/{language_tag}",
                detail="No semantic keys indexed for this lexical form",
            )

        all_candidates: list[SenseCandidate] = []
        for key in semantic_keys:
            result = self.resolve_key(
                key, context_ref=context_ref, scope=scope, valid_at=valid_at
            )
            all_candidates.extend(result.candidates)

        # Separate active from opaque
        active = [c for c in all_candidates if c.status == "active"]
        opaque = [c for c in all_candidates if c.status in ("candidate", "provisional")]

        # Best active candidate: highest version, then highest confidence
        best_active = None
        if active:
            best_active = max(active, key=lambda c: (c.version, c.confidence))

        return ResolutionResult(
            query=f"{surface}/{language_tag}",
            candidates=tuple(all_candidates),
            active_candidate=best_active,
            opaque_candidates=tuple(opaque),
        )

    def resolve_key(
        self,
        semantic_key: str,
        context_ref: str | None = None,
        scope: Scope | None = None,
        valid_at: datetime | None = None,
    ) -> ResolutionResult:
        """Resolve a semantic key to candidate schema revisions.

        Narrower access scope does not blindly replace wider meaning.
        A user-scoped revision may represent a user theory or private
        convention without overriding an active global schema.
        """
        envelopes = self._store.find_candidates(
            semantic_key,
            context_ref=context_ref,
            scope=scope,
            valid_at=valid_at,
        )

        if not envelopes:
            return ResolutionResult(
                query=semantic_key,
                detail="No candidates found for semantic key",
            )

        candidates: list[SenseCandidate] = []
        for env in envelopes:
            # Scope filtering: include both narrower and wider
            # The caller (GroundingResolver) decides precedence
            if scope is not None:
                # If a narrower-scope revision exists, include it
                # but don't exclude wider-scope ones
                pass

            candidates.append(SenseCandidate(
                semantic_key=env.semantic_key,
                record_id=env.record_id,
                schema_kind=env.schema_kind,
                status=env.status,
                scope=env.scope,
                version=env.version,
                confidence=env.confidence,
                applicability_context_refs=env.applicability_context_refs,
                valid_time=env.valid_time,
            ))

        # Separate active from opaque
        active = [c for c in candidates if c.status == "active"]
        opaque = [c for c in candidates if c.status in ("candidate", "provisional")]

        # Best active candidate
        best_active = None
        if active:
            # Prefer matching scope, then highest version, then confidence
            if scope is not None:
                scope_matches = [c for c in active if c.scope.level == scope.level]
                if scope_matches:
                    best_active = max(
                        scope_matches,
                        key=lambda c: (c.version, c.confidence),
                    )
            if best_active is None:
                best_active = max(active, key=lambda c: (c.version, c.confidence))

        return ResolutionResult(
            query=semantic_key,
            candidates=tuple(candidates),
            active_candidate=best_active,
            opaque_candidates=tuple(opaque),
        )

    def resolve_strict(
        self,
        semantic_key: str,
        context_ref: str | None = None,
        scope: Scope | None = None,
        valid_at: datetime | None = None,
    ) -> SchemaEnvelope | None:
        """Resolve to the single active schema for a key, if any.

        This is a convenience method for cases where only an active
        schema is acceptable (e.g. operational execution). For
        candidate/provisional exploration, use resolve_key instead.
        """
        return self._store.find_active(
            semantic_key,
            context_ref=context_ref,
            valid_at=valid_at,
        )

    def get_sense_clusters(self) -> dict[str, set[str]]:
        """Get all sense clusters in the store.

        Useful for diagnostics and for detecting polysemy.
        """
        # Return a copy to prevent external mutation
        return {
            key: set(ids)
            for key, ids in self._store._sense_clusters.items()
        }

    def get_opaque_clusters(
        self, surface: str, language_tag: str = "und"
    ) -> tuple[tuple[str, ...], ...]:
        """Get distinct opaque sense clusters for a lexical form.

        Opaque uses of one spelling may remain separate candidate
        sense clusters until evidence supports merge.
        """
        semantic_keys = self._store.lookup_lexical_form(surface, language_tag)
        clusters: list[tuple[str, ...]] = []
        for key in semantic_keys:
            envelopes = self._store.find_candidates(key)
            if any(e.status in ("candidate", "provisional") for e in envelopes):
                clusters.append((key,))
        return tuple(clusters)
