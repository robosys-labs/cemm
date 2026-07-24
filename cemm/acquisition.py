#!/usr/bin/env python3
"""Reviewed and autonomous acquisition for CEMM v1.

The reviewed ``acquire`` function is not a phrase router.  A training/review
system supplies mention spans and semantic kinds for genuinely unknown forms.
The script creates opaque identities + designations, reloads the new authority
generation, then lets the ordinary open structured semantic codec infer/commit
meaning from the text.

The ``AutonomousAcquirer`` (weakness #11 fix) eliminates the manual anchor
requirement: when the interpreter encounters a surface token with no designation,
it infers the semantic kind from the predicted operator+role context (or defaults
to ``"concept"``), creates a provisional world-scope atom + designation, and
retries interpretation.  Acquired atoms are ``authority_scope='world'`` and
claims are ``authority_status='provisional'``, so the authority boundary is
preserved exactly.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from cemm.store import Store
from cemm.runtime import Runtime
from cemm.config import Config
from cemm.model import stable,lit


class AutonomousAcquirer:
    """Autonomously acquire unknown surface forms with inferred semantic kinds.

    When a surface token has no designation match, the interpreter calls this
    class to create a provisional world-scope atom + designation fact, then
    retries interpretation.  The kind is inferred from the predicted
    operator+role context via ``KIND_INFERENCE``, defaulting to ``"concept"``.
    """

    KIND_INFERENCE = {
        ("op:type", "role:class"): "concept",
        ("op:type", "role:instance"): "entity",
        ("op:relation", "role:subject"): "entity",
        ("op:relation", "role:object"): "entity",
        ("op:relation", "role:relation"): "relation_type",
        ("op:state", "role:subject"): "entity",
        ("op:state", "role:value"): "value",
        ("op:event", "role:actor"): "entity",
        ("op:event", "role:type"): "event_type",
        ("op:designation", "role:target"): "entity",
    }

    def __init__(self, store, config=None):
        self.store = store
        self.config = config or Config()

    def infer_kind(self, operator, role):
        """Return the inferred semantic kind for an (operator, role) pair."""
        return self.KIND_INFERENCE.get((operator, role), "concept")

    def acquire(self, surface, kind, language="en", generation=None):
        """Create a provisional world-scope atom + designation for an unknown surface.

        Returns the atom ref.  The atom is ``authority_scope='world'`` and the
        designation claim is ``authority_status='provisional'`` with
        ``source_ref='autonomous_acquisition'``, so neither enters the authority
        hash.
        """
        with self.store.db:
            g = generation if generation is not None else self.store.begin(
                f"autonomous_acquisition:{surface}"
            )
            ref = stable("atom", kind, "autonomous", surface)
            self.store.exact(
                "atoms",
                ["ref", "kind", "metadata", "generation", "authority_scope"],
                [ref, kind, "{}", g, "world"],
                ["ref"],
                {"generation"},
            )
            args = {
                "role:target": ref,
                "role:label_type": "label:lexical",
                "role:surface": lit(surface),
                "role:language": lit(language),
                "role:script": lit("Latn"),
                "role:prior": lit(1.0, "float"),
                "role:preferred": lit(True, "bool"),
            }
            obs = self.store.add_observation(
                surface, {"designation": ref}, language,
                "autonomous_acquisition", g,
                occurrence_ref=f"autonomous:{surface}",
            )
            self.store.insert_app(
                "op:designation", args, g, obs, "support", 1.0, "provisional",
            )
            self.store.rebuild_designations()
            self.store.finish(g)
        return ref

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
