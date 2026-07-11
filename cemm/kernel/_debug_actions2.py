import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cemm.tests.harness import SeededSystem
system = SeededSystem()
sk = system.schema_kernel
print(f'schema_kernel: {sk}')
if sk:
    print(f'action_operators: {type(sk.action_operators)}')
    print(f'has evaluate_positive: {sk.action_operators.get("evaluate_positive")}')
    # try to list some keys
    keys = list(sk.action_operators.keys())[:10]
    print(f'some keys: {keys}')
