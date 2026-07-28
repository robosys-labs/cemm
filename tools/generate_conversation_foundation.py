#!/usr/bin/env python3
"""Generate reviewed conversational authority without ref-name lexicalization.

Semantic atoms are not automatically language forms. Only surfaces listed in
REVIEWED_DESIGNATIONS are published to the designation index.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def atom(ref: str, kind: str, **metadata: Any) -> dict[str, Any]:
    return {"ref": ref, "kind": kind, "metadata": {"foundational": True, **metadata}}


def lit(value: Any, kind: str = "text") -> dict[str, Any]:
    return {"literal": {"type": kind, "value": value}}


def fact(operator: str, args: dict[str, Any], ref: str | None = None, source: str = "seed") -> dict[str, Any]:
    output = {
        "operator": operator,
        "args": args,
        "stance": "support",
        "confidence": 1.0,
        "authority_status": "reviewed",
        "source_ref": source,
    }
    if ref:
        output["fact_ref"] = ref
    return output


def rel(subject: str, relation: str, object_ref: str, ref: str | None = None) -> dict[str, Any]:
    return fact(
        "op:relation",
        {"role:subject": subject, "role:relation": relation, "role:object": object_ref},
        ref,
    )


def designation(
    target: str,
    surface: str,
    label: str = "label:lexical",
    language: str = "en",
    preferred: bool = True,
    prior: float = 1.0,
) -> dict[str, Any]:
    script = "Latn"
    return fact(
        "op:designation",
        {
            "role:target": target,
            "role:label_type": label,
            "role:surface": lit(surface),
            "role:language": lit(language),
            "role:script": lit(script),
            "role:prior": lit(float(prior), "float"),
            "role:preferred": lit(bool(preferred), "bool"),
        },
    )


CONCEPTS = [
    "concept:agent", "concept:participant", "concept:person", "concept:entity",
    "concept:object", "concept:place", "concept:time", "concept:quantity",
    "concept:language", "concept:language_form", "concept:lexical_form",
    "concept:construction", "concept:designation", "concept:identity",
    "concept:definition", "concept:learning", "concept:teaching", "concept:memory",
    "concept:knowledge", "concept:question", "concept:answer",
    "concept:clarification", "concept:correction", "concept:reference",
    "concept:context", "concept:conversation", "concept:communication",
    "concept:preference", "concept:emotion", "concept:location",
    "concept:operation", "concept:resource", "concept:process", "concept:result",
    "concept:property", "concept:identifier", "concept:abbreviation",
    "concept:acronym", "concept:laughing_out_loud", "concept:gratitude",
    "concept:apology", "concept:agreement", "concept:disagreement",
    "concept:possibility", "concept:necessity",
]

RELATIONS = [
    "rel:equivalent_to", "rel:refers_to", "rel:synonym_of", "rel:antonym_of",
    "rel:part_of", "rel:located_in", "rel:owns", "rel:prefers", "rel:knows",
    "rel:about", "rel:before", "rel:after", "rel:caused_by", "rel:enables",
    "rel:requires", "rel:source_of", "rel:evidence_for", "rel:has_property",
    "rel:has_identifier", "rel:has_definition", "rel:communicates_with",
    "rel:answers", "rel:asks", "rel:corrects", "rel:clarifies",
    "rel:has_semantic_frame", "rel:licenses_learning_contract",
]

EVENTS = [
    "event:ask", "event:answer", "event:learn", "event:teach", "event:remember",
    "event:forget", "event:clarify", "event:correct", "event:retract",
    "event:thank", "event:apologize", "event:communicate", "event:define",
    "event:identify", "event:name", "event:confirm", "event:deny", "event:explain",
    "event:want", "event:intend", "event:say", "event:know", "event:translate",
    "event:infer", "event:acknowledge", "event:react",
]

LABELS = [
    "label:title", "label:identifier", "label:username", "label:abbreviation",
    "label:acronym", "label:nickname", "label:expansion", "label:translation",
]

CAPABILITIES = [
    "cap:learn", "cap:query", "cap:clarify", "cap:remember", "cap:designate",
    "cap:explain",
]

RESOURCES = [
    "resource:semantic_store", "resource:designation_index", "resource:form_processor",
    "resource:inference_engine", "resource:common_ground",
]

DIMENSIONS = [
    "dim:availability", "dim:confidence", "dim:location", "dim:quantity",
    "dim:preference", "dim:emotional_state", "dim:memory_status",
    "dim:learning_status", "dim:communication_status",
]

VALUES = [
    "value:available", "value:unavailable", "value:known", "value:remembered",
    "value:forgotten", "value:learning", "value:learned_confirmed",
    "value:communicating", "value:idle", "value:positive", "value:neutral",
    "value:possible", "value:necessary",
]

# Explicit reviewed language publication. No ref-name derivation is permitted.
REVIEWED_DESIGNATIONS: dict[str, list[tuple[str, str, str, bool, float]]] = {
    "concept:laughing_out_loud": [
        ("laughing out loud", "label:name_full", "en", True, 1.8),
        ("LOL", "label:acronym", "en", True, 1.7),
        ("lol", "label:lexical", "en", True, 1.6),
    ],
    "concept:meaning": [
        ("meaning", "label:lexical", "en", True, 1.3),
        ("sense", "label:lexical", "en", False, 0.8),
        ("significado", "label:translation", "es", True, 1.1),
    ],
    "concept:definition": [("definition", "label:lexical", "en", True, 1.3)],
    "concept:learning": [
        ("learning", "label:lexical", "en", True, 1.2),
        ("aprendizaje", "label:translation", "es", True, 1.1),
    ],
    "concept:memory": [
        ("memory", "label:lexical", "en", True, 1.2),
        ("memoria", "label:translation", "es", True, 1.1),
    ],
    "concept:knowledge": [
        ("knowledge", "label:lexical", "en", True, 1.2),
        ("conocimiento", "label:translation", "es", True, 1.1),
    ],
    "concept:question": [
        ("question", "label:lexical", "en", True, 1.2),
        ("pregunta", "label:translation", "es", True, 1.1),
    ],
    "concept:answer": [
        ("answer", "label:lexical", "en", True, 1.2),
        ("respuesta", "label:translation", "es", True, 1.1),
    ],
    "concept:clarification": [
        ("clarification", "label:lexical", "en", True, 1.2),
        ("aclaración", "label:translation", "es", True, 1.1),
    ],
    "concept:conversation": [
        ("conversation", "label:lexical", "en", True, 1.2),
        ("conversación", "label:translation", "es", True, 1.1),
    ],
    "concept:context": [("context", "label:lexical", "en", True, 1.2)],
    "concept:identity": [("identity", "label:lexical", "en", True, 1.2)],
    "concept:property": [("property", "label:lexical", "en", True, 1.2)],
    "concept:preference": [("preference", "label:lexical", "en", True, 1.2)],
    "concept:location": [("location", "label:lexical", "en", True, 1.2)],
    "concept:quantity": [("quantity", "label:lexical", "en", True, 1.2)],
    "rel:knows": [("know", "label:lexical", "en", True, 1.5)],
    "rel:prefers": [("prefer", "label:lexical", "en", True, 1.3)],
    "rel:refers_to": [("refer to", "label:lexical", "en", True, 1.2)],
    "rel:equivalent_to": [("equivalent to", "label:lexical", "en", True, 1.1)],
    "rel:located_in": [("located in", "label:lexical", "en", True, 1.1)],
    "event:ask": [("ask", "label:lexical", "en", True, 1.3)],
    "event:answer": [("answer", "label:lexical", "en", True, 1.3)],
    "event:learn": [("learn", "label:lexical", "en", True, 1.5)],
    "event:teach": [("teach", "label:lexical", "en", True, 1.4)],
    "event:remember": [("remember", "label:lexical", "en", True, 1.4)],
    "event:forget": [("forget", "label:lexical", "en", True, 1.3)],
    "event:clarify": [("clarify", "label:lexical", "en", True, 1.2)],
    "event:correct": [("correct", "label:lexical", "en", True, 1.2)],
    "event:retract": [("retract", "label:lexical", "en", True, 1.1)],
    "event:thank": [("thank", "label:lexical", "en", True, 1.2)],
    "event:apologize": [("apologize", "label:lexical", "en", True, 1.2)],
    "event:communicate": [("communicate", "label:lexical", "en", True, 1.2)],
    "event:define": [
        ("define", "label:lexical", "en", True, 1.3),
        ("mean", "label:lexical", "en", True, 1.25),
        ("signify", "label:lexical", "en", False, 1.0),
    ],
    "event:identify": [("identify", "label:lexical", "en", True, 1.2)],
    "event:name": [("name", "label:lexical", "en", True, 1.2)],
    "event:confirm": [("confirm", "label:lexical", "en", True, 1.2)],
    "event:deny": [("deny", "label:lexical", "en", True, 1.2)],
    "event:explain": [("explain", "label:lexical", "en", True, 1.2)],
    "event:want": [("want", "label:lexical", "en", True, 1.4)],
    "event:intend": [("intend", "label:lexical", "en", True, 1.2)],
    "event:say": [("say", "label:lexical", "en", True, 1.3)],
    "event:know": [("know", "label:lexical", "en", True, 1.4)],
    "event:translate": [("translate", "label:lexical", "en", True, 1.2)],
    "event:infer": [("infer", "label:lexical", "en", True, 1.1)],
    "event:acknowledge": [("acknowledge", "label:lexical", "en", True, 1.0)],
    # Capability labels remain nominal; verbs denote events and modal composition
    # derives capability assessments.
    "cap:learn": [("learning ability", "label:lexical", "en", True, 1.1)],
    "cap:query": [("query ability", "label:lexical", "en", True, 1.0)],
    "cap:clarify": [("clarification ability", "label:lexical", "en", True, 1.0)],
    "cap:remember": [("memory ability", "label:lexical", "en", True, 1.0)],
    "cap:designate": [("designation ability", "label:lexical", "en", True, 1.0)],
    "cap:explain": [("explanation ability", "label:lexical", "en", True, 1.0)],
    "label:title": [("title", "label:lexical", "en", True, 1.0)],
    "label:identifier": [("identifier", "label:lexical", "en", True, 1.0)],
    "label:username": [("username", "label:lexical", "en", True, 1.0)],
    "label:abbreviation": [("abbreviation", "label:lexical", "en", True, 1.0)],
    "label:acronym": [("acronym", "label:lexical", "en", True, 1.0)],
    "label:nickname": [("nickname", "label:lexical", "en", True, 1.0)],
    "label:translation": [("translation", "label:lexical", "en", True, 1.0)],
}


# Reviewed inflection publication. These forms are explicit language authority,
# not names derived from semantic refs. The preferred lemma entries remain in
# REVIEWED_DESIGNATIONS; inflections are non-preferred designations of the same
# semantic target. A future morphology resolver may replace this finite bootstrap
# without changing the semantic substrate.
REVIEWED_INFLECTIONS: dict[str, tuple[str, ...]] = {
    "rel:knows": ("knows", "knew", "known", "knowing"),
    "rel:prefers": ("prefers", "preferred", "preferring"),
    "event:ask": ("asks", "asked", "asking"),
    "event:answer": ("answers", "answered", "answering"),
    "event:learn": ("learns", "learned", "learning"),
    "event:teach": ("teaches", "taught", "teaching"),
    "event:remember": ("remembers", "remembered", "remembering"),
    "event:forget": ("forgets", "forgot", "forgotten", "forgetting"),
    "event:clarify": ("clarifies", "clarified", "clarifying"),
    "event:correct": ("corrects", "corrected", "correcting"),
    "event:retract": ("retracts", "retracted", "retracting"),
    "event:thank": ("thanks", "thanked", "thanking"),
    "event:apologize": ("apologizes", "apologized", "apologizing"),
    "event:communicate": ("communicates", "communicated", "communicating"),
    "event:define": (
        "defines", "defined", "defining",
        "means", "meant", "meaning",
        "signifies", "signified", "signifying",
    ),
    "event:identify": ("identifies", "identified", "identifying"),
    "event:name": ("names", "named", "naming", "call", "calls", "called", "calling"),
    "event:confirm": ("confirms", "confirmed", "confirming"),
    "event:deny": ("denies", "denied", "denying"),
    "event:explain": ("explains", "explained", "explaining"),
    "event:want": ("wants", "wanted", "wanting"),
    "event:intend": ("intends", "intended", "intending"),
    "event:say": ("says", "said", "saying"),
    "event:know": ("knows", "knew", "known", "knowing"),
    "event:translate": ("translates", "translated", "translating"),
    "event:infer": ("infers", "inferred", "inferring"),
    "event:acknowledge": ("acknowledges", "acknowledged", "acknowledging"),
}

FRAME_RELATION = "rel:has_semantic_frame"
DESIGNATION_LEARNING_CONTRACT = "contract:designation_learning"
DESIGNATION_ANSWER_CONTRACT = "contract:designation_target_answer"
DESIGNATION_LEARNING_GOAL = "goal:acquire_designation"


def semantic_frame(
    ref: str,
    *,
    ports_provided: list[str],
    ports_required: list[str] | None = None,
    roles: list[dict[str, Any]] | None = None,
    score: float = 0.2,
    replace_defaults: bool = True,
    **metadata: Any,
) -> dict[str, Any]:
    return atom(
        ref,
        "semantic_frame",
        conversation_foundation=True,
        semantic_frame={
            "contribution_kind": "predicate",
            "predicate": True,
            "ports_provided": ports_provided,
            "ports_required": list(ports_required or []),
            "roles": list(roles or []),
            "score": score,
            "replace_defaults": replace_defaults,
            "kernel_operator_ref": "op:event",
            **metadata,
        },
    )


def frame_role(role_ref: str, *, required: bool, filler_kinds: list[str]) -> dict[str, Any]:
    return {
        "role_ref": role_ref,
        "required": required,
        "filler_kinds": filler_kinds,
        "cardinality": "one",
    }


FRAME_SPECS: dict[str, tuple[str, list[dict[str, Any]], list[str], dict[str, Any]]] = {
    "event:learn": (
        "frame:event-learn",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True},
    ),
    "event:teach": (
        "frame:event-teach",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:target", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:target", "argument:object"],
        {"proposition_taking": True},
    ),
    "event:remember": (
        "frame:event-remember",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True},
    ),
    "event:forget": (
        "frame:event-forget",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True},
    ),
    "event:define": (
        "frame:event-define",
        [frame_role("role:actor", required=False, filler_kinds=["atom"]),
         frame_role("role:target", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:object"],
        {"designation_effect": True},
    ),
    "event:want": (
        "frame:event-want",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True, "scope_kind": "desire"},
    ),
    "event:intend": (
        "frame:event-intend",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True, "scope_kind": "intention"},
    ),
    "event:know": (
        "frame:event-know",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:target", required=False, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True, "epistemic_event": True},
    ),
    "event:say": (
        "frame:event-say",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:target", required=False, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True},
    ),
    "event:translate": (
        "frame:event-translate",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True},
    ),
    "event:infer": (
        "frame:event-infer",
        [frame_role("role:actor", required=True, filler_kinds=["atom"]),
         frame_role("role:object", required=True, filler_kinds=["atom"])],
        ["argument:subject", "argument:object"],
        {"proposition_taking": True},
    ),
}


def build() -> dict[str, Any]:
    atoms: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []

    for ref in CONCEPTS:
        atoms.append(atom(ref, "concept", conversation_foundation=True))
    internal_relations = {"rel:has_semantic_frame", "rel:licenses_learning_contract"}
    for ref in RELATIONS:
        atoms.append(atom(
            ref,
            "relation_type",
            conversation_foundation=True,
            user_visible=ref not in internal_relations,
        ))
    for ref in EVENTS:
        atoms.append(atom(ref, "event_type", conversation_foundation=True))
    for ref in LABELS:
        atoms.append(atom(ref, "label_type", conversation_foundation=True))
    for ref in CAPABILITIES:
        atoms.append(atom(ref, "capability", conversation_foundation=True))
    for ref in RESOURCES:
        atoms.append(atom(ref, "resource", conversation_foundation=True))
    for ref in DIMENSIONS:
        atoms.append(atom(ref, "state_dimension", conversation_foundation=True, exclusive=True, cardinality="one", domain_type="categorical"))
    for ref in VALUES:
        atoms.append(atom(ref, "value", conversation_foundation=True))

    atoms.extend([
        atom(
            DESIGNATION_LEARNING_CONTRACT,
            "concept",
            conversation_foundation=True,
            learning_contract={
                "goal_ref": DESIGNATION_LEARNING_GOAL,
                "capability_ref": "cap:learn",
                "commit_operator_ref": "op:designation",
                "answer_contract_ref": DESIGNATION_ANSWER_CONTRACT,
                "label_type_ref": "label:lexical",
                "expected_target_kinds": [
                    "concept", "entity", "event_type", "relation_type",
                    "state_dimension", "value", "label_type", "capability", "time",
                ],
                "licensed_query_kinds": [
                    "designation_learning", "meaning_query", "designation_query",
                ],
            },
        ),
        atom(DESIGNATION_ANSWER_CONTRACT, "concept", conversation_foundation=True),
        atom(DESIGNATION_LEARNING_GOAL, "goal", conversation_foundation=True),
    ])
    for target_ref, (frame_ref, roles, required_ports, metadata) in FRAME_SPECS.items():
        atoms.append(semantic_frame(
            frame_ref,
            ports_provided=["predicate:event"],
            ports_required=required_ports,
            roles=roles,
            **metadata,
        ))

    for child, parent in (
        ("label:title", "label:lexical"),
        ("label:identifier", "label:lexical"),
        ("label:username", "label:identifier"),
        ("label:abbreviation", "label:lexical"),
        ("label:acronym", "label:abbreviation"),
        ("label:nickname", "label:name_alias"),
        ("label:expansion", "label:lexical"),
        ("label:translation", "label:lexical"),
    ):
        facts.append(rel(child, "rel:subtype_of", parent))

    for child, parent in (
        ("concept:agent", "concept:entity"),
        ("concept:participant", "concept:entity"),
        ("concept:person", "concept:participant"),
        ("concept:object", "concept:entity"),
        ("concept:place", "concept:entity"),
        ("concept:language_form", "concept:information"),
        ("concept:lexical_form", "concept:language_form"),
        ("concept:construction", "concept:language_form"),
        ("concept:designation", "concept:information"),
        ("concept:definition", "concept:information"),
        ("concept:question", "concept:query"),
        ("concept:answer", "concept:response"),
        ("concept:clarification", "concept:response"),
        ("concept:correction", "concept:response"),
        ("concept:conversation", "concept:communication"),
        ("concept:operation", "concept:process"),
        ("concept:learning", "concept:process"),
        ("concept:teaching", "concept:process"),
        ("concept:memory", "concept:resource"),
        ("concept:knowledge", "concept:information"),
        ("concept:identifier", "concept:designation"),
        ("concept:abbreviation", "concept:designation"),
        ("concept:acronym", "concept:abbreviation"),
    ):
        facts.append(rel(child, "rel:subtype_of", parent))

    for target_ref, (frame_ref, _roles, _required_ports, _metadata) in FRAME_SPECS.items():
        facts.append(rel(target_ref, FRAME_RELATION, frame_ref))

    # Greeting is owned by base authority; this foundation may only reference it.
    greeting_frame_ref = "frame:event-greeting-discourse"
    atoms.append(atom(
        greeting_frame_ref,
        "semantic_frame",
        conversation_foundation=True,
        semantic_frame={
            "contribution_kind": "discourse",
            "predicate": False,
            "ports_provided": ["discourse:greeting"],
            "ports_required": [],
            "roles": [],
            "score": 0.35,
            "replace_defaults": False,
            "discourse_act": "greeting",
        },
    ))
    facts.append(rel("event:greeting", FRAME_RELATION, greeting_frame_ref))
    facts.append(rel("concept:laughing_out_loud", FRAME_RELATION, "frame:reaction-amusement"))
    atoms.append(atom(
        "frame:reaction-amusement",
        "semantic_frame",
        conversation_foundation=True,
        semantic_frame={
            "contribution_kind": "discourse",
            "predicate": False,
            "ports_provided": ["discourse:reaction"],
            "ports_required": [],
            "roles": [],
            "score": 0.3,
            "replace_defaults": False,
            "reaction_kind": "amusement",
        },
    ))

    facts.append(rel("event:learn", "rel:requires_capability", "cap:learn"))
    facts.append(rel("event:remember", "rel:requires_capability", "cap:remember"))
    facts.append(rel("event:define", "rel:requires_capability", "cap:designate"))
    facts.append(rel("event:ask", "rel:requires_capability", "cap:query"))
    facts.append(rel("event:explain", "rel:requires_capability", "cap:explain"))
    facts.append(rel("cap:learn", "rel:licenses_learning_contract", DESIGNATION_LEARNING_CONTRACT))

    # The capability inventory query starts from the current participant and
    # follows ordinary TYPE → entitlement graph edges. Keep the self profile
    # explicit rather than inferring it from an internal ref name.
    facts.append(fact(
        "op:type",
        {"role:instance": "participant:system", "role:class": "concept:digital_agent"},
        "seed:system-digital-agent-type",
    ))

    for capability in CAPABILITIES:
        facts.append(rel("concept:digital_agent", "rel:entitles_capability", capability))
    for resource in RESOURCES:
        facts.append(rel("concept:digital_agent", "rel:entitles_resource", resource))

    for capability, dependency in (
        ("cap:learn", "cap:interpret"),
        ("cap:learn", "resource:semantic_store"),
        ("cap:learn", "resource:designation_index"),
        ("cap:query", "cap:interpret"),
        ("cap:query", "resource:inference_engine"),
        ("cap:clarify", "cap:query"),
        ("cap:clarify", "cap:realize"),
        ("cap:remember", "resource:semantic_store"),
        ("cap:remember", "resource:common_ground"),
        ("cap:designate", "resource:designation_index"),
        ("cap:explain", "cap:query"),
        ("cap:explain", "cap:realize"),
    ):
        facts.append(rel(capability, "rel:depends_on", dependency))

    value_dimensions = {
        "dim:availability": ["value:available", "value:unavailable"],
        "dim:confidence": ["value:uncertain", "value:supported", "value:contradicted"],
        "dim:memory_status": ["value:remembered", "value:forgotten", "value:unknown"],
        "dim:learning_status": ["value:learning", "value:learned", "value:learned_confirmed", "value:unknown"],
        "dim:communication_status": ["value:communicating", "value:idle"],
        "dim:emotional_state": ["value:positive", "value:neutral", "value:negative"],
    }
    for dimension, values in value_dimensions.items():
        facts.append(rel(dimension, "rel:dimension_domain", "domain:categorical"))
        for value in values:
            facts.append(rel(value, "rel:value_of_dimension", dimension))

    facts.extend(
        [
            designation("participant:system", "CEMM", "label:name", "en", True, 2.0),
            designation("participant:system", "Contextual Event Memory Model", "label:name_full", "en", True, 1.8),
            designation("participant:system", "CEMM", "label:acronym", "en", True, 1.6),
            designation("participant:user", "user", "label:title", "en", False, 0.8),
        ]
    )

    # Operational self-state is emitted by cycle-local providers. No timeless
    # positive/available/emotional claims are seeded here.

    published = set()
    for target, entries in REVIEWED_DESIGNATIONS.items():
        for surface, label, language, preferred, prior in entries:
            facts.append(designation(target, surface, label, language, preferred, prior))
            published.add((target, surface.casefold(), language))
    for target, surfaces in REVIEWED_INFLECTIONS.items():
        for surface in surfaces:
            key = (target, surface.casefold(), "en")
            if key in published:
                continue
            facts.append(designation(
                target, surface, "label:lexical", "en", False, 1.05
            ))
            published.add(key)

    atom_map = {item["ref"]: item for item in atoms}
    fact_map = {
        json.dumps([item["operator"], item.get("stance", "support"), item["args"]], sort_keys=True, ensure_ascii=False, separators=(",", ":")): item
        for item in facts
    }
    return {
        "atoms": [atom_map[key] for key in sorted(atom_map)],
        "operator_roles": [],
        "control_symbols": {
            "semantic.frame_relation": FRAME_RELATION,
            "learning.designation_contract": DESIGNATION_LEARNING_CONTRACT,
        },
        "reference_forms": [],
        "facts": [fact_map[key] for key in sorted(fact_map)],
        "rules": [],
    }


def main() -> None:
    output = ROOT / "cemm" / "data" / "conversation_foundation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(output), "atoms": len(build()["atoms"]), "facts": len(build()["facts"])}, indent=2))


if __name__ == "__main__":
    main()
