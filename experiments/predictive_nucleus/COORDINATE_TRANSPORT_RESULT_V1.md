# G5 learned-coordinate transport result v1

## Decision

**`KEEP_TRANSPORT_PREFLIGHT`**. All 80 condition gates passed, with zero
collection failures and zero scoring-validation errors. The qualification
uses the two existing acquired words and four supplied sign transformations
of their saved learned effect/role coordinates. The learned layout map and
native physical forecasts transport evidence across fresh participant
instances. The frozen protocol defines this static scope.
[Protocol](COORDINATE_TRANSPORT_PROTOCOL_V1.md)

Scientific G5 admission is **`NOT_ADMITTED`**. The retained development
baseline is the v1 scoped evidence rule. Temporal/scope correction,
transformed-frame persistence and a prospectively matched unstructured fit
are subsequent requirements.

## Publication and repetition

| Stage | Published commit |
|---|---|
| Protocol before implementation | `97ff1f00ed8f3f3ca330ea14f566bdc87a4d9028` |
| Implementation before preparation | `64a3b038e2002d4c21594533057ebe1b0b8866ba` |
| Prepared public inputs and separate evaluator | `6a56dd29d037c193a636d6996479300c3992cf2b` |
| Raw forecasts and repetition receipt before scoring | `da935850230e46a8c2c128a595479e58f087213e` |

Both complete native invocations ran at the prepared-data commit. All ten
compressed shards matched byte-for-byte, totaling **7,026,416 bytes**.
Separate invocation IDs and execution receipts identify the two runs.
The collector verified the evaluator's published Git-blob hash and used
public prefixes and demonstration endpoints for inference. Evaluator truth
was parsed by the scoring stage after raw publication.
[Native repetition receipt](results/coordinate-transport-v1/raw/replication.json)

Two complete scoring runs at the raw-publication commit also matched
byte-for-byte. The compressed score is **1,564,192 bytes**, with SHA-256
`c1bc1d7fbc2f406ef2604f00d3180861e0b4722f37c2ddc2f2accf5c518b4129`.
[Scored evidence](results/coordinate-transport-v1/scored.json.xz)

The finite counterbalanced bank contains **1,536 distinct trials**, **4,608
instances** and **13,824 unique participants**. Every fitted seed receives
the same bank. Participant and episode overlap with historical teaching and
rehearsal is zero. Across five fits and three mapping views, the retained
inventory comprises **69,120 projection receipts**, **276,480 hypothesis
distributions**, **92,160 target predictions** and **138,240 priced policies**.
[Data audit](data/coordinate-transport-v1/audit.json)

## Frozen condition gates

Every law/seed condition has **768/768 correct target endpoints** and
**768/768 correct local actions** under intact retained evidence. Every
condition has zero wrong endpoints at confidence at least .95. The mean
Brier comparisons below use the same realized demonstration tape.

| Law | Seed | Intact retained | Reset | Latest only | Zero-layout retained |
|---|---:|---:|---:|---:|---:|
| NAND | 7 | .010213 | .500001 | .254798 | .500001 |
| NAND | 11 | .010586 | .500002 | .255056 | .500003 |
| NAND | 23 | .010432 | .500002 | .254969 | .500002 |
| NAND | 37 | .010425 | .500004 | .254972 | .500004 |
| NAND | 53 | .010624 | .500002 | .255050 | .500002 |
| NOR | 7 | .013923 | .625001 | .319547 | .504553 |
| NOR | 11 | .014260 | .625002 | .319744 | .504581 |
| NOR | 23 | .014159 | .625001 | .319725 | .504640 |
| NOR | 37 | .014100 | .625003 | .319645 | .504582 |
| NOR | 53 | .014285 | .625002 | .319726 | .504570 |

The following balanced averages summarize 7,680 target predictions per row.
All 120 law/seed/view/evidence groups and their calibration bins are retained
in the scored artifact.

| Mapping and evidence | Endpoint accuracy | Action accuracy | Mean Brier | Mean NLL | Mean condition ECE |
|---|---:|---:|---:|---:|---:|
| Intact, reset | 50.000% | 25.000% | .562502 | .868056 | .000789 |
| Intact, first only | 71.875% | 62.500% | .287325 | .431489 | .028420 |
| Intact, latest only | 71.875% | 62.500% | .287323 | .431489 | .028414 |
| Intact, retained | 100.000% | 100.000% | .012301 | .072559 | .068927 |
| Zero layout, retained | 50.000% | 50.000% | .502294 | .719780 | .000743 |
| Cycled layout, retained | 33.542% | 33.750% | 1.098835 | 2.315680 | .568060 |

Intact retained mean conditional-oracle KL is **.072559 nats**. Its .95
confidence coverage is **28.125%**, or 2,160 of 7,680 predictions. Zero
high-confidence errors coexist with residual probability calibration error.
No realized or conditional-oracle zero-probability failure occurred in any
of the 92,160 target prediction records.

Cycling the learned layout response produces **1,196 high-confidence wrong
endpoints** under retained evidence. Removing that response reduces retained
endpoint accuracy to 50%. These fixed interventions measure the contribution
of the fitted cross-layout alignment.

## Actual clarification outcomes

The optional paid observation is the second demonstration's endpoint. Its
purpose is prediction of a different target instance. Each fee branch starts
from its registered pre-query belief and consumes the second endpoint only
when purchased. At fee .05, every seed has the following results over 768
trials per law.

| Law | Prior | Paid questions | Correct target endpoints | Mean net reward |
|---|---|---:|---:|---:|
| NAND | Retained first observation | 384 | 768 | .975000 |
| NAND | Reset | 576 | 576 | .712500 |
| NOR | Retained first observation | 480 | 768 | .968750 |
| NOR | Reset | 576 | 528 | .650000 |

Across all ten conditions, retained evidence purchases **4,320** answers
against **5,760** for reset, a **25% reduction**. Final endpoint correctness
is **7,680/7,680** against **5,520/7,680**. Mean net reward is **.971875**
against **.681250**. Both .75-fee and unavailable intact branches purchase
zero answers, with 71.875% correctness for retained and 50% for reset.
All 180 policy groups and 69,120 keyed paired-policy comparisons are saved.

## Adverse cases

Pointwise regressions are retained alongside the aggregate pass.

| Comparison over 7,680 target predictions | Retained Brier worsens | Largest increase |
|---|---:|---:|
| Intact retained against first only | 184 | .0001263001 |
| Intact retained against latest only | 184 | .0001130200 |
| Intact retained against cycled-layout retained | 512 | .0007693444 |

Retained endpoint NLL worsens on 120 cases against first-only evidence and
72 against latest-only evidence.

The cheap retained policy has **480** paired net-reward regressions of .05,
caused by an additional fee with equal final correctness. Its paired
correctness-regression count is zero. Expensive and unavailable retained
branches each have **696** paired correctness/net regressions against reset,
with aggregate accuracy still 71.875% against 50%.

Under cycled layout, cheap retained mean net reward is **.306250** against
**.368750** for reset. The incorrect alignment can therefore amplify error
through evidence retention. Every paired record remains available for
inspection in the scored evidence.

## Verification and cost

An independent development audit reconstructed the learned action
probabilities directly from saved coefficients, matched every receipt to
the published public prefix, and checked all actual repetition files.
Maximum action-probability residual was **1.1102230246251565e-16**, and maximum
independent native-projection residual was **4.440892098500626e-16**.
Public-evidence posterior, forecast and policy replay was exact.
[Public custody audit](results/coordinate-transport-v1/independent-audit.json)

An independent raw/evaluator roll-up checked all 120 forecast groups and
180 policy groups. Its maximum scalar difference was **1.1102230246251565e-16**
from ECE rounding. All 69,120 paired-policy records matched exactly.
[Scoring audit](results/coordinate-transport-v1/independent-scoring-audit.json)

The full isolated suite ran **1,313 tests** with zero failures and two
intentional sealed v7/v8 collector skips. The 49 new synthetic checks passed.
All 37 historical snapshot manifests verified, and the historical guarded
preflight completed from a clean published checkout.

Timed native shard work consumed **71.7403** and **69.9409 CPU seconds** in
the two invocations. Native peak RSS reached **500,288 KiB**. Complete
scoring processes consumed **35.7776** and **35.6862 CPU seconds**, with peak
RSS **1,346,232 KiB**. Python was 3.13.5 and Torch was 2.10.0+cpu, with one
intra-op thread. These figures describe this development execution.
[Qualification receipt](results/coordinate-transport-v1/qualification.json)

The tranche adds **1,228 study-source lines** and **1,063 test lines**. The
projection adapter occupies 160 lines. The inclusive sandbox contains
**65,579 physical Python lines across 401 files**, including 26,625 test
lines. The inclusive 2,000-line objective is unmet.

## Scope and next requirement

Freshness applies to participant identities and physical instances. The two
words, three layouts, four primitive actions and two native physical laws
were already exposed. The four coordinate sign hypotheses, uniform prior,
query fees and decision rule are supplied. Saved language and physical
coefficients provide the learned projection. Each law is evaluated with its
own frozen world. The trials form a dependent finite factorial bank.

The next bounded requirement is duplicate-safe cold-process persistence of
the transformed hypothesis frame. A temporal/scope contract must then
distinguish durable corrections, temporary exceptions and conflicting
sources. The archived GRU parent received 1,024 events per update against
1,152 for the coordinate parent, while the existing text-only arm omits
physical state. A matched neural comparison therefore requires a new
prospective fit.

The broader G5 exit requires new sentence families, matched-final-correctness
clarification savings, durable competence after episodic-memory clearing,
contradictory-source cases and irreducible ambiguity. G6 corpus acquisition,
G7 measured Wikipedia utility and G8 integration are pending.
