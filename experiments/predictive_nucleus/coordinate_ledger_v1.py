"""Explicit checkpoint recovery for a fixed, learned-coordinate hypothesis frame."""
from copy import deepcopy
from math import fsum

from . import acceptance_contract as c
from .coordinate_transport_v1 import ENDPOINT_ENCODING, TRANSFORMS, VIEWS
from .physical_ledger_v1 import Ledger, MAX_RECEIPTS
from .physical_query_v1 import _row

VERSION = 'coordinate-ledger-v1'


def _frame(value):
    c.fields(value, ('version', 'language_sha256', 'registry_sha256', 'world_sha256',
                     'lexical_id', 'transforms', 'view'))
    c.require(type(value['version']) is str and value['version'] == 'coordinate-transport-v1' and
              type(value['view']) is str and value['view'] in VIEWS, 'unsupported transport frame')
    c.require(all(c.is_sha(value[name]) for name in
                  ('language_sha256', 'registry_sha256', 'world_sha256', 'lexical_id')),
              'invalid frame digest or lexical identity')
    signs = value['transforms']
    c.require(type(signs) is list and len(signs) == 4 and all(
        type(row) is list and len(row) == 2 and all(type(v) is int for v in row) for row in signs)
        and signs == [list(row) for row in TRANSFORMS], 'ordered hypothesis transforms differ')
    return deepcopy(value)


def _matrix(value, height, width):
    c.require(type(value) in (list, tuple) and len(value) == height and all(
        type(row) in (list, tuple) and len(row) == width for row in value), 'probability dimensions differ')
    try:
        for row in value:
            _row(row, probability=True)
    except OverflowError as error:
        raise ValueError('invalid projection probability') from error
    return [list(row) for row in value]


def _projection(value, frame_digest):
    c.fields(value, ('evidence_id', 'prefix_digest', 'entities', 'actions', 'endpoint_encoding',
                     'action_probabilities', 'native_likelihood', 'likelihood', 'frame', 'frame_digest'))
    c.require(c.identifier(value['evidence_id']) and c.is_sha(value['prefix_digest']),
              'invalid evidence identity or prefix digest')
    frame = _frame(value['frame'])
    c.require(c.is_sha(value['frame_digest']) and
              value['frame_digest'] == c.digest(frame) == frame_digest, 'projection frame differs')
    roster = value['entities']
    c.require(type(roster) is list and len(roster) == 3 and all(map(c.identifier, roster)) and
              len(set(roster)) == 3, 'invalid ordered participant roster')
    actions = value['actions']
    c.require(type(actions) is list and len(actions) == 4 and all(
        type(row) is list and len(row) == 4 and all(type(v) is int for v in row) for row in actions),
        'invalid local action dimensions or coordinates')
    a, b = actions[0][1:3]
    c.require(0 <= a < 3 and 0 <= b < 3 and a != b and
              actions == [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]],
              'local physical menu geometry differs')
    c.require(type(value['endpoint_encoding']) is str and value['endpoint_encoding'] == ENDPOINT_ENCODING,
              'endpoint encoding differs')
    weights = _matrix(value['action_probabilities'], 4, 4)
    native = _matrix(value['native_likelihood'], 4, 8)
    likelihood = _matrix(value['likelihood'], 4, 8)
    c.require(all(abs(.25 * fsum(row[a] for row in weights) - .25) <= 1e-12 for a in range(4)),
              'uniform hypothesis action mixture differs')
    c.require(all(abs(likelihood[h][y] - fsum(weights[h][a] * native[a][y] for a in range(4)))
                  <= 1e-12 for h in range(4) for y in range(8)), 'native projection differs')
    return {**deepcopy(value), 'frame': frame, 'action_probabilities': weights,
            'native_likelihood': native, 'likelihood': likelihood}


class CoordinateLedger(Ledger):
    """Reuse the physical update; its candidate coordinates now name fixed transforms."""
    def __init__(self, frame, source_sha256, prior):
        self._frame = _frame(frame)
        self._frame_digest = c.digest(self._frame)
        super().__init__({'interpretation_sha256': self._frame_digest,
            'world_sha256': self._frame['world_sha256'], 'source_sha256': source_sha256,
            'actions': self._frame['transforms'], 'endpoint_encoding': ENDPOINT_ENCODING,
            'endpoint_count': 8}, prior)
        self._deliveries = {}

    def add(self, projection, endpoint):
        projected = _projection(projection, self._frame_digest)
        c.require(type(endpoint) is int and 0 <= endpoint < 8, 'invalid observed endpoint')
        delivery = {'projection': projected, 'endpoint': endpoint}
        evidence_id = projected['evidence_id']
        if evidence_id in self._deliveries:
            c.require(c.digest(delivery) == c.digest(self._deliveries[evidence_id]),
                      'conflicting full delivery for existing evidence ID')
            return False
        accepted = super().add({'evidence_id': evidence_id, 'prefix_digest': projected['prefix_digest'],
            'binding_digest': self._binding_digest, 'kind': 'physical_endpoint',
            'likelihood': projected['likelihood'], 'endpoint': endpoint})
        c.require(accepted, 'inconsistent physical and full delivery inventories')
        self._deliveries[evidence_id] = delivery
        return True

    def snapshot(self):
        return {'version': VERSION, 'frame': deepcopy(self._frame),
                'source_sha256': self._binding['source_sha256'],
                'initial_prior': list(self._initial_prior),
                'deliveries': deepcopy(list(self._deliveries.values()))}

    @classmethod
    def load(cls, path, expected_sha256, expected_frame, expected_source_sha256):
        data = c.load_json(path, expected_sha256)
        c.fields(data, ('version', 'frame', 'source_sha256', 'initial_prior', 'deliveries'))
        c.require(type(data['version']) is str and data['version'] == VERSION, 'unsupported coordinate ledger')
        ledger = cls(expected_frame, expected_source_sha256, data['initial_prior'])
        c.require(c.digest(_frame(data['frame'])) == ledger._frame_digest and
                  c.is_sha(data['source_sha256']) and data['source_sha256'] == expected_source_sha256,
                  'checkpoint frame or source binding differs')
        deliveries = data['deliveries']
        c.require(type(deliveries) is list and len(deliveries) <= MAX_RECEIPTS,
                  'invalid persisted delivery inventory')
        for delivery in deliveries:
            c.fields(delivery, ('projection', 'endpoint'))
            c.require(ledger.add(delivery['projection'], delivery['endpoint']), 'duplicate persisted evidence ID')
        return ledger
