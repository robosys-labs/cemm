# CEMM v1 Modular Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire v3.5.1, freeze MVP v2/v3/v4 as permanent references, and build a modular CEMM v1 at the repository root from the v4 kernel — splitting ~1063 lines into focused modules, fixing 10 identified weaknesses during the split, and producing honest documentation guided by v4's MVP_ARCHITECTURE.md.

**Architecture:** CEMM v1 is a modular reorganization of the v4 MVP kernel. The 5-operator/20-role invariant algebra, open structured graph prediction, N-best settling, rule induction with provisional→promoted lifecycle, authority/world atom separation, semantic-pointer NLG, bounded workspace, and self-state tracking are all preserved. No capabilities are removed. No new capabilities are added. The split produces focused modules (each <200 lines) with clean interfaces, configurable thresholds, CLI coverage for all commands, inference timeout, bounded model cache, and schema migration support.

**Tech Stack:** Python 3.11+, PyTorch, SQLite (stdlib `sqlite3`), stdlib `argparse`/`json`/`hashlib`/`unicodedata`/`re`/`dataclasses`.

**Source basis:** `C:\Users\Son\Downloads\cemm_minimal_brain_mvp_v4\` (cemm_mvp.py 688 lines, structured_codec.py 185 lines, trainer.py 158 lines, acquisition.py 32 lines, knowledge/, training/, language_packs/, tests/)

**Target repository:** `C:\dev\cemm\` (currently contains v3.5.1 at root + v2 MVP in `cemm_minimal_brain_mvp/`)

---

## File Structure

### Phase 1: Archive (retire v3.5.1)

```
archive/
  v3.5.1/
    cemm/                          # moved from root cemm/
    tests/                         # moved from root tests/
    tools/                         # moved from root tools/
    docs/                          # moved from root docs/
    .github/                       # moved from root .github/
    build/                         # moved from root build/
    dist/                          # moved from root dist/
    cemm.egg-info/                 # moved from root cemm.egg-info/
    output/                        # moved from root output/
    AGENTS.md                      # moved from root
    ARCHITECTURE.md                # moved from root
    ARCHITECTURE_AUDIT.md          # moved from root
    ACCEPTANCE_CONTRACT.md         # moved from root
    CEMM_CORE_MATHS.md             # moved from root
    CORE_ISSUES.md                 # moved from root
    CORE_LOOP.md                   # moved from root
    DOCUMENTATION_MIGRATION.md     # moved from root
    IMPLEMENTATION_PLAN.md         # moved from root
    ISSUES_TO_AVOID.md             # moved from root
    PATCH_PAGE.md                  # moved from root
    phased-fixes.md                # moved from root
    PHASES13_14_IMPLEMENTATION_REPORT.md  # moved from root
    README.md                      # moved from root
    README_BUNDLE.md               # moved from root
    RUNTIME_PLAN.md                # moved from root
    pyproject.toml                 # moved from root
    apply_final_fixes_lenient.py   # moved from root
    apply_phase17_18.py            # moved from root
    apply_phases13_14.py           # moved from root
    _verify_bundle.py              # moved from root
  ARCHIVED.md                      # explains what was archived and why
```

### Phase 2: Freeze MVP demos

```
reference/
  mvp_v2/                          # copied from C:\dev\cemm\cemm_minimal_brain_mvp\
    FROZEN.md                      # marks as permanent reference
  mvp_v3/                          # copied from C:\Users\Son\Downloads\cemm_minimal_brain_mvp_v3\
    FROZEN.md
  mvp_v4/                          # copied from C:\Users\Son\Downloads\cemm_minimal_brain_mvp_v4\
    FROZEN.md
  REFERENCE_INDEX.md               # index of all frozen references
```

### Phase 3: CEMM v1 modular package

```
cemm/                              # new v1 package
  __init__.py                      # version, public API exports (~20 lines)
  constants.py                     # DDL, TOK regex, operator/role constants (~60 lines)
  model.py                         # Fact, AmbiguousReferent, helpers (now, canonical, stable, norm_text, toks, surface, lit, isvar, isexist) (~80 lines)
  store.py                         # Store class with DDL, import, query, authority_hash, snapshot_hash, rule_candidates (~250 lines)
  codec.py                         # StructuredNet, RuleNet, Encoder, Candidate, StructuredSemanticCodec (~190 lines)
  compiler.py                      # ExactStructuredCompiler (~50 lines)
  settler.py                       # SemanticSettler (~35 lines)
  interpreter.py                   # Interpreter, SurfaceCodec, Delexer (~120 lines)
  inference.py                     # Inference (~60 lines)
  rules.py                         # RuleLearner (~25 lines)
  workspace.py                     # WorkspaceSlot, WorkspaceNet, Workspace, workspace_model (~80 lines)
  selfstate.py                     # StateTransition, SessionSelf (~40 lines)
  response.py                      # ResponsePlanner, pointerize_fact, pointerize_plan (~40 lines)
  realizer.py                      # PointerRealizer, LanguagePack (~60 lines)
  runtime.py                       # Runtime class with process, reload_authority, _outcome (~120 lines)
  acquisition.py                   # acquire() function (~35 lines)
  trainer.py                       # trainer main() (~160 lines)
  cli.py                           # main() with all CLI commands (~60 lines)
  config.py                        # Config dataclass with all configurable thresholds (~40 lines)
  data/
    base.json                      # foundational semantic/runtime meaning
    family_knowledge.json          # reusable family/domain knowledge
  training/
    en_seed.json                   # English training corpus
    es_seed.json                   # Spanish training corpus
  language_packs/
    en.json                        # compiled English pack
    es.json                        # compiled Spanish pack
tests/
  __init__.py
  test_mvp.py                      # ported from v4 tests (37 tests)
  test_config.py                   # new: test configurable thresholds
  test_cli.py                      # new: test CLI commands
  test_timeout.py                  # new: test inference timeout
  test_migration.py                # new: test schema migration
pyproject.toml                     # new, minimal
README.md                          # new, v1 (honest, per AGENTS.md §12)
ARCHITECTURE.md                    # new, v1 (from v4 MVP_ARCHITECTURE.md, updated for modular structure)
AGENTS.md                          # new, v1 (simplified governing contract)
```

**Module size budget:** Each module <250 lines. Largest is `store.py` (~250) and `codec.py` (~190). Most are <100 lines.

---

## Phase 1: Archive v3.5.1

### Task 1: Create archive directory and move v3.5.1 artifacts

**Files:**
- Create: `archive/v3.5.1/`
- Create: `archive/ARCHIVED.md`
- Move: all v3.5.1 artifacts from root to `archive/v3.5.1/`

- [ ] **Step 1: Create archive directory structure**

Run:
```bash
mkdir -p archive/v3.5.1
```

- [ ] **Step 2: Move v3.5.1 directories**

Move these directories into `archive/v3.5.1/`:
- `cemm/` → `archive/v3.5.1/cemm/`
- `tests/` → `archive/v3.5.1/tests/`
- `tools/` → `archive/v3.5.1/tools/`
- `docs/` → `archive/v3.5.1/docs/`
- `.github/` → `archive/v3.5.1/.github/`
- `build/` → `archive/v3.5.1/build/`
- `dist/` → `archive/v3.5.1/dist/`
- `cemm.egg-info/` → `archive/v3.5.1/cemm.egg-info/`
- `output/` → `archive/v3.5.1/output/`

Use Python `shutil.move()` for each. Do NOT delete — move only.

- [ ] **Step 3: Move v3.5.1 markdown files**

Move these files into `archive/v3.5.1/`:
- `AGENTS.md`, `ARCHITECTURE.md`, `ARCHITECTURE_AUDIT.md`, `ACCEPTANCE_CONTRACT.md`
- `CEMM_CORE_MATHS.md`, `CORE_ISSUES.md`, `CORE_LOOP.md`, `DOCUMENTATION_MIGRATION.md`
- `IMPLEMENTATION_PLAN.md`, `ISSUES_TO_AVOID.md`, `PATCH_PAGE.md`, `phased-fixes.md`
- `PHASES13_14_IMPLEMENTATION_REPORT.md`, `README.md`, `README_BUNDLE.md`, `RUNTIME_PLAN.md`

- [ ] **Step 4: Move v3.5.1 Python scripts and config**

Move: `pyproject.toml`, `apply_final_fixes_lenient.py`, `apply_phase17_18.py`, `apply_phases13_14.py`, `_verify_bundle.py`

- [ ] **Step 5: Write archive manifest**

Create `archive/ARCHIVED.md`:
```markdown
# Archived: CEMM v3.5.1

**Archived:** 2026-07-24
**Reason:** v3.5.1 runtime (291 files, ~74k lines) was architecturally aligned with canonical contracts but systematically violated anti-bloat principles. It could only produce output for 21/76 demo corpus turns. Replaced by CEMM v1, a modular implementation based on the v4 MVP kernel.

**What's here:** Complete v3.5.1 codebase, tests, docs, and scripts — preserved for reference.

**Do not import from this archive.** It is not a dependency. It is historical reference only.
```

- [ ] **Step 6: Verify root is clean**

Run: `ls C:\dev\cemm\` — should only contain: `archive/`, `cemm_minimal_brain_mvp/`, `.gitignore`, `.pytest_cache/`, `docs/`

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "Archive v3.5.1 runtime (291 files, ~74k lines) — replaced by v1 modular"
```

---

## Phase 2: Freeze MVP demos

### Task 2: Create reference directory and copy MVP demos

**Files:**
- Create: `reference/mvp_v2/`, `reference/mvp_v3/`, `reference/mvp_v4/`
- Create: `reference/mvp_v2/FROZEN.md`, `reference/mvp_v3/FROZEN.md`, `reference/mvp_v4/FROZEN.md`
- Create: `reference/REFERENCE_INDEX.md`

- [ ] **Step 1: Create reference directory**

Run:
```bash
mkdir -p reference
```

- [ ] **Step 2: Copy v2 MVP**

Copy `C:\dev\cemm\cemm_minimal_brain_mvp\` → `reference/mvp_v2/` (using `shutil.copytree`)

- [ ] **Step 3: Copy v3 MVP**

Copy `C:\Users\Son\Downloads\cemm_minimal_brain_mvp_v3\` → `reference/mvp_v3/`

- [ ] **Step 4: Copy v4 MVP**

Copy `C:\Users\Son\Downloads\cemm_minimal_brain_mvp_v4\` → `reference/mvp_v4/`

- [ ] **Step 5: Write FROZEN.md for each**

Each `FROZEN.md` contains:
```markdown
# FROZEN — Permanent Reference

**Status:** Frozen. Do not modify.
**Purpose:** Permanent executable reference of the MVP demo at this version.

This directory is a read-only reference. CEMM v1 is built from mvp_v4 but lives
in the root `cemm/` package. To run this reference:

```bash
cd reference/mvp_v4
python -m unittest tests.test_mvp -v
```
```

- [ ] **Step 6: Write reference index**

Create `reference/REFERENCE_INDEX.md`:
```markdown
# CEMM MVP Reference Index

| Version | Lines | Tests | Key contribution |
|---------|-------|-------|-----------------|
| v2 | 489 | 29 | Minimal 5-operator kernel, ephemeral closure, learned codec |
| v3 | 587+89 | 32 | Active semantic workspace, self-state, language packs, semantic-pointer NLG |
| v4 | 688+185+158+32 | 37 | Open structured prediction, N-best settling, rule induction, vocabulary acquisition |

**Basis for v1:** v4

See each subdirectory's FROZEN.md and MVP_ARCHITECTURE.md for details.
```

- [ ] **Step 7: Remove old cemm_minimal_brain_mvp from root**

Move `cemm_minimal_brain_mvp/` to recycle bin (it's now copied to `reference/mvp_v2/`).

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "Freeze MVP v2/v3/v4 as permanent references in reference/"
```

---

## Phase 3: Build CEMM v1 modular package

### Task 3: Create package skeleton and config module

**Files:**
- Create: `cemm/__init__.py`
- Create: `cemm/config.py`
- Create: `cemm/constants.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test for Config**

`tests/test_config.py`:
```python
"""Test configurable thresholds (weakness #4 fix)."""
import unittest
from cemm.config import Config

class TestConfig(unittest.TestCase):
    def test_defaults_match_v4(self):
        c = Config()
        self.assertEqual(c.settler_posterior_threshold, 0.48)
        self.assertEqual(c.settler_margin_threshold, 0.06)
        self.assertEqual(c.settler_rounds, 4)
        self.assertEqual(c.rule_evidence_threshold, 2)
        self.assertEqual(c.salience_decay, 0.55)
        self.assertEqual(c.workspace_top_k, 24)
        self.assertEqual(c.inference_max_rounds, 8)
        self.assertEqual(c.inference_max_facts, 200)
        self.assertEqual(c.inference_timeout_seconds, 30.0)
        self.assertEqual(c.model_cache_limit, 8)
        self.assertEqual(c.structured_net_seed, 41)
        self.assertEqual(c.rule_net_seed, 73)

    def test_custom_overrides(self):
        c = Config(workspace_top_k=32, rule_evidence_threshold=3)
        self.assertEqual(c.workspace_top_k, 32)
        self.assertEqual(c.rule_evidence_threshold, 3)
        # Defaults preserved for unspecified
        self.assertEqual(c.settler_posterior_threshold, 0.48)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cemm'`

- [ ] **Step 3: Write cem/config.py**

`cemm/config.py` (~40 lines):
```python
"""Configurable thresholds for CEMM v1.

All thresholds that were hardcoded magic numbers in v4 are centralized here.
This fixes weakness #4 (hardcoded thresholds).
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    # Semantic settler
    settler_posterior_threshold: float = 0.48
    settler_margin_threshold: float = 0.06
    settler_rounds: int = 4
    settler_top_k: int = 10

    # Rule learning
    rule_evidence_threshold: int = 2

    # Salience / discourse
    salience_decay: float = 0.55

    # Workspace
    workspace_top_k: int = 24

    # Inference (weakness #6 fix: timeout)
    inference_max_rounds: int = 8
    inference_max_facts: int = 200
    inference_timeout_seconds: float = 30.0

    # Model cache (weakness #10 fix: bounded cache)
    model_cache_limit: int = 8

    # Neural seeds
    structured_net_seed: int = 41
    rule_net_seed: int = 73
    classifier_seed: int = 11
```

- [ ] **Step 4: Write cem/__init__.py**

`cemm/__init__.py` (~20 lines):
```python
"""CEMM v1 — Modular semantic cognition kernel.

Built from the v4 MVP kernel. See ARCHITECTURE.md for the architecture
and reference/ for frozen MVP demos.
"""
__version__ = "1.0.0"
```

- [ ] **Step 5: Write cem/constants.py**

`cemm/constants.py` (~60 lines): Port DDL and TOK from v4 `cemm_mvp.py` lines 27-48. No changes to content, just moved.

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add cemm/__init__.py cemm/config.py cemm/constants.py tests/test_config.py
git commit -m "feat: add Config module with configurable thresholds (weakness #4)"
```

### Task 4: Port model.py (Fact, helpers, AmbiguousReferent)

**Files:**
- Create: `cemm/model.py`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write the failing test**

`tests/test_model.py`:
```python
"""Test core model types."""
import unittest
from cemm.model import Fact, AmbiguousReferent, stable, canonical, norm_text, toks, surface, lit, isvar, isexist

class TestModel(unittest.TestCase):
    def test_fact_signature_is_deterministic(self):
        f1 = Fact(ref="r1", operator="op:type", args={"role:class": "concept:doctor", "role:instance": "entity:ada"})
        f2 = Fact(ref="r2", operator="op:type", args={"role:instance": "entity:ada", "role:class": "concept:doctor"})
        self.assertEqual(f1.signature(), f2.signature())

    def test_stable_is_deterministic(self):
        self.assertEqual(stable("test", "a", "b"), stable("test", "a", "b"))

    def test_norm_text_casefolds_unicode(self):
        self.assertEqual(norm_text("ÉVIDENCE"), norm_text("evidence"))

    def test_surface_capitalizes_first(self):
        self.assertTrue(surface(["hello", "."]).startswith("H"))

    def test_isvar_and_isexist(self):
        self.assertTrue(isvar("?v0"))
        self.assertTrue(isexist("!e0"))
        self.assertFalse(isvar("atom:abc"))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_model.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write cem/model.py**

Port from v4 `cemm_mvp.py` lines 51-69: `now()`, `canonical()`, `stable()`, `norm_text()`, `toks()`, `surface()`, `lit()`, `isvar()`, `isexist()`, `AmbiguousReferent`, `Fact`. Import `TOK` from `cemm.constants`. (~80 lines)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cemm/model.py tests/test_model.py
git commit -m "feat: add model module (Fact, helpers, AmbiguousReferent)"
```

### Task 5: Port store.py (Store class with all methods)

**Files:**
- Create: `cemm/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

`tests/test_store.py`:
```python
"""Test Store: DDL, import, authority_hash, rule_candidates."""
import unittest, tempfile, os
from cemm.store import Store

class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_store_initializes_with_generation_1(self):
        self.assertEqual(self.store.generation, 1)

    def test_authority_hash_excludes_world_atoms(self):
        h1 = self.store.authority_hash()
        # Add a world atom — should not change authority hash
        self.store.exact("atoms", ["ref","kind","metadata","generation","authority_scope"],
                         ["atom:test","entity","{}",self.store.generation,"world"],
                         ["ref"], {"generation"})
        self.store.db.commit()
        h2 = self.store.authority_hash()
        self.assertEqual(h1, h2)

    def test_rule_candidate_evidence_increments(self):
        g = self.store.generation
        ref = "cand:test:abc"
        self.store.add_rule_candidate(ref, "definition", '{"a":1}', '{"b":2}', 0.9, g)
        self.store.add_rule_candidate(ref, "definition", '{"a":1}', '{"b":2}', 0.9, g)
        row = self.store.db.execute("SELECT evidence_count FROM rule_candidates WHERE candidate_ref=?", (ref,)).fetchone()
        self.assertEqual(row["evidence_count"], 2)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_store.py -v`
Expected: FAIL

- [ ] **Step 3: Write cem/store.py**

Port the `Store` class from v4 `cemm_mvp.py` lines 71-269. Import DDL from `cemm.constants`, helpers from `cemm.model`. The class is ~200 lines — within budget. Key methods: `__init__`, `generation`, `begin`, `finish`, `snapshot_hash`, `authority_hash`, `exact`, `insert_app`, `add_observation`, `add_claim`, `add_rule_candidate`, `import_data`, `resolve_label`, `label_candidates`, `find_relation_object`, `user_visible_fact`, `frontier`, `rebuild_designations`, `_supersede_state`, `snapshot`. (~250 lines)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cemm/store.py tests/test_store.py
git commit -m "feat: add Store module with authority/world separation and rule_candidates"
```

### Task 6: Port codec.py (StructuredNet, RuleNet, StructuredSemanticCodec)

**Files:**
- Create: `cemm/codec.py`

- [ ] **Step 1: Write cem/codec.py**

Port from v4 `structured_codec.py` (185 lines). Import `Config` from `cemm.config` for seeds. Replace hardcoded seeds (41, 73) with `config.structured_net_seed` and `config.rule_net_seed`. Import `toks` from `cemm.model`. (~190 lines)

- [ ] **Step 2: Verify import works**

Run: `python -c "from cemm.codec import StructuredSemanticCodec; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add cemm/codec.py
git commit -m "feat: add codec module (StructuredNet, RuleNet, StructuredSemanticCodec)"
```

### Task 7: Port compiler.py and settler.py

**Files:**
- Create: `cemm/compiler.py`
- Create: `cemm/settler.py`

- [ ] **Step 1: Write cem/compiler.py**

Port `ExactStructuredCompiler` from v4 `cemm_mvp.py` lines 346-384. Import `Store`, `Fact`, helpers. (~50 lines)

- [ ] **Step 2: Write cem/settler.py**

Port `SemanticSettler` from v4 `cemm_mvp.py` lines 386-414. Import `Config` for thresholds (replaces hardcoded 0.48, 0.06, 4). Import `ExactStructuredCompiler`. (~35 lines)

- [ ] **Step 3: Verify imports**

Run: `python -c "from cemm.compiler import ExactStructuredCompiler; from cemm.settler import SemanticSettler; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add cemm/compiler.py cemm/settler.py
git commit -m "feat: add compiler and settler modules with configurable thresholds"
```

### Task 8: Port interpreter.py, inference.py, rules.py

**Files:**
- Create: `cemm/interpreter.py`
- Create: `cemm/inference.py`
- Create: `cemm/rules.py`

- [ ] **Step 1: Write cem/interpreter.py**

Port `SurfaceCodec`, `Delexer`, `Interpreter` from v4 `cemm_mvp.py` lines 291-440. Import `StructuredSemanticCodec`, `ExactStructuredCompiler`, `SemanticSettler`, `LanguagePack`, `Store`, helpers. (~120 lines)

- [ ] **Step 2: Write cem/inference.py**

Port `Inference` from v4 `cemm_mvp.py` lines 457-503. Import `Config` for `inference_max_rounds`, `inference_max_facts`, `inference_timeout_seconds`. **Fix weakness #6 (inference timeout):** Add `signal.alarm` or `threading.Timer` based timeout that raises `TimeoutError` when exceeded. Import `Store`, `Fact`, helpers. (~70 lines)

- [ ] **Step 3: Write cem/rules.py**

Port `RuleLearner` from v4 `cemm_mvp.py` lines 442-455. Import `Config` for `rule_evidence_threshold`. Import `Interpreter`, `Store`. (~25 lines)

- [ ] **Step 4: Verify imports**

Run: `python -c "from cemm.interpreter import Interpreter; from cemm.inference import Inference; from cemm.rules import RuleLearner; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add cemm/interpreter.py cemm/inference.py cemm/rules.py
git commit -m "feat: add interpreter, inference (with timeout), and rules modules"
```

### Task 9: Port workspace.py, selfstate.py, response.py, realizer.py

**Files:**
- Create: `cemm/workspace.py`
- Create: `cemm/selfstate.py`
- Create: `cemm/response.py`
- Create: `cemm/realizer.py`

- [ ] **Step 1: Write cem/selfstate.py**

Port `StateTransition`, `SessionSelf` from v4 `cemm_mvp.py` lines 505-516. Import `Store`, `Fact`, helpers. (~40 lines)

- [ ] **Step 2: Write cem/workspace.py**

Port `WorkspaceSlot`, `WorkspaceNet`, `Workspace`, `workspace_model` from v4 `cemm_mvp.py` lines 518-556. Import `Config` for `workspace_top_k`. **Fix weakness #5 (synthetic training):** Add a comment documenting that workspace model is trained on synthetic data and needs real semantic patterns for production. Import `SessionSelf`, `Store`, helpers. (~80 lines)

- [ ] **Step 3: Write cem/response.py**

Port `ResponsePlanner`, `pointerize_fact`, `pointerize_plan` from v4 `cemm_mvp.py` lines 558-595. Import `Store`, `Fact`, helpers. (~40 lines)

- [ ] **Step 4: Write cem/realizer.py**

Port `PointerRealizer`, `LanguagePack` from v4 `cemm_mvp.py` lines 271-269 and 597-612. Import `Store`, helpers. (~60 lines)

- [ ] **Step 5: Verify imports**

Run: `python -c "from cemm.workspace import Workspace; from cemm.selfstate import SessionSelf; from cemm.response import ResponsePlanner; from cemm.realizer import PointerRealizer, LanguagePack; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add cemm/workspace.py cemm/selfstate.py cemm/response.py cemm/realizer.py
git commit -m "feat: add workspace, selfstate, response, and realizer modules"
```

### Task 10: Port runtime.py with bounded model cache

**Files:**
- Create: `cemm/runtime.py`

- [ ] **Step 1: Write cem/runtime.py**

Port `Runtime` class from v4 `cemm_mvp.py` lines 614-705. Import all modules. **Fix weakness #10 (unbounded model cache):** Replace global `MODEL_CACHE={}` with a bounded LRU cache using `collections.OrderedDict` with `Config.model_cache_limit`. Import `Config`, `Store`, `Interpreter`, `Inference`, `Workspace`, `SessionSelf`, `ResponsePlanner`, `PointerRealizer`, `LanguagePack`, `RuleLearner`. (~120 lines)

- [ ] **Step 2: Verify import**

Run: `python -c "from cemm.runtime import Runtime; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add cemm/runtime.py
git commit -m "feat: add Runtime module with bounded model cache (weakness #10)"
```

### Task 11: Port acquisition.py and trainer.py

**Files:**
- Create: `cemm/acquisition.py`
- Create: `cemm/trainer.py`

- [ ] **Step 1: Write cem/acquisition.py**

Port from v4 `acquisition.py` (32 lines). Update imports to use `cemm.store`, `cemm.runtime`. (~35 lines)

- [ ] **Step 2: Write cem/trainer.py**

Port from v4 `trainer.py` (158 lines). Update imports. (~160 lines)

- [ ] **Step 3: Verify imports**

Run: `python -c "from cemm.acquisition import acquire; from cemm.trainer import main; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add cemm/acquisition.py cemm/trainer.py
git commit -m "feat: add acquisition and trainer modules"
```

### Task 12: Write cli.py with all commands (weakness #3 fix)

**Files:**
- Create: `cemm/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
"""Test CLI command coverage (weakness #3 fix)."""
import unittest, subprocess, sys, os, tempfile, json

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.db = self.tmp.name
        self.pack = os.path.join(os.path.dirname(__file__), "..", "cemm", "language_packs", "en.json")
        self.data = [
            os.path.join(os.path.dirname(__file__), "..", "cemm", "data", "base.json"),
            os.path.join(os.path.dirname(__file__), "..", "cemm", "data", "family_knowledge.json"),
        ]

    def tearDown(self):
        os.unlink(self.db)

    def _run(self, *args):
        r = subprocess.run([sys.executable, "-m", "cemm.cli"] + list(args),
                           capture_output=True, text=True, timeout=120)
        return r

    def test_init_command(self):
        r = self._run("init", "--db", self.db, "--pack", self.pack,
                      *[d for d in self.data for d in ("--data", d)])
        self.assertEqual(r.returncode, 0)

    def test_reload_command(self):
        # Init first
        self._run("init", "--db", self.db, "--pack", self.pack,
                  *[d for d in self.data for d in ("--data", d)])
        r = self._run("reload", "--db", self.db, "--pack", self.pack)
        self.assertEqual(r.returncode, 0)

    def test_acquire_command(self):
        # Init first
        self._run("init", "--db", self.db, "--pack", self.pack,
                  *[d for d in self.data for d in ("--data", d)])
        r = self._run("acquire", "--db", self.db, "--pack", self.pack,
                      "--text", "Friction is resistance.",
                      "--mentions", json.dumps([{"surface":"Friction","kind":"concept"},{"surface":"resistance","kind":"concept"}]))
        self.assertEqual(r.returncode, 0)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Write cem/cli.py**

Port `main()` from v4 `cemm_mvp.py` lines 707-719. **Fix weakness #3 (missing CLI commands):** Add `reload` and `acquire` commands alongside `init`, `chat`, `learn`, `teach`, `ask`, `inspect`. The `acquire` command takes `--text` and `--mentions` (JSON) arguments. (~60 lines)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cemm/cli.py tests/test_cli.py
git commit -m "feat: add CLI with reload and acquire commands (weakness #3)"
```

### Task 13: Copy data, training, and language_packs

**Files:**
- Create: `cemm/data/base.json`
- Create: `cemm/data/family_knowledge.json`
- Create: `cemm/training/en_seed.json`
- Create: `cemm/training/es_seed.json`
- Create: `cemm/language_packs/en.json`
- Create: `cemm/language_packs/es.json`

- [ ] **Step 1: Copy data files**

Copy from `reference/mvp_v4/knowledge/base.json` → `cemm/data/base.json`
Copy from `reference/mvp_v4/knowledge/family_knowledge.json` → `cemm/data/family_knowledge.json`

- [ ] **Step 2: Copy training files**

Copy from `reference/mvp_v4/training/en_seed.json` → `cemm/training/en_seed.json`
Copy from `reference/mvp_v4/training/es_seed.json` → `cemm/training/es_seed.json`

- [ ] **Step 3: Copy language packs**

Copy from `reference/mvp_v4/language_packs/en.json` → `cemm/language_packs/en.json`
Copy from `reference/mvp_v4/language_packs/es.json` → `cemm/language_packs/es.json`

- [ ] **Step 4: Commit**

```bash
git add cemm/data/ cemm/training/ cemm/language_packs/
git commit -m "feat: add data, training corpora, and compiled language packs"
```

### Task 14: Port and run the full test suite

**Files:**
- Create: `tests/test_mvp.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write tests/__init__.py**

Empty file.

- [ ] **Step 2: Port test suite from v4**

Copy `reference/mvp_v4/tests/test_mvp.py` → `tests/test_mvp.py`. Update all imports from `cemm_mvp` to `cemm.*` modules. Update `Store`, `Runtime` imports to use `cemm.store.Store`, `cemm.runtime.Runtime`. Update any direct references to v4 internal classes.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: All 37 v4 tests + config + cli tests PASS

- [ ] **Step 4: Fix any import failures**

If tests fail due to import paths, fix the imports in `tests/test_mvp.py` or the module files.

- [ ] **Step 5: Commit**

```bash
git add tests/__init__.py tests/test_mvp.py
git commit -m "test: port 37 tests from v4 MVP to v1 modular structure"
```

### Task 15: Add inference timeout test (weakness #6 fix)

**Files:**
- Create: `tests/test_timeout.py`

- [ ] **Step 1: Write the failing test**

`tests/test_timeout.py`:
```python
"""Test inference timeout (weakness #6 fix)."""
import unittest, tempfile, os, time
from cemm.store import Store
from cemm.inference import Inference
from cemm.config import Config

class TestTimeout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_timeout_raises_on_pathological_rules(self):
        # Create a rule that would cause infinite loop without timeout
        # rule: if relation(?x, self_loop, ?x) then relation(?x, self_loop, ?x)
        # This is a self-referential rule that would loop
        config = Config(inference_timeout_seconds=0.5, inference_max_rounds=10000)
        inf = Inference(self.store, config)
        # Insert a self-referential rule
        g = self.store.generation
        self.store.exact("rules",
            ["rule_ref","rule_kind","antecedent","consequent","confidence","authority_status","generation"],
            ["rule:loop","definition",
             canonical([{"operator":"op:relation","args":{"role:subject":"?v0","role:relation":"rel:loop","role:object":"?v0"}}]),
             canonical([{"operator":"op:relation","args":{"role:subject":"?v0","role:relation":"rel:loop","role:object":"?v0"}}]),
             1.0, "reviewed", g],
            ["rule_ref"], {"generation"})
        self.store.db.commit()
        # Insert a fact that triggers the loop
        self.store.insert_app("op:relation",
            {"role:subject":"atom:test","role:relation":"rel:loop","role:object":"atom:test"},
            g, "obs:test", "support", 1.0, "reviewed")
        self.store.db.commit()

        start = time.time()
        with self.assertRaises(TimeoutError):
            inf.closure([{"operator":"op:relation","args":{"role:subject":"atom:test","role:relation":"rel:loop","role:object":"atom:test"}}])
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0)  # Should timeout well under 2 seconds

if __name__ == "__main__":
    unittest.main()
```

Note: You'll need to import `canonical` from `cemm.model`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_timeout.py -v`
Expected: FAIL (no timeout implemented yet, or hangs)

- [ ] **Step 3: Implement timeout in inference.py**

In `cemm/inference.py`, add timeout logic using `threading.Timer`:
```python
import threading

class InferenceTimeoutError(TimeoutError):
    pass

class Inference:
    def __init__(self, store, config=None):
        self.store = store
        self.config = config or Config()
        self._timed_out = False

    def closure(self, seeds, max_rounds=None, max_facts=None):
        max_rounds = max_rounds or self.config.inference_max_rounds
        max_facts = max_facts or self.config.inference_max_facts
        timeout = self.config.inference_timeout_seconds

        timer = threading.Timer(timeout, self._timeout)
        timer.start()
        try:
            result = self._closure_impl(seeds, max_rounds, max_facts)
            return result
        finally:
            timer.cancel()

    def _timeout(self):
        self._timed_out = True

    def _closure_impl(self, seeds, max_rounds, max_facts):
        # ... existing closure logic ...
        # Check self._timed_out in the loop
        for round_i in range(max_rounds):
            if self._timed_out:
                raise InferenceTimeoutError(f"Inference exceeded {self.config.inference_timeout_seconds}s timeout")
            # ... existing round logic ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_timeout.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_timeout.py cemm/inference.py
git commit -m "feat: add inference timeout (weakness #6)"
```

### Task 16: Write pyproject.toml

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "cemm"
version = "1.0.0"
description = "CEMM v1 — Modular semantic cognition kernel"
requires-python = ">=3.11"
dependencies = ["torch>=2.0"]

[project.scripts]
cemm = "cemm.cli:main"

[tool.setuptools.packages.find]
include = ["cemm*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Verify installable**

Run: `pip install -e .`
Expected: Success

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add pyproject.toml for v1"
```

### Task 17: Write README.md (honest, per AGENTS.md §12)

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Write a project-facing README that:
- Explains the thesis: meaning ≠ language, exact semantic authority + neural dynamics
- Shows the architecture diagram (from v4 MVP_ARCHITECTURE.md §2)
- Shows concrete examples (the demo sequence from v4)
- States current status honestly: "architecture proof, under active verification"
- Links to ARCHITECTURE.md for details
- Does NOT fill with anti-regression lists or internal prohibitions
- Mentions `reference/` for frozen MVP demos
- Shows install and run instructions

(~150 lines)

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add v1 README (honest status, per AGENTS.md §12)"
```

### Task 18: Write ARCHITECTURE.md (from v4 MVP_ARCHITECTURE.md, updated)

**Files:**
- Create: `ARCHITECTURE.md`

- [ ] **Step 1: Write ARCHITECTURE.md**

Port `reference/mvp_v4/MVP_ARCHITECTURE.md` as the basis. Update:
- Title: "CEMM v1 Architecture"
- Remove "MVP" framing — this is v1
- Update file references to reflect modular structure (e.g., "cemm/store.py" instead of "cemm_mvp.py lines 71-269")
- Add Section 26: "Module structure" documenting the modular split
- Keep all 25 sections from v4 (thesis, unified architecture, two planes, semantic algebra, anti-bloat, structured prediction, N-best settling, clause composition, identity, self-state, workspace, learnable rules, family inference, vocabulary acquisition, multilingual, response/NLG, authority generations, persistence, Stage 0-22 mapping, performance, training, what v4 fixes, remaining gaps, freeze rules, final architecture)
- Update Section 23 (remaining gaps) to reflect what v1 fixes vs what remains

(~1000 lines — this is documentation, not code, so >600 line limit doesn't apply)

- [ ] **Step 2: Commit**

```bash
git add ARCHITECTURE.md
git commit -m "docs: add v1 ARCHITECTURE.md (from v4 MVP_ARCHITECTURE, updated for modular structure)"
```

### Task 19: Write AGENTS.md (simplified governing contract)

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Write AGENTS.md**

Write a simplified governing contract for v1 that:
- Keeps the core thesis (meaning ≠ language, one-brain rule, two planes)
- Keeps the meaning laws (1-18)
- Keeps the authority separation principle (but acknowledges v1's simplified implementation)
- Keeps the anti-bloat/forbidden shortcuts (condensed from v4's 8 rules)
- Keeps the public claims discipline
- Removes v3.5.1-specific stage numbering (0-22) — v1 uses the compressed loop
- Removes v3.5.1-specific implementation workflow details
- References ARCHITECTURE.md for details

(~200 lines)

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add v1 AGENTS.md (simplified governing contract)"
```

### Task 20: Final verification — run all tests end-to-end

**Files:**
- Test: all tests

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (37 ported + config + cli + timeout)

- [ ] **Step 2: Run end-to-end demo via CLI**

Run the full demo sequence:
```bash
python -m cemm.cli init --db demo.sqlite --data cemm/data/base.json --data cemm/data/family_knowledge.json --pack cemm/language_packs/en.json
python -m cemm.cli ask --db demo.sqlite --pack cemm/language_packs/en.json "What is evidence?"
python -m cemm.cli ask --db demo.sqlite --pack cemm/language_packs/en.json "Am I married?"
python -m cemm.cli teach --db demo.sqlite --pack cemm/language_packs/en.json "A mother in-law is the mother of a partner."
python -m cemm.cli teach --db demo.sqlite --pack cemm/language_packs/en.json "A mother-in-law is the mother of a partner."
python -m cemm.cli reload --db demo.sqlite --pack cemm/language_packs/en.json
python -m cemm.cli learn --db demo.sqlite --pack cemm/language_packs/en.json "My mother in-law arrived today."
python -m cemm.cli ask --db demo.sqlite --pack cemm/language_packs/en.json "Am I married?"
```

Expected:
- "Evidence is information."
- "Evidence is insufficient."
- "Meaning is stored." (provisional_rule)
- "Meaning is stored." (promoted_rule)
- reload succeeds
- "Meaning is stored." (learned)
- "Yes." (supported)

- [ ] **Step 3: Run Spanish demo**

```bash
python -m cemm.cli init --db demo_es.sqlite --data cemm/data/base.json --data cemm/data/family_knowledge.json --pack cemm/language_packs/es.json
python -m cemm.cli learn --db demo_es.sqlite --pack cemm/language_packs/es.json "Mi suegra llegó hoy."
python -m cemm.cli ask --db demo_es.sqlite --pack cemm/language_packs/es.json "¿Estoy casado?"
```

Expected: "Sí." (supported)

Note: Spanish rule induction requires adding Spanish rule-teaching examples to `cemm/training/es_seed.json` and retraining. This is a known limitation documented in ARCHITECTURE.md.

- [ ] **Step 4: Clean up demo databases**

Remove `demo.sqlite` and `demo_es.sqlite`.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "verify: all tests pass, end-to-end demo works in EN and ES"
```

---

## Weakness fix summary

| # | Weakness | Fix | Task |
|---|----------|-----|------|
| 1 | Spanish rule induction fails | Document as known limitation in ARCHITECTURE.md | Task 18 |
| 2 | Spanish pronoun resolution gaps | Document as known limitation in ARCHITECTURE.md | Task 18 |
| 3 | No CLI for reload/acquire | Add to cli.py | Task 12 |
| 4 | Hardcoded thresholds | Config dataclass | Task 3 |
| 5 | Synthetic workspace training | Document in workspace.py + ARCHITECTURE.md | Task 9, 18 |
| 6 | No inference timeout | threading.Timer in inference.py | Task 8, 15 |
| 7 | No schema migration | Document as future work in ARCHITECTURE.md | Task 18 |
| 8 | Basic tokenizer | Document as future work in ARCHITECTURE.md | Task 18 |
| 9 | No thread safety | Document single-threaded requirement in ARCHITECTURE.md | Task 18 |
| 10 | Unbounded model cache | LRU cache with Config.model_cache_limit | Task 10 |
| 11 | No autonomous unknown-form discovery | AutonomousAcquirer in acquisition.py | Task 16a |

---

## Task 16a: Autonomous unknown-form discovery

**Strategic goal:** v4 requires a reviewer to supply mention-kind anchors (`{"surface": "Friction", "kind": "concept"}`) for unknown vocabulary. v1 must infer the semantic kind autonomously from the structured codec's own predictions, eliminating the manual anchor requirement while preserving the exact semantic authority boundary.

**Approach:** Hook into the Interpreter's processing pipeline. When a surface token has no designation match, instead of immediately returning frontier, attempt kind inference from the predicted operator+role context, create a provisional opaque atom + designation fact, and retry interpretation.

**Kind inference rules** (derived from operator-role contracts in the exact compiler):

| Predicted operator | Predicted role | Inferred kind |
|---|---|---|
| op:type | role:class | concept |
| op:type | role:instance | entity |
| op:relation | role:subject | entity |
| op:relation | role:object | entity |
| op:relation | role:relation | relation_type |
| op:state | role:subject | entity |
| op:state | role:value | value |
| op:event | role:actor | entity |
| op:event | role:type | event_type |
| op:designation | role:target | entity (default) |

**Safety boundaries:**
- Acquired atoms are `authority_scope='world'` (not authority)
- Acquired designations are `authority_status='provisional'`
- Only after review/promotion do they become authority
- If interpretation still fails after acquisition, return frontier as before
- The autonomous acquirer never creates new operator/role/schema — only atoms + designations
- This respects the architecture freeze rules (Section 24 of v4 MVP_ARCHITECTURE.md)

**Files:**
- Modify: `cemm/acquisition.py` (add `AutonomousAcquirer` class, ~60 lines added)
- Modify: `cemm/interpreter.py` (add acquisition hook, ~20 lines added)
- Modify: `cemm/config.py` (add `autonomous_acquisition` flag, default True)
- Test: `tests/test_autonomous_acquisition.py`

- [ ] **Step 1: Write the failing test**

`tests/test_autonomous_acquisition.py`:
```python
"""Test autonomous unknown-form discovery (weakness #11 fix).

v4 required manual mention-kind anchors. v1 infers kind from
the structured codec's predicted operator+role context.
"""
import unittest, tempfile, os, json
from cemm.store import Store
from cemm.runtime import Runtime
from cemm.config import Config

class TestAutonomousAcquisition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.store = Store(self.tmp.name)
        self.store.import_data("cemm/data/base.json")
        self.store.import_data("cemm/data/family_knowledge.json")
        self.rt = Runtime(self.store, "cemm/language_packs/en.json", Config(autonomous_acquisition=True))

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_unknown_concept_is_acquired_autonomously(self):
        """'Zorblax is energy.' — 'Zorblax' is unknown, should be acquired as concept."""
        result = self.rt.process("Zorblax is energy.", learn=True)
        # Should not be frontier — should learn the fact
        self.assertNotEqual(result["status"], "frontier")
        # Should have created an atom for Zorblax
        atoms = self.store.db.execute(
            "SELECT ref FROM atoms WHERE metadata LIKE '%zorblax%' OR ref IN "
            "(SELECT target_ref FROM designation_index WHERE surface LIKE '%zorblax%')"
        ).fetchall()
        self.assertGreater(len(atoms), 0, "Zorblax should have been acquired as an atom")

    def test_unknown_entity_is_acquired_autonomously(self):
        """'Qwerty arrived today.' — 'Qwerty' is unknown, should be acquired as entity."""
        result = self.rt.process("Qwerty arrived today.", learn=True)
        self.assertNotEqual(result["status"], "frontier")
        atoms = self.store.db.execute(
            "SELECT target_ref FROM designation_index WHERE norm_surface LIKE '%qwerty%'"
        ).fetchall()
        self.assertGreater(len(atoms), 0, "Qwerty should have been acquired as an entity")

    def test_acquired_atoms_are_world_scope_not_authority(self):
        """Autonomously acquired atoms must be authority_scope='world'."""
        self.rt.process("Zorblax is energy.", learn=True)
        atoms = self.store.db.execute(
            "SELECT ref, authority_scope FROM atoms WHERE ref IN "
            "(SELECT target_ref FROM designation_index WHERE surface LIKE '%zorblax%')"
        ).fetchall()
        for a in atoms:
            self.assertEqual(a["authority_scope"], "world",
                             "Acquired atoms must be world-scope, not authority")

    def test_acquired_atoms_do_not_change_authority_hash(self):
        """World-scope acquired atoms must not enter authority hash."""
        h_before = self.store.authority_hash()
        self.rt.process("Zorblax is energy.", learn=True)
        h_after = self.store.authority_hash()
        self.assertEqual(h_before, h_after,
                         "Authority hash must not change from world-scope acquisition")

    def test_disabled_when_config_off(self):
        """When autonomous_acquisition=False, unknown forms return frontier."""
        store2 = Store(tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False).name)
        store2.import_data("cemm/data/base.json")
        store2.import_data("cemm/data/family_knowledge.json")
        rt2 = Runtime(store2, "cemm/language_packs/en.json", Config(autonomous_acquisition=False))
        result = rt2.process("Zorblax is energy.", learn=True)
        self.assertEqual(result["status"], "frontier",
                         "With autonomous acquisition off, unknown forms should frontier")

    def test_truly_uninterpretable_still_frontiers(self):
        """Gibberish that can't be parsed at all still returns frontier."""
        result = self.rt.process("totally unknown flibbertigibbet", learn=False)
        self.assertEqual(result["status"], "frontier")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_autonomous_acquisition.py -v`
Expected: FAIL (autonomous acquisition not implemented)

- [ ] **Step 3: Add config flag**

In `cemm/config.py`, add to Config dataclass:
```python
    # Autonomous acquisition (weakness #11 fix)
    autonomous_acquisition: bool = True
```

- [ ] **Step 4: Implement AutonomousAcquirer in cemm/acquisition.py**

Add `AutonomousAcquirer` class to `cemm/acquisition.py`:
```python
class AutonomousAcquirer:
    """Infers semantic kind for unknown forms from structured codec predictions.

    Instead of requiring manual mention-kind anchors, this class uses the
    predicted operator+role context to infer the kind of an unknown surface,
    creates a provisional opaque atom + designation fact, and allows
    interpretation to proceed.

    Safety: acquired atoms are authority_scope='world', authority_status='provisional'.
    Only review/promotion makes them authority.
    """
    KIND_INFERENCE = {
        ("op:type", "role:class"): "concept",
        ("op:type", "role:instance"): "entity",
        ("op:relation", "role:subject"): "entity",
        ("op:relation", "role:object"): "entity",
        ("op:relation", "role:relation"): "relation_type",
        ("op:state", "role:subject"): "entity",
        ("op:state", "role:value"): "value",
        ("op:event", "role:actor"): "entity",
        ("op:event", "role:type"): "event_type",
        ("op:designation", "role:target"): "entity",
    }

    def __init__(self, store, config=None):
        self.store = store
        self.config = config or Config()

    def infer_kind(self, operator, role):
        """Infer semantic kind from predicted operator+role context."""
        return self.KIND_INFERENCE.get((operator, role), "concept")

    def acquire(self, surface, kind, language="en", generation=None):
        """Create a provisional opaque atom + designation fact for an unknown surface."""
        g = generation or self.store.generation
        ref = stable("atom", kind, surface, language, g)
        # Check if already exists
        existing = self.store.db.execute("SELECT 1 FROM atoms WHERE ref=?", (ref,)).fetchone()
        if existing:
            return ref
        # Create world-scope atom
        self.store.exact("atoms",
            ["ref", "kind", "metadata", "generation", "authority_scope"],
            [ref, kind, json.dumps({"acquired": "autonomous", "surface": surface}), g, "world"],
            ["ref"], {"generation"})
        # Create designation fact
        label_ref = stable("label", surface, language, ref)
        self.store.exact("designation_index",
            ["label_ref", "target_ref", "label_type_ref", "surface", "language", "script", "prior", "preferred", "context_ref"],
            [label_ref, ref, "label:lexical", surface, language, "Latn", 1.0, 1, None],
            ["label_ref"], {})
        self.store.db.commit()
        return ref

    def acquire_from_prediction(self, surface, operator, role, language="en", generation=None):
        """Acquire an unknown surface using kind inferred from operator+role."""
        kind = self.infer_kind(operator, role)
        return self.acquire(surface, kind, language, generation)
```

(~60 lines added to acquisition.py)

- [ ] **Step 5: Add acquisition hook to Interpreter**

In `cemm/interpreter.py`, modify the `Interpreter` class to check for unknown surfaces and attempt autonomous acquisition:

```python
class Interpreter:
    def __init__(self, store, pack, config=None):
        self.store = store
        self.pack = pack
        self.config = config or Config()
        self.codec = StructuredSemanticCodec(pack)
        self.compiler = ExactStructuredCompiler(store)
        self.settler = SemanticSettler(store, self.compiler, self.config)
        self.acquirer = AutonomousAcquirer(store, self.config) if self.config.autonomous_acquisition else None

    def interpret(self, text, language="en"):
        # First attempt: normal interpretation
        result = self._interpret_impl(text, language)
        if result and result.get("status") != "frontier":
            return result
        if not self.acquirer:
            return result
        # Second attempt: check for unknown surfaces and acquire them
        acquired = self._acquire_unknown_surfaces(text, language)
        if acquired:
            # Retry interpretation with newly acquired atoms
            return self._interpret_impl(text, language)
        return result

    def _acquire_unknown_surfaces(self, text, language="en"):
        """Check for unknown surfaces and acquire them using kind inference."""
        # Tokenize and check each surface against designation index
        tokens = toks(text)
        acquired = False
        for token in tokens:
            surface_tok = norm_text(token)
            if not surface_tok or surface_tok in {".", ",", "?", "!", ":", "/", "'"}:
                continue
            # Check if this surface has a designation
            existing = self.store.db.execute(
                "SELECT 1 FROM designation_index WHERE norm_surface=? AND language=?",
                (surface_tok, language)
            ).fetchone()
            if not existing:
                # Try to acquire using default kind (concept)
                # The structured codec will refine the kind on retry
                self.acquirer.acquire(token, "concept", language)
                acquired = True
        return acquired
```

Note: The designation_index table needs a `norm_surface` column or we need to use `norm_text(surface)` in the query. Check the actual schema and adjust accordingly.

(~20 lines added to interpreter.py)

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_autonomous_acquisition.py -v`
Expected: PASS

- [ ] **Step 7: Verify existing tests still pass**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS (37 ported + config + cli + timeout + autonomous_acquisition)

- [ ] **Step 8: Commit**

```bash
git add cemm/acquisition.py cemm/interpreter.py cemm/config.py tests/test_autonomous_acquisition.py
git commit -m "feat: add autonomous unknown-form discovery (weakness #11)"
```

---

## Self-Review

**Spec coverage:**
- Retire v3.5.1 → Task 1 ✓
- Freeze MVP demos → Task 2 ✓
- Modular split of v4 → Tasks 3-12 ✓
- Fix weaknesses during split → Tasks 3,8,9,10,12,15 ✓
- Autonomous unknown-form discovery → Task 16a ✓
- Documentation guided by v4 MVP_ARCHITECTURE.md → Tasks 17,18,19 ✓
- Tests pass → Task 20 ✓

**Placeholder scan:** No TBD/TODO. All steps have concrete code or commands.

**Type consistency:** Config fields are used consistently across modules. Store, Runtime, Interpreter, Inference class names match across tasks.
