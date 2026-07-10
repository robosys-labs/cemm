# CEMM Core Loop: Causal Recursive Spine

This note maps the runtime loop after the 3.2 operational spine changes. It is
intended to make component load and recursion points explicit, especially for
clarification and meaning research.

> **Alignment note:** This diagram reflects the v3.2 runtime order. The canonical
> step numbering in `semantic_kernel_runtime.run_turn()` differs slightly (steps
> are grouped into 0-9 phases) but the causal order is identical.

## ASCII Map

```text
USER SIGNAL
    |
    v
+---------------------------+
| 1. Normalization/Language |
| - token forms             |
| - language adapter rules  |
| - known/unknown surfaces  |
+---------------------------+
    |
    v
+---------------------------+
| 2. Meaning Perceptor      |
| - meaning groups          |
| - intents/actions/states  |
| - cue metadata from data  |
| - unknown lexeme records  |
+---------------------------+
    |
    v
+---------------------------+
| 3. UOL Graph Builder      |
| - atoms and edges         |
| - candidate sets          |
| - concept resolutions     |
| - port bindings           |
| - patch candidates        |
| - state-delta candidates  |
+---------------------------+
    |
    v
+---------------------------+
| 4. Semantic Program       |
| - group instructions      |
| - entry ranking           |
| - discourse hierarchy     |
+---------------------------+
    |
    v
+----------------------------------+
| 5. Operational Meaning Compiler  |
| - frame type                     |
| - target scope                   |
| - decode quality from graph      |
| - query/write/reaction policy    |
| - NO language-local cue tables   |
+----------------------------------+
    |
    v
+----------------------------------+
| 5a. State Transmutation Compiler |
| - state occupancy from graph     |
| - state delta from action ops    |
| - scope/provenance/persistence   |
| - ephemeral/session/durable      |
+----------------------------------+
    |
    v
+----------------------------------+
| 5b. Causal/Effect Router         |
| - feedback → style delta         |
| - write → effect only if writable|
| - fresh query → retrieval effect |
| - safety → refusal/risk effect   |
+----------------------------------+
    |
    +------------------------------+
    |                              |
    v                              v
+------------------------+   +---------------------------+
| 6a. Clarification Gate |   | 6b. Normal Meaning Route  |
| - missing action/object|   | - profile assertion       |
| - unresolved operator  |   | - self/world/profile query|
| - low decode coverage  |   | - teaching/world fact     |
+------------------------+   +---------------------------+
    |                          |
    v                          v
+---------------------------+  +------------------------------+
| 7a. Ask Clarification     |  | 7b. Obligation Contract      |
| - no durable retrieval    |  | - QueryContract             |
| - no memory write         |  | - WriteContract             |
| - ask for missing meaning |  | - Reaction/Safety contracts |
+---------------------------+  +------------------------------+
    |                          |
    |                          v
    |                     +---------------------------+
    |                     | 8. Query / Write Execute  |
    |                     | - strict durable filters  |
    |                     | - no broad fallback       |
    |                     | - validated patch commit  |
    |                     +---------------------------+
    |                          |
    +------------+-------------+
                 |
                 v
        +---------------------+
        | 9. Response/NLG     |
        | - primitive goals   |
        | - response moves    |
        | - language renderer |
        | - no routing logic  |
        +---------------------+
                 |
                 v
             AI OUTPUT
```

## Recursive Meaning Research Path

```text
Low-decode turn
    |
    v
clarification_request frame
    |
    v
ask_clarification obligation
    |
    v
assistant asks for missing meaning
    |
    v
user teaches: <surface> means <operational meaning>
    |
    v
normal loop compiles teaching frame
    |
    v
validated write / lexeme or concept learning path
    |
    v
future turns re-enter at normalization/perception with stronger bindings
```

The recursion is not a recursive function call inside the compiler. It is a
turn-level causal loop: uncertainty becomes a clarification obligation; the
next user turn supplies evidence; learning updates the model; future perception
has better grounding.

## Component Responsibilities

```text
Component                     Load it should carry
----------------------------  ---------------------------------------------
Language adapter/normalizer   Surface/token normalization per language.
Meaning perceptor             Language-specific cue use, unknown lexeme emit.
UOL graph builder             Preserve evidence as atoms, edges, candidates.
Semantic program compiler     Rank grouped instructions, not route responses.
Operational meaning compiler  Route only from semantic structure and coverage.
State transmutation compiler  Extract state occupancy/delta from graph and action ops; scope as ephemeral/session/durable.
Causal/effect router          Convert transmutations and affordances into operational effects (style, write, query, safety).
Contract builders             Convert selected frame + effects to query/write/reaction/safety contracts.
Query executor                Retrieve only within contract constraints.
Patch extractor/validator     Commit only authorized writable meanings.
Response/NLG                  Render selected move; no semantic rerouting.
```

## Architectural Constraints

```text
1. Operational compiler must not own language-local word tables.
2. Clarification is an operational frame, not a social fallback.
3. Low decode quality blocks query/write contracts unless a complete relation
   shape or resolvable query target is present.
4. Unknown functional/discourse surfaces should recurse through clarification
   and teaching, then become learned bindings.
5. NLG may name the unknown token, but it must not decide what the token means.
```

## Current Known Debt

Several older compiler heuristics still inspect English-looking surfaces for
profile, self, and world query patterns. They predate this correction. The new
decode gate should not add more of that load; the long-term migration is to
move these recognizers into perception/language adapters and pass only semantic
cue metadata into operational compilation.

### Phase 0 Extraction Debt

10 of 14 subcomponents remain embedded in `MeaningPerceptor`. The extracted ones
are `predicate_phrase_extractor.py`, `implicit_predicate_detector.py`,
`anaphora_resolver.py`, and `entity_salience_tracker.py`. The remaining 10
(`predicate_argument_aligner`, `interpretation_path`, `alternative_graph_branch`,
`branching_graph_builder`, `discourse_relation_resolver`, `group_predicate_index`,
`candidate_set_resolver`, `interpretation_path_selector`, `planner_branch_adapter`,
`deictic_resolver`) still need extraction.

### Clarification Gate Not Explicitly Wired

The clarification gate (step 6a/7a) is logically present in
`OperationalMeaningCompiler` which produces `clarification_request` frame types,
but the runtime does not have an explicit fork that skips contract building for
low-decode turns. This is a future hardening item.

## References

- `newarch/3.2-improvement-plan.md` — full implementation record and remaining gaps
- `cemm/kernel/semantic_kernel_runtime.py` — canonical `run_turn()` implementation
- `cemm/kernel/operational_meaning_compiler.py`
- `cemm/kernel/state_transmutation_compiler.py`
- `cemm/kernel/operational_causal_router.py`
