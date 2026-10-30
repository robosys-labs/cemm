# Prospective observed data and exact conditional oracle

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22), following the
acceptance contract in [draft #60](https://github.com/robosys-labs/cemm/pull/60).
This tranche implements public, same-author engineering assets under the original
binary-contact physical law. **G1 remains NOT ADMITTED.** The original protocol,
95% target, model seeds and closed studies retain their existing status.

## Review findings and decisions

PR60's passing tests establish collection and scoring invariants. Its oracle
validator checks consistency, but cannot establish that a caller included every
compatible hidden alternative. The new oracle computes those alternatives from
the observed prefix. The original generator also resets contact operands before
each interaction; the new generator carries state between contacts.

Three design distinctions matter before fitting:

1. A balanced hidden role can make a first discriminating contact irreducibly
   ambiguous. The expected all-action accuracy ceiling must be audited before
   treating 95% as attainable. An answerable-only denominator is a separate
   diagnostic and does not replace the original gate.
2. A fixed MAP tie rule can lower trajectory or reversed-pair conjunction scores
   even when the complete probability forecast is correct. Report the behavior
   of that rule, without calling it an optimal joint-policy ceiling.
3. Source/data commitments can be frozen before fitting; checkpoint byte hashes
   become available afterward. The exporter creates a data manifest, never a
   fictitious completed acceptance plan with placeholder checkpoint hashes.

## Frozen data design

`prospective_data_protocol_v1.json` and its separate SHA-256 lock freeze this
data-only design. Fresh split seeds are `2026103001` through `2026103004`.
Model seeds remain `[7, 11, 23, 37, 53]`; no model is fitted here.

| Split | Physical draws | Episode views | Family scope |
|---|---:|---:|---|
| Train | 64 | 128 | Single contact; overlapping or repeated two-contact histories |
| Selection | 32 | 64 | Same development families, disjoint blueprints |
| Calibration | 32 | 64 | Same development families, disjoint blueprints |
| Evaluation | 200 | 368 | Development families plus chain, fork, cycle, disjoint and self-contact |
| Total | 328 | 624 | Reversed views remain grouped by physical lineage |

The domain remains three to six binary entities, with a complete initial anchor,
noiseless visible readings and at most 12 actions. Topologies requiring four
entities are omitted at three entities by the fixed inventory, not after scores.
Self-contact appears only in evaluation and has one view because reversing its
aliased operands creates no distinct role pair. These are fresh public assets,
not an independently held challenge or evidence of unseen entity-count transfer.

For each candidate blueprint, initial bits are fair independent draws. A
two-contact candidate chooses an overlapping or repeated pair with probability
one half each. One leading set and one trailing observe are independently
proposed with probability one half each; intervention entity/value are uniform.
There is no set between contacts. These are proposal probabilities: global
duplicate rejection can change the accepted blueprint distribution. The audit
conditions on every accepted blueprint rather than assuming proposal frequencies
survive rejection.

All physical IDs are selected for sensing. A missing-bit count is sampled
uniformly from zero through three, then that many distinct action/coordinate
cells are chosen uniformly before truth is simulated. IDs, actions, coverage and
missingness are independent of the actual hidden-mode draw. The entire episode
has at most three missing bit-events. Consequently a dense full-support model
needs at most eight recurrent histories and 512 candidate expansions, within
the existing bounds. No oracle support is used to prune a participant's paths.

Blueprint identity binds initial state, actions, selected coverage and realized
masks, excluding later bit values and actual mode. Canonical coordinates follow
action occurrence; untouched coordinates use their anchor/coverage/mask
signatures. The minimum over global contact reversal groups reversed and renamed
derivatives. A duplicate is rejected before the hidden-mode draw; exhaustion of
the attempt budget fails explicitly. Accepted blueprints never cross splits.
Concrete action templates can repeat in the in-family splits and are reported;
the word "disjoint" does not imply every atomic observation or prefix is novel.

Each ordinary draw creates two episodes with the same IDs, anchor, persistent
mode and masks, reversing every contact. The simulator replays each direction
separately. The audit checks exact configured inventories and actual family
topologies, as well as pair coupling and source identities.

## Oracle and feasibility audit

`prospective_oracle.py` uses affine maps over GF(2), independently structured
from the imperative `world.step` simulator. It starts with both equally likely
persistent orientations, propagates each through the current action, aggregates
their world probability masses, records the forecast, then filters hypotheses
using delivered feedback. Modes remain distinct when their current worlds
coincide. A self-contact addresses one physical coordinate and sums it with
itself; a distinct repeated contact and an aliased contact therefore differ.

The oracle receives an observed case only. Actual mode, full hidden truth and
family are absent from its arguments. Its result is complete **conditional on
the declared two-mode physical and observation law**; it does not quantify a
learner's uncertainty about an unknown law or authenticate that law externally.

`prospective_audit.py` reconstructs both equiprobable modes of every accepted
blueprint with the same exogenous masks. It reports actual inventories and
law-weighted expectations separately. For each conditional distribution `q`,
the event MAP ceiling is `max(q)`, the NLL floor is its entropy, and the sum-form
Brier floor is `1 - sum(q*q)`. The calculations use explicit mode probabilities;
they do not infer a uniform prior merely from the number of support worlds.

Expected ceilings are conditional design calculations, not hard bounds on one
finite realized sample. All-action, contact, answerable and ambiguous strata
remain visible. Trajectory and role-pair conjunctions follow coherent latent
branches with delivered feedback; marginal event probabilities are never
multiplied to manufacture a trajectory score.

For example, with anchor `(a,b,c)=(1,0,0)`, the first contacts `(a,b)` and `(b,a)`
both have exact conditional mass one half on `100` and `110`. Lexicographic MAP
chooses `100` in each view, while the actual paired targets are opposite for
either shared mode. Pair exactness is zero despite correct probability forecasts.
This is a tie/identifiability limitation, not proof of failed role learning.

The carry audit suppresses an earlier contact and checks a later contact's
destination under the same fixed mode. It counts actual dependencies, rather
than inferring composition from a graph name or a surviving bystander change.
Every no-carry, no-change and ambiguous case remains in the data.

## Compiled default assets

The checked-in `data/prospective-assets-v1.json.xz` contains the complete observed
and evaluator bundle plus the audit. Two separate exports produced identical
bytes for all 11 files. Archive SHA-256:
`42cf52fb84fece67d23b78751080cd6c6d603767cc6981a517116dca52995f6d`.

| Evaluation scope | Planned predictions | Law-expected ambiguous predictions | Expected optimal event accuracy |
|---|---:|---:|---:|
| In-family | 334 | 96 | 85.6287% |
| All seven families | 1,185 | 304 | 87.1730% |

For the in-family scope, the calculation is `1 - 0.5 * 96 / 334`.
The original 95% target is therefore incompatible **in expectation** with an
all-action interpretation on this design. The earlier closed common-objective
study already documented an ambiguity ceiling of 93.75% for its different
workload. These are distinct information-design calculations, not a regression
in trained-model accuracy; no learned model was scored here.

All 624 views fit the conservative resource bounds: at most eight histories and
512 candidate expansions. The training tape contains 336 events, of which 332
deliver at least one bit; four all-missing events remain present. Of 192 contact
events, 64 have complete immediately preceding and subsequent world readings,
and 104 have both operand readings available before and after. These raw
observation counts do not establish equal eligible targets under every empirical
history policy or equal training cost.

There are 45 action templates shared across in-family splits, explicitly listed
by the audit. Canonical blueprint and physical-lineage overlap across splits is
zero. In evaluation, 198 of 736 counterfactual mode/view branches have at least
one carried-effect witness; all remaining branches are retained. Views and mode
branches are not independent experimental samples.

Decision: **KEEP the data/oracle implementation; REVISE the prospective study's
information and decision contract before research fitting.** Keep all-action
diagnostics, define any task/query scope from permitted information before
outcomes, and preserve ambiguous cases with proper scores. A proposed
identifiable-query interpretation must be explicit and reviewed; this tranche
does not substitute it for the original G1 target or admit any gate.

## Generate, inspect and use

Use the pinned Python 3.13 environment for byte reproducibility:

```sh
python -m experiments.predictive_nucleus.prospective_data --output /absolute/new-directory
```

The exporter builds and audits before creating the destination. It refuses an
existing directory and writes `manifest.json` last. An I/O failure may leave a
new incomplete directory without that completion manifest. The output contains
four `.inputs.json` files, four separate evaluator `.oracle.json` files,
`audit.json`, a deterministic `asset-bundle.json.xz`, and the manifest. The
manifest records exact byte/content hashes, source hashes, configuration and
case lineage; its own hash is returned separately to avoid self-reference.

The participant receives only the observed input file and its native checkpoint.
Keep oracle, audit, case metadata and the combined archive on the evaluator side.
For later training, the new observed-only adapter uses the same delivered tape:

```python
from experiments.predictive_nucleus.observed_io import load_batches

batches = load_batches("train.inputs.json", ACTUAL_INPUT_FILE_SHA256, batch_size=32)
```

`observed_io` imports no simulator or prospective oracle. It groups complete
episodes by entity count and action length, preserves input order within each
group, sorts physical coordinates, and preserves missing values as `-1` with
separate masks. There is no temporal padding, hidden-target filling or new
training objective. All compared arms must use the same batching policy.

## Scientific comparison remains a separate freeze

Research fitting and model scoring are disabled in this data contract. A full
prefit study still requires fixed arm configurations, selection and calibration
rules, usable-target/exposure/capacity/consumed-compute comparisons, material
effect size, statistical unit and multiplicity decisions. Reversed views and
steps are correlated; model seeds and physical worlds are distinct replication
dimensions. Five seed pairs alone cannot reach a two-sided 5% exact sign-flip
threshold: the smallest p-value is `2 / 2**5 = 0.0625`.

After prescribed fitting and selection, bind real checkpoint byte hashes into
the existing acceptance plan while preserving the prefit commitments. Collect
once under evaluator-controlled isolation. Independent authorship/custody and
review remain necessary for admission; public deterministic seeds and a second
implementation by the same assistant do not satisfy them. The two closed public
studies remain closed, and language/G2 promotion does not follow from this audit.
