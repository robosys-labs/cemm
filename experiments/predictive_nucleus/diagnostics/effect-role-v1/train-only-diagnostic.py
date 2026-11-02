"""Post-publication TRAIN-only diagnosis. No updates and no challenge/evaluator reads."""
import hashlib,json,lzma,math,pathlib,sys
REPO=pathlib.Path('/workspace/scratch/2d722e4a2602/cemm-g3')
sys.path.insert(0,str(REPO))
import torch
from experiments.predictive_nucleus import effect_role_model as m
from experiments.predictive_nucleus import effect_role_run as run
from experiments.predictive_nucleus.binding_model import factor_inputs
from experiments.predictive_nucleus.joint_objective import fingerprint
from experiments.predictive_nucleus.active_checkpoint import load_checkpoint

torch.set_num_threads(1)
ROOT=REPO/'experiments/predictive_nucleus'
DATA=ROOT/'data/effect-role-v1'
FITTED=ROOT/'data/effect-role-fit-v1'
reads={}
def read(path):
    raw=path.read_bytes(); reads[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(lzma.decompress(raw) if path.suffix=='.xz' else raw)
observed={k:read(DATA/f'{k}-inputs.json.xz') for k in ('teach','rehearsal')}
registry=read(DATA/'lexical-registry.json')
freeze=read(DATA/'freeze.json')
saved=read(FITTED/'training.json')
parents=read(run.LANGUAGE)['checkpoints']

class ScoringView:
    def __init__(self,net,neutral): self.net,self.neutral=net,neutral
    def __call__(self,features):
        lexical,layout=factor_inputs(features)
        content=self.net.lexical[2](self.net.lexical[1](self.net.lexical[0](lexical)))
        binding=self.net.layout[0](1.-layout)
        logits=self.net.order(content,binding)
        if self.neutral:
            logits=torch.cat((logits[:,:2].log_softmax(-1)+math.log(2.),logits[:,2:]),-1)
        return logits.log_softmax(-1)

def tensor_stats(values):
    return {'min':float(values.min()),'mean':float(values.mean()),'max':float(values.max())}

def diagnostic(net,world,tapes,neutral):
    before=fingerprint(net.state_dict()); native_before=fingerprint(world.state_dict())
    wrapper=ScoringView(net,neutral)
    assert len(tapes['teach'])==1 and len(tapes['teach'][0]['events'])==1
    group=tapes['teach'][0]; event=group['events'][0]
    lexical,layout=factor_inputs(event['features'])
    content=net.lexical[2](net.lexical[1](net.lexical[0](lexical)))
    binding=net.layout[0](1.-layout)
    raw_logits=net.order(content,binding)
    logp=wrapper(event['features'])
    options=event['likelihood']+group['state'][:,None,:,None]
    likelihood=options.gather(3,event['target'][:,None,None,None].expand(-1,4,2,1)).squeeze(-1).logsumexp(-1)
    endpoint=(logp+likelihood).logsumexp(-1)
    posterior=(logp+likelihood-endpoint[:,None]).exp()
    probabilities=logp.exp()
    teach_loss=-endpoint.mean()
    rehearsal_loss,rehearsal_count=run.objective('grounded',wrapper,world,tapes['rehearsal'])
    params=dict(net.named_parameters())
    teach_grad=torch.autograd.grad(teach_loss,tuple(params.values()),retain_graph=True)
    rehearsal_grad=torch.autograd.grad(rehearsal_loss,tuple(params.values()))
    gradients={}
    for (name,_),gt,gr in zip(params.items(),teach_grad,rehearsal_grad,strict=True):
        gradients[name]={'teach':gt.detach().tolist(),'rehearsal':gr.detach().tolist(),
                         'combined_l2':float(((gt+gr)*.5).norm())}
    rows=[]
    for row,record in enumerate(group['records']):
        word=next(t for t in record['utterances'][0]['text'].split() if t not in record['entities'])
        rows.append({'id':record['id'],'word':word,'lexical_position':int((1.-layout[row]).argmax()),
            'pre':record['context'][-1]['reading'],'post':record['utterances'][0]['reading'],
            'context_mode_posterior':group['state'][row].exp().tolist(),
            'content':float(content[row].detach()),'binding':float(binding[row].detach()),
            'interaction':float((content[row]*binding[row]).detach()),
            'raw_logits':raw_logits[row].detach().tolist(),'action_probability':probabilities[row].detach().tolist(),
            'endpoint_likelihood_by_action':likelihood[row].exp().tolist(),
            'endpoint_action_responsibility':posterior[row].detach().tolist(),
            'effective_logit_gradient':(probabilities[row]-posterior[row]).detach().tolist(),
            'endpoint_nll':float(-endpoint[row].detach())})
    summary={'teach_nll':float(teach_loss.detach()),'rehearsal_nll':float(rehearsal_loss.detach()),
        'teach_count':len(rows),'rehearsal_count':rehearsal_count,
        'set_prior_mass':tensor_stats(probabilities[:,2:].sum(-1).detach()),
        'set_posterior_responsibility':tensor_stats(posterior[:,2:].sum(-1).detach()),
        'native_contact_endpoint_likelihood':tensor_stats(likelihood[:,:2].exp()),
        'native_best_set_endpoint_likelihood':tensor_stats(likelihood[:,2:].max(-1).values.exp()),
        'gradient_l2':{'teach':float(torch.cat([x.flatten() for x in teach_grad]).norm()),
                       'rehearsal':float(torch.cat([x.flatten() for x in rehearsal_grad]).norm()),
                       'combined':float(torch.cat([((x+y)*.5).flatten() for x,y in zip(teach_grad,rehearsal_grad,strict=True)]).norm())},
        'lexemes':{}}
    for word in sorted({r['word'] for r in rows}):
        rs=[r for r in rows if r['word']==word]
        summary['lexemes'][word]={'teach_nll':sum(r['endpoint_nll'] for r in rs)/len(rs),
            'set_prior_mass':sum(sum(r['action_probability'][2:]) for r in rs)/len(rs),
            'set_posterior_responsibility':sum(sum(r['endpoint_action_responsibility'][2:]) for r in rs)/len(rs)}
    assert fingerprint(net.state_dict())==before and fingerprint(world.state_dict())==native_before
    assert all(p.grad is None for p in world.parameters())
    return {'summary':summary,'parameter_gradients':gradients,'rows':rows,'weights_unchanged':True,'world_unchanged':True}

output={'version':'post-publication-train-only-diagnostic-v1',
    'weights_publication':'6742c7df5b00f966c99c2a93d885d91eb21034e6',
    'scope':{'training_only':True,'challenge_access':False,'evaluator_access':False,
             'optimizer_steps':0,'new_fits':0,'prospective_fix_evaluated_only_at_initialization':True},
    'neutral_formula':'softmax(concat(log_softmax(contact_logits)+log(2), set_logits)); new SET logits remain zero',
    'seeds':{}}
for seed in (7,11,23,37,53):
    item=freeze['world_checkpoints'][f'nand/{seed}']
    path=run.WORLD/item['file']; reads[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    world=load_checkpoint(path,item['sha256'])['model'].eval().requires_grad_(False)
    tapes={k:m.pack(v,world,registry) for k,v in observed.items()}
    result={}
    for variant,final,neutral in [('initial_v1',False,False),('final_v1',True,False),('initial_probability_neutral',False,True)]:
        net=m.encoder(seed,parents[f'coordinates/{seed}']['state'])
        if final:
            record=read(FITTED/f'grounded-{seed}.json')
            net.load_state_dict({k:torch.tensor(v,dtype=torch.float64) for k,v in record['state'].items()})
            assert fingerprint(net.state_dict())==saved['reports'][f'grounded/{seed}']['final_sha256']
        else: assert fingerprint(net.state_dict())==saved['reports'][f'grounded/{seed}']['initial_sha256']
        result[variant]=diagnostic(net,world,tapes,neutral)
        if not neutral:
            reported=saved['reports'][f'grounded/{seed}']['final_objective'] if final else saved['reports'][f'grounded/{seed}']['curve'][0]
            assert all(abs(result[variant]['summary'][k+'_nll']-reported[k])<1e-12 for k in ('teach','rehearsal'))
        print(json.dumps({'seed':seed,'variant':variant,**result[variant]['summary']}),flush=True)
    output['seeds'][str(seed)]=result
output['read_inputs_sha256']=reads
output['exposure_counts']={'five_native_worlds_packed_on_two_original_training_tapes':True,
    'language_forward_conditions':15,'teach_forecasts_per_condition':16,'rehearsal_forecasts_per_condition':1152,
    'total_train_forecasts':15*(16+1152),'parameter_gradient_conditions':15,'updates':0}
path=pathlib.Path('/tmp/cemm_g3_v1_train_diagnostic.json')
path.write_text(json.dumps(output,sort_keys=True,indent=2,allow_nan=False)+'\n')
print(json.dumps({'artifact':str(path),'read_files':len(reads),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
