"""GroundingResolver — referent grounding + definition grounding.

Import boundary: model + schema + language submodules only. No engine imports.

Architectural guardrails (UNDERSTANDING_PIPELINE.md §4-5, AGENTS.md §7.1-7.2):
- GroundingResolver answers two distinct questions:
    1. Referent grounding: What is being mentioned? What is its identity?
    2. Definition grounding: Which schema revision defines this sense?
       Are required fields present? What competence has been demonstrated?
- Schema lookup, structural executability, independent competence,
  epistemic admissibility, and current usability are different decisions.
- The path is: recognized surface → candidate sense/schema reference →
  schema-family definition closure → competence profile → epistemic
  admissibility by context → operation-specific SchemaUseProfile.
- Scope is not truth precedence. Resolution order:
    1. determine the intended sense
    2. determine epistemic world/context
    3. filter domain and valid time
    4. check access scope
    5. compare explicit supersession/override relations
    6. evaluate structural usability and epistemic admissibility
    7. select the revision appropriate for the requested operation
- Neither GroundingResolver nor SchemaGroundingAssessment may activate
  a revision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.identity import Scope, ScopeLevel
from ..schema.store import SemanticSchemaStore
from ..schema.envelope import SchemaEnvelope
from ..schema.grounding_spec import GroundingSpecification, SemanticPattern
from ..schema.closure import (
    SchemaGroundingAssessment, GroundedDefinitionClosure,
    CompetenceProfile, RecursiveComponent,
)
from ..schema.competence import CompetenceAssessment, CompetenceHarness
from ..schema.use_profile import (
    SchemaUseProfile, derive_use_profile, UseProfileLevel, SemanticOperation,
)
from ..schema.provenance import FieldProvenanceMap, ContributionRecord, ProvenanceKind
from ..schema.resolver import SchemaResolver


@dataclass(frozen=True, slots=True)
class ReferentGrounding:
    """Result of referent grounding — what is being mentioned."""
    referent_ref: str = ""  # Ref[Referent]
    referent_kind: str = ""  # instance, schema_sense, lexical_form, value, etc.
    discourse_identity: str = ""  # stable identity within discourse
    confidence: float = 0.0
    is_unknown: bool = False


@dataclass(frozen=True, slots=True)
class DefinitionGrounding:
    """Result of definition grounding — which schema defines this sense."""
    schema_record_ref: str = ""  # Ref[SchemaEnvelope]
    semantic_key: str = ""
    semantic_family: str = ""
    assessment: SchemaGroundingAssessment | None = None
    use_profile: SchemaUseProfile | None = None
    competence: CompetenceAssessment | None = None
    is_grounded: bool = False
    blockers: tuple[str, ...] = ()


class GroundingResolver:
    """Sole authority for referent and definition grounding.

    Answers two distinct questions:
    1. Referent grounding: What is being mentioned?
    2. Definition grounding: Which schema revision could define this sense?

    Does NOT activate, write, or mutate the store. Does NOT select final
    meaning (that's InterpretationResolver's job). Produces derived control
    records (SchemaGroundingAssessment, SchemaUseProfile) that inform the
    interpretation resolver.

    Scope is not truth precedence — resolution follows the 7-step order
    from UNDERSTANDING_PIPELINE.md §5.
    """

    def __init__(
        self,
        store: SemanticSchemaStore,
        resolver: SchemaResolver | None = None,
    ) -> None:
        self._store = store
        self._resolver = resolver or SchemaResolver(store)
        self._closure_checker = GroundedDefinitionClosure()
        self._competence_harness = CompetenceHarness()

    def ground_referent(
        self,
        surface: str,
        language_tag: str = "en",
        discourse_context: dict[str, Any] | None = None,
    ) -> ReferentGrounding:
        """Ground a referent from a surface form.

        Answers: What is being mentioned? What is its discourse identity?
        Does NOT select final meaning or activate schemas.
        """
        # Look up lexical form in the store's index
        semantic_keys = self._store.lookup_lexical_form(surface, language_tag)

        if not semantic_keys:
            # Unknown referent — not converted to generic entity
            return ReferentGrounding(
                referent_ref=f"ref:unknown:{surface}",
                referent_kind="unknown",
                is_unknown=True,
                confidence=0.0,
            )

        # Find candidates for each semantic key
        # The resolver's job is to find candidates, not select one
        best_key = None
        best_confidence = -1.0
        for key in semantic_keys:
            candidates = self._store.find_candidates(key)
            active = [c for c in candidates if c.status == "active"]
            if active:
                best = max(active, key=lambda e: e.version)
                if best.confidence >= best_confidence:
                    best_confidence = best.confidence
                    best_key = key

        if best_key is None:
            # No active schema — referent is a candidate sense
            return ReferentGrounding(
                referent_ref=f"ref:lexical:{surface}:{language_tag}",
                referent_kind="lexical_form",
                discourse_identity=f"{surface}:{language_tag}",
                confidence=0.3,
            )

        return ReferentGrounding(
            referent_ref=f"ref:schema:{best_key}",
            referent_kind="schema_sense",
            discourse_identity=f"{best_key}:{language_tag}",
            confidence=best_confidence,
        )

    def ground_definition(
        self,
        semantic_key: str,
        context_ref: str = "",
        scope: Scope | None = None,
        valid_at: datetime | None = None,
        patterns: tuple[SemanticPattern, ...] = (),
        provenance_map: FieldProvenanceMap | None = None,
        competence_cases: tuple[Any, ...] = (),
        implementation_path: str = "",
        environment_fingerprint: str = "",
    ) -> DefinitionGrounding:
        """Ground a definition — which schema revision defines this sense?

        Follows the 7-step resolution order from UNDERSTANDING_PIPELINE.md §5:
        1. Determine the intended sense
        2. Determine epistemic world/context
        3. Filter domain and valid time
        4. Check access scope
        5. Compare explicit supersession/override relations
        6. Evaluate structural usability and epistemic admissibility
        7. Select the revision appropriate for the requested operation

        Does NOT activate the schema. Produces a SchemaGroundingAssessment
        and SchemaUseProfile as derived control records.
        """
        from datetime import datetime

        # Step 1: Determine the intended sense
        candidates = self._store.find_candidates(
            semantic_key,
            context_ref=context_ref or None,
            scope=scope,
            valid_at=valid_at,
        )

        if not candidates:
            return DefinitionGrounding(
                semantic_key=semantic_key,
                blockers=("No candidates found for semantic key",),
            )

        # Step 5: Compare supersession — prefer active over provisional over candidate
        active = [c for c in candidates if c.status == "active"]
        provisional = [c for c in candidates if c.status == "provisional"]
        candidate_schemas = [c for c in candidates if c.status == "candidate"]

        if active:
            envelope = max(active, key=lambda e: e.version)
        elif provisional:
            envelope = max(provisional, key=lambda e: e.version)
        elif candidate_schemas:
            envelope = max(candidate_schemas, key=lambda e: e.version)
        else:
            return DefinitionGrounding(
                semantic_key=semantic_key,
                blockers=("No usable candidates (all rejected/superseded)",),
            )

        # Step 6: Evaluate structural usability
        grounding_spec = GroundingSpecification(
            semantic_family=envelope.schema_kind,
            required_definition_fields=(),
            allowed_cycle_classes=frozenset({"positive_monotone_recursive"}),
            minimum_independent_oracle_classes=frozenset({"invariant"}),
        )

        assessment = self._closure_checker.assess(
            envelope=envelope,
            grounding_spec=grounding_spec,
            patterns=patterns,
            provenance_map=provenance_map,
            dependencies=envelope.dependency_refs,
            environment_fingerprint=environment_fingerprint,
        )

        # Step 6b: Evaluate competence
        competence: CompetenceAssessment | None = None
        if competence_cases:
            from ..schema.competence import CompetenceCase
            cases = tuple(
                c if isinstance(c, CompetenceCase) else CompetenceCase(
                    case_id=str(i),
                    check_kind=c.get("check_kind", "positive_case"),
                    input_lineage=c.get("input_lineage", ""),
                    oracle_lineage=c.get("oracle_lineage", ""),
                    is_independent=c.get("is_independent", False),
                    passed=c.get("passed", False),
                )
                for i, c in enumerate(competence_cases)
            )
            competence = self._competence_harness.assess(cases, implementation_path)

        # Step 7: Derive use profile
        is_competent = competence is not None and competence.is_competent
        is_self_certified = competence is not None and competence.is_self_certified

        use_profile = derive_use_profile(
            assessment=assessment,
            context_ref=context_ref,
            competence_is_competent=is_competent,
            competence_is_self_certified=is_self_certified,
            epistemic_admissible=True,  # Phase 6 will provide EpistemicEvaluator
            scope_accessible=True,
        )

        return DefinitionGrounding(
            schema_record_ref=envelope.record_id,
            semantic_key=semantic_key,
            semantic_family=envelope.schema_kind,
            assessment=assessment,
            use_profile=use_profile,
            competence=competence,
            is_grounded=assessment.is_structurally_executable and is_competent,
            blockers=assessment.blocker_reasons if not assessment.is_structurally_executable else (),
        )
