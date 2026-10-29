# Common-objective public diagnostic: completed; stop tuning this fixture

Tracking: #22 / #52. Date: 2026-10-29.

**Decision: KEEP the demonstrated evidence-conditioned predictive capability;
CLOSE this public diagnostic; REJECT any architectural-superiority claim over
the strong empirical abstraction; G1 admission remains unproved.**

## Verified execution and retained evidence

The frozen comparison ran once, without retraining retries or changed settings:
[Actions run 40838302597](https://github.com/robosys-labs/cemm/actions/runs/40838302597).
All execution, publication and retention steps succeeded. The reviewed runner
was committed as `afadbbe9d67a081c5bc535804d94d763a673037a`, before the separate
execution workflow commit `a86addbb098aecd04520f4777435e68717a432de`.
Both commits' invariant CI succeeded; the source suite ran 363 tests, no skips,
including the synthetic six-model full pipeline. All 14 manifest locks passed.

Evidence is committed, not merely an expiring Actions artifact:
[results commit d622161](https://github.com/robosys-labs/cemm/commit/d622161fc7e27165715415c5a50c0d64bd076f49),
under `experiments/predictive_nucleus/results/common-objective-40838302597/`.
The branch is `research-results/common-objective-40838302597`.
`headline.json` and `decision.json` provide the reported aggregates; the two
`bundle.tar.gz.part-*` files contain the complete report, forecasts, controls,
initial/final checkpoints and failure/provenance machinery. Concatenate the
parts in lexical order to reconstruct the tar.gz; verify PARTS_SHA256.txt and
ARCHIVE_SHA256.txt before extraction. No local download of the entire bundle or
independent full re-scoring is claimed by this document. The CI runner checked
inventory/hashes and its publication step verified the report completion hash.

- Protocol SHA-256: `15732afe065f19f3b412a7638e386373eb586ddaa273104e2de63c14a782b1f3`.
- Report SHA-256: `581172fcfd257127772ea9962544bae1071bc43ce683fca225128e9de5f5d078`.
- Bundle SHA-256: `6314cde6d40a5781f243d94fb6344a2f81eacd115728397f119a8aadef1a70fd`.
- 120 neural fits, 240 neural evaluations and 16 distinct control evaluations.
- 2,949,120 neural forecasts and 10,560 paired per-step comparison records.
- Measured pipeline wall/CPU: 589.137 / 588.660 seconds; peak process RSS
  483,204 KiB on AMD EPYC 7763. Model tensors are explicitly float64; the reported
  torch default dtype being float32 does not change their dtype.

## Main result: informative second-pair final contact

Mean complete-world MAP accuracy across seeds 7,11,23,37,53. Each seed uses
1,536 related views of the SAME 256 public factorial cases; these are not
independent physical-world samples. The primary query is step 6, after all
three bits have been reset and the query pair differs from the probe pair.

| Model | 128-update regime | 2-second CPU-budget regime |
|---|---:|---:|
| Structured, learned background/persistence | 100% | 100% |
| Structured, supplied persistence | 100% | 100% |
| Structured, untied role hypotheses, learned background | 100% | 100% |
| Structured, memory reset | 62.5% | 62.5% |
| Flat GRU | 61.3672% | 61.9792% |
| Flat GRU with supplied persistence | 60.2214% | 60.4297% |

Every seed of each of the three non-reset structured arms has 1,536/1,536
correct queries in BOTH regimes; the memory-reset arm has 960/1,536 in every
seed/regime. The fixed-update learned-background arm's mean query NLL is
0.0020197963 and mean joint Brier 0.00000588994, calculated from the five retained
per-seed values. Without the informative probe, its fixed-update query accuracy
is 62.5% for every seed, with NLL close to the finite-fixture Bayes floor
0.75*ln(2) = 0.5198603854. Lower accuracy in that condition is not evidence of a
prediction defect when the supplied history genuinely cannot identify the truth.

On the informative query, persistent versus reset memory repairs 576 outcomes
per seed/regime with no query-level correct-to-wrong change. Relative to flat,
the fixed-update learned-background arm repairs 2,967 of the 7,680 correlated
seed/view query records; the CPU-budget arm repairs 2,920. These are arithmetic
consequences of the retained complete-query counts, NOT independent sample
counts or claims about zero regressions on every other step.

### The control that prevents an exaggerated conclusion

The prior-contact empirical abstraction ALSO obtains 1,536/1,536 informative
second-pair queries, query NLL 0 and Brier 0; all 768 reversed-role pairs are
correct. The current-state/action empirical control obtains 960/1,536 (62.5%).
Exact full-prefix memory abstains on all final second-pair queries. No-change
obtains 768/1,536 (50%) and has infinite uncapped query NLL.

Controls were fitted once per condition and reused descriptively; they are not
separate neural runs under the two training budgets. The contact control has a
SUPPLIED cross-pair abstraction; neither its success nor the kernel's success
shows that the abstraction was discovered from scratch. The model learns local
outcome probabilities but still supplies two persistent latent modes, action
locality and identifier-equivariant parameter sharing. Untying role hypotheses
does not remove all these assumptions. No special neural advantage over the
strong empirical control has been established.

## What this closes, and what it does not

The repaired public experiment answers the immediate question: a small learned
transition kernel with retained evidence can predict the second-pair query
after the current-state shortcut is removed. Explicit fixed persistence and
role-swap tying are not necessary for this query's perfect MAP score in the
tested untied/learned-background arm. Resetting its evidence state loses the
advantage. These are useful, bounded development results.

They are NOT G1 admission: same-pair scores are resubstitution; second-pair
chronology is new but local contexts overlap; all readings are noiseless and
complete; there are only three entities; capacities and consumed resources are
not matched. Equal update or CPU ceilings are not equal consumed compute.
The informative all-step theoretical ceiling is 93.75%, so pooled accuracy
must not be used to manufacture a 95% G1 pass. The original independent gate
and all historical failed studies remain unchanged.

## Stop rule and next focused scientific task

1. Do not refit, retune or extend this opened fixture. Preserve these checkpoints
   as fixed baselines. No new diagnostic framework or language work follows.
2. The next comparison must change the EVIDENCE QUESTION: separately authored,
   frozen trajectory families with partial-observation cases, role reversal,
   identity changes and new chronology, at explicit capacity/exposure/compute
   budgets. Its case author must not tune the learners against its targets.
   Test answerable complete-world queries separately from deliberately ambiguous
   strata with proper scores; do not inflate the denominator with easy resets.
3. Include the strong empirical abstraction, not only a weak flat baseline.
   Identify which challenge contexts are absent from each control's training
   support. If a simpler control explains the result, reject superiority rather
   than adding architecture to preserve a preferred conclusion.
4. Keep G1 bounded to the issue #22 world-learning gate. Learned communication
   is G4 and durable lifelong learning is G5; they are not new implicit G1
   prerequisites. Do not call our own fixture authoring independent custody.

Ordinary CI now runs all invariants/manifests and preflight rather than repeatedly
refitting the historical public studies. This removes a process loop without
weakening a scientific gate. This tranche adds 879 Python lines including tests;
prior retained count plus additions is 16,615, not a fresh full-tree enumeration
or satisfaction of the practical 2,000-line target. The next task should reuse
this execution path rather than create another competing harness.
