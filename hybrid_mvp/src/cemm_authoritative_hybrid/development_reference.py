"""Bounded output-only English reference; not realization, proof or admission.

Consumes actual CycleResult owners. It never interprets input text, publishes
focus, writes a store, or calls the historical realizer or neural model.
"""
from dataclasses import dataclass
import json
from types import MappingProxyType

from .authority import LinkedAuthority
from .config import RuntimeConfig
from .cycle import CycleStatus, SemanticMode
from .decision import DecisionAction, DecisionStatus
from .descriptions import DescriptionCompleteness
from .expressions import (
    ApplicationFiller, BoundVariable, GroundedReference, LiteralValue,
    QueryProjection, SemanticApplication, ScopeOperator, ExpressionLink,
    VariableBinder,
)
from .gaps import BudgetExhausted
from .r3_cycle import CycleResult
from .r3_designations import AdmittedDesignationReader
from .r3_effects import EffectReceipt
from .r3_response import validate_response_linkage

# Finite output records select explicit facts, not lexicographically chosen
# aliases. Morphology is output-only and cannot enter form classification.
_FORMS = MappingProxyType({
    "entity:alice": ("Alice", "name"), "entity:bob": ("Bob", "name"),
    "entity:carol": ("Carol", "name"), "entity:mary": ("Mary", "name"),
    "participant:system": ("CEMM", "name"),
    "entity:server": ("server", "count"), "entity:lamp": ("lamp", "count"),
    "entity:book": ("book", "count"), "concept:mother": ("mother", "count"),
    "concept:job_role": ("job role", "count"),
    "rel:likes": ("likes", "verbal"), "rel:owns": ("owns", "verbal"),
    "rel:mother_in_law": ("mother-in-law", "nominal"),
    "rel:has_partner": ("partner", "nominal"),
    "cap:respond": ("respond", "unary_capability"),
    "cap:learn_alias": ("learn aliases", "unary_capability"),
    "dim:availability": ("availability", "dimension"),
    "dim:power": ("power", "dimension"),
    "dim:marital_status": ("marital status", "dimension"),
    "dim:operational_status": ("status", "dimension"),
    "value:operating_normally": ("operating normally", "value"),
    "value:online": ("online", "value"), "value:offline": ("offline", "value"),
    "value:on": ("on", "value"), "value:off": ("off", "value"),
    "value:married": ("married", "value"),
    "value:available": ("available", "value"), "value:unavailable": ("unavailable", "value"),
    "value:enabled": ("enabled", "value"), "value:disabled": ("disabled", "value"),
    "event:leave": ("departure", "event_nominal"),
    "event:learn_alias": ("learning", "event_nominal"),
    "event:teach": ("instruction", "event_nominal"),
    "event:greeting": ("greetings", "event_nominal"),
    "event:farewell": ("farewell", "event_nominal"),
    "event:say": ("say", "saying"), "event:set_state": ("set", "setting"),
})
_EVENT_ROLES = MappingProxyType({
    "role:actor": "by", "role:addressee": "to", "role:content": "with content",
    "role:target": "with target", "role:dimension": "with dimension",
    "role:value": "with value", "role:surface": "with label",
})
_SCOPE = MappingProxyType({
    ("scope:polarity", "scope_value:polarity:negative"): "not",
    ("scope:polarity", "scope_value:polarity:positive"): "affirmed",
    ("scope:modality", "scope_value:modality:capability"): "capable of",
    ("scope:simulation", "scope_value:simulation:imagined"): "imagined",
    ("scope:tense", "scope_value:tense:past"): "in the past",
    ("scope:tense", "scope_value:tense:present"): "at present",
    ("scope:tense", "scope_value:tense:future"): "in the future",
})
_LINKS = MappingProxyType({
    "link:coordination": " and ", "link:conjunction": " and ",
    "link:disjunction": " or ", "link:contrast": " but ",
    "link:condition": " implies ", "link:cause": " causes ",
    "link:purpose": " for the purpose of ", "link:sequence": " then ",
})
_STANCE_PREFIXES = MappingProxyType({
    "epistemic_status:contested": "Unverified claim: ",
    "epistemic_status:attributed": "Attributed claim: ",
    "epistemic_status:unknown": "Unknown: ",
    "epistemic_status:conflict": "Conflicting evidence: ",
    "epistemic_status:supported": "Supported: ",
    "epistemic_status:contradicted": "Contradicted: ",
    "epistemic_status:observed": "Observed: ",
    "epistemic_status:partial": "Incomplete: ",
    "epistemic_status:pending": "Pending: ",
    "epistemic_status:denied": "Denied: ",
    "epistemic_status:simulated": "Hypothetical: ",
})


@dataclass(frozen=True)
class OutputLimitation:
    kind: str
    semantic_refs: tuple[str, ...]


@dataclass(frozen=True)
class DevelopmentDiagnostic:
    surface: str | None
    cycle_ref: str
    response_meaning_ref: str | None
    gap_ref: str | None
    designation_provenance: tuple[tuple[str, str, tuple[str, ...]], ...]
    output_rule_refs: tuple[str, ...]
    slot_coverage: tuple[tuple[str, str], ...]
    evidence_sources: tuple[tuple[int, str], ...]
    limitations: tuple[OutputLimitation, ...]
    development_only: bool = True

    def as_dict(self):
        return {
            "development_only": True, "surface": self.surface,
            "cycle_ref": self.cycle_ref, "response_meaning_ref": self.response_meaning_ref,
            "gap_ref": self.gap_ref,
            "designation_provenance": [dict(target_ref=t, designation_ref=d, provenance_refs=list(p))
                for t, d, p in self.designation_provenance],
            "output_rule_refs": list(self.output_rule_refs),
            "slot_coverage": [list(row) for row in self.slot_coverage],
            "evidence_sources": [dict(number=n, source_ref=s) for n, s in self.evidence_sources],
            "limitations": [dict(kind=row.kind, semantic_refs=list(row.semantic_refs)) for row in self.limitations],
        }


class _CannotPresent(Exception):
    def __init__(self, kind, *refs):
        self.limitation = OutputLimitation(kind, tuple(refs))


def _request_prefix(response):
    """Output grammar for an uncompleted request, retaining actual stance."""
    stance = _STANCE_PREFIXES.get(response.epistemic_status_ref)
    if stance is None:
        raise _CannotPresent("unsupported_response_stance", response.epistemic_status_ref)
    if response.discourse_action not in {
            "unknown", "deny", "clarify", "report_gap", "answer",
            "acknowledge", "acknowledge_operation", "acknowledge_observation"}:
        raise _CannotPresent("unsupported_request_discourse", response.discourse_action)
    outcome = ""
    if response.cycle_status is CycleStatus.OPERATION_FAILED:
        outcome = "Failed; "
    elif (response.cycle_status is CycleStatus.DENIED
            and response.epistemic_status_ref != "epistemic_status:denied"):
        outcome = "Denied; "
    elif response.discourse_action == "report_gap":
        outcome = "Evidence bound exceeded; "
    elif response.discourse_action == "clarify":
        outcome = "Clarification required; "
    return outcome + stance.removesuffix(": ") + "; no action completed; requested: "


class DevelopmentPresentationOwner:
    def __init__(self, authority, config, designation_reader, *, communicative_owner=None):
        if type(authority) is not LinkedAuthority or type(config) is not RuntimeConfig:
            raise TypeError("development presentation requires exact linked authority/config")
        if (type(designation_reader) is not AdmittedDesignationReader
                or designation_reader.authority is not authority):
            raise TypeError("development presentation requires the orientation designation reader")
        self.authority, self.config, self.reader = authority, config, designation_reader
        self.communicative_owner = communicative_owner
        # Validation is generation-static and indexed; no atom enumeration.
        for target, (surface, _kind) in _FORMS.items():
            rows = authority.designations.bounded_facts("target", target, "en", maximum=16)
            if not any(row.surface == surface for row in rows):
                raise ValueError("output-only record lacks explicit designation: " + target)

    def present(self, cycle):
        if type(cycle) is not CycleResult:
            raise TypeError("development reference requires exact CycleResult")
        cycle.__post_init__()  # Revalidate canonical cycle and actual source linkage.
        response = cycle.response_meaning
        provenance, rules, coverage = [], [], []
        sources = () if response is None else tuple(enumerate(response.source_refs, 1))
        def diagnostic(surface, limitations=()):
            return DevelopmentDiagnostic(surface, cycle.cycle_ref,
                None if response is None else response.response_meaning_ref,
                None if cycle.gap_receipt is None else cycle.gap_receipt.gap_ref,
                tuple(dict.fromkeys(provenance)), tuple(dict.fromkeys(rules)),
                tuple(dict.fromkeys(coverage)), sources, limitations)
        if response is None:
            gap = cycle.gap_receipt
            rules.append("output:early-gap-condition")
            conditions = {"budget_exhausted": "Interpretation exceeded its bound.",
                "verification_ambiguous": "Meaning is ambiguous.",
                "proposal_abstained": "Meaning is unresolved.",
                "verification_rejected": "Meaning is unresolved."}
            actions = {"request_reference_resolution": "Clarify the reference.",
                "request_proposal_review": "Review the interpretation.",
                "request_clarification": "Clarify the intended meaning.",
                "bound_cycle": "Reduce the request."}
            condition, action = conditions.get(gap.status), actions.get(gap.safe_response_action)
            coverage.extend(((gap.gap_ref, "condition"), (gap.gap_ref, "safe_response_action")))
            rules.append("output:early-gap-safe-action")
            return diagnostic(None if condition is None or action is None else condition + " " + action,
                (OutputLimitation("early_gap_without_response_meaning", (gap.gap_ref,)),))
        evaluation, effect = cycle.evaluation, cycle.effect_receipt
        meaning = cycle.verification.selected_meaning
        from .communicative import selected_owned_inputs
        program, receipt = selected_owned_inputs(cycle.proposal, cycle.verification, meaning)
        if (evaluation.situation.communicative_source is not None
                and evaluation.situation.communicative_source.evidence.packet_ref != cycle.input_ref):
            raise ValueError("communicative presentation evidence/input mismatch")
        validate_response_linkage(response=response, evaluation=evaluation,
            situation=evaluation.situation, effect=effect, meaning=meaning,
            communicative_owner=self.communicative_owner, orientation=cycle.orientation, program=program, receipt=receipt)
        try:
            with self.reader.batch(self.reader.stores.revision_pin()) as batch:
                renderer = _EnglishGraph(batch, evaluation.situation, provenance, rules, coverage)
                bundle = response.description_proof
                if bundle is not None and bundle.completeness is DescriptionCompleteness.SUFFICIENT:
                    expression = bundle.description.answer_expression
                    local = dict(zip(bundle.application_refs,
                        (a.application_ref for a in expression.applications), strict=True))
                    sources = tuple(enumerate(tuple(dict.fromkeys(c.source_ref for c in bundle.claims)), 1))
                    numbers = {source: number for number, source in sources}
                    texts = [f"Evidence [{numbers[c.source_ref]}] {'supports' if c.stance == 'support' else 'denies'}: "
                        + renderer.graph(expression, (local[c.application_ref],)) + "." for c in bundle.claims]
                    rules.append("output:signed-claim-attribution")
                    return diagnostic(" ".join(texts))
                content = renderer.graph(response.response_expression)
                expression = response.response_expression
                if (bundle is None and evaluation.situation.mode is SemanticMode.QUERY
                        and evaluation.decision.status is DecisionStatus.UNKNOWN
                        and evaluation.decision.action is DecisionAction.REQUEST_CLARIFICATION
                        and len(expression.applications) == len(expression.binders) == 1
                        and not expression.scope_operators and not expression.expression_links
                        and expression.applications[0].operator == "op:designation"
                        and expression.applications[0].predicate_ref == "label:lexical"):
                    literal = dict((r.role_ref, r.filler) for r in expression.applications[0].roles)["role:surface"]
                    if type(literal) is LiteralValue and literal.value_type == "string":
                        rules.append("output:unknown-lexical-clarification")
                        coverage.extend(((response.response_meaning_ref, "epistemic_status"),
                            (response.response_meaning_ref, "discourse_action"), (effect.receipt_ref, "effect_outcome")))
                        return diagnostic("Meaning unknown. What does " + json.dumps(literal.value, ensure_ascii=True) + " mean?")
                if bundle is not None:
                    prefix = {"missing": "No sufficient evidence for: ", "conflict": "Conflicting evidence for: ",
                        "partial": "Incomplete evidence for: ", "budget_exhausted": "Evidence bound exceeded for: "}[bundle.completeness.value]
                elif response.learning_plan is not None:
                    prefix = "Pending review; no acquisition: "
                elif type(effect) is EffectReceipt and effect.status.value == "committed":
                    prefix = "Completed effect: "
                elif evaluation.situation.mode is SemanticMode.REQUEST:
                    prefix = _request_prefix(response)
                elif evaluation.decision.action is DecisionAction.RESPOND:
                    prefix = "Response: "
                else:
                    prefix = _STANCE_PREFIXES.get(response.epistemic_status_ref)
                    if prefix is None:
                        raise _CannotPresent("unsupported_response_stance", response.epistemic_status_ref)
                rules.append("output:response-stance-effect")
                coverage.extend(((response.response_meaning_ref, "epistemic_status"),
                    (response.response_meaning_ref, "discourse_action"), (effect.receipt_ref, "effect_outcome")))
                return diagnostic(prefix + content + ("?" if renderer.simple_variable_query else "."))
        except _CannotPresent as failure:
            return diagnostic(None, (failure.limitation,))
        except BudgetExhausted:
            return diagnostic(None, (OutputLimitation("designation_budget_exhausted", (response.response_meaning_ref,)),))


class _EnglishGraph:
    def __init__(self, batch, situation, provenance, rules, coverage):
        self.batch, self.situation = batch, situation
        self.provenance, self.rules, self.coverage = provenance, rules, coverage

    def label(self, target, *, referent=False):
        if referent and target == self.situation.addressee_ref:
            self.rules.append("output:participant-perspective")
            return "I"
        if referent and target == self.situation.speaker_ref:
            self.rules.append("output:participant-perspective")
            return "you"
        record = _FORMS.get(target)
        if record is None:
            raise _CannotPresent("missing_output_designation_rule", target)
        surface, kind = record
        rows = self.batch.for_target(target, "en", maximum=16)
        selected = [row for row in rows if row.designation.surface == surface]
        if not selected:
            raise _CannotPresent("missing_explicit_designation", target)
        for row in selected:
            self.provenance.append((target, row.designation.designation_fact_ref, row.provenance_refs))
        self.rules.append("output:designation:" + target)
        return "the " + surface if referent and kind == "count" else surface

    def graph(self, expression, roots=None):
        self.simple_variable_query = False
        nodes = {n.application_ref: n for n in expression.applications}
        nodes.update((n.scope_ref, n) for n in expression.scope_operators)
        nodes.update((n.link_ref, n) for n in expression.expression_links)
        nodes.update((n.binder_ref, n) for n in expression.binders)
        nodes.update((n.projection_ref, n) for n in expression.query_projections)
        if expression.unresolved_fillers:
            raise _CannotPresent("unresolved_semantic_filler", *(u.unresolved_ref for u in expression.unresolved_fillers))
        def filler(value, *, referent=True):
            if type(value) is GroundedReference:
                return self.label(value.target_ref, referent=referent)
            if type(value) is LiteralValue:
                self.rules.append("output:literal")
                return json.dumps(value.value, ensure_ascii=True)
            if type(value) is BoundVariable:
                raise _CannotPresent("unbound_output_variable", value.variable_ref)
            if type(value) is ApplicationFiller:
                return "(" + node(value.node_ref) + ")"
            raise _CannotPresent("unsupported_filler", value.unresolved_ref)
        def possessive(value):
            text = filler(value)
            return "my" if text == "I" else "your" if text == "you" else text + "'s"
        def node(ref):
            n = nodes[ref]
            self.coverage.append((ref, "node"))
            if type(n) is QueryProjection:
                self.rules.append("output:query-projection")
                self.coverage.extend(((ref, "requested_content"), (ref, "target")))
                return n.requested_content + " of " + self.label(n.target_ref, referent=True)
            if type(n) is ScopeOperator:
                word = _SCOPE.get((n.operator_type, n.value_ref))
                if word is None: raise _CannotPresent("unsupported_scope", ref, n.operator_type, n.value_ref)
                self.rules.append("output:scope:" + n.operator_type)
                self.coverage.extend(((ref, "value"), (ref, "operand")))
                return word + " (" + node(n.operand_ref) + ")"
            if type(n) is ExpressionLink:
                self.rules.append("output:link:" + n.link_type)
                self.coverage.extend((ref, str(i)) for i in range(len(n.operand_refs)))
                return _LINKS[n.link_type].join("(" + node(r) + ")" for r in n.operand_refs)
            if type(n) is VariableBinder:
                body = nodes[n.body_ref]
                # Only this complete lexical answer-domain construction is licensed.
                if (type(body) is SemanticApplication and body.operator == "op:designation"
                        and {r.role_ref: r.filler for r in body.roles}.get("role:target") == BoundVariable(n.variable_ref)):
                    self.rules.append("output:lexical-answer-binder")
                    self.coverage.extend(((ref, "variable"), (ref, "body")))
                    return application(body, lexical_query=True)
                # A finite question grammar, not a general free-variable renderer.
                # The binder carries no person-kind restriction or existence claim.
                if (type(body) is SemanticApplication
                        and len(expression.applications) == len(expression.binders) == 1
                        and expression.root_refs == (ref,)
                        and not expression.scope_operators and not expression.expression_links
                        and not expression.query_projections and roots is None):
                    variable_roles = tuple(r.role_ref for r in body.roles
                        if r.filler == BoundVariable(n.variable_ref))
                    licensed_roles = (() if body.operator not in {"op:type", "op:relation"}
                        else ("role:instance",) if body.operator == "op:type"
                        else ("role:subject", "role:object")
                        if _FORMS.get(body.predicate_ref, (None, None))[1] == "verbal" else ())
                    if (len(variable_roles) == 1 and variable_roles[0] in licensed_roles
                            and all(type(r.filler) is GroundedReference
                                or r.filler == BoundVariable(n.variable_ref) for r in body.roles)):
                        self.rules.append("output:simple-variable-question")
                        self.coverage.extend(((ref, "variable"), (ref, "body"),
                            (body.application_ref, "node")))
                        content = application(body, question_variable=n.variable_ref)
                        self.simple_variable_query = True
                        return content
                raise _CannotPresent("unsupported_binder", ref, n.variable_ref)
            return application(n)
        def application(n, lexical_query=False, question_variable=None):
            if n.qualifiers:
                raise _CannotPresent("unsupported_qualifiers", n.application_ref, *(r.role_ref for r in n.qualifiers))
            r = {row.role_ref: row.filler for row in n.roles}
            self.rules.append("output:skeleton:" + n.operator)
            self.coverage.extend(((n.application_ref, "operator"), (n.application_ref, "predicate")))
            self.coverage.extend((n.application_ref, role) for role in r)
            def exact(roles):
                if set(r) != set(roles): raise _CannotPresent("unsupported_complete_role_rule", n.application_ref, *r)
            def question_filler(value, *, referent=True):
                if question_variable is not None and value == BoundVariable(question_variable):
                    self.rules.append("output:neutral-query-variable")
                    return "who or what"
                return filler(value, referent=referent)
            if n.operator == "op:type":
                exact(("role:instance", "role:class"))
                if r["role:class"] != GroundedReference(n.predicate_ref):
                    raise _CannotPresent("type_predicate_mismatch", n.application_ref)
                subject = question_filler(r["role:instance"])
                copula = "am" if subject == "I" else "are" if subject == "you" else "is"
                return subject + " " + copula + " a " + filler(r["role:class"], referent=False)
            if n.operator == "op:relation":
                if _FORMS.get(n.predicate_ref, (None, None))[1] == "unary_capability":
                    exact(("role:subject",))
                    self.rules.append("output:unary-capability")
                    return filler(r["role:subject"]) + " can " + self.label(n.predicate_ref)
                exact(("role:subject", "role:object"))
                pred = self.label(n.predicate_ref)
                subject = question_filler(r["role:subject"])
                if _FORMS[n.predicate_ref][1] == "nominal":
                    return subject + (" am " if subject == "I" else " are " if subject == "you" else " is ") + possessive(r["role:object"]) + " " + pred
                if _FORMS[n.predicate_ref][1] != "verbal": raise _CannotPresent("unsupported_relation_morphology", n.predicate_ref)
                verb = {"likes": "like", "owns": "own"}[pred] if subject in {"I", "you"} else pred
                object_text = question_filler(r["role:object"])
                return subject + " " + verb + " " + ("me" if object_text == "I" else object_text)
            if n.operator == "op:state":
                exact(("role:subject", "role:dimension", "role:value"))
                if r["role:dimension"] != GroundedReference(n.predicate_ref): raise _CannotPresent("state_predicate_mismatch", n.application_ref)
                return possessive(r["role:subject"]) + " " + self.label(n.predicate_ref) + " is " + filler(r["role:value"], referent=False)
            if n.operator == "op:designation":
                exact(("role:label_type", "role:surface", "role:target"))
                if n.predicate_ref != "label:lexical": raise _CannotPresent("unsupported_label_type", n.predicate_ref)
                self.rules.append("output:lexical-label-kind")
                surface = filler(r["role:surface"])
                return "meaning of " + surface if lexical_query else surface + " means " + filler(r["role:target"], referent=False)
            if n.operator == "op:event":
                pred = self.label(n.predicate_ref)
                kind = _FORMS[n.predicate_ref][1]
                if kind in {"saying", "setting"}: pred = kind
                elif kind != "event_nominal": raise _CannotPresent("unsupported_event_morphology", n.predicate_ref)
                if any(role not in _EVENT_ROLES for role in r): raise _CannotPresent("unsupported_event_role", n.application_ref, *r)
                parts = []
                for role, value in r.items():
                    text = filler(value, referent=role not in {"role:dimension", "role:value"})
                    if text == "I": text = "me"
                    parts.append(_EVENT_ROLES[role] + " " + text)
                return pred + " " + " ".join(parts)
            raise _CannotPresent("unsupported_operator", n.operator)
        return "; ".join(node(ref) for ref in (expression.root_refs if roots is None else roots))
