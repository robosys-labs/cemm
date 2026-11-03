"""Freeze the communication study and guard each write-once research stage."""
from contextlib import contextmanager
import platform
import subprocess
import sys
import time

from . import continuation_run as io
from .acceptance_contract import require

ROOT, REPO = io.ROOT, io.REPO
BASE = 'a0ec72982c9f2b1808564c88da46b1e2aa316fb6'
REF = 'refs/heads/research/g4-communication-v1'
ORIGIN = 'https://github.com/robosys-labs/cemm.git'
FREEZE = ROOT / 'communication_freeze_v1.json'
RESULTS = ROOT / 'results/communication-v1'
STAGES = {'fit': 'fit', 'collect': 'raw', 'score': 'scored'}
G3_INPUTS = ('data/effect-role-v3', 'data/effect-role-fit-v3', 'data/set-acquisition-fit-v2',
             'results/effect-role-v3/traces', 'acceptance_contract.py', 'acceptance_scoring.py',
             'continuation_run.py')
write_json = io._write


def _relative(path):
    return path.relative_to(REPO).as_posix()


def _manifest():
    sources = {*ROOT.glob('communication_*.py'), *ROOT.glob('communication_protocol*.json'),
               *ROOT.glob('tests/test_communication_*.py'), ROOT / 'COMMUNICATION_STUDY_V1.md'}
    bank = ROOT / 'data/communication-v1'
    expected = {f'{law}-{suffix}.json.xz' for law in ('nand', 'nor')
                for suffix in ('lineage', 'train-targets', 'challenge-targets')}
    require({p.name for p in bank.iterdir()} == expected, 'prepared bank inventory differs')
    parents = {}
    for name in G3_INPUTS:
        path = _relative(ROOT / name)
        parents[name] = io._git('rev-parse', f'{BASE}:{path}')
        require(io._git('rev-parse', f'HEAD:{path}') == parents[name],
                'inherited G3 dependency changed: ' + name)
    return {'base': BASE, 'g3_objects': parents,
            'sources': {p.relative_to(ROOT).as_posix(): io._hash(p) for p in sorted(sources)},
            'prepared': {name: io._hash(bank / name) for name in sorted(expected)},
            'runtime': {'python': sys.version, 'implementation': sys.implementation.name,
                        'machine': platform.machine(), 'libc': list(platform.libc_ver())}}


def freeze():
    """Preparation only. Does not fit, inspect the challenge or run a policy."""
    require(not RESULTS.exists(), 'research outputs already exist')
    return write_json(FREEZE, _manifest())


def _unchanged_since_added(path, marker):
    """The current artifact tree must equal its first committed version."""
    added = io._git('log', BASE + '..HEAD', '--format=%H', '--diff-filter=A', '--',
                    _relative(marker)).splitlines()
    require(len(added) == 1, 'missing or recreated publication: ' + marker.name)
    rel = _relative(path)
    require(io._git('rev-parse', f'{added[0]}:{rel}') == io._git('rev-parse', f'HEAD:{rel}'),
            'published evidence changed: ' + rel)
    return added[0]


def _outputs(directory):
    paths = [p for p in directory.rglob('*') if p.is_file()
             and p not in (directory / 'attempt.json', directory / 'receipt.json')]
    require(paths and not any(p.is_symlink() for p in paths), 'missing or linked stage output')
    return {p.relative_to(directory).as_posix(): io._hash(p) for p in sorted(paths)}


def _preflight(stage):
    require(stage in STAGES and io._git('status', '--porcelain', '--untracked-files=all') == '',
            'a clean committed checkout is required')
    head = io._git('rev-parse', 'HEAD')
    io._git('merge-base', '--is-ancestor', BASE, head)
    # Transport failures precede the attempt. A read-only preflight may be repeated.
    remote = subprocess.check_output(['git', 'ls-remote', '--exit-code', ORIGIN, REF],
                                     text=True, timeout=45).split()
    require(remote == [head, REF], 'HEAD is not the published study tip')
    require(io._read(FREEZE) == _manifest(), 'source, G3 objects or runtime differ from freeze')
    published = _unchanged_since_added(FREEZE, FREEZE)
    for index, (previous, name) in enumerate(STAGES.items()):
        directory = RESULTS / name
        if previous == stage:
            require(head == published, 'run directly from the preceding publication')
            require(not any((RESULTS / n).exists() for n in tuple(STAGES.values())[index:]),
                    'current or later stage already attempted')
            return head
        attempt = io._read(directory / 'attempt.json')
        receipt = io._read(directory / 'receipt.json')
        require(attempt == {'stage': previous, 'input_head': published}
                and receipt['status'] == 'complete' and receipt['outputs'] == _outputs(directory),
                'incomplete or mismatched prerequisite: ' + previous)
        published = _unchanged_since_added(directory, directory / 'attempt.json')


@contextmanager
def published_stage(stage):
    head = _preflight(stage)
    destination = RESULTS / STAGES[stage]
    destination.mkdir(parents=True, exist_ok=False)
    write_json(destination / 'attempt.json', {'stage': stage, 'input_head': head})
    cpu, wall = time.process_time(), time.monotonic()
    try:
        yield destination
        receipt = {'status': 'complete', 'outputs': _outputs(destination)}
    except BaseException as exc:
        receipt = {'status': 'failed', 'error': repr(exc)}
        raise
    finally:
        receipt.update(cpu_seconds=time.process_time() - cpu, wall_seconds=time.monotonic() - wall)
        if sys.platform.startswith('linux'):
            import resource
            receipt['peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        write_json(destination / 'receipt.json', receipt)


if __name__ == '__main__':
    freeze()
