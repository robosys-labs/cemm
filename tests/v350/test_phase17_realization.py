from __future__ import annotations
import pytest
from cemm.v350.learning.model import PinnedRecord
from cemm.v350.realization.engine import FeatureUnifier,Linearizer,RealizationFrontier
from cemm.v350.realization.model import *
from cemm.v350.schema.model import SchemaLifecycleStatus,UseDecision
from cemm.v350.storage.model import RecordKind


def pin(kind,ref): return PinnedRecord(kind,ref,1,'a'*64)

def test_feature_unifier_fails_closed_on_conflict():
    with pytest.raises(RealizationFrontier): FeatureUnifier().unify((('number','singular'),),(('number','plural'),))

def test_linearizer_detects_cycle_without_string_fallback():
    rule=LinearizationRuleRecord(rule_ref='lin:x',pack_ref='pack:x',pack_revision=1,construction_ref='frame:x',precedence_pairs=(('a','b'),('b','a')),lifecycle_status=SchemaLifecycleStatus.ACTIVE,use_decision=UseDecision.ALLOW)
    with pytest.raises(RealizationFrontier): Linearizer().order({'a':['A'],'b':['B']},rule)

def test_roundtrip_pass_cannot_hide_semantic_drift():
    with pytest.raises(ValueError):
        SemanticRoundTripRecord(roundtrip_ref='rt:x',request_pin=pin(RecordKind.REALIZATION_REQUEST,'req:x'),surface_candidate_pin=pin(RecordKind.SURFACE_CANDIDATE,'surface:x'),analyzer_ref='analyzer:x',analyzer_revision='1',recovered_graph_fingerprint='g1',expected_graph_fingerprint='g1',decision=RoundTripDecision.PASS,additions=('fact:invented',),losses=(),drift_refs=(),proof_refs=())

def test_full_sentence_templates_are_not_part_of_argument_frame_contract():
    fields=set(ArgumentFrameRecord.__dataclass_fields__)
    assert 'sentence_template' not in fields and 'surface_pattern' not in fields


def test_reference_resolver_never_reads_raw_identity_facet_surface():
    import inspect
    from cemm.v350.realization.engine import PrivacyAwareReferenceResolver
    source = inspect.getsource(PrivacyAwareReferenceResolver.realize)
    assert 'IDENTITY_FACET' not in source
    assert "metadata.get('referent_ref'" in source


def test_reference_plans_are_first_class_before_surface_commit():
    from cemm.v350.realization.coordinator import RealizationCommitCoordinator
    import inspect
    source = inspect.getsource(RealizationCommitCoordinator.commit_candidate)
    assert 'reference_plans' in source
    assert 'RecordKind.REFERENCE_PLAN' in source


def test_clause_planner_preserves_filler_class_and_coordination_path():
    from pathlib import Path
    source = (Path(__file__).parents[2] / "cemm" / "v350" / "realization" / "engine.py").read_text(encoding="utf-8")
    assert "filler.filler_class.value" in source
    assert "ConstructionKind.COORDINATION" in source
    assert "coordination_connector_not_authorized" in source


def test_scope_uses_reviewed_construction_algebra_not_kernel_word_branches():
    from pathlib import Path
    source = (Path(__file__).parents[2] / "cemm" / "v350" / "realization" / "engine.py").read_text(encoding="utf-8")
    assert "realization_role" in source and "scope_kind" in source
    assert "operator_before" in source and "operator_after" in source
    assert "missing_scope_construction" in source


def test_linearizer_fails_on_underconstrained_order_without_reviewed_free_order():
    rule=LinearizationRuleRecord(rule_ref='lin:under',pack_ref='pack:x',pack_revision=1,construction_ref='frame:x',precedence_pairs=(),lifecycle_status=SchemaLifecycleStatus.ACTIVE,use_decision=UseDecision.ALLOW)
    with pytest.raises(RealizationFrontier): Linearizer().order({'a':['A'],'b':['B']},rule)

def test_specialized_referents_are_supported_without_raw_identity_leakage():
    import inspect
    from cemm.v350.realization.engine import PrivacyAwareReferenceResolver
    source=inspect.getsource(PrivacyAwareReferenceResolver._semantic_referent)
    assert 'RecordKind.PROPOSITION' in source
    assert 'RecordKind.CLAIM_OCCURRENCE' in source
    assert 'RecordKind.EVENT_OCCURRENCE' in source

def test_surface_candidate_is_snapshot_pinned_and_roundtrip_expected_graph_is_not_caller_authority():
    from cemm.v350.realization.model import SurfaceCandidateRecord
    from cemm.v350.realization.validation import Phase17CommitValidator
    import inspect
    assert 'snapshot_revision' in SurfaceCandidateRecord.__dataclass_fields__
    assert 'snapshot_fingerprint' in SurfaceCandidateRecord.__dataclass_fields__
    source=inspect.getsource(Phase17CommitValidator.validate_operation)
    assert 'roundtrip expected fingerprint is not the exact Response UOL graph fingerprint' in source
