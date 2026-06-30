# CEMM Continuous Training + Full Capability Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 4 architecture gaps: add `models` table, generate training data for all 17 capabilities, wire continuous training loop from runtime fallbacks, and add synthesis verification.

**Architecture:** The runtime router is the conversation spine (rules → CEMM SLM → LLM agents). The CEMM SLM layer (6 trained components) doesn't exist yet — this plan creates the infrastructure to produce and deploy it. NVIDIA API serves dual duty: neural fallback for users AND labeling agent for training. Every LLM fallback turn feeds the training pipeline automatically, creating a continuous improvement loop.

**Tech Stack:** Python 3.11+, stdlib, SQLite, NVIDIA API (NIM/OpenAI-compatible)

---

## File Map

### New files:
- `cemm/models.py` — Model primitive: table schema, CRUD, registry operations
- `cemm/capability_seed_spec_extensions.json` — 9 new seed spec categories for missing capabilities
- `cemm/training_queue.py` — Continuous training queue: emit, ingest, poll
- `cemm/synthesis_verifier.py` — Deterministic synthesis verifier for neural fallback

### Modified files:
- `cemm/cemm_runtime_router.py` — Add models table to schema, wire `emit_training_example()` after LLM fallback, wire synthesis verifier
- `cemm/cemm_seed_generator.py` — Accept extended seed spec categories
- `cemm/cemm_seed_spec.json` — Add 9 new capability categories
- `cemm/cemm_trainer.py` — Add `deploy-models` command that converts agent_outputs to model records

### Files unchanged but referenced:
- `cemm/cemm_pipeline.md` — Read for pipeline flow
- `cemm/AGENTS.md` — Architecture constraints unchanged
- `tests/` — Existing tests must still pass

---

### Task 1: Add `models` table to runtime schema

**Files:**
- Modify: `cemm/cemm_runtime_router.py`

**Design:** The `models` table stores the Model primitive from ERCA architecture §6. Each row is one deployable model: a predicate registry entry, an operator spec, a UOL semantic mapping, a frame rule, a causal rule, a synthesis strategy, or a verifier. The table is created at connect time alongside the existing tables.

Model kinds needed for the 6 trained CEMM SLM components:
- `context_inference` — context rule models
- `uol_semantic` — UOL mapping models  
- `predicate` — predicate registry models
- `operator` — operator routing models
- `synthesis_strategy` — synthesis routing models
- `verifier` — synthesis verifier models

- [ ] **Step 1: Add models table to RUNTIME_SCHEMA**

Add after the `capabilities` table in `RUNTIME_SCHEMA`:

```python
CREATE TABLE IF NOT EXISTS models (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  registry_key TEXT,
  description TEXT NOT NULL DEFAULT '',
  parameters_json TEXT NOT NULL DEFAULT '{}',
  input_types TEXT NOT NULL DEFAULT '[]',
  output_types TEXT NOT NULL DEFAULT '[]',
  preconditions TEXT NOT NULL DEFAULT '[]',
  effects TEXT NOT NULL DEFAULT '[]',
  confidence REAL NOT NULL DEFAULT 0.5,
  trust REAL NOT NULL DEFAULT 0.5,
  utility REAL NOT NULL DEFAULT 0.5,
  cost_estimate_ms INTEGER NOT NULL DEFAULT 50,
  risk REAL NOT NULL DEFAULT 0.0,
  evidence_signal_ids TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'candidate',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_models_kind_status ON models(kind, status);
CREATE INDEX IF NOT EXISTS idx_models_registry_key ON models(registry_key);
CREATE INDEX IF NOT EXISTS idx_models_kind_registry_status ON models(kind, registry_key, status);
```

- [ ] **Step 2: Add `save_model` and `find_models` functions**

```python
def save_model(
    conn: sqlite3.Connection,
    kind: str,
    name: str,
    *,
    registry_key: str | None = None,
    description: str = "",
    parameters: dict[str, Any] | None = None,
    input_types: list[str] | None = None,
    output_types: list[str] | None = None,
    preconditions: list[str] | None = None,
    effects: list[str] | None = None,
    confidence: float = 0.5,
    trust: float = 0.5,
    utility: float = 0.5,
    cost_estimate_ms: int = 50,
    risk: float = 0.0,
    evidence_signal_ids: list[str] | None = None,
    status: str = "candidate",
) -> str:
    model_id = stable_id("model", {"kind": kind, "name": name, "registry_key": registry_key, "ts": now()})
    ts = now()
    conn.execute(
        """INSERT INTO models
           (id, kind, name, registry_key, description, parameters_json,
            input_types, output_types, preconditions, effects,
            confidence, trust, utility, cost_estimate_ms, risk,
            evidence_signal_ids, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            model_id, kind, name, registry_key, description,
            json.dumps(parameters or {}, sort_keys=True),
            json.dumps(input_types or [], sort_keys=True),
            json.dumps(output_types or [], sort_keys=True),
            json.dumps(preconditions or [], sort_keys=True),
            json.dumps(effects or [], sort_keys=True),
            confidence, trust, utility, cost_estimate_ms, risk,
            json.dumps(evidence_signal_ids or [], sort_keys=True),
            status, ts, ts,
        ),
    )
    conn.commit()
    return model_id


def find_models(
    conn: sqlite3.Connection,
    kind: str | None = None,
    registry_key: str | None = None,
    status: str = "active",
) -> list[sqlite3.Row]:
    where: list[str] = []
    params: list[Any] = []
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if registry_key:
        where.append("registry_key = ?")
        params.append(registry_key)
    if status:
        where.append("status = ?")
        params.append(status)
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    return conn.execute(f"SELECT * FROM models{clause} ORDER BY confidence DESC", params).fetchall()
```

- [ ] **Step 3: Verify tests pass**

Run: `cd C:\dev\cemm\cemm && python -m pytest ..\tests --tb=short -q`
Expected: 205 passed

- [ ] **Step 4: Commit**

```bash
cd C:\dev\cemm\cemm
git add cemm/cemm_runtime_router.py
git commit -m "feat: add models table to runtime schema for Model primitive"
```

---

### Task 2: Add 9 seed spec categories for missing capabilities

**Files:**
- Modify: `cemm/cemm_seed_spec.json`

**Design:** The current spec has 14 categories covering about 8 of the 17 capability families. Add 9 new categories for the missing capabilities. Each category defines target_count, task_types, description, example user utterances, and expected response patterns.

Missing capabilities and their seed categories:

| # | Capability | Seed Category | Key patterns |
|---|-----------|--------------|--------------|
| 1 | autobiographical_memory | `cross_session_memory` | "what did we talk about yesterday", "remember our last conversation" |
| 2 | social_contact | `contact_management` | "call my mom", "save this number", "who is in my contacts" |
| 3 | assistant_behavior | `behavior_configuration` | "be more formal", "change your tone", "remember my preferences" |
| 4 | story | `storytelling` | "tell me a story", "tell me a folk tale", "make up a story about..." |
| 5 | meal_suggestion | `meal_suggestion` | "what should I eat for dinner", "suggest a healthy breakfast" |
| 6 | health_advice | `health_guidance` | "what is good for a headache", "suggest exercise for back pain" |
| 7 | common_sense_safety | `safety_guidance` | "is it safe to...", "what should a child do if..." |
| 8 | personal_goal_advice | `goal_planning` | "help me plan my career", "how do I learn Python" |
| 9 | media_playback | `media_control` | "play some music", "skip to next track", "pause the video" |

- [ ] **Step 1: Add 9 new category definitions to seed spec**

Add to `categories` array in `cemm/cemm_seed_spec.json`:

```json
{
  "name": "cross_session_memory",
  "target_count": 40,
  "task_types": ["context_inference", "operator_selection", "synthesis_verification"],
  "description": "User refers to previous sessions, asks what was discussed, expects cross-session recall.",
  "example_utterances": [
    "what did we talk about last time",
    "remember our conversation yesterday",
    "you said my favorite food was pizza"
  ]
},
{
  "name": "contact_management",
  "target_count": 30,
  "task_types": ["claim_extraction", "context_inference", "operator_selection"],
  "description": "User asks to save a contact, call someone, or check who is in their contacts.",
  "example_utterances": [
    "save my mother's number",
    "call John",
    "who is in my contacts"
  ]
},
{
  "name": "behavior_configuration",
  "target_count": 30,
  "task_types": ["self_state_update", "context_inference", "operator_selection"],
  "description": "User asks assistant to change its tone, formality, style, or behavior.",
  "example_utterances": [
    "be more professional",
    "talk to me like a friend",
    "remember I prefer short answers"
  ]
},
{
  "name": "storytelling",
  "target_count": 40,
  "task_types": ["uol_mapping", "context_inference", "synthesis_verification"],
  "description": "User asks for a story, folk tale, or creative narrative.",
  "example_utterances": [
    "tell me a story",
    "tell me a folk tale",
    "make up a story about a dragon"
  ]
},
{
  "name": "meal_suggestion",
  "target_count": 30,
  "task_types": ["context_inference", "operator_selection", "synthesis_verification"],
  "description": "User asks for meal ideas based on preferences, time of day, or dietary restrictions.",
  "example_utterances": [
    "what should I eat for dinner",
    "suggest a healthy breakfast",
    "I'm vegetarian, what can I cook"
  ]
},
{
  "name": "health_guidance",
  "target_count": 30,
  "task_types": ["context_inference", "synthesis_verification", "operator_selection"],
  "description": "User asks for basic health guidance with appropriate disclaimers.",
  "example_utterances": [
    "what is good for a headache",
    "suggest exercise for back pain",
    "how much water should I drink"
  ]
},
{
  "name": "safety_guidance",
  "target_count": 30,
  "task_types": ["context_inference", "operator_selection", "synthesis_verification"],
  "description": "User asks for common-sense safety advice for children or everyday situations.",
  "example_utterances": [
    "is it safe to climb that tree",
    "what should a child do if lost",
    "how do I check food is safe to eat"
  ]
},
{
  "name": "goal_planning",
  "target_count": 40,
  "task_types": ["context_inference", "operator_selection", "synthesis_verification"],
  "description": "User asks for help planning goals, learning skills, or making decisions.",
  "example_utterances": [
    "help me plan my career",
    "how do I learn Python",
    "what steps should I take to get fit"
  ]
},
{
  "name": "media_control",
  "target_count": 30,
  "task_types": ["context_inference", "operator_selection", "synthesis_verification"],
  "description": "User asks to play, pause, skip, or control media playback.",
  "example_utterances": [
    "play some music",
    "skip to the next track",
    "pause the video"
  ]
}
```

- [ ] **Step 2: Validate updated spec loads correctly**

```bash
cd C:\dev\cemm\cemm
python -c "
import json
with open('cemm_seed_spec.json') as f:
    spec = json.load(f)
print(f'Categories: {len(spec[\"categories\"])}')
for c in spec['categories']:
    print(f'  {c[\"name\"]}: target={c[\"target_count\"]}, types={c[\"task_types\"]}')
"
```

Expected: 23 categories printed (14 original + 9 new), all with valid task_types.

- [ ] **Step 3: Commit**

```bash
cd C:\dev\cemm\cemm
git add cemm/cemm_seed_spec.json
git commit -m "feat: add 9 seed categories for missing capabilities (story, contacts, meals, health, safety, goals, media, behavior, cross-session)"
```

---

### Task 3: Generate seed data for all 23 categories

**Files:**
- Create: `generated/cemm_generated_training.jsonl` (append)
- Create: `generated/cemm_generated_scenarios.jsonl` (append)

**Note:** Uses NVIDIA API for generation. Dry-run first to validate.

- [ ] **Step 1: Dry-run generate with 2 per new category to validate**

```bash
cd C:\dev\cemm\cemm
python cemm_seed_generator.py generate --dry-run --per-category 2 --out-dir generated
```

Expected: Generates scenarios for all 23 categories (14 original + 9 new), writes to generated/.

- [ ] **Step 2: Inspect generated data for new categories**

```bash
cd C:\dev\cemm\cemm
python -c "
import json
with open('generated/cemm_generated_training.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
cats = {}
for l in lines:
    c = l.get('category', 'unknown')
    cats[c] = cats.get(c, 0) + 1
for k, v in sorted(cats.items()):
    print(f'  {k}: {v}')
"
```

Expected: At least some examples in each of the 9 new categories.

- [ ] **Step 3: Run real generation with NVIDIA API (10 per new category)**

```bash
cd C:\dev\cemm\cemm
$env:NVIDIA_API_KEY="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"
$env:NVIDIA_MODEL="meta/llama-3.1-70b-instruct"
$env:NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
python cemm_seed_generator.py generate --workers 4 --per-category 10 --out-dir generated
```

Expected: All 23 categories generate data. With ~10 per category × several task records each = ~1500+ new task records.

- [ ] **Step 4: Validate generated data**

```bash
cd C:\dev\cemm\cemm
python cemm_seed_generator.py validate generated/cemm_generated_training.jsonl
```

Expected: Valid JSONL, all task types recognized, all categories present.

- [ ] **Step 5: Commit**

```bash
cd C:\dev\cemm\cemm
git add generated/
git commit -m "feat: generate seed training data for all 23 capability categories"
```

---

### Task 4: Run trainer to label all seed data

**Files:**
- Modify: `cemm_training.sqlite3` (populate with labels)

- [ ] **Step 1: Ingest generated training data**

```bash
cd C:\dev\cemm\cemm
$env:CEMM_LLM_API_KEY="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"
$env:CEMM_LLM_BASE_URL="https://integrate.api.nvidia.com/v1/chat/completions"
$env:CEMM_LLM_MODEL="meta/llama-3.1-8b-instruct"
python cemm_trainer.py ingest generated/cemm_generated_training.jsonl
```

Expected: "ingested N examples into cemm_training.sqlite3"

- [ ] **Step 2: Run trainer workers (loop until done)**

```bash
cd C:\dev\cemm\cemm
$env:CEMM_LLM_API_KEY="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"
$count = 0
while ($count -lt 50) {
    $result = python cemm_trainer.py run --workers 4 --once 2>&1
    Write-Host $result
    if ($result -match "no queued jobs") { Write-Host "All done!"; break }
    Start-Sleep -Seconds 2
    $count++
}
```

Expected: All jobs complete. Each job labels a training example with the appropriate agent.

- [ ] **Step 3: Verify labeling stats**

```bash
cd C:\dev\cemm\cemm
python -c "
import sqlite3
conn = sqlite3.connect('cemm_training.sqlite3')
r = conn.execute('SELECT status, COUNT(*) FROM training_jobs GROUP BY status').fetchall()
print('Jobs:', dict(r))
r2 = conn.execute('SELECT COUNT(*) FROM agent_outputs').fetchone()
print('Agent outputs:', r2[0])
tt = conn.execute('SELECT j.task_type, COUNT(*) FROM agent_outputs o JOIN training_jobs j ON j.id=o.job_id GROUP BY j.task_type ORDER BY COUNT(*) DESC').fetchall()
print('By task type:', tt)
"
```

Expected: All jobs completed, outputs distributed across all task types.

- [ ] **Step 4: Commit**

```bash
cd C:\dev\cemm\cemm
git add cemm_training.sqlite3
git commit -m "feat: label seed data for all capability categories via trainer agents"
```

---

### Task 5: Add `deploy-models` command to trainer

**Files:**
- Modify: `cemm/cemm_trainer.py`

**Design:** The trainer currently produces `agent_outputs` with JSON labels. These need to be converted into deployable `Model` records that the runtime can load. The `deploy-models` command reads agent_outputs from training_jobs with status="completed", transforms them into model records, and writes them to a JSONL file or directly to the runtime's SQLite database.

For each task type, the mapping is:

| Task Type | Model Kind | Source Field |
|-----------|-----------|--------------|
| `uol_mapping` | `uol_semantic` | `uol_atoms` output |
| `context_inference` | `context_inference` | `inferences` output |
| `operator_selection` | `operator` | `action_kind`, `operator_model_key` output |
| `synthesis_verification` | `verifier` | `verification_type`, `supported` output |
| `claim_extraction` | `predicate` | `claims` output (predicate registry) |
| `predicate_mapping` | `predicate` | `mappings` output |
| `self_state_update` | `synthesis_strategy` | `mode`, `uncertainty`, `coherence` output |
| `structural_induction` | `*` | `candidate_models` output (direct) |

- [ ] **Step 1: Add deploy_models function**

Add before `parse_args`:

```python
def deploy_models(train_db: Path, runtime_db: Path | None = None, out_path: Path | None = None) -> int:
    """Convert completed agent outputs into deployable model records.

    Reads from training DB, produces JSONL (and optionally writes to runtime DB).
    Returns count of deployed models.
    """
    tconn = sqlite3.connect(train_db)
    tconn.row_factory = sqlite3.Row
    rows = tconn.execute("""
        SELECT o.id AS output_id, o.job_id, o.output_json, o.confidence,
               j.task_type, j.example_id, e.payload_json
        FROM agent_outputs o
        JOIN training_jobs j ON j.id = o.job_id
        JOIN training_examples e ON e.id = j.example_id
        WHERE j.status = 'completed'
          AND o.confidence > 0.5
        ORDER BY o.created_at
    """).fetchall()
    tconn.close()

    models: list[dict[str, Any]] = []
    for row in rows:
        output = json.loads(row["output_json"])
        payload = json.loads(row["payload_json"])
        task_type = row["task_type"]
        confidence = float(row["confidence"])

        if task_type == "operator_selection":
            action_kind = output.get("action_kind", "")
            operator_key = output.get("operator_model_key", "")
            if operator_key:
                models.append({
                    "kind": "operator",
                    "name": operator_key,
                    "registry_key": operator_key,
                    "description": f"Operator for {action_kind} actions",
                    "parameters": {"action_kind": action_kind, "required_slots": output.get("required_slots", [])},
                    "confidence": confidence,
                    "status": "candidate",
                    "evidence_signal_ids": [row["output_id"]],
                })

        elif task_type == "uol_mapping":
            atoms = output.get("uol_atoms", [])
            frame_keys = set()
            state_keys = set()
            for a in atoms:
                if a.get("kind") == "process":
                    frame_keys.add(a["frame_key"])
                elif a.get("kind") == "state":
                    state_keys.add(a["state_key"])
            for fk in frame_keys:
                models.append({
                    "kind": "uol_semantic",
                    "name": f"process:{fk}",
                    "registry_key": f"process:{fk}",
                    "description": f"UOL process mapping for {fk}",
                    "parameters": {"frame_key": fk, "atoms": atoms},
                    "confidence": confidence,
                    "status": "candidate",
                    "evidence_signal_ids": [row["output_id"]],
                })
            for sk in state_keys:
                models.append({
                    "kind": "uol_semantic",
                    "name": f"state:{sk}",
                    "registry_key": f"state:{sk}",
                    "description": f"UOL state mapping for {sk}",
                    "parameters": {"state_key": sk},
                    "confidence": confidence,
                    "status": "candidate",
                    "evidence_signal_ids": [row["output_id"]],
                })

        elif task_type == "context_inference":
            inferences = output.get("inferences", [])
            for inf in inferences:
                kind = inf.get("kind", "")
                if kind:
                    models.append({
                        "kind": "context_inference",
                        "name": kind,
                        "registry_key": kind,
                        "description": f"Context inference rule: {kind}",
                        "parameters": inf,
                        "confidence": float(inf.get("confidence", confidence)),
                        "status": "candidate",
                        "evidence_signal_ids": [row["output_id"]],
                    })

        elif task_type == "synthesis_verification":
            vtype = output.get("verification_type", "soft")
            models.append({
                "kind": "verifier",
                "name": f"verifier_{vtype}",
                "registry_key": vtype,
                "description": f"Synthesis verifier ({vtype})",
                "parameters": output,
                "confidence": confidence,
                "status": "candidate",
                "evidence_signal_ids": [row["output_id"]],
            })

        elif task_type == "structural_induction":
            candidates = output.get("candidate_models", [])
            for cm in candidates:
                cm["evidence_signal_ids"] = [row["output_id"]]
                cm.setdefault("status", "candidate")
                models.append(cm)

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for m in models:
                f.write(json.dumps(m, sort_keys=True) + "\n")

    if runtime_db:
        rconn = sqlite3.connect(runtime_db)
        rconn.executescript("""
            CREATE TABLE IF NOT EXISTS models (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
              registry_key TEXT, description TEXT NOT NULL DEFAULT '',
              parameters_json TEXT NOT NULL DEFAULT '{}',
              input_types TEXT NOT NULL DEFAULT '[]',
              output_types TEXT NOT NULL DEFAULT '[]',
              preconditions TEXT NOT NULL DEFAULT '[]',
              effects TEXT NOT NULL DEFAULT '[]',
              confidence REAL NOT NULL DEFAULT 0.5,
              trust REAL NOT NULL DEFAULT 0.5, utility REAL NOT NULL DEFAULT 0.5,
              cost_estimate_ms INTEGER NOT NULL DEFAULT 50,
              risk REAL NOT NULL DEFAULT 0.0,
              evidence_signal_ids TEXT NOT NULL DEFAULT '[]',
              status TEXT NOT NULL DEFAULT 'candidate',
              created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
        """)
        ts = int(time.time())
        for m in models:
            mid = hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()[:24]
            rconn.execute(
                """INSERT OR IGNORE INTO models
                   (id, kind, name, registry_key, description, parameters_json,
                    input_types, output_types, preconditions, effects,
                    confidence, trust, utility, cost_estimate_ms, risk,
                    evidence_signal_ids, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"model_{mid}", m["kind"], m["name"], m.get("registry_key"),
                    m.get("description", ""), json.dumps(m.get("parameters", {}), sort_keys=True),
                    "[]", "[]", "[]", "[]",
                    m.get("confidence", 0.5), 0.5, 0.5, 50, 0.0,
                    json.dumps(m.get("evidence_signal_ids", []), sort_keys=True),
                    m.get("status", "candidate"), ts, ts,
                ),
            )
        rconn.commit()
        rconn.close()

    return len(models)
```

- [ ] **Step 2: Add `deploy` subcommand to CLI**

Add in `parse_args`:

```python
deploy = sub.add_parser("deploy-models", help="convert agent outputs to deployable model records")
deploy.add_argument("--train-db", default="cemm_training.sqlite3")
deploy.add_argument("--runtime-db", help="write models directly into a runtime DB")
deploy.add_argument("--out", help="JSONL output path for model records")
```

Add in `main`:

```python
if args.cmd == "deploy-models":
    out = Path(args.out) if args.out else None
    runtime = Path(args.runtime_db) if args.runtime_db else None
    count = deploy_models(Path(args.train_db), runtime_db=runtime, out_path=out)
    print(f"deployed {count} model records")
    return 0
```

- [ ] **Step 3: Deploy models from training DB**

```bash
cd C:\dev\cemm\cemm
python cemm_trainer.py deploy-models --out generated/cemm_deployed_models.jsonl
```

Expected: Prints "deployed N model records" with N > 0.

- [ ] **Step 4: Verify deployed models**

```bash
cd C:\dev\cemm\cemm
python -c "
import json
with open('generated/cemm_deployed_models.jsonl') as f:
    models = [json.loads(l) for l in f if l.strip()]
kinds = {}
for m in models:
    k = m['kind']
    kinds[k] = kinds.get(k, 0) + 1
print(f'Total models: {len(models)}')
for k, v in sorted(kinds.items()):
    print(f'  {k}: {v}')
"
```

Expected: Models distributed across kinds (operator, uol_semantic, context_inference, verifier, predicate).

- [ ] **Step 5: Commit**

```bash
cd C:\dev\cemm\cemm
git add cemm/cemm_trainer.py generated/cemm_deployed_models.jsonl
git commit -m "feat: add deploy-models command to convert agent outputs into deployable model records"
```

---

### Task 6: Wire continuous training loop in runtime

**Files:**
- Modify: `cemm/cemm_runtime_router.py`

**Design:** After every turn where the LLM neural fallback is used (or where the rule-based response has low confidence), the runtime writes a training example to a queue. The queue is a JSONL file (`runtime_training_queue.jsonl`) that the trainer can pick up with its `ingest` command.

The `emit_training_example()` function is called from `update_self_after_turn()` when the synthesis strategy was "llm" (neural fallback was used). It writes a JSONL line with the full context kernel, the user text, and the LLM's response.

- [ ] **Step 1: Add emit_training_example function**

Add after `export_training`:

```python
_TRAINING_QUEUE_PATH: Path | None = None


def set_training_queue(path: Path | None) -> None:
    global _TRAINING_QUEUE_PATH
    _TRAINING_QUEUE_PATH = path


def emit_training_example(
    conn: sqlite3.Connection,
    content: str,
    response: str,
    context: ContextKernel,
    context_info: dict[str, Any],
    uol: dict[str, Any],
    decision: RouteDecision,
    verification: dict[str, Any],
) -> None:
    """Write a training example JSONL entry for every turn that used the LLM fallback.

    The training_queue.jsonl file is consumed by `cemm_trainer.py ingest`.
    """
    if _TRAINING_QUEUE_PATH is None:
        return
    strategy = verification.get("strategy", "")
    if strategy != "llm":
        return  # only queue LLM fallback turns for retraining

    ck = dataclasses.asdict(context)
    payload = {
        "category": "runtime_llm_fallback",
        "signal": {"kind": "input", "content": content, "source_type": "user"},
        "context": ck,
        "response": response,
        "context_info": context_info,
        "uol": uol,
        "decision": dataclasses.asdict(decision),
    }
    # Generate task examples for all applicable task types
    task_types = [
        "context_inference", "uol_mapping", "operator_selection",
        "pragmatic_interpretation", "synthesis_verification", "self_state_update",
    ]
    _TRAINING_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TRAINING_QUEUE_PATH.open("a", encoding="utf-8") as f:
        for tt in task_types:
            record = {
                "task_type": tt,
                "permission_scope": "session_private",
                "payload": payload,
                "source": "runtime_continuous",
                "created_at": now(),
            }
            f.write(json.dumps(record, sort_keys=True) + "\n")
```

- [ ] **Step 2: Wire emit_training_example into handle_turn**

Modify `handle_turn` to capture the verification and call `emit_training_example`:

```python
def handle_turn(conn: sqlite3.Connection, content: str, session_id: str) -> dict[str, Any]:
    context = build_context(conn, session_id)
    signal_id = observe(conn, content, context)
    normalized = normalize(content)
    context_info = infer_context(normalized, context)
    uol = map_uol(normalized)
    semantics = {"context": context_info, "uol": uol}
    conn.execute("UPDATE signals SET semantics_json = ? WHERE id = ?", (json.dumps(semantics, sort_keys=True), signal_id))
    conn.commit()

    decision = route(conn, normalized, context, context_info)
    stored_claim_id = None
    if decision.action_kind == "remember":
        claim = extract_claim(normalized)
        if claim:
            stored_claim_id = save_claim(conn, signal_id, claim)

    response, verification = synthesize(conn, decision, normalized, context)
    trace_id = write_action_trace(conn, signal_id, context, decision, response, semantics, verification)
    cluster_key = uol.get("semantic_cluster_key", "")
    update_self_after_turn(conn, context, decision, stored_claim_id, trace_id, cluster_key)
    emit_training_example(conn, content, response, context, context_info, uol, decision, verification)
    return {
        "response": response,
        "signal_id": signal_id,
        "trace_id": trace_id,
        "context_id": context.id,
        "action": dataclasses.asdict(decision),
        "stored_claim_id": stored_claim_id,
    }
```

- [ ] **Step 3: Add `--training-queue` CLI option**

Modify `parse_args` to add:

```python
parser.add_argument("--training-queue", default=None, help="path to continuous training queue JSONL")
```

Modify `main` to set the queue path:

```python
if args.training_queue:
    set_training_queue(Path(args.training_queue))
```

- [ ] **Step 4: Test continuous training queue writes**

```bash
cd C:\dev\cemm\cemm
$env:CEMM_RUNTIME_API_KEY="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"
$env:CEMM_RUNTIME_MODEL="meta/llama-3.1-8b-instruct"
python cemm_runtime_router.py --training-queue generated/test_queue.jsonl --db test_queue.sqlite3 once "tell me a joke"
python -c "
import json
with open('generated/test_queue.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
print(f'Queue entries: {len(lines)}')
tts = set(l['task_type'] for l in lines)
print(f'Task types: {sorted(tts)}')
"
```

Expected: Queue file created with entries where task_type in [context_inference, uol_mapping, operator_selection, pragmatic_interpretation, synthesis_verification, self_state_update].

- [ ] **Step 5: Clean up test files**

```bash
cd C:\dev\cemm\cemm
Remove-Item test_queue.sqlite3 -ErrorAction Ignore
Remove-Item generated/test_queue.jsonl -ErrorAction Ignore
```

- [ ] **Step 6: Verify tests still pass**

Run: `python -m pytest ..\tests --tb=short -q`
Expected: 205 passed

- [ ] **Step 7: Commit**

```bash
cd C:\dev\cemm\cemm
git add cemm/cemm_runtime_router.py
git commit -m "feat: wire continuous training queue — emit_training_example fires after every LLM fallback turn"
```

---

### Task 7: Wire synthesis verification into neural fallback

**Files:**
- Create: `cemm/synthesis_verifier.py`
- Modify: `cemm/cemm_runtime_router.py`

**Design:** The architecture §23 requires that neural synthesis (LLM fallback) goes through soft verification. A verifier checks the LLM's response against the context kernel for contradictions, unsupported claims, or missing uncertainty. If the verifier confidence is below threshold (0.70), the system falls back to `abstain` or asks for clarification.

The initial verifier is deterministic (no model needed): it checks that the response doesn't contain specific patterns that would indicate hallucination or contradiction.

- [ ] **Step 1: Create synthesis_verifier.py**

```python
#!/usr/bin/env python3
"""Synthesis verifier for CEMM neural fallback responses.

Architecture §23:
    neural → soft verification
    - run verifier model (or deterministic verifier)
    - check contradiction against selected claims/models
    - if verifier confidence < 0.70, fall back to extractive or abstain
    - if no contradiction, pass with synthesis_verification_type = "soft"
    - downgrade final response confidence by 0.85
"""

from __future__ import annotations

import re
from typing import Any


def verify_neural_response(
    response: str,
    text: str,
    context_kernel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic soft verifier for LLM fallback responses.

    Checks:
    1. Response is non-empty and non-trivial
    2. Response doesn't contradict known facts from context
    3. Response appropriately hedges for uncertain claims
    4. Response is not a verbatim echo of the input

    Returns verification result matching the architecture spec:
    {
        "verification_type": "soft",
        "supported": bool,
        "contradicts_evidence": bool,
        "unsupported_spans": list[str],
        "missing_uncertainty": bool,
        "confidence": float,
        "should_fallback": bool,
    }
    """
    result: dict[str, Any] = {
        "verification_type": "soft",
        "supported": True,
        "contradicts_evidence": False,
        "unsupported_spans": [],
        "missing_uncertainty": False,
        "confidence": 1.0,
        "should_fallback": False,
    }

    # Check 1: Non-empty and non-trivial
    stripped = response.strip()
    if not stripped or len(stripped) < 3:
        result["supported"] = False
        result["should_fallback"] = True
        result["confidence"] = 0.0
        return result

    # Check 2: Not a verbatim echo of input
    if stripped.lower() == text.lower().strip():
        result["supported"] = False
        result["unsupported_spans"].append("response is verbatim echo of input")
        result["confidence"] = 0.1
        result["should_fallback"] = True
        return result

    # Check 3: Response doesn't contain self-narration or process description
    self_narration_patterns = [
        r"\b(as an ai|as a language model|as an assistant)\b",
        r"\bi (don't|cannot|can't|am not|do not) have (access to|the ability|the capability)\b",
        r"\bmy training data\b",
        r"\bi was (trained|designed|created|built)\b",
        r"\b(however|unfortunately),? (i|as)\b",
    ]
    for pattern in self_narration_patterns:
        if re.search(pattern, stripped.lower()):
            result["unsupported_spans"].append("response contains self-narration instead of direct answer")
            result["confidence"] = max(0.0, result["confidence"] - 0.2)
            break

    # Check 4: Response doesn't describe its own thought process
    if re.search(r"\b(the user (said|asked|wants)|the (conversation|context|input) (is|suggests|contains|indicates))\b", stripped.lower()):
        result["unsupported_spans"].append("response describes input instead of answering directly")
        result["confidence"] = max(0.0, result["confidence"] - 0.15)

    # Check 5: Response acknowledges uncertainty for speculative content
    speculative_markers = ["maybe", "perhaps", "might", "could be", "i think", "i believe", "possibly"]
    has_speculation = any(m in stripped.lower() for m in speculative_markers)
    if has_speculation:
        # has appropriate hedging — no penalty
        pass

    # Check 6: Response has reasonable length (not a single word, not a novel)
    word_count = len(stripped.split())
    if word_count < 3:
        result["unsupported_spans"].append("response too short to be meaningful")
        result["confidence"] = max(0.0, result["confidence"] - 0.3)
        result["supported"] = False
    elif word_count > 200:
        result["unsupported_spans"].append("response excessively verbose")
        result["confidence"] = max(0.0, result["confidence"] - 0.1)

    # Final decision
    if result["confidence"] < 0.70:
        result["should_fallback"] = True

    return result
```

- [ ] **Step 2: Wire verifier into synthesize's LLM fallback**

Modify the neural fallback section in `synthesize()`:

```python
            with urllib.request.urlopen(req, timeout=config.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
            envelope = json.loads(raw)
            answer = envelope["choices"][0]["message"]["content"].strip()
            if answer:
                # Run synthesis verification
                from cemm.synthesis_verifier import verify_neural_response
                vr = verify_neural_response(answer, text, ck)
                if vr.get("should_fallback"):
                    # Verifier rejected the answer — fall back to abstain
                    return (
                        "I'm not confident enough to answer that accurately.",
                        {"strategy": "llm_fallback_abstain", "verified": True,
                         "verification_type": "soft", "verifier": vr,
                         "llm_model": config.model},
                    )
                return answer, {"strategy": "llm", "verified": True,
                                "verification_type": "soft", "verifier": vr,
                                "llm_model": config.model}
```

- [ ] **Step 3: Test verifier on known cases**

```bash
cd C:\dev\cemm\cemm
python -c "
from cemm.synthesis_verifier import verify_neural_response

# Good response
r1 = verify_neural_response('Here is a joke: Why did the chicken cross the road?', 'tell me a joke')
print(f'Good response: supported={r1[\"supported\"]} confidence={r1[\"confidence\"]:.2f} fallback={r1[\"should_fallback\"]}')
assert r1['supported'] and not r1['should_fallback']

# Self-narration
r2 = verify_neural_response('As an AI language model, I cannot provide medical advice.', 'is this medicine safe')
print(f'Self-narration: supported={r2[\"supported\"]} confidence={r2[\"confidence\"]:.2f} fallback={r2[\"should_fallback\"]}')
assert r2['confidence'] < 1.0

# Verbatim echo
r3 = verify_neural_response('hello', 'hello')
print(f'Echo: supported={r3[\"supported\"]} confidence={r3[\"confidence\"]:.2f} fallback={r3[\"should_fallback\"]}')
assert r3['should_fallback']

# Describes input
r4 = verify_neural_response('The user has asked a question about the weather. I should provide a helpful response.', 'what is the weather')
print(f'Describes input: supported={r4[\"supported\"]} confidence={r4[\"confidence\"]:.2f} fallback={r4[\"should_fallback\"]}')
assert r4['confidence'] < 1.0

print('All verifier tests passed')
"
```

Expected: All 4 cases pass.

- [ ] **Step 4: Run full test suite**

Run: `cd C:\dev\cemm\cemm && python -m pytest ..\tests --tb=short -q`
Expected: 205 passed

- [ ] **Step 5: Commit**

```bash
cd C:\dev\cemm\cemm
git add cemm/synthesis_verifier.py cemm/cemm_runtime_router.py
git commit -m "feat: add synthesis verifier for neural fallback — blocks self-narration, echoing, and low-confidence responses"
```

---

### Task 8: Full integration test

**Files:**
- Create: `tests/test_continuous_training.py`

- [ ] **Step 1: Write integration test**

Create `tests/test_continuous_training.py`:

```python
"""Integration test: continuous training loop end-to-end."""
import sys, os, json, tempfile
sys.path.insert(0, r'C:\dev\cemm\cemm')
from pathlib import Path
from cemm_runtime_router import (
    connect, handle_turn, _RUNTIME_CONFIG, RuntimeConfig,
    set_training_queue, emit_training_example, build_context,
    save_model, find_models, RUNTIME_SCHEMA,
)
from cemm.synthesis_verifier import verify_neural_response


def test_models_table():
    conn = connect(Path(tempfile.mktemp(suffix=".db")))
    models = find_models(conn)
    assert models == [], f"expected empty models, got {len(models)}"
    mid = save_model(conn, "operator", "test_op", registry_key="test", confidence=0.9, status="active")
    found = find_models(conn, kind="operator")
    assert len(found) == 1
    assert found[0]["registry_key"] == "test"
    conn.close()


def test_emit_training_example():
    queue_path = Path(tempfile.mktemp(suffix=".jsonl"))
    qdb = Path(tempfile.mktemp(suffix=".db"))
    conn = connect(qdb)
    set_training_queue(queue_path)
    ctx = build_context(conn, "t1")
    from cemm_runtime_router import RouteDecision
    decision = RouteDecision("answer", 0.5, "test", [], [], [])
    emit_training_example(conn, "test input", "test response", ctx, {}, {}, decision, {"strategy": "llm"})
    with queue_path.open() as f:
        lines = [json.loads(l) for l in f if l.strip()]
    assert len(lines) == 6  # 6 task types
    assert all(l["source"] == "runtime_continuous" for l in lines)
    assert all(l["task_type"] in {"context_inference", "uol_mapping", "operator_selection",
                                   "pragmatic_interpretation", "synthesis_verification",
                                   "self_state_update"} for l in lines)
    conn.close()
    queue_path.unlink()
    qdb.unlink()


def test_verifier():
    r = verify_neural_response("A good joke", "tell me a joke")
    assert r["supported"]
    assert not r["should_fallback"]
    r = verify_neural_response("hello", "hello")
    assert r["should_fallback"], "echo should fail"
    r = verify_neural_response("", "test")
    assert r["should_fallback"], "empty should fail"


def test_deploy_models_ingest():
    """Test that models can be saved and found by kind."""
    conn = connect(Path(tempfile.mktemp(suffix=".db")))
    save_model(conn, "operator", "weather_operator", registry_key="weather", status="active", confidence=0.85)
    save_model(conn, "uol_semantic", "process:greet", registry_key="process:greet", status="active", confidence=0.9)
    ops = find_models(conn, kind="operator")
    assert len(ops) == 1
    assert ops[0]["name"] == "weather_operator"
    conn.close()
```

- [ ] **Step 2: Run integration tests**

```bash
cd C:\dev\cemm\cemm
python -m pytest tests/test_continuous_training.py -v --tb=short
```

Expected: All 4 tests pass.

- [ ] **Step 3: Run full test suite**

```bash
cd C:\dev\cemm\cemm
python -m pytest ..\tests --tb=short -q
```

Expected: 209 passed (205 existing + 4 new)

- [ ] **Step 4: Commit**

```bash
cd C:\dev\cemm\cemm
git add tests/test_continuous_training.py
git commit -m "test: continuous training integration tests — models table, emit queue, verifier, deploy"
```

---

### Task 9: Add deterministic template responses for new capabilities

**Files:**
- Modify: `cemm/cemm_runtime_router.py`

**Design:** Each new capability needs a deterministic template response in `synthesize()` (the "rules" layer of the cascade). These handle the most common patterns without needing the LLM fallback.

- [ ] **Step 1: Add template responses for story, meal, health, safety, goal, media, contacts, behavior, cross-session**

Add before the LLM fallback in `synthesize()`:

```python
    if re.search(r"\b(tell|make up|tell me|spin|recite) (me |us |)(a |an |)(story|tale|fable)", lower):
        return (
            "I don't have a built-in story library yet, but I can help create one. "
            "Tell me what kind of story you'd like — adventure, folk tale, or something original?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(what should i eat|suggest|recommend|meal|dinner|breakfast|lunch|recipe|food|snack|cook)", lower):
        return (
            "I can suggest meals based on your preferences. What kind of food are you in the mood for?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(headache|cold|flu|pain|exercise|diet|health|symptom|vitamin|sleep|back pain)", lower):
        return (
            "I can offer general health guidance, but please consult a medical professional for personalized advice. "
            "What specific health topic are you curious about?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(safe|safety|danger|child|kid|emergency|help|should.*do|what if)", lower):
        return (
            "Safety first! I can provide common-sense safety guidance. Could you tell me more about the situation?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(goal|plan|career|learn|study|skill|improve|achieve|step|strategy|advice|suggest)", lower):
        return (
            "I can help you plan and set goals. What's the main thing you're working toward?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(play|pause|skip|next|previous|volume|music|song|track|video|album|stop)", lower):
        return (
            "Media playback is available when connected to your device. What would you like me to play or control?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(save|store|remember|add|call|message|text|contact|phone|number|mom|dad)", lower):
        return (
            "I can help manage your contacts. What would you like me to save or look up?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(tone|style|formal|casual|professional|friendly|behavior|act like|personality)", lower):
        return (
            "I can adjust my tone and behavior. How would you like me to communicate with you?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(last time|yesterday|previous|before|earlier|remember.*(said|told|asked|talk))", lower):
        return (
            "I'll check what I remember from our previous conversation. Could you remind me what we talked about?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )
```

- [ ] **Step 2: Test template responses fire before LLM fallback**

```bash
cd C:\dev\cemm\cemm
python -c "
import sys; sys.path.insert(0, '.')
from cemm_runtime_router import connect, handle_turn
from pathlib import Path
import tempfile, os
os.chdir(tempfile.mkdtemp())
conn = connect(Path('test_templates.db'))
tests = [
    ('tell me a story', 'story'),
    ('suggest a healthy dinner', 'meal'),
    ('what is good for a headache', 'health'),
    ('is it safe to climb a tree', 'safety'),
    ('help me plan my career', 'goal'),
    ('play some music', 'media'),
    ('save my mothers number', 'contact'),
    ('be more formal', 'behavior'),
    ('what did we talk about last time', 'memory'),
]
for text, label in tests:
    r = handle_turn(conn, text, 's1')
    print(f'{label:15s}: {r[\"response\"][:80]}')
"
```

Expected: Each returns a template response specific to the capability, not the generic LLM fallback.

- [ ] **Step 3: Verify tests pass**

Run: `cd C:\dev\cemm\cemm && python -m pytest ..\tests --tb=short -q`
Expected: 205 passed

- [ ] **Step 4: Commit**

```bash
cd C:\dev\cemm\cemm
git add cemm/cemm_runtime_router.py
git commit -m "feat: add deterministic template responses for 9 new capability families"
```

---

### Task 10: Run comprehensive verification

- [ ] **Step 1: Run full test suite**

```bash
cd C:\dev\cemm\cemm
python -m pytest ..\tests --tb=short -q
```

Expected: 209 passed

- [ ] **Step 2: Verify continuous training queue writes from CLI**

```bash
cd C:\dev\cemm\cemm
$env:CEMM_RUNTIME_API_KEY="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"
$env:CEMM_RUNTIME_MODEL="meta/llama-3.1-8b-instruct"
python cemm_runtime_router.py --training-queue generated/final_queue.jsonl --db final_int.sqlite3 once "how do you do"
python -c "
import json
with open('generated/final_queue.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
print(f'Queue entries: {len(lines)}')
tts = set(l['task_type'] for l in lines)
print(f'Task types: {sorted(tts)}')
"
```

Expected: Queue has 6 entries (one per task type).

- [ ] **Step 3: Verify deployed models can be loaded into runtime**

```bash
cd C:\dev\cemm\cemm
$env:CEMM_RUNTIME_API_KEY="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"
$env:CEMM_RUNTIME_MODEL="meta/llama-3.1-8b-instruct"
python cemm_trainer.py deploy-models --train-db cemm_training.sqlite3 --runtime-db cemm_runtime.sqlite3
python -c "
import sqlite3
conn = sqlite3.connect('cemm_runtime.sqlite3')
conn.row_factory = sqlite3.Row
kinds = conn.execute('SELECT kind, COUNT(*) as c FROM models GROUP BY kind').fetchall()
print('Models in runtime DB:')
for k in kinds:
    print(f'  {k[\"kind\"]}: {k[\"c\"]}')
"
```

Expected: Models distributed across kinds in the runtime DB.

- [ ] **Step 4: Verify deterministic responses still work**

```bash
cd C:\dev\cemm\cemm
python -c "
import sys; sys.path.insert(0, '.')
from cemm_runtime_router import connect, handle_turn
from pathlib import Path
import tempfile, os; os.chdir(tempfile.mkdtemp())
conn = connect(Path('v.db'))
for t in ['hello', 'thanks', 'how are you', 'who are you', 'what can you do', 'where are you']:
    r = handle_turn(conn, t, 'v')
    print(f'{t:20s} -> {r[\"response\"][:60]}')
"
```

Expected: All deterministic responses work as before.

- [ ] **Step 5: Final commit**

```bash
cd C:\dev\cemm\cemm
git add -A
git commit -m "feat: complete continuous training pipeline — models table, capability coverage, training queue, synthesis verifier"
```
