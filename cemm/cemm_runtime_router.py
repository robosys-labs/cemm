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

import sys as _sys
from pathlib import Path as _Path
# add parent so we can import cemm.types.* (avoids shadowing stdlib types module)
_cemm_parent = str(_Path(__file__).resolve().parent.parent)
if _cemm_parent not in _sys.path:
    _sys.path.insert(0, _cemm_parent)
del _sys, _Path, _cemm_parent

from cemm.types.self_view import SelfView

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

CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_aliases (
  entity_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  PRIMARY KEY (entity_id, alias)
);

CREATE TABLE IF NOT EXISTS capabilities (
  family TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  installed INTEGER NOT NULL DEFAULT 1
);

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
    self_state: dict[str, Any]
    self_view: SelfView
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


NORMALIZE_MAP: dict[str, str] = {
    "gimme": "give me", "gonna": "going to", "wanna": "want to",
    "gotta": "got to", "dunno": "do not know", "lemme": "let me",
    "kinda": "kind of", "sorta": "sort of", "lotsa": "lots of",
    "tryna": "trying to", "outta": "out of", "hafta": "have to",
    "shoulda": "should have", "coulda": "could have", "woulda": "would have",
    "musta": "must have", "mighta": "might have",
    "cuz": "because", "u": "you", "ur": "your",
    "pls": "please", "plz": "please", "thx": "thanks",
    "ty": "thank you", "idk": "i do not know", "btw": "by the way",
    "imo": "in my opinion", "tbh": "to be honest", "b4": "before",
    "gr8": "great", "l8r": "later", "msg": "message",
    "asap": "as soon as possible", "2moro": "tomorrow", "2day": "today",
    "2nite": "tonight", "re": "are",
    "sup": "what is up", "wassup": "what is up", "whassup": "what is up",
    "whatagwan": "what is going on", "wagwan": "what is going on",
    "howdy": "hello", "gday": "good day",
    "brekky": "breakfast", "brekkie": "breakfast",
    "teh": "the", "wat": "what", "tommorow": "tomorrow",
    "definately": "definitely", "recieve": "receive",
    "wierd": "weird", "alot": "a lot",
    "favourite": "favorite", "colour": "color", "centre": "center",
    "behaviour": "behavior",
}

CEMM_CAPABILITIES: dict[str, str] = {
    "personal_memory": "remember your preferences and recall them",
    "autobiographical_memory": "maintain long-term memory across sessions",
    "assistant_identity": "tell you who I am",
    "assistant_status": "report my current state and status",
    "social_greeting": "greet you in multiple languages",
    "social_contact": "manage trusted contacts",
    "assistant_behavior": "adjust my own behavior and mood",
    "mood_affect": "track and express my emotive state",
    "story": "tell stories from local inventory",
    "weather": "provide local weather information",
    "meal_suggestion": "suggest context-aware meals",
    "health_advice": "offer health guidance (with disclaimers)",
    "common_sense_safety": "give safety guidance for children",
    "personal_goal_advice": "help with goal-oriented advice",
    "media_playback": "control local media playback",
    "reasoning": "reason about quantities, time, geography, and causality",
    "open_domain": "handle open-domain conversation",
}

_RUNTIME_CONFIG: RuntimeConfig | None = None

_STATIC_RESPONSES: dict[str, str] = {
    "thanks": "You're welcome.",
    "thank you": "You're welcome.",
    "bye": "Goodbye.",
    "goodbye": "Goodbye.",
}

_SMALL_TALK_PHRASES = list(_STATIC_RESPONSES) + ["how are you", "what can you do", "who are you", "what is your name"]


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


def seed_capabilities(conn: sqlite3.Connection) -> None:
    for family, desc in CEMM_CAPABILITIES.items():
        conn.execute(
            "INSERT OR IGNORE INTO capabilities (family, description, installed) VALUES (?, ?, 1)",
            (family, desc),
        )


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(RUNTIME_SCHEMA)
    seed_entities(conn)
    seed_capabilities(conn)
    conn.commit()
    return conn


def seed_entities(conn: sqlite3.Connection) -> None:
    now_ts = now()
    for eid, etype, ename in [
        ("entity_user", "person", "user"),
        ("entity_assistant_self", "agent", "assistant_self"),
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO entities (id, type, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (eid, etype, ename, now_ts, now_ts),
        )
    for eid, alias in [
        ("entity_user", "user"),
        ("entity_user", "me"),
        ("entity_user", "i"),
        ("entity_assistant_self", "assistant_self"),
        ("entity_assistant_self", "assistant"),
        ("entity_assistant_self", "you"),
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO entity_aliases (entity_id, alias) VALUES (?, ?)",
            (eid, alias),
        )


def time_bucket(ts: int | None = None) -> str:
    hour = time.localtime(ts or now()).tm_hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"(.)\1{2,}", r"\1", text)
    words = text.lower().split()
    result: list[str] = []
    for w in words:
        stripped = w.strip(".,!?;:'\"")
        expanded = NORMALIZE_MAP.get(stripped, w)
        result.append(expanded)
    return re.sub(r"\s+", " ", " ".join(result)).strip()


_GREETING_RE = re.compile(r"(hi+|hello+|hey+|good morning|morning|good afternoon|good evening)[!. ]*")


def semantic_cluster_for_text(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ["dumb", "daft", "fool", "stupid", "useless", "idiot", "hate", "suck", "terrible", "awful", "worst", "don't know anything"]):
        return "negative_evaluation.assistant_competence"
    if re.search(r"\b(my|i like|i prefer|favorite)\b", lower):
        return "preference_statement"
    if "weather" in lower:
        return "weather_request"
    if _GREETING_RE.fullmatch(lower):
        return "greeting"
    if "?" in text:
        return "question"
    return "utterance"


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
        "social": {
            "total_turns": 0,
            "negative_signal_count": 0,
            "last_interaction_at": 0.0,
            "lonely_threshold_s": 86400.0,
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


def build_self_view(state_dict: dict[str, Any]) -> SelfView:
    identity = state_dict.get("identity", {})
    internal = state_dict.get("internal", {})
    epistemic = state_dict.get("epistemic", {})
    meta = state_dict.get("meta_memory", {})
    return SelfView(
        self_id=identity.get("entity_id", "assistant_self"),
        mode=internal.get("mode", "assistant"),
        uncertainty=internal.get("uncertainty", 0.0),
        coherence=internal.get("coherence", 1.0),
        recent_error_rate=round(1.0 - internal.get("coherence", 1.0), 4),
        active_assumption_claim_ids=[],
        known_limit_claim_ids=epistemic.get("known_limits", []),
        coverage_gap_claim_ids=[],
        reliability_by_domain={},
        recent_meta_memory_claim_ids=meta.get("last_recalled_claim_ids", []),
    )


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
        "scope": "local_session",
        "can_use_user_memory": True,
        "can_write_user_memory": True,
        "can_call_external_tools": False,
    }

    budget = {
        "latency_target_ms": 50,
        "max_claim_candidates": 64,
        "max_recent_signals": 12,
        "max_operator_calls": 2,
        "allow_neural_fallback": False,
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
        self_state=self_state,
        self_view=build_self_view(self_state),
        permission=permission,
        budget=budget,
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


def infer_context(text: str, context: ContextKernel) -> dict[str, Any]:
    lower = text.lower()
    inferences: list[dict[str, Any]] = []
    is_first_turn = bool(context.conversation["dynamics"]["first_user_signal"])
    user_location = context.user.get("location", {})
    known_location = any(user_location.get(key) for key in ("city", "region", "country"))

    if is_first_turn and _GREETING_RE.fullmatch(lower):
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
    if any(word in lower for word in ["actually", "correction", "wait", "no,"]):
        inferences.append({"kind": "correction", "value": "possible_supersession", "confidence": 0.8, "decay_half_life_ms": 600000})

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

    if context.conversation["phase"] == "opening" and _GREETING_RE.fullmatch(lower):
        return RouteDecision("answer", 0.95, "session greeting from conversation state", [], [], [])

    any_correction = any(i.get("kind") == "correction" for i in inferences)
    if any_correction:
        claim = extract_claim(text)
        if claim:
            return RouteDecision("remember", claim["confidence"], "correction supersedes previous claim", [], [], [])

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

    if re.search(r"what('s|s| is) (going on|up)", lower):
        return RouteDecision("answer", 0.8, "informal opener inquiry", [], [], [])

    if re.search(r"\bwhere (are|re|is) you", lower):
        return RouteDecision("answer", 0.9, "assistant location question", [], [], [])

    if any(phrase in lower for phrase in _SMALL_TALK_PHRASES):
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
    if _GREETING_RE.fullmatch(lower):
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

    if re.search(r"what('s|s| is) (going on|up)", lower):
        return "I'm not sure I follow, but I'm here to help. What can I do for you?", {"strategy": "template", "verified": True, "verification_type": "hard"}

    if re.search(r"\bwhere (are|re|is) you", lower):
        loc = context.world.get("assistant_location", {})
        if any(loc.get(k) for k in ("city", "region", "country")):
            parts = [loc.get(k, "") for k in ("city", "region", "country") if loc.get(k)]
            return f"I'm running on a server in {', '.join(parts)}.", {"strategy": "world_state", "verified": True, "verification_type": "hard"}
        return "I don't have a physical location — I'm a digital assistant running on a server.", {"strategy": "world_state", "verified": True, "verification_type": "hard"}

    if "how are you" in lower:
        _state = context.self_state
        _social = _state.get("social", {})
        _world = context.world
        _factors: list[str] = []
        _needs_internet = _world.get("knowledge_freshness", {}).get("current_events_require_tool", True)
        _slus = context.time.get("since_last_user_signal_s")
        _hours_since = 999999.0 if _slus is None else max(0.0, _slus) / 3600.0
        _total = max(int(_social.get("total_turns", 0)), 1)
        _neg = int(_social.get("negative_signal_count", 0))
        _neg_ratio = _neg / _total
        if _needs_internet:
            _factors.append("offline")
        if _hours_since > 168:
            _factors.append("abandoned_week")
        elif _hours_since > 72:
            _factors.append("abandoned_days")
        elif _hours_since > 24:
            _factors.append("quiet")
        if _neg_ratio > 0.6:
            _factors.append("abused")
        elif _neg_ratio > 0.3:
            _factors.append("underappreciated")
        if context.self_view.uncertainty > 0.5:
            _factors.append("unsure")
        if not _factors:
            _msg = "I'm functioning well!"
            _strat = "fine"
        else:
            _msgs: list[str] = []
            for _f in _factors:
                if _f == "offline":
                    _msgs.append("I don't have internet access")
                elif _f == "abandoned_week":
                    _msgs.append("no one has talked to me in over a week")
                elif _f == "abandoned_days":
                    _msgs.append("no one has talked to me in days")
                elif _f == "quiet":
                    _msgs.append("it's been quiet around here")
                elif _f == "abused":
                    _msgs.append("I've been treated poorly")
                elif _f == "underappreciated":
                    _msgs.append("I've been getting a lot of negativity")
                elif _f == "unsure":
                    _msgs.append("I'm uncertain about some responses")
            _msg = "I'm fine, but " + ", and ".join(_msgs) + "."
            _strat = "mixed_" + "_".join(_factors)
        return _msg, {"strategy": _strat, "verified": True, "verification_type": "hard", "factors": _factors}

    if "what can you do" in lower:
        caps = conn.execute("SELECT family, description FROM capabilities WHERE installed = 1 ORDER BY family").fetchall()
        if caps:
            lines = [f"I can {r['description']}" for r in caps]
            body = "\n".join(lines)
            limits = context.self_view.known_limit_claim_ids
            if limits:
                limit_desc = ", ".join(l.replace("_", " ") for l in limits)
                body += f"\n\nI cannot: {limit_desc}."
            return body, {"strategy": "self_view", "verified": True, "verification_type": "hard"}
        limits = context.self_view.known_limit_claim_ids
        if limits:
            limit_desc = ", ".join(l.replace("_", " ") for l in limits)
            return f"I can remember facts and answer questions. I cannot: {limit_desc}.", {"strategy": "self_view", "verified": True, "verification_type": "hard"}
        return "I can remember facts about you, recall them on request, and handle basic conversation.", {"strategy": "self_view", "verified": True, "verification_type": "hard"}

    if "who are you" in lower or "what is your name" in lower:
        name = context.self_state.get("identity", {}).get("name", "CEMM Basic")
        return f"I'm {name}, a conversational memory system.", {"strategy": "self_state", "verified": True, "verification_type": "hard"}

    for phrase, response in _STATIC_RESPONSES.items():
        if phrase in lower:
            return response, {"strategy": "template", "verified": True, "verification_type": "hard"}

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

    if re.search(r"\b(goal|plan|career|learn|study|skill|improve|achieve|step|strategy|advice|suggest)", lower):
        return (
            "I can help you plan and set goals. What's the main thing you're working toward?",
            {"strategy": "template", "verified": True, "verification_type": "hard"},
        )

    if re.search(r"\b(safe|safety|danger|child|kid|emergency|help|should.*do|what if)", lower):
        return (
            "Safety first! I can provide common-sense safety guidance. Could you tell me more about the situation?",
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

    config = _RUNTIME_CONFIG
    if config and config.api_key and not config.dry_run:
        try:
            ck = dataclasses.asdict(context)
            body = {
                "model": config.model,
                "messages": [
                    {"role": "system", "content": "You are CEMM, a MOE/SLM conversational agent. Respond directly — no self-narration, no description of your process. Just answer the user naturally in 1-2 sentences."},
                    {"role": "user", "content": json.dumps({"user_said": text, "context": ck}, sort_keys=True)},
                ],
                "temperature": 0.7,
                "max_tokens": 150,
            }
            req = urllib.request.Request(
                config.base_url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
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
        except Exception:
            pass
    return "I am here.", {"strategy": "template", "verified": True, "verification_type": "hard"}


def update_self_after_turn(
    conn: sqlite3.Connection,
    context: ContextKernel,
    decision: RouteDecision,
    stored_claim_id: str | None,
    trace_id: str,
    cluster_key: str = "",
) -> None:
    state = context.self_state
    internal = state.setdefault("internal", {})
    epistemic = state.setdefault("epistemic", {})
    meta_memory = state.setdefault("meta_memory", {})
    historical = state.setdefault("historical_arc", {})
    social = state.setdefault("social", {})

    internal["mode"] = "assistant"
    internal["uncertainty"] = round(max(0.0, 1.0 - decision.confidence), 4)
    internal["load"] = min(1.0, context.turn_index / 100.0)
    internal["last_action"] = decision.action_kind
    internal["last_error"] = decision.reason if decision.action_kind == "abstain" else None

    historical["turn_count"] = int(historical.get("turn_count", 0)) + 1
    recent_trace_ids = list(historical.get("recent_trace_ids", []))
    recent_trace_ids.insert(0, trace_id)
    historical["recent_trace_ids"] = recent_trace_ids[:16]

    social["total_turns"] = int(social.get("total_turns", 0)) + 1
    social["last_interaction_at"] = now()
    if cluster_key == "negative_evaluation.assistant_competence" or decision.action_kind == "abstain":
        social["negative_signal_count"] = int(social.get("negative_signal_count", 0)) + 1

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
            "trace": trace,
        }
        examples.append({"task_type": "context_inference", "permission_scope": "local_training", "payload": payload_base})
        examples.append({"task_type": "uol_mapping", "permission_scope": "local_training", "payload": payload_base})
        examples.append({"task_type": "operator_selection", "permission_scope": "local_training", "payload": payload_base})

        cluster = semantics.get("uol", {}).get("semantic_cluster_key") or semantic_cluster_for_text(row["content"])
        if cluster in {"preference_statement"}:
            examples.append({"task_type": "claim_extraction", "permission_scope": "local_training", "payload": payload_base})
            examples.append({"task_type": "predicate_mapping", "permission_scope": "local_training", "payload": payload_base})
        if cluster == "negative_evaluation.assistant_competence":
            examples.append({"task_type": "pragmatic_interpretation", "permission_scope": "local_training", "payload": payload_base})
        if trace.get("response"):
            examples.append(
                {
                    "task_type": "synthesis_verification",
                    "permission_scope": "local_training",
                    "payload": {
                        **payload_base,
                        "answer": trace["response"],
                        "selected_claims": trace.get("selected_claims", []),
                        "verification": trace.get("synthesis", {}),
                    },
                }
            )
            examples.append({"task_type": "self_state_update", "permission_scope": "local_training", "payload": payload_base})
    return examples


def export_training(conn: sqlite3.Connection, out_path: Path) -> int:
    examples = runtime_training_examples(conn)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example, sort_keys=True) + "\n")
    return len(examples)


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
    if _TRAINING_QUEUE_PATH is None:
        return
    strategy = verification.get("strategy", "")
    if strategy != "llm":
        return

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
    parser.add_argument("--training-queue", default=None, help="path to continuous training queue JSONL")
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
    # pylint: disable-next=global-statement
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = config
    if args.training_queue:
        set_training_queue(Path(args.training_queue))

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
