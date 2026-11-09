#!/usr/bin/env python3
"""Merge source and runtime registries; build an offline, text-searchable catalog."""
from pathlib import Path
import hashlib, json
ROOT=Path(__file__).resolve().parents[1]
a=json.loads((ROOT/'data/manifest_v1.json').read_text())
b=json.loads((ROOT/'data/runtime_manifest.json').read_text())
for item in a['assets']:
    item['batch']='01'
    item['kind']='reference' if '/references/' in item['path'] or '/ui/panels/' in item['path'] else 'concept-extract'
    item['production_status']='concept-prototype'
manifest={'format_version':2,'name':'St. Gabriel Estate — Asset Library','asset_count':len(a['assets'])+len(b['assets']),'assets':a['assets']+b['assets'],'animations':b['animations'],'conventions':b['conventions']}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(ROOT/'data/assets.js').write_text('window.ASSET_LIBRARY = '+json.dumps(manifest)+';\n')
(ROOT/'SHA256SUMS.txt').write_text(''.join(f"{v['sha256']}  {v['path']}\n" for v in manifest['assets']))
print('Catalog registry:',manifest['asset_count'],'PNG files')
