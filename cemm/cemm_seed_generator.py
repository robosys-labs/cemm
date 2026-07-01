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
import dataclasses
import hashlib
import json
import os
import random
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ALLOWED_TASK_TYPES = {
    "semantic_graph_extraction",
    "semantic_graph_denoising",
    "semantic_latent_target",
    "semantic_answer_composition",
    "semantic_text_realization",
    "next_event_prediction",
    "uol_mapping",
    "claim_extraction",
    "predicate_mapping",
    "context_inference",
    "pragmatic_interpretation",
    "synthesis_verification",
    "causal_rule_extraction",
    "causal_effect_prediction",
    "tool_handoff_planning",
    "procedure_model_induction",
    "temporal_relation_derivation",
    "memory_retrieval_ranking",
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
Return strict JSON only:
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
        "action_kind": "answer|ask|remember|update|act|abstain",
        "synthesis_strategy": "template|extractive|neural|abstain",
        "notes": ""
      },
      "task_examples": [
        {
          "task_type": "semantic_graph_extraction",
          "permission_scope": "session_private",
          "priority": 50,
          "signal": {"kind": "input", "content": "text", "source_type": "user"},
          "context_kernel": {},
          "expected_semantic_event_graph": {}
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
        "You generate high-quality seed training data for CEMM-SLC, the Contextual Event Memory Model "
        "with a Semantic Latent Core. CEMM is not trained on words alone; it learns from signal + "
        "ContextKernel + SemanticEventGraph + memory + SemanticAnswerGraph. "
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
        "response_format": {"type": "json_object"},
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
    if category == "noisy_casual_chat":
        return {
            "task_type": task_type,
            "permission_scope": "local_training",
            "priority": 50,
            "category": category,
            "context_kernel": {
                "conversation": {"turn_index": 2},
                "permission": {"scope": "local_training"},
            },
            "input_text": "heyyy lol what??",
            "semantic_event_graph": {
                "source_signal_ids": ["seed_sig"],
                "context_id": "seed_ctx",
                "entity_refs": [],
                "processes": [
                    {"kind": "process", "frame_key": "request_clarification", "confidence": 0.8}
                ],
                "states": [],
                "permission_scope": "local_training",
                "confidence": 0.8,
            },
            "observation_semantics": {
                "speech_act": "confusion",
                "semantic_cluster_key": "confusion",
                "confidence": 0.8,
            },
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
    elif task_type == "semantic_graph_extraction":
        if category == "math_tool_handoff":
            base["signal"] = {"kind": "input", "content": "What is 17.5% of 420000?", "source_type": "user"}
            base["context_kernel"] = {"conversation": {"turn_index": 1}, "permission": {"scope": "session_private"}}
            base["expected_semantic_event_graph"] = {
                "processes": [{"frame_key": "compute_percentage"}],
                "states": [{"state_key": "exact_computation_required"}],
            }
        elif category == "scheduling_procedure_skill":
            base["signal"] = {
                "kind": "input",
                "content": "Schedule a virtual meeting with ada@example.com and ben@example.com next week.",
                "source_type": "user",
            }
            base["context_kernel"] = {"conversation": {"turn_index": 1}, "permission": {"scope": "session_private"}}
            base["expected_semantic_event_graph"] = {
                "entity_refs": [{"entity_id": "ada", "role": "participant"}, {"entity_id": "ben", "role": "participant"}],
                "processes": [{"frame_key": "schedule_virtual_meeting"}],
                "states": [{"state_key": "missing_duration"}, {"state_key": "missing_title"}],
            }
        else:
            base["signal"] = {"kind": "input", "content": "My favorite database is Postgres.", "source_type": "user"}
            base["context_kernel"] = {
                "conversation": {"turn_index": 2},
                "user": {"known": True},
                "permission": {"scope": "session_private"},
            }
            base["expected_semantic_event_graph"] = {
                "entity_refs": [{"entity_id": "user", "role": "actor"}],
                "processes": [{"frame_key": "state_preference"}],
                "states": [{"state_key": "user_preference"}],
            }
    elif task_type == "semantic_graph_denoising":
        base["corrupted_graph"] = {"processes": [{"frame_key": "favorite"}], "states": []}
        base["context_kernel"] = {"permission": {"scope": "session_private"}}
    elif task_type == "semantic_latent_target":
        base["semantic_event_graphs"] = [
            {"id": "g1", "processes": [{"frame_key": "assert_evaluation"}], "states": [{"state_key": "low_competence"}]},
            {"id": "g2", "processes": [{"frame_key": "assert_evaluation"}], "states": [{"state_key": "low_competence"}]},
        ]
        base["target"] = "align paraphrased negative evaluations while preserving target and intensity"
    elif task_type == "semantic_answer_composition":
        if category == "math_tool_handoff":
            base["question_graph"] = {"processes": [{"frame_key": "compute_percentage"}]}
            base["tool_result"] = {"tool_id": "calculator.basic", "result": 73500}
        elif category == "scheduling_procedure_skill":
            base["question_graph"] = {"processes": [{"frame_key": "schedule_virtual_meeting"}]}
            base["missing_slots"] = ["duration", "title"]
            base["selected_models"] = [{"registry_key": "schedule_virtual_meeting", "kind": "procedure_model"}]
        else:
            base["question_graph"] = {"processes": [{"frame_key": "recall_memory"}]}
            base["selected_claims"] = [{"id": "claim_fav_db", "subject": "user", "predicate": "favorite_database", "object": "Postgres"}]
    elif task_type == "semantic_text_realization":
        if category == "math_tool_handoff":
            base["semantic_answer_graph"] = {"intent": "answer", "states": [{"state_key": "computed_result", "value": 73500}]}
            base["tool_result"] = {"tool_id": "calculator.basic", "result": 73500}
        else:
            base["semantic_answer_graph"] = {
                "intent": "answer",
                "selected_claim_ids": ["claim_fav_db"],
                "states": [{"state_key": "favorite_database", "holder_entity_id": "user"}],
            }
            base["selected_claims"] = [{"id": "claim_fav_db", "predicate": "favorite_database", "object": "Postgres"}]
    elif task_type == "next_event_prediction":
        base["recent_events"] = [
            {"semantic_cluster_key": "failed_answer"},
            {"semantic_cluster_key": "negative_evaluation.assistant_competence"},
        ]
        base["context_kernel"] = {"conversation": {"turn_index": 3}, "user": {"affect": {"frustration": 0.7}}}
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
        if category == "math_tool_handoff":
            base["answer"] = "17.5% of 420000 is 73500."
            base["tool_result"] = {"tool_id": "calculator.basic", "result": 73500}
        else:
            base["answer"] = "Your favorite database is Postgres."
            base["selected_claims"] = [{"subject": "user", "predicate": "favorite_database", "object": "Postgres"}]
    elif task_type == "causal_rule_extraction":
        base["sequence"] = [{"event": "assistant_failed_answer"}, {"event": "user_repeats_negative_evaluation"}]
    elif task_type == "causal_effect_prediction":
        base["causal_models"] = [{"preconditions": ["assistant_failed_answer"], "effects": ["user_frustration_increases"], "confidence": 0.7}]
        base["current_event"] = "assistant_failed_answer"
    elif task_type == "tool_handoff_planning":
        if category == "scheduling_procedure_skill":
            base["signal"] = {
                "kind": "input",
                "content": "Schedule a virtual meeting with ada@example.com and ben@example.com next week.",
                "source_type": "user",
            }
            base["semantic_event_graph"] = {
                "processes": [{"frame_key": "schedule_virtual_meeting"}],
                "states": [{"state_key": "calendar_availability_required"}],
            }
            base["available_tool_models"] = [
                {"tool_id": "calendar.availability", "input_schema": "participants,time_window"},
                {"tool_id": "calendar.create_event", "input_schema": "participants,start,end,title"},
                {"tool_id": "meeting_link.generate", "input_schema": "event_id"},
            ]
        else:
            base["signal"] = {"kind": "input", "content": "What is 17.5% of 420000?", "source_type": "user"}
            base["semantic_event_graph"] = {
                "processes": [{"frame_key": "compute_percentage"}],
                "states": [{"state_key": "exact_computation_required"}],
            }
            base["available_tool_models"] = [{"tool_id": "calculator.basic", "input_schema": "expression"}]
    elif task_type == "procedure_model_induction":
        base["workflow_traces"] = [
            {
                "goal": "schedule_virtual_meeting",
                "slots": ["participants", "time_window", "duration", "title"],
                "tool_sequence": ["calendar.availability", "calendar.create_event", "meeting_link.generate"],
                "outcome": "success",
            }
        ]
    elif task_type == "memory_retrieval_ranking":
        base["query_graph"] = {"processes": [{"frame_key": "recall_memory"}], "states": [{"state_key": "favorite_database"}]}
        base["candidates"] = [
            {"id": "claim_good", "predicate": "favorite_database", "object": "Postgres", "confidence": 0.92},
            {"id": "claim_bad", "predicate": "favorite_color", "object": "Blue", "confidence": 0.9},
        ]
    elif task_type == "operator_selection":
        if category == "scheduling_procedure_skill":
            base["semantic_event_graph"] = {"processes": [{"frame_key": "schedule_virtual_meeting"}]}
            base["grounded_graph"] = {"missing_slots": ["duration", "title"], "permission": {"scope": "session_private"}}
            base["expected_action_kind"] = "ask"
        else:
            base["signal"] = {"kind": "input", "content": f"Seed example {idx} for {task_type}", "source_type": "user"}
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
                    "action_kind": "answer",
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


def generate_category(config: Config, spec: dict[str, Any], category: dict[str, Any], count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if config.dry_run:
        payload = generate_dry_run_category(category, count)
    else:
        system, user = build_prompt(spec, category, count)
        key = stable_id(
            "seed",
            {
                "model": config.model,
                "category": category,
                "count": count,
                "prompt": user,
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
            futures.append(pool.submit(generate_category, config, spec, category, count))
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
    gen.add_argument("--temperature", type=float, default=0.7)
    gen.add_argument("--seed", type=int, default=7)
    gen.add_argument("--dry-run", action="store_true")

    val = sub.add_parser("validate", help="validate generated task JSONL")
    val.add_argument("jsonl")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.cmd == "generate":
        generate(args)
        return 0
    if args.cmd == "validate":
        validate(args)
        return 0
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
