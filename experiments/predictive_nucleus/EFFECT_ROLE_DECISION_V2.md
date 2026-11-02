# G3 probability normalization v2 — incomplete evidence

**Status: `STOP_INCOMPLETE_EVIDENCE`. Development G3 remains open.** All 15
planned fits survive in the public repository, but the original raw collection
was lost before publication. No v2 target scoring or full saved-record audit
occurred. There is no v2 scientific pass/fail decision: neither
`REVISE_EFFECT_ROLE_GROUNDING` nor a G3 pass is supported by this incomplete
record. The completed v1 REVISE decision remains unchanged.

[Interruption receipt](results/effect-role-interruption-v2.json) ·
[surviving training receipt](data/effect-role-fit-v2/training.json) ·
[frozen study](EFFECT_ROLE_STUDY_V2.md) · [protocol](effect_role_protocol_v2.json) ·
[continuation handoff](EFFECT_ROLE_HANDOFF_V2.md).

## Surviving evidence

Source/data publication:
[`26d8d54ab0748e70d8981acc14e6351a5a279ab1`](https://github.com/robosys-labs/cemm/commit/26d8d54ab0748e70d8981acc14e6351a5a279ab1).
Actual weights publication:
[`30880caf676c10773857221d9d5bc2437651fb6f`](https://github.com/robosys-labs/cemm/commit/30880caf676c10773857221d9d5bc2437651fb6f).
Freeze: `be204b7a610a892ce0f62a83f8144159512f36d29da0339eb12591c4a8f73a4a`.

The five seeds each completed grounded, supervised-parser and text-only fits
once, with 256 updates, the same 16 teaching and 1,152 rehearsal events, and
92/92/1,048 language parameters. Actual checkpoint bytes, final objectives and
learning curves remain published. The original training receipt records all
native worlds unchanged and exact v1 reproduction of every text-only checkpoint
and non-resource training report, including its curve. This package rechecks
those saved byte/report equalities without model execution. The equality receipt
is scoped to the original runtime; it does not establish new-runtime reproduction.

| Grounded seed | Final teaching NLL | Final rehearsal NLL |
| --- | --- | --- |
| 7 | 0.512492329 | 0.263864946 |
| 11 | 0.513953624 | 0.265964793 |
| 23 | 0.005194265 | 0.033929270 |
| 37 | 0.007890211 | 0.037878356 |
| 53 | 0.007959858 | 0.038471522 |

These are TRAIN objectives. Seeds 7 and 11 motivate concern and future hypotheses;
they do not establish a challenge failure. The surviving checkpoints alone cannot
substitute for the missing frozen challenge evidence.

## Lost collection and execution stop

The original collection reported completion of 101 artifacts: 100 trace files
plus the lexical-identity receipt. Including its attempt and manifest, the
reported inventory was **103 files / 32,162,048 bytes**. The recorded intended
raw Git tree is **`c5df023722a4843ff62096d5cd8a0aa83f065cbb`**. The frozen protocol
planned 546,240 rows: 276,480 fresh/control, 131,520 historical-retention and
138,240 opened-v1 rows. The lost raw bytes cannot now be checked against that
inventory or those row counts.

The publication wait was interrupted after five hours, followed by loss of the
scratch workspace and temporary files. The public branch remained at the weights
commit; the publication lookup for the recorded tree returned HTTP 404. The
original raw commitment remains unrecovered. A recorded tree identifier and
session completion report are not a published, inspectable raw evidence bank.

Restoration recovered Python 3.13.16, PyTorch 2.10.0+cpu and NumPy 2.3.5, but the
CPU changed from Intel Xeon Platinum 8573C to AMD EPYC 9V74. The original frozen
runtime guard rejected the restored environment **before predictions**. No
replacement collection, replay, additional fit or v2 scoring occurred. Unpublished
recovery proposals do not constitute executed research. This package changes no
frozen source, data, protocol, checkpoint, numerical threshold or runtime guard.

| Stage | CPU seconds | Wall seconds | Peak RSS (KiB) | Evidence status |
| --- | --- | --- | --- | --- |
| training | 82.318406338 | 82.33598428299956 | 367960 | Published training receipt |
| original collection | 401.62604972400004 | 404.48114579299727 | 502448 | Session-reported; raw receipt lost |
| scoring / full saved-record audit | — | — | — | Not executed |

The five-hour publication wait is separate from these measured research-stage
costs. Collection costs are retained as reported costs, not reverified telemetry.
There is no complete audited v2 execution total or scored headline.

## Next prospective tranche

The next candidate separates effect-family uncertainty from participant-role
confidence through exact lexical identities. It retains the entire accepted
88-parameter coordinate parent as protected state and adds two neutral learned
coordinates for each of two new identities: an effect logit and a role coordinate.
That is **92 total parameters: 88 frozen, four learned**, with all four new values
initialized to zero. Legacy identities keep the inherited contact distribution;
new identities initially distribute probability equally across the four supplied
actions. Endpoints supply grounded supervision. Unregistered raw tokens retain
distinct unresolved identities and receive no semantic prediction.

This is a new hypothesis, not a repaired v2 result. It requires a new source/data
publication and an explicit AMD runtime freeze before research execution. Freeze
fresh compositions, current-runtime controls and evaluation of the published v2
weights as a reference under that same new runtime. Such reference forecasts
belong to the new study; they cannot reconstruct or close this v2 attempt.
Previously presented compositions remain opened evidence if reused. Preserve the
same TRAIN tapes, five seeds, 256-update budget, all original G3 gates and complete
adverse retention reporting.

The protected complement gives a structural legacy-retention invariant; it does
not demonstrate learning to resist forgetting. Per-identity storage growth is
explicit, with no claim of shared-parameter lexical learning, zero-shot word
meaning or unrestricted polysemy. The complete next protocol and actual saved
evidence must establish whether this bounded candidate satisfies development G3.

## Retained decisions and limits

Accepted G1/G2 development results, coordinate transfer and native SET v2 remain
intact. [Effect/role v1](EFFECT_ROLE_DECISION_V1.md) remains a completed scientific
REVISE in all ten conditions. G3 remains open and G4 is not unlocked. Independent
custody, matched consumed compute, general calibration, the 2,000-line objective
and formal scientific admission remain unresolved. Production runtime, semantic
authority and ABIs are unchanged.
