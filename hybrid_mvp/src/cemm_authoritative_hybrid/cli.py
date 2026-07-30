from __future__ import annotations
import argparse,json
from pathlib import Path
from .bootstrap import load_runtime

DEMO_TURNS=[
    "hello",
    "what can you do",
    "can you learn",
    "alice is bob mother-in-law",
    "is bob married",
    "mary said bob left",
    "did bob leave",
    "did mary say bob left",
    "do you have a telescope",
    "server is offline",
    "imagine server is online",
    "turn lamp on",
    "yoz means hello",
]

def demo(runtime,trace=False):
    rows=[]
    for text in DEMO_TURNS:
        row=runtime.process(text,trace=trace); rows.append(row)
        print(f"USER: {text}")
        print(f"CEMM: {row['response']}")
        print(f"      family={row['selected_family']} status={row['meaning']['status']} session={row['session_phase']}")
    runtime.new_session()
    row=runtime.process("yoz",trace=trace); rows.append(row)
    print("USER: yoz")
    print(f"CEMM: {row['response']}")
    print("      dynamic alias reused in a new session")
    return rows

def interactive(runtime,trace=False):
    print("CEMM authoritative hybrid MVP. /new, /trace, /state, /quit")
    tracing=trace
    while True:
        try: text=input("you> ").strip()
        except EOFError: print(); break
        if not text: continue
        if text=="/quit": break
        if text=="/new": runtime.new_session(); print("cemm> new root session event"); continue
        if text=="/trace": tracing=not tracing; print(f"cemm> trace={tracing}"); continue
        if text=="/state":
            print(json.dumps({"session":runtime.session.__dict__,"world_revision":runtime.stores.world.revision,"facts":[f.__dict__ for f in runtime.stores.world.facts]},indent=2,default=str)); continue
        row=runtime.process(text,trace=tracing); print("cemm>",row["response"])
        if tracing: print(json.dumps(row,indent=2,default=str))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--demo",action="store_true")
    parser.add_argument("--interactive",action="store_true")
    parser.add_argument("--trace",action="store_true")
    args=parser.parse_args(); runtime=load_runtime(args.root)
    if args.demo: demo(runtime,args.trace)
    else: interactive(runtime,args.trace)

if __name__=="__main__": main()
