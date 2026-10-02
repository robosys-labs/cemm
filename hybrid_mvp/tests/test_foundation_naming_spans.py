"""Construction-local naming literals; public meaning and acquisition proofs."""
import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.expressions import (
    SemanticApplication, SemanticExpression, RoleBinding, GroundedReference, LiteralValue,
)
from tests.test_foundation_learning_proposal import ROOT
from tests.test_foundation_designation_consumers import _publish_alias


@pytest.mark.parametrize("directive,label", (
    (False, "luz nuvemora"), (False, "luz   nuvemora"), (False, "mother nuvemora"),
    (False, "luz nuve móra"), (False, "mother learn nuvemora"),
    (True, "luz nuvemora"), (True, "luz   nuvemora"), (True, "mother nuvemora"),
    (True, "luz nuve móra"), (True, "mother learn nuvemora")),
    ids=("declaration-multiword", "declaration-whitespace", "declaration-known-word", "declaration-unicode", "declaration-known-event",
         "directive-multiword", "directive-whitespace", "directive-known-word", "directive-unicode", "directive-known-event"))
def test_naming_label_preserves_complete_literal_and_exact_meaning(tmp_path, label, directive):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        surface = ("learn " if directive else "") + label + " means mother"
        result = runtime.process("session:naming-span", surface)
        meaning = result.verification.selected_meaning
        assert meaning is not None, result.proposal.status
        assert result.orientation.mode.value == ("REQUEST" if directive else "OBSERVE")
        roles = (
            RoleBinding("role:actor" if directive else "role:label_type",
                GroundedReference("participant:system" if directive else "label:lexical")),
            RoleBinding("role:surface", LiteralValue("string", label)),
            RoleBinding("role:target", GroundedReference("concept:mother")),
        )
        app = SemanticApplication("application:expected", "op:event" if directive else "op:designation",
            "event:learn_alias" if directive else "label:lexical", roles)
        assert meaning.expression == SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        assert not result.proposal.truncated
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("shared_span", (False, True), ids=("distinct-occurrences", "one-occurrence"))
def test_contribution_profile_limit_is_occurrence_local(tmp_path, shared_span):
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.proposal_context import ContributionSlot, _bounded_unique_contributions
    config = RuntimeConfig.release()
    maximum = config.max_affordances_per_target * 2
    slots = tuple(ContributionSlot.create(contribution_ref=f"contribution:test-{index}", kind="predicate",
        source_unit_refs=("unit:0" if shared_span else f"unit:{index}",),
        target_ref="event:learn_alias", target_kind="event_type", input_ports=("role:surface", "role:target"),
        output_ports=("role:event",), constraints=(("profile", str(index)),), provenance_refs=("frame:reviewed",))
        for index in range(maximum + 1))
    retained = _bounded_unique_contributions(slots, config)
    assert retained == (slots[:maximum] if shared_span else slots)


__cemm_test_inventory__ = {
    "tests/test_foundation_naming_spans.py::test_contribution_profile_limit_is_occurrence_local[distinct-occurrences]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:contribution-profile-limit-is-occurrence-local-distinct-occurrences",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ad054d649bcecd309ee4e77d9e7157514c45c4c851239986754a573aa0451170"
    },
    "tests/test_foundation_naming_spans.py::test_contribution_profile_limit_is_occurrence_local[one-occurrence]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:contribution-profile-limit-is-occurrence-local-one-occurrence",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ad054d649bcecd309ee4e77d9e7157514c45c4c851239986754a573aa0451170"
    },
    "tests/test_foundation_naming_spans.py::test_first_naming_predicate_owns_known_event_word_inside_literal": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:first-naming-predicate-owns-known-event-word-inside-literal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "0f64825ba0d0a6aabb936f8ee43e7d518c537db8281d97ba430710ce13a90ec0"
    },
    "tests/test_foundation_naming_spans.py::test_markerless_words_do_not_manufacture_naming_literals": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:markerless-words-do-not-manufacture-naming-literals",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a076493de854824b330ac34ac561fbfc5a37927659299641cc192c1ae4f8e5fd"
    },
    "tests/test_foundation_naming_spans.py::test_mentioned_event_does_not_supply_directive_mode[bare-then-mentioned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:mentioned-event-does-not-supply-directive-mode-bare-then-mentioned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a26a72d2f84c00ed69cfd8fb75384dce808f38d81bf6f5b72a7fbe69706f5d43"
    },
    "tests/test_foundation_naming_spans.py::test_mentioned_event_does_not_supply_directive_mode[bare]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:mentioned-event-does-not-supply-directive-mode-bare",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a26a72d2f84c00ed69cfd8fb75384dce808f38d81bf6f5b72a7fbe69706f5d43"
    },
    "tests/test_foundation_naming_spans.py::test_mentioned_event_does_not_supply_directive_mode[coordination]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:mentioned-event-does-not-supply-directive-mode-coordination",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a26a72d2f84c00ed69cfd8fb75384dce808f38d81bf6f5b72a7fbe69706f5d43"
    },
    "tests/test_foundation_naming_spans.py::test_mentioned_event_does_not_supply_directive_mode[event-designation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:mentioned-event-does-not-supply-directive-mode-event-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a26a72d2f84c00ed69cfd8fb75384dce808f38d81bf6f5b72a7fbe69706f5d43"
    },
    "tests/test_foundation_naming_spans.py::test_mentioned_event_does_not_supply_directive_mode[mentioned-then-bare]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:mentioned-event-does-not-supply-directive-mode-mentioned-then-bare",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a26a72d2f84c00ed69cfd8fb75384dce808f38d81bf6f5b72a7fbe69706f5d43"
    },
    "tests/test_foundation_naming_spans.py::test_mentioned_event_does_not_supply_directive_mode[repeated-then-bare]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:mentioned-event-does-not-supply-directive-mode-repeated-then-bare",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a26a72d2f84c00ed69cfd8fb75384dce808f38d81bf6f5b72a7fbe69706f5d43"
    },
    "tests/test_foundation_naming_spans.py::test_mentioned_event_does_not_supply_directive_mode[self-designation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:mentioned-event-does-not-supply-directive-mode-self-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "a26a72d2f84c00ed69cfd8fb75384dce808f38d81bf6f5b72a7fbe69706f5d43"
    },
    "tests/test_foundation_naming_spans.py::test_multiword_alias_publication_and_restart_reuse": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:multiword-alias-publication-and-restart-reuse",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "029eba977e001457d4a7a5cefc5011f248fe6cc1e8de5e9bb82a93b5a48b5b4f"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[declaration-known-event]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-declaration-known-event",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[declaration-known-word]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-declaration-known-word",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[declaration-multiword]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-declaration-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[declaration-unicode]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-declaration-unicode",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[declaration-whitespace]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-declaration-whitespace",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[directive-known-event]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-directive-known-event",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[directive-known-word]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-directive-known-word",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[directive-multiword]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-directive-multiword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[directive-unicode]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-directive-unicode",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_label_preserves_complete_literal_and_exact_meaning[directive-whitespace]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-label-preserves-complete-literal-and-exact-meaning-directive-whitespace",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "ea2b6aedfa818411b1d4166473bd71539d92b2d99195fc6967b358cd0f45dc13"
    },
    "tests/test_foundation_naming_spans.py::test_naming_labels_do_not_borrow_words_or_markers_across_clauses": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-labels-do-not-borrow-words-or-markers-across-clauses",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "5173a1d162195943cf1cd272d9c32cb4dd0189babbf4d12a83340670a8cc07f9"
    },
    "tests/test_foundation_naming_spans.py::test_naming_literal_binding_requires_exact_owner_in_compilation_and_reconstruction[foreign-owner-declaration]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-literal-binding-requires-exact-owner-in-compilation-and-reconstruction-foreign-owner-declaration",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7bddc301d47971640dfc842eacc19ed38bd29cd97911f9ed4a0ceac850122c01"
    },
    "tests/test_foundation_naming_spans.py::test_naming_literal_binding_requires_exact_owner_in_compilation_and_reconstruction[foreign-owner-directive]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-literal-binding-requires-exact-owner-in-compilation-and-reconstruction-foreign-owner-directive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7bddc301d47971640dfc842eacc19ed38bd29cd97911f9ed4a0ceac850122c01"
    },
    "tests/test_foundation_naming_spans.py::test_naming_literal_binding_requires_exact_owner_in_compilation_and_reconstruction[missing-owner-declaration]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-literal-binding-requires-exact-owner-in-compilation-and-reconstruction-missing-owner-declaration",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7bddc301d47971640dfc842eacc19ed38bd29cd97911f9ed4a0ceac850122c01"
    },
    "tests/test_foundation_naming_spans.py::test_naming_literal_binding_requires_exact_owner_in_compilation_and_reconstruction[missing-owner-directive]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:naming-literal-binding-requires-exact-owner-in-compilation-and-reconstruction-missing-owner-directive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7bddc301d47971640dfc842eacc19ed38bd29cd97911f9ed4a0ceac850122c01"
    },
    "tests/test_foundation_naming_spans.py::test_quotation_boundary_before_naming_predicate_is_not_discarded[direct-quoted]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-boundary-before-naming-predicate-is-not-discarded-direct-quoted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f17816b84401ed997569f4adab453e2421442cdc1d5834aa52d01487af259f6f"
    },
    "tests/test_foundation_naming_spans.py::test_quotation_boundary_before_naming_predicate_is_not_discarded[direct-unclosed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-boundary-before-naming-predicate-is-not-discarded-direct-unclosed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f17816b84401ed997569f4adab453e2421442cdc1d5834aa52d01487af259f6f"
    },
    "tests/test_foundation_naming_spans.py::test_quotation_boundary_before_naming_predicate_is_not_discarded[embedded-quoted]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-boundary-before-naming-predicate-is-not-discarded-embedded-quoted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f17816b84401ed997569f4adab453e2421442cdc1d5834aa52d01487af259f6f"
    },
    "tests/test_foundation_naming_spans.py::test_quotation_boundary_before_naming_predicate_is_not_discarded[embedded-unclosed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quotation-boundary-before-naming-predicate-is-not-discarded-embedded-unclosed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "f17816b84401ed997569f4adab453e2421442cdc1d5834aa52d01487af259f6f"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[declaration-partial-quote]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-declaration-partial-quote",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[declaration-punctuated]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-declaration-punctuated",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[declaration-quoted]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-declaration-quoted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[declaration-unclosed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-declaration-unclosed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[directive-partial-quote]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-directive-partial-quote",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[directive-punctuated]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-directive-punctuated",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[directive-quoted]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-directive-quoted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment[directive-unclosed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:quoted-label-without-reviewed-quote-span-never-learns-a-fragment-directive-unclosed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "situation-context",
        "source_ast_sha256": "7b0f8b37a16e674aa50bdc725edfa40a7a3f33658b879f18626835437bbfc038"
    },
    "tests/test_foundation_naming_spans.py::test_unseen_naming_event_alias_inherits_complete_label_span": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:unseen-naming-event-alias-inherits-complete-label-span",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "e7dd867c2d1461097b446ac34be8b3c4decbf902282226f7afbc6532b2e59a1f"
    }
}


def test_naming_labels_do_not_borrow_words_or_markers_across_clauses(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        text = "Alice likes Bob and learn luz nuvemora means mother and learn veltora means likes"
        _, context = runtime.orient("session:boundaries", text)
        labels = [row for row in context.contribution_slots if any(k == "naming_frame_ref" for k, _ in row.constraints)]
        assert {row.literal_value for row in labels} == {"luz nuvemora", "veltora"}
        spans = {ref: (start, end) for ref, start, end in context.source_unit_spans}
        for row in labels:
            first = min(spans[ref][0] for ref in row.source_unit_refs)
            last = max(spans[ref][1] for ref in row.source_unit_refs)
            assert text[first:last] == row.literal_value + " means"
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("directive,label", (
    (False, '"mother nuvemora"'), (False, '"mother nuvemora'), (False, 'mother "nuvemora"'), (False, 'mother; nuvemora'),
    (True, '"mother nuvemora"'), (True, '"mother nuvemora'), (True, 'mother "nuvemora"'), (True, 'mother; nuvemora')),
    ids=("declaration-quoted", "declaration-unclosed", "declaration-partial-quote", "declaration-punctuated",
         "directive-quoted", "directive-unclosed", "directive-partial-quote", "directive-punctuated"))
def test_quoted_label_without_reviewed_quote_span_never_learns_a_fragment(tmp_path, label, directive):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        result = runtime.process("session:quoted", ("learn " if directive else "") + f"{label} means mother")
        assert result.verification.selected_meaning is None
        assert result.evaluation is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_unseen_naming_event_alias_inherits_complete_label_span(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    before = (ROOT / "data/languages/en/forms.json").read_bytes()
    try:
        receipt = _publish_alias(runtime, "aprenora", "learn", "event:learn_alias")
        assert len(receipt.committed_fact_refs) == 1
        ordinary = runtime.process("session:ordinary", "learn luz nuvemora means mother")
        learned = runtime.process("session:learned", "aprenora luz nuvemora means mother")
        assert learned.verification.selected_meaning is not None
        assert learned.verification.selected_meaning.expression == ordinary.verification.selected_meaning.expression
        assert runtime.stores.world.revision == 1
        assert (ROOT / "data/languages/en/forms.json").read_bytes() == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", ("learn", "learn means learn", "turn means learn", "learn and learn",
    "learn means turn and turn", "learn means learn and learn", "learn and learn means learn"),
    ids=("bare", "self-designation", "event-designation", "coordination", "mentioned-then-bare", "repeated-then-bare", "bare-then-mentioned"))
def test_mentioned_event_does_not_supply_directive_mode(tmp_path, surface):
    from cemm_authoritative_hybrid.cycle import SemanticMode
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        result = runtime.process("session:mentioned-event", surface)
        assert result.orientation.mode is SemanticMode.OBSERVE
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_first_naming_predicate_owns_known_event_word_inside_literal(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        result = runtime.process("session:event-label", "learn learn nuvemora means mother")
        assert result.verification.selected_meaning is not None
        app, = result.verification.selected_meaning.expression.applications
        roles = {role.role_ref: role.filler for role in app.roles}
        assert app.predicate_ref == "event:learn_alias"
        assert roles["role:surface"] == LiteralValue("string", "learn nuvemora")
        assert roles["role:target"] == GroundedReference("concept:mother")
        assert roles["role:actor"] == GroundedReference("participant:system")
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_markerless_words_do_not_manufacture_naming_literals(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        _, context = runtime.orient("session:no-marker", "learn mother and learn likes")
        assert not any(key == "naming_frame_ref" for row in context.contribution_slots for key, _ in row.constraints)
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", ('"learn that velnora means mother', '"learn that velnora means mother"',
    '"learn velnora means mother', '"learn velnora means mother"'),
    ids=("embedded-unclosed", "embedded-quoted", "direct-unclosed", "direct-quoted"))
def test_quotation_boundary_before_naming_predicate_is_not_discarded(tmp_path, surface):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        result = runtime.process("session:quoted-predicate", surface)
        assert result.verification.selected_meaning is None
        assert result.evaluation is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("directive,corruption", ((False, "foreign-owner"), (True, "foreign-owner"),
    (False, "missing-owner"), (True, "missing-owner")),
    ids=("foreign-owner-declaration", "foreign-owner-directive", "missing-owner-declaration", "missing-owner-directive"))
def test_naming_literal_binding_requires_exact_owner_in_compilation_and_reconstruction(tmp_path, directive, corruption):
    from cemm_authoritative_hybrid.recursive_compiler import compile_recursive
    from cemm_authoritative_hybrid.verifier_reconstruction import reconstruct_expected_expression
    from cemm_authoritative_hybrid.expressions import CompilationFailure
    from tests.test_foundation_semantics import _membership_unchecked
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        text = ("learn " if directive else "") + "luz nuvemora means mother"
        _, context = runtime.orient("session:owner", text)
        program = runtime.proposal_model.propose(context).candidates[0].program
        action = next(row for row in program.actions if row.action_type == "bind_role" and row.arguments[1] == "role:surface")
        slot = context.contribution(action.arguments[2])
        key = "naming_frame_ref" if directive else "teaching_evidence_ref"
        assert any(k == key for k, _ in slot.constraints)
        constraints = tuple((k, "foreign:owner") if k == key else (k, v) for k, v in slot.constraints
            if corruption != "missing-owner" or k != key)
        forged_slot = _membership_unchecked(slot, constraints=constraints)
        forged_context = _membership_unchecked(context, contribution_slots=tuple(forged_slot if row.slot_ref == slot.slot_ref else row for row in context.contribution_slots))
        assert isinstance(compile_recursive(program, forged_context), CompilationFailure)
        assert reconstruct_expected_expression(program, forged_context) is None
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_multiword_alias_publication_and_restart_reuse(tmp_path):
    path = tmp_path / "store"
    runtime = load_runtime(ROOT, profile="development", store_path=path)
    before = (ROOT / "data/languages/en/forms.json").read_bytes()
    try:
        receipt = _publish_alias(runtime, "luz nuvemora", "likes", "rel:likes")
        assert len(receipt.committed_fact_refs) == 1
    finally:
        runtime.stores.close()
    runtime = load_runtime(ROOT, profile="development", store_path=path)
    try:
        from tests.test_foundation_semantics import _matrix_expression, _matrix_relation
        result = runtime.process("session:restarted", "Bob luz nuvemora Alice.")
        assert result.verification.selected_meaning.expression == _matrix_expression(_matrix_relation("entity:bob", "entity:alice"))
        assert runtime.stores.world.revision == 1
        assert (ROOT / "data/languages/en/forms.json").read_bytes() == before
    finally:
        runtime.stores.close()
