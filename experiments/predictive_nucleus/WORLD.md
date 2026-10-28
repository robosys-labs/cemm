# G1a — independent binary-contact simulator (not a learned model)

No language, old CEMM parser, teacher model, policy or production effect is used.
`world.py` implements the frozen G0 `binary-contact-v1` contract: 3–6 same-kind
opaque handles; one binary state each; ordered participant contacts with a
per-episode hidden orientation; unilateral set interventions; no-effect sensor
observations. Contact changes **only** the other positional participant by
XOR with the source's current bit. This physics is oracle code, **not**
learner-supplied semantics. New states, observations and actions are immutable
or freshly allocated; no in-place mutation is permitted.

The deterministic generator allocates distinct lineage IDs using SHA256 of the
preregistered split, master seed, episode index, family and generator version.
Initial observations show all identities in shuffled order; subsequent readings
may be partially occluded/shuffled. `learner_turn` exposes only current sensor
readings and the chosen ordered action. `causal_replay` calls model prediction
**before** delivering the next observation. Hidden orientation and all
unobserved post-state values remain in the evaluator-only `Episode` trace.

The independent truth-table test computes its own expected transitions from
two possible hidden orientations, all four binary pair states and both action
orders. Other tests cover state non-mutation, source-only preservation, opaque
identity relabeling, intervention isolation, deterministic replay, forbidden
split/family combinations, event order and absence of future/oracle fields in
learner inputs. No sealed G1 challenge seed has been opened in local tests.

## Identifiability STOP before fitting

With v1 orientation independently sampled per episode, **first-contact exact
prediction is not always identifiable**. For input state `(A=1, B=0)` and
observed action `contact(A,B)`, two worlds with hidden orientation 0 vs 1
have identical public histories, but one sets B=1 and the other leaves B=0.
With independent fair bits and a fair orientation, 3 of 4 bit patterns are
ambiguous; an exact predictor with no prior orientation evidence can obtain
at most `1/4 + (3/4)*(1/2) = 62.5%` on that first-contact distribution.
This is a **mathematical diagnostic**, not a measured G1 score.

The 62.5% calculation additionally assumes that orientation remains fair
conditional on *all* learner-visible inputs, including IDs. The public legacy
generator can reveal orientation through enumerable IDs, so this idealized
bound is not established for an unrestricted predictor on its actual generated
episodes. The public two-pair fixture has a separate, finite ambiguity: two
orientation-twin pairs have identical complete sensor histories. Neither fact
establishes independent challenge performance.

Under those idealized assumptions the >=95% exact target cannot be achieved
on that first-contact distribution, regardless of network size or compute.
The frozen manifest does not specify that all gate cases are first contacts,
so this calculation alone does not determine its aggregate gate outcome.
Do not fit a model to the sealed challenges until the research protocol
predeclares one of the following without lowering the target:

1. a bounded informative contact/probe prefix, evaluated separately, before
   scoring post-evidence generalization to unseen contacts; or
2. a persistent globally shared mechanism (orientation) across episodes, to
   be learned from training outcomes; separately test unresolved per-episode
   orientation with proper probabilistic calibration and abstention.

Keep all unidentifiable first-contact cases and report their Brier/NLL and
coverage, even when not counted toward a **distinctly labeled, predeclared**
post-evidence exactness gate. The G0 hash/threshold must not be silently
changed to accommodate observed results. Version a replacement protocol and
freeze an independent new challenge *before* training. Existing challenges
remain unopened. **Decision: simulator KEEP; G1 learning gate BLOCKED** until
this ambiguity is reconciled. The model has not been trained.

## Local validation

```sh
python -m unittest discover -s experiments/predictive_nucleus/tests -v
```
