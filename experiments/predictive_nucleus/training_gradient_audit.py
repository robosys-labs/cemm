"""Read-only training diagnostic, not a fit, held-out evaluation or admission.

Replay the unchanged observed-outcome loss. Immediate logit gradients are q-r,
where r is the posterior over the two *model* actions after observed feedback;
r is not a supplied semantic label. Full gradients include later feedback.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
import time

import torch

from . import continuation_run as io, bilingual_run as native, saturation_run as saved
from .bilingual_model import combine
from .domain_kernel import DomainKernel
from .joint_objective import fingerprint, require

BASE = '148a98f62665445e6bb0a39cbabe23689ec0614b'
DATA = io.ROOT / 'data/saturation-v1'
FITTED = io.ROOT / 'data/saturation-fit-v1'


def flat(values):
    return torch.cat([x.reshape(-1) for x in values])


def stats(value):
    value = value.detach().reshape(-1)
    require(len(value) > 0 and bool(torch.isfinite(value).all()), 'nonfinite diagnostic')
    return dict(zip(('min', 'median', 'max', 'mean'), map(float,
        (value.min(), value.median(), value.max(), value.mean()))))


def analyze(model, world, observed):
    """Analyze a private copy, preserving caller tensors, gradients, flags and RNG."""
    require(type(world) is DomainKernel and world.memory and
        all(not p.requires_grad for p in world.parameters()) and
        all(not m.training for m in world.modules()), 'frozen evaluation world required')
    before = fingerprint(world.state_dict())
    net = deepcopy(model).eval().requires_grad_(True)
    params = tuple(net.parameters())
    require(sum(p.numel() for p in params) == 89, 'expected 89-parameter factor encoder')
    groups, rows, cache = native.pack(observed, world), [], {}
    hooks = [net.order.register_forward_hook(lambda _, args, out: cache.update(
        content=args[0], binding=args[1], logits=out)),
        net.lexical[0].register_forward_hook(lambda _, args, out: cache.update(hidden_pre=out))]
    try:
        for group in groups:
            state = group['state']
            for t, event in enumerate(group['events']):
                order = net(event['features'])
                options = event['likelihood'] + state[:, None, :, None]
                raw, pending = combine(order, options)
                target = event['target']
                loss = -raw.gather(1, target[:, None]).squeeze(1)
                action_ll = options.gather(-1, target[:, None, None, None].expand(-1, 2, 2, 1)).squeeze(-1).logsumexp(-1)
                responsibility = (order + action_ll).softmax(-1)
                direct = (order.exp() - responsibility).detach()
                require(bool(torch.isfinite(loss).all()), 'nonfinite training likelihood')
                require(torch.allclose(loss, -(order + action_ll).logsumexp(-1), atol=1e-12, rtol=0.), 'mixture arithmetic differs')
                cells = []
                for record in group['records']:
                    tokens = record['utterances'][t]['text'].split()
                    index = next(i for i, w in enumerate(tokens) if w not in record['entities'])
                    cells.append((tokens[index], index))  # Observed strings/positions, not roles.
                rows.append({**cache, 'loss': loss, 'direct': direct, 'cells': cells,
                    'ids': [[r['id'], t] for r in group['records']],
                    'order': order, 'responsibility': responsibility.detach(),
                    'action_gap': (action_ll[:, 1] - action_ll[:, 0]).detach(),
                    'correct': raw.argmax(-1) == target})
                state = world.receive(pending, event['post'])
        require(bool(rows), 'empty training diagnostic')
        count = sum(len(r['loss']) for r in rows)
        objective = sum(r['loss'].sum() for r in rows) / count
        gradient = torch.autograd.grad(objective, params, create_graph=True, retain_graph=True)
        vector = flat(gradient)
        require(bool(torch.isfinite(vector).all()), 'nonfinite parameter gradient')
        logits = tuple(r['logits'] for r in rows)
        total_logits = torch.autograd.grad(objective * count, logits, retain_graph=True)
        direct_gradient = torch.autograd.grad(logits, params,
            grad_outputs=tuple(r['direct'] / count for r in rows), retain_graph=True)
        direct_vector = flat(direct_gradient)
        # Exact 89x89 Hessian at fixed weights. No finite-difference weight perturbation.
        hessian = torch.stack([flat(torch.autograd.grad(g, params, retain_graph=True)) for g in vector])
        asymmetry = float((hessian - hessian.T).abs().max())
        require(bool(torch.isfinite(hessian).all()) and asymmetry < 1e-8, 'invalid Hessian')
        eigenvalues = torch.linalg.eigvalsh((hessian + hessian.T) / 2)
        cells, cell_gradients = [], []
        for word, position in sorted({cell for r in rows for cell in r['cells']}):
            masks = [torch.tensor([c == (word, position) for c in r['cells']]) for r in rows]
            losses = torch.cat([r['loss'][m] for r, m in zip(rows, masks)])
            contribution = losses.sum() / count
            cg = flat(torch.autograd.grad(contribution, params, retain_graph=True)).detach()
            cell_gradients.append(cg)
            take = lambda key: torch.cat([r[key][m] for r, m in zip(rows, masks)])
            lg = torch.cat([g[m] for g, m in zip(total_logits, masks)])
            hidden = take('hidden_pre').tanh()
            cells.append({'word': word, 'lexical_position': position, 'events': len(losses),
                'mean_nll': float(losses.detach().mean()), 'max_nll': float(losses.detach().max()),
                'exact_errors': int((~take('correct')).sum()),
                'error_ids': [identity for r, m in zip(rows, masks) for identity, select, correct
                              in zip(r['ids'], m.tolist(), r['correct'].tolist()) if select and not correct],
                'p_order_1': stats(take('order')[:, 1].exp()),
                'posterior_order_1': stats(take('responsibility')[:, 1]),
                'observed_log_likelihood_ratio_1_over_0': stats(take('action_gap')),
                'content': stats(take('content')), 'binding': stats(take('binding')),
                'hidden_tanh_derivative': stats(1 - hidden.square()),
                'immediate_logit_gradient_l1': stats(take('direct').abs().sum(-1)),
                'full_logit_gradient_l1': stats(lg.abs().sum(-1)),
                'future_logit_gradient_l1': stats((lg - take('direct')).abs().sum(-1)),
                'weighted_parameter_gradient_norm': float(cg.norm())})
        summed = torch.stack(cell_gradients).sum(0)
        partition_error = float((summed - vector.detach()).abs().max())
        require(partition_error < 1e-10, 'cell gradient accounting differs')
        denominator = sum(float(g.norm()) for g in cell_gradients)
        named = list(net.named_parameters())
        report = {'observed_events': count, 'mean_nll': float(objective.detach()),
            'exact_errors': sum(c['exact_errors'] for c in cells), 'cells': cells,
            'parameter_gradient_norm': float(vector.detach().norm()),
            'immediate_parameter_gradient_norm': float(direct_vector.norm()),
            'future_parameter_gradient_norm': float((vector.detach() - direct_vector).norm()),
            'cell_gradient_cancellation_ratio': float(vector.detach().norm()) / denominator if denominator else None,
            'cell_gradient_sum_max_error': partition_error,
            'parameter_blocks': {name: {'gradient_norm': float(g.detach().norm()),
                'parameter_norm': float(p.detach().norm())} for (name, p), g in zip(named, gradient)},
            'hessian_eigenvalues': eigenvalues.detach().tolist(), 'hessian_max_asymmetry': asymmetry,
            'negative_eigenvalues_below_minus_1e_6': int((eigenvalues < -1e-6).sum()),
            'model_state_sha256': fingerprint(net.state_dict()), 'world_state_sha256': before}
        require(report['model_state_sha256'] == fingerprint(model.state_dict()), 'language weights changed')
        require(before == fingerprint(world.state_dict()), 'world weights changed')
        return report
    finally:
        for hook in hooks: hook.remove()


class TrainingReadBoundary:
    """Audit-hook allowlist for repository data reads; not an OS sandbox."""
    def __init__(self, allowed):
        self.allowed = {Path(p).resolve() for p in allowed}
        self.reads, self.active = set(), False

    def check(self, event, args):
        if not self.active or event != 'open' or not isinstance(args[0], (str, bytes)):
            return
        path = Path(args[0]).resolve()
        if not path.is_relative_to(io.ROOT): return
        mode, flags = args[1:3]
        require(not (flags & 3), 'repository writes prohibited during diagnostic')
        if path.suffix in ('.py', '.pyc'):
            return
        require(path in self.allowed, 'unapproved diagnostic data read: ' + str(path))
        self.reads.add(path)

    def __enter__(self):
        sys.addaudithook(self.check); self.active = True
        return self

    def __exit__(self, *_): self.active = False


def run(output):
    """Fixed all-seed audit, loading no oracle, challenge, retention or parser data."""
    require(not output.exists(), 'output already exists')
    allowed = [saved.PROTOCOL, io.ROOT / 'snapshots/saturation_protocol_v1.sha256',
        DATA / 'freeze.json', DATA / 'train-inputs.json.xz', FITTED / 'checkpoints.json.xz']
    # These are the five known NAND training-world files, not held NOR worlds.
    allowed += [native.old.FITTED / f'nand-{seed}.json' for seed in io.SEEDS]
    wall, cpu = time.perf_counter(), time.process_time()
    with TrainingReadBoundary(allowed) as boundary:
        config, freeze = saved.protocol(), io._read(DATA / 'freeze.json')
        require(config['model_seeds'] == list(io.SEEDS), 'all five prescribed seeds required')
        require(io._hash(DATA / 'train-inputs.json.xz') == freeze['artifacts']['train-inputs.json.xz']['sha256'], 'training bytes differ')
        # Hash sources without opening any named data/challenge artifact.
        for name, digest in freeze['sources'].items():
            if name.endswith('.py'): require(io._hash(io.ROOT / name) == digest, 'frozen source differs: ' + name)
        models = saved.load_models(FITTED, config, DATA)
        observed, checkpoints = io._read(DATA / 'train-inputs.json.xz'), io._read(FITTED / 'checkpoints.json.xz')
        results = {}
        for seed in io.SEEDS:
            world = native.world_for(freeze['checkpoints'], 'nand', seed)
            for arm in saved.ARMS:
                key = f'{arm}/{seed}'
                result = analyze(models[key], world, observed)
                expected = checkpoints['reports'][str(seed)]['reports'][arm]['final_observed_train_nll']
                require(abs(result['mean_nll'] - expected) < 1e-11, 'saved training loss differs')
                require(result['observed_events'] == config['train_forecasts'], 'training exposure differs')
                results[key] = result
                print(key, result['mean_nll'], result['parameter_gradient_norm'], flush=True)
        bindings = {str(p.relative_to(io.ROOT)): io._hash(p) for p in allowed}
    report = {'version': 'training-gradient-audit-v1', 'base_commit': BASE,
        'scope': 'TRAINING_ONLY_NO_UPDATES', 'scientific_admission': False, 'gate_g3': 'OPEN',
        'parameter_updates': 0, 'held_challenge_reads': 0, 'bindings': bindings,
        'read_files': sorted(str(p.relative_to(io.ROOT)) for p in boundary.reads),
        'results': results, 'cpu_seconds': time.process_time() - cpu,
        'wall_seconds': time.perf_counter() - wall}
    io._write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    run(args.output)


if __name__ == '__main__': main()
