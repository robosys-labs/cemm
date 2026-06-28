# CEMM Training Architecture — Day-One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the missing pieces to complete the Day-One training system specified in `cemm_training_architecture.md` — the training runner (`cemm_trainer.py`) is already complete at 514 lines (SQLite queue, JSONL ingest, parallel workers, HTTP adapter, caching, prompts).

**Architecture:** 5 phases — add missing tables → add Arbiter (disagreement scoring + arbitration) → add Evaluator → add Promoter → wire into main. No duplication of existing `cemm_trainer.py` functionality.

**Tech Stack:** Pure Python 3.11+, stdlib, SQLite via sqlite3, pytest.

---

## File Structure

- Modify: `C:\dev\cemm\cemm\store\schema.py` (add `training_labels`, `eval_sets`, `eval_results`, `promotion_candidates` tables)
- Create: `C:\dev\cemm\cemm\training\__init__.py`
- Create: `C:\dev\cemm\cemm\training\types.py`
- Create: `C:\dev\cemm\cemm\training\arbiter.py`
- Create: `C:\dev\cemm\cemm\training\evaluator.py`
- Create: `C:\dev\cemm\cemm\training\promoter.py`
- Modify: `C:\dev\cemm\cemm\__main__.py` (wire training run)

Reference: `C:\dev\cemm\cemm\cemm_trainer.py` — existing standalone runner, NOT duplicated

---

## Phase 1: Missing Tables + Training Init + Types

**Files:**
- Modify: `C:\dev\cemm\cemm\store\schema.py`
- Create: `C:\dev\cemm\cemm\training\__init__.py`
- Create: `C:\dev\cemm\cemm\training\types.py`

- [ ] **Step 1: Add missing tables to schema.py**

Append these table definitions to `C:\dev\cemm\cemm\store\schema.py` (before `INDEXES`):

```python
TRAINING_LABELS_TABLE = """
CREATE TABLE IF NOT EXISTS training_labels (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    arbiter_label_json TEXT,
    final_confidence REAL,
    source TEXT NOT NULL DEFAULT 'auto',
    created_at REAL NOT NULL DEFAULT 0.0,
    version TEXT NOT NULL DEFAULT 'cemm.training.v1',
    FOREIGN KEY (job_id) REFERENCES training_jobs(id)
)
"""

EVAL_SETS_TABLE = """
CREATE TABLE IF NOT EXISTS eval_sets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at REAL NOT NULL DEFAULT 0.0,
    version TEXT NOT NULL DEFAULT 'cemm.eval.v1'
)
"""

EVAL_SET_EXAMPLES_TABLE = """
CREATE TABLE IF NOT EXISTS eval_set_examples (
    eval_set_id TEXT NOT NULL,
    example_id TEXT NOT NULL,
    PRIMARY KEY (eval_set_id, example_id),
    FOREIGN KEY (eval_set_id) REFERENCES eval_sets(id),
    FOREIGN KEY (example_id) REFERENCES training_examples(id)
)
"""

EVAL_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS eval_results (
    id TEXT PRIMARY KEY,
    eval_set_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    score REAL,
    metrics_json TEXT,
    created_at REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (eval_set_id) REFERENCES eval_sets(id),
    FOREIGN KEY (job_id) REFERENCES training_jobs(id)
)
"""

PROMOTION_CANDIDATES_TABLE = """
CREATE TABLE IF NOT EXISTS promotion_candidates (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at REAL NOT NULL DEFAULT 0.0,
    reviewed_at REAL,
    version TEXT NOT NULL DEFAULT 'cemm.training.v1',
    FOREIGN KEY (model_id) REFERENCES models(id)
)
"""
```

- [ ] **Step 2: Add indexes**

Add to the `INDEXES` dict:

```python
    "idx_train_labels_job": "CREATE INDEX IF NOT EXISTS idx_train_labels_job ON training_labels(job_id)",
    "idx_eval_results_set": "CREATE INDEX IF NOT EXISTS idx_eval_results_set ON eval_results(eval_set_id)",
    "idx_promotion_candidates_status": "CREATE INDEX IF NOT EXISTS idx_promotion_candidates_status ON promotion_candidates(status)",
```

- [ ] **Step 3: Add create_schema calls**

Append to `create_schema()`:

```python
    conn.executescript(TRAINING_LABELS_TABLE)
    conn.executescript(EVAL_SETS_TABLE)
    conn.executescript(EVAL_SET_EXAMPLES_TABLE)
    conn.executescript(EVAL_RESULTS_TABLE)
    conn.executescript(PROMOTION_CANDIDATES_TABLE)
```

- [ ] **Step 4: Create `C:\dev\cemm\cemm\training\__init__.py`**

```python
from __future__ import annotations
```

- [ ] **Step 5: Create `C:\dev\cemm\cemm\training\types.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrainingLabel:
    id: str
    job_id: str
    arbiter_label: dict[str, Any] | None = None
    final_confidence: float | None = None
    source: str = "auto"
    created_at: float = 0.0


@dataclass
class EvalSet:
    id: str
    name: str
    description: str | None = None
    created_at: float = 0.0


@dataclass
class EvalResult:
    id: str
    eval_set_id: str
    job_id: str
    score: float | None = None
    metrics: dict[str, Any] | None = None
    created_at: float = 0.0


@dataclass
class PromotionCandidate:
    id: str
    model_id: str
    reason: str
    score: float = 0.0
    status: str = "pending"
    created_at: float = 0.0
    reviewed_at: float | None = None
```

- [ ] **Step 6: Run tests to verify no regression**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/ -v --tb=short }
```

Expected: all passing.

- [ ] **Step 7: Commit**

```bash
cd C:\dev\cemm; if ($?) { rtk git add -A; rtk git commit -m "feat: add training labels, eval sets, eval results, promotion candidate tables" }
```

---

## Phase 2: Arbiter (Disagreement Scoring + Arbitration)

**File:**
- Create: `C:\dev\cemm\cemm\training\arbiter.py`

This implements Sec 9 of the training architecture (confidence, disagreement scoring, arbitration). Does NOT exist in `cemm_trainer.py`.

- [ ] **Step 1: Write the failing test**

Create `C:\dev\cemm\tests\test_training_arbiter.py`:

```python
from __future__ import annotations
from cemm.training.arbiter import DisagreementScorer, Arbiter
from cemm.store.store import Store
import json


class TestDisagreementScorer:
    def test_identical_outputs_no_disagreement(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}], "confidence": 0.9}
        b = {"entities": [{"name": "A"}], "confidence": 0.9}
        assert scorer.score(a, b) == 0.0

    def test_different_entities_high_disagreement(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}], "confidence": 0.9}
        b = {"entities": [{"name": "B"}], "confidence": 0.9}
        assert scorer.score(a, b) > 0.0

    def test_confidence_gap_adds_disagreement(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}], "confidence": 0.9}
        b = {"entities": [{"name": "A"}], "confidence": 0.3}
        assert scorer.score(a, b) > 0.0

    def test_disagreement_bounded(self):
        scorer = DisagreementScorer()
        a = {"entities": [{"name": "A"}, {"name": "B"}], "confidence": 0.9,
             "evidence_refs": ["e1"], "uncertainty_reason": "low"}
        b = {"entities": [{"name": "C"}], "confidence": 0.1,
             "evidence_refs": ["e2"], "uncertainty_reason": "high"}
        assert 0.0 <= scorer.score(a, b) <= 1.0


class TestArbiter:
    def test_picks_highest_confidence(self):
        arbiter = Arbiter()
        outputs = [
            {"data": {"label": "A"}, "confidence": 0.9, "agent": "extractor"},
            {"data": {"label": "B"}, "confidence": 0.3, "agent": "critic"},
        ]
        result = arbiter.arbitrate(outputs)
        assert result["chosen_agent"] == "extractor"
        assert result["final_label"] == {"label": "A"}

    def test_single_agent_no_arbitration(self):
        arbiter = Arbiter()
        outputs = [{"data": {"label": "A"}, "confidence": 0.9, "agent": "extractor"}]
        result = arbiter.arbitrate(outputs)
        assert result["chosen_agent"] == "extractor"

    def test_empty_outputs_returns_default(self):
        arbiter = Arbiter()
        result = arbiter.arbitrate([])
        assert result["chosen_agent"] is None

    def test_score_and_store(self):
        """Integration: score disagreement then arbitrate."""
        store = Store(":memory:")
        arbiter = Arbiter(store=store)
        outputs = [
            {"data": {"label": "A"}, "confidence": 0.95, "agent": "extractor"},
            {"data": {"label": "B"}, "confidence": 0.4, "agent": "critic"},
        ]
        result = arbiter.arbitrate(outputs)
        assert result["chosen_agent"] == "extractor"
        assert result["final_label"] == {"label": "A"}

    def test_store_label(self):
        store = Store(":memory:")
        arbiter = Arbiter(store=store)
        label = arbiter.store_label("job_1", {"result": "ok"}, confidence=0.95)
        assert label.job_id == "job_1"
        assert label.final_confidence == 0.95
        assert label.source == "arbiter"
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/test_training_arbiter.py -v --tb=short }
```

Expected: ImportError.

- [ ] **Step 3: Write arbiter implementation**

```python
from __future__ import annotations
import sqlite3
import time
import uuid
from typing import Any
from ..store.store import Store
from .types import TrainingLabel


class DisagreementScorer:
    def score(self, output_a: dict[str, Any], output_b: dict[str, Any]) -> float:
        s = 0.0
        s += self._structure_mismatch(output_a, output_b)
        s += self._confidence_gap(output_a, output_b)
        s += self._evidence_mismatch(output_a, output_b)
        s += self._frame_mismatch(output_a, output_b)
        s += self._contradiction_flag(output_a, output_b)
        return min(s, 1.0)

    def _structure_mismatch(self, a: dict, b: dict) -> float:
        skip = {"confidence", "evidence_refs", "uncertainty_reason"}
        a_keys = set(a.keys()) - skip
        b_keys = set(b.keys()) - skip
        if not a_keys and not b_keys:
            return 0.0
        overlap = a_keys & b_keys
        total = a_keys | b_keys
        return 1.0 - (len(overlap) / len(total))

    def _confidence_gap(self, a: dict, b: dict) -> float:
        ca = a.get("confidence", 0.5) if isinstance(a.get("confidence"), (int, float)) else 0.5
        cb = b.get("confidence", 0.5) if isinstance(b.get("confidence"), (int, float)) else 0.5
        return abs(ca - cb)

    def _evidence_mismatch(self, a: dict, b: dict) -> float:
        ea = set(a.get("evidence_refs", []))
        eb = set(b.get("evidence_refs", []))
        if not ea and not eb:
            return 0.0
        overlap = ea & eb
        total = ea | eb
        return 1.0 - (len(overlap) / len(total))

    def _frame_mismatch(self, a: dict, b: dict) -> float:
        fa = a.get("context_frame") or a.get("frame_id")
        fb = b.get("context_frame") or b.get("frame_id")
        if fa is None and fb is None:
            return 0.0
        return 0.0 if fa == fb else 1.0

    def _contradiction_flag(self, a: dict, b: dict) -> float:
        contradictions = a.get("contradictions", [])
        if isinstance(contradictions, list):
            return 1.0 if contradictions else 0.0
        return 0.0


class Arbiter:
    def __init__(self, store: Store | None = None) -> None:
        self._scorer = DisagreementScorer()
        self._store = store
        self._conn: sqlite3.Connection | None = store._conn if store else None

    def arbitrate(self, agent_outputs: list[dict[str, Any]]) -> dict[str, Any]:
        if not agent_outputs:
            return {"final_label": None, "confidence": 0.0,
                    "explanation": "No agent outputs", "chosen_agent": None}
        if len(agent_outputs) == 1:
            o = agent_outputs[0]
            return {"final_label": o.get("data"), "confidence": o.get("confidence", 0.5),
                    "explanation": "Single agent", "chosen_agent": o.get("agent")}
        best = max(agent_outputs, key=lambda o: o.get("confidence", 0.0))
        return {"final_label": best.get("data"), "confidence": best.get("confidence", 0.5),
                "explanation": "Selected highest confidence agent",
                "chosen_agent": best.get("agent")}

    def store_label(
        self, job_id: str, label: dict[str, Any],
        confidence: float | None = None, source: str = "arbiter",
    ) -> TrainingLabel | None:
        if self._conn is None:
            return None
        label_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT INTO training_labels (id, job_id, arbiter_label_json, final_confidence, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (label_id, job_id, json.dumps(label) if label else None,
             confidence, source, now),
        )
        self._conn.commit()
        return TrainingLabel(
            id=label_id, job_id=job_id,
            arbiter_label=label, final_confidence=confidence,
            source=source, created_at=now,
        )
```

- [ ] **Step 4: Run tests**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/test_training_arbiter.py -v --tb=short }
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd C:\dev\cemm; if ($?) { rtk git add -A; rtk git commit -m "feat: add arbiter with disagreement scoring and label storage" }
```

---

## Phase 3: Evaluator

**File:**
- Create: `C:\dev\cemm\cemm\training\evaluator.py`

- [ ] **Step 1: Write the failing test**

Create `C:\dev\cemm\tests\test_training_evaluator.py`:

```python
from __future__ import annotations
from cemm.training.evaluator import Evaluator
from cemm.store.store import Store


class TestEvaluator:
    def test_create_eval_set(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "A test set")
        assert es.id is not None
        assert es.name == "test_set"

    def test_add_examples_to_set(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "")
        e.add_examples(es.id, ["ex1", "ex2"])
        count = e._conn.execute(
            "SELECT COUNT(*) FROM eval_set_examples WHERE eval_set_id = ?", (es.id,)
        ).fetchone()[0]
        assert count == 2

    def test_record_result(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "")
        r = e.record_result(es.id, "job_1", score=0.95, metrics={"precision": 0.9})
        assert r.eval_set_id == es.id
        assert r.job_id == "job_1"
        assert r.score == 0.95
        assert r.metrics == {"precision": 0.9}

    def test_get_results(self):
        e = Evaluator(Store(":memory:"))
        es = e.create_eval_set("test_set", "")
        e.record_result(es.id, "job_1", score=0.9)
        e.record_result(es.id, "job_2", score=0.8)
        results = e.get_results(es.id)
        assert len(results) == 2
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/test_training_evaluator.py -v --tb=short }
```

Expected: ImportError.

- [ ] **Step 3: Write evaluator implementation**

```python
from __future__ import annotations
import json
import sqlite3
import time
import uuid
from typing import Any
from ..store.store import Store
from .types import EvalSet, EvalResult


class Evaluator:
    def __init__(self, store: Store) -> None:
        self._conn: sqlite3.Connection = store._conn

    def create_eval_set(self, name: str, description: str | None = None) -> EvalSet:
        es_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT INTO eval_sets (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (es_id, name, description, now),
        )
        self._conn.commit()
        return EvalSet(id=es_id, name=name, description=description, created_at=now)

    def add_examples(self, eval_set_id: str, example_ids: list[str]) -> None:
        for ex_id in example_ids:
            self._conn.execute(
                "INSERT OR IGNORE INTO eval_set_examples (eval_set_id, example_id) VALUES (?, ?)",
                (eval_set_id, ex_id),
            )
        self._conn.commit()

    def record_result(
        self, eval_set_id: str, job_id: str,
        score: float | None = None, metrics: dict[str, Any] | None = None,
    ) -> EvalResult:
        r_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT INTO eval_results (id, eval_set_id, job_id, score, metrics_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (r_id, eval_set_id, job_id, score,
             json.dumps(metrics) if metrics else None, now),
        )
        self._conn.commit()
        return EvalResult(
            id=r_id, eval_set_id=eval_set_id, job_id=job_id,
            score=score, metrics=metrics, created_at=now,
        )

    def get_results(self, eval_set_id: str) -> list[EvalResult]:
        rows = self._conn.execute(
            "SELECT id, eval_set_id, job_id, score, metrics_json, created_at "
            "FROM eval_results WHERE eval_set_id = ? ORDER BY created_at",
            (eval_set_id,),
        ).fetchall()
        return [
            EvalResult(
                id=r[0], eval_set_id=r[1], job_id=r[2],
                score=r[3], metrics=json.loads(r[4]) if r[4] else None,
                created_at=r[5],
            )
            for r in rows
        ]
```

- [ ] **Step 4: Run tests**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/test_training_evaluator.py -v --tb=short }
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd C:\dev\cemm; if ($?) { rtk git add -A; rtk git commit -m "feat: add evaluator with eval sets and results tracking" }
```

---

## Phase 4: Promoter

**File:**
- Create: `C:\dev\cemm\cemm\training\promoter.py`

- [ ] **Step 1: Write the failing test**

Create `C:\dev\cemm\tests\test_training_promoter.py`:

```python
from __future__ import annotations
from cemm.training.promoter import Promoter
from cemm.store.store import Store
from cemm.types.model import Model, ModelKind, ModelStatus
import time


class TestPromoter:
    def test_create_candidate(self):
        p = Promoter(Store(":memory:"))
        c = p.create_candidate("model_1", "High accuracy", score=0.95)
        assert c.model_id == "model_1"
        assert c.score == 0.95
        assert c.status == "pending"

    def test_candidate_must_reference_existing_model(self):
        """Create candidate should succeed even if model doesn't exist yet."""
        p = Promoter(Store(":memory:"))
        c = p.create_candidate("nonexistent_model", "test", score=0.5)
        assert c.status == "pending"

    def test_approve_promotion(self):
        store = Store(":memory:")
        now = time.time()
        model = Model(
            id="model_to_promote", kind=ModelKind.PREDICATE, name="test",
            status=ModelStatus.CANDIDATE, created_at=now, updated_at=now,
        )
        store.models.put(model)
        p = Promoter(store)
        c = p.create_candidate("model_to_promote", "Good", score=0.9)
        success = p.approve(c.id)
        assert success is True
        row = p._conn.execute(
            "SELECT status FROM promotion_candidates WHERE id = ?", (c.id,)
        ).fetchone()
        assert row[0] == "approved"
        model_row = p._conn.execute(
            "SELECT status FROM models WHERE id = ?", ("model_to_promote",)
        ).fetchone()
        assert model_row[0] == "active"

    def test_reject_promotion(self):
        store = Store(":memory:")
        now = time.time()
        model = Model(
            id="model_to_reject", kind=ModelKind.PREDICATE, name="test",
            status=ModelStatus.CANDIDATE, created_at=now, updated_at=now,
        )
        store.models.put(model)
        p = Promoter(store)
        c = p.create_candidate("model_to_reject", "Bad", score=0.2)
        success = p.reject(c.id)
        assert success is True
        row = p._conn.execute(
            "SELECT status FROM promotion_candidates WHERE id = ?", (c.id,)
        ).fetchone()
        assert row[0] == "rejected"
        model_row = p._conn.execute(
            "SELECT status FROM models WHERE id = ?", ("model_to_reject",)
        ).fetchone()
        assert model_row[0] == "candidate"

    def test_list_pending(self):
        p = Promoter(Store(":memory:"))
        p.create_candidate("m1", "test", score=0.9)
        p.create_candidate("m2", "test2", score=0.3)
        pending = p.list_pending()
        assert len(pending) == 2

    def test_list_pending_ordered_by_score(self):
        p = Promoter(Store(":memory:"))
        p.create_candidate("m1", "low", score=0.3)
        p.create_candidate("m2", "high", score=0.9)
        p.create_candidate("m3", "mid", score=0.6)
        pending = p.list_pending()
        scores = [c.score for c in pending]
        assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/test_training_promoter.py -v --tb=short }
```

Expected: ImportError.

- [ ] **Step 3: Write promoter implementation**

```python
from __future__ import annotations
import sqlite3
import time
import uuid
from ..store.store import Store
from .types import PromotionCandidate


class Promoter:
    def __init__(self, store: Store) -> None:
        self._conn: sqlite3.Connection = store._conn

    def create_candidate(
        self, model_id: str, reason: str, score: float = 0.0,
    ) -> PromotionCandidate:
        c_id = uuid.uuid4().hex[:16]
        now = time.time()
        self._conn.execute(
            "INSERT INTO promotion_candidates (id, model_id, reason, score, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (c_id, model_id, reason, score, now),
        )
        self._conn.commit()
        return PromotionCandidate(
            id=c_id, model_id=model_id, reason=reason,
            score=score, status="pending", created_at=now,
        )

    def approve(self, candidate_id: str) -> bool:
        now = time.time()
        row = self._conn.execute(
            "SELECT model_id FROM promotion_candidates WHERE id = ? AND status = 'pending'",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return False
        model_id = row[0]
        self._conn.execute(
            "UPDATE promotion_candidates SET status = 'approved', reviewed_at = ? WHERE id = ?",
            (now, candidate_id),
        )
        self._conn.execute(
            "UPDATE models SET status = 'active' WHERE id = ?", (model_id,),
        )
        self._conn.commit()
        return True

    def reject(self, candidate_id: str) -> bool:
        now = time.time()
        self._conn.execute(
            "UPDATE promotion_candidates SET status = 'rejected', reviewed_at = ? "
            "WHERE id = ? AND status = 'pending'",
            (now, candidate_id),
        )
        self._conn.commit()
        return self._conn.total_changes > 0

    def list_pending(self) -> list[PromotionCandidate]:
        rows = self._conn.execute(
            "SELECT id, model_id, reason, score, status, created_at, reviewed_at "
            "FROM promotion_candidates WHERE status = 'pending' ORDER BY score DESC",
        ).fetchall()
        return [
            PromotionCandidate(id=r[0], model_id=r[1], reason=r[2],
                              score=r[3], status=r[4], created_at=r[5],
                              reviewed_at=r[6])
            for r in rows
        ]
```

- [ ] **Step 4: Run tests**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/test_training_promoter.py -v --tb=short }
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd C:\dev\cemm; if ($?) { rtk git add -A; rtk git commit -m "feat: add promoter with approve/reject lifecycle" }
```

---

## Phase 5: Wire into Main

**Files:**
- Modify: `C:\dev\cemm\cemm\__main__.py`

Add a `--train` subcommand that calls the existing `cemm_trainer.py`. Simple delegation rather than reimplementing what the standalone runner already does.

- [ ] **Step 1: Update `__main__.py`**

Add after existing imports:

```python
from .training.arbiter import Arbiter, DisagreementScorer
from .training.evaluator import Evaluator
from .training.promoter import Promoter
```

Add `--train` subcommand to the argparse section:

```python
    parser.add_argument("--train", nargs="?", const="cemm_training.sqlite3",
                        help="Run training: path to SQLite DB (default: cemm_training.sqlite3)")
```

Add to main(), before `if args.eval:`:

```python
    if args.train:
        if args.train == "cemm_training.sqlite3" and not os.path.exists(args.train):
            print(f"No training DB at {args.train}. Create one via:")
            print(f"  python -m cemm.cemm_trainer ingest examples.jsonl")
            print(f"  python -m cemm.cemm_trainer run --workers 4")
            return
        from . import cemm_trainer
        sys.argv = ["cemm_trainer", "run", "--db", args.train, "--workers",
                    str(args.workers), "--poll-s", "2.0"]
        if args.dry_run:
            sys.argv.append("--dry-run")
        raise SystemExit(cemm_trainer.main(sys.argv[1:]))
```

Also add `--dry-run` to the parser:

```python
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode for training")
```

And add `import os` if not already present.

- [ ] **Step 2: Run full test suite**

```bash
cd C:\dev\cemm; if ($?) { python -m pytest tests/ -v --tb=short }
```

Expected: all passing (176 + new tests).

- [ ] **Step 3: Commit**

```bash
cd C:\dev\cemm; if ($?) { rtk git add -A; rtk git commit -m "feat: wire training subcommand into main, delegate to cemm_trainer" }
```

---

## Verification

```bash
cd C:\dev\cemm; if ($?) { rtk python -m pytest tests/ -v --tb=short }
```

Expected: all tests passing.

---

## Self-Review Checklist

1. **Spec coverage:** Covers Sec 9 (disagreement scoring + arbiter), Sec 12 (eval_sets, eval_results, promotion_candidates tables), Sec 15 (metrics tracked via eval_results). No duplication of Sec 14 items already in `cemm_trainer.py` (SQLite queue, JSONL ingest, worker pool, HTTP adapter, caching, prompts, JSON parsing).
2. **Placeholder scan:** No TBD, TODO, or "implement later" patterns.
3. **Type consistency:** All types from `training/types.py` are single source of truth for the new modules. `cemm_trainer.py` uses its own schemas and stays independent.
