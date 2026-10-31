# G3: lexical direction from observed consequences

Tracking: [roadmap #22](https://github.com/robosys-labs/cemm/issues/22).
Parent: [bilingual role binding, PR #68](https://github.com/robosys-labs/cemm/pull/68),
commit `02500ffe5d310364142ca6cecfcde14e83b8e827`.
Prepared 31 October 2026 (Africa/Lagos). **Implemented; not fitted or evaluated.**

## Roadmap alignment

The acquired world, coherent joint predictions, composition, hidden propagation
and explicit timing are retained G1/G2 development capabilities. Bilingual-v1
then established outcome-trained participant ordering. Its single relation could
be solved from identity-token positions, so it did not establish lexical meaning.
This tranche closes that specific gap before communication or clarification work.
Formal scientific admission and historical failed decisions remain unchanged.

The same **474-parameter neural encoder** now has to use a word to distinguish two
different consequences at identical name positions. Its two probabilities enter
the existing **562-parameter learned world**, with a shared mode/world mixture.
No new neural layer, parameter, action kind, world physics, parser or workspace
is introduced. Frozen bilingual and native source files remain byte-identical.

The new capability is lexical selection of an acquired **directed contact**.
The two legal action alternatives, token/event boundaries and exact roster
identity linkage are supplied. The network does not invent those alternatives.
The generator defines the controlled lexicon, but candidate inference contains
no literal-word dispatch or gold linguistic participant-order mapping.

## Contrast and structural test

| Fixed layout | Direct usage | Inverse usage |
|---|---|---|
| English-like SVO | `Ada contacts Ben` / `Ada touches Ben` | `Ada receives Ben` / `Ada accepts Ben` |
| Artificial OSV | `Ben Ada dax` / `Ben Ada mip` | `Ben Ada vok` / `Ben Ada nuz` |

Direct usage denotes native `contact(Ada, Ben)`; inverse usage denotes
`contact(Ben, Ada)`. These are declared controlled-language meanings. Each final
lexical pair shares the complete observed history, names and token positions.
Only the final lexical item differs; the two complete-world outcomes differ.
The shared three-to-five-contact prefix alternates direct/inverse meanings.

A second, small test addresses structural recombination. Teach
`contacts/receives` and `dax/vok` in **both layouts** through observed outcomes.
Teach `touches/accepts` only in SVO and `mip/nuz` only in OSV. At the final probe,
replace the word with its same-meaning counterpart from the other lexicon while
keeping the layout fixed. The first set supplies a seen-combination control;
the second tests **word × layout combinations absent from training**. Use
`contrast_synonym`, the actual final token's variant, to separate these strata.

The structural result is reported separately from the primary lexical decision.
A lexical success cannot stand in for a failed composition result. Conversely,
a structural failure does not erase an established fixed-order lexical gain.
Neither outcome establishes general language comprehension, invented operators,
an internal symbolic representation or architecture superiority.

## Fitting and evidence boundaries

Five language encoders start from their successful bilingual-v1 grounded
checkpoints, published at `2db941c2dd4fed97d0b5cef718b24f17ba88bb39`.
All ten world checkpoints from `25ae19b317c5b7dbfc487fa5204fb5da5f0e7420`
remain frozen. Fit only on NAND; transfer each resulting encoder unchanged to NOR.
Adam starts with fresh optimizer state; this is weight continuation, not optimizer
resume. No teacher logits or stored predictions enter fitting.

| Training evidence | Episodes | Observed text outcomes |
|---|---:|---:|
| Exact original training rehearsal | 256 | 384 |
| Fresh atomic lexical examples, including 128 shared-word examples | 384 | 384 |
| Total per update | 640 | 768 |

The objective is the mean complete-world NLL over all 768 observed outcomes.
Fresh direct/inverse evidence is balanced 192:192. The old examples are all
direct, making total semantic exposure **576 direct:192 inverse**. This is
intentional retention weighting, not a globally balanced fit. The matched final
challenge prevents a position/frequency policy from passing both alternatives.
Use 256 updates, Adam learning rate .02 and gradient clip 5, exactly once for
each seed 7, 11, 23, 37 and 53. Use the final checkpoint without selection.

The learner sees words, a supplied identity roster, observed native calibration
actions and subsequent state readings. Linguistic events have **no gold order,
action-kind, language-ID or parser supervision**. Native acquisition/reset
actions remain supplied observed context. New data contain no training oracle
or parser-label artifact. Old and new challenge outcomes never enter fitting.

## Collection and controls

Each law has 1,152 fresh challenge episodes, 4,160 forecasts and 576 final lexical
pairs. Fresh names, permutations and chain/fork/cycle/repeated/disjoint families
test longer combinations after atomic lexical fitting.

The candidate computes each prefix once. Three final-only views share its exact
pre-query mode belief and native likelihoods:

- **Mask:** zero only current lexical character features. Paired effective inputs
  become identical, so both different worlds cannot be correct; balanced MAP
  accuracy is at most 50%.
- **Swap:** exchange the current direct/inverse word. This is a valid
  counterfactual message; its prediction must match the counterpart's world and
  distribution, not merely lose accuracy against the original outcome.
- **Word × layout transfer:** substitute the same-meaning counterpart from the
  other controlled lexicon. Separate seen and held-out combinations.

The unchanged old encoder forecasts the fresh bank as a baseline. Only the
updated encoder runs on the old challenge, compared against saved old forecasts.
This is explicitly an opened-bank retention measurement; historical models,
traces and decisions are not rerun or replaced.

Across both laws and five seeds, the complete collection contains **138,560
rows**: 41,600 candidate, 41,600 prior, 34,560 final-only views and 20,800 retention
forecasts. The evaluator separately records 41,600 gold-action native references.
Shared prefixes are not counted as new control forecasts. All candidate/control
traces must be durable and validate before any challenge oracle is decoded.

## Frozen decisions

The [protocol](lexical_protocol_v1.json) fixes accuracy, NLL and conjunction
requirements by family, layout, lexical polarity, law and seed. Critical true
probability must be at least .9, foil probability at most .1 and lexical separation
at least .8. Masked twin TV must be at most 1e-10; swapped vectors must match their
counterpart within the same tolerance. Require zero old-correct → new-wrong
worlds and record every probability loss separately. Structural transfer has its
own frozen seen/held-out checks and cannot be inferred from pooled accuracy.

Completed primary outcomes are `KEEP_LEXICAL_GROUNDING` or
`REVISE_LEXICAL_GROUNDING`; malformed/incomplete execution yields
`STOP_INCOMPLETE_EXECUTION`. Separately report `STRUCTURAL_TRANSFER_ESTABLISHED`
or `STRUCTURAL_TRANSFER_NOT_ESTABLISHED`. Retain all failures. No post-challenge
tuning, retries or extra G1/G2 prerequisites are permitted by this study.

## Reproduction and size

Publish source/data/protocol first; run one fit; publish all five checkpoints;
then run one collection. Output directories are exclusive.

```sh
python -m experiments.predictive_nucleus.lexical_run prepare \
  --output experiments/predictive_nucleus/data/lexical-v1
python -m experiments.predictive_nucleus.lexical_run fit \
  --data experiments/predictive_nucleus/data/lexical-v1 \
  --output experiments/predictive_nucleus/data/lexical-fit-v1
python -m experiments.predictive_nucleus.lexical_run collect \
  --data experiments/predictive_nucleus/data/lexical-v1 \
  --fitted experiments/predictive_nucleus/data/lexical-fit-v1 \
  --output experiments/predictive_nucleus/results/lexical-v1
```

Use pinned Python 3.13.16 / Torch 2.10.0+cpu / NumPy 2.3.5, one numerical thread
and deterministic algorithms. Runtime, checkpoints, all reused sources and
historical retention inputs/outputs are bound by hashes. Report cache construction
once, forecast costs separately and batch-amortized latency without implying
single-request latency. Report exact added source/test lines and retained total;
the program's inclusive 2,000-line objective remains unmet. The implementation
reuses the frozen model and scoring primitives rather than adding a second model.
