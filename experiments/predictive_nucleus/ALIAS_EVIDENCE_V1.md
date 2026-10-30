# Alias evidence v1: fixed architecture, matched observations

This is one prospective public development experiment under
[`alias_evidence_protocol_v1.json`](alias_evidence_protocol_v1.json). Its source,
data and decision criteria are committed before fitting; actual checkpoint
hashes are committed before collection. G1 remains **NOT_ADMITTED**.

## Question and exact repairs

The prior [continuation-v1 result](CONTINUATION_DECISION_V1.md) is retained with
its original `STOP_INCOMPLETE_RUN`. Its shared model answered all 704 continuation
queries but only 7/16 self-contact queries at each of five seeds. The latter
failure was confident: ordinary input `11` trains outcomes `10`/`01`, while the
supplied alias condition discards those outcomes and renormalizes the untrained
`00`/`11` ratio. Retained tensors put only 0.04–0.11% mass on these two outcomes.
Their ratio is not identified by the ordinary training targets.

The alias loss has a direct gradient on the difference between those two logits.
Synthetic differentiation through the actual replay path confirms finite
corrective gradients without updating weights. There is no demonstrated need
for a bigger model or an alias-specific network for this world law.

Separately, `EmpiricalPaths.receive` rejected an impossible observation before
its existing observation-based reentry branch. Inference v6 removes that premature
exception and records `support_contradiction`. Full observations plus sufficient
observed history permit reentry; missing current/history evidence still abstains.
The old forecast keeps zero probability/infinite loss and the mismatch alarm
remains committed. No empirical table or unknown past observation is rewritten.
This fix adds two net inference lines. It is not retrospective v1 rescoring.

## Matched intervention

Both arms use a fresh `DomainKernel(hidden=11, persistence=False,
role_tying=False, memory=True)` with 562 parameters. At each seed
`[7, 11, 23, 37, 53]` they start from identical tensors.

The ordinary arm receives a fresh ordinary-contact tape. In the alias arm, the
first two eligible single-contact physical lineages per entity count have both
reversed views replaced with a self-contact on each view's first operand.
Eligibility requires unequal precontact bits, computed from the initial anchor
and any leading set before looking at the hidden mode or contact outcome.
This gives 16 substituted episode views from eight related physical lineages,
balanced at two views per entity count and starting bit. The paired views remain
dependent observations, not independent self-contact replications.

All other evidence is identical. Episode IDs, entity counts, action kinds/counts,
coverage, masks and visible-bit exposure match. Each arm completes 128 full-tape
Adam updates at learning rate .02, with a 300 CPU-second cap per fit. Bounds stay
64 live paths and 512 candidate expansions. There is no tuning, retry,
selection/calibration fit, flat-model comparison or empirical refit in this
intervention. Actual CPU/wall/path/RSS costs are reported separately.

Both arms receive the same fresh evaluation tape. Sixteen self queries are
explicitly balanced at two per entity count (3–6) and starting bit. Their
canonical blueprints exclude both training tapes, reserved splits, current
evaluation duplicates and previous v1 self queries. The ordinary continuation
bank retains 704 queries, including 672 three-to-five-contact queries.

The complete tiny-world bank has some canonical overlap with earlier ordinary
examples; the audit reports it explicitly. This is fresh evidence selection and
fresh self evaluation under a familiar supplied law, not novel physics or
independent scientific custody.

## Decision frozen before fitting

1. **STOP_INCOMPLETE_EXECUTION** for unequal prescribed updates, interrupted
   collection, missing trial/episode inventory, invalid identity or unknown errors.
   The two source-pinned neural support errors with impossible-observation evidence
   are measured participant failures: preserve infinite loss and every unproduced
   forecast on planned denominators. This distinction does not change v1's rule.
2. **REVISE_EVIDENCE_FIX** if any seed falls below 95% self accuracy for either
   starting bit, lacks full self/continuation support, violates unchanged-bit
   preservation, falls below 95% continuation accuracy/role-pair conjunction, or
   introduces even one newly wrong continuation query versus its paired control.
3. **KEEP_EVIDENCE_FIX** only if those checks pass, mean self gain is at least
   20 percentage points, and the gain is positive at every seed.
4. Otherwise **NO_MATERIAL_EVIDENCE_EFFECT**.

Raw joint NLL, Brier, fixed-bin ECE, all-action accuracy, per-seed changes and
both self starting bits remain visible. A KEEP establishes learnability of this
specific alias evidence gap under supplied diagonal conditioning. It does not
establish arbitrary self laws, architecture superiority, broad calibration,
independent admission or the original 95% all-action target.

## Reproduction

Use Python 3.13.16, PyTorch 2.10.0+cpu and NumPy 2.3.5, one thread, deterministic
float64. The runner enforces exact source/data hashes and exclusive output paths.

```sh
python -m experiments.predictive_nucleus.alias_evidence_run prepare --output /tmp/alias-prepared
# Commit the protocol, source, data/alias-evidence-prefit-v1.json and assets archive.
python -m experiments.predictive_nucleus.alias_evidence_run fit --data /tmp/alias-prepared --output /tmp/alias-fit
python -m experiments.predictive_nucleus.alias_evidence_run bind --data /tmp/alias-prepared --fitted /tmp/alias-fit
# Copy fit outputs into data/alias-evidence-fit-v1 and commit actual hashes/plan.
python -m experiments.predictive_nucleus.alias_evidence_run collect --data /tmp/alias-prepared --fitted experiments/predictive_nucleus/data/alias-evidence-fit-v1 --output /tmp/alias-results
```

Keep a failed attempt. A different output path is not permission to retry.
The fitter imports only observed histories and existing learning APIs; simulator
generation is confined to preparation. Historical artifacts stay immutable.
