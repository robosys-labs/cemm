#!/usr/bin/env python3
"""CEMM v1 language-pack trainer.

Compiles reviewed text+meaning examples into *structured supervision*.
It deliberately does NOT serialize a closed semantic program class. Interpretation
supervision is decomposed into intent, application slots, operators and binding
sources. Definition supervision is decomposed into antecedent/consequent graph slots.
Surface realization remains a learned language plan over exact semantic pointers.
"""
from __future__ import annotations
import argparse, hashlib, json, re, unicodedata
from pathlib import Path
from typing import Any

MAX_ANCHORS=8
MAX_APPS=3
MAX_RULE_IF=3
MAX_RULE_THEN=3
SOURCE_CLASSES=["NONE","USER","SYSTEM"]+[f"A{i}" for i in range(MAX_ANCHORS)]+["NEW_ENTITY_0","NEW_ENTITY_1","NEW_EVENT_0","NEW_EVENT_1"]
RULE_SOURCES=["NONE"]+[f"A{i}" for i in range(MAX_ANCHORS)]+["V0","V1","V2","E0","E1"]

def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def norm(s):return unicodedata.normalize("NFKC",str(s))
def pack_hash(x):return hashlib.sha256(canonical(x).encode()).hexdigest()

def load_kinds(paths):
    out={}
    for p in paths:
        d=json.loads(Path(p).read_text(encoding="utf-8"))
        for a in d.get("atoms",[]):out[a["ref"]]=a["kind"]
    out.setdefault("participant:user","participant");out.setdefault("participant:system","participant")
    return out

def replace_mentions(surface:str,mentions:list[dict[str,Any]],kind_map:dict[str,str]):
    refs=[]
    for m in mentions:
        if m["ref"] not in refs:refs.append(m["ref"])
    ref_to_ph={r:f"A{i}" for i,r in enumerate(refs)}
    spans=[]
    for m in mentions:
        q=m["surface"]
        for hit in re.finditer(r"(?<!\w)"+re.escape(q)+r"(?!\w)",surface,flags=re.I|re.UNICODE):spans.append((hit.start(),hit.end(),len(q),m["ref"]))
    chosen=[]
    for x in sorted(spans,key=lambda z:(z[0],-z[2])):
        if not any(x[0]<y[1] and x[1]>y[0] for y in chosen):chosen.append(x)
    out=[];p=0
    for a,b,_,ref in sorted(chosen):
        out.append(surface[p:a]);kind=next((m.get("kind") for m in mentions if m["ref"]==ref and m.get("kind")),None) or kind_map.get(ref,"atom");out.append(f"@{ref_to_ph[ref]}<{kind}>");p=b
    out.append(surface[p:])
    return "".join(out),ref_to_ph

def source_for(v,ref_to_ph,new_map):
    if isinstance(v,str) and v in ref_to_ph:return ref_to_ph[v]
    if v=="participant:user":return "USER"
    if v=="participant:system":return "SYSTEM"
    if isinstance(v,str) and v in new_map:return new_map[v]
    if isinstance(v,dict) and "literal" in v:return "NONE"
    # Unanchored domain constants are intentionally not teachable through the language codec.
    return None

def structured_target(semantic,ref_to_ph):
    new_map={};ec=vc=0
    for n in semantic.get("new",[]):
        if n["kind"]=="entity":new_map[n["token"]]=f"NEW_ENTITY_{ec}";ec+=1
        elif n["kind"]=="event":new_map[n["token"]]=f"NEW_EVENT_{vc}";vc+=1
    if semantic.get("describe"):
        s=source_for(semantic["describe"],ref_to_ph,new_map)
        if not s:raise ValueError("describe target must be grounded")
        return {"intent":"describe","describe_source":s,"apps":[]}
    query=semantic.get("query")
    apps=[query] if query else semantic.get("apps",[])
    intent="query" if query else "assert"
    out=[]
    for a in apps[:MAX_APPS]:
        binds={}
        for role,v in a.get("args",{}).items():
            # State dimension may be reconstructed from a grounded value in exact meaning data.
            if a["operator"]=="op:state" and role=="role:dimension" and source_for(v,ref_to_ph,new_map) is None:continue
            s=source_for(v,ref_to_ph,new_map)
            if s:binds[role]=s
        out.append({"operator":a["operator"],"bindings":binds})
    return {"intent":intent,"describe_source":"NONE","apps":out}

def rule_value(v,ref_to_ph,var_map):
    if isinstance(v,str) and v in ref_to_ph:return ref_to_ph[v]
    if isinstance(v,str) and v in var_map:return var_map[v]
    return None

def rule_target(rule,ref_to_ph):
    vars_seen=[];exists=[]
    for side in (rule.get("if",[]),rule.get("then",[])):
        for a in side:
            for v in a.get("args",{}).values():
                if isinstance(v,str) and v.startswith("?") and v not in vars_seen:vars_seen.append(v)
                if isinstance(v,str) and v.startswith("!") and v not in exists:exists.append(v)
    vm={v:f"V{i}" for i,v in enumerate(vars_seen[:3])};vm.update({v:f"E{i}" for i,v in enumerate(exists[:2])})
    def side(xs,maxn):
        out=[]
        for a in xs[:maxn]:
            b={}
            for r,v in a.get("args",{}).items():
                q=rule_value(v,ref_to_ph,vm)
                if not q:raise ValueError(f"rule constant must be mention-grounded or variable: {v}")
                b[r]=q
            out.append({"operator":a["operator"],"bindings":b})
        return out
    return {"rule_kind":rule.get("rule_kind","definition"),"if":side(rule.get("if",[]),MAX_RULE_IF),"then":side(rule.get("then",[]),MAX_RULE_THEN)}

def realization_refs(x):
    refs=[]
    def add(v):
        if isinstance(v,str) and ":" in v and v not in refs:refs.append(v)
    if "plan" in x:
        p=x["plan"]
        if p.get("value"):add(p["value"])
        for f in p.get("facts",[]):
            for _,v in sorted(f.get("args",{}).items()):add(v)
    else:
        for _,v in sorted(x["fact"].get("args",{}).items()):add(v)
    return {r:f"@A{i}" for i,r in enumerate(refs)}

def replace_with_map(surface,mentions,refs):
    spans=[]
    for m in mentions:
        if m["ref"] not in refs:continue
        for hit in re.finditer(r"(?<!\w)"+re.escape(m["surface"])+r"(?!\w)",surface,flags=re.I|re.UNICODE):spans.append((hit.start(),hit.end(),len(m["surface"]),refs[m["ref"]]))
    chosen=[]
    for x in sorted(spans,key=lambda z:(z[0],-z[2])):
        if not any(x[0]<y[1] and x[1]>y[0] for y in chosen):chosen.append(x)
    out=[];p=0
    for a,b,_,ph in sorted(chosen):out += [surface[p:a],ph];p=b
    out.append(surface[p:]);return "".join(out)

def val(v,refs):
    if isinstance(v,str) and v in refs:return refs[v]
    if isinstance(v,dict) and "literal" in v:return f"lit:{v['literal']['type']}:{v['literal']['value']}"
    return str(v)
def serialize_fact(f,refs):
    parts=["FACT",f.get("stance","support"),f["operator"]]
    for r,v in sorted(f.get("args",{}).items()):parts += [r,val(v,refs)]
    return " ".join(parts)
def serialize_plan(plan,refs):
    parts=["PLAN",plan["goal"]]
    if plan.get("value"):parts += ["VALUE",val(plan["value"],refs)]
    for f in plan.get("facts",[]):parts += ["|",serialize_fact(f,refs)]
    return " ".join(parts)

def compile_corpus(corpus:Path,knowledge_paths:list[Path]):
    d=json.loads(corpus.read_text(encoding="utf-8"));kinds=load_kinds(knowledge_paths);lang=d["language"]
    out={"version":4,"language":lang,"source_classes":SOURCE_CLASSES,"rule_sources":RULE_SOURCES,"operators":[],"roles":[],"structured_examples":[],"rule_examples":[],"realization_examples":[],"grammar_tokens":[]}
    for i,x in enumerate(d.get("interpretation_examples",[])):
        inp,refs=replace_mentions(x["surface"],x.get("mentions",[]),kinds);target=structured_target(x["semantic"],refs)
        out["structured_examples"].append({"example_ref":x.get("example_ref",f"{lang}:s:{i}"),"input":inp,"target":target,"weight":float(x.get("weight",1))})
    for i,x in enumerate(d.get("definition_examples",[])):
        inp,refs=replace_mentions(x["surface"],x.get("mentions",[]),kinds);target=rule_target(x["rule"],refs)
        out["rule_examples"].append({"example_ref":x.get("example_ref",f"{lang}:d:{i}"),"input":inp,"target":target,"weight":float(x.get("weight",1))})
    for i,x in enumerate(d.get("realization_examples",[])):
        refs=realization_refs(x);delex=replace_with_map(x["surface"],x.get("mentions",[]),refs);sem=serialize_plan(x["plan"],refs) if "plan" in x else serialize_fact(x["fact"],refs)
        out["realization_examples"].append({"example_ref":x.get("example_ref",f"{lang}:r:{i}"),"semantic":sem,"surface_plan":delex,"weight":float(x.get("weight",1))})
        out["grammar_tokens"].extend(t for t in re.findall(r"@[A-Z]\d+|[\wÀ-ÿ'’-]+|[^\w\s]",delex,re.UNICODE) if not t.startswith("@A"))
    ops=set();roles=set()
    for ex in out["structured_examples"]:
        for a in ex["target"].get("apps",[]):ops.add(a["operator"]);roles.update(a.get("bindings",{}))
    for ex in out["rule_examples"]:
        for side in ("if","then"):
            for a in ex["target"].get(side,[]):ops.add(a["operator"]);roles.update(a.get("bindings",{}))
    out["operators"]=sorted(ops);out["roles"]=sorted(roles)
    out["grammar_tokens"]=sorted(set(t.casefold() for t in out["grammar_tokens"]));out["pack_hash"]=pack_hash({k:v for k,v in out.items() if k!="pack_hash"});return out

def main():
    p=argparse.ArgumentParser();p.add_argument("corpus");p.add_argument("output");p.add_argument("--knowledge",action="append",default=[]);a=p.parse_args();pack=compile_corpus(Path(a.corpus),[Path(x) for x in a.knowledge]);Path(a.output).write_text(json.dumps(pack,ensure_ascii=False,indent=2),encoding="utf-8");print(pack["pack_hash"])
if __name__=="__main__":main()
