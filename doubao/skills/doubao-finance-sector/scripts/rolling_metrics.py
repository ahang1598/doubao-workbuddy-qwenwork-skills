#!/usr/bin/env python3
'''Non-overlapping rolling means and ratios.'''
import json,math,sys
from datetime import timezone
from decimal import Decimal,localcontext
import sector_metrics as sm
E=sm.ContractError

def number(v,p,null=False):
    if v is None and null:return None
    if isinstance(v,bool) or not isinstance(v,(int,float,Decimal)):raise E(p+' must be finite number or null')
    n=v if isinstance(v,Decimal) else Decimal(str(v))
    if not n.is_finite():raise E(p+' must be finite number or null')
    return n
def count(v,p):
    if isinstance(v,bool) or not isinstance(v,(int,Decimal)) or int(v)!=v or v<=0:raise E(p+' must be positive integer')
    return int(v)
def out(v,p):
    if v is None:return None
    if v==0:return 0.0
    n=float(v)
    if not math.isfinite(n) or n==0:raise E(p+' outside finite output range')
    return n
def iso(v):return v.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def mean(v):
    with localcontext() as c:c.prec=50;return sum(v,Decimal(0))/Decimal(len(v))
def boundary(v):return {'start':iso(v[0]['at']) if v else None,'end':iso(v[-1]['at']) if v else None}
def seconds(v):return Decimal(v.days*86400+v.seconds)+Decimal(v.microseconds)/Decimal(1000000)

def process(doc):
    root=sm.obj(doc,'input'); raw_as=sm.req(root,'as_of','input'); asof=sm.timestamp(raw_as,'input.as_of'); rows=sm.req(root,'rows','input')
    if not isinstance(rows,list):raise E('input.rows must be array')
    result=[];ids=set()
    for i,raw in enumerate(rows):
        p='input.rows['+str(i)+']';r=sm.obj(raw,p);rid=sm.text(sm.req(r,'id',p),p+'.id')
        if rid in ids:raise E('duplicate row id: '+rid)
        ids.add(rid);n=count(sm.req(r,'recent_count',p),p+'.recent_count');m=count(sm.req(r,'prior_count',p),p+'.prior_count');limit=None
        if r.get('max_staleness_seconds') is not None:
            limit=number(r['max_staleness_seconds'],p+'.max_staleness_seconds')
            if limit<=0:raise E(p+'.max_staleness_seconds must be positive')
        obs=[];last=None
        for j,x in enumerate(sm.req(r,'observations',p)):
            q=p+'.observations['+str(j)+']';x=sm.obj(x,q);at=sm.timestamp(sm.req(x,'at',q),q+'.at')
            if last is not None and at<=last:raise E(p+'.observations must be strictly ordered and unique')
            last=at;obs.append({'at':at,'value':number(sm.req(x,'value',q),q+'.value',True)})
        eligible=[x for x in obs if x['at']<=asof];selected=eligible[-(n+m):];recent=selected[-min(n,len(selected)):] if selected else [];prior=selected[:max(0,len(selected)-len(recent))];latest=eligible[-1]['at'] if eligible else None;gap=seconds(asof-latest) if latest else None;reason=None;pm=rm=ratio=None
        if len(selected)<n+m:reason='insufficient_observations'
        elif any(x['value'] is None for x in selected):reason='missing_value_in_selected_windows'
        else:
            pm=mean([x['value'] for x in prior]);rm=mean([x['value'] for x in recent])
            if pm==0:reason='zero_prior_mean'
            elif limit is not None and gap>limit:reason='stale_latest_observation'
            else:ratio=rm/pm
        result.append({'id':rid,'status':'unknown' if reason else 'supported','reason':reason,'ratio':out(ratio,rid+'.ratio'),'counts':{'recent_requested':n,'prior_requested':m,'recent_selected':len(recent),'prior_selected':len(prior),'recent_values':sum(x['value'] is not None for x in recent),'prior_values':sum(x['value'] is not None for x in prior),'eligible':len(eligible),'future_excluded':len(obs)-len(eligible)},'windows':{'prior':boundary(prior),'recent':boundary(recent)},'means':{'prior':out(pm,rid+'.prior_mean'),'recent':out(rm,rid+'.recent_mean')},'latest_eligible_at':iso(latest) if latest else None,'as_of_gap_seconds':out(gap,rid+'.gap'),'staleness_status':'no_eligible_observation' if latest is None else ('not_assessed' if limit is None else ('stale' if gap>limit else 'within_limit'))})
    return {'version':'rolling-metrics-v1','as_of':raw_as,'rows':result}

def schema():return {'$schema':'https://json-schema.org/draft/2020-12/schema','title':'rolling-metrics-v1','input':{'required':['as_of','rows'],'row_required':['id','recent_count','prior_count','observations'],'observation_required':['at','value']},'success_required':['version','as_of','rows'],'statuses':['supported','unknown'],'reasons':[None,'insufficient_observations','missing_value_in_selected_windows','zero_prior_mean','stale_latest_observation'],'error_required':['error.code','error.message']}
def emit(v):sys.stdout.write(json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
def main():
    try:
        if len(sys.argv)!=2:raise E('usage: rolling_metrics.py INPUT.json, -, or --schema')
        if sys.argv[1]=='--schema':emit(schema());return 0
        raw=sys.stdin.read() if sys.argv[1]=='-' else open(sys.argv[1],encoding='utf-8').read();value=process(sm.load_json(raw))
    except E as x:emit({'error':{'code':'invalid_input','message':str(x) or 'invalid input'}});return 1
    except Exception as x:emit({'error':{'code':'processing_failed','message':str(x) or 'processing failed'}});return 1
    emit(value);return 0
if __name__=='__main__':sys.exit(main())
