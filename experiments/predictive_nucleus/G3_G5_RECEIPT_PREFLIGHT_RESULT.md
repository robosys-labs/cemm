# G3 physical receipt preflight result

The frozen protocol ran on November 6 with Python 3.13.5 and PyTorch 2.10.0+cpu. All 16 TRAIN episodes were retained for each of five frozen NAND worlds, giving 80 dependent model-row measurements. Two complete invocations produced byte-identical output. The three synthetic prefix guards passed. Every current-endpoint complement preserved the delivered prefix, native prior state, language features, candidate actions and candidate likelihoods. [Protocol](G3_G5_RECEIPT_PREFLIGHT.md) · [All recorded measurements](results/g3-g5-receipt-preflight.json).

Each event retains its evidence ID, prefix digest, four physical action tuples, full endpoint distributions, observed likelihoods and all six pairwise total-variation distances. The data support one conditional likelihood vector per physical answer in a future G5 study. Candidate alignment across different utterances remains a separate requirement.

| Frozen world seed | Range of largest single-receipt posterior | SET-pair TV on the eight all-ones rows |
|---|---:|---:|
| 7 | .499699–.499985 | .00051247 |
| 11 | .499486–.499768 | .00047844 |
| 23 | .499629–.499729 | .00050616 |
| 37 | .499438–.499774 | .00094959 |
| 53 | .499451–.499766 | .00059625 |

The posterior uses equal initial weight for each of the four event-local candidates. Every single observed endpoint leaves the two highest candidates nearly tied. The largest best-to-second likelihood ratio across all 80 rows is 1.000572. A physical endpoint therefore cannot be treated as a perfect semantic answer in these examples.

At the frozen numerical tolerance of 1e−10, zero candidate pairs have equal predicted distributions. The table shows the relevant limitation. Even the physically role-insensitive all-ones examples receive slightly different learned SET distributions. Small prediction differences require calibration against physical evidence before being used as evidence of identifiability. The tolerance qualifies numerical equality only.

This preflight establishes the event-local receipt interface and exposes ambiguity in the actual teaching data. Learned retention through restart, query savings, cross-layout alignment and fresh-identity transfer require the next prospective study. The available eight exact utterance pairs have different physical histories and matching physical action tuples, which permit a bounded follow-on check of how much a second observation resolves.

Reproduce with `python -m experiments.predictive_nucleus.g3_g5_receipt_preflight`. Run the delivered-order and label-exclusion guards with `python -m unittest experiments.predictive_nucleus.tests.test_g3_g5_receipt_preflight`.
