#!/usr/bin/env python3
"""Offline structural/deduplication check. Never dispatches or authorizes work."""
import argparse, datetime as dt, hashlib, json, re, sys
ACTIVE={'claimed','submitted','running','validating','unknown'}
STATES=ACTIVE|{'planned','done','failed','blocked','cancelled'}
def validate(data):
    errors=[]; ids={}; keys={}
    if not isinstance(data,dict) or not isinstance(data.get('tasks'),list): return ['manifest requires a tasks array']
    if not data.get('project_id'): errors.append('project_id missing')
    for i,t in enumerate(data['tasks']):
        if not isinstance(t,dict): errors.append(f'task[{i}] must be object'); continue
        name=t.get('task_id'); tag=name or f'task[{i}]'
        if not isinstance(name,str) or not name:
            errors.append(f'task[{i}]: task_id missing'); continue
        elif name in ids: errors.append(f'{tag}: duplicate task_id')
        ids[name]=t
        if not isinstance(t.get('status'),str) or t.get('status') not in STATES: errors.append(f'{tag}: invalid status')
        for f in ('input_sha256','script_sha256'):
            if not isinstance(t.get(f),str) or not re.fullmatch('[a-f0-9]{64}',t[f]): errors.append(f'{tag}: {f} must be SHA-256')
        if not isinstance(t.get('revision'),int) or isinstance(t.get('revision'),bool) or t['revision']<1: errors.append(f'{tag}: revision must be positive integer')
        if not isinstance(t.get('resource'),str) or not t.get('resource'): errors.append(f'{tag}: resource must be nonempty string')
        if t.get('model_revision') is not None and not isinstance(t.get('model_revision'),str): errors.append(f'{tag}: model_revision must be string or null')
        if not isinstance(t.get('outputs',[]),list): errors.append(f'{tag}: outputs must be array')
        if not isinstance(t.get('parameters'),dict): errors.append(f'{tag}: parameters must be object')
        if not isinstance(t.get('shard_id'),str) or not t['shard_id']: errors.append(f'{tag}: shard_id missing')
        if not isinstance(t.get('dependencies'),list) or not all(isinstance(x,str) for x in t.get('dependencies',[])): errors.append(f'{tag}: dependencies must be string array')
        if isinstance(t.get('status'),str) and t.get('status') in ACTIVE:
            if not t.get('owner'): errors.append(f'{tag}: active task needs owner')
            try:
                expiry=dt.datetime.fromisoformat(t.get('lease_until','').replace('Z','+00:00'))
                if expiry.tzinfo is None: raise ValueError()
                if expiry<=dt.datetime.now(dt.timezone.utc): errors.append(f'{tag}: expired lease; reconcile platform before reclaim')
            except (TypeError,ValueError,AttributeError): errors.append(f'{tag}: active task needs timezone-aware lease_until')
            key=hashlib.sha256(json.dumps([t.get(k) for k in ('input_sha256','script_sha256','parameters','model_revision','shard_id')],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if key in keys: errors.append(f'{tag}: equivalent active work also assigned to {keys[key]}')
            keys[key]=tag
        if isinstance(t.get('status'),str) and t.get('status') in {'submitted','running','validating'} and not t.get('submission_ref'): errors.append(f'{tag}: submitted work needs submission_ref')
        if t.get('status')=='done':
            if not t.get('outputs'): errors.append(f'{tag}: done task needs verified outputs')
            for out in t.get('outputs',[]) if isinstance(t.get('outputs'),list) else [None]:
                if not isinstance(out,dict) or out.get('verified') is not True or not re.fullmatch('[a-f0-9]{64}',str(out.get('sha256',''))): errors.append(f'{tag}: invalid verified output')
    for name,t in ids.items():
        deps=t.get('dependencies',[])
        if not isinstance(deps,list): continue
        for dep in deps:
            if not isinstance(dep,str) or dep not in ids: errors.append(f'{name}: unknown dependency {dep}'); continue
            if isinstance(t.get('status'),str) and t.get('status') in ACTIVE and ids[dep].get('status')!='done': errors.append(f'{name}: dependency {dep} not done')
    visiting=set(); visited=set()
    def visit(n):
        if n in visiting: errors.append(f'{n}: dependency cycle'); return
        if n in visited: return
        visiting.add(n)
        for d in ids[n].get('dependencies',[]) if isinstance(ids[n].get('dependencies'),list) else []:
            if isinstance(d,str) and d in ids: visit(d)
        visiting.remove(n);visited.add(n)
    for n in ids: visit(n)
    return errors
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('manifest');args=a.parse_args()
    try:
        with open(args.manifest,encoding='utf8') as f: errors=validate(json.load(f))
    except (OSError,ValueError) as e: errors=[str(e)]
    print(json.dumps({'ok':not errors,'errors':errors,'scope':'offline checks only; no authorization or dispatch'},ensure_ascii=False,indent=2))
    sys.exit(bool(errors))
