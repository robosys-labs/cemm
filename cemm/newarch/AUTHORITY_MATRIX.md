# CEMM v3.4 — Final Sole-Authority Matrix

| Decision | Sole authority | Authoritative output | Must not decide it |
|---|---|---|---|
| surface analysis | language/modality adapter | reversible `SurfaceEvidence` | query/write/NLG code |
| semantic composition | `SemanticComposer` | competing predication/proposition candidates | conversation-act router, templates |
| referent/sense/role grounding | `GroundingResolver` | grounded candidates, open ports, candidate use profiles | graph builder hard-coded roles |
| schema identity/version resolution | `SemanticSchemaStore` / resolver | candidate exact schema revisions | lexicon overlay, action registry |
| structural grounding assessment | `SchemaGroundingValidator` invoked by store | derived `SchemaGroundingAssessment` | learning coordinator, NLG |
| competence execution | sandboxed `CompetenceHarness` | immutable case results with lineage | schema itself, renderer |
| schema lifecycle activation | `SemanticSchemaStore` | atomic active/provisional/rejected revision outcome | validator, learning coordinator |
| recursive-cluster classification | schema validator | cycle class and fixed-point/stratification result | generic graph SCC checker alone |
| interpretation selection | `InterpretationResolver` | selected/rejected branches | operational compiler, response planner |
| context isolation | `ContextResolver` | actual/reported/belief/etc. frames | memory writer |
| semantic retrieval | `SemanticRetriever` | evidence/revision-aware results | runtime-local helper |
| truth and context admissibility | `EpistemicEvaluator` | support/admissibility assessments | schema store, existence check, NLG |
| current schema use | `GroundingResolver` from immutable assessments | operation/context-specific `SchemaUseProfile` | language pack, static schema flag |
| derived-cognition retraction | truth maintenance using typed dependency index | stale/retracted dependent artifacts | individual caches independently |
| current capability | `CapabilityEvaluator` | live capability assessment | static schema slot, canned responder |
| gap creation | `GapDetector` | concrete blocked-competency gap | unknown-token logger |
| learning lifecycle | `LearningCoordinator` | child revision proposal and transaction state | session overlay |
| replay scheduling/idempotence | learning replay queue | deduplicated snapshot-pinned work | ad-hoc callbacks |
| active goals | `GoalArbiter` | active desired propositions | instruction-kind composer |
| plan selection | `Planner` | selected/rejected plans | response ranker |
| operation authorization | `OperationAuthorizer` | live authorization per operation instance | schema usability tier, score preference |
| execution | `OperationExecutor` | typed operation outcome | graph builder, NLG |
| outcome reconciliation | `OutcomeReconciler` | confirmed/predicted deltas and ledger | planner success flag |
| persistent mutation | `CommitCoordinator` | exact operation-level commit outcome | direct store calls |
| common ground | `CommonGroundManager` through output commit | actual participant commitments | intended response plan |
| response content | `ResponsePlanner` | evidence-bound semantic message plan | templates, renderer, raw input |
| surface realization | language renderer | channel payload | truth, capability, schema activation |
| cycle scheduling | `CognitiveKernel`/scheduler | next cycle/wake | hidden background mutation |

## Registration invariant

Exactly one implementation registers each authority key at startup. Duplicate authoritative registrations fail startup. Helpers may derive candidates or convert records, but may not commit a competing decision.
