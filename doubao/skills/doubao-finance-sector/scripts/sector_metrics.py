#!/usr/bin/env python3
'''Validate and compute comparable sector metrics.'''
import json, math, sys
from datetime import datetime, timezone
from decimal import Decimal, DecimalException, localcontext

class ContractError(Exception): pass

def _constant(v): raise ContractError('invalid JSON numeric constant: '+v)
def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ContractError('duplicate JSON key: '+k)
        out[k]=v
    return out

def load_json(raw):
    try: return json.loads(raw,object_pairs_hook=_pairs,parse_float=Decimal,parse_int=int,parse_constant=_constant)
    except ContractError: raise
    except Exception as e: raise ContractError('malformed JSON: '+str(e)) from None

def req(o,k,p):
    if k not in o: raise ContractError(p+'.'+k+' is required')
    return o[k]
def obj(v,p):
    if not isinstance(v,dict): raise ContractError(p+' must be an object')
    return v
def text(v,p):
    if not isinstance(v,str) or v=='': raise ContractError(p+' must be a nonempty string')
    return v
def timestamp(v,p):
    s=text(v,p); s=s[:-1]+'+00:00' if s.endswith('Z') else s
    try: d=datetime.fromisoformat(s); off=d.utcoffset()
    except Exception as e: raise ContractError(p+' must be a valid ISO 8601 timestamp: '+str(e)) from None
    if off is None: raise ContractError(p+' must include a timezone')
    return d.astimezone(timezone.utc)
def positive(v,p):
    if isinstance(v,bool) or not isinstance(v,(int,Decimal)): raise ContractError(p+' must be a positive finite number')
    n=Decimal(v) if isinstance(v,int) else v
    if not n.is_finite() or n<=0: raise ContractError(p+' must be a positive finite number')
    return n
def count(v,p,positive_only=False):
    if isinstance(v,bool) or not isinstance(v,(int,Decimal)): raise ContractError(p+' must be an integer')
    if isinstance(v,Decimal):
        if not v.is_finite() or v!=v.to_integral_value(): raise ContractError(p+' must be an integer')
        v=int(v)
    if v<0 or (positive_only and v==0): raise ContractError(p+' must be a valid integer')
    return v
def pair(row,k,p):
    v=row.get(k)
    if v is None: return None
    v=obj(v,p+'.'+k)
    return {'start':positive(req(v,'start',p+'.'+k),p+'.'+k+'.start'),'end':positive(req(v,'end',p+'.'+k),p+'.'+k+'.end')}
def breadth(row,p):
    v=row.get('breadth')
    if v is None: return None
    v=obj(v,p+'.breadth'); r={k:count(req(v,k,p+'.breadth'),p+'.breadth.'+k,k=='total') for k in ('up','down','unchanged','total')}
    if r['up']+r['down']+r['unchanged']!=r['total']: raise ContractError(p+'.breadth counts must sum to total')
    return r
def row(v,i):
    p='rows['+str(i)+']'; v=obj(v,p)
    r={'id':text(req(v,'id',p),p+'.id'),'market':text(req(v,'market',p),p+'.market'),'taxonomy':text(req(v,'taxonomy',p),p+'.taxonomy'),'basis':text(req(v,'basis',p),p+'.basis'),'state':text(req(v,'state',p),p+'.state'),'start':timestamp(req(v,'start',p),p+'.start'),'end':timestamp(req(v,'end',p),p+'.end'),'available_at':timestamp(req(v,'available_at',p),p+'.available_at'),'quote':pair(v,'quote',p),'benchmark':pair(v,'benchmark',p),'breadth':breadth(v,p)}
    if r['start']>=r['end']: raise ContractError(p+'.start must be earlier than end')
    return r
def calc(label,fn):
    try:
        with localcontext() as c: c.prec=50; v=fn()
    except (DecimalException,OverflowError,ZeroDivisionError) as e: raise ContractError(label+' calculation failed: '+str(e)) from None
    if not v.is_finite(): raise ContractError(label+' calculation overflowed')
    return v
def number(v,label):
    if v.is_zero(): return 0.0
    try: n=float(v)
    except Exception as e: raise ContractError(label+' is outside finite output range: '+str(e)) from None
    if not math.isfinite(n) or n==0.0: raise ContractError(label+' is outside finite output range')
    return n
def ret(v,label):
    if v is None: return None,None
    d=calc(label,lambda:(v['end']/v['start']-Decimal(1))*Decimal(100)); return d,number(d,label)
def metrics(r):
    a,av=ret(r['quote'],r['id']+'.return_pct'); b,bv=ret(r['benchmark'],r['id']+'.benchmark_return_pct'); rel=None
    if a is not None and b is not None: rel=number(calc(r['id']+'.relative_pp',lambda:a-b),r['id']+'.relative_pp')
    up=down=None
    if r['breadth'] is not None:
        up=number(calc(r['id']+'.up_share',lambda:Decimal(r['breadth']['up'])/Decimal(r['breadth']['total'])),r['id']+'.up_share')
        down=number(calc(r['id']+'.down_share',lambda:Decimal(r['breadth']['down'])/Decimal(r['breadth']['total'])),r['id']+'.down_share')
    return {'return_pct':av,'benchmark_return_pct':bv,'relative_pp':rel,'up_share':up,'down_share':down}
def process(doc):
    root=obj(doc,'input'); raw_as=req(root,'as_of','input'); asof=timestamp(raw_as,'as_of'); values=req(root,'rows','input')
    if not isinstance(values,list): raise ContractError('rows must be an array')
    rows=[]; seen=set()
    for i,v in enumerate(values):
        r=row(v,i)
        if r['id'] in seen: raise ContractError('duplicate row id: '+r['id'])
        seen.add(r['id']); rows.append(r)
    output=[]; groups=[]; positions={}
    for r in rows:
        reasons=[]
        if r['end']>asof: reasons.append('end_after_as_of')
        if r['available_at']>asof: reasons.append('available_at_after_as_of')
        eligible=not reasons; out={'id':r['id'],'eligible':eligible,'reasons':reasons,'return_pct':None,'benchmark_return_pct':None,'relative_pp':None,'up_share':None,'down_share':None}
        if eligible:
            out.update(metrics(r)); key=(r['market'],r['taxonomy'],r['basis'],r['state'],r['start'],r['end'])
            if key not in positions: positions[key]=len(groups); groups.append([])
            groups[positions[key]].append(r['id'])
        output.append(out)
    return {'as_of':raw_as,'rows':output,'comparison_groups':groups}
def emit(v): sys.stdout.write(json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
def main():
    try:
        if len(sys.argv)!=2: raise ContractError('usage: sector_metrics.py INPUT.json or -')
        if sys.argv[1]=='-': raw=sys.stdin.read()
        else:
            try:
                with open(sys.argv[1],'r',encoding='utf-8') as f: raw=f.read()
            except Exception as e: raise ContractError('cannot read input: '+str(e)) from None
        result=process(load_json(raw))
    except ContractError as e: emit({'error':{'message':str(e) or 'invalid input'}}); return 1
    except Exception as e: emit({'error':{'message':'processing failed: '+str(e)}}); return 1
    emit(result); return 0
if __name__=='__main__': sys.exit(main())
