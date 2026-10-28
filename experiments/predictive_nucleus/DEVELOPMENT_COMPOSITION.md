# Public one-pair to two-pair diagnostic

**OPEN DEVELOPMENT ONLY; G1 NOT RUN.** This run is intended to expose
specific prediction failures in already-public fixtures, not establish
independent generalization or an architectural advantage. The G1 roadmap
still requires matched-example and compute controls, reviewed provenance and
an independently authored and held challenge. No G0 challenge is opened.

The v2 [development protocol](dev_composition_protocol_v2.json) and its
SHA-256 lock were committed before fitting or scoring. V1 remains in history
but was not run; v2 clarifies that the observed overlap groups contact and set
samples by type, not their full chronological order. The plan trains on both
32-case public one-pair blocks with a declared, noiseless observe(A,B) action
inserted after the first contact. It evaluates all five actions of the open
64-case two-pair block. Both models use 200 Adam updates at each of five model
seeds; no calibration or model selection is performed. The structured model,
flat GRU, persistence control and frozen local-event table plus persistence
receive copies of each case's same realized history. The oracle scores only
after their forecasts; process isolation and independent custody are not
established.

Report every case and action, with separate contact/set and observe strata.
Joint MAP uses a fixed sorted-ID tie break; Brier is summed over all eight
three-bit worlds. Abstention is excluded from conditional scoring and included
in coverage and per-query denominators. A represented zero has infinite
uncapped log loss, recorded explicitly rather than silently floored. The
legacy clipped value is labeled separately. Per-step structured feedback
status and likelihood show when the filter retained an unconditioned forecast.

The evaluation factorial shares identities within a block and is reused
across seeds. All action-local contact and set tuples appear in training; eight
evaluation cases share the same ordered contact list and ordered set list
after grouping by type. Their chronological action order is different. This
does not imply bitwise equality of flat inputs. The flat model sees sorted-ID
operand ranks in evaluation that are absent in training; observation order,
sensor geometry, objectives and actual compute also differ. The structured
model supplies exact belief and persistence machinery, two-mode symmetry and
a numerical cache from its learned weights. It is not an unbiased comparison.

An information limit can be checked directly on the public fixture before
any model fit: grouping its 64 first turns by the complete initial observation
and first action yields eight input groups, whose majority outcomes total
40/64. This is the maximum exact first-contact accuracy for a deterministic
predictor reset for each case and restricted to that input, without access to
the evaluator, case index or future records. It is a property of this public
factorial, not a result for the historical generator or the G1 gate. These
ambiguous cases remain in all reported denominators.

The no-op observation in training repeats an existing noiseless reading and
is not independent sensor evidence. Sixteen flat input columns remain zero
throughout training, so 336 of 1,457 flat parameters receive no data gradient;
their weights are checked against initialization. The observe feature is
present in training, and its weight changes are reported. Resource timings,
input/weight hashes and hardware details aid reproduction but do not establish
matched FLOPs or cross-machine determinism. The experimental Python tree has
9,224 physical lines across 63 files including tests, above the roadmap's
practical 2,000-line target; do not remove correctness evidence to conceal it.
