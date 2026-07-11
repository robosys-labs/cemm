import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cemm.tests.harness import SeededSystem
system = SeededSystem()
result = system.run('I love music')
cycle = result.get('cycle')
percept = getattr(cycle, 'percept', None)
if percept:
    print(f'actions: {len(percept.actions)}')
    for a in percept.actions:
        family = getattr(a, 'operator_family', 'N/A')
        print(f'  action: key={a.action_key} surface={a.surface} family={family}')
    print(f'groups: {len(percept.meaning_groups)}')
    for g in percept.meaning_groups:
        print(f'  group: id={g.id} func={g.function} surface={g.surface!r}')
        if hasattr(g, 'members'):
            print(f'    members: {g.members}')
    print(f'predicates: {len(percept.predicates)}')
    for p in percept.predicates[:5]:
        print(f'  predicate: key={p.predicate_key} surface={p.surface}')
else:
    print('no percept')
