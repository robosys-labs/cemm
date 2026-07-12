"""Structural regression tests for CEMM 3.3 forbidden surface-text patterns.

These tests verify that AGENTS.md §5 forbidden patterns (raw-text string
matching, regex, surface-text routing in operational meaning, contracts,
query, safety, patch, response planning) are not present in the designated
kernel components.

For each component, the test asserts the absence of specific known violation
patterns. As fixes are applied, this file should be updated to assert the new
authoritative behavior.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from types import SimpleNamespace

from cemm.kernel import meaning_perceptor
from cemm.kernel import meaning_graph_builder
from cemm.kernel import uol_metadata
from cemm.kernel.output_state_updater import _detect_question_type, OutputStateUpdater


class TestMeaningPerceptorAuthority:
    """MeaningPerceptor must not contain hardcoded English intent cue sets."""

    def test_no_hardcoded_answer_token_set(self):
        source = inspect.getsource(meaning_perceptor)
        assert 'token_set <= {"yes", "yeah", "yup", "no", "nah", "ok", "okay", "sure", "right"}' not in source
        assert "_ANSWER_TOKENS" not in source or "_ANSWER_TOKENS" not in source

    def test_no_dead_hardcoded_query_methods(self):
        source = inspect.getsource(meaning_perceptor)
        assert "def _is_capability_query" not in source
        assert "def _is_self_identity_query" not in source
        assert "def _is_self_knowledge_query" not in source

    def test_teaching_group_uses_data_driven_cue_set(self):
        source = inspect.getsource(meaning_perceptor.MeaningPerceptor._is_teaching_group)
        assert "_TEACHING_CUES" in source
        assert '{"means", "called", "refers", "equals"}' not in source

    def test_repair_group_uses_data_driven_cue_set(self):
        source = inspect.getsource(meaning_perceptor.MeaningPerceptor._is_repair_group)
        assert "cue_set(\"repair\")" in source
        assert '{"mean", "that"}' not in source
        assert '{"what", "mean"}' not in source

    def test_reflect_fallback_uses_frame_alias(self):
        source = inspect.getsource(meaning_perceptor.MeaningPerceptor._intent_key_for_group)
        assert 'frame_alias_set("command_reflect")' in source
        assert '{"reflect", "reflect_on", "introspect", "self_reflect"}' not in source


class TestUOLMetadataAcknowledgment:
    """uol_metadata must expose acknowledgment tokens from JSON, not hardcoded."""

    def test_pure_acknowledgment_set_is_data_driven(self):
        acks = uol_metadata.pure_acknowledgment_set()
        assert "ok" in acks
        assert "okay" in acks
        assert "yes" in acks
        assert "yeah" in acks

    def test_answer_tokens_include_negative_acknowledgments(self):
        acks = meaning_perceptor._ACK_TOKENS
        assert "ok" in acks
        assert "yes" in acks
        assert "no" in acks or "nope" in acks or "nah" in acks

    def test_teaching_cue_contains_teach(self):
        cues = uol_metadata.cue_set("teaching_cue")
        assert "teach" in cues
        assert "means" in cues
        assert "called" in cues


class TestOutputStateUpdaterAuthority:
    """OutputStateUpdater must not regex-parse generated English output text."""

    def test_no_regex_question_patterns(self):
        source = Path("cemm/kernel/output_state_updater.py").read_text(encoding="utf-8")
        assert "_QUESTION_PATTERNS" not in source
        assert "re.findall" not in source
        assert "re.search" not in source

    def test_detect_question_from_response_mode_and_moves(self):
        # Social phatic check-in (e.g. "How are you doing?")
        bundle = SimpleNamespace(moves=[SimpleNamespace(move_type="phatic_response")])
        assert _detect_question_type("social", bundle, None) == ("social_checkin", "social_status")

        # Clarification question
        qc = SimpleNamespace(query_kind="clarification")
        assert _detect_question_type("clarify", None, qc) == ("idiom_confirmation", "yes_no_or_definition")

        # Preference question
        qc = SimpleNamespace(query_kind="profile_dimension")
        assert _detect_question_type("clarify", None, qc) == ("preference_query", "preference")

        # General clarification
        assert _detect_question_type("clarify", None, None) == ("general_question", "free_form")

        # Confirmation write
        assert _detect_question_type("confirm_write", None, None) == ("yes_no", "yes_no")

        # Non-question outputs
        assert _detect_question_type("answer", None, None) == ("", "")
        assert _detect_question_type("acknowledge", None, None) == ("", "")

    def test_update_uses_semantic_contracts(self):
        updater = OutputStateUpdater()
        kernel = SimpleNamespace()
        bundle = SimpleNamespace(moves=[SimpleNamespace(move_type="phatic_response")])
        contract = SimpleNamespace(query_contract=SimpleNamespace(query_kind="clarification"))
        update = updater.update(
            kernel,
            output_text="How are you doing?",
            response_mode="social",
            obligation_contract=contract,
            response_bundle=bundle,
        )
        assert update.pending_assistant_question == "social_checkin"


class TestMeaningGraphBuilderSurfaceRemoval:
    """MeaningGraphBuilder must no longer contain surface relation parsing.

    Per AGENTS.md §3.1 (surface evidence is not authority) and §3.4 (one
    authority per decision), surface relation parsing belongs in the
    perception layer (RelationExtractor), not the graph builder.
    """

    def test_no_surface_teaching_relations_method(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_add_surface_teaching_relations" not in source

    def test_no_parse_surface_relation_method(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_parse_surface_relation" not in source

    def test_no_parse_possessive_relation_method(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_parse_possessive_relation" not in source

    def test_no_clean_relation_side_method(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_clean_relation_side" not in source

    def test_no_split_domain_phrase_method(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_split_domain_phrase" not in source

    def test_no_extract_remember_relation_observations(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_extract_remember_relation_observations" not in source

    def test_no_lookup_relation_verb(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_lookup_relation_verb" not in source

    def test_no_possessive_pronouns_constant(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_POSSESSIVE_PRONOUNS" not in source

    def test_no_contractions_constant(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_CONTRACTIONS" not in source

    def test_no_possessive_slot_to_predicate(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_POSSESSIVE_SLOT_TO_PREDICATE" not in source

    def test_no_subject_pronoun_to_entity(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_SUBJECT_PRONOUN_TO_ENTITY" not in source

    def test_no_possessive_to_entity(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_POSSESSIVE_TO_ENTITY" not in source

    def test_no_discourse_markers_constant(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_DISCOURSE_MARKERS" not in source

    def test_no_filler_words_constant(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_FILLER_WORDS" not in source

    def test_no_remember_extra_verbs(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_REMEMBER_EXTRA_VERBS" not in source

    def test_no_inline_re_import(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "import re" not in source

    def test_no_last_possessive_prop_dim(self):
        source = inspect.getsource(meaning_graph_builder)
        assert "_last_possessive_prop_dim" not in source


class TestRelationExtractorAuthority:
    """RelationExtractor is the perception-layer authority for relation atoms.

    Per AGENTS.md §3.4, one authority per decision. Relation extraction
    belongs in RelationExtractor, not MeaningGraphBuilder.
    """

    def test_relation_extractor_importable(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        assert RelationExtractor is not None

    def test_relation_extractor_produces_atoms_for_possessive(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        from cemm.types.meaning_percept import MeaningGroup, IntentAtom
        extractor = RelationExtractor()
        group = MeaningGroup(
            id="g1",
            group_type="clause",
            surface="my name is Chibueze",
            tokens=["my", "name", "is", "chibueze"],
            confidence=0.6,
            intents=[IntentAtom(intent_key="statement", confidence=0.7, surface="my name is Chibueze", group_id="g1")],
        )
        atoms = extractor.extract([group])
        assert len(atoms) == 1
        atom = atoms[0]
        assert atom.relation_key == "has_property"
        assert atom.features["subject_surface"] == "user"
        assert atom.features["object_surface"] == "Chibueze"
        assert atom.features["property_dimension"] == "name"
        assert atom.features["is_teaching"] is True

    def test_relation_extractor_produces_atoms_for_identity(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        from cemm.types.meaning_percept import MeaningGroup, IntentAtom
        extractor = RelationExtractor()
        group = MeaningGroup(
            id="g1",
            group_type="clause",
            surface="i am Chibueze",
            tokens=["i", "am", "chibueze"],
            confidence=0.6,
            intents=[IntentAtom(intent_key="statement", confidence=0.7, surface="i am Chibueze", group_id="g1")],
        )
        atoms = extractor.extract([group])
        assert len(atoms) == 1
        atom = atoms[0]
        assert atom.relation_key == "is_a"
        assert atom.features["subject_surface"] == "user"
        assert atom.features["object_surface"] == "Chibueze"

    def test_relation_extractor_produces_atoms_for_remember_command(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        from cemm.kernel.semantic_schema_kernel import get_kernel
        from cemm.types.meaning_percept import MeaningGroup, IntentAtom
        extractor = RelationExtractor(schema_kernel=get_kernel())
        group = MeaningGroup(
            id="g1",
            group_type="command",
            surface="remember I like coffee",
            tokens=["remember", "i", "like", "coffee"],
            confidence=0.7,
            intents=[IntentAtom(intent_key="command", confidence=0.8, surface="remember I like coffee", group_id="g1")],
        )
        atoms = extractor.extract([group])
        assert len(atoms) == 1
        atom = atoms[0]
        assert atom.features["is_remember_command"] is True
        assert atom.features["subject_surface"] == "user"
        assert "coffee" in atom.features["object_surface"]

    def test_relation_extractor_rejects_discourse_markers(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        from cemm.types.meaning_percept import MeaningGroup, IntentAtom
        extractor = RelationExtractor()
        group = MeaningGroup(
            id="g1",
            group_type="clause",
            surface="well it is cool",
            tokens=["well", "it", "is", "cool"],
            confidence=0.5,
            intents=[IntentAtom(intent_key="statement", confidence=0.6, surface="well it is cool", group_id="g1")],
        )
        atoms = extractor.extract([group])
        assert len(atoms) == 0

    def test_relation_extractor_uses_data_driven_possessive_pronouns(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert "cue_set(\"possessive_pronoun\")" in source

    def test_relation_extractor_no_hardcoded_contractions(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert "_contractions_map" in source
        assert '"i\'m": "i am"' not in source
        assert '"you\'re": "you are"' not in source

    def test_relation_extractor_no_hardcoded_pronoun_maps(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert "_pronoun_to_entity_map" in source
        assert "_possessive_to_entity_map" in source
        assert '"i": "user"' not in source
        assert '"my": "user"' not in source

    def test_relation_extractor_no_hardcoded_stop_words(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert 'cue_set("stopword")' in source
        assert "frozenset({" not in source

    def test_relation_extractor_no_hardcoded_discourse_markers(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert 'frame_alias_set("discourse_marker")' in source
        assert '"i mean"' not in source
        assert '"you know"' not in source

    def test_relation_extractor_no_hardcoded_filler_words(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert 'cue_set("filler_word")' in source
        assert '"lol"' not in source
        assert '"haha"' not in source

    def test_relation_extractor_no_hardcoded_slot_to_predicate(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert "_slot_to_predicate_map" in source
        assert '"name": ("has_property"' not in source
        assert '"age": ("has_property"' not in source

    def test_relation_extractor_no_hardcoded_remember_verbs(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert "_remember_extra_verbs_map" in source
        assert '"have": "has_property"' not in source

    def test_relation_extractor_no_hardcoded_identity_cues(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert 'cue_set("definition_cue")' in source
        assert 'frozenset({"means"' not in source

    def test_relation_extractor_no_hardcoded_copula_cues(self):
        from cemm.kernel.relation_extractor import RelationExtractor
        source = inspect.getsource(RelationExtractor)
        assert 'cue_set("identity_cue")' in source
        assert 'frozenset({"is"' not in source

    def test_meaning_perceptor_uses_relation_extractor(self):
        source = inspect.getsource(meaning_perceptor)
        assert "RelationExtractor" in source
        assert "_relation_extractor" in source

    def test_possessive_with_leading_discourse_marker(self):
        """'well my name is X' should still produce has_property with name dimension."""
        from cemm.kernel.relation_extractor import RelationExtractor
        from cemm.types.meaning_percept import MeaningGroup, IntentAtom
        extractor = RelationExtractor()
        group = MeaningGroup(
            id="g1",
            group_type="clause",
            surface="well my name is Chibueze",
            tokens=["well", "my", "name", "is", "chibueze"],
            confidence=0.6,
            intents=[IntentAtom(intent_key="statement", confidence=0.7, surface="well my name is Chibueze", group_id="g1")],
        )
        atoms = extractor.extract([group])
        assert len(atoms) == 1
        atom = atoms[0]
        assert atom.relation_key == "has_property"
        assert atom.features["subject_surface"] == "user"
        assert atom.features["property_dimension"] == "name"

    def test_identity_cue_priority_over_copula(self):
        """'X is called Y' should produce same_as (from 'called'), not is_a (from 'is')."""
        from cemm.kernel.relation_extractor import RelationExtractor
        from cemm.types.meaning_percept import MeaningGroup, IntentAtom
        extractor = RelationExtractor()
        group = MeaningGroup(
            id="g1",
            group_type="clause",
            surface="X is called Y",
            tokens=["x", "is", "called", "y"],
            confidence=0.6,
            intents=[IntentAtom(intent_key="statement", confidence=0.7, surface="X is called Y", group_id="g1")],
        )
        atoms = extractor.extract([group])
        assert len(atoms) == 1
        assert atoms[0].relation_key == "same_as"

    def test_identity_falls_through_on_failed_parse(self):
        """If first cue produces empty sides, next cue should be tried."""
        from cemm.kernel.relation_extractor import RelationExtractor
        from cemm.types.meaning_percept import MeaningGroup, IntentAtom
        extractor = RelationExtractor()
        # "is" at index 0 gives empty left, but "am" at index 2 works
        group = MeaningGroup(
            id="g1",
            group_type="clause",
            surface="is I am Chibueze",
            tokens=["is", "i", "am", "chibueze"],
            confidence=0.6,
            intents=[IntentAtom(intent_key="statement", confidence=0.7, surface="is I am Chibueze", group_id="g1")],
        )
        atoms = extractor.extract([group])
        # Should find "am" and produce is_a with user -> Chibueze
        assert len(atoms) == 1
        assert atoms[0].relation_key == "is_a"
        assert atoms[0].features["subject_surface"] == "user"


class TestEntityFactExtractorAuthority:
    """Verify EntityFactExtractor is atom-first only, no regex surface patterns."""

    def test_entity_fact_extractor_no_import_re(self):
        from cemm.kernel import entity_fact_extractor
        source = inspect.getsource(entity_fact_extractor)
        assert "import re" not in source

    def test_entity_fact_extractor_no_regex_compile(self):
        from cemm.kernel import entity_fact_extractor
        source = inspect.getsource(entity_fact_extractor)
        assert "re.compile" not in source
        assert "re.sub" not in source
        assert "re.findall" not in source
        assert "re.search" not in source
        assert "re.split" not in source
        assert "re.escape" not in source

    def test_entity_fact_extractor_no_clause_patterns(self):
        from cemm.kernel import entity_fact_extractor
        source = inspect.getsource(entity_fact_extractor)
        assert "_CLAUSE_PATTERNS" not in source
        assert "_CLAUSE_SPLIT_RE" not in source
        assert "_segment_clauses" not in source

    def test_entity_fact_extractor_no_contractions(self):
        from cemm.kernel import entity_fact_extractor
        source = inspect.getsource(entity_fact_extractor)
        assert "_CONTRACTIONS" not in source
        assert "_expand_contractions" not in source

    def test_entity_fact_extractor_no_surface_patterns_method(self):
        from cemm.kernel import entity_fact_extractor
        source = inspect.getsource(entity_fact_extractor)
        assert "_from_surface_patterns" not in source
        assert "_resolve_possessive_self" not in source
        assert "_is_possessive_self" not in source

    def test_entity_fact_extractor_no_hardcoded_blocked_subjects(self):
        from cemm.kernel import entity_fact_extractor
        source = inspect.getsource(entity_fact_extractor)
        assert 'cue_set("user_subject")' in source
        assert 'cue_set("self_target")' in source
        assert '"i", "me", "my"' not in source

    def test_entity_fact_extractor_uses_uol_metadata(self):
        from cemm.kernel import entity_fact_extractor
        source = inspect.getsource(entity_fact_extractor)
        assert "from .uol_metadata import" in source
        assert "pronoun_to_entity" in source


class TestConversationActClassifierAuthority:
    """Verify conversation_act_classifier has no regex surface patterns."""

    def test_classifier_no_import_re(self):
        from cemm.kernel import conversation_act_classifier
        source = inspect.getsource(conversation_act_classifier)
        assert "import re" not in source

    def test_classifier_no_regex_search(self):
        from cemm.kernel import conversation_act_classifier
        source = inspect.getsource(conversation_act_classifier)
        assert "re.search" not in source
        assert "re.compile" not in source
        assert "re.findall" not in source
        assert "re.sub" not in source

    def test_classifier_no_hardcoded_reciprocal_patterns(self):
        from cemm.kernel import conversation_act_classifier
        source = inspect.getsource(conversation_act_classifier)
        assert "reciprocal_patterns" not in source
        assert 'r"(?:i\'?m' not in source
        assert 'reciprocal_phatic' in source

    def test_classifier_no_hardcoded_retro_repair_patterns(self):
        from cemm.kernel import conversation_act_classifier
        source = inspect.getsource(conversation_act_classifier)
        assert "retro_repair_patterns" not in source
        assert 'r"i just wanted' not in source
        assert "retro_repair" in source

    def test_classifier_no_hardcoded_trouble_patterns(self):
        from cemm.kernel import conversation_act_classifier
        source = inspect.getsource(conversation_act_classifier)
        assert "trouble_patterns" not in source
        assert 'r"looking for' not in source
        assert "social_conflict" in source

    def test_classifier_uses_tokenize_surface_from_text_match(self):
        from cemm.kernel import conversation_act_classifier
        source = inspect.getsource(conversation_act_classifier)
        assert "from .text_match import" in source
        assert "tokenize_surface" in source


class TestSemanticQueryEngineAuthority:
    """Verify semantic_query_engine has no regex."""

    def test_query_engine_no_import_re(self):
        from cemm.kernel import semantic_query_engine
        source = inspect.getsource(semantic_query_engine)
        assert "import re" not in source

    def test_query_engine_no_regex_compile(self):
        from cemm.kernel import semantic_query_engine
        source = inspect.getsource(semantic_query_engine)
        assert "re.compile" not in source
        assert "re.match" not in source
        assert "_STATE_DELTA_SURFACE_RE" not in source

    def test_query_engine_non_answerable_keys_at_module_level(self):
        from cemm.kernel import semantic_query_engine
        source = inspect.getsource(semantic_query_engine)
        assert "_NON_ANSWERABLE_KEYS" in source
        # Should not be defined inside a method body
        assert "frozenset({\n                \"has_role\"" not in source


class TestRealizationVerifierAuthority:
    """Verify realization_verifier has no regex."""

    def test_verifier_no_inline_import_re(self):
        source = Path("cemm/kernel/realization_verifier.py").read_text(encoding="utf-8")
        assert "import re" not in source

    def test_verifier_no_re_split(self):
        source = Path("cemm/kernel/realization_verifier.py").read_text(encoding="utf-8")
        assert "re.split" not in source
