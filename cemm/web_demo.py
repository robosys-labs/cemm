"""CEMM v1 Web Demo — FastAPI backend.

Run: python -m cemm.web_demo --port 8765
Open: http://127.0.0.1:8765
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from cemm.config import Config
from cemm.runtime import Runtime
from cemm.store import Store

_WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="CEMM v1 Web Demo", version="1.0.0")

# ---------------------------------------------------------------------------
# Global runtime state (single-user demo)
# ---------------------------------------------------------------------------
_runtime: Runtime | None = None
_store: Store | None = None
_config: Config | None = None


def _ensure_runtime() -> Runtime:
    global _runtime, _store, _config
    if _runtime is None:
        db_path = _db_path
        _store = Store(db_path)
        for d in _data_files:
            _store.import_data(d)
        _config = Config()
        _runtime = Runtime(_store, _pack_path, _config)
    return _runtime


# Module-level config set in main()
_db_path: str = ":memory:"
_pack_path: str = ""
_data_files: list[str] = []


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    text: str
    mode: str = "ask"  # ask | learn | teach


class ChatResponse(BaseModel):
    status: str
    response: str
    facts: list[dict[str, Any]] = []
    workspace: dict[str, Any] | None = None
    self_state: dict[str, Any] = {}
    realization_proof: dict[str, Any] | None = None
    response_plan: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = _WEB_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health() -> dict[str, Any]:
    rt = _ensure_runtime()
    return {
        "ok": True,
        "version": "1.0.0",
        "authority_generation": rt.s.generation,
        "authority_hash": rt.s.authority_hash()[:16],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    rt = _ensure_runtime()
    text = req.text.strip()
    if not text:
        return ChatResponse(status="error", response="Empty input.")
    learn = req.mode == "learn"
    teach = req.mode == "teach"
    if req.mode == "ask":
        learn = False
        teach = False
    result = rt.process(text, learn=learn, teach=teach)
    return ChatResponse(
        status=result.get("status", "unknown"),
        response=result.get("response", ""),
        facts=result.get("facts", []),
        workspace=result.get("workspace"),
        self_state=result.get("self_state", {}),
        realization_proof=result.get("realization_proof"),
        response_plan=result.get("response_plan"),
    )


@app.post("/api/reload")
async def reload() -> dict[str, Any]:
    rt = _ensure_runtime()
    att = rt.reload_authority()
    return {
        "ok": True,
        "authority_generation": att.get("authority_generation"),
        "authority_hash": att.get("authority_generation_hash", "")[:16],
    }


@app.get("/api/inspect")
async def inspect() -> dict[str, Any]:
    rt = _ensure_runtime()
    s = rt.s
    tables = [
        "atoms", "operator_roles", "applications", "bindings",
        "observations", "claims", "rules", "rule_candidates",
        "reference_forms", "designation_index", "frontiers",
    ]
    counts = {}
    for t in tables:
        try:
            counts[t] = s.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except Exception:
            counts[t] = -1
    return {
        "generation": s.generation,
        "authority_hash": s.authority_hash()[:16],
        "table_counts": counts,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global _db_path, _pack_path, _data_files
    parser = argparse.ArgumentParser(description="CEMM v1 Web Demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=":memory:", help="SQLite path (default: in-memory)")
    parser.add_argument("--pack", default=None, help="Language pack JSON path")
    parser.add_argument("--data", action="append", default=[], help="Knowledge JSON paths")
    args = parser.parse_args()

    _db_path = args.db
    # Default paths relative to package
    pkg_dir = Path(__file__).parent
    _pack_path = args.pack or str(pkg_dir / "language_packs" / "en.json")
    _data_files = args.data or [
        str(pkg_dir / "data" / "base.json"),
        str(pkg_dir / "data" / "family_knowledge.json"),
    ]

    import uvicorn

    print(f"CEMM v1 Web Demo")
    print(f"  Language pack: {_pack_path}")
    print(f"  Data files: {', '.join(_data_files)}")
    print(f"  Database: {_db_path}")
    print(f"  Listening: http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
