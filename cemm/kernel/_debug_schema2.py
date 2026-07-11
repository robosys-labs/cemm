import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cemm.tests.harness import SeededSystem
system = SeededSystem()
# Run a turn to get the pipeline initialized
result = system.run('I love music')
cycle = result.get('cycle')
percept = getattr(cycle, 'percept', None)

# The perceptor is on the pipeline runtime's CPU
runtime = system.pipeline._runtime
cpu = runtime._cpu
perceptor = cpu.perceptor
builder = cpu.graph_builder

print(f'builder._schema_kernel: {builder._schema_kernel}')
if builder._schema_kernel:
    op = builder._schema_kernel.action_operators.get('evaluate_positive')
    print(f'  evaluate_positive from builder.schema_kernel: {op}')
    if op:
        print(f'  operator_family: {op.operator_family}')
else:
    print('  builder._schema_kernel is None')

# Check the action from the packet
if percept:
    for a in getattr(percept, 'candidate_actions', []):
        ak = a.action_key or ''
        print(f'action_key: {ak!r}')
        sk = builder._schema_kernel
        if sk:
            schema = sk.action_operators.get(ak)
            print(f'  lookup result: {schema}')
