"""Language-neutral DECIDE-stage response-intent derivation.

The decider consumes semantic interpretations, retrieval records, and audited
runtime policies.  It never examines transcript phrases to choose a response.
"""
from __future__ import annotations

import hashlib
from typing import Any

from .planner import ResponseIntent, ResponseIntentRole


class ResponseDecider:
    def __init__(self, policies: tuple[dict[str, Any], ...] = ()) -> None:
        self._policies = policies

    def decide(self, cycle) -> tuple[ResponseIntent, ...]:
        intents: list[ResponseIntent] = []
        selected = tuple(getattr(cycle, "selected_interpretations", ()) or ())

        for interpretation in selected:
            force = getattr(interpretation, "communicative_force", "")
            if force in {"ask", "query"}:
                intents.extend(self._answer_from_retrieval(cycle, interpretation))
            intents.extend(self._policy_intents(cycle, interpretation))

        if not intents:
            fallback = self._fallback_intent(cycle)
            if fallback is not None:
                intents.append(fallback)
        return self._dedupe(intents)

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
        return ResponseIntent(
            intent_id=f"retrieval:{getattr(fact, 'fact_id', self._stable_id(provenance))}",
            predicate_key=fact.predicate_key,
            roles=roles,
            communicative_force="assert",
            context_ref=fact.context_ref,
            polarity=fact.polarity,
            modality=fact.modality,
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
                intent_id=f"policy:{policy.get('policy_id', self._stable_id(provenance))}",
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
                tuple((role.role_key, role.value_ref) for role in intent.roles),
            )
            if key not in seen:
                seen.add(key)
                result.append(intent)
        return tuple(result)
