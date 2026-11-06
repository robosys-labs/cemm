"""Bounded, single-writer physical evidence ledger with explicit checkpoint recovery."""
from copy import deepcopy
from hashlib import sha256
import json
from math import fsum
import os
from pathlib import Path
import tempfile

from . import acceptance_contract as c
from .physical_query_v1 import _belief, _row, posterior

VERSION = 'physical-ledger-v1'
MAX_RECEIPTS = 256
MAX_HYPOTHESES = 32
MAX_ENDPOINTS = 64


class Ledger:
    def __init__(self, binding, prior):
        c.fields(binding, ('interpretation_sha256', 'world_sha256', 'source_sha256',
                           'actions', 'endpoint_encoding', 'endpoint_count'))
        for field in ('interpretation_sha256', 'world_sha256', 'source_sha256'):
            c.require(c.is_sha(binding[field]), 'invalid binding digest')
        c.require(c.identifier(binding['endpoint_encoding']), 'invalid endpoint encoding')
        c.require(type(binding['endpoint_count']) is int and
                  1 <= binding['endpoint_count'] <= MAX_ENDPOINTS, 'invalid endpoint count')
        actions = binding['actions']
        c.require(type(actions) in (list, tuple) and
                  1 <= len(actions) <= MAX_HYPOTHESES, 'invalid candidate count')
        for action in actions:
            c.require(type(action) in (list, tuple) and 1 <= len(action) <= 16 and
                      all(type(value) is int and -(2 ** 31) <= value < 2 ** 31 for value in action),
                      'invalid candidate coordinates')
        c.require(len({tuple(action) for action in actions}) == len(actions), 'duplicate candidate')
        c.require(type(prior) in (list, tuple) and len(prior) == len(actions),
                  'prior and candidate dimensions differ')
        try:
            normalized = _row(prior, probability=True)
        except OverflowError as error:
            raise ValueError('invalid initial probability') from error
        self._binding = {**binding, 'actions': [list(action) for action in actions]}
        self._binding_digest = c.digest(self._binding)
        # Persist the original numbers so recovery repeats the same normalization.
        self._initial_prior = tuple(prior)
        self._posterior = normalized
        self._failure_evidence_id = None
        self._receipts = {}

    @property
    def posterior(self):
        return self._posterior

    @property
    def belief(self):
        c.require(self._posterior is not None, 'belief unavailable after failed posterior update')
        return self._posterior

    @property
    def failure_evidence_id(self):
        return self._failure_evidence_id

    @property
    def receipt_count(self):
        return len(self._receipts)

    def add(self, receipt):
        c.fields(receipt, ('evidence_id', 'prefix_digest', 'binding_digest', 'kind',
                           'likelihood', 'endpoint'))
        c.require(c.identifier(receipt['evidence_id']), 'invalid evidence ID')
        c.require(c.is_sha(receipt['prefix_digest']), 'invalid public prefix digest')
        c.require(c.is_sha(receipt['binding_digest']) and
                  receipt['binding_digest'] == self._binding_digest, 'receipt binding mismatch')
        c.require(type(receipt['kind']) is str and receipt['kind'] == 'physical_endpoint',
                  'expected physical endpoint evidence')
        likelihood = receipt['likelihood']
        c.require(type(likelihood) in (list, tuple) and len(likelihood) == len(self._initial_prior)
                  and all(type(row) in (list, tuple) and len(row) == self._binding['endpoint_count']
                          for row in likelihood), 'invalid likelihood dimensions')
        prior = self._posterior if self._posterior is not None else self._initial_prior
        try:
            normalized_prior, normalized_likelihood = _belief(prior, likelihood)
        except OverflowError as error:
            raise ValueError('invalid likelihood probability') from error
        endpoint = receipt['endpoint']
        c.require(type(endpoint) is int and 0 <= endpoint < self._binding['endpoint_count'],
                  'invalid observed endpoint')
        stored = {**receipt, 'likelihood': [list(row) for row in likelihood]}
        evidence_id = stored['evidence_id']
        if evidence_id in self._receipts:
            c.require(c.digest(stored) == c.digest(self._receipts[evidence_id]),
                      'conflicting payload for existing evidence ID')
            return False
        c.require(len(self._receipts) < MAX_RECEIPTS, 'receipt capacity exceeded')
        updated, failed = self._posterior, self._failure_evidence_id
        if updated is not None:
            mass = fsum(p * row[endpoint] for p, row in zip(normalized_prior, normalized_likelihood))
            if mass == 0:
                updated, failed = None, evidence_id
            else:
                updated = posterior(prior, likelihood, endpoint)
        self._receipts[evidence_id] = stored
        self._posterior, self._failure_evidence_id = updated, failed
        return True

    def snapshot(self):
        return {'version': VERSION, 'binding': deepcopy(self._binding),
                'initial_prior': list(self._initial_prior),
                'receipts': deepcopy(list(self._receipts.values()))}

    def save(self, path):
        """Publish a complete explicit checkpoint, returning its externally held SHA-256."""
        raw = (json.dumps(self.snapshot(), sort_keys=True, separators=(',', ':'),
                          allow_nan=False) + '\n').encode()
        c.require(len(raw) <= c.MAX_BYTES, 'checkpoint exceeds size limit')
        path, temporary = Path(path), None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                             prefix='.' + path.name + '.', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return sha256(raw).hexdigest()

    @classmethod
    def load(cls, path, expected_sha256, expected_binding):
        data = c.load_json(path, expected_sha256)
        c.fields(data, ('version', 'binding', 'initial_prior', 'receipts'))
        c.require(data['version'] == VERSION, 'unsupported ledger version')
        ledger = cls(expected_binding, data['initial_prior'])
        c.require(c.digest(data['binding']) == ledger._binding_digest, 'checkpoint binding mismatch')
        c.require(type(data['receipts']) is list and len(data['receipts']) <= MAX_RECEIPTS,
                  'invalid persisted receipt inventory')
        for receipt in data['receipts']:
            c.require(ledger.add(receipt), 'duplicate persisted evidence ID')
        return ledger
