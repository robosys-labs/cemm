#!/usr/bin/env python3
"""Bind fixed reviewed canonical v3.5.1 authority compilers into the signed supplement.

This tool never activates a release. It content-addresses the three fixed reviewed Phase-12
candidate authority sets. ObservationModel/calibration entries remain explicit review inputs and
are copied unchanged from the source supplement.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

from cemm.v350.csir.runtime_projection_v351 import (
    CANONICAL_AUTHORITY_SET_REFS,
    canonical_authority_set_fingerprints_v351,
)

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=Path("cemm/data/v350/semantic_authority_supplement_v351.json"))
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    output=a.output or a.source
    doc=json.loads(a.source.read_text(encoding="utf-8"))
    observed=canonical_authority_set_fingerprints_v351()
    doc["canonical_authority_sets"]=[
        {"set_ref":ref,"expected_fingerprint":observed[ref]}
        for ref in CANONICAL_AUTHORITY_SET_REFS
    ]
    metadata=dict(doc.get("metadata",{}))
    metadata["canonical_sets_status"]="content_addressed"
    metadata["canonical_set_refs"]=list(CANONICAL_AUTHORITY_SET_REFS)
    doc["metadata"]=metadata
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(output),"canonical_authority_sets":doc["canonical_authority_sets"]},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
