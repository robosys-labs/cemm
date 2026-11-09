#!/usr/bin/env python3
"""Validate inventory, hashes, alpha, frame geometry, pivots, SVGs and original ZIP."""
from pathlib import Path
import collections,hashlib,json,sys,zipfile,xml.etree.ElementTree as ET
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1]

def main():
 m=json.loads((ROOT/'manifest.json').read_text());items=m['assets'];errors=[]
 def check(condition,message):
  if not condition:errors.append(message)
 check(m['asset_count']==len(items),'Manifest count mismatch')
 check(len({a['id'] for a in items})==len(items),'Duplicate IDs')
 check(len({a['path'] for a in items})==len(items),'Duplicate paths')
 for a in items:
  p=ROOT/a['path'];check(p.is_file(),f'Missing {p}')
  if not p.is_file():continue
  check(hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],f'Hash mismatch {p}')
  with Image.open(p) as im:
   check(im.size==(a['width'],a['height']),f'Dimension mismatch {p}')
   if a.get('batch')=='02':
    check(im.mode=='RGBA',f'Not RGBA {p}')
    check(im.getchannel('A').getextrema()[1]>0,f'Empty alpha {p}')
    x,y=a['pivot'];check(0<=x<=im.width and 0<=y<=im.height,f'Pivot outside canvas {p}')
  if a.get('source_svg'):
   psvg=ROOT/a['source_svg'];check(psvg.is_file(),f'Missing SVG {psvg}')
   if psvg.exists():ET.parse(psvg)
 for anim in m['animations']:
  w,h=anim['frame_width'],anim['frame_height'];cols=anim['columns']
  check(len(anim['frames'])==anim['frame_count'],f'Frame count {anim["name"]}')
  with Image.open(ROOT/anim['atlas']).convert('RGBA') as atlas:
   check(atlas.size==(cols*w,anim['rows']*h),f'Atlas size {anim["name"]}')
   for i,path in enumerate(anim['frames']):
    frame=Image.open(ROOT/path).convert('RGBA')
    check(frame.size==(w,h),f'Frame size {path}')
    part=atlas.crop(((i%cols)*w,(i//cols)*h,(i%cols+1)*w,(i//cols+1)*h))
    check(ImageChops.difference(frame,part).getbbox(alpha_only=False) is None,f'Atlas pixels {path}')
 roads=[a for a in items if a.get('category')=='runtime/roads' and a['path'].split('/')[-1][5:7].isdigit()]
 check({a.get('connection_mask') for a in roads}==set(range(16)),'Missing road connectivity masks')
 # Preserve the original extracted assets byte-for-byte, including the user's ZIP.
 with zipfile.ZipFile(ROOT/'releases/St_Gabriel_Estate_Individual_Assets.zip') as z:
  check(z.testzip() is None,'Original ZIP CRC failed')
  for a in json.loads((ROOT/'data/manifest_v1.json').read_text())['assets']:
   original=z.read('St_Gabriel_Estate_Individual_Assets/'+a['path'])
   check(hashlib.sha256(original).hexdigest()==hashlib.sha256((ROOT/a['path']).read_bytes()).hexdigest(),f'Original modified {a["path"]}')
 result={'passed':not errors,'asset_count':len(items),'animation_count':len(m['animations']),'runtime_png_count':sum(a.get('batch')=='02' for a in items),'svg_sources':sum('source_svg' in a for a in items),'counts_by_kind':dict(collections.Counter(a.get('kind','unknown') for a in items)),'errors':errors}
 (ROOT/'data/validation_report.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return bool(errors)
if __name__=='__main__':sys.exit(main())
