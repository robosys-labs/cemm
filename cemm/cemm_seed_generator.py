#!/usr/bin/env python3
"""
Generate CEMM seed training data end-to-end with NVIDIA NIM/OpenAI-compatible APIs.

The script creates two useful outputs:
- cemm_generated_training.jsonl: flat task records for cemm_trainer.py ingest
- cemm_generated_scenarios.jsonl: scenario-level records for inspection/evals

No API keys are stored. Set:
  export NVIDIA_API_KEY="..."
  export NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
  export NVIDIA_MODEL="meta/llama-3.1-70b-instruct"

Smoke test without an API key:
  python3 cemm_seed_generator.py generate --dry-run --per-category 2

Real generation:
  python3 cemm_seed_generator.py generate --workers 4 --per-category 20

Then:
  python3 cemm_trainer.py ingest generated/cemm_generated_training.jsonl
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import dataclasses
import hashlib
import json
import os
import random
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ALLOWED_TASK_TYPES = {
    "uol_mapping",
    "claim_extraction",
    "predicate_mapping",
    "context_inference",
    "pragmatic_interpretation",
    "synthesis_verification",
    "causal_rule_extraction",
    "temporal_relation_derivation",
    "structural_induction",
    "entity_resolution",
    "claim_canonicalization",
    "frame_classification",
    "contradiction_detection",
    "operator_selection",
    "verifier_calibration",
    "self_state_update",
    "ranking_judgment",
}


CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_cache (
  cache_key TEXT PRIMARY KEY,
  output_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""


@dataclasses.dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    model: str
    dry_run: bool
    timeout_s: int
    max_retries: int
    cache_db: Path
    temperature: float


def now() -> int:
    return int(time.time())


def stable_id(prefix: str, data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:24]}"


def connect_cache(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(CACHE_SCHEMA)
    conn.commit()
    return conn


def load_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        spec = json.load(handle)
    if "categories" not in spec or not isinstance(spec["categories"], list):
        raise ValueError("seed spec must contain categories[]")
    return spec


def response_schema_hint() -> str:
    return """
Return ONLY valid JSON. Do NOT include any explanatory text, markdown formatting, or code fences. Your entire response must be parseable as JSON:
{
  "scenarios": [
    {
      "scenario_id": "stable_short_id",
      "category": "category_name",
      "conversation": [
        {"speaker": "user", "content": "text"},
        {"speaker": "assistant", "content": "optional expected response"}
      ],
      "context": {
        "turn_index": 1,
        "time_bucket": "morning",
        "user_locale": null,
        "assistant_locale": {"timezone": "Africa/Lagos"},
        "active_goal": null
      },
      "expected": {
        "uol_atoms": [],
        "claims": [],
        "operator": "answer|ask|remember|update_claim|retrieve|reflect|abstain",
        "synthesis_strategy": "template|extractive|neural|abstain",
        "notes": ""
      },
      "task_examples": [
        {
          "task_type": "context_inference",
          "permission_scope": "session_private",
          "priority": 50,
          "signal": {"kind": "input", "content": "text", "source_type": "user"},
          "context": {}
        }
      ]
    }
  ]
}

Rules:
- task_type must be one of the allowed CEMM task types.
- Include diverse contexts and negative/ambiguous cases.
- Do not include API keys, personal data, secrets, or real private identifiers.
- For UOL, prefer process/state keys, not surface grammar labels.
- For current-world facts, mark stale/fresh-retrieval need rather than inventing facts.
"""


def build_prompt(spec: dict[str, Any], category: dict[str, Any], count: int) -> tuple[str, str]:
    registry = json.dumps(spec.get("registry_seeds", {}), indent=2, sort_keys=True)
    allowed = ", ".join(sorted(ALLOWED_TASK_TYPES))
    system = (
        "You generate high-quality seed training data for CEMM, the Contextual Event Memory Model. "
        "CEMM is not trained on words alone; it learns from scenario + context + expected structure. "
        "You must output strict JSON only."
    )
    user = f"""
Generate {count} diverse seed scenarios for this category.

Category:
{json.dumps(category, indent=2, sort_keys=True)}

Registry seeds:
{registry}

Allowed task types:
{allowed}

{response_schema_hint()}
"""
    return system, user


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object found in model output")
    return json.loads(text[start : end + 1])


def call_nvidia(config: Config, system: str, user: str, cache_key: str) -> dict[str, Any]:
    conn = connect_cache(config.cache_db)
    cached = conn.execute("SELECT output_json FROM llm_cache WHERE cache_key = ?", (cache_key,)).fetchone()
    if cached:
        return json.loads(cached["output_json"])

    if config.dry_run:
        raise RuntimeError("dry_run should use generate_dry_run_category")

    endpoint = config.base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": config.temperature,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
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
            parsed = extract_json_object(content)
            conn.execute(
                "INSERT OR REPLACE INTO llm_cache (cache_key, output_json, created_at) VALUES (?, ?, ?)",
                (cache_key, json.dumps(parsed, sort_keys=True), now()),
            )
            conn.commit()
            return parsed
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"NVIDIA API call failed: {last_error}")


def dry_task_record(category: str, task_type: str, idx: int) -> dict[str, Any]:
    base = {
        "task_type": task_type,
        "permission_scope": "session_private",
        "priority": 50,
        "category": category,
    }
    if task_type == "uol_mapping":
        base.update(
            {
                "sequence": [
                    {"speaker": "user", "content": "you are dumb"},
                    {"speaker": "user", "content": "you are daft"},
                ],
                "context": {"target": "assistant_self"},
            }
        )
    elif task_type == "claim_extraction":
        base["signal"] = {"kind": "input", "content": f"My seed preference {idx} is Postgres.", "source_type": "user"}
    elif task_type == "predicate_mapping":
        base["predicates"] = ["likes_database", "favorite_database"]
    elif task_type == "context_inference":
        base["signal"] = {"kind": "input", "content": "Good morning", "source_type": "user"}
        base["context"] = {"turn_index": 1, "time_bucket": "morning"}
    elif task_type == "pragmatic_interpretation":
        base["sequence"] = [{"speaker": "user", "content": "you are dumb"}, {"speaker": "user", "content": "you are a fool"}]
    elif task_type == "synthesis_verification":
        base["answer"] = "Your favorite database is Postgres."
        base["selected_claims"] = [{"subject": "user", "predicate": "favorite_database", "object": "Postgres"}]
    elif task_type == "causal_rule_extraction":
        base["sequence"] = [{"event": "assistant_failed_answer"}, {"event": "user_repeats_negative_evaluation"}]
    elif task_type == "temporal_relation_derivation":
        base["claims"] = [
            {"id": f"claim_{idx}_a", "valid_from": 1000, "valid_until": 4000},
            {"id": f"claim_{idx}_b", "valid_from": 2500, "valid_until": 4500},
        ]
    elif task_type == "structural_induction":
        base["patterns"] = [{"type": "sequential", "a": "ActionA", "b": "SignalB", "support": 7, "failures": 2}]
    else:
        base["signal"] = {"kind": "input", "content": f"Seed example {idx} for {task_type}", "source_type": "user"}
    return base


def generate_dry_run_category(category: dict[str, Any], count: int) -> dict[str, Any]:
    scenarios = []
    task_types = category.get("task_types", ["context_inference"])
    for i in range(count):
        task_examples = [dry_task_record(category["name"], task_type, i) for task_type in task_types]
        scenarios.append(
            {
                "scenario_id": stable_id("scenario", {"category": category["name"], "i": i}),
                "category": category["name"],
                "conversation": [{"speaker": "user", "content": f"Dry-run seed {i} for {category['name']}"}],
                "context": {"turn_index": 1, "time_bucket": "morning", "active_goal": None},
                "expected": {
                    "uol_atoms": [],
                    "claims": [],
                    "operator": "answer",
                    "synthesis_strategy": "template",
                    "notes": "dry-run generated scaffold",
                },
                "task_examples": task_examples,
            }
        )
    return {"scenarios": scenarios}


def normalize_task_record(record: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    task_type = record.get("task_type")
    if task_type not in ALLOWED_TASK_TYPES:
        raise ValueError(f"invalid task_type {task_type!r}")
    normalized = dict(record)
    normalized.setdefault("permission_scope", "session_private")
    normalized.setdefault("priority", 100)
    normalized.setdefault("scenario_id", scenario.get("scenario_id"))
    normalized.setdefault("category", scenario.get("category"))
    return normalized


def validate_and_flatten(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("model output missing scenarios[]")
    flat_tasks: list[dict[str, Any]] = []
    valid_scenarios: list[dict[str, Any]] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        scenario.setdefault("scenario_id", stable_id("scenario", scenario))
        scenario.setdefault("task_examples", [])
        tasks = []
        for task in scenario["task_examples"]:
            if not isinstance(task, dict):
                continue
            tasks.append(normalize_task_record(task, scenario))
        scenario["task_examples"] = tasks
        flat_tasks.extend(tasks)
        valid_scenarios.append(scenario)
    return valid_scenarios, flat_tasks


def generate_category(config: Config, spec: dict[str, Any], category: dict[str, Any], count: int, batch: int = 0) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if config.dry_run:
        payload = generate_dry_run_category(category, count)
    else:
        system, user = build_prompt(spec, category, count)
        if batch:
            user += f"\n\nIMPORTANT: This is batch {batch}. Generate scenarios that are DIFFERENT from any previous batch. Cover different sub-topics, different phrasings, and different user goals within this category. DO NOT repeat scenarios from earlier batches."
        key = stable_id(
            "seed",
            {
                "model": config.model,
                "category": category,
                "count": count,
                "prompt": user,
                "batch": batch,
            },
        )
        payload = call_nvidia(config, system, user, key)
    return validate_and_flatten(payload)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def generate(args: argparse.Namespace) -> None:
    spec = load_spec(Path(args.spec))
    out_dir = Path(args.out_dir)
    config = Config(
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.getenv("NVIDIA_API_KEY", ""),
        model=os.getenv("NVIDIA_MODEL", args.model),
        dry_run=args.dry_run,
        timeout_s=args.timeout_s,
        max_retries=args.max_retries,
        cache_db=Path(args.cache_db),
        temperature=args.temperature,
    )
    if not config.dry_run and not config.api_key:
        raise SystemExit("NVIDIA_API_KEY is required unless --dry-run is set")

    categories = spec["categories"]
    if args.categories:
        wanted = set(args.categories.split(","))
        categories = [category for category in categories if category["name"] in wanted]
    if args.limit_categories:
        categories = categories[: args.limit_categories]

    all_scenarios: list[dict[str, Any]] = []
    all_tasks: list[dict[str, Any]] = []
    random.seed(args.seed)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = []
        for category in categories:
            count = args.per_category or int(category.get("target_count", 10))
            futures.append(pool.submit(generate_category, config, spec, category, count, args.batch))
        for future in concurrent.futures.as_completed(futures):
            scenarios, tasks = future.result()
            all_scenarios.extend(scenarios)
            all_tasks.extend(tasks)
            print(f"generated scenarios={len(scenarios)} tasks={len(tasks)}")

    scenario_path = out_dir / "cemm_generated_scenarios.jsonl"
    task_path = out_dir / "cemm_generated_training.jsonl"
    write_jsonl(scenario_path, all_scenarios)
    write_jsonl(task_path, all_tasks)
    print(f"wrote {len(all_scenarios)} scenarios to {scenario_path}")
    print(f"wrote {len(all_tasks)} task records to {task_path}")


def validate(args: argparse.Namespace) -> None:
    path = Path(args.jsonl)
    counts: dict[str, int] = {}
    total = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            task_type = row.get("task_type")
            if task_type not in ALLOWED_TASK_TYPES:
                raise SystemExit(f"line {line_no}: invalid task_type {task_type!r}")
            counts[task_type] = counts.get(task_type, 0) + 1
            total += 1
    print(json.dumps({"total": total, "by_task_type": counts}, indent=2, sort_keys=True))


MUTATION_MAP: dict[str, str] = {
    "you": "u", "your": "ur", "are": "re", "why": "y",
    "please": "pls", "thanks": "thx", "thank you": "ty",
    "what": "wat", "the": "teh", "because": "cuz",
    "going to": "gonna", "want to": "wanna", "got to": "gotta",
    "do not know": "dunno", "let me": "lemme", "kind of": "kinda",
    "sort of": "sorta", "give me": "gimme",
    "before": "b4", "great": "gr8", "later": "l8r", "message": "msg",
    "favorite": "favourite", "color": "colour", "center": "centre",
}


def mutate_utterance(text: str, rng: random.Random) -> str:
    if not text:
        return text
    lower = text.lower()
    words = lower.split()
    mutated: list[str] = []
    for w in words:
        m = w.strip(".,!?;:")
        if not m:
            continue
        if m in MUTATION_MAP and rng.random() < 0.5:
            mutated.append(MUTATION_MAP[m])
        elif rng.random() < 0.15:
            chars = list(m)
            if len(chars) >= 3 and rng.random() < 0.4:
                idx = rng.randint(1, len(chars) - 2)
                chars[idx] = chars[idx] * rng.randint(2, 3)
            elif len(chars) >= 3 and rng.random() < 0.3:
                idx = rng.randint(0, len(chars) - 2)
                chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
            mutated.append("".join(chars))
        else:
            mutated.append(m)
    result = " ".join(mutated)
    if text[0].isupper():
        result = result.capitalize()
    return result


def mutate_scenario(scenario: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    new = copy.deepcopy(scenario)
    for turn in new.get("conversation", []):
        raw = turn.get("content")
        if isinstance(raw, str):
            turn["content"] = mutate_utterance(raw, rng)
        elif isinstance(raw, dict) and "text" in raw:
            raw["text"] = mutate_utterance(raw["text"], rng)
    for te in new.get("task_examples", []):
        if "signal" in te:
            sc = te["signal"].get("content")
            if isinstance(sc, str):
                te["signal"]["content"] = mutate_utterance(sc, rng)
            elif isinstance(sc, dict) and "text" in sc:
                sc["text"] = mutate_utterance(sc["text"], rng)
    return new


def mutate_task_record(record: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    new = copy.deepcopy(record)
    if "signal" in new:
        sc = new["signal"].get("content")
        if isinstance(sc, str):
            new["signal"]["content"] = mutate_utterance(sc, rng)
        elif isinstance(sc, dict) and "text" in sc:
            sc["text"] = mutate_utterance(sc["text"], rng)
    if "input" in new and isinstance(new["input"], str):
        new["input"] = mutate_utterance(new["input"], rng)
    return new


def mutate(args: argparse.Namespace) -> None:
    scenarios_path = Path(args.scenarios)
    tasks_path = Path(args.tasks)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    count = args.count

    rng = random.Random(args.seed)
    all_scenarios: list[dict[str, Any]] = []
    all_tasks: list[dict[str, Any]] = []

    with scenarios_path.open("r", encoding="utf-8") as f:
        clean_scenarios = [json.loads(line.strip()) for line in f if line.strip()]
    with tasks_path.open("r", encoding="utf-8") as f:
        clean_tasks = [json.loads(line.strip()) for line in f if line.strip()]

    task_by_scenario: dict[str, list[dict[str, Any]]] = {}
    for t in clean_tasks:
        task_by_scenario.setdefault(t.get("scenario_id", ""), []).append(t)

    for scenario in clean_scenarios:
        for v in range(count):
            vseed = rng.randint(0, 2**31)
            vrng = random.Random(vseed)
            all_scenarios.append(mutate_scenario(scenario, vrng))
        sid = scenario.get("scenario_id", "")
        for task in task_by_scenario.get(sid, []):
            for v in range(count):
                vseed = rng.randint(0, 2**31)
                vrng = random.Random(vseed)
                all_tasks.append(mutate_task_record(task, vrng))

    scenario_out = out_dir / "cemm_generated_scenarios.jsonl"
    task_out = out_dir / "cemm_generated_training.jsonl"
    write_jsonl(scenario_out, all_scenarios)
    write_jsonl(task_out, all_tasks)
    print(f"mutated {len(clean_scenarios)} scenarios x{count} = {len(all_scenarios)} scenarios")
    print(f"mutated {len(clean_tasks)} tasks x{count} = {len(all_tasks)} task records")
    print(f"wrote to {scenario_out} and {task_out}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate CEMM seed training data with NVIDIA API")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="generate seed training data")
    gen.add_argument("--spec", default="cemm_seed_spec.json")
    gen.add_argument("--out-dir", default="generated")
    gen.add_argument("--cache-db", default="generated/cemm_seed_cache.sqlite3")
    gen.add_argument("--model", default="meta/llama-3.1-70b-instruct")
    gen.add_argument("--workers", type=int, default=2)
    gen.add_argument("--per-category", type=int, default=0)
    gen.add_argument("--limit-categories", type=int, default=0)
    gen.add_argument("--categories", default="", help="comma-separated category names")
    gen.add_argument("--timeout-s", type=int, default=120)
    gen.add_argument("--max-retries", type=int, default=3)
    gen.add_argument("--batch", type=int, default=0, help="batch number for prompt variation (0=no variation)")
    gen.add_argument("--temperature", type=float, default=0.7)
    gen.add_argument("--seed", type=int, default=7)
    gen.add_argument("--dry-run", action="store_true")

    val = sub.add_parser("validate", help="validate generated task JSONL")
    val.add_argument("jsonl")

    mut = sub.add_parser("mutate", help="create noisy variants of scenarios for robustness training")
    mut.add_argument("--scenarios", required=True, help="path to clean scenarios JSONL")
    mut.add_argument("--tasks", required=True, help="path to clean task records JSONL")
    mut.add_argument("--out-dir", default="generated_noisy")
    mut.add_argument("--count", type=int, default=2, help="noisy variants per clean example")
    mut.add_argument("--seed", type=int, default=42)

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.cmd == "generate":
        generate(args)
        return 0
    if args.cmd == "validate":
        validate(args)
        return 0
    if args.cmd == "mutate":
        mutate(args)
        return 0
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
