"""Archive-only arithmetic verification; imports no project/model/scorer code."""
import gzip, hashlib, itertools, json, math, sys
from pathlib import Path
import numpy as np

if not __debug__:
    raise RuntimeError('Run verification without Python -O; assertions are required')
root = Path(sys.argv[1])
raw_report = (root/'report.json').read_bytes()
assert hashlib.sha256(raw_report).hexdigest() == (root/'COMPLETE').read_text().strip()
report = json.loads(raw_report)
assert len(report['evaluations']) == 210 and len(report['checkpoint_checks']) == 30
worlds = np.array(list(itertools.product((0,1),repeat=3)))
mappings = tuple(itertools.permutations(range(3)))
cache, status_rows, answered_rows, summary_cells = {}, 0, 0, 0

def log_array(record):
    assert record['null_status'] == 'negative_infinity'
    a = np.array(record['values'],dtype=float)
    return np.where(np.isnan(a),-np.inf,a)

def near(a,b):
    assert a is not None and b is not None and math.isclose(a,b,rel_tol=1e-10,abs_tol=2e-12),(a,b)

def check_summary(row, good, answered, nll, brier, selected):
    n,a,c = int(selected.sum()),int((selected&answered).sum()),int((selected&good).sum())
    assert (row['queries'],row['answered'],row['correct'],row['wrong'],row['abstained'])==(n,a,c,a-c,n-a)
    valid=selected&answered
    infinite=int(np.isinf(nll[valid]).sum())
    assert row['infinite_nll_count']==infinite
    assert row['nll_status']==('infinite' if infinite else 'finite' if a else 'no_answers')
    if a:
        near(row['mean_brier'],float(brier[valid].mean()))
        near(row['accuracy_among_answered'],c/a)
        if not infinite:near(row['mean_nll'],float(nll[valid].mean()))
        else:assert row['mean_nll'] is None
    else:assert row['mean_nll'] is None and row['mean_brier'] is None

for entry in report['evaluations']:
    path=root/'records'/entry['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['file_sha256']
    with gzip.open(path,'rt') as f:
        rows=[json.loads(line,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x))) for line in f]
    assert len(rows)==19 and rows[0]['kind']=='header' and rows[-2]['kind']=='evaluator'
    header, evaluator=rows[0], rows[-2]
    x=np.array(header['readings'],dtype=np.float64); masks=np.array(header['masks'],dtype=bool)
    actions=np.array(header['actions'],dtype=np.int64)
    assert x.shape==masks.shape==(9,1536,3) and actions.shape==(8,1536,4)
    assert (x[~masks]==-1).all()
    digest=hashlib.sha256()
    for name,array,dtype in [('actions',actions,'torch.int64'),('masks',masks,'torch.bool'),('readings',x,'torch.float64')]:
        meta=json.dumps([name,dtype,list(array.shape)]).encode()
        for value in (meta,array.tobytes()):digest.update(len(value).to_bytes(8,'big'));digest.update(value)
    assert digest.hexdigest()==header['trace_sha256']==report['datasets'][entry['family']+'-'+entry['policy']]['trace_sha256']
    truth=np.array(evaluator['truth']);oracle=np.array(evaluator['oracle'])
    assert truth.shape==(9,1536,3) and oracle.shape==(8,1536,8)
    assert np.isin(truth,(0,1)).all() and np.allclose(oracle.sum(-1),1,atol=0,rtol=0)
    answers=[]; logs=[]
    for t in range(8):
        a,b=rows[1+2*t:3+2*t]
        assert a['kind']=='raw_forecast' and b['kind']=='normalized_forecast' and a['step']==b['step']==t
        answered=np.array(a['answered'],dtype=bool);raw=log_array(a['raw_log']);norm=log_array(b['log'])
        assert raw.shape==norm.shape==(1536,8)
        logz=np.logaddexp.reduce(raw[answered],axis=-1)
        assert (np.abs(logz)<=1e-10).all()
        assert np.allclose(raw[answered]-logz[:,None],norm[answered],atol=2e-12,rtol=1e-12)
        assert np.allclose(logz,np.array(b['subtracted_log_mass'])[answered],atol=2e-12,rtol=0)
        answers.append(answered);logs.append(norm)
    answer=np.array(answers);logp=np.array(logs);prob=np.exp(logp)
    gold=truth[1:]@np.array([4,2,1]);best=np.argmax(logp,axis=-1)
    correct=answer&(gold==best);nll=-np.take_along_axis(logp,gold[...,None],-1)[...,0]
    onehot=np.eye(8)[gold];brier=((prob-onehot)**2).sum(-1)
    codes=np.where(answer,correct.astype(np.uint8),2)
    assert np.array_equal(codes,np.array(evaluator['codes']))
    unchanged=(truth[:-1]==truth[1:]);errors=((worlds[best]!=truth[1:])&unchanged&answer[...,None]).sum(-1)
    assert np.array_equal(errors,np.array(evaluator['unchanged_bit_errors']))
    for t,row in enumerate(entry['steps']):
        ambiguous=(oracle[t]>0).sum(-1)>1
        check_summary(row,correct[t],answer[t],nll[t],brier[t],np.ones(1536,dtype=bool))
        check_summary(row['identifiable'],correct[t],answer[t],nll[t],brier[t],~ambiguous)
        check_summary(row['ambiguous'],correct[t],answer[t],nll[t],brier[t],ambiguous)
        assert row['unchanged_bit_errors']==int(errors[t].sum())
        summary_cells+=1
    pair=codes[6].reshape(256,6)
    assert entry['role_pairs']['both_correct']==int(((pair[::2]==1)&(pair[1::2]==1)).sum())
    assert entry['role_pairs']['both_answered']==int(((pair[::2]!=2)&(pair[1::2]!=2)).sum())
    viewprob=prob.reshape(8,256,6,8);viewanswer=answer.reshape(8,256,6);tv=[];statuschanged=0
    for v,mapping in enumerate(mappings[1:],1):
        lookup=[]
        for bits in worlds:
            renamed=[0,0,0]
            for old,new in enumerate(mapping):renamed[new]=bits[old]
            lookup.append(int(np.dot(renamed,[4,2,1])))
        valid=viewanswer[:,:,0]&viewanswer[:,:,v]
        differences=np.abs(viewprob[:,:,v,:][:,:,lookup]-viewprob[:,:,0,:]).sum(-1)/2
        tv.extend(differences[valid].tolist())
        statuschanged+=int((viewanswer[:,:,0]!=viewanswer[:,:,v]).sum())
    r=entry['renaming'];assert r['comparisons']==len(tv) and r['status_changed']==statuschanged
    assert r['over_tolerance']==sum(value>1e-10 for value in tv)
    if tv:near(r['max_tv'],max(tv));near(r['median_tv'],float(np.median(tv)))
    else:assert r['max_tv'] is None and r['median_tv'] is None
    cache[entry['family'],entry['policy'],entry['model'],entry['seed']]=codes
    status_rows+=codes.size;answered_rows+=int(answer.sum())

for row in report['paired_full_to_masked']:
    k=row['family'],row['policy'],row['model'],row['seed'];t=row['step']
    before=cache[k[0],'full',k[2],k[3]][t];after=cache[k][t]
    assert row['queries']==1536
    for field,a,b in [('correct_to_wrong',1,0),('wrong_to_correct',0,1),('correct_to_abstained',1,2),('abstained_to_correct',2,1)]:
        assert row[field]==np.flatnonzero((before==a)&(after==b)).tolist()
assert len(report['paired_full_to_masked'])==1120
result={'status':'ARCHIVE_ARITHMETIC_VERIFIED','report_sha256':hashlib.sha256(raw_report).hexdigest(),
        'evaluations':len(cache),'status_rows':status_rows,'answered_forecasts':answered_rows,
        'abstentions':status_rows-answered_rows,'per_step_summary_cells':summary_cells,
        'paired_comparisons':1120,'model_replay':False,'project_imports':False,
        'scope':'Hashes, sensor/mask encoding, raw normalization, MAP/NLL/Brier and identifiable/ambiguous subsets, unchanged-bit errors, role pairs, distribution renaming, regression IDs. Same-author separate implementation, not independent scientific review.'}
destination = Path(sys.argv[2]) if len(sys.argv) > 2 else root.parent / 'transfer-arithmetic-verification.json'
destination.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
