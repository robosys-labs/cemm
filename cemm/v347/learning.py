"""Grounded, scoped learning-frontier compiler.

Learning produces candidate GraphPatches.  It never activates a schema merely
because an utterance matched a pattern or a user repeated a claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .model import (
    FormLattice,
    GapKind,
    GapRecord,
    GraphPatch,
    MeaningBundle,
    PatchOperation,
    PatchOperationKind,
    ReferentKind,
    RuleFunction,
    RuleStrength,
    SchemaStatus,
    semantic_hash,
)
from .language import primary_language
from .schema import SemanticSchemaStore


@dataclass(frozen=True, slots=True)
class LearningContribution:
    contribution_id: str
    contribution_kind: str
    target_ref: str
    payload: Mapping[str, Any]
    grounding_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    scope_ref: str
    confidence: float


@dataclass(frozen=True, slots=True)
class GroundingFrontierItem:
    frontier_id: str
    dependency_ref: str
    expected_kind: str
    reason: str
    depth: int
    sensitive: bool = False
    resolved: bool = False


@dataclass(frozen=True, slots=True)
class LearningTransaction:
    transaction_id: str
    context_ref: str
    contributions: tuple[LearningContribution, ...]
    frontier: tuple[GroundingFrontierItem, ...]
    status: str
    max_depth: int
    max_items: int
    evidence_refs: tuple[str, ...]


class LearningEligibilityAssessor:
    def explicit_teaching(self, lattice: FormLattice) -> bool:
        semantic_refs = {ref for span in lattice.spans for ref in span.semantic_refs}
        return "force:teach" in semantic_refs or any(
            span.candidate_kind == "teaching_marker" for span in lattice.spans
        )

    def eligible_gap(self, gap: GapRecord, *, explicit_teaching: bool) -> bool:
        if not explicit_teaching:
            return False
        return gap.kind in {GapKind.LEXICAL, GapKind.SCHEMA}


class LearningContributionCompiler:
    def __init__(self, schemas: SemanticSchemaStore):
        self._schemas = schemas

    def compile(
        self,
        lattice: FormLattice,
        bundle: MeaningBundle | None,
        *,
        context_ref: str,
    ) -> tuple[LearningContribution, ...]:
        if bundle is None:
            return ()
        result: list[LearningContribution] = []
        explicit = LearningEligibilityAssessor().explicit_teaching(lattice)
        for proposition_ref in bundle.proposition_refs:
            proposition = bundle.graph.referents.get(proposition_ref)
            payload = proposition.payload or {} if proposition else {}
            for predication_ref in payload.get("predication_refs", ()):
                predication = bundle.graph.predications.get(str(predication_ref))
                if predication is None:
                    continue
                schema = self._schemas.maybe_predicate(predication.predicate_schema_ref)
                if schema is None:
                    continue
                bindings = {
                    binding.port_id: binding.referent_refs
                    for binding in predication.bindings
                }
                contribution_kind = str(schema.metadata.get("learning_contribution", ""))
                definition: Mapping[str, Any] = {
                    "predicate_schema_ref": predication.predicate_schema_ref,
                    "bindings": bindings,
                    "proposition_ref": proposition_ref,
                }
                target_ref = predication.predication_id

                # Classification is based on grounded predicate semantics, never
                # on an English teaching phrase.  Only explicit teaching may turn
                # ordinary relation assertions into schema/rule candidates.
                if explicit and predication.predicate_schema_ref == "predicate:subkind_of":
                    child = self._single(bindings.get("child", ()))
                    parent = self._single(bindings.get("parent", ()))
                    if child and parent:
                        target_ref = semantic_hash("rule:learned:subkind", (child, parent, context_ref))
                        contribution_kind = "rule_schema"
                        definition = {
                            "rule": {
                                "rule_ref": target_ref,
                                "antecedents": [{
                                    "predicate_schema_ref": "predicate:instance_of",
                                    "port_variables": {"instance": "x"},
                                    "fixed_referent_refs": {"kind": child},
                                }],
                                "consequent": {
                                    "predicate_schema_ref": "predicate:instance_of",
                                    "port_variables": {"instance": "x"},
                                    "fixed_referent_refs": {"kind": parent},
                                },
                                "function": RuleFunction.CONSTITUTIVE.value,
                                "strength": RuleStrength.STRICT.value,
                                "status": SchemaStatus.CANDIDATE.value,
                                "scope_ref": context_ref,
                                "support_lineage_refs": predication.source_evidence_refs,
                            },
                            "bindings": bindings,
                            "proposition_ref": proposition_ref,
                        }
                elif explicit and predication.predicate_schema_ref in {"predicate:causes", "predicate:enables"}:
                    left_port, right_port = (
                        ("cause", "effect") if predication.predicate_schema_ref == "predicate:causes"
                        else ("condition", "possibility")
                    )
                    antecedent = self._pattern_from_referent(
                        self._single(bindings.get(left_port, ())), bundle
                    )
                    consequent = self._pattern_from_referent(
                        self._single(bindings.get(right_port, ())), bundle
                    )
                    if antecedent and consequent:
                        target_ref = semantic_hash("rule:learned", (antecedent, consequent, context_ref))
                        contribution_kind = "rule_schema"
                        definition = {
                            "rule": {
                                "rule_ref": target_ref,
                                "antecedents": [antecedent],
                                "consequent": consequent,
                                "function": (
                                    RuleFunction.CAUSAL.value
                                    if predication.predicate_schema_ref == "predicate:causes"
                                    else RuleFunction.ENABLING.value
                                ),
                                "strength": RuleStrength.DEFEASIBLE.value,
                                "status": SchemaStatus.CANDIDATE.value,
                                "scope_ref": context_ref,
                                "support_lineage_refs": predication.source_evidence_refs,
                            },
                            "bindings": bindings,
                            "proposition_ref": proposition_ref,
                        }
                elif explicit and predication.predicate_schema_ref == "predicate:means":
                    term_ref = self._single(bindings.get("term", ()))
                    meaning_ref = self._single(bindings.get("meaning", ()))
                    term = bundle.graph.referents.get(term_ref or "")
                    meaning = bundle.graph.referents.get(meaning_ref or "")
                    if term and meaning and term.kind == ReferentKind.TEXT and meaning.kind != ReferentKind.TEXT:
                        surface = str((term.payload or {}).get("text", "")).strip()
                        if surface:
                            target_ref = semantic_hash("schema:lexical_alias", (
                                primary_language(lattice), surface, meaning.referent_id, context_ref
                            ))
                            contribution_kind = "lexical_alias"
                            definition = {
                                "schema_ref": target_ref,
                                "schema_kind": "lexical_alias",
                                "surface": surface,
                                "referent_ref": meaning.referent_id,
                                "language_tag": primary_language(lattice),
                                "bindings": bindings,
                                "proposition_ref": proposition_ref,
                            }
                    elif term_ref and meaning_ref:
                        contribution_kind = "grounded_definition"
                        target_ref = semantic_hash("schema:definition", (term_ref, meaning_ref, context_ref))
                        definition = {
                            "schema_ref": target_ref,
                            "schema_kind": "grounded_definition",
                            "term_ref": term_ref,
                            "meaning_ref": meaning_ref,
                            "bindings": bindings,
                            "proposition_ref": proposition_ref,
                        }

                if not contribution_kind and not explicit:
                    continue
                if not contribution_kind:
                    contribution_kind = "schema_statement"
                grounding_refs = tuple(dict.fromkeys(
                    ref
                    for binding_refs in bindings.values()
                    for ref in binding_refs
                    if ref in bundle.graph.referents
                    and bundle.graph.referents[ref].kind != ReferentKind.TEXT
                ))
                result.append(LearningContribution(
                    contribution_id=semantic_hash("learning:contribution", (
                        proposition_ref, predication.predication_id, contribution_kind, definition
                    )),
                    contribution_kind=contribution_kind,
                    target_ref=target_ref,
                    payload=definition,
                    grounding_refs=grounding_refs,
                    evidence_refs=predication.source_evidence_refs,
                    scope_ref=context_ref,
                    confidence=predication.confidence,
                ))
        return tuple(result)


    @staticmethod
    def _single(values: Iterable[str]) -> str | None:
        values = tuple(values)
        return str(values[0]) if len(values) == 1 else None

    @staticmethod
    def _pattern_from_referent(
        referent_ref: str | None, bundle: MeaningBundle
    ) -> Mapping[str, Any] | None:
        if not referent_ref:
            return None
        referent = bundle.graph.referents.get(referent_ref)
        if referent is None or referent.kind != ReferentKind.PROPOSITION:
            return None
        predication_refs = tuple((referent.payload or {}).get("predication_refs", ()))
        if len(predication_refs) != 1:
            return None
        predication = bundle.graph.predications.get(str(predication_refs[0]))
        if predication is None:
            return None
        fixed = {
            binding.port_id: binding.referent_refs[0]
            for binding in predication.bindings if len(binding.referent_refs) == 1
        }
        return {
            "predicate_schema_ref": predication.predicate_schema_ref,
            "port_variables": {},
            "fixed_referent_refs": fixed,
        }


class GroundingFrontierBuilder:
    def build(
        self,
        contributions: Iterable[LearningContribution],
        bundle: MeaningBundle | None,
        *,
        max_depth: int = 4,
        max_items: int = 24,
    ) -> tuple[GroundingFrontierItem, ...]:
        if bundle is None:
            return ()
        frontier: list[GroundingFrontierItem] = []
        for contribution in contributions:
            for binding_refs in contribution.payload.get("bindings", {}).values():
                for ref in binding_refs:
                    referent = bundle.graph.referents.get(str(ref))
                    if referent is None:
                        frontier.append(self._item(str(ref), "referent", "binding_not_in_selected_uol", 0))
                    elif referent.kind == ReferentKind.TEXT and not referent.type_refs:
                        frontier.append(self._item(str(ref), "referent_kind", "opaque_text_requires_grounding", 1))
            if not contribution.grounding_refs:
                frontier.append(self._item(
                    contribution.target_ref,
                    "known_grounding_anchor",
                    "learning_contribution_has_no_non_text_anchor",
                    0,
                ))
        deduped: dict[str, GroundingFrontierItem] = {}
        for item in frontier:
            if item.depth <= max_depth:
                deduped[item.dependency_ref] = item
        return tuple(list(deduped.values())[:max_items])

    @staticmethod
    def _item(ref: str, expected: str, reason: str, depth: int) -> GroundingFrontierItem:
        return GroundingFrontierItem(
            frontier_id=semantic_hash("learning:frontier", (ref, expected, reason)),
            dependency_ref=ref,
            expected_kind=expected,
            reason=reason,
            depth=depth,
        )


class LearningCoordinator:
    def __init__(self, schemas: SemanticSchemaStore):
        self._schemas = schemas
        self.eligibility = LearningEligibilityAssessor()
        self.compiler = LearningContributionCompiler(schemas)
        self.frontier_builder = GroundingFrontierBuilder()

    def inspect(
        self,
        lattice: FormLattice,
        bundle: MeaningBundle | None,
        gaps: Iterable[GapRecord],
        *,
        context_ref: str,
    ) -> LearningTransaction | None:
        explicit = self.eligibility.explicit_teaching(lattice)
        contributions = self.compiler.compile(lattice, bundle, context_ref=context_ref)
        eligible_gaps = tuple(
            gap for gap in gaps if self.eligibility.eligible_gap(gap, explicit_teaching=explicit)
        )
        if not contributions and not eligible_gaps:
            return None
        frontier = self.frontier_builder.build(contributions, bundle)
        status = "ready_candidate" if contributions and not frontier else "needs_grounding"
        evidence = tuple(dict.fromkeys(
            ref for contribution in contributions for ref in contribution.evidence_refs
        ))
        return LearningTransaction(
            transaction_id=semantic_hash("learning:transaction", (
                context_ref,
                tuple(item.contribution_id for item in contributions),
                tuple(item.gap_id for item in eligible_gaps),
            )),
            context_ref=context_ref,
            contributions=contributions,
            frontier=frontier,
            status=status,
            max_depth=4,
            max_items=24,
            evidence_refs=evidence,
        )

    def compile_patch(
        self,
        transaction: LearningTransaction | None,
        *,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        if transaction is None or not transaction.contributions:
            return None
        operations: list[PatchOperation] = []
        for contribution in transaction.contributions:
            candidate_ref = semantic_hash("schema:candidate", (
                contribution.contribution_kind,
                contribution.target_ref,
                contribution.payload,
                transaction.context_ref,
            ))
            is_rule = contribution.contribution_kind == "rule_schema"
            operations.append(PatchOperation(
                operation_id=f"op:{candidate_ref}",
                kind=(
                    PatchOperationKind.UPSERT_RULE_CANDIDATE
                    if is_rule else PatchOperationKind.UPSERT_SCHEMA_CANDIDATE
                ),
                target_ref=candidate_ref,
                payload={
                    "scope_ref": transaction.context_ref,
                    "status": SchemaStatus.CANDIDATE.value,
                    "payload": {
                        "contribution_kind": contribution.contribution_kind,
                        "target_ref": contribution.target_ref,
                        "definition": dict(contribution.payload),
                        "rule": dict(contribution.payload.get("rule", {})) if is_rule else {},
                        "grounding_refs": contribution.grounding_refs,
                        "frontier_refs": tuple(item.frontier_id for item in transaction.frontier),
                        "confidence": contribution.confidence,
                    },
                    "evidence_refs": contribution.evidence_refs,
                },
            ))
        return GraphPatch(
            patch_id=semantic_hash("patch:learning", transaction.transaction_id),
            context_ref=transaction.context_ref,
            scope_ref=transaction.context_ref,
            source_ref="runtime:learning",
            evidence_refs=transaction.evidence_refs,
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            permission_ref="private_learning",
            validation_requirements=(
                "grounding_frontier_closed_before_activation",
                "independent_competence_before_promotion",
                "scope_review",
            ),
            rollback_hint="reject candidate revision",
            metadata={
                "transaction_ref": transaction.transaction_id,
                "status": transaction.status,
            },
        )
