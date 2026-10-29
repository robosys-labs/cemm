# Retained-checkpoint replay: completed, post-hoc, not G1

**Date:** 2026-10-29. **Decision:** KEEP the replay/audit mechanism; REVISE the comparison; **G1 HOLD / REVISE**. The original v2 study remains **INCOMPLETE**. No language, production runtime, PR #21 or admission changes.

## Execution and retention

[Run 40812903804](https://github.com/robosys-labs/cemm/actions/runs/40812903804) completed the frozen protocol once at execution commit `3493b3b62967d4f1edf84da15698ef84732ecb5f`. The unchanged runner is `157436f161977063412b9d9bc21005dfe73691cb`; the protocol was committed at `8905b0529af6ba0e4bade780d737f4d17fad0ccd`. No neural model was retrained or selected. All 40 checkpoint byte hashes and restored tensor fingerprints and all six reconstructed control-table hashes passed. The workflow requires the exact PR, same-repository branch, direct parent, workflow-only diff, reviewed runner/test Git blob hashes, protocol SHA-256 and first run attempt. Subsequent pushes and reruns cannot execute this replay through that guard.

The complete artifact, including raw forecasts, normalization audits, case-level scores, report and exact source snapshot, is retained in the owner's CEMM Library as [cemm-posthoc-replay-3493b3b.zip](https://chatgpt.com/library?file_id=libfile_0c184e88e03081919438a47f9fff7254&account_id=personal). This Library copy is access-controlled; external replication requires access to the bundle. [Actions artifact 12871580518](https://github.com/robosys-labs/cemm/actions/runs/40812903804/artifacts/12871580518) expires on 2027-01-27 and is not the durable copy.

| Retained bytes | SHA-256 |
|---|---|
| Complete replay ZIP | `ea687a913da3d59a7bf032957263c50c9518cce8fdd4252c47fd06c5b1845a0e` |
| `report.json` | `d46cf61680d39506cb2bed064b61d2acb440afc85a7d056ccbb3f879364c3475` |
| `cases.jsonl` | `0015679c10251836b1575987e679e27e3941bfb5952af65db24047675b28255a` |
| Separate original failed-study ZIP, unchanged | `e8a891e113de13fcc6dce00bbf2b39a08a20f20a80881d1fba351d4c976d7bc7` |

The original ZIP and its 40 checkpoint byte hashes were also checked after a separate download. The replay itself received extracted Actions files and correctly reports `archive_zip_hash_verified: false`; this external ZIP check does not rewrite its report or recover the original host.

## Descriptive results

Every flat arm has 1,536 contact/set queries per seed: 64 already-opened physical cases, six correlated ID views and four scored contact/set positions. The 384 observe queries per seed/arm are reported separately. The five model seeds reuse the same physical cases; these are not independent test worlds. Both models received identical realized histories, but objectives, supplied biases and compute remain different.

Flat-model complete-world MAP accuracy on those contact/set queries:

| Training arm | Seed 7 | Seed 11 | Seed 23 | Seed 37 | Seed 53 | Five-seed mean |
|---|---:|---:|---:|---:|---:|---:|
| Repeated IDs, masked targets | 26.76% | 22.46% | 25.98% | 26.04% | 27.15% | **25.68%** |
| Repeated IDs, full targets | 34.44% | 32.55% | 32.62% | 31.12% | 27.15% | **31.58%** |
| Permuted IDs, masked targets | 33.01% | 33.92% | 34.77% | 28.39% | 36.59% | **33.33%** |
| Permuted IDs, full targets | 78.32% | 78.26% | 72.59% | 78.39% | 72.79% | **76.07%** |

The exact correct counts in seed order are `[411,345,399,400,417]`, `[529,500,501,478,417]`, `[507,521,534,436,562]`, and `[1203,1202,1115,1204,1118]`, each over 1,536. The retained report contains all per-step Brier/log scores, abstentions and paired records; percentages are not a replacement for those records.

For reference, structured scores are 88.28125%, the local empirical control with supplied persistence scores 81.25%, and no-change scores 50% on this same contact/set denominator in every arm/seed. These are descriptive comparisons, not matched-compute architecture effects. Literal-ID history memory abstains everywhere. Role-normalized history memory answers only the first contact, so neither supplies a strong full-trajectory memorization baseline.

Regressions are retained. Across the five seeds and related views (7,680 queries per contrast), masked-to-full targets with ID augmentation fix 3,744 previously wrong predictions but break 462 previously correct predictions. Adding ID augmentation with full targets fixes 3,867 and breaks 450. The other contrasts and per-seed differences in differences remain in the raw report. No iid confidence interval is claimed.

**Interpretation:** full-target supervision and ID augmentation together materially improve this flat baseline on opened cases. The earlier gap cannot responsibly be presented as architectural superiority. This does not prove the remaining structured advantage is learned composition, or identify a general causal explanation: training losses, supplied persistence/role symmetry, effective examples and compute are still unmatched. It also does not establish a new G1 result.

## Arithmetic verification and numerical behavior

The standalone `audit_posthoc_archive.py` imports no model, simulator, fitter, historical scorer or normalizer. It reads the retained output without modifying it and independently recomputes normalization, full-world MAP, Brier, clipped and uncapped log scores, zero counts, coverage, 600 summary cells, 20 primary cells, 20 paired contrasts and five interaction cells. All **230,400 forecast-status records across 64 cases** passed. Its result is retained in `results/posthoc-3493b3b-audit.json`.

There were 59 raw forecasts containing a probability above one within the frozen small-mass tolerance. Uniform normalization changed neither maximizer sets nor lexicographic MAP in any forecast. Raw distributions and corrections remain retained. Numerical zeros stay zeros; for example, no-change has infinite uncapped aggregate contact/set log loss rather than a silently clipped finite value. This audit does not independently verify sensor provenance, temporal custody, callback timings or every renaming-diagnostic field; it is arithmetic/inventory validation, not an independent challenge or reviewer.

```sh
python -m experiments.predictive_nucleus.audit_posthoc_archive /path/to/posthoc-replay-output
python -m unittest experiments.predictive_nucleus.tests.test_posthoc_archive_audit -v
python -m unittest discover -s experiments/predictive_nucleus/tests -v
```

Six new adversarial tests cover invalid/duplicate masses, forged corrections/scores, abstention, infinite loss, report-hash failure and incomplete inventory. All **263** isolated tests passed locally with Python 3.13.5 and PyTorch 2.10.0+cpu. The original execution and inherited invariant CI runs passed; consult the PR checks for the later audit commit's CI status.

Replay-only wall/process CPU times were 97.116/97.105 seconds. Host: AMD EPYC 7763, Python 3.13.17, PyTorch 2.10.0+cpu, one intra-op thread, four inter-op threads, deterministic algorithms enabled. Reported process peak RSS was 586,008 KiB. Original training-host metadata remain unknown. Cross-host equality is not established.

## Roadmap consequence and next implementation boundary

Do not open G2-G5 or add another language/parser layer. The next substantive G1 work is a frozen comparison with the same delivered histories and full-state learning objective, explicit ablations of supplied persistence/ID symmetry, and a predeclared measured resource budget. Before fitting, establish which query histories contain enough evidence to identify the dynamics and fix an informative, equal-cost acquisition schedule; keep ambiguous cases and proper scores instead of relabeling uncertainty as success or weakening the 95% research target. Then require a fresh independently authored and held challenge before G1 admission.

This replay is finished; do not retune or rerun its opened protocol. The research namespace now contains **13,456 physical Python lines including tests**, above the practical 2,000-line target. The next design should consolidate the minimal learning/comparison path rather than continue expanding diagnostic scaffolding. This statement does not authorize deleting historical failures or changing frozen manifests.
