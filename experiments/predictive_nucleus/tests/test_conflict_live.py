import unittest

from experiments.predictive_nucleus.conflict_live import _prefix


class ConflictLiveTests(unittest.TestCase):
    def test_final_reading_is_redacted_before_g3_inference(self):
        record = dict(id='r', entities=['a', 'b', 'c'], anchor=[0, 0, 0], context=[],
                      utterances=[dict(text='a lights b', reading=[1, 0, 0]),
                                  dict(text='b lights c', reading=[1, 1, 1])])
        prefix = _prefix(record)
        self.assertEqual(prefix['utterances'][-1], dict(text='b lights c', reading=[0, 0, 0]))
        self.assertEqual(prefix['utterances'][0], record['utterances'][0])
        self.assertEqual(record['utterances'][-1]['reading'], [1, 1, 1])
