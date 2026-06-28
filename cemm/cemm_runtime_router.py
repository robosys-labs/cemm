#!/usr/bin/env python3
"""
CEMM runtime router for basic end-to-end conversations.

This is the bridge between generated/labeled training data and a usable assistant loop.

Design:
- Fast deterministic routing first.
- SQLite memory for signals, claims, actions, traces, and user facts.
- Optional OpenAI-compatible LLM task calls for context/UOL/operator/synthesis.
- Template/extractive synthesis before neural fallback.
- Every turn writes a trace.

Environment for optional neural path:
  export CEMM_RUNTIME_API_KEY="..."
  export CEMM_RUNTIME_BASE_URL="https://integrate.api.nvidia.com/v1/chat/completions"
  export CEMM_RUNTIME_MODEL="meta/llama-3.1-70b-instruct"

Examples:
  python3 cemm_runtime_router.py chat --dry-run
  python3 cemm_runtime_router.py once "My favorite database is Postgres."
  python3 cemm_runtime_router.py once "What is my favorite database?"
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


RUNTIME_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  source_type TEXT NOT NULL,
  content TEXT NOT NULL,
  context_json TEXT NOT NULL,
  semantics_json TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object_value TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  confidence REAL NOT NULL DEFAULT 0.8,
  evidence_signal_id TEXT NOT NULL,
  frame_id TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_sp ON claims(subject, predicate, status);

CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  input_signal_id TEXT NOT NULL,
  selected_claim_ids_json TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS traces (
  id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL,
  action_id TEXT NOT NULL,
  trace_json TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
"""


@dataclasses.dataclass(frozen=True)
class RuntimeConfig:
    db_path: Path
    dry_run: bool
    base_url: str
    api_key: str
    model: str
    timeout_s: int
    max_retries: int


@dataclasses.dataclass
class ContextKernel:
    session_id: str
    turn_index: int
    time_bucket: str
    user_known: bool
    recent_signal_ids: list[str]
    active_claim_ids: list[str]
    mode: str
    budget_ms: int


@dataclasses.dataclass
class RouteDecision:
    action_kind: str
    confidence: float
    reason: str
    selected_claim_ids: list[str]
    required_slots: list[str]
    missing_slots: list[str]


def now() -> int:
    return int(time.time())


def stable_id(prefix: str, data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:24]}"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(RUNTIME_SCHEMA)
    conn.commit()
    return conn


def time_bucket(ts: int | None = None) -> str:
    hour = time.localtime(ts or now()).tm_hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def build_context(conn: sqlite3.Connection, session_id: str) -> ContextKernel:
    rows = conn.execute(
        "SELECT id FROM signals WHERE json_extract(context_json, '$.session_id') = ? ORDER BY created_at DESC LIMIT 8",
        (session_id,),
    ).fetchall()
    claim_rows = conn.execute("SELECT id FROM claims WHERE status = 'active' ORDER BY updated_at DESC LIMIT 32").fetchall()
    return ContextKernel(
        session_id=session_id,
        turn_index=len(rows) + 1,
        time_bucket=time_bucket(),
        user_known=True,
        recent_signal_ids=[row["id"] for row in rows],
        active_claim_ids=[row["id"] for row in claim_rows],
        mode="assistant",
        budget_ms=50,
    )


def observe(conn: sqlite3.Connection, content: str, context: ContextKernel) -> str:
    payload = {"content": content, "session_id": context.session_id, "turn_index": context.turn_index}
    signal_id = stable_id("sig", payload | {"ts": int(time.time() * 1000000)})
    conn.execute(
        """
        INSERT INTO signals (id, kind, source_type, content, context_json, semantics_json, created_at)
        VALUES (?, 'input', 'user', ?, ?, NULL, ?)
        """,
        (signal_id, content, json.dumps(dataclasses.asdict(context), sort_keys=True), now()),
    )
    conn.commit()
    return signal_id


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def infer_context(text: str, context: ContextKernel) -> dict[str, Any]:
    lower = text.lower()
    inferences: list[dict[str, Any]] = []
    if context.turn_index == 1 and re.fullmatch(r"(hi|hello|hey|good morning|morning|good afternoon|good evening)[!. ]*", lower):
        inferences.append({"kind": "session_opening", "value": "greeting", "confidence": 0.95})
    if context.turn_index == 1 and len(lower.split()) <= 4 and any(word in lower for word in ["fix", "now", "quick", "urgent"]):
        inferences.append({"kind": "urgency", "value": "possible_hurry", "confidence": 0.45})
    if "weather" in lower and not any(place in lower for place in ["lagos", "abuja", "london", "new york", "enugu"]):
        inferences.append({"kind": "missing_slot", "value": "location", "confidence": 0.9})
    if any(word in lower for word in ["actually", "correction", "correction", "wait", "no,"]):
        inferences.append({"kind": "correction", "value": "possible_supersession", "confidence": 0.8})
    return {"inferences": inferences, "confidence": max([i["confidence"] for i in inferences], default=0.5)}


def map_uol(text: str) -> dict[str, Any]:
    lower = text.lower()
    atoms: list[dict[str, Any]] = []
    if any(word in lower for word in ["dumb", "daft", "fool", "don't know anything"]):
        atoms.extend(
            [
                {"kind": "entity_ref", "entity": "assistant_self", "role": "target", "confidence": 0.95},
                {
                    "kind": "process",
                    "frame_key": "assert_evaluation",
                    "participants": [{"role": "target", "entity": "assistant_self"}],
                    "polarity": "affirmed",
                    "intensity": 0.85,
                    "confidence": 0.9,
                },
                {
                    "kind": "state",
                    "state_key": "low_competence",
                    "holder": "assistant_self",
                    "dimension": "competence",
                    "value": -0.8,
                    "polarity": "negative",
                    "intensity": 0.9,
                    "confidence": 0.9,
                },
            ]
        )
    if re.search(r"\b(my|i like|i prefer|favorite)\b", lower):
        atoms.append({"kind": "process", "frame_key": "state_preference", "confidence": 0.75})
    if "?" in text:
        atoms.append({"kind": "process", "frame_key": "ask_question", "confidence": 0.8})
    return {"uol_atoms": atoms, "semantic_cluster_key": atoms[1]["frame_key"] if len(atoms) > 1 else ""}


def extract_claim(text: str) -> dict[str, Any] | None:
    lower = text.lower().strip()
    match = re.search(r"my favorite ([a-z _-]+?) is ([a-z0-9 ._-]+)", lower)
    if match:
        field = re.sub(r"[^a-z0-9]+", "_", match.group(1)).strip("_")
        value = match.group(2).strip(" .")
        return {"subject": "user", "predicate": f"favorite_{field}", "object_value": value, "confidence": 0.92}
    match = re.search(r"i prefer ([a-z0-9 ._-]+)", lower)
    if match:
        return {"subject": "user", "predicate": "preference", "object_value": match.group(1).strip(" ."), "confidence": 0.8}
    return None


def retrieve_claim(conn: sqlite3.Connection, predicate: str) -> sqlite3.Row | None:
    row = conn.execute(
        "SELECT * FROM claims WHERE subject = 'user' AND predicate = ? AND status = 'active' ORDER BY confidence DESC, updated_at DESC LIMIT 1",
        (predicate,),
    ).fetchone()
    return row


def find_recall_predicate(text: str) -> str | None:
    lower = text.lower()
    match = re.search(r"(what is|what's|whats) my favorite ([a-z _-]+)", lower)
    if match:
        field = re.sub(r"[^a-z0-9]+", "_", match.group(2)).strip("_?")
        return f"favorite_{field}"
    return None


def route(conn: sqlite3.Connection, text: str, context: ContextKernel, context_info: dict[str, Any]) -> RouteDecision:
    lower = text.lower().strip()
    if any(i.get("kind") == "missing_slot" for i in context_info.get("inferences", [])):
        return RouteDecision("ask", 0.9, "missing location slot", [], ["location"], ["location"])

    if context.turn_index == 1 and re.fullmatch(r"(hi|hello|hey|good morning|morning|good afternoon|good evening)[!. ]*", lower):
        return RouteDecision("answer", 0.95, "session greeting", [], [], [])

    any_correction = any(i.get("kind") == "correction" for i in context_info.get("inferences", []))
    if any_correction:
        claim = extract_claim(text)
        if claim:
            return RouteDecision("remember", claim["confidence"], "correction supersedes previous claim", [], [], [])

    claim = extract_claim(text)
    if claim:
        return RouteDecision("remember", claim["confidence"], "user stated a rememberable claim", [], [], [])

    predicate = find_recall_predicate(text)
    if predicate:
        row = retrieve_claim(conn, predicate)
        if row:
            return RouteDecision("answer", float(row["confidence"]), "recall selected claim", [row["id"]], [], [])
        return RouteDecision("ask", 0.6, "requested memory not found", [], [], [])

    if any(word in lower for word in ["dumb", "daft", "fool"]):
        return RouteDecision("answer", 0.75, "pragmatic negative evaluation", [], [], [])

    small_talk_phrases = ["how are you", "what can you do", "who are you",
                          "what is your name", "thanks", "thank you", "bye", "goodbye"]
    if any(phrase in lower for phrase in small_talk_phrases):
        return RouteDecision("answer", 0.85, "small talk match", [], [], [])

    if "?" in text:
        return RouteDecision("abstain", 0.55, "unsupported open question in basic runtime", [], [], [])

    return RouteDecision("answer", 0.5, "small talk fallback", [], [], [])


def save_claim(conn: sqlite3.Connection, signal_id: str, claim: dict[str, Any]) -> str:
    claim_id = stable_id("claim", claim)
    ts = now()
    conn.execute(
        """
        UPDATE claims SET status = 'superseded', updated_at = ?
        WHERE subject = ? AND predicate = ? AND status = 'active'
        """,
        (ts, claim["subject"], claim["predicate"]),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO claims
        (id, subject, predicate, object_value, status, confidence, evidence_signal_id, frame_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'active', ?, ?, 'session', ?, ?)
        """,
        (
            claim_id,
            claim["subject"],
            claim["predicate"],
            claim["object_value"],
            float(claim.get("confidence", 0.8)),
            signal_id,
            ts,
            ts,
        ),
    )
    conn.commit()
    return claim_id


def synthesize(conn: sqlite3.Connection, decision: RouteDecision, text: str, context: ContextKernel) -> tuple[str, dict[str, Any]]:
    if decision.action_kind == "ask":
        if "location" in decision.missing_slots:
            return "Which location should I use?", {"strategy": "template", "verified": True}
        return "Can you clarify that?", {"strategy": "template", "verified": True}

    if decision.action_kind == "remember":
        return "Got it.", {"strategy": "template", "verified": True}

    if decision.action_kind == "abstain":
        return "I don't have enough grounded context to answer that yet.", {"strategy": "template", "verified": True}

    if decision.selected_claim_ids:
        claim_id = decision.selected_claim_ids[0]
        row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if row:
            readable = row["predicate"].replace("_", " ")
            return f"Your {readable} is {row['object_value']}.", {"strategy": "template", "verified": True, "claim_id": claim_id}

    lower = text.lower().strip()
    if re.fullmatch(r"(hi|hello|hey|good morning|morning|good afternoon|good evening)[!. ]*", lower):
        return "Good morning." if "morning" in lower else "Hello.", {"strategy": "template", "verified": True}

    if any(word in lower for word in ["dumb", "daft", "fool"]):
        return "I hear the frustration. Let me focus on fixing the part that failed.", {"strategy": "template", "verified": True}

    small_talk = {
        "how are you": "I'm functioning well, thanks for asking.",
        "what can you do": "I can remember facts about you and answer based on what I've learned.",
        "who are you": "I'm CEMM-Basic, a conversational memory system.",
        "what is your name": "I'm CEMM-Basic.",
        "thanks": "You're welcome.",
        "thank you": "You're welcome.",
        "bye": "Goodbye.",
        "goodbye": "Goodbye.",
    }
    for phrase, response in small_talk.items():
        if phrase in lower:
            return response, {"strategy": "template", "verified": True}

    return "I'm here.", {"strategy": "template", "verified": True}


def write_action_trace(
    conn: sqlite3.Connection,
    signal_id: str,
    decision: RouteDecision,
    response: str,
    semantics: dict[str, Any],
    verification: dict[str, Any],
) -> str:
    action_id = stable_id("act", {"signal_id": signal_id, "decision": dataclasses.asdict(decision), "ts": now()})
    ts = now()
    conn.execute(
        """
        INSERT INTO actions (id, kind, input_signal_id, selected_claim_ids_json, confidence, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'executed', ?)
        """,
        (action_id, decision.action_kind, signal_id, json.dumps(decision.selected_claim_ids), decision.confidence, ts),
    )
    trace = {
        "signal_id": signal_id,
        "action_id": action_id,
        "action_kind": decision.action_kind,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "selected_claim_ids": decision.selected_claim_ids,
        "semantics": semantics,
        "synthesis": verification,
        "response": response,
    }
    trace_id = stable_id("trace", trace)
    conn.execute(
        "INSERT INTO traces (id, signal_id, action_id, trace_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (trace_id, signal_id, action_id, json.dumps(trace, sort_keys=True), ts),
    )
    conn.commit()
    return trace_id


def handle_turn(conn: sqlite3.Connection, content: str, session_id: str) -> dict[str, Any]:
    context = build_context(conn, session_id)
    signal_id = observe(conn, content, context)
    normalized = normalize(content)
    context_info = infer_context(normalized, context)
    uol = map_uol(normalized)
    semantics = {"context": context_info, "uol": uol}
    conn.execute("UPDATE signals SET semantics_json = ? WHERE id = ?", (json.dumps(semantics, sort_keys=True), signal_id))

    decision = route(conn, normalized, context, context_info)
    stored_claim_id = None
    if decision.action_kind == "remember":
        claim = extract_claim(normalized)
        if claim:
            stored_claim_id = save_claim(conn, signal_id, claim)

    response, verification = synthesize(conn, decision, normalized, context)
    trace_id = write_action_trace(conn, signal_id, decision, response, semantics, verification)
    return {
        "response": response,
        "signal_id": signal_id,
        "trace_id": trace_id,
        "action": dataclasses.asdict(decision),
        "stored_claim_id": stored_claim_id,
    }


def call_llm(config: RuntimeConfig, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if config.dry_run:
        return {"task_type": task_type, "confidence": 0.0, "dry_run": True}
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "Return strict JSON for the requested CEMM runtime task."},
            {"role": "user", "content": json.dumps({"task_type": task_type, "payload": payload}, sort_keys=True)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        config.base_url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=config.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
            envelope = json.loads(raw)
            return json.loads(envelope["choices"][0]["message"]["content"])
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"runtime LLM call failed: {last_error}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CEMM basic runtime router")
    parser.add_argument("--db", default="cemm_runtime.sqlite3")
    parser.add_argument("--session-id", default="default")
    sub = parser.add_subparsers(dest="cmd", required=True)

    once = sub.add_parser("once", help="handle one user turn")
    once.add_argument("text")
    once.add_argument("--json", action="store_true")

    chat = sub.add_parser("chat", help="interactive chat")
    chat.add_argument("--dry-run", action="store_true")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = RuntimeConfig(
        db_path=Path(args.db),
        dry_run=bool(getattr(args, "dry_run", False)),
        base_url=os.getenv("CEMM_RUNTIME_BASE_URL", "https://integrate.api.nvidia.com/v1/chat/completions"),
        api_key=os.getenv("CEMM_RUNTIME_API_KEY", ""),
        model=os.getenv("CEMM_RUNTIME_MODEL", "meta/llama-3.1-70b-instruct"),
        timeout_s=int(os.getenv("CEMM_RUNTIME_TIMEOUT_S", "60")),
        max_retries=int(os.getenv("CEMM_RUNTIME_MAX_RETRIES", "2")),
    )
    conn = connect(config.db_path)

    if args.cmd == "once":
        result = handle_turn(conn, args.text, args.session_id)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(result["response"])
        return 0

    if args.cmd == "chat":
        print("CEMM basic router. Ctrl-D to exit.")
        for line in sys.stdin:
            text = line.strip()
            if not text:
                continue
            result = handle_turn(conn, text, args.session_id)
            print(result["response"])
        return 0

    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
