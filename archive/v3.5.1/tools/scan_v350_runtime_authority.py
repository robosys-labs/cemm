#!/usr/bin/env python3
"""Static authority scanner for Phase20: imports, public entrypoints, and debt."""
from __future__ import annotations
import argparse,ast,json,re,sys
from pathlib import Path
FORBIDDEN=('cemm.v347','cemm.v350.migration')
# Narrow signals only; language modules and offline migration are explicitly excluded.
SUSPICIOUS=(re.compile(r'\btry_v350_else_legacy\b'),re.compile(r'\blegacy_if_(?:low_confidence|language_unknown|timeout|schema_missing)\b'),re.compile(r'\bFALLBACK_LEGACY\b'),re.compile(r'\bUSE_OLD_NLG\b'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('repo',nargs='?',default='.');ap.add_argument('--preactivate',action='store_true');a=ap.parse_args();root=Path(a.repo).resolve();issues=[]
 for p in (root/'cemm').rglob('*.py'):
  rel=p.relative_to(root).as_posix()
  if rel.startswith('cemm/v347/') or rel.startswith('cemm/v350/migration/') or (a.preactivate and rel in {'cemm/__init__.py','cemm/app/runtime.py','cemm/__main__.py'}):continue
  text=p.read_text(encoding='utf-8',errors='ignore')
  try:tree=ast.parse(text)
  except SyntaxError as e:issues.append({'path':rel,'kind':'syntax','detail':str(e)});continue
  for n in ast.walk(tree):
   names=[]
   if isinstance(n,ast.Import):names=[a.name for a in n.names]
   elif isinstance(n,ast.ImportFrom) and n.module:names=[n.module]
   for name in names:
    if any(name==x or name.startswith(x+'.') for x in FORBIDDEN) or name=='v347' or name.startswith('v347.') or name=='v350.migration' or name.startswith('v350.migration.') or (rel.startswith('cemm/v350/') and (name=='migration' or name.startswith('migration.'))):issues.append({'path':rel,'kind':'forbidden_import','detail':name})
  for pat in SUSPICIOUS:
   if pat.search(text):issues.append({'path':rel,'kind':'semantic_fallback_signal','detail':pat.pattern})
 print(json.dumps({'ok':not issues,'issues':issues},indent=2));raise SystemExit(0 if not issues else 2)
if __name__=='__main__':main()
