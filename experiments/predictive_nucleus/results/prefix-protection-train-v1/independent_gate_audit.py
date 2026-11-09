"""Independent scalar arithmetic for the seven registered native TRAIN checks."""
import argparse
from hashlib import sha256
import json
import lzma
import math
from pathlib import Path


def read(path):
    data = path.read_bytes()
    return json.loads(lzma.decompress(data) if path.suffix == '.xz' else data)


def audit(selected, baseline, candidate, output):
    source = read(selected)
    rows = source['rows']
    identities = [row['id'] for row in rows]
    assert len(identities) == len(set(identities)) == 2048
    results = {}
    for seed in (7, 11, 23, 37, 53):
        records = [read(path / f'raw-native-{seed}.json.xz') for path in (baseline, candidate)]
        assert all(record['ids'] == identities for record in records)
        for law in ('nand', 'nor'):
            indices = [i for i, row in enumerate(rows) if row['law'] == law]
            values = []
            for record in records:
                metrics = {}
                for stage in ('teaching', 'claim', 'first', 'second'):
                    for field in ('target', 'protected'):
                        forecasts = record['predictions'][stage][field]
                        correct, briers = 0, []
                        for i in indices:
                            p, y = forecasts[i], rows[i]['answers'][field + '_y']
                            assert len(p) == 8 and all(math.isfinite(v) and v >= 0 for v in p)
                            assert abs(math.fsum(p) - 1) <= 1e-10
                            correct += max(range(8), key=p.__getitem__) == y
                            briers.append(math.fsum((v - (j == y)) ** 2 for j, v in enumerate(p)))
                        metrics[stage + '/' + field] = (correct, math.fsum(briers) / len(indices))
                values.append(metrics)
            old, new = values
            checks = [new['second/target'][0] >= old['second/target'][0],
                      new['second/target'][1] <= old['second/target'][1] + 1e-12,
                      new['second/protected'][0] >= old['second/protected'][0],
                      new['second/protected'][1] < old['second/protected'][1] - 1e-4,
                      math.fsum(new[s + '/protected'][1] for s in ('claim', 'first', 'second')) / 3
                      < math.fsum(old[s + '/protected'][1] for s in ('claim', 'first', 'second')) / 3 - 1e-4,
                      new['teaching/protected'][0] >= old['teaching/protected'][0],
                      new['teaching/protected'][1] <= old['teaching/protected'][1] + 1e-12]
            results[f'{seed}/{law}'] = {'count': len(indices), 'baseline': old, 'candidate': new, 'checks': checks}
    passed = sum(sum(cell['checks']) for cell in results.values())
    result = {'scope': 'Scalar saved-TRAIN-array arithmetic; no learner or primary scorer imported.',
              'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
              'input_sha256': sha256(selected.read_bytes()).hexdigest(), 'cells': results,
              'passed_checks': passed, 'total_checks': 70,
              'decision': 'KEEP_PREFIX_OBJECTIVE_FOR_FRESH_STUDY' if passed == 70 else 'REVISE_PREFIX_OBJECTIVE'}
    with output.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    return {'passed_checks': passed, 'decision': result['decision']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'baseline', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.input, args.baseline, args.candidate, args.output)))
