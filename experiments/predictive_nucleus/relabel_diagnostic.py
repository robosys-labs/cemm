"""Post-hoc ID-renaming diagnostic on the opened public fixture, never G1.

Each bijection is applied to the same action and sensor records, including
feedback. It tests sensitivity of a forecast distribution to arbitrary ID
assignment, not the cause of any model gap or performance on a new world.
"""
from hashlib import sha256
from itertools import permutations, product
import json
import platform
import resource
from time import perf_counter, process_time
from math import fsum
from pathlib import Path
from zipfile import ZipFile

from .causal_replay import DevelopmentHistory, PublicReplay
from .development_run import (MODEL_NAMES, _Flat, _LocalMemory, _NoChange, _Structured,
                              _fingerprint, _json, _training_history, read_protocol, score_forecast)
from .schedule_fixture import make_evaluator_episode as training_episode
from .sensor_controls import EventMemory
from .shared_training_smoke import collect_shared_development, tensorize
from .two_pair_fixture import make_evaluator_episode, sensor_view

ARCHIVE = Path(__file__).with_name('results') / 'public-composition-v2-1f6f5bb.zip'
ARCHIVE_SHA256 = 'c0dc4f5e696d71b237242df67e7ecc8b8e941094e29afd0febfb47efce38b08f'
TV_TOLERANCE = 1e-12


def rename_history(history, mapping):
    """Apply a bijection to every ID, preserving order, values and time."""
    ids = tuple(sorted(name for name, _ in history._observations[0]))
    if set(mapping) != set(ids) or set(mapping.values()) != set(ids) or len(mapping) != len(ids):
        raise ValueError('mapping must bijectively permute anchor IDs')
    observations = tuple(tuple((mapping[name], bit) for name, bit in observation)
                         for observation in history._observations)
    actions = tuple((kind, tuple(mapping[name] for name in participants), value)
                    for kind, participants, value in history._action_records)
    return DevelopmentHistory(observations, actions)


def to_original(distribution, original_ids, mapping):
    """Map a distribution indexed by sorted renamed IDs back to original IDs."""
    if distribution is None:
        return None
    renamed_ids = tuple(sorted(mapping.values()))
    if set(original_ids) != set(mapping) or len(original_ids) != len(mapping):
        raise ValueError('invalid original identity order')
    indices = tuple(renamed_ids.index(mapping[name]) for name in original_ids)
    return {tuple(world[i] for i in indices): probability for world, probability in distribution.items()}


def compare_forecasts(original, renamed, original_ids, mapping, truth):
    """Compare joint distributions and separately track sorted-ID MAP ties."""
    status0, reason0, dist0 = original
    status1, reason1, dist1 = renamed
    scored0 = score_forecast(status0, reason0, dist0, truth)
    # Validate renamed distribution in its own ID order before mapping it back.
    renamed_truth = tuple(dict(zip(original_ids, truth))[name]
                          for name in sorted(original_ids, key=lambda name: mapping[name]))
    scored1 = score_forecast(status1, reason1, dist1, renamed_truth)
    mapped = to_original(dist1, original_ids, mapping)
    worlds = tuple(product((0, 1), repeat=len(original_ids)))
    if status0 != status1 or status0 == 'ABSTAIN':
        return {'status_original': status0, 'status_renamed': status1,
                'reason_original': reason0, 'reason_renamed': reason1, 'tv': None,
                'map_changed': None, 'correct_original': scored0['map_correct'],
                'correct_renamed': scored1['map_correct'], 'original_world_probabilities': scored0['world_probabilities'],
                'renamed_world_probabilities_mapped_back': (None if mapped is None else
                    [{'world': list(w), 'probability': float(mapped.get(w, 0))} for w in worlds])}

    tv = 0.5 * fsum(abs(float(dist0.get(w, 0)) - float(mapped.get(w, 0))) for w in worlds)
    renamed_map = to_original({tuple(scored1['map_world']): 1.0}, original_ids, mapping)
    map_world = next(iter(renamed_map))
    maximum0 = max(dist0.values())
    maximum1 = max(dist1.values())
    return {'status_original': status0, 'status_renamed': status1, 'tv': tv,
            'over_tolerance': tv > TV_TOLERANCE,
            'map_changed': tuple(scored0['map_world']) != map_world,
            'original_map_tied': sum(p == maximum0 for p in dist0.values()) > 1,
            'renamed_map_tied': sum(p == maximum1 for p in dist1.values()) > 1,
            'correct_original': scored0['map_correct'], 'correct_renamed': scored1['map_correct'],
            'original_world_probabilities': scored0['world_probabilities'],
            'renamed_world_probabilities_mapped_back': [{'world': list(w), 'probability': float(mapped.get(w, 0))}
                                                       for w in worlds]}


def _replay(history, kernel, flat, memory):
    agents = (_Structured(kernel), _Flat(flat), _NoChange(), _LocalMemory(memory))
    PublicReplay.from_development_history(history).run(agents[0], agents[1])
    PublicReplay.from_development_history(history).run(agents[2], agents[3])
    if any(agent.history != agents[0].history or agent.ids != agents[0].ids for agent in agents[1:]):
        raise RuntimeError('different delivered histories or identity orders')
    return agents


def _evaluate_case(episode, archived_case, kernel, flat, memory):
    """Finish every replay before consulting any evaluator truth for a case."""
    history = DevelopmentHistory.from_sensor_view(sensor_view(episode))
    original_ids = tuple(sorted(name for name, _ in history._observations[0]))
    identity_agents = _replay(history, kernel, flat, memory)
    variants = []
    for perm in permutations(original_ids):
        mapping = dict(zip(original_ids, perm))
        renamed = rename_history(history, mapping)
        if rename_history(renamed, {v: k for k, v in mapping.items()}) != history:
            raise RuntimeError('history renaming failed to round trip')
        variants.append((mapping, _replay(renamed, kernel, flat, memory)))
    # No oracle access until identity and all six counterfactual replays end.
    truths = []
    for step in range(5):
        gold = episode.gold_after(step)
        truths.append(tuple(gold[name] for name in original_ids))
    history_match = int([json.loads(row) for row in identity_agents[0].history] == archived_case['public_history'])
    identity_matches = 0
    for step, truth in enumerate(truths):
        for name, agent in zip(MODEL_NAMES, identity_agents):
            score = score_forecast(*agent.forecasts[step], truth)
            archived_score = dict(archived_case['steps'][step]['models'][name])
            archived_score.pop('feedback_diagnostic', None)
            identity_matches += int(score == archived_score and list(truth) == archived_case['steps'][step]['truth'])
    rows = []
    for mapping, agents in variants:
        for step, truth in enumerate(truths):
            rows.append({'step': step, 'mapping': mapping,
                         'models': {name: compare_forecasts(first.forecasts[step], second.forecasts[step],
                                                            original_ids, mapping, truth)
                                    for name, first, second in zip(MODEL_NAMES, identity_agents, agents)}})
    return rows, identity_matches, history_match


def _archive():
    raw = ARCHIVE.read_bytes()
    if sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('public artifact hash mismatch')
    with ZipFile(ARCHIVE) as archive:
        if archive.namelist() != ['public-composition-diagnostic.json']:
            raise ValueError('unexpected archive contents')
        return json.loads(archive.read(archive.namelist()[0]))


def run():
    """Refit frozen protocol and compare all six relabelings; no new challenge."""
    start_wall, start_cpu = perf_counter(), process_time()
    protocol, archive = read_protocol(), _archive()
    import torch
    from .flat_reference import FlatWorldGRU, fit_flat
    from .latent_model import fit_kernel
    if (torch.version.cuda is not None or torch.version.hip is not None or
            (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()) or
            (hasattr(torch, 'xpu') and torch.xpu.is_available())):
        raise RuntimeError('requires CPU-only PyTorch')
    previous_threads = torch.get_num_threads()
    try:
        with torch.random.fork_rng(devices=[]):
            torch.set_num_threads(1)
            views = [_training_history(training_episode(case, block=block))
                     for block in (0, 1) for case in range(32)]
            records = [collect_shared_development(view) for view in views]
            batch, samples = tensorize(records)
            inputs = {'flat': _fingerprint({'flat_features': batch[0], 'flat_targets': batch[1], 'flat_valid': batch[2]}),
                      'structured': _fingerprint({'structured_contact': samples.contact, 'structured_episode': samples.episode_id,
                                                  'structured_set': samples.intervention})}
            memory = EventMemory.fit(views)
            table_hash = sha256(_json(memory.rows).encode()).hexdigest()
            output = []
            for seed, archived_seed in zip(protocol['model_seeds'], archive['results'], strict=True):
                if archived_seed['model_seed'] != seed:
                    raise RuntimeError('archive seed inventory drift')
                torch.manual_seed(seed)
                FlatWorldGRU()  # Match initial construction in frozen runner.
                fit_wall, fit_cpu = perf_counter(), process_time()
                structured, sinfo = fit_kernel(samples, seed, steps=protocol['model_updates'])
                flat, finfo = fit_flat(batch, seed, max_steps=protocol['model_updates'],
                                       fixed_steps=protocol['model_updates'], wall_budget_seconds=3600.0)
                if sinfo['gradient_steps'] != 200 or finfo['gradient_steps'] != 200:
                    raise RuntimeError('fitting schedule drift')
                fit_cost = {'wall_seconds': perf_counter() - fit_wall, 'cpu_seconds': process_time() - fit_cpu}
                fingerprints = {'structured': _fingerprint(structured.state_dict()), 'flat': _fingerprint(flat.state_dict())}
                weight_match = all(fingerprints[name] == archived_seed[name + '_weights_sha256']
                                   for name in ('structured', 'flat'))
                kernel = structured.freeze()
                rows, identity_matches, history_matches = [], 0, 0
                replay_wall, replay_cpu = perf_counter(), process_time()
                for case in range(64):
                    episode = make_evaluator_episode(case, block=0)
                    archived_case = archived_seed['cases'][case]
                    if archived_case['case'] != case:
                        raise RuntimeError('archive case inventory drift')
                    case_rows, case_matches, case_history_match = _evaluate_case(episode, archived_case, kernel, flat, memory)
                    identity_matches += case_matches
                    history_matches += case_history_match
                    rows.extend({'case': case, **row} for row in case_rows)
                replay_cost = {'wall_seconds': perf_counter() - replay_wall, 'cpu_seconds': process_time() - replay_cpu}
                output.append({'seed': seed, 'fingerprints': fingerprints, 'weight_fingerprints_match': weight_match,
                               'combined_fit_cost': fit_cost, 'replay_and_scoring_cost': replay_cost,
                               'identity_score_matches': identity_matches, 'identity_score_total': 64 * 5 * 4,
                               'identity_history_matches': history_matches, 'identity_history_total': 64,
                               'rows': rows})
            all_match = (inputs == archive['training_input_sha256'] and table_hash == archive['event_memory_table_sha256'] and
                         all(item['weight_fingerprints_match'] and item['identity_score_matches'] == item['identity_score_total']
                             and item['identity_history_matches'] == item['identity_history_total'] for item in output))
            try:
                cpu_model = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                                  if line.lower().startswith('model name')), platform.processor() or 'unknown')
            except OSError:
                cpu_model = platform.processor() or 'unknown'
            hardware = {'python': platform.python_version(), 'torch': torch.__version__, 'cpu': cpu_model,
                        'threads': torch.get_num_threads(),
                        'torch_config_sha256': sha256(torch.__config__.show().encode()).hexdigest(),
                        'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
                        'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
            return {'status': 'POST_HOC_OPEN_PUBLIC_FIXTURE_NOT_G1', 'reproduces_archived_predictions_and_weights': all_match,
                    'hardware': hardware, 'wall_seconds': perf_counter() - start_wall, 'cpu_seconds': process_time() - start_cpu,
                    'training_input_fingerprints': inputs, 'training_inputs_match': inputs == archive['training_input_sha256'],
                    'event_memory_fingerprint': table_hash, 'event_memory_match': table_hash == archive['event_memory_table_sha256'],
                    'tv_tolerance': TV_TOLERANCE, 'seeds': output,
                    'limitations': ['Repeated counterfactual views of 64 opened cases, not independent worlds.',
                                    'Combined sensitivity to input/output slots; does not attribute the model performance gap.',
                                    'Lexicographic MAP tie-breaking can change under renaming even at zero TV.',
                                    'This refit is not the archived model unless all recorded fingerprints and identity forecasts match.']}
    finally:
        torch.set_num_threads(previous_threads)


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True, allow_nan=False))
