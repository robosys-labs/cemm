"""Reviewed minimal Swahili Phase-17 source package.

This is deliberately a *source package*, not an activation claim. It uses the exact same generic
composition VM and symbolic semantic slots as English. A release may advertise Swahili competence
only after shared-competence CSIR equivalence evidence passes under the final authority generation.
"""
from __future__ import annotations

from .minimum_english_v351 import FormSeed, SenseSeed, ConstructionSeed, ProgramStep, CompositionFamily
from .model import ConstructionProgramOperation


FORMS = (
    FormSeed("mimi", "pronoun.first.singular", "pronoun", (("person", "1"), ("number", "sg"))),
    FormSeed("wewe", "pronoun.second.singular", "pronoun", (("person", "2"), ("number", "sg"))),
    FormSeed("ni", "copula.present", "copula", (("tense", "present"),)),
    FormSeed("sio", "copula.negative", "copula", (("polarity", "negative"),)),
    FormSeed("nani", "wh.person", "wh", (("projection", "referent"),)),
    FormSeed("nini", "wh.thing", "wh", (("projection", "referent_or_definition"),)),
    FormSeed("wapi", "wh.place", "wh", (("projection", "place"),)),
    FormSeed("lini", "wh.time", "wh", (("projection", "time"),)),
    FormSeed("kwa nini", "wh.reason", "wh", (("projection", "explanation"),)),
    FormSeed("vipi", "wh.manner_state", "wh", (("projection", "manner_or_state"),)),
    FormSeed("hujambo", "discourse.greeting", "interjection"),
    FormSeed("jambo", "discourse.greeting", "interjection"),
)

SENSES = (
    SenseSeed("pronoun.first.singular", "participant_role:speaker", "referential"),
    SenseSeed("pronoun.second.singular", "participant_role:addressee", "referential"),
    SenseSeed("copula.present", "operator:predication", "construction"),
    SenseSeed("copula.negative", "operator:predication", "construction", (("polarity", "negative"),)),
    SenseSeed("wh.person", "projection:referent_person", "projection"),
    SenseSeed("wh.thing", "projection:referent_or_definition", "projection"),
    SenseSeed("wh.place", "projection:place", "projection"),
    SenseSeed("wh.time", "projection:time", "projection"),
    SenseSeed("wh.reason", "projection:explanation", "projection"),
    SenseSeed("wh.manner_state", "projection:manner_or_state", "projection"),
    SenseSeed("discourse.greeting", "discourse:greeting", "construction"),
)

# Shared competence is intentionally small and structurally explicit. Swahili morphology that is not
# reviewed here remains a form/morphology frontier; it is not approximated with English word order.
CONSTRUCTIONS = (
    ConstructionSeed(
        "construction:sw:v351:participant-pronoun",
        CompositionFamily.PRONOUNS_DEIXIS,
        ("pronoun",), (),
        (ProgramStep(ConstructionProgramOperation.UNIFY),),
        ("case:shared:pronoun:speaker", "case:shared:pronoun:addressee"),
    ),
    ConstructionSeed(
        "construction:sw:v351:copular-predication",
        CompositionFamily.IDENTITY_CLASSIFICATION,
        ("nominal_or_pronoun", "copula", "nominal_or_property"), (),
        (
            ProgramStep(ConstructionProgramOperation.ACTIVATE_SCHEMA_CLASS_CANDIDATES),
            ProgramStep(ConstructionProgramOperation.BIND_PORT_FROM_SLOT),
            ProgramStep(ConstructionProgramOperation.UNIFY),
        ),
        ("case:shared:copula:identity", "case:shared:copula:classification"),
    ),
    ConstructionSeed(
        "construction:sw:v351:wh-query",
        CompositionFamily.WH_QUERY,
        ("wh",), (),
        (ProgramStep(ConstructionProgramOperation.SET_PROJECTION),),
        ("case:shared:wh:projection",),
    ),
    ConstructionSeed(
        "construction:sw:v351:greeting",
        CompositionFamily.GREETINGS,
        ("interjection",), (),
        (ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:greeting"),),
        ("case:shared:greeting",),
    ),
)

SHARED_SEMANTIC_SLOTS = tuple(sorted({
    item.semantic_slot for item in SENSES
    if item.semantic_slot
} | {
    step.semantic_slot for construction in CONSTRUCTIONS for step in construction.program
    if step.semantic_slot
}))


def source_package_v351():
    return {
        "language_tag": "sw",
        "forms": FORMS,
        "senses": SENSES,
        "constructions": CONSTRUCTIONS,
        "shared_semantic_slots": SHARED_SEMANTIC_SLOTS,
        "activation_claim": False,
        "requires_equivalence_gate": True,
    }


__all__ = ["CONSTRUCTIONS", "FORMS", "SENSES", "SHARED_SEMANTIC_SLOTS", "source_package_v351"]
