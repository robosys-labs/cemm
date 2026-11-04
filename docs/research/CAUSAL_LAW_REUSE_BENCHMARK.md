# CEMM causal-law reuse: prospective benchmark design

**Status:** Proposed evaluation specification, **not** an executed result, frozen G5 experiment, or admission gate. Implement as an independent research benchmark only after the protocol, generation, matched-control budgets and data-custody plan are approved. The original G5 work is unaffected.

## Scientific claim to test

**Given observed histories of familiar operations, can a model infer reusable transition mechanisms, generalize them to new participants and new compositions, recognize non-identifiability, and correct faulty explanations more efficiently than size/compute-matched unstructured neural and generic rule-induction controls?**

A demonstration must compare *actual causal competence on unseen situations*, not mere agreement with labels seen in training.

## Inputs and information boundaries

Each trial has time-indexed **observed** state attributes, object identities, performed actions, measured effects, sources and optional expressions/prosody. None supplies the simulator's law, correct cause, counterfactual outcomes, preassigned true role-semantic alignment, or unseen answers. A private evaluator retains ground truth. All policies receive exactly the same realized past actions and sensor histories at each step.

Separate **physical action events** from descriptions/claims about actions. The mere sentence "X stole Y" is not an executed theft. The evaluator separately controls what physical events actually occurred and which claims are true, false, negated or unverified.

A candidate may request a permitted, priced intervention or verification; every comparator receives the same action menu, information and cost policy. If one policy selects a probe, report its resulting path and use matched off-policy/randomized schedules or intervention replay to avoid confounding a stronger model with richer observation opportunities.

## Controlled curriculum and fresh test partitions

| Partition | TRAIN exposure | TEST challenge | Failure signal |
|---|---|---|---|
| A. Known-law, new identities | Repeated contacts on familiar participants | Entirely unseen identities and attribute mixtures; no action-ID/role-position shortcut | Identity-specific memorization |
| B. New action compositions | Individual actions and limited action pairs | Held-out order, nesting and three-step interactions, including noncommuting effects | No reusable transition computation |
| C. New linguistic descriptions | Paired utterances, observed physical traces and context | Withheld paraphrases, word orders, two controlled languages, role reversal and prosodic focus | Learned wording, not events |
| D. Claim-versus-event | Source-attributed true/false claims and physical traces | "Ada claims Ben stole the book", denial, quotation, rumor, unrelated witness, verified theft | Treating claims as physical events |
| E. Ambiguous causation | Observational histories compatible with two causal laws | Before intervention: preserve ambiguity; after a discriminating controlled action: update | False causal certainty |
| F. Nonstationary dynamics | Stable laws with occasional measurement errors | True law revision, source degradation/reversal, unseen contexts, delayed noisy outcomes | Either never revises or overreacts |
| G. Cross-domain reuse | Training domains with disjoint values but shared abstract mechanisms | Fresh domain with new state symbols, object labels and rendered utterances | Law keyed to surface/domain |

**Pairing rule:** Where evidence is indistinguishable to the model, construct matched latent worlds with the same public prefix and opposite unseen outcomes; demand appropriately uncertain predictions until a discriminating observation is available. Partition families must be independently re-seeded and physically novel rather than renamed copies.

## Necessary controls (all share identical evidence)

1. **CEMM candidate:** learn an operation representation from transitions and infer participant-role binding, with bounded memory and provenance. Do not add one hand-coded rule per test family.
2. **Unstructured neural:** appropriately capacity- and training-budget-matched recurrent or feed-forward transition network. Same observation encoding and available state, time, action and source features; no ontology-based hints intentionally withheld. Compare several parameter sizes in a small fixed preregistered range to avoid selecting a conveniently weak control.
3. **Generic rule learner:** induce rules from the same observed input/output events with a frozen generic search/description language. It must never read true generator transition rules or hidden role bindings.
4. **Ablations:** disable shared law reuse, shuffle identifiers, remove intervention history, remove source provenance, freeze interpretations, and discard/reset learned mechanisms. These isolate the source of any gain.

For combined language+causality evaluation, use both a **shared frozen perception/encoding front end** and a **full-stack end-to-end condition**. The former isolates causal learning; the latter tests actual expression grounding. Record parameter counts, wall/CPU/GPU time, training updates, steps, parameter memory, learned-law storage bytes and inference cost. State and query budgets must be matched, not just weights.

## Scoring and primary decision

Report **independent case/world/seed denominators**; do not count correlated paraphrases as independent samples. All prospective gates must be frozen before challenge collection. The principal outcome is a paired comparison on **identifiable, genuinely held-out applications of the same operation**:

```text
Law Reuse Advantage (LRA) =
  successful held-out operation applications per retained law
  at a common accuracy, uncertainty, observation and compute budget

Secondary: outcomes/observations needed to reach a fixed transfer score;
           proportion of new participants, contexts, action orderings
           and expression families solved with no new law fit.
```

Also record:
- Exact and probabilistic next-state accuracy, intervention/causal effect error and worst-seed regret; distinguish observed predictions from counterfactual claims.
- Calibration (Brier/NLL), epistemically ambiguous abstentions, wrong >=95%-confidence claims, correct-old-meaning retention and unjustified retractions.
- Correctly grounded event/role and **attributed claim vs actual event** counts, plus prosodic-focus interpretation without claim-to-truth promotion.
- Number, price and realized value of physical probes and clarifying questions; unnecessary queries and missed beneficial probes.
- Parameter/storage/runtime cost of each accepted operation, law reuse after process restart, revision when a *physical* contradiction arrives, performance on unrelated old mechanisms.
- Negative controls for swapped participant-order, coincidental succession, confounding and observationally equivalent causes.

**Candidate admission criteria to preregister** (proposed, **not** retroactive/current G5 gates):
- A measurable margin over the **stronger** of unstructured neural and generic rule learner on held-out law reuse, with uncertainty reported by independent seed/domain, **not** cherry-picked cases. A useful initial target is >=10 percentage points on transferable next-state accuracy or >=2x independent correctly solved applications per retained law **at matched compute and quality**. Final numerical targets must be declared with sample/power analysis before any experiment.
- No worse calibrated uncertainty, false confident causal claims, or claim/event attribution than the strongest control; zero claim-only utterances may be treated as directly observed physical transitions in the registered claim-isolation fixture.
- No confidence in an observationally non-identifiable direction before discriminating evidence; measurable correction after a real intervention.
- Retention of old accepted mechanisms and no per-operation code/schema changes for novel identities and roles.
- A fail on any protected safety, custody, identifiability or worst-seed criterion prevents promotion regardless of aggregate gain.

A rule-based learner **winning** is a valid outcome: the hypothesis is an architectural advantage, not a guaranteed result. A tied learned rule with significantly better storage, inference or sample efficiency may justify another study but not a claim of general causal superiority.

## Custody: sequence before any scientific score

1. Publish benchmark protocol, blind law families, data-generation description, baseline source, optimizer budgets, split policy, confounders and ambiguity gates.
2. Publish implementation hashes and TRAIN-only stress tests; enforce a strict generator-to-learner interface. Private evaluator truth is never imported by training code.
3. Fit all candidate/control training checkpoints once; publish immutable weights, random seeds, compute/evidence receipts and exact source snapshots.
4. Collect **raw predictions and planned queries** on a fresh challenge bank; seal raw hashes before opening evaluator truth.
5. Evaluate raw only after collection; disclose all law/seed partitions, failures, counterfactual costs, negative evidence and code/runtime exceptions. No revised thresholds after scoring.
6. Admission is only **bounded experimental evidence** until independent generator custody and substantially different physical or embodied environments replicate it.

## Minimal implementation tranche after agreement

First build **physical-dynamics-only** tasks with 2–3 unknown latent operations acting on 2–4 observable state factors and permutable participant roles. Expose observed pre-action state, actual action occurrence, measured post-state, optional safe interventions; do **not** expose any symbolic transition. Then add new identities and two-action compositions, before expanding to expression grounding and prosody. This prevents linguistic ambiguity from concealing whether causal law reuse works.

Do not commence this tranche as a change to the frozen G5 v8 branch. Maintain the root runtime's five operators and evidence/authority boundary; activation, ABI changes and production integration require separate review.
