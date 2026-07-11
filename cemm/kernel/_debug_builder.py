import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Monkey-patch before import
import cemm.kernel.meaning_graph_builder as mgb
orig = mgb.MeaningGraphBuilder._add_emotional_evaluations
def debug_add(self, graph, packet):
    actions = (packet.actions or []) + (getattr(packet, 'candidate_actions', None) or [])
    print(f'_add_emotional_evaluations called: {len(actions)} actions')
    for a in actions:
        ak = a.action_key or ''
        schema = self._schema_kernel.action_operators.get(ak)
        print(f'  action: key={ak!r} surface={a.surface!r} group_id={a.group_id!r}')
        if schema:
            print(f'  schema found: family={schema.operator_family!r}')
        else:
            print(f'  schema NOT found for key {ak!r}')
    result = orig(self, graph, packet)
    evaluates = [e for e in graph.edges if e.edge_type == 'evaluates']
    print(f'  after: {len(evaluates)} evaluates edges')
    return result
mgb.MeaningGraphBuilder._add_emotional_evaluations = debug_add

from cemm.tests.harness import SeededSystem
system = SeededSystem()
result = system.run('I love music')
cycle = result.get('cycle')
graph = cycle.uol_graph if cycle else None
if graph:
    ev = [e for e in graph.edges if e.edge_type == 'evaluates']
    print(f'Final evaluates edges: {len(ev)}')
