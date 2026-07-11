with open('cemm/kernel/meaning_graph_builder.py') as f:
    c = f.read()

# Rename methods
c = c.replace(
    'def _extract_emotional_evaluation_patches(self, graph: UOLGraph) -> None:',
    'def _extract_emotional_evaluation_observations(self, graph: UOLGraph) -> None:'
)
c = c.replace(
    'def _extract_state_delta_patches(self, graph: UOLGraph) -> None:',
    'def _extract_state_delta_observations(self, graph: UOLGraph) -> None:'
)
c = c.replace(
    'def _extract_remember_relation_patches(self, graph: UOLGraph) -> None:',
    'def _extract_remember_relation_observations(self, graph: UOLGraph) -> None:'
)

# Update internal calls
c = c.replace(
    'self._extract_remember_relation_patches(graph)\n        self._extract_emotional_evaluation_patches(graph)\n        self._extract_state_delta_patches(graph)',
    'self._extract_remember_relation_observations(graph)\n        self._extract_emotional_evaluation_observations(graph)\n        self._extract_state_delta_observations(graph)'
)

assert 'def _extract_emotional_evaluation_observations' in c
assert 'def _extract_state_delta_observations' in c
assert 'def _extract_remember_relation_observations' in c

# Update docstrings
c = c.replace(
    'Extract upsert_state patch candidates from schema-driven state delta atoms.',
    'Extract state delta structural observations from schema-driven state delta atoms.'
)
c = c.replace(
    'State atoms created by _compile_state_deltas have source=\'schema_state_delta\'.\n        For each, we produce an upsert_state patch operation targeting the entity\n        that holds the state, with the dimension and direction from the schema.',
    'State atoms created by _compile_state_deltas have source=\'schema_state_delta\'.\n        For each, we produce a structural observation for downstream patch compilation.'
)
c = c.replace(
    "Extract relation patches from 'remember' command groups.",
    "Extract relation observations from 'remember' command groups."
)
c = c.replace(
    "Detects patterns like 'remember I like coffee' and creates\n        upsert_relation_candidate patches for the embedded relation.",
    "Detects patterns like 'remember I like coffee' and creates\n        structural observations for the embedded relation."
)

with open('cemm/kernel/meaning_graph_builder.py', 'w') as f:
    f.write(c)
print('Step 3: method renames and docstrings OK')
