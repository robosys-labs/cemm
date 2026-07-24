#!/usr/bin/env python3
"""CEMM minimal semantic brain MVP.

Invariant code knows only:
  opaque atoms, a fixed universal operator algebra, role bindings, evidence,
  exact claims, generic graph rules, referent/label ranking, learned language
  codecs, bounded inference, queries, and verified meaning->language output.

Domain-specific concepts and relationships are atoms/rules/data, never Python branches or schema classes.
New domain detail grows knowledge, not the database schema or Python branches.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, math, random, re, sqlite3, sys, unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:
    import torch
    from torch import nn
except Exception as exc:
    raise SystemExit("pip install torch") from exc

torch.set_num_threads(1)

DDL = r"""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS atoms(ref TEXT PRIMARY KEY,kind TEXT NOT NULL,metadata TEXT NOT NULL DEFAULT '{}',generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS operator_roles(operator_ref TEXT NOT NULL,role_ref TEXT NOT NULL,required INTEGER NOT NULL DEFAULT 0,cardinality TEXT NOT NULL DEFAULT 'one',filler_kind TEXT,PRIMARY KEY(operator_ref,role_ref));
CREATE TABLE IF NOT EXISTS applications(app_ref TEXT PRIMARY KEY,operator_ref TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS bindings(binding_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,role_ref TEXT NOT NULL,filler_kind TEXT NOT NULL CHECK(filler_kind IN('atom','literal','app')),filler_value TEXT NOT NULL,ordinal INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS observations(observation_ref TEXT PRIMARY KEY,surface TEXT NOT NULL,modality TEXT NOT NULL,language TEXT NOT NULL,source_ref TEXT NOT NULL,observed_at TEXT NOT NULL,packet TEXT NOT NULL,confidence REAL NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS claims(claim_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,stance TEXT NOT NULL CHECK(stance IN('support','deny')),confidence REAL NOT NULL,authority_status TEXT NOT NULL,valid_from TEXT,valid_to TEXT,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS proof_links(proof_ref TEXT PRIMARY KEY,subject_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,operation TEXT NOT NULL,parent_refs TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS rules(rule_ref TEXT PRIMARY KEY,rule_kind TEXT NOT NULL CHECK(rule_kind IN('definition','entailment','causal','default')),antecedent TEXT NOT NULL,consequent TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 1,authority_status TEXT NOT NULL DEFAULT 'reviewed',generation INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rules_semantic ON rules(rule_kind,antecedent,consequent);
CREATE TABLE IF NOT EXISTS language_examples(example_ref TEXT PRIMARY KEY,language TEXT NOT NULL,delex_surface TEXT NOT NULL,program TEXT NOT NULL,weight REAL NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS realization_examples(example_ref TEXT PRIMARY KEY,language TEXT NOT NULL,semantic TEXT NOT NULL,surface TEXT NOT NULL,weight REAL NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS reference_forms(language TEXT NOT NULL,surface TEXT NOT NULL,features TEXT NOT NULL DEFAULT '{}',bound_ref TEXT,weight REAL NOT NULL DEFAULT 1,PRIMARY KEY(language,surface,bound_ref));
CREATE TABLE IF NOT EXISTS control_symbols(role TEXT PRIMARY KEY,semantic_ref TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS designation_index(label_ref TEXT PRIMARY KEY,target_ref TEXT NOT NULL,label_type_ref TEXT NOT NULL,surface TEXT NOT NULL,language TEXT NOT NULL,script TEXT NOT NULL,prior REAL NOT NULL,preferred INTEGER NOT NULL,context_ref TEXT);
CREATE INDEX IF NOT EXISTS idx_designation_surface ON designation_index(language,surface);
CREATE TABLE IF NOT EXISTS label_stats(label_ref TEXT PRIMARY KEY,use_count INTEGER NOT NULL DEFAULT 0,last_used TEXT);
CREATE TABLE IF NOT EXISTS discourse_entities(atom_ref TEXT PRIMARY KEY,salience REAL NOT NULL,last_turn INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS frontiers(frontier_ref TEXT PRIMARY KEY,surface TEXT NOT NULL,reason TEXT NOT NULL,details TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS generations(generation INTEGER PRIMARY KEY,parent_generation INTEGER,created_at TEXT NOT NULL,reason TEXT NOT NULL,content_hash TEXT NOT NULL);
"""
TOK = re.compile(r"@[aAxX][0-9]+|@[0-9]+|<[A-Za-z0-9]+>|[\w:/.-]+|[^\w\s]", re.UNICODE)
MODEL_CACHE: dict[str, Any] = {}
MODEL_CACHE_LIMIT = 8

def now(): return datetime.now(timezone.utc).isoformat()
def canonical(x): return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def stable(prefix,*parts): return f"{prefix}:{hashlib.sha256(canonical(parts).encode()).hexdigest()[:24]}"
def norm_text(s): return unicodedata.normalize("NFKC", str(s)).casefold()
def tokens(s): return TOK.findall(unicodedata.normalize("NFKC", s.strip()))
def surface(ts):
    s=" ".join(ts); s=re.sub(r"\s+([.,!?;:])",r"\1",s); s=re.sub(r"([('¿¡])\s+",r"\1",s); s=re.sub(r"\s+([)'])",r"\1",s)
    return s[:1].upper()+s[1:] if s else s

def lit(value,typ="text"): return {"literal":{"type":typ,"value":value}}
def isvar(x): return isinstance(x,str) and x.startswith("?")
def isexist(x): return isinstance(x,str) and x.startswith("!")

class AmbiguousReferent(ValueError):
    def __init__(self,surface,candidates): self.surface,self.candidates=surface,candidates; super().__init__(surface)

@dataclass(frozen=True)
class Fact:
    ref:str; operator:str; args:dict[str,Any]; stance:str="support"; confidence:float=1.; derived:bool=False; proof:dict[str,Any]|None=None
    def signature(self): return stable("fact",self.operator,sorted(self.args.items(),key=lambda x:x[0]),self.stance)

class Store:
    SNAP=("atoms","operator_roles","applications","bindings","observations","claims","proof_links","rules","language_examples","realization_examples","reference_forms","control_symbols")
    def __init__(self,path):
        self.path=str(path); self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row; self.db.executescript(DDL)
        if not self.db.execute("SELECT 1 FROM generations").fetchone():
            self.db.execute("INSERT INTO generations VALUES(1,NULL,?,?,?)",(now(),"initial",hashlib.sha256(b"initial").hexdigest())); self.db.commit()
    @property
    def generation(self): return int(self.db.execute("SELECT max(generation) FROM generations").fetchone()[0])
    def begin(self,reason):
        g=self.generation+1; self.db.execute("INSERT INTO generations VALUES(?,?,?,?,?)",(g,g-1,now(),reason,"pending")); return g
    def finish(self,g):
        h=self.snapshot_hash(); self.db.execute("UPDATE generations SET content_hash=? WHERE generation=?",(h,g)); return h
    def snapshot_hash(self):
        material=[]
        for t in self.SNAP:
            cols=[x[1] for x in self.db.execute(f"PRAGMA table_info({t})") if x[1] not in {"observed_at","generation"}]
            rows=self.db.execute(f"SELECT {','.join(cols)} FROM {t} ORDER BY {cols[0]}").fetchall(); material.append((t,[dict(r) for r in rows]))
        return hashlib.sha256(canonical(material).encode()).hexdigest()
    def exact(self,t,cols,vals,keys,ignore=()):
        try:self.db.execute(f"INSERT INTO {t}({','.join(cols)}) VALUES({','.join('?' for _ in vals)})",vals)
        except sqlite3.IntegrityError:
            kv=[vals[cols.index(k)] for k in keys]; row=self.db.execute(f"SELECT * FROM {t} WHERE "+" AND ".join(f"{k}=?" for k in keys),kv).fetchone()
            if not row: raise
            for c,v in zip(cols,vals):
                if c not in ignore and row[c]!=v: raise ValueError(f"immutable conflict {t}:{kv}:{c}")
    def atom(self,ref): return self.db.execute("SELECT * FROM atoms WHERE ref=?",(ref,)).fetchone()
    def foundational(self,ref):
        a=self.atom(ref); return bool(a and json.loads(a["metadata"]).get("foundational"))
    def symbol(self,role):
        r=self.db.execute("SELECT semantic_ref FROM control_symbols WHERE role=?",(role,)).fetchone()
        if not r: raise ValueError(f"missing control symbol {role}")
        return str(r[0])
    def creatable_kinds(self): return {str(r[0]) for r in self.db.execute("SELECT semantic_ref FROM control_symbols WHERE role LIKE 'new_kind.%'")}
    def roles(self,op): return {r["role_ref"]:r for r in self.db.execute("SELECT * FROM operator_roles WHERE operator_ref=?",(op,))}
    def encode_value(self,v):
        if isinstance(v,dict) and "literal" in v:return "literal",canonical(v["literal"])
        if isinstance(v,dict) and "app" in v:return "app",str(v["app"])
        return "atom",str(v)
    def decode_value(self,k,v): return {"literal":json.loads(v)} if k=="literal" else {"app":v} if k=="app" else v
    def _validate_filler(self,role,v,spec):
        fk,fv=self.encode_value(v); exp=spec["filler_kind"]
        if exp and exp.startswith("literal:"):
            if fk!="literal" or json.loads(fv)["type"]!=exp.split(":",1)[1]: raise ValueError(f"literal kind {role}")
            return
        if fk=="atom" and not self.atom(fv): raise ValueError(f"unknown atom filler {role}:{fv}")
        if fk=="app" and not self.db.execute("SELECT 1 FROM applications WHERE app_ref=?",(fv,)).fetchone(): raise ValueError(f"unknown app filler {role}:{fv}")
        if exp in {"atom","app"} and fk!=exp: raise ValueError(f"filler class {role}")
        if exp and exp not in {"atom","app"} and not exp.startswith("literal:"):
            if fk!="atom" or self.atom(fv)["kind"]!=exp: raise ValueError(f"filler kind {role}: expected {exp}")
    def validate_app(self,op,args):
        if not self.atom(op): raise ValueError(f"unknown operator {op}")
        specs=self.roles(op); seen={}
        for role,v in args.items():
            if role not in specs: raise ValueError(f"{op} disallows {role}")
            seen[role]=seen.get(role,0)+1; self._validate_filler(role,v,specs[role])
        for role,s in specs.items():
            if s["required"] and role not in seen: raise ValueError(f"missing {op}:{role}")
    def app_signature(self,op,args): return stable("app",op,sorted((r,*self.encode_value(v)) for r,v in args.items()))
    def insert_app(self,op,args,g,obs,stance="support",confidence=1.,authority="reviewed",valid_from=None):
        self.validate_app(op,args); ar=self.app_signature(op,args); self.db.execute("INSERT OR IGNORE INTO applications VALUES(?,?,?)",(ar,op,g))
        for n,(role,v) in enumerate(sorted(args.items())):
            fk,fv=self.encode_value(v); br=stable("bind",ar,role,fk,fv,n); self.db.execute("INSERT OR IGNORE INTO bindings VALUES(?,?,?,?,?,?)",(br,ar,role,fk,fv,n))
        cr=stable("claim",ar,obs,stance); self.db.execute("INSERT OR IGNORE INTO claims VALUES(?,?,?,?,?,?,?,?,?)",(cr,ar,obs,stance,float(confidence),authority,valid_from,None,g)); self.db.execute("INSERT OR IGNORE INTO proof_links VALUES(?,?,?,?,?)",(stable("proof",cr),cr,obs,"assert","[]"))
        self._supersede_state(ar,op,args,cr,stance)
        return ar
    def _supersede_state(self,new_ref,op,args,new_claim,stance):
        try: state_op=self.symbol("operator.state"); subj=self.symbol("role.subject"); dim=self.symbol("role.dimension"); val=self.symbol("role.value")
        except ValueError:return
        if stance!="support" or op!=state_op or subj not in args or dim not in args or val not in args:return
        d=self.atom(str(args[dim])); meta=json.loads(d["metadata"]) if d else {}
        if not meta.get("exclusive"):return
        for f in self.base_facts():
            if f.ref==new_ref or f.operator!=op or f.stance!="support":continue
            if f.args.get(subj)==args[subj] and f.args.get(dim)==args[dim] and f.args.get(val)!=args[val]: self.db.execute("UPDATE claims SET valid_to=? WHERE app_ref=? AND stance='support' AND valid_to IS NULL",(now(),f.ref))
    def base_facts(self):
        out=[]
        for a in self.db.execute("SELECT * FROM applications ORDER BY app_ref"):
            args={}
            for b in self.db.execute("SELECT * FROM bindings WHERE app_ref=? ORDER BY role_ref,ordinal",(a["app_ref"],)): args[b["role_ref"]]=self.decode_value(b["filler_kind"],b["filler_value"])
            rows=self.db.execute("SELECT stance,confidence FROM claims WHERE app_ref=? AND valid_to IS NULL",(a["app_ref"],)).fetchall(); st={r["stance"] for r in rows}
            if "support" in st: out.append(Fact(a["app_ref"],a["operator_ref"],args,"support",max(float(r["confidence"]) for r in rows if r["stance"]=="support")))
            if "deny" in st: out.append(Fact(a["app_ref"],a["operator_ref"],args,"deny",max(float(r["confidence"]) for r in rows if r["stance"]=="deny")))
        return out
    def add_observation(self,surface,packet,lang,source,g,confidence=.95,occurrence_ref=None):
        ref=stable("obs",surface,lang,source,packet,occurrence_ref or "dedup"); self.db.execute("INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?,?,?,?)",(ref,surface,"language",lang,source,now(),canonical(packet),confidence,g)); return ref
    def validate_rule(self,x):
        ants=list(x.get("if",[])); cons=list(x.get("then",[]))
        if not ants or not cons: raise ValueError("rule requires antecedent and consequent")
        if not 0 < float(x.get("confidence",1)) <= 1: raise ValueError("rule confidence out of range")
        bound={v for c in ants for v in c.get("args",{}).values() if isvar(v)}
        if any(isexist(v) for c in ants for v in c.get("args",{}).values()): raise ValueError("existential witness cannot appear in antecedent")
        for c in ants+cons:
            op=c.get("operator")
            if not self.atom(op): raise ValueError(f"rule unknown operator {op}")
            specs=self.roles(op)
            for role,v in c.get("args",{}).items():
                if role not in specs: raise ValueError(f"rule {op} disallows {role}")
                if isinstance(v,str) and (isvar(v) or isexist(v)):
                    if c in cons and isvar(v) and v not in bound: raise ValueError(f"unbound consequent variable {v}")
                    continue
                self._validate_filler(role,v,specs[role])
            if c in cons:
                for role,r in specs.items():
                    if r["required"] and role not in c.get("args",{}): raise ValueError(f"rule consequent missing {op}:{role}")
    def import_data(self,path):
        d=json.loads(Path(path).read_text(encoding="utf-8"))
        with self.db:
            g=self.begin(f"import:{Path(path).name}")
            for x in d.get("atoms",[]):self.exact("atoms",["ref","kind","metadata","generation"],[x["ref"],x["kind"],canonical(x.get("metadata",{})),g],["ref"],{"generation"})
            for x in d.get("operator_roles",[]):
                if x.get("cardinality","one") != "one": raise ValueError("MVP supports one filler per role; represent multiplicity with repeated applications")
                self.exact("operator_roles",["operator_ref","role_ref","required","cardinality","filler_kind"],[x["operator_ref"],x["role_ref"],int(x.get("required",False)),x.get("cardinality","one"),x.get("filler_kind")],["operator_ref","role_ref"])
            for k,v in d.get("control_symbols",{}).items():self.exact("control_symbols",["role","semantic_ref"],[k,v],["role"])
            for x in d.get("reference_forms",[]):self.exact("reference_forms",["language","surface","features","bound_ref","weight"],[x.get("language","en"),x["surface"],canonical(x.get("features",{})),x.get("bound_ref"),float(x.get("weight",1))],["language","surface","bound_ref"])
            for x in d.get("language_examples",[]):self.exact("language_examples",["example_ref","language","delex_surface","program","weight"],[x["example_ref"],x.get("language","en"),x["delex_surface"],x["program"],float(x.get("weight",1))],["example_ref"])
            for x in d.get("realization_examples",[]):self.exact("realization_examples",["example_ref","language","semantic","surface","weight"],[x["example_ref"],x.get("language","en"),x["semantic"],x["surface"],float(x.get("weight",1))],["example_ref"])
            for x in d.get("rules",[]):
                self.validate_rule(x); rk=x.get("rule_kind","entailment"); ant=canonical(x.get("if",[])); con=canonical(x.get("then",[]))
                if self.db.execute("SELECT 1 FROM rules WHERE rule_kind=? AND antecedent=? AND consequent=?",(rk,ant,con)).fetchone(): continue
                self.exact("rules",["rule_ref","rule_kind","antecedent","consequent","confidence","authority_status","generation"],[x["rule_ref"],rk,ant,con,float(x.get("confidence",1)),x.get("authority_status","reviewed"),g],["rule_ref"],{"generation"})
            for x in d.get("facts",[]):
                obs=self.add_observation(x.get("source_text",x.get("fact_ref",x["operator"])),x,"und",x.get("source_ref","seed"),g,float(x.get("confidence",1))); self.insert_app(x["operator"],x.get("args",{}),g,obs,x.get("stance","support"),x.get("confidence",1),x.get("authority_status","reviewed"))
            self.rebuild_designations(); self.finish(g)
        return g
    def rebuild_designations(self):
        self.db.execute("DELETE FROM designation_index")
        try:
            op=self.symbol("operator.designation"); roles={k:self.symbol(f"designation.{k}") for k in ("target","type","surface","language","script","prior","preferred","context")}
        except ValueError:return
        for f in self.base_facts():
            if f.operator!=op or f.stance!="support":continue
            def v(k,default=None):
                x=f.args.get(roles[k],default)
                return x.get("literal",{}).get("value") if isinstance(x,dict) and "literal" in x else x
            if not v("target") or not v("surface"):continue
            self.db.execute("INSERT OR REPLACE INTO designation_index VALUES(?,?,?,?,?,?,?,?,?)",(f.ref,str(v("target")),str(v("type","label:default")),str(v("surface")),str(v("language","und")),str(v("script","Zyyy")),float(v("prior",1)),int(bool(v("preferred",False))),v("context")))
    def label_candidates(self,surf,lang,kind=None):
        rows=self.db.execute("""SELECT d.*,a.kind,coalesce(s.use_count,0) use_count,coalesce(e.salience,0) salience FROM designation_index d JOIN atoms a ON a.ref=d.target_ref LEFT JOIN label_stats s ON s.label_ref=d.label_ref LEFT JOIN discourse_entities e ON e.atom_ref=d.target_ref WHERE d.language IN (?, 'und')""",(lang,)).fetchall(); by={}
        needle=norm_text(surf.strip())
        for r in rows:
            if norm_text(r["surface"])!=needle: continue
            if kind and r["kind"]!=kind:continue
            score=float(r["prior"])+.25*int(r["preferred"])+.05*math.log1p(int(r["use_count"]))+.8*float(r["salience"])+(.08 if r["language"]==lang else 0); old=by.get(r["target_ref"])
            if not old or score>old[0]:by[r["target_ref"]]=(score,r)
        return sorted([(ref,*x) for ref,x in by.items()],key=lambda x:(-x[1],x[0]))
    def resolve_label(self,surf,lang,kind=None,margin=.18):
        cs=self.label_candidates(surf,lang,kind)
        if not cs:return None
        if len(cs)>1 and cs[0][1]-cs[1][1]<margin:raise AmbiguousReferent(surf,[{"ref":x[0],"score":x[1]} for x in cs[:5]])
        return cs[0][0]
    def record_use(self,surf,lang,ref):
        rows=self.db.execute("SELECT label_ref,surface,preferred,prior FROM designation_index WHERE target_ref=? AND language IN (?, 'und') ORDER BY preferred DESC,prior DESC",(ref,lang)).fetchall(); needle=norm_text(surf)
        r=next((x for x in rows if norm_text(x["surface"])==needle),None)
        if r:self.db.execute("INSERT INTO label_stats VALUES(?,1,?) ON CONFLICT(label_ref) DO UPDATE SET use_count=use_count+1,last_used=excluded.last_used",(r["label_ref"],now()))
    def preferred(self,ref,lang,context=None):
        rows=self.db.execute("SELECT d.*,coalesce(s.use_count,0) use_count FROM designation_index d LEFT JOIN label_stats s ON s.label_ref=d.label_ref WHERE target_ref=? AND language IN (?, 'und')",(ref,lang)).fetchall()
        if not rows:return ref
        def score(r):return float(r["prior"])+.5*int(r["preferred"])+.04*math.log1p(int(r["use_count"]))+(.1 if r["language"]==lang else 0)+(.7 if context and r["context_ref"]==context else 0)-(.15 if context and r["context_ref"] and r["context_ref"]!=context else 0)
        return str(max(rows,key=score)["surface"])
    def touch(self,refs):
        self.db.execute("UPDATE discourse_entities SET salience=salience*.55"); turn=int(self.db.execute("SELECT coalesce(max(last_turn),0)+1 FROM discourse_entities").fetchone()[0])
        for ref in set(refs):
            a=self.atom(ref)
            if a and a["kind"] in {"entity","participant","resource","source","existential"}:self.db.execute("INSERT INTO discourse_entities VALUES(?,1,?) ON CONFLICT(atom_ref) DO UPDATE SET salience=min(3,salience+1),last_turn=excluded.last_turn",(ref,turn))
    def frontier(self,surface_,reason,details):
        ref=stable("frontier",surface_,reason,details,self.generation); self.db.execute("INSERT OR IGNORE INTO frontiers VALUES(?,?,?,?,?)",(ref,surface_,reason,canonical(details),self.generation)); self.db.commit(); return ref
    def training_hash(self,lang):
        material=[]
        for t in ("language_examples","realization_examples"):material.append((t,[dict(r) for r in self.db.execute(f"SELECT * FROM {t} WHERE language IN (?, 'und') ORDER BY 1",(lang,))]))
        material.append(("operator_roles",[dict(r) for r in self.db.execute("SELECT * FROM operator_roles ORDER BY 1,2")]))
        return hashlib.sha256(canonical(material).encode()).hexdigest()

class SeqNet(nn.Module):
    def __init__(self,v,d=48):
        super().__init__(); self.emb=nn.Embedding(v,d,padding_idx=0); self.pos=nn.Embedding(256,d); self.tr=nn.Transformer(d,4,1,1,96,dropout=0,batch_first=True); self.out=nn.Linear(d,v)
    def e(self,x):return self.emb(x)+self.pos(torch.arange(x.size(1))[None,:])
    def forward(self,s,t):return self.out(self.tr(self.e(s),self.e(t),tgt_mask=nn.Transformer.generate_square_subsequent_mask(t.size(1)),src_key_padding_mask=s.eq(0),memory_key_padding_mask=s.eq(0)))

def train_seq(pairs,seed=23,epochs=420):
    rx=re.compile(r"@[aAxX][0-9]+|@[0-9]+|<[A-Za-z0-9]+>|[\w:/?.!-]+|[^\s]",re.UNICODE); tk=lambda s:rx.findall(s.lower()); vocab=["<pad>","<bos>","<eos>","<unk>"]+sorted(set(itertools.chain.from_iterable(tk(a)+tk(b) for a,b in pairs))); vi={x:i for i,x in enumerate(vocab)}; enc=lambda s:[vi.get(x,3) for x in tk(s)]; ms=max(len(enc(a)) for a,_ in pairs); mt=max(len(enc(b)) for _,b in pairs)+1; S=[];T=[];O=[]
    for a,b in pairs:
        x,y=enc(a),enc(b)+[2]; z=[1]+y[:-1]; S.append(x+[0]*(ms-len(x))); T.append(z+[0]*(mt-len(z))); O.append(y+[0]*(mt-len(y)))
    S,T,O=torch.tensor(S),torch.tensor(T),torch.tensor(O); torch.manual_seed(seed); m=SeqNet(len(vocab)); opt=torch.optim.AdamW(m.parameters(),lr=.006)
    for _ in range(epochs):opt.zero_grad(); q=m(S,T); loss=nn.functional.cross_entropy(q.reshape(-1,len(vocab)),O.reshape(-1),ignore_index=0); loss.backward(); opt.step()
    m.eval(); return {"vocab":vocab,"vi":vi,"rx":rx},m

def translate(meta,model,task,text,maxn=180):
    ts=meta["rx"].findall(f"<{task}> {text}".lower()); src=torch.tensor([[meta["vi"].get(x,3) for x in ts]]); out=torch.tensor([[1]])
    with torch.no_grad():
        for _ in range(maxn):
            n=int(model(src,out)[0,-1].argmax())
            if n==2:break
            out=torch.cat([out,torch.tensor([[n]])],1)
    return " ".join(meta["vocab"][i] for i in out[0,1:].tolist())

class Codecs:
    def __init__(self,s,lang):
        self.lang=lang; le=s.db.execute("SELECT delex_surface,program FROM language_examples WHERE language IN (?, 'und') ORDER BY example_ref",(lang,)).fetchall(); lp=[(r[0],r[1]) for r in le]; pairs=[(f"<T2P> {a}",b) for a,b in lp]+[(f"<P2T> {b}",a) for a,b in lp]; self.lm,self.ln=train_seq(pairs,29,500); self.vm,self.vn=train_seq(pairs,37,500)
        rexs=s.db.execute("SELECT semantic,surface FROM realization_examples WHERE language IN (?, 'und') ORDER BY example_ref",(lang,)).fetchall(); rp=[(r[0],r[1]) for r in rexs]; self.rm,self.rn=train_seq([(f"<S2T> {a}",b) for a,b in rp]+[(f"<T2S> {b}",a) for a,b in rp],31,420)
    @classmethod
    def get(cls,s,lang):
        k=f"{lang}:{s.training_hash(lang)}"
        if k not in MODEL_CACHE:
            if len(MODEL_CACHE) >= MODEL_CACHE_LIMIT: MODEL_CACHE.pop(next(iter(MODEL_CACHE)))
            MODEL_CACHE[k]=cls(s,lang)
        return MODEL_CACHE[k]
    def interpret(self,delex):
        p=translate(self.lm,self.ln,"T2P",delex); alt=translate(self.vm,self.vn,"T2P",delex); inv=translate(self.lm,self.ln,"P2T",p); p2=translate(self.lm,self.ln,"T2P",inv)
        same_program=[norm_text(x) for x in tokens(p2)]==[norm_text(x) for x in tokens(p)]
        independent_agreement=[norm_text(x) for x in tokens(alt)]==[norm_text(x) for x in tokens(p)]
        src_placeholders=sorted(norm_text(x) for x in tokens(delex) if x.lower().startswith("@a")); inv_placeholders=sorted(norm_text(x) for x in tokens(inv) if x.lower().startswith("@a"))
        placeholder_conservation=src_placeholders==inv_placeholders
        ok=same_program and independent_agreement and placeholder_conservation
        return p,ok,{"delex":delex,"program":p,"independent_program":alt,"inverse_delex":inv,"reencoded_program":p2,"program_roundtrip":same_program,"independent_agreement":independent_agreement,"placeholder_conservation":placeholder_conservation,"verified":ok}
    def realize(self,semantic):
        p=translate(self.rm,self.rn,"S2T",semantic); inv=translate(self.rm,self.rn,"T2S",p); ok=[x.lower() for x in tokens(inv)]==[x.lower() for x in tokens(semantic)]; return p,ok,{"semantic":semantic,"surface_plan":p,"inverse_semantic":inv,"verified":ok}

class Delexer:
    def __init__(self,s,lang):self.s,self.lang=s,lang; self.sal={r["atom_ref"]:float(r["salience"]) for r in s.db.execute("SELECT * FROM discourse_entities")}
    def reference(self,surf):
        rows=[r for r in self.s.db.execute("SELECT * FROM reference_forms WHERE language IN (?, 'und') ORDER BY weight DESC",(self.lang,)).fetchall() if norm_text(r["surface"])==norm_text(surf)]
        for r in rows:
            if r["bound_ref"]:return str(r["bound_ref"])
            f=json.loads(r["features"]); cs=[]; required_type=f.get("required_type"); typed=set()
            if required_type:
                facts,_=Inference(self.s,max_rounds=8,max_facts=500).closure(); typed={x.args.get("role:instance") for x in facts if x.operator=="op:type" and x.stance=="support" and x.args.get("role:class")==required_type}
            for ref,score in self.sal.items():
                a=self.s.atom(ref); m=json.loads(a["metadata"]) if a else {}; meta={k:v for k,v in f.items() if k not in {"kind","required_type"}}
                if a and all(m.get(k)==v for k,v in meta.items()) and (not f.get("kind") or a["kind"]==f["kind"]) and (not required_type or ref in typed):cs.append((score,ref))
            cs.sort(reverse=True)
            if cs:
                if len(cs)>1 and cs[0][0]-cs[1][0]<.25:raise AmbiguousReferent(surf,[{"ref":x[1],"score":x[0]} for x in cs[:5]])
                return cs[0][1]
        return None
    def run(self,text):
        phmap={}; rev={}; uses=[]; nexti=0; out=[]
        def ph(ref):
            nonlocal nexti
            if ref not in rev:rev[ref]=f"@A{nexti}"; phmap[rev[ref]]=ref; nexti+=1
            return rev[ref]
        labels=self.s.db.execute("SELECT DISTINCT surface FROM designation_index WHERE language IN (?, 'und') ORDER BY length(surface) DESC",(self.lang,)).fetchall(); refs=self.s.db.execute("SELECT DISTINCT surface FROM reference_forms WHERE language IN (?, 'und') ORDER BY length(surface) DESC",(self.lang,)).fetchall()
        for sent in re.split(r"(?<=[.!?])\s+",text.strip()):
            cand=[]
            for typ,rows in (("ref",refs),("label",labels)):
                for row in rows:
                    q=str(row[0])
                    for m in re.finditer(r"(?<!\w)"+re.escape(q)+r"(?!\w)",sent,flags=re.I):cand.append((m.start(),m.end(),typ,q))
            chosen=[]
            for c in sorted(cand,key=lambda x:(x[0],-(x[1]-x[0]),0 if x[2]=="ref" else 1)):
                if not any(c[0]<x[1] and c[1]>x[0] for x in chosen):chosen.append(c)
            pos=0; pieces=[]; mentioned=[]
            for a,b,typ,q in sorted(chosen):
                pieces.append(sent[pos:a]); ref=self.reference(q) if typ=="ref" else self.s.resolve_label(q,self.lang)
                if ref:pieces.append(ph(ref)); mentioned.append(ref); uses.append((q,ref)) if typ=="label" else None
                else:pieces.append(sent[a:b])
                pos=b
            pieces.append(sent[pos:]); out.append("".join(pieces)); self.sal={k:v*.55 for k,v in self.sal.items()}
            for ref in mentioned:self.sal[ref]=min(3,self.sal.get(ref,0)+1)
        return " ".join(out),phmap,uses

class Interpreter:
    def __init__(self,s,lang):self.s,self.lang=s,lang
    def parse(self,text):
        delex,ph,uses=Delexer(self.s,self.lang).run(text); program,ok,trace=Codecs.get(self.s,self.lang).interpret(delex)
        if not ok:return None,[],uses,{**trace,"reason":"semantic_codec_roundtrip_failed"}
        program=re.sub(r"@\s*([ax]\d+)",lambda m:"@"+m.group(1).upper(),program,flags=re.I); program=re.sub(r"\s*=\s*","=",program); apps=[]; news=[]; query=None; describe=None
        for stmt in [x.strip() for x in program.split("|") if x.strip()]:
            p=stmt.split()
            if p[0]=="new":
                if len(p)<3 or p[2] not in self.s.creatable_kinds(): raise ValueError(f"non-creatable structural kind: {p[2] if len(p)>2 else ''}")
                news.append({"token":p[1].upper(),"kind":p[2]}); continue
            if p[0]=="describe":describe=self._value(p[1],ph); continue
            if p[0] not in {"app","query"}:return None,[],uses,{**trace,"reason":"bad_program","statement":stmt}
            op=p[2] if p[0]=="app" else p[1]; start=3 if p[0]=="app" else 2; args={}
            if not self.s.foundational(op): raise ValueError(f"non-foundational operator in learned program: {op}")
            allowed=self.s.roles(op)
            for kv in p[start:]:
                if "=" not in kv:continue
                r,v=kv.split("=",1)
                if r not in allowed or not self.s.foundational(r): raise ValueError(f"non-foundational/disallowed role: {r}")
                args[r]=self._value(v,ph)
            if p[0]=="app":apps.append({"id":p[1],"operator":op,"args":args,"stance":"support"})
            else:query={"operator":op,"args":args}
        return {"apps":apps,"query":query,"describe":describe},news,uses,trace
    def _value(self,v,ph):
        if v.upper().startswith("@A"):return ph[v.upper()]
        if v.upper().startswith("@X"):return {"new":v.upper()}
        if v.startswith("lit:"):
            typ,val=v.split(":",2)[1:]; return lit(val,typ)
        if v.startswith("?"):return v
        a=self.s.atom(v)
        if a and json.loads(a["metadata"]).get("foundational"):return v
        raise ValueError(f"non-placeholder domain constant rejected: {v}")

class Inference:
    def __init__(self,s,max_rounds=12,max_facts=1000):self.s,self.max_rounds,self.max_facts=s,max_rounds,max_facts; self.incomplete=False; self.incomplete_reason=None
    def closure(self,extra=()):
        self.incomplete=False; self.incomplete_reason=None
        facts=list(self.s.base_facts())+list(extra); bysig={f.signature():f for f in facts}; byref={f.ref:f for f in facts}; rules=[dict(r) for r in self.s.db.execute("SELECT * FROM rules WHERE rule_kind IN('definition','entailment') AND authority_status IN('reviewed','promoted') ORDER BY rule_ref")]
        for _round in range(self.max_rounds):
            added=0
            for r in rules:
                ants=json.loads(r["antecedent"]); cons=json.loads(r["consequent"])
                for env,parents in self._matches(ants,list(bysig.values())):
                    ex={}; parent_refs=tuple(sorted(x.ref for x in parents))
                    for c in cons:
                        args={k:self._inst(v,env,ex,r["rule_ref"],parent_refs) for k,v in c.get("args",{}).items()}; st=c.get("stance","support"); ref=stable("derived",r["rule_ref"],parent_refs,c.get("operator"),args,st); f=Fact(ref,c["operator"],args,st,min([x.confidence for x in parents]+[1.])*float(r["confidence"]),True,{"rule_ref":r["rule_ref"],"parents":parent_refs})
                        if f.signature() not in bysig:bysig[f.signature()]=f; byref[f.ref]=f; added+=1
                        if len(bysig)>=self.max_facts:self.incomplete=True; self.incomplete_reason="max_facts"; return list(bysig.values()),byref
            if not added:break
        else:
            self.incomplete=True; self.incomplete_reason="max_rounds"
        return list(bysig.values()),byref
    def _matches(self,clauses,facts):
        states=[({},[])]
        for c in clauses:
            nxt=[]
            for env,pars in states:
                for f in facts:
                    e=dict(env)
                    if self._unify_clause(c,f,e):nxt.append((e,pars+[f]))
            states=nxt
            if not states:break
        return states
    def _unify_clause(self,c,f,env):
        if c.get("stance","support")!=f.stance:return False
        if not self._unify(c["operator"],f.operator,env):return False
        for role,pv in c.get("args",{}).items():
            if role not in f.args or not self._unify(pv,f.args[role],env):return False
        return True
    def _unify(self,p,v,env):
        if isvar(p):
            if p in env:return canonical(env[p])==canonical(v)
            env[p]=v; return True
        return canonical(p)==canonical(v)
    def _inst(self,v,env,ex,rule,parents):
        if isvar(v):return env[v]
        if isexist(v):
            if v not in ex:ex[v]=stable("existential",rule,parents,v)
            return ex[v]
        return v
    def match(self,pattern,facts):
        return [f for f in facts if self._unify_clause({"operator":pattern["operator"],"args":pattern.get("args",{}),"stance":pattern.get("stance","support")},f,{})]
    def explain(self,f,byref):
        if not f.derived:return {"fact_ref":f.ref,"source":"observed","operator":f.operator,"args":f.args}
        return {"fact_ref":f.ref,"source":"derived","operator":f.operator,"args":f.args,"rule_ref":f.proof["rule_ref"],"parents":[self.explain(byref[x],byref) for x in f.proof["parents"] if x in byref]}

class Realizer:
    def __init__(self,s,lang):self.s,self.lang=s,lang
    def response(self,semantic):
        plan,ok,p=Codecs.get(self.s,self.lang).realize(f"RESP {semantic}"); return (surface(plan.split()) if ok else ""),p
    def fact(self,f):
        ph={}; parts=["FACT",f.stance,f.operator]
        for i,(role,v) in enumerate(sorted(f.args.items())):
            p=f"@{i}"; parts += [role,p]; ph[p]=self._lex(v,role)
        sem=" ".join(parts); plan,ok,proof=Codecs.get(self.s,self.lang).realize(sem)
        for p,v in ph.items():plan=plan.replace(p,str(v))
        rendered=surface(plan.split()) if ok else ""
        if re.search(r"\b(?:atom|existential|app|fact):[0-9a-fA-F]+",rendered):
            proof={**proof,"verified":False,"reason":"unresolved_referring_expression"}; rendered=""
        return rendered,proof
    def _lex(self,v,context):
        if isinstance(v,dict) and "literal" in v:return v["literal"]["value"]
        return self.s.preferred(str(v),self.lang,context)

class Runtime:
    def __init__(self,s,lang="en"):self.s,self.lang=s,lang; self.i=Interpreter(s,lang); self.inf=Inference(s); self.z=Realizer(s,lang)
    def _materialize(self,packet,news,g,seed):
        facts,_=self.inf.closure(); mapping={}
        for x in news:
            tok,kind=x["token"],x["kind"]; candidates=None
            for a in packet.get("apps",[]):
                roles=[r for r,v in a.get("args",{}).items() if isinstance(v,dict) and v.get("new")==tok]
                if len(roles)!=1: continue
                role=roles[0]; known={}
                for r,v in a.get("args",{}).items():
                    if r==role: continue
                    if isinstance(v,dict) and "new" in v:
                        if v["new"] in mapping: known[r]=mapping[v["new"]]
                        continue
                    known[r]=v
                if not known: continue
                vals=set()
                for f in self.inf.match({"operator":a["operator"],"args":known},facts):
                    v=f.args.get(role); atom=self.s.atom(v) if isinstance(v,str) else None
                    if atom and atom["kind"]==kind: vals.add(v)
                if vals: candidates=vals if candidates is None else candidates & vals
            if candidates and len(candidates)>1: raise AmbiguousReferent(tok,[{"ref":r,"score":1.0} for r in sorted(candidates)])
            mapping[tok]=next(iter(candidates)) if candidates else stable("atom",kind,seed,tok)
        for x in news:
            ref=mapping[x["token"]]
            if not self.s.atom(ref): self.s.exact("atoms",["ref","kind","metadata","generation"],[ref,x["kind"],"{}",g],["ref"],{"generation"})
        p=json.loads(canonical(packet))
        def cv(v):return mapping[v["new"]] if isinstance(v,dict) and "new" in v else v
        for a in p.get("apps",[]):a["args"]={k:cv(v) for k,v in a["args"].items()}
        if p.get("query"):p["query"]["args"]={k:cv(v) for k,v in p["query"]["args"].items()}
        return p,mapping
    def process(self,text,learn=True):
        try:packet,news,uses,trace=self.i.parse(text)
        except AmbiguousReferent as e:return self._frontier(text,"ambiguous_referent",{"surface":e.surface,"candidates":e.candidates})
        except Exception as e:return self._frontier(text,"interpretation_error",{"error":str(e)})
        if not packet:return self._frontier(text,trace.get("reason","no_candidate"),trace)
        if packet.get("query") or packet.get("describe"):
            facts,byref=self.inf.closure();
            if self.inf.incomplete:return self._frontier(text,"inference_incomplete",{"reason":self.inf.incomplete_reason,"max_rounds":self.inf.max_rounds,"max_facts":self.inf.max_facts})
            if packet.get("describe"):
                target=packet["describe"]; des=self.s.symbol("operator.designation"); xs=[f for f in facts if f.stance=="support" and f.operator!=des and target in f.args.values()]; outs=[x for f in xs if (x:=self.z.fact(f)[0])][:5]; return {"status":"ok" if outs else "unknown","response":" ".join(outs),"facts":[f.__dict__ for f in xs[:10]]}
            pos=self.inf.match(packet["query"],facts); neg=self.inf.match({**packet["query"],"stance":"deny"},facts); result="conflict" if pos and neg else "supported" if pos else "contradicted" if neg else "unknown"; key={"supported":"response.yes","contradicted":"response.no","unknown":"response.unknown","conflict":"response.conflict"}[result]; out,proof=self.z.response(self.s.symbol(key)); chosen=(pos or neg); exp=self.inf.explain(chosen[0],byref) if chosen else None; return {"status":"ok","response":out,"result":result,"query":packet["query"],"proof":exp,"realization_proof":proof,"ephemeral_fact_count":sum(f.derived for f in facts)}
        if not learn:return {"status":"interpreted","packet":packet,"trace":trace}
        try:
            with self.s.db:
                g=self.s.begin("learn:"+hashlib.sha256(text.encode()).hexdigest()[:12]); p,m=self._materialize(packet,news,g,f"generation:{g}"); obs=self.s.add_observation(text,p,self.lang,"user",g,occurrence_ref=f"generation:{g}")
                refs=[]
                for a in p.get("apps",[]):
                    ar=self.s.insert_app(a["operator"],a["args"],g,obs,a.get("stance","support"),.95,"provisional"); refs += [v for v in a["args"].values() if isinstance(v,str)]
                for surf_,ref in uses:self.s.record_use(surf_,self.lang,ref)
                self.s.touch(refs); self.s.rebuild_designations(); self.s.finish(g)
            out,rp=self.z.response(self.s.symbol("response.learned")); return {"status":"learned","response":out,"packet":p,"generation":g,"new_atoms":m,"trace":trace,"realization_proof":rp}
        except AmbiguousReferent as e:return self._frontier(text,"ambiguous_referent",{"surface":e.surface,"candidates":e.candidates})
        except Exception as e:return self._frontier(text,"learning_rejected",{"error":str(e),"packet":packet})
    def _frontier(self,text,reason,details):
        ref=self.s.frontier(text,reason,details); out,p=self.z.response(self.s.symbol("response.frontier")); return {"status":"frontier","response":out,"frontier":{"ref":ref,"reason":reason,"details":details},"realization_proof":p}

def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=["init","import","chat","learn","ask","inspect"]); p.add_argument("text",nargs="?"); p.add_argument("--db",default="cemm_mvp.sqlite"); p.add_argument("--data",action="append",default=[]); p.add_argument("--language",default="en"); a=p.parse_args(); s=Store(a.db)
    for d in a.data:s.import_data(d)
    rt=Runtime(s,a.language)
    if a.command in {"init","import"}:Codecs.get(s,a.language); print(canonical({"generation":s.generation,"hash":s.snapshot_hash()}))
    elif a.command in {"learn","ask"}:print(json.dumps(rt.process(a.text or "",a.command=="learn"),ensure_ascii=False,indent=2))
    elif a.command=="chat":
        for line in sys.stdin:
            if line.strip():print(rt.process(line.strip())["response"])
    else:
        for t in ("atoms","operator_roles","applications","bindings","claims","rules","language_examples","realization_examples","designation_index","label_stats","frontiers","generations"):print(t,s.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0])
        print("snapshot",s.snapshot_hash())
if __name__=="__main__":main()
