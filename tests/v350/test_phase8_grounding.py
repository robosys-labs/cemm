from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.grounding import (
    CandidateOrigin,
    ClaimGroundingCompiler,
    ClaimGroundingError,
    DiscourseAnchor,
    GroundingCandidate,
    GroundingCandidateProvider,
    GroundingConstraint,
    GroundingConstraintKind,
    GroundingFactor,
    GroundingFactorKind,
    IdentityProposalEngine,
    JointGrounder,
    JointGroundingSolver,
    MentionHypothesis,
    MentionTargetClass,
    MultimodalTrack,
    ProvisionalReferentPlanner,
    Span,
    SystemOutputAnchor,
)
from cemm.v350.language import FormLatticeAnalyzer
from cemm.v350.schema.model import StorageKind
from cemm.v350.storage import (
    EvidenceRecord,
    GraphPatch,
    IdentityFacetRecord,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SemanticStore,
    encode_record,
    record_ref,
    record_revision,
)
from cemm.v350.uol.model import IdentityStatus, Referent

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"


def operation(kind, record):
    return PatchOperation(
        operation_ref=f"operation:phase8:{kind.value}:{record_ref(kind, record)}",
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=kind,
        target_ref=record_ref(kind, record),
        record_revision=record_revision(kind, record),
        payload=encode_record(kind, record),
        reason="phase-8 grounding fixture",
    )


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    directory = tmp_path_factory.mktemp("phase8")
    first = DeterministicSQLiteCompiler().compile(SOURCE, directory / "a.sqlite", make_read_only=False)
    second = DeterministicSQLiteCompiler().compile(SOURCE, directory / "b.sqlite", make_read_only=False)
    assert first.output_path.read_bytes() == second.output_path.read_bytes()
    return first


@pytest.fixture(scope="module")
def store(compiled):
    value = SemanticStore(":memory:", boot_path=compiled.output_path)
    evidence = EvidenceRecord(
        evidence_ref="evidence:phase8:fixtures",
        source_ref="test:phase8",
        confidence=1.0,
        lineage_ref="lineage:phase8:fixtures",
    )
    referents = (
        Referent("referent:alex:a", identity_status=IdentityStatus.RESOLVED,
                 type_refs=("type:software_agent",), context_refs=("actual",),
                 identity_facet_refs=("identity:alex:a",)),
        Referent("referent:alex:b", identity_status=IdentityStatus.RESOLVED,
                 type_refs=("type:software_agent",), context_refs=("actual",),
                 identity_facet_refs=("identity:alex:b",)),
        Referent("referent:event:incident", storage_kind=StorageKind.EVENT_OCCURRENCE,
                 identity_status=IdentityStatus.RESOLVED, type_refs=("type:event_occurrence",),
                 context_refs=("actual",), identity_facet_refs=("identity:event:incident",)),
        Referent("referent:state:condition", storage_kind=StorageKind.STATE_OCCURRENCE,
                 identity_status=IdentityStatus.RESOLVED, type_refs=("type:state_occurrence",),
                 context_refs=("actual",), identity_facet_refs=("identity:state:condition",)),
        Referent("referent:proposition:proposal", storage_kind=StorageKind.PROPOSITION,
                 identity_status=IdentityStatus.RESOLVED, type_refs=("type:proposition",),
                 context_refs=("actual",), identity_facet_refs=("identity:proposition:proposal",)),
        Referent("referent:timed", identity_status=IdentityStatus.RESOLVED,
                 type_refs=("type:referent",), context_refs=("actual",),
                 valid_time_ref="time:one", identity_facet_refs=("identity:timed",)),
    )
    facets = (
        IdentityFacetRecord("identity:alex:a", "referent:alex:a", "facet:identity", "alex",
                            evidence_refs=(evidence.evidence_ref,)),
        IdentityFacetRecord("identity:alex:b", "referent:alex:b", "facet:identity", "alex",
                            evidence_refs=(evidence.evidence_ref,)),
        IdentityFacetRecord("identity:event:incident", "referent:event:incident", "facet:identity", "incident",
                            evidence_refs=(evidence.evidence_ref,)),
        IdentityFacetRecord("identity:state:condition", "referent:state:condition", "facet:identity", "condition",
                            evidence_refs=(evidence.evidence_ref,)),
        IdentityFacetRecord("identity:timed", "referent:timed", "facet:identity", "timed",
                            evidence_refs=(evidence.evidence_ref,)),
        IdentityFacetRecord("identity:proposition:proposal", "referent:proposition:proposal",
                            "facet:identity", "proposal", evidence_refs=(evidence.evidence_ref,)),
    )
    result = value.apply_patch(GraphPatch(
        patch_ref="patch:phase8:fixtures",
        context_ref="actual",
        scope_ref="phase8-test",
        source_ref="test",
        permission_ref="internal",
        operations=(operation(RecordKind.EVIDENCE, evidence),
                    *(operation(RecordKind.REFERENT, item) for item in referents),
                    *(operation(RecordKind.IDENTITY_FACET, item) for item in facets)),
        expected_store_revision=value.revision,
    ))
    assert result.committed, result.errors
    yield value
    value.close()


@pytest.fixture(scope="module")
def analyzer(store):
    return FormLatticeAnalyzer(store.repositories.language.registry())


@pytest.fixture(scope="module")
def grounder(store, analyzer):
    return JointGrounder(store, analyzer)


def mention(ref, surface, *, target=MentionTargetClass.REFERENT, types=(), storage=(), time_ref=None,
            descriptions=(), metadata=None):
    return MentionHypothesis(
        mention_ref=ref,
        source_ref="source:phase8:test",
        span=Span(0, len(surface)),
        surface=surface,
        normalized_surface=surface.casefold(),
        target_class=target,
        expected_type_refs=types,
        expected_storage_kinds=storage,
        description_application_refs=descriptions,
        context_ref="actual",
        time_ref=time_ref,
        evidence_refs=(f"evidence:{ref}",),
        metadata={} if metadata is None else metadata,
    )


def test_self_deictic_resolves_only_self(grounder) -> None:
    anchor = DiscourseAnchor(
        "anchor:self", "referent:self", "actual", 1.0, 0,
        role_refs=("self", "speaker"), evidence_refs=("evidence:anchor:self",),
    )
    _, result = grounder.ground_text(
        "I", source_ref="utterance:self", context_ref="actual", discourse_anchors=(anchor,)
    )
    assert result.selected is not None
    assert dict(result.selected.mention_to_target) == {result.mentions[0].mention_ref: "referent:self"}
    assert {item.target_ref for item in result.candidates} == {"referent:self"}


def test_unknown_name_remains_provisional_frontier_not_resolved(grounder) -> None:
    _, result = grounder.ground_text("UnknownName", source_ref="utterance:unknown", context_ref="actual")
    assert result.selected is None
    assert result.frontier_refs
    assert result.metadata["provisional_frontier_only"] is True
    assert all(item.provisional for item in result.candidates)
    assert not any(item.origin == CandidateOrigin.STORE for item in result.candidates)


def test_same_name_candidates_preserve_identity_ambiguity(grounder) -> None:
    _, result = grounder.ground_text("Alex", source_ref="utterance:alex", context_ref="actual")
    resolved = [item for item in result.candidates if item.origin == CandidateOrigin.STORE]
    assert {item.target_ref for item in resolved} == {"referent:alex:a", "referent:alex:b"}
    assert result.selected is None
    assert result.ambiguous_mention_refs == (result.mentions[0].mention_ref,)


def test_discourse_anchor_disambiguates_anaphoric_and_addressee_grounding(grounder) -> None:
    anchor = DiscourseAnchor(
        anchor_ref="anchor:alex:a",
        referent_ref="referent:alex:a",
        context_ref="actual",
        salience=1.0,
        turn_index=3,
        role_refs=("addressee", "audience"),
        type_refs=("type:software_agent",),
        evidence_refs=("evidence:anchor:alex:a",),
    )
    _, result = grounder.ground_text("you", source_ref="utterance:addressee", context_ref="actual", discourse_anchors=(anchor,))
    assert result.selected is not None
    assert tuple(dict(result.selected.mention_to_target).values()) == ("referent:alex:a",)
    assert not {item.target_ref for item in result.candidates if item.origin == CandidateOrigin.STORE} - {"referent:alex:a"}


def test_description_application_is_a_hard_grounding_factor(store) -> None:
    provider = GroundingCandidateProvider(store)
    item = mention("mention:described-self", "assistant", descriptions=("application:self:name",))
    candidates = provider.generate((item,), allow_provisional=False)
    assert {candidate.target_ref for candidate in candidates} == {"referent:self"}
    assert any(factor.factor_kind == GroundingFactorKind.DESCRIPTION for factor in candidates[0].factors)


@pytest.mark.parametrize(
    ("surface", "target", "storage_kind", "expected_ref"),
    [
        ("incident", MentionTargetClass.EVENT, StorageKind.EVENT_OCCURRENCE, "referent:event:incident"),
        ("condition", MentionTargetClass.STATE, StorageKind.STATE_OCCURRENCE, "referent:state:condition"),
        ("proposal", MentionTargetClass.PROPOSITION, StorageKind.PROPOSITION,
         "referent:proposition:proposal"),
    ],
)
def test_event_state_and_proposition_referents_ground_by_typed_identity(store, surface, target, storage_kind, expected_ref) -> None:
    candidate = GroundingCandidateProvider(store).generate((mention(
        f"mention:{surface}", surface, target=target, storage=(storage_kind,)
    ),), allow_provisional=False)
    assert {item.target_ref for item in candidate} == {expected_ref}
    assert all(item.storage_kind == storage_kind for item in candidate)


def test_schema_topics_pin_exact_active_schema_revision(store) -> None:
    item = mention(
        "mention:schema:observe", "observe", target=MentionTargetClass.SCHEMA_TOPIC,
        storage=(StorageKind.SCHEMA_TOPIC,), metadata={"schema_target_refs": ("event:observe",)},
    )
    candidates = GroundingCandidateProvider(store).generate((item,), allow_provisional=False)
    exact = next(candidate for candidate in candidates if candidate.target_ref == "event:observe")
    assert exact.origin == CandidateOrigin.SCHEMA
    assert exact.metadata == {"schema_revision": 1, "schema_class": "event"}


def test_demonstrative_jointly_considers_multimodal_and_system_output_only(grounder) -> None:
    track = MultimodalTrack(
        track_ref="track:visible-object",
        modality="vision",
        context_ref="actual",
        type_refs=("type:physical_entity",),
        salience=0.95,
        evidence_refs=("evidence:vision",),
    )
    output = SystemOutputAnchor(
        output_ref="output:previous",
        context_ref="actual",
        content_referent_refs=("referent:self",),
        turn_index=2,
        evidence_refs=("evidence:output",),
    )
    _, result = grounder.ground_text(
        "this", source_ref="utterance:this", context_ref="actual",
        multimodal_tracks=(track,), system_outputs=(output,),
    )
    assert {item.origin for item in result.candidates} >= {CandidateOrigin.MULTIMODAL, CandidateOrigin.SYSTEM_OUTPUT}
    assert not any(item.origin == CandidateOrigin.STORE for item in result.candidates)
    multimodal = next(item for item in result.candidates if item.origin == CandidateOrigin.MULTIMODAL)
    assert {"type:physical_entity", "type:concrete", "type:referent"} <= set(multimodal.type_refs)
    assert result.assignments


def test_time_constraints_reject_incompatible_referent(store) -> None:
    provider = GroundingCandidateProvider(store)
    wrong = provider.generate((mention("mention:time:wrong", "timed", time_ref="time:two", metadata={"unresolved_form": True}),), allow_provisional=False)
    right = provider.generate((mention("mention:time:right", "timed", time_ref="time:one", metadata={"unresolved_form": True}),), allow_provisional=False)
    assert not wrong
    assert {item.target_ref for item in right} == {"referent:timed"}
    assert any(factor.factor_kind == GroundingFactorKind.TIME for factor in right[0].factors)


def _candidate(mention_ref, target_ref, score=1.0):
    factor = GroundingFactor(
        factor_ref=f"factor:{mention_ref}:{target_ref}",
        factor_kind=GroundingFactorKind.IDENTITY,
        score=score,
        evidence_refs=(f"evidence:{mention_ref}:{target_ref}",),
        reason="test identity",
    )
    return GroundingCandidate(
        candidate_ref=f"candidate:{mention_ref}:{target_ref}",
        mention_ref=mention_ref,
        target_ref=target_ref,
        origin=CandidateOrigin.STORE,
        storage_kind=StorageKind.ORDINARY,
        type_refs=("type:referent",),
        context_refs=("actual",),
        factors=(factor,),
    )


def test_joint_solver_enforces_coreference_and_distinctness() -> None:
    left = mention("mention:left", "it")
    right = mention("mention:right", "it")
    candidates = (
        _candidate(left.mention_ref, "referent:a", 2.0),
        _candidate(left.mention_ref, "referent:b", 1.8),
        _candidate(right.mention_ref, "referent:a", 1.0),
        _candidate(right.mention_ref, "referent:b", 2.0),
    )
    solver = JointGroundingSolver()
    corefer = GroundingConstraint("constraint:corefer", GroundingConstraintKind.COREFER,
                                  (left.mention_ref, right.mention_ref), required=True,
                                  evidence_refs=("evidence:corefer",))
    coref_result = solver.solve((left, right), candidates, constraints=(corefer,))
    assert all(len(set(dict(item.mention_to_target).values())) == 1 for item in coref_result.assignments)
    distinct = GroundingConstraint("constraint:distinct", GroundingConstraintKind.DISTINCT,
                                   (left.mention_ref, right.mention_ref), required=True,
                                   evidence_refs=("evidence:distinct",))
    distinct_result = solver.solve((left, right), candidates, constraints=(distinct,))
    assert all(len(set(dict(item.mention_to_target).values())) == 2 for item in distinct_result.assignments)


def test_lexical_event_predicate_introduces_provisional_occurrence_not_arbitrary_history(grounder) -> None:
    _, grounding = grounder.ground_text("say", source_ref="utterance:event-introduction", context_ref="actual")
    event = next(item for item in grounding.mentions if item.target_class == MentionTargetClass.EVENT)
    candidates = [item for item in grounding.candidates if item.mention_ref == event.mention_ref]
    assert candidates
    assert all(item.origin == CandidateOrigin.PROVISIONAL for item in candidates)
    assert all(item.storage_kind == StorageKind.EVENT_OCCURRENCE for item in candidates)
    assert all(item.metadata["introduced_by_schema_refs"] == ("event:claim",) for item in candidates)
    assert not any(item.target_ref == "referent:event:incident" for item in candidates)
    assert grounding.selected is None
    assert event.mention_ref in grounding.unresolved_mention_refs


def test_claim_source_audience_and_attributed_context_are_preserved_without_admission(grounder) -> None:
    addressee = DiscourseAnchor(
        "anchor:claim:addressee", "referent:alex:a", "actual", 1.0, 4,
        role_refs=("addressee", "audience"), type_refs=("type:software_agent",),
        evidence_refs=("evidence:claim:addressee",),
    )
    self_anchor = DiscourseAnchor(
        "anchor:claim:self", "referent:self", "actual", 1.0, 4,
        role_refs=("self", "speaker"), evidence_refs=("evidence:claim:self",),
    )
    _, grounding = grounder.ground_text(
        "I say you", source_ref="utterance:claim", context_ref="actual",
        discourse_anchors=(addressee, self_anchor),
    )
    claim = next(item for item in grounding.mentions if item.target_class == MentionTargetClass.EVENT)
    source = next(item for item in grounding.mentions if item.surface == "I")
    audience = next(item for item in grounding.mentions if item.target_class == MentionTargetClass.AUDIENCE)
    assert grounding.assignments
    compiled = ClaimGroundingCompiler(grounder.store).compile(
        grounding,
        claim_mention_ref=claim.mention_ref,
        proposition_ref="referent:foundation:proposition-example",
        source_mention_ref=source.mention_ref,
        audience_mention_refs=(audience.mention_ref,),
        source_context_ref="actual",
        reported_context_ref="context:reported:claim",
        assignment_ref=grounding.assignments[0].assignment_ref,
    )
    assert compiled.source_ref == "referent:self"
    assert compiled.audience_refs == ("referent:alex:a",)
    assert compiled.admission_refs == ()
    assert compiled.confidence <= 0.49  # the claim occurrence is still provisional
    with pytest.raises(ValueError, match="cannot admit"):
        replace(compiled, admission_refs=("knowledge:forbidden",))


def test_claim_compiler_rejects_role_and_storage_category_errors(grounder) -> None:
    addressee = DiscourseAnchor(
        "anchor:claim:validation", "referent:alex:a", "actual", 1.0, 5,
        role_refs=("addressee", "audience"), type_refs=("type:software_agent",),
        evidence_refs=("evidence:claim:validation",),
    )
    self_anchor = DiscourseAnchor(
        "anchor:claim:validation:self", "referent:self", "actual", 1.0, 5,
        role_refs=("self", "speaker"), evidence_refs=("evidence:claim:validation:self",),
    )
    _, grounding = grounder.ground_text(
        "I say you", source_ref="utterance:claim:validation", context_ref="actual",
        discourse_anchors=(addressee, self_anchor),
    )
    claim = next(item for item in grounding.mentions if item.target_class == MentionTargetClass.EVENT)
    source = next(item for item in grounding.mentions if item.surface == "I")
    audience = next(item for item in grounding.mentions if item.target_class == MentionTargetClass.AUDIENCE)
    assignment_ref = grounding.assignments[0].assignment_ref
    compiler = ClaimGroundingCompiler(grounder.store)

    with pytest.raises(ClaimGroundingError, match="event-occurrence storage"):
        compiler.compile(
            grounding, claim_mention_ref=source.mention_ref,
            proposition_ref="referent:foundation:proposition-example",
            source_mention_ref=source.mention_ref, source_context_ref="actual",
            reported_context_ref="context:reported:invalid-claim",
            assignment_ref=assignment_ref,
        )
    with pytest.raises(ClaimGroundingError, match="claim source"):
        compiler.compile(
            grounding, claim_mention_ref=claim.mention_ref,
            proposition_ref="referent:foundation:proposition-example",
            source_mention_ref=claim.mention_ref, source_context_ref="actual",
            reported_context_ref="context:reported:invalid-source",
            assignment_ref=assignment_ref,
        )
    with pytest.raises(ClaimGroundingError, match="claim audience"):
        compiler.compile(
            grounding, claim_mention_ref=claim.mention_ref,
            proposition_ref="referent:foundation:proposition-example",
            source_mention_ref=source.mention_ref, audience_mention_refs=(claim.mention_ref,),
            source_context_ref="actual",
            reported_context_ref="context:reported:invalid-audience",
            assignment_ref=assignment_ref,
        )


def test_claim_compiler_requires_explicit_assignment_when_ambiguous(grounder) -> None:
    self_anchor = DiscourseAnchor(
        "anchor:ambiguous-claim:self", "referent:self", "actual", 1.0, 6,
        role_refs=("self", "speaker"), evidence_refs=("evidence:ambiguous-claim:self",),
    )
    _, grounding = grounder.ground_text(
        "Alex say I", source_ref="utterance:ambiguous-claim", context_ref="actual",
        discourse_anchors=(self_anchor,),
    )
    claim = next(item for item in grounding.mentions if item.target_class == MentionTargetClass.EVENT)
    source = next(item for item in grounding.mentions if item.surface == "Alex")
    with pytest.raises(ClaimGroundingError, match="explicit assignment"):
        ClaimGroundingCompiler(grounder.store).compile(
            grounding,
            claim_mention_ref=claim.mention_ref,
            proposition_ref="referent:foundation:proposition-example",
            source_mention_ref=source.mention_ref,
            source_context_ref="actual",
            reported_context_ref="context:reported:ambiguous",
        )


def test_provisional_referent_is_reviewable_patch_not_automatic_mutation(store, grounder) -> None:
    _, result = grounder.ground_text("NewEntity", source_ref="utterance:new-entity", context_ref="actual")
    mention_item = result.mentions[0]
    frontier = result.frontier_refs[0]
    planner = ProvisionalReferentPlanner()
    proposal = planner.propose(
        mention_item, referent_ref=frontier, type_refs=("type:referent",),
        storage_kind=StorageKind.ORDINARY,
    )
    graph_patch = planner.graph_patch(
        proposal, source_ref="utterance:new-entity", expected_store_revision=store.revision,
        store=store,
    )
    assert store.get_record(RecordKind.REFERENT, frontier) is None
    assert {item.record_kind for item in graph_patch.operations} == {
        RecordKind.EVIDENCE, RecordKind.REFERENT, RecordKind.IDENTITY_FACET
    }
    assert not {RecordKind.KNOWLEDGE, RecordKind.CLAIM_RECORD, RecordKind.CLAIM_OCCURRENCE}.intersection(
        item.record_kind for item in graph_patch.operations
    )
    committed = store.apply_patch(graph_patch)
    assert committed.committed, committed.errors
    assert store.repositories.referents.require(frontier).payload.identity_status == IdentityStatus.PROVISIONAL


def test_identity_merge_and_split_are_review_only_proposals(grounder) -> None:
    _, result = grounder.ground_text("Alex", source_ref="utterance:identity-review", context_ref="actual")
    engine = IdentityProposalEngine()
    merges = engine.merge_proposals(result.candidates, context_ref="actual")
    assert merges
    assert all(item.requires_review for item in merges)
    split = engine.split_proposal(
        referent_ref="referent:alex:a",
        partition_keys=("context:work", "context:home"),
        context_ref="actual",
        conflicting_factor_refs=("factor:identity-conflict",),
        evidence_refs=("evidence:identity-conflict",),
        confidence=0.8,
    )
    assert split.requires_review is True
    assert split.partition_keys == ("context:home", "context:work")


def test_grounding_is_deterministic(grounder) -> None:
    first = grounder.ground_text("Alex", source_ref="utterance:deterministic", context_ref="actual")[1]
    second = grounder.ground_text("Alex", source_ref="utterance:deterministic", context_ref="actual")[1]
    assert first == second
    assert first.fingerprint == second.fingerprint


def test_grounding_inputs_and_constraints_require_evidence() -> None:
    with pytest.raises(ValueError, match="mention hypothesis requires evidence"):
        MentionHypothesis(
            mention_ref="mention:no-evidence",
            source_ref="source:test",
            span=Span(0, 1),
            surface="x",
            normalized_surface="x",
        )
    with pytest.raises(ValueError, match="grounding constraint requires evidence"):
        GroundingConstraint(
            constraint_ref="constraint:no-evidence",
            constraint_kind=GroundingConstraintKind.TYPE_COMPATIBLE,
            mention_refs=("mention:a",),
        )


def test_solver_does_not_emit_empty_assignment_for_unresolved_mentions() -> None:
    unresolved = mention("mention:no-candidate", "nobody")
    result = JointGroundingSolver().solve((unresolved,), ())
    assert result.assignments == ()
    assert result.selected is None
    assert result.unresolved_mention_refs == (unresolved.mention_ref,)


def test_all_provisional_alternatives_remain_learning_frontiers() -> None:
    item = mention("mention:frontier", "novel")
    candidates = tuple(
        GroundingCandidate(
            candidate_ref=f"candidate:frontier:{suffix}",
            mention_ref=item.mention_ref,
            target_ref=f"referent:provisional:{suffix}",
            origin=CandidateOrigin.PROVISIONAL,
            storage_kind=StorageKind.ORDINARY,
            type_refs=("type:referent",),
            context_refs=("actual",),
            factors=(GroundingFactor(
                factor_ref=f"factor:frontier:{suffix}",
                factor_kind=GroundingFactorKind.PROVISIONAL,
                score=0.5,
                evidence_refs=(f"evidence:frontier:{suffix}",),
                reason="candidate learning frontier",
            ),),
            provisional=True,
        )
        for suffix in ("a", "b")
    )
    result = JointGroundingSolver().solve((item,), candidates)
    assert result.selected is None
    assert set(result.frontier_refs) == {
        "referent:provisional:a",
        "referent:provisional:b",
    }
    assert result.metadata["provisional_frontier_only"] is True


def test_identity_proposals_cannot_disable_review_requirement() -> None:
    from cemm.v350.grounding import IdentityMergeProposal, IdentitySplitProposal

    with pytest.raises(ValueError, match="must require review"):
        IdentityMergeProposal(
            proposal_ref="proposal:merge:no-review",
            left_ref="referent:a",
            right_ref="referent:b",
            context_ref="actual",
            confidence=0.8,
            evidence_refs=("evidence:merge",),
            supporting_factor_refs=("factor:merge",),
            requires_review=False,
        )
    with pytest.raises(ValueError, match="must require review"):
        IdentitySplitProposal(
            proposal_ref="proposal:split:no-review",
            referent_ref="referent:a",
            partition_keys=("partition:a", "partition:b"),
            context_ref="actual",
            confidence=0.8,
            evidence_refs=("evidence:split",),
            conflicting_factor_refs=("factor:split",),
            requires_review=False,
        )


def test_system_output_preserves_both_targets_and_content_referents(store) -> None:
    item = mention(
        "mention:system-output:both",
        "that",
        target=MentionTargetClass.SYSTEM_OUTPUT,
        metadata={"grounding_channels": ("system_output",)},
    )
    output = SystemOutputAnchor(
        output_ref="output:target-and-content",
        context_ref="actual",
        content_referent_refs=("referent:alex:b",),
        target_refs=("referent:alex:a",),
        turn_index=5,
        evidence_refs=("evidence:output:target-and-content",),
    )
    candidates = GroundingCandidateProvider(store).generate(
        (item,), system_outputs=(output,), allow_provisional=False,
    )
    assert {candidate.target_ref for candidate in candidates} == {
        "referent:alex:a",
        "referent:alex:b",
    }
    metadata = {
        candidate.target_ref: next(
            factor.metadata for factor in candidate.factors
            if factor.factor_kind == GroundingFactorKind.SYSTEM_OUTPUT
        )
        for candidate in candidates
    }
    assert metadata["referent:alex:a"]["is_target"] is True
    assert metadata["referent:alex:b"]["is_target"] is False
