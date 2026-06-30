#!/usr/bin/env python3
"""
CEMM runtime router for basic end-to-end conversations.

This file is intentionally small, but it must still obey the CEMM architecture:
- routing is grounded in ContextKernel, not raw text alone
- ContextKernel carries world, user, time, conversation, goal, memory, self,
  permission, and budget state
- every turn writes a trace
- traces can be exported back into the trainer as context-grounded examples

Environment for optional neural path:
  export CEMM_RUNTIME_API_KEY="..."
  export CEMM_RUNTIME_BASE_URL="https://integrate.api.nvidia.com/v1/chat/completions"
  export CEMM_RUNTIME_MODEL="meta/llama-3.1-70b-instruct"

Examples:
  python3 cemm_runtime_router.py chat
  python3 cemm_runtime_router.py once "My favorite database is Postgres."
  python3 cemm_runtime_router.py export-training --out generated/runtime_training.jsonl
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

CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);

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

CREATE TABLE IF NOT EXISTS self_state (
  id TEXT PRIMARY KEY,
  state_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS world_state (
  id TEXT PRIMARY KEY,
  state_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL
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
    id: str
    session_id: str
    world: dict[str, Any]
    user: dict[str, Any]
    time: dict[str, Any]
    conversation: dict[str, Any]
    goal: dict[str, Any]
    memory: dict[str, Any]
    self_view: dict[str, Any]
    permission: dict[str, Any]
    budget: dict[str, Any]

    @property
    def turn_index(self) -> int:
        return int(self.conversation["turn_index"])

    @property
    def time_bucket(self) -> str:
        return str(self.time["bucket"])

    @property
    def budget_ms(self) -> int:
        return int(self.budget["latency_target_ms"])


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


def parse_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


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


def default_self_state() -> dict[str, Any]:
    return {
        "identity": {
            "entity_id": "assistant_self",
            "name": "CEMM Runtime",
            "role": "conversation_runtime",
            "architecture": "contextual_event_memory_model",
        },
        "internal": {
            "mode": "assistant",
            "uncertainty": 0.0,
            "coherence": 1.0,
            "load": 0.0,
            "last_action": None,
            "last_error": None,
        },
        "epistemic": {
            "known_limits": ["no_live_world_fetch_without_tool"],
            "unsupported_query_count": 0,
            "recent_low_confidence_count": 0,
        },
        "meta_memory": {
            "stored_claim_count": 0,
            "last_memory_write_signal_id": None,
            "last_recalled_claim_ids": [],
        },
        "historical_arc": {
            "turn_count": 0,
            "created_at": now(),
            "recent_trace_ids": [],
        },
        "version": "cemm.self.v1",
    }


def default_world_state() -> dict[str, Any]:
    return {
        "assistant_location": {
            "country": os.getenv("CEMM_ASSISTANT_COUNTRY", ""),
            "region": os.getenv("CEMM_ASSISTANT_REGION", ""),
            "city": os.getenv("CEMM_ASSISTANT_CITY", ""),
            "timezone": os.getenv("CEMM_ASSISTANT_TIMEZONE", time.tzname[0] if time.tzname else ""),
        },
        "knowledge_freshness": {
            "current_events_require_tool": True,
            "last_external_refresh_at": None,
        },
        "active_frame_ids": [],
        "causal_model_ids": [],
        "version": "cemm.world.v1",
    }


def load_state(conn: sqlite3.Connection, table: str, key: str, default: dict[str, Any]) -> dict[str, Any]:
    row = conn.execute(f"SELECT state_json FROM {table} WHERE id = ?", (key,)).fetchone()
    if row:
        return parse_json(row["state_json"], default)
    conn.execute(
        f"INSERT INTO {table} (id, state_json, updated_at) VALUES (?, ?, ?)",
        (key, json.dumps(default, sort_keys=True), now()),
    )
    conn.commit()
    return default


def save_state(conn: sqlite3.Connection, table: str, key: str, state: dict[str, Any]) -> None:
    conn.execute(
        f"""
        INSERT INTO {table} (id, state_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
        """,
        (key, json.dumps(state, sort_keys=True), now()),
    )
    conn.commit()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def semantic_cluster_for_text(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["dumb", "daft", "fool", "don't know anything"]):
        return "negative_evaluation.assistant_competence"
    if re.search(r"\b(my|i like|i prefer|favorite)\b", lower):
        return "preference_statement"
    if "weather" in lower:
        return "weather_request"
    if re.fullmatch(r"(hi|hello|hey|good morning|morning|good afternoon|good evening)[!. ]*", lower):
        return "greeting"
    if "?" in text:
        return "question"
    return "utterance"


def recent_signal_rows(conn: sqlite3.Connection, session_id: str, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM signals
        WHERE json_extract(context_json, '$.session_id') = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()


def active_claim_rows(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM claims WHERE status = 'active' ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()


def build_context(conn: sqlite3.Connection, session_id: str) -> ContextKernel:
    ts = now()
    recent_rows = recent_signal_rows(conn, session_id, 12)
    claim_rows = active_claim_rows(conn, 64)
    self_state = load_state(conn, "self_state", "assistant_self", default_self_state())
    world_state = load_state(conn, "world_state", "default", default_world_state())

    turn_index = len(recent_rows) + 1
    session_started_at = min([row["created_at"] for row in recent_rows], default=ts)
    last_user_signal_at = recent_rows[0]["created_at"] if recent_rows else None
    recent_clusters = [semantic_cluster_for_text(row["content"]) for row in recent_rows]
    negative_repeat_count = sum(1 for cluster in recent_clusters[:5] if cluster == "negative_evaluation.assistant_competence")
    active_repetition_groups = []
    if negative_repeat_count >= 2:
        active_repetition_groups.append(
            {
                "cluster_key": "negative_evaluation.assistant_competence",
                "count": negative_repeat_count,
                "decay_half_life_ms": 900000,
                "likely_user_state": "frustration_or_mischief",
            }
        )

    user_city = os.getenv("CEMM_USER_CITY", "")
    user_region = os.getenv("CEMM_USER_REGION", "")
    user_country = os.getenv("CEMM_USER_COUNTRY", "")
    user_timezone = os.getenv("CEMM_USER_TIMEZONE", "")

    user = {
        "entity_id": os.getenv("CEMM_USER_ID", "user"),
        "known": True,
        "location": {
            "country": user_country,
            "region": user_region,
            "city": user_city,
            "timezone": user_timezone,
        },
        "affect": {
            "valence": -0.2 if negative_repeat_count else 0.0,
            "arousal": min(1.0, negative_repeat_count * 0.25),
            "frustration": min(1.0, negative_repeat_count * 0.35),
            "hostility": min(1.0, negative_repeat_count * 0.2),
            "playfulness": 0.0,
            "decay_half_life_ms": 900000,
        },
    }

    time_state = {
        "now_unix": ts,
        "bucket": time_bucket(ts),
        "session_elapsed_s": max(0, ts - session_started_at),
        "since_last_user_signal_s": None if last_user_signal_at is None else max(0, ts - last_user_signal_at),
    }

    conversation = {
        "session_id": session_id,
        "turn_index": turn_index,
        "phase": "opening" if turn_index == 1 else "active",
        "recent_signal_ids": [row["id"] for row in recent_rows],
        "active_claim_ids": [row["id"] for row in claim_rows],
        "active_repetition_groups": active_repetition_groups,
        "dynamics": {
            "first_user_signal": turn_index == 1,
            "temporary_affect_state": user["affect"],
        },
    }

    goal = {
        "active_goal_id": None,
        "required_slots": [],
        "missing_slots": [],
        "success_criteria": [],
    }

    memory = {
        "working_signal_ids": [row["id"] for row in recent_rows],
        "candidate_claim_ids": [row["id"] for row in claim_rows],
        "active_frame_ids": world_state.get("active_frame_ids", []),
        "source_trust": {"user": 0.85, "runtime": 0.75, "external_tool": 0.9},
    }

    permission = {
        "scope": "session_private",
        "can_use_user_memory": True,
        "can_write_user_memory": True,
        "can_call_external_tools": False,
    }

    budget = {
        "latency_target_ms": 50,
        "max_entities": 16,
        "max_claims": 64,
        "max_models": 8,
        "max_ranked": 32,
        "max_actions": 2,
        "max_recursive_steps": 0,
        "allow_dense_fallback": False,
        "allow_simulation": False,
    }

    context_id = stable_id(
        "ctx",
        {
            "session_id": session_id,
            "turn_index": turn_index,
            "time_bucket": time_state["bucket"],
            "recent": conversation["recent_signal_ids"],
            "claims": memory["candidate_claim_ids"],
        },
    )
    return ContextKernel(
        id=context_id,
        session_id=session_id,
        world=world_state,
        user=user,
        time=time_state,
        conversation=conversation,
        goal=goal,
        memory=memory,
        self_view=self_state,
        permission=permission,
        budget=budget,
    )


def observe(conn: sqlite3.Connection, content: str, context: ContextKernel) -> str:
    payload = {"content": content, "session_id": context.session_id, "turn_index": context.turn_index}
    signal_id = stable_id("sig", payload | {"ts": now()})
    conn.execute(
        """
        INSERT INTO signals (id, kind, source_type, content, context_json, semantics_json, created_at)
        VALUES (?, 'input', 'user', ?, ?, NULL, ?)
        """,
        (signal_id, content, json.dumps(dataclasses.asdict(context), sort_keys=True), now()),
    )
    conn.commit()
    return signal_id


def infer_context(text: str, context: ContextKernel) -> dict[str, Any]:
    lower = text.lower()
    inferences: list[dict[str, Any]] = []
    is_first_turn = bool(context.conversation["dynamics"]["first_user_signal"])
    user_location = context.user.get("location", {})
    known_location = any(user_location.get(key) for key in ("city", "region", "country"))

    if is_first_turn and re.fullmatch(r"(hi|hello|hey|good morning|morning|good afternoon|good evening)[!. ]*", lower):
        inferences.append({"kind": "session_opening", "value": "greeting", "confidence": 0.95, "decay_half_life_ms": 600000})
    if is_first_turn and len(lower.split()) <= 4 and any(word in lower for word in ["fix", "now", "quick", "urgent"]):
        inferences.append({"kind": "urgency", "value": "possible_hurry", "confidence": 0.45, "decay_half_life_ms": 900000})
    if "weather" in lower and not known_location and not any(place in lower for place in ["lagos", "abuja", "london", "new york", "enugu"]):
        inferences.append({"kind": "missing_slot", "value": "location", "confidence": 0.9, "decay_half_life_ms": 300000})
    if any(term in lower for term in ["president", "latest", "today", "current", "news"]):
        inferences.append(
            {
                "kind": "world_state_requirement",
                "value": "fresh_external_evidence_required",
                "confidence": 0.85,
                "decay_half_life_ms": 300000,
            }
        )

    for group in context.conversation.get("active_repetition_groups", []):
        inferences.append(
            {
                "kind": "repetition",
                "value": group["cluster_key"],
                "confidence": min(0.95, 0.55 + 0.1 * group["count"]),
                "decay_half_life_ms": group["decay_half_life_ms"],
            }
        )

    return {
        "inferences": inferences,
        "needs_clarification": any(i["kind"] == "missing_slot" for i in inferences),
        "stale_world_state": any(i["kind"] == "world_state_requirement" for i in inferences),
        "confidence": max([i["confidence"] for i in inferences], default=0.5),
    }


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
                    "input_state_keys": [],
                    "output_state_keys": ["low_competence"],
                    "modality": "asserted",
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
        atoms.append(
            {
                "kind": "process",
                "frame_key": "state_preference",
                "participants": [{"role": "holder", "entity": "user"}],
                "input_state_keys": [],
                "output_state_keys": ["preference"],
                "modality": "asserted",
                "polarity": "affirmed",
                "intensity": 0.7,
                "confidence": 0.75,
            }
        )
    if "?" in text:
        atoms.append({"kind": "process", "frame_key": "ask_question", "confidence": 0.8})
    return {"uol_atoms": atoms, "semantic_cluster_key": semantic_cluster_for_text(text)}


def build_semantic_event_graph(
    signal_id: str,
    context: ContextKernel,
    semantics: dict[str, Any],
    claim: dict[str, Any] | None,
) -> dict[str, Any]:
    uol = semantics.get("uol", {})
    uol_atoms = uol.get("uol_atoms", [])
    atom_confidences = [float(atom.get("confidence", 0.0) or 0.0) for atom in uol_atoms]
    claim_confidence = float((claim or {}).get("confidence", 0.0) or 0.0)
    context_confidence = float(semantics.get("context", {}).get("confidence", 0.0) or 0.0)
    graph_confidence = min(0.95, max(atom_confidences + [claim_confidence, context_confidence, 0.5]))
    graph = {
        "id": stable_id("seg", {"signal_id": signal_id, "uol": uol_atoms, "claim": claim}),
        "source_signal_ids": [signal_id],
        "context_id": context.id,
        "entity_refs": [atom for atom in uol_atoms if atom.get("kind") == "entity_ref"],
        "processes": [atom for atom in uol_atoms if atom.get("kind") == "process"],
        "states": [atom for atom in uol_atoms if atom.get("kind") == "state"],
        "claim_refs": [],
        "model_refs": [],
        "action_refs": [],
        "temporal_edges": [],
        "causal_edges": [],
        "permission_scope": context.permission["scope"],
        "confidence": graph_confidence,
        "version": "cemm.semantic_event_graph.v1",
    }
    if claim:
        graph["claim_candidate"] = claim
    return graph


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
        """
        SELECT * FROM claims
        WHERE subject = 'user' AND predicate = ? AND status = 'active'
        ORDER BY confidence DESC, updated_at DESC LIMIT 1
        """,
        (predicate,),
    ).fetchone()
    return row


def selected_claims(conn: sqlite3.Connection, claim_ids: list[str]) -> list[dict[str, Any]]:
    if not claim_ids:
        return []
    rows = conn.execute(
        f"SELECT * FROM claims WHERE id IN ({','.join('?' for _ in claim_ids)})",
        claim_ids,
    ).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def find_recall_predicate(text: str) -> str | None:
    lower = text.lower()
    match = re.search(r"(what is|what's|whats) my favorite ([a-z _-]+)", lower)
    if match:
        field = re.sub(r"[^a-z0-9]+", "_", match.group(2)).strip("_?")
        return f"favorite_{field}"
    return None


def route(conn: sqlite3.Connection, text: str, context: ContextKernel, context_info: dict[str, Any]) -> RouteDecision:
    lower = text.lower().strip()
    inferences = context_info.get("inferences", [])

    if any(i.get("kind") == "missing_slot" for i in inferences):
        context.goal["required_slots"] = ["location"]
        context.goal["missing_slots"] = ["location"]
        return RouteDecision("ask", 0.9, "context kernel missing required world/location slot", [], ["location"], ["location"])

    if any(i.get("kind") == "world_state_requirement" for i in inferences) and not context.permission.get("can_call_external_tools"):
        return RouteDecision("abstain", 0.78, "fresh world state required but external tools are not permitted", [], [], [])

    if context.conversation["phase"] == "opening" and re.fullmatch(
        r"(hi|hello|hey|good morning|morning|good afternoon|good evening)[!. ]*", lower
    ):
        return RouteDecision("answer", 0.95, "session greeting from conversation state", [], [], [])

    claim = extract_claim(text)
    if claim and context.permission.get("can_write_user_memory"):
        return RouteDecision("remember", claim["confidence"], "user stated a rememberable claim", [], [], [])

    predicate = find_recall_predicate(text)
    if predicate and context.permission.get("can_use_user_memory"):
        row = retrieve_claim(conn, predicate)
        if row:
            return RouteDecision("answer", float(row["confidence"]), "recall selected claim from memory state", [row["id"]], [], [])
        return RouteDecision("ask", 0.6, "requested memory not found", [], [], [])

    if semantic_cluster_for_text(text) == "negative_evaluation.assistant_competence":
        affect = context.user.get("affect", {})
        confidence = 0.7 + min(0.2, float(affect.get("frustration", 0.0)) * 0.2)
        return RouteDecision("answer", confidence, "pragmatic negative evaluation grounded in user affect state", [], [], [])

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
            return "Which location should I use?", {"strategy": "template", "verified": True, "verification_type": "hard"}
        return "Can you clarify that?", {"strategy": "template", "verified": True, "verification_type": "hard"}

    if decision.action_kind == "remember":
        return "Got it.", {"strategy": "template", "verified": True, "verification_type": "hard"}

    if decision.action_kind == "abstain":
        if "fresh world state" in decision.reason:
            return (
                "I need fresh world context for that, and this runtime has external tools disabled.",
                {"strategy": "template", "verified": True, "verification_type": "hard"},
            )
        return (
            "I don't have enough grounded context to answer that yet.",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if decision.selected_claim_ids:
        claim_id = decision.selected_claim_ids[0]
        row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if row:
            readable = row["predicate"].replace("_", " ")
            return (
                f"Your {readable} is {row['object_value']}.",
                {"strategy": "template", "verified": True, "verification_type": "hard", "claim_id": claim_id},
            )

    lower = text.lower().strip()
    if re.fullmatch(r"(hi|hello|hey|good morning|morning|good afternoon|good evening)[!. ]*", lower):
        if "morning" in lower:
            return "Good morning.", {"strategy": "template", "verified": True, "verification_type": "hard"}
        return "Hello.", {"strategy": "template", "verified": True, "verification_type": "hard"}

    if semantic_cluster_for_text(text) == "negative_evaluation.assistant_competence":
        affect = context.user.get("affect", {})
        if float(affect.get("frustration", 0.0)) > 0.4:
            return (
                "I hear the repeated frustration. I should identify the failure and correct it directly.",
                {"strategy": "template", "verified": True, "verification_type": "hard"},
            )
        return (
            "I hear the frustration. Let me focus on fixing the part that failed.",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    return "I am here.", {"strategy": "template", "verified": True, "verification_type": "hard"}


def compose_semantic_answer_graph(
    conn: sqlite3.Connection,
    signal_id: str,
    context: ContextKernel,
    decision: RouteDecision,
    semantic_event_graph: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    claims = selected_claims(conn, decision.selected_claim_ids)
    return {
        "id": stable_id(
            "sag",
            {
                "signal_id": signal_id,
                "decision": dataclasses.asdict(decision),
                "selected_claim_ids": decision.selected_claim_ids,
            },
        ),
        "intent": decision.action_kind,
        "source_signal_ids": [signal_id],
        "context_id": context.id,
        "selected_claim_ids": decision.selected_claim_ids,
        "selected_model_ids": [],
        "entity_refs": semantic_event_graph.get("entity_refs", []),
        "processes": semantic_event_graph.get("processes", []),
        "states": semantic_event_graph.get("states", []),
        "causal_edges": semantic_event_graph.get("causal_edges", []),
        "temporal_edges": semantic_event_graph.get("temporal_edges", []),
        "action_candidates": [dataclasses.asdict(decision)],
        "selected_claims": claims,
        "confidence": decision.confidence,
        "uncertainty_reasons": [] if decision.confidence >= 0.75 else [decision.reason],
        "permission_scope": context.permission["scope"],
        "verification": {
            "supported": bool(verification.get("verified", False)),
            "verification_type": verification.get("verification_type", "none"),
            "confidence": decision.confidence,
        },
        "version": "cemm.semantic_answer_graph.v1",
    }


def update_self_after_turn(
    conn: sqlite3.Connection,
    context: ContextKernel,
    decision: RouteDecision,
    stored_claim_id: str | None,
    trace_id: str,
) -> None:
    state = context.self_view
    internal = state.setdefault("internal", {})
    epistemic = state.setdefault("epistemic", {})
    meta_memory = state.setdefault("meta_memory", {})
    historical = state.setdefault("historical_arc", {})

    internal["mode"] = "assistant"
    internal["uncertainty"] = round(max(0.0, 1.0 - decision.confidence), 4)
    internal["load"] = min(1.0, context.turn_index / 100.0)
    internal["last_action"] = decision.action_kind
    internal["last_error"] = decision.reason if decision.action_kind == "abstain" else None

    historical["turn_count"] = int(historical.get("turn_count", 0)) + 1
    recent_trace_ids = list(historical.get("recent_trace_ids", []))
    recent_trace_ids.insert(0, trace_id)
    historical["recent_trace_ids"] = recent_trace_ids[:16]

    if stored_claim_id:
        meta_memory["stored_claim_count"] = int(meta_memory.get("stored_claim_count", 0)) + 1
        meta_memory["last_memory_write_signal_id"] = stored_claim_id
    if decision.selected_claim_ids:
        meta_memory["last_recalled_claim_ids"] = decision.selected_claim_ids
    if decision.confidence < 0.65:
        epistemic["recent_low_confidence_count"] = int(epistemic.get("recent_low_confidence_count", 0)) + 1
    if decision.action_kind == "abstain":
        epistemic["unsupported_query_count"] = int(epistemic.get("unsupported_query_count", 0)) + 1

    save_state(conn, "self_state", "assistant_self", state)


def write_action_trace(
    conn: sqlite3.Connection,
    signal_id: str,
    context: ContextKernel,
    decision: RouteDecision,
    response: str,
    semantics: dict[str, Any],
    semantic_event_graph: dict[str, Any],
    semantic_answer_graph: dict[str, Any],
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
        "context_id": context.id,
        "context_kernel": dataclasses.asdict(context),
        "action_kind": decision.action_kind,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "required_slots": decision.required_slots,
        "missing_slots": decision.missing_slots,
        "selected_claim_ids": decision.selected_claim_ids,
        "selected_claims": selected_claims(conn, decision.selected_claim_ids),
        "semantics": semantics,
        "semantic_event_graph": semantic_event_graph,
        "semantic_answer_graph": semantic_answer_graph,
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
    claim_candidate = extract_claim(normalized)
    semantic_event_graph = build_semantic_event_graph(signal_id, context, semantics, claim_candidate)
    conn.execute("UPDATE signals SET semantics_json = ? WHERE id = ?", (json.dumps(semantics, sort_keys=True), signal_id))
    conn.commit()

    decision = route(conn, normalized, context, context_info)
    stored_claim_id = None
    if decision.action_kind == "remember":
        if claim_candidate:
            stored_claim_id = save_claim(conn, signal_id, claim_candidate)
            semantic_event_graph["claim_refs"].append(stored_claim_id)

    response, verification = synthesize(conn, decision, normalized, context)
    semantic_answer_graph = compose_semantic_answer_graph(conn, signal_id, context, decision, semantic_event_graph, verification)
    trace_id = write_action_trace(
        conn,
        signal_id,
        context,
        decision,
        response,
        semantics,
        semantic_event_graph,
        semantic_answer_graph,
        verification,
    )
    update_self_after_turn(conn, context, decision, stored_claim_id, trace_id)
    return {
        "response": response,
        "signal_id": signal_id,
        "trace_id": trace_id,
        "context_id": context.id,
        "action": dataclasses.asdict(decision),
        "stored_claim_id": stored_claim_id,
    }


def runtime_training_examples(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT s.id AS signal_id, s.content, s.context_json, s.semantics_json,
               t.id AS trace_id, t.trace_json
        FROM signals s
        LEFT JOIN traces t ON t.signal_id = s.id
        WHERE s.kind = 'input'
        ORDER BY s.created_at ASC
        """
    ).fetchall()
    examples: list[dict[str, Any]] = []
    for row in rows:
        context = parse_json(row["context_json"], {})
        semantics = parse_json(row["semantics_json"], {})
        trace = parse_json(row["trace_json"], {}) if row["trace_json"] else {}
        payload_base = {
            "signal_id": row["signal_id"],
            "trace_id": row["trace_id"],
            "text": row["content"],
            "context_kernel": context,
            "semantics": semantics,
            "semantic_event_graph": trace.get("semantic_event_graph"),
            "semantic_answer_graph": trace.get("semantic_answer_graph"),
            "trace": trace,
        }
        permission_scope = context.get("permission", {}).get("scope", "session_private")
        examples.append({"task_type": "semantic_graph_extraction", "permission_scope": permission_scope, "payload": payload_base})
        examples.append({"task_type": "semantic_latent_target", "permission_scope": permission_scope, "payload": payload_base})
        examples.append({"task_type": "context_inference", "permission_scope": permission_scope, "payload": payload_base})
        examples.append({"task_type": "uol_mapping", "permission_scope": permission_scope, "payload": payload_base})
        examples.append({"task_type": "operator_selection", "permission_scope": permission_scope, "payload": payload_base})
        examples.append({"task_type": "semantic_answer_composition", "permission_scope": permission_scope, "payload": payload_base})

        cluster = semantics.get("uol", {}).get("semantic_cluster_key") or semantic_cluster_for_text(row["content"])
        if cluster in {"preference_statement"}:
            examples.append({"task_type": "claim_extraction", "permission_scope": permission_scope, "payload": payload_base})
            examples.append({"task_type": "predicate_mapping", "permission_scope": permission_scope, "payload": payload_base})
        if cluster == "negative_evaluation.assistant_competence":
            examples.append({"task_type": "pragmatic_interpretation", "permission_scope": permission_scope, "payload": payload_base})
        if trace.get("response"):
            examples.append(
                {
                    "task_type": "synthesis_verification",
                    "permission_scope": permission_scope,
                    "payload": {
                        **payload_base,
                        "answer": trace["response"],
                        "selected_claims": trace.get("selected_claims", []),
                        "semantic_answer_graph": trace.get("semantic_answer_graph"),
                        "verification": trace.get("synthesis", {}),
                    },
                }
            )
            examples.append(
                {
                    "task_type": "semantic_text_realization",
                    "permission_scope": permission_scope,
                    "payload": {
                        **payload_base,
                        "answer": trace["response"],
                        "semantic_answer_graph": trace.get("semantic_answer_graph"),
                    },
                }
            )
            examples.append({"task_type": "self_state_update", "permission_scope": permission_scope, "payload": payload_base})
        if context.get("conversation", {}).get("recent_signal_ids"):
            examples.append({"task_type": "next_event_prediction", "permission_scope": permission_scope, "payload": payload_base})
    return examples


def export_training(conn: sqlite3.Connection, out_path: Path) -> int:
    examples = runtime_training_examples(conn)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example, sort_keys=True) + "\n")
    return len(examples)


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
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"runtime LLM call failed: {last_error}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CEMM context-grounded runtime router")
    parser.add_argument("--db", default="cemm_runtime.sqlite3")
    parser.add_argument("--session-id", default="default")
    sub = parser.add_subparsers(dest="cmd", required=True)

    once = sub.add_parser("once", help="handle one user turn")
    once.add_argument("text")
    once.add_argument("--json", action="store_true")

    chat = sub.add_parser("chat", help="interactive chat")
    chat.add_argument("--dry-run", action="store_true")

    show_context = sub.add_parser("show-context", help="print the current ContextKernel")
    show_context.add_argument("--json", action="store_true")

    export = sub.add_parser("export-training", help="export runtime traces as trainer JSONL")
    export.add_argument("--out", required=True)

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

    if args.cmd == "show-context":
        context = build_context(conn, args.session_id)
        if args.json:
            print(json.dumps(dataclasses.asdict(context), indent=2, sort_keys=True))
        else:
            print(f"context_id={context.id} turn={context.turn_index} bucket={context.time_bucket} budget_ms={context.budget_ms}")
        return 0

    if args.cmd == "export-training":
        count = export_training(conn, Path(args.out))
        print(f"exported {count} examples to {args.out}")
        return 0

    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
