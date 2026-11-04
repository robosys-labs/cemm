"""Read-only post-score attribution. TEST is already opened; never refit."""
from collections import defaultdict, Counter
from pathlib import Path
import json
from math import isclose
import unittest

from experiments.predictive_nucleus.goal_policy_v6 import (
    GOALS, after_answer, choose, public_task
)
from experiments.predictive_nucleus.independent_task_v6 import (
    SEEDS, LAWS, inventory, _uniform, SOURCE_ERROR
)
from experiments.predictive_nucleus.revision_study import select_triples
from experiments.predictive_nucleus.transfer_task import catalogue

ROOT = Path(__file__).resolve().parents[1] / 'results/independent-v6'
ARMS = ('temporal', 'scoped_rule')
GOAL_NAMES = ('direct', 'reverse', 'indifferent', 'low-margin')


def _bucket():
    return dict(n=0, net_delta=0., mid_brier=0., rule_mid_brier=0.,
                final_brier=0., rule_final_brier=0.,
                mid_wrong_confident=0, final_wrong_confident=0)


def _p(cell, arm):
    if arm == 'temporal':
        return cell[0]
    if arm == 'scoped_rule':
        return .5 if cell[2] is None else float(cell[2])
    raise ValueError('wrong arm')


def _actions(mid, final, goals, fee, truth):
    policy = choose(mid, goals[0], fee)
    if policy['ask']:
        a = after_answer(goals[0], truth)
        b = after_answer(goals[1], truth)
    else:
        a = policy['action']
        b = choose(final, goals[1], None)['action']
    return (a, b), policy['ask']


def _reward(actions, goals, truth, fee, asked):
    return (goals[0][truth][actions[0]] +
            goals[1][truth][actions[1]] -
            (fee if asked else 0.))


class OpenedTestFailureAttribution(unittest.TestCase):
    def test_frozen_raw_vs_saved_score_without_new_model(self):
        summary = Counter()
        subsets = defaultdict(_bucket)
        seeds = {}
        query_cases = []
        loss_cases = []
        observed_noise = {s: Counter() for s in ('A', 'B')}
        world_ids = set()

        for law in LAWS:
            bank = catalogue(law, 'challenge')
            triples = select_triples(bank, SEEDS[0])  # metadata only here
            self.assertEqual(len(triples), 6)
            for seed in SEEDS:
                key = f'{law}-{seed}'
                raw = json.loads((ROOT/'raw'/f'{key}.json').read_text())
                saved = json.loads((ROOT/'scored'/f'{key}.json').read_text())
                episodes = inventory(law, seed, 'challenge', bank)
                local = Counter()
                case_groups = defaultdict(_bucket)
                source_triples = select_triples(bank, seed)

                self.assertEqual(len(raw['rows']), len(episodes))
                self.assertEqual(len(episodes), 192)
                for i, (r, ep) in enumerate(zip(raw['rows'], episodes, strict=True)):
                    self.assertEqual(r['id'], ep.uid)
                    self.assertNotIn(ep.uid, world_ids)
                    world_ids.add(ep.uid)
                    g_mid, g_final, fee = public_task(ep.uid)
                    goals = (g_mid, g_final)
                    self.assertEqual(r['fee'], fee)
                    self.assertEqual(r['goals'], json.loads(json.dumps(goals)))

                    post_truth = ep.truth[3]
                    flip = ep.truth[2] != post_truth
                    source = r['source_ids'][12]
                    category = GOAL_NAMES[GOALS.index(g_mid)]
                    p_mid = {a: _p(r['beliefs'][0], a) for a in ARMS}
                    p_final = {a: _p(r['beliefs'][1], a) for a in ARMS}
                    decisions = {}
                    for arm in ARMS:
                        a, ask = _actions(p_mid[arm], p_final[arm],
                                          goals, fee, post_truth)
                        decisions[arm] = dict(ask=ask, actions=a,
                            net=_reward(a, goals, post_truth, fee, ask))
                    td = decisions['temporal']
                    rd = decisions['scoped_rule']
                    delta = td['net'] - rd['net']
                    local['utility_delta_sum'] += delta
                    local['temporal_net'] += td['net']
                    local['rule_net'] += rd['net']
                    local['queries_temporal'] += td['ask']
                    local['queries_rule'] += rd['ask']
                    kind = ('both' if td['ask'] and rd['ask'] else
                            'temporal_only' if td['ask'] else
                            'rule_only' if rd['ask'] else 'neither')
                    local[kind] += 1
                    summary[kind] += 1
                    summary['episodes'] += 1
                    summary['utility_delta_sum'] += delta
                    subgroup = f'{law}|flip={int(flip)}|epoch_source={source}'
                    strata = (subsets[subgroup], case_groups[subgroup])
                    for z in strata:
                        z['n'] += 1
                        z['net_delta'] += delta
                        z['mid_brier'] += (p_mid['temporal']-post_truth)**2
                        z['rule_mid_brier'] += (p_mid['scoped_rule']-post_truth)**2
                        z['final_brier'] += (p_final['temporal']-post_truth)**2
                        z['rule_final_brier'] += (p_final['scoped_rule']-post_truth)**2
                        z['mid_wrong_confident'] += (
                            (p_mid['temporal'] > .95 and post_truth == 0)
                            or (p_mid['temporal'] < .05 and post_truth == 1))
                        z['final_wrong_confident'] += (
                            (p_final['temporal'] > .95 and post_truth == 0)
                            or (p_final['temporal'] < .05 and post_truth == 1))

                    if kind == 'temporal_only':
                        no_question = (
                            choose(p_mid['temporal'], g_mid, None)['action'],
                            choose(p_final['temporal'], g_final, None)['action'])
                        gross = _reward(td['actions'], goals, post_truth, None, False) - (
                                _reward(no_question, goals, post_truth, None, False))
                        net = gross - fee
                        summary['extra_query_realized_gross_gain'] += gross
                        summary['extra_query_realized_net_gain'] += net
                        summary['extra_query_beneficial'] += net > 1e-12
                        summary['extra_query_adverse'] += net < -1e-12
                        summary['extra_query_neutral'] += abs(net) <= 1e-12
                        summary[f'extra_query_goal_{category}'] += 1
                        summary[f'extra_query_source_{source}'] += 1
                        summary[f'extra_query_flip_{int(flip)}'] += 1
                        query_cases.append(dict(key=key,id=ep.uid,flip=bool(flip),
                            epoch_source=source,goal=category,fee=fee,
                            temporal_mid_p=p_mid['temporal'],
                            rule_mid_p=p_mid['scoped_rule'],actual=post_truth,
                            realized_gross_gain=gross,realized_net_gain=net,
                            relative_net_delta=delta))
                    if delta < -1e-9:
                        loss_cases.append(dict(key=key,id=ep.uid,flip=bool(flip),
                            epoch_source=source,goal=category,fee=fee,
                            temporal_mid_p=p_mid['temporal'],
                            rule_mid_p=p_mid['scoped_rule'],
                            temporal_final_p=p_final['temporal'],
                            rule_final_p=p_final['scoped_rule'],
                            actual=post_truth,temporal_asks=td['ask'],
                            rule_asks=rd['ask'],delta=delta))

                    # Evaluate actual sensor errors *after* scoring only;
                    # independent of the learned source-agnostic filter.
                    k, j = divmod(i, 32)
                    sites = source_triples[k]
                    lineage = tuple(x[0]['lineage'] for x in sites)
                    random_key = ('challenge',law,seed,lineage,k,j)
                    for rec in ep.records:
                        if not rec.physical:
                            continue
                        source_id = rec.source.removeprefix('sensor-')
                        site = (sites[0] if rec.term=='nav' or rec.scope==ep.root
                                else sites[1] if rec.scope==ep.region else sites[2])
                        meaning = (ep.truth[4] if rec.term=='nav' else
                                   ep.truth[0] if rec.scope==ep.root else
                                   ep.truth[1] if rec.scope==ep.region else
                                   ep.truth[2] if rec.event_time < 9 else ep.truth[3])
                        action = int(_uniform((*random_key,'action',rec.term,rec.event_time)) < .5)
                        clean = site[0]['rewards'][action][meaning]
                        errors = observed_noise[source_id]
                        errors['observations'] += 1
                        errors['actual_inversions'] += rec.outcome != clean

                for arm in ARMS:
                    self.assertTrue(isclose(local[f'{arm}_net'] if f'{arm}_net' in local
                        else local['temporal_net' if arm=='temporal' else 'rule_net'],
                        saved['arms'][arm]['utility_sum'],rel_tol=0,abs_tol=1e-9))
                self.assertEqual(local['queries_temporal'], saved['arms']['temporal']['queries'])
                self.assertEqual(local['queries_rule'], saved['arms']['scoped_rule']['queries'])
                self.assertTrue(isclose(local['utility_delta_sum'],
                    saved['arms']['temporal']['utility_sum'] -
                    saved['arms']['scoped_rule']['utility_sum'],rel_tol=0,abs_tol=1e-9))
                seeds[key] = dict(local, subgroups={k:v for k,v in sorted(case_groups.items())})

        self.assertEqual(summary['episodes'], 1920)
        self.assertEqual(summary['both'], 73)
        self.assertEqual(summary['temporal_only'], 15)
        self.assertEqual(summary['rule_only'], 0)
        self.assertEqual(summary['neither'], 1832)
        self.assertEqual(len(world_ids),1920)
        self.assertEqual(sum(x['observations'] for x in observed_noise.values()),28800)
        self.assertEqual(len(query_cases),15)
        self.assertTrue(all(e['fee']==.05 for e in query_cases))
        payload=dict(version='g5-v6-posthoc-failure-attribution',
            stage='READ_ONLY_OPENED_TEST',
            original_v6_raw_commit='3f0d247d88c51132ff63e1fde34dfca1b45747ab',
            original_v6_score_commit='61e1a979b79e2174ea634b5849f2db89dbb4501f',
            note='No refit, no decision threshold change, no independent challenge claim',
            summary=dict(summary),by_condition=seeds,
            subgroups={k:v for k,v in sorted(subsets.items())},
            realized_sensor_errors={k:dict(v) for k,v in observed_noise.items()},
            additional_temporal_query_cases=query_cases,
            adverse_case_examples=sorted(loss_cases,key=lambda z:z['delta'])[:24],
            total_adverse_cases=len(loss_cases))
        print('G5_V6_POSTHOC_ATTRIBUTION '+
              json.dumps(payload,separators=(',',':'),sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
