"""Read-only audit of the omitted-first-answer control; no CEMM imports."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
import lzma
from pathlib import Path

import numpy as np


def read(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data), sha256(data).hexdigest()


def main(args):
    oracle, oracle_hash = read(args.prepared / 'oracle.json.xz')
    score, score_hash = read(args.score)
    rows = oracle['rows']
    ids = np.array([row['id'] for row in rows])
    law = np.array([row['law'] for row in rows])
    cause = np.array([row['cause'] for row in rows])
    protected_y = np.array([row['protected_y'] for row in rows])
    target_y = np.array([row['target_y'] for row in rows])
    cells, raw_hashes, discrepancies = {}, {}, []
    totals = defaultdict(int)
    checks = 0
    for seed in (7, 11, 23, 37, 53):
        name = f'raw-{seed}-native.json.xz'
        raw, raw_hashes[name] = read(args.raw / name)
        assert raw['ids'] == ids.tolist()
        keep = np.asarray(raw['views']['retained']['protected']).argmax(1) == protected_y
        clear = np.asarray(raw['views']['cleared']['protected']).argmax(1) == protected_y
        target_keep = np.asarray(raw['views']['retained']['after_second']).argmax(1) == target_y
        target_clear = np.asarray(raw['views']['cleared']['after_second']).argmax(1) == target_y
        for current_law in ('nand', 'nor'):
            key = f'{current_law}/{seed}'
            selected = law == current_law
            regress = clear & ~keep & selected
            repair = keep & ~clear & selected
            pairs = score['cells'][key]['paired']['cleared']['protected']
            for label, mask in (('exact_regressions', regress), ('exact_repairs', repair)):
                checks += 1
                if ids[mask].tolist() != pairs[label]:
                    discrepancies.append(f'{key}/{label}')
            cell = {'cases': int(selected.sum()), 'protected_retained_correct': int((keep & selected).sum()),
                    'protected_cleared_correct': int((clear & selected).sum()),
                    'protected_regressions': int(regress.sum()), 'protected_repairs': int(repair.sum()),
                    'target_regressions': int((target_clear & ~target_keep & selected).sum()),
                    'target_repairs': int((target_keep & ~target_clear & selected).sum()),
                    'target_repairs_with_protected_regression': int((target_keep & ~target_clear & regress).sum()),
                    'protected_regressions_by_cause': {str(c): int((regress & (cause == c)).sum()) for c in sorted(set(cause))}}
            cells[key] = cell
            for label, count in cell.items():
                if isinstance(count, int):
                    totals[label] += count
    report = {'status': 'PASS' if not discrepancies else 'FAIL', 'checks': checks, 'discrepancies': discrepancies,
              'oracle_sha256': oracle_hash, 'score_sha256': score_hash, 'raw_sha256': raw_hashes,
              'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(), 'cells': cells, 'totals': dict(totals),
              'scope': 'Post hoc saved-record localization of first-answer interference; no model, fit, or changed gate.'}
    args.output.write_text(json.dumps(report, sort_keys=True, separators=(',', ':')) + '\n')
    print(json.dumps({'status': report['status'], 'checks': checks, 'totals': dict(totals)}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'raw', 'score', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    main(parser.parse_args())
