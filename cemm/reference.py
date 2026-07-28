"""Perspective-aware reference planning and same-CSIR canonical realization."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import re
from string import Formatter
from typing import Any, Mapping, Sequence

from cemm.model import canonical, stable

_SEMANTIC_REF = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class ReferenceChoice:
    semantic_ref: str
    relation_to_speaker: str
    grammatical_person: str
    number: str = "singular"
    possessive: bool = False
    reflexive: bool = False
    emphasis: bool = False
    selected_form: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "semantic_ref": self.semantic_ref,
            "relation_to_speaker": self.relation_to_speaker,
            "grammatical_person": self.grammatical_person,
            "number": self.number,
            "possessive": self.possessive,
            "reflexive": self.reflexive,
            "emphasis": self.emphasis,
            "selected_form": self.selected_form,
        }


@dataclass(frozen=True)
class ReferencePlan:
    plan_ref: str
    speaker_ref: str
    addressee_ref: str
    choices: tuple[ReferenceChoice, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_ref": self.plan_ref,
            "speaker_ref": self.speaker_ref,
            "addressee_ref": self.addressee_ref,
            "choices": [item.as_dict() for item in self.choices],
        }


@dataclass(frozen=True)
class SurfaceDecisionTrace:
    decision_ref: str
    response_ref: str
    response_action: str
    obligation_ref: str | None
    chosen_surface: str
    grammar_rule_ref: str
    reference_plan: ReferencePlan
    semantic_signature: str
    alternatives: tuple[str, ...] = ()
    verification: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_ref": self.decision_ref,
            "response_ref": self.response_ref,
            "response_action": self.response_action,
            "obligation_ref": self.obligation_ref,
            "chosen_surface": self.chosen_surface,
            "grammar_rule_ref": self.grammar_rule_ref,
            "reference_plan": self.reference_plan.as_dict(),
            "semantic_signature": self.semantic_signature,
            "alternatives": list(self.alternatives),
            "verification": dict(self.verification),
        }


@dataclass(frozen=True)
class ResponseEquivalenceReceipt:
    receipt_ref: str
    response_ref: str
    equivalent: bool
    action_preserved: bool
    obligation_preserved: bool
    target_preserved: bool
    query_kind_preserved: bool
    payload_preserved: bool
    source_signature: str
    realized_signature: str
    required_semantic_slots: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt_ref": self.receipt_ref,
            "response_ref": self.response_ref,
            "equivalent": self.equivalent,
            "action_preserved": self.action_preserved,
            "obligation_preserved": self.obligation_preserved,
            "target_preserved": self.target_preserved,
            "query_kind_preserved": self.query_kind_preserved,
            "payload_preserved": self.payload_preserved,
            "source_signature": self.source_signature,
            "realized_signature": self.realized_signature,
            "required_semantic_slots": list(self.required_semantic_slots),
            "reason": self.reason,
        }


class ReferencePlanner:
    @staticmethod
    def _relation(ref: str, output_frame: Any) -> tuple[str, str]:
        if ref == output_frame.speaker_ref:
            return "speaker", "first"
        if ref == output_frame.addressee_ref:
            return "addressee", "second"
        return "third_party", "third"

    @classmethod
    def plan(
        cls,
        refs: Sequence[str],
        output_frame: Any,
        *,
        possessive_refs: Sequence[str] = (),
        emphasis_refs: Sequence[str] = (),
    ) -> ReferencePlan:
        possessive = set(possessive_refs)
        emphasis = set(emphasis_refs)
        choices = []
        for ref in dict.fromkeys(refs):
            relation, person = cls._relation(ref, output_frame)
            choices.append(
                ReferenceChoice(
                    ref,
                    relation,
                    person,
                    possessive=ref in possessive,
                    emphasis=ref in emphasis,
                )
            )
        payload = (
            output_frame.speaker_ref,
            output_frame.addressee_ref,
            [item.as_dict() for item in choices],
        )
        return ReferencePlan(
            stable("reference-plan", payload),
            output_frame.speaker_ref,
            output_frame.addressee_ref,
            tuple(choices),
        )


class CanonicalResponseRealizer:
    """Realize one exact Response CSIR through language-pack grammar."""

    def __init__(self, store: Any, pack: Any):
        self.store = store
        self.pack = pack
        self.rules = tuple(pack.data.get("response_grammar", ()))
        self.reference_forms = tuple(pack.data.get("reference_realization", ()))
        self.predicate_forms = tuple(pack.data.get("predicate_realization", ()))

    @staticmethod
    def _literal(value: Any) -> Any:
        if isinstance(value, Mapping) and "literal" in value:
            return value["literal"].get("value")
        return value

    def _lex(self, value: Any, context: str | None = None) -> str:
        is_typed_literal = isinstance(value, Mapping) and "literal" in value
        raw = self._literal(value)
        if raw is None:
            return ""
        surface_context = bool(
            context in {"evidence", "object_surface", "predicate_surface"}
            or str(context or "").endswith("_surface")
            or str(context or "").startswith("surface_choice")
        )
        if is_typed_literal or surface_context:
            return str(raw)
        if isinstance(raw, str) and _SEMANTIC_REF.fullmatch(raw):
            surface = self.store.preferred(raw, self.pack.language, context)
            return "" if surface == raw else str(surface)
        return str(raw)

    @staticmethod
    def _query_kind(response: Any) -> str | None:
        return dict(getattr(response, "qualifiers", {}) or {}).get("query_kind")

    def _rule_candidates(self, response: Any) -> tuple[Mapping[str, Any], ...]:
        action = str(response.action)
        query_kind = self._query_kind(response)
        candidates: list[tuple[int, str, Mapping[str, Any]]] = []
        for rule in self.rules:
            when = dict(rule.get("when", {}))
            if when.get("action") not in (None, action):
                continue
            if when.get("query_kind") not in (None, query_kind):
                continue
            if when.get("has_bindings") is not None and bool(response.bindings) is not bool(when["has_bindings"]):
                continue
            if when.get("has_facts") is not None and bool(response.facts) is not bool(when["has_facts"]):
                continue
            required_qualifiers = dict(when.get("qualifiers", {}) or {})
            actual_qualifiers = dict(getattr(response, "qualifiers", {}) or {})
            if any(actual_qualifiers.get(key) != value for key, value in required_qualifiers.items()):
                continue
            specificity = sum(value is not None for key, value in when.items() if key != "qualifiers") + len(required_qualifiers)
            candidates.append((specificity, str(rule.get("ref", "")), rule))
        if not candidates:
            return ()
        top = max(item[0] for item in candidates)
        return tuple(item[2] for item in sorted(candidates) if item[0] == top)

    def _reference_form(self, choice: ReferenceChoice) -> str:
        candidates = []
        for record in self.reference_forms:
            features = dict(record.get("features", {}))
            if features.get("person") not in (None, choice.grammatical_person):
                continue
            if features.get("number") not in (None, choice.number):
                continue
            if bool(features.get("possessive", False)) != bool(choice.possessive):
                continue
            if bool(features.get("reflexive", False)) != bool(choice.reflexive):
                continue
            candidates.append((float(record.get("weight", 1.0)), str(record.get("surface", ""))))
        if not candidates:
            return self._lex(choice.semantic_ref)
        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1]

    def _predicate_form(self, choice: ReferenceChoice | None, *, lemma="be", tense="present") -> str:
        candidates = []
        for record in self.predicate_forms:
            features = dict(record.get("features", {}))
            if features.get("lemma") not in (None, lemma):
                continue
            if features.get("tense") not in (None, tense):
                continue
            if choice is not None:
                if features.get("person") not in (None, choice.grammatical_person):
                    continue
                if features.get("number") not in (None, choice.number):
                    continue
            candidates.append((float(record.get("weight", 1.0)), str(record.get("surface", ""))))
        if not candidates:
            return ""
        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1]

    @staticmethod
    def _fact_roles(response: Any) -> dict[str, Any]:
        slots: dict[str, Any] = {}
        query_kind = dict(getattr(response, "qualifiers", {}) or {}).get("query_kind")
        preferred_operator = {
            "designation_property": "op:designation",
            "operational_condition_query": "op:state",
            "state_query": "op:state",
            "type_query": "op:type",
            "relation_query": "op:relation",
        }.get(query_kind)
        facts = tuple(getattr(response, "facts", ()))
        ordered = sorted(facts, key=lambda fact: (fact.operator != preferred_operator, fact.ref))
        for fact in ordered:
            if fact.operator == "op:designation" and preferred_operator == "op:designation":
                slots.setdefault("subject_ref", fact.args.get("role:target"))
                slots.setdefault("property_ref", fact.args.get("role:label_type"))
                slots.setdefault("value", fact.args.get("role:surface"))
            elif fact.operator == "op:state":
                slots.setdefault("subject_ref", fact.args.get("role:subject"))
                slots.setdefault("property_ref", fact.args.get("role:dimension"))
                slots.setdefault("value", fact.args.get("role:value"))
            elif fact.operator == "op:type":
                slots.setdefault("subject_ref", fact.args.get("role:instance"))
                slots.setdefault("property_ref", "label:type")
                slots.setdefault("value", fact.args.get("role:class"))
            elif fact.operator == "op:relation":
                slots.setdefault("subject_ref", fact.args.get("role:subject"))
                slots.setdefault("relation_ref", fact.args.get("role:relation"))
                slots.setdefault("object_ref", fact.args.get("role:object"))
        return slots

    def _slots(self, response: Any, output_frame: Any) -> tuple[dict[str, str], ReferencePlan, dict[str, Any]]:
        raw = self._fact_roles(response)
        for key, value in dict(getattr(response, "qualifiers", {}) or {}).items():
            if key not in {"query_status", "coverage", "unresolved_variables"}:
                raw.setdefault(str(key), value)
        bindings = tuple(getattr(response, "bindings", ()))
        binding_values = []
        for binding in bindings:
            binding_values.extend(dict(binding).values())
        if binding_values:
            raw.setdefault("binding_values", tuple(binding_values))
            raw.setdefault("value", binding_values[0] if len(binding_values) == 1 else tuple(binding_values))
        evidence = tuple(getattr(response, "evidence_literals", ()))
        if evidence:
            raw.setdefault("evidence", evidence[0])
        raw["target_ref"] = getattr(response, "target_ref", None)

        refs = [
            value
            for key, value in raw.items()
            if key.endswith("_ref") and isinstance(value, str) and _SEMANTIC_REF.fullmatch(value)
        ]
        subject_ref = raw.get("subject_ref")
        base_plan = ReferencePlanner.plan(refs, output_frame)
        choices = {item.semantic_ref: item for item in base_plan.choices}
        slots: dict[str, str] = {"action": str(response.action), "query_kind": str(self._query_kind(response) or "")}
        for key, value in raw.items():
            if isinstance(value, tuple):
                slots[key] = ", ".join(self._lex(item, key) for item in value)
            else:
                slots[key] = self._lex(value, key) if value is not None else ""

        realized_choices: list[ReferenceChoice] = []
        for choice in base_plan.choices:
            form = self._reference_form(choice)
            realized_choices.append(replace(choice, selected_form=form))
        choices = {item.semantic_ref: item for item in realized_choices}
        if subject_ref and subject_ref in choices:
            ordinary = choices[subject_ref]
            slots["subject"] = ordinary.selected_form or ""
            slots["copula"] = self._predicate_form(ordinary)
            possessive_choice = ReferenceChoice(
                ordinary.semantic_ref,
                ordinary.relation_to_speaker,
                ordinary.grammatical_person,
                ordinary.number,
                possessive=True,
                selected_form=None,
            )
            possessive_choice = replace(possessive_choice, selected_form=self._reference_form(possessive_choice))
            slots["subject_possessive"] = possessive_choice.selected_form or ""
            realized_choices.append(possessive_choice)
        else:
            slots.setdefault("subject", "")
            slots.setdefault("subject_possessive", "")
            slots.setdefault("copula", "")
        slots.setdefault("property", slots.get("property_ref", ""))
        slots.setdefault("relation", slots.get("relation_ref", ""))
        slots.setdefault("target", slots.get("target_ref", ""))
        slots.setdefault("value", "")
        slots.setdefault("evidence", "")
        realized_plan = ReferencePlan(
            stable(
                "reference-plan-realized",
                base_plan.speaker_ref,
                base_plan.addressee_ref,
                [item.as_dict() for item in realized_choices],
            ),
            base_plan.speaker_ref,
            base_plan.addressee_ref,
            tuple(realized_choices),
        )
        return slots, realized_plan, raw

    @staticmethod
    def _required_semantic_slots(response: Any) -> frozenset[str]:
        qualifiers = dict(getattr(response, "qualifiers", {}) or {})
        action = str(response.action)
        query_kind = qualifiers.get("query_kind")
        query_actions = {
            "answer_bindings",
            "report_multiple_bindings",
            "confirm",
            "deny",
            "report_conflict",
            "report_target_uncertainty",
            "report_operational_condition",
        }
        base = {"query_ref", "query_kind"} if action in query_actions else set()
        if action in {"answer_bindings", "report_multiple_bindings"} and query_kind in {"designation_property", "state_query"}:
            return frozenset(base | {"subject_ref", "property_ref", "binding_values"})
        if action in {"answer_bindings", "report_multiple_bindings"} and query_kind == "type_query":
            return frozenset(base | {"subject_ref", "binding_values"})
        if action == "report_operational_condition":
            return frozenset(base | {"target_ref", "assessment_status", "snapshot_ref"})
        if action in {"confirm", "deny"} and query_kind == "relation_query":
            return frozenset(base | {"subject_ref", "object_surface", "relation_ref"})
        if action == "report_target_uncertainty" and query_kind == "relation_query":
            return frozenset(base | {"subject_ref", "object_surface", "relation_ref"})
        if action == "report_target_uncertainty" and query_kind == "type_query":
            return frozenset(base | {"subject_ref"})
        if action == "report_target_uncertainty" and query_kind in {"designation_property", "state_query"}:
            return frozenset(base | {"subject_ref", "property_ref"})
        if action == "request_learning_evidence":
            return frozenset({
                "evidence", "learning_plan_ref", "query_ref", "query_kind"
            })
        if action == "request_targeted_clarification":
            return frozenset({"evidence", "frontier_ref"})
        if action == "request_generic_clarification":
            return frozenset({"frontier_ref"})
        if action in {"answer_bindings", "report_multiple_bindings"} and query_kind == "capability_inventory_query":
            return frozenset(base | {"binding_values", "target_ref"})
        if action == "report_target_uncertainty" and query_kind == "capability_inventory_query":
            return frozenset(base | {"target_ref"})
        if action == "explain_surface_choice":
            return frozenset({"surface_decision_ref", "surface_choice_a", "surface_choice_b", "prior_response_ref", "prior_surface"})
        if action == "acknowledge_attributed_claim":
            return frozenset({"subject_ref", "predicate_surface", "claim_kind"})
        if action == "report_capability":
            return frozenset({"target_ref", "status"})
        return frozenset(base)

    @staticmethod
    def _template_fields(template: str) -> frozenset[str]:
        return frozenset(
            field_name
            for _literal, field_name, _format, _conversion in Formatter().parse(template)
            if field_name
        )

    def _format(self, template: str, slots: Mapping[str, str]) -> str:
        try:
            rendered = template.format_map({key: value for key, value in slots.items()})
        except (KeyError, ValueError):
            return ""
        rendered = " ".join(rendered.split()).strip()
        orthography = dict(self.pack.data.get("orthography", {}) or {})
        if orthography.get("sentence_initial_capitalization") and rendered:
            for index, char in enumerate(rendered):
                if char.isalpha():
                    rendered = rendered[:index] + char.upper() + rendered[index + 1:]
                    break
        return rendered

    def realize(self, response: Any, output_frame: Any) -> tuple[str, dict[str, Any]]:
        candidates = self._rule_candidates(response)
        if not candidates:
            return "", {
                "verified": False,
                "verification_mode": "exact_response_grammar",
                "reason": "no_semantic_equivalent_response_rule",
                "response_ref": response.response_ref,
            }
        signatures = {
            canonical(
                {
                    "template": rule.get("template"),
                    "required_slots": rule.get("required_slots"),
                    "semantic_slots": rule.get("semantic_slots"),
                    "when": rule.get("when"),
                }
            )
            for rule in candidates
        }
        if len(signatures) != 1:
            return "", {
                "verified": False,
                "verification_mode": "exact_response_grammar",
                "reason": "ambiguous_semantic_response_rules",
                "response_ref": response.response_ref,
                "candidate_rule_refs": sorted(str(x.get("ref")) for x in candidates),
            }
        rule = sorted(candidates, key=lambda item: str(item.get("ref", "")))[0]
        slots, reference_plan, raw = self._slots(response, output_frame)
        template = str(rule.get("template", ""))
        surface = self._format(template, slots)
        required = tuple(rule.get("required_slots", ()))
        missing = tuple(slot for slot in required if not slots.get(slot))
        declared_semantic = frozenset(rule.get("semantic_slots", ()))
        required_semantic = self._required_semantic_slots(response)
        missing_semantic_contract = tuple(sorted(required_semantic - declared_semantic))
        unresolved_semantic = tuple(sorted(slot for slot in required_semantic if raw.get(slot) in (None, "", (), [])))
        template_fields = self._template_fields(template)
        undeclared_template_fields = tuple(sorted(template_fields - set(required)))
        unused_required_fields = tuple(sorted(set(required) - template_fields))
        when = dict(rule.get("when", {}) or {})
        action_preserved = when.get("action") in (None, response.action)
        query_kind = self._query_kind(response)
        query_kind_preserved = when.get("query_kind") in (None, query_kind)
        rule_obligation = rule.get("obligation_ref")
        obligation_preserved = rule_obligation in (None, getattr(response, "obligation_ref", None))
        target_ref = getattr(response, "target_ref", None)
        target_preserved = target_ref is None or raw.get("target_ref") == target_ref
        if response.action == "report_operational_condition":
            target_preserved = target_ref == output_frame.speaker_ref
        payload_preserved = not (
            missing_semantic_contract
            or unresolved_semantic
            or undeclared_template_fields
            or unused_required_fields
        )
        equivalent = bool(
            surface
            and not missing
            and action_preserved
            and obligation_preserved
            and target_preserved
            and query_kind_preserved
            and payload_preserved
        )
        reason_parts = []
        if missing:
            reason_parts.append("missing_required_surface_slots")
        if missing_semantic_contract:
            reason_parts.append("grammar_rule_missing_semantic_contract")
        if unresolved_semantic:
            reason_parts.append("unresolved_semantic_payload")
        if undeclared_template_fields:
            reason_parts.append("template_fields_not_required")
        if unused_required_fields:
            reason_parts.append("required_fields_not_realized")
        if not action_preserved:
            reason_parts.append("action_changed")
        if not obligation_preserved:
            reason_parts.append("obligation_changed")
        if not target_preserved:
            reason_parts.append("target_changed")
        if not query_kind_preserved:
            reason_parts.append("query_kind_changed")
        source_signature = response.semantic_signature() if hasattr(response, "semantic_signature") else canonical(response.as_dict())
        realized_signature = canonical(
            {
                "response_ref": response.response_ref,
                "rule_ref": rule.get("ref"),
                "action": response.action,
                "obligation_ref": response.obligation_ref,
                "target_ref": target_ref,
                "query_kind": query_kind,
                "required_semantic_payload": {key: raw.get(key) for key in sorted(required_semantic)},
            }
        )
        receipt = ResponseEquivalenceReceipt(
            stable(
                "response-equivalence",
                response.response_ref,
                rule.get("ref"),
                source_signature,
                realized_signature,
                equivalent,
            ),
            response.response_ref,
            equivalent,
            action_preserved,
            obligation_preserved,
            target_preserved,
            query_kind_preserved,
            payload_preserved,
            source_signature,
            realized_signature,
            tuple(sorted(required_semantic)),
            "same_response_csir" if equivalent else ",".join(reason_parts or ["not_equivalent"]),
        )
        decision = SurfaceDecisionTrace(
            stable("surface-decision", response.response_ref, rule.get("ref"), surface, receipt.receipt_ref),
            response.response_ref,
            response.action,
            response.obligation_ref,
            surface,
            str(rule.get("ref", "")),
            reference_plan,
            source_signature,
            (),
            receipt.as_dict(),
        )
        return (
            surface if equivalent else "",
            {
                "verified": equivalent,
                "verification_mode": "exact_response_grammar",
                "language_pack_hash": self.pack.hash,
                "response_equivalence": receipt.as_dict(),
                "surface_decision": decision.as_dict(),
                "missing_slots": list(missing),
                "missing_semantic_contract": list(missing_semantic_contract),
                "unresolved_semantic_payload": list(unresolved_semantic),
                "undeclared_template_fields": list(undeclared_template_fields),
                "unused_required_fields": list(unused_required_fields),
            },
        )
