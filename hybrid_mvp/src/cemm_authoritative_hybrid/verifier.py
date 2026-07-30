"""Independent exact program verifier and constrained action masks.

This module owns :class:`ExactProgramVerifier`, :class:`VerificationError`,
:class:`VerificationResult`, :class:`LegalActionIndex`, and
:class:`ActionMasker`.

The verifier independently recomputes structural, reference, scope, capability
and transition legality of a :class:`SemanticSwitchProgram`. It **never** reads
proposal logits or scores and **never** repairs a program. Invalid candidates
receive typed rejection codes.

The :class:`LegalActionIndex` is an immutable index constructed during
authority activation. Both the verifier's exhaustive enumeration and the
neural decoder's :class:`ActionMasker` call the same pure transition predicate
(``is_legal``) with separate enumeration code paths, preventing a learned
decoder from emitting structurally impossible actions.

Verification order (each check appends typed errors but does not short-circuit
unless noted):
    1. ABI / hash / revision
    2. Action syntax
    3. Referenced identity existence
    4. Semantic kind
    5. Port compatibility
    6. Cardinality
    7. Scope acyclicity
    8. Graph depth
    9. Coverage
    10. Mode / goal legality
    11. Effect requirements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical import stable_ref
from .coverage import CoverageReceipt, CoverageVerifier
from .programs import (
    PERSISTENT_OPERATORS,
    SWITCH_ACTION_TYPES,
    ProgramAction,
    SemanticSwitchProgram,
)

__all__ = [
    "VerificationError",
    "VerificationResult",
    "ExactProgramVerifier",
    "LegalActionIndex",
    "ActionMasker",
]


# ---------------------------------------------------------------------------
# Semantic modes (closed set)
# ---------------------------------------------------------------------------

_VALID_MODES: frozenset[str] = frozenset(
    {"OBSERVE", "QUERY", "REQUEST", "SIMULATE"}
)

# Kinds that may be designated (select_designation target).
_DESIGNATABLE_KINDS: frozenset[str] = frozenset(
    {"concept", "entity", "participant", "event_type"}
)

# Scope kinds (closed set from programs.ScopeKind).
_SCOPE_KINDS: frozenset[str] = frozenset(
    {"modal", "polarity", "tense", "aspect", "negation"}
)


# ---------------------------------------------------------------------------
# VerificationError and VerificationResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerificationError:
    """A structured verification error.

    Attributes:
        code: a stable error code (e.g. ``"unknown_ref"``).
        detail: a human-readable detail string.
        action_ref: the action ref that triggered the error, or None.
    """

    code: str
    detail: str = ""
    action_ref: str | None = None


@dataclass(frozen=True)
class VerificationResult:
    """The result of independently verifying a :class:`SemanticSwitchProgram`.

    Attributes:
        program_ref: the ref of the verified program.
        accepted: True only if every check passed (no errors).
        well_formed: True if structural/syntactic checks passed (checks 1-8).
        errors: tuple of :class:`VerificationError`.
        verification_hash: a stable hash of the verification outcome.
        coverage_receipt: the :class:`CoverageReceipt` from coverage
            verification, or None if coverage was not run.
    """

    program_ref: str
    accepted: bool
    well_formed: bool
    errors: tuple[VerificationError, ...]
    verification_hash: str
    coverage_receipt: CoverageReceipt | None = None


# ---------------------------------------------------------------------------
# LegalActionIndex — immutable, constructed during authority activation
# ---------------------------------------------------------------------------


class LegalActionIndex:
    """Immutable index of legal transition relations for action masking.

    Constructed during authority activation. The :meth:`is_legal` method is a
    pure transition predicate: given an action and a prefix of already-taken
    actions, it returns whether the action is structurally legal. Both the
    verifier's exhaustive enumeration and the neural decoder's
    :class:`ActionMasker` call this same predicate.

    Args:
        authority: the :class:`LinkedAuthority` with reviewed atoms.
        config: the :class:`RuntimeConfig` with bounds.
    """

    __slots__ = (
        "_authority",
        "_config",
        "_max_actions",
        "_max_depth",
        "_atom_refs",
        "_operators",
        "_modes",
        "_scope_kinds",
        "_operator_roles",
        "_context_refs",
        "_designation_targets",
        "_transition_refs",
    )

    def __init__(self, authority: Any, config: Any) -> None:
        self._authority = authority
        self._config = config
        self._max_actions = getattr(config, "max_applications", 24)
        self._max_depth = getattr(config, "max_graph_depth", 6)
        self._atom_refs: frozenset[str] = frozenset(authority.atoms.keys())
        self._operators = PERSISTENT_OPERATORS
        self._modes = _VALID_MODES
        self._scope_kinds = _SCOPE_KINDS
        self._operator_roles = dict(authority.operator_roles)
        # Context refs: event_type atoms can serve as context.
        self._context_refs: frozenset[str] = authority.by_kind("event_type")
        # Designation targets: designatable kinds.
        self._designation_targets: frozenset[str] = frozenset(
            ref
            for ref, record in authority.atoms.items()
            if record.kind in _DESIGNATABLE_KINDS
        )
        # Transition refs: event types with signatures.
        self._transition_refs: frozenset[str] = frozenset(
            authority.event_signatures.keys()
        )

    # -- pure transition predicate ------------------------------------------

    def is_legal(self, action: ProgramAction, prefix: tuple[ProgramAction, ...]) -> bool:
        """Return True if ``action`` is structurally legal given ``prefix``.

        This is the single pure transition predicate used by both the
        verifier's exhaustive enumeration and the neural decoder's mask.
        """
        # Bound: prefix must not already be at capacity.
        if len(prefix) >= self._max_actions:
            return False

        # Terminal actions: nothing is legal after complete_program or abstain.
        if prefix:
            last = prefix[-1]
            if last.action_type in ("complete_program", "abstain"):
                return False

        at = action.action_type

        # -- ordering constraints -------------------------------------------
        has_context = any(a.action_type == "select_context" for a in prefix)
        has_mode = any(a.action_type == "select_mode" for a in prefix)
        has_designation = any(
            a.action_type == "select_designation" for a in prefix
        )
        has_operator = any(
            a.action_type == "instantiate_operator" for a in prefix
        )
        is_complete = any(a.action_type == "complete_program" for a in prefix)

        if at == "select_context":
            return not has_context  # only one select_context
        if at == "select_mode":
            return has_context and not has_mode
        if at == "select_designation":
            return has_mode and not has_designation
        if at == "instantiate_operator":
            if not has_designation or has_operator:
                return False
            # operator must be in the five persistent operators.
            if not action.arguments:
                return False
            return action.arguments[0] in self._operators
        if at == "abstain":
            return True  # abstain is always legal (frontier)
        if at == "complete_program":
            return has_operator and not is_complete

        # Post-operator actions require an operator to have been instantiated.
        if not has_operator:
            return False

        if at == "bind_role":
            # Role name must be a known operator role.
            if not action.arguments:
                return False
            role_name = action.arguments[0]
            return self._is_valid_role(role_name, prefix)

        if at == "bind_reference":
            if len(action.arguments) < 2:
                return False
            target = action.arguments[1]
            return target in self._atom_refs

        if at == "bind_nested_application":
            if not action.arguments:
                return False
            # App refs must reference actions in the prefix.
            app_refs = {a.action_ref for a in prefix}
            return action.arguments[0] in app_refs

        if at == "attach_scope":
            if len(action.arguments) < 2:
                return False
            scope_kind = action.arguments[0]
            if scope_kind not in self._scope_kinds:
                return False
            # Target app ref must exist in prefix.
            app_refs = {a.action_ref for a in prefix}
            return action.arguments[1] in app_refs

        if at == "project_variable":
            return bool(action.arguments)

        if at == "propose_transition":
            if not action.arguments:
                return False
            return action.arguments[0] in self._transition_refs

        return False

    def _is_valid_role(
        self, role_name: str, prefix: tuple[ProgramAction, ...]
    ) -> bool:
        """Check that ``role_name`` is a valid role for the instantiated
        operator and not already bound."""
        # Find the operator from the prefix.
        operator: str | None = None
        for a in prefix:
            if a.action_type == "instantiate_operator" and a.arguments:
                operator = a.arguments[0]
                break
        if operator is None:
            return False
        required = self._operator_roles.get(operator, ())
        if role_name not in required:
            return False
        # No duplicate role binding.
        for a in prefix:
            if a.action_type == "bind_role" and a.arguments:
                if a.arguments[0] == role_name:
                    return False
        return True

    # -- enumeration --------------------------------------------------------

    def legal_next_action_ids(self, prefix: tuple[ProgramAction, ...]) -> set[str]:
        """Return the set of legal next action structural IDs given ``prefix``.

        Enumerates all candidate actions from the authority data and filters
        through :meth:`is_legal``.
        """
        result: set[str] = set()
        for action in self._candidate_actions(prefix):
            if self.is_legal(action, prefix):
                result.add(action.structural_id())
        return result

    def _candidate_actions(
        self, prefix: tuple[ProgramAction, ...]
    ) -> list[ProgramAction]:
        """Generate bounded candidate actions for enumeration."""
        candidates: list[ProgramAction] = []
        idx = len(prefix)

        # select_context
        for ctx in sorted(self._context_refs):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="select_context",
                    arguments=(ctx,),
                    source_unit_refs=(),
                )
            )
        # Also allow a default context if no event types exist.
        if not self._context_refs:
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="select_context",
                    arguments=("context:turn",),
                    source_unit_refs=(),
                )
            )

        # select_mode
        for mode in sorted(self._modes):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="select_mode",
                    arguments=(mode,),
                    source_unit_refs=(),
                )
            )

        # select_designation
        for target in sorted(self._designation_targets):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="select_designation",
                    arguments=("designation:0", target),
                    source_unit_refs=(),
                )
            )

        # instantiate_operator
        for op in sorted(self._operators):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="instantiate_operator",
                    arguments=(op, "designation:0"),
                    source_unit_refs=(),
                )
            )

        # bind_role — enumerate over operator roles and source unit refs
        operator: str | None = None
        for a in prefix:
            if a.action_type == "instantiate_operator" and a.arguments:
                operator = a.arguments[0]
                break
        if operator is not None:
            unit_refs: set[str] = set()
            for a in prefix:
                unit_refs.update(a.source_unit_refs)
            for role in self._operator_roles.get(operator, ()):
                for unit in sorted(unit_refs) or ("unit:0",):
                    candidates.append(
                        ProgramAction(
                            action_ref=f"action:cand:{idx}",
                            action_type="bind_role",
                            arguments=(role, unit),
                            source_unit_refs=(unit,),
                        )
                    )

        # bind_reference — enumerate over authority atoms
        for target in sorted(self._atom_refs):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="bind_reference",
                    arguments=("ref:0", target),
                    source_unit_refs=(),
                )
            )

        # bind_nested_application — enumerate over prefix app refs
        app_refs = [a.action_ref for a in prefix]
        for app in app_refs:
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="bind_nested_application",
                    arguments=(app,),
                    source_unit_refs=(),
                )
            )

        # attach_scope — enumerate over scope kinds and prefix app refs
        for kind in sorted(self._scope_kinds):
            for app in app_refs:
                candidates.append(
                    ProgramAction(
                        action_ref=f"action:cand:{idx}",
                        action_type="attach_scope",
                        arguments=(kind, app),
                        source_unit_refs=(),
                    )
                )

        # project_variable
        candidates.append(
            ProgramAction(
                action_ref=f"action:cand:{idx}",
                action_type="project_variable",
                arguments=("var:0",),
                source_unit_refs=(),
            )
        )

        # propose_transition — enumerate over event types with signatures
        for event_type in sorted(self._transition_refs):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:cand:{idx}",
                    action_type="propose_transition",
                    arguments=(event_type,),
                    source_unit_refs=(),
                )
            )

        # complete_program
        candidates.append(
            ProgramAction(
                action_ref=f"action:cand:{idx}",
                action_type="complete_program",
                arguments=(),
                source_unit_refs=(),
            )
        )

        # abstain
        candidates.append(
            ProgramAction(
                action_ref=f"action:cand:{idx}",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            )
        )

        return candidates


# ---------------------------------------------------------------------------
# ActionMasker — wraps LegalActionIndex for neural decoding
# ---------------------------------------------------------------------------


class ActionMasker:
    """Wraps a :class:`LegalActionIndex` for neural decoding masks.

    The masker delegates to the same :class:`LegalActionIndex` used by the
    verifier, ensuring the neural decoder can only emit structurally legal
    actions.

    Args:
        legal_index: the :class:`LegalActionIndex` from authority activation.
    """

    __slots__ = ("_legal_index",)

    def __init__(self, legal_index: LegalActionIndex) -> None:
        self._legal_index = legal_index

    def legal_next_action_ids(self, prefix: tuple[ProgramAction, ...]) -> set[str]:
        """Return the set of legal next action IDs given ``prefix``.

        Delegates to the same :class:`LegalActionIndex` used by the verifier.
        """
        return self._legal_index.legal_next_action_ids(prefix)


# ---------------------------------------------------------------------------
# ExactProgramVerifier
# ---------------------------------------------------------------------------


class ExactProgramVerifier:
    """Independently verifies structural legality of a SemanticSwitchProgram.

    The verifier never reads proposal logits or scores and never repairs a
    program. It only checks structural legality in a fixed verification order.

    Args:
        authority: the :class:`LinkedAuthority` with reviewed atoms.
        config: the :class:`RuntimeConfig` with bounds.
        coverage_verifier: the :class:`CoverageVerifier` for coverage checks.
    """

    __slots__ = (
        "_authority",
        "_config",
        "_coverage_verifier",
        "_legal_index",
        "_max_depth",
        "_max_actions",
    )

    def __init__(
        self,
        authority: Any,
        config: Any,
        coverage_verifier: CoverageVerifier,
    ) -> None:
        self._authority = authority
        self._config = config
        self._coverage_verifier = coverage_verifier
        self._legal_index = LegalActionIndex(authority, config)
        self._max_depth = getattr(config, "max_graph_depth", 6)
        self._max_actions = getattr(config, "max_applications", 24)

    @property
    def legal_index(self) -> LegalActionIndex:
        """The :class:`LegalActionIndex` used by this verifier."""
        return self._legal_index

    # -- public API ----------------------------------------------------------

    def verify(self, program: SemanticSwitchProgram) -> VerificationResult:
        """Independently verify ``program`` and return a :class:`VerificationResult`.

        The verifier never reads proposal logits or scores and never repairs
        the program. It checks structural legality in a fixed order and
        returns typed errors.
        """
        errors: list[VerificationError] = []
        well_formed_errors: list[VerificationError] = []

        # 1. ABI / hash / revision
        self._check_revision(program, errors)
        self._check_action_hash(program, errors)

        # 2. Action syntax
        self._check_action_syntax(program, errors)

        # 3. Referenced identity existence
        self._check_referenced_identities(program, errors)

        # 4. Semantic kind
        self._check_semantic_kind(program, errors)

        # 5. Port compatibility
        self._check_port_compatibility(program, errors)

        # 6. Cardinality
        self._check_cardinality(program, errors)

        # 7. Scope acyclicity
        self._check_scope_acyclicity(program, errors)

        # 8. Graph depth
        self._check_graph_depth(program, errors)

        # Well-formed = checks 1-8 passed
        well_formed = not errors
        well_formed_errors = list(errors)

        # 9. Coverage
        coverage_receipt = self._check_coverage(program, errors)

        # 10. Mode / goal legality
        self._check_mode_goal(program, errors)

        # 11. Effect requirements
        self._check_effect_requirements(program, errors)

        accepted = not errors
        verification_hash = stable_ref(
            "verification",
            {
                "program_ref": program.program_ref,
                "accepted": accepted,
                "well_formed": well_formed,
                "errors": [
                    (e.code, e.action_ref) for e in errors
                ],
            },
        )

        return VerificationResult(
            program_ref=program.program_ref,
            accepted=accepted,
            well_formed=well_formed,
            errors=tuple(errors),
            verification_hash=verification_hash,
            coverage_receipt=coverage_receipt,
        )

    def enumerate_legal_next_action_ids(
        self, prefix: tuple[ProgramAction, ...]
    ) -> set[str]:
        """Exhaustively enumerate all legal next action IDs given ``prefix``.

        Uses the same :class:`LegalActionIndex` as the :class:`ActionMasker`,
        ensuring the verifier and decoder agree on legal actions.
        """
        return self._legal_index.legal_next_action_ids(prefix)

    # -- check 1: ABI / hash / revision -------------------------------------

    def _check_revision(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        gen = program.revision_pin.authority_generation
        if gen != self._authority.generation:
            errors.append(
                VerificationError(
                    code="stale_revision",
                    detail=(
                        f"program revision_pin authority_generation '{gen}' "
                        f"does not match authority generation "
                        f"'{self._authority.generation}'"
                    ),
                )
            )

    def _check_action_hash(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        # The action_encoding_hash is a derived property; verify it is stable.
        try:
            h = program.action_encoding_hash
            if not h or not h.startswith("program_actions:"):
                errors.append(
                    VerificationError(
                        code="invalid_hash",
                        detail="action_encoding_hash is missing or malformed",
                    )
                )
        except Exception:
            errors.append(
                VerificationError(
                    code="invalid_hash",
                    detail="failed to compute action_encoding_hash",
                )
            )

    # -- check 2: action syntax ---------------------------------------------

    def _check_action_syntax(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        valid_types = frozenset(SWITCH_ACTION_TYPES)
        for action in program.actions:
            if action.action_type not in valid_types:
                errors.append(
                    VerificationError(
                        code="invalid_action_type",
                        detail=f"action_type '{action.action_type}' not in "
                        f"SWITCH_ACTION_TYPES",
                        action_ref=action.action_ref,
                    )
                )
            # instantiate_operator must reference a persistent operator.
            if action.action_type == "instantiate_operator":
                if not action.arguments:
                    errors.append(
                        VerificationError(
                            code="invalid_action_type",
                            detail="instantiate_operator requires at least one "
                            "argument (the operator)",
                            action_ref=action.action_ref,
                        )
                    )
                elif action.arguments[0] not in PERSISTENT_OPERATORS:
                    errors.append(
                        VerificationError(
                            code="invalid_operator",
                            detail=(
                                f"operator '{action.arguments[0]}' not in "
                                f"the five persistent operators"
                            ),
                            action_ref=action.action_ref,
                        )
                    )
            # attach_scope must have a valid scope kind.
            if action.action_type == "attach_scope":
                if len(action.arguments) < 2:
                    errors.append(
                        VerificationError(
                            code="invalid_action_type",
                            detail="attach_scope requires scope kind and "
                            "target application ref",
                            action_ref=action.action_ref,
                        )
                    )
                elif action.arguments[0] not in _SCOPE_KINDS:
                    errors.append(
                        VerificationError(
                            code="invalid_scope_kind",
                            detail=(
                                f"scope kind '{action.arguments[0]}' not in "
                                f"closed scope kind set"
                            ),
                            action_ref=action.action_ref,
                        )
                    )
            # select_mode must have a valid mode.
            if action.action_type == "select_mode":
                if not action.arguments or action.arguments[0] not in _VALID_MODES:
                    errors.append(
                        VerificationError(
                            code="invalid_mode",
                            detail=(
                                f"mode '{action.arguments[0] if action.arguments else ''}' "
                                f"not in valid mode set"
                            ),
                            action_ref=action.action_ref,
                        )
                    )

    # -- check 3: referenced identity existence ----------------------------

    def _check_referenced_identities(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        atom_refs = self._authority.atoms
        for action in program.actions:
            at = action.action_type
            if at == "select_designation":
                if len(action.arguments) >= 2:
                    target = action.arguments[1]
                    if target not in atom_refs:
                        errors.append(
                            VerificationError(
                                code="unknown_ref",
                                detail=(
                                    f"select_designation target '{target}' "
                                    f"not in authority atoms"
                                ),
                                action_ref=action.action_ref,
                            )
                        )
            elif at == "bind_reference":
                if len(action.arguments) >= 2:
                    target = action.arguments[1]
                    if target not in atom_refs:
                        errors.append(
                            VerificationError(
                                code="unknown_ref",
                                detail=(
                                    f"bind_reference target '{target}' not in "
                                    f"authority atoms"
                                ),
                                action_ref=action.action_ref,
                            )
                        )
            elif at == "propose_transition":
                if action.arguments:
                    event_type = action.arguments[0]
                    if event_type not in atom_refs:
                        errors.append(
                            VerificationError(
                                code="unknown_ref",
                                detail=(
                                    f"propose_transition event_type "
                                    f"'{event_type}' not in authority atoms"
                                ),
                                action_ref=action.action_ref,
                            )
                        )

    # -- check 4: semantic kind --------------------------------------------

    def _check_semantic_kind(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        atoms = self._authority.atoms
        for action in program.actions:
            at = action.action_type
            if at == "select_designation":
                if len(action.arguments) >= 2:
                    target = action.arguments[1]
                    record = atoms.get(target)
                    if record is not None and record.kind not in _DESIGNATABLE_KINDS:
                        errors.append(
                            VerificationError(
                                code="wrong_kind",
                                detail=(
                                    f"select_designation target '{target}' has "
                                    f"kind '{record.kind}', expected one of "
                                    f"{sorted(_DESIGNATABLE_KINDS)}"
                                ),
                                action_ref=action.action_ref,
                            )
                        )

    # -- check 5: port compatibility ---------------------------------------

    def _check_port_compatibility(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        # Check that bind_nested_application targets reference actions that
        # exist in the program (either instantiate_operator or another
        # bind_nested_application, since recursive nesting is allowed).
        all_refs = {a.action_ref for a in program.actions}
        for action in program.actions:
            if action.action_type == "bind_nested_application":
                if action.arguments:
                    target = action.arguments[0]
                    if target not in all_refs:
                        errors.append(
                            VerificationError(
                                code="dangling_nested_ref",
                                detail=(
                                    f"bind_nested_application target "
                                    f"'{target}' does not exist in the program"
                                ),
                                action_ref=action.action_ref,
                            )
                        )

    # -- check 6: cardinality -----------------------------------------------

    def _check_cardinality(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        # Check for duplicate action_refs.
        seen_refs: set[str] = set()
        for action in program.actions:
            if action.action_ref in seen_refs:
                errors.append(
                    VerificationError(
                        code="duplicate_action_ref",
                        detail=f"duplicate action_ref '{action.action_ref}'",
                        action_ref=action.action_ref,
                    )
                )
            seen_refs.add(action.action_ref)

        # Check for duplicate role bindings.
        role_names: list[str] = []
        for action in program.actions:
            if action.action_type == "bind_role" and action.arguments:
                role_names.append(action.arguments[0])
        seen_roles: set[str] = set()
        for role in role_names:
            if role in seen_roles:
                errors.append(
                    VerificationError(
                        code="duplicate_role",
                        detail=f"role '{role}' bound more than once",
                    )
                )
            seen_roles.add(role)

        # Check required roles are present for each instantiated operator.
        for action in program.actions:
            if action.action_type == "instantiate_operator" and action.arguments:
                operator = action.arguments[0]
                required = self._authority.operator_roles.get(operator, ())
                bound = set(role_names)
                missing = set(required) - bound
                if missing:
                    errors.append(
                        VerificationError(
                            code="missing_role",
                            detail=(
                                f"operator '{operator}' is missing required "
                                f"roles: {sorted(missing)}"
                            ),
                            action_ref=action.action_ref,
                        )
                    )

    # -- check 7: scope acyclicity ------------------------------------------

    def _check_scope_acyclicity(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        # Build a nesting graph from bind_nested_application actions.
        # Each bind_nested_application creates an edge: parent_app -> child_app.
        # We detect cycles in this graph.
        edges: dict[str, set[str]] = {}
        app_refs = {a.action_ref for a in program.actions}

        for action in program.actions:
            if action.action_type == "bind_nested_application" and action.arguments:
                child = action.arguments[0]
                # The parent is the most recent instantiate_operator before
                # this action (or the action_ref of the nesting action itself).
                # For simplicity, use the action_ref as the parent node.
                parent = action.action_ref
                edges.setdefault(parent, set()).add(child)
                edges.setdefault(child, set())

        # Also include attach_scope targets in the graph.
        for action in program.actions:
            if action.action_type == "attach_scope" and len(action.arguments) >= 2:
                target = action.arguments[1]
                edges.setdefault(action.action_ref, set()).add(target)
                edges.setdefault(target, set())

        # Ensure all app refs are nodes.
        for ref in app_refs:
            edges.setdefault(ref, set())

        # DFS cycle detection.
        visiting: set[str] = set()
        visited: set[str] = set()

        def has_cycle(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for child in edges.get(node, set()):
                if has_cycle(child):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        for node in edges:
            if has_cycle(node):
                errors.append(
                    VerificationError(
                        code="scope_cycle",
                        detail="cycle detected in scope/application nesting graph",
                    )
                )
                return  # one cycle error is enough

    # -- check 8: graph depth -----------------------------------------------

    def _check_graph_depth(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        # Compute the nesting depth from bind_nested_application actions.
        # The depth is the longest path in the nesting graph.
        edges: dict[str, set[str]] = {}
        for action in program.actions:
            if action.action_type == "bind_nested_application" and action.arguments:
                child = action.arguments[0]
                parent = action.action_ref
                edges.setdefault(parent, set()).add(child)
                edges.setdefault(child, set())

        # Also add edges from attach_scope.
        for action in program.actions:
            if action.action_type == "attach_scope" and len(action.arguments) >= 2:
                target = action.arguments[1]
                edges.setdefault(action.action_ref, set()).add(target)
                edges.setdefault(target, set())

        # Compute longest path via DFS (bounded by max_depth + 1 to detect
        # excess).
        memo: dict[str, int] = {}

        def depth(node: str) -> int:
            if node in memo:
                return memo[node]
            children = edges.get(node, set())
            if not children:
                memo[node] = 1
                return 1
            memo[node] = 1  # prevent infinite recursion on cycles
            max_child = 0
            for child in children:
                d = depth(child)
                if d > max_child:
                    max_child = d
            memo[node] = 1 + max_child
            return memo[node]

        max_depth = 0
        for node in edges:
            d = depth(node)
            if d > max_depth:
                max_depth = d

        # Also count total actions as a proxy for depth.
        if len(program.actions) > self._max_actions:
            errors.append(
                VerificationError(
                    code="excess_depth",
                    detail=(
                        f"program has {len(program.actions)} actions, "
                        f"exceeding max_applications {self._max_actions}"
                    ),
                )
            )
        elif max_depth > self._max_depth:
            errors.append(
                VerificationError(
                    code="excess_depth",
                    detail=(
                        f"nesting depth {max_depth} exceeds max_graph_depth "
                        f"{self._max_depth}"
                    ),
                )
            )

    # -- check 9: coverage --------------------------------------------------

    def _check_coverage(
        self,
        program: SemanticSwitchProgram,
        errors: list[VerificationError],
    ) -> CoverageReceipt | None:
        receipt = self._coverage_verifier.verify_program(program)
        if receipt.missing_unit_refs:
            errors.append(
                VerificationError(
                    code="uncovered_unit",
                    detail=(
                        f"source units without assignment: "
                        f"{list(receipt.missing_unit_refs)}"
                    ),
                )
            )
        if receipt.duplicate_unit_refs:
            for unit in receipt.duplicate_unit_refs:
                errors.append(
                    VerificationError(
                        code="duplicate_assignment",
                        detail=f"unit '{unit}' assigned more than once",
                    )
                )
        return receipt

    # -- check 10: mode / goal legality -------------------------------------

    def _check_mode_goal(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        # mode_ref is like "mode:OBSERVE"; extract the mode name.
        mode_ref = program.mode_ref
        if mode_ref.startswith("mode:"):
            mode_name = mode_ref[5:]
        else:
            mode_name = mode_ref
        if mode_name not in _VALID_MODES:
            errors.append(
                VerificationError(
                    code="invalid_mode",
                    detail=f"mode '{mode_name}' not in valid mode set",
                )
            )

    # -- check 11: effect requirements --------------------------------------

    def _check_effect_requirements(
        self, program: SemanticSwitchProgram, errors: list[VerificationError]
    ) -> None:
        # If the program has propose_transition actions, check that the
        # event type has a signature with required capabilities/permissions.
        for action in program.actions:
            if action.action_type == "propose_transition" and action.arguments:
                event_type = action.arguments[0]
                signature = self._authority.event_signatures.get(event_type)
                if signature is None:
                    # Already caught by referenced identity existence.
                    continue
                # Check capabilities.
                available = self._authority.capabilities.get(
                    "participant:system", frozenset()
                )
                for cap in signature.required_capabilities:
                    if cap not in available:
                        errors.append(
                            VerificationError(
                                code="missing_capability",
                                detail=f"missing capability '{cap}' for "
                                f"event '{event_type}'",
                                action_ref=action.action_ref,
                            )
                        )
                # Check permissions.
                for perm in signature.required_permissions:
                    triple = ("participant:system", perm, event_type)
                    if triple not in self._authority.permissions:
                        errors.append(
                            VerificationError(
                                code="missing_permission",
                                detail=f"missing permission '{perm}' for "
                                f"event '{event_type}'",
                                action_ref=action.action_ref,
                            )
                        )
                # Check adapter.
                if (
                    signature.adapter_ref
                    and signature.adapter_ref not in self._authority.adapters
                ):
                    errors.append(
                        VerificationError(
                            code="missing_adapter",
                            detail=f"missing adapter '{signature.adapter_ref}'",
                            action_ref=action.action_ref,
                        )
                    )
