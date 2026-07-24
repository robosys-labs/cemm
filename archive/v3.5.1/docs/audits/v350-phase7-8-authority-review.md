# CEMM v3.5 Phase 7–8 Authority and Correctness Review

**Reviewed base:** `e362bf82da4ee4f6704be2ed522cd7bf9418d6bf` (`Phase 7-8 patch`)

**Review standard:** `ARCHITECTURE.md`, `CORE_LOOP.md`, `IMPLEMENTATION_PLAN.md`, `ACCEPTANCE_CONTRACT.md`, `docs/architecture/UOL.md`, and `docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`.

## Verdict

Phase 7–8 is a useful implementation substrate, but the original patch was not accepted unchanged. The review found authority leaks that could become future ontology shortcuts even though current tests passed. They were corrected before Phase 9 was treated as a valid successor.

The corrected boundary is:

- Phase 7 emits reversible language/form/construction evidence only.
- Phase 8 emits referent/schema candidates, ranked joint grounding hypotheses, unresolved frontiers, attributed claim participant grounding, and review-only identity proposals.
- Neither phase admits proposition truth, mutates actual-world state, creates transition authority, or chooses meaning because it is easy to realize.

## Findings corrected

### 1. Named ontology references in grounding kernel

Some grounding paths encoded structural semantic type names directly in Python. That creates a subtle source-code ontology: a later learned type can only participate if it happens to inherit a type name the kernel knows.

**Correction:** candidate/constraint generation now compiles compatibility from exact schema port contracts, type closure, storage constraints, deictic evidence, discourse roles, and reviewed sense metadata. Named semantic-reference literals are prohibited in grounding/composition/epistemic kernel packages by architecture lint.

### 2. Magic claim metadata used as kernel authority

Claim grounding used the metadata cue `claim_content_not_fact` as a semantic recognition switch. A metadata label is evidence/documentation, not a safe executable ontology discriminator.

**Correction:** claim grounding validates the exact selected schema structurally: proposition-storage content port, required identity-contributing source port, and remaining schema-declared referent participant ports. The compiler is invoked only after the upstream hypothesis classifies the occurrence as claim-like; it does not infer claim semantics from a magic string.

### 3. Implicit actual-world context defaults

Grounding/composition entrypoints defaulted `context_ref` to `actual`. This is convenient but violates the core-loop pinning law: world/context placement must be a Stage-0 cycle input, not a hidden default in a downstream cognitive stage.

**Correction:** grounding and composition entrypoints require an explicit context pin. Architecture lint now rejects an implicit `actual` default in grounding/composition/epistemic kernel APIs.

### 4. Existing-event identity versus event-introduction

Lexical evidence for an event predicate must not resolve to an arbitrary historical event occurrence merely because storage/type constraints match.

**Verified correction:** predicate evidence introduces a provisional typed occurrence unless independent identity, description, discourse, multimodal, deictic, or other grounding evidence identifies an existing occurrence.

### 5. Provisional-only candidate selection

A single candidate is not necessarily resolved identity when that candidate itself is provisional.

**Verified correction:** provisional-only assignments remain unresolved frontiers and cannot be reported as settled identity merely because no competitor exists.

### 6. Repeated construction instances

One construction type can occur multiple times in a turn. Treating construction type as construction instance collapses repeated clauses and can silently merge argument frames.

**Verified correction:** construction matching is trigger-anchored, bounded, deterministic, and instance-specific; explicit trigger edges prevent repeated-clause collapse.

### 7. Reversible normalization and exact source evidence

Normalization must never replace observation identity or reconstruct source text approximately.

**Verified correction:** normalization evidence retains exact original source spans and reversible proposals. Surface normalization remains evidence, not semantic truth.

### 8. Construction-to-grounding role propagation

Participant roles cannot be inferred from token positions or English-like order.

**Verified correction:** participant roles come from reviewed construction slots mapped to exact semantic ports and dependency/constituency evidence.

## Permanent prohibitions added

CI/static architecture lint now prevents:

- exact named semantic-reference literals in grounding/composition/epistemic kernel code;
- implicit actual-world context defaults in those cognitive stages;
- language surface branching in canonical semantic kernel code;
- event-specific semantic/mutation branches;
- source-code learned-type enums;
- generic negative-axis collapse;
- targetless/canned response authority.

## Remaining deliberate boundaries

This review does **not** declare CEMM v3.5 complete or runtime-authoritative. Phase 7–8 still deliberately does not own:

- selected UOL meaning composition;
- epistemic admission or four-state truth aggregation;
- inference or state transitions;
- response planning or realization;
- runtime cutover.

Those authorities must remain separately implemented, independently tested, and explicitly wired in their own phases.
