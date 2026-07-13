"""Boot schema manifest — audited boot schemas with versioned foundation.

Import boundary: model + schema + foundations submodules only.

Architectural guardrails (SEMANTIC_FOUNDATIONS.md §5):
- Every boot schema has: ordinary schema representation, field-level boot
  provenance, typed dependencies, GroundingSpecification, independent
  property/invariant tests, versioned foundation manifest, activation assessment.
- The same package may not self-certify solely by supplying its own
  example/expected graph pairs. Boot validation includes kernel invariants
  and independently implemented property tests.
- Failure policy: failed foundations halt or enter diagnostic-safe mode;
  failed optional boot concepts load opaque/provisional and downgrade dependents;
  no failing schema silently activates.

Boot schemas are ordinary schema revisions — boot origin is provenance,
not a separate lifecycle state (AGENTS.md §7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..schema.envelope import SchemaEnvelope, SchemaDependency
from ..schema.grounding_spec import GroundingSpecification
from ..schema.role import RoleSchema
from ..schema.predicate import PredicateSchema
from ..schema.entity_kind import EntityKindSchema
from ..schema.state_dimension import StateDimensionSchema
from ..schema.context import ContextSchema
from ..schema.operation import OperationSchema, CapabilitySchema
from ..schema.policy import PolicySchema
from ..schema.metalanguage import MetalanguageSchema
from ..schema.store import SemanticSchemaStore
from ..model.identity import Scope, ScopeLevel, Provenance, Permission, TimeExtent


# ── Boot manifest ──────────────────────────────────────────────────


class BootSchemaTier(str, Enum):
    """Tier of boot schema — determines failure policy."""
    FOUNDATION = "foundation"       # failure halts boot
    REQUIRED = "required"           # failure enters diagnostic-safe mode
    OPTIONAL = "optional"           # failure loads opaque/provisional


@dataclass(frozen=True, slots=True)
class BootSchemaEntry:
    """An entry in the boot schema manifest.

    Every boot schema has:
    - ordinary schema representation (SchemaEnvelope)
    - field-level boot provenance
    - typed dependencies
    - GroundingSpecification
    - independent property/invariant test references
    - versioned foundation manifest
    - activation assessment (deferred to boot validation)
    """
    record_id: str
    semantic_key: str
    schema_kind: str
    tier: BootSchemaTier
    envelope: SchemaEnvelope
    grounding_spec: GroundingSpecification
    dependencies: tuple[SchemaDependency, ...] = ()
    property_test_refs: tuple[str, ...] = ()
    manifest_version: int = 1
    foundation_version: str = "v3.4"
    description: str = ""


@dataclass(frozen=True, slots=True)
class FoundationManifest:
    """Versioned foundation manifest — top-level boot manifest.

    Records the kernel foundation version, value type versions,
    predicate versions, and boot schema versions. A version change
    invalidates dependent assessments and cognition.
    """
    manifest_id: str
    foundation_version: str = "v3.4"
    value_type_version: int = 1
    predicate_version: int = 1
    epistemic_predicate_version: int = 1
    boot_schema_version: int = 1
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    entries: tuple[BootSchemaEntry, ...] = ()

    def fingerprint(self) -> str:
        """Compute a fingerprint for the manifest.

        A foundation version change invalidates all dependent assessments.
        """
        import hashlib
        parts = [
            self.foundation_version,
            str(self.value_type_version),
            str(self.predicate_version),
            str(self.epistemic_predicate_version),
            str(self.boot_schema_version),
        ]
        for entry in sorted(self.entries, key=lambda e: e.record_id):
            parts.append(f"{entry.record_id}:{entry.manifest_version}")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


# ── Boot schema builders ───────────────────────────────────────────


def _boot_provenance(description: str = "") -> Provenance:
    return Provenance(
        source_id="boot",
        source_kind="boot",
    )


def _boot_envelope(
    record_id: str,
    semantic_key: str,
    schema_kind: str,
    payload: Any = None,
    scope: Scope | None = None,
) -> SchemaEnvelope:
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind=schema_kind,
        status="candidate",
        scope=scope or Scope(level=ScopeLevel.GLOBAL),
        version=1,
        payload=payload,
        provenance=_boot_provenance(),
        permission=Permission.public(),
    )


def _basic_grounding_spec(semantic_family: str = "") -> GroundingSpecification:
    return GroundingSpecification(
        semantic_family=semantic_family,
        required_definition_fields=(),
        allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
        minimum_independent_oracle_classes=frozenset({"invariant"}),
    )


# ── Entity kind boot schemas ───────────────────────────────────────


def _entity_kind_entry(
    semantic_key: str,
    description: str,
    parent_kinds: tuple[str, ...] = (),
    state_dimensions: tuple[str, ...] = (),
    tier: BootSchemaTier = BootSchemaTier.OPTIONAL,
) -> BootSchemaEntry:
    payload = EntityKindSchema(
        semantic_key=semantic_key,
        parent_kind_refs=parent_kinds,
        state_dimension_refs=state_dimensions,
    )
    envelope = _boot_envelope(
        f"boot:entity_kind:{semantic_key}:v1",
        semantic_key,
        "entity_kind",
        payload=payload,
    )
    deps = tuple(
        SchemaDependency(dependency_kind="definition", target_schema_ref=f"boot:entity_kind:{pk}:v1")
        for pk in parent_kinds
    )
    return BootSchemaEntry(
        record_id=f"boot:entity_kind:{semantic_key}:v1",
        semantic_key=semantic_key,
        schema_kind="entity_kind",
        tier=tier,
        envelope=envelope,
        grounding_spec=_basic_grounding_spec("entity_kind"),
        dependencies=deps,
        description=description,
    )


def boot_entity_kinds() -> tuple[BootSchemaEntry, ...]:
    """Boot entity kind schemas (SEMANTIC_FOUNDATIONS.md §5).

    Useful concepts supplied as ordinary schema revisions — not kernel primitives.
    """
    return (
        _entity_kind_entry("physical_entity", "A physical entity occupying space"),
        _entity_kind_entry("biological_entity", "A biological entity", parent_kinds=("physical_entity",)),
        _entity_kind_entry("person", "A person", parent_kinds=("biological_entity",)),
        _entity_kind_entry("agent", "An agent capable of action"),
        _entity_kind_entry("software_system", "A software system", parent_kinds=("agent",)),
        _entity_kind_entry("organization", "An organization", parent_kinds=("agent",)),
        _entity_kind_entry("place", "A place or location"),
        _entity_kind_entry("information_object", "An information object"),
        _entity_kind_entry("group", "A group of entities"),
        _entity_kind_entry("goal", "A goal artifact"),
    )


# ── State dimension boot schemas ───────────────────────────────────


def _state_dimension_entry(
    semantic_key: str,
    description: str,
    value_type: str = "text",
    holder_kinds: frozenset[str] | None = None,
    tier: BootSchemaTier = BootSchemaTier.OPTIONAL,
) -> BootSchemaEntry:
    payload = StateDimensionSchema(
        semantic_key=semantic_key,
        holder_kinds=holder_kinds or frozenset(),
        value_type=value_type,
    )
    envelope = _boot_envelope(
        f"boot:state_dimension:{semantic_key}:v1",
        semantic_key,
        "state_dimension",
        payload=payload,
    )
    return BootSchemaEntry(
        record_id=f"boot:state_dimension:{semantic_key}:v1",
        semantic_key=semantic_key,
        schema_kind="state_dimension",
        tier=tier,
        envelope=envelope,
        grounding_spec=_basic_grounding_spec("state_dimension"),
        description=description,
    )


def boot_state_dimensions() -> tuple[BootSchemaEntry, ...]:
    """Boot state dimension schemas."""
    return (
        _state_dimension_entry("name", "Name of an entity", value_type="text"),
        _state_dimension_entry("age", "Age of an entity", value_type="quantity"),
        _state_dimension_entry("location_state", "Location state", value_type="text"),
        _state_dimension_entry("status", "Status of an entity", value_type="enum"),
        _state_dimension_entry("confidence_level", "Confidence level", value_type="probability"),
    )


# ── Context boot schemas ───────────────────────────────────────────


def boot_contexts() -> tuple[BootSchemaEntry, ...]:
    """Boot context schemas."""
    entries: list[BootSchemaEntry] = []
    for kind in ["actual", "reported", "belief", "hypothetical", "counterfactual", "simulated", "quoted", "desired"]:
        payload = ContextSchema(
            semantic_key=f"context:{kind}",
            allows_parent_access=True,
            allows_sibling_access=False,
            allows_actual_world_access=(kind in ("actual", "reported", "belief")),
        )
        envelope = _boot_envelope(
            f"boot:context:{kind}:v1",
            f"context:{kind}",
            "context",
            payload=payload,
        )
        entries.append(BootSchemaEntry(
            record_id=f"boot:context:{kind}:v1",
            semantic_key=f"context:{kind}",
            schema_kind="context",
            tier=BootSchemaTier.REQUIRED,
            envelope=envelope,
            grounding_spec=_basic_grounding_spec("context"),
            description=f"Context frame for {kind} propositions",
        ))
    return tuple(entries)


# ── Cognitive operation boot schemas ───────────────────────────────


def boot_cognitive_operations() -> tuple[BootSchemaEntry, ...]:
    """Boot cognitive operation schemas."""
    ops = [
        ("perceive", "Perceive input signals"),
        ("interpret", "Interpret perceived signals"),
        ("ground", "Ground interpreted candidates"),
        ("assess_epistemic", "Assess epistemic status"),
        ("assess_capability", "Assess capability status"),
        ("detect_gaps", "Detect competence gaps"),
        ("plan", "Plan operations toward goals"),
        ("authorize", "Authorize an operation"),
        ("execute", "Execute an operation"),
        ("reconcile", "Reconcile execution outcomes"),
        ("learn", "Learn from evidence and replay"),
        ("respond", "Plan response content"),
        ("realize", "Realize response in language"),
        ("introspect", "Introspect on self state"),
    ]
    entries: list[BootSchemaEntry] = []
    for key, desc in ops:
        payload = OperationSchema(
            semantic_key=f"op:{key}",
            operation_class="cognitive",
        )
        envelope = _boot_envelope(
            f"boot:op:{key}:v1",
            f"op:{key}",
            "operation",
            payload=payload,
        )
        entries.append(BootSchemaEntry(
            record_id=f"boot:op:{key}:v1",
            semantic_key=f"op:{key}",
            schema_kind="operation",
            tier=BootSchemaTier.REQUIRED,
            envelope=envelope,
            grounding_spec=_basic_grounding_spec("operation"),
            description=desc,
        ))
    return tuple(entries)


# ── Communicative operation boot schemas ───────────────────────────


def boot_communicative_operations() -> tuple[BootSchemaEntry, ...]:
    """Boot communicative operation schemas."""
    ops = [
        ("assert", "Assert a proposition"),
        ("ask", "Ask a question"),
        ("request", "Request an action"),
        ("direct", "Give a directive"),
        ("acknowledge", "Acknowledge a proposition"),
        ("correct", "Correct a proposition"),
        ("promise", "Promise an action"),
        ("refuse", "Refuse a request"),
    ]
    entries: list[BootSchemaEntry] = []
    for key, desc in ops:
        payload = OperationSchema(
            semantic_key=f"comm:{key}",
            operation_class="communicative",
        )
        envelope = _boot_envelope(
            f"boot:comm:{key}:v1",
            f"comm:{key}",
            "operation",
            payload=payload,
        )
        entries.append(BootSchemaEntry(
            record_id=f"boot:comm:{key}:v1",
            semantic_key=f"comm:{key}",
            schema_kind="operation",
            tier=BootSchemaTier.REQUIRED,
            envelope=envelope,
            grounding_spec=_basic_grounding_spec("operation"),
            description=desc,
        ))
    return tuple(entries)


# ── Policy boot schemas ────────────────────────────────────────────


def boot_policies() -> tuple[BootSchemaEntry, ...]:
    """Boot policy schemas."""
    policies = [
        ("access_policy", "Default access policy"),
        ("retention_policy", "Default retention policy"),
        ("execution_policy", "Default execution policy"),
        ("safety_policy", "Default safety policy"),
        ("learning_policy", "Default learning policy"),
    ]
    entries: list[BootSchemaEntry] = []
    for key, desc in policies:
        payload = PolicySchema(
            semantic_key=f"policy:{key}",
            policy_kind=key.replace("_policy", ""),
            default_decision="allow",
        )
        envelope = _boot_envelope(
            f"boot:policy:{key}:v1",
            f"policy:{key}",
            "policy",
            payload=payload,
        )
        entries.append(BootSchemaEntry(
            record_id=f"boot:policy:{key}:v1",
            semantic_key=f"policy:{key}",
            schema_kind="policy",
            tier=BootSchemaTier.REQUIRED,
            envelope=envelope,
            grounding_spec=_basic_grounding_spec("policy"),
            description=desc,
        ))
    return tuple(entries)


# ── Metalanguage boot schemas ──────────────────────────────────────


def boot_metalanguage() -> tuple[BootSchemaEntry, ...]:
    """Boot metalanguage schemas for metalinguistic predicates."""
    entries: list[BootSchemaEntry] = []
    for key in ["means", "knows", "understands", "defines"]:
        payload = MetalanguageSchema(
            semantic_key=f"meta:{key}",
            target_predicate_ref=f"boot:predicate:{key}:v1",
            supports_nested_queries=True,
        )
        envelope = _boot_envelope(
            f"boot:meta:{key}:v1",
            f"meta:{key}",
            "metalanguage",
            payload=payload,
        )
        entries.append(BootSchemaEntry(
            record_id=f"boot:meta:{key}:v1",
            semantic_key=f"meta:{key}",
            schema_kind="metalanguage",
            tier=BootSchemaTier.REQUIRED,
            envelope=envelope,
            grounding_spec=_basic_grounding_spec("metalanguage"),
            description=f"Metalanguage support for {key}",
        ))
    return tuple(entries)


# ── Full manifest ──────────────────────────────────────────────────


def build_boot_manifest() -> FoundationManifest:
    """Build the complete boot foundation manifest.

    Combines all boot schema entries into a versioned manifest.
    """
    entries: list[BootSchemaEntry] = []
    entries.extend(boot_entity_kinds())
    entries.extend(boot_state_dimensions())
    entries.extend(boot_contexts())
    entries.extend(boot_cognitive_operations())
    entries.extend(boot_communicative_operations())
    entries.extend(boot_policies())
    entries.extend(boot_metalanguage())
    return FoundationManifest(
        manifest_id="boot:foundation:v3.4",
        entries=tuple(entries),
    )


def all_boot_entries() -> tuple[BootSchemaEntry, ...]:
    """Get all boot schema entries."""
    return build_boot_manifest().entries
