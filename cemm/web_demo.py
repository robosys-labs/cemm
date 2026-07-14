"""
CEMM Web Demo — full v4.2 runtime with structured debug output.

Uses python stdlib http.server only. No external dependencies.
Exposes the complete RuntimeCycleResult diagnostics in a collapsible debug panel.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

from cemm.registry import Registry
from cemm.legacy.v3_3.pipeline import Pipeline
from cemm.memory.concept_lattice import ConceptLattice
from cemm.memory.construction_lattice import ConstructionLattice
from cemm.memory.episodic_trace_store import EpisodicTraceStore
from cemm.memory.persistent_lattice_store import PersistentLatticeStore
from cemm.__main__ import process_input, seed_registry, seed_self_state

_registry = Registry()
_persistent_store = PersistentLatticeStore(":memory:")
_concept_lattice = ConceptLattice(persistent_store=_persistent_store)
_construction_lattice = ConstructionLattice()
_episodic_store = EpisodicTraceStore()
_pipeline = Pipeline(
    _registry,
    concept_lattice=_concept_lattice,
    construction_lattice=_construction_lattice,
    episodic_store=_episodic_store,
    auto_consolidate=True,
)

seed_registry(_registry)
seed_self_state(concept_lattice=_concept_lattice, durable_store=_pipeline._runtime.durable_semantic_store)

_context_id = "web_demo"
_turn_count = [0]
_DEBUG = False


def _diag_value(val: object) -> object:
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if hasattr(val, "to_dict"):
        return val.to_dict()
    if hasattr(val, "__dataclass_fields__"):
        return {k: _diag_value(getattr(val, k)) for k in vars(val)}
    if isinstance(val, list):
        return [_diag_value(v) for v in val[:5]] + (["…"] if len(val) > 5 else [])
    if isinstance(val, dict):
        return {k: _diag_value(v) for k, v in val.items()}
    return str(val)


def _extract_debug(cycle) -> dict:
    info: dict = {}

    if cycle.surface_evidence is not None:
        se = cycle.surface_evidence
        info["Surface Evidence"] = {
            "token_count": len(getattr(se, "tokens", ())),
            "referent_count": len(getattr(se, "referents", ())),
            "predicate_phrase_count": len(getattr(se, "predicate_phrases", ())),
        }

    if cycle.candidate_graph is not None:
        cg = cycle.candidate_graph
        info["Candidate Graph"] = {
            "predications": len(getattr(cg, "candidate_predications", ())),
            "propositions": len(getattr(cg, "candidate_propositions", ())),
            "contexts": len(getattr(cg, "candidate_contexts", ())),
            "communicative_forces": len(getattr(cg, "candidate_communicative_forces", ())),
        }

    if cycle.grounding_assessments:
        info["Grounding Assessments"] = {
            "count": len(cycle.grounding_assessments),
        }

    if cycle.epistemic_assessments:
        info["Epistemic Assessments"] = {
            "count": len(cycle.epistemic_assessments),
        }

    if cycle.capability_assessment is not None:
        info["Capability Assessment"] = {"present": True}

    if cycle.commit_outcome is not None:
        info["Commit Outcome"] = {
            "phase": getattr(cycle.commit_outcome, "phase", ""),
            "committed": len(getattr(cycle.commit_outcome, "committed_refs", ())),
        }

    if cycle.common_ground_entries:
        info["Common Ground"] = {
            "entries": len(cycle.common_ground_entries),
        }

    if cycle.uol_graph is not None:
        g = cycle.uol_graph
        info["UOL Graph"] = {
            "atoms": len(g.atoms),
            "edges": len(g.edges),
            "groups": len(g.groups),
            "candidate_sets": len(getattr(g, "candidate_sets", [])),
            "patch_candidates": len(getattr(g, "patch_candidates", [])),
        }

    if cycle.semantic_program is not None:
        sp = cycle.semantic_program
        d = getattr(sp, "diagnostics", {}) or {}
        info["Semantic Program"] = {
            "entry_kind": d.get("entry_kind"),
            "instruction_count": len(getattr(sp, "instructions", [])),
            "entry_instruction_id": getattr(sp, "entry_instruction_id", ""),
        }

    if cycle.obligation_frame is not None:
        of = cycle.obligation_frame
        info["Obligation Frame"] = {
            "obligation_kind": getattr(of, "obligation_kind", ""),
            "response_mode": getattr(of, "response_mode", ""),
            "evidence_policy": getattr(of, "evidence_policy", ""),
            "write_policy": getattr(of, "write_policy", ""),
            "confidence": getattr(of, "confidence", 0.0),
            "blocked_by": getattr(of, "blocked_by", []),
            "suppressed_count": len(getattr(of, "suppressed_obligations", [])),
        }

    from cemm.legacy.v3_3.teaching_frame_manager import TeachingFrameManager
    tfm = getattr(_pipeline._runtime, "_teaching_frame_manager", None)
    if tfm is not None:
        active = tfm.active_frame
        if active is not None:
            info["Teaching Frame"] = {
                "frame_id": getattr(active, "frame_id", ""),
                "target_concept_key": getattr(active, "target_concept_key", ""),
                "open_slots": list(getattr(active, "open_slots", [])),
            }

    if cycle.relation_frames:
        info["Relation Frames"] = {
            "count": len(cycle.relation_frames),
            "keys": [getattr(f, "relation_key", "") for f in cycle.relation_frames],
        }

    if cycle.semantic_query is not None:
        sq = cycle.semantic_query
        info["Semantic Query"] = {
            "query_kind": getattr(sq, "query_kind", ""),
            "relation_key": getattr(sq, "relation_key", ""),
        }

    if cycle.answer_binding is not None:
        ab = cycle.answer_binding
        info["Answer Binding"] = {
            "has_answer": getattr(ab, "has_answer", False),
            "slot_count": len(getattr(ab, "slot_fills", [])),
            "confidence": getattr(ab, "confidence", 0.0),
            "abstention_reason": getattr(ab, "abstention_reason", ""),
        }

    if cycle.response_bundle is not None:
        bundle = cycle.response_bundle
        info["Response Bundle"] = {
            "text": getattr(bundle, "text", ""),
            "language": getattr(bundle, "language", ""),
            "obligation_kind": getattr(bundle, "obligation_kind", ""),
            "confidence": getattr(bundle, "confidence", 0.0),
            "move_types": [getattr(m, "move_type", "") for m in getattr(bundle, "moves", [])],
        }

    if cycle.patch_candidates:
        info["Patch Candidates"] = {
            "count": len(cycle.patch_candidates),
            "targets": list({getattr(p, "target", "") for p in cycle.patch_candidates}),
        }

    if cycle.validation:
        accepted = sum(1 for v in cycle.validation if getattr(v, "accepted", False))
        info["Validation"] = {"total": len(cycle.validation), "accepted": accepted}

    if cycle.diagnostics is not None and isinstance(cycle.diagnostics, dict):
        d = cycle.diagnostics
        commit = d.get("patch_commit")
        if commit:
            info["Patch Commit"] = {
                "count": commit.get("count", 0),
                "committed": commit.get("committed", 0),
                "durable_relations": commit.get("durable_relations", 0),
            }

    info["Cost"] = {"ms": round(cycle.cost_ms, 1)}
    info["Turn"] = _turn_count[0]

    diag = cycle.diagnostics
    if diag and isinstance(diag, dict) and diag.get("errors"):
        info["Errors"] = diag["errors"]

    return info


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CEMM — Runtime Diagnostics</title>
<style>
  :root {
    --bg: #0b0d14;
    --surface: #141720;
    --surface-2: #1a1e2b;
    --border: #262b3e;
    --border-light: #303650;
    --text: #dee0ec;
    --text-dim: #7a7f9a;
    --text-muted: #555a75;
    --accent: #7c6ef0;
    --accent-dim: #5a4ec0;
    --green: #4caf7d;
    --red: #e5555e;
    --amber: #e8b84b;
    --blue: #5b9cf5;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 14px;
    flex-shrink: 0;
  }
  header .logo {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, var(--accent), var(--accent-dim));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 15px; color: white;
  }
  header h1 { font-size: 17px; font-weight: 600; letter-spacing: -0.3px; }
  header .subtitle { font-size: 11px; color: var(--text-dim); margin-top: 1px; }
  header .spacer { flex: 1; }
  .header-badge {
    font-size: 11px; color: var(--text-muted); border: 1px solid var(--border);
    border-radius: 6px; padding: 4px 10px;
  }
  .toggle-btn {
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }
  .toggle-btn:hover { color: var(--text); border-color: var(--accent); }
  .toggle-btn.on { background: var(--accent); color: white; border-color: var(--accent); }
  .main {
    flex: 1;
    display: flex;
    flex-direction: row;
    overflow: hidden;
  }
  .chat-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    transition: flex 0.2s ease;
  }
  #debug-col {
    width: 0;
    overflow: hidden;
    background: var(--surface);
    border-left: 1px solid var(--border);
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    font-size: 11.5px;
    line-height: 1.6;
    transition: width 0.2s ease;
    display: flex;
    flex-direction: column;
  }
  #debug-col.open {
    width: 420px;
  }
  #debug-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px 24px;
  }
  #debug-scroll::-webkit-scrollbar { width: 4px; }
  #debug-scroll::-webkit-scrollbar-track { background: transparent; }
  #debug-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
  .debug-entry { margin-bottom: 14px; }
  .debug-entry .section-header {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    margin-bottom: 6px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
  }
  .debug-entry .section-header:hover { color: var(--text-dim); }
  .debug-entry .section-body { margin-left: 0; }
  .debug-row { display: flex; padding: 1px 0; }
  .debug-row .key {
    color: var(--accent);
    min-width: 110px;
    flex-shrink: 0;
  }
  .debug-row .val { color: var(--text); word-break: break-all; }
  .debug-row .val.null { color: var(--text-muted); font-style: italic; }
  .debug-row .val.num { color: var(--amber); }
  .debug-row .val.str { color: var(--green); }
  .debug-row .val.bool { color: var(--blue); }
  .debug-row .val.list { color: var(--text-dim); }
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    max-width: 760px;
    width: 100%;
    margin: 0 auto;
  }
  .chat-container::-webkit-scrollbar { width: 4px; }
  .chat-container::-webkit-scrollbar-track { background: transparent; }
  .chat-container::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
  .msg { display: flex; gap: 10px; max-width: 88%; animation: fadein 0.25s ease; }
  .msg.user { align-self: flex-end; flex-direction: row-reverse; }
  .msg.bot { align-self: flex-start; }
  .msg .av {
    width: 30px; height: 30px; border-radius: 8px;
    flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 600;
  }
  .msg.user .av { background: var(--accent); color: white; }
  .msg.bot .av { background: var(--surface-2); color: var(--text-dim); border: 1px solid var(--border); }
  .msg .bbl {
    padding: 10px 14px; border-radius: 10px;
    font-size: 13.5px; line-height: 1.55; white-space: pre-wrap;
  }
  .msg.user .bbl { background: var(--surface-2); }
  .msg.bot .bbl { background: var(--surface); border: 1px solid var(--border-light); }
  .input-area {
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 14px 24px 16px;
    flex-shrink: 0;
  }
  .input-row {
    display: flex; gap: 10px; align-items: center;
    max-width: 760px; margin: 0 auto;
  }
  .input-row input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
    color: var(--text);
    font-size: 13.5px;
    outline: none;
    font-family: inherit;
    transition: border-color 0.15s;
  }
  .input-row input:focus { border-color: var(--accent); }
  .input-row input::placeholder { color: var(--text-muted); }
  .input-row button {
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
    font-family: inherit;
  }
  .input-row button:hover { background: var(--accent-dim); }
  .input-row button:disabled { opacity: 0.4; cursor: not-allowed; }
  .suggestions {
    display: flex; gap: 6px; flex-wrap: wrap;
    max-width: 760px; margin: 8px auto 0;
  }
  .suggestions button {
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }
  .suggestions button:hover { color: var(--text); border-color: var(--accent); }
  .typing { display: flex; gap: 3px; align-items: center; padding: 6px 0; }
  .typing span {
    width: 5px; height: 5px;
    background: var(--text-muted);
    border-radius: 50%;
    animation: bounce 1.4s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes fadein { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }
  .error-badge { color: var(--red); font-size: 11px; margin-top: 4px; }
</style>
</head>
<body>
<header>
  <div class="logo">C</div>
  <div>
    <h1>CEMM</h1>
    <div class="subtitle">Contextual Event Memory Model · v3.4 cognitive kernel</div>
  </div>
  <span class="header-badge" id="turn-badge">turn 0</span>
  <div class="spacer"></div>
  <button class="toggle-btn" id="dbg-btn" onclick="toggleDebug()">Debug</button>
</header>
<div class="main">
  <div class="chat-col">
    <div class="chat-container" id="chat">
      <div class="msg bot">
        <div class="av">AI</div>
        <div><div class="bbl">Hello! I'm CEMM. Try typing a message below.</div></div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-row">
        <input type="text" id="inp" placeholder="Type a message…" autocomplete="off" autofocus>
        <button id="send-btn" onclick="send()">Send</button>
      </div>
      <div class="suggestions">
        <button onclick="pick('hi')">hi</button>
        <button onclick="pick('remember I like coffee')">remember I like coffee</button>
        <button onclick="pick('what do I like?')">what do I like?</button>
        <button onclick="pick('how are you?')">how are you?</button>
        <button onclick="pick('who are you?')">who are you?</button>
        <button onclick="pick('what can you do?')">what can you do?</button>
        <button onclick="pick('reflect')">reflect</button>
        <button onclick="pick('hiii')">hiii</button>
      </div>
    </div>
  </div>
  <div id="debug-col">
    <div id="debug-scroll"></div>
  </div>
</div>
<script>
const chat = document.getElementById('chat');
const inp = document.getElementById('inp');
const sendBtn = document.getElementById('send-btn');
const debugCol = document.getElementById('debug-col');
const debugScroll = document.getElementById('debug-scroll');
const dbgBtn = document.getElementById('dbg-btn');
const turnBadge = document.getElementById('turn-badge');
let debugOn = false;
const debugTurns = [];
const cemmContextId = (() => {
  const key = 'cemm.web_demo.context_id';
  let value = localStorage.getItem(key);
  if (!value) {
    value = (globalThis.crypto && crypto.randomUUID)
      ? crypto.randomUUID()
      : 'web-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
    localStorage.setItem(key, value);
  }
  return value;
})();
inp.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
function pick(t) { inp.value = t; send(); }
function toggleDebug() {
  debugOn = !debugOn;
  dbgBtn.classList.toggle('on', debugOn);
  if (debugOn && debugTurns.length) renderDebugAll();
  else debugCol.classList.remove('open');
}
function esc(v) {
  if (v === null || v === undefined) return '<span class="null">null</span>';
  if (typeof v === 'boolean') return '<span class="bool">' + v + '</span>';
  if (typeof v === 'number') return '<span class="num">' + v + '</span>';
  if (Array.isArray(v)) {
    if (v.length === 0) return '<span class="null">[]</span>';
    const items = v.map(x => typeof x === 'string' ? '"' + x + '"' : String(x)).join(', ');
    return '<span class="list">[' + items + ']</span>';
  }
  if (typeof v === 'object') return '<span class="num">{' + Object.keys(v).length + ' keys}</span>';
  return '<span class="str">"' + String(v).replace(/"/g, '\\"') + '"</span>';
}
function renderEntry(turn, data) {
  let html = '<div class="debug-entry">';
  let first = true;
  for (const [section, fields] of Object.entries(data)) {
    if (section === 'Turn' && typeof fields === 'number') continue;
    html += '<div class="section-header">' + (first ? 'Turn ' + turn + ' — ' : '') + section + '</div>';
    first = false;
    if (typeof fields === 'object' && fields !== null && !Array.isArray(fields)) {
      html += '<div class="section-body">';
      for (const [k, v] of Object.entries(fields)) {
        html += '<div class="debug-row"><span class="key">' + k + '</span><span class="val">' + esc(v) + '</span></div>';
      }
      html += '</div>';
    } else {
      html += '<div class="section-body"><div class="debug-row"><span class="key">value</span><span class="val">' + esc(fields) + '</span></div></div>';
    }
  }
  html += '</div>';
  return html;
}
function renderDebugAll() {
  debugScroll.innerHTML = debugTurns.map((d, i) => renderEntry(i + 1, d)).join('<hr style="border-color:var(--border);margin:6px 0">');
  if (debugOn) debugCol.classList.add('open');
}
function addMsg(text, isUser) {
  const d = document.createElement('div');
  d.className = 'msg ' + (isUser ? 'user' : 'bot');
  d.innerHTML = '<div class="av">' + (isUser ? 'You' : 'AI') + '</div><div><div class="bbl">' + text.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div></div>';
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}
function addTyping() {
  const d = document.createElement('div');
  d.id = 't-indicator';
  d.className = 'msg bot';
  d.innerHTML = '<div class="av">AI</div><div class="bbl"><div class="typing"><span></span><span></span><span></span></div></div>';
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}
function rmTyping() { const el = document.getElementById('t-indicator'); if (el) el.remove(); }
async function send() {
  const text = inp.value.trim();
  if (!text) return;
  inp.value = '';
  sendBtn.disabled = true;
  addMsg(text, true);
  addTyping();
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, context_id: cemmContextId}),
    });
    const data = await r.json();
    rmTyping();
    addMsg(data.response || '(empty)', false);
    turnBadge.textContent = 'turn ' + (data.turn || '?');
    if (data.debug) {
      debugTurns.push(data.debug);
      if (debugOn) renderDebugAll();
    }
  } catch (err) {
    rmTyping();
    addMsg('Error: ' + err.message, false);
  }
  sendBtn.disabled = false;
  inp.focus();
}
</script>
</body>
</html>"""


class CEMMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
                text = data.get("text", "")
                context_id = str(data.get("context_id", "") or _context_id)
                context_turn = [_pipeline._runtime.session_store.get_turn_count(context_id)]
                output = process_input(
                    text, _pipeline, context_id, context_turn,
                )
                payload: dict = {"response": output, "turn": context_turn[0], "context_id": context_id}
                if _DEBUG:
                    cycle = getattr(_pipeline._runtime, "_last_cycle", None)
                    if cycle:
                        payload["debug"] = _extract_debug(cycle)
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                body = json.dumps({"response": f"Error: {e}", "turn": _turn_count[0], "_trace": tb}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        if _DEBUG:
            BaseHTTPRequestHandler.log_message(self, fmt, *args)


def _patch_runtime() -> None:
    """Hook into Pipeline to capture the latest RuntimeCycleResult."""
    orig = _pipeline._runtime.run_turn

    def hooked(signal, kernel, **kw):
        cycle = orig(signal, kernel, **kw)
        _pipeline._runtime._last_cycle = cycle
        return cycle

    _pipeline._runtime.run_turn = hooked


_patch_runtime()


if __name__ == "__main__":
    port = 5000
    import argparse
    _ap = argparse.ArgumentParser(description="CEMM Web Demo")
    _ap.add_argument("--port", type=int, default=5000)
    _ap.add_argument("--debug", action="store_true")
    _args, _ = _ap.parse_known_args()
    port = _args.port
    _DEBUG = _args.debug
    print(f"CEMM Web Demo at http://127.0.0.1:{port}" + (" (debug)" if _DEBUG else ""))
    print("Press Ctrl+C to stop.")
    HTTPServer(("127.0.0.1", port), CEMMHandler).serve_forever()
