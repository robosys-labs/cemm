# Milestone 2 Universal Hybrid Proposal and Verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every task and superpowers:verification-before-completion before the milestone commit. Track work with the checkboxes below.

**Goal:** Convert reversible form evidence into bounded, recursively composed `SemanticSwitchProgram` candidates, then accept only programs whose identity, ports, scope, coverage, and action sequence are exact-authority legal.

**Architecture:** `ORIENT` builds a revision-pinned structural view; a proposal model selects only indexed contribution/action IDs; `VERIFY` independently reconstructs legality and complete source coverage. `BootstrapProposer` is a deterministic oracle for tests and episode construction only. The running product must load a safetensors-backed `NeuralSwitchProposer`.

**Tech Stack:** Python 3.13, frozen dataclasses, PyTorch, safetensors, canonical JSON, pytest, Hypothesis.

---

### Task 1: Replace phrase parsing with reversible form evidence and bounded grounding

**Files:**
- Rewrite: `src/cemm_authoritative_hybrid/forms.py`
- Create: `src/cemm_authoritative_hybrid/grounding.py`
- Modify: `data/languages/en/forms.json`
- Create: `tests/test_form_lattice.py`
- Create: `tests/test_grounding.py`
- Remove: tests that assert phrase templates, regex intents, or raw-token operator selection

- [ ] **Step 1: Write failing reversibility and unseen-synonym tests**

```python
def test_form_lattice_preserves_every_source_unit(form_resolver):
    lattice = form_resolver.resolve("And you are called what?")
    assert "".join(unit.source_text for unit in lattice.units) == "And you are called what?"
    assert all(unit.source_start < unit.source_end for unit in lattice.units)
    assert len(lattice.hypotheses) <= 16

def test_new_designation_uses_target_affordance_without_pack_regeneration(
    grounder, designation_store, form_pack_hash
):
    designation_store.commit_reviewed("progenitor", "concept:mother")
    result = grounder.ground_text("progenitor")
    assert result.designations[0].target_ref == "concept:mother"
    assert grounder.form_pack_hash == form_pack_hash

def test_unknown_surface_is_typed_not_manufactured(grounder):
    result = grounder.ground_text("zorbulate")
    assert result.designations == ()
    assert result.unresolved[0].kind == "designation"
    assert "concept:zorbulate" not in result.created_refs

def test_reviewed_sensor_evidence_enters_same_semantic_plane(grounder, door_sensor_evidence):
    result = grounder.ground(door_sensor_evidence)
    assert result.designations[0].target_ref == "entity:door"
    assert result.grounded_items[0].source_kind == "sensor"
    assert result.provenance_refs == (door_sensor_evidence.adapter_receipt_ref,)
```

- [ ] **Step 2: Run and observe the earliest failure**

Run: `python -m pytest tests/test_form_lattice.py tests/test_grounding.py -v`

Expected: FAIL because the existing tokenizer/compiler does not preserve a source lattice and open-class learning is coupled to candidate families.

- [ ] **Step 3: Implement frozen form and grounding artifacts**

```python
@dataclass(frozen=True)
class FormUnit:
    unit_ref: str
    source_text: str
    normalized_forms: tuple[str, ...]
    source_start: int
    source_end: int
    features: tuple[tuple[str, str], ...]

@dataclass(frozen=True)
class DesignationCandidate:
    unit_refs: tuple[str, ...]
    target_ref: str
    designation_fact_ref: str
    score: float
    provenance_refs: tuple[str, ...]
```

`EvidencePacket` accepts typed text, reviewed sensor/entity-resolution evidence, and prior operation observations. `FormResolver` owns only text tokenisation, morphology, punctuation, closed-class evidence, and bounded construction annotations. `Grounder` performs indexed exact-designation lookup, participant/deictic binding, or adapter-schema-pinned nonlinguistic grounding. Every evidence item keeps source/provenance and reaches the same contribution plane. Neither component chooses an operator or inspects internal ref spelling.

- [ ] **Step 4: Validate bounds and language-pack ownership**

Add Hypothesis tests proving that no unit is lost, span offsets remain monotonic, designation candidates never exceed `max_designations_per_span`, and adding a designation changes the authority generation but not `data/languages/en/forms.json`.

- [ ] **Step 5: Remove obsolete phrase owners, run, and commit**

```powershell
python -m pytest tests\test_form_lattice.py tests\test_grounding.py -v
rg -n "phrase_template|regex_intent|surface.*operator|function_forms.*learn" src data\authority data\languages
git add src\cemm_authoritative_hybrid\forms.py src\cemm_authoritative_hybrid\grounding.py data\languages\en\forms.json tests\test_form_lattice.py tests\test_grounding.py
git commit -m "feat: ground reversible form evidence"
```

Expected: tests pass; the search has no production semantic dispatch hit.

### Task 2: Derive affordances, contributions, and structural self projection

**Files:**
- Create: `src/cemm_authoritative_hybrid/affordances.py`
- Create: `src/cemm_authoritative_hybrid/contributions.py`
- Modify: `src/cemm_authoritative_hybrid/cycle.py`
- Create: `data/authority/frames/semantic_affordances.json`
- Create: `tests/test_affordances.py`
- Create: `tests/test_orientation_projection.py`

- [ ] **Step 1: Write failing kind-derived affordance tests**

```python
def test_synonyms_inherit_identical_affordances(affordance_index):
    mother = affordance_index.for_target("concept:mother")
    assert mother == affordance_index.for_designation("progenitor")

def test_ref_name_cannot_create_affordance(affordance_index):
    assert affordance_index.for_unlinked_ref("event:learn") == ()

def test_orientation_projects_self_other_and_reachable_context(runtime):
    orientation = runtime.orient("session:one", "what did you say?")
    assert orientation.participants == ("participant:system", "participant:user")
    assert orientation.active_turn_ref in orientation.event_refs
    assert orientation.focus_refs
    assert orientation.revision_pin.authority_generation
    assert orientation.scanned_atom_count == 0
```

- [ ] **Step 2: Run and confirm affordance ownership is absent**

Run: `python -m pytest tests/test_affordances.py tests/test_orientation_projection.py -v`

Expected: FAIL before `SemanticAffordanceIndex` and reachable-context projection exist.

- [ ] **Step 3: Implement the closed transient contribution ABI**

```python
ContributionKind = Literal[
    "anchor", "predicate", "binder", "reference", "scope",
    "discourse", "connector", "qualifier", "literal", "open_variable",
]

@dataclass(frozen=True)
class SemanticContribution:
    contribution_ref: str
    kind: ContributionKind
    source_unit_refs: tuple[str, ...]
    target_ref: str | None
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    constraints: tuple[tuple[str, str], ...]
```

Defaults are indexed by semantic kind. Reviewed frame atoms may refine them only when generation-pinned and linked. Limit profiles per target and contributions per source unit using `RuntimeConfig`.

- [ ] **Step 4: Implement bounded ORIENT projection**

Projection starts from participants, active turn/session events, verified focus, open obligations, and relevant goals. It traverses indexed typed relations within the configured depth and records index probes, visited refs, cache key, and revision pin. Entity, concept, relation, state, and event identities remain independently addressable; events do not become a universal wrapper.

- [ ] **Step 5: Run anti-bloat tests and commit**

```powershell
python -m pytest tests\test_affordances.py tests\test_orientation_projection.py -v
git add src\cemm_authoritative_hybrid\affordances.py src\cemm_authoritative_hybrid\contributions.py src\cemm_authoritative_hybrid\cycle.py data\authority\frames\semantic_affordances.json tests\test_affordances.py tests\test_orientation_projection.py
git commit -m "feat: derive semantic contribution ports"
```

### Task 3: Define the recursive Semantic Switch Program and exact coverage ABI

**Files:**
- Create: `src/cemm_authoritative_hybrid/programs.py`
- Create: `src/cemm_authoritative_hybrid/coverage.py`
- Create: `tests/test_program_abi.py`
- Create: `tests/test_coverage.py`

- [ ] **Step 1: Write failing action and one-consumption tests**

```python
def test_program_uses_only_five_persistent_operators(program_factory):
    program = program_factory("what is your name?")
    assert set(program.persistent_operators) <= {
        "op:designation", "op:type", "op:relation", "op:state", "op:event"
    }

def test_switch_action_vocabulary_matches_confirmed_abi_exactly():
    assert SWITCH_ACTION_TYPES == (
        "select_context", "select_mode", "select_designation", "instantiate_operator",
        "bind_role", "bind_reference", "bind_nested_application", "attach_scope",
        "project_variable", "propose_transition", "complete_program", "abstain",
    )

def test_every_source_unit_is_consumed_once_or_one_residual(coverage_verifier, case):
    receipt = coverage_verifier.verify(case.lattice, case.program)
    assert receipt.duplicate_unit_refs == ()
    assert receipt.missing_unit_refs == ()
    assert set(receipt.assigned_unit_refs).isdisjoint(receipt.residual_unit_refs)

def test_source_assignments_are_inside_serialized_program(valid_program, canonical_round_trip):
    restored = canonical_round_trip(valid_program, SemanticSwitchProgram)
    assert restored.source_assignments == valid_program.source_assignments
    assert {row.source_unit_ref for row in restored.source_assignments} == set(valid_program.source_unit_refs)

def test_missing_or_duplicate_program_assignment_is_rejected(verifier, valid_program):
    assert verifier.verify(with_assignment_removed(valid_program)).errors[0].code == "missing_source_assignment"
    assert verifier.verify(with_assignment_duplicated(valid_program)).errors[0].code == "duplicate_source_assignment"

def test_critical_residual_rejects_execution(coverage_verifier, negated_effect_case):
    receipt = coverage_verifier.verify(*negated_effect_case)
    assert not receipt.executable
    assert receipt.critical_residuals[0].contribution_kind == "scope"
```

- [ ] **Step 2: Run and confirm the old candidate representation cannot express the ABI**

Run: `python -m pytest tests/test_program_abi.py tests/test_coverage.py -v`

Expected: FAIL because candidate families do not provide typed recursive actions or exact source assignment.

- [ ] **Step 3: Implement the bounded program representation**

```python
@dataclass(frozen=True)
class ProgramAction:
    action_ref: str
    action_type: Literal[
        "select_context", "select_mode", "select_designation", "instantiate_operator",
        "bind_role", "bind_reference", "bind_nested_application", "attach_scope",
        "project_variable", "propose_transition", "complete_program", "abstain"
    ]
    arguments: tuple[str, ...]
    source_unit_refs: tuple[str, ...]

@dataclass(frozen=True)
class SourceAssignment:
    assignment_ref: str
    source_unit_ref: str
    contribution_ref: str
    assignment_kind: Literal["role", "reference", "scope", "qualifier", "discourse", "residual"]
    target_ref: str | None
    residual_kind: ContributionKind | None
    critical: bool

@dataclass(frozen=True)
class SemanticSwitchProgram:
    program_ref: str
    orientation_ref: str
    actions: tuple[ProgramAction, ...]
    root_graph_refs: tuple[str, ...]
    mode_ref: str
    goal_refs: tuple[str, ...]
    source_unit_refs: tuple[str, ...]
    source_assignments: tuple[SourceAssignment, ...]
    revision_pin: RevisionPin
```

This 12-action vocabulary is copied exactly from the confirmed `SemanticSwitchProgram` contract and is closed; synonyms or replacement actions are an ABI change. Exact source assignments, including typed residuals, are immutable serialized fields of the completed program—not inferred or appended by `CoverageVerifier`. Role/reference/scope actions establish consumed assignments; `complete_program` carries an explicit bounded residual-assignment table for every remaining source unit without creating a thirteenth action type. `CoverageVerifier` only validates this table. Structural action IDs are derived from the ABI plus reviewed role/kind schemas, sorted canonically, and hashed into `action_encoding_hash`; dynamic designation, target, contribution, and context selections use bounded pointer slots. Adding a designation to an existing identity therefore changes the designation/world revision but neither expands the action vocabulary nor requires model retraining. Programs are limited by action count, nesting depth, application count, and beam/search bounds.

- [ ] **Step 4: Implement exact coverage receipts**

`CoverageVerifier` proves the program already contains exactly one assignment per source unit, valid contribution-to-port binding, explicit typed residuals, and correct criticality; it never repairs or synthesizes an assignment. Punctuation/discourse may be noncritical only under reviewed form rules. Negation, modality, reference, unknown anchors, and effect-related evidence are always critical until consumed.

- [ ] **Step 5: Run property tests and commit**

```powershell
python -m pytest tests\test_program_abi.py tests\test_coverage.py -v
git add src\cemm_authoritative_hybrid\programs.py src\cemm_authoritative_hybrid\coverage.py tests\test_program_abi.py tests\test_coverage.py
git commit -m "feat: define recursive switch programs"
```

### Task 4: Implement the independent exact verifier and constrained action masks

**Files:**
- Rewrite: `src/cemm_authoritative_hybrid/verifier.py`
- Create: `tests/test_exact_verifier.py`
- Create: `tests/test_action_masks.py`
- Create: `tests/test_adversarial_programs.py`

- [ ] **Step 1: Write failing legality and tamper tests**

```python
@pytest.mark.parametrize("mutation", [
    "unknown_ref", "wrong_kind", "missing_role", "duplicate_role",
    "scope_cycle", "stale_revision", "excess_depth", "uncovered_unit",
])
def test_mutated_program_is_rejected(verifier, valid_program, mutation):
    result = verifier.verify(mutate(valid_program, mutation))
    assert not result.accepted
    assert result.errors[0].code == mutation

def test_decoder_mask_matches_verifier_legal_next_actions(masker, verifier, prefix):
    masked = set(masker.legal_next_action_ids(prefix))
    exhaustive = set(verifier.enumerate_legal_next_action_ids(prefix))
    assert masked == exhaustive
```

- [ ] **Step 2: Run and expose any verifier dependence on candidate score/family**

Run: `python -m pytest tests/test_exact_verifier.py tests/test_action_masks.py tests/test_adversarial_programs.py -v`

Expected: FAIL until exact action-level validation exists.

- [ ] **Step 3: Implement ordered verification**

Verification order is: ABI/hash/revision, action syntax, referenced identity existence, semantic kind, port compatibility, cardinality, scope acyclicity, graph depth, coverage, mode/goal legality, then effect requirements. The verifier never reads proposal logits and never repairs a program.

- [ ] **Step 4: Implement prefix masks from the same legal transition relation**

Expose an immutable `LegalActionIndex` constructed during authority activation. Both exhaustive verifier tests and neural decoding masks call the same pure transition predicate with separate enumeration code paths, preventing a learned decoder from emitting structurally impossible actions.

- [ ] **Step 5: Run mutation/property tests and commit**

```powershell
python -m pytest tests\test_exact_verifier.py tests\test_action_masks.py tests\test_adversarial_programs.py -v
git add src\cemm_authoritative_hybrid\verifier.py tests\test_exact_verifier.py tests\test_action_masks.py tests\test_adversarial_programs.py
git commit -m "feat: verify semantic programs exactly"
```

### Task 5: Build the deterministic proposal oracle and semantic episode seed

**Files:**
- Create: `src/cemm_authoritative_hybrid/proposal.py`
- Create: `data/bootstrap/proposal_episodes.jsonl`
- Create: `scripts/build_bootstrap_episodes.py`
- Create: `tests/test_bootstrap_proposer.py`
- Create: `tests/test_bootstrap_episode_generation.py`

- [ ] **Step 1: Write failing generic-composition tests**

```python
@pytest.mark.parametrize("surface", [
    "what is your name?", "your name is what?", "what are you called?",
    "and you are called what?", "can I call you CEMM?",
    "I can call you CEMM, right?",
])
def test_paraphrases_compile_without_phrase_families(bootstrap_proposer, surface):
    proposals = bootstrap_proposer.propose(orient(surface))
    assert any(exact_verifier.verify(p).accepted for p in proposals)
    assert all(not hasattr(p, "family") for p in proposals)
```

- [ ] **Step 2: Run and confirm generic search is missing**

Run: `python -m pytest tests/test_bootstrap_proposer.py tests/test_bootstrap_episode_generation.py -v`

Expected: FAIL before the bounded contribution-port search exists.

- [ ] **Step 3: Implement `ProposalModel` and deterministic bounded search**

```python
class ProposalModel(Protocol):
    model_identity: str
    def propose(self, orientation: Orientation) -> ProposalResult:
        raise NotImplementedError

@dataclass(frozen=True)
class ProposalResult:
    candidates: tuple[SemanticSwitchProgram, ...]
    explored_states: int
    truncated: bool
    model_identity: str
```

`BootstrapProposer` searches legal action prefixes using indexed contributions and ports. It has no phrase inventory and no word/regex branch. Canonical tie-breaking makes episode generation deterministic. It raises if constructed by the release runtime factory.

- [ ] **Step 4: Generate and validate bootstrap episodes**

The generator records form lattice, orientation projection, action sequence, rejected legal alternatives, coverage, and authority/action hashes. Two runs must be byte-identical. Include word-order, synonym, modality, reference, scope, teaching, query, and typed-gap seeds.

- [ ] **Step 5: Run, regenerate, and commit**

```powershell
python scripts\build_bootstrap_episodes.py --output data\bootstrap\proposal_episodes.jsonl
python -m pytest tests\test_bootstrap_proposer.py tests\test_bootstrap_episode_generation.py -v
git add src\cemm_authoritative_hybrid\proposal.py scripts\build_bootstrap_episodes.py data\bootstrap\proposal_episodes.jsonl tests\test_bootstrap_proposer.py tests\test_bootstrap_episode_generation.py
git commit -m "feat: generate verified proposal episodes"
```

### Task 6: Train and cut over to the neural switch proposer

**Files:**
- Rewrite: `src/cemm_authoritative_hybrid/model.py`
- Rewrite: `src/cemm_authoritative_hybrid/training.py`
- Modify: `src/cemm_authoritative_hybrid/bootstrap.py`
- Modify: `src/cemm_authoritative_hybrid/cycle.py`
- Create: `configs/proposal_dev.json`
- Create: `scripts/train_proposer.py`
- Create: `artifacts/proposal_dev/model.safetensors`
- Create: `artifacts/proposal_dev/model_metadata.json`
- Create: `artifacts/proposal_dev/model_manifest.json`
- Create: `tests/test_neural_proposer.py`
- Create: `tests/test_neural_weight_use.py`
- Create: `tests/test_production_proposer_cutover.py`
- Remove: `src/cemm_authoritative_hybrid/compiler.py`
- Remove: `src/cemm_authoritative_hybrid/retrieval.py`
- Remove: `src/cemm_authoritative_hybrid/graph_actions.py`
- Remove: `src/cemm_authoritative_hybrid/types.py`
- Remove: `tests/test_neural_workstream.py`

- [ ] **Step 1: Write failing neural artifact and production-cutover tests**

```python
def test_release_runtime_requires_neural_switch_proposer(release_factory):
    runtime = release_factory()
    assert isinstance(runtime.proposal_model, NeuralSwitchProposer)
    assert runtime.proposal_model.metadata.action_encoding_hash == runtime.action_encoding_hash

def test_neural_decoder_never_emits_masked_action(trained_proposer, orientations):
    for orientation in orientations:
        result = trained_proposer.propose(orientation)
        assert result.candidates
        assert all(exact_verifier.verify(p).well_formed for p in result.candidates)

def test_internal_ref_spelling_does_not_affect_model_logits(
    trained_proposer, alpha_equivalent_orientations
):
    original, renamed = alpha_equivalent_orientations
    assert original.target_refs != renamed.target_refs
    assert trained_proposer.structural_logits(original) == trained_proposer.structural_logits(renamed)

def test_proposal_model_capacity_is_bounded(trained_proposer):
    assert trained_proposer.trainable_parameter_count <= 25_000_000

def test_compatible_new_designation_keeps_model_active(release_factory, designation_store):
    runtime = release_factory()
    model_identity = runtime.proposal_model.model_identity
    designation_store.commit_reviewed("cheerful", "state_value:happy")
    runtime.refresh_compatible_generation()
    assert runtime.proposal_model.model_identity == model_identity
    assert runtime.propose_and_verify("s", "I am cheerful").accepted

def test_release_proposal_invokes_loaded_weights(monkeypatch, release_factory):
    runtime = release_factory()
    calls = 0
    original = runtime.proposal_model.network.forward
    def observed_forward(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(runtime.proposal_model.network, "forward", observed_forward)
    result = runtime.propose_and_verify("s", "your name is what?")
    assert calls > 0
    assert result.proposal.model_identity == runtime.proposal_model.model_identity

def test_weight_ablation_breaks_learned_selection(release_factory, structural_holdout):
    runtime = release_factory()
    full = exact_program_accuracy(runtime, structural_holdout)
    ablated = exact_program_accuracy(runtime.with_zeroed_proposal_weights(), structural_holdout)
    assert full >= 0.90
    assert ablated <= 0.50
    assert full - ablated >= 0.30

def test_release_path_does_not_delegate_to_bootstrap(monkeypatch, release_factory):
    monkeypatch.setattr(BootstrapProposer, "propose", lambda *args: (_ for _ in ()).throw(AssertionError("bootstrap called")))
    assert release_factory().propose_and_verify("s", "what is your name?").accepted

def test_legacy_candidate_api_is_absent():
    import cemm_authoritative_hybrid as package
    assert not hasattr(package, "CandidateGenerator")
```

- [ ] **Step 2: Run and confirm production still depends on the legacy ranker**

Run: `python -m pytest tests/test_neural_proposer.py tests/test_neural_weight_use.py tests/test_production_proposer_cutover.py -v`

Expected: FAIL until the new model is trained and wired.

- [ ] **Step 3: Implement the constrained sequence model**

Encode reversible character/subword form evidence, closed-class features, anonymized dynamic target slots, contribution kinds/ports, bounded orientation features, and current legal prefix state. Semantic refs are never tokenized by their spelling. Decode structural action IDs plus pointer selections into the current designation/contribution/context tables under `LegalActionIndex` masks, so a newly reviewed alias or authority target can be used without changing the neural vocabulary or retraining. Logits rank legal alternatives only; exact acceptance remains in `ExactProgramVerifier`. Calibration metadata stores temperature and minimum accepted margin. Proposal and realization models together are capped at 50 million trainable parameters for this MVP; actual parameter and memory counts enter the benchmark receipt. The release factory calls the loaded network directly and has no bootstrap/static delegate; artifact identity is recorded on every `ProposalResult`.

- [ ] **Step 4: Train and publish the development artifact safely**

```powershell
python scripts\train_proposer.py --config configs\proposal_dev.json --episodes data\bootstrap\proposal_episodes.jsonl --output artifacts\proposal_dev
python scripts\validate_mvp.py --profile proposal --output artifacts\validation\M2_PROPOSAL_RECEIPT.json
```

Expected: `model.safetensors`, canonical metadata, manifest, complete SHA-256 identity, authority model-compatibility hash, action-encoding hash, dataset hash, seed, dependency versions, and calibration values are present. The activation receipt separately records the current full authority generation hash.

- [ ] **Step 5: Delete the old semantic path**

Remove `CandidateGenerator`, candidate `.family`, phrase compiler routing, graph-action ranker loading, old `.pt` fixtures, compatibility branches, and tests whose only purpose is retaining those types. Delete the four named legacy modules and `tests/test_neural_workstream.py` only after still-valid masking, ranking, holdout, and artifact assertions have exact replacements in the new M2 tests.

- [ ] **Step 6: Run the milestone gate and commit**

```powershell
python -m pytest tests\test_form_lattice.py tests\test_grounding.py tests\test_affordances.py tests\test_orientation_projection.py tests\test_program_abi.py tests\test_coverage.py tests\test_exact_verifier.py tests\test_action_masks.py tests\test_adversarial_programs.py tests\test_bootstrap_proposer.py tests\test_bootstrap_episode_generation.py tests\test_neural_proposer.py tests\test_neural_weight_use.py tests\test_production_proposer_cutover.py -v
python -m pytest -q
rg -n "CandidateGenerator|candidate\.family|graph_action_ranker|torch\.load\(|phrase_intent|Stage [0-9]" src
python scripts\validate_mvp.py --profile milestone-2 --output artifacts\validation\MILESTONE_RECEIPT.json
git diff --check
git add -A
git commit -m "feat: propose verified semantic switch programs"
```

Expected: all tests pass, forbidden-source search is empty, the receipt pins the neural artifact and records the full-versus-zero-weight accuracy drop, and the working tree is clean.
