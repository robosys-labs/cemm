import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cemm.tests.harness import SeededSystem
system = SeededSystem()

# Hook into the runtime's run_turn
runtime = system.pipeline._runtime
orig_run = runtime.run_turn

def debug_run(signal, kernel, **kw):
    result = orig_run(signal, kernel, **kw)
    if result.uol_graph:
        pc = len(result.uol_graph.patch_candidates)
        obs = len(result.uol_graph.structural_observations)
        print(f'[after run_turn] pc={pc} obs={obs}')
    else:
        print(f'[after run_turn] no uol_graph')
    return result

runtime.run_turn = debug_run

result = system.run('remember I like coffee')
cycle = result.get('cycle')
graph = cycle.uol_graph
print(f'[final] pc={len(graph.patch_candidates)} obs={len(graph.structural_observations)}')
