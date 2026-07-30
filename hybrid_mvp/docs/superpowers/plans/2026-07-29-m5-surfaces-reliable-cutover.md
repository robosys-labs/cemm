# Milestone 5 Surfaces, Reliable Bundle, and Hard Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every task, browser:control-in-app-browser for the final web interaction test, and superpowers:verification-before-completion before the release commit. Track work with the checkboxes below.

**Goal:** Expose one identical six-phase runtime through CLI, API, and web; prove a clean bundle installs and verifies; delete all superseded runtime/test/documentation paths; and safely apply the certified bundle.

**Architecture:** Every surface submits typed requests to the same `HybridRuntime` and renders its receipts. Surfaces contain no semantic routing, canned normal answers, or alternate stores. The release archive is reproducibly assembled from an allowlist, verified from a clean extraction, and atomically applied with a recoverable filesystem backup.

**Tech Stack:** Python 3.13, FastAPI, HTTPX, vanilla HTML/CSS/JavaScript, SQLite, pytest, Playwright/in-app browser, canonical JSON, zip archives.

---

### Task 1: Replace the CLI with a thin typed runtime surface

**Files:**
- Rewrite: `src/cemm_authoritative_hybrid/cli.py`
- Modify: `src/cemm_authoritative_hybrid/bootstrap.py`
- Create: `src/cemm_authoritative_hybrid/auth.py`
- Modify: `requirements.lock`
- Create: `tests/test_cli.py`
- Create: `tests/test_surface_parity.py`
- Create: `tests/test_reviewer_auth.py`

- [ ] **Step 1: Write failing CLI and parity tests**

```python
def test_cli_emits_semantic_result_and_receipt(cli_runner, runtime):
    result = cli_runner.invoke(["ask", "--session", "s", "what is your name?", "--json"])
    payload = json.loads(result.stdout)
    assert payload["cycle_ref"]
    assert payload["response_meaning"]["status"] == "supported"
    assert payload["realization_receipt"]["equivalent"] is True

def test_cli_does_not_own_response_phrases(source_text):
    cli = source_text("src/cemm_authoritative_hybrid/cli.py")
    assert "My name is CEMM" not in cli
    assert "Could you clarify" not in cli

def test_cli_review_requires_signed_reviewer_assertion(cli_runner, pending_plan, stores):
    before = stores.revisions()
    denied = cli_runner.invoke(["review-learning", pending_plan.plan_ref, "--decision", "approve"])
    assert denied.exit_code == 3
    assert stores.revisions() == before

def test_reviewer_assertion_is_bound_expiring_and_single_use(cli_runner, signed_assertion, pending_plan):
    accepted = cli_runner.invoke([
        "review-learning", pending_plan.plan_ref,
        "--decision", "approve",
        "--reviewer-assertion", str(signed_assertion.path),
    ])
    assert accepted.exit_code == 0
    replay = cli_runner.invoke([
        "review-learning", pending_plan.plan_ref,
        "--decision", "approve",
        "--reviewer-assertion", str(signed_assertion.path),
    ])
    assert replay.exit_code == 3

def test_cli_cannot_substitute_decision(cli_runner, approve_assertion, pending_plan):
    result = cli_runner.invoke([
        "review-learning", pending_plan.plan_ref,
        "--decision", "reject",
        "--reviewer-assertion", str(approve_assertion.path),
    ])
    assert result.exit_code == 3
```

- [ ] **Step 2: Run and reproduce any surface-specific path**

Run: `python -m pytest tests/test_cli.py tests/test_surface_parity.py tests/test_reviewer_auth.py -v`

Expected: FAIL until the CLI delegates to the release runtime factory.

- [ ] **Step 3: Implement CLI commands over shared services**

Provide `ask`, `inspect-cycle`, `inspect-gap`, `review-learning`, `health`, and `version`. Human output displays verified surface plus semantic status/gap; JSON output serializes canonical artifacts. `--trace` changes observability only. Startup failures exit nonzero with activation/recovery receipt. `review-learning` accepts only a short-lived Ed25519-signed assertion file or OS credential-provider assertion bound to reviewer identity, policy ref, exact plan ref, exact `approve`/`reject` decision, nonce, audience, and expiry; the CLI decision must equal the signed claim. It never accepts a conversational claim or raw reviewer secret on the command line. `ReviewerAuthenticator` journals consumed nonces and produces the typed reviewer context required by `LearningCoordinator`. Add the exact signature-library version and hashes to `requirements.lock` before running the auth tests.

- [ ] **Step 4: Run and commit**

```powershell
python -m pytest tests\test_cli.py tests\test_surface_parity.py tests\test_reviewer_auth.py -v
python -m cemm_authoritative_hybrid.cli health --json
git add src\cemm_authoritative_hybrid\cli.py src\cemm_authoritative_hybrid\bootstrap.py src\cemm_authoritative_hybrid\auth.py requirements.lock tests\test_cli.py tests\test_surface_parity.py tests\test_reviewer_auth.py
git commit -m "feat: expose the shared semantic CLI"
```

### Task 2: Replace the API with four typed endpoints over the same runtime

**Files:**
- Create: `src/cemm_authoritative_hybrid/api.py`
- Create: `src/cemm_authoritative_hybrid/api_models.py`
- Modify: `requirements.lock`
- Create: `tests/test_api.py`
- Modify: `tests/test_surface_parity.py`

- [ ] **Step 1: Write failing endpoint, error, and parity tests**

```python
def test_turn_endpoint_returns_exact_cycle(client):
    response = client.post("/v1/turns", json={"session_ref": "s", "evidence": {"text": "hi"}, "trace": True})
    assert response.status_code == 200
    body = response.json()
    assert body["trace"][-1]["phase"] == "REALIZE"
    assert body["trace"][-1]["status"] == "completed"
    assert body["realization_receipt"]["surface"]

def test_cli_and_api_share_cycle_semantics(cli_cycle, api_cycle):
    assert cli_cycle["selected_program_ref"] == api_cycle["selected_program_ref"]
    assert cli_cycle["response_meaning"] == api_cycle["response_meaning"]

def test_invalid_payload_is_transport_error_not_semantic_gap(client):
    response = client.post("/v1/turns", json={"session_ref": "s"})
    assert response.status_code == 422

def test_learning_review_requires_authorized_bound_reviewer(
    client, pending_plan, reviewer_bearer, fresh_approve_bearer
):
    url = "/v1/learning-reviews"
    payload = {"plan_ref": pending_plan.plan_ref, "decision": "approve"}
    assert client.post(url, json=payload).status_code == 401
    wrong = client.post(url, json=payload, headers={"Authorization": "Bearer wrong-policy"})
    assert wrong.status_code == 403
    accepted = client.post(url, json=payload, headers={"Authorization": f"Bearer {reviewer_bearer}"})
    assert accepted.status_code == 200
    replay = client.post(url, json=payload, headers={"Authorization": f"Bearer {reviewer_bearer}"})
    assert replay.status_code == 409
    substituted = client.post(
        url,
        json={"plan_ref": pending_plan.plan_ref, "decision": "reject"},
        headers={"Authorization": f"Bearer {fresh_approve_bearer}"},
    )
    assert substituted.status_code == 403
```

- [ ] **Step 2: Run and confirm no shared API owner exists**

Run: `python -m pytest tests/test_api.py tests/test_surface_parity.py -v`

Expected: FAIL before API construction.

- [ ] **Step 3: Implement exactly four product endpoints**

Use `POST /v1/turns`, `GET /v1/cycles/{cycle_ref}`, `POST /v1/learning-reviews`, and `GET /v1/health`. Request/response models version their transport schema separately from semantic ABIs. One process owns one runtime/store registry; SQLite coordinates workers. Review bearer assertions are signature-verified, audience/expiry/policy/plan/decision-bound, replay-journaled, and converted to the same typed reviewer context as CLI assertions. The signed decision must equal the JSON decision. Unauthorized, wrong-policy, expired, cross-plan, decision-substituted, and replayed assertions never call `LearningCoordinator`. No endpoint accepts arbitrary authority refs as trusted acquisition.

- [ ] **Step 4: Run and commit**

```powershell
python -m pytest tests\test_api.py tests\test_surface_parity.py -v
git add src\cemm_authoritative_hybrid\api.py src\cemm_authoritative_hybrid\api_models.py requirements.lock tests\test_api.py tests\test_surface_parity.py
git commit -m "feat: expose typed semantic HTTP API"
```

### Task 3: Rebuild the web demo as a transparent API client

**Files:**
- Create: `web/index.html`
- Create: `web/app.js`
- Create: `web/styles.css`
- Create: `release/browser_runtime.json`
- Create: `scripts/provision_browser.py`
- Modify: `requirements.lock`
- Create: `tests/test_web_assets.py`
- Create: `tests/test_web_e2e.py`
- Modify: `tests/test_surface_parity.py`
- Create: `artifacts/validation/WEB_E2E_RECEIPT.json`
- Create: `artifacts/validation/web/greeting.png`
- Create: `artifacts/validation/web/reasoning.png`
- Create: `artifacts/validation/web/learning.png`
- Create: `artifacts/validation/web/failure.png`

- [ ] **Step 1: Write failing asset and browser-flow tests**

```python
def test_web_has_no_semantic_phrase_router():
    source = Path("web/app.js").read_text(encoding="utf-8")
    for forbidden in ("includes(\"hi\")", "request_generic_clarification", "answer_bindings"):
        assert forbidden not in source

def test_unknown_renders_verified_safe_surface(page, live_server):
    page.goto(live_server.url)
    page.get_by_label("Message").fill("zorbulate")
    page.get_by_role("button", name="Send").click()
    page.get_by_test_id("turn-status").wait_for()
    assert page.get_by_test_id("turn-status").inner_text() == "designation · unknown"
    assert "[no authorized surface]" not in page.locator("body").inner_text()
```

- [ ] **Step 2: Run and reproduce the historical no-surface regression**

Run: `python -m pytest tests/test_web_assets.py tests/test_web_e2e.py -v`

Expected: FAIL until the web demo renders the API realization receipt and safe failure channel.

- [ ] **Step 3: Implement the demo**

Render transcript surface, semantic status, gap kind, proof/source summary, and opt-in expandable six-phase trace. Disable review controls unless the server advertises reviewed acquisition and supplies an authenticated review flow. Accessibility labels, keyboard submission, pending state, network error, and restart/session continuity are required.

- [ ] **Step 4: Add the small cross-language structural proof**

Add reviewed English and one second-language designation/form cases that resolve to the same program graph and response meaning while realizing in the requested language. This proves language/meaning separation without pretending broad multilingual coverage.

- [ ] **Step 5: Run browser verification and commit**

```powershell
python scripts\provision_browser.py --manifest release\browser_runtime.json --cache C:\Users\Son\Downloads\cemm_browser_cache --receipt dist\BROWSER_TOOLCHAIN.json
$env:CEMM_BROWSER_BIN = (Get-Content -Raw dist\BROWSER_TOOLCHAIN.json | ConvertFrom-Json).binary_path
python -m pytest tests\test_web_assets.py tests\test_web_e2e.py tests\test_surface_parity.py -v
git add web release\browser_runtime.json scripts\provision_browser.py requirements.lock tests\test_web_assets.py tests\test_web_e2e.py tests\test_surface_parity.py artifacts\validation\WEB_E2E_RECEIPT.json artifacts\validation\web
git commit -m "feat: rebuild transparent semantic web demo"
```

`browser_runtime.json` pins the browser product/revision, approved download source, executable SHA-256, and license. Provisioning is the only networked browser step; it verifies the executable and records its path/hash. Tests and clean verification require `CEMM_BROWSER_BIN`, re-hash it before launch, and fail rather than skip when absent or mismatched. Start the local server with a hidden/background process, invoke the browser control skill, and manually verify greeting/name, family inference/`what did you say`, authenticated learning review, and unknown/denied failure. Capture the four declared screenshots, write a canonical receipt containing their hashes and cycle refs, and stop the server.

### Task 4: Build a reproducible clean bundle and verification harness

**Files:**
- Create: `release/manifest.json`
- Create: `scripts/build_bundle.py`
- Create: `scripts/verify_clean_bundle.py`
- Create: `scripts/run_acceptance_matrix.py`
- Modify: `scripts/validate_mvp.py`
- Create: `tests/test_release_manifest.py`
- Create: `tests/test_clean_bundle.py`

- [ ] **Step 1: Write failing allowlist and clean-install tests**

```python
def test_release_manifest_excludes_unsafe_and_generated_files(release_members):
    assert not any(path.endswith(".pt") for path in release_members)
    assert not any(part in path for path in release_members for part in ("__pycache__", ".pytest_cache", ".git"))
    assert not any(path.endswith((".db", ".db-wal", ".db-shm")) for path in release_members)
    assert "artifacts/proposal_release/model.safetensors" in release_members
    assert "artifacts/realizer_release/model.safetensors" in release_members

def test_two_bundle_builds_are_byte_identical(build_bundle, tmp_path):
    left, right = tmp_path / "a.zip", tmp_path / "b.zip"
    build_bundle(left); build_bundle(right)
    assert left.read_bytes() == right.read_bytes()
```

- [ ] **Step 2: Run and show the current repository is not a certified archive**

Run: `python -m pytest tests/test_release_manifest.py tests/test_clean_bundle.py -v`

Expected: FAIL until canonical timestamps/order/modes and an explicit allowlist exist.

- [ ] **Step 3: Implement build and isolated verification**

The build uses only `release/manifest.json`, canonical member order, normalized timestamps/modes, and full hashes. Verification extracts to a new temp directory, creates a clean virtual environment, proves every `requirements-model.lock` pin appears identically in the aggregate lock, installs `requirements.lock` with `--require-hashes`, validates authority/store/artifacts, compiles source, runs all tests with skip/xfail rejection, executes deterministic train/evaluate smoke, launches CLI/API/web checks, and writes a canonical receipt. Browser E2E receives only the explicit `--browser-binary` path, verifies it against `release/browser_runtime.json`, and runs network-disabled; no user-cache discovery or implicit download is allowed.

- [ ] **Step 4: Build twice and verify**

```powershell
python scripts\provision_browser.py --manifest release\browser_runtime.json --cache C:\Users\Son\Downloads\cemm_browser_cache --receipt dist\BROWSER_TOOLCHAIN.json
$env:CEMM_BROWSER_BIN = (Get-Content -Raw dist\BROWSER_TOOLCHAIN.json | ConvertFrom-Json).binary_path
python scripts\build_bundle.py --output dist\cemm_authoritative_hybrid_mvp.zip --receipt dist\BUILD_RECEIPT.json
python scripts\build_bundle.py --output dist\cemm_authoritative_hybrid_mvp.second.zip --receipt dist\BUILD_RECEIPT.second.json
python scripts\verify_clean_bundle.py dist\cemm_authoritative_hybrid_mvp.zip --browser-binary $env:CEMM_BROWSER_BIN --output dist\CLEAN_BUNDLE_RECEIPT.json
python -m pytest tests\test_release_manifest.py tests\test_clean_bundle.py -v
```

Expected: archives hash identically; the clean verifier passes with network disabled except the explicitly pre-cached Qwen benchmark dependency/model.

- [ ] **Step 5: Commit**

```powershell
git add release scripts\build_bundle.py scripts\verify_clean_bundle.py scripts\run_acceptance_matrix.py scripts\validate_mvp.py tests\test_release_manifest.py tests\test_clean_bundle.py
git commit -m "build: certify reproducible MVP bundle"
```

### Task 5: Delete superseded architecture and make documentation executable

**Files:**
- Rewrite: `README.md`
- Create: `ARCHITECTURE.md`
- Create: `RUNTIME_ARCHITECTURE.md`
- Create: `DATA_ARCHITECTURE.md`
- Create: `docs/FAILURE_CONTRACT.md`
- Create: `docs/TRAINING_AND_EVALUATION.md`
- Create: `docs/OPERATIONS.md`
- Modify: `release/manifest.json`
- Create: `tests/test_no_legacy_architecture.py`
- Create: `tests/test_documented_commands.py`
- Remove: `tests/test_safety_and_contracts.py`
- Remove: `tests/test_extended_governance.py`
- Remove: `docs/AUTHORITY_GOVERNANCE.md`
- Remove: `docs/ARCHITECTURE.md`
- Remove: `docs/EVALUATION_PROTOCOL.md`
- Remove: `docs/COMPARISON.md`
- Remove: `docs/EVALUATION_REPORT.md`
- Remove: `docs/WORKTREE_INTEGRATION.md`
- Remove: `docs/KNOWN_LIMITATIONS.md`
- Remove: `docs/RUNTIME_AND_EFFECTS.md`
- Remove: `docs/IMPLEMENTATION_PLAN.md`
- Remove: `docs/NEURAL_MODEL.md`
- Remove: `docs/GRAPH_PROGRAM_ABI.md`
- Remove: `docs/RUNTIME_TRACES.md`

- [ ] **Step 1: Write failing forbidden-inventory and command tests**

```python
FORBIDDEN = (
    "Stage 0", "Stage 22", "CandidateGenerator", "candidate.family",
    "graph_action_ranker.pt", "torch.load(", "disabled_by_milestone",
    "ABI 6", "backward compatibility", "request_generic_clarification",
)

def test_active_tree_contains_no_legacy_architecture(product_text_files):
    hits = {term: files_containing(product_text_files, term) for term in FORBIDDEN}
    assert not {term: paths for term, paths in hits.items() if paths}

def test_every_documented_command_is_executable(documented_commands):
    for command in documented_commands:
        assert command.run().returncode == 0
```

- [ ] **Step 2: Run and capture the exact deletion inventory**

Run: `python -m pytest tests/test_no_legacy_architecture.py tests/test_documented_commands.py -v`

Expected: FAIL and list every remaining superseded owner. Review each hit: move genuine historical evidence outside the release allowlist or delete it; never weaken the search to hide active ambiguity.

- [ ] **Step 3: Delete rather than deprecate**

`product_text_files` is restricted to executable source, authority/form data, web assets, and release configuration; governing documents may name retired concepts only to forbid them. Remove old stage coordinators, numbered stage receipts, candidate families/rankers/phrase compilers, ABI adapters, `.pt` loaders/artifacts, migration branches, old web canned-response code, preservation-only tests, and the named superseded documents. Delete `tests/test_safety_and_contracts.py` and `tests/test_extended_governance.py` only after mapping their still-valid assertions to the new constitution, safety, artifact, authority, and release tests. There is no alias module, feature flag, environment escape hatch, or compatibility package.

- [ ] **Step 4: Write the authoritative documentation set**

Document the six phases, five operators, structural grounding/self projection, exact/neural authority boundary, persistence, learning security, effects, 18 gaps, corpus lineage, measured limits, surfaces, artifact identity, backup/application, and actual limitations. Generate ABI/model/evaluation tables from canonical receipts so documentation cannot drift.

- [ ] **Step 5: Run and commit**

```powershell
python -m pytest tests\test_no_legacy_architecture.py tests\test_documented_commands.py -v
rg -n "Stage (0|[1-9]|1[0-9]|2[0-2])|CandidateGenerator|candidate\.family|graph_action_ranker|torch\.load\(|disabled_by_milestone|ABI 6|request_generic_clarification" src data\authority data\languages web release
git diff --check
git add -A
git commit -m "refactor: delete superseded semantic runtime"
```

Expected: forbidden search is empty and all documented commands execute.

### Task 6: Run final acceptance, create the release, and apply it safely

**Files:**
- Create: `scripts/apply_verified_bundle.py`
- Create: `tests/test_atomic_application.py`
- Create: `artifacts/validation/FINAL_VALIDATION_RECEIPT.json`
- Create: `artifacts/validation/FINAL_ACCEPTANCE.json`
- Modify: `artifacts/evaluation/CEMM_EVALUATION.json`
- Modify: `artifacts/evaluation/COMPETITIVE_EVALUATION.json`
- Verify: `dist/cemm_authoritative_hybrid_mvp.zip`
- Verify: `dist/BUILD_RECEIPT.json`
- Verify: `dist/CLEAN_BUNDLE_RECEIPT.json`
- Verify: `dist/APPLICATION_RECEIPT.json`
- Apply: `C:/Users/Son/Downloads/cemm_authoritative_hybrid_mvp`

- [ ] **Step 1: Write failing application rollback tests**

Test invalid archive hash, failed staging verification, interrupted pre-swap, failed post-swap verification, existing backup collision, cross-volume target, and successful same-volume swap. Every failure before swap leaves the target untouched; every failure after swap restores the verified backup or reports an exact recoverable state.

- [ ] **Step 2: Implement safe filesystem application**

Resolve absolute target/staging/backup paths; require staging and target parent on one volume; reject roots, home, workspace root, symlinks escaping the parent, and non-matching build receipt. Extract to a unique sibling, verify there, rename target to timestamped backup, rename staging to target, verify target, then write `APPLICATION_RECEIPT.json`. Never recursively delete the prior target.

- [ ] **Step 3: Run final semantic gates before the release commit**

```powershell
python -m pytest -q
python scripts\evaluate_cemm.py --episodes data\partitions\test.jsonl --output artifacts\evaluation\CEMM_EVALUATION.json
python scripts\compare_baselines.py --cemm artifacts\evaluation\CEMM_EVALUATION.json --qwen artifacts\evaluation\QWEN_BASELINE.json --output artifacts\evaluation\COMPETITIVE_EVALUATION.json
python scripts\validate_mvp.py --profile release --output artifacts\validation\FINAL_VALIDATION_RECEIPT.json
python -m pytest tests\test_atomic_application.py -v
```

Expected: zero failures/errors/skips/xfails/xpasses; absolute gates pass; the measured Qwen comparison is present and its claim matches evidence. A `baseline_unavailable` diagnostic fails this gate. No `dist/` file is a source-of-truth input or staged artifact.

- [ ] **Step 4: Inspect final semantic scenarios**

Run `scripts/run_acceptance_matrix.py` over every case in completion-design Section 16 and inspect receipts. The matrix also includes `how are you`, `what can you do`, unknown weather, `what does hi/what/does mean`, the five reviewed family teaching statements before the marriage query, and cross-language equivalence. It must cover greeting, name variants, capabilities, meaning lookup for closed/open-class forms, recursive mother-in-law inference, reported speech/denial, demonstratives, `what did you say`, learning/reuse, temporal state, simulation, permission denial, operation success/timeout, polysemy, incompatible evidence/residuals, out-of-domain transitions, and all 18 gaps.

```powershell
python scripts\run_acceptance_matrix.py --profile release --output artifacts\validation\FINAL_ACCEPTANCE.json
```

- [ ] **Step 5: Create the release commit**

```powershell
git diff --check
git status --short
git add -A
git commit -m "release: certify six-phase authoritative hybrid MVP"
git status --short
```

Expected: clean working tree. `dist/` remains ignored build output and is never forced into Git; the commit contains source, locked dependencies, reviewed data, model artifacts, and final semantic/evaluation receipts.

- [ ] **Step 6: Build and verify exactly the release commit**

```powershell
python scripts\provision_browser.py --manifest release\browser_runtime.json --cache C:\Users\Son\Downloads\cemm_browser_cache --receipt dist\BROWSER_TOOLCHAIN.json
$env:CEMM_BROWSER_BIN = (Get-Content -Raw dist\BROWSER_TOOLCHAIN.json | ConvertFrom-Json).binary_path
python scripts\build_bundle.py --source-commit HEAD --output dist\cemm_authoritative_hybrid_mvp.zip --receipt dist\BUILD_RECEIPT.json
python scripts\verify_clean_bundle.py dist\cemm_authoritative_hybrid_mvp.zip --browser-binary $env:CEMM_BROWSER_BIN --output dist\CLEAN_BUNDLE_RECEIPT.json
git status --short
```

Expected: clean extraction installs from hashed locks, links authority, opens SQLite, loads and ablates both safetensors models, runs the complete suite with zero skipped/expected failures, runs deterministic train/evaluate smoke, and passes CLI/API/web acceptance. `BUILD_RECEIPT.json` pins the release commit and every archive member; `git status --short` is empty because `dist/` is ignored.

- [ ] **Step 7: Apply once and verify the target**

```powershell
python scripts\provision_browser.py --manifest release\browser_runtime.json --cache C:\Users\Son\Downloads\cemm_browser_cache --receipt dist\BROWSER_TOOLCHAIN.json
$env:CEMM_BROWSER_BIN = (Get-Content -Raw dist\BROWSER_TOOLCHAIN.json | ConvertFrom-Json).binary_path
python scripts\apply_verified_bundle.py --archive dist\cemm_authoritative_hybrid_mvp.zip --build-receipt dist\BUILD_RECEIPT.json --target C:\Users\Son\Downloads\cemm_authoritative_hybrid_mvp --output dist\APPLICATION_RECEIPT.json
Set-Location C:\Users\Son\Downloads\cemm_authoritative_hybrid_mvp
python scripts\verify_clean_bundle.py . --browser-binary $env:CEMM_BROWSER_BIN --output C:\Users\Son\Downloads\cemm_authoritative_hybrid_mvp_implementation\dist\APPLIED_VALIDATION_RECEIPT.json
python scripts\run_acceptance_matrix.py --profile user --output C:\Users\Son\Downloads\cemm_authoritative_hybrid_mvp_implementation\dist\APPLIED_ACCEPTANCE.json
```

Expected: the target is the certified bundle, the timestamped prior target remains recoverable, the applied hashes match the release receipt, and neural proposal/realization are active on every product surface.
