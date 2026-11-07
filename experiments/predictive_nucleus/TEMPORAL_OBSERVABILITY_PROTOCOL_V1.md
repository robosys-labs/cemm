# G5 temporal observation support v1

## Bounded question and stop rule

Parent: `9083c5c0f371c8d8a950abb4e8f748b95ff8d778` (PR #99).
This exact task-design preflight asks which available physical observations
can distinguish a durable local correction, one-event exception, report-only
change, or parent-scope correction. It does not fit or evaluate a learner,
alter G1–G4, promote G5, or authorize G6–G8.

Publish this protocol before implementation, then publish source and synthetic
tests before the complete enumeration. Run that enumeration twice, compare
deterministic output bytes, independently check its partitions and utility,
and publish the result and a concrete next learner contract. Stop there:
no parameter sweep, new generic framework, or extra persistence qualification.

## Fixed finite environment

Reuse the existing Boolean simulator and the independently implemented table
oracle in `bilingual_data._step` and `effect_role_data._distribution`.
Require agreement on every used physical endpoint. There are two native laws
(NAND, NOR), two established physical modes, four primitive operation choices
(two contact directions and SET of either participant), and all eight binary
states of three participants. The underlying physical law never changes.

For each law/mode, old operation and original event state, enumerate every
distinct proposed new operation and four evaluator-only histories:

| History | Original local event at t=0 | Local at t>=1 | Sibling at t>=1 |
|---|---|---|---|
| Local correction | new | new | old |
| One-event exception | new | old | old |
| Report-only change | old | old | old |
| Parent correction | new | new | new |

A protected second word keeps its original operation in every history.
"Durable" means retained through the finite t=2 target horizon; no permanence
beyond that horizon is established. Scope topology, time and source identity
are supplied task metadata, not discoveries by a model.

Inventory: 2 laws × 2 modes × 4 old operations × 8 original states = 128
pre-report contexts; 3 new alternatives × 4 histories = 12 equally weighted
worlds per context, or 1,536 worlds / 384 old-new designs. These are dependent
enumerated counterfactuals, not independent experimental samples.

## Public histories and weighting

The pre-report physical teaching includes all eight states for the old
operation and a complete public primitive-action calibration table. Thus the
old operation's observable behavior and physical environment are established.

All four histories of a given old/new design emit the same source claim at
t=0: the endpoint of the proposed new operation on the original state.
In the report-only history this claim may accidentally be true. Retain these
coincident-endpoint cases; do not filter to forced contradictions.

This is a declared adversarial equal-likelihood construction, not random
sensor noise or an estimate of real-world source reliability. The prior is
uniform over the 12 evaluator worlds before the report; condition it only on
the actually observed report endpoint. Crucially, pool ALL proposed-new
alternatives with the same complete public prefix. Do not give the decision
calculation the private old/new pair or cause. Public identifiers and probe
menus must be independent of those hidden choices.

Record ordered evidence identities and a digest of the delivered prefix.
The 12 worlds share exactly the same pre-report prefix; worlds within each
post-report group share the same full public prefix, goals, fees and menus.
Private world identity, new operation and cause are evaluator-only. This
preflight emits no learner training file and makes no learned-performance claim.

## Available observations

- Immediate verification: an independent authenticated measurement of the
  ACTUAL t=0 event, at its actual initial state. It is not a new intervention
  and cannot query counterfactual initial states of that historical event.
- Delayed local probe: a fresh t=1 instance at each of the eight initial states.
- Delayed sibling probe: the same menu in the sibling scope.
- Protected-word probe: a fresh t=1 instance using the unchanged second word.
- Report replay: the same source claim with the same evidence identity. It
  contributes no new independent observation and does not alter the posterior.

All fresh probes are independent reset instances; their outcomes do not change
the target state. Each target is a separate t=2 instance, local or sibling,
at each of eight states. Goals are correct target-endpoint prediction with
reward 1 and incorrect prediction with reward 0, explicitly not a benchmark
of autonomous goal selection or world action execution.

Study two menus: (a) immediate verification available; (b) original measurement
lost, with no subsequent ability to reconstruct it. Also study no questions
available. The target utility calculation cannot retrieve an unavailable
measurement. Fees are .05 (cheap), 1.0 (prohibitive), or unavailable.
Reject a query unless its exact expected target benefit strictly exceeds cost.
Break ties by the frozen public menu order.

## Required calculations and invariants

For every identical-prefix group, report:
1. Posterior world weights under the declared construction.
2. Full endpoint table for every available observation and every target.
3. Exact partitions of worlds induced by each observation and the complete
   menu, distinguishing cause identifiability from target identifiability.
4. Minimum nonadaptive set of DISTINCT probes that identifies the target,
   if one exists, under each menu; retain unidentifiable causes explicitly.
5. One-step target-optimal question value, selected question, expected
   correctness and net reward for each fee/menu condition.
6. After observing that selected answer, the retained posterior and target
   forecast on the fresh instance; replay must leave both unchanged.
7. Remaining support for transient versus report-only histories when the
   original measurement is absent or its physical outcomes coincide.

Use exact rational arithmetic for the reference partitions and utility.
Cross-check the existing `physical_query_v1.choose` formula, without
modifying it. Treat duplicate answers as the same evidence identity, not
additional corroboration. Rename/reorder world labels and public handles
without changing partitions, target distributions or utility.

No conclusion is based on a confidence threshold or a hard-coded .5 prior
after observing a report. The uniform weighting is part of the constructed
population, never a learned calibration claim. Read no opened scientific
challenge outputs to select cases or tune a policy.

## Decision and deliverables

Record `KEEP_TEMPORAL_OBSERVATION_PREFLIGHT` only if:
- all 1,536 worlds and all prefix-equivalent new-operation alternatives are
  retained, with no hidden-pair conditioning or public cause leakage;
- both physical implementations agree and every partition/utility audit passes;
- every delayed target is identifiable from its complete physical probe menu,
  or each counterexample is retained and the decision becomes REVISE;
- report replay, protected-word evidence, prohibitive fees and unavailable
  questions cannot produce false information gain or paid queries;
- lost-event cause ambiguity is retained rather than mislabeled as a defect;
- identical runs reproduce bytes and all relevant regression gates pass.

Publish deterministic detailed results, source/protocol hashes, separate
execution receipts, the independent audit, source/test and inclusive LOC,
runtime/RSS, and all adverse cases. Preserve historical evidence and production.

## Next learner experiment, constrained by this result

Freeze one fresh, held-out temporal/scope study using only attainable observation
menus. Train the structured candidate and a similarly sized unstructured
candidate from scratch on the EXACT SAME ordered realized action/sensor
histories, physical state, source/scope/time metadata, optimizer update counts
and consumed examples; record per-forecast evidence IDs and prefix digests.
Do not reuse the archived mismatched GRU as a matched control.

Keep the retained scoped rule and a retained-state-cleared control. Fit from
observed physical outcomes only; no cause labels, gold operation/role labels
or symbolic law implementations enter either learner. Choose hyperparameters
only on fresh TRAIN/validation data, then freeze before TEST.

Report target proper scores, query cost at matched correctness, retained and
worst-seed performance, new sentence-family transfer, and competence after
episodic-memory clearing. Score cause claims only where the available history
can distinguish them; do not require them to answer an already identifiable
target. No further task-design preflight is needed unless this one records a
specific unresolved counterexample.
