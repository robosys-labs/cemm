# CEMM research direction: native causal computation through learned-law reuse

**Status:** Proposed architecture/research north star, **not** a runtime contract or scientific admission. Approval of this document would not activate new mechanisms, change five kernel operators or ABI versions, or modify any frozen G5 protocol, model, checkpoint, raw bank or score. Root and Hybrid MVP integration require separate reviewed decisions.

## Thesis

CEMM should discover reusable computational causes from grounded experience, not approximate a smaller transformer or disguise hand-authored transition functions behind an event ontology.

**Primary intelligence measure:** after acquiring a compact operation from observed experience, how accurately, efficiently and safely can it reuse that operation with unseen identities, role permutations, unfamiliar state combinations, reordered action sequences and alternative linguistic descriptions?

Learned reusable law, not next-token likelihood, parameter count, surface fluency or storing a larger event dictionary, is the principal target. An event record is a hypothesis or observation; it is not automatically a correct interpretation, a verified cause or an executable law.

## Three learning problems with distinct evidence and failure accounting

1. **Interpretation:** infer candidate referents, event/action identities, participant roles, proposition scope, attribution, negation, salience and discourse force from text, audio, sensors and context. Unknown designations, unseen participant bindings and unfamiliar utterances must remain hypotheses. Evidence order, construction and prosodic emphasis affect *hypothesis weights and focus*, not a universal lexical priority rule or truth promotion.
2. **Dynamics:** infer compact, participant-general operations that predict changes of world state under action and context, including preconditions, persistence, reversibility, composition and interaction. No gold transition implementation, privileged action effects, role-order answer or hidden simulator mechanism may enter training. The learner must update a law when a physically observed outcome contradicts it.
3. **Epistemics:** represent source provenance, ambiguity, claim/observation distinction, expected predictive loss, causal identifiability, confidence and targeted clarification. An unexplained prediction failure is not automatically evidence of a new law; it might reflect observation error, wrong interpretation, hidden state or insufficient evidence.

An accepted system must solve all three without quietly treating a supplied ontology, event schema, simulator or grammar as a learned law. For evaluation, isolate each problem with diagnostic controls before evaluating their composition.

## Event and claim example

Input: **"Ada claims that Ben stole the book."**

- What is directly observed is **the current speaker's utterance**. Its content reports that Ada made a claim, and embeds a **further unverified theft proposition** concerning Ben and the book. If Ada herself was directly heard speaking, her claim event can additionally be observed; a third-party report alone does not verify that Ada actually made the claim.
- Neither layer by itself warrants a committed physical theft, transfer of the book, or transition of Ben's world state.
- "Ada **CLAIMS**..." versus "Ada claims **BEN** stole..." may change focus, contrast and pragmatic confidence; it does **not** turn the embedded theft into an observed fact. Prosody is evidence that interacts with context, language and learned focus interpretation.
- A later independent inspection, verified action trace or other physical observation may support or refute the proposition. Its connection to the claim is provenance, **not** automatic factual authority.
- Likewise, event B occurring after A does not by itself mean A caused B; unobserved confounders and observationally equivalent mechanisms must remain plausible.

The existing five application shapes (designation, type, relation, state, event) remain the semantic substrate. An unverified proposition is still representable using these shapes, but has a distinct epistemic placement. A **learned law is a reusable versioned transition hypothesis with evidence and scoped prediction rights**, not a sixth fundamental operator or a pre-authored semantic implementation.

## Minimal mechanism interface, not a hard-coded law language

Public history contains typed events and observations with time, source, optional goal, participants and pre/post observations. The causal learner maintains candidate latent operation representations, uncertain participant-role bindings and state factors.

Conceptual learning objective:

```text
observed history H_t = (observed state fragments, action/evidence,
                        time, source, participant bindings, outcomes)
interpretation alternatives q_φ(z, roles, attribution | form, sensors, H_t)
learned dynamics          p_θ(x_(t+1) | x_t, z, roles, context)
epistemic state           P(alternatives, trust, unknowns | H_t)
```

Here `z` is **learned** from event/state regularities, not assigned the simulator's true operation label. The displayed factorization expresses the problem but does not prescribe a grammar, architecture, loss or symbolic implementation. Identity substitution must preserve the same law if the physical effect is invariant. A genuine new operation may acquire new parameters or a new reusable mechanism, but no new hand-written operation branch or term-specific schema.

The runtime should **propose -> predict -> compare to physical outcome -> revise -> preserve/reuse**, with a bounded hypothesis library and revisioned provenance. Physical interventions and deliberately varied environments can help distinguish causal alternatives. If available evidence is insufficient, preserve competing explanations and ask a discriminating question rather than produce certain invented effects.

## Non-negotiable anti-shortcut boundaries

- No learner access to hidden transition functions, simulator seeds, gold event semantics, actual source corruption labels, omitted future outcomes, or oracle participant-role order.
- No `if action == "..." then mutate ...` per operation; no expanding lookup table keyed by identity pairs; no rule-library seeded with benchmark answers.
- No unique lexical identifier, timestamp, participant ID, object ID, ordering artifact or answer-shaped receipt that leaks the hidden law. Exact identity tracking is allowed; **identity-specific law memorization is not**.
- No privileged predicate/role structures supplied to CEMM but withheld from baselines. If interpretation is factored out to isolate dynamics, share **exactly the same extracted observed inputs** across all arms.
- An independently evaluated matched neural model and a generic rule-induction/search baseline receive the same realized action and observation histories, source channels, queried answers and budgets. The rule baseline may use generic induction primitives, **not the true generator rules**.
- Instrument observation source/reliability separately from semantic interpretation, inferred mechanism and admission. A source statement never automatically triggers the operation it describes.
- Do not optimize benchmark-only code that cannot transfer to a new domain without adding operator-specific logic.

## Research-to-runtime boundary

The existing architecture's evidence, candidate, semantic authority, world, operational and response planes remain authoritative. A research learner may propose candidate mechanisms; promotion into exact semantic authority or execution requires independently reviewed evidence, admissibility, competence scope and commit receipts under existing Stage-13 and operational boundaries. No autonomous code execution or real-world actuation follows from an unreviewed causal hypothesis.

Current G5 v1 rule remains the selected bounded baseline. G5 v6/v7/v8 research, the G1–G4 results, and G6–G8 admission gates are unchanged. This charter adds **no** runtime activation or new scientific-admission claim.

See [the measurable evaluation contract](CAUSAL_LAW_REUSE_BENCHMARK.md).

## Research context

- Interventional identifiability is conditional on explicit assumptions, not guaranteed by an event vocabulary: [Varici et al., AISTATS 2024](https://proceedings.mlr.press/v238/varici24a.html).
- Causal representation learning can be severely underdetermined without extra constraints, even when observations are rich: [Morioka & Hyvarinen, ICML 2024](https://proceedings.mlr.press/v235/morioka24a.html).
- Matched data diversity, capacity and compute matter in attributing a compositional advantage: [Kapl et al., ICML 2026](https://proceedings.mlr.press/v306/kapl26b.html).
- Speech prosody affects focus and interpretation but is not an oracle of intended meaning: [Carlson, 2009](https://compass.onlinelibrary.wiley.com/doi/10.1111/j.1749-818X.2009.00150.x).
