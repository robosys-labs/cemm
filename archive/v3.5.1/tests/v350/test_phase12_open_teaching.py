from __future__ import annotations

from cemm.v350.conversation.session_memory import (
    ReferenceSurfaceEntry,
    SessionDiscourseMemory,
    SessionMemoryCommit,
)
from cemm.v350.grounding.model import DiscourseAnchor
from cemm.v350.language.constructions import ConstructionMatcher
from cemm.v350.language.model import (
    ConstructionKind,
    ConstructionRecord,
    ConstructionSlot,
    FormCandidate,
    FormObservation,
    LanguageFormRecord,
    Span,
)


class _Registry:
    def __init__(self, construction, form):
        self.construction = construction
        self.form = form

    def active_constructions(self):
        return (self.construction,)

    def construction_match_authority(self, construction):
        return True, "test-exact-record", ("e:construction",)

    def require_form(self, ref, revision=None):
        assert ref == self.form.form_ref
        return self.form

    def require_sense(self, ref, revision=None):
        raise AssertionError("no senses are used in this open-observation test")


def test_reviewed_open_observation_slot_can_bind_first_use_unknown_term():
    # Raw unknown observations gain no global lexical/semantic authority.  This exact
    # construction record explicitly licenses one slot to consume a word observation.
    form = LanguageFormRecord(
        form_ref="form:is", pack_ref="pack:en", pack_revision=1,
        written_form="is", normalized_form="is",
        feature_values=(("category", "verb"),),
    )
    construction = ConstructionRecord(
        construction_ref="construction:test:teaching",
        pack_ref="pack:en", pack_revision=1,
        construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
        slots=(ConstructionSlot(
            slot_ref="term", accepted_categories=("proper_name",), semantic_port_ref="term",
        ),),
        trigger_form_refs=("form:is",),
        metadata={
            "open_observation_slots": {
                "term": {"observation_categories": ("word",), "purpose": "first_use_reference"},
            },
        },
    )
    observations = (
        FormObservation("obs:zorb", Span(0, 4), "Zorb", "zorb", "Latin", "word", ("e:zorb",)),
        FormObservation("obs:is", Span(5, 7), "is", "is", "Latin", "word", ("e:is",)),
    )
    forms = (
        FormCandidate(
            candidate_ref="fc:is", observation_refs=("obs:is",), span=Span(5, 7),
            form_ref="form:is", form_revision=1, language_tag="en", confidence=1.0,
            evidence_refs=("e:is",),
        ),
    )

    candidates = ConstructionMatcher(_Registry(construction, form)).match(
        observations, forms, (), (), (),
    )
    assert candidates
    assert any(dict(item.slot_fillers)["term"] == ("obs:zorb",) for item in candidates)
    assert all(item.confidence <= 1.0 for item in candidates)


def test_session_reference_surface_is_reintroduced_as_grounding_identity_evidence():
    memory = SessionDiscourseMemory()
    commit = SessionMemoryCommit(
        commit_ref="commit:1", expected_revision=0,
        discourse_anchors=(DiscourseAnchor(
            "anchor:zorb", "referent:provisional:zorb", "conversation", 0.9, 1,
            evidence_refs=("e:zorb",),
        ),),
        reference_surfaces=(ReferenceSurfaceEntry(
            "reference:zorb", "referent:provisional:zorb", "Zorb", "zorb", "en",
            "conversation", ("e:zorb",), 1,
        ),),
    )
    memory.commit("conversation", "public", commit)
    anchors = memory.grounding_anchors("conversation", "public")
    assert anchors[0].normalized_surface_keys == ("zorb",)
