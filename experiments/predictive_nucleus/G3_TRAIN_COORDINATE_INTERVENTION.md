# G3 intervention on fitted lexical coordinates

Frozen diagnostic on the existing G3 v3 TRAIN tape. The question is whether each stored coordinate affects the probability of an observed endpoint through the corresponding action marginal. The prior comparison masked the entire word. Synthetic tests checked the factorization on constructed weights.

Use the published G3 v3 source and inputs at `2c5cdbe2` and grounded fits at `66a74921`. Read the 16 teaching events in `data/effect-role-v3/teach-inputs.json.xz`, the lexical registry, and the matching NAND world and grounded checkpoint for each seed (7, 11, 23, 37, 53). Keep both identities, all 16 rows, their original physical contexts and the four supplied action candidates. Eight distinct text strings recur across the 16 contexts. The five fits share this tape.

For each frozen fit, score four conditions in order. First use the saved parameters. Then set the effect column of both new identity rows to zero, leaving role intact. Restore the rows and set only their role column to zero. Finally restore both columns. Reuse the same packed observed inputs and frozen world in every condition. No fitting, parser labels, challenge data or new cases enter this diagnostic.

Record the mean observed endpoint NLL per condition and each intervention's paired NLL change per seed. Record the count of rows with higher/equal/lower NLL (absolute tolerance `1e-12`). Separately check the maximum absolute change in the unaffected action marginal across rows (role under effect ablation, family under role ablation). Check the ablated marginal returns to 0.5 and report its maximum absolute change from intact. Use the existing float64 model and native forecast path. Reject a comparison if any mean is nonfinite, a count differs from 16, intact mean NLL differs from the published TRAIN objective by more than `1e-10`, a marginal invariant differs by more than `1e-12`, or restored predictions or model fingerprints differ from intact.

Report all directions, including zeros and improvements after ablation. An endpoint cost measures dependence on the fitted coordinate on the teaching examples. The factorization and action menu are supplied. G3 development status and scientific admission do not depend on this diagnostic.

## Recorded result on November 6

Protocol commit `c2fddad` preceded execution. All five fitted NAND worlds and all 16 teaching records were included. The [native driver](g3_train_coordinate_intervention.py) verifies the training receipt, checkpoint hashes and physical-world fingerprint before evaluation. Results reproduced exactly on Python 3.13.5 / PyTorch 2.10.0+cpu / NumPy 2.3.5 after an initial Python 3.12.14 run.

| Condition | Mean observed endpoint NLL | Higher / equal / lower NLL across 80 paired seed-row comparisons |
|---|---:|---:|
| Intact saved coordinates | 0.0413431 | Reference |
| Effect coordinate zeroed | 0.5220358 | 68 / 0 / 12 |
| Role coordinate zeroed | 0.3743883 | 40 / 40 / 0 |
| Both coordinates restored | 0.0413431 | 0 / 80 / 0 |

Each intact objective equals its archived training objective exactly. Restoring both coordinates reproduces all forecasts and model fingerprints exactly. The largest change in the orthogonal action marginal was 2.22e−16. Removing each fitted coordinate increases the mean endpoint loss on every seed. The five fits share the same teaching tape.

Post-score inspection found eight teaching lineages, each replayed in two distinct physical histories. All 16 complete records differ even after canonical participant renaming. All 40 role-insensitive comparisons belong to the eight all-ones examples, where either participant produces the same observed endpoint. The other eight examples change a bit, and every role ablation raises their loss. Twelve effect-ablation improvements occur in four bit-changing contexts across seeds 7, 37 and 53. Each improvement is smaller than 0.00023 NLL. In those contexts the frozen CONTACT mixture assigns slightly greater likelihood to the endpoint than the SET mixture.

The result establishes use of the fitted effect and role coordinates on observed teaching data within the supplied action structure. Each new lexical identity owns a separate parameter row, and both words were taught the same operation. All five fits contain equal rows for those two identities. Shared-operation discovery and reuse across distinct operations remain open.

Reproduce with `python -m experiments.predictive_nucleus.g3_train_coordinate_intervention`. [Per-seed results](results/g3-train-coordinate-intervention.json).
