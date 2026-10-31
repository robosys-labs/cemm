# Predictive World-Model Nucleus — research and implementation roadmap

**Tracking:** [Issue #22](https://github.com/robosys-labs/cemm/issues/22)  
**Status:** Proposed research protocol. **No phase has been admitted by this document.**  
**Date:** 2026-10-27  
**Implementation boundary:** independent experiment first; no root runtime or Hybrid cutover  
**Companion foundation:** [draft PR #21](https://github.com/robosys-labs/cemm/pull/21)

## Current development checkpoint — 2026-10-31

G1's verified development foundation is sufficient to proceed into **G2**. The
frozen mixed-composition challenge retained **KEEP_MIXED_COMPOSITION**; the
subsequent observed-history dependency test now has **KEEP_JOINT_CORRELATION**
at all five seeds. Both reused V2 weights with zero new training updates and
no inference/model change. The explicit equal-marginal/different-correlation
requirement is complete for this supplied binary law.
Formal G1 scientific admission remains open; the historical gate below is unchanged.
See [the G1/G2 review](../../experiments/predictive_nucleus/G1_G2_PROGRESS_REVIEW.md),
[joint-correlation result](../../experiments/predictive_nucleus/JOINT_CORRELATION_DECISION_V1.md)
and [PR #64](https://github.com/robosys-labs/cemm/pull/64). Do not reopen successful
alias fitting or interpret unknowable hidden outcomes as a new architectural defect.
The assumption review corrected the proposed ternary extension: atomic-event
arity does not imply a serial-composition limit. The subsequent
[NAND/NOR law-learning study](../../experiments/predictive_nucleus/MULTISOURCE_LAW_DECISION_V1.md)
now has **KEEP_MULTISOURCE_LAWS**: all 30,720 planned forecasts completed, with
11,520/11,520 identifiable and 7,680/7,680 primary matched forecasts correct and
320/320 common-history law contrast pairs passing. Ten paired fits completed
1,280 updates on the unchanged 562-parameter model; historical weights and
inference implementations remain unchanged. [PR #65](https://github.com/robosys-labs/cemm/pull/65)
retains the full results and local regressions.

The subsequent [hidden-cycle study](../../experiments/predictive_nucleus/HIDDEN_CYCLE_DECISION_V1.md)
now has **KEEP_HIDDEN_CYCLE**: all 15,360 planned forecasts completed;
10,240/10,240 identifiable complete worlds, 2,560/2,560 hidden final worlds and
480/480 critical propagation cases are correct, with zero full-to-hidden MAP
regressions. It reused all ten checkpoints with zero fits, parameter growth or
inference-source changes. Probability costs of missing feedback remain recorded.
[PR #66](https://github.com/robosys-labs/cemm/pull/66) retains the public freeze,
traces, audit and decision. This closes the selected hidden-intermediate task.

Next is the explicit simultaneous/ordered timing requirement: introduce a bounded
compound-contact input with a declared common-snapshot scheduler, then compare
fresh timing twins using frozen learned pair distributions. Event-local outputs
must be combined after each reads the same base world; independently mixing
fixed modes or forcing overlapping factors onto one final variable is invalid.
Scheduling semantics are supplied and must be reported separately from learned
dynamics. The task is selected, not yet implemented or frozen. The
correlation control excludes unconditional marginals, not representations
conditioned on the persistent mechanism. No completed gate is reopened.

## 0. Decision

Try a **world-first, language-second** experiment rather than continuing to grow the existing semantic parser. An agent should acquire predictive distinctions through observations and actions, then learn which utterances communicate those distinctions or help achieve goals. This is a falsifiable hypothesis, not a claim about the origin of human language or current general cognition.

Do not use this roadmap to change the repository's active five-operator authority, six-phase runtime, AGENTS.md, ABI, source-review rules, or effect authorization. The experiment can use a different *internal learned representation* in its isolated sandbox; integration requires a later reviewed interface contract. Draft PR #21 is separately in progress and does not automatically admit this proposal.

**Ultimate objective:** a small nucleus that (a) learns grounded relations and their compositions, (b) transfers learned content across language, prediction and decisions, (c) accumulates knowledge while preserving uncertainty/provenance, and (d) becomes **at least 3× more useful** on a fixed externally judged task bank after Wikipedia exposure, with strong controls showing more than retrieval/memorization.

## 1. Why abandon the previous optimization loop?

The historical mini-nucleus experiments have demonstrated genuine narrower capabilities: learned directed roles between same-kind participants, conditional effects from outcomes, transfer to novel combination families, and within-episode clarification. They also exposed recurring weaknesses:

1. **Misbound updates:** the correct atomic effect exists but an incorrect entity/event binding wins in a longer description; source-only entities can be changed.
2. **Non-systematic composition:** atomic relationships work when isolated, then interfere in nested or multi-clause situations; in some models predictions are additive across sources and cannot express joint two-source functions.
3. **Shortcut learning:** a model can fit training states via self-copy, persistence, default routing or a repeated cue without acquiring the intended mechanism.
4. **Observation insufficiency:** two roles can predict the same outcome in uninformative states; more of those states cannot distinguish them.
5. **Transient belief:** clarification can select better hypotheses for this episode without automatically making later sentences easier.
6. **Lexical isolation:** added word identities can remain unknown to neighboring-word processing; one sense/effect per word is a restrictive assumption.
7. **Evaluation traps:** confidence, phrase-level tests, query answers (especially 'unknown'), averaged bit accuracy and redundant derivations can conceal wrong meanings.

These justify a *new experimental objective* rather than further phrase conditions or grammar production families. Retain the strongest previous models as baselines, not imports or authority for the new learner.

## 2. The proposed primitive machine

The first prototype should require only a handful of dependable computational facilities:

| Supplied facility | Reason | What is **not** supplied |
|---|---|---|
| Addressable, stable entity handles | Preserve identity under observation-order shuffles | Word ↔ identity mappings; semantic roles |
| Timestamped observation/action records | Separate before, after, intervention and provenance | Causal rules, event names, relation labels |
| Shared per-object / per-interaction neural computation | Allow learned computation to transfer to novel objects | Predicate-specific functions or parse recipes |
| Bounded recurrent memory / belief over alternatives | Preserve identity, history, hidden state and uncertainty | Gold present-state answers or hidden simulator parameters |
| A pure predictive step | Evaluate possible futures without world mutation | Which future is desired; fact admission |
| Separate goal/reward evaluation | Prevent preferences from rewriting beliefs | ASK/ASSERT/COMMAND labels, linguistic intentions |
| Opaque token/character stream when language begins | Preserve unknown word identities | Hard-coded POS, roles, templates or glosses |

Learned model at time t, schematically:

~~~text
memory_(t+1) = update_theta(memory_t, observable_t, action_t, message_t?)
forecast     = predict_theta(memory_t, candidate_action, context)
decision     = plan(forecast, externally supplied preference, costs)
~~~

The simulator may have exact rules to generate training **outcomes**, but these cannot be imported, retrieved, distilled into lookup tables, or otherwise accessed by the learner at inference. Ground-truth roles and rule names remain evaluator-only.

**Strong distinction:** predict world consequences given a message ≠ understand that a message is true. A message is an observed communication event, with a source and context; its asserted content may be false, hypothetical, uncertain or goal-directed.

### Supplied structure vs learning ledger

Every experimental run must report, in a machine-readable manifest:

- **Supplied**: sensor geometry, stable identity handles, possible actions, intervention API, episode boundaries, target reward/preference, evaluation oracle, controlled-language generation.
- **Learned**: state dynamics, interaction roles, reusable latent distinctions, text-to-world alignment, belief update from other agents, communicative policy and goals inferred from messages (not the external goal itself).
- **Mixed**: memory addressing, number of slots, architecture bias, decoding/search and planner. Attribute benefits of these biases through ablations.
- **Not established** until independently tested: human language discovery, unrestricted grammar, open-world causality, consciousness, Wikipedia-grounded understanding, supremacy over LLMs.

## 3. Code and repository boundaries

Suggested experimental checkout, **not created by this document**:

~~~text
experiments/predictive_nucleus/
  README.md                # exact run commands, supplied-vs-learned inventory
  world.py                 # independent deterministic simulator / oracle
  model.py                 # shared learned world state and predictive dynamics
  train.py                 # outcome-only and then communication training
  evaluate.py              # no-training evaluation with full traces
  protocol.json            # budget, strata, seeds, freeze metadata
  tests/                   # exact implementation invariants only
  snapshots/               # manifests/digests; large data elsewhere
~~~

Aim for <2,000 authored Python physical LOC **including** generator, training, tests and evaluation *when practical*. The scientific contract has higher priority than this convenience target. Always print exact source size, neural parameter count, number of unique experiences, training FLOP proxy/GPU-hours, hardware, latency percentiles, throughput and peak RSS. No hidden imports of previous CEMM inference or pretrained teacher models.

Never overwrite the older seed/checkpoints, the root five-operator runtime or the in-progress six-phase foundation. The research can graduate only by a future reviewed decision compatible with authority and effect boundaries.

## 4. Rigorous evaluation discipline

### 4.1 Blind challenge design

Generate independent random worlds and privately authored test situations before training. Keep a cryptographic digest of manifests and oracle versions. Entire **structure families**, not merely surface strings, must be held out:

- complete directed role-reversal pairs (same-kind participants) and their bilingual twins;
- 1–2 interactions during training vs 3–5 interactions and different topologies at test;
- no-change, source-only, true self-reference, repeated names, delayed state effects;
- simultaneous vs sequential effects and two-source interactions;
- earlier observation vs current observation vs hypothetical future;
- different goals on the exact same acquired model, without further world training;
- unfamiliar expressions/words and previously unseen compositions;
- uncertain, conflicting or unreliable communication, including false messages.

Training, selection, calibration and final evaluation partitions must not share duplicate-risk lineage (same episode, paraphrase, simulator seed, template family or derived surface). The oracle cannot be inferred from the learner's own prediction or pseudolabel.

### 4.2 Primary metrics (report strata, not just averages)

1. **Complete-world outcome accuracy**: every entity's complete predicted state for each exhaustive situation/trajectory, including untouched entities.
2. **Role-pair correctness**: *both* reversed participant assignments correct; one-direction success gets zero pair credit.
3. **Generalization**: novel entity count, graph family, composition depth, action order, controlled language, goal and word.
4. **Probabilistic quality**: predictive NLL, Brier, calibration plot/expected calibration error, coverage under abstention, epistemic vs aleatoric uncertainty.
5. **Interaction**: optimal external-goal action rate, regret, question/answer cost, causal contribution of communication.
6. **Regression**: number of previously correct items broken, newly repaired items, affected families and worst seed.
7. **Efficiency**: training examples/tokens, parameters, wall clock, memory, p50/p95 per-step latency, candidate/search expansion count.

### 4.3 Required controls

- no-learning; no-change; memorization; flat recurrent model at matched budget;
- model without persistent memory; without object-level sharing; without language;
- word-shuffled / random-message / messages removed; source assignments swapped;
- observation-only vs learned world model; direct supervised text-to-program parser when language enters;
- retrieval-only and text-frequency-only when corpus enters;
- unchanged architecture + more data; unchanged data + proposed architecture; matched parameter count and compute;
- fixed oracle with output changes independently resampled to detect shortcuts.

**No training after opening a sealed challenge.** If a hypothesis is adjusted after analysis, preregister a fresh challenge for the next round. Prior failures become diagnostic regression examples, not new blind successes.

### 4.4 Failure taxonomy (one primary cause per audited case)

- **Implementation invariant failure:** serialization, identity alias, leakage, stale revision, state mutation or inconsistent equivalence.
- **Representation/function-class limit:** no possible parameter setting can express target operation or joint dependency.
- **Identifiability gap:** available observations cannot distinguish candidate explanations.
- **Optimization issue:** hypothesis class can express it, but fitted weights fail, collapse or plateau.
- **Data/distribution gap:** training lacks a distinguishing context or compositional family.
- **Search/resource issue:** correct interpretation exists but is pruned, times out or runs out of memory.
- **Belief/communication issue:** false assertion admitted, repeated evidence double-counted, query unhelpful or preference contaminates belief.
- **Evaluation defect:** leakage, wrong oracle, phrase-based gold, wrong identity normalization, duplicated split.

Only the diagnosis determines whether to change training evidence, model architecture, code invariant, search or evaluation. No sentence-specific parser patches.

## 5. Sequential implementation tranches

Each tranche is **one small PR** with its own gate, no unrelated changes. The authoritative checklist is in [issue #22](https://github.com/robosys-labs/cemm/issues/22); the details here define the experiments.

### G0: Freeze protocol / baselines

**Inputs:** the last consolidated and local-reference evaluations as historical baselines plus an independently reproducible flat neural reference. Baselines imported only into the evaluator, not the learner.

**Work:** declare minimal world physics; learner-visible fields; fixed held-out families; leakage checks; task metrics schema; CPU/GPU budget; ≥5 random seeds; canary tests for state mutation and action timing.

**Evidence:** split hashes; smoke-run and deterministic replay; distinct train/test generator sources; minimal ablation runner.

**Exit:** a complete protocol manifest before any world-model training.

### G1: World-first self-supervised predictions, no language

**Seed world:** 3–6 same-kind agents; 1–2 state dimensions (start with a binary lamp), directed interactions, physical interventions, neutral actions, nontrivial history, occasional partial observation. IDs are given to focus the study on relation learning; make it explicit.

**Learner view:** observation_t, action_t, observation_(t+1) *only when it arrives*; observation order is randomized. Gold transition tables and relation names are evaluator-only.

**Learning:** shared transition network plus persistent memory. No hardcoded copy/opposition/XOR interpretation. Require contrasts distinguishing actor vs source when types agree. Compare against flat neural/no-change and parameter-matched structured baselines.

**Gate:** as a predeclared target, ≥95% exact full-world prediction across ≥5 seeds on unseen in-family episodes, role-pair transfer and no spurious changes; significant matched-budget improvement on novel graph compositions. Failure is a STOP/REVISE, not permission to seed semantics.

### G2: Composition and coherent predictive state

**Training:** at most two interacting relationships per episode and bounded memory updates. **Evaluation:** three to five relationships, previously unseen cycles/chains/disjoint components, sequential vs simultaneous timing, self-referential arguments and multi-source functions.

**If current model cannot express** XOR of two independent external sources, add *one* general intermediate mechanism, then ablate it against extra compute/parameters. This is an allowed architectural change justified by a function-class proof—not a special XOR branch.

**Dependency test:** two belief distributions with identical individual 50/50 marginals but opposite correlation must yield different relational predictions. Reuse of one uncertain fixed mechanism across two applications must preserve correlation rather than resampling it.

**Gate:** full table and prediction-loss improvements at fixed budgets, including untouched entities and held-out compositions; calibration checked.

### G3: Grounded words after learning the world

Keep world weights frozen for the first language transfer stage.

Train a small text/communication encoder on episodes with both:
- English-like SVO;
- explicit artificial OSV (not English with synonym substitution).

Word meanings and order are **not** given as parser programs. Some utterances correspond to prior observable episodes; others do not. Test 'Ada follows Ben' vs 'Ben follows Ada' where both roles have the same kind and are feasible.

**Predeclared teach-once test:** introduce a fresh interaction through *non-linguistic* episodes, then a handful of grounded bilingual expressions, then freeze. Test transfer to new participants, role reversals, predictions, goals and never-seen phrase combinations. Compare to a text-only model and a supervised text-to-program baseline.

**Gate:** grounded bilingual generalization. New lexical identities must be stored distinctly; no permanent <unk> collapse and no automatic single POS/sense commitment.

### G4: Meaningful messages, information and desire

Provide two agents with different information, common physical actions and goals specified **externally** as rewards/preferences.

A message is an *observable* act; the agent is not given an ASK/ASSERT/COMMAND class. Training may contain successful and unsuccessful communication episodes. Test:
- sender tells receiver what sender observed;
- sender seeks information that affects a planned action;
- same sentence with different desire or context;
- one misleading/false report;
- changed focus, conflicting sources and delayed evidence;
- when not to ask, because the answer cannot change a choice.

**Decision gate:** communicative behavior yields higher *held-out utility* than silent/random/shuffled message baselines at matched query/step budgets; demonstrate causal effect of delivered message; no belief mutation solely from untrusted utterances.

### G5: Ask–revise–retain, not ask–forget

Retain competing beliefs, their source/time/evidence IDs and scope. On non-identifiable questions return explicit uncertainty; select discriminating queries where possible. Verify effects in the environment; keep counterexamples. Train a shared learner or reusable memory with *only answered observations*, then clear episode memory.

**Gate:** new sentence families require fewer clarifications at matched final correctness, correct earlier behavior retained, duplicates don't inflate certainty and contradictory sources remain visible. Include wrong-high-confidence cases and cases where no available question could resolve ambiguity.

### G6: Text/corpus acquisition bridge

Only after G1–G5, stream unlabeled descriptions and treat them as sourced observations of communication. Preserve token identity, mention/coreference alternatives, evidence provenance and conflict; develop a link from text evidence to world prediction/decisions. Do not create a separate word-frequency model and label its lower perplexity 'semantic cognition.'

**Gate:** improvement on *new* grounded predictions / inference / decisions beyond retrieval and frequency controls. Unresolved language creates an investigable frontier; no implicit promotion of unverified claims.

### G7: Wikipedia task bank and 3× target

**Freeze upfront** at least 100 answerable tasks, plus ≥20 unanswerable controls, externally authored from a predeclared corpus snapshot and evaluation sources. Reserve >=30 inferential/compositional tasks that cannot be passed by verbatim lookup alone. Keep article/topic/answer lineages split; do not copy answers into training prompts; respect Wikimedia usage terms and attribution.

Proposed balanced bank (revise **before freeze**, not post hoc):
- 20 earlier-competence retention;
- 20 direct source retrieval;
- 30 paraphrased designation/relationship;
- 30 cross-statement inference and knowledge transfer;
- 20 separate unanswerable/conflict controls.

Compare exactly the same nucleus **before/after** ingestion at the same query compute, against retrieval-only and retrieval+matched-model. Start with 20 articles, then 200, then 2,000 only when pilot adds semantic utility. Save per-item evidence/provenance and resource cost.

**Utility definition:** U = number of **correct, supported substantive responses or decisions** on identical preregistered answerable tasks. Threefold gain: U_after / U_before ≥ 3.0, with U_before >= 20/100 (avoid tiny-denominator artifacts). Concurrent gates: answer precision ≥95%; false claims on unanswerable controls ≤5%; retain ≥95% of pre-ingestion successes; p95 latency ≤2× baseline at comparable resources; no safety/effect boundary breach. Report 95% confidence intervals/≥5 seeds as appropriate. A retrieval-only win is useful but cannot support the stronger claim of acquired compositional meaning.

No claim of a general 3× advantage over Claude, DeepSeek or other foundation models follows from this metric.

### G8: Promotion / integration (not automatic)

Independently reproduce G1–G7 on fresh worlds and corpora. Conduct adversarial data/speech injection, authority/evidence poisoning and unauthorized action tests. Review the model's interface separately from its internal representation. Preserve existing exact, proof, authorization, revision and rollback controls.

Any integration requires an approved architecture/ABI/AGENTS change coordinated with PR #21 and its successors. Research success **does not** waive R4/R5 acceptance/admission status. A single experimental learner must not create a parallel production brain.

**Exit:** documented acceptance, code review, all CI gates, compare/rollback, owner and operational budget. Otherwise remain an isolated experiment.

## 6. Working cadence and tranche template

For each implementation PR, include the following table:

| Field | Required evidence |
|---|---|
| Hypothesis | One falsifiable mechanism and one comparison |
| What changed | Smallest mechanism; LOC/parameter/compute delta |
| What stayed fixed | Learner-visible fields, data budget, baselines, seed policies |
| Who supplied meaning | Simulator/teacher/learner boundaries and leakage audit |
| Tests | Invariants vs frozen scientific challenge, independent oracle |
| Results | All seeds; per family/language/length; complete-world and calibration |
| Regressions | Previously correct -> wrong; type, magnitude, case IDs |
| Failures | Reproduction commands, score/trace, earliest divergent state |
| Costs | Tokens, time, RAM, inference latency, search expansion |
| Decision | KEEP, REVISE, REJECT; independent sign-off |

**Promotion rule:** no passing a tranche by selecting a favorable seed, changing exact-match gold, dropping a difficult group, inflating correlated samples, or omitting failed experiments. A zero-result experiment may be valuable; record why and whether it falsifies the hypothesis.

**Stop conditions:** (1) world learning does not beat strong baselines after a fixed budget; (2) supposed groundings remain unrecoverable from outcomes; (3) candidate meaning cannot express independent-source interactions; (4) communication succeeds only through memorized codes; (5) corpus reading improves likelihood but not downstream tasks; (6) 3× result rests on source lookup or tiny denominator; (7) implementation/authority boundary compromised. Diagnose before adding features.

## 7. First four proposed commits (future; not done here)

1. **G0 experiment manifest:** isolated directory, README, supplied-vs-learned inventory, evaluation schema and frozen seed manifests. No neural model.
2. **G1 world + invariants:** deterministic multi-entity simulator, interventions, oracle, independent reverse-role and state-isolation tests.
3. **G1 model + training:** minimal shared predictive model trained from trajectories; flat and no-change baselines; complete-cost report.
4. **G1 blind outcome report:** locked model checkpoints, independent generation seeds, per-case errors, ablations and GO/NO-GO. No language before passing G1.

Later commit scopes follow gates G2–G8. The research issue remains open through the entire program; leave failing gates checked off only when their declared exit evidence is genuinely recorded.

## 8. Status and pointers

- **Issue:** [#22](https://github.com/robosys-labs/cemm/issues/22) — master checklist and research progress.
- **Existing work:** [PR #21](https://github.com/robosys-labs/cemm/pull/21) — draft six-phase foundation, not an admitted new learning objective.
- **Root authority:** [AGENTS.md](../../AGENTS.md); **Hybrid subtree authority:** [hybrid_mvp/AGENTS.md](../../hybrid_mvp/AGENTS.md). Both are unchanged by this document.
- **Roadmap state at creation:** planning only; no new model trained, no Wikipedia benchmarks run, no runtime switched, no release status promoted.

**Success requires evidence, not architecture prose.** The value of this roadmap is that it can fail in informative ways and still guide the next independent experiment.
