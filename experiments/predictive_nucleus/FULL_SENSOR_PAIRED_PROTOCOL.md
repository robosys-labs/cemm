# Full-sensor paired development protocol

The companion `full_sensor_paired_protocol_v1.json` is a candidate public
development protocol. It is not a G1 challenge and cannot support a claim of
held-out generalization. Review and commit the exact protocol bytes and hash
before the study's first neural fit or scored output. The independently
reviewed runner must be committed after that protocol and before execution;
its commit and source hash are recorded with the result. This document does
not by itself freeze anything.

The four arms compare direct flat loss masks and consistent entity-ID
permutations. All arms receive the same complete action and sensor histories
within each ID view. A target masked at one step remains visible in the
following input, except after the final action. The loss-mask contrast is
therefore conditional on full observation; it does not test removal of sensor
access or isolate learned persistence. Both ID arms repeat each of the same
64 already-opened histories six times, either verbatim or under six mappings.
They are 384 related records, not independent draws.

The protocol requires all seed/arm model fits to finish before scoring. For
each physical evaluation case, it requires every seed, arm, ID permutation
and model replay to finish before reading that case's evaluator truth. This
is a cooperative in-process ordering: the evaluator and offline records are
not independently held or isolated from Python callbacks. Inputs are sensor
observations, actions and later observations; supplied structural biases,
oracle truth and computed metrics must not be passed as learner features.

Four independently fitted structured models per seed follow the proposed
arm budget even when their structured tensors agree. Empirical controls are
fitted once per ID arm and shared across masks and seeds, with the shared
cost reported as such. Equal updates, event counts and a single host do not
establish matched compute or information. No model seed or public case may be
selected or discarded after seeing outcomes. Model checkpoints, their file
and semantic hashes, full per-case distributions and every paired change are
required for a complete result.

An exploratory role-normalized memory table was fitted on opened training
histories and queried on opened evaluation histories before this protocol,
solely to inspect ID equivariance and prefix coverage. No evaluator truth or
correctness scores were used. Those checks are prior public development, not
preregistered results. Incomplete runs must retain any obtainable failure
record and partial checkpoints but must not emit a complete primary summary.
Output-path creation errors can prevent writing even the failure record.

The current public data and full-sensor condition do not establish partially
observed performance, independent oracle custody or the roadmap's G1 exit.
G1 remains **HOLD / REVISE** regardless of the resulting development scores.
