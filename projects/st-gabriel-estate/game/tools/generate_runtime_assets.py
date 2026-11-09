#!/usr/bin/env python3
"""Deterministically build prototype UI, effects and isometric connectivity tiles.

Requirements: Pillow, numpy, CairoSVG. No network or font-file bundling.
All animation frames retain the same canvas and pivot; source artwork is preserved.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
from pathlib import Path
import random
from typing import Any
import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/runtime'
SOURCES = ROOT / 'sources/runtime'
ASSETS.mkdir(parents=True, exist_ok=True)
SOURCES.mkdir(parents=True, exist_ok=True)
GOLD = (239, 194, 107)
CREAM = (255, 244, 206)
VIOLET = (130, 91, 180)
records: list[dict[str, Any]] = []
animations: list[dict[str, Any]] = []


def save(image: Image.Image, category: str, name: str, *, kind='sprite', pivot=None, **extra: Any) -> dict[str, Any]:
    path = ASSETS / category / f'{name}.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    image = image.convert('RGBA')
    image.save(path, optimize=True)
    a = np.asarray(image.getchannel('A'))
    rec = dict(id=f'runtime_{category.replace("/", "_")}_{name}', category=f'runtime/{category}',
               path=path.relative_to(ROOT).as_posix(), width=image.width, height=image.height,
               kind=kind, pivot=pivot or [image.width/2, image.height/2],
               transparency='straight-alpha' if np.any(a < 255) else 'opaque',
               sha256=hashlib.sha256(path.read_bytes()).hexdigest(), batch='02',
               production_status='prototype-runtime', **extra)
    records.append(rec)
    return rec


def svg_asset(body: str, category: str, name: str, width: int, height: int, **extra: Any) -> dict[str, Any]:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{body}</svg>'
    src = SOURCES / category / f'{name}.svg'
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(svg, encoding='utf-8')
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=width*2, output_height=height*2)
    image = Image.open(io.BytesIO(png)).convert('RGBA').resize((width,height), Image.Resampling.LANCZOS)
    return save(image, category, name, source_svg=src.relative_to(ROOT).as_posix(), **extra)


def make_icons() -> None:
    icons = {
      'light':'<circle cx="32" cy="32" r="11"/><path d="M32 7v7m0 36v7M7 32h7m36 0h7M14 14l5 5m26 26 5 5M14 50l5-5m26-26 5-5"/>',
      'faith':'<path d="M29 7h6v16h14v6H35v28h-6V29H15v-6h14z"/>',
      'grace':'<path d="M32 53S7 39 7 24C7 10 25 7 32 20 39 7 57 10 57 24 57 39 32 53 32 53z"/><path d="m27 30 5-7 5 7-5 8z"/>',
      'charity':'<path d="M7 44h10l8 8h15l17-17c-1-6-7-7-11-3l-9 9H27m-10 3V30h11l8 7c3 4 0 7-4 6l-8-4"/><path d="M33 24s-12-7-12-13c0-7 9-8 12-2 3-6 12-5 12 2 0 6-12 13-12 13z"/>',
      'age':'<rect x="9" y="13" width="46" height="43" rx="5"/><path d="M9 25h46M21 7v13M43 7v13M20 35h7m10 0h7M20 46h7m10 0h7"/>',
      'happiness':'<circle cx="32" cy="32" r="24"/><path d="M20 38q12 14 24 0M21 23h2m18 0h2"/>',
      'concern':'<circle cx="32" cy="32" r="24"/><path d="M20 46q12-14 24 0M20 24l6-3m12 0 6 3"/>',
      'halo':'<ellipse cx="32" cy="30" rx="25" ry="12"/><ellipse cx="32" cy="30" rx="18" ry="7"/>',
      'halo_fading':'<ellipse cx="32" cy="30" rx="25" ry="12" stroke-dasharray="12 7"/>',
      'halo_dark':'<ellipse cx="32" cy="30" rx="25" ry="12"/><path d="m15 40-3 9m20-5v11m17-15 3 9M17 14l-3-6m33 6 3-6"/>',
      'influence':'<circle cx="32" cy="13" r="6"/><circle cx="13" cy="45" r="6"/><circle cx="51" cy="45" r="6"/><path d="M29 19 16 39m19-20 13 20M20 45h24"/>',
      'vocation':'<circle cx="32" cy="32" r="23"/><circle cx="32" cy="32" r="13"/><path d="m32 32 18-18m-3-6h9v9"/>',
      'lifespan':'<path d="M17 7h30M17 57h30M20 8v10c0 9 24 20 24 28v10M44 8v10c0 9-24 20-24 28v10M24 15h16M24 50h16"/>',
      'temple':'<path d="M7 28 32 11l25 17M12 28v28h40V28M6 56h52M27 56V40h10v16M32 3v13m-5-8h10M19 31v6m26-6v6"/>',
      'priest':'<circle cx="32" cy="18" r="11"/><path d="M10 57V45c0-20 44-20 44 0v12M20 34l12 7 12-7M27 40h10v7H27z"/>',
      'health':'<path d="M24 8h16v16h16v16H40v16H24V40H8V24h16z"/>',
      'family':'<circle cx="18" cy="17" r="8"/><circle cx="46" cy="17" r="8"/><circle cx="32" cy="33" r="6"/><path d="M5 50V36c0-12 23-12 23-1m8 0c0-11 23-11 23 1v14M21 57v-9c0-11 22-11 22 0v9"/>',
      'home':'<path d="M5 29 32 7l27 22M13 27v29h38V27M27 56V39h10v17M20 31h3m18 0h3"/>',
      'welcome':'<path d="M13 56V9h35v47M22 56V18h17v38M28 36h2M6 47l8-6 8 6m20 0 8-6 8 6"/>',
      'food':'<path d="M12 26c-8 4-9 22 0 27h39c9-6 7-23 0-27-3-23-36-23-39 0zM21 21l-4 11m16-15-4 14m15-11-4 12"/>',
      'water':'<path d="M32 5S12 29 12 41a20 20 0 0 0 40 0C52 29 32 5 32 5zM22 41q0 11 10 11"/>',
      'rest':'<path d="M10 27v30m44-30v30M10 45h44M10 37h44v8M14 27h13v10H14zM27 30h19q8 0 8 7"/>',
      'work':'<rect x="7" y="22" width="50" height="33" rx="4"/><path d="M23 22v-9h18v9M7 33l25 8 25-8M28 37h8v8h-8z"/>',
      'education':'<path d="M32 13 4 25l28 12 28-12zM16 31v14q16 13 32 0V31M57 27v22"/>',
      'prayer':'<path d="M11 53l10-18 4-21c1-6 7-6 7 1v23L22 56M53 53 43 35l-4-21c-1-6-7-6-7 1v23l10 18M5 50l13 8m41-8-13 8"/>',
      'novena':'<circle cx="32" cy="32" r="16"/>'+''.join(f'<circle cx="{32+25*math.cos(t*2*math.pi/9):.3f}" cy="{32+25*math.sin(t*2*math.pi/9):.3f}" r="2"/>' for t in range(9)),
      'candle':'<path d="M24 57V29h16v28M20 57h24M32 8c-11 12-8 19 0 19s11-7 0-19zM32 28v5"/>',
      'celebration':'<path d="M5 9q27 15 54 0M12 12v12l9-8m8 2 4 12 7-13m7-2 6 9 3-12M13 43h38v12H13zM20 35v8m12-10v10m12-8v8"/>',
      'calendar':'<rect x="7" y="13" width="50" height="43" rx="5"/><path d="M7 25h50M20 7v12M44 7v12m-25 17 10 10 17-17"/>',
      'guardian':'<circle cx="32" cy="13" r="7"/><path d="M32 22v24M32 26 14 39m18-13 18 13M32 46l-12 11m12-11 12 11M8 28q-7 24 7 28M56 28q7 24-7 28"/>',
      'protection':'<path d="M32 7 10 17v17c0 15 22 24 22 24s22-9 22-24V17zM22 32l8 8 14-16"/>',
      'comfort':'<path d="M32 48S17 39 17 29c0-9 11-12 15-4 4-8 15-5 15 4 0 10-15 19-15 19zM8 30v14l12 13m36-27v14L44 57"/>',
      'danger':'<path d="M32 7 59 55H5zM32 24v14m0 8v1"/>',
      'car':'<path d="M7 46V32l7-5 6-14h24l6 14 7 5v14zM14 27h36M15 36h7m20 0h7M12 46v8m40-8v8M24 13l-3 14"/>',
      'crossing':'<circle cx="34" cy="10" r="5"/><path d="m30 20-9 11m9-11 11 5 10-5M30 20l-5 19 14 11v9M25 39 15 55M5 60h54"/>',
      'targeted_pressure':'<path d="M8 32C9 12 49 9 53 29c5 22-25 34-33 20-7-12 8-22 15-13 4 5-2 9-5 7M8 32l-3-9m3 9 10-3"/>',
      'pause':'<rect x="17" y="12" width="9" height="40" rx="1"/><rect x="38" y="12" width="9" height="40" rx="1"/>',
      'play':'<path d="M19 11v42l32-21z"/>',
      'fast_forward':'<path d="M8 14v36l23-18zM33 14v36l23-18z"/>',
      'close':'<path d="m16 16 32 32M48 16 16 48"/>',
      'settings':'<circle cx="32" cy="32" r="10"/><path d="m26 6 12 0 2 9 7 4 9-3 6 11-7 6v8l5 6-6 10-10-4-7 4-2 8H24l-2-8-7-4-9 3-6-11 7-6v-8l-5-6 6-10 10 4 7-4z" transform="translate(3 0) scale(.9)"/>',
      'information':'<circle cx="32" cy="32" r="25"/><path d="M32 28v18M29 28h3m-3 18h6M32 18v1"/>',
      'relationships':'<circle cx="19" cy="24" r="8"/><circle cx="45" cy="24" r="8"/><path d="M5 54V44c0-14 28-14 28 0v10m-2-10c0-14 28-14 28 0v10M20 9l12-5 12 5"/>',
      'history':'<path d="M11 25A23 23 0 1 1 10 42M11 25V10m0 15h15M32 16v17l10 7"/>',
    }
    for name,shape in icons.items():
        body=f'<g fill="none" stroke="#e9c078" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round">{shape}</g>'
        svg_asset(body,'ui/icons',name,64,64,kind='icon',pivot=[32,32])


def make_panels() -> None:
    specs = {
        'panel_dark': (512,384,'#29282f','#171a23','#b58b50'),
        'panel_parchment': (512,384,'#f7eedc','#e2d1b7','#a7804c'),
        'hud_tile': (320,112,'#33323a','#1b202a','#c8a265'),
        'tooltip': (320,128,'#292c34','#161a23','#8a7553'),
        'button_default': (256,64,'#434047','#262932','#ae8f5d'),
        'button_hover': (256,64,'#6b5235','#3d332b','#f2d391'),
        'button_pressed': (256,64,'#30291f','#51412d','#d1aa68'),
        'button_disabled': (256,64,'#34353b','#292c33','#666770'),
        'tab_default': (160,52,'#d6c8b4','#bcad97','#a08460'),
        'tab_selected': (160,52,'#fff5df','#ead9ba','#bf9559'),
        'notification_warning': (384,104,'#43362c','#25242b','#d9a55a'),
        'notification_care': (384,104,'#2c3e3b','#222c31','#89b1a0'),
    }
    for name,(w,h,c1,c2,line) in specs.items():
        body=f'''<defs><linearGradient id="g" x2="0" y2="1"><stop stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
        <rect x="2" y="2" width="{w-4}" height="{h-4}" rx="14" fill="url(#g)" stroke="{line}" stroke-width="2"/>
        <rect x="6" y="6" width="{w-12}" height="{h-12}" rx="10" fill="none" stroke="{line}" opacity=".35"/>
        <path d="M16 12h12M12 16v12M{w-28} 12h12M{w-12} 16v12M12 {h-28}v12M16 {h-12}h12M{w-28} {h-12}h12M{w-12} {h-28}v12" stroke="{line}" opacity=".8" fill="none"/>'''
        svg_asset(body,'ui/components',name,w,h,kind='nine-slice',nine_slice={'left':20,'top':20,'right':20,'bottom':20},note='Blank component; render accessible/localizable text separately.')
    for name,color in [('track','#353640'),('fill_light','#e7b95b'),('fill_care','#89b5a0'),('fill_risk','#bb8794')]:
        svg_asset(f'<rect x="1" y="1" width="254" height="14" rx="7" fill="{color}" stroke="#b69b6b" stroke-width="1"/>','ui/components',f'meter_{name}',256,16,kind='nine-slice',nine_slice={'left':8,'right':8,'top':0,'bottom':0})


def iso(body: str) -> str:
    return f'<defs><clipPath id="tile"><rect width="256" height="256"/></clipPath></defs><g transform="matrix(.5 .25 -.5 .25 128 0)" clip-path="url(#tile)">{body}</g>'


def make_tiles() -> None:
    colors={'grass':'#788265','grass_dry':'#8e8668','earth':'#947c63','concrete':'#b7afa3','asphalt':'#4b515c','water':'#4d7884','pavers':'#ad9c88','garden':'#6b795a'}
    for name,color in colors.items():
        body=f'<rect width="256" height="256" fill="{color}"/>'
        if name=='pavers':
            body+='<defs><pattern id="p" width="64" height="32" patternUnits="userSpaceOnUse"><path d="M0 0h64M0 32h64M0 0v32M32 0v16M0 16h64M64 0v32" stroke="#756c60" stroke-width="2" fill="none"/></pattern></defs><rect width="256" height="256" fill="url(#p)"/>'
        elif name=='water':
            body+=''.join(f'<path d="M0 {y}q16-5 32 0t32 0t32 0t32 0t32 0t32 0t32 0t32 0" stroke="#85a3a6" stroke-opacity=".38" stroke-width="2" fill="none"/>' for y in range(12,256,24))
        else:
            rng=random.Random(name)
            for _ in range(250):
                x,y=rng.randrange(5,251),rng.randrange(5,251)
                body+=f'<circle cx="{x}" cy="{y}" r="{rng.choice([1,1,2])}" fill="{"#ede4c8" if rng.random()>.5 else "#25312b"}" opacity=".10"/>'
        svg_asset(iso(body),'terrain',name,256,128,kind='tile',pivot=[128,64],footprint=[1,1],tile_size=[256,128])
    # World-grid directions, not compass headings on the screen.
    edge={1:(128,0),2:(256,128),4:(128,256),8:(0,128)}
    road_names={0:'isolated',1:'end_n',2:'end_e',3:'corner_ne',4:'end_s',5:'straight_ns',6:'corner_es',7:'tee_nes',8:'end_w',9:'corner_nw',10:'straight_ew',11:'tee_new',12:'corner_sw',13:'tee_nsw',14:'tee_esw',15:'cross'}
    def road_body(mask: int,variant='') -> str:
        paths=' '.join(f'M128 128L{x} {y}' for bit,(x,y) in edge.items() if mask&bit)
        b='<rect width="256" height="256" fill="#788265"/>'
        if mask==0:
            b+='<circle cx="128" cy="128" r="77" fill="#b8afa2"/><circle cx="128" cy="128" r="62" fill="#4b515c"/>'
        else:
            b+=f'<path d="{paths}" fill="none" stroke="#b8afa2" stroke-width="152" stroke-linecap="butt" stroke-linejoin="round"/>'
            b+=f'<path d="{paths}" fill="none" stroke="#4b515c" stroke-width="124" stroke-linecap="butt" stroke-linejoin="round"/>'
            b+='<circle cx="128" cy="128" r="62" fill="#4b515c"/>'
            for bit,(x,y) in edge.items():
                if mask&bit:
                    sx,sy=128+(x-128)*.65,128+(y-128)*.65
                    b+=f'<path d="M{sx} {sy}L{x} {y}" stroke="#ddcd93" stroke-width="3" stroke-dasharray="12 10" fill="none"/>'
        if variant=='crosswalk':
            b+=''.join(f'<rect x="{x}" y="103" width="10" height="50" fill="#e6dfca"/>' for x in range(74,186,17))
        elif variant=='speed_bump':
            b+='<rect x="66" y="108" width="124" height="40" rx="5" fill="#e1b45c"/>'
            b+=''.join(f'<path d="m{x} 108h15l-16 40h-15z" fill="#353942"/>' for x in range(80,192,32))
        elif variant=='stop_line':
            b+='<rect x="137" y="182" width="45" height="6" fill="#f1e8cd"/>'
        elif variant=='pothole':
            b+='<path d="m93 123 9-15 24-9 28 7 12 17-10 25-27 8-25-12z" fill="#252b32" stroke="#74716c" stroke-width="4"/>'
        return b
    for mask,name in road_names.items():
        svg_asset(iso(road_body(mask)),'roads',f'road_{mask:02d}_{name}',256,128,kind='tile',pivot=[128,64],footprint=[1,1],connection_mask=mask,tile_size=[256,128])
    for variant in ['crosswalk','speed_bump','stop_line','pothole']:
        svg_asset(iso(road_body(5,variant)),'roads',f'road_ns_{variant}',256,128,kind='tile',pivot=[128,64],footprint=[1,1],connection_mask=5,tile_size=[256,128])
    for name,color in [('selected','#efc576'),('assignment','#94b9b0'),('risk','#c88fa5')]:
        svg_asset(f'<path d="M128 5 247 64 128 123 9 64Z" fill="{color}" fill-opacity=".06" stroke="{color}" stroke-width="3" stroke-dasharray="18 7"/>','markers',f'tile_{name}',256,128,kind='overlay',pivot=[128,64])


def glow_image(size: tuple[int,int], draw_fn, color=GOLD, opacity=1., blur=8.) -> Image.Image:
    scale=2
    mask=Image.new('L',(size[0]*scale,size[1]*scale))
    d=ImageDraw.Draw(mask)
    draw_fn(d,scale)
    mask=mask.resize(size,Image.Resampling.LANCZOS)
    result=Image.new('RGBA',size)
    for radius,gain,c in [(blur*2,.22,color),(blur,.48,color),(0,.95,color)]:
        a=mask.filter(ImageFilter.GaussianBlur(radius)) if radius else mask
        a=a.point(lambda v: max(0,min(255,int(v*gain*opacity))))
        lay=Image.new('RGBA',size,c+(0,));lay.putalpha(a)
        result=Image.alpha_composite(result,lay)
    return result


def halo_frame(state: str,phase: float,w=256,h=128) -> Image.Image:
    temple=w>256
    factor=w/256
    cx,cy=w/2,h/2
    rx,ry=82*factor,24*factor
    color=VIOLET if state=='dark' else GOLD
    alpha={'faint':.42,'fading':.6,'bright':.86,'radiant':1.,'dark':.9,'dim':.25,'healthy':.7}.get(state,1.)
    alpha*=.84+.16*math.cos(phase*math.tau)
    def draw(d,s):
        box=tuple(v*s for v in (cx-rx,cy-ry,cx+rx,cy+ry))
        width=max(2,round(2.3*factor*s))
        if state=='fading':
            for start,end in [(0,66),(83,126),(152,218),(239,271),(292,334)]:
                d.arc(box,start+phase*12,end+phase*12,fill=230,width=width)
        else:
            d.ellipse(box,outline=245,width=width)
        if state in ('radiant','dark'):
            for i in range(12):
                a=math.tau*i/12+phase*.18
                x,y=cx+(rx+10*factor)*math.cos(a),cy+(ry+6*factor)*math.sin(a)
                le=(3+(1+math.sin(phase*math.tau+i))*2)*factor
                d.line((x*s,(y-le)*s,x*s,(y+le)*s),fill=180,width=max(1,round(factor*s)))
                d.line(((x-le)*s,y*s,(x+le)*s,y*s),fill=180,width=max(1,round(factor*s)))
        if temple:
            d.arc(tuple(v*s for v in (cx-rx*1.12,cy-ry*1.42,cx+rx*1.12,cy+ry*1.42)),185,355,fill=110,width=width)
    return glow_image((w,h),draw,color,alpha,blur=5*factor)


def animate(category: str,name: str,frames: list[Image.Image],*,fps=12,loop=True,pivot=None,note='',source=None) -> None:
    n=len(frames);w,h=frames[0].size
    cols=4;rows=math.ceil(n/cols)
    atlas=Image.new('RGBA',(cols*w,rows*h))
    paths=[]
    for i,img in enumerate(frames):
        rec=save(img,category+f'/{name}',f'{name}_{i:02d}',kind='animation-frame',pivot=pivot,frame=i,animation=name,note=note)
        paths.append(rec['path']);atlas.paste(img,((i%cols)*w,(i//cols)*h))
    ar=save(atlas,'atlases',name,kind='atlas',pivot=[0,0],note=note)
    anim={'name':name,'frame_count':n,'fps':fps,'loop':loop,'frame_width':w,'frame_height':h,'columns':cols,'rows':rows,'atlas':ar['path'],'frames':paths,'pivot':pivot or [w/2,h/2],'alpha_mode':'straight','note':note,'source':source}
    animations.append(anim)


def make_effects() -> None:
    for state in ['faint','fading','bright','radiant','dark']:
        save(halo_frame(state,0),'effects/halos',f'person_{state}',kind='overlay',pivot=[128,64])
        animate('effects/halos',f'person_{state}',[halo_frame(state,i/12) for i in range(12)],fps=10,pivot=[128,64],note='Head-anchor overlay; state is a fictional visual variable, not inferred from wealth or mood.')
    for state in ['dim','healthy','radiant']:
        save(halo_frame(state,0,768,384),'effects/temple',f'temple_{state}',kind='overlay',pivot=[384,192])
        animate('effects/temple',f'temple_{state}',[halo_frame(state,i/12,768,384) for i in range(12)],fps=8,pivot=[384,192],note='Separate building aura; place at temple anchor. No illumination baked into the underlying building.')
    # Precisely composable wingless energy-form companions, derived from approved art.
    for shape in ['ribbon','prayer']:
        src=ROOT/f'assets/characters/angels/angel_{shape}_wingless.png'
        base=Image.open(src).convert('RGBA')
        base.thumbnail((170,208),Image.Resampling.LANCZOS)
        for state in ['encouraging','concerned']:
            frames=[]
            for i in range(12):
                im=base.copy()
                if state=='concerned':
                    a=np.array(im)
                    lum=np.mean(a[:,:,:3].astype(float),axis=2)
                    for k,f in enumerate([.86,.9,1.]):a[:,:,k]=np.clip(lum*f,0,255).astype(np.uint8)
                    im=Image.fromarray(a)
                im.putalpha(im.getchannel('A').point(lambda v:round(v*(.87+.1*math.cos(i*math.tau/12)))))
                canvas=Image.new('RGBA',(224,256))
                canvas.alpha_composite(im,((224-im.width)//2,round(230-im.height+4*math.sin(i*math.tau/12))))
                frames.append(canvas)
            save(frames[0],'effects/companions',f'wingless_{shape}_{state}',kind='sprite',pivot=[112,230],note='Approved wingless energy form; concerned state uses cool tint, not a new facial pose.')
            animate('effects/companions',f'wingless_{shape}_{state}',frames,pivot=[112,230],note='Idle bob and luminance loop only; not a walk cycle or articulated character animation.',source=src.relative_to(ROOT).as_posix())
    for effect in ['protection','charity_link','targeted_whisper']:
        frames=[]
        for i in range(12):
            phase=i/12
            def draw(d,s,phase=phase):
                if effect=='protection':
                    d.arc((26*s,32*s,294*s,232*s),180,360,fill=230,width=3*s)
                    d.arc((40*s,42*s,280*s,222*s),180,360,fill=95,width=2*s)
                    for k in range(3):
                        t=(phase+k/3)%1;x=160+134*math.cos(math.pi+math.pi*t);y=132+100*math.sin(math.pi+math.pi*t)
                        d.ellipse(((x-3)*s,(y-3)*s,(x+3)*s,(y+3)*s),fill=250)
                else:
                    pts=[]
                    for k in range(101):
                        t=k/100
                        x=24+272*t;y=94+18*math.sin(t*math.tau+phase*math.tau)
                        pts.append((round(x*s),round(y*s)))
                    d.line(pts,fill=170,width=2*s)
                    for q in range(3):
                        t=(phase+q/3)%1;x=24+272*t;y=94+18*math.sin(t*math.tau+phase*math.tau)
                        d.ellipse(((x-2)*s,(y-2)*s,(x+2)*s,(y+2)*s),fill=255)
            c=(110,191,181) if effect=='targeted_whisper' else GOLD
            frames.append(glow_image((320,192),draw,c,blur=5))
        save(frames[0],'effects/interventions',effect,kind='overlay',pivot=[160,132])
        animate('effects/interventions',effect,frames,pivot=[160,132],note='Overlay only; protection is a readable assignment effect, not a guaranteed gameplay outcome.')


def main() -> None:
    make_icons();make_panels();make_tiles();make_effects()
    manifest={'format_version':2,'name':'St. Gabriel Estate — Runtime Extensions','batch':'02','assets':records,'asset_count':len(records),'animations':animations,'conventions':{'alpha':'straight','tile_size':[256,128],'axis_mask':{'N':1,'E':2,'S':4,'W':8},'source':'Generated procedurally; approved wingless spirit art reused only where named.','font_files':'none'}}
    out=ROOT/'data/runtime_manifest.json';out.write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'data/animations.json').write_text(json.dumps({'animations':animations},indent=2)+'\n')
    print(f'Created {len(records)} PNG assets, {len(animations)} animations and {len(list(SOURCES.rglob("*.svg")))} SVG sources.')

if __name__=='__main__':main()
