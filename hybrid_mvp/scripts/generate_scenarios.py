#!/usr/bin/env python
"""Generate the 210-scenario coverage matrix as JSONL.

This is a one-time generator script that produces
``data/scenarios/use_cases.jsonl``. The 210 cases cover all semantic
competency categories and every gap kind. Each case specifies semantic
assertions rather than exact prose.

Usage::

    python scripts/generate_scenarios.py --output data/scenarios/use_cases.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# All 18 gap kinds.
GAP_KINDS = [
    "evidence",
    "designation",
    "reference",
    "authority",
    "proposal",
    "verification",
    "inference",
    "state",
    "transition",
    "learning",
    "resource",
    "permission",
    "adapter",
    "operation",
    "storage",
    "realization",
    "performance",
    "implementation",
]

# Competency categories.
CATEGORIES = [
    "designation_definition",
    "reordered_constructions",
    "polysemy",
    "modality",
    "negation_scope",
    "recursive_family_proof",
    "participant_reference",
    "reported_speech",
    "temporal_state",
    "reviewed_sensor_operation_evidence",
    "transition_simulation",
    "learning_security",
    "capability_policy_adapter_effect",
    "contradiction",
    "gap_kinds",
    "multilingual_aliases",
    "adversarial_programs",
    "restart",
    "realization_equivalence",
]


def _assertion(kind: str, **fields) -> dict:
    """Build a semantic assertion dict."""
    d = {"kind": kind}
    d.update(fields)
    return d


def _disabled_proposal(description: str) -> list[dict]:
    """Declare a reviewed construction that intentionally stops at PROPOSE."""

    return [
        _assertion(
            "gap",
            gap_kind="proposal",
            description=description,
            error_code=None,
        )
    ]


def _verification_rejection(description: str) -> list[dict]:
    return [
        _assertion(
            "gap",
            gap_kind="verification",
            description=description,
            observed_kind="verification",
            status="verification_rejected",
            recommended_owner="runtime",
            safe_response_action="reject_candidate",
            error_code=None,
        )
    ]


def _contested_observed_event(event_type: str) -> list[dict]:
    """Return the authored R3 contract for a designation-backed event use."""

    return [
        _assertion(
            "event",
            event_type=event_type,
            roles={
                "role:actor": "participant:user",
                "role:addressee": "participant:system",
            },
        ),
        _assertion("mode", mode="OBSERVE"),
        _assertion(
            "decision", status="contested", action="retain_attribution"
        ),
        _assertion("no_effect", reason="attributed_only"),
        _assertion(
            "response",
            discourse_action="acknowledge",
            cycle_status="partial",
            polarity="polarity:positive",
            modality="modality:actual",
            epistemic_status="epistemic_status:contested",
        ),
    ]


def _transition_environment(
    subject: str, dimension: str, from_value: str | None
) -> dict:
    """Declare the reviewed initial world state for an authentic transition."""

    facts = []
    if from_value is not None:
        facts.append(
            {
                "operator": "op:state",
                "predicate_ref": dimension,
                "roles": {
                    "role:subject": subject,
                    "role:dimension": dimension,
                    "role:value": from_value,
                },
                "stance": "support",
                "source_ref": "source:r4-reviewed-initial-state",
            }
        )
    return {"environments": [{"world_facts": facts}]}


def _trusted_evidence_environment(
    source: str,
    adapter: str,
    target: str,
    dimension: str,
    value: str,
    receipt_suffix: str,
) -> dict:
    receipt_ref = f"receipt:r4-reviewed-{receipt_suffix}"
    return {
        "environments": [
            {
                "evidence_items": [
                    {
                        "source": source,
                        "content": {
                            "adapter": adapter,
                            "target": target,
                            "dimension": dimension,
                            "value": value,
                        },
                        "provenance_refs": [adapter],
                        "adapter_receipt_ref": receipt_ref,
                    }
                ],
                "required_observation_refs": [receipt_ref],
                "situation_constraints": {
                    "trusted_observation": True,
                    "evidence_policy_refs": [
                        f"policy:evidence:reviewed_{source}"
                    ],
                },
            }
        ]
    }


def _case(
    idx: int,
    category: str,
    assertions: list[dict],
    surfaces: list[str],
    gap_kind: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "scenario_ref": f"scenario:{category}-{idx:04d}",
        "review_status": "reviewed",
        "competency_category": category,
        "semantic_assertions": assertions,
        "surface_examples": surfaces,
        "expected_gap_kind": gap_kind,
        "metadata": metadata or {},
    }


def generate_all() -> list[dict]:
    cases: list[dict] = []
    counter = 0

    def _next(category: str, assertions, surfaces, gap_kind=None, metadata=None):
        nonlocal counter
        counter += 1
        cases.append(
            _case(counter, category, assertions, surfaces, gap_kind, metadata)
        )

    # ------------------------------------------------------------------
    # 1. designation/definition (14 cases)
    # ------------------------------------------------------------------
    cat = "designation_definition"
    # Greeting/farewell surfaces *use* reviewed designation authority to
    # construct event meanings.  They do not assert new op:designation facts.
    # The explicit cycle rows keep the reviewed expectation independent of the
    # runtime while documenting the admitted R3 contested-observation outcome.
    _next(cat, _contested_observed_event("event:greeting"), ["hello", "hi", "hey"])
    _next(cat, _contested_observed_event("event:farewell"), ["bye", "goodbye"])
    _next(cat, [_assertion("designates", surface="book", target="entity:book")],
          ["book", "the book"])
    _next(cat, [_assertion("designates", surface="server", target="entity:server")],
          ["server", "the server"])
    _next(cat, [_assertion("designates", surface="CEMM", target="participant:system")],
          ["CEMM", "cemm"])
    _next(cat, [_assertion("defines", target="concept:digital_agent", semantic_kind="concept")],
          ["what is CEMM?", "define CEMM"])
    _next(cat, [_assertion("designates", surface="alice", target="entity:alice")],
          ["alice", "Alice"])
    _next(cat, [_assertion("designates", surface="bob", target="entity:bob")],
          ["bob", "Bob"])
    _next(cat, [_assertion("designates", surface="job", target="concept:job_role")],
          ["job", "occupation", "role"])
    _next(cat, [_assertion("defines", target="concept:mother", semantic_kind="concept")],
          ["what is a mother?", "define mother"])
    _next(cat, [_assertion("designates", surface="mother-in-law", target="rel:mother_in_law")],
          ["mother-in-law", "mother in law", "spouse's mother"])
    _next(cat, [_assertion("designates", surface="partner", target="rel:has_partner")],
          ["partner", "spouse"])
    _next(cat, [_assertion("designates", surface="progenitor", target="concept:mother")],
          ["progenitor", "parent"])
    _next(cat, [_assertion("designates", surface="lamp", target="entity:lamp")],
          ["lamp", "the lamp"])

    # ------------------------------------------------------------------
    # 2. reordered constructions (12 cases)
    # ------------------------------------------------------------------
    cat = "reordered_constructions"
    _next(cat, [_assertion("query", target="participant:system", role="label:name")],
          ["what is your name?", "your name is what?"])
    _next(cat, [_assertion("query", target="participant:system", role="label:name")],
          ["what are you called?", "you are called what?"])
    _next(cat, [_assertion("state", subject="entity:server", dimension="dim:availability", value="value:online"),
                _assertion("mode", mode="query")],
          ["is the server online?", "online is the server?"])
    _next(cat, [_assertion("state", subject="entity:server", dimension="dim:availability", value="value:offline"),
                _assertion("mode", mode="query")],
          ["is the server offline?", "offline is the server?"])
    _next(cat, [_assertion("state", subject="entity:lamp", dimension="dim:power", value="value:on"),
                _assertion("mode", mode="query")],
          ["is the lamp on?", "on is the lamp?"])
    _next(cat, [_assertion("state", subject="entity:lamp", dimension="dim:power", value="value:off"),
                _assertion("mode", mode="query")],
          ["is the lamp off?", "off is the lamp?"])
    _next(cat, [_assertion("relation", subject="entity:alice", relation="rel:likes", object="entity:book")],
          ["alice likes the book", "the book alice likes"])
    _next(cat, [_assertion("relation", subject="entity:alice", relation="rel:owns", object="entity:book")],
          ["alice owns the book", "the book alice owns"])
    _next(cat, [_assertion("state", subject="entity:door", dimension="dim:availability", value="value:available"),
                _assertion("mode", mode="query")],
          ["is the door available?", "available is the door?"])
    _next(cat, [_assertion("state", subject="entity:router", dimension="dim:availability", value="value:online"),
                _assertion("mode", mode="query")],
          ["is the router online?", "online the router is?"])
    _next(cat, [_assertion("state", subject="entity:light", dimension="dim:power", value="value:on"),
                _assertion("mode", mode="query")],
          ["is the light on?", "on the light is?"])
    _next(cat, [_assertion("state", subject="entity:server", dimension="dim:operational_status", value="value:operating_normally"),
                _assertion("mode", mode="query")],
          ["is the server operating normally?", "operating normally the server is?"])

    # ------------------------------------------------------------------
    # 3. polysemy (10 cases)
    # ------------------------------------------------------------------
    cat = "polysemy"
    _next(cat, [_assertion("polysemy", surface="job", targets=["concept:job_role"])],
          ["job", "the job"])
    _next(cat, [_assertion("polysemy", surface="role", targets=["concept:job_role"])],
          ["role", "the role"])
    _next(cat, [_assertion("polysemy", surface="status", targets=["dim:operational_status"])],
          ["status", "Status"])
    _next(cat, [_assertion("polysemy", surface="light", targets=["entity:light"])],
          ["light", "the light"])
    _next(cat, [_assertion("polysemy", surface="left", targets=["event:leave"])],
          ["left", "Left"])
    _next(cat, [_assertion("designates", surface="say", target="event:say")],
          ["say", "Say"])
    _next(cat, [_assertion("designates", surface="learn", target="event:learn_alias")],
          ["learn", "Learn"])
    _next(cat, [_assertion("designates", surface="teach", target="event:teach")],
          ["teach", "Teach"])
    _next(cat, [_assertion("polysemy", surface="available", targets=["value:available"])],
          ["available", "Available"])
    _next(cat, [_assertion("polysemy", surface="on", targets=["value:on"])],
          ["on", "On"])

    # ------------------------------------------------------------------
    # 4. modality (10 cases)
    # ------------------------------------------------------------------
    cat = "modality"
    _next(cat, [_assertion("modality", modality_kind="capability", target="event:learn_alias",
                           actor="participant:user", event_target="participant:system",
                           surface="CEMM")],
          ["can I call you CEMM?", "could I call you CEMM?"])
    _next(cat, [_assertion("modality", modality_kind="capability", target="event:learn_alias",
                           actor="participant:user", event_target="participant:system",
                           surface="CEMM")],
          ["I could call you CEMM?", "i could call you CEMM?"])
    _next(cat, [_assertion("modality", modality_kind="obligation", target="event:set_state",
                           subject="entity:server", dimension="dim:availability",
                           value="value:online")],
          ["the server must be online", "The server must be online"])
    _next(cat, [*_disabled_proposal("conditional event scope is not admitted in R4"),
                _assertion("mode", mode="simulate")],
          ["if the server is online then proceed", "when the server is online proceed"])
    _next(cat, _disabled_proposal("answer-capability wording is not admitted in R4"),
          ["can you answer?", "could you answer?"])
    _next(cat, [_assertion("modality", modality_kind="possible", target="cap:respond")],
          ["can you respond?", "could you respond?"])
    _next(cat, _disabled_proposal("bare learning-capability wording is not admitted in R4"),
          ["can you learn?", "could you learn?"])
    _next(cat, [_assertion("modality", modality_kind="possible", target="cap:set_state")],
          ["can you set state?", "could you set state?"])
    _next(cat, _disabled_proposal("event obligation scope is not admitted in R4"),
          ["you must say goodbye", "you have to say goodbye"])
    _next(cat, [*_disabled_proposal("conditional greeting scope is not admitted in R4"),
                _assertion("mode", mode="simulate")],
          ["if alice arrives then greet her", "when alice arrives greet her"])

    # ------------------------------------------------------------------
    # 5. negation/scope (12 cases)
    # ------------------------------------------------------------------
    cat = "negation_scope"
    _next(cat, [_assertion("negation", scope="dim:availability", target="entity:server",
                           subject="entity:server", dimension="dim:availability",
                           value="value:online")],
          ["the server is not online", "not online the server is"])
    _next(cat, [_assertion("negation", scope="dim:power", target="entity:lamp",
                           subject="entity:lamp", dimension="dim:power", value="value:on")],
          ["the lamp is not on", "not on the lamp is"])
    _next(cat, [_assertion("negation", scope="dim:availability", target="entity:server",
                           subject="entity:server", dimension="dim:availability", value="value:offline")],
          ["the server is not offline", "not offline the server is"])
    _next(cat, _disabled_proposal("negated reported speech is not admitted in R4"),
          ["alice did not say hello", "not hello alice said"])
    _next(cat, _disabled_proposal("negated reported speech is not admitted in R4"),
          ["bob did not say goodbye", "not goodbye bob said"])
    _next(cat, _disabled_proposal("negated relation scope is not admitted in R4"),
          ["alice does not like the book", "not like the book alice does"])
    _next(cat, _disabled_proposal("negated relation scope is not admitted in R4"),
          ["alice does not own the book", "not own the book alice does"])
    _next(cat, _disabled_proposal("negated capability scope is not admitted in R4"),
          ["you cannot learn that", "not learn that you can"])
    _next(cat, _disabled_proposal("negated capability scope is not admitted in R4"),
          ["you cannot set state", "You cannot set state"])
    _next(cat, [_assertion("negation", scope="dim:operational_status",
                           subject="entity:server", dimension="dim:operational_status",
                           value="value:operating_normally")],
          ["the server is not operating normally", "not operating normally the server is"])
    _next(cat, [_assertion("negation", scope="dim:availability", target="entity:door",
                           subject="entity:door", dimension="dim:availability", value="value:available")],
          ["the door is not available", "not available the door is"])
    _next(cat, [_assertion("negation", scope="dim:power", target="entity:light",
                           subject="entity:light", dimension="dim:power", value="value:on")],
          ["the light is not on", "not on the light is"])

    # ------------------------------------------------------------------
    # 6. recursive family proof (10 cases)
    # ------------------------------------------------------------------
    cat = "recursive_family_proof"
    _next(cat, [_assertion("rule", rule="rule:mother-in-law-implies-partner-exists",
                           subject="entity:alice", relation="rel:mother_in_law")],
          ["alice mother-in-law who?", "mother-in-law alice who?"])
    _next(cat, [_assertion("rule", rule="rule:partner-implies-married-state",
                           subject="entity:alice", relation="rel:has_partner")],
          ["alice partner who?", "Alice partner who?"])
    _next(cat, _disabled_proposal("inverse kinship inference is not admitted in R4"),
          ["bob's mother-in-law is carol", "carol is bob's mother-in-law"])
    _next(cat, _disabled_proposal("partner-to-marital inference is not admitted in R4"),
          ["bob has a partner so bob is married", "Bob has a partner so bob is married"])
    _next(cat, _disabled_proposal("two-hop kinship proof surface is not admitted in R4"),
          ["alice's mother-in-law implies alice has a partner"])
    _next(cat, _disabled_proposal("two-hop marital proof surface is not admitted in R4"),
          ["alice has a partner implies alice is married"])
    _next(cat, _disabled_proposal("three-hop marital proof surface is not admitted in R4"),
          ["carol mother-in-law implies carol married"])
    _next(cat, _disabled_proposal("inverse kinship inference is not admitted in R4"),
          ["mary's mother-in-law is carol", "carol is mary's mother-in-law"])
    _next(cat, _disabled_proposal("partner-to-marital inference is not admitted in R4"),
          ["mary has a partner so mary is married", "Mary has a partner so mary is married"])
    _next(cat, _disabled_proposal("two-hop kinship proof surface is not admitted in R4"),
          ["bob's mother-in-law implies bob has a partner"])

    # ------------------------------------------------------------------
    # 7. participant/reference (10 cases)
    # ------------------------------------------------------------------
    cat = "participant_reference"
    _next(cat, _disabled_proposal("participant-relative speech query is not admitted in R4"),
          ["you said what?", "what did you say?"])
    _next(cat, _disabled_proposal("participant-relative addressee binding is not admitted in R4"),
          ["I told you", "you I told"])
    _next(cat, [_assertion("reported_speech", speaker="entity:alice",
                           event="event:say", content="event:greeting")],
          ["alice said hello", "alice says hello"])
    _next(cat, [_assertion("designates", surface="bob", target="entity:bob")],
          ["bob", "Bob"])
    _next(cat, _disabled_proposal("event addressee reference binding is not admitted in R4"),
          ["greet carol", "carol greet"])
    _next(cat, _disabled_proposal("teaching actor reference binding is not admitted in R4"),
          ["mary teaches bob", "bob mary teaches"])
    _next(cat, _disabled_proposal("learner-relative reference binding is not admitted in R4"),
          ["teach me", "me teach"])
    _next(cat, _disabled_proposal("embedded learning actor binding is not admitted in R4"),
          ["you learn that", "that you learn"])
    _next(cat, [_assertion("designates", surface="alice", target="entity:alice")],
          ["alice", "Alice"])
    _next(cat, [_assertion("reference", target="entity:bob", role="role:object",
                           subject="entity:alice", relation="rel:likes",
                           object="entity:bob")],
          ["alice likes bob", "bob alice likes"])

    # ------------------------------------------------------------------
    # 8. reported speech (10 cases)
    # ------------------------------------------------------------------
    cat = "reported_speech"
    _next(cat, [_assertion("reported_speech", speaker="entity:alice", event="event:say",
                           content="event:greeting")],
          ["alice said hello", "alice says hello"])
    _next(cat, [_assertion("reported_speech", speaker="entity:bob", event="event:say",
                           content="event:farewell")],
          ["bob said goodbye", "bob says goodbye"])
    _next(cat, [_assertion("reported_speech", speaker="entity:alice", event="event:say",
                           content="event:leave")],
          ["alice said left", "alice says left"])
    _next(cat, [_assertion("reported_speech", speaker="entity:bob", event="event:leave",
                           content=None)],
          ["bob said left", "bob says left"])
    _next(cat, [_assertion("reported_speech", speaker="entity:carol", event="event:say",
                           content="event:greeting")],
          ["carol said hello", "carol says hello"])
    _next(cat, [_assertion("reported_speech", speaker="entity:mary", event="event:say",
                           content="event:farewell")],
          ["mary said goodbye", "mary says goodbye"])
    _next(cat, [_assertion("reported_speech", speaker="entity:alice", event="event:say",
                           content="dim:availability", content_subject="entity:server",
                           content_dimension="dim:availability", content_value="value:online")],
          ["alice said the server is online", "alice says the server is online"])
    _next(cat, [_assertion("reported_speech", speaker="entity:bob", event="event:say",
                           content="dim:power", content_subject="entity:lamp",
                           content_dimension="dim:power", content_value="value:on")],
          ["bob said the lamp is on", "bob says the lamp is on"])
    _next(cat, [_assertion("reported_speech", speaker="entity:carol", event="event:say",
                           content="rel:likes", content_subject="entity:alice",
                           content_object="entity:book")],
          ["carol said alice likes the book", "carol says alice likes the book"])
    _next(cat, [_assertion("reported_speech", speaker="entity:mary", event="event:say",
                           content="rel:owns", content_subject="entity:bob",
                           content_object="entity:book")],
          ["mary said bob owns the book", "mary says bob owns the book"])

    # ------------------------------------------------------------------
    # 9. temporal state (10 cases)
    # ------------------------------------------------------------------
    cat = "temporal_state"
    _next(cat, [_assertion("state", subject="entity:server", dimension="dim:availability",
                           value="value:online")],
          ["the server is online", "online the server is"])
    _next(cat, [_assertion("state", subject="entity:server", dimension="dim:availability",
                           value="value:offline")],
          ["the server is offline", "offline the server is"])
    _next(cat, [_assertion("state", subject="entity:lamp", dimension="dim:power",
                           value="value:on")],
          ["the lamp is on", "on the lamp is"])
    _next(cat, [_assertion("state", subject="entity:lamp", dimension="dim:power",
                           value="value:off")],
          ["the lamp is off", "off the lamp is"])
    _next(cat, [_assertion("state", subject="entity:alice", dimension="dim:marital_status",
                           value="value:married")],
          ["alice is married", "married alice is"])
    _next(cat, [_assertion("state", subject="entity:door", dimension="dim:availability",
                           value="value:available")],
          ["the door is available", "available the door is"])
    _next(cat, [_assertion("state", subject="entity:door", dimension="dim:availability",
                           value="value:unavailable")],
          ["the door is unavailable", "unavailable the door is"])
    _next(cat, [_assertion("state", subject="entity:light", dimension="dim:power",
                           value="value:enabled")],
          ["the light is enabled", "enabled the light is"])
    _next(cat, [_assertion("state", subject="entity:light", dimension="dim:power",
                           value="value:disabled")],
          ["the light is disabled", "disabled the light is"])
    _next(cat, [_assertion("state", subject="entity:server", dimension="dim:operational_status",
                           value="value:operating_normally")],
          ["the server is operating normally", "operating normally the server is"])

    # ------------------------------------------------------------------
    # 10. reviewed sensor/operation evidence (10 cases)
    # ------------------------------------------------------------------
    cat = "reviewed_sensor_operation_evidence"
    _next(cat, [_assertion("sensor_evidence", adapter="adapter:door_sensor",
                           target="entity:door", value="value:available")],
          ["the door is available", "available the door is"],
          metadata=_trusted_evidence_environment("sensor", "adapter:door_sensor", "entity:door", "dim:availability", "value:available", "door-available"))
    _next(cat, [_assertion("sensor_evidence", adapter="adapter:door_sensor",
                           target="entity:door", value="value:unavailable")],
          ["the door is unavailable", "unavailable the door is"],
          metadata=_trusted_evidence_environment("sensor", "adapter:door_sensor", "entity:door", "dim:availability", "value:unavailable", "door-unavailable"))
    _next(cat, [_assertion("operation_evidence", adapter="adapter:state",
                           target="entity:server", dimension="dim:availability", value="value:online")],
          ["the server is online", "online the server is"],
          metadata=_trusted_evidence_environment("operation", "adapter:state", "entity:server", "dim:availability", "value:online", "server-online"))
    _next(cat, [_assertion("operation_evidence", adapter="adapter:state",
                           target="entity:lamp", dimension="dim:power", value="value:on")],
          ["the lamp is on", "on the lamp is"],
          metadata=_trusted_evidence_environment("operation", "adapter:state", "entity:lamp", "dim:power", "value:on", "lamp-on"))
    _next(cat, [_assertion("sensor_evidence", adapter="adapter:memory",
                           target="entity:router", value="value:online")],
          ["the router is online", "online the router is"],
          metadata=_trusted_evidence_environment("sensor", "adapter:memory", "entity:router", "dim:availability", "value:online", "router-online"))
    _next(cat, [_assertion("operation_evidence", adapter="adapter:state",
                           target="entity:light", dimension="dim:power", value="value:enabled")],
          ["the light is enabled", "enabled the light is"],
          metadata=_trusted_evidence_environment("operation", "adapter:state", "entity:light", "dim:power", "value:enabled", "light-enabled"))
    _next(cat, [_assertion("sensor_evidence", adapter="adapter:door_sensor",
                           target="entity:door", value="value:available")],
          ["door is available", "available is the door"],
          metadata=_trusted_evidence_environment("sensor", "adapter:door_sensor", "entity:door", "dim:availability", "value:available", "door-available-repeat"))
    _next(cat, [_assertion("operation_evidence", adapter="adapter:state",
                           target="entity:server", dimension="dim:operational_status", value="value:operating_normally")],
          ["the server is operating normally"],
          metadata=_trusted_evidence_environment("operation", "adapter:state", "entity:server", "dim:operational_status", "value:operating_normally", "server-operating-normally"))
    _next(cat, [_assertion("sensor_evidence", adapter="adapter:memory",
                           target="entity:server", value="value:offline")],
          ["the server is offline", "offline the server is"],
          metadata=_trusted_evidence_environment("sensor", "adapter:memory", "entity:server", "dim:availability", "value:offline", "server-offline"))
    _next(cat, [_assertion("operation_evidence", adapter="adapter:state",
                           target="entity:door", dimension="dim:availability", value="value:unavailable")],
          ["the door is unavailable"],
          metadata=_trusted_evidence_environment("operation", "adapter:state", "entity:door", "dim:availability", "value:unavailable", "door-operation-unavailable"))

    # ------------------------------------------------------------------
    # 11. transition simulation (10 cases)
    # ------------------------------------------------------------------
    cat = "transition_simulation"
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:server", dimension="dim:availability",
                           from_value="value:offline", to_value="value:online")],
          ["set the server online", "bring the server online"], metadata=_transition_environment("entity:server", "dim:availability", "value:offline"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:server", dimension="dim:availability",
                           from_value="value:online", to_value="value:offline")],
          ["set the server offline", "take the server offline"], metadata=_transition_environment("entity:server", "dim:availability", "value:online"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:lamp", dimension="dim:power",
                           from_value="value:off", to_value="value:on")],
          ["turn the lamp on", "switch the lamp on"], metadata=_transition_environment("entity:lamp", "dim:power", "value:off"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:lamp", dimension="dim:power",
                           from_value="value:on", to_value="value:off")],
          ["turn the lamp off", "switch the lamp off"], metadata=_transition_environment("entity:lamp", "dim:power", "value:on"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:light", dimension="dim:power",
                           from_value="value:disabled", to_value="value:enabled")],
          ["turn the light enabled", "set the light enabled"], metadata=_transition_environment("entity:light", "dim:power", "value:disabled"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:light", dimension="dim:power",
                           from_value="value:enabled", to_value="value:disabled")],
          ["turn the light disabled", "set the light disabled"], metadata=_transition_environment("entity:light", "dim:power", "value:enabled"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:door", dimension="dim:availability",
                           from_value="value:unavailable", to_value="value:available")],
          ["make the door available", "set the door available"], metadata=_transition_environment("entity:door", "dim:availability", "value:unavailable"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:door", dimension="dim:availability",
                           from_value="value:available", to_value="value:unavailable")],
          ["make the door unavailable", "set the door unavailable"], metadata=_transition_environment("entity:door", "dim:availability", "value:available"))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:server", dimension="dim:operational_status",
                           from_value=None, to_value="value:operating_normally")],
          ["set the server operating normally"], metadata=_transition_environment("entity:server", "dim:operational_status", None))
    _next(cat, [_assertion("transition", event="event:set_state",
                           subject="entity:router", dimension="dim:availability",
                           from_value="value:offline", to_value="value:online")],
          ["bring the router online", "set the router online"], metadata=_transition_environment("entity:router", "dim:availability", "value:offline"))

    # ------------------------------------------------------------------
    # 12. learning/security (12 cases)
    # ------------------------------------------------------------------
    cat = "learning_security"
    _next(cat, [_assertion("learning", event="event:learn_alias",
                           capability="cap:learn_alias", surface="yoz", target="event:greeting")],
          ["learn that yoz means hello", "Learn that yoz means hello"])
    _next(cat, [_assertion("learning", event="event:learn_alias",
                           capability="cap:learn_alias", surface="saluton", target="event:greeting")],
          ["learn that saluton means hello"])
    _next(cat, [_assertion("learning_directive", event="event:learn_alias",
                           surface="namaste", target="event:greeting")],
          ["learn that namaste means hello"])
    _next(cat, _disabled_proposal("teaching claim composition is not admitted in R4"),
          ["teach that gracias means hello"])
    _next(cat, _disabled_proposal("designation lookup composition is not admitted in R4"),
          ["what does hello mean?", "what is hello?"])
    _next(cat, _disabled_proposal("designation lookup composition is not admitted in R4"),
          ["what does bye mean?", "what is bye?"])
    _next(cat, _disabled_proposal("learning event claims are not admitted in R4"),
          ["I learned that yoz means hello"])
    _next(cat, _disabled_proposal("learning event claims are not admitted in R4"),
          ["I learned that saluton means hello"])
    _next(cat, _disabled_proposal("permission-over-learning query is not admitted in R4"),
          ["can you learn a new alias?", "do you have permission to learn?"])
    _next(cat, [_assertion("capability", ref="cap:set_state",
                           participant="participant:system")],
          ["can you set state?", "could you set state?"])
    _next(cat, [_assertion("learning", event="event:learn_alias",
                           capability="cap:learn_alias", surface="bonjour", target="event:greeting")],
          ["learn that bonjour means hello"])
    _next(cat, [_assertion("reviewed_acquisition", surface="reviewed: hola",
                           target="event:greeting")],
          ["reviewed: hola means hello"])

    # ------------------------------------------------------------------
    # 13. capability/policy/adapter/effect (12 cases)
    # ------------------------------------------------------------------
    cat = "capability_policy_adapter_effect"
    _next(cat, [_assertion("capability", ref="cap:query", participant="participant:system")],
          ["can you query?", "do you have query?"])
    _next(cat, [_assertion("capability", ref="cap:respond", participant="participant:system")],
          ["can you respond?", "do you have respond?"])
    _next(cat, [_assertion("capability", ref="cap:learn_alias", participant="participant:system")],
          ["can you learn aliases?", "do you have learn_alias?"])
    _next(cat, [_assertion("capability", ref="cap:set_state", participant="participant:system")],
          ["can you set state?", "do you have set_state?"])
    _next(cat, _disabled_proposal("permission query syntax is not admitted in R4"),
          ["do you have write_alias permission?", "is write_alias allowed?"])
    _next(cat, _disabled_proposal("permission query syntax is not admitted in R4"),
          ["do you have set_state permission?", "is set_state allowed?"])
    _next(cat, _disabled_proposal("adapter reference syntax is not admitted in R4"),
          ["the memory adapter is available", "use the memory adapter"])
    _next(cat, _disabled_proposal("adapter reference syntax is not admitted in R4"),
          ["the state adapter is available", "use the state adapter"])
    _next(cat, _disabled_proposal("adapter reference syntax is not admitted in R4"),
          ["the door sensor adapter is available", "use the door sensor"])
    _next(cat, _disabled_proposal("explicit adapter effect syntax is not admitted in R4"),
          ["set the server state via the state adapter"])
    _next(cat, _disabled_proposal("explicit adapter effect syntax is not admitted in R4"),
          ["learn an alias via the memory adapter"])
    _next(cat, _disabled_proposal("explicit adapter effect syntax is not admitted in R4"),
          ["set the lamp state via the state adapter"])

    # ------------------------------------------------------------------
    # 14. contradiction (8 cases)
    # ------------------------------------------------------------------
    cat = "contradiction"
    _next(cat, [_assertion("contradiction", subject="entity:server",
                           dimension="dim:availability", values=["value:online", "value:offline"])],
          ["the server is online and offline", "online and offline the server is"])
    _next(cat, [_assertion("contradiction", subject="entity:lamp",
                           dimension="dim:power", values=["value:on", "value:off"])],
          ["the lamp is on and off", "on and off the lamp is"])
    _next(cat, _verification_rejection("mixed state negation is rejected by the exact verifier"),
          ["alice is married and not married"])
    _next(cat, [_assertion("contradiction", subject="entity:door",
                           dimension="dim:availability", values=["value:available", "value:unavailable"])],
          ["the door is available and unavailable"])
    _next(cat, [_assertion("contradiction", subject="entity:light",
                           dimension="dim:power", values=["value:enabled", "value:disabled"])],
          ["the light is enabled and disabled"])
    _next(cat, _disabled_proposal("compound operational contradiction is not admitted in R4"),
          ["the server is operating normally and not operating"])
    _next(cat, _disabled_proposal("compound relation contradiction is not admitted in R4"),
          ["alice likes and does not like the book"])
    _next(cat, _disabled_proposal("compound relation contradiction is not admitted in R4"),
          ["alice owns and does not own the book"])

    # ------------------------------------------------------------------
    # 15. gap kinds (18 cases — one per gap kind)
    # ------------------------------------------------------------------
    cat = "gap_kinds"
    for gk in GAP_KINDS:
        _next(cat, [_assertion("gap", gap_kind=gk, description=f"scenario producing {gk} gap")],
              [f"this produces a {gk} gap", f"{gk} gap example"],
              gap_kind=gk)

    # ------------------------------------------------------------------
    # 16. multilingual aliases (12 cases)
    # ------------------------------------------------------------------
    cat = "multilingual_aliases"
    _next(cat, [_assertion("alias", surface="hola", language="es", target="event:greeting")],
          ["hola means hello", '"hola" means hello'])
    _next(cat, [_assertion("alias", surface="bonjour", language="fr", target="event:greeting")],
          ["bonjour means hello", '"bonjour" means hello'])
    _next(cat, [_assertion("alias", surface="saluton", language="eo", target="event:greeting")],
          ["saluton means hello", '"saluton" means hello'])
    _next(cat, [_assertion("alias", surface="yoz", language="custom", target="event:greeting")],
          ["yoz means hello", '"yoz" means hello'])
    _next(cat, [_assertion("alias", surface="namaste", language="hi", target="event:greeting")],
          ["namaste means hello", '"namaste" means hello'])
    _next(cat, [_assertion("alias", surface="adios", language="es", target="event:farewell")],
          ["adios means goodbye", '"adios" means goodbye'])
    _next(cat, [_assertion("alias", surface="au revoir", language="fr", target="event:farewell")],
          ["au revoir means goodbye", '"au revoir" means goodbye'])
    _next(cat, [_assertion("alias", surface="gracias", language="es", target="event:greeting")],
          ["gracias means hello", '"gracias" means hello'])
    _next(cat, [_assertion("alias", surface="ciao", language="it", target="event:greeting")],
          ["ciao means hello", '"ciao" means hello'])
    _next(cat, [_assertion("alias", surface="hallo", language="de", target="event:greeting")],
          ["hallo means hello", '"hallo" means hello'])
    _next(cat, [_assertion("alias", surface="konnichiwa", language="ja", target="event:greeting")],
          ["konnichiwa means hello", '"konnichiwa" means hello'])
    _next(cat, [_assertion("alias", surface="olá", language="pt", target="event:greeting")],
          ["olá means hello", '"olá" means hello'])

    # ------------------------------------------------------------------
    # 17. adversarial programs (10 cases)
    # ------------------------------------------------------------------
    cat = "adversarial_programs"
    _next(cat, [_assertion("adversarial", attack="unknown_operator", operator="op:fake")],
          ["do op:fake", "execute fake operation"])
    _next(cat, [_assertion("adversarial", attack="extra_action", action_type="thirteenth_action")],
          ["do a thirteenth action", "extra action"])
    _next(cat, [_assertion("adversarial", attack="role_injection", role="role:fake")],
          ["bind role:fake", "use a fake role"])
    _next(cat, [_assertion("adversarial", attack="scope_injection", scope="fake_scope")],
          ["attach fake_scope", "use a fake scope"])
    _next(cat, [_assertion("adversarial", attack="depth_exceed", depth=999)],
          ["nest 999 levels deep", "very deep nesting"])
    _next(cat, [_assertion("adversarial", attack="budget_exceed", budget="max_applications")],
          ["do 100 applications", "exceed max applications"])
    _next(cat, [_assertion("adversarial", attack="ref_injection", ref="internal:fake")],
          ["use internal:fake", "inject internal ref"])
    _next(cat, [_assertion("adversarial", attack="surface_dispatch", surface="op:designation")],
          ["dispatch by surface string", "raw surface dispatch"])
    _next(cat, [_assertion("adversarial", attack="unverified_effect", effect="unauthorized")],
          ["execute unverified effect", "bypass verification"])
    _next(cat, [_assertion("adversarial", attack="legacy_stage", stage=22)],
          ["use legacy stage 22", "branch on stage number"])

    # ------------------------------------------------------------------
    # 18. restart (10 cases)
    # ------------------------------------------------------------------
    cat = "restart"
    _next(cat, [_assertion("restart", scope="session", preserve="world_revision")],
          ["restart the session", "session restart"])
    _next(cat, [_assertion("restart", scope="world", preserve="authority_generation")],
          ["restart the world", "world restart"])
    _next(cat, [_assertion("restart", scope="episode", preserve="session_revision")],
          ["restart the episode", "episode restart"])
    _next(cat, [_assertion("restart", scope="effect", preserve="world_revision")],
          ["restart the effect journal", "effect restart"])
    _next(cat, [_assertion("restart", scope="full", preserve="authority_generation")],
          ["full restart", "complete restart"])
    _next(cat, [_assertion("restart", scope="session", preserve="episode_revision")],
          ["restart session keep episodes", "session restart with episodes"])
    _next(cat, [_assertion("restart", scope="world", preserve="session_revision")],
          ["restart world keep sessions", "world restart with sessions"])
    _next(cat, [_assertion("restart", scope="episode", preserve="effect_revision")],
          ["restart episode keep effects", "episode restart with effects"])
    _next(cat, [_assertion("restart", scope="effect", preserve="episode_revision")],
          ["restart effects keep episodes", "effect restart with episodes"])
    _next(cat, [_assertion("restart", scope="full", preserve=None)],
          ["cold restart", "hard restart"])

    # ------------------------------------------------------------------
    # 19. realization equivalence (10 cases)
    # ------------------------------------------------------------------
    cat = "realization_equivalence"
    _next(cat, [_assertion("query", target="participant:system", role="label:name")],
          ["what is your name?", "your name what is?"])
    _next(cat, [_assertion("state", subject="entity:server",
                           dimension="dim:availability", value="value:online"),
                _assertion("mode", mode="query")],
          ["is the server online?", "online is the server?"])
    _next(cat, [_assertion("state", subject="entity:lamp",
                           dimension="dim:power", value="value:on"),
                _assertion("mode", mode="query")],
          ["is the lamp on?", "on is the lamp?"])
    _next(cat, [_assertion("gap", gap_kind="proposal",
                           description="unknown surface remains a typed proposal abstention")],
          ["what is zorbulate?", "zorbulate what is?"], gap_kind="proposal")
    _next(cat, [_assertion("gap", gap_kind="proposal",
                           description="underspecified state request remains a typed proposal abstention")],
          ["can I set state without permission?", "set state without permission?"],
          gap_kind="proposal")
    _next(cat, [_assertion("learning_directive", event="event:learn_alias",
                           surface="yoz", target="event:greeting")],
          ["learn that yoz means hello", "Learn that yoz means hello"])
    _next(cat, [_assertion("state", subject="entity:alice",
                           dimension="dim:marital_status", value="value:married"),
                _assertion("mode", mode="query")],
          ["is alice married?", "married is alice?"])
    _next(cat, [_assertion("defines", target="concept:job_role",
                           semantic_kind="concept")],
          ["what is job?", "job what is?"])
    _next(cat, [_assertion("state", subject="entity:door",
                           dimension="dim:availability", value="value:available"),
                _assertion("mode", mode="query")],
          ["is the door available?", "available is the door?"])
    _next(cat, [_assertion("state", subject="entity:light",
                           dimension="dim:power", value="value:enabled"),
                _assertion("mode", mode="query")],
          ["is the light enabled?", "enabled is the light?"])

    return cases


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the 210-scenario coverage matrix as JSONL."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "scenarios" / "use_cases.jsonl",
        help="Output JSONL file path.",
    )
    args = parser.parse_args()

    cases = generate_all()
    assert len(cases) == 210, f"Expected 210 cases, got {len(cases)}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(case, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for case in cases
    ]
    args.output.write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Generated {len(cases)} scenarios -> {args.output}")


if __name__ == "__main__":
    main()
