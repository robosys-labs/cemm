"""Export frozen inference definitions and weights; never fit or score a model."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import shutil

SOURCE = Path(__file__).parent
BASE_COMMIT = '0d48f779215296120577b850d4c9ee329082e59f'
REPORT_SHA256 = '581172fcfd257127772ea9962544bae1071bc43ce683fca225128e9de5f5d078'
PINS = {
    'joint_objective.py': 'c00551ac3f0cff682b2dcd415929d8e8b7279f7fe92494fd07a2411a29ad1f4f',
    'empirical_joint.py': 'd93175b6c0b30a485e54f6417b98108a8e2cff06bc972f78e2c451490f4832dc',
    'masked_replay.py': 'fb79da609986721172b85737ef18150c465ea255b38ca176d945cc132dae69fa',
    'comparison_scoring.py': '95865f228ccb06345deda847570efa1aaea8e72828f64645d00d19a360b6a473',
    'informative_curriculum.py': '5fbb22e4a26e30d2bcbc609db976000ab0fc30ff96ee106a9caff7bafa13aada',
}
MODELS = ('kernel_supplied_persistence', 'kernel_learned_persistence', 'kernel_untied_roles',
          'kernel_memory_reset', 'flat', 'flat_supplied_persistence')
SEEDS = (7, 11, 23, 37, 53)
# Extract whole definitions verbatim, including original docstrings/comments.
# Only module-level imports/constants change to remove evaluator dependencies.
SELECTION = {
    'joint_objective.py': (
        'from collections import Counter\nfrom dataclasses import dataclass\n'
        'from hashlib import sha256\nfrom itertools import product\nimport json\nimport math\n'
        'import torch\nfrom torch import nn\nfrom torch.nn import functional as F\n'
        'WORLDS = tuple(product((0, 1), repeat=3))\nDTYPE = torch.float64\n',
        ('require', 'world_index', 'fingerprint', 'SensorBatch', '_mlp', 'persistence_support',
         'JointKernel', 'JointFlatGRU')),
    'empirical_joint.py': (
        'from collections import Counter, defaultdict\nfrom hashlib import sha256\n'
        'import json\nimport math\nimport torch\nfrom .joint_objective import WORLDS\n',
        ('queries', 'context', 'SensorMemory')),
    'comparison_scoring.py': ('import numpy as np\nimport torch\n', ('require', 'log_record', 'normalize')),
    'masked_replay.py': (
        'from itertools import product\nimport math\nimport numpy as np\nimport torch\n'
        'from . import comparison_scoring as scores\nWORLDS = tuple(product((0, 1), repeat=3))\n',
        ('NeuralPaths', 'EmpiricalPaths', 'LastObserved')),
    'informative_curriculum.py': ('', ('model_factories',)),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def selected_source(name):
    path = SOURCE / name
    require(digest(path) == PINS[name], f'frozen source changed: {name}')
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    nodes = {node.name: node for node in ast.parse(text).body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
    header, names = SELECTION[name]
    blocks = []
    for symbol in names:
        node = nodes[symbol]
        first = min([node.lineno] + [item.lineno for item in node.decorator_list])
        blocks.append(''.join(lines[first - 1:node.end_lineno]))
    return '# Verbatim frozen inference definitions; see manifest for origin.\n' + header + '\n\n' + '\n\n'.join(blocks)


def _json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def export(evidence, output):
    """New output only. Evidence is the already-completed PR52 result directory."""
    evidence, output = Path(evidence).resolve(), Path(output)
    raw = (evidence / 'report.json').read_bytes()
    require(sha256(raw).hexdigest() == REPORT_SHA256 and
            (evidence / 'COMPLETE').read_text().strip() == REPORT_SHA256, 'original completed report mismatch')
    report = json.loads(raw)
    fits = report['fits']
    require(json.loads((evidence / 'fits' / 'FIT_PHASE.json').read_text()) == fits, 'fit report mismatch')
    chosen = [row for row in fits['fits'] if row['task']['regime'] == 'fixed_exposure'
              and row['task']['condition'] == 'informative']
    expected = {(model, seed) for model in MODELS for seed in SEEDS}
    require(len(chosen) == 30 and {(r['task']['model'], r['task']['seed']) for r in chosen} == expected,
            'all thirty previously selected checkpoints are required')
    controls = [r for r in fits['controls'] if r['condition'] == 'informative']
    require(len(controls) == 3 and {r['mode'] for r in controls} == {'prefix', 'local', 'contact'},
            'all three empirical tables are required')
    sources = {name: selected_source(name) for name in SELECTION}
    require(not output.is_symlink() and not output.resolve().is_relative_to(SOURCE.parents[1]),
            'output must be outside source checkout')
    output.mkdir(exist_ok=False, parents=False)
    try:
        core = output / 'participant_core'
        core.mkdir()
        (core / '__init__.py').write_text('', encoding='utf-8')
        for name, content in sources.items():
            (core / name).write_text(content, encoding='utf-8')
        shutil.copyfile(SOURCE / 'external_participant.py', output / 'participant.py')
        (output / 'weights').mkdir()
        (output / 'tables').mkdir()
        manifest = {'format': 'cemm-external-participant-v1', 'origin_commit': BASE_COMMIT,
                    'original_report_sha256': REPORT_SHA256, 'source_pins': PINS,
                    'extracted_definitions': {n: list(v[1]) for n, v in SELECTION.items()},
                    'selection': 'All six informative/fixed-exposure arms, all five seeds from PR53; no new selection.',
                    'independent_evaluation': False, 'gate_g1': 'NOT_ADMITTED',
                    'limits': {'entities': 3, 'binary_state': True, 'paths': 64, 'steps': 128,
                               'full_anchor': True, 'noisy_visible_readings_supported': False},
                    'models': [], 'controls': [], 'files': {}}
        for row in sorted(chosen, key=lambda r: (r['task']['model'], r['task']['seed'])):
            task, meta = row['task'], row['final']
            require(type(task['ordinal']) is int and task['ordinal'] >= 0 and meta['file'] == 'final.pt',
                    'invalid frozen checkpoint location')
            src = evidence / 'fits' / f"fit-{task['ordinal']:03d}" / 'final.pt'
            require(digest(src) == meta['file_sha256'], 'checkpoint byte mismatch')
            name = f"weights/{task['model']}-{task['seed']}.pt"
            shutil.copyfile(src, output / name)
            manifest['models'].append({'model': task['model'], 'seed': task['seed'], 'file': name,
                                      'tensor_sha256': meta['tensor_sha256'], 'training': row['fit']})
        for row in sorted(controls, key=lambda r: r['mode']):
            require(Path(row['file']).name == row['file'], 'unsafe table filename')
            src = evidence / 'fits' / row['file']
            require(digest(src) == row['file_sha256'], 'control byte mismatch')
            name = f"tables/{row['mode']}.json"
            shutil.copyfile(src, output / name)
            manifest['controls'].append({'model': row['mode'], 'file': name, 'table_sha256': row['table_sha256']})
        for path in sorted(output.rglob('*')):
            if path.is_file():
                manifest['files'][path.relative_to(output).as_posix()] = digest(path)
        manifest['python_physical_lines'] = sum(len(p.read_text().splitlines()) for p in output.rglob('*.py'))
        _json(output / 'manifest.json', manifest)
        (output / 'manifest.sha256').write_text(digest(output / 'manifest.json') + '  manifest.json\n', encoding='ascii')
        return manifest
    except BaseException as error:
        (output / 'manifest.json').unlink(missing_ok=True)
        (output / 'manifest.sha256').unlink(missing_ok=True)
        _json(output / 'FAILED.json', {'status': 'INCOMPLETE_EXPORT', 'error': str(error)})
        raise


def verify_export(output):
    """Compare exported and original inference on a hand-written, unscored trace.

    Checks all thirty saved states and all five controls, not public fixtures.
    No fitting, simulator, evaluator truth, model selection or accuracy metric.
    """
    import importlib
    import importlib.util
    import sys
    import torch
    import numpy as np
    from . import external_participant as api, joint_objective as original
    from . import masked_replay as old_paths
    from .informative_curriculum import model_factories
    output = Path(output).resolve()
    manifest_hash = digest(output / 'manifest.json')
    manifest = api.verify_bundle(output, manifest_hash)
    for name in PINS:
        selected_source(name)  # verify reference bytes too
    alias = '_cemm_export_' + manifest_hash[:16]
    spec = importlib.util.spec_from_file_location(alias, output / 'participant_core' / '__init__.py',
                         submodule_search_locations=[str(output / 'participant_core')])
    require(alias not in sys.modules, 'verification namespace already loaded')
    sys.modules[alias] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sys.modules[alias])
    threads = torch.get_num_threads()
    checks = []
    try:
        torch.set_num_threads(1)
        with torch.random.fork_rng(devices=[]), torch.inference_mode():
            new_paths = importlib.import_module(alias + '.masked_replay')
            factories = model_factories()
            identities = [(r['model'], r['seed']) for r in manifest['models']]
            identities += [(name, None) for name in ('prefix', 'local', 'contact', 'first_contact', 'no_change')]
            for name, seed in identities:
                new, memory = api.restore(alias, manifest, output, name, seed)
                old = factories[name]() if new is not None else None
                if old is not None:
                    old.load_state_dict(new.state_dict(), strict=True)
                    old.eval()
                for masked in (False, True):
                    anchor = torch.tensor([[1., 1., 0.]], dtype=torch.float64)
                    def adapter(module, model):
                        return (module.NeuralPaths(model, anchor) if model is not None else
                                module.EmpiricalPaths(memory, anchor, first_contact=name == 'first_contact')
                                if memory is not None else module.LastObserved(anchor))
                    left, right = adapter(old_paths, old), adapter(new_paths, new)
                    actions = ((0, 0, 1, -1), (1, 2, -1, 1), (2, -1, -1, -1), (0, 2, 0, -1))
                    readings = ((1, 0, 0), (1, 0, 1), (1, 0, 1))
                    for step, action in enumerate(actions):
                        tensor = torch.tensor([action], dtype=torch.long)
                        a, ma = left.predict(tensor); b, mb = right.predict(tensor)
                        require(torch.equal(a, b) and np.array_equal(ma, mb), 'export forecast parity failure')
                        if step < len(readings):
                            x = torch.tensor([readings[step]], dtype=torch.float64)
                            mask = torch.ones(1, 3, dtype=torch.bool)
                            if masked:
                                mask[0, (0, 2, 1)[step]] = False
                                x[~mask] = -1
                            left.receive(x.clone(), mask.clone()); right.receive(x.clone(), mask.clone())
                    checks.append({'participant': name, 'seed': seed, 'masked': masked, 'identical_forecasts': 4})
        return {'status': 'EXPORTED_INFERENCE_PARITY_ONLY', 'manifest_sha256': manifest_hash,
                'source_commit': BASE_COMMIT, 'verified_neural_checkpoints': 30, 'verified_table_files': 3,
                'checks': checks, 'forecast_vectors_compared': sum(c['identical_forecasts'] for c in checks),
                'score_computed': False, 'independent_review': False, 'study_run': False,
                'python_physical_lines': manifest['python_physical_lines'],
                'environment': {'torch': str(torch.__version__), 'numpy': np.__version__}}
    finally:
        torch.set_num_threads(threads)
        for name in list(sys.modules):
            if name == alias or name.startswith(alias + '.'):
                del sys.modules[name]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    manifest = export(args.evidence, args.output)
    if args.verify:
        print(json.dumps(verify_export(args.output), indent=2, sort_keys=True, allow_nan=False))
    else:
        print(json.dumps({'manifest_sha256': digest(Path(args.output) / 'manifest.json'),
                      'models': len(manifest['models']), 'tables': len(manifest['controls']),
                      'python_physical_lines': manifest['python_physical_lines'], 'evaluated': False}))
