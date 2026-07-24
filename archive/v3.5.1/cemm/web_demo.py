"""Small stdlib web demo for the canonical CEMM v3.5.1 runtime."""
from __future__ import annotations
import argparse,json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs,urlparse
from .app.runtime import Runtime
from .v350.cutover import RuntimeAuthorityError

HTML="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CEMM v3.5.1 Web Demo</title><style>:root{font-family:Inter,system-ui,sans-serif}body{margin:0;background:#f4f6f8;color:#17202a}main{max-width:920px;margin:auto;padding:24px}#log{min-height:420px;border:1px solid #c9d2dc;background:white;padding:14px;overflow:auto}.turn{margin:0 0 12px}.speaker{font-weight:700}form{display:grid;grid-template-columns:1fr auto;gap:10px;margin-top:12px}input,button{font:inherit;min-height:42px}input{padding:0 12px}button{padding:0 16px}pre{white-space:pre-wrap;background:#edf1f5;padding:12px}</style></head><body><main><header><h1>CEMM Web Demo</h1><div>canonical v3.5.1 runtime</div></header><section id="log"></section><form id="chat"><input id="text" autocomplete="off" autofocus placeholder="Type a message"><button>Send</button></form><details><summary>Trace</summary><pre id="trace">{}</pre></details></main><script>const log=document.querySelector('#log'),trace=document.querySelector('#trace'),form=document.querySelector('#chat'),input=document.querySelector('#text'),contextId='web-demo:'+crypto.randomUUID();function addTurn(who,text){const p=document.createElement('p');p.className='turn';const s=document.createElement('span');s.className='speaker';s.textContent=who+': ';p.append(s,document.createTextNode(text));log.append(p)}form.addEventListener('submit',async e=>{e.preventDefault();const text=input.value.trim();if(!text)return;input.value='';addTurn('You',text);const r=await fetch('/api/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({text,context_id:contextId,include_trace:true})});const x=await r.json();addTurn('CEMM',x.output_text||'[no semantically authorized surface output]');trace.textContent=JSON.stringify(x.trace||{},null,2)});</script></body></html>"""

class UnavailableRuntime:
    VERSION=Runtime.VERSION
    def __init__(self,error:str)->None:self.error=error
    def close(self)->None:return None


def handle_chat(runtime:Runtime|UnavailableRuntime,payload:dict[str,Any])->dict[str,Any]:
    text=str(payload.get('text','')).strip()
    if not text:return {'ok':False,'error':'empty_text'}
    if isinstance(runtime,UnavailableRuntime):
        return {'ok':False,'error':'runtime_authority_unavailable','output_text':None,'trace':{'activation_error':runtime.error}}
    result=runtime.run_text(text,context_id=str(payload.get('context_id') or 'web-demo'),language_hint=payload.get('language'),target_language=payload.get('target_language'))
    response={'ok':True,'output_text':result.output_text,'cycle_id':result.cycle_id,'context_id':result.context_id,'target_language':result.target_language,'emission_authorized':result.emitted,'frontier_refs':list(result.frontier_refs),'errors':list(result.errors)}
    if payload.get('include_trace'):response['trace']={'stages':list(result.trace.stages),'details':result.trace.details,'errors':list(result.trace.errors)}
    return response

class DemoHandler(BaseHTTPRequestHandler):
    runtime:Runtime|UnavailableRuntime
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path in {'','/'}:return self._send(HTTPStatus.OK,HTML.encode(),'text/html; charset=utf-8')
        if parsed.path=='/health':
            if isinstance(self.runtime,UnavailableRuntime):return self._send_json({'ok':False,'version':Runtime.VERSION,'error':'runtime_authority_unavailable','detail':self.runtime.error},status=HTTPStatus.SERVICE_UNAVAILABLE)
            return self._send_json({'ok':True,'version':Runtime.VERSION})
        if parsed.path=='/api/chat':
            q=parse_qs(parsed.query);return self._send_json(handle_chat(self.runtime,{'text':q.get('text',[''])[0],'context_id':q.get('context_id',['web-demo'])[0],'include_trace':q.get('trace',[''])[0] in {'1','true','yes'}}))
        self._send_json({'ok':False,'error':'not_found'},status=HTTPStatus.NOT_FOUND)
    def do_POST(self):
        if urlparse(self.path).path!='/api/chat':return self._send_json({'ok':False,'error':'not_found'},status=HTTPStatus.NOT_FOUND)
        raw=self.rfile.read(int(self.headers.get('content-length','0') or '0'))
        try:payload=json.loads(raw.decode() or '{}')
        except json.JSONDecodeError:return self._send_json({'ok':False,'error':'invalid_json'},status=HTTPStatus.BAD_REQUEST)
        self._send_json(handle_chat(self.runtime,payload))
    def log_message(self,format,*args):return
    def _send_json(self,payload,*,status=HTTPStatus.OK):self._send(status,json.dumps(payload,ensure_ascii=False,default=str).encode(),'application/json; charset=utf-8')
    def _send(self,status,body,content_type):self.send_response(status);self.send_header('content-type',content_type);self.send_header('content-length',str(len(body)));self.end_headers();self.wfile.write(body)

def serve(host='127.0.0.1',port=8765,database_path=':memory:'):
    try:runtime:Runtime|UnavailableRuntime=Runtime(database_path=database_path)
    except RuntimeAuthorityError as exc:runtime=UnavailableRuntime(str(exc))
    DemoHandler.runtime=runtime;server=ThreadingHTTPServer((host,port),DemoHandler)
    try:print(f'CEMM v3.5.1 web demo listening at http://{host}:{port}');server.serve_forever()
    finally:server.server_close();runtime.close()

def main():
    p=argparse.ArgumentParser(description='CEMM v3.5.1 web demo');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765);p.add_argument('--database',default=':memory:');a=p.parse_args();serve(a.host,a.port,a.database)
if __name__=='__main__':main()
