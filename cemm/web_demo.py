"""CEMM canonical v3.4.3 web demo.

The HTTP layer projects the authoritative CognitiveCycle.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse
import json
import uuid

from cemm.app.runtime import Runtime

_RUNTIME = Runtime()
_DEFAULT_CONTEXT = f"web:{uuid.uuid4().hex[:10]}"
_DEBUG = False


def handle_chat(text: str, context_id: str) -> dict:
    cycle = _RUNTIME.run_text(text, context_id=context_id)
    result = _RUNTIME.project(cycle)
    payload = {
        "response": result.output_text,
        "context_id": result.context_id,
        "cycle_id": result.cycle_id,
        "transport_status": (
            "dispatched" if result.output_text else "no_authorized_surface"
        ),
    }
    if _DEBUG:
        payload["debug"] = {
            "trace_stages": list(result.trace_stages),
            "errors": list(result.errors),
            "realized_item_refs": list(result.realized_item_refs),
            "blocked_item_refs": list(result.blocked_item_refs),
            "selected_interpretations": len(cycle.selected_interpretations),
            "gaps": [
                {
                    "kind": getattr(gap, "gap_kind", ""),
                    "target": getattr(gap, "target_artifact_ref", ""),
                    "missing_fields": list(getattr(gap, "missing_fields", ())),
                }
                for gap in cycle.gaps
            ],
            "learning_transactions": [
                {
                    "id": getattr(tx, "id", ""),
                    "status": getattr(tx, "status", ""),
                    "target": getattr(tx, "target_sense_ref", ""),
                    "frontier": list(getattr(tx, "grounding_frontier", ())),
                }
                for tx in cycle.learning_transactions
            ],
            "dialogue_resolution": (
                {
                    "kind": getattr(cycle.dialogue_resolution, "resolution_kind", ""),
                    "target": getattr(cycle.dialogue_resolution, "target_artifact_ref", ""),
                    "remaining": list(getattr(cycle.dialogue_resolution, "remaining_field_refs", ())),
                }
                if cycle.dialogue_resolution is not None else None
            ),
        }
    return payload


HTML_PAGE = r'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>CEMM v3.4.3</title>
<style>
body{font:15px system-ui;max-width:900px;margin:0 auto;padding:24px;background:#0b0d14;color:#e8eaf2}
#chat{min-height:65vh;border:1px solid #30354a;border-radius:12px;padding:16px;overflow:auto}
.msg{margin:10px 0;padding:10px 12px;border-radius:10px;background:#171b29}.user{background:#252b45}
.status{font-size:12px;color:#9299b5}form{display:flex;gap:8px;margin-top:12px}input{flex:1;padding:12px;border-radius:8px;border:1px solid #30354a;background:#111521;color:white}button{padding:0 18px}
pre{white-space:pre-wrap;color:#aeb5d0}
</style></head><body><h2>CEMM <small>canonical v3.4.3</small></h2><div id="chat"></div>
<form id="form"><input id="input" autocomplete="off"><button>Send</button></form>
<script>
const chat=document.querySelector('#chat'),input=document.querySelector('#input');
const contextId=localStorage.cemmContextId||(localStorage.cemmContextId='web:'+crypto.randomUUID());
function add(text,cls,status=''){const d=document.createElement('div');d.className='msg '+cls;d.textContent=text;chat.appendChild(d);if(status){const s=document.createElement('div');s.className='status';s.textContent=status;chat.appendChild(s)}chat.scrollTop=chat.scrollHeight}
document.querySelector('#form').onsubmit=async e=>{e.preventDefault();const text=input.value.trim();if(!text)return;input.value='';add(text,'user');const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,context_id:contextId})});const data=await r.json();if(data.response)add(data.response,'ai');else add('[no semantically authorized surface output]','status',data.transport_status);if(data.debug)add(JSON.stringify(data.debug,null,2),'status')};
</script></body></html>'''


class CEMMHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        self._send(200, HTML_PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            text = str(data.get("text", ""))
            context_id = str(data.get("context_id") or _DEFAULT_CONTEXT)
            payload = handle_chat(text, context_id)
            self._send(200, json.dumps(payload).encode(), "application/json")
        except Exception as exc:
            self._send(
                500,
                json.dumps({
                    "response": "",
                    "transport_status": "runtime_error",
                    "error": str(exc),
                }).encode(),
                "application/json",
            )

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        if _DEBUG:
            super().log_message(fmt, *args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    _DEBUG = args.debug
    print(f"CEMM v3.4.3 at http://127.0.0.1:{args.port}")
    HTTPServer(("127.0.0.1", args.port), CEMMHandler).serve_forever()
