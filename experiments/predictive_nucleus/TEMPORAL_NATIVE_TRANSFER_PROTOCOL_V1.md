# G5 native temporal updater — one bounded matched comparison

## Decision and boundary

Freeze this contract before implementation, preparation or fitting. Publish
implementation before preparing data, prepared data before fitting, every fitted
checkpoint before TEST collection, and raw forecasts before scoring. Execute one
fit per arm/seed and one complete collection. A failed gate is REVISE; do not
extend the update budget or tune against TEST. Preserve the opened temporal
observation preflight and the explicitly post hoc restricted-input audit.

Hypothesis: a small learned receipt updater that reuses the frozen native
physical forecasts predicts temporal corrections better than an equally exposed
flat endpoint decoder. This is a bounded learned-update experiment, not complete
G5 admission, discovery of the supplied hypothesis family, or a production change.

## Observed environment and finite split

Use the same two physical laws, two modes, four primitive operations, three
participants and four temporal histories defined in
`TEMPORAL_OBSERVABILITY_PROTOCOL_V1.md`. The simulator and separate oracle must
agree on every generated endpoint. Neither physical implementation is imported
by the learner or collector. Old/new operations and temporal causes are hidden.

Enumerate law × mode × old × distinct new × cause × original three-bit state ×
target scope (local/sibling) × target three-bit state: 24,576 cases. Let `a` and
`b` be the original and target active two-bit inputs. TRAIN contains
`(a+b) mod 4` in {0,1}; TEST contains {2,3}: 12,288 cases each. Sample 2,048
TRAIN cases without replacement using Python Random seed 20261108101. Freeze
the sampler and full held-out inventory before fitting. Identities differ by
split and episode; identifiers are never model features. Within a public
context, new-operation/cause alternatives share handles and question menus.

Each history delivers four parent-scope physical teaching states for each of
the tested and protected words, followed by one local source claim about t=0.
The protected word always retains its earlier interpretation. Then supply a
first physical probe and make a second physical probe available at t=1.
The first scope is local for even `a` and sibling for odd `a`; the second is
the other scope. Their active inputs are `(b+1) mod 4` and `(b+2) mod 4`.
Use spectator bit 0 for the first and 1 for the second. These choices use only
public inputs and exclude the target's interacting-pair input in BOTH scopes.
The target and protected-word check are separate t=2 physical instances.

The fixed two-probe schedule is not the unrestricted optimal menu. Compute
its own exact conditional target distribution and attainable scores from all
12 counterfactual worlds, conditioned only on actually delivered endpoints.
Keep ambiguous cases, stable/report-only cases, local/parent corrections and
the protected word. Do not use the 97.265625% full-menu ceiling as this fixed
schedule's gate or label these dependent worlds independent replications.

## Frozen native input and learned arms

For seeds 7,11,23,37,53 use `coordinate_transport_v1.restore/project` unchanged.
Its four supplied sign transformations provide four native eight-endpoint
distributions. Mode must be inferred from delivered physical calibration
actions/readings, never read from the evaluator's mode label by a model. Keep
all native language/world coefficients frozen. Both arms receive identical
native distributions and physical/source/scope/time/word observations. TRAIN
uses SVO/OSV; TEST uses VOS. These are existing G3 layouts, so this does not
establish acquisition of a new sentence family. Record all inherited model
hashes and endpoint-placeholder invariance checks.

Both new arms use float64 CPU GRUCell(18,8), followed by Linear(49,8), tanh.
Receipt features are: four native likelihoods of the delivered endpoint;
three endpoint bits; three initial bits; scope one-hot(parent/local/sibling);
time scalar; source one-hot(physical/claim); word one-hot(tested/protected).
Query features are the flattened 4×8 native distributions plus initial bits,
scope, time and word (41 values); concatenate the recurrent state (8).
The native arm outputs four softmax mixture weights over the native rows.
The flat arm outputs eight endpoint softmax probabilities directly. Trainable
counts are 1,108 and 1,144 respectively; the flat arm has 3.25% more parameters.
No cause, gold operation, gold participant order or symbolic transition code
enters either arm. The supplied native candidate family remains a limitation.

## Fixed training exposure

For each seed initialize both arms with that seed, Adam lr=.01, default other
Adam settings, no weight decay, 256 updates, batch size 128, no clipping,
early stopping, hyperparameter search or calibration fit. Both arms use the
same fixed sequence of 256 sampled minibatches (sampling with replacement,
Random seed `20261108200 + model_seed`). Record their digest and exact exposure.

Train on observed endpoint NLL only. Each sampled episode supplies six equally
weighted forecasts: first probe before its answer; second probe after the
first; target before either probe, after the first, and after both; protected
target after both. The target is observed once and supplies three forecast
horizons; disclose this reuse. Claims are delivered observations, not loss
labels. Both arms see the identical ordered history and physical answers.
The numerical budget is equal updates/examples, not equal consumed CPU time.

## Collection and controls

Freeze all ten checkpoints before TEST. Collect target forecasts before,
after the first and after both probes and protected-word forecasts. For the
optional second question, predict its endpoint distribution before its answer,
simulate all eight possible answers through the learned updater, and compute
expected target accuracy minus the current maximum target probability. Buy
only for positive benefit strictly above fee (.05, 1, unavailable), using
1e-12 arithmetic tolerance. The actual second answer can be consumed only
after this decision. Persist each pre-answer forecast, decision and all
conditional forecasts so scoring needs no model execution.

Compare native and flat learned arms, the same fitted native arm with the
first-probe update cleared, and a supplied empirical consistency rule over
the same native hypotheses using source/scope-tagged observed evidence.
The rule's exact selection/update contract must be included in implementation
before preparation; it must not read hidden causes. This rule is a diagnostic
baseline and cannot replace the historically retained G5 v1 rule or establish
new learned capabilities. Record consumed evidence IDs/prefix digests and
duplicate/conflicting-ID handling. Raw records may be discarded after a
recurrent summary is made; that is not the full G5 episodic-clear requirement.

## One decision, complete reporting

Report all ten law/seed cells, both arms, cleared and rule controls: complete
world accuracy, observed multiclass Brier and uncapped NLL; excess Brier over
the attainable conditional distribution; >=.95 confident errors; protected
retention; paid questions, realized reward and net reward; paired regressions
and worst seed. Keep every adverse case, including unresolved targets.

Keep this native learned updater for further G5 work only if every law/seed
cell has: (1) after-both accuracy within .02 of its conditional optimum;
(2) after-both excess Brier <=.02; (3) protected accuracy >=.95;
(4) <=1% confident wrong targets; (5) native after-both Brier no worse than
flat by >1e-12 and strictly better than cleared by >1e-4; and
(6) native cheap-query net reward no worse than flat or cleared by >1e-12.
Otherwise record REVISE_NATIVE_TEMPORAL_UPDATER and stop this version. Rule
comparisons and query/correctness tradeoffs remain visible even if these
primitive gates pass; no full clarification-efficiency or G5 claim follows.

Publish source/parameter/total Python growth, fit/collection CPU and wall time,
RSS, complete checkpoints, raw/scored artifacts, deterministic saved-record
rescoring and independent audit. Run the isolated regression suite and
historical manifests once after implementation. No architecture expansion,
persistence rerun, G6 ingestion or G8 integration is part of this tranche.
