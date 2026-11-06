"""Read-only intervention specified in G3_TRAIN_COORDINATE_INTERVENTION.md."""
import json
import platform

import torch

from . import continuation_run as io
from .effect_role_lexical import encoder, inherited_ids
from .effect_role_model import forecasts, pack
from .effect_role_run import world_for
from .joint_objective import DTYPE, fingerprint, require


def read_locked(path, digest):
    require(io._hash(path) == digest, f'input hash differs: {path.name}')
    return io._read(path)


def predict(net, world, groups):
    endpoints, actions, targets = [], [], []
    for group in groups:
        for (raw, action), event in zip(forecasts('grounded', net, world, group),
                                        group['events'], strict=True):
            endpoints.append(raw)
            actions.append(action)
            targets.append(event['target'])
    raw, action = torch.cat(endpoints), torch.cat(actions)
    nll = -raw.gather(1, torch.cat(targets)[:, None]).flatten()
    require(nll.shape == (16,) and bool(nll.isfinite().all()), 'invalid TRAIN endpoint scores')
    # Four supplied actions are ordered (family 0 role 0/1, family 1 role 0/1).
    mass = action.exp().reshape(16, 2, 2)
    marginals = torch.stack((mass[:, 1, :].sum(-1), mass[:, :, 1].sum(-1)), dim=1)
    return raw, action, nll, marginals


@torch.no_grad()
def compare(seed, freeze, training, teach, registry):
    fitted = io.ROOT / 'data/effect-role-fit-v3'
    key = f'grounded/{seed}'
    report, checkpoint = training['reports'][key], training['checkpoints'][key]
    saved = read_locked(fitted / f'grounded-{seed}.json', checkpoint['sha256'])
    state = {k: torch.tensor(v, dtype=DTYPE) for k, v in saved['state'].items()}
    parent = {k.removeprefix('parent.'): v for k, v in state.items() if k.startswith('parent.')}
    net = encoder(seed, parent, registry, inherited_ids(registry)).eval()
    net.load_state_dict(state, strict=True)
    original = net.new_coordinates.detach().clone()
    net_hash = fingerprint(net.state_dict())
    require(net_hash == saved['state_sha256'] == report['final_sha256'], 'grounded weights differ')
    require(list(net.new_ids) == report['new_ids'], 'lexical identity binding differs')
    world = world_for(freeze, 'nand', seed)
    world_hash = fingerprint(world.state_dict())
    require(world_hash == report['world_sha256'], 'native world differs')
    groups = pack(teach, world, registry)
    intact = predict(net, world, groups)
    mean = intact[2].mean().item()
    archived = report['final_objective']['teach']
    require(abs(mean - archived) <= 1e-10, 'intact endpoint NLL differs from archived TRAIN fit')
    result = {'archived_nll': archived, 'intact_nll': mean}
    for column, name in enumerate(('zero_effect', 'zero_role')):
        net.new_coordinates.copy_(original)
        net.new_coordinates[:, column].zero_()
        _, _, losses, marginals = predict(net, world, groups)
        delta = losses - intact[2]
        movement = (marginals - intact[3]).abs().amax(0)
        residual = (marginals[:, column] - .5).abs().max().item()
        require(residual <= 1e-12 and movement[1 - column] <= 1e-12, 'action marginal invariant failed')
        result[name] = {
            'mean_nll': losses.mean().item(), 'mean_delta_nll': delta.mean().item(),
            'higher': int((delta > 1e-12).sum()), 'equal': int((delta.abs() <= 1e-12).sum()),
            'lower': int((delta < -1e-12).sum()), 'ablated_marginal_max_change': movement[column].item(),
            'other_marginal_max_change': movement[1 - column].item(), 'max_residual_from_half': residual,
        }
    net.new_coordinates.copy_(original)
    restored = predict(net, world, groups)
    require(all(torch.equal(a, b) for a, b in zip(intact, restored, strict=True)) and
            fingerprint(net.state_dict()) == net_hash and fingerprint(world.state_dict()) == world_hash,
            'restored predictions or weights differ')
    result['restored_nll'] = restored[2].mean().item()
    return result


def run():
    torch.set_num_threads(1)
    data = io.ROOT / 'data/effect-role-v3'
    training = read_locked(io.ROOT / 'data/effect-role-fit-v3/training.json',
                           '766a8315d66e4a0bfca0079183d3966fbc7a0b4ed65c98177650d245a10671ed')
    freeze = read_locked(data / 'freeze.json', training['freeze_sha256'])
    def observed(name):
        return read_locked(data / name, freeze['artifacts'][name]['sha256'])
    teach, registry = observed('teach-inputs.json.xz'), observed('lexical-registry.json')
    require(len(teach['episodes']) == 16, 'incomplete teaching bank')
    return {'protocol_commit': 'c2fddad', 'teaching_rows': 16, 'torch': torch.__version__,
            'python': platform.python_version(), 'scope': 'G3 v3 observed TRAIN endpoints',
            'seeds': {s: compare(s, freeze, training, teach, registry) for s in (7, 11, 23, 37, 53)}}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, allow_nan=False))
