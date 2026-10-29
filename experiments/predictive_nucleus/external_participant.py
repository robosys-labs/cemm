"""Standalone JSONL participant. Evaluator truth/scoring must stay in another process.

Run the EXPORTED copy with the manifest hash supplied out of band. Hashes are
integrity checks, not signatures or a sandbox. This does not authorize G1.
"""
from collections import Counter
from hashlib import sha256
import importlib
import json
import math
from pathlib import Path
import sys
from time import perf_counter, process_time

MAX_LINE = 65536


def require(ok, message):
    if not ok:
        raise ValueError(message)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON constant')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def verify_bundle(root, expected):
    raw = (root / 'manifest.json').read_bytes()
    require(sha256(raw).hexdigest() == expected, 'manifest hash mismatch')
    manifest = strict_json(raw)
    require(manifest['format'] == 'cemm-external-participant-v1', 'unsupported bundle')
    for name, digest in manifest['files'].items():
        relative = Path(name)
        path = root / relative
        require(not relative.is_absolute() and '..' not in relative.parts and
                not any(p.is_symlink() for p in (path, *path.parents) if p != root.parent) and
                path.resolve().is_relative_to(root), 'unsafe bundle path')
        require(sha256(path.read_bytes()).hexdigest() == digest, f'bundle file mismatch: {name}')
    return manifest


def restore(core, manifest, root, name, seed):
    """Only previously selected checkpoints/tables; no checkpoint paths from input."""
    import torch
    factories = importlib.import_module(core + '.informative_curriculum').model_factories()
    joint = importlib.import_module(core + '.joint_objective')
    memory_type = importlib.import_module(core + '.empirical_joint').SensorMemory
    if name in factories:
        rows = [r for r in manifest['models'] if r['model'] == name and r['seed'] == seed]
        require(len(rows) == 1, 'unknown model/seed')
        row = rows[0]
        tensors = torch.load(root / row['file'], map_location='cpu', weights_only=True)
        require(type(tensors) is dict and all(type(k) is str and type(v) is torch.Tensor for k, v in tensors.items()),
                'checkpoint must contain plain tensors')
        require(joint.fingerprint(tensors) == row['tensor_sha256'], 'tensor fingerprint mismatch')
        with torch.random.fork_rng(devices=[]):
            model = factories[name]()
        expected = model.state_dict()
        require(set(expected) == set(tensors), 'checkpoint key mismatch')
        for key, value in tensors.items():
            require(value.dtype == expected[key].dtype and value.shape == expected[key].shape and
                    value.layout == torch.strided and bool(torch.isfinite(value).all()), 'invalid checkpoint tensor')
        model.load_state_dict(tensors, strict=True)
        require(joint.fingerprint(model.state_dict()) == row['tensor_sha256'], 'loaded fingerprint mismatch')
        return model.eval(), None
    require(seed is None, 'controls have no seed replication')
    require(name in ('prefix', 'local', 'contact', 'first_contact', 'no_change'), 'unknown control')
    if name == 'no_change':
        return None, None
    mode = 'contact' if name == 'first_contact' else name
    row = next(r for r in manifest['controls'] if r['model'] == mode)
    saved = strict_json((root / row['file']).read_bytes())
    require(saved['mode'] == mode, 'table mode mismatch')
    memory = memory_type(mode)
    def tuples(value):
        return tuple(map(tuples, value)) if isinstance(value, list) else value
    for key, entries in saved['rows']:
        key = tuples(key)
        require(key not in memory.table and entries, 'duplicate/empty table key')
        counts = Counter()
        for world, count in entries:
            world = tuples(world)
            require(len(world) == 3 and all(type(b) is int and b in (0, 1) for b in world) and
                    type(count) is int and count > 0 and world not in counts, 'invalid table count')
            counts[world] = count
        memory.table[key] = counts
    require(memory.digest() == row['table_sha256'] == saved['table_sha256'], 'table digest mismatch')
    return None, memory


class Session:
    """One episode; predict must finish before matching feedback can be accepted."""
    def __init__(self, paths, scores, joint, *, model=None, memory=None, control=None):
        self.paths, self.scores, self.joint = paths, scores, joint
        self.model, self.memory, self.control = model, memory, control
        self.phase, self.step, self.receipt = 'NEW', 0, None
        self.weights = joint.fingerprint(model.state_dict()) if model is not None else None
        self.table = memory.digest() if memory is not None else None

    def _observation(self, data, anchor=False):
        import torch
        require(type(data) is dict and set(data) == set(self.ids), 'observation must name exactly the three IDs')
        values = [data[name] for name in self.ids]
        require(all(v is None or (type(v) is int and v in (0, 1)) for v in values), 'invalid reading')
        require(not anchor or all(v is not None for v in values), 'full anchor required')
        return (torch.tensor([[v if v is not None else -1 for v in values]], dtype=torch.float64),
                torch.tensor([[v is not None for v in values]], dtype=torch.bool))

    def _action(self, data):
        import torch
        require(type(data) is dict and data.get('kind') in ('contact', 'set', 'observe'), 'invalid action')
        kind = data['kind']
        require(set(data) == ({'kind', 'participants', 'value'} if kind == 'set' else {'kind', 'participants'}),
                'extra/missing action field')
        members = data['participants']
        require(type(members) is list and all(type(n) is str and n in self.ids for n in members) and
                len(members) == {'contact': 2, 'set': 1, 'observe': 0}[kind] and
                len(set(members)) == len(members), 'invalid action participants')
        value = data.get('value', -1)
        require(type(value) is int and (kind != 'set' or value in (0, 1)), 'invalid set value')
        return torch.tensor([[('contact', 'set', 'observe').index(kind),
            self.ids.index(members[0]) if members else -1,
            self.ids.index(members[1]) if len(members) == 2 else -1, value]], dtype=torch.long)

    def handle(self, request):
        import torch
        require(self.phase not in ('ERROR', 'CLOSED'), 'session closed; no retries')
        try:
            with torch.inference_mode():
                return self._handle(request)
        except BaseException:
            self.phase = 'ERROR'
            raise

    def _handle(self, r):
        require(type(r) is dict and type(r.get('op')) is str, 'invalid command')
        op = r['op']
        if op == 'start':
            require(self.phase == 'NEW' and set(r) == {'op', 'episode', 'ids', 'observation'}, 'invalid start')
            require(type(r['episode']) is str and 0 < len(r['episode']) <= 128, 'invalid episode identifier')
            require(type(r['ids']) is list and len(r['ids']) == 3 and
                    all(type(x) is str and 0 < len(x) <= 128 for x in r['ids']) and len(set(r['ids'])) == 3,
                    'exactly three distinct IDs required')
            self.episode, self.ids = r['episode'], tuple(sorted(r['ids']))
            anchor, _ = self._observation(r['observation'], anchor=True)
            self.filter = (self.paths.NeuralPaths(self.model, anchor) if self.model is not None else
                           self.paths.EmpiricalPaths(self.memory, anchor, first_contact=self.control == 'first_contact')
                           if self.memory is not None else self.paths.LastObserved(anchor))
            self.phase = 'READY'
            return {'status': 'STARTED', 'episode': self.episode, 'ids': self.ids,
                    'world_order': self.paths.WORLDS, 'gate_g1': 'NOT_ADMITTED'}
        require(self.phase != 'NEW' and r.get('episode') == self.episode, 'episode mismatch')
        if op == 'end':
            require(set(r) == {'op', 'episode'}, 'invalid end')
            require(self.model is None or self.joint.fingerprint(self.model.state_dict()) == self.weights, 'weights changed')
            require(self.memory is None or self.memory.digest() == self.table, 'control table changed')
            pending = self.phase == 'PENDING'
            self.phase = 'CLOSED'
            return {'status': 'ENDED', 'feedback_steps': self.step, 'pending_forecast': pending,
                    'predictions': self.step + int(pending), 'evaluated': False}
        require(type(r.get('step')) is int and r['step'] == self.step, 'step mismatch or duplicate feedback')
        if op == 'predict':
            require(self.phase == 'READY' and set(r) == {'op', 'episode', 'step', 'action'}, 'predict ordering/fields')
            require(self.step < 128, 'transport step cap exceeded')
            action = self._action(r['action'])
            start, cpu = perf_counter(), process_time()
            raw, answered = self.filter.predict(action)
            norm, correction = self.scores.normalize(raw.clone(), answered)
            response = {'status': 'PREDICTED' if answered[0] else 'ABSTAIN', 'episode': self.episode,
                        'step': self.step, 'ids': self.ids, 'raw_log': self.scores.log_record(raw.numpy()),
                        'log': self.scores.log_record(norm), 'subtracted_log_mass': correction.tolist(),
                        'filter': dict(self.filter.diagnostic), 'wall_seconds': perf_counter() - start,
                        'cpu_seconds': process_time() - cpu}
            if not answered[0]:
                response.update(raw_log=None, log=None, reason='unsupported empirical history')
            canonical = {key: value for key, value in response.items() if key not in ('wall_seconds', 'cpu_seconds')}
            self.receipt = sha256(json.dumps(canonical, sort_keys=True, allow_nan=False).encode()).hexdigest()
            response['receipt'] = self.receipt
            self.phase = 'PENDING'
            return response
        require(op == 'feedback' and self.phase == 'PENDING' and
                set(r) == {'op', 'episode', 'step', 'receipt', 'observation'} and r['receipt'] == self.receipt,
                'feedback ordering/receipt/fields')
        reading, mask = self._observation(r['observation'])
        self.filter.receive(reading, mask)
        self.step += 1
        self.phase = 'READY'
        return {'status': 'RECEIVED', 'episode': self.episode, 'next_step': self.step}


def serve(session, incoming, outgoing):
    """Read one frame, write/flush one response, then read the next frame."""
    try:
        while session.phase != 'CLOSED':
            line = incoming.readline(MAX_LINE + 1)
            require(line and len(line) <= MAX_LINE and line.endswith('\n'), 'truncated/oversized frame or missing end')
            reply = session.handle(strict_json(line))
            outgoing.write(json.dumps(reply, sort_keys=True, allow_nan=False) + '\n')
            outgoing.flush()
        return 0
    except Exception as error:
        session.phase = 'ERROR'
        outgoing.write(json.dumps({'status': 'ERROR', 'error_type': type(error).__name__,
                                    'message': str(error), 'step': session.step, 'evaluated': False}) + '\n')
        outgoing.flush()
        return 2


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--participant', required=True)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = verify_bundle(root, args.manifest_sha256)  # before importing bundle code
    import numpy as np
    import torch
    require(sys.version_info[:2] == (3, 13) and torch.__version__ == '2.10.0+cpu' and np.__version__ == '2.3.5',
            'requires Python 3.13, CPU PyTorch 2.10.0 and NumPy 2.3.5')
    require(torch.version.cuda is None and torch.version.hip is None, 'CPU-only build required')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    core = 'participant_core'
    model, memory = restore(core, manifest, root, args.participant, args.seed)
    session = Session(importlib.import_module(core + '.masked_replay'),
                      importlib.import_module(core + '.comparison_scoring'),
                      importlib.import_module(core + '.joint_objective'),
                      model=model, memory=memory, control=args.participant)
    return serve(session, sys.stdin, sys.stdout)


if __name__ == '__main__':
    sys.exit(main())
