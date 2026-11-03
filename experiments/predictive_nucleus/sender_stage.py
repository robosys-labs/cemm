"""Write-once publication stages for the goal-dependent sender study."""
from contextlib import contextmanager
import platform
import resource
import subprocess
import sys
import time

from . import continuation_run as io
from .acceptance_contract import require
from .communication_freeze import _outputs

BASE = 'f654226c11d22accfa4c161aa5997053f0e5011f'
BRANCH = 'refs/heads/research/g4-goal-sender-v1'
ORIGIN = 'https://github.com/robosys-labs/cemm.git'
DATA = io.ROOT / 'data/sender-v1'
RESULTS = io.ROOT / 'results/sender-v1'
FREEZE = io.ROOT / 'sender_freeze_v1.json'
STAGES = ('fit', 'raw', 'scored')


def manifest():
    expected = {f'{law}-{split}-{kind}.json.xz' for law in ('nand', 'nor')
                for split in ('train', 'challenge') for kind in ('pairs', 'targets')}
    require({p.name for p in DATA.iterdir()} == expected, 'prepared files differ')
    paths = [io.ROOT / 'SENDER_STUDY_V1.md', *io.ROOT.glob('sender_*.py'),
             *io.ROOT.glob('tests/test_sender*.py'), *DATA.iterdir()]
    return dict(parent=BASE, python=sys.version, implementation=sys.implementation.name,
                machine=platform.machine(), libc=list(platform.libc_ver()),
                hashes={p.relative_to(io.REPO).as_posix(): io._hash(p) for p in sorted(paths)})


def freeze():
    require(not RESULTS.exists() and io._git('rev-parse', 'HEAD') == BASE, 'wrong preparation parent')
    io._write(FREEZE, manifest())


@contextmanager
def stage(name):
    index = STAGES.index(name)
    require(not io._git('status', '--porcelain', '--untracked-files=all'), 'dirty study checkout')
    chain = io._git('rev-list', '--reverse', '--first-parent', BASE + '..HEAD').splitlines()
    require(len(chain) == index + 1 and io._git('rev-parse', chain[0] + '^') == BASE,
            'unexpected study publication sequence')
    remote = subprocess.check_output(['git', 'ls-remote', '--exit-code', ORIGIN, BRANCH],
                                     timeout=45, text=True).split()
    require(remote == [chain[-1], BRANCH], 'stage requires the published commit')
    require(io._read(FREEZE) == manifest(), 'input/runtime differs from freeze')
    require(not io._git('diff', '--name-only', '--diff-filter=DMRT', BASE, chain[0]),
            'source publication changed an inherited file')
    for i, commit in enumerate(chain[1:]):
        prev = RESULTS / STAGES[i]
        prefix = prev.relative_to(io.REPO).as_posix() + '/'
        paths = io._git('diff', '--name-only', chain[i], commit).splitlines()
        require(paths and all(p.startswith(prefix) for p in paths), 'stage changed prior evidence or source')
        record = io._read(prev / 'receipt.json')
        require(record['status'] == 'complete' and record['outputs'] == _outputs(prev)
                and io._read(prev / 'attempt.json')['input'] == chain[i], 'unsealed predecessor')
    out = RESULTS / name
    out.mkdir(parents=True, exist_ok=False)
    io._write(out / 'attempt.json', dict(input=chain[-1], stage=name))
    wall, cpu = time.monotonic(), time.process_time()
    try:
        yield out
        receipt = dict(status='complete', outputs=_outputs(out))
    except BaseException as exc:
        receipt = dict(status='failed', error=repr(exc))
        raise
    finally:
        receipt.update(cpu_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-wall,
                       peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        io._write(out / 'receipt.json', receipt)
