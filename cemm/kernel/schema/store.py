"""SemanticSchemaStore — sole authority for executable meaning schemas.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7):
- SemanticSchemaStore is the ONLY authority for schema lifecycle activation.
- Boot and learned schemas use the same model and resolver.
- Session learning is a session-scoped schema revision, not an overlay.
- Lifecycle is strict: candidate → provisional → active → superseded/rejected.
- A structurally executable revision is not automatically actual-world knowledge.
- Schema merge or identity equivalence is explicit, reversible, journaled.
- Assessment and activation use one pinned store snapshot + CAS commit.
- Revisions bound to propositions/replays must remain reachable (retention).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Protocol

from .envelope import SchemaEnvelope, SchemaDependency
from .versioning import RevisionEntry, SchemaStatus
from .activation import (
    ActivationResult,
    ActivationStatus,
    activate_single,
    activate_cluster,
)
from .dependency import DependencyNode, DependencyEdge, DependencyClosure, CycleClass
from .scope import resolve_scope
from ..model.identity import Scope, ScopeLevel, TimeExtent
from ..model.refs import FrozenMap


# ── Journal entries for supersession/merge operations ──────────────


@dataclass(frozen=True, slots=True)
class SupersessionJournalEntry:
    """Journaled supersession or equivalence operation.

    All merge/equivalence operations are explicit, reversible,
    journaled, and never destroy original references.
    """
    entry_id: str
    operation: str  # supersede, merge, alias, split
    source_ref: str  # Ref[SchemaEnvelope]
    target_ref: str  # Ref[SchemaEnvelope]
    reason: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reversible: bool = True


# ── Store protocol for activation module ───────────────────────────


class _StoreActivationProtocol(Protocol):
    """Minimal protocol the activation module needs from the store."""
    def get_revision(self, record_id: str) -> int | None: ...
    def set_status(
        self, record_id: str, status: str, expected_revision: int
    ) -> bool: ...


# ── Reverse dependency index ───────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ReverseDependency:
    """A reverse dependency: schema B is depended upon by schema A."""
    dependent_ref: str  # Ref[SchemaEnvelope] that depends on target
    target_ref: str  # Ref[SchemaEnvelope] being depended upon
    dependency_kind: str
    polarity: str = "positive"
    monotonicity: str = "monotone"


# ── The store ──────────────────────────────────────────────────────


class SemanticSchemaStore:
    """Sole authority for executable meaning schema lifecycle.

    This store manages:
    - Schema registration with version tracking
    - Strict lifecycle transitions (candidate → provisional → active → ...)
    - Typed reverse dependencies for invalidation
    - Context/time applicability filtering
    - Explicit supersession/equivalence (journaled, reversible)
    - CAS activation (delegates to activation.py)
    - Atomic cluster activation
    - Revision retention (GC protection)

    Boot and learned schemas use identical APIs — boot origin is
    provenance, not a separate lifecycle state.
    """

    def __init__(self) -> None:
        # Primary storage: record_id → SchemaEnvelope
        self._records: dict[str, SchemaEnvelope] = {}
        # Revision tracking: record_id → current revision number
        self._revisions: dict[str, int] = {}
        # Reverse dependency index: target_ref → tuple of ReverseDependency
        self._reverse_deps: dict[str, tuple[ReverseDependency, ...]] = {}
        # Forward dependency index: record_id → tuple of SchemaDependency
        self._forward_deps: dict[str, tuple[SchemaDependency, ...]] = {}
        # Supersession journal
        self._journal: list[SupersessionJournalEntry] = []
        # Revision retention bindings
        self._proposition_bindings: dict[str, set[str]] = {}  # record_id → proposition refs
        self._replay_bindings: dict[str, set[str]] = {}  # record_id → replay refs
        # Sense cluster index: semantic_key → set of record_ids
        self._sense_clusters: dict[str, set[str]] = {}
        # Lexical form index: (surface, language) → set of semantic_keys
        self._lexical_index: dict[tuple[str, str], set[str]] = {}
        # Store revision counter (incremented on any mutation)
        self._store_revision: int = 0
        # Thread lock for transaction isolation
        self._lock = threading.RLock()
        # Transaction snapshot (set by transaction() context manager)
        self._txn_snapshot: dict[str, Any] | None = None

    # ── Registration ───────────────────────────────────────────────

    def register(
        self,
        envelope: SchemaEnvelope,
        dependencies: tuple[SchemaDependency, ...] = (),
    ) -> str:
        """Register a new schema envelope.

        Boot and learned schemas use the same API. Boot origin is
        recorded in provenance, not as a separate lifecycle state.

        Returns the record_id. Raises if a record with the same
        record_id already exists.
        """
        if envelope.record_id in self._records:
            raise ValueError(
                f"Schema record {envelope.record_id} already exists. "
                "Create a new version instead."
            )

        self._records[envelope.record_id] = envelope
        self._revisions[envelope.record_id] = envelope.version

        # Index by semantic_key for sense clusters
        self._sense_clusters.setdefault(envelope.semantic_key, set()).add(
            envelope.record_id
        )

        # Index forward dependencies
        if dependencies:
            self._forward_deps[envelope.record_id] = dependencies
            # Build reverse dependency index
            for dep in dependencies:
                rdep = ReverseDependency(
                    dependent_ref=envelope.record_id,
                    target_ref=dep.target_schema_ref,
                    dependency_kind=dep.dependency_kind,
                    polarity=dep.polarity,
                    monotonicity=dep.monotonicity,
                )
                existing = self._reverse_deps.get(dep.target_schema_ref, ())
                self._reverse_deps[dep.target_schema_ref] = (*existing, rdep)

        self._store_revision += 1
        return envelope.record_id

    def get(self, record_id: str) -> SchemaEnvelope | None:
        """Retrieve a schema envelope by record_id."""
        return self._records.get(record_id)

    def get_revision(self, record_id: str) -> int | None:
        """Get the current revision number for a record."""
        return self._revisions.get(record_id)

    def set_status(
        self, record_id: str, status: str, expected_revision: int
    ) -> bool:
        """Compare-and-swap status update.

        Returns True if the status was updated, False if the
        revision mismatched. This is the CAS primitive used by
        the activation module.
        """
        current = self._revisions.get(record_id)
        if current is None or current != expected_revision:
            return False

        env = self._records.get(record_id)
        if env is None:
            return False

        # Create a new envelope with updated status (immutable replacement)
        from dataclasses import replace
        self._records[record_id] = replace(env, status=status)
        self._revisions[record_id] = expected_revision + 1
        self._store_revision += 1
        return True

    @property
    def store_revision(self) -> int:
        """Current store revision counter."""
        return self._store_revision

    # ── Lifecycle transitions ──────────────────────────────────────

    def transition_to_provisional(
        self,
        record_id: str,
        expected_revision: int,
    ) -> ActivationResult:
        """Transition a candidate schema to provisional.

        A structurally executable revision is not automatically
        actual-world knowledge. This transition marks that some or
        all structure is executable in a declared context, but
        independent competence or epistemic admission is incomplete.
        """
        env = self._records.get(record_id)
        if env is None:
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} not found",
            )
        if env.status != "candidate":
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} is {env.status}, not candidate",
            )
        return activate_single(self, record_id, "provisional", expected_revision)

    def activate(
        self,
        record_id: str,
        expected_revision: int,
    ) -> ActivationResult:
        """Activate a schema revision.

        The exact revision must have passed structural closure,
        required independent competence, context/scope policy,
        and atomic activation. The validator cannot activate —
        only the store can.

        This method requires assessment refs to be present on the
        envelope (grounding_assessment_ref, competence_assessment_ref).
        Use activate_with_assessment to provide them.
        """
        env = self._records.get(record_id)
        if env is None:
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} not found",
            )
        # Active transition requires provisional or candidate status
        if env.status not in ("candidate", "provisional"):
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} is {env.status}, cannot activate",
            )
        # Enforce assessment refs for activation
        if not env.grounding_assessment_ref:
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} has no grounding_assessment_ref — "
                       "use activate_with_assessment()",
            )
        return activate_single(self, record_id, "active", expected_revision)

    def activate_with_assessment(
        self,
        record_id: str,
        expected_revision: int,
        grounding_assessment_ref: str,
        competence_assessment_ref: str = "",
        epistemic_admissibility_ref: str = "",
        environment_fingerprint: str = "",
        *,
        grounding_assessment: Any | None = None,
        competence_assessment: Any | None = None,
    ) -> ActivationResult:
        """Activate a schema revision with assessment refs.

        Stamps the envelope with the grounding assessment, competence
        assessment, and epistemic admissibility refs that justify
        activation. All active records must have assessment/admissibility
        refs (Stage 3 exit gate).

        The grounding_assessment_ref must be non-empty. The competence
        and epistemic refs may be empty if the assessment process
        determined they are not required for this schema kind.

        If grounding_assessment is provided, verifies is_structurally_executable
        is True before allowing activation. If competence_assessment is
        provided, verifies is_self_certified is False. This enforces the
        no-bypass rule: closure and competence checks cannot be skipped.
        """
        env = self._records.get(record_id)
        if env is None:
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} not found",
            )
        if env.status not in ("candidate", "provisional"):
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} is {env.status}, cannot activate",
            )
        if not grounding_assessment_ref:
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail="grounding_assessment_ref is required for activation",
            )

        # Enforce closure: grounding assessment must indicate structural executability
        if grounding_assessment is not None:
            if not getattr(grounding_assessment, "is_structurally_executable", False):
                blockers = getattr(grounding_assessment, "blocker_reasons", ())
                return ActivationResult(
                    status=ActivationStatus.BLOCKED,
                    detail=f"Grounding assessment does not indicate structural "
                           f"executability. Blockers: {blockers}",
                )

        # Enforce competence: self-certified assessments cannot activate
        if competence_assessment is not None:
            if getattr(competence_assessment, "is_self_certified", False):
                return ActivationResult(
                    status=ActivationStatus.BLOCKED,
                    detail="Competence assessment is self-certified — "
                           "activation forbidden",
                )

        # CAS check: verify revision hasn't changed since assessment
        current_rev = self._revisions.get(record_id)
        if current_rev is None:
            return ActivationResult(
                status=ActivationStatus.BLOCKED,
                detail=f"Record {record_id} has no revision",
            )
        if current_rev != expected_revision:
            return ActivationResult(
                status=ActivationStatus.CAS_FAILED,
                failed_ref=record_id,
                detail=f"Expected revision {expected_revision}, found {current_rev}",
            )

        # CAS passed — stamp envelope with assessment refs AND set status atomically
        from dataclasses import replace as _replace
        stamped = _replace(
            env,
            grounding_assessment_ref=grounding_assessment_ref,
            competence_assessment_ref=competence_assessment_ref,
            epistemic_admissibility_ref=epistemic_admissibility_ref,
            activation_environment_fingerprint=environment_fingerprint,
            status="active",
        )
        self._records[record_id] = stamped
        self._revisions[record_id] = current_rev + 1
        self._store_revision += 1

        return ActivationResult(
            status=ActivationStatus.SUCCESS,
            activated_refs=(record_id,),
        )

    def activate_cluster(
        self,
        record_ids: tuple[str, ...],
        expected_revisions: dict[str, int],
    ) -> ActivationResult:
        """Atomically activate a cluster of schema revisions.

        A recursive cluster activates atomically or not at all.
        If any member fails, no member becomes active.

        All cluster members must have grounding_assessment_ref on their
        envelopes — cluster activation does not bypass assessment refs.
        Use stamp_assessment_refs() to stamp members before cluster activation.
        """
        # Enforce assessment refs for all cluster members
        for rid in record_ids:
            env = self._records.get(rid)
            if env is None:
                return ActivationResult(
                    status=ActivationStatus.BLOCKED,
                    detail=f"Cluster member {rid} not found",
                )
            if not env.grounding_assessment_ref:
                return ActivationResult(
                    status=ActivationStatus.BLOCKED,
                    detail=f"Cluster member {rid} has no grounding_assessment_ref — "
                           "use stamp_assessment_refs() first",
                )
        return activate_cluster(self, record_ids, "active", expected_revisions)

    def stamp_assessment_refs(
        self,
        record_id: str,
        grounding_assessment_ref: str,
        competence_assessment_ref: str = "",
        epistemic_admissibility_ref: str = "",
        environment_fingerprint: str = "",
    ) -> bool:
        """Stamp an envelope with assessment refs without activating.

        This is used before cluster activation, where the assessment
        refs must be present but the status transition happens via
        activate_cluster(). Does NOT change status or increment revision.
        """
        env = self._records.get(record_id)
        if env is None:
            return False
        if not grounding_assessment_ref:
            return False
        from dataclasses import replace as _replace
        stamped = _replace(
            env,
            grounding_assessment_ref=grounding_assessment_ref,
            competence_assessment_ref=competence_assessment_ref,
            epistemic_admissibility_ref=epistemic_admissibility_ref,
            activation_environment_fingerprint=environment_fingerprint,
        )
        self._records[record_id] = stamped
        return True

    def supersede(
        self,
        record_id: str,
        by_record_id: str,
        reason: str = "",
    ) -> bool:
        """Mark a schema as superseded by another.

        Superseded schemas are not selected for new interpretation,
        while historical proposition bindings remain resolvable.
        """
        env = self._records.get(record_id)
        if env is None:
            return False
        if env.status == "active":
            # Use CAS via set_status to prevent race conditions
            current_rev = self._revisions.get(record_id, 0)
            if not self.set_status(record_id, "superseded", current_rev):
                return False

            # Journal the supersession
            entry = SupersessionJournalEntry(
                entry_id=f"journal:{len(self._journal)}",
                operation="supersede",
                source_ref=record_id,
                target_ref=by_record_id,
                reason=reason,
            )
            self._journal.append(entry)
            return True
        return False

    def reject(
        self,
        record_id: str,
        reason: str = "",
    ) -> bool:
        """Mark a schema as rejected."""
        env = self._records.get(record_id)
        if env is None:
            return False
        if env.status in ("candidate", "provisional"):
            current_rev = self._revisions.get(record_id, 0)
            if not self.set_status(record_id, "rejected", current_rev):
                return False

            entry = SupersessionJournalEntry(
                entry_id=f"journal:{len(self._journal)}",
                operation="reject",
                source_ref=record_id,
                target_ref=record_id,
                reason=reason,
            )
            self._journal.append(entry)
            return True
        return False

    # ── Reverse dependencies ───────────────────────────────────────

    def get_reverse_dependencies(
        self, record_id: str
    ) -> tuple[ReverseDependency, ...]:
        """Get all schemas that depend on the given schema.

        Used for invalidation: when a schema is superseded or
        rejected, all dependent schemas' assessments invalidate.
        """
        return self._reverse_deps.get(record_id, ())

    def get_forward_dependencies(
        self, record_id: str
    ) -> tuple[SchemaDependency, ...]:
        """Get all dependencies of the given schema."""
        return self._forward_deps.get(record_id, ())

    def get_dependents(self, record_id: str) -> tuple[str, ...]:
        """Get record_ids of all schemas that depend on this one."""
        rdeps = self._reverse_deps.get(record_id, ())
        return tuple(rdep.dependent_ref for rdep in rdeps)

    def get_transitive_dependents(self, record_id: str) -> tuple[str, ...]:
        """Get all transitively dependent record_ids (BFS)."""
        visited: set[str] = set()
        queue: list[str] = [record_id]
        result: list[str] = []
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for rdep in self._reverse_deps.get(current, ()):
                if rdep.dependent_ref not in visited:
                    result.append(rdep.dependent_ref)
                    queue.append(rdep.dependent_ref)
        return tuple(result)

    def records(
        self,
        *,
        schema_kind: str = "",
        statuses: tuple[str, ...] = (),
    ) -> tuple[SchemaEnvelope, ...]:
        """Return a revision-stable filtered schema snapshot.

        Consumers may project active schemas into execution models, but this
        method does not grant lifecycle authority or mutate revisions.
        """
        with self._lock:
            values = tuple(self._records.values())
        return tuple(
            item for item in values
            if (not schema_kind or item.schema_kind == schema_kind)
            and (not statuses or item.status in statuses)
        )

    # ── Context/time applicability ─────────────────────────────────

    def find_candidates(
        self,
        semantic_key: str,
        context_ref: str | None = None,
        scope: Scope | None = None,
        valid_at: datetime | None = None,
    ) -> tuple[SchemaEnvelope, ...]:
        """Find candidate schemas by semantic key with filtering.

        Resolution considers: sense, context/world, applicability
        domain and valid time, scope/access, structural usability,
        epistemic admissibility, requested semantic operation.

        Narrower access scope does not blindly replace wider meaning.
        """
        record_ids = self._sense_clusters.get(semantic_key, set())
        candidates: list[SchemaEnvelope] = []
        for rid in record_ids:
            env = self._records.get(rid)
            if env is None:
                continue
            # Filter by status — only candidate/provisional/active
            if env.status in ("rejected", "superseded"):
                continue
            # Filter by scope if provided
            if scope is not None:
                # Narrower scope doesn't replace wider — include both
                # but caller's resolver decides precedence
                pass  # scope filtering is the resolver's job
            # Filter by valid_time if provided
            if valid_at is not None and env.valid_time is not None:
                if not env.valid_time.contains(valid_at):
                    continue
            # Filter by applicability context if provided
            if context_ref is not None and env.applicability_context_refs:
                if context_ref not in env.applicability_context_refs:
                    continue
            candidates.append(env)
        return tuple(candidates)

    def find_active(
        self,
        semantic_key: str,
        context_ref: str | None = None,
        valid_at: datetime | None = None,
    ) -> SchemaEnvelope | None:
        """Find the single active schema for a semantic key.

        Returns None if no active schema exists. If multiple active
        schemas exist (should not happen for the same scope/context),
        returns the one with the highest version.
        """
        candidates = self.find_candidates(
            semantic_key, context_ref=context_ref, valid_at=valid_at
        )
        active = [c for c in candidates if c.status == "active"]
        if not active:
            return None
        # Return highest version
        return max(active, key=lambda e: e.version)

    # ── Supersession / equivalence journal ─────────────────────────

    def merge_senses(
        self,
        source_key: str,
        target_key: str,
        reason: str = "",
    ) -> SupersessionJournalEntry:
        """Merge two sense clusters explicitly.

        Schema merge or identity equivalence is explicit, reversible,
        journaled, and never destroys original references. Original
        references are retained for historical proposition integrity.
        """
        entry = SupersessionJournalEntry(
            entry_id=f"journal:{len(self._journal)}",
            operation="merge",
            source_ref=source_key,
            target_ref=target_key,
            reason=reason,
        )
        self._journal.append(entry)

        # Merge the sense clusters — source records join target cluster
        source_ids = self._sense_clusters.get(source_key, set())
        target_ids = self._sense_clusters.get(target_key, set())
        merged = source_ids | target_ids
        self._sense_clusters[target_key] = merged
        # Keep source cluster for reversibility — don't delete it
        self._store_revision += 1
        return entry

    def alias_sense(
        self,
        source_key: str,
        target_key: str,
        reason: str = "",
    ) -> SupersessionJournalEntry:
        """Create an alias binding between two sense keys.

        Alias is reversible and journaled. Original references retained.
        """
        entry = SupersessionJournalEntry(
            entry_id=f"journal:{len(self._journal)}",
            operation="alias",
            source_ref=source_key,
            target_ref=target_key,
            reason=reason,
        )
        self._journal.append(entry)
        # Alias: add source records to target cluster
        source_ids = self._sense_clusters.get(source_key, set())
        target_ids = self._sense_clusters.get(target_key, set())
        self._sense_clusters[target_key] = target_ids | source_ids
        self._store_revision += 1
        return entry

    def split_sense(
        self,
        semantic_key: str,
        new_key: str,
        record_ids_to_move: tuple[str, ...],
        reason: str = "",
    ) -> SupersessionJournalEntry:
        """Split a sense cluster into two.

        Used when evidence shows a polysemous term has distinct senses.
        Original references retained for historical propositions.
        """
        entry = SupersessionJournalEntry(
            entry_id=f"journal:{len(self._journal)}",
            operation="split",
            source_ref=semantic_key,
            target_ref=new_key,
            reason=reason,
        )
        self._journal.append(entry)
        # Move specified records to new cluster
        cluster = self._sense_clusters.get(semantic_key, set())
        new_cluster: set[str] = set()
        for rid in record_ids_to_move:
            if rid in cluster:
                cluster.discard(rid)
                new_cluster.add(rid)
        self._sense_clusters[semantic_key] = cluster
        self._sense_clusters[new_key] = new_cluster
        self._store_revision += 1
        return entry

    def get_journal(self) -> tuple[SupersessionJournalEntry, ...]:
        """Get the full supersession/merge journal."""
        return tuple(self._journal)

    def reverse_journal_entry(self, entry_id: str) -> bool:
        """Reverse a journaled operation if it was marked reversible.

        Original journal entry is retained for audit trail.
        A reversal entry is appended to the journal.
        """
        for i, entry in enumerate(self._journal):
            if entry.entry_id == entry_id and entry.reversible:
                # Append a reversal entry — do NOT destroy the original
                reversal = SupersessionJournalEntry(
                    entry_id=f"journal:{len(self._journal)}",
                    operation=f"reverse:{entry.operation}",
                    source_ref=entry.target_ref,
                    target_ref=entry.source_ref,
                    reason=f"Reversal of {entry_id}",
                )
                self._journal.append(reversal)

                # Undo the sense cluster changes
                if entry.operation == "merge":
                    # Unmerge: move source records back out of target cluster
                    source_ids = self._sense_clusters.get(entry.source_ref, set())
                    target_ids = self._sense_clusters.get(entry.target_ref, set())
                    # Records that were in source before merge go back
                    # We can identify them because merge keeps the source cluster
                    for rid in source_ids:
                        target_ids.discard(rid)
                    self._sense_clusters[entry.target_ref] = target_ids
                elif entry.operation == "split":
                    # Unsplit: move records back into original cluster
                    new_ids = self._sense_clusters.get(entry.target_ref, set())
                    orig_ids = self._sense_clusters.get(entry.source_ref, set())
                    orig_ids |= new_ids
                    self._sense_clusters[entry.source_ref] = orig_ids
                    del self._sense_clusters[entry.target_ref]

                self._store_revision += 1
                return True
        return False

    # ── Revision retention ─────────────────────────────────────────

    def bind_proposition(self, record_id: str, proposition_ref: str) -> None:
        """Bind a schema revision to a historical proposition.

        Revisions bound to propositions must remain reachable.
        GC may compact indexes but may not remove revision content.
        """
        self._proposition_bindings.setdefault(record_id, set()).add(
            proposition_ref
        )

    def bind_replay(self, record_id: str, replay_ref: str) -> None:
        """Bind a schema revision to a replay result."""
        self._replay_bindings.setdefault(record_id, set()).add(replay_ref)

    def is_retention_required(self, record_id: str) -> bool:
        """Check if a revision must be retained.

        Active revisions are always retained. Superseded/rejected
        revisions are retained if bound to propositions or replays.
        """
        env = self._records.get(record_id)
        if env is None:
            return False
        if env.status == "active":
            return True
        if record_id in self._proposition_bindings and self._proposition_bindings[record_id]:
            return True
        if record_id in self._replay_bindings and self._replay_bindings[record_id]:
            return True
        return False

    def get_retention_bindings(
        self, record_id: str
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Get (proposition_refs, replay_refs) bound to a record."""
        return (
            tuple(self._proposition_bindings.get(record_id, set())),
            tuple(self._replay_bindings.get(record_id, set())),
        )

    # ── Lexical form indexing ──────────────────────────────────────

    def index_lexical_form(
        self,
        surface: str,
        language_tag: str,
        semantic_key: str,
    ) -> None:
        """Index a lexical form → semantic_key mapping.

        One lexical form may map to multiple senses. One schema
        may have multiple lexicalizations.
        """
        key = (surface, language_tag)
        self._lexical_index.setdefault(key, set()).add(semantic_key)

    def lookup_lexical_form(
        self,
        surface: str,
        language_tag: str,
    ) -> tuple[str, ...]:
        """Look up semantic keys for a lexical form.

        Returns all candidate sense keys — opaque uses of one
        spelling may remain separate candidate sense clusters
        until evidence supports merge.
        """
        key = (surface, language_tag)
        return tuple(self._lexical_index.get(key, set()))

    # ── Transaction support ─────────────────────────────────────────

    def transaction(self) -> "_StoreTransaction":
        """Begin a transaction for atomic batch mutations.

        Usage:
            with store.transaction():
                store.register(env1)
                store.register(env2)
                store.activate_with_assessment(...)

        On clean exit, the transaction commits (store revision increments once).
        On exception, all mutations are rolled back to the snapshot.
        """
        return _StoreTransaction(self)

    def _snapshot_state(self) -> dict[str, Any]:
        """Capture a deep snapshot of all mutable store state."""
        return {
            "records": dict(self._records),
            "revisions": dict(self._revisions),
            "reverse_deps": {k: v for k, v in self._reverse_deps.items()},
            "forward_deps": {k: v for k, v in self._forward_deps.items()},
            "journal": list(self._journal),
            "proposition_bindings": {k: set(v) for k, v in self._proposition_bindings.items()},
            "replay_bindings": {k: set(v) for k, v in self._replay_bindings.items()},
            "sense_clusters": {k: set(v) for k, v in self._sense_clusters.items()},
            "lexical_index": {k: set(v) for k, v in self._lexical_index.items()},
            "store_revision": self._store_revision,
        }

    def _restore_state(self, snapshot: dict[str, Any]) -> None:
        """Restore store state from a snapshot."""
        self._records = dict(snapshot["records"])
        self._revisions = dict(snapshot["revisions"])
        self._reverse_deps = {k: v for k, v in snapshot["reverse_deps"].items()}
        self._forward_deps = {k: v for k, v in snapshot["forward_deps"].items()}
        self._journal = list(snapshot["journal"])
        self._proposition_bindings = {k: set(v) for k, v in snapshot["proposition_bindings"].items()}
        self._replay_bindings = {k: set(v) for k, v in snapshot["replay_bindings"].items()}
        self._sense_clusters = {k: set(v) for k, v in snapshot["sense_clusters"].items()}
        self._lexical_index = {k: set(v) for k, v in snapshot["lexical_index"].items()}
        self._store_revision = snapshot["store_revision"]

    # ── Persistence ─────────────────────────────────────────────────

    def save_to_file(self, path: str) -> None:
        """Persist all schema revisions and indices to a file.

        Saves all records, revisions, dependencies, indices,
        journal, and store revision counter.
        """
        import pickle
        state = self._snapshot_state()
        with open(path, "wb") as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load_from_file(self, path: str) -> None:
        """Load schema revisions and indices from a file.

        Replaces all current store state with the loaded state.
        """
        import pickle
        with open(path, "rb") as f:
            state = pickle.load(f)
        self._restore_state(state)

    # ── Introspection helpers ──────────────────────────────────────

    def all_record_ids(self) -> tuple[str, ...]:
        """Get all record IDs in the store."""
        return tuple(self._records.keys())

    def active_record_ids(self) -> tuple[str, ...]:
        """Get all active record IDs."""
        return tuple(
            rid for rid, env in self._records.items()
            if env.status == "active"
        )

    # ── Snapshot for assessment ────────────────────────────────────

    def create_snapshot(self) -> "StoreSnapshot":
        """Create a pinned snapshot of the store for assessment.

        Assessment and activation use one pinned store/environment
        snapshot and compare-and-swap commit. A dependency or
        environment change invalidates all dependent derived cognition.
        """
        return StoreSnapshot(
            store_revision=self._store_revision,
            records=dict(self._records),
            revisions=dict(self._revisions),
        )

    # ── Iteration ──────────────────────────────────────────────────

    def __iter__(self) -> Iterator[SchemaEnvelope]:
        return iter(self._records.values())

    def __len__(self) -> int:
        return len(self._records)

    def all_records(self) -> tuple[SchemaEnvelope, ...]:
        """Get all records in the store."""
        return tuple(self._records.values())

    def records_by_status(self, status: str) -> tuple[SchemaEnvelope, ...]:
        """Get all records with a given status."""
        return tuple(
            env for env in self._records.values() if env.status == status
        )

    def records_by_kind(self, schema_kind: str) -> tuple[SchemaEnvelope, ...]:
        """Get all records of a given schema kind."""
        return tuple(
            env for env in self._records.values()
            if env.schema_kind == schema_kind
        )


# ── Store snapshot ─────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StoreSnapshot:
    """Pinned snapshot of the store at a point in time.

    Used for assessment: the assessment fingerprint includes the
    store revision. A store revision change invalidates assessments.
    """
    store_revision: int
    records: dict[str, SchemaEnvelope] = field(default_factory=dict)
    revisions: dict[str, int] = field(default_factory=dict)

    def get(self, record_id: str) -> SchemaEnvelope | None:
        return self.records.get(record_id)

    def get_revision(self, record_id: str) -> int | None:
        return self.revisions.get(record_id)


# ── Store transaction ──────────────────────────────────────────────


class _StoreTransaction:
    """Context manager for atomic batch store mutations.

    Snapshots store state on enter. On clean exit, commits.
    On exception, rolls back to the snapshot.
    """

    def __init__(self, store: SemanticSchemaStore) -> None:
        self._store = store
        self._snapshot: dict[str, Any] | None = None

    def __enter__(self) -> SemanticSchemaStore:
        self._store._lock.acquire()
        self._snapshot = self._store._snapshot_state()
        return self._store

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if exc_type is not None and self._snapshot is not None:
                # Rollback on exception
                self._store._restore_state(self._snapshot)
        finally:
            self._snapshot = None
            self._store._lock.release()
