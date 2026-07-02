"""
CEMM Web Demo — stdlib-only chat UI for browser testing.
Uses http.server (no external dependencies).
"""
from __future__ import annotations

import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "cemm")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.abstain import AbstainOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.reflect import ReflectOperator
from cemm.operators.update_claim import UpdateClaimOperator
from cemm.operators.create_model import CreateModelOperator
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.operators.simulate import SimulateOperator
from cemm.operators.synthesize import SynthesizeOperator
from cemm.operators.call_tool import CallToolOperator
from cemm.operators.learn import LearnOperator
from cemm.types.action import ActionKind
from cemm.__main__ import process_input, seed_registry, seed_self_state

# Global state — single session for demo
_store = Store(":memory:")
_registry = Registry()
_op_registry = OperatorRegistry()
_pipeline = Pipeline(_store, _registry)
_online_learner = OnlineLearner(_store.source_trust, _store.self_store, _store.claims, _store.models)
_inductor = Inductor(_store)
_recursive_loop = RecursiveLoop(_pipeline, _store, _online_learner, _inductor)

seed_registry(_registry)
seed_self_state(_store)

for op in [
    AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator(),
    ReflectOperator(), UpdateClaimOperator(), CreateModelOperator(),
    RetrieveOperator(), SimulateOperator(), SynthesizeOperator(), CallToolOperator(),
]:
    _op_registry.register(op)

# Learning operators share the pipeline's lexeme memory.
_learn_mem = _pipeline._lexeme_memory
_op_registry.register(LearnOperator(lexeme_memory=_learn_mem, action_kind=ActionKind.LEARN_LEXEME))
_op_registry.register(LearnOperator(lexeme_memory=_learn_mem, action_kind=ActionKind.LEARN_COMMAND_ALIAS))
_op_registry.register(LearnOperator(lexeme_memory=_learn_mem, action_kind=ActionKind.LEARN_CORRECTION))

_context_id = "web_demo"
_turn_count = [0]

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CEMM — Contextual Event Memory Model</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface-hover: #222636;
    --border: #2a2e3e;
    --text: #e4e6ef;
    --text-dim: #8b8fa3;
    --accent: #7c6ef0;
    --accent-dim: #5a4ec0;
    --user-bubble: #2d3142;
    --bot-bubble: #1e212e;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  header .logo {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--accent), var(--accent-dim));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 16px; color: white;
  }
  header h1 { font-size: 18px; font-weight: 600; }
  header .subtitle { font-size: 12px; color: var(--text-dim); margin-top: 2px; }
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
  }
  .message {
    display: flex;
    gap: 12px;
    max-width: 85%;
    animation: fadeIn 0.3s ease;
  }
  .message.user { align-self: flex-end; flex-direction: row-reverse; }
  .message.bot { align-self: flex-start; }
  .message .avatar {
    width: 32px; height: 32px;
    border-radius: 8px;
    flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 600;
  }
  .message.user .avatar { background: var(--accent); color: white; }
  .message.bot .avatar { background: var(--surface-hover); color: var(--text-dim); }
  .message .bubble {
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.5;
    white-space: pre-wrap;
  }
  .message.user .bubble { background: var(--user-bubble); }
  .message.bot .bubble { background: var(--bot-bubble); border: 1px solid var(--border); }
  .input-area {
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 16px 24px;
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
  }
  .input-wrapper {
    display: flex;
    gap: 12px;
    align-items: center;
  }
  .input-wrapper input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .input-wrapper input:focus { border-color: var(--accent); }
  .input-wrapper button {
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }
  .input-wrapper button:hover { background: var(--accent-dim); }
  .input-wrapper button:disabled { opacity: 0.5; cursor: not-allowed; }
  .suggestions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 12px;
  }
  .suggestions button {
    background: var(--surface-hover);
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .suggestions button:hover { color: var(--text); border-color: var(--accent); }
  .typing { display: flex; gap: 4px; align-items: center; }
  .typing span {
    width: 6px; height: 6px;
    background: var(--text-dim);
    border-radius: 50%;
    animation: bounce 1.4s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }
</style>
</head>
<body>
<header>
  <div class="logo">C</div>
  <div>
    <h1>CEMM</h1>
    <div class="subtitle">Contextual Event Memory Model</div>
  </div>
</header>
<div class="chat-container" id="chat">
  <div class="message bot">
    <div class="avatar">AI</div>
    <div><div class="bubble">Hello! I'm CEMM. I can remember facts, answer questions, reflect on my state, and retrieve stored knowledge. Try typing a command or asking a question.</div></div>
  </div>
</div>
<div class="input-area">
  <div class="input-wrapper">
    <input type="text" id="input" placeholder="Type a message..." autocomplete="off" autofocus>
    <button id="send" onclick="send()">Send</button>
  </div>
  <div class="suggestions">
    <button onclick="quick('remember I like coffee')">remember I like coffee</button>
    <button onclick="quick('what do I like?')">what do I like?</button>
    <button onclick="quick('reflect on your state')">reflect on your state</button>
    <button onclick="quick('retrieve claims about user')">retrieve claims</button>
    <button onclick="quick('hello')">hello</button>
    <button onclick="quick('rember I like tea')">rember I like tea (typo)</button>
    <button onclick="quick('exit')">exit</button>
  </div>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
function quick(text) { input.value = text; send(); }
function addMessage(text, isUser) {
  const msg = document.createElement('div');
  msg.className = 'message ' + (isUser ? 'user' : 'bot');
  const div = document.createElement('div');
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  div.appendChild(bubble);
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = isUser ? 'You' : 'AI';
  msg.appendChild(avatar);
  msg.appendChild(div);
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}
function addTyping() {
  const msg = document.createElement('div');
  msg.id = 'typing-indicator';
  msg.className = 'message bot';
  msg.innerHTML = '<div class="avatar">AI</div><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}
function removeTyping() { const el = document.getElementById('typing-indicator'); if (el) el.remove(); }
async function send() {
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  sendBtn.disabled = true;
  addMessage(text, true);
  addTyping();
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await resp.json();
    removeTyping();
    addMessage(data.response || '(no response)', false);
  } catch (err) {
    removeTyping();
    addMessage('Error: ' + err.message, false);
  }
  sendBtn.disabled = false;
  input.focus();
}
</script>
</body>
</html>"""


class CEMMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
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
            content_length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(content_length)
            try:
                data = json.loads(raw)
                text = data.get("text", "")
                output = process_input(
                    text, _store, _registry, _op_registry, _pipeline,
                    _online_learner, _recursive_loop, _context_id, _turn_count,
                )
                response = json.dumps({"response": output, "turn": _turn_count[0]})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(response.encode("utf-8"))
            except Exception as e:
                response = json.dumps({"response": f"Error: {e}", "turn": _turn_count[0]})
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = 5000
    print(f"CEMM Web Demo running at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")
    server = HTTPServer(("127.0.0.1", port), CEMMHandler)
    server.serve_forever()
