#!/usr/bin/env python3
"""Compile language training corpora into CEMM language packs.

The trainer is deliberately language-generic.  Training corpora provide natural
surface examples plus reviewed semantic structures/mention anchors.  This script:
1. delexicalizes semantic mentions;
2. serializes the universal semantic structure into executable program classes;
3. derives meaning->surface pointer plans;
4. writes a pack consumed by the runtime's Transformer classifiers.

No language examples live in the foundational meaning DB.
"""
from __future__ import annotations
import argparse, hashlib, json, re, unicodedata
from pathlib import Path
from typing import Any

def canonical(x): return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def stable(prefix,*parts): return f"{prefix}:{hashlib.sha256(canonical(parts).encode()).hexdigest()[:24]}"
def norm(s): return unicodedata.normalize("NFKC",str(s))

def replace_mentions(surface:str, mentions:list[dict[str,Any]], ref_to_ph=None):
    # One semantic ref gets one pointer even if several surface mentions/coreferences refer to it.
    if ref_to_ph is None:
        refs=[]
        for m in mentions:
            if m["ref"] not in refs: refs.append(m["ref"])
        ref_to_ph={r:f"@A{i}" for i,r in enumerate(refs)}
    spans=[]
    for m in mentions:
        q=m["surface"]
        for hit in re.finditer(r"(?<!\w)"+re.escape(q)+r"(?!\w)",surface,flags=re.I|re.UNICODE):
            spans.append((hit.start(),hit.end(),len(q),ref_to_ph[m["ref"]]))
    chosen=[]
    for x in sorted(spans,key=lambda z:(z[0],-z[2])):
        if not any(x[0]<y[1] and x[1]>y[0] for y in chosen): chosen.append(x)
    out=[]; p=0
    for a,b,_,ph in sorted(chosen): out.extend([surface[p:a],ph]); p=b
    out.append(surface[p:])
    return "".join(out),ref_to_ph

def val(v, refs):
    if isinstance(v,str) and v in refs:return refs[v]
    if isinstance(v,dict) and "literal" in v:
        q=v["literal"]; return f"lit:{q['type']}:{q['value']}"
    return str(v)

def serialize_program(sem, refs):
    parts=[]
    for n in sem.get("new",[]):parts.append(f"new {n['token']} {n['kind']}")
    for i,a in enumerate(sem.get("apps",[])):
        args=" ".join(f"{r}={val(v,refs)}" for r,v in a.get("args",{}).items())
        parts.append(f"app g{i} {a['operator']} {args}".strip())
    if sem.get("query"):
        q=sem["query"]; args=" ".join(f"{r}={val(v,refs)}" for r,v in q.get("args",{}).items()); parts.append(f"query {q['operator']} {args}".strip())
    if sem.get("describe"):parts.append(f"describe {val(sem['describe'],refs)}")
    return " | ".join(parts)

def serialize_fact(f, refs):
    parts=["FACT",f.get("stance","support"),f["operator"]]
    for r,v in sorted(f.get("args",{}).items()):parts += [r,val(v,refs)]
    return " ".join(parts)

def serialize_plan(plan, refs):
    parts=["PLAN",plan["goal"]]
    if plan.get("value"): parts += ["VALUE",val(plan["value"],refs)]
    for f in plan.get("facts",[]):parts += ["|",serialize_fact(f,refs)]
    return " ".join(parts)



def realization_refs(x):
    refs=[]
    def add(v):
        if isinstance(v,str) and ':' in v and v not in refs: refs.append(v)
    if "plan" in x:
        p=x["plan"]
        if p.get("value"): add(p["value"])
        for f in p.get("facts",[]):
            for _,v in sorted(f.get("args",{}).items()): add(v)
    else:
        for _,v in sorted(x["fact"].get("args",{}).items()): add(v)
    return {r:f"@A{i}" for i,r in enumerate(refs)}

def compile_corpus(path:Path):
    d=json.loads(path.read_text(encoding="utf-8")); lang=d["language"]; out={"language":lang,"interpretation_examples":[],"realization_examples":[],"grammar_tokens":[]}
    for i,x in enumerate(d.get("interpretation_examples",[])):
        delex,refs=replace_mentions(x["surface"],x.get("mentions",[])); program=serialize_program(x["semantic"],refs)
        out["interpretation_examples"].append({"example_ref":x.get("example_ref",f"{lang}:i:{i}"),"language":lang,"delex_surface":delex,"program":program,"weight":float(x.get("weight",1))})
    for i,x in enumerate(d.get("realization_examples",[])):
        refs=realization_refs(x); delex,_=replace_mentions(x["surface"],x.get("mentions",[]),refs)
        sem=serialize_plan(x["plan"],refs) if "plan" in x else serialize_fact(x["fact"],refs)
        out["realization_examples"].append({"example_ref":x.get("example_ref",f"{lang}:r:{i}"),"language":lang,"semantic":sem,"surface_plan":delex,"weight":float(x.get("weight",1))})
        # All non-pointer surface tokens form the learned grammar vocabulary.
        out["grammar_tokens"].extend(t for t in re.findall(r"@[A-Z]\d+|[\wÀ-ÿ'’-]+|[^\w\s]",delex,re.UNICODE) if not t.startswith("@A"))
    out["grammar_tokens"]=sorted(set(t.casefold() for t in out["grammar_tokens"]))
    out["pack_hash"]=hashlib.sha256(canonical({k:v for k,v in out.items() if k!="pack_hash"}).encode()).hexdigest()
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument("corpus"); p.add_argument("output"); a=p.parse_args(); pack=compile_corpus(Path(a.corpus)); Path(a.output).write_text(json.dumps(pack,ensure_ascii=False,indent=2),encoding="utf-8"); print(pack["pack_hash"])
if __name__=="__main__":main()
