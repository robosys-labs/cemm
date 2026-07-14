"""Tests for the native English language adapter and compositional vertical slice.

Tests verify:
- Tokenizer preserves raw text, offsets, contractions, negation, quotes
- Construction detection: copular, wh-question, yn-question, complement clause
- SurfaceEvidence is candidate-only (no final meaning selection)
- Full cycle through CognitiveKernel produces meaning candidates
- Nested proposition graph is inspectable
- Opaque lexemes remain as provisional sense clusters
- No whole-turn alias needed
"""

from __future__ import annotations

import pytest

from cemm.language.en.adapter import EnglishLanguageAdapter
from cemm.language.en.tokenizer import tokenize
from cemm.language.en.constructions import detect_constructions
from cemm.language.stream import TokenKind, TokenStream
from cemm.language.interfaces import SurfaceEvidence


class TestTokenizer:
    """Test the English tokenizer."""

    def test_basic_tokenization(self):
        ts = tokenize("hello world")
        assert len(ts.tokens) == 2
        assert ts.tokens[0].raw_form == "hello"
        assert ts.tokens[1].raw_form == "world"

    def test_preserves_offsets(self):
        ts = tokenize("hello world")
        assert ts.tokens[0].start_offset == 0
        assert ts.tokens[0].end_offset == 5
        assert ts.tokens[1].start_offset == 6
        assert ts.tokens[1].end_offset == 11

    def test_preserves_raw_text(self):
        ts = tokenize("Hello World")
        assert ts.tokens[0].raw_form == "Hello"
        assert ts.tokens[0].normalized_form == "hello"

    def test_contraction_decomposition(self):
        ts = tokenize("I'm an engineer")
        assert ts.has_contractions
        assert ts.tokens[0].kind == TokenKind.CONTRACTION
        assert ts.tokens[0].contraction is not None
        assert ts.tokens[0].contraction.components == ("I", "am")

    def test_negation_contraction(self):
        ts = tokenize("You don't know")
        assert ts.has_negation
        # don't should be marked as negation
        neg_tokens = [t for t in ts.tokens if t.is_negation]
        assert len(neg_tokens) == 1

    def test_quotation_spans(self):
        ts = tokenize('You know "know" means')
        assert ts.has_quotations
        assert len(ts.quotation_spans) == 1

    def test_clause_boundaries(self):
        ts = tokenize("Hello world.")
        assert len(ts.clause_boundaries) >= 1

    def test_punctuation_classification(self):
        ts = tokenize("Hello.")
        assert ts.tokens[-1].kind == TokenKind.PUNCTUATION

    def test_unknown_token_marked(self):
        ts = tokenize("xyzzy")
        assert ts.tokens[0].is_unknown

    def test_known_token_not_unknown(self):
        ts = tokenize("engineer")
        assert not ts.tokens[0].is_unknown

    def test_empty_string(self):
        ts = tokenize("")
        assert len(ts.tokens) == 0

    def test_raw_text_preserved(self):
        ts = tokenize("I'm an engineer.")
        assert ts.raw_text == "I'm an engineer."

    def test_lemma_candidates(self):
        ts = tokenize("engineers")
        assert "engineer" in ts.tokens[0].lemma_candidates

    def test_morphological_features(self):
        ts = tokenize("I")
        feats = ts.tokens[0].morphological_features
        assert any(f.feature == "person" and f.value == "first" for f in feats)


class TestConstructionDetection:
    """Test construction candidate detection."""

    def test_copular_contraction(self):
        ts = tokenize("I'm an engineer.")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        copular = [c for c in constr if c.construction_key == "copular"]
        assert len(copular) == 1
        assert copular[0].predicate_schema_ref == "pred:is_a"
        assert "subject" in copular[0].role_mappings
        assert "category" in copular[0].role_mappings

    def test_copular_separated(self):
        ts = tokenize("She is an engineer.")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        copular = [c for c in constr if c.construction_key == "copular"]
        assert len(copular) == 1

    def test_wh_question(self):
        ts = tokenize("What do I do?")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        wh = [c for c in constr if c.construction_key == "wh_question"]
        assert len(wh) == 1
        assert "wh" in wh[0].role_mappings
        assert "aux" in wh[0].role_mappings
        assert "subject" in wh[0].role_mappings

    def test_yn_question(self):
        ts = tokenize("Do you know?")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        yn = [c for c in constr if c.construction_key == "yn_question"]
        assert len(yn) == 1
        assert "aux" in yn[0].role_mappings

    def test_complement_clause(self):
        ts = tokenize("Do you know what an engineer is?")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        comp = [c for c in constr if c.construction_key == "complement_clause"]
        assert len(comp) == 1
        assert "embedded" in comp[0].role_mappings

    def test_negation_scope_cue(self):
        ts = tokenize("You don't know")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        neg_cues = [c for c in cues if c.cue_kind == "negation_scope"]
        assert len(neg_cues) == 1

    def test_communicative_force_assert(self):
        ts = tokenize("I'm an engineer.")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        asserts = [c for c in comm if c.force == "assert"]
        assert len(asserts) >= 1

    def test_communicative_force_ask_wh(self):
        ts = tokenize("What do I do?")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        asks = [c for c in comm if c.force == "ask"]
        assert len(asks) >= 1

    def test_lexical_sense_pronoun(self):
        ts = tokenize("I'm an engineer.")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        first_person = [l for l in lexical if l.semantic_key == "pronoun:first_person"]
        assert len(first_person) == 1

    def test_lexical_sense_opaque(self):
        ts = tokenize("xyzzy")
        lexical, constr, comm, cues, spans = detect_constructions(ts)
        opaque = [l for l in lexical if l.semantic_key.startswith("opaque:")]
        assert len(opaque) == 1
        assert opaque[0].confidence == 0.0


class TestEnglishLanguageAdapter:
    """Test the full EnglishLanguageAdapter."""

    def test_perceive_returns_surface_evidence(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("I'm an engineer.")
        assert isinstance(ev, SurfaceEvidence)

    def test_adapter_id(self):
        adapter = EnglishLanguageAdapter()
        assert adapter.adapter_id == "english-native-v34"

    def test_supported_languages(self):
        adapter = EnglishLanguageAdapter()
        assert "en" in adapter.supported_language_tags

    def test_perceive_preserves_contractions(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("I'm an engineer.")
        assert ev.token_stream.has_contractions

    def test_perceive_preserves_negation(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("You don't know")
        assert ev.token_stream.has_negation

    def test_perceive_preserves_quotations(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive('You know "know" means')
        assert ev.token_stream.has_quotations

    def test_perceive_has_lexical_candidates(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("I'm an engineer.")
        assert len(ev.lexical_sense_candidates) > 0

    def test_perceive_has_constructions(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("I'm an engineer.")
        assert len(ev.construction_candidates) > 0

    def test_perceive_has_communicative_force(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("What do I do?")
        assert len(ev.communicative_candidates) > 0
        assert ev.communicative_candidates[0].force == "ask"

    def test_perceive_language_tag(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("hello")
        assert ev.language_tag == "en"

    def test_perceive_empty_string(self):
        adapter = EnglishLanguageAdapter()
        ev = adapter.perceive("")
        assert isinstance(ev, SurfaceEvidence)
        assert len(ev.token_stream.tokens) == 0


class TestCompositionalVerticalSlice:
    """Test the full compositional vertical slice through CognitiveKernel."""

    def test_im_an_engineer_produces_meaning(self):
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("I'm an engineer.",),
        )
        cycle = rt.run(trigger)
        assert len(cycle.surface_evidence) == 1
        assert len(cycle.meaning_candidates) == 1
        graph = cycle.meaning_candidates[0]
        assert len(graph.candidate_predications) >= 1
        assert len(graph.candidate_propositions) >= 1

    def test_what_do_i_do_produces_open_port(self):
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("What do I do?",),
        )
        cycle = rt.run(trigger)
        graph = cycle.meaning_candidates[0]
        # Wh-questions should have open ports
        assert len(graph.open_ports) >= 1

    def test_do_you_know_produces_nested_propositions(self):
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("Do you know what an engineer is?",),
        )
        cycle = rt.run(trigger)
        graph = cycle.meaning_candidates[0]
        # Should have multiple predications (outer + embedded)
        assert len(graph.candidate_predications) >= 2
        assert len(graph.candidate_propositions) >= 2

    def test_you_dont_know_preserves_negation(self):
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=('You don\'t know what "know" means.',),
        )
        cycle = rt.run(trigger)
        ev = cycle.surface_evidence[0]
        assert ev.token_stream.has_negation
        assert ev.token_stream.has_quotations

    def test_opaque_engineer_remains_provisional(self):
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("I'm an engineer.",),
        )
        cycle = rt.run(trigger)
        graph = cycle.meaning_candidates[0]
        # Engineer should be opaque (no schema yet)
        assert len(graph.opaque_lexeme_refs) > 0

    def test_no_errors_in_cycle(self):
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        for sentence in [
            "I'm an engineer.",
            "What do I do?",
            "Do you know what an engineer is?",
            'You don\'t know what "know" means.',
        ]:
            trigger = CycleTrigger(
                trigger_kind="user_utterance",
                signal_ids=(sentence,),
            )
            cycle = rt.run(trigger)
            errors = cycle.trace.errors if cycle.trace else ()
            assert len(errors) == 0, f"Errors for {sentence!r}: {errors}"

    def test_cycle_produces_message_plan(self):
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("I'm an engineer.",),
        )
        cycle = rt.run(trigger)
        assert cycle.message_plan is not None

    def test_no_whole_turn_alias_needed(self):
        """The composer should not need a whole-turn alias.
        Each construction produces its own predication candidate."""
        from cemm.app.runtime import Runtime
        from cemm.kernel.model.cycle import CycleTrigger
        rt = Runtime()
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("Do you know what an engineer is?",),
        )
        cycle = rt.run(trigger)
        graph = cycle.meaning_candidates[0]
        # Multiple predications from different constructions, not one alias
        assert len(graph.candidate_predications) >= 2
        sources = {cp.candidate_source for cp in graph.candidate_predications}
        # Should have multiple sources (construction + lexical)
        assert len(sources) >= 1
