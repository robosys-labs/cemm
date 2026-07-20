# CEMM v3.5 Phase 3–4 Remediation Review

**Baseline reviewed:** `fc16e719168b7a84ebb9de5b6a61da0f67e8cb26` (`main`) plus the user-described integration/test cleanup.  
**Authority:** root `AGENTS.md`, `ARCHITECTURE.md`, `CORE_LOOP.md`, `phased-fixes.md`, `ACCEPTANCE_CONTRACT.md`.

## Phase 3: productive composition substrate

This patch adds:

- durable `MorphologyAnalysisRuleRecord`;
- reversible productive input morphology for unseen surface forms, including inflection-class rules and exact-lexeme exceptions;
- durable `ConstructionProgramRecord`;
- bounded construction-program operations:
  - `INTRODUCE_VARIABLE`
  - `INSTANTIATE_SCHEMA`
  - `ACTIVATE_SCHEMA_CLASS_CANDIDATES`
  - `BIND_PORT_FROM_SLOT`
  - `BIND_PORT_FROM_SYMBOL`
  - `UNIFY`
  - `ADD_RESTRICTION`
  - `SET_PROJECTION`
  - `ADD_SCOPE`
  - `ADD_TIME_FEATURE`
  - `ADD_ASPECT_FEATURE`
  - `ADD_MODALITY`
  - `WRAP_DISCOURSE_ACT`
  - `PRESERVE_GAP`
- construction choices represented as N-best semantic plans rather than one `choice:active`;
- multi-port lexical operators no longer assume `len(local_ports) == 1`;
- process/activity represented through event/action schema + reviewed aspect/eventuality features rather than a new Python `PROCESS` ontology enum.

### Morphology precedence

Exact reviewed surface forms are authoritative before productive class analysis. Productive rules apply only when the observed surface is not already covered by an exact/normalized reviewed form for that language. This gives irregular/suppletive forms a deterministic override while regular rules remain reusable across arbitrarily many lexemes sharing an inflection class.

### Compatibility boundary

`ConstructionMatcher` no longer reads `metadata.interpretation_enabled`.

A bounded migration-only compatibility compiler remains for unmigrated signed boot records:

1. explicit `ConstructionProgramRecord` always wins;
2. legacy `interpretation_enabled=false` becomes an explicit compatibility DENY only when no typed program exists;
3. legacy fixed `output_schema_ref` constructions compile into the same generic plan algebra;
4. compatibility is trace-marked;
5. Phase 9 seed migration must remove this reader.

This preserves old boot replay without making legacy metadata a competing new authority.

## Phase 4: participant grounding and referent-driven closure

This patch adds:

- structural `ParticipantRole` values;
- `ParticipantFrame -> DiscourseAnchor` bridge;
- `REFERENTIAL contribution.role_ref -> required_discourse_roles` wiring;
- Stage-4 `SemanticClosureCandidate` generation from:
  - active property/relation/role/function applications;
  - state applicability;
  - affordances;
  - live capabilities;
  - entitlement value domains as latent applicability;
- Stage 4 emits closure candidates before Stage 5;
- Stage 5 construction schema-class activation can be bounded by exact closure pins;
- Stage-4 compatibility is moved from same-span lexical coupling to semantic-port/grounded-referent compatibility.

Missing projections remain uncertainty, not proof of incompatibility.

## Eventuality boundary

No `PROCESS` Python enum is added.

The phase establishes the representation needed to distinguish:

- state: `StateDimensionSchema` / assignments;
- process/activity: dynamic/durative aspect features over event/action schemas;
- event/transition: occurrence/boundary/result structure;
- action: event/effect structure with control/intentionality contracts.

Future learned aspect profiles remain data.

## Performance properties

- morphology rules are indexed by language in `LanguageRegistry`;
- class-wide productive morphology uses inverse lemma recovery followed by indexed `(pack, inflection-class, lemma)` lookup rather than scanning the vocabulary;
- construction programs are indexed by exact construction revision;
- semantic plan expansion is bounded (`maximum_plans`, default 64);
- Stage-4 closure candidates are exact schema pins, deduplicated before Stage 5;
- no global semantic regex scan is introduced;
- no full-sentence phrase routing is introduced.

## Release integration gate

The checked-in runtime-authority manifest reviewed at this baseline omitted Phase-1/2
record kinds already present in `RecordKind`. `RuntimeAuthorityGuard` requires exact
record-kind equality.

Phase 3 adds:

- `morphology_analysis_rule`
- `construction_program`

Therefore:

- do **not** hand-edit signed hashes;
- do **not** weaken the guard;
- regenerate boot/release artifacts using deterministic repository tooling;
- rerun cutover/release verifiers after regeneration.

## Required verification

```bash
git apply --check cemm-v350-phases-3-4.patch

pytest -q tests/v350/test_phase3_4_semantic_composition.py
pytest -q tests/v350/test_phase1_2_semantic_substrate.py
pytest -q tests/v350/test_phase7_language.py
pytest -q tests/v350/test_phase6_foundation.py
pytest -q tests/v350

python tools/verify_v350_language_grounding.py
# regenerate signed boot/manifest/report using canonical release tooling
# rerun Phase-20/cutover/release verifiers
```

## Not claimed complete in Phase 3–4

- full typed WH/query projection activation — Phase 5;
- universal Stage-10 binder across all semantic record families — Phase 5;
- runtime-observed self state/capability truth — Phase 6;
- generic response-policy migration — Phase 7;
- learning promotion/cutover — Phase 8;
- EN/FR/SW seed migration and removal of legacy compatibility — Phase 9.
