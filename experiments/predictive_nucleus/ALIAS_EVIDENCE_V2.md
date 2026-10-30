# Alias evidence v2: observable acquisition before alias learning

This is one fresh experiment following the retained
[v1 REVISE decision](ALIAS_EVIDENCE_DECISION_V1.md), under
[`alias_evidence_protocol_v2.json`](alias_evidence_protocol_v2.json).
Architecture, loss, optimizer, width, parameter count and update ceiling are
unchanged. It reuses the same data/runner modules and existing artifact formats.
The v1 protocol, inputs, checkpoints, results and decision remain intact.

## Specific hypothesis

V1 teaches aliases as first contacts. At failed seed 37, one latent branch
explains almost every alias-zero observation, leaving the other branch very
little gradient. Its correct probabilities are 0.9942864 and 0.0047649, whose
equal mixture falls just below one half. This is not an exact tie or a proven
representational impossibility: four other seeds learn both branches.

The smallest prospective change supplies an informative **observed** ordinary
contact before the alias. The learner receives no hidden mode label. Retained
tensor arithmetic shows such an observation can increase the failed branch's
alias correction approximately 158-fold. This is an endpoint mechanism
calculation; no optimization trajectory or retraining result was inferred.

## Fixed schedule

For each entity count 3–6, select the first eligible two-contact lineage with a
known untouched zero and the first different lineage with a known untouched
one. Eligibility uses the initial anchor and optional leading set, before
contact outcomes. The target is the first eligible sorted ID outside the first
contact's operands. Both related reversed views stay in their original lineage.

Retain the first informative contact and its complete observation. In treatment,
replace only the second contact with self-contact on that untouched entity;
ordinary controls retain the original second contact. Every preceding reading,
action count/kind, coverage and mask is identical between paired tapes.
Subsequent observations reflect the actual respective actions.

Selected training orientations are allocated before final realization in both
arms using `(N - 3 + prebit) % 2`: one of each orientation per N and two physical
lineages per starting-bit/orientation combination across N. This allocation is
supplied experimental design; no orientation field enters the observed learner
input. The model still infers its anonymous branch from actual contact feedback.

There are sixteen alias views from eight dependent lineages. Both v2 tapes have
128 episodes, **334 observed events and 1,514 visible bits per update**. V1 had
340 events/1,538 bits, so matching is within each fresh comparison; between-study
performance is descriptive. Parameters stay **562**, updates **128**, learning
rate **.02**, CPU ceiling **300 seconds per fit**, with the same five seeds and
identical initial tensors within each pair. No tuning or retry is permitted.

The common fresh evaluation bank contains 704 continuation queries and sixteen
first-self queries, balanced across both starting bits and N. Self blueprints
exclude current training/reserved cases, historical continuation self cases,
and opened v1 self/training cases. Ordinary canonical overlap in this finite
world is disclosed. No new physics or independent custody is claimed.

## Unchanged acceptance criteria

The five-seed criteria are identical to v1: at least 95% exactness for each
self starting bit, full query support, zero self/continuation unchanged-bit
errors, at least 95% continuation/role-pair exactness, and **zero newly incorrect
continuation queries**. KEEP additionally requires at least 20 percentage points
mean self gain and positive gain at every seed. All actions, proper scores,
failures and planned denominators remain recorded.

The support-failure versus execution-failure distinction is unchanged. G1 remains
NOT_ADMITTED for any outcome, and the original all-action 95% target remains in
force. Failure means revise or stop this configuration; it does not authorize
a same-bank fit, a threshold change, or another infrastructure tranche.

## Execution

Use the existing four-stage command with `--study v2`:

```sh
python -m experiments.predictive_nucleus.alias_evidence_run prepare --study v2 --output /tmp/alias-v2-prepared
# Commit sources, protocol, data/alias-evidence-prefit-v2.json and the assets archive.
python -m experiments.predictive_nucleus.alias_evidence_run fit --study v2 --data /tmp/alias-v2-prepared --output /tmp/alias-v2-fit
python -m experiments.predictive_nucleus.alias_evidence_run bind --study v2 --data /tmp/alias-v2-prepared --fitted /tmp/alias-v2-fit
# Copy into data/alias-evidence-fit-v2 and commit actual checkpoint hashes and plan.
python -m experiments.predictive_nucleus.alias_evidence_run collect --study v2 --data /tmp/alias-v2-prepared --fitted experiments/predictive_nucleus/data/alias-evidence-fit-v2 --output /tmp/alias-v2-results
```

All v1 research attempts are closed. Their original source commits reproduce
their frozen artifact identities; current sources intentionally identify v2's
reused driver implementation. No inference source changed after v1.
