import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cemm.kernel.semantic_schema_kernel import SemanticSchemaKernel, get_kernel
sk = get_kernel()
print(f'schema_kernel: {sk}')
if sk:
    print(f'action_operators type: {type(sk.action_operators)}')
    op = sk.action_operators.get("evaluate_positive")
    print(f'evaluate_positive: {op}')
    if op:
        print(f'  operator_family: {op.operator_family}')
    print(f'keys count: {len(sk.action_operators)}')
    print(f'some keys: {list(sk.action_operators.keys())[:10]}')
