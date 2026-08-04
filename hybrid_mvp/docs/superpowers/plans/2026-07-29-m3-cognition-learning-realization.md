# Milestone 3 Cognition, Learning, and Realization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every task and superpowers:verification-before-completion before the milestone commit. Track work with the checkboxes below.

**Goal:** Complete the proof-bearing cognitive loop: query and inference, epistemic admission, state transitions, guarded effects, typed learning, dialogue reference, and semantically verified neural realization.

**Architecture:** A verified program is evaluated against revision-pinned semantic stores. Claims remain attributed until admission policy proves otherwise; capabilities are derived from current prerequisites; effects use one gateway; only exact `ResponseMeaning` enters focus; surface language is accepted only after semantic-equivalence verification.

**Tech Stack:** Python 3.13, SQLite WAL, frozen dataclasses, PyTorch, safetensors, canonical JSON/JSONL, pytest, Hypothesis.

---

### Task 1: Implement indexed query, proof, and selective recursive inference

**Files:**
- Create: `src/cemm_authoritative_hybrid/query.py`
- Create: `src/cemm_authoritative_hybrid/proof.py`
- Modify: `src/cemm_authoritative_hybrid/persistence.py`
- Create: `data/authority/rule_schemas/generic_definition.json`
- Create: `tests/test_query_engine.py`
- Create: `tests/test_recursive_inference.py`
- Create: `tests/test_inference_bounds.py`
- Remove: `src/cemm_authoritative_hybrid/inference.py`

- [ ] **Step 1: Write failing proof and family-inference tests**

```python
def test_generic_family_rule_lowering_supports_marriage_with_trace(
    generic_definition_lowerer, verified_family_teaching_programs,
    verified_family_arrival_program, test_authority_factory, query_engine_factory,
    semantic_stores
):
    before = semantic_stores.revisions()
    lowering = generic_definition_lowerer.preview(verified_family_teaching_programs)
    assert lowering.created_rule_refs
    linked_fixture = test_authority_factory.link_with_validated_rules(lowering.rules)
    assert semantic_stores.revisions() == before
    family_query_engine = query_engine_factory(linked_fixture)
    family_query_engine.observe(verified_family_arrival_program)
    result = family_query_engine.ask(query("participant:user", "state:married"))
    assert result.status == "supported"
    proof = result.proof
    assert {"concept:mother", "relation:in-law", "state:married"} <= set(proof.semantic_refs)
    assert proof.rule_applications
    assert set(proof.source_refs) >= set(lowering.source_program_refs)

def test_unknown_is_not_false(query_engine):
    result = query_engine.ask(query("state:married", "entity:unobserved"))
    assert result.status == "unknown"
    assert result.proof is None

def test_inference_exhaustion_is_explicit(bounded_query_engine, recursive_rules):
    result = bounded_query_engine.ask(recursive_rules.query)
    assert result.status == "budget_exhausted"
    assert result.receipt.rounds == bounded_query_engine.limits.max_inference_rounds

@pytest.mark.parametrize("surface,expected", [
    ("hi", {"event:greeting"}),
    ("what", {"open_variable", "query_projection"}),
    ("does", {"binder", "tense"}),
])
def test_meaning_description_is_composed_from_grounded_structure(meaning_query_engine, surface, expected):
    description = meaning_query_engine.describe_surface(surface, language="en")
    assert expected <= set(description.semantic_refs + description.contribution_kinds)
    assert description.provenance_refs
    assert description.static_gloss is None

def test_existential_witness_is_proof_local(query_engine, world_store):
    before = world_store.revision
    result = query_engine.ask(existential_query("a family relative arrived today"))
    assert result.proof.transient_witness_refs
    assert world_store.revision == before
```

- [ ] **Step 2: Run and confirm current retrieval cannot prove derived answers**

Run: `python -m pytest tests/test_query_engine.py tests/test_recursive_inference.py tests/test_inference_bounds.py -v`

Expected: FAIL before indexed rules, proof nodes, and explicit closure bounds exist.

- [ ] **Step 3: Implement query and proof artifacts**

```python
@dataclass(frozen=True)
class QueryResult:
    query_ref: str
    status: Literal["supported", "contradicted", "conflict", "unknown", "partial", "budget_exhausted"]
    bindings: tuple[tuple[str, str], ...]
    proof: ProofGraph | None
    semantic_description: SemanticDescription | None
    retrieval_receipt: RetrievalReceipt

@dataclass(frozen=True)
class SemanticDescription:
    target_refs: tuple[str, ...]
    semantic_refs: tuple[str, ...]
    contribution_kinds: tuple[str, ...]
    definition_graph_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    static_gloss: None = None

@dataclass(frozen=True)
class ProofNode:
    conclusion_ref: str
    source_fact_refs: tuple[str, ...]
    rule_ref: str | None
    premise_node_refs: tuple[str, ...]
```

Use predicate/role/argument/time/source indexes. Retrieve only rules whose heads can unify with the query or recursively opened subgoals. Memoize by `(query structure, authority revision, world revision, epistemic placement)` and record fact/rule probes.

`SemanticDescription` is constructed from the queried form's designation targets or closed-class contribution contracts, then their reviewed kinds, affordances, frames, learned/reviewed definition graph, relation neighbourhood, and operational consequences. It never reads an internal ref name or returns a stored dictionary sentence as semantic authority. This is how CEMM can explain `hi`, `what`, `does`, and newly learned aliases using the same atomic material it composes with.

- [ ] **Step 4: Encode the family example atomically**

Implement side-effect-free generic preview lowering from verified generic-definition propositions into named-role inference rules. Task 1 may validate the rules only by linking a test-only authority fixture; it exposes no production install/publish method and cannot change an active store or generation. The five family lessons derive partner/marriage structure through independently designated `mother`, `in-law`, `partner`, `lawful`, `wedded`, `wife`, and `husband` atoms. No family-specific Python branch, preseeded `mother_in_law -> married` rule, or phrase intent is permitted. Add an unseen synonym for `mother` and prove that the rules work without regeneration. Existential witnesses remain proof-local unless an independently admitted claim establishes an entity.

- [ ] **Step 5: Run, inspect proofs, and commit**

```powershell
python -m pytest tests\test_query_engine.py tests\test_recursive_inference.py tests\test_inference_bounds.py -v
git add src\cemm_authoritative_hybrid\query.py src\cemm_authoritative_hybrid\proof.py src\cemm_authoritative_hybrid\persistence.py data\authority\rule_schemas\generic_definition.json tests\test_query_engine.py tests\test_recursive_inference.py tests\test_inference_bounds.py
git rm src\cemm_authoritative_hybrid\inference.py
git commit -m "feat: prove bounded recursive queries"
```

### Task 2: Implement epistemic placement, temporal state, and transition simulation

**Files:**
- Create: `src/cemm_authoritative_hybrid/epistemics.py`
- Create: `src/cemm_authoritative_hybrid/state.py`
- Create: `tests/test_epistemic_admission.py`
- Create: `tests/test_temporal_state.py`
- Create: `tests/test_transition_simulation.py`

- [ ] **Step 1: Write failing attribution and simulation tests**

```python
def test_reported_speech_does_not_become_world_truth(runtime):
    result = runtime.process("s", "Ada said the door is open")
    occurrence = result.evaluation.claim_occurrences[0]
    assert occurrence.placement.source_ref == "entity:ada"
    assert occurrence.placement.mode == "reported"
    assert runtime.world.query(state("door", "open")).status == "unknown"

def test_simulated_transition_does_not_commit(runtime):
    before = runtime.stores.world.revision
    result = runtime.process("s", "If I open the door, will it be open?")
    assert result.evaluation.transition_previews[0].resulting_state.value_ref == "value:open"
    assert runtime.stores.world.revision == before

def test_conflicting_observations_preserve_both_sources(runtime):
    runtime.observe(state_claim("door", "open", source="sensor:a", at=10))
    runtime.observe(state_claim("door", "closed", source="sensor:b", at=10))
    result = runtime.query(state("door", "open"))
    assert result.status == "conflict"
    assert set(result.source_refs) == {"sensor:a", "sensor:b"}

def test_transition_sequence_is_typed_composition_not_state_overwrite(transition_engine, offline_state):
    first = transition_engine.preview(offline_state, "transition:power_on")
    second = transition_engine.preview(first.resulting_state, "transition:connect")
    composed = transition_engine.preview_sequence(
        offline_state, ("transition:power_on", "transition:connect")
    )
    assert composed.resulting_state == second.resulting_state
    assert composed.proof_refs == first.proof_refs + second.proof_refs
    assert transition_engine.inverse_of("transition:power_on") is None
```

- [ ] **Step 2: Run and expose any direct claim-to-world mutation**

Run: `python -m pytest tests/test_epistemic_admission.py tests/test_temporal_state.py tests/test_transition_simulation.py -v`

Expected: FAIL until claim occurrence and admission are separated.

- [ ] **Step 3: Implement occurrence, placement, and admission decisions**

Every claim records source, evidence, interval, confidence, modality, scope, and revision. `AdmissionDecision` is policy-derived and cannot be requested by a lexical token. Corrections supersede exact occurrences without deleting provenance. Belief, desire, prediction, quotation, report, and simulation remain nested placements.

- [ ] **Step 4: Implement typed state and transitions**

`TransitionEngine.preview()` checks signature and preconditions and returns predicted assertions without mutation. `preview_sequence()` composes typed transition relations left-to-right only when each resulting state satisfies the next signature; it records proof lineage and has no implicit commutativity, inverse, or overwrite law. `commit()` accepts only a verified transition/effect receipt, uses optimistic revision checks, and appends history. State indexes are keyed by entity, dimension, interval, and epistemic placement.

- [ ] **Step 5: Run and commit**

```powershell
python -m pytest tests\test_epistemic_admission.py tests\test_temporal_state.py tests\test_transition_simulation.py -v
git add src\cemm_authoritative_hybrid\epistemics.py src\cemm_authoritative_hybrid\state.py tests\test_epistemic_admission.py tests\test_temporal_state.py tests\test_transition_simulation.py
git commit -m "feat: preserve epistemic and temporal state"
```

### Task 3: Derive capabilities and route every effect through one gateway

**Files:**
- Create: `src/cemm_authoritative_hybrid/effects.py`
- Create: `src/cemm_authoritative_hybrid/capabilities.py`
- Modify: `src/cemm_authoritative_hybrid/cycle.py`
- Create: `tests/test_capability_derivation.py`
- Create: `tests/test_effect_gateway.py`
- Create: `tests/test_effect_recovery.py`

- [ ] **Step 1: Write failing capability, denial, and idempotency tests**

```python
def test_capability_is_derived_under_revision(capability_engine, context):
    result = capability_engine.check("participant:system", "event:open", context)
    assert result.status == "available"
    assert {"permission:door", "adapter:door", "resource:door"} <= set(result.proof_refs)

def test_denial_is_not_reported_as_incapacity(runtime):
    result = runtime.process("s", "open the door")
    assert result.effect_receipt.status == "denied"
    assert result.gap_receipt.kind == "permission"

def test_retry_does_not_duplicate_external_effect(gateway, counting_adapter, plan):
    first = gateway.execute(plan)
    second = gateway.execute(plan)
    assert first == second
    assert counting_adapter.calls == 1
```

- [ ] **Step 2: Run and locate any path that bypasses effect policy**

Run: `python -m pytest tests/test_capability_derivation.py tests/test_effect_gateway.py tests/test_effect_recovery.py -v`

Expected: FAIL until one proof-bearing gateway owns all effectful commits.

- [ ] **Step 3: Implement lazy capability proofs**

Capability status is derived from actor kind, event/transition signature, current state, resources, permission, policy, and adapter availability under exact revisions. The cache key contains all revisions and requested signature. Statuses distinguish `available`, `unknown`, `resource_unavailable`, `denied`, and `adapter_missing`.

- [ ] **Step 4: Implement preview, journal, invoke, observe, and commit**

```python
@dataclass(frozen=True)
class EffectPlan:
    effect_ref: str
    idempotency_key: str
    program_ref: str
    actor_ref: str
    transition_ref: str
    expected_world_revision: int
    requirement_proof_refs: tuple[str, ...]

class EffectGateway:
    def execute(self, plan: EffectPlan) -> EffectReceipt:
        decision = self.verifier.authorize(plan)
        pending = self.journal.begin_once(plan, decision)
        if pending.completed_receipt is not None:
            return pending.completed_receipt
        adapter_receipt = self.adapters.invoke(pending)
        observation = self.observations.validate(adapter_receipt)
        return self.journal.finish_and_commit(pending, observation)
```

Timeout/partial failure remains unresolved and never admits predicted success. Restart reads the journal before retry. No adapter may write semantic stores directly.

- [ ] **Step 5: Run recovery tests and commit**

```powershell
python -m pytest tests\test_capability_derivation.py tests\test_effect_gateway.py tests\test_effect_recovery.py -v
git add src\cemm_authoritative_hybrid\effects.py src\cemm_authoritative_hybrid\capabilities.py src\cemm_authoritative_hybrid\cycle.py tests\test_capability_derivation.py tests\test_effect_gateway.py tests\test_effect_recovery.py
git commit -m "feat: guard all semantic effects"
```

### Task 4: Implement typed designation learning without conversational authority escalation

**Files:**
- Create: `src/cemm_authoritative_hybrid/learning.py`
- Create: `data/authority/contracts/designation_learning.json`
- Create: `data/authority/contracts/generic_definition_acquisition.json`
- Create: `data/authority/policies/acquisition.json`
- Create: `tests/test_learning_distinctions.py`
- Create: `tests/test_learning_security.py`
- Create: `tests/test_synonym_acquisition.py`

- [ ] **Step 1: Write failing lookup/teaching/directive/event distinctions**

```python
def test_meaning_lookup_does_not_mutate(runtime):
    before = runtime.stores.revisions()
    runtime.process("s", "what does hi mean?")
    assert runtime.stores.revisions() == before

def test_untrusted_teaching_is_attributed_only(runtime):
    result = runtime.process("s", "glad means happy")
    assert result.evaluation.claim_occurrences
    assert not runtime.designations.contains("glad", "state_value:happy")

def test_reviewed_alias_inherits_target_semantics(runtime, reviewer_authorization):
    pending = runtime.process("s", "learn that cheerful means happy")
    receipt = runtime.learning.review_and_commit(pending.learning_plan, reviewer_authorization)
    assert receipt.operator_ref == "op:designation"
    assert runtime.process("s", "I am cheerful").verification.accepted

def test_reviewed_generic_definitions_publish_one_linked_generation(
    learning_coordinator, reviewed_family_programs, reviewer_authorization, authority_store
):
    before = authority_store.active
    plan = learning_coordinator.plan_reviewed_acquisition(
        reviewed_family_programs, acquisition_kind="rule"
    )
    receipt = learning_coordinator.review_and_commit(plan, reviewer_authorization.for_plan(plan))
    assert receipt.parent_generation == before.generation_ref
    assert authority_store.active_generation == receipt.new_generation
    assert receipt.authority_compatibility_hash == before.model_compatibility_hash
    assert len(receipt.created_rule_refs) >= 5

def test_one_invalid_definition_rejects_entire_acquisition(
    learning_coordinator, family_programs_with_one_invalid, reviewer_authorization, authority_store
):
    before = authority_store.active
    plan = learning_coordinator.plan_reviewed_acquisition(
        family_programs_with_one_invalid, acquisition_kind="rule"
    )
    with pytest.raises(AuthorityLinkError):
        learning_coordinator.review_and_commit(
            plan,
            reviewer_authorization.for_plan(plan),
        )
    assert authority_store.active_generation == before.generation_ref
```

- [ ] **Step 2: Run and expose any lexical write authorization**

Run: `python -m pytest tests/test_learning_distinctions.py tests/test_learning_security.py tests/test_synonym_acquisition.py -v`

Expected: FAIL until typed learning plans and trust policy exist.

- [ ] **Step 3: Implement the exact pending plan contract**

```python
@dataclass(frozen=True)
class LearningPlan:
    plan_ref: str
    contract_ref: str
    source_query_ref: str
    goal_ref: str
    capability_ref: str
    commit_operator_ref: Literal["op:designation"]
    surface_literal: str
    expected_target_kinds: tuple[str, ...]
    answer_contract_ref: str
    provenance_refs: tuple[str, ...]
    expires_at_turn: int

@dataclass(frozen=True)
class ReviewedAcquisitionPlan:
    plan_ref: str
    contract_ref: str
    verified_program_refs: tuple[str, ...]
    acquisition_kind: Literal["identity", "frame", "rule", "dimension", "transition"]
    expected_owner_ref: str
    reviewer_policy_ref: str
    provenance_refs: tuple[str, ...]
    authority_parent_generation: str
```

One pending obligation is bound to one exact `QueryResult`. A successful designation commit requires `cap:learn`, a typed `ReviewerAuthorization` bound to reviewer/policy/plan/decision/nonce/expiry, existing target identity, non-conflict, and an atomic six-phase commit receipt. Core tests receive this authorization only from a test policy issuer; Milestone 5 owns real CLI/API authentication that issues the same type. New identities, frames, rules, dimensions, and transitions use `ReviewedAcquisitionPlan`, which accepts already verified semantic programs under an independently configured reviewer policy, invokes the side-effect-free lowerer, links the complete candidate bundle, and atomically publishes a new authority generation. Conversational wording cannot select that policy. No public `install_rules`, `add_rule`, or mutable-authority shortcut exists. This reviewed path replaces the test-only Task-1 fixture in the end-to-end family lesson case; it is generic acquisition, not a family rule loader.

- [ ] **Step 4: Test poisoning, replay, ambiguity, and expiry**

Add cases for a target-kind mismatch, two meanings with inadequate margin, expired plan, replayed answer, answer from another session, attempted internal-ref lexicalization, and direct “trust me” escalation. Each must produce a learning or permission gap without mutation.

- [ ] **Step 5: Run and commit**

```powershell
python -m pytest tests\test_learning_distinctions.py tests\test_learning_security.py tests\test_synonym_acquisition.py -v
git add src\cemm_authoritative_hybrid\learning.py data\authority\contracts\designation_learning.json data\authority\contracts\generic_definition_acquisition.json data\authority\policies\acquisition.json tests\test_learning_distinctions.py tests\test_learning_security.py tests\test_synonym_acquisition.py
git commit -m "feat: acquire designations through typed plans"
```

### Task 5: Implement focus, obligations, goals, and discourse reference

**Files:**
- Create: `src/cemm_authoritative_hybrid/dialogue.py`
- Modify: `src/cemm_authoritative_hybrid/cycle.py`
- Create: `tests/test_dialogue_focus.py`
- Create: `tests/test_discourse_reference.py`
- Create: `tests/test_dialogue_obligations.py`

- [ ] **Step 1: Write failing conversation-reference tests**

```python
def test_what_did_you_say_resolves_verified_system_speech(runtime):
    first = runtime.process("s", "what is your name?")
    second = runtime.process("s", "what did you say?")
    assert second.evaluation.query_results[0].bindings == (
        ("content", first.realization_receipt.semantic_content_ref),
    )

def test_that_resolves_prior_verified_proposition(runtime):
    prior = runtime.process("s", "CEMM can learn reviewed aliases")
    result = runtime.process("s", "that's the best thing I ever heard")
    prior_claim_ref = prior.evaluation.claim_occurrences[0].proposition_ref
    assert result.verification.program.reference_bindings["that"] == prior_claim_ref

def test_unverified_output_never_enters_focus(runtime, corrupt_realizer):
    result = runtime.process("s", "what is your name?", realizer=corrupt_realizer)
    assert result.realization_receipt.status == "rejected"
    assert result.response_meaning.response_ref not in runtime.focus.refs
```

- [ ] **Step 2: Run and confirm transcript text is not semantic focus**

Run: `python -m pytest tests/test_dialogue_focus.py tests/test_discourse_reference.py tests/test_dialogue_obligations.py -v`

Expected: FAIL until focus stores verified semantic refs and reference constraints.

- [ ] **Step 3: Implement structural dialogue state**

`VerifiedSemanticFocus` stores proposition/entity/event refs plus salience evidence, participant, turn, and revision. Reference resolution applies person/number/kind/recency/scope constraints and preserves alternatives below margin. `GoalArbiter` selects among verified goals/obligations by policy; a UI intent label is derived afterward and has no control authority.

- [ ] **Step 4: Implement typed obligations**

Clarification, learning answers, requested evidence, and pending operation resolution use frozen `Obligation` records with source query, expected semantic answer contract, expiry, and completion receipt. Only one learning obligation may exist; unrelated dialogue cannot accidentally consume it.

- [ ] **Step 5: Run and commit**

```powershell
python -m pytest tests\test_dialogue_focus.py tests\test_discourse_reference.py tests\test_dialogue_obligations.py -v
git add src\cemm_authoritative_hybrid\dialogue.py src\cemm_authoritative_hybrid\cycle.py tests\test_dialogue_focus.py tests\test_discourse_reference.py tests\test_dialogue_obligations.py
git commit -m "feat: resolve semantic dialogue focus"
```

### Task 6: Generate exact response meaning and verify neural realization

**Files:**
- Create: `src/cemm_authoritative_hybrid/response.py`
- Create: `src/cemm_authoritative_hybrid/realization.py`
- Modify: `src/cemm_authoritative_hybrid/model.py`
- Modify: `src/cemm_authoritative_hybrid/training.py`
- Create: `data/bootstrap/realization_episodes.jsonl`
- Create: `configs/realizer_dev.json`
- Create: `scripts/train_realizer.py`
- Create: `artifacts/realizer_dev/model.safetensors`
- Create: `artifacts/realizer_dev/model_metadata.json`
- Create: `artifacts/realizer_dev/model_manifest.json`
- Create: `tests/test_response_meaning.py`
- Create: `tests/test_realization_verifier.py`
- Create: `tests/test_safe_realizer.py`
- Create: `tests/test_neural_realizer_weight_use.py`

- [ ] **Step 1: Write failing equivalence and safety tests**

```python
def test_response_meaning_precedes_language(runtime):
    result = runtime.process("s", "what is your name?")
    assert result.response_meaning.proposition_ref
    phases = {receipt.phase: receipt for receipt in result.trace}
    assert phases["EVALUATE"].duration_ns is not None
    assert tuple(phases) == ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE")

def test_flipped_polarity_is_rejected(realization_verifier, supported_answer):
    result = realization_verifier.verify(supported_answer, "No, that is not supported.")
    assert not result.equivalent
    assert result.mismatch_codes == ("polarity",)

@pytest.mark.parametrize("status", ["unknown", "ambiguous", "denied", "operation_failed", "realization_failed"])
def test_safe_realizer_is_limited_to_failure_actions(safe_realizer, status):
    assert safe_realizer.realize(failure_meaning(status)).status == "safe"
    with pytest.raises(UnsafeFallbackError):
        safe_realizer.realize(normal_answer_meaning())

def test_normal_realization_invokes_loaded_weights(monkeypatch, release_realizer, normal_answer_meaning):
    calls = 0
    original = release_realizer.network.forward
    def observed_forward(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(release_realizer.network, "forward", observed_forward)
    receipt = release_realizer.realize(normal_answer_meaning)
    assert calls > 0
    assert receipt.model_identity == release_realizer.model_identity

def test_zero_weight_realizer_loses_domain_generation_accuracy(release_realizer, realization_holdout):
    full = verified_realization_accuracy(release_realizer, realization_holdout)
    ablated = verified_realization_accuracy(release_realizer.with_zeroed_weights(), realization_holdout)
    assert full == 1.0
    assert ablated <= 0.50
    assert full - ablated >= 0.30

def test_normal_answer_cannot_fall_back_when_network_fails(monkeypatch, release_realizer, normal_answer_meaning):
    monkeypatch.setattr(release_realizer.network, "forward", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("sentinel")))
    receipt = release_realizer.realize(normal_answer_meaning)
    assert receipt.status == "realization_failed"
    assert receipt.surface is None
```

- [ ] **Step 2: Run and confirm current text generation has no equivalence proof**

Run: `python -m pytest tests/test_response_meaning.py tests/test_realization_verifier.py tests/test_safe_realizer.py tests/test_neural_realizer_weight_use.py -v`

Expected: FAIL until response contracts and round-trip verification exist.

- [ ] **Step 3: Implement exact response meaning**

`ResponseBuilder` maps evaluation/effect receipts to a `ResponseMeaning` containing mode, status, proposition graph refs, requested bindings, polarity, modality, epistemic status, source/proof refs, discourse action, and permitted omissions. It cannot inspect input words or select canned response text.

- [ ] **Step 4: Implement constrained neural generation and independent equivalence checking**

`NeuralConstrainedRealizer` consumes only `ResponseMeaning`, allowed designation forms, language features, and bounded dialogue style. The verifier re-orients generated text with output grammar excluded from input classification, obtains candidate programs, and proves equivalence to the response contract. Candidate failure tries the bounded neural beam; total failure invokes `SafeRealizer` only for reviewed failure meanings. Every normal realization receipt records the loaded model identity and decoder invocation count. Test-only zero-weight clones cannot pass artifact activation and exist only to prove learned-weight dependence.

- [ ] **Step 5: Train the development realizer artifact**

```powershell
python scripts\train_realizer.py --config configs\realizer_dev.json --episodes data\bootstrap\realization_episodes.jsonl --output artifacts\realizer_dev
python -m pytest tests\test_response_meaning.py tests\test_realization_verifier.py tests\test_safe_realizer.py tests\test_neural_realizer_weight_use.py -v
```

Expected: a safetensors artifact pinned to response ABI, language/designation feature ABI, dataset hash, and authority model-compatibility hash; the active full authority/designation revisions are recorded in each receipt, and all emitted accepted samples have equivalence receipts.

- [ ] **Step 6: Commit**

```powershell
git add src\cemm_authoritative_hybrid\response.py src\cemm_authoritative_hybrid\realization.py src\cemm_authoritative_hybrid\model.py src\cemm_authoritative_hybrid\training.py data\bootstrap\realization_episodes.jsonl configs\realizer_dev.json scripts\train_realizer.py tests\test_response_meaning.py tests\test_realization_verifier.py tests\test_safe_realizer.py tests\test_neural_realizer_weight_use.py artifacts\realizer_dev
git commit -m "feat: verify neural semantic realization"
```

### Task 7: Close the end-to-end persistent cognitive loop and gap matrix

**Files:**
- Modify: `src/cemm_authoritative_hybrid/cycle.py`
- Modify: `src/cemm_authoritative_hybrid/gaps.py`
- Modify: `src/cemm_authoritative_hybrid/bootstrap.py`
- Create: `tests/test_cognitive_loop_e2e.py`
- Create: `tests/test_gap_matrix.py`
- Create: `tests/test_restart_e2e.py`
- Remove: `tests/test_authority_and_inference.py`
- Remove: `tests/test_authoritative_hybrid_e2e.py`

- [ ] **Step 1: Write failing end-to-end acceptance tests**

Cover greeting and operational condition; names and aliases; reordered questions; atomic meaning lookup for `hi`, `what`, `does`, and a newly learned alias; modality; reviewed acquisition of the five conversational family definitions followed by `My mother in-law arrived today` / `Am I married?`; attributed speech and attributed denial under contrast; `what did you say`; demonstratives; correction; past/current state intervals; simulation; capability; denial; successful operation; adapter failure; learning continuation; unknown surface; polysemy with preserved alternatives; incompatible multi-anchor/residual cases; and restart after a pending/committed effect. Assert program, coverage, learned-rule provenance, proof, placement, effect, response meaning, gap, and realization receipt—not response text alone.

- [ ] **Step 2: Parameterize all 18 gap kinds**

```python
@pytest.mark.parametrize("kind,owner", [
    ("evidence", "data"), ("designation", "data"), ("reference", "training"),
    ("authority", "authority"), ("proposal", "training"), ("verification", "runtime"),
    ("inference", "runtime"), ("state", "data"), ("transition", "authority"),
    ("learning", "policy"), ("resource", "data"), ("permission", "policy"),
    ("adapter", "adapter"), ("operation", "adapter"), ("storage", "runtime"),
    ("realization", "training"), ("performance", "runtime"), ("implementation", "runtime"),
])
def test_gap_has_exact_owner_and_safe_action(gap_case, kind, owner):
    receipt = gap_case(kind, owner)
    assert receipt.kind == kind
    assert receipt.recommended_owner == owner
    assert receipt.safe_response_action
```

These are canonical fixtures, not one universal owner per kind. Add branch cases required by the design: reference ambiguity with an existing candidate routes to training while an absent identity/frame routes to authority; missing transition routes to authority while an exhausted proof bound routes to runtime; resource absence, permission denial, and adapter failure remain distinct.

Parameterize the closed `CycleStatus` vocabulary as well and prove that every status is reachable from a typed decision/gap fixture, while no status is selected from response wording or a phrase label.

- [ ] **Step 3: Integrate phases without hidden fallback**

Finalize the result contract now that every owner exists:

```python
@dataclass(frozen=True)
class CycleResult:
    cycle_ref: str
    status: CycleStatus
    orientation: Orientation
    proposal: ProposalResult
    verification: VerificationResult
    evaluation: Decision
    effect_receipt: EffectReceipt | None
    response_meaning: ResponseMeaning
    realization_receipt: RealizationReceipt
    gap_receipt: GapReceipt | None
    trace: tuple[PhaseReceipt, ...]
    final_revision_pin: RevisionPin
```

`HybridRuntime.process()` executes six phase methods once, carrying immutable artifacts forward. Stale revisions restart at `ORIENT` within `max_operation_reentry`; all other failures stop at their earliest owner. An already committed effect remains journaled if realization fails. No broad exception converts an implementation error into clarification. `KernelCycleResult` remains an internal typed-fixture test artifact and is not exported by the release runtime.

The CLI/API serializers accept only `CycleStatus` values. Add property tests that construction and transport decoding reject any other string before it can become an externally reachable result.

After mapping every still-valid assertion to the new query/proof/cognitive-loop tests, delete `tests/test_authority_and_inference.py` and `tests/test_authoritative_hybrid_e2e.py`; neither legacy program families nor legacy response wording remains an acceptance oracle.

- [ ] **Step 4: Run restart and full cognitive tests**

```powershell
python -m pytest tests\test_cognitive_loop_e2e.py tests\test_gap_matrix.py tests\test_restart_e2e.py -v
python -m pytest -q
python scripts\validate_mvp.py --profile milestone-3 --output artifacts\validation\MILESTONE_RECEIPT.json
rg -n "except Exception.*clarif|fallback.*answer|raw_text.*(mode|goal|operator)|intent.*dispatch" src tests
git diff --check
```

Expected: all tests pass, all 18 gap owners are reachable, the forbidden search is empty, and restart preserves exact revisions/effects.

- [ ] **Step 5: Commit the milestone**

```powershell
git add -A
git commit -m "feat: complete persistent semantic cognition"
git status --short
```

Expected: clean working tree and a milestone receipt pinned to authority, model, world schema, and ABI identities.
