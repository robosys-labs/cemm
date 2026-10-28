import unittest
from copy import deepcopy
from importlib.util import find_spec
from math import isfinite

from experiments.predictive_nucleus.causal_replay import DevelopmentHistory, FullSensorHistory, PublicReplay
from experiments.predictive_nucleus.development_run import _training_history
from experiments.predictive_nucleus.full_sensor_fixture import make_full_training_history
from experiments.predictive_nucleus.history_memory import HistoryMemory
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode
from experiments.predictive_nucleus.shared_training_smoke import collect_shared_full_sensor
from experiments.predictive_nucleus.world import Action, observe, step


class FullSensorFixtureTests(unittest.TestCase):
    def test_same_actions_and_actual_observations_over_entire_public_schedule(self):
        histories, event_count, target_bits, contacts, sets = [], 0, 0, 0, 0
        for block in (0, 1):
            for case in range(32):
                episode = make_evaluator_episode(case, block=block)
                old = _training_history(episode)
                full = make_full_training_history(case, block=block)
                histories.append(full)
                self.assertEqual(full._action_records, old._action_records)
                self.assertEqual(full._observations[0], old._observations[0])
                self.assertEqual([a[0] for a in full._action_records],
                                 ["contact", "observe", "contact", "set", "set"])
                world = episode.states[0]
                ids = sorted(name for name, _ in old._observations[0])
                for time, (kind, participants, value) in enumerate(old._action_records, 1):
                    world = step(world, Action(kind, participants, value))
                    old_record, new_record = old._observations[time], full._observations[time]
                    self.assertEqual(new_record[:len(old_record)], old_record)
                    self.assertEqual(tuple(name for name, _ in new_record[len(old_record):]),
                                     tuple(name for name in ids if name not in dict(old_record)))
                    sampled = observe(world, time, tuple(name for name, _ in new_record))
                    self.assertEqual(new_record, tuple((m["id"], m["bit"]) for m in sampled["measurements"]))
                    self.assertEqual(set(dict(new_record)), set(ids))
                record = collect_shared_full_sensor(full)
                self.assertEqual(len(record.flat_rows), 5)
                self.assertEqual(len(record.history), 11)
                event_count += len(record.flat_rows)
                target_bits += sum(sum(bit >= 0 for bit in row[1]) for row in record.flat_rows)
                contacts += len(record.contacts)
                sets += len(record.interventions)
        self.assertEqual((event_count, target_bits, contacts, sets), (320, 960, 128, 128))
        memory = HistoryMemory.fit_full_sensor(histories)
        self.assertEqual((memory.episode_count, memory.total_events, memory.complete_targets), (64, 320, 320))

    def test_full_mode_is_explicit_and_complete(self):
        h = make_full_training_history(0)
        with self.assertRaises(ValueError):
            DevelopmentHistory(h._observations, h._action_records)
        with self.assertRaises(ValueError):
            PublicReplay.from_development_history(h)
        with self.assertRaises(ValueError):
            HistoryMemory.fit([h])
        with self.assertRaises(ValueError):
            HistoryMemory.fit_full_sensor([_training_history(make_evaluator_episode(0))])
        for broken in (h._observations[1][:-1], h._observations[1] + (("unknown", 1),),
                       h._observations[1] + (h._observations[1][0],)):
            observations = (h._observations[0], broken, *h._observations[2:])
            with self.assertRaises(ValueError):
                FullSensorHistory(observations, h._action_records)
        m = HistoryMemory.fit_full_sensor([h])
        with self.assertRaises(ValueError):
            HistoryMemory(m._rows, m.episode_count, m.total_events, m.complete_targets)
        with self.assertRaises(ValueError):
            HistoryMemory(m._rows, m.episode_count, m.total_events, m.complete_targets, "other")

    def test_memory_and_shared_replay_enforce_full_feedback_after_prediction(self):
        h = make_full_training_history(0)
        memory = HistoryMemory.fit_full_sensor([h])
        class Recorder:
            def __init__(self): self.model, self.results, self.events = memory.new_predictor(), [], []
            def start(self, anchor): self.model.start(anchor); self.events.append(("start", deepcopy(anchor)))
            def predict(self, turn):
                self.events.append(("predict", deepcopy(turn)))
                self.results.append(self.model.predict(turn))
            def receive(self, feedback):
                self.events.append(("receive", deepcopy(feedback))); self.model.receive(feedback)
        a, b = Recorder(), Recorder()
        PublicReplay.from_full_sensor_history(h).run(a, b)
        self.assertEqual(a.events, b.events)
        self.assertEqual([event[0] for event in a.events], ["start"] + [x for _ in range(5) for x in ("predict", "receive")])
        self.assertTrue(all(result["status"] == "PREDICTED" for result in a.results))
        m = memory.new_predictor()
        m.start(h.learner_turn(0)["observation"])
        m.predict(h.learner_turn(0))
        partial = deepcopy(h.reveal_after_prediction(0))
        partial["measurements"].pop()
        with self.assertRaises(ValueError): m.receive(partial)
        m.receive(h.reveal_after_prediction(0))

    def test_full_replay_copies_each_payload_and_predicts_before_feedback(self):
        h, events = make_full_training_history(0), []
        class Consumer:
            def __init__(self, name, mutate): self.name, self.mutate = name, mutate
            def record(self, op, value):
                events.append((self.name, op, deepcopy(value)))
                if self.mutate:
                    (value["observation"] if op == "predict" else value)["measurements"].clear()
                    if op == "predict": value["action"]["participants"].clear()
            def start(self, anchor): self.record("start", anchor)
            def predict(self, turn): self.record("predict", turn)
            def receive(self, feedback): self.record("receive", feedback)
        replay = PublicReplay.from_full_sensor_history(h)
        replay.run(Consumer("first", True), Consumer("second", False))
        self.assertEqual(replay.state, "completed")
        self.assertEqual(events[0][2], events[1][2])
        for i in range(5):
            group = events[2 + 4*i: 6 + 4*i]
            self.assertEqual([(name, op) for name, op, _ in group],
                             [("first", "predict"), ("second", "predict"),
                              ("first", "receive"), ("second", "receive")])
            self.assertEqual(group[0][2], group[1][2])
            self.assertEqual(group[1][2], h.learner_turn(i))
            self.assertEqual(group[2][2], group[3][2])
            self.assertEqual(group[3][2], h.reveal_after_prediction(i))

    @unittest.skipUnless(find_spec("torch") is not None, "PyTorch is not installed")
    def test_one_update_on_the_shared_complete_sensor_histories(self):
        """Wiring and finite gradients only, never a model comparison."""
        import torch
        from experiments.predictive_nucleus.flat_reference import fit_flat
        from experiments.predictive_nucleus.latent_model import fit_kernel
        from experiments.predictive_nucleus.shared_training_smoke import tensorize

        old_threads = torch.get_num_threads()
        try:
            with torch.random.fork_rng(devices=[]):
                torch.set_num_threads(1)
                records = [collect_shared_full_sensor(make_full_training_history(i, block=b))
                           for b in (0, 1) for i in range(32)]
                batch, samples = tensorize(records)
                self.assertEqual(int(batch[2].sum()), 320)
                self.assertEqual(int((batch[1] >= 0).sum()), 960)
                self.assertEqual((samples.episodes, len(samples.contact), len(samples.intervention)), (64, 128, 128))
                structured, sinfo = fit_kernel(samples, 7, steps=1)
                flat, finfo = fit_flat(batch, 7, max_steps=1, fixed_steps=1, wall_budget_seconds=60.0)
                self.assertEqual((sinfo["gradient_steps"], finfo["gradient_steps"]), (1, 1))
                self.assertTrue(all(isfinite(sinfo[key]) for key in ("train_marginal_nll", "train_set_nll")))
                self.assertTrue(isfinite(finfo["training_sensor_nll"]))
                for model in (structured, flat):
                    gradients = [parameter.grad for parameter in model.parameters()]
                    self.assertTrue(all(g is not None and bool(torch.isfinite(g).all()) for g in gradients))
                    self.assertTrue(any(bool((g != 0).any()) for g in gradients))
        finally:
            torch.set_num_threads(old_threads)


if __name__ == "__main__":
    unittest.main()
