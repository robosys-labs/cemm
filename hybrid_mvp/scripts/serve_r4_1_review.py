#!/usr/bin/env python3
"""Serve the accountable R4.1 reviewer on one bounded loopback endpoint."""
from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import secrets
import sys
from pathlib import Path
import threading
from typing import Mapping, Sequence
from urllib.parse import parse_qsl, quote, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.build_r4_1_review_worksheets import (  # noqa: E402
    _json_bytes,
    _read_regular,
    _strict_json,
    _trusted_directory,
)
from scripts.r4_1_guided_review import GuidedReviewService  # noqa: E402
from scripts.r4_1_review_session import (  # noqa: E402
    ActionPreview,
    ReviewAction,
    ReviewPaths,
    ReviewSession,
)

MAX_REQUEST_BYTES = 64 * 1024
MAX_STATIC_BYTES = 1024 * 1024
API_ROUTES = frozenset(
    {
        "/api/bootstrap",
        "/api/guided/bootstrap",
        "/api/guided/next",
        "/api/guided/preview",
        "/api/items",
        "/api/preview",
        "/api/apply",
        "/api/reviewer",
        "/api/export",
        "/api/shutdown",
    }
)
STATIC_ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/styles.css": "styles.css",
    "/app.js": "app.js",
}
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "connect-src 'self'; img-src 'none'; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
)
_CONTENT_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
}
_POST_ROUTES = frozenset(
    {
        "/api/preview",
        "/api/guided/preview",
        "/api/apply",
        "/api/reviewer",
        "/api/export",
        "/api/shutdown",
    }
)


class _AuthorizationError(ValueError):
    pass


class _RequestTooLarge(ValueError):
    pass


class _StaleRevision(ValueError):
    pass


class ReviewHTTPServer(HTTPServer):
    session: ReviewSession
    guided: GuidedReviewService
    session_token: str
    static_root: Path
    origin: str


def _wire_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _wire_value(item) for key, item in value.items()}
    if type(value) in {list, tuple}:
        return [_wire_value(item) for item in value]
    if type(value) is frozenset:
        return sorted(_wire_value(item) for item in value)
    if is_dataclass(value):
        return {
            field.name: _wire_value(getattr(value, field.name))
            for field in fields(value)
        }
    return value


def _exact_fields(
    value: object,
    expected: frozenset[str],
    *,
    owner: str,
) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{owner} fields are invalid")
    return value


def _exact_revision(value: object, current: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("state revision is invalid")
    if value != current:
        raise _StaleRevision("state revision is stale")
    return value


def _preview_result(preview: ActionPreview) -> dict[str, object]:
    return {
        "preview_hash": preview.preview_hash,
        "state_revision": preview.state_revision,
        "action": _wire_value(preview.action),
        "affected_refs": list(preview.affected_refs),
        "cleared_refs": list(preview.cleared_refs),
        "requires_clear_confirmation": preview.requires_clear_confirmation,
        "resulting_counts": dict(preview.resulting_counts),
    }


class ReviewRequestHandler(BaseHTTPRequestHandler):
    server: ReviewHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_bytes(
        self,
        *,
        status: int,
        raw: bytes,
        content_type: str,
        csp: bool,
    ) -> None:
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if self.close_connection:
            self.send_header("Connection", "close")
        if csp:
            self.send_header("Content-Security-Policy", CSP)
        self.end_headers()
        self.wfile.write(raw)
        self.wfile.flush()

    def _send_envelope(
        self,
        *,
        status: int,
        result: object | None = None,
        error: str | None = None,
    ) -> None:
        envelope: dict[str, object] = {
            "ok": error is None,
            "state_revision": self.server.session.state_revision,
        }
        if error is None:
            envelope["result"] = _wire_value(result)
        else:
            envelope["error"] = error
        self._send_bytes(
            status=status,
            raw=_json_bytes(envelope),
            content_type="application/json; charset=utf-8",
            csp=False,
        )

    def _request_id(self) -> str:
        return secrets.token_hex(8)

    def _handle_failure(self, exc: Exception, request_id: str) -> None:
        if isinstance(exc, _AuthorizationError):
            status = 403
            message = "request authorization failed"
        elif isinstance(exc, _RequestTooLarge):
            status = 413
            message = "request body exceeds byte bound"
            self.close_connection = True
        elif isinstance(exc, _StaleRevision) or (
            isinstance(exc, ValueError) and "stale preview" in str(exc)
        ):
            status = 409
            message = str(exc)
        elif isinstance(exc, (TypeError, ValueError)):
            status = 400
            message = str(exc)
        else:
            status = 500
            message = "internal request failure"
        if status == 500:
            print(
                f"review request {request_id} failed: {type(exc).__name__}",
                file=sys.stderr,
                flush=True,
            )
        try:
            self._send_envelope(status=status, error=message)
        except (BrokenPipeError, ConnectionError, OSError):
            pass

    def _authorize_api(self, *, require_origin: bool) -> None:
        supplied = self.headers.get("X-CEMM-Review-Token")
        if (
            type(supplied) is not str
            or not hmac.compare_digest(supplied, self.server.session_token)
        ):
            raise _AuthorizationError("session token is invalid")
        if require_origin and self.headers.get("Origin") != self.server.origin:
            raise _AuthorizationError("request origin is invalid")

    def _read_json_body(self) -> dict[str, object]:
        if self.headers.get("Transfer-Encoding") is not None:
            raise ValueError("transfer encoding is unavailable")
        if self.headers.get("Content-Type") != "application/json":
            raise ValueError("content type must be application/json")
        length_text = self.headers.get("Content-Length")
        if (
            type(length_text) is not str
            or not length_text.isdecimal()
            or (len(length_text) > 1 and length_text.startswith("0"))
        ):
            raise ValueError("content length is invalid")
        length = int(length_text)
        if length <= 0:
            raise ValueError("request body must be nonempty")
        if length > MAX_REQUEST_BYTES:
            self.rfile.read(min(length, MAX_REQUEST_BYTES + 1))
            raise _RequestTooLarge("request body exceeds byte bound")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError("request body was read incompletely")
        value = _strict_json(raw, owner="review API request")
        if type(value) is not dict:
            raise ValueError("review API request must be one object")
        return value

    def _serve_static(self, path: str) -> None:
        name = STATIC_ROUTES[path]
        raw = _read_regular(
            self.server.static_root / name,
            maximum=MAX_STATIC_BYTES,
            owner=f"review UI {name}",
        )
        self._send_bytes(
            status=200,
            raw=raw,
            content_type=_CONTENT_TYPES[name],
            csp=name in {"index.html", "app.js"},
        )

    def _serve_items(self, query: str) -> None:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True)
        expected = {"section", "filter", "query", "offset", "limit"}
        keys = [key for key, _ in pairs]
        if len(keys) != len(expected) or set(keys) != expected:
            raise ValueError("review item query fields are invalid")
        values = dict(pairs)
        for name in ("offset", "limit"):
            text = values[name]
            if (
                not text.isdecimal()
                or (len(text) > 1 and text.startswith("0"))
            ):
                raise ValueError(f"review item {name} is invalid")
        result = self.server.session.items(
            section=values["section"],
            state_filter=values["filter"],
            query=values["query"],
            offset=int(values["offset"]),
            limit=int(values["limit"]),
        )
        self._send_envelope(status=200, result=result)

    def _serve_guided_next(self, query: str) -> None:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True)
        if len(pairs) != 1 or pairs[0][0] != "after":
            raise ValueError("guided next query fields are invalid")
        after = pairs[0][1]
        if len(after) > 256:
            raise ValueError("guided after-item ref violates its bound")
        self._send_envelope(
            status=200,
            result=self.server.guided.next_item(
                after_item_ref=None if after == "" else after
            ),
        )

    def do_GET(self) -> None:
        request_id = self._request_id()
        try:
            target = urlsplit(self.path)
            if target.path in STATIC_ROUTES and not target.query:
                self._serve_static(target.path)
                return
            if target.path not in API_ROUTES:
                self._send_envelope(status=404, error="route not found")
                return
            self._authorize_api(require_origin=False)
            if target.path not in {
                "/api/bootstrap",
                "/api/guided/bootstrap",
                "/api/guided/next",
                "/api/items",
            }:
                self._send_envelope(status=405, error="method not allowed")
                return
            if target.path == "/api/bootstrap":
                if target.query:
                    raise ValueError("bootstrap query is unavailable")
                self._send_envelope(
                    status=200,
                    result=self.server.session.bootstrap(),
                )
            elif target.path == "/api/guided/bootstrap":
                if target.query:
                    raise ValueError("guided bootstrap query is unavailable")
                self._send_envelope(
                    status=200,
                    result=self.server.session.bootstrap(),
                )
            elif target.path == "/api/guided/next":
                self._serve_guided_next(target.query)
            else:
                self._serve_items(target.query)
        except Exception as exc:
            self._handle_failure(exc, request_id)

    def do_POST(self) -> None:
        request_id = self._request_id()
        try:
            target = urlsplit(self.path)
            if target.query:
                raise ValueError("POST query is unavailable")
            if target.path not in API_ROUTES:
                self._send_envelope(status=404, error="route not found")
                return
            self._authorize_api(require_origin=True)
            if target.path not in _POST_ROUTES:
                self._send_envelope(status=405, error="method not allowed")
                return
            body = self._read_json_body()
            revision = _exact_revision(
                body.get("state_revision"),
                self.server.session.state_revision,
            )
            shutdown = False
            if target.path == "/api/reviewer":
                value = _exact_fields(
                    body,
                    frozenset({"state_revision", "reviewer_refs"}),
                    owner="reviewer request",
                )
                refs = value["reviewer_refs"]
                if type(refs) is not list:
                    raise TypeError("reviewer refs must be one exact list")
                self.server.session.set_reviewers(tuple(refs))
                result = {
                    "reviewer_refs": list(
                        self.server.session.state["reviewer_refs"]
                    ),
                    "audit_warning": self.server.session.audit_warning,
                }
            elif target.path == "/api/guided/preview":
                value = _exact_fields(
                    body,
                    frozenset(
                        {"state_revision", "item_ref", "choice_ref"}
                    ),
                    owner="guided preview request",
                )
                result = self.server.guided.preview_choice(
                    item_ref=value["item_ref"],
                    choice_ref=value["choice_ref"],
                )
            elif target.path == "/api/preview":
                value = _exact_fields(
                    body,
                    frozenset({"state_revision", "action"}),
                    owner="preview request",
                )
                result = _preview_result(
                    self.server.session.preview(
                        ReviewAction.from_wire(value["action"])
                    )
                )
            elif target.path == "/api/apply":
                value = _exact_fields(
                    body,
                    frozenset({"state_revision", "preview_hash"}),
                    owner="apply request",
                )
                result = self.server.session.apply(
                    preview_hash=value["preview_hash"],
                    expected_revision=revision,
                )
            elif target.path == "/api/export":
                _exact_fields(
                    body,
                    frozenset({"state_revision"}),
                    owner="export request",
                )
                result = self.server.session.export()
            else:
                _exact_fields(
                    body,
                    frozenset({"state_revision"}),
                    owner="shutdown request",
                )
                result = {"shutdown": True}
                shutdown = True
            self._send_envelope(status=200, result=result)
            if shutdown:
                threading.Thread(
                    target=self.server.shutdown,
                    daemon=True,
                ).start()
        except Exception as exc:
            self._handle_failure(exc, request_id)

    def _method_not_allowed(self) -> None:
        request_id = self._request_id()
        try:
            target = urlsplit(self.path)
            if target.path in API_ROUTES:
                self._authorize_api(require_origin=False)
            self._send_envelope(status=405, error="method not allowed")
        except Exception as exc:
            self._handle_failure(exc, request_id)

    do_DELETE = _method_not_allowed
    do_HEAD = _method_not_allowed
    do_OPTIONS = _method_not_allowed
    do_PATCH = _method_not_allowed
    do_PUT = _method_not_allowed


def create_review_server(
    *,
    session: ReviewSession,
    host: str,
    port: int,
    session_token: str,
    static_root: Path | None = None,
) -> ReviewHTTPServer:
    if host != "127.0.0.1":
        raise ValueError("review server must bind exact IPv4 loopback")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("review server port is invalid")
    if (
        type(session_token) is not str
        or not 1 <= len(session_token) <= 512
    ):
        raise ValueError("review server token violates its bound")
    assets = (
        Path(static_root).absolute()
        if static_root is not None
        else ROOT / "scripts/r4_1_review_ui"
    )
    _trusted_directory(assets, owner="review UI static root")
    server = ReviewHTTPServer((host, port), ReviewRequestHandler)
    server.session = session
    server.guided = GuidedReviewService(session)
    server.session_token = session_token
    server.static_root = assets
    selected_port = server.server_address[1]
    server.origin = f"http://127.0.0.1:{selected_port}"
    return server


def _paths_from_args(args: argparse.Namespace) -> ReviewPaths:
    root = Path(args.root).absolute()
    inputs = root / "artifacts/review_inputs/r4_1"
    return ReviewPaths(
        repository_root=root,
        draft_root=Path(args.draft).absolute()
        if args.draft is not None
        else root / "artifacts/review_drafts/r4_1",
        template_path=Path(args.template).absolute()
        if args.template is not None
        else inputs / "SELECTION_TEMPLATE.json",
        working_path=Path(args.working).absolute()
        if args.working is not None
        else inputs / "SELECTION_WORKING.json",
        journal_path=Path(args.journal).absolute()
        if args.journal is not None
        else inputs / "REVIEW_ACTIONS.jsonl",
        export_path=Path(args.export).absolute()
        if args.export is not None
        else inputs / "SELECTION.json",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--working", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)
    session = ReviewSession.open(_paths_from_args(args))
    token = secrets.token_urlsafe(32)
    server = create_review_server(
        session=session,
        host="127.0.0.1",
        port=args.port,
        session_token=token,
    )
    launch_url = f"{server.origin}/#token={quote(token, safe='')}"
    print(launch_url, flush=True)
    if not args.no_open:
        webbrowser.open(launch_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
