import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cemm.tests.harness import SeededSystem
system = SeededSystem()
result = system.run('I love music')
cycle = result.get('cycle')
percept = getattr(cycle, 'percept', None)
if percept:
    print(f'hasattr candidate_actions: {hasattr(percept, "candidate_actions")}')
    print(f'candidate_actions type: {type(getattr(percept, "candidate_actions", None))}')
    print(f'candidate_actions value: {getattr(percept, "candidate_actions", "N/A")}')
    print(f'actions: {percept.actions}')
