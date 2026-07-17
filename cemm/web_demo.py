"""Small stdlib web demo for the canonical CEMM v3.4.7 runtime."""
from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from .v347.runtime import Runtime


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CEMM v3.4.7 Web Demo</title>
  <style>
    :root { color-scheme: light dark; font-family: Inter, Segoe UI, Arial, sans-serif; }
    body { margin: 0; background: #f4f6f8; color: #17202a; }
    main { max-width: 920px; margin: 0 auto; padding: 24px; }
    header { display: flex; justify-content: space-between; gap: 16px; align-items: baseline; margin-bottom: 18px; }
    h1 { font-size: 24px; margin: 0; letter-spacing: 0; }
    .version { color: #52616f; font-size: 14px; }
    #log { min-height: 420px; border: 1px solid #c9d2dc; background: #fff; padding: 14px; overflow: auto; }
    .turn { margin: 0 0 12px; line-height: 1.45; }
    .speaker { font-weight: 700; margin-right: 6px; }
    .user .speaker { color: #0b5cad; }
    .cemm .speaker { color: #157347; }
    form { display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-top: 12px; }
    input, button { font: inherit; border: 1px solid #9fb0bf; min-height: 42px; }
    input { padding: 0 12px; background: #fff; color: inherit; }
    button { padding: 0 16px; background: #17202a; color: #fff; cursor: pointer; }
    details { margin-top: 12px; color: #34495e; }
    pre { white-space: pre-wrap; background: #edf1f5; padding: 12px; overflow: auto; }
    @media (prefers-color-scheme: dark) {
      body { background: #111820; color: #e8edf2; }
      #log, input { background: #18222c; border-color: #3d4b59; }
      button { background: #d9e6f2; color: #111820; }
      .version, details { color: #a8b5c2; }
      pre { background: #1d2935; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <h1>CEMM Web Demo</h1>
    <div class="version">canonical v3.4.7 runtime</div>
  </header>
  <section id="log" aria-live="polite"></section>
  <form id="chat">
    <input id="text" name="text" autocomplete="off" autofocus placeholder="Type a message">
    <button type="submit">Send</button>
  </form>
  <details>
    <summary>Trace</summary>
    <pre id="trace">{}</pre>
  </details>
</main>
<script>
const log = document.querySelector("#log");
const trace = document.querySelector("#trace");
const form = document.querySelector("#chat");
const input = document.querySelector("#text");
const contextId = "web-demo:" + crypto.randomUUID();

function addTurn(who, text) {
  const row = document.createElement("p");
  row.className = "turn " + (who === "You" ? "user" : "cemm");
  const speaker = document.createElement("span");
  speaker.className = "speaker";
  speaker.textContent = who + ":";
  row.append(speaker, document.createTextNode(" " + text));
  log.append(row);
  log.scrollTop = log.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addTurn("You", text);
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {"content-type": "application/json"},
    body: JSON.stringify({text, context_id: contextId, include_trace: true})
  });
  const payload = await response.json();
  addTurn("CEMM", payload.output_text || "[no semantically authorized surface output]");
  trace.textContent = JSON.stringify(payload.trace || {}, null, 2);
});
</script>
</body>
</html>
"""


def handle_chat(runtime: Runtime, payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", "")).strip()
    if not text:
        return {"ok": False, "error": "empty_text"}
    result = runtime.run_text(
        text,
        context_id=str(payload.get("context_id") or "web-demo"),
        language_hint=payload.get("language"),
        target_language=payload.get("target_language"),
    )
    response: dict[str, Any] = {
        "ok": True,
        "output_text": result.output_text,
        "cycle_id": result.cycle_id,
        "context_id": result.context_id,
        "target_language": result.target_language,
        "committed_patch_refs": list(result.committed_patch_refs),
        "emission_authorized": bool(result.emission_proof and result.emission_proof.authorized),
        "blocked_semantic_refs": list(result.emission_proof.blocked_semantic_refs if result.emission_proof else ()),
    }
    if payload.get("include_trace"):
        response["trace"] = {
            "stages": list(result.trace.stages),
            "details": result.trace.details,
            "errors": list(result.trace.errors),
        }
    return response


class DemoHandler(BaseHTTPRequestHandler):
    runtime: Runtime

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"", "/"}:
            self._send(HTTPStatus.OK, HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/health":
            body = json.dumps({"ok": True, "version": Runtime.VERSION}).encode("utf-8")
            self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")
            return
        if parsed.path == "/api/chat":
            query = parse_qs(parsed.query)
            payload = {
                "text": query.get("text", [""])[0],
                "context_id": query.get("context_id", ["web-demo"])[0],
                "include_trace": query.get("trace", [""])[0] in {"1", "true", "yes"},
            }
            self._send_json(handle_chat(self.runtime, payload))
            return
        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/chat":
            self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("content-length", "0") or "0")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json(handle_chat(self.runtime, payload))

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = "127.0.0.1", port: int = 8765, database_path: str = ":memory:") -> None:
    runtime = Runtime(database_path=database_path)
    DemoHandler.runtime = runtime
    server = ThreadingHTTPServer((host, port), DemoHandler)
    try:
        print(f"CEMM web demo listening at http://{host}:{port}")
        server.serve_forever()
    finally:
        server.server_close()
        runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM v3.4.7 web demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", default=":memory:")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, database_path=args.database)


if __name__ == "__main__":
    main()
