"""Bounded numerical-runtime receipt; no model execution or unrestricted env dump."""
import os
from pathlib import Path
import platform
import sys

from . import acceptance_contract as c


ENVIRONMENT = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
               'PYTHONHASHSEED', 'MKL_CBWR', 'MKL_DEBUG_CPU_TYPE',
               'ONEDNN_MAX_CPU_ISA', 'DNNL_MAX_CPU_ISA', 'ATEN_CPU_CAPABILITY')


def runtime(config):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    basic = {'python': platform.python_version(), 'torch': str(torch.__version__),
        'numpy': np.__version__, 'threads': torch.get_num_threads(), 'dtype': 'float64',
        'deterministic_algorithms': torch.are_deterministic_algorithms_enabled()}
    c.require(basic == config['execution']['runtime'], 'frozen numerical runtime differs')
    cpu = {}
    path = Path('/proc/cpuinfo')
    if path.is_file():
        for line in path.read_text().split('\n\n', 1)[0].splitlines():
            key, _, value = line.partition(':')
            if key.strip() in ('vendor_id', 'cpu family', 'model', 'model name', 'stepping', 'flags'):
                cpu[key.strip()] = value.strip()
    return {**basic, 'python_implementation': platform.python_implementation(),
        'python_build': list(platform.python_build()), 'python_compiler': platform.python_compiler(),
        'system': platform.system(), 'kernel': platform.release(), 'machine': platform.machine(),
        'libc': list(platform.libc_ver()), 'cpu': cpu,
        'cpu_capability': torch.backends.cpu.get_cpu_capability(),
        'interop_threads': torch.get_num_interop_threads(),
        'torch_build': torch.__config__.show(), 'torch_parallel': torch.__config__.parallel_info(),
        'float_info': {'mant_dig': sys.float_info.mant_dig, 'rounds': sys.float_info.rounds},
        'environment': {key: os.environ.get(key) for key in ENVIRONMENT}}


def verify_runtime(config, frozen):
    actual = runtime(config)
    c.require(actual == frozen, 'frozen numerical execution identity differs')
    return actual
