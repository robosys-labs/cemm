# Proposed post-hoc replay of retained checkpoints

The original public factorial study remains **INCOMPLETE**: it stopped after
six written cases and during scoring of case 6. This proposal is a separate,
post-hoc analysis, selected after those cases and a subsequent numerical
inspection were opened. It cannot supply a preregistered result, reconstruct
the original failing forecast, or establish the original host configuration.
The independent G1 challenge remains outstanding; **G1 HOLD / REVISE**.

The [protocol](full_sensor_posthoc_replay_protocol_v1.json) fixes a single
replay of all 40 retained neural checkpoints, with no neural retraining, on
the 64 already-opened public cases. It requires verification of checkpoint
bytes and tensor fingerprints and reconstruction and hash checks of six
empirical controls before evaluation. All seed, arm, ID-renaming and model
replays for a case finish before its truth is read. Both learned models and
controls receive the same realized action and full-sensor histories; the
simulator uses state in-process to create feedback, so this is not independent
custody or an isolation boundary.

Every predicted joint distribution receives the same near-unit global
normalization, with the entire original vector and correction audit retained.
Abstentions remain abstentions. The existing strict scorer receives normalized
vectors only; normalization can alter proper scores or collapse a maximum to
a tie. The analysis must retain those effects and reject materially invalid
mass instead of clipping it. Its comparisons describe this replay on opened
cases, with unequal training objectives and supplied model biases, not a
matched-compute or architecture-superiority test.

The original failure archive's ZIP hash identifies the durable source; an
Actions download that yields extracted files can verify its hash-verified
failure and progress logs and all checkpoint files, but must not claim to have
verified ZIP bytes it did not obtain. Earlier case records include truth and
partial scores and are not inputs to the replay. Exact cross-host equivalence
remains unknown. Review the manifest independently, commit it first, then
independently review and commit the runner before enabling a guarded one-time
workflow. Preserve incomplete output on failure and the complete raw output
on success; do not silently retry after inspecting results.
