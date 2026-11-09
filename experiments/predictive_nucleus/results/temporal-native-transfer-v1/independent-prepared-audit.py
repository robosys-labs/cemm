from pathlib import Path
from collections import Counter,defaultdict
from hashlib import sha256
from itertools import product
import json,lzma,math,random,re,subprocess,time
root=Path('/workspace/scratch/83f6093549cc/cemm/experiments/predictive_nucleus');folder=root/'data/temporal-native-transfer-v1';start=time.perf_counter();checks=Counter();failures=[]
def check(name,ok,detail=None):
 checks[name]+=1
 if not ok:failures.append({'check':name,'detail':detail})
def enc(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def digest(v):return sha256(enc(v)).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(lzma.decompress(b) if p.suffix=='.xz' else b)
def h(p):return sha256(p.read_bytes()).hexdigest()
def clean(q):return {k:v for k,v in q.items() if k not in ('entities','evidence_id')}
m=read(folder/'manifest.json');execution=read(folder/'execution.json');check('manifest_execution_binding',h(folder/'manifest.json')==execution['manifest_sha256'])
check('source_protocol_binding',m['source_commit']=='cd8f2f6b650b315a71797338b9d43374b71d1631' and m['protocol_commit']=='0bdb45172f85b755c7916907cefbcd30f21766ed')
for name,x in m['artifacts'].items():check('artifact_hash_size',h(folder/name)==x['sha256'] and (folder/name).stat().st_size==x['bytes'],name)
for name,expected in m['source_sha256'].items():
 published=subprocess.check_output(['git','show',m['source_commit']+':experiments/predictive_nucleus/'+name],cwd=root.parents[1]);check('published_source_hash',h(root/name)==expected==sha256(published).hexdigest(),name)
pub=read(folder/'public.json.xz');answers=read(folder/'test-answers.json.xz');private=read(folder/'oracle.json.xz')['rows'];oracle={r['id']:r for r in private}
check('inventory',len(pub['train'])==2048 and len(pub['test'])==len(answers)==len(private)==len(oracle)==12288 and {r['id'] for r in pub['test']}==set(oracle)==set(answers))
check('training_history_digest',digest(pub['train'])==m['history_digest'])
train_ids=[];test_ids=[]
for number,(law,mode,old,original,scope,target) in enumerate(product(('nand','nor'),range(2),range(4),range(8),('local','sibling'),range(8))):
 split='train' if ((original>>1)+(target>>1))%4 in (0,1) else 'test';ticket=digest([m['version'],split,number])[:24];(train_ids if split=='train' else test_ids).extend(ticket+'/case/'+str(i) for i in range(12))
check('frozen_sampler',random.Random(20261108101).sample(train_ids,2048)==[r['id'] for r in pub['train']]);check('test_order',[r['id'] for r in pub['test']]==test_ids)
seen=set();entities={'train':set(),'test':set()};contexts={};groups={k:defaultdict(list) for k in ('base','first','second','both')};used_keys=set()
for split in ('train','test'):
 for r in pub[split]:
  ident=r['id'];ticket,case=ident.split('/case/');check('case_id',ident not in seen and bool(re.fullmatch('[a-f0-9]{24}',ticket)) and int(case) in range(12),ident);seen.add(ident)
  base=r['base'];f=r['first']['query'];s=r['second'];t=r['target'];p=r['protected'];a=2*base[-1]['query']['before'][0]+base[-1]['query']['before'][1];b=2*t['before'][0]+t['before'][1]
  check('public_schema_no_hidden_labels',set(r)==({'id','law','base','first','second','target','protected','answers'} if split=='train' else {'id','law','base','first','second','target','protected'}) and all(set(x)=={'query','endpoint','source'} for x in base) and set(r['first'])=={'query','endpoint'},ident)
  check('modulo_split',((a+b)%4 in (0,1))==(split=='train'),ident)
  check('target_active_input_exclusion',f['before'][:2]!=t['before'][:2] and s['before'][:2]!=t['before'][:2],ident)
  check('public_probe_schedule',f['before']==[((b+1)%4)>>1,((b+1)%4)&1,0] and s['before']==[((b+2)%4)>>1,((b+2)%4)&1,1] and f['scope']==('local' if a%2==0 else 'sibling') and s['scope']==('sibling' if a%2==0 else 'local'),ident)
  check('source_scope_time_word',len(base)==9 and [x['source'] for x in base]==['physical']*8+['claim'] and all(x['query']['scope']=='parent' and x['query']['time']==-1 and x['query']['word']==i//4 for i,x in enumerate(base[:8])) and base[-1]['query']['scope']=='local' and base[-1]['query']['time']==0 and base[-1]['query']['word']==0 and f['time']==s['time']==1 and f['word']==s['word']==t['word']==0 and p['word']==1 and p['before']==t['before'] and p['scope']==t['scope'] and p['time']==t['time']==2,ident)
  qs=[x['query'] for x in base]+[f,s,t,p]
  for stage,q in enumerate(qs):
   check('descriptor_schema',set(q)=={'native_key','before','word','scope','time','evidence_id','entities','layout'},ident)
   check('receipt_and_participant_ids',q['evidence_id']==ticket+'/'+str(stage) and q['entities']==['E'+digest([q['evidence_id'],slot])[:18] for slot in range(3)] and len(set(q['entities']))==3,ident)
   check('layout_split',q['layout']==(('svo','osv')[stage%2] if split=='train' else 'vos'),ident)
   law,mode,layout,state,word=q['native_key'].split('/');state=int(state);check('query_native_key_binding',law==r['law'] and mode in ('0','1') and layout==q['layout'] and int(word)==q['word'] and q['before']==[(state>>2)&1,(state>>1)&1,state&1],ident)
   used_keys.add(q['native_key']);entities[split].update(q['entities'])
  check('unique_receipt_order',len({q['evidence_id'] for q in qs})==13,ident)
  common=(base[:8],base[-1]['query'],f,s,t,p);key=(split,ticket)
  if key in contexts:check('hidden_alternative_menu_equality',contexts[key][0]==common,ident);contexts[key][1].add(int(case))
  else:contexts[key]=[common,{int(case)}]
  if split=='train':
   check('train_answers',set(r['answers'])=={'second_y','target_y','protected_y'} and all(type(v)is int and v in range(8) for v in r['answers'].values()) and r['answers']['protected_y']==((base[4+b]['endpoint']&6)|t['before'][2]),ident)
  else:
   o=oracle[ident];check('private_answer_binding',answers[ident]==o['second_y'] and r['first']['endpoint']==o['first_y'] and o['law']==r['law'] and o['target_scope']==t['scope'] and o['target_state']==4*t['before'][0]+2*t['before'][1]+t['before'][2] and o['protected_y']==((base[4+b]['endpoint']&6)|t['before'][2]),ident)
   prefix=digest({'law':r['law'],'base':[{'query':clean(x['query']),'endpoint':x['endpoint'],'source':x['source']} for x in base],'first':clean(f),'second':clean(s),'target':clean(t),'protected':clean(p)})
   for view,extra in (('base',()),('first',(r['first']['endpoint'],)),('second',(answers[ident],)),('both',(r['first']['endpoint'],answers[ident]))):
    groups[view][(prefix,*extra)].append(ident);q=o['distributions'][view];check('actual_target_in_oracle_support',len(q)==8 and all(math.isfinite(v) and v>=0 for v in q) and abs(sum(q)-1)<1e-12 and q[o['target_y']]>0,{'id':ident,'view':view})
check('split_participant_separation',not entities['train'].intersection(entities['test']))
for (split,ticket),(common,cases) in contexts.items():
 if split=='test':check('twelve_hidden_worlds_per_context',cases==set(range(12)),ticket)
for view,partitions in groups.items():
 for ids in partitions.values():
  counts=Counter(oracle[ident]['target_y'] for ident in ids);q=[counts[y]/len(ids) for y in range(8)]
  for ident in ids:check('independent_conditional_distribution',q==oracle[ident]['distributions'][view],{'id':ident,'view':view})
training_path=root/'data/effect-role-fit-v3/training.json';training=read(training_path);freeze_path=root/'data/effect-role-v3/freeze.json';freeze=read(freeze_path);rename=0;native_rows=0
for seed in (7,11,23,37,53):
 native=read(folder/f'native-{seed}.json.xz');expected_keys={f'{law}/{mode}/{layout}/{state}/{word}' for law,mode,layout,state,word in product(('nand','nor'),range(2),('svo','osv','vos'),range(8),range(2))};check('native_inventory',set(native)==expected_keys and used_keys<=set(native),seed)
 lang=training['checkpoints'][f'grounded/{seed}'];langpath=root/'data/effect-role-fit-v3'/lang['file'];saved=read(langpath);check('inherited_language_file_hash',h(langpath)==lang['sha256'],seed)
 cells={x['metadata']['law']:x for x in m['native'][str(seed)]}
 for law,cell in cells.items():
  meta=cell['metadata'];c=cell['checks'];old=freeze['world_checkpoints'][f'{law}/{seed}'];worldpath=root/'data/set-acquisition-fit-v2'/old['file'];world=read(worldpath)
  check('native_inherited_weight_bindings',meta['checkpoint_sha256']==lang['sha256'] and meta['language_sha256']==saved['state_sha256']==training['reports'][f'grounded/{seed}']['final_sha256'] and meta['world_sha256']==world['state_sha256']==old['state_sha256'] and h(worldpath)==old['sha256'] and meta['freeze_sha256']==h(freeze_path) and meta['training_sha256']==h(training_path),{'seed':seed,'law':law})
  check('native_preparation_attestations',c['participant_rename_exact']==c['records']==c['endpoint_complement_checks']==c['uniform_hypothesis_checks']==96 and c['projection_checks']==384 and c['language_unchanged'] is True and c['world_unchanged'] is True and c['maximum_projection_error']<=1e-12 and c['maximum_uniform_error']<=1e-12,{'seed':seed,'law':law});rename+=c['participant_rename_exact']
 for key,row in native.items():
  law,mode,layout,state,word=key.split('/');meta=cells[law]['metadata'];frame=row['frame'];native_rows+=1
  check('native_frame_binding',frame['language_sha256']==meta['language_sha256'] and frame['world_sha256']==meta['world_sha256'] and frame['registry_sha256']==meta['registry_sha256'] and frame['lexical_id']==meta['new_ids'][int(word)] and frame['version']=='coordinate-transport-v1' and frame['view']=='intact' and frame['transforms']==[[1,1],[1,-1],[-1,1],[-1,-1]],{'seed':seed,'key':key})
  check('native_distributions',len(row['likelihood'])==4 and all(len(q)==8 and all(math.isfinite(v) and v>=0 for v in q) and abs(sum(q)-1)<1e-12 for q in row['likelihood']),{'seed':seed,'key':key})
  p=row['observed_prefix'];check('observed_mode_calibration',set(p)=={'id','entities','anchor','context','text'} and p['anchor']==[0,0,0] and len(p['context'])==4 and p['context'][0]['action']==[0,0,1,-1] and p['context'][0]['reading']==([0,1,0] if mode=='0' else [1,0,0]) and p['context'][-1]['reading']==[(int(state)>>2)&1,(int(state)>>1)&1,int(state)&1],{'seed':seed,'key':key})
check('960_renaming_attestations',rename==960)
report={'status':'PASS' if not failures else 'FAIL','scope':'Read-only pre-fit prepared-data custody/leakage and conditional-target audit. No model fitting, forecasting/scoring, native inference replay, original generator or original oracle code executed.','source_commit':m['source_commit'],'manifest_sha256':h(folder/'manifest.json'),'train_cases':2048,'test_cases':12288,'native_projection_rows':native_rows,'participant_renaming_checks_attested':rename,'renaming_scope':'All 960 recorded checks verified against committed preparation source, frozen native frames and exact published old-weight file hashes; renamed projections were not retained, so no independent replay is claimed.','independent_conditional_rows':checks['independent_conditional_distribution'],'independent_public_groups':{k:len(v) for k,v in groups.items()},'public_contexts':dict(Counter(k[0] for k in contexts)),'checks':dict(checks),'check_total':sum(checks.values()),'failure_count':len(failures),'failures':failures[:100],'audit_execution_note':'An earlier read-only audit invocation stopped during optional tensor-byte reconstruction because archived world tensor records are structured dictionaries. No data/source was altered. This completed audit uses published file-hash/path/state-receipt bindings, as requested; all boundary and conditional checks were repeated to produce a complete receipt.','wall_seconds':time.perf_counter()-start}
out=Path('/workspace/scratch/83f6093549cc/prepared-audit.json');out.write_bytes(enc(report));print(json.dumps({k:v for k,v in report.items() if k not in ('checks','audit_execution_note','renaming_scope','scope')},sort_keys=True))
