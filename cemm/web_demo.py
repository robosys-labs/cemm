"""CEMM v1 single-user development web surface."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from cemm.config import Config
from cemm.runtime import MODE_NORMAL, MODE_READ_ONLY, MODE_REVIEWED_TEACH, Runtime
from cemm.store import Store
from cemm.acquisition import acquire_reviewed

_WEB_DIR = Path(__file__).parent / "web"
app = FastAPI(title="CEMM v1 Web Demo", version="1.0.0")
_runtime: Runtime | None = None
_store: Store | None = None
_config: Config | None = None
_db_path = ":memory:"
_pack_path = ""
_data_files: list[str] = []


def _ensure_runtime() -> Runtime:
    global _runtime, _store, _config
    if _runtime is None:
        _store = Store(_db_path)
        # Bootstrap only a genuinely empty final-v1 store. Reopening a durable
        # database must not append duplicate import generations.
        empty = not _store.db.execute("SELECT 1 FROM atoms LIMIT 1").fetchone()
        if empty:
            for path in _data_files:
                _store.import_data(path)
        _config = Config()
        _runtime = Runtime(_store, _pack_path, _config)
    return _runtime


class ChatRequest(BaseModel):
    text: str
    mode: str = Field(default=MODE_NORMAL, pattern="^(normal|read_only|reviewed_teach)$")


class ChatResponse(BaseModel):
    status: str
    response: str
    response_csir: dict[str, Any] | None = None
    query_result: dict[str, Any] | None = None
    frontier_graph: dict[str, Any] | None = None
    capability_assessments: list[dict[str, Any]] = Field(default_factory=list)
    stage_trace: dict[str, Any] | None = None
    realization_proof: dict[str, Any] | None = None


class AcquisitionMention(BaseModel):
    surface: str
    kind: str = "concept"
    ref: str | None = None
    preferred: bool = True


class AcquisitionRequest(BaseModel):
    mentions: list[AcquisitionMention]
    text: str = ""
    teach_rule: bool = False


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((_WEB_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    runtime = _ensure_runtime()
    return {
        "ok": True,
        "version": "1.0.0",
        "authority_generation": runtime.runtime_attestation["authority_generation"],
        "authority_hash": runtime.runtime_attestation["authority_generation_hash"][:16],
        "revisions": runtime.s.revisions(),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    text = request.text.strip()
    if not text:
        return ChatResponse(status="error", response="Empty input.")
    result = _ensure_runtime().process(text, mode=request.mode)
    return ChatResponse(
        status=result["status"],
        response=result.get("response", "") or "",
        response_csir=result.get("response_csir"),
        query_result=result.get("query_result"),
        frontier_graph=result.get("frontier_graph"),
        capability_assessments=result.get("capability_assessments", []),
        stage_trace=result.get("stage_trace"),
        realization_proof=result.get("realization_proof"),
    )


@app.post("/api/reload")
async def reload():
    return {"ok": True, **_ensure_runtime().reload_authority()}


@app.post("/api/acquire")
async def acquire(request: AcquisitionRequest):
    """Reviewed lexical acquisition: admit new concepts with explicit kinds.

    This is the architecturally correct way to teach the system new words.
    Normal conversation intentionally cannot admit concepts (no concept
    fallback). The reviewer must specify the semantic kind explicitly.
    """
    runtime = _ensure_runtime()
    document = {
        "document_ref": f"web-acquire:{request.mentions[0].surface}",
        "mentions": [
            {
                "surface": m.surface,
                "kind": m.kind,
                "ref": m.ref,
                "preferred": m.preferred,
            }
            for m in request.mentions
        ],
        "text": request.text,
        "teach_rule": request.teach_rule,
    }
    try:
        result = acquire_reviewed(runtime.s, runtime, document)
        return result
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}


@app.get("/api/inspect")
async def inspect():
    store = _ensure_runtime().s
    tables = (
        "atoms", "applications", "claims", "rules", "frontiers",
        "commit_receipts", "common_ground", "effect_journal",
    )
    return {
        "generation": store.generation,
        "revisions": store.revisions(),
        "table_counts": {
            table: store.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in tables
        },
    }


def main():
    global _db_path, _pack_path, _data_files
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=":memory:")
    parser.add_argument("--pack")
    parser.add_argument("--data", action="append", default=[])
    args = parser.parse_args()
    package = Path(__file__).parent
    _db_path = args.db
    _pack_path = args.pack or str(package / "language_packs" / "en.json")
    # Final v1 authority is canonical base.json; family_knowledge.json contains
    # pre-final atoms (rel:state_dimension, etc.) that the final schema rejects.
    _data_files = args.data or [str(package / "data" / "base.json")]
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
