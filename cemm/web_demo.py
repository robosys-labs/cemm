"""CEMM v1 single-user development web surface."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from cemm.acquisition import acquire_reviewed
from cemm.activation import activation_attestation, assert_native_semantic_activation
from cemm.config import Config
from cemm.runtime import MODE_NORMAL, MODE_READ_ONLY, MODE_REVIEWED_TEACH, Runtime
from cemm.store import Store

_WEB_DIR = Path(__file__).parent / "web"
app = FastAPI(title="CEMM v1 Web Demo", version="1.2.0")
_runtime: Runtime | None = None
_store: Store | None = None
_config: Config | None = None
_activation: dict[str, Any] | None = None
_db_path = ":memory:"
_pack_path = ""
_data_files: list[str] = []


def _ensure_runtime() -> Runtime:
    global _runtime, _store, _config, _activation
    if _runtime is None:
        _store = Store(_db_path)
        empty = not _store.db.execute("SELECT 1 FROM atoms LIMIT 1").fetchone()
        if empty:
            # All authority documents are one graph. Link and validate the
            # complete bundle before the first durable write.
            _store.import_bundle(_data_files)
        _config = Config()
        _runtime = Runtime(_store, _pack_path, _config)
        # Fail before serving chat when an old installed package, stale process,
        # or mismatched form pack is shadowing the checked-out recursive semantic source.
        _activation = assert_native_semantic_activation(_runtime.i.form_pack, _runtime.s)
    return _runtime


class ChatRequest(BaseModel):
    text: str
    mode: str = Field(
        default=MODE_NORMAL, pattern="^(normal|read_only|reviewed_teach)$"
    )


class ChatResponse(BaseModel):
    status: str
    response: str
    response_csir: dict[str, Any] | None = None
    query_result: dict[str, Any] | None = None
    frontier_graph: dict[str, Any] | None = None
    capability_assessments: list[dict[str, Any]] = Field(default_factory=list)
    stage_trace: dict[str, Any] | None = None
    realization_proof: dict[str, Any] | None = None
    activation_ref: str | None = None


class AcquisitionMention(BaseModel):
    surface: str
    # No unknown-form-to-concept default. A reviewer must state identity kind.
    kind: str
    ref: str | None = None
    label_type: str = "label:lexical"
    preferred: bool = True


class AcquisitionRequest(BaseModel):
    mentions: list[AcquisitionMention]
    text: str = ""
    teach_rule: bool = False
    language: str | None = None


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((_WEB_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    runtime = _ensure_runtime()
    attestation = dict(_activation or activation_attestation(runtime.i.form_pack, runtime.s))
    return {
        "ok": bool(attestation.get("ok")),
        "version": "1.2.0",
        "authority_generation": runtime.runtime_attestation["authority_generation"],
        "authority_hash": runtime.runtime_attestation["authority_generation_hash"][:16],
        "form_pack_hash": runtime.i.form_pack.hash,
        "coverage_abi": attestation["coverage_abi"],
        "feature_algebra_version": attestation["feature_algebra_version"],
        "activation_ref": attestation["activation_ref"],
        "activation": attestation,
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
        activation_ref=(_activation or {}).get("activation_ref"),
    )


@app.post("/api/reload")
async def reload():
    # This endpoint intentionally reloads semantic authority only. Python source
    # changes require terminating and restarting the web-demo process. Any
    # pending learning plan is invalidated because it was licensed against the
    # previous authority generation.
    global _activation
    runtime = _ensure_runtime()
    receipt = runtime.reload_authority()
    _activation = assert_native_semantic_activation(runtime.i.form_pack, runtime.s)
    return {
        "ok": True,
        "reload_scope": "authority_only",
        "python_source_reloaded": False,
        "process_restart_required_for_source_changes": True,
        "activation_ref": _activation["activation_ref"],
        "activation": dict(_activation),
        **receipt,
    }


@app.post("/api/acquire")
async def acquire(request: AcquisitionRequest):
    """Publish explicitly reviewed identities/designations.

    Normal conversation only opens typed learning frontiers. It never mints an
    identity or defaults an unknown surface to ``concept``.
    """
    runtime = _ensure_runtime()
    document = {
        "document_ref": f"web-acquire:{request.mentions[0].surface}",
        "language": request.language or runtime.lang,
        "mentions": [
            {
                "surface": mention.surface,
                "kind": mention.kind,
                "ref": mention.ref,
                "label_type": mention.label_type,
                "preferred": mention.preferred,
            }
            for mention in request.mentions
        ],
        "text": request.text,
        "teach_rule": request.teach_rule,
    }
    try:
        return acquire_reviewed(runtime.s, runtime, document)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}


@app.get("/api/inspect")
async def inspect():
    store = _ensure_runtime().s
    tables = (
        "atoms",
        "applications",
        "claims",
        "rules",
        "frontiers",
        "commit_receipts",
        "common_ground",
        "effect_journal",
    )
    return {
        "generation": store.generation,
        "revisions": store.revisions(),
        "activation": dict(_activation or {}),
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
    _data_files = args.data or [
        str(package / "data" / "base.json"),
        str(package / "data" / "conversation_foundation.json"),
    ]
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
