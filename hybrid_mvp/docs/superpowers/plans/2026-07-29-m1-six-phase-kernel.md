# Milestone 1 Constitutional Six-Phase Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace legacy activation assumptions with the five-operator, six-phase constitutional kernel, safe artifact identity, linked authority, typed gaps, and crash-consistent reference persistence.

**Architecture:** The milestone exposes a typed cycle over injected proposal/evaluation fixtures without advertising language competence yet. It removes unsafe checkpoint loading immediately and establishes the exact stores, revisions, phase artifacts, and activation checks required by every later milestone.

**Tech Stack:** Python 3.13, frozen dataclasses, canonical JSON, hashlib, safetensors, SQLite WAL, pytest, Hypothesis.

---

### Task 1: Install the hard-cutover constitution and frozen configuration

**Files:**
- Create: `AGENTS.md`
- Create: `docs/ABI_REGISTRY.md`
- Create: `src/cemm_authoritative_hybrid/config.py`
- Create: `tests/test_constitution.py`
- Create: `tests/test_config.py`
- Rewrite: `tests/conftest.py`
- Modify: `README.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing constitutional tests**

```python
from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_active_contract_is_six_phase_and_hard_cutover():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for phase in ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"):
        assert phase in text
    assert "Stage 0–22 ordering is not an activation invariant" in text
    assert "Runtime cutover: hard" in text

def test_exactly_five_persistent_operators_are_declared():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert text.count("op:designation") == 1
    for operator in ("op:type", "op:relation", "op:state", "op:event"):
        assert operator in text
```

- [ ] **Step 2: Run the tests and confirm the contract is absent**

Run: `python -m pytest tests/test_constitution.py -v`

Expected: FAIL because `AGENTS.md` does not exist.

- [ ] **Step 3: Write the constitution and ABI registry**

`AGENTS.md` copies the confirmed laws from the completion design and declares these active ABIs:

```text
Semantic Contribution ABI: 1
Semantic Switch Program ABI: 1
Coverage ABI: 1
Phase Receipt ABI: 1
Gap Receipt ABI: 1
Learning Plan ABI: 1
Response Meaning ABI: 1
Realization Receipt ABI: 1
```

It explicitly forbids stage-number ownership, compatibility runtime branches, raw-surface semantic dispatch, internal-ref lexicalization, implicit atom creation, unverified effects, and unverified response focus. `docs/ABI_REGISTRY.md` records owner file, serialized/transient status, validator, and activation gate for each ABI.

Set pytest `xfail_strict = true` and `--strict-markers` in `pyproject.toml`; no active release test may use skip/xfail markers.

- [ ] **Step 4: Write failing configuration tests**

```python
import dataclasses
from cemm_authoritative_hybrid.config import ABIRegistry, RuntimeConfig

def test_release_configuration_is_frozen_and_bounded():
    config = RuntimeConfig.release()
    assert config.abis == ABIRegistry(1, 1, 1, 1, 1, 1, 1, 1)
    assert config.max_input_tokens == 64
    assert config.max_complete_candidates == 48
    assert config.max_applications == 24
    assert config.max_graph_depth == 6
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.max_graph_depth = 7
```

- [ ] **Step 5: Implement the frozen configuration**

```python
@dataclass(frozen=True)
class ABIRegistry:
    contribution: int = 1
    switch_program: int = 1
    coverage: int = 1
    phase_receipt: int = 1
    gap_receipt: int = 1
    learning_plan: int = 1
    response_meaning: int = 1
    realization_receipt: int = 1

@dataclass(frozen=True)
class RuntimeConfig:
    abis: ABIRegistry = field(default_factory=ABIRegistry)
    max_input_tokens: int = 64
    max_designations_per_span: int = 8
    max_affordances_per_target: int = 4
    max_orientation_alternatives: int = 16
    max_beam_states: int = 32
    max_complete_candidates: int = 48
    max_applications: int = 24
    max_graph_depth: int = 6
    max_inference_rounds: int = 6
    max_inference_facts: int = 256
    max_inference_rules: int = 64
    max_learning_obligations: int = 1
    max_operation_reentry: int = 1

    def __post_init__(self) -> None:
        values = [v for v in vars(self).values() if isinstance(v, int)]
        if any(v <= 0 for v in values):
            raise ValueError("runtime bounds must be positive")

    @classmethod
    def release(cls) -> "RuntimeConfig":
        return cls()
```

- [ ] **Step 6: Run and commit**

```powershell
python -m pytest tests\test_constitution.py tests\test_config.py -v
git add AGENTS.md README.md pyproject.toml docs\ABI_REGISTRY.md src\cemm_authoritative_hybrid\config.py tests\conftest.py tests\test_constitution.py tests\test_config.py
git commit -m "docs: govern the six-phase semantic kernel"
```

Expected: tests pass and the commit contains no legacy compatibility promise.

### Task 2: Add canonical identity and safe model artifacts

**Files:**
- Create: `src/cemm_authoritative_hybrid/canonical.py`
- Create: `src/cemm_authoritative_hybrid/artifacts.py`
- Rewrite: `src/cemm_authoritative_hybrid/model.py`
- Rewrite: `src/cemm_authoritative_hybrid/training.py`
- Create: `tests/test_canonical.py`
- Create: `tests/test_artifact_security.py`
- Create: `requirements-model.lock`
- Create: `requirements.lock`
- Remove: `requirements.txt`

- [ ] **Step 1: Write failing canonical and tamper tests**

```python
from cemm_authoritative_hybrid.canonical import canonical_bytes, stable_ref
from cemm_authoritative_hybrid.artifacts import ArtifactError, load_model_artifact

def test_mapping_order_does_not_change_identity():
    assert canonical_bytes({"b": 2, "a": 1}) == canonical_bytes({"a": 1, "b": 2})
    assert stable_ref("fact", {"b": 2, "a": 1}) == stable_ref("fact", {"a": 1, "b": 2})

def test_tail_tamper_fails_before_tensor_use(model_artifact):
    payload = bytearray(model_artifact.weights.read_bytes())
    payload[-1] ^= 1
    model_artifact.weights.write_bytes(payload)
    with pytest.raises(ArtifactError, match="weights hash"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)

def test_model_dependency_lock_mismatch_fails_before_tensor_use(model_artifact, monkeypatch):
    monkeypatch.setattr("cemm_authoritative_hybrid.artifacts.current_model_lock_hash", lambda: "0" * 64)
    with pytest.raises(ArtifactError, match="dependency lock"):
        load_model_artifact(model_artifact.root, model_artifact.manifest_sha256)
```

- [ ] **Step 2: Run and reproduce unsafe legacy loading**

Run: `python -m pytest tests/test_canonical.py tests/test_artifact_security.py -v`

Expected: FAIL; current startup uses `torch.load(..., weights_only=False)` and canonical helpers do not exist.

- [ ] **Step 3: Implement canonical serialization and complete tensor identity**

`canonical.py` serializes primitives, dataclasses, mappings, sets, tuples, and decimals with sorted keys and explicit type tags. `stable_ref(namespace, payload)` hashes namespace plus canonical bytes. Tensor identity hashes sorted name, dtype, shape, and every contiguous CPU byte.

```python
def stable_ref(namespace: str, payload: object) -> str:
    digest = hashlib.sha256(namespace.encode("utf-8") + b"\0" + canonical_bytes(payload)).hexdigest()
    return f"{namespace}:{digest[:24]}"
```

- [ ] **Step 4: Implement the safe artifact contract**

```python
@dataclass(frozen=True)
class ModelMetadata:
    model_kind: Literal["proposal", "realization", "joint"]
    model_identity: str
    authority_compatibility_hash: str
    action_encoding_hash: str
    dataset_hash: str
    model_dependency_lock_sha256: str
    python_abi: str
    source_revision: str
    abi_registry: Mapping[str, int]
    config: Mapping[str, object]

def load_model_artifact(root: Path, expected_manifest_sha256: str, device: str = "cpu"):
    manifest_path = root / "model_manifest.json"
    if sha256_file(manifest_path) != expected_manifest_sha256:
        raise ArtifactError("manifest hash mismatch")
    manifest = parse_manifest(manifest_path)
    verify_file_hash(root / "model_metadata.json", manifest.metadata_sha256)
    verify_file_hash(root / "model.safetensors", manifest.weights_sha256)
    metadata = ModelMetadata(**read_canonical_json(root / "model_metadata.json"))
    if metadata.model_dependency_lock_sha256 != current_model_lock_hash():
        raise ArtifactError("dependency lock mismatch")
    if metadata.python_abi != current_python_abi():
        raise ArtifactError("python ABI mismatch")
    tensors = safetensors.torch.load_file(str(root / "model.safetensors"), device=device)
    if fingerprint_model(metadata, tensors) != metadata.model_identity:
        raise ArtifactError("model identity mismatch")
    return metadata, tensors
```

No production module calls `torch.load(...)`. Generate `requirements-model.lock` for tensor/model execution and an aggregate hashed `requirements.lock` for clean development/release verification, then delete the floating `requirements.txt`. Model activation pins the stable model-dependency lock hash and Python ABI before tensor use; later surface/test dependencies may extend only the aggregate lock and must preserve every model pin exactly. Training records the exact source revision as provenance. Clean installation uses `python -m pip install --require-hashes -r requirements.lock` and validates it contains the model lock unchanged. Until Milestone 2 publishes a new model, runtime construction requires an injected proposal fixture and cannot advertise neural language competence.

- [ ] **Step 5: Remove the legacy checkpoint and loader tests**

Delete the `.pt` file if present, the old checkpoint loader, and tests that pin the old checkpoint revision. Add a source test that scans production modules for `torch.load(`, `weights_only=False`, and `graph_action_ranker.pt`; it must not reject `safetensors.torch.load_file`.

- [ ] **Step 6: Run and commit**

```powershell
python -m pytest tests\test_canonical.py tests\test_artifact_security.py -v
git add src\cemm_authoritative_hybrid\canonical.py src\cemm_authoritative_hybrid\artifacts.py src\cemm_authoritative_hybrid\model.py src\cemm_authoritative_hybrid\training.py tests\test_canonical.py tests\test_artifact_security.py
git add requirements-model.lock requirements.lock
git rm requirements.txt
git rm --ignore-unmatch artifacts\graph_action_ranker.pt
git commit -m "security: require canonical tensor-only artifacts"
```

Expected: all artifact tests pass and no unsafe loader remains.

### Task 3: Implement crash-consistent semantic persistence

**Files:**
- Create: `src/cemm_authoritative_hybrid/persistence.py`
- Remove: `src/cemm_authoritative_hybrid/stores.py`
- Create: `tests/test_persistence.py`
- Create: `tests/test_persistence_recovery.py`

- [ ] **Step 1: Write failing revision, restart, and recovery tests**

```python
def test_stale_writer_cannot_overwrite_newer_world(sqlite_stores, fact_factory):
    revision = sqlite_stores.world.revision
    sqlite_stores.world.commit((fact_factory("one"),), expected_revision=revision)
    with pytest.raises(StaleRevisionError):
        sqlite_stores.world.commit((fact_factory("stale"),), expected_revision=revision)

def test_restart_recovers_last_verified_revisions(store_path, stores_factory, fact_factory):
    first = stores_factory(store_path)
    receipt = first.world.commit((fact_factory("persisted"),), expected_revision=0)
    first.close()
    second = stores_factory(store_path)
    assert second.world.revision == receipt.new_revision
    assert second.world.get("fact:persisted") is not None

def test_duplicate_effect_key_returns_original_receipt(sqlite_stores, effect_factory):
    first = sqlite_stores.effects.commit(effect_factory("effect:key"))
    assert sqlite_stores.effects.commit(effect_factory("effect:key")) == first
```

- [ ] **Step 2: Run and confirm mutable stores lack recovery**

Run: `python -m pytest tests/test_persistence.py tests/test_persistence_recovery.py -v`

Expected: FAIL because the current stores are process-local and non-transactional.

- [ ] **Step 3: Implement one SQLite reference backend**

Use WAL, `PRAGMA foreign_keys=ON`, `BEGIN IMMEDIATE`, canonical payload hashes, revision rows, immutable episode rows, unique effect keys, and transaction receipts. Tables are `metadata`, `world_facts`, `sessions`, `focus`, `obligations`, `episodes`, `effects`, and `models`.

```python
@dataclass(frozen=True)
class RevisionPin:
    authority_generation: str
    world_revision: int
    session_revision: int
    episode_revision: int
    effect_revision: int
    model_identity: str | None

@dataclass(frozen=True)
class CommitReceipt:
    store: str
    parent_revision: int
    new_revision: int
    delta_hash: str
    transaction_ref: str
```

- [ ] **Step 4: Implement activation integrity and recovery receipts**

Startup checks schema version, row hashes, revision continuity, active authority generation, and unresolved effect records. Corruption raises `StoreActivationError` with `RecoveryReceipt(last_verified_revision, corrupt_refs, recommended_action)`; it never resets the database.

- [ ] **Step 5: Run both backends and commit**

```powershell
python -m pytest tests\test_persistence.py tests\test_persistence_recovery.py -v
git add src\cemm_authoritative_hybrid\persistence.py tests\test_persistence.py tests\test_persistence_recovery.py
git rm src\cemm_authoritative_hybrid\stores.py
git commit -m "feat: persist semantic revisions and effect journals"
```

Expected: in-memory fixture and SQLite parametrizations pass; restart preserves exact hashes.

### Task 4: Link authority as one reviewed graph

**Files:**
- Create: `src/cemm_authoritative_hybrid/authority.py`
- Create: `data/authority/manifest.json`
- Create: `data/authority/kernel.json`
- Create: `data/authority/conversation.json`
- Create: `data/authority/state_operations.json`
- Create: `data/languages/en/forms.json`
- Create: `tests/test_authority_linker.py`
- Remove: `data/authority.json`

- [ ] **Step 1: Write failing atomic-link tests**

```python
def test_missing_target_rejects_entire_generation(authority_factory):
    bundle = authority_factory(designation_target="concept:missing")
    with pytest.raises(AuthorityLinkError, match="missing target"):
        AuthorityLinker().link(bundle.manifest)
    assert bundle.store.active_generation is None

def test_internal_ref_is_not_automatically_a_surface(linked_authority):
    assert linked_authority.designations.for_surface("semantic store", "en") == ()

def test_exactly_one_owner_per_atom(authority_factory):
    with pytest.raises(AuthorityLinkError, match="duplicate owner"):
        AuthorityLinker().link(authority_factory(duplicate_atom="event:greeting").manifest)
```

- [ ] **Step 2: Run and reproduce permissive monolith activation**

Run: `python -m pytest tests/test_authority_linker.py -v`

Expected: FAIL because the linker and split source bundle do not exist.

- [ ] **Step 3: Implement source records and indexes**

`AuthorityLinker` validates owner, kind, five-operator role schemas, refs, definitions, rules, frames, transition signatures, capabilities, permissions, policies, adapters, and explicit designations before returning `LinkedAuthority`. It builds bounded indexes for surface/language, target designations, kind, frame, rule signature, state dimension, event signature, and transition. It emits both a full content/generation hash and a model-compatibility hash over only the contribution ABI, semantic kinds/ports, structural action ABI, and model feature encoding. Compatible reviewed identities, designations, facts, and rules change the full generation without invalidating weights; any structural encoding change changes the compatibility hash and blocks model activation until retraining.

- [ ] **Step 4: Replace the monolith with reviewed owners**

Move existing meaning-bearing records into the three exact owners, correct invalid implicit/ref-derived surfaces, add source/provenance metadata, generate `manifest.json` hashes, and delete `data/authority.json`. This is a hard data rewrite; no runtime monolith loader or migration branch remains.

- [ ] **Step 5: Add the minimal English structural pack**

`forms.json` contains tokenization/morphology, participant/deixis, binders, query/projection, polarity, modality, tense/aspect, connectors, correction, and discourse evidence. Open-class meanings remain explicit authority designations rather than `function_forms`.

- [ ] **Step 6: Link twice, run, and commit**

```powershell
python -c "from cemm_authoritative_hybrid.authority import AuthorityLinker; print(AuthorityLinker().link_path('data/authority/manifest.json').content_hash)"
python -m pytest tests\test_authority_linker.py -v
git add src\cemm_authoritative_hybrid\authority.py data\authority data\languages\en\forms.json tests\test_authority_linker.py
git rm data\authority.json
git commit -m "data: activate one linked semantic authority"
```

Expected: repeated link hashes match and no compatibility loader exists.

### Task 5: Define phase and gap receipts

**Files:**
- Create: `src/cemm_authoritative_hybrid/gaps.py`
- Create: `src/cemm_authoritative_hybrid/cycle.py`
- Create: `tests/test_phase_receipts.py`
- Create: `tests/test_gap_receipts.py`

- [ ] **Step 1: Write failing receipt tests**

```python
def test_trace_contains_six_named_phases_not_stage_numbers(cycle_fixture):
    result = cycle_fixture.run(trace=True)
    assert tuple(r.phase for r in result.trace) == (
        "ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"
    )
    assert "stage" not in str(result.as_dict()).casefold()

def test_semantic_modes_are_closed_and_not_phrase_intents():
    assert tuple(mode.value for mode in SemanticMode) == (
        "OBSERVE", "QUERY", "REQUEST", "SIMULATE"
    )

def test_external_cycle_outcomes_are_closed():
    assert tuple(status.value for status in CycleStatus) == (
        "resolved", "partial", "ambiguous", "unknown", "conflict", "unsupported",
        "denied", "resource_unavailable", "budget_exhausted", "operation_failed",
        "realization_failed",
    )

def test_missing_owner_is_implementation_gap(gap_classifier):
    gap = gap_classifier.classify(MissingOwner("realizer"))
    assert gap.kind == "implementation"
    assert gap.recommended_owner == "runtime"
    assert gap.safe_response_action == "activation_failure"
```

- [ ] **Step 2: Run and confirm no receipt ABI exists**

Run: `python -m pytest tests/test_phase_receipts.py tests/test_gap_receipts.py -v`

Expected: collection ERROR.

- [ ] **Step 3: Implement exact receipt types**

```python
@dataclass(frozen=True)
class PhaseReceipt:
    cycle_ref: str
    phase: Literal["ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"]
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    revision_pin: RevisionPin
    budget_use: Mapping[str, int]
    status: str
    rejection_codes: tuple[str, ...] = ()
    duration_ns: int | None = None

@dataclass(frozen=True)
class GapReceipt:
    gap_ref: str
    kind: GapKind
    status: str
    source_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    missing_contract_refs: tuple[str, ...]
    rejected_candidate_refs: tuple[str, ...]
    recommended_owner: RepairOwner
    safe_response_action: str

@dataclass(frozen=True)
class KernelCycleResult:
    cycle_ref: str
    status: CycleStatus
    phase_output_refs: Mapping[SemanticPhase, tuple[str, ...]]
    gap_receipt: GapReceipt | None
    trace: tuple[PhaseReceipt, ...]
    final_revision_pin: RevisionPin
```

`GapClassifier` maps typed exceptions/results only; it never examines surface text. Unknown exceptions become `implementation` and fail development tests rather than reaching users.

`SemanticMode` is the closed cycle-mode enum `OBSERVE`, `QUERY`, `REQUEST`, and `SIMULATE`. `CycleStatus` is the closed externally reachable outcome enum asserted above. Modes constrain evaluation/effect legality after composition; they are not phrase intents and cannot be selected by a raw-surface branch.

- [ ] **Step 4: Implement opt-in trace serialization**

The cycle always transfers phase artifacts but stores serialized `PhaseReceipt` rows only for `trace=True`, evaluation capture, or a durable effect. Trace collection must be observational: identical input/revision/model with trace on/off yields identical semantic result and store revisions.

- [ ] **Step 5: Run and commit**

```powershell
python -m pytest tests\test_phase_receipts.py tests\test_gap_receipts.py -v
git add src\cemm_authoritative_hybrid\gaps.py src\cemm_authoritative_hybrid\cycle.py tests\test_phase_receipts.py tests\test_gap_receipts.py
git commit -m "feat: record six-phase and real-world gap receipts"
```

### Task 6: Cut runtime bootstrap to the six-phase kernel

**Files:**
- Rewrite: `src/cemm_authoritative_hybrid/runtime.py`
- Rewrite: `src/cemm_authoritative_hybrid/bootstrap.py`
- Modify: `src/cemm_authoritative_hybrid/__init__.py`
- Create: `scripts/validate_mvp.py`
- Create: `artifacts/validation/MILESTONE_RECEIPT.json`
- Create: `tests/test_six_phase_runtime.py`
- Create: `tests/test_no_legacy_runtime.py`
- Remove: `tests/test_runtime_workstream.py`
- Remove: legacy checkpoint/candidate-family startup tests that cannot be restated semantically

- [ ] **Step 1: Write failing typed-cycle and deletion tests**

```python
def test_injected_program_runs_through_six_phase_owners(runtime_factory, verified_observation_program):
    runtime = runtime_factory(proposal_fixture=verified_observation_program)
    result = runtime.process_evidence({"source":"test", "units":("unit:1",)}, trace=True)
    assert result.status == "resolved"
    assert tuple(r.phase for r in result.trace) == SIX_PHASES
    assert result.final_revision_pin.world_revision == 1

def test_active_source_has_no_stage_or_legacy_checkpoint_contract():
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("src").rglob("*.py"))
    forbidden = ("StageRecord", "stage_trace", "range(23)", "graph_action_ranker.pt", "weights_only=False")
    assert not any(token in source for token in forbidden)
```

- [ ] **Step 2: Run and reproduce the old runtime dependency**

Run: `python -m pytest tests/test_six_phase_runtime.py tests/test_no_legacy_runtime.py -v`

Expected: FAIL because bootstrap requires the legacy checkpoint and runtime has no six-phase API.

- [ ] **Step 3: Implement the injected-owner runtime**

`HybridRuntime` accepts typed owner protocols for proposal, verification, evaluation, effects, and realization. `bootstrap.load_runtime()` links authority, opens SQLite, verifies configuration/artifacts, and refuses to start until every capability advertised by the selected profile has an owner.

Development `typed_fixture` profile accepts injected test owners and advertises only typed-program execution. `neural` profile is defined but fails activation with `MissingOwner("neural_proposer")` until Milestone 2.

- [ ] **Step 4: Implement the incremental validator**

`scripts/validate_mvp.py --profile development` compiles source, links authority, checks SQLite activation, scans forbidden legacy/phrase/stage constructs, runs active tests to JUnit XML, rejects any failure/error/skip/xfail/xpass, and writes canonical status/manifest hashes. It fails if an unimplemented capability is advertised.

- [ ] **Step 5: Run the Milestone 1 gates**

```powershell
python -m pytest -q
python scripts\validate_mvp.py --profile development --output artifacts\validation\MILESTONE_RECEIPT.json
```

Expected: all active six-phase, authority, persistence, artifact, canonical, and deletion tests pass. Delete `tests/test_runtime_workstream.py` only after each still-valid six-phase, persistence, and effect-safety assertion has a named replacement in the commit diff.

- [ ] **Step 6: Commit Milestone 1**

```powershell
git add AGENTS.md README.md docs src tests data scripts artifacts\validation
git commit -m "feat: establish six-phase authoritative kernel"
git status --short
```

Expected: clean worktree and no active Stage 0–22 or unsafe checkpoint dependency.
