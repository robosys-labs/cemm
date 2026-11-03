"""Recompute G4 action values from observed prefixes and the two frozen G3 models."""
import math
import time
from itertools import islice

from . import communication_world as g3, continuation_run as io
from .acceptance_contract import digest, require
from .acceptance_scoring import _index
from .transfer_task import catalogue

PARITY_ATOL = 1e-10


def _prefix(record):
    # G3's batch schema requires a last reading. Only the question is visible at
    # prediction time. The final generator yield is consumed before receive().
    events = record['utterances']
    last = {'text': events[-1]['text'], 'reading': [0] * len(record['entities'])}
    return {**record, 'utterances': [*events[:-1], last]}


def _predict(visible, model, language, registry):
    import torch
    from .effect_role_model import forecasts, pack

    result = {}
    with torch.inference_mode():
        for group in pack(visible, model, registry):
            stream = forecasts('grounded', language, model, group)
            logp, _ = next(islice(stream, len(group['events']) - 1, None))
            for record, values in zip(group['records'], logp.tolist(), strict=True):
                result[record['id']] = values
    return result


def _models(freeze, training, registry, law, seed):
    import torch
    from .active_checkpoint import load_checkpoint
    from .effect_role_lexical import encoder, inherited_ids
    from .joint_objective import fingerprint

    native = freeze['world_checkpoints'][f'{law}/{seed}']
    item = training['checkpoints'][f'grounded/{seed}']
    saved = g3._bound(g3.FIT / item['file'], item['sha256'])
    weights = {name: torch.tensor(value, dtype=torch.float64) for name, value in saved['state'].items()}
    parent = {name.removeprefix('parent.'): value for name, value in weights.items() if name.startswith('parent.')}
    language = encoder(seed, parent, registry, inherited_ids(registry))
    language.load_state_dict(weights, strict=True)
    world = load_checkpoint(g3.NATIVE / native['file'], native['sha256'])['model']
    require(fingerprint(language.state_dict()) == saved['state_sha256'] and
            fingerprint(world.state_dict()) == native['state_sha256'], 'live G3 checkpoint differs')
    return (world.eval().requires_grad_(False), language.eval().requires_grad_(False),
            {'world_sha256': native['sha256'], 'language_sha256': item['sha256']})


def live_catalogue(law, split):
    """Return a standard parent catalogue with live values plus its parity receipt."""
    import torch

    started = time.perf_counter()
    torch.set_num_threads(1)
    bank = catalogue(law, split)
    reference = bank.pop('forecasts')
    freeze = g3._bound(g3.DATA / 'freeze.json', g3.FREEZE)
    training = g3._bound(g3.FIT / 'training.json', g3.TRAINING)
    def artifact(name):
        return g3._bound(g3.DATA / name, freeze['artifacts'][name]['sha256'])
    registry = artifact('lexical-registry.json')
    inputs = artifact(f'{law}-inputs.json.xz')
    needed = {k for sites in bank['sites'].values() for site in sites for row in site['episodes'] for k in row}
    records = {r['id']: r for r in inputs['episodes'] if r['id'] in needed}
    require(set(records) == needed and needed, 'live G3 input inventory differs')
    visible = {'version': inputs['version'], 'episodes': [_prefix(records[k]) for k in sorted(needed)]}

    goals = {}
    physical = 0
    for sites in bank['sites'].values():
        for site in sites:
            for bit, row in enumerate(site['episodes']):
                for action, key in enumerate(row):
                    record = records[key]
                    events = record['utterances']
                    before = events[-2]['reading'] if len(events) > 1 else record['context'][-1]['reading']
                    goal = g3._target(before, site['participants'], site['goal'])
                    require(record['entities'] == site['entities'] and
                            record['context'][0]['reading'][0] == bit and
                            events[-1]['text'] == site['texts'][action] and
                            int(events[-1]['reading'] == goal) == site['rewards'][bit][action],
                            'physical goal, witness or action differs')
                    goals[site['id'], key] = _index(goal)
                    physical += 1

    live, records_by_seed = {}, {}
    worst, changed, count = 0., 0, 0
    for seed in io.SEEDS:
        tick = time.perf_counter()
        world, language, record = _models(freeze, training, registry, law, seed)
        outputs = _predict(visible, world, language, registry)
        tables = {}
        for pair, sites in bank['sites'].items():
            tables[pair] = []
            for site, archived in zip(sites, reference[str(seed)][pair], strict=True):
                matrix = [[math.exp(outputs[key][goals[site['id'], key]]) for key in row]
                          for row in site['episodes']]
                for values, old in zip(matrix, archived, strict=True):
                    require(all(math.isfinite(v) and 0 <= v <= 1 for v in values), 'invalid live G3 value')
                    worst = max(worst, *(abs(x-y) for x, y in zip(values, old, strict=True)))
                    changed += (values[1] > values[0]) != (old[1] > old[0])
                    count += len(values)
                tables[pair].append(matrix)
        live[str(seed)] = tables
        records_by_seed[str(seed)] = {**record, 'wall_seconds': time.perf_counter()-tick}
    require(worst <= PARITY_ATOL and changed == 0, 'live and archived G3 probabilities or choices differ')
    bank['forecasts'] = live
    return bank, dict(law=law, split=split, torch=str(torch.__version__), torch_threads=torch.get_num_threads(),
        unique_episodes=len(needed), condition_goal_values=count, physical_payoffs=physical,
        max_abs_error=worst, argmax_mismatches=changed, records=records_by_seed,
        wall_seconds=time.perf_counter()-started, forecast_sha256=digest(live))
