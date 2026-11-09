from pathlib import Path
from playwright.sync_api import sync_playwright
import base64,json,re,shutil
root=Path(__file__).resolve().parents[1];out=root/'artifacts/browser-check';out.mkdir(parents=True,exist_ok=True)
manifest=json.loads((root/'manifest.json').read_text())
# In-memory test transport: this Chromium runtime blocks file:// and localhost navigation.
# Supply our own local asset bytes, without changing browser policy or fetching a URL.
images={a['path']:'data:image/png;base64,'+base64.b64encode((root/a['path']).read_bytes()).decode() for a in manifest['assets'] if a['kind']!='animation-frame'}
registry=(root/'data/assets.js').read_text();fixtures=(root/'data/residents.js').read_text()
script=(root/'demo/app.js').read_text().replace('im.src=R+path','im.src=window.IMAGE_BYTES[path]')
script=script.replace(';for(const btn of document.querySelectorAll',";document.querySelectorAll('#panel img').forEach(im=>im.src=window.IMAGE_BYTES[im.getAttribute('src').replace('../','')]);for(const btn of document.querySelectorAll")
html=(root/'demo/index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(root/'demo/style.css').read_text()+'</style>')
html=re.sub(r'<script src="[^"]+"></script>','',html)
html=html.replace('</body>',f'<script>window.IMAGE_BYTES={json.dumps(images)};{registry}{fixtures}{script}</script></body>')
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1600,'height':1050},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html,wait_until='load');page.wait_for_timeout(1800)
 page.screenshot(path=str(out/'demo.png'),full_page=True)
 bad=page.evaluate('[...document.images].filter(x=>!x.complete||!x.naturalWidth).map(x=>x.getAttribute("src").slice(0,60))')
 assert not bad,bad
 page.get_by_role('button',name='Emeka',exact=True).click();assert '31%' in page.locator('#panel').inner_text()
 page.get_by_role('button',name='Victor',exact=True).click();assert 'Dark' in page.locator('#panel').inner_text()
 page.get_by_role('button',name='Spiritual view: on',exact=True).click();assert page.get_by_role('button',name='Spiritual view: off',exact=True).is_visible()
 page.get_by_role('button',name='Pause effects',exact=True).click();assert page.get_by_role('button',name='Play effects',exact=True).is_visible()
 catalog=(root/'index.html').read_text().replace('<script src="data/assets.js"></script>','<script>window.IMAGE_BYTES='+json.dumps(images)+';'+registry+'</script>')
 catalog=catalog.replace('img.src=a.path','img.src=window.IMAGE_BYTES[a.path]||a.path')
 page.set_content(catalog,wait_until='load');page.wait_for_timeout(300)
 page.select_option('#batch','02');page.screenshot(path=str(out/'catalog.png'),full_page=False)
 assert page.locator('#count').inner_text()=='121 / 438 PNGs',page.locator('#count').inner_text()
 page.fill('#search','temple_radiant');assert page.locator('#count').inner_text()=='2 / 438 PNGs'
 assert not errors,errors
 result={'passed':True,'transport':'in-memory local assets; direct file and localhost navigation unavailable in this runtime','checks':['demo first render','all DOM images loaded','resident selection','spiritual overlay toggle','animation pause toggle','catalog batch filtering','catalog search'],'errors':errors}
 (root/'data/browser_validation.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
 b.close()
