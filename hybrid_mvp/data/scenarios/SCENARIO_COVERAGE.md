# Scenario Coverage Matrix

**File:** `data/scenarios/use_cases.jsonl`
**Total cases:** 210 unique reviewed scenarios
**Review status:** all `reviewed`

## Design principle

Each case specifies **semantic assertions** rather than exact prose. The
`surface_examples` field provides illustrative surface forms, but the
assertions are the semantic contract. This keeps the scenario source
language-agnostic and leakage-controlled.

## Competency categories

| Category | Count | Description |
|---|---|---|
| `designation_definition` | 14 | Designation and definition: surface-to-identity mapping and concept definition queries |
| `reordered_constructions` | 12 | Same semantic content with reordered surface word order |
| `polysemy` | 10 | One surface producing multiple semantic targets or affordance profiles |
| `modality` | 10 | Modal scope (possible, necessary, conditional) over events and capabilities |
| `negation_scope` | 12 | Negation and polarity scope over states, events, relations, and capabilities |
| `recursive_family_proof` | 10 | Multi-hop rule inference and recursive family relationship proofs |
| `participant_reference` | 10 | Participant and entity reference resolution (you, I, alice, bob) |
| `reported_speech` | 10 | Reported speech with speaker, event, and embedded content |
| `temporal_state` | 10 | State assertions over entities and dimensions (online, off, married) |
| `reviewed_sensor_operation_evidence` | 10 | Reviewed sensor and operation adapter evidence |
| `transition_simulation` | 10 | State transition simulation via the effect gateway |
| `learning_security` | 12 | Learning distinctions: lookup, teaching claim, learning directive, learning event claim, reviewed acquisition, security |
| `capability_policy_adapter_effect` | 12 | Capability, policy, adapter, and effect authorization |
| `contradiction` | 8 | Contradictory state and relation assertions |
| `gap_kinds` | 18 | One scenario per gap kind (all 18 canonical gap kinds) |
| `multilingual_aliases` | 12 | Multilingual alias learning (es, fr, eo, hi, it, de, ja, pt, custom) |
| `adversarial_programs` | 10 | Adversarial program attacks (unknown operators, role injection, depth exceed, etc.) |
| `restart` | 10 | Session/world/episode/effect/full restart with revision preservation |
| `realization_equivalence` | 10 | Realization equivalence across surface variations |

## Gap kind coverage

All 18 canonical gap kinds are represented with at least one scenario:

| Gap kind | Scenario count |
|---|---|
| `evidence` | 1 |
| `designation` | 1 |
| `reference` | 1 |
| `authority` | 1 |
| `proposal` | 1 |
| `verification` | 1 |
| `inference` | 1 |
| `state` | 1 |
| `transition` | 1 |
| `learning` | 1 |
| `resource` | 1 |
| `permission` | 1 |
| `adapter` | 1 |
| `operation` | 1 |
| `storage` | 1 |
| `realization` | 1 |
| `performance` | 1 |
| `implementation` | 1 |

## Scenario record format

Each scenario is a JSON object on one line of the JSONL file:

```json
{
  "scenario_ref": "scenario:designation_definition-0001",
  "review_status": "reviewed",
  "competency_category": "designation_definition",
  "semantic_assertions": [
    {"kind": "designates", "surface": "hello", "target": "event:greeting"}
  ],
  "surface_examples": ["hello", "hi", "hey"],
  "expected_gap_kind": null,
  "metadata": {}
}
```

- `scenario_ref`: unique ref starting with `scenario:`.
- `review_status`: always `"reviewed"` for the source matrix.
- `competency_category`: one of the 19 categories above.
- `semantic_assertions`: list of structured assertion dicts. Each has a `kind`
  key and category-specific fields.
- `surface_examples`: illustrative surface form strings (not the semantic
  contract).
- `expected_gap_kind`: the expected `GapKind` value, or `null` if the scenario
  is expected to resolve.
- `metadata`: optional metadata (language, polarity, etc.).

## Training source typing

Episodes built from these scenarios carry typed training source provenance:

- `reviewed_scenario`: the primary source kind for all 210 cases.
- `authority_derived`: episodes derived directly from authority data.
- `human_paraphrase`: untrusted human language; requires a reviewed semantic
  target and independent re-verification.
- `teacher_paraphrase`: untrusted teacher language; requires a reviewed
  semantic target and independent re-verification.
- `verified_correction`: a verified correction; requires independent
  re-verification.

Human/teacher language is untrusted evidence: it may become an episode only
when paired with an already reviewed semantic target and independently
re-verified. It never creates an atom, rule, frame, policy, or transition.
