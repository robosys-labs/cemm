# G5 temporal observation support — completed, with a reuse limit

PR #100's frozen enumeration is complete: **KEEP_TEMPORAL_OBSERVATION_PREFLIGHT**.
Its original result and criteria are preserved. Both published invocations of
source `94eaddd1bb07a58247660909b958158dbd7ddd67` produced the same compressed
566,520-byte report, SHA-256
`3c7ecfe48708cad5dd1450c971876bc426114fd87002ffb4ac19f22c2486aaad`.
The [repetition receipt](results/temporal-observability-v1/replication.json)
retains both runs and their execution costs. Do not rerun this completed
enumeration or the completed transformed-frame persistence qualification
without a concrete new defect.

## What the original result establishes

All 1,536 constructed worlds survive in 128 original contexts and 288 groups
conditioned on the actual report. The calculation pools proposed operations
with identical observable histories; it does not disclose a private old/new
pair to the decision calculation. It cross-checks 4,096 physical endpoints,
511,488 question-value formulas, 13,824 renamings and 49,504 replay branches.
No registered invariant fails.

With the original measurement available, 192 groups identify the temporal
cause and 96 preserve ambiguity. Losing that measurement leaves cause ambiguity
in all 288 groups. The next target can nevertheless be predictable: identifying
a cause and predicting an endpoint are different questions.

This is an exact analysis of a supplied finite environment, not a trained
learner, independently sampled replication or G5 admission. Original-run CPU
costs were 82.277 and 80.791 seconds; peak RSS was 442,560 and 442,536 KiB.

## Why this did not yet establish reusable learning

Each original menu includes a physical probe with the target's own scope and
initial state. Its endpoint column is identical to the target column. Different
event IDs alone therefore do not establish reuse across different inputs.
Removing only the exact three-bit state is also insufficient: the third entity
is untouched, so toggling its bit leaves the interacting pair unchanged.

The new [saved-record audit](temporal_reuse_audit_v1.py) excludes any observation
whose first two active input bits match the target, in both scopes and in
historical verification. The filter uses public input descriptors only, never
hidden operations or endpoint equality. This is explicitly a **post hoc audit
of an opened bank**, not a fresh challenge. It neither fits a model nor changes
the original decision.

## Attainable limits after excluding matching inputs

Immediate and lost-measurement menus have the same target limits. Weighting is
by the 12 original counterfactual worlds, not equally by the differently sized
post-report groups.

| Information available | Exact population-weighted accuracy ceiling |
|---|---:|
| Report-conditioned prior only | 23/32 = 71.875% |
| Best one observation | 495/512 = 96.6796875% |
| Best fixed pair of distinct observations | 249/256 = 97.265625% |
| Complete permitted menu | 249/256 = 97.265625% |

Per menu, 1,088 group/target cells need no observation, 2,976 need one, 96 need
two, and **448 cannot be identified even from the complete permitted menu**.
These are dependent cells; their population weights are 17/96, 131/192, 1/32
and 7/64 respectively. The two-observation result is nonadaptive.

All partitions and unresolved witness pairs remain in the
[complete audit](results/temporal-reuse-audit-v1/audit.json.xz). A concrete
counterexample is NAND with ordinary first-to-second contact, original `000`,
reported `010`, and local target `110`. Contact and SET(second=1) coincide at
every permitted active input; the target remains 50:50 between `100` and `110`.
No additional training can resolve that particular missing evidence.

At fee .05 the exact best-one reference asks on 145/192 of the population,
achieves 495/512 correctness and 1427/1536 net reward. Prohibitive or unavailable
questions produce no purchase. These are evaluator reference limits, not
learned-policy measurements.

## The executable continuation

The [native temporal updater protocol](TEMPORAL_NATIVE_TRANSFER_PROTOCOL_V1.md)
freezes one small learned comparison, five seeds and 256 updates per arm.
It uses identical realized histories, a native-mixture decoder, a similarly
sized flat decoder, an omitted-first-answer control and a clearly labeled
supplied four-way rule. Its fixed question schedule gets its own conditional
ceiling; the full-menu ceiling above is not substituted for that schedule.

The publication freeze is `0bdb45172f85b755c7916907cefbcd30f21766ed`. It has
the same tree as local freeze `59247d8e`; connected GitHub publication was used
after prior repository authorization was verified and the local checkout was
found to lack Git credentials. The completed PR #99 evidence and PR #100
observability artifacts now coexist on one continuation branch.

There is no further general task-design or persistence prerequisite. Finish
this one fixed-budget learner comparison, save its outcome, and make the next
decision from that evidence. Full G5, G6–G8 and the inclusive 2,000-line
objective remain open; production runtime, authority and ABIs are unchanged.
