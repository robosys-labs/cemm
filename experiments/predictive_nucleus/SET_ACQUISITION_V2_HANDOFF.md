# Native set acquisition v2 — publication handoff

Updated 2026-11-02. **Implemented and locally frozen; zero research fits,
collections or scores.** The preceding v1 run remains unaccepted. This file is
an execution handoff, not a result or a change to the frozen protocol.

## Reviewable change

Initial local freeze commit: `c3fed8193e619c275229d65a41825ceae876b64c`.
Branch: `research/predictive-nucleus-set-retention-v2-20261102`, based on
`9ad9656e0f47209082556fa7f3602dc4f8ed5b54` / existing draft PR #77.
Destination: the **public** `https://github.com/robosys-labs/cemm` repository.
No force push or main-branch mutation is planned.

[Study](SET_ACQUISITION_STUDY_V2.md) · [protocol](set_acquisition_protocol_v2.json) ·
[runner](set_acquisition_run_v2.py) · [retention](set_acquisition_retention_v2.py) ·
[data recipe](set_acquisition_data_v2.py) · [saved-record auditor](audit_set_acquisition_v2.py).

The exact source/data/runtime freeze has SHA256
`fff7bdc0423ddf46840473c29a4852d3e95e23a23541949d0639754204f8f807`.
The later auditor is an independent arithmetic check and is outside that frozen
execution source list; it does not replace the original scorer.

## Actual blocker

Automatic approval review rejected the public branch push twice. The second
review still required trusted end-user approval for this payload and destination,
despite verified connected-user admin/push permissions and an inspected payload
containing only isolated research source/tests and deterministic synthetic
binary-world episodes. No push succeeded and no draft PR for v2 was created.

Request explicit approval to publish these changes and this v2 study's subsequent
checkpoints/results to the named public research repository and to maintain its
draft PR. Do not switch publishing channels to bypass the rejection. The user's
approval then applies to that bounded continuation. Until it is provided, keep
the publication-before-fitting gate intact.

## Work already complete

- Frozen v1 source, data, checkpoints, forecast archives and failure are preserved.
- V2 keeps the same 562 parameters, 68-scalar update mask, 48-event observed tape,
  five seeds, two laws, 256 updates and native scientific thresholds.
- Fresh interleaved, rotating and contact/SET feedback compositions pass canonical
  overlap checks against training and the explicitly named opened native banks.
- Both world/order logs use prospective absolute 1e-10 bounds. Exact tensor and
  MAP checks remain; valid failed criteria produce complete reports.
- The full numerical runtime is frozen and checked at every execution stage.
- Synthetic pipeline tests verify completed failures, malformed-evidence stops,
  numerical boundaries, near-tie flips, infinities and runtime/recipe integrity.
- The stdlib auditor passes 6,620 synthetic arithmetic comparisons and verifies
  an input-only pre-score path. These are software checks, not research results.

## Authorized sequence after publication approval

Use `/tmp/cemm-venv/bin/python` with `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `PYTHONHASHSEED=0`. The frozen runtime is Python
3.13.16, PyTorch 2.10.0+cpu and NumPy 2.3.5; verify the complete runtime receipt.

1. Publish the local source/data/runtime changes and verify remote commit/tree
   equality. Open a draft PR stacked on #77. Check the complete isolated suite,
   original protocol, all 34 locks and frozen-input preflight.
2. Run `set_acquisition_run_v2 fit` once, using `data/set-acquisition-v2`, output
   `data/set-acquisition-fit-v2` and the verified source-publication commit.
3. Verify and publish all ten actual checkpoints before collection.
4. Run `set_acquisition_run_v2 collect` once into
   `results/set-acquisition-v2/traces`, bound to the verified weights commit.
5. Publish all 189,120 planned forecasts. Run
   `audit_set_acquisition_v2 --pre-score` with `--repo` set to the checkout and
   an exclusive `--output` JSON path. Require a complete valid inventory before
   parsing evaluation targets. Its evaluator-file hashes are opaque byte checks.
6. Run `set_acquisition_run_v2 score` once into
   `results/set-acquisition-v2/scored`, passing the verified raw-publication SHA.
7. Run the auditor without `--pre-score` against saved raw and scored records.
   Preserve all failed checks, adverse probability changes and exact regressions.
8. Publish the honest KEEP/REVISE/STOP result, source-size/cost accounting,
   checkpoint/forecast chronology and updated roadmap/issue/PR status.

The stage runner is invoked as `python -m experiments.predictive_nucleus.set_acquisition_run_v2`;
its `--help` lists path arguments. No execution output path currently exists for
fitting, collection or scoring. Do not retry after opening the new challenge.

## Deferred next capability

Only a native acquisition pass unlocks effect-and-role language learning.
Static review shows that current language candidates contain two contact orders.
The smallest direct extension supplies four word-independent alternatives:
contact(A,B), contact(B,A), set(A,1), set(B,1). Widening the bilinear head from two
to four outputs adds four parameters, for 92 total; keeping 88 would require a
different parameter-sharing design and is not established.

Under NAND, a single endpoint may not identify SET(A,1) uniquely: a contact can
produce the same change, and setting an already-lit entity can be indistinguishable
from another no-change action. The future loss must marginalize observationally
equivalent actions and learn from contrasting contexts, without gold action-kind
or participant-order labels. This is a design finding, not an implemented model.

G1/G2 development readiness and accepted coordinate transfer remain intact.
Full G3, G4, independent scientific admission and the 2,000-line goal remain open.

## Verified local code

Clean-checkout source `a784795b97cc05a2002e95f27e088e8999b40e4b` passes all **1,013 tests** in
**137.553 seconds**, all **34 locks**, the original protocol and frozen preflight.
[Machine-readable validation](results/set-acquisition-validation-v2.json) retains
the test log and preflight receipt. No v2 scientific result exists.
