# CEMM v3.5 Phase 9 — UOL factor-graph composer

**Base:** `e362bf82da4ee4f6704be2ed522cd7bf9418d6bf` plus the Phase-7/8 authority hardening patch
**Status:** implemented and phase-verified; not public-runtime-authoritative
**Authority:** cycle-local exact-schema factor compilation over pinned Phase-7/8 evidence

## Boundary

Phase 9 implements Core Loop stages 5–7: build a typed UOL factor graph, solve bounded meaning hypotheses, and select a partial-safe meaning bundle. It does not perform epistemic admission, transition effects, state mutation, response realization, or runtime cutover.

The central anti-drift rule is that the solver is ontology-agnostic. Learned schema refs, event refs, type refs, and language forms are data values. The builder resolves their exact reviewed revisions and compiles authorization/compatibility into finite factor tables. No semantic predicate name is interpreted by solver control flow.

## Subphases

- **9A — variables:** senses, exact schema activations, referent identities, ports, scope, time, context, and construction activation.
- **9B — hard contracts:** sense/schema links, exact ports, type compatibility, context/time isolation, Phase-8 joint grounding, construction evidence exclusivity, and scope compatibility.
- **9C — soft evidence:** decomposed discourse/world/grounding evidence and bounded complexity; defaults may rank but never materialize facts.
- **9D — solver:** deterministic bounded best-first/beam propagation with hard pruning trace and explicit search exhaustion.
- **9E — UOL materialization:** semantic applications, mentioned event occurrences, coordination, nested operators, and typed open variables only where schema contracts authorize partial composition.
- **9F — selection:** close alternatives retained; decisiveness requires margin plus absence of unresolved frontiers/search exhaustion.
- **9G — verification:** pinned contract, competence hash, deterministic double compilation, multilingual equivalence, non-transition/non-admission assertions.

## Corrections made while implementing

1. Open semantic-variable fillers are now accepted when the exact port independently authorizes their `open_binding_purpose`; they no longer require a duplicated filler-class declaration.
2. Nested operator applications are structurally composable without naming individual operators; leaf-schema restrictions still constrain the eventual operand.
3. Phase-8 local grounding scores are decomposed into explicit factors rather than becoming one opaque Phase-9 score.
4. Context, type, and explicit time evidence are represented as first-class variables/factors.
5. Meaning selection contains no realization score or target-language preference.

## Exit gates

- deterministic factor graph and bounded solve;
- traceable hard pruning;
- nested operator scope;
- multilingual equivalent semantic schemas;
- repeated clauses remain separate applications;
- unknown content preserves a valid partial subgraph/frontier;
- event mentions have no admission refs or deltas;
- grammatical claims are not admitted;
- architecture lint rejects named semantic authority literals in composition kernel code.
