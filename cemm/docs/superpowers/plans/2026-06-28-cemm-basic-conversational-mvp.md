# CEMM-Basic Conversational MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a basic conversational assistant (CEMM-Basic) that handles greeting, small talk, remember/recall user facts, answer from memory, ask clarification, handle correction, detect frustration/repetition, and abstain when unsupported.

**Architecture:** Hybrid system using deterministic routing + SQLite memory + template/extractive synthesis first, with optional LLM neural fallback for hard cases. Training pipeline uses LLM agents to label seed conversation data. The runtime router (`cemm_runtime_router.py`) is the conversation engine; the seed generator + trainer are the offline pipeline.

**Tech Stack:** Python 3.11+, stdlib only, SQLite via sqlite3, NVIDIA API for LLM labeling/fallback.

---

### Task 1: Copy new files into project

**Files:**
- Copy: `new/cemm_trainer.py` → `cemm/cemm_trainer.py` (replace)
- Copy: `new/cemm_runtime_router.py` → `cemm/cemm_runtime_router.py` (create)
- Copy: `new/cemm_seed_generator.py` → `cemm/cemm_seed_generator.py` (create)
- Copy: `new/cemm_seed_spec.json` → `cemm/cemm_seed_spec.json` (create)
- Copy: `new/architecture.md` → `cemm/architecture.md` (replace)
- Copy: `new/cemm_pipeline.md` → `cemm/cemm_pipeline.md` (create)
- Copy: `new/cemm_training_architecture.md` → `cemm/cemm_training_architecture.md` (replace)

- [ ] **Step 1: Copy all 7 files**

Run:
```powershell
Copy-Item "C:\dev\cemm\cemm\new\cemm_trainer.py" "C:\dev\cemm\cemm\cemm_trainer.py" -Force
Copy-Item "C:\dev\cemm\cemm\new\cemm_runtime_router.py" "C:\dev\cemm\cemm\cemm_runtime_router.py"
Copy-Item "C:\dev\cemm\cemm\new\cemm_seed_generator.py" "C:\dev\cemm\cemm\cemm_seed_generator.py"
Copy-Item "C:\dev\cemm\cemm\new\cemm_seed_spec.json" "C:\dev\cemm\cemm\cemm_seed_spec.json"
Copy-Item "C:\dev\cemm\cemm\new\architecture.md" "C:\dev\cemm\cemm\architecture.md" -Force
Copy-Item "C:\dev\cemm\cemm\new\cemm_pipeline.md" "C:\dev\cemm\cemm\cemm_pipeline.md"
Copy-Item "C:\dev\cemm\cemm\new\cemm_training_architecture.md" "C:\dev\cemm\cemm\cemm_training_architecture.md" -Force
```

Expected: 7 files copied without errors.

- [ ] **Step 2: Verify new files work**

Run:
```powershell
python -c "import sys; sys.path.insert(0, '.'); from cemm_runtime_router import now, stable_id, time_bucket, ContextKernel, RouteDecision; print('runtime_router imports OK')"
python -c "import sys; sys.path.insert(0, '.'); from cemm_seed_generator import ALLOWED_TASK_TYPES, Config; print(f'seed_generator imports OK, {len(ALLOWED_TASK_TYPES)} task types')"
python -c "import sys; sys.path.insert(0, '.'); from cemm_trainer import PROMPTS; print(f'trainer imports OK, {len(PROMPTS)} prompt types')"
```

Expected: All three print OK messages.

- [ ] **Step 3: Commit**

```powershell
rtk git add cemm/cemm_trainer.py cemm/cemm_runtime_router.py cemm/cemm_seed_generator.py cemm/cemm_seed_spec.json cemm/architecture.md cemm/cemm_pipeline.md cemm/cemm_training_architecture.md
rtk git commit -m "feat: integrate CEMM-Basic pipeline (trainer v2, runtime router, seed generator, updated arch)"
```

---

### Task 2: Run seed generator — dry-run validation

**Files:**
- Create: `generated/` directory

- [ ] **Step 1: Create output directory**

Run:
```powershell
New-Item -ItemType Directory -Path "C:\dev\cemm\cemm\generated" -Force
```

- [ ] **Step 2: Run dry generate with 2 per category**

Run:
```powershell
rtk python cemm_seed_generator.py generate --dry-run --per-category 2 --limit-categories 3 --out-dir generated
```

Expected: "wrote N scenarios to generated/cemm_generated_scenarios.jsonl" and "wrote N task records to generated/cemm_generated_training.jsonl"

- [ ] **Step 3: Validate dry-run output**

Run:
```powershell
rtk python cemm_seed_generator.py validate generated/cemm_generated_training.jsonl
```

Expected: JSON output with total count and by_task_type breakdown.

- [ ] **Step 4: Inspect output quality**

Run:
```powershell
python -c "import json; lines = open('generated/cemm_generated_scenarios.jsonl').readlines(); print(f'{len(lines)} scenarios'); s = json.loads(lines[0]); print(f'Categories: {s.get(\"category\")}'); print(f'Task examples: {len(s.get(\"task_examples\", []))}')"
```

Expected: Scenarios look correct with category and task_examples.

---

### Task 3: Generate real seed data via NVIDIA API

**Files:**
- Modify: `generated/cemm_generated_scenarios.jsonl` (append)
- Modify: `generated/cemm_generated_training.jsonl` (append)

- [ ] **Step 1: Run seed generator with NVIDIA API for all 14 categories**

Run:
```powershell
$env:NVIDIA_API_KEY="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"
$env:NVIDIA_MODEL="meta/llama-3.1-70b-instruct"
$env:NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
rtk python cemm_seed_generator.py generate --workers 4 --per-category 10 --out-dir generated
```

Expected: Processes each category, generates scenarios + task records. With 14 categories at 10 each, ~140 scenarios × several task records each = ~400+ task records.

- [ ] **Step 2: Validate generated data**

Run:
```powershell
rtk python cemm_seed_generator.py validate generated/cemm_generated_training.jsonl
```

Expected: Valid JSONL, all task types recognized.

- [ ] **Step 3: Inspect distribution**

Run:
```powershell
python -c "
import json
with open('generated/cemm_generated_training.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
cats = {}
for l in lines:
    cat = l.get('category', 'unknown')
    cats[cat] = cats.get(cat, 0) + 1
print(f'Total tasks: {len(lines)}')
for k, v in sorted(cats.items()):
    print(f'  {k}: {v}')
"
```

Expected: Good spread across all categories that were requested.

- [ ] **Step 4: Retry any categories that hit rate limits**

Run the generation again with `--categories` flag for any categories that failed:
```powershell
$env:NVIDIA_API_KEY="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"
rtk python cemm_seed_generator.py generate --workers 2 --per-category 10 --categories "memory_write_preferences,memory_recall,corrections_and_supersession" --out-dir generated
```

Expected: New data appended for the specified categories.

---

### Task 4: Ingest and label seed data via trainer

**Files:**
- Create: `cemm_training.sqlite3` (or reuse existing)
- Modify: `cemm_training.sqlite3` (populate with labels)

- [ ] **Step 1: Ingest generated training data into new trainer DB**

Run:
```powershell
$env:CEMM_LLM_API_KEY="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"
$env:CEMM_LLM_BASE_URL="https://integrate.api.nvidia.com/v1/chat/completions"
$env:CEMM_LLM_MODEL="meta/llama-3.1-8b-instruct"
rtk python cemm_trainer.py ingest generated/cemm_generated_training.jsonl
```

Expected: "ingested N examples into cemm_training.sqlite3"

- [ ] **Step 2: Also ingest the existing device_assistant_examples.jsonl**

Run:
```powershell
rtk python cemm_trainer.py ingest "..\docs\superpowers\seeds\device_assistant_examples.jsonl"
```

Expected: "ingested N examples" (some may be duplicates, which INSERT OR IGNORE handles).

- [ ] **Step 3: Run trainer agents to label all jobs**

Run (with rate-limit-safe 2 workers, repeated until done):
```powershell
$env:CEMM_LLM_API_KEY="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"
rtk python cemm_trainer.py run --workers 2 --once
```

Run repeatedly in a loop:
```powershell
$env:CEMM_LLM_API_KEY="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"; $count = 0; while ($count -lt 30) { $result = python cemm_trainer.py run --workers 2 --once 2>&1; $result | Write-Host; if ($result -match "no queued jobs") { Write-Host "All done!"; break }; Start-Sleep -Seconds 1; $count++ }
```

Expected: All jobs complete successfully.

- [ ] **Step 4: Verify labeling stats**

Run:
```powershell
python -c "
import sqlite3, json
conn = sqlite3.connect('cemm_training.sqlite3')
r = conn.execute('SELECT status, COUNT(*) FROM training_jobs GROUP BY status').fetchall()
print('Jobs:', dict(r))
r2 = conn.execute('SELECT COUNT(*) FROM agent_outputs').fetchone()
print('Agent outputs:', r2[0])
r3 = conn.execute('SELECT COUNT(*) FROM agent_runs WHERE status=\"succeeded\"').fetchone()
print('Successful runs:', r3[0])
tt = conn.execute('SELECT j.task_type, COUNT(*) FROM agent_outputs o JOIN training_jobs j ON j.id=o.job_id GROUP BY j.task_type ORDER BY COUNT(*) DESC').fetchall()
print('By task type:', tt)
"
```

Expected: All jobs done, good distribution across task types.

---

### Task 5: Run basic runtime router and test conversation

**Files:**
- Create: `cemm_runtime.sqlite3` (runtime memory DB)

- [ ] **Step 1: Test single-turn greeting**

Run:
```powershell
rtk python cemm_runtime_router.py once "Good morning"
```

Expected: "Good morning."

- [ ] **Step 2: Test remember user fact**

Run:
```powershell
rtk python cemm_runtime_router.py once "My favorite database is Postgres."
```

Expected: "Got it."

- [ ] **Step 3: Test recall stored fact**

Run:
```powershell
rtk python cemm_runtime_router.py once "What is my favorite database?"
```

Expected: "Your favorite database is Postgres."

- [ ] **Step 4: Test weather location clarification**

Run:
```powershell
rtk python cemm_runtime_router.py once "What's the weather?"
```

Expected: "Which location should I use?"

- [ ] **Step 5: Test frustration handling**

Run:
```powershell
rtk python cemm_runtime_router.py once "You are dumb"
```

Expected: "I hear the frustration. Let me focus on fixing the part that failed."

- [ ] **Step 6: Test abstention for unsupported question**

Run:
```powershell
rtk python cemm_runtime_router.py once "What is the meaning of life?"
```

Expected: "I don't have enough grounded context to answer that yet."

- [ ] **Step 7: Test interactive chat session**

Run with stdin:
```powershell
"Good morning`nMy name is John`nWhat is my name?`nYou are stupid`nWhat is 42?`nI prefer Python over Java" | rtk python cemm_runtime_router.py chat
```

Expected: Each line gets an appropriate response.

- [ ] **Step 8: Verify trace was written**

Run:
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('cemm_runtime.sqlite3')
print('Signals:', conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0])
print('Claims:', conn.execute('SELECT COUNT(*) FROM claims').fetchone()[0])
print('Actions:', conn.execute('SELECT COUNT(*) FROM actions').fetchone()[0])
print('Traces:', conn.execute('SELECT COUNT(*) FROM traces').fetchone()[0])
# Show the stored facts
claims = conn.execute('SELECT subject, predicate, object_value, confidence FROM claims WHERE status=\"active\"').fetchall()
print('Stored facts:', claims)
"
```

Expected: Correct counts and stored facts visible.

---

### Task 6: Wire runtime router to work as CEMM submodule (via __main__.py)

**Files:**
- Modify: `cemm/__main__.py` (add `--chat` and `--once` subcommands)
- Modify: `pyproject.toml` if needed (entry points)

- [ ] **Step 1: Add chat subcommand to __main__.py**

Read the current `__main__.py`:
```powershell
rtk read cemm/__main__.py
```

Add `--chat` and `--once` subcommands that delegate to `cemm_runtime_router.main()`.

- [ ] **Step 2: Test via module call**

Run:
```powershell
rtk python -m cemm once "Good morning"
```

Expected: "Good morning."

- [ ] **Step 3: Test interactive via module**

Run:
```powershell
"hello`nmy favorite color is blue`nwhat is my favorite color?" | rtk python -m cemm chat
```

Expected: Works the same as direct router call.

- [ ] **Step 4: Run existing tests to verify nothing broke**

```powershell
rtk python -m pytest tests/ -v --tb=short
```

Expected: 205+ tests pass.

- [ ] **Step 5: Commit**

```powershell
rtk git add cemm/__main__.py
rtk git commit -m "feat: wire runtime router into __main__.py as --chat/--once"
```

---

### Task 7: Add correction handling to runtime router

The router handles "remember" and "recall", but not "correction" (e.g., "Actually, my favorite database is SQLite" should supersede previous claim).

**Files:**
- Modify: `cemm/cemm_runtime_router.py`

- [ ] **Step 1: Add correction detection to route()**

Add before the recall check in `route()`:
```python
# Handle corrections: "actually", "no,", "correction" signal supersession
if any(word in lower for word in ["actually", "correction", "wait", "no,"]):
    claim = extract_claim(text)
    if claim:
        return RouteDecision("remember", claim["confidence"], "correction/supersession of previous claim", [], [], [])
```

- [ ] **Step 2: Test correction chain**

Run:
```powershell
rtk python cemm_runtime_router.py once "My favorite database is Postgres."
rtk python cemm_runtime_router.py once "Actually, my favorite database is SQLite"
rtk python cemm_runtime_router.py once "What is my favorite database?"
```

Expected: Third call returns "SQLite", not "Postgres".

- [ ] **Step 3: Verify supersedence in DB**

```powershell
python -c "
import sqlite3
conn = sqlite3.connect('cemm_runtime.sqlite3')
claims = conn.execute('SELECT subject, predicate, object_value, status FROM claims WHERE predicate=\"favorite_database\" ORDER BY updated_at').fetchall()
print('Claim history:', claims)
"
```

Expected: First claim is "superseded", second is "active".

---

### Task 8: Add small talk fallback to runtime router

- [ ] **Step 1: Add small talk responses**

In `synthesize()`, add before the generic "I'm here" fallback:
```python
# Small talk fallback
small_talk = {
    "how are you": "I'm functioning well, thanks for asking.",
    "what can you do": "I can remember facts about you and answer based on what I know.",
    "who are you": "I'm CEMM-Basic, a conversational memory system.",
    "thanks": "You're welcome.",
    "thank you": "You're welcome.",
    "bye": "Goodbye.",
    "goodbye": "Goodbye.",
}
for phrase, response in small_talk.items():
    if phrase in lower:
        return response, {"strategy": "template", "verified": True}
```

- [ ] **Step 2: Test small talk**

```powershell
rtk python cemm_runtime_router.py once "How are you?"
rtk python cemm_runtime_router.py once "What can you do?"
rtk python cemm_runtime_router.py once "Thank you"
rtk python cemm_runtime_router.py once "Bye"
```

Expected: Each returns the appropriate template response.

---

### Task 9: Full conversation test and commit

**Files:**
- Create: `generated/full_session_test.jsonl`

- [ ] **Step 1: Run a 20-turn conversation session**

```powershell
python -c "
import subprocess, sys
turns = [
    'Good morning',
    'My name is Alex',
    'What is my name?',
    'My favorite programming language is Python',
    'Actually, my favorite language is Rust',
    'What is my favorite language?',
    'What is the weather like?',
    'London',
    'You are dumb',
    'How are you?',
    'What can you do?',
    'Tell me something I have not told you',
    'I prefer Vim over VS Code',
    'What is my preference?',
    'Thanks',
    'Goodbye',
]
runtime_db = 'cemm_runtime.sqlite3'
import os
if os.path.exists(runtime_db):
    os.remove(runtime_db)
for t in turns:
    result = subprocess.run([sys.executable, 'cemm_runtime_router.py', 'once', t], capture_output=True, text=True)
    print(f'  {t:50s} -> {result.stdout.strip()}')
"
```

Expected: All 16 turns handled appropriately, no crashes.

- [ ] **Step 2: Verify memory and traces**

```powershell
python -c "
import sqlite3
conn = sqlite3.connect('cemm_runtime.sqlite3')
signals = conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
claims = conn.execute('SELECT COUNT(*) FROM claims').fetchone()[0]
actions = conn.execute('SELECT COUNT(*) FROM actions').fetchone()[0]
traces = conn.execute('SELECT COUNT(*) FROM traces').fetchone()[0]
print(f'Signals={signals} Claims={claims} Actions={actions} Traces={traces}')
print('Active facts:')
for r in conn.execute('SELECT subject, predicate, object_value FROM claims WHERE status=\"active\"').fetchall():
    print(f'  {r[\"subject\"]} {r[\"predicate\"]} = {r[\"object_value\"]}')
"
```

Expected: Memory correctly reflects the final state (name=Alex, language=Rust, preference=Vim).

- [ ] **Step 3: Run existing test suite**

```powershell
rtk python -m pytest tests/ -v --tb=short
```

Expected: All tests pass.

- [ ] **Step 4: Commit everything**

```powershell
rtk git add cemm/cemm_runtime_router.py cemm/__main__.py generated/ cemm_training.sqlite3 cemm_runtime.sqlite3 -A
rtk git commit -m "feat: CEMM-Basic conversational MVP with router, correction handling, small talk, and full pipeline"
```

---

### Task 10: Verify 300-turn readiness

- [ ] **Step 1: Run a 50-turn stress test**

```powershell
python -c "
import subprocess, sys, os, random
runtime_db = 'cemm_runtime.sqlite3'
if os.path.exists(runtime_db):
    os.remove(runtime_db)

templates = [
    'Good morning', 'Hello', 'Hi there',
    'My favorite color is blue', 'My name is Sam',
    'I prefer cats over dogs', 'My favorite food is pizza',
    'Actually my favorite color is red', 'I like hiking',
    'My favorite database is Postgres',
    'What is my name?', 'What is my favorite color?',
    'What is my preference?', 'What is my favorite food?',
    'What is my favorite database?',
    'How are you?', 'What can you do?',
    'You are dumb', 'Thanks', 'Bye',
    'What is the weather?', 'What is the meaning of life?',
]
for i in range(50):
    text = random.choice(templates)
    result = subprocess.run([sys.executable, 'cemm_runtime_router.py', 'once', text], capture_output=True, text=True)
    if i % 10 == 0:
        print(f'turn {i}: {text:40s} -> {result.stdout.strip()[:60]}')

conn = sqlite3.connect(runtime_db)
print(f'\nAfter 50 turns: signals={conn.execute(\"SELECT COUNT(*) FROM signals\").fetchone()[0]} claims={conn.execute(\"SELECT COUNT(*) FROM claims\").fetchone()[0]}')
print('Active facts:')
for r in conn.execute('SELECT subject, predicate, object_value FROM claims WHERE status=\"active\"').fetchall():
    print(f'  {r[\"subject\"]} {r[\"predicate\"]} = {r[\"object_value\"]}')
import sqlite3
"
```

Expected: All 50 turns handled without errors. Memory maintains active facts correctly.

- [ ] **Step 2: Check performance**

```powershell
Measure-Command { python cemm_runtime_router.py once "Good morning" }
```

Expected: Sub-100ms response time for template-based responses.
