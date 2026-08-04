"""Tests for constrained action masks and the legal transition relation.

The :class:`ActionMasker` and :class:`LegalActionIndex` both use the same
pure context-local transition predicate. The neural decoder mask and the
underlying legality index must produce the same set of legal next actions,
preventing a learned decoder from emitting structurally impossible actions.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.programs import ProgramAction
from cemm_authoritative_hybrid.verifier import (
    ActionMasker,
    LegalActionIndex,
)


def _candidate_actions(context, action_index: int) -> tuple[ProgramAction, ...]:
    """Build a broad set of candidate ``ProgramAction`` values at *action_index*.

    The candidates cover every action type with plausible arguments drawn from
    the supplied :class:`ProposalContext` slots, so that ``filter_legal`` and
    ``is_legal`` can be exercised against the full transition relation.
    """
    candidates: list[ProgramAction] = []
    # select_context — the only legal action at an empty prefix.
    candidates.append(
        ProgramAction.create(
            action_index=action_index,
            action_type="select_context",
            arguments=(context.context_ref,),
        )
    )
    # select_mode — one candidate per mode slot.
    for slot in context.mode_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="select_mode",
                arguments=(slot.slot_ref,),
            )
        )
    # select_designation — one candidate per designation slot.
    for slot in context.designation_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="select_designation",
                arguments=(slot.slot_ref,),
            )
        )
    # instantiate_operator — one candidate per application frame.
    for frame in context.application_frames:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="instantiate_operator",
                arguments=("application:main", frame.slot_ref),
            )
        )
    # bind_role — one candidate per contribution slot.
    for contrib in context.contribution_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="bind_role",
                arguments=("application:main", "role:subject", contrib.slot_ref),
            )
        )
    # bind_reference — one candidate per reference slot.
    for ref in context.reference_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="bind_reference",
                arguments=("application:main", "role:subject", ref.slot_ref),
            )
        )
    # bind_nested_application (role variant) — one per proposition role.
    for frame in context.application_frames:
        for prop_role in frame.proposition_roles:
            candidates.append(
                ProgramAction.create(
                    action_index=action_index,
                    action_type="bind_nested_application",
                    arguments=(
                        "role",
                        "application:main",
                        prop_role,
                        "application:nested",
                    ),
                )
            )
    # bind_nested_application (link variant) — one per expression link slot.
    for link in context.expression_link_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="bind_nested_application",
                arguments=(
                    "link",
                    "link:0",
                    link.slot_ref,
                    "application:main",
                    "application:nested",
                ),
            )
        )
    # attach_scope — one candidate per scope slot.
    for scope in context.scope_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="attach_scope",
                arguments=("scope:0", scope.slot_ref, "application:main"),
            )
        )
    # project_variable — one candidate per variable slot.
    for var in context.variable_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="project_variable",
                arguments=("binder:0", var.slot_ref, "application:main"),
            )
        )
    # propose_transition — one candidate per transition slot.
    for trans in context.transition_slots:
        candidates.append(
            ProgramAction.create(
                action_index=action_index,
                action_type="propose_transition",
                arguments=(trans.slot_ref, "application:main"),
            )
        )
    # complete_program — terminal action with no arguments.
    candidates.append(
        ProgramAction.create(
            action_index=action_index,
            action_type="complete_program",
            arguments=(),
        )
    )
    # abstain — terminal action with no arguments.
    candidates.append(
        ProgramAction.create(
            action_index=action_index,
            action_type="abstain",
            arguments=(),
        )
    )
    return tuple(candidates)


# ---------------------------------------------------------------------------
# Mask and verifier produce the same legal action set
# ---------------------------------------------------------------------------


def test_decoder_mask_matches_verifier_legal_next_actions(masker, verifier, prefix):
    """The masker filter and the underlying legality index must agree."""
    context = masker.legal_index.context
    candidates = _candidate_actions(context, len(prefix))
    masked = masker.filter_legal(prefix, candidates)
    exhaustive = tuple(
        candidate
        for candidate in candidates
        if masker.legal_index.is_legal(candidate, prefix)
    )
    assert set(masked) == set(exhaustive)


def test_mask_and_verifier_match_for_empty_prefix(masker, verifier):
    """Both produce the same set for an empty prefix."""
    prefix = ()
    context = masker.legal_index.context
    candidates = _candidate_actions(context, 0)
    masked = masker.filter_legal(prefix, candidates)
    exhaustive = tuple(
        candidate
        for candidate in candidates
        if masker.legal_index.is_legal(candidate, prefix)
    )
    assert set(masked) == set(exhaustive)
    assert len(masked) > 0


def test_mask_and_verifier_match_after_complete(masker, verifier, valid_program):
    """After complete_program, no further actions are legal."""
    prefix = valid_program.actions  # ends with complete_program
    context = masker.legal_index.context
    candidates = _candidate_actions(context, len(prefix))
    masked = masker.filter_legal(prefix, candidates)
    exhaustive = tuple(
        candidate
        for candidate in candidates
        if masker.legal_index.is_legal(candidate, prefix)
    )
    assert set(masked) == set(exhaustive)
    assert set(masked) == set()


# ---------------------------------------------------------------------------
# Terminal actions block further actions
# ---------------------------------------------------------------------------


def test_complete_program_is_terminal(masker, valid_program):
    """No actions are legal after complete_program."""
    prefix = valid_program.actions
    context = masker.legal_index.context
    candidates = _candidate_actions(context, len(prefix))
    result = masker.filter_legal(prefix, candidates)
    assert result == ()


def test_abstain_is_terminal(masker):
    """No actions are legal after abstain."""
    abstain_action = ProgramAction.create(
        action_index=0,
        action_type="abstain",
        arguments=(),
    )
    context = masker.legal_index.context
    candidates = _candidate_actions(context, 1)
    result = masker.filter_legal((abstain_action,), candidates)
    assert result == ()


# ---------------------------------------------------------------------------
# Ordering constraints
# ---------------------------------------------------------------------------


def test_select_context_legal_at_empty_prefix(masker):
    """select_context is legal at the start (empty prefix)."""
    context = masker.legal_index.context
    candidates = _candidate_actions(context, 0)
    result = masker.filter_legal((), candidates)
    # Should contain at least one select_context action.
    assert any(action.action_type == "select_context" for action in result)


def test_select_mode_not_legal_without_context(masker):
    """select_mode is not legal without a preceding select_context."""
    context = masker.legal_index.context
    candidates = _candidate_actions(context, 0)
    result = masker.filter_legal((), candidates)
    assert not any(action.action_type == "select_mode" for action in result)


def test_select_mode_legal_after_context(masker):
    """select_mode is legal after select_context."""
    context = masker.legal_index.context
    ctx = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=(context.context_ref,),
    )
    candidates = _candidate_actions(context, 1)
    result = masker.filter_legal((ctx,), candidates)
    assert any(action.action_type == "select_mode" for action in result)


def test_instantiate_operator_not_legal_without_designation(masker):
    """instantiate_operator is not legal without a preceding select_designation."""
    context = masker.legal_index.context
    ctx = ProgramAction.create(
        action_index=0,
        action_type="select_context",
        arguments=(context.context_ref,),
    )
    mode = ProgramAction.create(
        action_index=1,
        action_type="select_mode",
        arguments=(context.mode_slots[0].slot_ref,),
    )
    candidates = _candidate_actions(context, 2)
    result = masker.filter_legal((ctx, mode), candidates)
    assert not any(action.action_type == "instantiate_operator" for action in result)


# ---------------------------------------------------------------------------
# Bound constraints
# ---------------------------------------------------------------------------


def test_legal_next_actions_bounded_by_max_actions(masker, linked_authority):
    """The legal action set is empty when prefix reaches max_applications."""
    from cemm_authoritative_hybrid.config import RuntimeConfig

    config = RuntimeConfig.release()
    max_actions = config.max_applications
    context = masker.legal_index.context
    # Build a prefix of max_actions actions; the final action is complete_program
    # so the prefix is terminal and no further actions are legal.
    prefix = tuple(
        ProgramAction.create(
            action_index=i,
            action_type="project_variable",
            arguments=(f"binder:{i}", f"var:{i}", f"node:{i}"),
        )
        for i in range(max_actions - 1)
    ) + (
        ProgramAction.create(
            action_index=max_actions - 1,
            action_type="complete_program",
            arguments=(),
        ),
    )
    candidates = _candidate_actions(context, max_actions)
    result = masker.filter_legal(prefix, candidates)
    assert result == ()


# ---------------------------------------------------------------------------
# LegalActionIndex purity
# ---------------------------------------------------------------------------


def test_is_legal_is_pure_predicate(masker, prefix):
    """is_legal returns the same result for the same inputs."""
    legal_index = masker.legal_index
    candidates = _candidate_actions(legal_index.context, len(prefix))
    if candidates:
        action = candidates[0]
        result1 = legal_index.is_legal(action, prefix)
        result2 = legal_index.is_legal(action, prefix)
        assert result1 == result2
