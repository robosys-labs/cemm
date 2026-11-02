# Isolated post-publication G3 v1 diagnostics

These artifacts explain completed negative evidence. They do not alter v1's source,
weights, protocol, acceptance thresholds or `REVISE_EFFECT_ROLE_GROUNDING` decision.

- [TRAIN-only diagnostic](TRAIN_ONLY_DIAGNOSTIC.md), [data](train-only-diagnostic.json)
  and [original script](train-only-diagnostic.py): 15 conditions across five seeds,
  each using the original 16-example teaching tape and 1,152-event rehearsal tape.
  **17,520 additional TRAIN-only forecast rows; zero optimizer updates or new fits.**
  This earlier diagnosis focuses on seed 7. It did not open challenge/evaluator
  inputs. Its original temporary paths are preserved as historical provenance.
- [Saved-curve arithmetic](curve-arithmetic.json): zero additional forecasts or updates.
- [Broader saved-evidence diagnosis](BROADER_SAVED_DIAGNOSIS.md) and
  [data](broader-saved-diagnosis.json): review of all ten completed scored reports,
  saved TRAIN-derived language states and frozen source. Zero new model executions,
  forward forecasts, gradients, updates, fits or collections. This review preserves
  calibration failures in every seed and the additional retention failures.
- [Saved-result summarizer](summarize-saved-results.py): reads completed reports,
  decisions and manifests only; it generated the separate headline summary.
- [Manifest](manifest.json): original file hashes, input scope and exposure accounting.

The probability-neutral normalization is a future fixed-budget hypothesis. Its
zero-update TRAIN behavior is not evidence that fresh generalization, bilingual
probability agreement or old-language retention will pass. Broader architectural
contingencies in the saved diagnosis are unimplemented proposals, not additions
to the active v2 experiment. CPU/wall/RSS for the original TRAIN-only diagnostic
were not recorded; none is silently counted as zero.
