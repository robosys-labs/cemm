# Native set acquisition v2: fresh compositions and prospective numerical retention

Registered 2026-11-02, continuing [#22](https://github.com/robosys-labs/cemm/issues/22)
and [PR #77](https://github.com/robosys-labs/cemm/pull/77) at
`9ad9656e0f47209082556fa7f3602dc4f8ed5b54`. This is a prospective protocol, not a result.
V1 remains `SCORING_ABORTED` / `REVISE_NATIVE_SET_ACQUISITION`; its source,
criteria, checkpoints, forecasts and failure are immutable.

## Question and unchanged learning

Can the same native SET acquisition pass complete competence and retention
assessment on fresh action compositions when numerical comparison and failure
reporting are specified correctly before execution?

Keep the exact **562-parameter world**. Fit the existing **57 intervention
scalars plus 11 set-only background weights**; verify the other **494 scalars**
bitwise after every update and in serialized checkpoints. Reuse the original
ten inherited contact checkpoints, five seeds **7/11/23/37/53**, NAND and NOR.
Do not continue the v1 acquired weights or change model/inference source.

Reuse the exact **48-event observed v1 training tape**, compressed SHA256
`7fbdddbe4efd188da6f6d0c82c31010a11cabd82b3038dda4e3513260e9c793a`.
It covers all four prior/request tuples. The learning hypothesis and exposure
are unchanged: full before/action/after observations, **256 updates**, fresh
Adam at **0.02**, betas **0.9/0.999**, epsilon **1e-8**, no weight decay, clip
**1.0** after masking, **180 CPU seconds per fit**. No gold roles, action-effect
formula, evaluation targets or language labels enter fitting. No seed selection,
early stopping, extra updates or research retries.

## New challenge, bounded novelty

Evaluation seed **20261102182** supplies fresh opaque identities and three
five-action templates. Let `S(A,v)` request a bit at A and `C(A,B)` be a contact:

| Family | Sequence |
|---|---|
| Interleaved sets | S(A,v), S(B,1−v), S(A,1−v), S(C,v), S(B,v) |
| Rotating sets | S(A,v), S(B,1−v), S(C,v), S(A,1−v), S(C,1−v) |
| Contact/set feedback | C(A,B), S(B,v), C(B,C), S(C,1−v), C(C,A) |

Use three through six entities, all eight first-three-bit anchors, both requests
and deterministically seeded spectator bits. Contact sequences have both
persistent hidden modes and complete reversal pairs. Set-only sequences avoid
duplicated mode/reversal views. Each law has **384 episodes / 1,920 predictions**,
**1,664 identifiable / 256 ambiguous** predictions and **128 role pairs**.

Audit canonical templates, blueprints and identity overlap against the training
tape and both-law opened SET-v1, multisource-law-v1 and hidden-cycle-v1 observed
banks. All overlaps must be zero. Renaming entities or reversing all contacts
does not evade the canonical audit. Novelty is limited to the checked identities
and compositions; atomic SET outcomes and contact laws are familiar. These are
dependent views, and full observed-prefix feedback is supplied. No autonomous
rollout or independent challenge-custody claim follows.

The original table-based prefix oracle and separately expressed Boolean
simulator are reused. `set-acquisition-v1-information` remains the unchanged
record-schema ABI; v2 source, law, data and protocol digests identify this study.

## Native criteria and controls

Reuse the exact v1 native scorer and every threshold. Every law/seed must have
complete coverage, at least 95% identifiable full-world accuracy, zero unsupported
MAP worlds, zero known-fixed-coordinate errors, correct identifiable trajectory
and role-pair conjunctions, and zero identifiable regressions against its parent.
The zero-unsupported-world condition effectively requires exact singleton
correctness. Each nonempty family/information stratum must have mean oracle KL
at most **0.05 nats**; ambiguous total variation must be at most **0.1**.
Each nonempty SET family/entity-count/prior/request/changed cell must have NLL
at most **0.05**, with changed-SET mean gain at least **0.1 nats** against both
the parent and no-change controls. Training NLL must be at most **0.05**.

All arms receive identical realized observations/actions. No-change is computed
once per law and shared across seed labels. Preserve infinity, ambiguous actual
errors, individual probability changes, repairs, regressions and all subgroup
results. No clipping, support truncation or matched-consumed-compute claim.

## Prospective numerical retention

Retain the **unchanged 88-parameter coordinate encoder** and compare **131,520
canonical forecasts** across six opened language banks with their archived
accepted coordinate forecasts. Historical reference models are not rerun.

Freeze separate **absolute log-probability bounds of 1e-10** for both world and
order distributions, with **no relative tolerance**. The world bound is
unchanged; applying this numerical standard to the order head is a prospective
v2 revision informed by v1's failure. It cannot reclassify v1. For finite logs,
the bound confines each probability ratio to `exp(±1e-10)`.

Language tensor fingerprints remain exact. Both the selected world and selected
order must remain **exactly identical**, using the first maximizing index.
Even a near-tie decision flip inside the numerical bound fails. Preserve zero
correctness regressions as a separate check. Retain every numerical difference,
MAP change, exact-equality count and adverse NLL delta.

Equal negative infinities have zero distance. Finite versus negative infinity
has infinite distance and fails. Both infinite NLLs give an explicitly undefined
delta; means are computed separately. JSON never contains NaN or clipped loss.

## Integrity, runtime and complete reporting

Malformed distributions, invalid or missing records, changed source/data/weights,
forbidden tensor updates and invalid runtime/publication provenance are integrity
errors and stop execution. Valid scientific failures are completed failed checks:
all **ten native reports and sixty retention cells** must be saved, followed by
`REVISE_NATIVE_SET_ACQUISITION`. No broad exception catch converts corrupted
evidence into a scientific result. Synthetic tests cover a failed first bank
followed by complete remaining reports, numerical boundaries, infinities and
near-tie behavior.

Pin Python **3.13.16**, PyTorch **2.10.0+cpu**, NumPy **2.3.5**, float64,
one intra-op and one inter-op thread and deterministic algorithms. Before fitting,
freeze a richer receipt: Python build/compiler, CPU model/flags/capability,
libc/kernel, PyTorch build and parallel backend, floating-point properties and
an explicit allowlist of numerical environment variables. Require exact receipt
equality during fitting, collection and scoring; bind it into every trace.
This improves reproducibility diagnosis without proving the cause of v1's drift.

Publish source/protocol/runtime/data before fitting, actual weights before
collection, and every **189,120 planned forecast** before scoring. Use clean
published checkouts and exclusive stage output paths. The scorer binds the
published raw-forecast commit. Same-team hashes and review are not independent
custody. Record execution costs and inclusive source/test size honestly.

Only a complete pass yields `KEEP_NATIVE_SET_ACQUISITION` and permits the next
separately frozen effect-and-role language study. The 88-parameter language
target remains prospective. Accepted coordinate transfer and G1/G2 development
readiness remain intact; full G3, independent scientific admission and G4 remain
open. No new neural parameters, semantic operators or production path are added.
