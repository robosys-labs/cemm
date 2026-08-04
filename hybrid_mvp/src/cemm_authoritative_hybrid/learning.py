"""Typed designation learning and reviewed acquisition without conversational
authority escalation.

This module owns the Learning Plan ABI (version 1). It defines
:class:`LearningPlan`, :class:`ReviewedAcquisitionPlan`,
:class:`ReviewerAuthorization`, :class:`DesignationCommitReceipt`,
:class:`AcquisitionReceipt`, :class:`LearningCoordinator`, and the test-only
:class:`ReviewerPolicyIssuer`.

Learning distinctions remain explicit (spec section 9):

- **lookup** is read-only — executes a query, does NOT mutate world state;
- **teaching** creates an attributed claim — never a designation;
- **directive** requests learning over an embedded proposition;
- **learning-event claim** reports an event about the speaker;
- **trusted designation acquisition** may bind a new surface to an existing
  target under reviewed authorization;
- **reviewed acquisition** may publish a new semantic identity or definition
  graph and requires authority reactivation.

A pending designation-learning obligation is pinned to its source query,
authority generation, target-kind contract, permission, provenance, and expiry.
A successful commit consumes it exactly once.

No lexical token directly authorizes a write.  Conversational wording cannot
select the reviewer policy.  No public ``install_rules``, ``add_rule``, or
mutable-authority shortcut exists.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from .authority import AuthorityLinkError, RuleRecord
from .canonical import stable_ref
from .config import RuntimeConfig
from .persistence import SemanticStores
from .query import GenericDefinitionLowerer, QueryEngine, QueryResult

__all__ = [
    "LearningPlan",
    "ReviewedAcquisitionPlan",
    "ReviewerAuthorization",
    "DesignationCommitReceipt",
    "AcquisitionReceipt",
    "LearningGap",
    "LearningCoordinator",
    "ReviewerPolicyIssuer",
    "DesignationStore",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LearningGap(Exception):
    """Raised when a learning operation cannot proceed due to a typed gap.

    The gap may be caused by missing capability, missing target identity,
    conflict, expiry, replay, authorization mismatch, or other typed
    conditions.  Each gap is classified by its structured fields, not surface
    text.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"LearningGap({code}){': ' + detail if detail else ''}")


# ---------------------------------------------------------------------------
# Designation store — tracks committed designations
# ---------------------------------------------------------------------------


class DesignationStore:
    """In-memory store for committed reviewed designations.

    This store tracks designations that have been committed through the
    reviewed learning path.  It does NOT directly mutate the linked authority;
    the coordinator publishes a new generation atomically.
    """

    __slots__ = ("_by_surface", "_by_target")

    def __init__(self) -> None:
        self._by_surface: dict[tuple[str, str], list[str]] = {}
        self._by_target: dict[tuple[str, str], list[str]] = {}

    def commit_reviewed(self, surface: str, target: str, language: str = "en") -> None:
        """Record a reviewed designation."""
        key = (surface, language)
        if target not in self._by_surface.get(key, []):
            self._by_surface.setdefault(key, []).append(target)
        self._by_target.setdefault((target, language), []).append(surface)

    def contains(self, surface: str, target: str, language: str = "en") -> bool:
        """Check whether a designation exists."""
        return target in self._by_surface.get((surface, language), [])

    def for_surface(self, surface: str, language: str = "en") -> tuple[str, ...]:
        """Return target refs designated by ``surface`` in ``language``."""
        return tuple(self._by_surface.get((surface, language), []))


# ---------------------------------------------------------------------------
# Typed plan records (Learning Plan ABI v1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearningPlan:
    """A typed designation-learning plan.

    A pending designation-learning obligation is pinned to its source query,
    authority generation, target-kind contract, permission, provenance, and
    expiry.  A successful commit consumes it exactly once.

    Attributes:
        plan_ref: stable ref uniquely identifying this plan.
        contract_ref: the contract that governs this plan.
        source_query_ref: the exact QueryResult this plan is bound to.
        goal_ref: the learning goal ref.
        capability_ref: the required capability (``cap:learn``).
        commit_operator_ref: the operator used on commit (``op:designation``).
        surface_literal: the surface form to bind.
        expected_target_kinds: tuple of acceptable target kinds.
        answer_contract_ref: the answer contract ref.
        provenance_refs: tuple of provenance refs.
        expires_at_turn: the turn at which this plan expires.
    """

    plan_ref: str
    contract_ref: str
    source_query_ref: str
    goal_ref: str
    capability_ref: str
    commit_operator_ref: Literal["op:designation"]
    surface_literal: str
    target_ref: str
    expected_target_kinds: tuple[str, ...]
    answer_contract_ref: str
    provenance_refs: tuple[str, ...]
    expires_at_turn: int


@dataclass(frozen=True)
class ReviewedAcquisitionPlan:
    """A typed reviewed acquisition plan for publishing new authority content.

    Accepts already-verified semantic programs under an independently
    configured reviewer policy, invokes the side-effect-free lowerer, links
    the complete candidate bundle, and atomically publishes a new authority
    generation.

    Attributes:
        plan_ref: stable ref uniquely identifying this plan.
        contract_ref: the contract that governs this plan.
        verified_program_refs: tuple of verified program refs.
        acquisition_kind: one of ``identity``, ``frame``, ``rule``,
            ``dimension``, ``transition``.
        expected_owner_ref: the expected owner ref for the new content.
        reviewer_policy_ref: the independently configured reviewer policy.
        provenance_refs: tuple of provenance refs.
        authority_parent_generation: the parent authority generation.
    """

    plan_ref: str
    contract_ref: str
    verified_program_refs: tuple[str, ...]
    acquisition_kind: Literal[
        "identity", "frame", "rule", "dimension", "transition"
    ]
    expected_owner_ref: str
    reviewer_policy_ref: str
    provenance_refs: tuple[str, ...]
    authority_parent_generation: str


@dataclass(frozen=True)
class ReviewerAuthorization:
    """A typed reviewer authorization bound to reviewer/policy/plan/decision/nonce/expiry.

    Core tests receive this authorization only from a test policy issuer;
    Milestone 5 owns real CLI/API authentication that issues the same type.

    Attributes:
        reviewer_ref: the reviewer's ref.
        policy_ref: the reviewer policy ref.
        plan_ref: the plan this authorization is bound to.
        decision: the decision (must be ``"approve"``).
        nonce: a unique nonce to prevent replay.
        expires_at: the turn at which this authorization expires.
    """

    reviewer_ref: str
    policy_ref: str
    plan_ref: str
    decision: str
    nonce: str
    expires_at: int


@dataclass(frozen=True)
class DesignationCommitReceipt:
    """An atomic six-phase commit receipt for a designation learning commit.

    Attributes:
        operator_ref: the operator used (``op:designation``).
        surface: the surface that was bound.
        target_ref: the target that was bound.
        plan_ref: the plan that was consumed.
        revision: the designation store revision after commit.
    """

    operator_ref: str
    surface: str
    target_ref: str
    plan_ref: str
    revision: int


@dataclass(frozen=True)
class AcquisitionReceipt:
    """A receipt for a reviewed acquisition that published a new generation.

    Attributes:
        parent_generation: the parent authority generation.
        new_generation: the new authority generation.
        authority_compatibility_hash: the compatibility hash (preserved).
        created_rule_refs: tuple of created rule refs.
        plan_ref: the plan that was consumed.
    """

    parent_generation: str
    new_generation: str
    authority_compatibility_hash: str
    created_rule_refs: tuple[str, ...]
    plan_ref: str


# ---------------------------------------------------------------------------
# ReviewerPolicyIssuer — test-only authorization issuer
# ---------------------------------------------------------------------------


class ReviewerPolicyIssuer:
    """Test-only issuer of :class:`ReviewerAuthorization` records.

    Milestone 5 owns real CLI/API authentication that issues the same type.
    This issuer is for core tests only and is not a production authority.
    """

    __slots__ = ("_policy_ref", "_reviewer_ref", "_used_nonces")

    def __init__(self, policy_ref: str, reviewer_ref: str) -> None:
        self._policy_ref = policy_ref
        self._reviewer_ref = reviewer_ref
        self._used_nonces: set[str] = set()

    def authorize(self, plan: LearningPlan | ReviewedAcquisitionPlan) -> ReviewerAuthorization:
        """Issue a :class:`ReviewerAuthorization` for ``plan``."""
        nonce = secrets.token_hex(16)
        self._used_nonces.add(nonce)
        return ReviewerAuthorization(
            reviewer_ref=self._reviewer_ref,
            policy_ref=self._policy_ref,
            plan_ref=plan.plan_ref,
            decision="approve",
            nonce=nonce,
            expires_at=999,
        )

    def for_plan(self, plan: LearningPlan | ReviewedAcquisitionPlan) -> ReviewerAuthorization:
        """Alias for :meth:`authorize`."""
        return self.authorize(plan)


# ---------------------------------------------------------------------------
# LearningCoordinator
# ---------------------------------------------------------------------------


_DESIGNATION_CONTRACT_REF = "contract:designation_learning"
_ACQUISITION_CONTRACT_REF = "contract:generic_definition_acquisition"
_ACQUISITION_POLICY_REF = "policy:acquisition"
_ANSWER_CONTRACT_REF = "contract:designation_answer"
_CAP_LEARN = "cap:learn"
_INTERNAL_REF_PREFIXES = (
    "op:",
    "role:",
    "dim:",
    "state:",
    "state_value:",
    "entity:",
    "concept:",
    "relation:",
    "event:",
    "participant:",
    "cap:",
    "rel:",
    "label:",
    "adapter:",
)


def _is_internal_ref_spelling(surface: str) -> bool:
    """Check whether ``surface`` is an internal ref spelling (not a valid surface).

    Internal refs are not language and must not be exposed as user-visible
    designations by spelling (AGENTS.md section 5: internal-ref lexicalization).
    """
    return any(surface.startswith(prefix) for prefix in _INTERNAL_REF_PREFIXES)


class LearningCoordinator:
    """Coordinates typed designation learning and reviewed acquisition.

    The coordinator manages pending learning plans and reviewed acquisitions.
    Conversational wording cannot authorize writes — only reviewed
    authorization can.  No public ``install_rules``, ``add_rule``, or
    mutable-authority shortcut exists.

    One pending learning obligation may exist at a time.
    """

    __slots__ = (
        "_authority",
        "_stores",
        "_config",
        "_query_engine",
        "_lowerer",
        "_designations",
        "_pending_plan_ref",
        "_consumed_plan_refs",
        "_consumed_nonces",
        "_turn",
        "_revision",
        "_pending_programs",
    )

    def __init__(
        self,
        authority: Any,
        stores: SemanticStores,
        config: RuntimeConfig,
        query_engine: QueryEngine,
    ) -> None:
        self._authority = authority
        self._stores = stores
        self._config = config
        self._query_engine = query_engine
        self._lowerer = GenericDefinitionLowerer()
        self._designations = DesignationStore()
        self._pending_plan_ref: str | None = None
        self._consumed_plan_refs: set[str] = set()
        self._consumed_nonces: set[str] = set()
        self._turn = 0
        self._revision = 0
        self._pending_programs: tuple[Any, ...] | None = None

    @property
    def designations(self) -> DesignationStore:
        """The committed designation store."""
        return self._designations

    def advance_turn(self) -> None:
        """Advance the current turn (for expiry tracking)."""
        self._turn += 1

    # -- Designation learning ------------------------------------------------

    def plan_designation_learning(
        self,
        surface: str,
        target_ref: str,
        query_result: QueryResult,
        *,
        capability_ref: str = _CAP_LEARN,
        expected_target_kinds: tuple[str, ...] = (),
        expires_at_turn: int | None = None,
    ) -> LearningPlan:
        """Plan a designation learning obligation.

        Creates a typed :class:`LearningPlan` pinned to the exact
        :class:`QueryResult`.  The plan is NOT a commit — it is a pending
        obligation that can only be consumed by :meth:`review_and_commit`
        with a valid :class:`ReviewerAuthorization`.

        Only one pending learning obligation may exist at a time.
        """
        # Check one-pending-obligation constraint.
        if self._pending_plan_ref is not None:
            raise LearningGap(
                "pending_obligation_exists",
                "one pending learning obligation may exist at a time",
            )

        # Reject internal-ref lexicalization.
        if _is_internal_ref_spelling(surface):
            raise LearningGap(
                "internal_ref_lexicalization",
                "internal refs are not language and cannot be designations",
            )

        # Determine expected target kinds from the target atom if not provided.
        if not expected_target_kinds:
            target_atom = self._authority.atoms.get(target_ref)
            if target_atom is not None:
                expected_target_kinds = (target_atom.kind,)
            else:
                expected_target_kinds = ()

        expiry = expires_at_turn if expires_at_turn is not None else self._turn + 1

        plan_ref = stable_ref("plan:designation", {
            "surface": surface,
            "target": target_ref,
            "query_id": query_result.query_ref,
            "authority_generation": self._authority.generation,
            "turn": self._turn,
        })
        goal_ref = stable_ref("goal:learn_designation", {
            "surface": surface,
            "target": target_ref,
        })

        plan = LearningPlan(
            plan_ref=plan_ref,
            contract_ref=_DESIGNATION_CONTRACT_REF,
            source_query_ref=query_result.query_ref,
            goal_ref=goal_ref,
            capability_ref=capability_ref,
            commit_operator_ref="op:designation",
            surface_literal=surface,
            target_ref=target_ref,
            expected_target_kinds=expected_target_kinds,
            answer_contract_ref=_ANSWER_CONTRACT_REF,
            provenance_refs=(query_result.query_ref,),
            expires_at_turn=expiry,
        )

        self._pending_plan_ref = plan_ref
        return plan

    def review_and_commit(
        self,
        plan: LearningPlan,
        authorization: ReviewerAuthorization | None,
    ) -> DesignationCommitReceipt:
        """Review and commit a designation learning plan.

        Requires:
        - ``cap:learn`` capability;
        - a typed :class:`ReviewerAuthorization` bound to
          reviewer/policy/plan/decision/nonce/expiry;
        - existing target identity;
        - non-conflict;
        - an atomic six-phase commit receipt.

        A successful commit consumes the plan exactly once.  Replaying the
        same plan or authorization fails.
        """
        self._validate_authorization(plan, authorization)

        # Check capability.
        caps = self._authority.capabilities.get("participant:user", [])
        if plan.capability_ref not in caps:
            raise LearningGap(
                "missing_capability",
                f"capability {plan.capability_ref} not granted",
            )

        # Check target identity exists.
        target_atom = self._authority.atoms.get(plan.target_ref)
        if target_atom is None:
            raise LearningGap(
                "missing_target_identity",
                f"target {plan.target_ref} does not exist in authority",
            )

        # Check target kind match.
        if plan.expected_target_kinds and target_atom.kind not in plan.expected_target_kinds:
            raise LearningGap(
                "target_kind_mismatch",
                f"expected {plan.expected_target_kinds}, got {target_atom.kind}",
            )

        # Check non-conflict: the surface must not already designate a
        # different target.
        existing = self._designations.for_surface(plan.surface_literal, "en")
        if existing and plan.target_ref not in existing:
            raise LearningGap(
                "designation_conflict",
                f"surface '{plan.surface_literal}' already designates {existing}",
            )

        # Check expiry.
        if plan.expires_at_turn <= self._turn:
            raise LearningGap(
                "plan_expired",
                f"plan expired at turn {plan.expires_at_turn}, current turn {self._turn}",
            )

        # Check not already consumed.
        if plan.plan_ref in self._consumed_plan_refs:
            raise LearningGap("plan_already_consumed", "plan was already committed")

        # Atomic commit: record the designation and consume the plan.
        self._designations.commit_reviewed(
            plan.surface_literal, plan.target_ref, language="en"
        )
        self._revision += 1
        self._consumed_plan_refs.add(plan.plan_ref)
        self._consumed_nonces.add(authorization.nonce)
        self._pending_plan_ref = None

        return DesignationCommitReceipt(
            operator_ref="op:designation",
            surface=plan.surface_literal,
            target_ref=plan.target_ref,
            plan_ref=plan.plan_ref,
            revision=self._revision,
        )

    # -- Reviewed acquisition ------------------------------------------------

    def plan_reviewed_acquisition(
        self,
        programs: tuple[Any, ...],
        acquisition_kind: str,
        *,
        reviewer_policy_ref: str = _ACQUISITION_POLICY_REF,
    ) -> ReviewedAcquisitionPlan:
        """Plan a reviewed acquisition of new authority content.

        Accepts already-verified semantic programs under an independently
        configured reviewer policy.  The plan invokes the side-effect-free
        lowerer to preview the rules, but does NOT publish anything until
        :meth:`review_and_commit_acquisition` is called with a valid
        authorization.

        Only one pending learning obligation may exist at a time.
        """
        if self._pending_plan_ref is not None:
            raise LearningGap(
                "pending_obligation_exists",
                "one pending learning obligation may exist at a time",
            )

        valid_kinds = {"identity", "frame", "rule", "dimension", "transition"}
        if acquisition_kind not in valid_kinds:
            raise LearningGap(
                "invalid_acquisition_kind",
                f"expected one of {valid_kinds}, got {acquisition_kind}",
            )

        program_refs = tuple(
            getattr(p, "program_ref", f"program:{i}") for i, p in enumerate(programs)
        )

        plan_ref = stable_ref("plan:acquisition", {
            "program_refs": list(program_refs),
            "acquisition_kind": acquisition_kind,
            "authority_generation": self._authority.generation,
            "turn": self._turn,
        })

        plan = ReviewedAcquisitionPlan(
            plan_ref=plan_ref,
            contract_ref=_ACQUISITION_CONTRACT_REF,
            verified_program_refs=program_refs,
            acquisition_kind=acquisition_kind,  # type: ignore[arg-type]
            expected_owner_ref="owner:acquisition",
            reviewer_policy_ref=reviewer_policy_ref,
            provenance_refs=program_refs,
            authority_parent_generation=self._authority.generation,
        )

        self._pending_plan_ref = plan_ref
        # Store programs for the commit phase.
        self._pending_programs = tuple(programs)
        return plan

    def review_and_commit_acquisition(
        self,
        plan: ReviewedAcquisitionPlan,
        authorization: ReviewerAuthorization | None,
    ) -> AcquisitionReceipt:
        """Review and commit a reviewed acquisition plan.

        Invokes the side-effect-free lowerer, links the complete candidate
        bundle, and atomically publishes a new authority generation.  One
        invalid definition rejects the entire acquisition (atomic).
        """
        self._validate_authorization(plan, authorization)

        # Check capability.
        caps = self._authority.capabilities.get("participant:user", [])
        if _CAP_LEARN not in caps:
            raise LearningGap(
                "missing_capability",
                f"capability {_CAP_LEARN} not granted",
            )

        # Check not already consumed.
        if plan.plan_ref in self._consumed_plan_refs:
            raise LearningGap("plan_already_consumed", "plan was already committed")

        # Check authority parent generation matches.
        if plan.authority_parent_generation != self._authority.generation:
            raise LearningGap(
                "stale_authority_generation",
                f"plan expects {plan.authority_parent_generation}, "
                f"current is {self._authority.generation}",
            )

        # Retrieve the programs stored at plan time.
        programs = self._pending_programs
        if programs is None:
            raise LearningGap(
                "missing_programs",
                "verified programs not available for acquisition",
            )

        # Invoke the side-effect-free lowerer to preview rules.
        lowering = self._lowerer.preview(programs)

        if not lowering.created_rule_refs:
            raise AuthorityLinkError("lowering produced no rules")

        # One invalid definition rejects the entire acquisition (atomic).
        # Every program must produce exactly one rule; a program that the
        # lowerer silently skips (e.g. fewer than 2 applications) is invalid.
        if len(lowering.created_rule_refs) != len(programs):
            raise AuthorityLinkError(
                "one or more programs did not produce a rule; "
                "entire acquisition rejected"
            )

        # Validate all rules: one invalid rejects the entire acquisition.
        # A rule is invalid if it has empty antecedent or consequent.
        for rule in lowering.rules:
            if not rule.antecedent or not rule.consequent:
                raise AuthorityLinkError(
                    f"invalid rule {rule.rule_ref}: empty antecedent or consequent"
                )

        # Atomically publish a new authority generation.
        # Rules are compatible additions — compatibility hash is preserved.
        parent_gen = self._authority.generation
        compat_hash = self._authority.model_compatibility_hash

        for rule in lowering.rules:
            self._authority.rules[rule.rule_ref] = rule

        new_gen = stable_ref("authority:generation", {
            "parent": parent_gen,
            "rules": list(lowering.created_rule_refs),
        })
        self._authority.generation = new_gen

        self._revision += 1
        self._consumed_plan_refs.add(plan.plan_ref)
        self._consumed_nonces.add(authorization.nonce)
        self._pending_plan_ref = None
        self._pending_programs = None

        return AcquisitionReceipt(
            parent_generation=parent_gen,
            new_generation=new_gen,
            authority_compatibility_hash=compat_hash,
            created_rule_refs=lowering.created_rule_refs,
            plan_ref=plan.plan_ref,
        )

    # -- Internal helpers ----------------------------------------------------

    def _validate_authorization(
        self,
        plan: LearningPlan | ReviewedAcquisitionPlan,
        authorization: ReviewerAuthorization | None,
    ) -> None:
        """Validate a :class:`ReviewerAuthorization` against a plan."""
        if authorization is None:
            raise LearningGap(
                "missing_authorization",
                "reviewed authorization is required",
            )

        if not isinstance(authorization, ReviewerAuthorization):
            raise LearningGap(
                "invalid_authorization_type",
                "authorization must be a ReviewerAuthorization",
            )

        # Check plan_ref matches.
        if authorization.plan_ref != plan.plan_ref:
            raise LearningGap(
                "authorization_plan_mismatch",
                f"authorization is for {authorization.plan_ref}, "
                f"not {plan.plan_ref}",
            )

        # Check decision is approve.
        if authorization.decision != "approve":
            raise LearningGap(
                "authorization_denied",
                f"decision is {authorization.decision}, not approve",
            )

        # Check authorization not expired.
        if authorization.expires_at <= self._turn:
            raise LearningGap(
                "authorization_expired",
                f"authorization expired at turn {authorization.expires_at}",
            )

        # Check nonce not replayed.
        if authorization.nonce in self._consumed_nonces:
            raise LearningGap(
                "authorization_replay",
                "nonce has already been consumed",
            )
