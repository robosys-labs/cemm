"""Bounded loopback adapter for the accountable R4.1 reviewer."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import threading
from typing import Mapping

import pytest

from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import (
    _json_bytes,
    build_review_worksheet_draft,
)
from scripts.r4_1_review_session import ReviewPaths, ReviewSession
from scripts.serve_r4_1_review import (
    MAX_REQUEST_BYTES,
    create_review_server,
)

ROOT = Path(__file__).parents[1]


def request(
    server: object,
    method: str,
    path: str,
    *,
    body: Mapping[str, object] | None = None,
    raw_body: bytes | None = None,
    headers: Mapping[str, str] | None = None,
) -> tuple[int, Mapping[str, str], bytes]:
    connection = http.client.HTTPConnection(*server.server_address, timeout=5)
    raw = raw_body if raw_body is not None else (
        None if body is None else _json_bytes(body)
    )
    connection.request(method, path, body=raw, headers=dict(headers or {}))
    response = connection.getresponse()
    payload = response.read()
    result = response.status, dict(response.getheaders()), payload
    connection.close()
    return result


@pytest.fixture
def server_fixture(tmp_path: Path):
    running: list[tuple[object, threading.Thread]] = []

    def create() -> object:
        index = len(running)
        draft = tmp_path / f"draft-{index}"
        inputs = tmp_path / f"inputs-{index}"
        static = tmp_path / f"static-{index}"
        inputs.mkdir()
        static.mkdir()
        (static / "index.html").write_text("<!doctype html><title>Review</title>")
        (static / "styles.css").write_text("body { color: black; }")
        (static / "app.js").write_text("'use strict';")
        build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
        template_path = inputs / "SELECTION_TEMPLATE.json"
        template_path.write_bytes(
            build_selection_template_bytes(
                repository_root=ROOT,
                draft_root=draft,
            )
        )
        paths = ReviewPaths(
            repository_root=ROOT,
            draft_root=draft,
            template_path=template_path,
            working_path=inputs / "SELECTION_WORKING.json",
            journal_path=inputs / "REVIEW_ACTIONS.jsonl",
            export_path=inputs / "SELECTION.json",
        )
        session = ReviewSession.open(paths)
        server = create_review_server(
            session=session,
            host="127.0.0.1",
            port=0,
            session_token="test-token",
            static_root=static,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        running.append((server, thread))
        return server

    yield create
    for server, thread in running:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _api_headers(server: object, *, post: bool = False) -> dict[str, str]:
    result = {"X-CEMM-Review-Token": server.session_token}
    if post:
        result.update(
            {
                "Content-Type": "application/json",
                "Origin": server.origin,
            }
        )
    return result


def test_server_binds_loopback_and_requires_session_token(server_fixture) -> None:
    server = server_fixture()
    assert server.server_address[0] == "127.0.0.1"
    status, _, body = request(server, "GET", "/api/bootstrap")
    assert status == 403
    assert set(json.loads(body)) == {"error", "ok", "state_revision"}

    status, headers, body = request(
        server,
        "GET",
        "/api/bootstrap",
        headers=_api_headers(server),
    )
    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    envelope = json.loads(body)
    assert set(envelope) == {"ok", "result", "state_revision"}
    assert envelope["result"]["inventory"]["structural"] == 12


def test_state_change_requires_exact_origin_token_and_revision(
    server_fixture,
) -> None:
    server = server_fixture()
    body = {
        "state_revision": server.session.state_revision,
        "action": {
            "action_kind": "structural",
            "target_refs": [],
            "selected_value": None,
        },
    }
    status, _, _ = request(
        server,
        "POST",
        "/api/preview",
        body=body,
        headers={
            "X-CEMM-Review-Token": server.session_token,
            "Content-Type": "application/json",
            "Origin": "https://hostile.example",
        },
    )
    assert status == 403

    status, _, _ = request(
        server,
        "POST",
        "/api/reviewer",
        body={
            "state_revision": 1,
            "reviewer_refs": ["reviewer:son"],
        },
        headers=_api_headers(server, post=True),
    )
    assert status == 409


def test_server_rejects_unsafe_request_bodies(server_fixture) -> None:
    server = server_fixture()
    token = {"X-CEMM-Review-Token": server.session_token}
    status, _, _ = request(
        server,
        "POST",
        "/api/reviewer",
        raw_body=b"{}\n",
        headers={**token, "Origin": server.origin},
    )
    assert status == 400

    headers = _api_headers(server, post=True)
    for raw in (
        b"{not-json}\n",
        b'{"state_revision":0,"state_revision":0,"reviewer_refs":[]}\n',
        b'{"state_revision":NaN,"reviewer_refs":[]}\n',
    ):
        status, _, body = request(
            server,
            "POST",
            "/api/reviewer",
            raw_body=raw,
            headers=headers,
        )
        assert status == 400
        assert b"Traceback" not in body

    status, _, _ = request(
        server,
        "POST",
        "/api/reviewer",
        raw_body=b"x" * (MAX_REQUEST_BYTES + 1),
        headers={
            **headers,
            "Content-Length": str(MAX_REQUEST_BYTES + 1),
        },
    )
    assert status == 413


def test_server_uses_fixed_route_and_asset_allowlists(server_fixture) -> None:
    server = server_fixture()
    status, headers, _ = request(server, "GET", "/")
    assert status == 200
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    status, headers, _ = request(server, "GET", "/app.js")
    assert status == 200
    assert "script-src 'self'" in headers["Content-Security-Policy"]
    assert request(server, "GET", "/../SELECTION_TEMPLATE.json")[0] == 404
    assert request(server, "GET", "/unknown.js")[0] == 404
    assert request(
        server,
        "PUT",
        "/api/bootstrap",
        headers=_api_headers(server),
    )[0] == 405
    assert request(
        server,
        "POST",
        "/api/bootstrap",
        headers=_api_headers(server, post=True),
    )[0] == 405


def test_items_reject_duplicate_or_unknown_query_parameters(server_fixture) -> None:
    server = server_fixture()
    headers = _api_headers(server)
    assert request(
        server,
        "GET",
        "/api/items?section=structural&section=purpose&filter=all&query=&offset=0&limit=10",
        headers=headers,
    )[0] == 400
    assert request(
        server,
        "GET",
        "/api/items?section=structural&filter=all&query=&offset=0&limit=10&extra=x",
        headers=headers,
    )[0] == 400


def test_reviewer_route_mutates_only_at_exact_revision(server_fixture) -> None:
    server = server_fixture()
    status, _, body = request(
        server,
        "POST",
        "/api/reviewer",
        body={
            "state_revision": 0,
            "reviewer_refs": ["reviewer:son"],
        },
        headers=_api_headers(server, post=True),
    )
    assert status == 200
    assert json.loads(body)["state_revision"] == 1
    assert server.session.state["reviewer_refs"] == ["reviewer:son"]

    row = next(iter(server.session.indexes.structural_rows_by_ref.values()))
    status, _, body = request(
        server,
        "POST",
        "/api/preview",
        body={
            "state_revision": 1,
            "action": {
                "action_kind": "structural",
                "target_refs": [row["row_ref"]],
                "selected_value": row["options"][0]["option_ref"],
            },
        },
        headers=_api_headers(server, post=True),
    )
    assert status == 200
    preview_hash = json.loads(body)["result"]["preview_hash"]
    status, _, body = request(
        server,
        "POST",
        "/api/apply",
        body={"state_revision": 1, "preview_hash": preview_hash},
        headers=_api_headers(server, post=True),
    )
    assert status == 200
    assert json.loads(body)["state_revision"] == 2


def test_shutdown_requires_authorization_and_exact_origin(server_fixture) -> None:
    server = server_fixture()
    body = {"state_revision": server.session.state_revision}
    assert request(server, "POST", "/api/shutdown", body=body)[0] == 403
    status, _, payload = request(
        server,
        "POST",
        "/api/shutdown",
        body=body,
        headers=_api_headers(server, post=True),
    )
    assert status == 200
    assert json.loads(payload)["result"]["shutdown"] is True
