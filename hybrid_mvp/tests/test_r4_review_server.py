"""Bounded loopback adapter for the accountable R4.1 reviewer."""
from __future__ import annotations

import ast
import http.client
import json
from pathlib import Path
import threading
from typing import Mapping
from urllib.parse import quote

import pytest

from scripts.build_r4_1_review_selection import (
    build_selection_template_bytes,
    validate_reviewed_selection_bytes,
)
from scripts.build_r4_1_review_worksheets import (
    _json_bytes,
    build_review_worksheet_draft,
)
from scripts.r4_1_guided_review import GUIDANCE, MAX_GUIDED_TARGET_REFS
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
    timeout: int = 5,
) -> tuple[int, Mapping[str, str], bytes]:
    connection = http.client.HTTPConnection(
        *server.server_address,
        timeout=timeout,
    )
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


def _guided_next(
    server: object,
    after: str | None,
) -> tuple[int, Mapping[str, object]]:
    encoded = quote("" if after is None else after, safe="")
    status, _, raw = request(
        server,
        "GET",
        f"/api/guided/next?after={encoded}",
        headers=_api_headers(server),
    )
    return status, json.loads(raw)


def _guided_preview(
    server: object,
    item: Mapping[str, object],
    choice: Mapping[str, object],
) -> tuple[int, Mapping[str, object]]:
    status, _, raw = request(
        server,
        "POST",
        "/api/guided/preview",
        body={
            "state_revision": server.session.state_revision,
            "item_ref": item["item_ref"],
            "choice_ref": choice["choice_ref"],
        },
        headers=_api_headers(server, post=True),
    )
    return status, json.loads(raw)


def test_guided_routes_require_existing_authorization_controls(
    server_fixture,
) -> None:
    server = server_fixture()
    assert request(server, "GET", "/api/guided/next?after=")[0] == 403

    status, envelope = _guided_next(server, None)
    assert status == 200
    assert envelope["result"]["phase"] == "identity"

    status, _, _ = request(
        server,
        "POST",
        "/api/guided/preview",
        body={"state_revision": 0, "item_ref": "x", "choice_ref": "y"},
        headers={
            "X-CEMM-Review-Token": server.session_token,
            "Content-Type": "application/json",
            "Origin": "https://hostile.example",
        },
    )
    assert status == 403


def test_guided_next_and_preview_never_expose_action_wire(
    server_fixture,
) -> None:
    server = server_fixture()
    status, _, _ = request(
        server,
        "POST",
        "/api/reviewer",
        body={"state_revision": 0, "reviewer_refs": ["reviewer:test"]},
        headers=_api_headers(server, post=True),
    )
    assert status == 200
    status, envelope = _guided_next(server, None)
    assert status == 200
    item = envelope["result"]
    assert "action" not in json.dumps(item)

    status, preview_envelope = _guided_preview(
        server,
        item,
        item["choices"][0],
    )
    assert status == 200
    assert "preview_hash" in preview_envelope["result"]
    assert "action" not in preview_envelope["result"]


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


def _drive_complete_review(server: object) -> tuple[dict[str, object], bytes]:
    revision = 0

    def post(
        path: str,
        body: Mapping[str, object],
        *,
        timeout: int = 5,
    ) -> Mapping[str, object]:
        nonlocal revision
        status, _, raw = request(
            server,
            "POST",
            path,
            body={"state_revision": revision, **body},
            headers=_api_headers(server, post=True),
            timeout=timeout,
        )
        envelope = json.loads(raw)
        assert status == 200, envelope
        revision = envelope["state_revision"]
        return envelope["result"]

    def apply_action(action: Mapping[str, object]) -> None:
        preview = post("/api/preview", {"action": action})
        post("/api/apply", {"preview_hash": preview["preview_hash"]})

    def items(section: str) -> list[Mapping[str, object]]:
        result: list[Mapping[str, object]] = []
        offset = 0
        while True:
            status, _, raw = request(
                server,
                "GET",
                f"/api/items?section={section}&filter=all&query=&offset={offset}&limit=100",
                headers=_api_headers(server),
            )
            envelope = json.loads(raw)
            assert status == 200, envelope
            page = envelope["result"]
            result.extend(page["items"])
            offset += len(page["items"])
            if offset >= page["total"]:
                return result

    post("/api/reviewer", {"reviewer_refs": ["reviewer:test"]})
    structural_labels = {
        "composed_expression_proposal": "approve_exact_proposal",
        "conflict_preservation": "preserve_as_alternatives",
        "legacy_conditional": "retain_typed_proposal_gaps",
        "restart_diagnostic": "approve_diagnostic_only",
        "generator_patch": "retain_typed_proposal_gaps",
    }
    for item in items("structural"):
        selected = next(
            option["option_ref"]
            for option in item["options"]
            if option["label"] == structural_labels[item["row_kind"]]
        )
        apply_action(
            {
                "action_kind": "structural",
                "target_refs": [item["row_ref"]],
                "selected_value": selected,
            }
        )

    purpose_rows = items("purpose")
    supervised = [
        item
        for item in purpose_rows
        if item["row_kind"] == "membership"
        and any(
            option["label"] == "direct_train"
            and option["selectable"] is True
            for option in item["options"]
        )
    ]
    purposes = ("train", "selection", "calibration", "frozen_test")
    for purpose_index, purpose in enumerate(purposes):
        refs = sorted(
            item["row_ref"]
            for item_index, item in enumerate(supervised)
            if item_index % len(purposes) == purpose_index
        )
        apply_action(
            {
                "action_kind": "purpose",
                "target_refs": refs,
                "selected_value": f"direct_{purpose}",
            }
        )
    for row_kind, option_label in (
        ("membership", "approve_diagnostic_only"),
        ("duplicate_group", "reject_group"),
        ("challenge_holdout", "not_a_holdout"),
        ("denominator", "minimum_one_each"),
    ):
        refs = sorted(
            item["row_ref"]
            for item in purpose_rows
            if item["row_kind"] == row_kind
            and any(
                option["label"] == option_label
                and option["selectable"] is True
                for option in item["options"]
            )
        )
        apply_action(
            {
                "action_kind": "purpose",
                "target_refs": refs,
                "selected_value": option_label,
            }
        )

    for item in items("recipe"):
        for purpose in item["display"]["eligible_purposes"]:
            apply_action(
                {
                    "action_kind": "recipe",
                    "target_refs": [item["row_ref"]],
                    "selected_value": {
                        "purpose": purpose,
                        "decision": "approve",
                        "reviewed_parameters": {
                            "review_basis": "accountable_ui_exact_family"
                        },
                    },
                }
            )

    designation_rows = items("designation")
    cohorts: set[str] = set()
    for item in designation_rows:
        if item["display"]["exceptional"]:
            decision = (
                "approve_candidate_bindings"
                if item["display"]["candidate_bindings"]
                else "approve_exact_empty"
            )
            apply_action(
                {
                    "action_kind": "designation_cases",
                    "target_refs": [item["row_ref"]],
                    "selected_value": {
                        "decision": decision,
                        "individual": True,
                    },
                }
            )
        else:
            cohorts.add(item["display"]["routine_cohort_ref"])
    for cohort_ref in sorted(cohorts):
        apply_action(
            {
                "action_kind": "designation_cohort",
                "target_refs": [cohort_ref],
                "selected_value": "approve_candidate_bindings",
            }
        )

    receipt = dict(post("/api/export", {}, timeout=60))
    status, _, raw = request(
        server,
        "GET",
        "/api/bootstrap",
        headers=_api_headers(server),
    )
    assert status == 200
    bootstrap = json.loads(raw)["result"]
    assert bootstrap["inventory"] == {
        "structural": 12,
        "purpose": 600,
        "recipe_family": 56,
        "designation": 388,
    }
    assert receipt["review_complete"] is True
    assert receipt["authoring_ready"] is True
    export_raw = server.session.paths.export_path.read_bytes()
    assert validate_reviewed_selection_bytes(
        repository_root=ROOT,
        draft_root=server.session.paths.draft_root,
        selection_raw=export_raw,
    )["selection_state"] == "reviewed"
    return receipt, export_raw


def _drive_complete_guided_review(
    server: object,
) -> tuple[dict[str, object], bytes]:
    revision = 0

    def post(
        path: str,
        body: Mapping[str, object],
        *,
        timeout: int = 5,
    ) -> Mapping[str, object]:
        nonlocal revision
        status, _, raw = request(
            server,
            "POST",
            path,
            body={"state_revision": revision, **body},
            headers=_api_headers(server, post=True),
            timeout=timeout,
        )
        envelope = json.loads(raw)
        assert status == 200, envelope
        revision = envelope["state_revision"]
        return envelope["result"]

    status, _, raw = request(
        server,
        "GET",
        "/api/guided/bootstrap",
        headers=_api_headers(server),
    )
    assert status == 200, json.loads(raw)
    post("/api/reviewer", {"reviewer_refs": ["reviewer:test"]})
    structural_labels = {
        "composed_expression_proposal": "approve_exact_proposal",
        "conflict_preservation": "preserve_as_alternatives",
        "legacy_conditional": "retain_typed_proposal_gaps",
        "restart_diagnostic": "approve_diagnostic_only",
        "generator_patch": "retain_typed_proposal_gaps",
    }
    purposes = ("train", "selection", "calibration", "frozen_test")
    supervised_index = 0
    after: str | None = None
    while True:
        status, envelope = _guided_next(server, after)
        assert status == 200, envelope
        item = envelope["result"]
        phase = item["phase"]
        if phase == "export":
            break
        source = item["technical_evidence"]["source"]
        row_kind = item["row_kind"]
        if phase == "structural":
            option_key = structural_labels[row_kind]
        elif phase == "purpose":
            if row_kind == "membership":
                selectable = {
                    option["label"]
                    for option in source["options"]
                    if option["selectable"] is True
                }
                if "direct_train" in selectable:
                    purpose = purposes[supervised_index % len(purposes)]
                    supervised_index += 1
                    option_key = f"direct_{purpose}"
                else:
                    option_key = "approve_diagnostic_only"
            elif row_kind == "duplicate_group":
                option_key = "reject_group"
            elif row_kind == "challenge_holdout":
                option_key = "not_a_holdout"
            else:
                assert row_kind == "denominator"
                option_key = "minimum_one_each"
        elif phase == "recipe":
            option_key = "approve"
        else:
            assert phase == "designation"
            option_key = (
                "approve_candidate_bindings"
                if source["candidate_bindings"]
                else "approve_exact_empty"
            )
        guidance_key = row_kind
        if phase == "designation":
            guidance_key = (
                "designation_nonempty"
                if source["candidate_bindings"]
                else "designation_empty"
            )
        choice_label = GUIDANCE[guidance_key].choices[option_key].label
        choice = next(
            candidate
            for candidate in item["choices"]
            if candidate["label"] == choice_label
        )
        status, preview_envelope = _guided_preview(server, item, choice)
        assert status == 200, preview_envelope
        revision = preview_envelope["state_revision"]
        post(
            "/api/apply",
            {"preview_hash": preview_envelope["result"]["preview_hash"]},
        )
        after = item["item_ref"]

    receipt = dict(post("/api/export", {}, timeout=60))
    export_raw = server.session.paths.export_path.read_bytes()
    assert receipt["review_complete"] is True
    assert receipt["authoring_ready"] is True
    assert (
        server.guided.maximum_projected_targets
        <= MAX_GUIDED_TARGET_REFS
    )
    return receipt, export_raw


def test_guided_and_advanced_http_reviews_export_identical_validated_bytes(
    server_fixture,
) -> None:
    guided = server_fixture()
    advanced = server_fixture()

    guided_receipt, guided_raw = _drive_complete_guided_review(guided)
    advanced_receipt, advanced_raw = _drive_complete_review(advanced)

    assert guided_raw == advanced_raw
    assert guided_receipt["sha256"] == advanced_receipt["sha256"]
    assert validate_reviewed_selection_bytes(
        repository_root=ROOT,
        draft_root=guided.session.paths.draft_root,
        selection_raw=guided_raw,
    )["selection_state"] == "reviewed"


def test_full_http_review_exports_deterministic_validated_bytes(
    server_fixture,
) -> None:
    first = server_fixture()
    second = server_fixture()

    first_receipt, first_raw = _drive_complete_review(first)
    second_receipt, second_raw = _drive_complete_review(second)

    assert first_raw == second_raw
    assert first_receipt["sha256"] == second_receipt["sha256"]


def test_runtime_source_never_imports_review_ui_or_server() -> None:
    forbidden = {
        "serve_r4_1_review",
        "r4_1_review_session",
        "http.server",
        "webbrowser",
        "scripts.r4_1_review_ui",
    }
    violations: list[tuple[str, str]] = []
    for path in sorted((ROOT / "src/cemm_authoritative_hybrid").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for item in ast.walk(tree):
            names: list[str] = []
            if isinstance(item, ast.Import):
                names = [alias.name for alias in item.names]
            elif isinstance(item, ast.ImportFrom) and item.module is not None:
                names = [item.module]
            for name in names:
                if any(blocked in name for blocked in forbidden):
                    violations.append((str(path.relative_to(ROOT)), name))
    assert violations == []
