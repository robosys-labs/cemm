# CEMM Hybrid ABI Registry

**Status:** active target contract under the 2026-08-02 Hybrid-only amendment
**Runtime cutover:** hard
**Scope:** `hybrid_mvp/` only; root adoption requires separate review

This registry distinguishes derivation ABIs from semantic-content ABIs. An ABI
version change invalidates every dependent scenario, episode, partition,
checkpoint, calibration, evaluation, activation and release artifact.

## 1. Active target registry

| ABI | Version | Canonical owner | Persistence | Validator / compiler | Activation gate |
|---|---:|---|---|---|---|
| Evidence ABI | 1 | `src/cemm_authoritative_hybrid/forms.py` | Transient / episode-serializable | `FormResolver` | Exact reversible source geometry; one immutable evidence packet; no downstream retokenization authority. |
| Semantic Contribution ABI | 1 | `src/cemm_authoritative_hybrid/contributions.py` | Transient | `ContributionExpander` | Every source unit yields bounded typed contributions or one typed unresolved contribution. |
| Proposal Context ABI | 1 | `src/cemm_authoritative_hybrid/proposal_context.py` | Transient / episode-serializable | `ProposalContextBuilder` | Contains only current grounded candidates, reviewed frames, bounded references/scopes/binders/transitions/residuals and exact revision pin. |
| Semantic Switch Program ABI | **2** | `src/cemm_authoritative_hybrid/programs.py` | Episode-serializable | `SemanticExpressionCompiler` and `ExactProgramVerifier` | Exactly one class owner; complete ordered full-content program hash including dynamic pointers, roots, bindings, assignments and revisions; no sorted action identity. |
| Semantic Expression ABI | **1** | `src/cemm_authoritative_hybrid/expressions.py` | Episode/world/reference serializable as permitted | `SemanticExpressionCompiler` | Canonical recursive five-operator expression forest/root set with applications, scope operators, expression links, binders and typed unresolved fillers. |
| Source Coverage ABI | 2 | `src/cemm_authoritative_hybrid/coverage.py` | Episode-serializable | `CoverageVerifier` | Each critical source unit has one exact structural assignment or one typed residual. Coverage does not manufacture semantic expression structure. |
| Proposal Result ABI | 2 | `src/cemm_authoritative_hybrid/proposal.py` | Episode-serializable | candidate-batch validator | Ranked candidates preserve order, scores, provenance, model identity and exact context ref; abstention is explicit. |
| Verification Batch ABI | **2** | `src/cemm_authoritative_hybrid/verifier.py` | Episode-serializable | `ExactProgramVerifier` | One receipt per candidate; accepted receipts carry `expression_ref` and compilation proof; disposition is selected/ambiguous/rejected/abstained. |
| Verified Meaning ABI | **1** | `src/cemm_authoritative_hybrid/expressions.py` | Transient / episode-serializable | `VerifiedMeaningValidator` | Binds program lineage, canonical expression, grounding, coverage, compilation proof, verification receipt and revision pin. |
| Situation Context ABI | 1 | `src/cemm_authoritative_hybrid/situation.py` | Transient / episode-serializable | `SituationContextValidator` | Independently binds force/mode, participants, temporal/source/epistemic and session context; never inferred from program identity. |
| Effect / No-Effect Receipt ABI | 1 | `src/cemm_authoritative_hybrid/effects.py` | Serialized | `EffectGateway` | Exactly one receipt per cycle; all mutations/adapters bind decision and verified-meaning refs and are idempotent. |
| Gap Receipt ABI | 1 | `src/cemm_authoritative_hybrid/gaps.py` | Serialized | `GapClassifier` | Earliest exact owner emits typed partial/ambiguous/unknown/unsupported/budget/resource/permission/failure status. |
| Learning Plan ABI | 2 | `src/cemm_authoritative_hybrid/learning.py` | Serialized | `LearningCoordinator` | Plans bind exact verified meaning, source query, target-kind contract, provenance, permission, revision and expiry; conversation cannot self-publish authority. |
| Response Meaning ABI | **2** | `src/cemm_authoritative_hybrid/response.py` | Episode-serializable | `ResponseBuilder` | Constructed from decision, proof, blockers, effect/no-effect receipt and obligation; contains an exact semantic-expression contract. |
| Realization Receipt ABI | **2** | `src/cemm_authoritative_hybrid/realization.py` | Serialized | `RealizationVerifier` | Surface is reinterpreted through the same evidence/proposal/compile/verify contracts and compared by canonical semantic expression. |
| Phase Receipt ABI | 2 | `src/cemm_authoritative_hybrid/cycle.py` | Serialized when trace/evaluation enabled | `CycleFinalizer` | Each phase binds exact input/output refs, revisions, disposition, rejection codes and budget use. |
| Cycle Result ABI | 2 | `src/cemm_authoritative_hybrid/cycle.py` | Serialized | `CycleFinalizer` | Carries every phase artifact without reconstruction and final identity from completed content. |

## 2. Canonical program identity

The Program ABI v2 hash includes the complete ordered payload:

```text
abi_version
orientation_ref / proposal_context_ref
ordered actions {
    action_ref
    action_type
    dynamic arguments and pointers
    source_unit_refs
}
root refs
mode / goals
source assignments and residuals
revision pin
```

The following are ABI violations:

- sorting actions before hashing;
- hashing structural action names while omitting dynamic targets;
- excluding roots, roles, assignments or revisions;
- treating a model-vocabulary/action-encoding hash as a program-instance hash.

`action_abi_hash` identifies the closed model vocabulary. `program_hash`
identifies one concrete derivation instance. They are different fields.

## 3. Canonical semantic-expression identity

A `SemanticExpression` is a bounded forest with an explicit non-empty root-ref
set, not an implicit single-root tree. Ordered links preserve operand order;
only link types explicitly registered as commutative may canonicalize operands,
and graph canonicalization must prove an exact bijection over local IDs.

The expression hash is derived from semantic content after exact compilation.
It is independent of derivation ordering and may alpha-normalize only local
application/variable IDs.

It retains:

```text
persistent operator
predicate identity
role names and fillers
grounded refs and licensed literals
roots and expression links
scope/binder structure
polarity, modality, attribution and temporal distinctions
```

## 4. Required public types

Conceptual minimum:

```python
@dataclass(frozen=True)
class SemanticExpression:
    expression_ref: str
    applications: tuple[SemanticApplication, ...]
    root_refs: tuple[str, ...]
    scope_operators: tuple[ScopeOperator, ...]
    expression_links: tuple[ExpressionLink, ...]
    binders: tuple[VariableBinder, ...]
    unresolved_fillers: tuple[UnresolvedFiller, ...]

@dataclass(frozen=True)
class VerifiedMeaning:
    verified_meaning_ref: str
    program_ref: str
    expression: SemanticExpression
    grounding_refs: tuple[str, ...]
    coverage_receipt_ref: str
    compilation_proof_ref: str
    verification_receipt_ref: str
    revision_pin: RevisionPin
```

`verified_meaning_ref` may include proof and derivation lineage. Semantic
comparison therefore uses `expression_ref` plus required verified situated
qualifiers, not `verified_meaning_ref` alone. Evidence geometry and coverage do
not enter expression identity unless attribution/source is itself meaning.

Names may change only through a reviewed registry update. The separation of
program, expression and verified meaning may not change.

## 5. Invalidation rule

Program ABI v2 and Semantic Expression ABI v1 require regeneration of:

```text
reviewed expected contracts
canonical derivation targets
episodes
hard negatives
partitions
proposal checkpoints
realizer checkpoints
calibration
evaluation
activation receipts
release bundles
```

No descendant generated under the duplicate/legacy program ABI may remain green.

## 6. Forbidden compatibility

- no duplicate `SemanticSwitchProgram`;
- no `propositions.py` runtime owner;
- no result-shape adapter;
- no signature inspection;
- no implicit conversion from program to meaning;
- no semantic equality based on action sets, refs, markers or strings;
- no evaluator accepting a raw program;
- no old checkpoint loader translating Program ABI v1 at runtime.
