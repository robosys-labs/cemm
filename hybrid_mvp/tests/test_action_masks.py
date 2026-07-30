"""Tests for constrained action masks and the legal transition relation.

The :class:`ActionMasker` and :class:`ExactProgramVerifier` both use the same
pure transition predicate from :class:`LegalActionIndex`. The neural decoder
mask and the verifier's exhaustive enumeration must produce the same set of
legal next action IDs, preventing a learned decoder from emitting structurally
impossible actions.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.programs import ProgramAction
from cemm_authoritative_hybrid.verifier import (
    ActionMasker,
    LegalActionIndex,
)


# ---------------------------------------------------------------------------
# Mask and verifier produce the same legal action set
# ---------------------------------------------------------------------------


def test_decoder_mask_matches_verifier_legal_next_actions(masker, verifier, prefix):
    """The masker and verifier must produce the same legal action set."""
    masked = set(masker.legal_next_action_ids(prefix))
    exhaustive = set(verifier.enumerate_legal_next_action_ids(prefix))
    assert masked == exhaustive


def test_mask_and_verifier_match_for_empty_prefix(masker, verifier):
    """Both produce the same set for an empty prefix."""
    prefix = ()
    masked = set(masker.legal_next_action_ids(prefix))
    exhaustive = set(verifier.enumerate_legal_next_action_ids(prefix))
    assert masked == exhaustive
    assert len(masked) > 0


def test_mask_and_verifier_match_after_complete(masker, verifier, valid_program):
    """After complete_program, no further actions are legal."""
    prefix = valid_program.actions  # ends with complete_program
    masked = set(masker.legal_next_action_ids(prefix))
    exhaustive = set(verifier.enumerate_legal_next_action_ids(prefix))
    assert masked == exhaustive
    assert masked == set()


# ---------------------------------------------------------------------------
# Terminal actions block further actions
# ---------------------------------------------------------------------------


def test_complete_program_is_terminal(masker, valid_program):
    """No actions are legal after complete_program."""
    prefix = valid_program.actions
    result = masker.legal_next_action_ids(prefix)
    assert result == set()


def test_abstain_is_terminal(masker):
    """No actions are legal after abstain."""
    abstain_action = ProgramAction(
        action_ref="action:abstain",
        action_type="abstain",
        arguments=(),
        source_unit_refs=(),
    )
    result = masker.legal_next_action_ids((abstain_action,))
    assert result == set()


# ---------------------------------------------------------------------------
# Ordering constraints
# ---------------------------------------------------------------------------


def test_select_context_legal_at_empty_prefix(masker):
    """select_context is legal at the start (empty prefix)."""
    result = masker.legal_next_action_ids(())
    # Should contain at least one select_context action.
    assert any(sid.startswith("select_context|") for sid in result)


def test_select_mode_not_legal_without_context(masker):
    """select_mode is not legal without a preceding select_context."""
    result = masker.legal_next_action_ids(())
    assert not any(sid.startswith("select_mode|") for sid in result)


def test_select_mode_legal_after_context(masker):
    """select_mode is legal after select_context."""
    ctx = ProgramAction(
        action_ref="action:select_context",
        action_type="select_context",
        arguments=("context:turn",),
        source_unit_refs=(),
    )
    result = masker.legal_next_action_ids((ctx,))
    assert any(sid.startswith("select_mode|") for sid in result)


def test_instantiate_operator_not_legal_without_designation(masker):
    """instantiate_operator is not legal without a preceding select_designation."""
    ctx = ProgramAction(
        action_ref="action:select_context",
        action_type="select_context",
        arguments=("context:turn",),
        source_unit_refs=(),
    )
    mode = ProgramAction(
        action_ref="action:select_mode",
        action_type="select_mode",
        arguments=("OBSERVE",),
        source_unit_refs=(),
    )
    result = masker.legal_next_action_ids((ctx, mode))
    assert not any(sid.startswith("instantiate_operator|") for sid in result)


# ---------------------------------------------------------------------------
# Bound constraints
# ---------------------------------------------------------------------------


def test_legal_next_actions_bounded_by_max_actions(masker, linked_authority):
    """The legal action set is empty when prefix reaches max_applications."""
    from cemm_authoritative_hybrid.config import RuntimeConfig

    config = RuntimeConfig.release()
    max_actions = config.max_applications
    # Build a prefix of max_actions project_variable actions.
    prefix = tuple(
        ProgramAction(
            action_ref=f"action:{i}",
            action_type="project_variable",
            arguments=(f"var:{i}",),
            source_unit_refs=(),
        )
        for i in range(max_actions)
    )
    result = masker.legal_next_action_ids(prefix)
    assert result == set()


# ---------------------------------------------------------------------------
# LegalActionIndex purity
# ---------------------------------------------------------------------------


def test_is_legal_is_pure_predicate(masker, prefix):
    """is_legal returns the same result for the same inputs."""
    legal_index = masker._legal_index
    # Pick any candidate action.
    candidates = list(legal_index._candidate_actions(prefix))
    if candidates:
        action = candidates[0]
        result1 = legal_index.is_legal(action, prefix)
        result2 = legal_index.is_legal(action, prefix)
        assert result1 == result2
