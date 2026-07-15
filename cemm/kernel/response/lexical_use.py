"""Operation-relative lexical and realization authorization.

A spelling may be recognized or mentioned without licensing semantic use.
This gate runs after response-content planning and before surface realization.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..model.message import LexicalRequirement, MessageContentItem, SemanticMessagePlan
from ..schema.realization import RealizationSchema


class LexicalUseStatus(str, Enum):
    ALLOWED = "allowed"
    QUALIFIED_ONLY = "qualified_only"
    MENTION_ONLY = "mention_only"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class LexicalUseAssessment:
    lexical_requirement: LexicalRequirement
    language_tag: str
    realization_schema_ref: str = ""
    selected_surface: str = ""
    status: LexicalUseStatus = LexicalUseStatus.BLOCKED
    limitations: tuple[str, ...] = ()

    @property
    def permits_generation(self) -> bool:
        return self.status in {
            LexicalUseStatus.ALLOWED,
            LexicalUseStatus.QUALIFIED_ONLY,
            LexicalUseStatus.MENTION_ONLY,
        }


@dataclass(frozen=True, slots=True)
class ItemRealizationAuthorization:
    item_ref: str
    assessments: tuple[LexicalUseAssessment, ...] = ()
    authorized: bool = False
    qualification_required: bool = False
    failure_reasons: tuple[str, ...] = ()

    def surface_for(self, semantic_key: str, default: str = "") -> str:
        for assessment in self.assessments:
            if assessment.lexical_requirement.semantic_key == semantic_key:
                return assessment.selected_surface or default
        return default


@dataclass(frozen=True, slots=True)
class RealizationAuthorization:
    plan_ref: str
    item_authorizations: tuple[ItemRealizationAuthorization, ...] = ()
    environment_fingerprint: str = ""

    def for_item(self, item_ref: str) -> ItemRealizationAuthorization | None:
        for item in self.item_authorizations:
            if item.item_ref == item_ref:
                return item
        return None

    @property
    def all_required_authorized(self) -> bool:
        return all(item.authorized for item in self.item_authorizations)


class LexicalUseGate:
    """Authorize lexical choices against realization schemas and use mode."""

    _MENTION_MODES = frozenset({"mention", "quote"})
    _QUALIFIED_MODES = frozenset({"probe", "qualified", "attribute"})

    def __init__(self, schema_store: Any | None = None) -> None:
        self._store = schema_store

    def authorize_plan(
        self,
        plan: SemanticMessagePlan,
        *,
        language: str = "en",
        environment_fingerprint: str = "",
    ) -> RealizationAuthorization:
        items = tuple(
            self.authorize_item(item, language=language)
            for item in plan.content_items
        )
        return RealizationAuthorization(
            plan_ref=plan.id,
            item_authorizations=items,
            environment_fingerprint=environment_fingerprint,
        )

    def authorize_item(
        self,
        item: MessageContentItem,
        *,
        language: str = "en",
    ) -> ItemRealizationAuthorization:
        assessments: list[LexicalUseAssessment] = []
        failures: list[str] = []
        qualification_required = False

        requirements = (
            item.all_lexical_requirements()
            if hasattr(item, "all_lexical_requirements")
            else item.lexical_requirements
        )
        for requirement in requirements:
            assessment = self._assess(requirement, language)
            assessments.append(assessment)
            if assessment.status == LexicalUseStatus.QUALIFIED_ONLY:
                qualification_required = True
            if requirement.required and not assessment.permits_generation:
                failures.append(
                    f"lexical use blocked: {requirement.semantic_key}/{requirement.use_mode}"
                )

        # A semantic item without explicit lexical requirements is not safe to
        # realize compositionally. Control-only items may be empty, but public
        # content must declare the words/senses it needs.
        if item.required and not requirements:
            failures.append("required message item has no lexical requirements")

        for clause in getattr(item, "clauses", ()):
            if clause.required and not clause.provenance_refs:
                failures.append(f"clause has no provenance: {clause.clause_ref}")
            if self._store is None:
                failures.append(f"cannot resolve clause predicate: {clause.predicate_key}")
                continue
            predicate = self._store.find_active(clause.predicate_key)
            if predicate is None or getattr(predicate, "schema_kind", "") != "predicate":
                failures.append(f"clause predicate is not active: {clause.predicate_key}")
                continue
            payload = getattr(predicate, "payload", None)
            required_roles = {
                str(role).removeprefix("role:")
                for role in getattr(payload, "role_refs", ())
            }
            supplied_roles = {value.role_key for value in clause.role_values}
            missing_roles = required_roles - supplied_roles
            if missing_roles:
                failures.append(
                    f"clause {clause.clause_ref} missing roles: "
                    + ",".join(sorted(missing_roles))
                )

        return ItemRealizationAuthorization(
            item_ref=item.semantic_ref,
            assessments=tuple(assessments),
            authorized=not failures,
            qualification_required=qualification_required,
            failure_reasons=tuple(failures),
        )

    def _assess(
        self,
        requirement: LexicalRequirement,
        language: str,
    ) -> LexicalUseAssessment:
        mode = requirement.use_mode

        # Mention/quotation can copy a user-provided surface without claiming
        # its meaning. The source surface remains explicit in provenance.
        if mode in self._MENTION_MODES:
            if requirement.surface_hint:
                return LexicalUseAssessment(
                    lexical_requirement=requirement,
                    language_tag=language,
                    selected_surface=requirement.surface_hint,
                    status=LexicalUseStatus.MENTION_ONLY,
                )
            return LexicalUseAssessment(
                lexical_requirement=requirement,
                language_tag=language,
                status=LexicalUseStatus.BLOCKED,
                limitations=("mention requires a source surface",),
            )

        envelope = self._find_realization(requirement.semantic_key, language)
        if envelope is None:
            return LexicalUseAssessment(
                lexical_requirement=requirement,
                language_tag=language,
                status=LexicalUseStatus.BLOCKED,
                limitations=("no usable realization schema",),
            )

        schema = getattr(envelope, "payload", None)
        if not isinstance(schema, RealizationSchema):
            return LexicalUseAssessment(
                lexical_requirement=requirement,
                language_tag=language,
                realization_schema_ref=getattr(envelope, "record_id", ""),
                status=LexicalUseStatus.BLOCKED,
                limitations=("realization payload has wrong type",),
            )

        if mode not in schema.allowed_use_modes:
            return LexicalUseAssessment(
                lexical_requirement=requirement,
                language_tag=language,
                realization_schema_ref=getattr(envelope, "record_id", ""),
                status=LexicalUseStatus.BLOCKED,
                limitations=(f"use mode {mode!r} not licensed",),
            )

        if not schema.competence_test_refs:
            return LexicalUseAssessment(
                lexical_requirement=requirement,
                language_tag=language,
                realization_schema_ref=getattr(envelope, "record_id", ""),
                status=LexicalUseStatus.BLOCKED,
                limitations=("realization has no competence-test provenance",),
            )

        semantic_status = "active"
        if schema.closed_class:
            # Closed-class material is licensed by audited grammar competence,
            # not by pretending it denotes a domain entity.
            if not all(ref.startswith("test:") for ref in schema.competence_test_refs):
                return LexicalUseAssessment(
                    lexical_requirement=requirement,
                    language_tag=language,
                    realization_schema_ref=getattr(envelope, "record_id", ""),
                    status=LexicalUseStatus.BLOCKED,
                    limitations=("closed-class grammar competence is ungrounded",),
                )
        else:
            semantic_ref = schema.semantic_schema_ref
            semantic_envelope = self._store.get(semantic_ref) if self._store and semantic_ref else None
            if semantic_envelope is None:
                return LexicalUseAssessment(
                    lexical_requirement=requirement,
                    language_tag=language,
                    realization_schema_ref=getattr(envelope, "record_id", ""),
                    status=LexicalUseStatus.BLOCKED,
                    limitations=("open-class realization has no semantic schema",),
                )
            semantic_status = getattr(semantic_envelope, "status", "candidate")
            if semantic_status == "active":
                if not getattr(semantic_envelope, "grounding_assessment_ref", ""):
                    return LexicalUseAssessment(
                        lexical_requirement=requirement,
                        language_tag=language,
                        realization_schema_ref=getattr(envelope, "record_id", ""),
                        status=LexicalUseStatus.BLOCKED,
                        limitations=("semantic schema lacks grounding assessment",),
                    )
                if not getattr(semantic_envelope, "competence_assessment_ref", ""):
                    return LexicalUseAssessment(
                        lexical_requirement=requirement,
                        language_tag=language,
                        realization_schema_ref=getattr(envelope, "record_id", ""),
                        status=LexicalUseStatus.BLOCKED,
                        limitations=("semantic schema lacks competence assessment",),
                    )
            elif semantic_status == "provisional" and mode not in self._QUALIFIED_MODES:
                return LexicalUseAssessment(
                    lexical_requirement=requirement,
                    language_tag=language,
                    realization_schema_ref=getattr(envelope, "record_id", ""),
                    status=LexicalUseStatus.BLOCKED,
                    limitations=("provisional meaning requires qualified use",),
                )
            elif semantic_status not in {"active", "provisional"}:
                return LexicalUseAssessment(
                    lexical_requirement=requirement,
                    language_tag=language,
                    realization_schema_ref=getattr(envelope, "record_id", ""),
                    status=LexicalUseStatus.BLOCKED,
                    limitations=(f"semantic schema status is {semantic_status}",),
                )

        status = getattr(envelope, "status", "candidate")
        if status == "active" and semantic_status == "active":
            use_status = LexicalUseStatus.ALLOWED
        elif status in {"active", "provisional"} and mode in self._QUALIFIED_MODES:
            use_status = LexicalUseStatus.QUALIFIED_ONLY
        else:
            return LexicalUseAssessment(
                lexical_requirement=requirement,
                language_tag=language,
                realization_schema_ref=getattr(envelope, "record_id", ""),
                status=LexicalUseStatus.BLOCKED,
                limitations=(f"realization schema status is {status}",),
            )

        return LexicalUseAssessment(
            lexical_requirement=requirement,
            language_tag=language,
            realization_schema_ref=getattr(envelope, "record_id", ""),
            selected_surface=schema.surface_for("base"),
            status=use_status,
        )

    def _find_realization(self, semantic_key: str, language: str) -> Any | None:
        if self._store is None:
            return None
        key = f"realize:{language}:{semantic_key}"
        candidates = tuple(self._store.find_candidates(key))
        usable = [
            candidate
            for candidate in candidates
            if getattr(candidate, "schema_kind", "") == "realization"
            and getattr(candidate, "status", "") in {"active", "provisional"}
        ]
        if not usable:
            return None
        return max(
            usable,
            key=lambda candidate: (
                getattr(candidate, "status", "") == "active",
                getattr(candidate, "version", 0),
                getattr(candidate, "confidence", 0.0),
            ),
        )
