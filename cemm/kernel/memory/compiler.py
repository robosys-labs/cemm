"""Compile selected grounded assertions into exact fact mutations."""
from __future__ import annotations
from dataclasses import dataclass
from uuid import uuid4
from ..model.identity import Permission, SemanticIdentity
from ..model.mutation import MutationOperation, MutationSet
from .semantic import FactRole, MutationPayloadRegistry, SemanticFact

@dataclass(frozen=True, slots=True)
class FactCompilationResult:
    mutation_set: MutationSet | None = None
    fact_refs: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

class FactMutationCompiler:
    def __init__(
        self, payload_registry: MutationPayloadRegistry, semantic_memory=None
    ):
        self._payloads = payload_registry
        self._memory = semantic_memory

    def compile(self, cycle):
        operations, fact_refs, blockers = [], [], []
        for interpretation in cycle.selected_interpretations:
            if interpretation.communicative_force not in {
                "assert", "correct"
            }:
                continue
            grounding = self._grounding(
                cycle, interpretation.predication_ref
            )
            proposition = self._proposition(
                cycle, interpretation.proposition_ref
            )
            if grounding is None or proposition is None:
                blockers.append(
                    "selected assertion lacks grounded structure"
                )
                continue
            if grounding.unresolved_role_refs:
                blockers.append(
                    f"open roles: {grounding.unresolved_role_refs}"
                )
                continue
            profile = grounding.use_profile
            level = getattr(
                getattr(profile, "level", ""),
                "value",
                getattr(profile, "level", ""),
            )
            actual = level in {"active", "causal"}
            attributed = level in {"partial", "opaque"}
            if not actual and not attributed:
                blockers.append(
                    f"{grounding.predicate_semantic_key} is unusable"
                )
                continue
            roles = tuple(
                FactRole(
                    role_key=binding.role_schema_ref.removeprefix(
                        "role:"
                    ),
                    value_ref=binding.grounded_filler_ref,
                    value_kind=(
                        getattr(
                            binding.grounding,
                            "referent_kind",
                            "referent",
                        )
                        if binding.grounding is not None
                        else "semantic_ref"
                    ),
                    semantic_key=(
                        binding.grounding.semantic_keys[0]
                        if binding.grounding is not None
                        and binding.grounding.semantic_keys
                        else ""
                    ),
                    surface=(
                        getattr(binding.grounding, "surface", "")
                        if binding.grounding is not None
                        else ""
                    ),
                )
                for binding in grounding.role_bindings
                if binding.grounded_filler_ref
            )
            if grounding.predicate_semantic_key == "subkind_of":
                blockers.append("definition retained in schema lifecycle")
                continue
            if (
                getattr(interpretation, "is_provisional", False)
                and grounding.opaque_role_refs
            ):
                blockers.append(
                    "provisional role fillers cannot enter actual memory"
                )
                continue
            fact_id = f"fact:{uuid4().hex[:16]}"
            evidence_ref = (
                f"input_evidence:{cycle.cycle_id}:"
                f"{proposition.id}"
            )
            context_kind = str(
                getattr(interpretation, "context_kind", "") or "actual"
            )
            # World context and source attribution are distinct.  A direct user
            # assertion is about the actual dialogue world but remains sourced
            # to the user and evidence-qualified; random proposition UUIDs are
            # not durable world identifiers.
            durable_context = (
                "actual"
                if context_kind in {"actual", "reported", ""}
                else context_kind
            )
            fact = SemanticFact(
                fact_id=fact_id,
                predicate_key=grounding.predicate_semantic_key,
                roles=roles,
                context_ref=durable_context,
                polarity=proposition.polarity,
                confidence=max(
                    0.35,
                    float(getattr(
                        interpretation, "confidence", 0.0
                    )),
                ),
                evidence_refs=(evidence_ref,),
                source_ref="user",
            )
            if self._is_correction(cycle, interpretation, fact):
                holder = next((
                    role.value_ref for role in fact.roles
                    if role.role_key == "holder"
                ), "")
                from .semantic import FactQuery
                for existing in self._memory.query(FactQuery(
                    predicate_key=fact.predicate_key,
                    role_constraints={"holder": holder},
                    context_refs=(fact.context_ref,),
                )):
                    if existing.semantic_identity == fact.semantic_identity:
                        continue
                    supersede_ref = f"payload:supersede:{existing.fact_id}"
                    self._payloads.put(supersede_ref, existing.fact_id)
                    operations.append(MutationOperation(
                        id=f"mutation:supersede:{existing.fact_id}",
                        operation_kind="semantic_fact",
                        semantic_identity=SemanticIdentity(
                            identity_kind="semantic_fact",
                            key=existing.semantic_identity,
                        ),
                        action="supersede",
                        payload_ref=supersede_ref,
                        required=True,
                        evidence_refs=(evidence_ref,),
                        permission=Permission.user_private(),
                        reason="grounded correction supersedes prior fact",
                    ))
            payload_ref = f"payload:{fact_id}"
            self._payloads.put(payload_ref, fact)
            operations.append(MutationOperation(
                id=f"mutation:{fact_id}",
                operation_kind="semantic_fact",
                semantic_identity=SemanticIdentity(
                    identity_kind="semantic_fact",
                    key=fact.semantic_identity,
                ),
                action="create",
                payload_ref=payload_ref,
                required=True,
                evidence_refs=(evidence_ref,),
                permission=Permission.user_private(),
                reason="grounded user assertion",
            ))
            fact_refs.append(fact_id)
        if not operations:
            return FactCompilationResult(
                blockers=tuple(blockers)
            )
        return FactCompilationResult(
            mutation_set=MutationSet(
                id=f"mutation_set:{uuid4().hex[:12]}",
                phase="critical",
                operations=tuple(operations),
            ),
            fact_refs=tuple(fact_refs),
            blockers=tuple(blockers),
        )

    def _is_correction(self, cycle, interpretation, fact):
        if self._memory is None or fact.predicate_key != "named":
            return False
        if interpretation.communicative_force == "correct":
            return True
        if any(
            role.role_key == "name_form"
            and role.semantic_key == "name_form:full"
            for role in fact.roles
        ):
            return True
        return any(
            relation.source_ref == interpretation.proposition_ref
            and relation.relation_kind == "correction"
            for graph in cycle.meaning_candidates
            for relation in graph.discourse_relations
        )

    @staticmethod
    def _grounding(cycle, predication_ref):
        for graph in cycle.grounded_candidates:
            found = graph.for_predication(predication_ref)
            if found is not None:
                return found
        return None

    @staticmethod
    def _proposition(cycle, proposition_ref):
        for graph in cycle.meaning_candidates:
            for candidate in graph.candidate_propositions:
                if candidate.proposition.id == proposition_ref:
                    return candidate.proposition
        return None
