# CEMM v3.4 — Remaining Legacy Runtime Inventory

**Audited commit:** `d45a0f6e2989ef11122de9fef66786c40c7ef2a5`

The following inventory distinguishes:

- **boundary adapter candidate** — temporarily usable only at an external boundary;
- **must migrate** — contains useful behavior but must be re-expressed under v3.4 authority;
- **must retire** — competing authority or obsolete control flow;
- **historical reference only** — move under `legacy/v3_3/` or archive.

---

# 1. Active legacy orchestrators

| Component | Current role | Disposition |
|---|---|---|
| `kernel/pipeline.py` | active app entry, old stores/lattices, old result model | replace with app assembly + `CognitiveKernel` |
| `kernel/semantic_kernel_runtime.py` | hybrid orchestrator containing all old/new paths | decompose and retire |
| `kernel/semantic_cpu.py` | old perception/graph/plan/patch CPU | retire after native vertical slice |
| `types/runtime_cycle.py` | old mutable result plus trace fields | replace with immutable `CognitiveCycle` |

---

# 2. Legacy perception and composition

| Component | Current use | Disposition |
|---|---|---|
| `meaning_perceptor.py` | authoritative input interpretation | retire |
| `meaning_graph_builder.py` | authoritative UOL graph | retire/migrate valid graph construction concepts |
| `construction_matcher.py` | phrase/construction scoring | demote to language candidate generator or retire |
| `language_adapter.py` | old language analysis | replace with native language pack adapter |
| `text_normalizer.py` | pre-v3.4 normalization | boundary-only until native stream |
| `predicate_phrase_extractor.py` | legacy predicate detection | migrate into construction evidence |
| `relation_extractor.py` | identity/possessive patterns | replace with compositional constructions |
| `intent_parser.py` / `conversation_act_classifier.py` | old act authority | retire |
| `pragmatic_interpreter.py` | affect/update heuristics | migrate as pragmatic evidence only |
| `entity_fact_extractor.py` | direct fact extraction | retire/migrate into proposition candidates |
| `implicit_predicate_detector.py` | old implicit frame creation | replace with schema-based hypotheses |
| `frame_binder.py` / `port_resolver.py` / `role_ref_resolver.py` | hard-coded roles/ports | replace with schema-generic grounding |

`PerceptToSurfaceEvidence` is itself transitional. Move it to `legacy/v3_3/adapter.py`; it must not remain the canonical surface authority.

---

# 3. Legacy grounding and interpretation

| Component | Current use | Disposition |
|---|---|---|
| old `entity_grounding_resolver.py` | parallel/shadow grounding | retire |
| old `interpretation_lattice.py` | active branch source for old operation path | retire |
| old `interpretation_resolver.py` | selects branches for old operation path | retire |
| `predicate_activation_resolver.py` | gates old operational frames | retire |
| `branch_arbitrator.py` | old branch authority | retire |
| `semantic_gap_detector` under old learning package | active learning gap path | retire after v3.4 gap flow works |
| `lexeme_candidate_index.py` | old candidate memory | migrate or retire into schema lexical index |

---

# 4. Legacy operational/control spine

These modules collectively remain the operative semantic/control CPU:

```text
semantic_attention_controller.py
semantic_program_compiler.py
operational_meaning_compiler.py
operational_contract_compiler.py
obligation_contract_builder.py
obligation_graph_builder.py
query_contract_builder.py
write_contract_builder.py
reaction_contract_builder.py
situation_frame_builder.py
state_occupancy_compiler.py
state_delta_compiler.py
state_transmutation_compiler.py
transmutation_authorizer.py
operational_causal_router.py
safety_frame_detector.py
turn_execution_planner.py
contract_executor.py
```

Disposition:

- migrate useful safety/permission/state semantics into v3.4 schemas/planner/authorizer;
- do not wrap these modules and continue treating their outputs as authoritative;
- retire the instruction/obligation/frame label pipeline after equivalent semantic vertical slices pass.

---

# 5. Legacy query and memory authorities

| Component | Current role | Disposition |
|---|---|---|
| `relation_frame_compiler.py` | builds query/write relation frames | replace with canonical predications/query patterns |
| `relation_algebra.py` | old relation lookup/inference | migrate required algebra into schema/epistemic query behavior |
| `semantic_query_engine.py` | actual answer retrieval | retire after v3.4 retriever works |
| `memory/predicate_schema_store.py` | second schema authority | migrate records into `SemanticSchemaStore`, retire |
| `memory/durable_semantic_store.py` | actual fact/relation persistence | wrap behind v3.4 persistence interface, then migrate |
| `learning/patch_validator.py` | old write validator | replace by CommitCoordinator validators |
| `learning/patch_committer.py` | actual writer | retire |
| old graph patch extractor | actual mutation extraction | replace with operation outcome → exact mutation proposals |
| concept/construction lattices | old semantic consolidation | migrate only if represented as indexes over canonical records |

---

# 6. Legacy learning

```text
LearningEpisodeManager
LearningQuestionPlanner
LearningAnswerAssimilator
TeachingFrameManager
TeachingInterpreter
PredicateSchemaInductor
PromotionGate
SessionLearningOverlay remnants, if any
```

Current behavior is still used for multi-turn teaching and clarification.

Disposition:

- preserve current user-visible learning regression scenarios as tests;
- migrate to persisted v3.4 `LearningTransaction`;
- retire old episodes/teaching frames once staged child → replay → provisional/active commit works.

---

# 7. Legacy response/discourse

| Component | Current role | Disposition |
|---|---|---|
| `response/response_formation_engine.py` | actual content and wording | content authority must be removed; may temporarily render a message plan |
| `response/types.py` / `ResponseSituation` / `ObligationFrame` | old response input | retire |
| `output_state_updater.py` | parses output into old conversation state | replace with output event + common-ground commit |
| `error_attribution_engine.py` | old reaction/error update | migrate as evidence/appraisal, not semantic authority |
| old session conversation kernel | old discourse/self state | replace with canonical discourse/common-ground/self records |

---

# 8. Potentially retainable adapters

Some old functionality may remain temporarily if made one-way and non-authoritative:

1. `ContextKernelBuilder`  
   Use only to translate old session context into v3.4 input records during migration.

2. `TextNormalizer`  
   Use only before the native reversible token stream is complete; never discard raw evidence.

3. `DurableSemanticStore`  
   Use behind a v3.4 persistence adapter, with all writes owned by `CommitCoordinator`.

4. `ResponseFormationEngine`  
   Use only as a renderer over `SemanticMessagePlan`; prohibit content selection and raw-input decisions.

5. selected safety rules  
   Convert into policy schemas/authorization checks rather than invoking the old operational compiler.

---

# 9. Retirement rule

A legacy module may be removed only after:

1. its user-visible regression cases exist as v3.4 tests;
2. its required semantic behavior has one v3.4 authority;
3. the new output is consumed by the next stage;
4. no old writer/query/response path remains;
5. the phase-12 guard passes without `xfail`;
6. production/session data has a migration path.

Deletion before these gates risks removing tests while leaving hidden behavior dependencies.
