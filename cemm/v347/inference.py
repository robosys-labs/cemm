"""Typed, bounded, proof-carrying inference over admitted propositions."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import time
from typing import Iterable, Mapping

from .model import (
    ConsequenceStatus,
    GraphPatch,
    InferenceOutcome,
    InferenceProofStep,
    KnowledgeRecord,
    PatchOperation,
    PatchOperationKind,
    Polarity,
    PortBinding,
    Predication,
    Referent,
    ReferentKind,
    RuleFunction,
    RulePattern,
    RuleSchema,
    RuleStrength,
    TruthStatus,
    canonical_data,
    semantic_hash,
)
from .relation_algebra import RelationAlgebraCoordinator
from .schema import SemanticSchemaStore
from .storage import SemanticStore


@dataclass(frozen=True, slots=True)
class InferenceBudget:
    wall_clock_ms: int = 50
    max_depth: int = 4
    max_firings: int = 128
    max_results: int = 64
    allow_sensitive: bool = False


@dataclass(frozen=True, slots=True)
class InferredGraph:
    referents: Mapping[str, Referent]
    predications: Mapping[str, Predication]
    outcome: InferenceOutcome


@dataclass(frozen=True, slots=True)
class _Fact:
    knowledge: KnowledgeRecord | None
    proposition: Referent
    predication: Predication
    depth: int = 0


class BoundedInferenceEngine:
    def __init__(self, store: SemanticStore, schemas: SemanticSchemaStore):
        self._store = store
        self._schemas = schemas
        self._relation_algebra = RelationAlgebraCoordinator(schemas)

    def infer(
        self,
        *,
        context_ref: str,
        rules: Iterable[RuleSchema] | None = None,
        budget: InferenceBudget | None = None,
    ) -> InferredGraph:
        budget = budget or InferenceBudget()
        start = time.perf_counter()
        available_rules = (
            tuple(rules) if rules is not None
            else self._schemas.active_rules() + self._relation_algebra.compiled_rules()
        )
        rules = tuple(sorted(
            (rule for rule in available_rules
             if not rule.context_refs or context_ref in rule.context_refs or "global" in rule.context_refs),
            key=lambda item: (item.priority, item.confidence, item.rule_ref),
            reverse=True,
        ))
        facts = self._load_facts(context_ref)
        all_facts = list(facts)
        new_referents: dict[str, Referent] = {}
        new_predications: dict[str, Predication] = {}
        proof_steps: list[InferenceProofStep] = []
        fired: list[str] = []
        blocked: list[str] = []
        signatures = {self._signature(item.predication) for item in all_facts}
        incomplete = False

        for depth in range(1, budget.max_depth + 1):
            generated_this_depth: list[_Fact] = []
            for rule in rules:
                if self._elapsed_ms(start) >= budget.wall_clock_ms:
                    incomplete = True
                    break
                if len(proof_steps) >= budget.max_firings or len(new_referents) >= budget.max_results:
                    incomplete = True
                    break
                if rule.sensitivity != "normal" and not budget.allow_sensitive:
                    blocked.append(rule.rule_ref)
                    continue
                matches = self._match_rule(rule, all_facts)
                for variable_bindings, premise_facts in matches:
                    if self._elapsed_ms(start) >= budget.wall_clock_ms:
                        incomplete = True
                        break
                    consequence = self._consequence_status(rule)
                    if consequence == ConsequenceStatus.BLOCKED:
                        blocked.append(rule.rule_ref)
                        continue
                    predication = self._instantiate(rule.consequent, variable_bindings, context_ref, rule)
                    signature = self._signature(predication)
                    if signature in signatures:
                        continue
                    signatures.add(signature)
                    proposition = Referent(
                        referent_id=semantic_hash("referent:proposition", (
                            predication.predication_id,
                            context_ref,
                            consequence.value,
                        )),
                        kind=ReferentKind.PROPOSITION,
                        type_refs=("kind:proposition",),
                        payload={
                            "predication_refs": (predication.predication_id,),
                            "context_ref": context_ref,
                            "polarity": Polarity.POSITIVE.value,
                            "modality_refs": (),
                            "attribution_ref": f"inference:{rule.rule_ref}",
                            "valid_time_ref": None,
                            "communicative_force": "assert",
                            "consequence_status": consequence.value,
                        },
                        scope_ref=context_ref,
                        context_ref=context_ref,
                        metadata={"rule_ref": rule.rule_ref, "inferred": True},
                    )
                    new_predications[predication.predication_id] = predication
                    new_referents[proposition.referent_id] = proposition
                    premise_refs = tuple(
                        item.knowledge.knowledge_id if item.knowledge is not None
                        else item.proposition.referent_id
                        for item in premise_facts
                    )
                    premise_propositions = tuple(item.proposition.referent_id for item in premise_facts)
                    root_lineage = tuple(dict.fromkeys(
                        ref
                        for item in premise_facts
                        for ref in (
                            item.knowledge.root_lineage_refs
                            if item.knowledge and item.knowledge.root_lineage_refs
                            else (item.knowledge.knowledge_id,) if item.knowledge else (item.proposition.referent_id,)
                        )
                    ))
                    proof_steps.append(InferenceProofStep(
                        step_id=semantic_hash("proof:step", (
                            rule.rule_ref, premise_refs, variable_bindings, proposition.referent_id
                        )),
                        rule_ref=rule.rule_ref,
                        premise_knowledge_refs=premise_refs,
                        variable_bindings=dict(variable_bindings),
                        conclusion_proposition_ref=proposition.referent_id,
                        consequence_status=consequence,
                        depth=depth,
                        premise_proposition_refs=premise_propositions,
                        dependency_fingerprint=semantic_hash("inference_dependency", (
                            rule.rule_ref, rule.revision, premise_refs, self._store.revision
                        ), 64),
                        root_lineage_refs=root_lineage,
                    ))
                    fired.append(rule.rule_ref)
                    generated_this_depth.append(_Fact(
                        knowledge=None,
                        proposition=proposition,
                        predication=predication,
                        depth=depth,
                    ))
                    if len(proof_steps) >= budget.max_firings or len(new_referents) >= budget.max_results:
                        incomplete = True
                        break
            all_facts.extend(generated_this_depth)
            if incomplete or not generated_this_depth:
                break
        return InferredGraph(
            referents=new_referents,
            predications=new_predications,
            outcome=InferenceOutcome(
                proposition_refs=tuple(new_referents),
                proof_steps=tuple(proof_steps),
                incomplete=incomplete,
                blocked_rule_refs=tuple(dict.fromkeys(blocked)),
                fired_rule_refs=tuple(dict.fromkeys(fired)),
                elapsed_ms=self._elapsed_ms(start),
            ),
        )

    def compile_admission_patch(
        self,
        graph: InferredGraph,
        *,
        context_ref: str,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        """Persist only strict entailed conclusions with their exact proofs.

        Defaults, causal predictions and enabling possibilities remain derived
        cycle-local cognition.  This prevents plausible consequences from being
        laundered into actual-world facts.
        """
        entailed = {
            step.conclusion_proposition_ref: step
            for step in graph.outcome.proof_steps
            if step.consequence_status == ConsequenceStatus.ENTAILED
        }
        if not entailed:
            return None
        operations: list[PatchOperation] = []
        evidence_refs: list[str] = []
        for proposition_ref, step in entailed.items():
            proposition = graph.referents.get(proposition_ref)
            if proposition is None:
                continue
            predication_refs = tuple((proposition.payload or {}).get("predication_refs", ()))
            for predication_ref in predication_refs:
                predication = graph.predications.get(str(predication_ref))
                if predication is None:
                    continue
                operations.append(PatchOperation(
                    operation_id=f"op:{predication.predication_id}",
                    kind=PatchOperationKind.UPSERT_PREDICATION,
                    target_ref=predication.predication_id,
                    payload=canonical_data(predication),
                ))
            operations.append(PatchOperation(
                operation_id=f"op:{proposition.referent_id}",
                kind=PatchOperationKind.UPSERT_PROPOSITION,
                target_ref=proposition.referent_id,
                payload=canonical_data(proposition),
            ))
            knowledge_ref = semantic_hash("knowledge:inferred", (
                proposition_ref, step.rule_ref, step.premise_knowledge_refs
            ))
            evidence = tuple(dict.fromkeys((f"rule:{step.rule_ref}", *step.premise_knowledge_refs)))
            evidence_refs.extend(evidence)
            operations.append(PatchOperation(
                operation_id=f"op:{knowledge_ref}",
                kind=PatchOperationKind.UPSERT_KNOWLEDGE,
                target_ref=knowledge_ref,
                payload=canonical_data(KnowledgeRecord(
                    knowledge_id=knowledge_ref,
                    proposition_ref=proposition_ref,
                    truth_status=TruthStatus.SUPPORTED,
                    context_ref=context_ref,
                    source_refs=(f"inference:{step.rule_ref}",),
                    evidence_refs=evidence,
                    confidence=min(1.0, graph.predications[predication_refs[0]].confidence),
                    scope_ref=context_ref,
                    permission_ref="conversation",
                    root_lineage_refs=step.root_lineage_refs,
                    derivation_refs=(step.step_id,),
                    metadata={
                        "inferred": True,
                        "rule_ref": step.rule_ref,
                        "premise_proposition_refs": step.premise_proposition_refs,
                        "dependency_fingerprint": step.dependency_fingerprint,
                    },
                )),
            ))
            for premise_ref in step.premise_knowledge_refs:
                dependency_ref = semantic_hash("dependency:inference", (knowledge_ref, premise_ref))
                operations.append(PatchOperation(
                    operation_id=f"op:{dependency_ref}",
                    kind=PatchOperationKind.ADD_DEPENDENCY,
                    target_ref=dependency_ref,
                    payload={
                        "dependent_ref": knowledge_ref,
                        "dependency_ref": premise_ref,
                        "dependency_kind": "inference_premise",
                        "dependent_revision": 1,
                        "dependency_revision": 1,
                        "active": True,
                        "metadata": {"fingerprint": step.dependency_fingerprint},
                    },
                ))
        if not operations:
            return None
        return GraphPatch(
            patch_id=semantic_hash("patch:inference", (
                context_ref, tuple(entailed), tuple(step.step_id for step in entailed.values())
            )),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:bounded_inference",
            evidence_refs=tuple(dict.fromkeys(evidence_refs)),
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            permission_ref="internal",
            validation_requirements=("strict_entailment_only", "proof_lineage_complete"),
        )

    def _load_facts(self, context_ref: str) -> list[_Fact]:
        result = []
        for knowledge in self._store.active_knowledge(
            context_ref=context_ref, scope_refs=("global", context_ref)
        ):
            proposition = self._store.get_referent(knowledge.proposition_ref)
            if proposition is None:
                continue
            payload = proposition.payload or {}
            for predication_ref in payload.get("predication_refs", ()):
                predication = self._store.get_predication(str(predication_ref))
                if predication is not None:
                    result.append(_Fact(knowledge, proposition, predication, 0))
        return result

    def _match_rule(
        self, rule: RuleSchema, facts: list[_Fact]
    ) -> list[tuple[dict[str, str], tuple[_Fact, ...]]]:
        candidate_sets = []
        for pattern in rule.antecedents:
            candidates = []
            for fact in facts:
                binding = self._match_pattern(pattern, fact.predication)
                if binding is not None:
                    candidates.append((binding, fact))
            if not candidates:
                return []
            candidate_sets.append(candidates)
        results = []
        for combination in product(*candidate_sets):
            merged: dict[str, str] = {}
            premise_facts = []
            compatible = True
            for binding, fact in combination:
                for variable, referent_ref in binding.items():
                    current = merged.get(variable)
                    if current is not None and current != referent_ref:
                        compatible = False
                        break
                    merged[variable] = referent_ref
                if not compatible:
                    break
                premise_facts.append(fact)
            if compatible and not self._exception_matches(rule, merged, facts):
                results.append((merged, tuple(premise_facts)))
        return results

    @staticmethod
    def _match_pattern(pattern: RulePattern, predication: Predication) -> dict[str, str] | None:
        if predication.predicate_schema_ref != pattern.predicate_schema_ref:
            return None
        bindings = {
            item.port_id: item.referent_refs[0]
            for item in predication.bindings if len(item.referent_refs) == 1
        }
        if any(bindings.get(port) != ref for port, ref in pattern.fixed_referent_refs.items()):
            return None
        result = {}
        for port, variable in pattern.port_variables.items():
            ref = bindings.get(port)
            if ref is None:
                return None
            current = result.get(variable)
            if current is not None and current != ref:
                return None
            result[variable] = ref
        return result

    def _exception_matches(
        self, rule: RuleSchema, variables: Mapping[str, str], facts: list[_Fact]
    ) -> bool:
        for exception in rule.exceptions:
            for fact in facts:
                candidate = self._match_pattern(exception, fact.predication)
                if candidate is None:
                    continue
                if all(variables.get(key) == value for key, value in candidate.items() if key in variables):
                    return True
        return False

    @staticmethod
    def _instantiate(
        pattern: RulePattern,
        variables: Mapping[str, str],
        context_ref: str,
        rule: RuleSchema,
    ) -> Predication:
        bindings = []
        for port, variable in pattern.port_variables.items():
            if variable not in variables:
                continue
            bindings.append(PortBinding(port_id=port, referent_refs=(variables[variable],)))
        for port, ref in pattern.fixed_referent_refs.items():
            bindings.append(PortBinding(port_id=port, referent_refs=(ref,)))
        return Predication(
            predication_id=semantic_hash("predication:inferred", (
                pattern.predicate_schema_ref,
                [(item.port_id, item.referent_refs) for item in bindings],
                context_ref,
                rule.rule_ref,
            )),
            predicate_schema_ref=pattern.predicate_schema_ref,
            bindings=tuple(bindings),
            context_ref=context_ref,
            source_evidence_refs=(f"rule:{rule.rule_ref}",),
            assumptions=(),
            confidence=rule.confidence,
        )

    @staticmethod
    def _signature(predication: Predication) -> tuple[str, tuple[tuple[str, tuple[str, ...]], ...]]:
        return (
            predication.predicate_schema_ref,
            tuple(sorted((item.port_id, item.referent_refs) for item in predication.bindings)),
        )

    @staticmethod
    def _consequence_status(rule: RuleSchema) -> ConsequenceStatus:
        if rule.function in {
            RuleFunction.IDENTITY,
            RuleFunction.CONSTITUTIVE,
            RuleFunction.STRICT,
            RuleFunction.PREREQUISITE,
        } and rule.strength == RuleStrength.STRICT:
            return ConsequenceStatus.ENTAILED
        if rule.function == RuleFunction.CAUSAL:
            return ConsequenceStatus.PREDICTED
        if rule.function in {RuleFunction.ENABLING, RuleFunction.PREVENTING}:
            return ConsequenceStatus.POSSIBLE
        if rule.function in {RuleFunction.DEFAULT, RuleFunction.STATISTICAL, RuleFunction.NORMATIVE}:
            return ConsequenceStatus.EXPECTED
        if rule.strength == RuleStrength.PROBABILISTIC:
            return ConsequenceStatus.EXPECTED
        return ConsequenceStatus.POSSIBLE

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return (time.perf_counter() - start) * 1000.0
