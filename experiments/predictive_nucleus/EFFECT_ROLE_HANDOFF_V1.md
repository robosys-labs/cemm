# G3 effect/role and goal transfer — frozen execution handoff

The user approved publication and requested completion of G3. The accepted native
world is [PR #78](https://github.com/robosys-labs/cemm/pull/78), commit
`444300f70509d74371e32ce789450c532149fb6c`. Do not refit it.

[Study](EFFECT_ROLE_STUDY_V1.md) · [protocol](effect_role_protocol_v1.json) ·
[runner](effect_role_run.py) · [saved-record auditor](audit_effect_role_saved.py).

Freeze SHA256: `7b500d3bb1811dd484ea0af9ce7131776e7aea6d7a60a33f0e8490e34d494dca`.
The frozen source inventory contains 68 files; 186 historical files are bound.

## Execution

Use `/tmp/cemm-venv/bin/python` with `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `PYTHONHASHSEED=0`. The complete numerical runtime must
match the prepared receipt. Stages use exclusive outputs and permit no retry.

1. Verify the full isolated suite, all protocol locks and original preflight;
   publish source/data/runtime on a new branch stacked on #78.
2. Run `effect_role_run fit --data experiments/predictive_nucleus/data/effect-role-v1
   --output experiments/predictive_nucleus/data/effect-role-fit-v1 --publication SOURCE_SHA`.
   This fits all 15 language/control checkpoints once; worlds are immutable.
3. Publish all actual checkpoint and training files before collection.
4. Run `effect_role_run collect` with data, fitted directory, output
   `experiments/predictive_nucleus/results/effect-role-v1/traces` and weights SHA.
5. Publish all 408,000 raw forecast rows and the lexical control receipt.
6. Run `audit_effect_role_saved --pre-score --repo REPO --publication RAW_SHA
   --output OUTSIDE_REPO_PATH`. No evaluator targets are parsed in this mode.
7. Run `effect_role_run score` with data, fitted and traces directories, output
   `experiments/predictive_nucleus/results/effect-role-v1/scored` and RAW_SHA.
8. Run the saved-record auditor without `--pre-score`, using the same RAW_SHA.
9. Publish the complete decision, adverse records, resource/line accounting and
   roadmap/issue/PR updates. Only a complete prospective pass closes development
   G3. Formal scientific admission remains separate and open.

Invoke stages with `python -m experiments.predictive_nucleus.MODULE`.
At this handoff the study is prepared and no G3 research execution has begun.

## Software verification before research execution

All 1,073 isolated tests pass in 144.907 seconds, all 35 protocol locks verify,
and original protocol/frozen-input preflight pass. The final freeze binds all
68 source and 186 historical dependencies; prepared data are unchanged by that
coverage extension. [Validation](results/effect-role-validation-v1.json).
