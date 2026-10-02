"""Reviewed source attribution at the R3 occurrence boundary."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.authority import AuthorityLinkError, AuthorityLinker
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.canonical import sha256_governed_text
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import DecisionAction, DecisionStatus
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller,
    GroundedReference,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
)
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.r3_artifacts import AdmissionStatus, PlacementMode
from cemm_authoritative_hybrid.r3_cognition import ObserveDecisionOwner
from cemm_authoritative_hybrid.r3_effects import (
    AdapterRegistry,
    NoEffectReason,
    NoEffectReceipt,
)
from cemm_authoritative_hybrid.situation import SituationContext


ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_reported_occurrences.py::test_reported_role_inheritance_control_rejects_invalid_authority[missing-source]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-role-inheritance-rejects-missing-source-control",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Occurrences", "owner_ref": "semantic-affordances",
        "source_ast_sha256": "55589bfaa5e38c8ca4f11803ac9bac10157e53c0b9cc8bf5c049ecc1669e0ce4",
    },
    "tests/test_foundation_reported_occurrences.py::test_reported_role_inheritance_control_rejects_invalid_authority[optional-child-role]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-role-inheritance-rejects-optional-child-role",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Occurrences", "owner_ref": "semantic-affordances",
        "source_ast_sha256": "55589bfaa5e38c8ca4f11803ac9bac10157e53c0b9cc8bf5c049ecc1669e0ce4",
    },
    "tests/test_foundation_reported_occurrences.py::test_reported_role_inheritance_control_rejects_invalid_authority[incompatible-child-role]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-role-inheritance-rejects-incompatible-child-role",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Occurrences", "owner_ref": "semantic-affordances",
        "source_ast_sha256": "55589bfaa5e38c8ca4f11803ac9bac10157e53c0b9cc8bf5c049ecc1669e0ce4",
    },
    "tests/test_foundation_reported_occurrences.py::test_reported_role_inheritance_control_rejects_invalid_authority[duplicate-signature]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-role-inheritance-rejects-duplicate-signature",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Occurrences", "owner_ref": "semantic-affordances",
        "source_ast_sha256": "55589bfaa5e38c8ca4f11803ac9bac10157e53c0b9cc8bf5c049ecc1669e0ce4",
    },
    "tests/test_foundation_reported_occurrences.py::test_reported_role_inheritance_control_rejects_invalid_authority[source-control-collision]": {
        "activation_phase": "R3", "assertion_ref": "assertion:reported-role-inheritance-rejects-source-control-collision",
        "diagnostic_role": "owner", "introduced_by_task": "Foundation-Reported-Occurrences", "owner_ref": "semantic-affordances",
        "source_ast_sha256": "55589bfaa5e38c8ca4f11803ac9bac10157e53c0b9cc8bf5c049ecc1669e0ce4",
    },
    "tests/test_foundation_reported_occurrences.py::test_say_source_attribution_control_is_linked_cached_and_content_addressed": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:say-source-attribution-control-linked-cached-content-addressed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "semantic-affordances",
        "source_ast_sha256": "1169b9d4b47b39a69048ddd17a5aaceaf6260c8feac1d71c5fd02af5e40f6a97",
    },
    "tests/test_foundation_reported_occurrences.py::test_source_attribution_control_rejects_nonproposition_content_role": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:source-attribution-control-rejects-nonproposition-content-role",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "semantic-affordances",
        "source_ast_sha256": "49bc812c637583461009d1c43b956c68a872c261787e4a2d1713ffdd98896ce2",
    },
    "tests/test_foundation_reported_occurrences.py::test_direct_r3_say_emits_outer_and_exact_attributed_child_occurrences": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:direct-r3-say-emits-outer-and-exact-attributed-child-occurrences",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-evaluate-observe",
        "source_ast_sha256": "f8be7038ca205c6844db72c0e3a26d9236d6e9b28a8832c590c0baa27bb0e50a",
    },
    "tests/test_foundation_reported_occurrences.py::test_direct_r3_preserves_negated_child_node_and_never_flattens_it": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:direct-r3-preserves-negated-child-node-and-never-flattens-it",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-evaluate-observe",
        "source_ast_sha256": "ef2bb2ac264c90caac6eaef6cc24ccd0a4341063787039a8a541e3b55798b974",
    },
    "tests/test_foundation_reported_occurrences.py::test_proposition_valued_teach_role_does_not_imply_source_attribution": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:proposition-valued-teach-role-does-not-imply-source-attribution",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-evaluate-observe",
        "source_ast_sha256": "490a25b7564e9db0d7de8c96f3141ea6cf39287c6cacd06d26a3e2297b1924a9",
    },
    "tests/test_foundation_reported_occurrences.py::test_public_reported_clause_preserves_source_and_has_no_effect[reported-state]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-reported-state-preserves-source-no-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-public-cycle",
        "source_ast_sha256": "8c9e71cc90f4bd89ea1e1c96bdddeef24db052ef02a2147de5074f6b76dde2bd",
    },
    "tests/test_foundation_reported_occurrences.py::test_public_reported_clause_preserves_source_and_has_no_effect[reported-relation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-reported-relation-preserves-source-no-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-public-cycle",
        "source_ast_sha256": "8c9e71cc90f4bd89ea1e1c96bdddeef24db052ef02a2147de5074f6b76dde2bd",
    },
    "tests/test_foundation_reported_occurrences.py::test_public_reported_clause_preserves_source_and_has_no_effect[reported-event]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-reported-event-preserves-source-no-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-public-cycle",
        "source_ast_sha256": "8c9e71cc90f4bd89ea1e1c96bdddeef24db052ef02a2147de5074f6b76dde2bd",
    },
    "tests/test_foundation_reported_occurrences.py::test_public_reported_clause_preserves_source_and_has_no_effect[reported-deixis]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-reported-participant-relative-source-no-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-public-cycle",
        "source_ast_sha256": "8c9e71cc90f4bd89ea1e1c96bdddeef24db052ef02a2147de5074f6b76dde2bd",
    },
    "tests/test_foundation_reported_occurrences.py::test_public_reported_clause_preserves_source_and_has_no_effect[reported-negation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-reported-negated-state-preserves-scope-no-effect",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Reported-Occurrences",
        "owner_ref": "r3-public-cycle",
        "source_ast_sha256": "8c9e71cc90f4bd89ea1e1c96bdddeef24db052ef02a2147de5074f6b76dde2bd",
    },
}


def _authority_copy(tmp_path: Path) -> Path:
    target = tmp_path / "authority"
    shutil.copytree(ROOT / "data" / "authority", target)
    return target


def _rewrite_affordance_owner(authority_dir: Path, change) -> None:
    owner_path = authority_dir / "frames" / "semantic_affordances.json"
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    change(owner)
    owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf-8")
    manifest_path = authority_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = next(item for item in manifest["owners"] if item["name"] == "semantic_affordances")
    row["sha256"] = sha256_governed_text(owner_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _situation(stores) -> SituationContext:
    return SituationContext.create(
        orientation_ref="orientation:reported-occurrence",
        proposal_context_ref="proposal_context:reported-occurrence",
        mode=SemanticMode.OBSERVE,
        session_ref="session:reported-occurrence",
        turn_ref="turn:reported-occurrence",
        turn_index=1,
        session_phase_ref="active",
        participant_refs=("participant:system", "participant:user"),
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        actor_ref=None,
        temporal_frame_ref="time:now",
        active_event_refs=(),
        focus_snapshot_ref="snapshot:focus:reported-occurrence",
        focus_refs=(),
        obligation_snapshot_ref="snapshot:obligation:reported-occurrence",
        obligation_refs=(),
        capability_refs=(),
        permission_snapshot_ref="snapshot:permission:reported-occurrence",
        permission_refs=(),
        resource_snapshot_ref="snapshot:resource:reported-occurrence",
        resource_refs=(),
        adapter_snapshot_ref="snapshot:adapter:reported-occurrence",
        adapter_refs=(),
        evidence_kinds=("text",),
        evidence_policy_refs=("policy:evidence:reported-occurrence",),
        adapter_receipt_refs=(),
        trusted_observation=False,
        source_refs=("source:reported-occurrence",),
        epistemic_scope_ref="epistemic_scope:observed",
        revision_pin=stores.revision_pin(),
    )


def _state_application() -> SemanticApplication:
    return SemanticApplication(
        "application:server-offline",
        "op:state",
        "dim:availability",
        (
            RoleBinding("role:subject", GroundedReference("entity:server")),
            RoleBinding("role:dimension", GroundedReference("dim:availability")),
            RoleBinding("role:value", GroundedReference("value:offline")),
        ),
    )


class _ForbiddenReportAdapter:
    def __init__(self) -> None:
        self.requests = []

    def invoke(self, request):
        self.requests.append(request)
        raise AssertionError("a reported clause must not invoke an adapter")

    def reconcile(self, request):
        self.requests.append(request)
        raise AssertionError("a reported clause must not reconcile an adapter")


def _say_expression(child_ref: str, *nodes: object) -> tuple[SemanticExpression, SemanticApplication]:
    speech = SemanticApplication(
        "application:alice-said",
        "op:event",
        "event:say",
        (
            RoleBinding("role:actor", GroundedReference("entity:alice")),
            RoleBinding("role:content", ApplicationFiller(child_ref)),
        ),
    )
    applications = tuple(node for node in nodes if type(node) is SemanticApplication)
    scopes = tuple(node for node in nodes if type(node) is ScopeOperator)
    return (
        SemanticExpression.create(
            applications=(*applications, speech),
            scope_operators=scopes,
            root_refs=(speech.application_ref,),
        ),
        speech,
    )


def test_say_source_attribution_control_is_linked_cached_and_content_addressed(tmp_path: Path) -> None:
    linked = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    assert linked.generation == "authority-v1-2026-10-01-communicative-controls"
    control = linked.source_attribution_control("event:say", "role:content")
    assert control is linked.source_attribution_control("event:say", "role:content")
    assert control.parent_frame_ref == "frame:event:say"
    assert control.source_role_ref == "role:actor"
    assert control.placement == "reported"
    assert linked.source_attribution_control("event:teach", "role:content") is None

    copied = _authority_copy(tmp_path)
    def replace_control_ref(owner):
        replacement = "control:source_attribution:event_say:reviewed-copy"
        owner["source_attribution_controls"][0]["control_ref"] = replacement
        for row in owner["reported_role_inheritance_controls"]:
            row["source_attribution_control_ref"] = replacement

    _rewrite_affordance_owner(copied, replace_control_ref)
    changed = AuthorityLinker().link_path(copied / "manifest.json")
    assert changed.content_hash != linked.content_hash
    assert changed.model_compatibility_hash == linked.model_compatibility_hash
    for inherited in (
        linked.reported_role_inheritance_control(
            "event:say", "role:content", target, "role:actor"
        )
        for target in ("event:greeting", "event:farewell")
    ):
        assert inherited is not None
        assert linked.designations.for_surface(inherited.control_ref, "en") == ()


@pytest.mark.parametrize(
    "attack,match",
    (
        ("missing-source", "linked source control"),
        ("optional-child-role", "absent or incompatible"),
        ("incompatible-child-role", "absent or incompatible"),
        ("duplicate-signature", "duplicate reported role inheritance signature"),
        ("source-control-collision", "duplicate reported role inheritance control identity"),
    ),
    ids=(
        "missing-source",
        "optional-child-role",
        "incompatible-child-role",
        "duplicate-signature",
        "source-control-collision",
    ),
)
def test_reported_role_inheritance_control_rejects_invalid_authority(
    tmp_path: Path, attack: str, match: str
) -> None:
    copied = _authority_copy(tmp_path)

    def mutate(owner):
        rows = owner["reported_role_inheritance_controls"]
        if attack == "missing-source":
            rows[0]["source_attribution_control_ref"] = "control:missing"
        elif attack == "optional-child-role":
            rows[0]["child_role_ref"] = "role:addressee"
        elif attack == "incompatible-child-role":
            rows[0]["child_target_ref"] = "event:set_state"
            rows[0]["child_role_ref"] = "role:value"
        elif attack == "duplicate-signature":
            duplicate = dict(rows[0])
            duplicate["control_ref"] = "control:reported_role_inheritance:duplicate"
            rows.append(duplicate)
        elif attack == "source-control-collision":
            rows[0]["control_ref"] = owner["source_attribution_controls"][0][
                "control_ref"
            ]

    _rewrite_affordance_owner(copied, mutate)
    with pytest.raises(AuthorityLinkError, match=match):
        AuthorityLinker().link_path(copied / "manifest.json")


def test_source_attribution_control_rejects_nonproposition_content_role(tmp_path: Path) -> None:
    copied = _authority_copy(tmp_path)
    _rewrite_affordance_owner(
        copied,
        lambda owner: owner["source_attribution_controls"][0].update(
            content_role_ref="role:actor"
        ),
    )
    with pytest.raises(AuthorityLinkError, match="proposition"):
        AuthorityLinker().link_path(copied / "manifest.json")


def test_direct_r3_say_emits_outer_and_exact_attributed_child_occurrences() -> None:
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    stores = memory_stores(authority_generation=authority.generation)
    try:
        child = _state_application()
        expression, _ = _say_expression(child.application_ref, child)
        result = ObserveDecisionOwner(authority).evaluate_full(
            expression, project_expression(expression), _situation(stores)
        )
        speech = next(
            row for row in expression.applications if row.predicate_ref == "event:say"
        )
        child_ref = next(
            row.filler.node_ref for row in speech.roles
            if row.role_ref == "role:content"
        )

        assert tuple(row.root_ref for row in result.claim_occurrences) == (
            speech.application_ref,
            child_ref,
        )
        outer, reported = result.claim_occurrences
        assert outer.source_ref == "source:reported-occurrence"
        assert outer.placement is PlacementMode.OBSERVED
        assert reported.source_ref == "entity:alice"
        assert reported.placement is PlacementMode.REPORTED
        admissions = {
            row.occurrence_ref: row for row in result.admission_decisions
        }
        assert admissions[outer.occurrence_ref].status is AdmissionStatus.CONTESTED
        assert admissions[reported.occurrence_ref].status is AdmissionStatus.ATTRIBUTED
        assert speech.application_ref in admissions[reported.occurrence_ref].proof_refs
        assert "control:source_attribution:event_say" in admissions[reported.occurrence_ref].proof_refs
        assert result.state_deltas == ()
        assert result.contribution.status is DecisionStatus.CONTESTED
        assert result.contribution.action is DecisionAction.RETAIN_ATTRIBUTION
    finally:
        stores.close()


def test_direct_r3_preserves_negated_child_node_and_never_flattens_it() -> None:
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    stores = memory_stores(authority_generation=authority.generation)
    try:
        child = _state_application()
        scope = ScopeOperator(
            "scope:server-not-offline",
            "scope:polarity",
            "polarity:negative",
            child.application_ref,
        )
        expression, _ = _say_expression(scope.scope_ref, child, scope)
        result = ObserveDecisionOwner(authority).evaluate_full(
            expression, project_expression(expression), _situation(stores)
        )

        canonical_scope = expression.scope_operators[0]
        assert result.claim_occurrences[1].root_ref == canonical_scope.scope_ref
        assert result.claim_occurrences[1].source_ref == "entity:alice"
        assert result.claim_occurrences[1].placement is PlacementMode.REPORTED
        assert result.state_deltas == ()
        assert all(row.proposed_fact_refs == () for row in result.admission_decisions)
    finally:
        stores.close()


def test_proposition_valued_teach_role_does_not_imply_source_attribution() -> None:
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    stores = memory_stores(authority_generation=authority.generation)
    try:
        child = _state_application()
        teaching = SemanticApplication(
            "application:alice-taught-bob",
            "op:event",
            "event:teach",
            (
                RoleBinding("role:actor", GroundedReference("entity:alice")),
                RoleBinding("role:learner", GroundedReference("entity:bob")),
                RoleBinding("role:content", ApplicationFiller(child.application_ref)),
            ),
        )
        expression = SemanticExpression.create(
            applications=(child, teaching), root_refs=(teaching.application_ref,)
        )
        result = ObserveDecisionOwner(authority).evaluate_full(
            expression, project_expression(expression), _situation(stores)
        )

        assert tuple(row.root_ref for row in result.claim_occurrences) == expression.root_refs
        assert result.claim_occurrences[0].placement is PlacementMode.OBSERVED
        assert result.state_deltas == ()
    finally:
        stores.close()


@pytest.mark.parametrize(
    ("text", "source_ref", "child_identity"),
    (
        ("Alice said the server is offline.", "entity:alice", "dim:availability"),
        ("Alice said Bob likes Alice.", "entity:alice", "rel:likes"),
        ("Alice said Bob left.", "entity:alice", "event:leave"),
        ("You said goodbye.", "participant:system", "event:farewell"),
        ("Alice said the server is not online.", "entity:alice", "scope:polarity"),
    ),
    ids=(
        "reported-state",
        "reported-relation",
        "reported-event",
        "reported-deixis",
        "reported-negation",
    ),
)
def test_public_reported_clause_preserves_source_and_has_no_effect(
    tmp_path: Path, text: str, source_ref: str, child_identity: str
) -> None:
    adapter = _ForbiddenReportAdapter()
    runtime = load_runtime(
        ROOT,
        profile="development",
        store_path=tmp_path / (text.replace(" ", "-").replace(".", "") + ".db"),
        adapters=AdapterRegistry({"adapter:state": adapter}),
    )
    try:
        before = runtime.stores.world.revision, runtime.stores.r3_world_facts()
        result = runtime.process("session:public-reported-occurrence", text)

        assert result.evaluation is not None
        occurrences = result.evaluation.claim_occurrences
        assert len(occurrences) == 2
        assert occurrences[0].placement is PlacementMode.OBSERVED
        assert occurrences[1].placement is PlacementMode.REPORTED
        assert occurrences[1].source_ref == source_ref
        child_node = project_expression(result.evaluation.expression).node_by_ref[
            occurrences[1].root_ref
        ]
        assert (
            child_node.operator_type
            if type(child_node) is ScopeOperator
            else child_node.predicate_ref
        ) == child_identity
        assert result.evaluation.state_deltas == ()
        assert result.evaluation.effect_intents == ()
        assert type(result.effect_receipt) is NoEffectReceipt
        assert result.effect_receipt.reason is NoEffectReason.ATTRIBUTED_ONLY
        assert adapter.requests == []
        assert (runtime.stores.world.revision, runtime.stores.r3_world_facts()) == before
    finally:
        runtime.stores.close()
