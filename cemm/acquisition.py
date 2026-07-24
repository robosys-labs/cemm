#!/usr/bin/env python3
"""Reviewed incremental acquisition for CEMM v1.

This is not a phrase router.  A training/review system supplies mention spans and
semantic kinds for genuinely unknown forms.  The script creates opaque identities +
designations, reloads the new authority generation, then lets the ordinary open
structured semantic codec infer/commit meaning from the text.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from cemm.store import Store
from cemm.runtime import Runtime
from cemm.model import stable,lit

def acquire(store:Store,runtime:Runtime,doc:dict):
    lang=doc.get("language",runtime.lang);created={}
    with store.db:
        g=store.begin("reviewed_acquisition:"+doc.get("document_ref","document"))
        for i,m in enumerate(doc.get("mentions",[])):
            ref=m.get("ref") or store.resolve_label(m["surface"],lang,m.get("kind"))
            if not ref:
                ref=stable("atom",m.get("kind","concept"),doc.get("document_ref","document"),i)
                store.exact("atoms",["ref","kind","metadata","generation"],[ref,m.get("kind","concept"),"{}",g],["ref"],{"generation"})
            created[m["surface"]]=ref
            args={"role:target":ref,"role:label_type":m.get("label_type","label:lexical"),"role:surface":lit(m["surface"]),"role:language":lit(lang),"role:script":lit(m.get("script","Latn")),"role:prior":lit(float(m.get("prior",1.2)),"float"),"role:preferred":lit(bool(m.get("preferred",True)),"bool")}
            obs=store.add_observation(m["surface"],{"designation":ref},lang,"reviewed_acquisition",g,occurrence_ref=f"designation:{i}");store.insert_app("op:designation",args,g,obs,"support",1.0,"reviewed")
        store.rebuild_designations();store.finish(g)
    runtime.reload_authority()
    result=runtime.process(doc["text"],learn=not doc.get("teach_rule",False),teach=bool(doc.get("teach_rule",False)))
    return {"created_or_resolved":created,"result":result}

def main():
    p=argparse.ArgumentParser();p.add_argument("document");p.add_argument("--db",default="cemm_v4.sqlite");p.add_argument("--base",action="append",default=[]);p.add_argument("--pack",required=True);a=p.parse_args();s=Store(a.db)
    for x in a.base:s.import_data(x)
    rt=Runtime(s,a.pack);d=json.loads(Path(a.document).read_text(encoding="utf-8"));print(json.dumps(acquire(s,rt,d),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
