"""Post-score diagnostics using only the published v8 raw and scored JSON."""
from collections import Counter
from hashlib import sha1
import json
from math import log
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).with_name('results') / 'independent-v8'
RAW_MANIFEST = 'bfd85e4467e45b5179cfe7d5143bcd8074370137'
SCORED_MANIFEST = 'beaaea37f5bba334766cc5db77403f6004b710ce'


def read_blob(path, expected):
    data = path.read_bytes()
    if sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != expected:
        raise ValueError(f'published blob mismatch: {path}')
    return json.loads(data)


def confidence_band(p):
    return -1 if p <= .05 else 1 if p >= .95 else 0


def audit(root=ROOT):
    raw = read_blob(root / 'raw/manifest.json', RAW_MANIFEST)
    scored = read_blob(root / 'scored/manifest.json', SCORED_MANIFEST)
    decision = read_blob(root / 'scored/decision.json', scored['decision_blob_sha'])
    if raw['files'].keys() != scored['files'].keys():
        raise ValueError('raw and scored condition keys differ')
    pre = []
    ids = set()
    protected = {scope: Counter() for scope in ('root', 'sentinel')}
    strata = {}
    cost = Counter()
    view_brier = Counter()
    matched_goals = 0
    wrong_receipt = wrong_source = 0
    for key, entry in raw['files'].items():
        rows = read_blob(root / 'raw' / f'{key}.json', entry['raw_blob_sha'])['rows']
        report = read_blob(root / 'scored' / f'{key}.json', scored['files'][key]['blob_sha'])
        for left, right in zip(rows[::2], rows[1::2], strict=True):
            for field in ('pre_record_hash', 'pre_post_meaning_p', 'trust_pre_p', 'source_ids'):
                if left[field] != right[field]:
                    raise ValueError(f'{key}: unmatched twin {field}')
            for row in (left, right):
                if row['id'] in ids:
                    raise ValueError('duplicate world')
                ids.add(row['id'])
                # Frozen generator emits qor, nav at each of the first three
                # timestamps. Joint forecasts emit nav, qor at those times.
                for t in range(3):
                    source_qor, source_nav = row['source_ids'][2*t:2*t+2]
                    wrong_receipt += 2
                    wrong_source += 2 * (source_qor != source_nav)
            pre.append(left['pre_post_meaning_p'])
            matched_goals += all(left[f] == right[f] for f in ('goals', 'fee'))
            for index, scope in ((3, 'root'), (4, 'sentinel')):
                a, b = left['beliefs'][index], right['beliefs'][index]
                for arm, name in ((0, 'joint'), (2, 'neutral')):
                    protected[scope][name + '_changed'] += abs(a[arm] - b[arm]) > 1e-12
                    protected[scope][name + '_changed_band'] += confidence_band(a[arm]) != confidence_band(b[arm])
        for stratum, arms in report['source_epoch_subgroups'].items():
            group = strata.setdefault(stratum, Counter())
            group['worlds'] += arms['joint']['n']
            group['net_delta'] += arms['joint']['net_sum'] - arms['neutral']['net_sum']
            for arm in ('joint', 'neutral'):
                group[arm + '_first_brier_sum'] += arms[arm]['mid_local_brier_sum']
        for arm in ('joint', 'neutral'):
            z = report['arms'][arm]
            cost[arm + '_fees'] += z['question_cost_sum']
            cost[arm + '_net'] += z['utility_sum']
        for view, arms in report['views'].items():
            view_brier[view] += arms['joint']['brier_sum'] - arms['neutral']['brier_sum']
    if len(ids) != decision['worlds'] or len(pre) != decision['matched_twin_pairs']:
        raise ValueError('incomplete sealed bank')
    net_delta = cost['joint_net'] - cost['neutral_net']
    fees_delta = cost['joint_fees'] - cost['neutral_fees']
    if abs(sum(z['net_delta'] for z in strata.values()) - net_delta) > 1e-8:
        raise ValueError('strata do not account for utility loss')
    return {
        'frozen_decision': decision['decision'],
        'worlds': len(ids), 'twin_pairs': len(pre),
        'prefix': {
            # Each indistinguishable prefix has one positive and one negative target.
            'brier': mean((p*p + (1-p)**2) / 2 for p in pre),
            'nll': mean(-(log(p) + log(1-p)) / 2 for p in pre),
            'min_p': min(pre), 'max_p': max(pre),
            'pairs_outside_20_80': sum(p < .2 or p > .8 for p in pre),
        },
        'joint_payoff_alignment': {'swapped_receipts': wrong_receipt, 'wrong_sensors': wrong_source},
        'protected_twin_views': protected, 'pairs_matching_goals_and_fee': matched_goals,
        'joint_minus_neutral': {
            'net': net_delta, 'fees_paid': fees_delta, 'gross': net_delta + fees_delta,
            'mean_brier_change_by_view': {k: v / len(ids) for k, v in view_brier.items()},
        },
        'epoch_strata': {
            k: {'worlds': v['worlds'], 'net_delta': v['net_delta'],
                **{arm + '_first_brier': v[arm + '_first_brier_sum'] / v['worlds']
                   for arm in ('joint', 'neutral')}}
            for k, v in strata.items()
        },
    }


if __name__ == '__main__':
    print(json.dumps(audit(), sort_keys=True, indent=2))
