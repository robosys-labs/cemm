#!/usr/bin/env python3
"""
Continuous CEMM training runner.

This is a dependency-free starter implementation:
- SQLite-backed queue
- JSONL ingest
- parallel workers
- OpenAI-compatible HTTP adapter
- deterministic response cache
- strict JSON parsing
- dry-run mode

API keys are read from environment variables only.

Example:
  export CEMM_LLM_API_KEY="..."
  export CEMM_LLM_BASE_URL="https://api.example.com/v1/chat/completions"
  export CEMM_LLM_MODEL="small-model"
  python3 cemm_trainer.py ingest examples.jsonl
  python3 cemm_trainer.py run --workers 8
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import os
import queue
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS training_examples (
  id TEXT PRIMARY KEY,
  task_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  permission_scope TEXT NOT NULL DEFAULT 'public',
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS training_jobs (
  id TEXT PRIMARY KEY,
  example_id TEXT NOT NULL,
  task_type TEXT NOT NULL,
  status TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 100,
  attempts INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  model TEXT NOT NULL,
  status TEXT NOT NULL,
  cost_ms INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_outputs (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  output_json TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS training_cache (
  cache_key TEXT PRIMARY KEY,
  output_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""


PROMPTS: dict[str, dict[str, str]] = {
    "claim_extraction": {
        "agent": "extractor",
        "system": (
            "You extract CEMM claims from an event. Return strict JSON only. "
            "Do not invent evidence. Include confidence from 0 to 1."
        ),
        "user": (
            "Extract canonical candidate claims from this payload.\n"
            "Return JSON: {{\"claims\":[{{\"subject\":\"\",\"predicate\":\"\","
            "\"object\":\"\",\"qualifiers\":{{}},\"confidence\":0.0}}],"
            "\"uncertainty_reason\":\"\"}}\n\nPayload:\n{payload}"
        ),
    },
    "predicate_mapping": {
        "agent": "canonicalizer",
        "system": (
            "You map predicates to registry keys. Return strict JSON only. "
            "Prefer existing canonical predicates when possible."
        ),
        "user": (
            "Map predicates in this payload to canonical registry keys.\n"
            "Return JSON: {{\"mappings\":[{{\"raw\":\"\",\"registry_key\":\"\","
            "\"confidence\":0.0}}],\"new_predicate_candidates\":[]}}\n\nPayload:\n{payload}"
        ),
    },
    "pragmatic_interpretation": {
        "agent": "pragmaticist",
        "system": (
            "You interpret session pragmatics for CEMM. Return strict JSON only. "
            "Detect meaning-level repetition across paraphrases, affect, target, and likely cause. "
            "Do not convert insults or affect into factual claims."
        ),
        "user": (
            "Interpret pragmatic meaning for this event or sequence.\n"
            "Return JSON: {{\"speech_act\":\"unknown\",\"target\":\"\","
            "\"semantic_cluster_key\":\"\",\"stance\":\"unknown\","
            "\"affect\":{{\"valence\":0.0,\"arousal\":0.0,\"frustration\":0.0,"
            "\"hostility\":0.0,\"playfulness\":0.0}},"
            "\"repetition_group_id\":\"\",\"repetition_count\":0,"
            "\"cause_hypotheses\":[],\"decay_half_life_ms\":900000,"
            "\"confidence\":0.0,\"uncertainty_reason\":\"\"}}\n\nPayload:\n{payload}"
        ),
    },
    "synthesis_verification": {
        "agent": "synthesis_judge",
        "system": (
            "You verify whether an answer is supported by selected CEMM claims/models. "
            "Return strict JSON only."
        ),
        "user": (
            "Verify the answer against selected evidence.\n"
            "Return JSON: {{\"supported\":true,\"unsupported_spans\":[],"
            "\"missing_uncertainty\":false,\"confidence\":0.0,"
            "\"uncertainty_reason\":\"\"}}\n\nPayload:\n{payload}"
        ),
    },
    "causal_rule_extraction": {
        "agent": "causalist",
        "system": (
            "You extract lightweight causal rules from events. Return strict JSON only. "
            "Predictions are not facts."
        ),
        "user": (
            "Extract candidate causal rules.\n"
            "Return JSON: {{\"rules\":[{{\"preconditions\":[],\"event\":\"\","
            "\"effects\":[],\"confidence\":0.0}}],\"uncertainty_reason\":\"\"}}\n\nPayload:\n{payload}"
        ),
    },
    "structural_induction": {
        "agent": "inductor",
        "system": (
            "You propose candidate CEMM Model records from repeated patterns. "
            "Return strict JSON only. Do not promote candidates."
        ),
        "user": (
            "Propose candidate models from this evidence.\n"
            "Return JSON: {{\"candidate_models\":[{{\"kind\":\"predicate\","
            "\"name\":\"\",\"description\":\"\",\"evidence_refs\":[],"
            "\"confidence\":0.0,\"risk\":0.0}}],\"uncertainty_reason\":\"\"}}\n\nPayload:\n{payload}"
        ),
    },
}


@dataclasses.dataclass(frozen=True)
class Config:
    db_path: Path
    base_url: str
    api_key: str
    model: str
    dry_run: bool
    timeout_s: int
    max_retries: int


def now() -> int:
    return int(time.time())


def stable_id(prefix: str, data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:24]}"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(DB_SCHEMA)
    conn.commit()
    return conn


def ingest_jsonl(db_path: Path, jsonl_path: Path) -> None:
    conn = connect(db_path)
    created = 0
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            task_type = payload.get("task_type")
            if task_type not in PROMPTS:
                raise ValueError(f"line {line_no}: unknown task_type {task_type!r}")
            permission_scope = payload.get("permission_scope", "public")
            example_id = stable_id("ex", payload)
            job = {"example_id": example_id, "task_type": task_type}
            job_id = stable_id("job", job)
            ts = now()
            conn.execute(
                """
                INSERT OR IGNORE INTO training_examples
                (id, task_type, payload_json, permission_scope, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (example_id, task_type, json.dumps(payload, sort_keys=True), permission_scope, ts),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO training_jobs
                (id, example_id, task_type, status, priority, attempts, created_at, updated_at)
                VALUES (?, ?, ?, 'queued', ?, 0, ?, ?)
                """,
                (job_id, example_id, task_type, int(payload.get("priority", 100)), ts, ts),
            )
            created += 1
    conn.commit()
    print(f"ingested {created} examples into {db_path}")


def fetch_jobs(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT j.id AS job_id, j.task_type, e.payload_json
        FROM training_jobs j
        JOIN training_examples e ON e.id = j.example_id
        WHERE j.status = 'queued'
        ORDER BY j.priority ASC, j.created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE training_jobs SET status = 'running', attempts = attempts + 1, updated_at = ? WHERE id = ?",
            (now(), row["job_id"]),
        )
    conn.commit()
    return rows


def cache_key(task_type: str, prompt_version: str, model: str, payload_json: str) -> str:
    return stable_id(
        "cache",
        {
            "task_type": task_type,
            "prompt_version": prompt_version,
            "model": model,
            "payload_json": payload_json,
        },
    )


def render_prompt(task_type: str, payload_json: str) -> tuple[str, str, str]:
    prompt = PROMPTS[task_type]
    payload_pretty = json.dumps(json.loads(payload_json), indent=2, sort_keys=True)
    return prompt["agent"], prompt["system"], prompt["user"].format(payload=payload_pretty)


def call_llm(config: Config, system: str, user: str) -> dict[str, Any]:
    if config.dry_run:
        return {
            "confidence": 0.5,
            "dry_run": True,
            "uncertainty_reason": "dry-run mode; no provider call made",
        }

    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        config.base_url,
        data=data,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=config.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
            envelope = json.loads(raw)
            content = envelope["choices"][0]["message"]["content"]
            return json.loads(content)
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"provider call failed: {last_error}")


def run_one(config: Config, job: sqlite3.Row) -> dict[str, Any]:
    task_type = job["task_type"]
    payload_json = job["payload_json"]
    prompt_version = "v1"
    key = cache_key(task_type, prompt_version, config.model, payload_json)

    conn = connect(config.db_path)
    cached = conn.execute("SELECT output_json FROM training_cache WHERE cache_key = ?", (key,)).fetchone()
    agent, system, user = render_prompt(task_type, payload_json)
    ts = now()
    run_id = stable_id("run", {"job_id": job["job_id"], "agent": agent, "ts": ts})

    started = time.time()
    try:
        if cached:
            output = json.loads(cached["output_json"])
        else:
            output = call_llm(config, system, user)
            conn.execute(
                "INSERT OR REPLACE INTO training_cache (cache_key, output_json, created_at) VALUES (?, ?, ?)",
                (key, json.dumps(output, sort_keys=True), ts),
            )

        confidence = float(output.get("confidence", 0.0) or 0.0)
        cost_ms = int((time.time() - started) * 1000)
        output_id = stable_id("out", {"run_id": run_id, "output": output})
        conn.execute(
            """
            INSERT INTO agent_runs
            (id, job_id, agent, model, status, cost_ms, error, created_at)
            VALUES (?, ?, ?, ?, 'succeeded', ?, NULL, ?)
            """,
            (run_id, job["job_id"], agent, config.model, cost_ms, ts),
        )
        conn.execute(
            """
            INSERT INTO agent_outputs
            (id, run_id, job_id, output_json, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (output_id, run_id, job["job_id"], json.dumps(output, sort_keys=True), confidence, ts),
        )
        conn.execute(
            "UPDATE training_jobs SET status = 'done', updated_at = ? WHERE id = ?",
            (now(), job["job_id"]),
        )
        conn.commit()
        return {"job_id": job["job_id"], "status": "done", "confidence": confidence}
    except Exception as exc:
        cost_ms = int((time.time() - started) * 1000)
        conn.execute(
            """
            INSERT INTO agent_runs
            (id, job_id, agent, model, status, cost_ms, error, created_at)
            VALUES (?, ?, ?, ?, 'failed', ?, ?, ?)
            """,
            (run_id, job["job_id"], agent, config.model, cost_ms, str(exc), ts),
        )
        conn.execute(
            "UPDATE training_jobs SET status = 'queued', updated_at = ? WHERE id = ?",
            (now(), job["job_id"]),
        )
        conn.commit()
        return {"job_id": job["job_id"], "status": "failed", "error": str(exc)}


def run_workers(config: Config, workers: int, poll_s: float, once: bool) -> None:
    print(f"running trainer db={config.db_path} workers={workers} dry_run={config.dry_run}")
    while True:
        conn = connect(config.db_path)
        jobs = fetch_jobs(conn, workers * 2)
        conn.close()
        if not jobs:
            if once:
                print("no queued jobs")
                return
            time.sleep(poll_s)
            continue

        results: queue.Queue[dict[str, Any]] = queue.Queue()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_one, config, job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                results.put(future.result())

        while not results.empty():
            result = results.get()
            print(json.dumps(result, sort_keys=True))

        if once:
            return


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CEMM continuous training runner")
    parser.add_argument("--db", default="cemm_training.sqlite3", help="SQLite database path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="ingest JSONL examples")
    ingest.add_argument("jsonl", help="path to JSONL file")

    run = sub.add_parser("run", help="run training workers")
    run.add_argument("--workers", type=int, default=int(os.getenv("CEMM_WORKERS", "4")))
    run.add_argument("--poll-s", type=float, default=2.0)
    run.add_argument("--once", action="store_true")
    run.add_argument("--dry-run", action="store_true", default=os.getenv("CEMM_DRY_RUN") == "1")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    db_path = Path(args.db)

    if args.cmd == "ingest":
        ingest_jsonl(db_path, Path(args.jsonl))
        return 0

    config = Config(
        db_path=db_path,
        base_url=os.getenv("CEMM_LLM_BASE_URL", "https://api.openai.com/v1/chat/completions"),
        api_key=os.getenv("CEMM_LLM_API_KEY", ""),
        model=os.getenv("CEMM_LLM_MODEL", "gpt-4o-mini"),
        dry_run=bool(args.dry_run),
        timeout_s=int(os.getenv("CEMM_TIMEOUT_S", "60")),
        max_retries=int(os.getenv("CEMM_MAX_RETRIES", "3")),
    )
    if not config.dry_run and not config.api_key:
        print("CEMM_LLM_API_KEY is required unless --dry-run is set", file=sys.stderr)
        return 2

    run_workers(config, workers=args.workers, poll_s=args.poll_s, once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
