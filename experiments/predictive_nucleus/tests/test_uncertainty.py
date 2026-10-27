"""Deterministic instrumentation tests. Toy kernel is a test-only stand-in."""
import copy
import unittest
from experiments.predictive_nucleus.uncertainty import EvidenceBelief


class ToyKernel:
    """Hand-authored independent fixture ONLY; not imported in inference."""
    def contact(self, a, b, hypothesis):
        if hypothesis == 0:
            result = (a, b ^ a)
        else:
            result = (a ^ b, b)
        probs = [0.0] * 4
        probs[2 * result[0] + result[1]] = 1.0
        return tuple(probs)

    def intervention(self, previous, value):
        return (1 - value, value)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.first = {"t": 0, "measurements": [
            {"id": "C", "bit": 0}, {"id": "B", "bit": 0}, {"id": "A", "bit": 1}]}
        self.contact = {"kind": "contact", "participants": ["A", "B"]}
        self.belief = EvidenceBelief(ToyKernel(), self.first)

    def test_same_observation_multiple_plausible_worlds_abstain(self):
        belief = self.belief
        result = belief.assess(self.contact)
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertTrue(result["abstain"])
        self.assertAlmostEqual(result["max_full_world_probability"], 0.5)
        self.assertAlmostEqual(result["expected_info_gain_bits"], 1)
        self.assertEqual(belief.mechanism_masses(), (0.5, 0.5))

    def test_probe_preview_pure_and_orientation_correlated_across_steps(self):
        belief = self.belief
        before = copy.deepcopy(belief.mass)
        self.assertAlmostEqual(belief.choose_probe([self.contact])["expected_info_gain_bits"], 1)
        self.assertEqual(before, belief.mass)
        belief.commit_action(self.contact)
        outcome = belief.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 1}, {"id": "C", "bit": 0}]}, "source-1")
        self.assertEqual(outcome.status, "EVIDENCE_SUPPORTED")
        self.assertEqual(belief.mechanism_masses(), (1, 0))
        self.assertEqual(belief.assess({"kind": "contact", "participants": ["B", "A"]})["status"],
                         "PREDICT_WITH_EVIDENCE")
        belief.commit_action({"kind": "contact", "participants": ["B", "A"]})
        belief.receive({"t": 2, "measurements": [
            {"id": "A", "bit": 0}, {"id": "B", "bit": 1}, {"id": "C", "bit": 0}]}, "source-2")
        self.assertEqual(belief.mechanism_masses(), (1, 0))

    def test_partial_observation_retains_competing_hypotheses(self):
        self.belief.commit_action(self.contact)
        observation = {"t": 1, "measurements": [{"id": "C", "bit": 0}]}
        receipt = self.belief.receive(observation, "partial-1")
        self.assertEqual(receipt.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(self.belief.mechanism_masses(), (.5, .5))
        self.assertEqual(self.belief.receipts["partial-1"], receipt)
        self.assertEqual(self.belief.receive(observation, "partial-1"), receipt)
        self.assertEqual(self.belief.mechanism_masses(), (.5, .5))
        with self.assertRaisesRegex(ValueError, "conflicting payload"):
            self.belief.receive({"t": 1, "measurements": [{"id": "C", "bit": 1}]}, "partial-1")
        with self.assertRaises(RuntimeError):
            self.belief.receive(observation, "alternate-duplicate-id")

    def test_all_hypotheses_disagree_is_model_mismatch_not_ambiguity(self):
        self.belief.commit_action(self.contact)
        receipt = self.belief.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 1}]}, "bad-evidence")
        self.assertEqual(receipt.status, "MODEL_MISMATCH_CANDIDATE")
        self.assertEqual(receipt.observed_probability, 0)
        self.assertEqual(self.belief.assess(self.contact)["status"], "MODEL_MISMATCH_CANDIDATE")
        self.assertTrue(self.belief.assess(self.contact)["abstain"])
        self.assertEqual(self.belief.mechanism_masses(), (.5, .5))

    def test_agreeing_hypotheses_allow_prediction_despite_latent_ambiguity(self):
        belief = EvidenceBelief(ToyKernel(), {"t": 0, "measurements": [
            {"id": "A", "bit": 0}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]})
        result = belief.assess(self.contact)
        self.assertEqual(result["orientation_entropy"], 1)
        self.assertEqual(result["status"], "PREDICT_WITH_EVIDENCE")
        self.assertEqual(belief.choose_probe([self.contact])["reason"], "NO_DISCRIMINATING_PROBE")
        preparations = [{"kind": "set", "participants": ["A"], "value": bit} for bit in (0, 1)]
        choice = belief.choose_probe([self.contact], interventions=preparations)
        self.assertEqual(choice["reason"], "PREPARE_INTERVENTION")
        self.assertEqual(choice["action"]["value"], 1)
        self.assertEqual(belief.t, 0)
        self.assertIsNone(belief.pending)
        belief.commit_action(choice["action"])
        belief.receive({"t": 1, "measurements": [{"id": "A", "bit": 1}]}, "prepared")
        self.assertAlmostEqual(belief.choose_probe([self.contact])["expected_info_gain_bits"], 1)

    def test_no_belief_reset_from_unknown_future_or_identity(self):
        belief = self.belief
        before = belief.mass.copy()
        for action in ({"kind": "contact", "participants": ["A", "UNKNOWN"]},
                       {"kind": "set", "participants": ["B"], "value": 5},
                       {"kind": "contact", "participants": ["A"]}):
            with self.assertRaises(ValueError):
                belief.preview(action)
        self.assertEqual(belief.mass, before)
        belief.commit_action(self.contact)
        with self.assertRaises(RuntimeError):
            belief.receive({"t": 3, "measurements": []}, "badtime")
        self.assertIsNotNone(belief.pending)


class ContradictionTests(unittest.TestCase):
    def test_surprising_alternative_is_evidence_conflict_not_no_rule(self):
        class SmoothKernel(ToyKernel):
            def contact(self, a, b, hypothesis):
                exact = super().contact(a, b, hypothesis)
                return tuple(.998 * x + .0005 for x in exact)
        start = {'t': 0, 'measurements': [
            {'id': 'A', 'bit': 1}, {'id': 'B', 'bit': 0}, {'id': 'C', 'bit': 0}]}
        believer = EvidenceBelief(SmoothKernel(), start)
        believer.commit_action({'kind': 'contact', 'participants': ['A', 'B']})
        believer.receive({'t': 1, 'measurements': [
            {'id': 'A', 'bit': 1}, {'id': 'B', 'bit': 1}, {'id': 'C', 'bit': 0}]}, 'observed-influence')
        self.assertLess(believer.mechanism_masses()[1], .01)
        action = {'kind': 'contact', 'participants': ['A', 'B']}
        believer.commit_action(action)
        result = believer.receive({'t': 2, 'measurements': [
            {'id': 'A', 'bit': 0}, {'id': 'B', 'bit': 1}, {'id': 'C', 'bit': 0}]}, 'contradiction')
        self.assertEqual(result.status, 'CONFLICTING_EVIDENCE')
        self.assertLess(result.observed_probability, .03)
        self.assertGreater(result.best_hypothesis_likelihood, .9)
        self.assertEqual(believer.assess(action)['status'], 'CONFLICTING_EVIDENCE')
        self.assertTrue(believer.assess(action)['abstain'])
