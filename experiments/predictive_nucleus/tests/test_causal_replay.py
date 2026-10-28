"""Cooperative public replay ordering only; no gate or model score."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import threading
import unittest

from experiments.predictive_nucleus.causal_replay import PublicReplay
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode, sensor_view


class Consumer:
    def __init__(self, name, log, *, mutate=False, fail=None):
        self.name, self.log, self.mutate, self.fail = name, log, mutate, fail

    def _record(self, method, payload):
        self.log.append((self.name, method, deepcopy(payload)))
        if self.mutate:
            if method == "predict":
                payload["action"]["participants"].clear()
                payload["observation"]["measurements"].clear()
            else:
                payload["measurements"].clear()
        if self.fail == method:
            raise ValueError(f"{self.name} {method} failure")

    def start(self, anchor):
        self._record("start", anchor)

    def predict(self, turn):
        self._record("predict", turn)

    def receive(self, feedback):
        self._record("receive", feedback)


def fixture(case=0):
    return sensor_view(make_evaluator_episode(case))


class ReplayTests(unittest.TestCase):
    def test_shared_history_order_and_nested_copy_isolation(self):
        view, log = fixture(8), []
        driver = PublicReplay(view)
        driver.run(Consumer("first", log, mutate=True), Consumer("second", log))
        self.assertEqual(driver.state, "completed")
        self.assertEqual([(n, op) for n, op, _ in log[:2]], [("first", "start"), ("second", "start")])
        self.assertEqual(log[0][2], log[1][2])
        for i in range(4):
            group = log[2 + i * 4: 6 + i * 4]
            self.assertEqual([(n, op) for n, op, _ in group],
                             [("first", "predict"), ("second", "predict"),
                              ("first", "receive"), ("second", "receive")])
            self.assertEqual(group[0][2], group[1][2])
            self.assertEqual(group[0][2], view.learner_turn(i))
            self.assertEqual(group[2][2], group[3][2])
            self.assertEqual(group[2][2], view.reveal_after_prediction(i))
            self.assertEqual(set(group[0][2]), {"observation", "action"})
            self.assertEqual(set(group[2][2]), {"t", "measurements"})
        with self.assertRaises(RuntimeError):
            driver.run(Consumer("first", log), Consumer("second", log))
        self.assertEqual(driver.state, "completed")

    def test_future_feedback_perturbation_cannot_change_prior_inputs(self):
        original = fixture(12)
        for t in range(1, 5):
            observations = list(original._observations)
            records = list(observations[t])
            records[0] = (records[0][0], records[0][1] ^ 1)
            observations[t] = tuple(records)
            altered = replace(original, _observations=tuple(observations))
            logs = []
            for view in (original, altered):
                log = []
                PublicReplay(view).run(Consumer("first", log), Consumer("second", log))
                logs.append(log)
            for i in range(t):
                self.assertEqual(logs[0][2 + 4 * i][2], logs[1][2 + 4 * i][2])
            self.assertNotEqual(logs[0][2 + 4 * (t - 1) + 2][2], logs[1][2 + 4 * (t - 1) + 2][2])

    def test_future_action_value_does_not_change_earlier_inputs(self):
        original = fixture(12)
        for changed_step in (2, 3):
            actions = list(original._action_records)
            kind, members, value = actions[changed_step]
            actions[changed_step] = (kind, members, 1 - value)
            altered = replace(original, _action_records=tuple(actions))
            logs = []
            for view in (original, altered):
                log = []
                PublicReplay(view).run(Consumer("first", log), Consumer("second", log))
                logs.append(log)
            for i in range(changed_step):
                self.assertEqual(logs[0][2 + 4 * i][2], logs[1][2 + 4 * i][2])
            self.assertNotEqual(logs[0][2 + 4 * changed_step][2], logs[1][2 + 4 * changed_step][2])

    def test_callback_failures_abort_without_future_calls(self):
        for failing_name, op, expected in (("first", "start", 1), ("second", "predict", 4),
                                            ("second", "receive", 6)):
            with self.subTest(failing_name=failing_name, op=op):
                log = []
                a = Consumer("first", log, fail=op if failing_name == "first" else None)
                b = Consumer("second", log, fail=op if failing_name == "second" else None)
                driver = PublicReplay(fixture())
                with self.assertRaisesRegex(ValueError, "failure"):
                    driver.run(a, b)
                self.assertEqual(driver.state, "aborted")
                self.assertEqual(len(log), expected)
                if op == "predict":
                    self.assertFalse(any(kind == "receive" for _, kind, _ in log))
                with self.assertRaises(RuntimeError):
                    driver.run(a, b)
                self.assertEqual(len(log), expected)

    def test_awaitable_return_is_not_a_completed_prediction(self):
        log = []
        class AsyncConsumer(Consumer):
            async def predict(self, turn):
                self._record("predict", turn)
        driver = PublicReplay(fixture())
        with self.assertRaisesRegex(TypeError, "synchronously"):
            driver.run(AsyncConsumer("first", log), Consumer("second", log))
        self.assertEqual(driver.state, "aborted")
        self.assertEqual([(n, kind) for n, kind, _ in log], [("first", "start"), ("second", "start")])

    def test_generator_returns_are_not_completed_predictions(self):
        for asynchronous in (False, True):
            log = []
            class GeneratorConsumer(Consumer):
                def predict(self, turn):
                    def deferred():
                        self._record("predict", turn)
                        yield None
                    async def async_deferred():
                        self._record("predict", turn)
                        yield None
                    return async_deferred() if asynchronous else deferred()
            driver = PublicReplay(fixture())
            with self.subTest(asynchronous=asynchronous), self.assertRaisesRegex(TypeError, "synchronously"):
                driver.run(GeneratorConsumer("first", log), Consumer("second", log))
            self.assertEqual(driver.state, "aborted")
            self.assertEqual([(n, kind) for n, kind, _ in log],
                             [("first", "start"), ("second", "start")])

    def test_swallowed_reentrant_attempt_still_aborts(self):
        log = []
        driver = PublicReplay(fixture())
        class Reentrant(Consumer):
            def predict(self, turn):
                self._record("predict", turn)
                try:
                    driver.run(self, Consumer("extra", log))
                except RuntimeError:
                    pass
        with self.assertRaisesRegex(RuntimeError, "aborted"):
            driver.run(Reentrant("first", log), Consumer("second", log))
        self.assertEqual(driver.state, "aborted")
        self.assertEqual([(n, op) for n, op, _ in log],
                         [("first", "start"), ("second", "start"), ("first", "predict")])

    def test_concurrent_start_aborts_active_replay(self):
        log, entered, release, errors = [], threading.Event(), threading.Event(), []
        driver = PublicReplay(fixture())
        class Blocking(Consumer):
            def predict(self, turn):
                self._record("predict", turn)
                entered.set()
                if not release.wait(3):
                    raise TimeoutError("test callback timed out")
        first, second = Blocking("first", log), Consumer("second", log)
        def run():
            try:
                driver.run(first, second)
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=run)
        thread.start()
        self.assertTrue(entered.wait(3))
        try:
            with self.assertRaisesRegex(RuntimeError, "concurrent"):
                driver.run(first, second)
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(driver.state, "aborted")
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)
        self.assertFalse(any(kind == "receive" for _, kind, _ in log))

    def test_invalid_consumer_and_malformed_snapshot_rejected(self):
        same = Consumer("same", [])
        duplicate = PublicReplay(fixture())
        with self.assertRaisesRegex(ValueError, "distinct"):
            duplicate.run(same, same)
        self.assertEqual(duplicate.state, "aborted")
        self.assertEqual(same.log, [])
        driver = PublicReplay(fixture())
        with self.assertRaises(TypeError):
            driver.run(object(), Consumer("other", []))
        self.assertEqual(driver.state, "aborted")
        v = fixture()
        broken = list(v._observations)
        broken[1] = (("not-an-identity", 0),)
        with self.assertRaises(ValueError):
            PublicReplay(replace(v, _observations=tuple(broken)))
        with self.assertRaises(ValueError):
            PublicReplay(None)

    @unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed")
    def test_untrained_existing_models_inference_only(self):
        import torch
        from experiments.predictive_nucleus.flat_reference import FlatWorldGRU
        from experiments.predictive_nucleus.latent_model import ContactKernel
        from experiments.predictive_nucleus.uncertainty import EvidenceBelief
        torch.manual_seed(7)
        kernel, flat = ContactKernel().freeze(), FlatWorldGRU()
        class Structured:
            def start(self, anchor):
                self.model = EvidenceBelief(kernel, anchor)
            def predict(self, turn):
                self.model.commit_action(turn["action"])
            def receive(self, feedback):
                self.model.receive(feedback, f'public-{feedback["t"]}')
        class Flat:
            def start(self, anchor):
                flat.reset(anchor, sensor_metadata_mode="neutral")
            def predict(self, turn):
                flat.commit(turn["action"])
            def receive(self, feedback):
                flat.receive(feedback)
        structured = Structured()
        driver = PublicReplay(fixture(5))
        driver.run(structured, Flat())
        self.assertEqual(driver.state, "completed")
        self.assertEqual(structured.model.t, 4)
        self.assertIsNone(structured.model.pending)
        self.assertEqual(flat.time, 4)
        self.assertIsNone(flat.pending)


if __name__ == "__main__":
    unittest.main()
