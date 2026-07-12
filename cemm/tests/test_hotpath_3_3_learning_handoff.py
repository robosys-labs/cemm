from types import SimpleNamespace

from cemm.learning.learning_answer_assimilator import LearningAnswerAssimilator
from cemm.learning.learning_episode_manager import LearningEpisodeManager
from cemm.types.learning_episode import LearningObligation, QuestionActKind


def test_pending_obligation_round_trips_and_consumes_next_turn():
    manager = LearningEpisodeManager()
    gap = SimpleNamespace(gap_id="gap-president")
    episode = manager.create_episode("ctx", [gap])
    obligation = LearningObligation(
        obligation_id="q1", episode_id=episode.episode_id,
        gap_ids=("gap-president",),
        question_act=QuestionActKind.ASK_SEMANTIC_KIND,
        expected_answer_schema={"answer_kind": "semantic_type"},
        created_turn_signal_id="assistant-turn",
    )
    manager.register_obligation(episode.episode_id, obligation)
    state = manager.context_to_dict("ctx")

    restored = LearningEpisodeManager()
    restored.restore_context("ctx", state)
    pending = restored.pending_obligations("ctx")
    assert len(pending) == 1
    restored_episode, restored_obligation = pending[0]

    relation = SimpleNamespace(
        proposition_mode="asserted",
        features={"proposition_mode": "asserted", "object_surface": "leader"},
    )
    percept = SimpleNamespace(relations=[relation], referents=[], states=[], tokens=["a", "leader"], unknown_lexemes=[])
    fields = LearningAnswerAssimilator().assimilate(
        restored_episode, restored_obligation, "a leader", percept,
    )
    assert fields == [("semantic_type", "leader")]
    assert restored.apply_answer_fields(
        restored_episode.episode_id, restored_obligation.obligation_id, fields,
        evidence_signal_id="user-turn",
    )
    assert restored.pending_obligations("ctx") == []
