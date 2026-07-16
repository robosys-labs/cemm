"""Language-neutral DECIDE-stage response-intent derivation."""
from __future__ import annotations

import hashlib
from typing import Any

from .planner import ResponseIntent, ResponseIntentRole


class ResponseDecider:
    def __init__(
        self, policies: tuple[dict[str, Any], ...] = (), *,
        ranker=None, semantic_memory=None
    ) -> None:
        self._policies = policies
        self._ranker = ranker
        self._semantic_memory = semantic_memory

    def _decide_unranked(self, cycle) -> tuple[ResponseIntent, ...]:
        intents: list[ResponseIntent] = []
        selected = tuple(getattr(cycle, "selected_interpretations", ()) or ())

        for interpretation in selected:
            force = getattr(interpretation, "communicative_force", "")
            predicate = getattr(
                interpretation, "predicate_semantic_key", ""
            )
            if force in {"ask", "query"}:
                if predicate == "capable_of":
                    intents.extend(
                        self._answer_from_capability(cycle, interpretation)
                    )
                elif predicate == "knows":
                    intents.extend(
                        self._answer_from_contextual_knowledge(
                            cycle, interpretation
                        )
                    )
                else:
                    intents.extend(
                        self._answer_from_retrieval(cycle, interpretation)
                    )
            intents.extend(self._policy_intents(cycle, interpretation))

        if not intents:
            learning_results = tuple((
                *tuple(getattr(cycle, "rule_learning_results", ()) or ()),
                *tuple(getattr(cycle, "definition_learning_results", ()) or ()),
            ))
            for result in learning_results:
                learned_ref = (
                    getattr(result, "rule_schema_ref", "")
                    or getattr(result, "schema_record_ref", "")
                )
                if not learned_ref:
                    continue
                provenance = tuple(dict.fromkeys((
                    learned_ref,
                    *tuple(getattr(result, "evidence_refs", ()) or ()),
                )))
                intents.append(ResponseIntent(
                    intent_id=f"grounded_learning:{learned_ref}",
                    predicate_key="acknowledges",
                    roles=(
                        ResponseIntentRole(
                            role_key="speaker",
                            value_ref="self",
                            value_kind="referent",
                            provenance_refs=provenance,
                        ),
                        ResponseIntentRole(
                            role_key="addressee",
                            value_ref="user",
                            value_kind="referent",
                            provenance_refs=provenance,
                        ),
                    ),
                    communicative_force="assert",
                    context_ref="actual",
                    provenance_refs=provenance,
                ))
        if not intents:
            fallback = self._fallback_intent(cycle)
            if fallback is not None:
                intents.append(fallback)
        return self._dedupe(intents)

    def decide_with_candidates(self, cycle):
        intents = list(self._decide_unranked(cycle))
        has_residue = any(
            tuple(getattr(graph, "unresolved_fragments", ()) or ())
            for graph in tuple(getattr(cycle, "meaning_candidates", ()) or ())
        )
        if has_residue and not any(
            intent.predicate_key == "requests" for intent in intents
        ):
            clarification = self._fallback_intent(cycle)
            if clarification is not None:
                intents.append(clarification)
        intents = self._dedupe(intents)
        if self._ranker is None:
            return intents, ()
        ranked = self._ranker.rank(intents, cycle)
        return self._ranker.select(ranked), ranked

    def decide(self, cycle) -> tuple[ResponseIntent, ...]:
        selected, _ = self.decide_with_candidates(cycle)
        return selected

    def _answer_from_contextual_knowledge(self, cycle, interpretation):
        if self._semantic_memory is None:
            return ()
        embedded = []
        for graph in tuple(getattr(cycle, "meaning_candidates", ()) or ()):
            outer = next((
                item for item in graph.candidate_propositions
                if item.proposition.id == interpretation.proposition_ref
            ), None)
            if outer is None:
                continue
            for embedded_ref in outer.embedded_proposition_refs:
                proposition = next((
                    item for item in graph.candidate_propositions
                    if item.proposition.id == embedded_ref
                ), None)
                if proposition is None:
                    continue
                grounding = next((
                    grounded.for_predication(proposition.proposition.predication_ref)
                    for grounded in cycle.grounded_candidates
                    if grounded.for_predication(
                        proposition.proposition.predication_ref
                    ) is not None
                ), None)
                if grounding is not None:
                    embedded.append(grounding)
        named = next((
            item for item in embedded
            if item.predicate_semantic_key == "named"
        ), None)
        if named is None:
            return ()
        holder = next((
            binding.grounded_filler_ref for binding in named.role_bindings
            if binding.role_schema_ref.removeprefix("role:") == "holder"
        ), "")
        if not holder:
            return ()
        from ..memory.semantic import FactQuery
        facts = list(self._semantic_memory.query(FactQuery(
            predicate_key="named",
            role_constraints={"holder": holder},
            context_refs=("actual",),
        )))
        if not facts:
            return ()
        fact = max(facts, key=lambda item: (
            any(
                role.role_key == "name_form"
                and role.semantic_key == "name_form:full"
                for role in item.roles
            ),
            item.created_at,
        ))
        return (self._intent_from_fact(fact),)

    def _answer_from_capability(self, cycle, interpretation):
        requested_operation = next((
            binding.filler_ref.removeprefix("ref:schema:")
            for binding in getattr(interpretation, "role_bindings", ())
            if binding.role_schema_ref.removeprefix("role:") == "operation"
        ), "")
        assessments = tuple(
            getattr(cycle, "capability_assessments", ()) or ()
        )
        if requested_operation:
            assessments = tuple(
                assessment
                for assessment in assessments
                if assessment.operation_schema_ref == requested_operation
            )
        else:
            # A broad capability query reports only currently available
            # operations. A specific query may truthfully return a negative.
            assessments = tuple(
                assessment
                for assessment in assessments
                if assessment.is_capable
            )
        return tuple(
            self._intent_from_capability(assessment)
            for assessment in assessments
        )

    def _intent_from_capability(self, assessment) -> ResponseIntent:
        assessment_ref = (
            assessment.assessment_id
            or f"capability:{self._stable_id((
                assessment.subject_ref,
                assessment.operation_schema_ref,
                assessment.status,
                assessment.environment_fingerprint,
            ))}"
        )
        provenance = tuple(dict.fromkeys((
            assessment_ref,
            *tuple(assessment.evidence_refs or ()),
        )))
        return ResponseIntent(
            intent_id=assessment_ref,
            predicate_key="capable_of",
            roles=(
                ResponseIntentRole(
                    role_key="agent",
                    value_ref=assessment.subject_ref,
                    value_kind="referent",
                    provenance_refs=provenance,
                ),
                ResponseIntentRole(
                    role_key="operation",
                    value_ref=assessment.operation_schema_ref,
                    value_kind="referent",
                    semantic_key=assessment.operation_schema_ref,
                    provenance_refs=provenance,
                ),
            ),
            communicative_force="assert",
            context_ref=assessment.context_ref or "actual",
            polarity="positive" if assessment.is_capable else "negative",
            provenance_refs=provenance,
        )

    def _answer_from_retrieval(self, cycle, interpretation):
        predicate_key = getattr(
            interpretation,
            "predicate_semantic_key",
            "",
        )
        if not predicate_key:
            return ()
        requested_roles = {
            binding.role_schema_ref.removeprefix("role:"): binding.filler_ref
            for binding in getattr(interpretation, "role_bindings", ())
        }
        facts = []
        for result in tuple(getattr(cycle, "retrieval_results", ()) or ()):
            for fact in tuple(getattr(result, "records", ()) or ()):
                if getattr(fact, "predicate_key", "") != predicate_key:
                    continue
                fact_roles = {
                    role.role_key: role.value_ref
                    for role in getattr(fact, "roles", ())
                }
                if any(
                    fact_roles.get(role) != value
                    for role, value in requested_roles.items()
                ):
                    continue
                facts.append(fact)
        if predicate_key == "named" and facts:
            by_holder = {}
            for fact in facts:
                holder = next((
                    role.value_ref for role in fact.roles
                    if role.role_key == "holder"
                ), "")
                current = by_holder.get(holder)
                full = any(
                    role.role_key == "name_form"
                    and role.semantic_key == "name_form:full"
                    for role in fact.roles
                )
                key = (full, getattr(fact, "created_at", ""))
                if current is None or key > current[0]:
                    by_holder[holder] = (key, fact)
            facts = [item[1] for item in by_holder.values()]
        return tuple(self._intent_from_fact(fact) for fact in facts)

    def _intent_from_fact(self, fact) -> ResponseIntent:
        provenance = tuple(dict.fromkeys((
            getattr(fact, "fact_id", ""),
            *tuple(getattr(fact, "evidence_refs", ()) or ()),
        )))
        roles = tuple(
            ResponseIntentRole(
                role_key=role.role_key,
                value_ref=role.value_ref,
                value_kind=self._role_family(role.value_kind),
                semantic_key=role.semantic_key,
                surface_hint=role.surface or (
                    role.value_ref
                    if self._role_family(role.value_kind) == "value"
                    else ""
                ),
                provenance_refs=provenance,
            )
            for role in fact.roles
        )
        qualification_key = ""
        if fact.predicate_key == "named":
            holder = next(
                (role.value_ref for role in fact.roles if role.role_key == "holder"),
                "",
            )
            if holder in {"self", "user"}:
                qualification_key = f"holder:{holder}"
        return ResponseIntent(
            intent_id=(
                f"retrieval:{getattr(fact, 'fact_id', self._stable_id(provenance))}"
            ),
            predicate_key=fact.predicate_key,
            roles=roles,
            communicative_force="assert",
            context_ref=fact.context_ref,
            polarity=fact.polarity,
            modality=fact.modality,
            qualification_key=qualification_key,
            provenance_refs=provenance,
        )

    def _policy_intents(self, cycle, interpretation):
        result = []
        for policy in self._policies:
            trigger = dict(policy.get("trigger", {}))
            if trigger.get("condition"):
                continue
            if trigger.get("predicate_key") and trigger["predicate_key"] != getattr(
                interpretation,
                "predicate_semantic_key",
                "",
            ):
                continue
            if trigger.get("force") and trigger["force"] != getattr(
                interpretation,
                "communicative_force",
                "",
            ):
                continue
            response = dict(policy.get("response", {}))
            if not response:
                continue
            provenance = tuple(dict.fromkeys((
                str(policy.get("policy_id", "")),
                getattr(interpretation, "proposition_ref", ""),
            )))
            role_values = {
                binding.role_schema_ref.removeprefix("role:"): binding.filler_ref
                for binding in getattr(interpretation, "role_bindings", ())
            }
            roles = []
            for role_key, spec in dict(response.get("roles", {})).items():
                spec = dict(spec)
                value_ref = str(spec.get("constant", ""))
                source_role = str(spec.get("from_role", ""))
                if source_role:
                    value_ref = role_values.get(source_role, "")
                if not value_ref:
                    continue
                roles.append(ResponseIntentRole(
                    role_key=str(role_key),
                    value_ref=value_ref,
                    value_kind=str(spec.get("value_kind", "referent")),
                    semantic_key=str(spec.get("semantic_key", "")),
                    surface_hint=str(spec.get("surface_hint", "")),
                    use_mode=str(spec.get("use_mode", "assert")),
                    provenance_refs=provenance,
                ))
            result.append(ResponseIntent(
                intent_id=(
                    f"policy:{policy.get('policy_id', self._stable_id(provenance))}"
                ),
                predicate_key=str(response.get("predicate_key", "")),
                roles=tuple(roles),
                communicative_force=str(response.get("force", "assert")),
                context_ref=str(response.get("context_ref", "actual")),
                provenance_refs=provenance,
            ))
        return tuple(result)

    def _fallback_intent(self, cycle):
        policy = next(
            (
                item
                for item in self._policies
                if dict(item.get("trigger", {})).get("condition")
                == "no_response_intent"
            ),
            None,
        )
        if policy is None:
            return None
        signal = next(
            iter(tuple(getattr(cycle.trigger, "input_signals", ()) or ())),
            None,
        )
        if signal is None:
            return None
        response = dict(policy.get("response", {}))
        provenance = tuple(dict.fromkeys((
            str(policy.get("policy_id", "")),
            str(getattr(signal, "id", "")),
        )))
        roles = []
        for role_key, raw_spec in dict(response.get("roles", {})).items():
            spec = dict(raw_spec)
            if spec.get("from_input") == "surface":
                value_ref = f"opaque:input:{self._stable_id((signal.content,))}"
                surface_hint = signal.content
            else:
                value_ref = str(spec.get("constant", ""))
                surface_hint = str(spec.get("surface_hint", ""))
            if not value_ref:
                continue
            roles.append(ResponseIntentRole(
                role_key=str(role_key),
                value_ref=value_ref,
                value_kind=str(spec.get("value_kind", "referent")),
                semantic_key=str(spec.get("semantic_key", "")),
                surface_hint=surface_hint,
                use_mode=str(spec.get("use_mode", "assert")),
                provenance_refs=provenance,
            ))
        return ResponseIntent(
            intent_id=f"policy:{policy.get('policy_id', 'fallback')}",
            predicate_key=str(response.get("predicate_key", "requests")),
            roles=tuple(roles),
            communicative_force=str(response.get("force", "ask")),
            context_ref=str(response.get("context_ref", "actual")),
            provenance_refs=provenance,
        )

    @staticmethod
    def _role_family(value_kind: str) -> str:
        if value_kind in {"text", "enum", "quantity", "boolean", "value"}:
            return "value"
        if value_kind == "context":
            return "context"
        if value_kind == "proposition":
            return "proposition"
        return "referent"

    @staticmethod
    def _stable_id(values) -> str:
        raw = "|".join(str(value) for value in values)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _dedupe(intents):
        result = []
        seen = set()
        for intent in intents:
            key = (
                intent.predicate_key,
                intent.communicative_force,
                intent.polarity,
                tuple((role.role_key, role.value_ref) for role in intent.roles),
            )
            if key not in seen:
                seen.add(key)
                result.append(intent)
        return tuple(result)
