#!/usr/bin/env python3
"""Verify structure and require an external signature verifier plugin."""
from __future__ import annotations
import argparse, importlib, json
from pathlib import Path
from cemm_authoritative_hybrid.r4_review import CorpusReviewManifest, ReviewManifestVerifier

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('--verifier',required=True,help='module:function external verifier');a=p.parse_args();module,name=a.verifier.split(':',1);verify=getattr(importlib.import_module(module),name);manifest=CorpusReviewManifest.from_dict(json.loads(a.manifest.read_text(encoding='utf-8')));ReviewManifestVerifier(verify).verify(manifest);print(manifest.manifest_ref);return 0
if __name__=='__main__':raise SystemExit(main())
