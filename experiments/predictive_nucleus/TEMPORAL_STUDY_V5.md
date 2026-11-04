# G5 v5 — two-hypothesis temporal correction, prospective bounded development

**Parent:** PR #89 at `191e2e47d94b8045518b993ccd7a885b1e3064e5`.
**Status:** freeze **before implementation, TRAIN fitting, TEST collection or scoring**.
**Decision scope:** development-only; cannot satisfy independent G5 scientific admission or warrant G6/production cutover.

## Question and minimal model

Can an outcome-trained, two-hypothesis temporal memory distinguish a *transient contradictory observation* from a *persistent meaning change* after an externally visible episode boundary, and outperform the accepted zero-trainable-parameter dated-evidence rule under noisy observed payoffs?

Keep the current two supplied meaning candidates, stable entity handles, declared hierarchical scopes, verified provenance, action choices and G3 reward-conditional probabilities. Do not import any gold meaning/role label, hidden simulator variable, future observation or language parser into the policy. No changes to any frozen G1–G4 checkpoint, accepted G5 v1 or production semantics.

Use only **two learned scalars**, shared across words/scopes/seeds: `h` (probability of *persistent* binary meaning switch at an observed episode boundary) and `e` (probability of an independent *event-local transient* payoff inversion). These two explanations are marginalized, not promoted into hardcoded phrase or meaning labels. A locally observed meaning maintains P(stable meaning=1), updated from selected observed payoffs via a two-state Bayesian filter. No state transition occurs merely because a receipt has a later timestamp; apply `h` only when a supplied, genuine epoch-boundary flag is true. A nondiscriminating likelihood cannot create information. Unknown scoped meanings remain unresolved; absent child evidence inherits the parent, while child observations are fitted with an initially neutral local prior. Unverified claims and identical evidence-ID replays cannot add information; conflicting reuse is rejected. Same-time evidence must not invent a transition per receipt. Snapshot/reload must reproduce beliefs.

## Fixed physical data and new uncertainty task

Use `transfer_task.catalogue(law, split)`, `revision_study.select_triples`, and the frozen G3 selected-action conditional payoff matrices. This physical catalogue has been opened in previous G4 research, **so no claim of independent physically blind evaluation** is possible. The *task structure and noise challenges* are prospective, with `train` versus `challenge` physical lineages and distinct deterministic salts, recorded before fitting. Use exactly both laws NAND/NOR and five inherited seeds 7, 11, 23, 37, 53.

Per law/seed/split, use six metadata-selected triples with all three word orders and nonoverlapping physical roster identities/lineages, 16 combinations of root/regional/local/sentinel meanings, and two **equally represented** counterfactual continuations: transient exception or persistent change. That is **192 episodes per condition**, each with equal public histories until a single conflicting physical payoff at a visible epoch boundary. Each episode contains repeated grounded root, regional and local evidence; an independent sentinel; a contradictory epoch event; two later discriminating physical selected-payoff receipts; a false unverified claim; and an optional identical receipt-ID replay. Selected payoff inversion noise is deterministic from a predeclared split-specific SHA-256 stream at an 8% rate on noncritical observed events; the paired contradictory event is held identical across opposite latent continuations. Sensor source identity alternates but is supplied and is never itself a meaning label. Record which evidence was noisy for **evaluator-only** analysis; the learner receives only `(source, scope, term, time, epoch, probabilities, selected payoff)` and exact receipt IDs.

TEST uses `challenge` physical catalogue and a distinct frozen salt; no generated test outcome may be read during fit or parameter selection. This is a reused-world development transfer study, *not* independently held-out scientific admission.

## Fit without gold

Fixed grid: `h ∈ (0.05, 0.15, 0.35, 0.5)`; `e ∈ (0.01, 0.05, 0.1, 0.2)`. Optimize only **one-step-ahead causal predictive NLL** of the observed selected payoff, strictly before incorporating that payoff, averaged over complete TRAIN histories; no latent interpretation labels, correctness, query answers or future outcomes may select the grid values. Numeric ties: smaller `h`, then smaller `e`. Fit all ten law/seed conditions once; publish every grid loss, chosen scalars and source/runtime identity **before** the first challenge execution. Also evaluate fixed `h=0`, the simpler zero-state no-memory reference, and a no-exception `e=0` control on the same causal history; do not invent probability scores for the v1 rule's discrete decisions.

## Registered TEST outputs and gates

At a checkpoint immediately after the matched contradictory epoch event and another after the two further physical observations, evaluate the current unit, sibling, outside/root and independent sentinel on the same histories. Parent/sentinel state may never be overwritten by a local receipt. Preserve all 192 scenarios and all ten conditions in denominator, including uncertainty and noisy errors. On pre-evidence counterfactual twins (same public prefix, opposite latent future meanings), count *premature confident decisions* explicitly. Distinguish fundamental unidentifiability (same public prefix) from empirical prediction error. Report paired before/after correct, incorrect, abstained, cheap informative queries at 0.05, costly/unavailable query avoidance, net utility, and change vs the unchanged G5 v1 rule, latest-event and no-memory references. The optional perfect verification reply must become visible **only after a paid question**; zero if unavailable or nondiscriminating.

Report NLL/Brier/calibration on held-out selected payoffs, causal action/provenance audits, held-out lineage overlap, signal/noise breakdown, source/epoch ablations, repeated IDs, same-time conflict, per-law/seed adverse cases, parameters, line count, CPU and memory. An unverified message cannot change a physical belief.

**KEEP_BOUNDED_TEMPORAL_CANDIDATE** requires: all protocol/retention/identity gates; no pre-probe false *confident* answer on indistinguishable balanced twins; no wrong high-confidence sentinel/parent predictions; fewer or equally many queries at matched or higher final correctness than the v1 rule; strictly greater held-out net utility or proper predictive performance against a **probabilistic control**, in every law and at least 4/5 seeds, without worse worst-seed utility; and no evidence of shortcut from source/epoch controls. If not, **REVISE_TEMPORAL_CANDIDATE** or **STOP_CONFOUNDED**, preserving adverse outcomes. Passing never means formal G5 admission; only the simplest demonstrated mechanism is retained.

## Sequence, integrity and bounds

1. Publish this protocol and freeze its exact source commit first.
2. Publish an isolated two-scalar learner, deterministic synthetic task generator, and software invariants (TRAIN-only); no challenge run yet.
3. Publish actual ten fitted TRAIN checkpoints, complete loss curves, and cost receipts.
4. Execute the untouched challenge **once**, seal raw forecasts and outcomes before scoring, then score separately against both strong rule references.
5. Publish full decision and unchanged roadmap caveats. No new language syntax, operator families, full framework, shadow runtime, or production model activation. Keep incremental code small relative to the existing oversized research namespace; the inclusive 2,000-LOC target remains unmet.
