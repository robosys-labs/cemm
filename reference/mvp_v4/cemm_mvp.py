#!/usr/bin/env python3
"""CEMM minimal semantic brain MVP v3.

Core invariant:
- Exact semantic truth lives in the meaning DB / CSIR-like graph.
- Session cognition lives in a bounded semantic workspace of slots + transitions.
- Neural models rank/select learned semantic programs and surface plans; they do not
  become semantic authority.
- Responses are built from ordinary grounded meaning and semantic pointers. Full
  text round-trip verification is policy-driven, not a mandatory per-message tax.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, math, random, re, sqlite3, sys, unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from structured_codec import StructuredSemanticCodec
try:
    import torch
    from torch import nn
except Exception as exc:
    raise SystemExit("pip install torch") from exc

torch.set_num_threads(1)

DDL=r"""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS atoms(ref TEXT PRIMARY KEY,kind TEXT NOT NULL,metadata TEXT NOT NULL DEFAULT '{}',generation INTEGER NOT NULL,authority_scope TEXT NOT NULL DEFAULT 'authority' CHECK(authority_scope IN('authority','world')));
CREATE TABLE IF NOT EXISTS operator_roles(operator_ref TEXT NOT NULL,role_ref TEXT NOT NULL,required INTEGER NOT NULL DEFAULT 0,cardinality TEXT NOT NULL DEFAULT 'one',filler_kind TEXT,PRIMARY KEY(operator_ref,role_ref));
CREATE TABLE IF NOT EXISTS applications(app_ref TEXT PRIMARY KEY,operator_ref TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS bindings(binding_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,role_ref TEXT NOT NULL,filler_kind TEXT NOT NULL CHECK(filler_kind IN('atom','literal','app')),filler_value TEXT NOT NULL,ordinal INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS observations(observation_ref TEXT PRIMARY KEY,surface TEXT NOT NULL,modality TEXT NOT NULL,language TEXT NOT NULL,source_ref TEXT NOT NULL,observed_at TEXT NOT NULL,packet TEXT NOT NULL,confidence REAL NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS claims(claim_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,stance TEXT NOT NULL CHECK(stance IN('support','deny')),confidence REAL NOT NULL,authority_status TEXT NOT NULL,valid_from TEXT,valid_to TEXT,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS proof_links(proof_ref TEXT PRIMARY KEY,subject_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,operation TEXT NOT NULL,parent_refs TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS rules(rule_ref TEXT PRIMARY KEY,rule_kind TEXT NOT NULL CHECK(rule_kind IN('definition','entailment','causal','default')),antecedent TEXT NOT NULL,consequent TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 1,authority_status TEXT NOT NULL DEFAULT 'reviewed',generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS rule_candidates(candidate_ref TEXT PRIMARY KEY,rule_kind TEXT NOT NULL,antecedent TEXT NOT NULL,consequent TEXT NOT NULL,evidence_count INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'provisional',confidence REAL NOT NULL DEFAULT 0,first_generation INTEGER NOT NULL,last_generation INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rules_semantic ON rules(rule_kind,antecedent,consequent);
CREATE TABLE IF NOT EXISTS reference_forms(language TEXT NOT NULL,surface TEXT NOT NULL,features TEXT NOT NULL DEFAULT '{}',bound_ref TEXT,weight REAL NOT NULL DEFAULT 1,PRIMARY KEY(language,surface,bound_ref));
CREATE TABLE IF NOT EXISTS control_symbols(role TEXT PRIMARY KEY,semantic_ref TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS designation_index(label_ref TEXT PRIMARY KEY,target_ref TEXT NOT NULL,label_type_ref TEXT NOT NULL,surface TEXT NOT NULL,language TEXT NOT NULL,script TEXT NOT NULL,prior REAL NOT NULL,preferred INTEGER NOT NULL,context_ref TEXT);
CREATE INDEX IF NOT EXISTS idx_designation_surface ON designation_index(language,surface);
CREATE TABLE IF NOT EXISTS label_stats(label_ref TEXT PRIMARY KEY,use_count INTEGER NOT NULL DEFAULT 0,last_used TEXT);
CREATE TABLE IF NOT EXISTS discourse_entities(atom_ref TEXT PRIMARY KEY,salience REAL NOT NULL,last_turn INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS frontiers(frontier_ref TEXT PRIMARY KEY,surface TEXT NOT NULL,reason TEXT NOT NULL,details TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS generations(generation INTEGER PRIMARY KEY,parent_generation INTEGER,created_at TEXT NOT NULL,reason TEXT NOT NULL,content_hash TEXT NOT NULL);
"""
TOK=re.compile(r"@[aAxX][0-9]+|@[0-9]+|<[A-Za-z0-9_:.=-]+>|[\wÀ-ÿ:/?.!'-]+|[^\s]",re.UNICODE)
MODEL_CACHE={}

def now():return datetime.now(timezone.utc).isoformat()
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def stable(prefix,*parts):return f"{prefix}:{hashlib.sha256(canonical(parts).encode()).hexdigest()[:24]}"
def norm_text(s):return unicodedata.normalize("NFKC",str(s)).casefold()
def toks(s):return TOK.findall(unicodedata.normalize("NFKC",str(s).strip()))
def surface(ts):
    s=" ".join(ts); s=re.sub(r"\s+([.,!?;:])",r"\1",s); s=re.sub(r"([('¿¡])\s+",r"\1",s); s=re.sub(r"\s+([)'])",r"\1",s)
    return s[:1].upper()+s[1:] if s else s
def lit(value,typ="text"):return {"literal":{"type":typ,"value":value}}
def isvar(x):return isinstance(x,str) and x.startswith("?")
def isexist(x):return isinstance(x,str) and x.startswith("!")

class AmbiguousReferent(ValueError):
    def __init__(self,surface,candidates):self.surface,self.candidates=surface,candidates;super().__init__(surface)

@dataclass(frozen=True)
class Fact:
    ref:str; operator:str; args:dict[str,Any]; stance:str="support"; confidence:float=1.; derived:bool=False; proof:dict[str,Any]|None=None
    def signature(self):return stable("fact",self.operator,sorted(self.args.items(),key=lambda x:x[0]),self.stance)

class Store:
    SNAP=("atoms","operator_roles","applications","bindings","observations","claims","proof_links","rules","reference_forms","control_symbols")
    def __init__(self,path):
        self.path=str(path);self.db=sqlite3.connect(self.path);self.db.row_factory=sqlite3.Row;self.db.executescript(DDL)
        if not self.db.execute("SELECT 1 FROM generations").fetchone():
            self.db.execute("INSERT INTO generations VALUES(1,NULL,?,?,?)",(now(),"initial",hashlib.sha256(b"initial").hexdigest()));self.db.commit()
    @property
    def generation(self):return int(self.db.execute("SELECT max(generation) FROM generations").fetchone()[0])
    def begin(self,reason):
        g=self.generation+1;self.db.execute("INSERT INTO generations VALUES(?,?,?,?,?)",(g,g-1,now(),reason,"pending"));return g
    def finish(self,g):
        h=self.snapshot_hash();self.db.execute("UPDATE generations SET content_hash=? WHERE generation=?",(h,g));return h
    def snapshot_hash(self):
        material=[]
        for t in self.SNAP:
            cols=[x[1] for x in self.db.execute(f"PRAGMA table_info({t})") if x[1] not in {"observed_at","generation"}]
            rows=self.db.execute(f"SELECT {','.join(cols)} FROM {t} ORDER BY {cols[0]}").fetchall();material.append((t,[dict(r) for r in rows]))
        return hashlib.sha256(canonical(material).encode()).hexdigest()
    def authority_hash(self,upto_generation=None):
        g=self.generation if upto_generation is None else int(upto_generation);material=[]
        # Immutable kernel/language-control tables are all authority. Generation-bearing
        # records are pinned to the authority cutoff so later world learning cannot alter attestation.
        for t in ("operator_roles","reference_forms","control_symbols"):
            cols=[x[1] for x in self.db.execute(f"PRAGMA table_info({t})")];rows=self.db.execute(f"SELECT {','.join(cols)} FROM {t} ORDER BY {cols[0]}").fetchall();material.append((t,[dict(r) for r in rows]))
        for t in ("atoms","rules"):
            cols=[x[1] for x in self.db.execute(f"PRAGMA table_info({t})") if x[1]!="generation"]
            where="generation<=?"+(" AND authority_scope='authority'" if t=="atoms" else "")
            rows=self.db.execute(f"SELECT {','.join(cols)} FROM {t} WHERE {where} ORDER BY {cols[0]}",(g,)).fetchall();material.append((t,[dict(r) for r in rows]))
        rows=self.db.execute("""SELECT a.app_ref,a.operator_ref,b.role_ref,b.filler_kind,b.filler_value,c.stance,c.authority_status
          FROM applications a JOIN bindings b ON b.app_ref=a.app_ref JOIN claims c ON c.app_ref=a.app_ref JOIN observations o ON o.observation_ref=c.observation_ref
          WHERE a.generation<=? AND o.source_ref IN('seed','reviewed_acquisition') AND c.authority_status IN('reviewed','promoted') ORDER BY a.app_ref,b.role_ref,b.ordinal,c.stance""",(g,)).fetchall()
        material.append(("seed_semantics",[dict(r) for r in rows]));return hashlib.sha256(canonical(material).encode()).hexdigest()
    def exact(self,t,cols,vals,keys,ignore=()):
        try:self.db.execute(f"INSERT INTO {t}({','.join(cols)}) VALUES({','.join('?' for _ in vals)})",vals)
        except sqlite3.IntegrityError:
            kv=[vals[cols.index(k)] for k in keys];row=self.db.execute(f"SELECT * FROM {t} WHERE "+" AND ".join(f"{k}=?" for k in keys),kv).fetchone()
            if not row:raise
            for c,v in zip(cols,vals):
                if c not in ignore and row[c]!=v:raise ValueError(f"immutable conflict {t}:{kv}:{c}")
    def atom(self,ref):return self.db.execute("SELECT * FROM atoms WHERE ref=?",(ref,)).fetchone()
    def foundational(self,ref):
        a=self.atom(ref);return bool(a and json.loads(a["metadata"]).get("foundational"))
    def symbol(self,role):
        r=self.db.execute("SELECT semantic_ref FROM control_symbols WHERE role=?",(role,)).fetchone()
        if not r:raise ValueError(f"missing control symbol {role}")
        return str(r[0])
    def creatable_kinds(self):return {str(r[0]) for r in self.db.execute("SELECT semantic_ref FROM control_symbols WHERE role LIKE 'new_kind.%'")}
    def roles(self,op):return {r["role_ref"]:r for r in self.db.execute("SELECT * FROM operator_roles WHERE operator_ref=?",(op,))}
    def encode_value(self,v):
        if isinstance(v,dict) and "literal" in v:return "literal",canonical(v["literal"])
        if isinstance(v,dict) and "app" in v:return "app",str(v["app"])
        return "atom",str(v)
    def decode_value(self,k,v):return {"literal":json.loads(v)} if k=="literal" else {"app":v} if k=="app" else v
    def _validate_filler(self,role,v,spec):
        fk,fv=self.encode_value(v);exp=spec["filler_kind"]
        if exp and exp.startswith("literal:"):
            if fk!="literal" or json.loads(fv)["type"]!=exp.split(":",1)[1]:raise ValueError(f"literal kind {role}")
            return
        if fk=="atom" and not self.atom(fv):raise ValueError(f"unknown atom filler {role}:{fv}")
        if fk=="app" and not self.db.execute("SELECT 1 FROM applications WHERE app_ref=?",(fv,)).fetchone():raise ValueError(f"unknown app filler {role}:{fv}")
        if exp in {"atom","app"} and fk!=exp:raise ValueError(f"filler class {role}")
        if exp and exp not in {"atom","app"} and not exp.startswith("literal:"):
            a=self.atom(fv) if fk=="atom" else None
            if not a or a["kind"]!=exp:raise ValueError(f"filler kind {role}: expected {exp}")
    def validate_app(self,op,args):
        if not self.atom(op):raise ValueError(f"unknown operator {op}")
        specs=self.roles(op)
        for role,v in args.items():
            if role not in specs:raise ValueError(f"{op} disallows {role}")
            self._validate_filler(role,v,specs[role])
        for role,s in specs.items():
            if s["required"] and role not in args:raise ValueError(f"missing {op}:{role}")
    def app_signature(self,op,args):return stable("app",op,sorted((r,*self.encode_value(v)) for r,v in args.items()))
    def insert_app(self,op,args,g,obs,stance="support",confidence=1.,authority="reviewed",valid_from=None):
        self.validate_app(op,args);ar=self.app_signature(op,args);self.db.execute("INSERT OR IGNORE INTO applications VALUES(?,?,?)",(ar,op,g))
        for n,(role,v) in enumerate(sorted(args.items())):
            fk,fv=self.encode_value(v);br=stable("bind",ar,role,fk,fv,n);self.db.execute("INSERT OR IGNORE INTO bindings VALUES(?,?,?,?,?,?)",(br,ar,role,fk,fv,n))
        cr=stable("claim",ar,obs,stance);self.db.execute("INSERT OR IGNORE INTO claims VALUES(?,?,?,?,?,?,?,?,?)",(cr,ar,obs,stance,float(confidence),authority,valid_from,None,g));self.db.execute("INSERT OR IGNORE INTO proof_links VALUES(?,?,?,?,?)",(stable("proof",cr),cr,obs,"assert","[]"));self._supersede_state(ar,op,args,stance);return ar
    def _supersede_state(self,new_ref,op,args,stance):
        try:state_op=self.symbol("operator.state");subj=self.symbol("role.subject");dim=self.symbol("role.dimension");val=self.symbol("role.value")
        except ValueError:return
        if stance!="support" or op!=state_op or any(x not in args for x in (subj,dim,val)):return
        d=self.atom(str(args[dim]));meta=json.loads(d["metadata"]) if d else {}
        if not meta.get("exclusive"):return
        for f in self.base_facts():
            if f.ref!=new_ref and f.operator==op and f.stance=="support" and f.args.get(subj)==args[subj] and f.args.get(dim)==args[dim] and f.args.get(val)!=args[val]:
                self.db.execute("UPDATE claims SET valid_to=? WHERE app_ref=? AND stance='support' AND valid_to IS NULL",(now(),f.ref))
    def base_facts(self):
        out=[]
        for a in self.db.execute("SELECT * FROM applications ORDER BY app_ref"):
            args={}
            for b in self.db.execute("SELECT * FROM bindings WHERE app_ref=? ORDER BY role_ref,ordinal",(a["app_ref"],)):args[b["role_ref"]]=self.decode_value(b["filler_kind"],b["filler_value"])
            rows=self.db.execute("SELECT stance,confidence FROM claims WHERE app_ref=? AND valid_to IS NULL",(a["app_ref"],)).fetchall();st={r["stance"] for r in rows}
            if "support" in st:out.append(Fact(a["app_ref"],a["operator_ref"],args,"support",max(float(r["confidence"]) for r in rows if r["stance"]=="support")))
            if "deny" in st:out.append(Fact(a["app_ref"],a["operator_ref"],args,"deny",max(float(r["confidence"]) for r in rows if r["stance"]=="deny")))
        return out
    def add_observation(self,surface_,packet,lang,source,g,confidence=.95,occurrence_ref=None):
        ref=stable("obs",surface_,lang,source,packet,occurrence_ref or "dedup");self.db.execute("INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?,?,?,?)",(ref,surface_,"language",lang,source,now(),canonical(packet),confidence,g));return ref
    def validate_rule(self,x):
        ants=list(x.get("if",[]));cons=list(x.get("then",[]))
        if not ants or not cons:raise ValueError("rule requires antecedent and consequent")
        if not 0<float(x.get("confidence",1))<=1:raise ValueError("rule confidence out of range")
        bound={v for c in ants for v in c.get("args",{}).values() if isvar(v)}
        if any(isexist(v) for c in ants for v in c.get("args",{}).values()):raise ValueError("existential witness cannot appear in antecedent")
        for c in ants+cons:
            op=c.get("operator")
            if not self.atom(op):raise ValueError(f"rule unknown operator {op}")
            specs=self.roles(op)
            for role,v in c.get("args",{}).items():
                if role not in specs:raise ValueError(f"rule {op} disallows {role}")
                if isinstance(v,str) and (isvar(v) or isexist(v)):
                    if c in cons and isvar(v) and v not in bound:raise ValueError(f"unbound consequent variable {v}")
                    continue
                self._validate_filler(role,v,specs[role])
            if c in cons:
                for role,r in specs.items():
                    if r["required"] and role not in c.get("args",{}):raise ValueError(f"rule consequent missing {op}:{role}")
    def infer_state_dimension(self,value_ref):
        try:
            rv=self.symbol("policy.state_value_relation");rd=self.symbol("policy.state_dimension_relation")
        except ValueError:return None
        specs=[f.args.get("role:subject") for f in self.base_facts() if f.operator=="op:relation" and f.stance=="support" and f.args.get("role:relation")==rv and f.args.get("role:object")==value_ref]
        dims={f.args.get("role:object") for f in self.base_facts() if f.operator=="op:relation" and f.stance=="support" and f.args.get("role:subject") in specs and f.args.get("role:relation")==rd}
        return next(iter(dims)) if len(dims)==1 else None
    def upsert_rule_candidate(self,rule,g,confidence=.9,min_evidence=2):
        self.validate_rule(rule);ant=canonical(rule["if"]);con=canonical(rule["then"]);kind=rule.get("rule_kind","definition");ref=stable("rulecand",kind,ant,con)
        row=self.db.execute("SELECT * FROM rule_candidates WHERE candidate_ref=?",(ref,)).fetchone()
        if row:self.db.execute("UPDATE rule_candidates SET evidence_count=evidence_count+1,last_generation=?,confidence=max(confidence,?) WHERE candidate_ref=?",(g,float(confidence),ref))
        else:self.db.execute("INSERT INTO rule_candidates VALUES(?,?,?,?,?,?,?,?,?)",(ref,kind,ant,con,1,"provisional",float(confidence),g,g))
        row=self.db.execute("SELECT * FROM rule_candidates WHERE candidate_ref=?",(ref,)).fetchone();promoted=False
        if int(row["evidence_count"])>=int(min_evidence) and row["status"]!="promoted":
            rr=stable("rule",kind,ant,con);self.db.execute("INSERT OR IGNORE INTO rules VALUES(?,?,?,?,?,?,?)",(rr,kind,ant,con,float(row["confidence"]),"promoted",g));self.db.execute("UPDATE rule_candidates SET status='promoted' WHERE candidate_ref=?",(ref,));promoted=True
        return ref,promoted
    def import_data(self,path):
        d=json.loads(Path(path).read_text(encoding="utf-8"))
        with self.db:
            g=self.begin(f"import:{Path(path).name}")
            for x in d.get("atoms",[]):self.exact("atoms",["ref","kind","metadata","generation"],[x["ref"],x["kind"],canonical(x.get("metadata",{})),g],["ref"],{"generation"})
            for x in d.get("operator_roles",[]):
                if x.get("cardinality","one")!="one":raise ValueError("MVP supports one filler per role; represent multiplicity with repeated applications")
                self.exact("operator_roles",["operator_ref","role_ref","required","cardinality","filler_kind"],[x["operator_ref"],x["role_ref"],int(x.get("required",False)),"one",x.get("filler_kind")],["operator_ref","role_ref"])
            for k,v in d.get("control_symbols",{}).items():self.exact("control_symbols",["role","semantic_ref"],[k,v],["role"])
            for x in d.get("reference_forms",[]):self.exact("reference_forms",["language","surface","features","bound_ref","weight"],[x.get("language","en"),x["surface"],canonical(x.get("features",{})),x.get("bound_ref"),float(x.get("weight",1))],["language","surface","bound_ref"])
            for x in d.get("rules",[]):
                self.validate_rule(x);rk=x.get("rule_kind","entailment");ant=canonical(x.get("if",[]));con=canonical(x.get("then",[]))
                if self.db.execute("SELECT 1 FROM rules WHERE rule_kind=? AND antecedent=? AND consequent=?",(rk,ant,con)).fetchone():continue
                self.exact("rules",["rule_ref","rule_kind","antecedent","consequent","confidence","authority_status","generation"],[x["rule_ref"],rk,ant,con,float(x.get("confidence",1)),x.get("authority_status","reviewed"),g],["rule_ref"],{"generation"})
            for x in d.get("facts",[]):
                obs=self.add_observation(x.get("source_text",x.get("fact_ref",x["operator"])),x,"und",x.get("source_ref","seed"),g,float(x.get("confidence",1)));self.insert_app(x["operator"],x.get("args",{}),g,obs,x.get("stance","support"),x.get("confidence",1),x.get("authority_status","reviewed"))
            self.rebuild_designations();self.finish(g)
        return g
    def rebuild_designations(self):
        self.db.execute("DELETE FROM designation_index")
        try:op=self.symbol("operator.designation");roles={k:self.symbol(f"designation.{k}") for k in ("target","type","surface","language","script","prior","preferred","context")}
        except ValueError:return
        for f in self.base_facts():
            if f.operator!=op or f.stance!="support":continue
            def v(k,default=None):
                x=f.args.get(roles[k],default);return x.get("literal",{}).get("value") if isinstance(x,dict) and "literal" in x else x
            if not v("target") or not v("surface"):continue
            self.db.execute("INSERT OR REPLACE INTO designation_index VALUES(?,?,?,?,?,?,?,?,?)",(f.ref,str(v("target")),str(v("type","label:default")),str(v("surface")),str(v("language","und")),str(v("script","Zyyy")),float(v("prior",1)),int(bool(v("preferred",False))),v("context")))
    def label_candidates(self,surf,lang,kind=None):
        rows=self.db.execute("""SELECT d.*,a.kind,coalesce(s.use_count,0) use_count,coalesce(e.salience,0) salience FROM designation_index d JOIN atoms a ON a.ref=d.target_ref LEFT JOIN label_stats s ON s.label_ref=d.label_ref LEFT JOIN discourse_entities e ON e.atom_ref=d.target_ref WHERE d.language IN (?, 'und')""",(lang,)).fetchall();by={};needle=norm_text(surf.strip())
        for r in rows:
            if r["context_ref"] is not None: continue
            if norm_text(r["surface"])!=needle or (kind and r["kind"]!=kind):continue
            score=float(r["prior"])+.25*int(r["preferred"])+.05*math.log1p(int(r["use_count"]))+.8*float(r["salience"])+(.08 if r["language"]==lang else 0);old=by.get(r["target_ref"])
            if not old or score>old[0]:by[r["target_ref"]]=(score,r)
        return sorted([(ref,*x) for ref,x in by.items()],key=lambda x:(-x[1],x[0]))
    def resolve_label(self,surf,lang,kind=None,margin=.18):
        cs=self.label_candidates(surf,lang,kind)
        if not cs:return None
        if len(cs)>1 and cs[0][1]-cs[1][1]<margin:raise AmbiguousReferent(surf,[{"ref":x[0],"score":x[1]} for x in cs[:5]])
        return cs[0][0]
    def record_use(self,surf,lang,ref):
        rows=self.db.execute("SELECT label_ref,surface,preferred,prior FROM designation_index WHERE target_ref=? AND language IN (?, 'und') ORDER BY preferred DESC,prior DESC",(ref,lang)).fetchall();needle=norm_text(surf);r=next((x for x in rows if norm_text(x["surface"])==needle),None)
        if r:self.db.execute("INSERT INTO label_stats VALUES(?,1,?) ON CONFLICT(label_ref) DO UPDATE SET use_count=use_count+1,last_used=excluded.last_used",(r["label_ref"],now()))
    def preferred(self,ref,lang,context=None):
        rows=self.db.execute("SELECT d.*,coalesce(s.use_count,0) use_count FROM designation_index d LEFT JOIN label_stats s ON s.label_ref=d.label_ref WHERE target_ref=? AND language IN (?, 'und')",(ref,lang)).fetchall()
        if not rows:return ref
        def score(r):return float(r["prior"])+.5*int(r["preferred"])+.04*math.log1p(int(r["use_count"]))+(.1 if r["language"]==lang else 0)+(.7 if context and r["context_ref"]==context else 0)-(.15 if context and r["context_ref"] and r["context_ref"]!=context else 0)
        return str(max(rows,key=score)["surface"])
    def touch(self,refs):
        self.db.execute("UPDATE discourse_entities SET salience=salience*.55");turn=int(self.db.execute("SELECT coalesce(max(last_turn),0)+1 FROM discourse_entities").fetchone()[0])
        for ref in set(refs):
            a=self.atom(ref)
            if a and a["kind"] in {"entity","participant","resource","source","existential"}:self.db.execute("INSERT INTO discourse_entities VALUES(?,1,?) ON CONFLICT(atom_ref) DO UPDATE SET salience=min(3,salience+1),last_turn=excluded.last_turn",(ref,turn))
    def frontier(self,surface_,reason,details):
        ref=stable("frontier",surface_,reason,details,self.generation);self.db.execute("INSERT OR IGNORE INTO frontiers VALUES(?,?,?,?,?)",(ref,surface_,reason,canonical(details),self.generation));self.db.commit();return ref
    def find_relation_object(self,subject,relation):
        for f in self.base_facts():
            if f.stance=="support" and f.operator=="op:relation" and f.args.get("role:subject")==subject and f.args.get("role:relation")==relation:return f.args.get("role:object")
        return None
    def user_visible_fact(self,f):
        if f.operator==self.symbol("operator.designation"): return False
        if f.operator=="op:relation":
            rel=f.args.get("role:relation");a=self.atom(rel) if isinstance(rel,str) else None
            if a and json.loads(a["metadata"]).get("user_visible") is False:return False
        return True

class LanguagePack:
    def __init__(self,path):
        self.path=str(path);self.data=json.loads(Path(path).read_text(encoding="utf-8"));self.language=self.data["language"];self.hash=self.data["pack_hash"];self.grammar=set(self.data.get("grammar_tokens",[]))

class TransformerClassifier(nn.Module):
    def __init__(self,vocab,ncls,d=48):
        super().__init__();self.emb=nn.Embedding(vocab,d,padding_idx=0);self.pos=nn.Embedding(128,d);layer=nn.TransformerEncoderLayer(d,4,96,dropout=0,batch_first=True);self.enc=nn.TransformerEncoder(layer,1);self.out=nn.Linear(d,ncls)
    def forward(self,x):
        p=torch.arange(x.size(1),device=x.device)[None,:];h=self.enc(self.emb(x)+self.pos(p),src_key_padding_mask=x.eq(0));mask=x.ne(0).float().unsqueeze(-1);z=(h*mask).sum(1)/mask.sum(1).clamp_min(1);return self.out(z)

def train_classifier(examples,key,label_key,seed=11,epochs=120):
    labels=sorted({x[label_key] for x in examples});li={x:i for i,x in enumerate(labels)};vocab=["<pad>","<unk>"]+sorted({t.casefold() for x in examples for t in toks(x[key])});vi={x:i for i,x in enumerate(vocab)};seqs=[[vi.get(t.casefold(),1) for t in toks(x[key])] for x in examples];m=max(map(len,seqs));X=torch.tensor([s+[0]*(m-len(s)) for s in seqs]);Y=torch.tensor([li[x[label_key]] for x in examples]);torch.manual_seed(seed);net=TransformerClassifier(len(vocab),len(labels));opt=torch.optim.AdamW(net.parameters(),lr=.01)
    for _ in range(epochs):opt.zero_grad();loss=nn.functional.cross_entropy(net(X),Y);loss.backward();opt.step()
    net.eval();return {"labels":labels,"vi":vi,"train_texts":[x[key] for x in examples]},net

def predict_classifier(meta,net,text):
    seq=[meta["vi"].get(t.casefold(),1) for t in toks(text)];known=sum(i!=1 for i in seq)/max(1,len(seq));x=torch.tensor([seq or [1]])
    with torch.no_grad():p=torch.softmax(net(x),-1)[0];vals,idx=torch.topk(p,min(2,len(p)))
    label=meta["labels"][int(idx[0])];margin=float(vals[0]-(vals[1] if len(vals)>1 else 0));return label,float(vals[0]),margin,known

class SurfaceCodec:
    def __init__(self,pack):
        ex=pack.data.get("realization_examples",[]);self.meta,self.net=train_classifier(ex,"semantic","surface_plan",23,110);self.allowed={}
        for x in ex:self.allowed.setdefault(norm_text(x["semantic"]),set()).add(norm_text(x["surface_plan"]))
    @classmethod
    def get(cls,pack):
        key=(pack.hash,"surface-v4")
        if key not in MODEL_CACHE:MODEL_CACHE[key]=cls(pack)
        return MODEL_CACHE[key]
    def realize(self,semantic):
        plan,p,m,k=predict_classifier(self.meta,self.net,semantic);authorized=norm_text(plan) in self.allowed.get(norm_text(semantic),set());return plan,{"semantic":semantic,"surface_plan":plan,"confidence":p,"margin":m,"known_token_ratio":k,"authorized_transform":authorized}

class Delexer:
    def __init__(self,s,lang,authority_generation=None):self.s,self.lang,self.authority_generation=s,lang,authority_generation;self.sal={r["atom_ref"]:float(r["salience"]) for r in s.db.execute("SELECT * FROM discourse_entities")}
    def reference(self,surf):
        rows=[r for r in self.s.db.execute("SELECT * FROM reference_forms WHERE language IN (?, 'und') ORDER BY weight DESC",(self.lang,)).fetchall() if norm_text(r["surface"])==norm_text(surf)]
        for r in rows:
            if r["bound_ref"]:return str(r["bound_ref"])
            f=json.loads(r["features"]);cs=[];required_type=f.get("required_type");typed=set()
            if required_type:
                facts,_=Inference(self.s,max_rounds=8,max_facts=500,authority_generation=self.authority_generation).closure();typed={x.args.get("role:instance") for x in facts if x.operator=="op:type" and x.stance=="support" and x.args.get("role:class")==required_type}
            for ref,score in self.sal.items():
                a=self.s.atom(ref);meta={k:v for k,v in f.items() if k not in {"kind","required_type"}}
                if a and all(json.loads(a["metadata"]).get(k)==v for k,v in meta.items()) and (not f.get("kind") or a["kind"]==f["kind"]) and (not required_type or ref in typed):cs.append((score,ref))
            cs.sort(reverse=True)
            if cs:
                if len(cs)>1 and cs[0][0]-cs[1][0]<.25:raise AmbiguousReferent(surf,[{"ref":x[1],"score":x[0]} for x in cs[:5]])
                return cs[0][1]
        return None
    def run(self,text):
        phmap={};rev={};uses=[];nexti=0;out=[]
        def ph(ref):
            nonlocal nexti
            if ref not in rev:rev[ref]=f"@A{nexti}";phmap[rev[ref]]=ref;nexti+=1
            return rev[ref]
        labels=self.s.db.execute("SELECT DISTINCT surface FROM designation_index WHERE language IN (?, 'und') AND context_ref IS NULL ORDER BY length(surface) DESC",(self.lang,)).fetchall();refs=self.s.db.execute("SELECT DISTINCT surface FROM reference_forms WHERE language IN (?, 'und') ORDER BY length(surface) DESC",(self.lang,)).fetchall()
        for sent in re.split(r"(?<=[.!?])\s+",text.strip()):
            cand=[]
            for typ,rows in (("ref",refs),("label",labels)):
                for row in rows:
                    q=str(row[0])
                    for m in re.finditer(r"(?<!\w)"+re.escape(q)+r"(?!\w)",sent,flags=re.I):cand.append((m.start(),m.end(),typ,q))
            chosen=[]
            for c in sorted(cand,key=lambda x:(x[0],-(x[1]-x[0]),0 if x[2]=="ref" else 1)):
                if not any(c[0]<x[1] and c[1]>x[0] for x in chosen):chosen.append(c)
            pos=0;pieces=[];mentioned=[]
            for a,b,typ,q in sorted(chosen):
                pieces.append(sent[pos:a]);ref=self.reference(q) if typ=="ref" else self.s.resolve_label(q,self.lang)
                if ref:pieces.append(ph(ref));mentioned.append(ref);uses.append((q,ref)) if typ=="label" else None
                else:pieces.append(sent[a:b])
                pos=b
            pieces.append(sent[pos:]);out.append("".join(pieces));self.sal={k:v*.55 for k,v in self.sal.items()}
            for ref in mentioned:self.sal[ref]=min(3,self.sal.get(ref,0)+1)
        return " ".join(out),phmap,uses

class ExactStructuredCompiler:
    def __init__(self,s):self.s=s
    def _kind_ok(self,spec,v):
        exp=spec["filler_kind"]
        if isinstance(v,dict) and "new" in v:return exp in {None,"atom",v.get("kind")}
        if isinstance(v,dict) and "literal" in v:return bool(exp and exp.startswith("literal:") and v["literal"].get("type")==exp.split(":",1)[1])
        a=self.s.atom(v) if isinstance(v,str) else None
        return bool(a and (not exp or exp=="atom" or a["kind"]==exp))
    def _rename(self,v,prefix,map_):
        if isinstance(v,dict) and "new" in v:
            old=v["new"]
            if old not in map_:map_[old]=f"@X_{prefix}_{old.replace('@X_','')}"
            return {"new":map_[old],"kind":v.get("kind","entity")}
        return v
    def compile(self,packet,prefix="C0"):
        p=json.loads(canonical(packet));news=[];ren={}
        def one(a):
            op=a["operator"];specs=self.s.roles(op)
            if not specs:raise ValueError(f"unknown/non-executable operator:{op}")
            args={r:self._rename(v,prefix,ren) for r,v in a.get("args",{}).items() if r in specs}
            if op=="op:state" and "role:dimension" not in args and "role:value" in args and isinstance(args["role:value"],str):
                dim=self.s.infer_state_dimension(args["role:value"])
                if dim:args["role:dimension"]=dim
            for r,sp in specs.items():
                if sp["required"] and r not in args:raise ValueError(f"missing {op}:{r}")
            for r,v in args.items():
                if not self._kind_ok(specs[r],v):raise ValueError(f"invalid filler {op}:{r}:{v}")
            return {"operator":op,"args":args,"stance":a.get("stance","support")}
        apps=[one(x) for x in p.get("apps",[])];query=one(p["query"]) if p.get("query") else None;describe=p.get("describe")
        if describe is not None:
            if not isinstance(describe,str) or not self.s.atom(describe):raise ValueError("invalid describe referent")
        for old,newtok in ren.items():
            # recover kind from all occurrences
            kind=None
            for a0 in list(p.get("apps",[]))+([p["query"]] if p.get("query") else []):
                for v in a0.get("args",{}).values():
                    if isinstance(v,dict) and v.get("new")==old:kind=v.get("kind")
            news.append({"token":newtok,"kind":kind or "entity"})
        return {"apps":apps,"query":query,"describe":describe},news

class SemanticSettler:
    """Tiny N-best recurrent settling proof.

    Neural likelihood proposes structure. Exact compilation clamps impossible graphs.
    Recurrent inhibition sharpens competing exact candidates; it never overrides exact
    semantic constraints.
    """
    def __init__(self,s,compiler):self.s,self.compiler=s,compiler
    def settle(self,candidates,prefix="C0"):
        valid=[]
        for c in candidates:
            try:p,news=self.compiler.compile(c.packet,prefix)
            except Exception as e:continue
            sig=canonical(p);valid.append({"packet":p,"news":news,"base":float(c.score),"trace":c.trace,"sig":sig})
        by={}
        for x in valid:
            if x["sig"] not in by or x["base"]>by[x["sig"]]["base"]:by[x["sig"]]=x
        xs=list(by.values())
        if not xs:return None,{"status":"no_exact_candidate","candidates":[]}
        m=max(x["base"] for x in xs)
        for x in xs:x["energy"]=x["base"]-m+.35
        for _ in range(4):
            z=sum(math.exp(x["energy"]) for x in xs);probs=[math.exp(x["energy"])/z for x in xs]
            for i,x in enumerate(xs):x["energy"]=(x["base"]-m+.35)-.28*(1-probs[i])
        z=sum(math.exp(x["energy"]) for x in xs)
        for x in xs:x["posterior"]=math.exp(x["energy"])/z
        xs.sort(key=lambda x:x["posterior"],reverse=True);top=xs[0];margin=top["posterior"]-(xs[1]["posterior"] if len(xs)>1 else 0)
        trace={"status":"settled" if len(xs)==1 or (top["posterior"]>=.48 and margin>=.06) else "ambiguous","posterior":top["posterior"],"margin":margin,"candidates":[{"posterior":round(x["posterior"],4),"packet":x["packet"],"neural":x["trace"]} for x in xs[:5]]}
        return (top["packet"],top["news"]) if trace["status"]=="settled" else None,trace

class Interpreter:
    def __init__(self,s,pack,authority_generation=None):self.s,self.pack,self.authority_generation=s,pack,authority_generation;self.lang=pack.language;self.codec=StructuredSemanticCodec(pack);self.compiler=ExactStructuredCompiler(s);self.settler=SemanticSettler(s,self.compiler)
    def _localize(self,clause,global_ph):
        order=[]
        for g in re.findall(r"@A\d+",clause):
            if g not in order:order.append(g)
        g2l={g:f"@A{i}" for i,g in enumerate(order)};local=clause
        for g,l in sorted(g2l.items(),key=lambda x:-len(x[0])):local=local.replace(g,l)
        anchors={l:global_ph[g] for g,l in g2l.items() if g in global_ph}
        for l,ref in anchors.items():
            a=self.s.atom(ref);kind=a["kind"] if a else "atom";local=local.replace(l,f"{l}<{kind}>")
        return local,anchors
    def parse(self,text):
        delex,ph,uses=Delexer(self.s,self.lang,self.authority_generation).run(text);clauses=[x.strip() for x in re.split(r"(?<=[.!?])\s+",delex.strip()) if x.strip()];combined={"apps":[],"query":None,"describe":None};news=[];traces=[]
        for i,clause in enumerate(clauses or [delex]):
            local,anchors=self._localize(clause,ph);cands=self.codec.predict(local,anchors,self.s,top_k=10);settled,trace=self.settler.settle(cands,f"C{i}");trace["input"]=local;traces.append(trace)
            if not settled:return None,[],uses,{"reason":"semantic_graph_unsettled","clauses":traces}
            pkt,nw=settled;news+=nw
            if pkt.get("query") or pkt.get("describe"):
                if len(clauses)>1 or combined["apps"]:return None,[],uses,{"reason":"mixed_query_document","clauses":traces}
                combined["query"],combined["describe"]=pkt.get("query"),pkt.get("describe")
            else:combined["apps"].extend(pkt.get("apps",[]))
        return combined,news,uses,{"structured_prediction":True,"clauses":traces,"n_best":True}
    def delex_for_rule(self,text):
        delex,ph,uses=Delexer(self.s,self.lang,self.authority_generation).run(text);return (*self._localize(delex,ph),uses)

class RuleLearner:
    def __init__(self,s,interpreter,min_evidence=2):self.s,self.i,self.min_evidence=s,interpreter,min_evidence
    def teach(self,text):
        local,anchors,uses=self.i.delex_for_rule(text);cands=self.i.codec.predict_rules(local,anchors,self.s,top_k=5);valid=[]
        for r in cands:
            rule={k:r[k] for k in ("rule_kind","if","then")}
            try:self.s.validate_rule(rule);valid.append((rule,float(r["score"])))
            except Exception:continue
        if not valid:return {"status":"frontier","reason":"rule_induction_unsettled","input":local}
        valid.sort(key=lambda x:x[1],reverse=True);rule,score=valid[0];margin=score-(valid[1][1] if len(valid)>1 else score-1)
        if len(valid)>1 and margin<.05:return {"status":"frontier","reason":"rule_induction_ambiguous","candidates":[x[0] for x in valid[:3]]}
        with self.s.db:
            g=self.s.begin("rule_learning:"+hashlib.sha256(text.encode()).hexdigest()[:12]);obs=self.s.add_observation(text,{"rule":rule},self.i.lang,"teaching",g,occurrence_ref=f"rule:{g}");ref,promoted=self.s.upsert_rule_candidate(rule,g,confidence=min(1,.75+max(0,margin)),min_evidence=self.min_evidence);self.s.finish(g)
        return {"status":"promoted_rule" if promoted else "provisional_rule","candidate_ref":ref,"rule":rule,"generation":g,"margin":margin,"observation_ref":obs}

class Inference:
    def __init__(self,s,max_rounds=12,max_facts=1000,authority_generation=None):self.s,self.max_rounds,self.max_facts,self.authority_generation=s,max_rounds,max_facts,authority_generation;self.incomplete=False;self.incomplete_reason=None
    def closure(self,extra=()):
        self.incomplete=False;self.incomplete_reason=None;facts=list(self.s.base_facts())+list(extra);bysig={f.signature():f for f in facts};byref={f.ref:f for f in facts};cut=self.authority_generation if self.authority_generation is not None else self.s.generation;rules=[dict(r) for r in self.s.db.execute("SELECT * FROM rules WHERE rule_kind IN('definition','entailment') AND authority_status IN('reviewed','promoted') AND generation<=? ORDER BY rule_ref",(cut,))]
        for _ in range(self.max_rounds):
            added=0
            for r in rules:
                ants=json.loads(r["antecedent"]);cons=json.loads(r["consequent"])
                for env,parents in self._matches(ants,list(bysig.values())):
                    ex={};parent_refs=tuple(sorted(x.ref for x in parents))
                    for c in cons:
                        args={k:self._inst(v,env,ex,r["rule_ref"],parent_refs) for k,v in c.get("args",{}).items()};st=c.get("stance","support");ref=stable("derived",r["rule_ref"],parent_refs,c.get("operator"),args,st);f=Fact(ref,c["operator"],args,st,min([x.confidence for x in parents]+[1.])*float(r["confidence"]),True,{"rule_ref":r["rule_ref"],"parents":parent_refs})
                        if f.signature() not in bysig:bysig[f.signature()]=f;byref[f.ref]=f;added+=1
                        if len(bysig)>=self.max_facts:self.incomplete=True;self.incomplete_reason="max_facts";return list(bysig.values()),byref
            if not added:break
        else:self.incomplete=True;self.incomplete_reason="max_rounds"
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
        if c.get("stance","support")!=f.stance or not self._unify(c["operator"],f.operator,env):return False
        return all(role in f.args and self._unify(pv,f.args[role],env) for role,pv in c.get("args",{}).items())
    def _unify(self,p,v,env):
        if isvar(p):
            if p in env:return canonical(env[p])==canonical(v)
            env[p]=v;return True
        return canonical(p)==canonical(v)
    def _inst(self,v,env,ex,rule,parents):
        if isvar(v):return env[v]
        if isexist(v):
            if v not in ex:ex[v]=stable("existential",rule,parents,v)
            return ex[v]
        return v
    def match(self,pattern,facts):return [f for f in facts if self._unify_clause({"operator":pattern["operator"],"args":pattern.get("args",{}),"stance":pattern.get("stance","support")},f,{})]
    def explain(self,f,byref):
        if not f.derived:return {"fact_ref":f.ref,"source":"observed","operator":f.operator,"args":f.args}
        return {"fact_ref":f.ref,"source":"derived","operator":f.operator,"args":f.args,"rule_ref":f.proof["rule_ref"],"parents":[self.explain(byref[x],byref) for x in f.proof["parents"] if x in byref]}

@dataclass
class StateTransition:
    dimension:str; before:str|None; after:str; cause:str; turn:int

class SessionSelf:
    def __init__(self,s):
        self.s=s;self.turn=0;self.state={s.symbol("self.response_state_dimension"):s.symbol("self.ready"),s.symbol("self.interpretation_state_dimension"):s.symbol("self.resolved"),s.symbol("self.epistemic_state_dimension"):s.symbol("self.sufficient")};self.transitions=[]
    def set(self,dimension,value,cause):
        before=self.state.get(dimension);self.turn+=1
        if before!=value:self.state[dimension]=value;self.transitions.append(StateTransition(dimension,before,value,cause,self.turn))
    def slots(self):
        selfref=self.s.symbol("self.ref");op=self.s.symbol("operator.state");return [Fact(stable("selfslot",d,v),op,{"role:subject":selfref,"role:dimension":d,"role:value":v},"support",1,True,{"session_state":True}) for d,v in self.state.items()]

@dataclass
class WorkspaceSlot:
    ref:str;fact:Fact;score:float;features:dict[str,float]

class WorkspaceNet(nn.Module):
    def __init__(self,d=24):
        super().__init__();self.proj=nn.Linear(6,d);layer=nn.TransformerEncoderLayer(d,4,48,dropout=0,batch_first=True);self.enc=nn.TransformerEncoder(layer,1);self.out=nn.Linear(d,1)
    def forward(self,x):return self.out(self.enc(self.proj(x))).squeeze(-1)

def workspace_model():
    k="workspace-v3"
    if k in MODEL_CACHE:return MODEL_CACHE[k]
    torch.manual_seed(7);random.seed(7);net=WorkspaceNet();opt=torch.optim.AdamW(net.parameters(),lr=.01);X=[];Y=[]
    for _ in range(96):
        seq=[];target=[]
        for _j in range(8):
            overlap=random.random();selfish=random.choice([0.,1.]);conf=random.uniform(.5,1);derived=random.choice([0.,1.]);sal=random.random();recent=random.random();seq.append([overlap,selfish,conf,derived,sal,recent]);target.append(2.4*overlap+.7*selfish+.35*conf+.25*sal+.15*recent-.08*derived)
        X.append(seq);Y.append(target)
    X=torch.tensor(X,dtype=torch.float32);Y=torch.tensor(Y,dtype=torch.float32)
    for _ in range(55):opt.zero_grad();q=net(X);loss=nn.functional.mse_loss(q,Y);loss.backward();opt.step()
    net.eval();MODEL_CACHE[k]=net;return net

class Workspace:
    def __init__(self,s,selfstate,top_k=24):self.s,self.selfstate,self.top_k=s,selfstate,top_k
    def build(self,facts,query=None,proof_refs=()):
        context={self.s.symbol("self.ref")}
        if query:
            for v in query.get("args",{}).values():
                if isinstance(v,str):context.add(v)
        discourse={r["atom_ref"]:(float(r["salience"]),int(r["last_turn"])) for r in self.s.db.execute("SELECT * FROM discourse_entities")};allfacts=list(facts)+self.selfstate.slots();vecs=[]
        for f in allfacts:
            refs={f.operator}|{str(v) for v in f.args.values() if isinstance(v,str)};overlap=len(refs&context)/max(1,len(context));selfish=float(self.s.symbol("self.ref") in refs);sal=max([discourse.get(r,(0,0))[0] for r in refs] or [0]);recent=max([discourse.get(r,(0,0))[1] for r in refs] or [0]);vecs.append([overlap,selfish,float(f.confidence),float(f.derived),min(1,sal/3),1/(1+max(0,self.selfstate.turn-recent))])
        if not vecs:return [],{"selected":[],"top_k":self.top_k}
        model=workspace_model()
        with torch.no_grad():scores=model(torch.tensor([vecs],dtype=torch.float32))[0].tolist()
        hard=set(proof_refs);ranked=sorted(zip(allfacts,scores,vecs),key=lambda x:(x[0].ref not in hard,-x[1],x[0].ref));selected=[]
        for f,score,v in ranked:
            if len(selected)>=self.top_k and f.ref not in hard:continue
            selected.append(WorkspaceSlot(f.ref,f,float(score),{"overlap":v[0],"self":v[1],"confidence":v[2],"derived":v[3],"salience":v[4],"recency":v[5]}))
        return selected,{"top_k":self.top_k,"selected":[{"ref":x.ref,"operator":x.fact.operator,"score":round(x.score,4),"features":x.features} for x in selected]}

class ResponsePlanner:
    def __init__(self,s):self.s=s
    def plan(self,outcome):
        result=self.s.symbol(f"result.{outcome}");goalrel=self.s.symbol("policy.response_goal_relation");goal=self.s.find_relation_object(result,goalrel)
        if not goal:raise ValueError(f"no response goal for {outcome}")
        valrel=self.s.symbol("policy.response_value_relation");value=self.s.find_relation_object(goal,valrel)
        if value:return {"goal":goal,"value":value,"facts":[]}
        srel=self.s.symbol("policy.response_state_subject_relation");prel=self.s.symbol("policy.response_state_spec_relation");subject=self.s.find_relation_object(goal,srel);spec=self.s.find_relation_object(goal,prel)
        if not subject or not spec:raise ValueError(f"incomplete response plan for {goal}")
        dim=self.s.find_relation_object(spec,self.s.symbol("policy.state_dimension_relation"));val=self.s.find_relation_object(spec,self.s.symbol("policy.state_value_relation"))
        if not dim or not val:raise ValueError(f"incomplete state spec {spec}")
        return {"goal":goal,"facts":[Fact(stable("planfact",goal,subject,dim,val),"op:state",{"role:subject":subject,"role:dimension":dim,"role:value":val})]}

def pointerize_fact(f):
    refs=[];contexts={}
    for role,v in sorted(f.args.items()):
        if isinstance(v,str) and v not in refs: refs.append(v); contexts[v]=role
    mp={r:f"@A{i}" for i,r in enumerate(refs)};parts=["FACT",f.stance,f.operator]
    for r,v in sorted(f.args.items()):parts += [r,mp.get(v,str(v))]
    return " ".join(parts),{mp[r]:(r,contexts.get(r)) for r in refs}

def pointerize_plan(plan):
    refs=[]
    def add(v):
        if isinstance(v,str) and v not in refs:refs.append(v)
    if plan.get("value"):add(plan["value"])
    for f in plan.get("facts",[]):
        for _,v in sorted(f.args.items()):add(v)
    mp={r:f"@A{i}" for i,r in enumerate(refs)};contexts={}
    if plan.get("value"): contexts[plan["value"]]="response:value"
    for f in plan.get("facts",[]):
        for role,v in sorted(f.args.items()): contexts.setdefault(v,role)
    parts=["PLAN",plan["goal"]]
    if plan.get("value"):parts += ["VALUE",mp[plan["value"]]]
    for f in plan.get("facts",[]):
        parts += ["|","FACT",f.stance,f.operator]
        for r,v in sorted(f.args.items()): parts += [r,mp.get(v,str(v))]
    return " ".join(parts),{mp[r]:(r,contexts.get(r)) for r in refs}

class PointerRealizer:
    def __init__(self,s,pack):self.s,self.pack=s,pack;self.codec=SurfaceCodec.get(pack)
    def _render(self,semantic,ph_info):
        plan,trace=self.codec.realize(semantic);used=sorted(set(x for x in toks(plan) if x.startswith("@A")));unknown=[x for x in used if x not in ph_info];pointers=[];rendered=plan
        for p in used:
            if p in ph_info:
                ref,context=ph_info[p];lex=self.s.preferred(ref,self.pack.language,context);pointers.append({"placeholder":p,"semantic_ref":ref,"context":context,"surface":lex});rendered=rendered.replace(p,lex)
        grammar=[x.casefold() for x in toks(plan) if not x.startswith("@A")];badgrammar=[x for x in grammar if x not in self.pack.grammar]
        leaked=bool(re.search(r"\b(?:atom|existential|app|fact):[0-9a-fA-F]+",rendered)) or any(x["surface"]==x["semantic_ref"] for x in pointers)
        ok=trace.get("authorized_transform",False) and not unknown and not badgrammar and not leaked and bool(rendered.strip())
        proof={**trace,"verified":ok,"verification_mode":"semantic_pointer_provenance","roundtrip_used":False,"pointers":pointers,"unknown_pointers":unknown,"unknown_grammar":badgrammar,"internal_id_leak":leaked,"language_pack_hash":self.pack.hash}
        return surface(toks(rendered)) if ok else "",proof
    def fact(self,f):
        sem,mp=pointerize_fact(f);return self._render(sem,mp)
    def plan(self,plan):
        sem,mp=pointerize_plan(plan);return self._render(sem,mp)

class Runtime:
    def __init__(self,s,pack_path,top_k=24):
        self.s=s;self.pack=LanguagePack(pack_path);self.lang=self.pack.language;self.top_k=top_k;self.selfstate=SessionSelf(s);self.r=PointerRealizer(s,self.pack);self.planner=ResponsePlanner(s);self.runtime_attestation={"authority_generation":s.generation,"authority_generation_hash":s.authority_hash(s.generation),"language_pack_hash":self.pack.hash,"read_generation":s.generation};self._bind_authority()
    def _bind_authority(self):
        g=int(self.runtime_attestation["authority_generation"]);self.i=Interpreter(self.s,self.pack,g);self.rulelearner=RuleLearner(self.s,self.i);self.inf=Inference(self.s,authority_generation=g);self.ws=Workspace(self.s,self.selfstate,self.top_k)
    def reload_authority(self):
        g=self.s.generation;self.runtime_attestation["authority_generation"]=g;self.runtime_attestation["authority_generation_hash"]=self.s.authority_hash(g);self.runtime_attestation["read_generation"]=g;self._bind_authority();return dict(self.runtime_attestation)
    def _materialize(self,packet,news,g,seed):
        facts,_=self.inf.closure();mapping={}
        for x in news:
            tok,kind=x["token"],x["kind"];candidates=None
            for a in packet.get("apps",[]):
                roles=[r for r,v in a.get("args",{}).items() if isinstance(v,dict) and v.get("new")==tok]
                if len(roles)!=1:continue
                role=roles[0];known={}
                for r,v in a.get("args",{}).items():
                    if r==role:continue
                    if isinstance(v,dict) and "new" in v:
                        if v["new"] in mapping:known[r]=mapping[v["new"]]
                        continue
                    known[r]=v
                if not known:continue
                vals=set()
                for f in self.inf.match({"operator":a["operator"],"args":known},facts):
                    v=f.args.get(role);atom=self.s.atom(v) if isinstance(v,str) else None
                    if atom and atom["kind"]==kind:vals.add(v)
                if vals:candidates=vals if candidates is None else candidates&vals
            if candidates and len(candidates)>1:raise AmbiguousReferent(tok,[{"ref":r,"score":1.0} for r in sorted(candidates)])
            mapping[tok]=next(iter(candidates)) if candidates else stable("atom",kind,seed,tok)
        for x in news:
            ref=mapping[x["token"]]
            if not self.s.atom(ref):self.s.exact("atoms",["ref","kind","metadata","generation","authority_scope"],[ref,x["kind"],"{}",g,"world"],["ref"],{"generation"})
        p=json.loads(canonical(packet));cv=lambda v:mapping[v["new"]] if isinstance(v,dict) and "new" in v else v
        for a in p.get("apps",[]):a["args"]={k:cv(v) for k,v in a["args"].items()}
        if p.get("query"):p["query"]["args"]={k:cv(v) for k,v in p["query"]["args"].items()}
        return p,mapping
    def _outcome(self,key,cause):
        if key in {"frontier"}:self.selfstate.set(self.s.symbol("self.interpretation_state_dimension"),self.s.symbol("self.unresolved"),cause);self.selfstate.set(self.s.symbol("self.response_state_dimension"),self.s.symbol("self.confused"),cause)
        elif key in {"unknown","conflict"}:self.selfstate.set(self.s.symbol("self.epistemic_state_dimension"),self.s.symbol("self.insufficient" if key=="unknown" else "self.uncertain"),cause);self.selfstate.set(self.s.symbol("self.response_state_dimension"),self.s.symbol("self.ready"),cause)
        else:self.selfstate.set(self.s.symbol("self.interpretation_state_dimension"),self.s.symbol("self.resolved"),cause);self.selfstate.set(self.s.symbol("self.epistemic_state_dimension"),self.s.symbol("self.sufficient"),cause);self.selfstate.set(self.s.symbol("self.response_state_dimension"),self.s.symbol("self.ready"),cause)
        plan=self.planner.plan(key);return self.r.plan(plan),plan
    def process(self,text,learn=True,teach=False):
        self.runtime_attestation["read_generation"]=self.s.generation
        if teach:
            rr=self.rulelearner.teach(text)
            if rr.get("status")=="frontier":return self._frontier(text,rr.get("reason","rule_learning_frontier"),rr)
            (out,rp),plan=self._outcome("learned","rule_learning")
            return {**rr,"response":out,"response_plan":self._plan_json(plan),"realization_proof":rp,"self_state":dict(self.selfstate.state)}
        self.selfstate.set(self.s.symbol("self.response_state_dimension"),self.s.symbol("self.processing"),"new_observation")
        try:packet,news,uses,trace=self.i.parse(text)
        except AmbiguousReferent as e:return self._frontier(text,"ambiguous_referent",{"surface":e.surface,"candidates":e.candidates})
        except Exception as e:return self._frontier(text,"interpretation_error",{"error":str(e)})
        if not packet:return self._frontier(text,trace.get("reason","no_candidate"),trace)
        # Greeting is an ordinary event recognized through a pinned semantic ref.
        greet=self.s.symbol("event.greeting") if self.s.db.execute("SELECT 1 FROM control_symbols WHERE role='event.greeting'").fetchone() else None
        if greet and any(a["operator"]=="op:event" and a["args"].get("role:type")==greet for a in packet.get("apps",[])):
            (out,proof),plan=self._outcome("greeting","greeting_event");return {"status":"ok","response":out,"response_plan":self._plan_json(plan),"realization_proof":proof,"self_state":dict(self.selfstate.state)}
        if packet.get("query") or packet.get("describe"):
            facts,byref=self.inf.closure()
            if self.inf.incomplete:return self._frontier(text,"inference_incomplete",{"reason":self.inf.incomplete_reason})
            if packet.get("describe"):
                target=packet["describe"];des=self.s.symbol("operator.designation");xs=[f for f in facts if f.stance=="support" and self.s.user_visible_fact(f) and target in f.args.values()];workspace,wtrace=self.ws.build(facts,{"operator":"describe","args":{"target":target}},[f.ref for f in xs]);outs=[];proofs=[]
                for f in xs[:5]:
                    x,p=self.r.fact(f)
                    if x:outs.append(x);proofs.append(p)
                if outs:
                    self.selfstate.set(self.s.symbol("self.interpretation_state_dimension"),self.s.symbol("self.resolved"),"describe_resolved");self.selfstate.set(self.s.symbol("self.response_state_dimension"),self.s.symbol("self.ready"),"describe_resolved")
                    return {"status":"ok","response":" ".join(outs),"facts":[f.__dict__ for f in xs[:10]],"workspace":wtrace,"realization_proofs":proofs,"self_state":dict(self.selfstate.state)}
                (out,p),plan=self._outcome("unknown","describe_no_fact");return {"status":"unknown","response":out,"workspace":wtrace,"response_plan":self._plan_json(plan),"realization_proof":p,"self_state":dict(self.selfstate.state)}
            pos=self.inf.match(packet["query"],facts);neg=self.inf.match({**packet["query"],"stance":"deny"},facts);result="conflict" if pos and neg else "supported" if pos else "contradicted" if neg else "unknown";chosen=(pos or neg);proof_refs=[]
            if chosen:
                def collect(n):
                    proof_refs.append(n.ref)
                    if n.derived:
                        for r in n.proof["parents"]:
                            if r in byref:collect(byref[r])
                collect(chosen[0])
            workspace,wtrace=self.ws.build(facts,packet["query"],proof_refs);(out,rp),plan=self._outcome(result,f"query:{result}");exp=self.inf.explain(chosen[0],byref) if chosen else None
            return {"status":"ok","response":out,"result":result,"query":packet["query"],"proof":exp,"workspace":wtrace,"response_plan":self._plan_json(plan),"realization_proof":rp,"ephemeral_fact_count":sum(f.derived for f in facts),"self_state":dict(self.selfstate.state),"self_transitions":[t.__dict__ for t in self.selfstate.transitions[-6:]]}
        if not learn:return {"status":"interpreted","packet":packet,"trace":trace}
        try:
            with self.s.db:
                g=self.s.begin("learn:"+hashlib.sha256(text.encode()).hexdigest()[:12]);p,m=self._materialize(packet,news,g,f"generation:{g}");obs=self.s.add_observation(text,p,self.lang,"user",g,occurrence_ref=f"generation:{g}");refs=[]
                for a in p.get("apps",[]):self.s.insert_app(a["operator"],a["args"],g,obs,a.get("stance","support"),.95,"provisional");refs += [v for v in a["args"].values() if isinstance(v,str)]
                for surf_,ref in uses:self.s.record_use(surf_,self.lang,ref)
                self.s.touch(refs);self.s.rebuild_designations();self.s.finish(g)
            (out,rp),plan=self._outcome("learned","knowledge_committed");return {"status":"learned","response":out,"packet":p,"generation":g,"new_atoms":m,"trace":trace,"response_plan":self._plan_json(plan),"realization_proof":rp,"self_state":dict(self.selfstate.state)}
        except AmbiguousReferent as e:return self._frontier(text,"ambiguous_referent",{"surface":e.surface,"candidates":e.candidates})
        except Exception as e:return self._frontier(text,"learning_rejected",{"error":str(e),"packet":packet})
    def _plan_json(self,p):return {"goal":p["goal"],"value":p.get("value"),"facts":[{"operator":f.operator,"args":f.args} for f in p.get("facts",[])]}
    def _frontier(self,text,reason,details):
        ref=self.s.frontier(text,reason,details);(out,p),plan=self._outcome("frontier",reason);return {"status":"frontier","response":out,"frontier":{"ref":ref,"reason":reason,"details":details},"response_plan":self._plan_json(plan),"realization_proof":p,"self_state":dict(self.selfstate.state)}

def main():
    p=argparse.ArgumentParser();p.add_argument("command",choices=["init","chat","learn","teach","ask","inspect"]);p.add_argument("text",nargs="?");p.add_argument("--db",default="cemm_mvp.sqlite");p.add_argument("--data",action="append",default=[]);p.add_argument("--pack",required=True);a=p.parse_args();s=Store(a.db)
    for d in a.data:s.import_data(d)
    rt=Runtime(s,a.pack)
    if a.command=="init":print(canonical(rt.runtime_attestation))
    elif a.command in {"learn","teach","ask"}:print(json.dumps(rt.process(a.text or "",a.command!="ask",a.command=="teach"),ensure_ascii=False,indent=2))
    elif a.command=="chat":
        for line in sys.stdin:
            if line.strip():print(rt.process(line.strip())["response"])
    else:
        for t in ("atoms","operator_roles","applications","bindings","claims","rules","designation_index","label_stats","frontiers","generations"):print(t,s.db.execute(f"SELECT count(*) FROM {t}").fetchone()[0])
        print("snapshot",s.snapshot_hash())
if __name__=="__main__":main()
