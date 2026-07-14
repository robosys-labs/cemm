"""Phase 1 gate tests: canonical immutable model and fingerprints.

Gates:
- no new canonical semantic object family
- records are immutable and serializable
- content hashes/fingerprints are stable
- historical schema revisions remain resolvable
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import get_type_hints

import pytest

from cemm.kernel.model.refs import Ref, FrozenMap
from cemm.kernel.model.identity import (
    Scope, ScopeLevel, Provenance, Permission, PermissionScope,
    RetentionPolicy, TimeExtent, SemanticIdentity,
    AssessmentEnvironmentFingerprint,
)
from cemm.kernel.model.signal import SignalEnvelope
from cemm.kernel.model.surface import SurfaceSpan, LexicalFormRef, KindHypothesis
from cemm.kernel.model.referent import Referent
from cemm.kernel.model.value import Value
from cemm.kernel.model.role_binding import RoleBinding, OpenPort, Constraint
from cemm.kernel.model.predication import Predication, AspectProfile
from cemm.kernel.model.proposition import Proposition, ModalQualifier
from cemm.kernel.model.context_frame import ContextFrame
from cemm.kernel.model.evidence import EvidenceRecord
from cemm.kernel.model.structural_link import StructuralLink, STRUCTURAL_LINK_TYPES
from cemm.kernel.model.semantic_graph import SemanticGraph
from cemm.kernel.model.workspace import WorkspaceEntry
from cemm.kernel.model.epistemic import EpistemicAssessment
from cemm.kernel.model.capability import CapabilityAssessment, ConditionResult
from cemm.kernel.model.gap import GapRecord, ProbePlan, LearningBudget
from cemm.kernel.model.goal import GoalRecord
from cemm.kernel.model.plan import PlanRecord, OperationInstance, OperationDependency, CostEstimate, RiskEstimate
from cemm.kernel.model.execution import ExecutionLedger, OperationOutcome, PredictionError, TypedFailure
from cemm.kernel.model.learning import (
    LearningTransaction, ReplayWorkItem, DerivedArtifactProvenance,
    SchemaHypothesis, CompetencyResult, ReplayResult,
)
from cemm.kernel.model.message import SemanticMessagePlan, MessageContentItem, RhetoricalRelation
from cemm.kernel.model.mutation import MutationSet, MutationOperation, CommitOutcome, CommitOperationResult
from cemm.kernel.model.failure import TypedFailure as FailureTypedFailure
from cemm.kernel.model.trace import CycleTrace, SemanticTrace

from cemm.kernel.schema.envelope import SchemaEnvelope, SchemaContribution, SchemaDependency
from cemm.kernel.schema.grounding_spec import SemanticPattern, GroundingSpecification
from cemm.kernel.schema.validation import CompetencyCase
from cemm.kernel.schema.use_profile import SchemaGroundingAssessment, SchemaUseProfile
from cemm.kernel.schema.dependency import DependencyNode, DependencyEdge, DependencyClosure, CycleClass
from cemm.kernel.schema.versioning import RevisionEntry, SchemaStatus, is_retention_required
from cemm.kernel.schema.role import RoleSchema
from cemm.kernel.schema.predicate import PredicateSchema
from cemm.kernel.schema.operation import OperationSchema, CapabilitySchema
from cemm.kernel.schema.state_dimension import StateDimensionSchema
from cemm.kernel.schema.entity_kind import EntityKindSchema
from cemm.kernel.schema.context import ContextSchema
from cemm.kernel.schema.lexeme import LexemeSenseSchema
from cemm.kernel.schema.construction import ConstructionSchema
from cemm.kernel.schema.realization import RealizationSchema
from cemm.kernel.schema.policy import PolicySchema
from cemm.kernel.schema.metalanguage import MetalanguageSchema
from cemm.kernel.schema.activation import activate_single, activate_cluster, ActivationStatus


# ── Gate: records are immutable ────────────────────────────────────


IMMUTABLE_RECORD_TYPES = [
    Ref, Scope, Provenance, Permission, TimeExtent,
    SemanticIdentity, AssessmentEnvironmentFingerprint,
    SignalEnvelope, SurfaceSpan, LexicalFormRef, KindHypothesis,
    Referent, Value, RoleBinding, OpenPort, Constraint,
    Predication, AspectProfile, Proposition, ModalQualifier,
    ContextFrame, EvidenceRecord, StructuralLink, SemanticGraph,
    WorkspaceEntry, EpistemicAssessment, CapabilityAssessment, ConditionResult,
    GapRecord, ProbePlan, LearningBudget, GoalRecord,
    PlanRecord, OperationInstance, OperationDependency, CostEstimate, RiskEstimate,
    ExecutionLedger, OperationOutcome, PredictionError, TypedFailure,
    LearningTransaction, ReplayWorkItem, DerivedArtifactProvenance,
    SchemaHypothesis, CompetencyResult, ReplayResult,
    SemanticMessagePlan, MessageContentItem, RhetoricalRelation,
    MutationSet, MutationOperation, CommitOutcome, CommitOperationResult,
    FailureTypedFailure, CycleTrace, SemanticTrace,
    SchemaEnvelope, SchemaContribution, SchemaDependency,
    SemanticPattern, GroundingSpecification, CompetencyCase,
    SchemaGroundingAssessment, SchemaUseProfile,
    DependencyNode, DependencyEdge, DependencyClosure,
    RevisionEntry,
    RoleSchema, PredicateSchema, OperationSchema, CapabilitySchema,
    StateDimensionSchema, EntityKindSchema, ContextSchema,
    LexemeSenseSchema, ConstructionSchema, RealizationSchema,
    PolicySchema, MetalanguageSchema,
]


@pytest.mark.parametrize("cls", IMMUTABLE_RECORD_TYPES)
def test_records_are_frozen(cls):
    """All canonical records must be frozen dataclasses."""
    assert is_dataclass(cls), f"{cls.__name__} is not a dataclass"
    # Check frozen=True in the dataclass __dataclass_params__
    params = getattr(cls, "__dataclass_params__", None)
    assert params is not None, f"{cls.__name__} has no __dataclass_params__"
    assert params.frozen, f"{cls.__name__} is not frozen"


def test_ref_is_generic():
    """Ref must be generic and opaque."""
    r: Ref[str] = Ref(id="test:123")
    assert r.id == "test:123"
    assert str(r) == "test:123"


def test_frozenmap_is_hashable():
    """FrozenMap must be immutable and hashable."""
    fm = FrozenMap({"a": 1, "b": 2})
    assert fm["a"] == 1
    assert len(fm) == 2
    h1 = hash(fm)
    fm2 = FrozenMap({"a": 1, "b": 2})
    assert hash(fm2) == h1
    assert fm == fm2
    with pytest.raises(KeyError):
        _ = fm["nonexistent"]


# ── Gate: no new canonical semantic object family ──────────────────


CANONICAL_SEMANTIC_OBJECTS = {
    "Referent", "Value", "Predication", "Proposition",
    "ContextFrame", "EvidenceRecord", "StructuralLink",
}

SCHEMA_RECORDS = {
    "SchemaEnvelope", "SchemaContribution", "SchemaDependency",
    "SemanticPattern", "GroundingSpecification", "CompetencyCase",
    "SchemaGroundingAssessment", "SchemaUseProfile",
    "RoleSchema", "PredicateSchema", "StateDimensionSchema",
    "OperationSchema", "CapabilitySchema",
    "LexemeSenseSchema", "ConstructionSchema",
    "ContextSchema", "RealizationSchema", "PolicySchema",
    "EntityKindSchema", "MetalanguageSchema",
}

CONTROL_RECORDS = {
    "WorkspaceEntry", "EpistemicAssessment", "CapabilityAssessment",
    "GapRecord", "GoalRecord", "PlanRecord", "OperationInstance",
    "ExecutionLedger", "LearningTransaction", "SemanticMessagePlan",
    "MutationSet", "CommitOutcome", "ReplayWorkItem",
    "DerivedArtifactProvenance",
}


def test_no_extra_canonical_object_families():
    """The canonical semantic object families must be exactly the specified set."""
    import cemm.kernel.model.referent as m_ref
    import cemm.kernel.model.value as m_val
    import cemm.kernel.model.predication as m_pred
    import cemm.kernel.model.proposition as m_prop
    import cemm.kernel.model.context_frame as m_ctx
    import cemm.kernel.model.evidence as m_ev
    import cemm.kernel.model.structural_link as m_sl

    found = set()
    for mod in [m_ref, m_val, m_pred, m_prop, m_ctx, m_ev, m_sl]:
        for name in dir(mod):
            obj = getattr(mod, name)
            if is_dataclass(obj) and getattr(obj, "__dataclass_params__", None) and obj.__module__ == mod.__name__:
                found.add(name)

    extra = found - CANONICAL_SEMANTIC_OBJECTS - {"AspectProfile", "ModalQualifier"}
    # AspectProfile and ModalQualifier are sub-records, not new families
    assert not extra, f"Unexpected canonical object families: {extra}"


# ── Gate: StructuralLink rejects semantic relations ────────────────


def test_structural_link_rejects_semantic_relations():
    """StructuralLink must reject semantic relation types like is_a, causes."""
    with pytest.raises(ValueError, match="Semantic relations"):
        StructuralLink(id="bad", link_type="is_a", source_ref="a", target_ref="b")


def test_structural_link_accepts_structural_types():
    """StructuralLink must accept structural types like has_role, refers_to."""
    link = StructuralLink(id="ok", link_type="has_role", source_ref="a", target_ref="b")
    assert link.link_type == "has_role"


def test_structural_link_vocabulary():
    """The structural link vocabulary must be exactly the canonical set."""
    expected = frozenset({
        "has_role", "instantiates", "refers_to", "grounded_by",
        "scoped_by", "supported_by", "opposed_by", "derived_from",
        "depends_on", "co_refers_with",
    })
    assert STRUCTURAL_LINK_TYPES == expected


# ── Gate: content hashes/fingerprints are stable ───────────────────


def test_assessment_fingerprint_stable():
    """AssessmentEnvironmentFingerprint must produce stable hashes."""
    fp1 = AssessmentEnvironmentFingerprint(
        schema_store_revision=1,
        dependency_revision_hash="abc",
        grounding_policy_version="v1",
        competency_suite_hash="cs1",
        kernel_foundation_version="kf1",
        type_registry_version="tr1",
        inference_policy_version="ip1",
        truth_maintenance_version="tm1",
        adapter_contract_hash="ac1",
        context_scope_policy_version="cs1",
    )
    fp2 = AssessmentEnvironmentFingerprint(
        schema_store_revision=1,
        dependency_revision_hash="abc",
        grounding_policy_version="v1",
        competency_suite_hash="cs1",
        kernel_foundation_version="kf1",
        type_registry_version="tr1",
        inference_policy_version="ip1",
        truth_maintenance_version="tm1",
        adapter_contract_hash="ac1",
        context_scope_policy_version="cs1",
    )
    assert hash(fp1) == hash(fp2)
    assert fp1 == fp2


def test_assessment_fingerprint_changes_on_revision():
    """Different store revisions must produce different fingerprints."""
    fp1 = AssessmentEnvironmentFingerprint(
        schema_store_revision=1,
        dependency_revision_hash="abc",
        grounding_policy_version="v1",
        competency_suite_hash="cs1",
        kernel_foundation_version="kf1",
        type_registry_version="tr1",
        inference_policy_version="ip1",
        truth_maintenance_version="tm1",
        adapter_contract_hash="ac1",
        context_scope_policy_version="cs1",
    )
    fp2 = AssessmentEnvironmentFingerprint(
        schema_store_revision=2,
        dependency_revision_hash="abc",
        grounding_policy_version="v1",
        competency_suite_hash="cs1",
        kernel_foundation_version="kf1",
        type_registry_version="tr1",
        inference_policy_version="ip1",
        truth_maintenance_version="tm1",
        adapter_contract_hash="ac1",
        context_scope_policy_version="cs1",
    )
    assert hash(fp1) != hash(fp2)


# ── Gate: historical schema revisions remain resolvable ────────────


def test_revision_retention_for_propositions():
    """Revisions bound to propositions must be retained."""
    entry = RevisionEntry(
        record_id="schema:engineer:v1",
        semantic_key="engineer",
        version=1,
        status=SchemaStatus.SUPERSEDED,
        retained_for_proposition_refs=("prop:1", "prop:2"),
    )
    bound = frozenset({"prop:1"})
    assert is_retention_required(entry, bound, frozenset())


def test_revision_retention_for_replay():
    """Revisions bound to replay results must be retained."""
    entry = RevisionEntry(
        record_id="schema:engineer:v1",
        semantic_key="engineer",
        version=1,
        status=SchemaStatus.SUPERSEDED,
        retained_for_replay_refs=("replay:1",),
    )
    assert is_retention_required(entry, frozenset(), frozenset({"replay:1"}))


def test_revision_not_required_when_unbound():
    """Unbound superseded revisions may be compacted."""
    entry = RevisionEntry(
        record_id="schema:engineer:v1",
        semantic_key="engineer",
        version=1,
        status=SchemaStatus.SUPERSEDED,
    )
    assert not is_retention_required(entry, frozenset(), frozenset())


def test_active_revision_always_retained():
    """Active revisions are always retained regardless of bindings."""
    entry = RevisionEntry(
        record_id="schema:engineer:v1",
        semantic_key="engineer",
        version=1,
        status=SchemaStatus.ACTIVE,
    )
    assert is_retention_required(entry, frozenset(), frozenset())


# ── Gate: records are serializable (via asdict) ─────────────────────


def test_referent_serializable():
    """Referent must be serializable to dict."""
    r = Referent(
        id="ref:user",
        referent_kind="entity",
        canonical_key="user",
    )
    d = asdict(r)
    assert d["id"] == "ref:user"
    assert d["referent_kind"] == "entity"


def test_proposition_serializable():
    """Proposition must be serializable to dict."""
    p = Proposition(
        id="prop:1",
        predication_ref="pred:1",
        context_ref="ctx:actual",
        polarity="positive",
    )
    d = asdict(p)
    assert d["id"] == "prop:1"
    assert d["polarity"] == "positive"


def test_evidence_record_serializable():
    """EvidenceRecord must be serializable to dict."""
    ev = EvidenceRecord(
        id="ev:1",
        evidence_kind="observation",
        target_refs=("prop:1",),
        stance="supports",
    )
    d = asdict(ev)
    assert d["id"] == "ev:1"
    assert d["stance"] == "supports"


# ── Gate: schema lifecycle states ──────────────────────────────────


def test_schema_envelope_default_candidate():
    """New schema envelopes default to candidate status."""
    env = SchemaEnvelope(
        record_id="schema:test:v1",
        semantic_key="test",
        schema_kind="predicate",
    )
    assert env.status == "candidate"


def test_schema_envelope_immutability():
    """SchemaEnvelope must be immutable."""
    env = SchemaEnvelope(
        record_id="schema:test:v1",
        semantic_key="test",
        schema_kind="predicate",
    )
    with pytest.raises((AttributeError, Exception)):
        env.status = "active"  # type: ignore[misc]


# ── Gate: CAS activation ───────────────────────────────────────────


class MockStore:
    """Minimal mock store for activation tests."""
    def __init__(self):
        self._records: dict[str, int] = {}
        self._statuses: dict[str, str] = {}

    def get_revision(self, record_id: str) -> int | None:
        return self._records.get(record_id)

    def set_status(self, record_id: str, status: str, expected_revision: int) -> bool:
        current = self._records.get(record_id)
        if current != expected_revision:
            return False
        self._statuses[record_id] = status
        return True

    def add(self, record_id: str, revision: int):
        self._records[record_id] = revision
        self._statuses[record_id] = "candidate"


def test_cas_activation_success():
    """CAS activation succeeds when revision matches."""
    store = MockStore()
    store.add("schema:a:v1", 1)
    result = activate_single(store, "schema:a:v1", "active", 1)
    assert result.status == ActivationStatus.SUCCESS
    assert "schema:a:v1" in result.activated_refs


def test_cas_activation_fails_on_revision_mismatch():
    """CAS activation fails when revision has changed."""
    store = MockStore()
    store.add("schema:a:v1", 2)
    result = activate_single(store, "schema:a:v1", "active", 1)
    assert result.status == ActivationStatus.CAS_FAILED


def test_cluster_activation_atomic_success():
    """Cluster activation succeeds atomically when all members match."""
    store = MockStore()
    store.add("schema:a:v1", 1)
    store.add("schema:b:v1", 1)
    result = activate_cluster(
        store,
        ("schema:a:v1", "schema:b:v1"),
        "active",
        {"schema:a:v1": 1, "schema:b:v1": 1},
    )
    assert result.status == ActivationStatus.SUCCESS
    assert len(result.activated_refs) == 2


def test_cluster_activation_atomic_failure():
    """Cluster activation fails atomically if any member revision mismatches."""
    store = MockStore()
    store.add("schema:a:v1", 1)
    store.add("schema:b:v1", 2)  # revision changed
    result = activate_cluster(
        store,
        ("schema:a:v1", "schema:b:v1"),
        "active",
        {"schema:a:v1": 1, "schema:b:v1": 1},
    )
    assert result.status == ActivationStatus.CAS_FAILED
    # Neither should be activated
    assert store._statuses.get("schema:a:v1") != "active"


# ── Gate: import boundary enforcement ──────────────────────────────


def test_model_imports_no_engine():
    """kernel.model must not import any engine module."""
    import importlib
    import pkgutil
    import cemm.kernel.model as model_pkg

    forbidden_substrings = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.kernel.operational_meaning_compiler",
        "cemm.memory.durable_semantic_store",
    ]

    for importer, modname, ispkg in pkgutil.iter_modules(model_pkg.__path__):
        full_name = f"cemm.kernel.model.{modname}"
        mod = importlib.import_module(full_name)
        # Check module source for forbidden imports
        source = getattr(mod, "__file__", "")
        if source:
            with open(source, encoding="utf-8") as f:
                content = f.read()
            for forbidden in forbidden_substrings:
                assert forbidden not in content, (
                    f"{full_name} imports forbidden module {forbidden}"
                )


# ── KernelSnapshot and CognitiveCycle ──────────────────────────────


def test_kernel_snapshot_is_immutable():
    """KernelSnapshot must be frozen."""
    from cemm.kernel.model.cycle import KernelSnapshot
    s = KernelSnapshot(schema_store_revision=42)
    with pytest.raises(Exception):
        s.schema_store_revision = 99


def test_kernel_snapshot_fingerprint_derived():
    """KernelSnapshot.fingerprint derives AssessmentEnvironmentFingerprint."""
    from cemm.kernel.model.cycle import KernelSnapshot
    s = KernelSnapshot(
        schema_store_revision=7,
        grounding_policy_version="v1",
        kernel_foundation_version="v3.4",
    )
    fp = s.fingerprint
    assert fp.schema_store_revision == 7
    assert fp.grounding_policy_version == "v1"
    assert fp.kernel_foundation_version == "v3.4"


def test_cognitive_cycle_is_immutable():
    """CognitiveCycle must be frozen."""
    from cemm.kernel.model.cycle import CognitiveCycle, CycleTrigger, KernelSnapshot
    c = CognitiveCycle(
        cycle_id="c1",
        trigger=CycleTrigger(trigger_kind="user_utterance"),
        snapshot=KernelSnapshot(),
    )
    with pytest.raises(Exception):
        c.cycle_id = "c2"


def test_cognitive_cycle_stages_empty_by_default():
    """CognitiveCycle starts with empty stage outputs."""
    from cemm.kernel.model.cycle import CognitiveCycle, CycleTrigger, KernelSnapshot
    c = CognitiveCycle(
        cycle_id="c1",
        trigger=CycleTrigger(trigger_kind="user_utterance"),
        snapshot=KernelSnapshot(),
    )
    assert c.surface_evidence == ()
    assert c.meaning_candidates == ()
    assert c.grounded_candidates == ()
    assert c.selected_interpretations == ()
    assert c.epistemic_assessments == ()
    assert c.capability_assessments == ()
    assert c.gaps == ()
    assert c.goals == ()
    assert c.plans == ()
    assert c.critical_commit is None
    assert c.output_commit is None
    assert c.trace is None
