#!/usr/bin/env python3
'''Validated sector workflow v2.'''
import copy,csv,hashlib,io,json,os,re,shutil,stat,sys,tempfile
from datetime import date,datetime,time,timezone
from decimal import Decimal
from pathlib import Path,PurePosixPath
from zoneinfo import ZoneInfo
import rolling_metrics as rm
import sector_metrics as sm
E=sm.ContractError

def req(o,k,p):
    if k not in o:raise E(p+'.'+k+' required')
    return o[k]
def obj(v,p):
    if not isinstance(v,dict):raise E(p+' must be object')
    return v
def arr(v,p):
    if not isinstance(v,list):raise E(p+' must be array')
    return v
def text(v,p):
    if not isinstance(v,str) or not v:raise E(p+' must be nonempty string')
    return v
def boolean(v,p):
    if not isinstance(v,bool):raise E(p+' must be boolean')
    return v
def positive_int(v,p):
    if isinstance(v,bool) or not isinstance(v,int) or v<=0:raise E(p+' must be positive integer')
    return v
def number(v,p):
    if isinstance(v,bool) or not isinstance(v,(int,Decimal)):raise E(p+' must be integer or decimal')
    return v
ROLES={'identifier','observation','source_excerpt','canonical'}
def decimal_token(v):
    text=format(v,'f')
    if '.' not in text and 'e' not in text.lower():text+='.0'
    return text
def typed_ready(v,markers):
    if v is None or isinstance(v,bool) or isinstance(v,str):return v
    if isinstance(v,int) and not isinstance(v,bool):return v
    if isinstance(v,Decimal):
        token='##DEC%d##'%len(markers);markers.append(decimal_token(v));return token
    if isinstance(v,float):
        if v!=v or v in (float('inf'),float('-inf')):raise E('non-finite float is not allowed in canonical JSON')
        token='##DEC%d##'%len(markers);markers.append(decimal_token(Decimal(str(v))));return token
    if isinstance(v,dict):return {k:typed_ready(x,markers) for k,x in v.items()}
    if isinstance(v,list):return [typed_ready(x,markers) for x in v]
    raise E('unsupported canonical JSON type: '+type(v).__name__)
def dumps_typed(v,**kwargs):
    markers=[];payload=dict(kwargs);payload.setdefault('ensure_ascii',False);payload['allow_nan']=False
    text=json.dumps(typed_ready(v,markers),**payload)
    for i,num in enumerate(markers):text=text.replace('"##DEC%d##"'%i,num)
    return text
def as_decimal(v):return v if isinstance(v,Decimal) else Decimal(v)
def compute(op,left,right,cid):
    if op=='divide':
        left,right=as_decimal(left),as_decimal(right)
        if right==0:raise E('calculation '+cid+' division by zero')
        return left/right
    if isinstance(left,int) and isinstance(right,int):
        if op=='add':return left+right
        if op=='subtract':return left-right
        return left*right
    left,right=as_decimal(left),as_decimal(right)
    if op=='add':return left+right
    if op=='subtract':return left-right
    return left*right
def choice(v,a,p):
    v=text(v,p)
    if v not in a:raise E(p+' invalid value')
    return v
def strings(v,p,empty=False):
    v=arr(v,p);out=[]
    for i,x in enumerate(v):
        x=text(x,p+'['+str(i)+']')
        if x in out:raise E(p+' duplicate value')
        out.append(x)
    if not empty and not out:raise E(p+' must not be empty')
    return out
def iso(v):return v.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def strict_equal(left,right):
    if type(left) is not type(right):return False
    if isinstance(left,dict):return left.keys()==right.keys() and all(strict_equal(left[k],right[k]) for k in left)
    if isinstance(left,list):return len(left)==len(right) and all(strict_equal(a,b) for a,b in zip(left,right))
    return left==right
def canonical_json(v):return dumps_typed(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(v):return hashlib.sha256(canonical_json(v).encode()).hexdigest()

def calendars(raw):
    out={}
    for i,c in enumerate(arr(raw,'calendars')):
        p='calendars['+str(i)+']';c=obj(c,p);cid=text(req(c,'id',p),p+'.id')
        if cid in out:raise E('duplicate calendar '+cid)
        zone=ZoneInfo(text(req(c,'timezone',p),p+'.timezone'));sessions=[];last=None;ids=set()
        for j,s in enumerate(arr(req(c,'sessions',p),p+'.sessions')):
            q=p+'.sessions['+str(j)+']';s=obj(s,q);sid=text(req(s,'id',q),q+'.id');a=sm.timestamp(req(s,'open',q),q+'.open');b=sm.timestamp(req(s,'close',q),q+'.close')
            if sid in ids or a>=b or (last and a<last):raise E(q+' duplicate, invalid or overlapping')
            ids.add(sid);last=b;sessions.append({'id':sid,'open':a,'close':b})
        out[cid]={'source':text(req(c,'source',p),p+'.source'),'zone':zone,'sessions':sessions,'index':{x['id']:n for n,x in enumerate(sessions)}}
    return out

def claims(raw,asof,cals):
    results=[];models={};all_evidence={};pids=set()
    for i,c in enumerate(arr(raw,'claims')):
        p='claims['+str(i)+']';c=obj(c,p);cid=text(req(c,'id',p),p+'.id');pid=text(req(c,'proposition_id',p),p+'.proposition_id')
        if cid in models or pid in pids:raise E(p+' duplicate claim or proposition')
        proposition=text(req(c,'proposition',p),p+'.proposition');pids.add(pid);status=choice(req(c,'status',p),{'supported','unverified','contradicted','conditional'},p+'.status');ctype=choice(req(c,'claim_type',p),{'market_finding','research_priority','market_sequence'},p+'.claim_type');quant=choice(req(c,'quantifier',p),{'bounded','universal','unique','necessary'},p+'.quantifier');scope=obj(req(c,'scope',p),p+'.scope');start=sm.timestamp(req(scope,'start',p+'.scope'),p+'.scope.start');end=sm.timestamp(req(scope,'end',p+'.scope'),p+'.scope.end');coverage=choice(req(scope,'coverage',p+'.scope'),{'complete','sample','unknown'},p+'.scope.coverage');strings(req(scope,'objects',p+'.scope'),p+'.scope.objects');text(req(scope,'market',p+'.scope'),p+'.scope.market');text(req(scope,'taxonomy',p+'.scope'),p+'.scope.taxonomy')
        if start>=end or (status!='conditional' and end>asof):raise E(p+' invalid scope interval')
        evidence={}
        for j,e in enumerate(arr(req(c,'evidence',p),p+'.evidence')):
            q=p+'.evidence['+str(j)+']';e=obj(e,q);eid=text(req(e,'id',q),q+'.id')
            if eid in all_evidence:raise E('duplicate evidence '+eid)
            observed=req(e,'observed_at',q);available=req(e,'available_at',q);observed=None if observed is None else sm.timestamp(observed,q+'.observed_at');available=None if available is None else sm.timestamp(available,q+'.available_at');eligible=observed is not None and available is not None and observed<=asof and available<=asof;role=choice(req(e,'role',q),{'support','contradict','context','isolated'},q+'.role')
            if observed and available and available<observed:raise E(q+' available_at precedes observed_at')
            if not eligible and role!='isolated':raise E(q+' ineligible evidence must be isolated')
            item={'id':eid,'eligible':eligible,'observed_at':observed,'available_at':available,'direct':boolean(req(e,'direct',q),q+'.direct'),'decisive':boolean(req(e,'decisive',q),q+'.decisive'),'role':role,'targets':strings(req(e,'targets',q),q+'.targets'),'supports':strings(req(e,'supports',q),q+'.supports',True),'session_ids':strings(e.get('session_ids',[]),q+'.session_ids',True),'group':text(req(e,'group',q),q+'.group'),'coverage':choice(req(e,'coverage',q),{'complete','partial','unknown'},q+'.coverage'),'claim_id':cid};text(req(e,'type',q),q+'.type');text(req(e,'source',q),q+'.source');evidence[eid]=item;all_evidence[eid]=item
        support=[e for e in evidence.values() if e['eligible'] and e['decisive'] and e['role']=='support' and pid in e['targets']];against=[e for e in evidence.values() if e['eligible'] and e['decisive'] and e['direct'] and e['role']=='contradict' and pid in e['targets']]
        if support and against:raise E(p+' has conflicting decisive evidence')
        if status=='supported' and not support:raise E(p+' unsupported supported claim')
        if status=='contradicted' and not against:raise E(p+' lacks direct contradiction')
        if status=='unverified' and (support or against):raise E(p+' unverified claim has decisive evidence')
        if status=='conditional' and against:raise E(p+' conditional claim has decisive contradiction')
        if status=='supported' and boolean(req(c,'independent_required',p),p+'.independent_required') and len({e['group'] for e in support})<2:raise E(p+' lacks independent evidence')
        inference=strings(req(c,'inferences',p),p+'.inferences',True)
        if ctype=='research_priority' and 'market_sequence' in inference:raise E(p+' research priority is not market sequence')
        for tag in ('investor_identity','investor_intent','actual_net_capital'):
            if tag in inference and status=='supported' and not any(e['direct'] and tag in e['supports'] for e in support):raise E(p+' lacks direct '+tag+' evidence')
        for channel in strings(req(c,'excluded_channels',p),p+'.excluded_channels',True):
            if not any(e['direct'] and 'exclude_channel:'+channel in e['supports'] for e in support):raise E(p+' cannot exclude '+channel)
        competitors=[]
        for x in arr(req(c,'competing_explanations',p),p+'.competing_explanations'):
            x=obj(x,p+'.competitor');xid=text(req(x,'id',p),p+'.competitor.id');xs=choice(req(x,'status',p),{'supported','unverified','contradicted'},p+'.competitor.status');eids=strings(req(x,'evidence_ids',p),p+'.competitor.evidence_ids',True)
            if any(eid not in evidence for eid in eids):raise E(p+' competitor references unknown evidence')
            selected=[evidence[eid] for eid in eids];role='support' if xs=='supported' else 'contradict'
            if xs!='unverified' and not any(e['eligible'] and e['direct'] and e['role']==role and xid in e['targets'] for e in selected):raise E(p+' competitor status lacks direct evidence')
            competitors.append(xs)
        complete=boolean(req(c,'competing_explanations_complete',p),p+'.competing_explanations_complete')
        if status=='supported' and quant in {'universal','unique','necessary'} and (coverage!='complete' or not any(e['coverage']=='complete' for e in support)):raise E(p+' lacks complete coverage')
        if status=='supported' and quant in {'unique','necessary'} and (not complete or any(x!='contradicted' for x in competitors)):raise E(p+' unresolved competitors')
        if 'consecutive_session_acceleration' in inference:
            x=obj(req(c,'comparison',p),p+'.comparison');cal=text(req(x,'calendar_id',p),p+'.comparison.calendar_id');left=text(req(x,'left_session_id',p),p+'.comparison.left_session_id');right=text(req(x,'right_session_id',p),p+'.comparison.right_session_id')
            if cal not in cals or left not in cals[cal]['index'] or right not in cals[cal]['index'] or cals[cal]['index'][right]!=cals[cal]['index'][left]+1:raise E(p+' requires adjacent single sessions')
            bound=set()
            for e in support:
                for sid in e['session_ids']:
                    if sid not in (left,right):raise E(p+' acceleration evidence references undeclared session')
                    session=cals[cal]['sessions'][cals[cal]['index'][sid]]
                    if e['observed_at'] is None or not session['open']<=e['observed_at']<=session['close']:raise E(p+' acceleration evidence outside declared session')
                    bound.add(sid)
            if bound!={left,right}:raise E(p+' acceleration evidence must bind both declared sessions')
        canonical=req(c,'canonical',p)
        if canonical is None or canonical=='':raise E(p+'.canonical empty')
        models[cid]={'id':cid,'pid':pid,'proposition':proposition,'decisive':boolean(req(c,'decisive',p),p+'.decisive'),'status':status,'canonical':canonical,'evidence':evidence};results.append({'id':cid,'proposition_id':pid,'proposition':proposition,'status':status,'canonical':canonical,'eligible_evidence_ids':[e['id'] for e in evidence.values() if e['eligible']],'isolated_evidence_ids':[e['id'] for e in evidence.values() if e['role']=='isolated'],'semantic_review_required':True})
    return results,models,all_evidence

def uses(raw,complete,models):
    if complete is not True:raise E('final_uses_complete must be true')
    out=[];seen=set();covered=set()
    for i,u in enumerate(arr(raw,'final_uses')):
        p='final_uses['+str(i)+']';u=obj(u,p);uid=text(req(u,'id',p),p+'.id');cid=text(req(u,'claim_id',p),p+'.claim_id')
        if uid in seen or cid not in models or not models[cid]['decisive']:raise E(p+' duplicate or non-decisive claim')
        text(req(u,'location',p),p+'.location');text(req(u,'kind',p),p+'.kind')
        if not strict_equal(req(u,'value',p),models[cid]['canonical']):raise E(p+' differs from canonical type or value')
        seen.add(uid);covered.add(cid);out.append(copy.deepcopy(u))
    missing=[x for x,m in models.items() if m['decisive'] and x not in covered]
    if missing:raise E('decisive claims lack final uses: '+','.join(missing))
    return {'complete':True,'uses':out}

def scenarios(raw,models,evidence,asof):
    allowed={'reinforcement':{'raise_priority','maintain_priority','gather_data'},'invalidation':{'lower_priority','suspend_conclusion','gather_data'},'missing_data':{'lower_priority','suspend_conclusion','gather_data'}};out=[];seen=set()
    for i,s in enumerate(arr(raw,'scenarios')):
        p='scenarios['+str(i)+']';s=obj(s,p);sid=text(req(s,'id',p),p+'.id');cid=text(req(s,'claim_id',p),p+'.claim_id')
        if sid in seen or cid not in models:raise E(p+' duplicate or unknown claim')
        seen.add(sid);condition=obj(req(s,'condition',p),p+'.condition');state=choice(req(condition,'state',p),set(allowed),p+'.condition.state')
        if req(condition,'proposition_id',p)!=models[cid]['pid']:raise E(p+' proposition mismatch')
        signal=text(req(condition,'signal',p),p+'.condition.signal');operator=text(req(condition,'operator',p),p+'.condition.operator');expected=req(condition,'expected',p);unit=req(condition,'unit',p);window=obj(req(s,'window',p),p+'.window');start=sm.timestamp(req(window,'start',p),p+'.window.start');end=sm.timestamp(req(window,'end',p),p+'.window.end');evaluation=choice(req(s,'evaluation',p),{'met','not_met','unknown'},p+'.evaluation')
        if start>=end or (evaluation!='unknown' and end>asof):raise E(p+' invalid evaluated window')
        ids=strings(req(s,'evidence_ids',p),p+'.evidence_ids',True)
        if any(x not in evidence or evidence[x]['claim_id']!=cid for x in ids):raise E(p+' unrelated evidence')
        selected=[evidence[x] for x in ids];action=obj(req(s,'action',p),p+'.action')
        if req(action,'authorization',p)!='research_only':raise E(p+' action must be research_only')
        direction=choice(req(action,'direction',p),allowed[state],p+'.action.direction');text(req(action,'description',p),p+'.action.description')
        in_window=lambda e:e['observed_at'] is not None and start<=e['observed_at']<=end
        if evaluation=='met' and state=='reinforcement':
            if models[cid]['status'] not in {'supported','conditional'}:raise E(p+' reinforcement incompatible with claim status')
            if models[cid]['status']=='conditional' and action.get('conditional') is not True:raise E(p+' conditional claim requires conditional reinforcement action')
            if not any(e['eligible'] and e['decisive'] and in_window(e) and e['role']=='support' and models[cid]['pid'] in e['targets'] for e in selected):raise E(p+' lacks decisive in-window proposition reinforcement evidence')
        if evaluation=='met' and state=='invalidation' and (models[cid]['status']!='contradicted' or not any(e['eligible'] and in_window(e) and e['direct'] and e['role']=='contradict' and models[cid]['pid'] in e['targets'] for e in selected)):raise E(p+' lacks in-window proposition-specific direct invalidation')
        if evaluation=='met' and state=='missing_data' and direction!='gather_data' and models[cid]['status']!='unverified':raise E(p+' missing-data downgrade requires unverified claim')
        declared=arr(req(s,'uses',p),p+'.uses')
        if not declared:raise E(p+' action uses required')
        for j,x in enumerate(declared):
            q=p+'.uses['+str(j)+']';x=obj(x,q);text(req(x,'location',q),q+'.location');text(req(x,'kind',q),q+'.kind')
            if not strict_equal(req(x,'value',q),action):raise E(p+' action uses inconsistent type or value')
        out.append({'id':sid,'claim_id':cid,'state':state,'condition':{'proposition_id':models[cid]['pid'],'signal':signal,'operator':operator,'expected':expected,'unit':unit,'state':state},'window':{'start':iso(start),'end':iso(end)},'evaluation':evaluation,'evidence_ids':ids,'action':copy.deepcopy(action),'uses':copy.deepcopy(declared),'current_action':copy.deepcopy(action) if evaluation=='met' else None,'semantic_review_required':True})
    return out

def events(raw,cals,asof):
    out=[];seen=set()
    for i,e in enumerate(arr(raw,'events')):
        p='events['+str(i)+']';e=obj(e,p);eid=text(req(e,'id',p),p+'.id');cid=text(req(e,'calendar_id',p),p+'.calendar_id')
        if eid in seen or cid not in cals:raise E(p+' duplicate or unknown calendar')
        seen.add(eid);precision=choice(req(e,'precision',p),{'timestamp','date'},p+'.precision');available=sm.timestamp(req(e,'available_at',p),p+'.available_at');needed=positive_int(req(e,'window_sessions',p),p+'.window_sessions');sessions=cals[cid]['sessions'];anchor=None;zone=str(cals[cid]['zone'])
        if precision=='timestamp':
            event=sm.timestamp(req(e,'event_at',p),p+'.event_at')
            if available<event:raise E(p+' available before event')
            effective=max(event,available);event_value=iso(event)
        else:
            day=date.fromisoformat(text(req(e,'event_at',p),p+'.event_at'));boundary=datetime.combine(day,time.min,tzinfo=cals[cid]['zone']).astimezone(timezone.utc)
            if available<boundary:raise E(p+' available before event date')
            policy=choice(req(e,'date_policy',p),{'next_session','unresolved'},p+'.date_policy')
            event_value=day.isoformat();effective=max(boundary,available)
            if policy=='unresolved':out.append({'id':eid,'event_at':event_value,'available_at':iso(available),'effective_at':None,'precision':precision,'timezone':zone,'status':'unresolved','reason':'date_precision_window_unresolved'});continue
        base={'id':eid,'event_at':event_value,'available_at':iso(available),'effective_at':iso(effective),'precision':precision,'timezone':zone}
        if effective>asof:out.append({**base,'status':'not_available_as_of','reason':'available_after_as_of'});continue
        for j,x in enumerate(sessions):
            if x['open']>=effective and (precision=='timestamp' or x['open'].astimezone(cals[cid]['zone']).date()>day):anchor=j;break
        if anchor is None:out.append({**base,'status':'incomplete','reason':'calendar_horizon_exhausted'});continue
        target=sessions[anchor:anchor+needed];observed=[x for x in target if x['close']<=asof];complete=len(target)==needed and len(observed)==needed;out.append({**base,'status':'complete' if complete else 'incomplete','reason':None if complete else 'response_window_incomplete','observed_session_ids':[x['id'] for x in observed],'response_start':iso(target[0]['open']),'response_end':iso(target[-1]['close']) if complete else None,'calendar_source':cals[cid]['source']})
    return out

def rel(v,p):
    v=text(v,p);x=PurePosixPath(v)
    if x.is_absolute() or any(y in ('','.','..') for y in x.parts):raise E(p+' unsafe path')
    return v
def render(x,p):
    fmt=choice(req(x,'format',p),{'json','text','csv'},p+'.format');c=req(x,'content',p)
    if fmt=='json':return fmt,(dumps_typed(c,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    if fmt=='text':return fmt,text(c,p+'.content').encode()
    cols=strings(req(c,'columns',p),p+'.columns');stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=cols,lineterminator='\n');writer.writeheader()
    for row in arr(req(c,'rows',p),p+'.rows'):writer.writerow({k:'' if row[k] is None else row[k] for k in cols})
    return fmt,stream.getvalue().encode()
def parse(fmt,data):
    if not data:raise E('empty artifact')
    if fmt=='json':return sm.load_json(data.decode())
    if fmt=='text':return data.decode()
    reader=csv.DictReader(io.StringIO(data.decode()));return {'columns':reader.fieldnames,'rows':list(reader)}
def pointer(v,path):
    if path=='':return v
    for raw in text(path,'pointer')[1:].split('/'):
        k=raw.replace('~1','/').replace('~0','~');v=v[int(k)] if isinstance(v,list) else v[k]
    return v
def field(doc,fmt,spec):
    kind=choice(req(spec,'kind','field'),{'json','csv','text'},'field.kind');selector=req(spec,'selector','field')
    if kind=='json' and fmt=='json':return pointer(doc,selector)
    if kind=='csv' and fmt=='csv':return [x[selector] for x in doc['rows']]
    if kind=='text' and fmt=='text':
        selector=text(selector,'field.selector')
        if len(selector)>256 or re.search(r'\\[1-9]|\(\?[=!<]|\([^)]*[+*][^)]*\)[+*{]',selector):raise E('text selector is not a bounded extraction pattern')
        m=re.search(selector,doc,re.MULTILINE)
        if not m:raise E('text field missing')
        return m.group(int(spec.get('group',1)))
    raise E('field extractor incompatible')
def raw_scalar(value,raw_kind,path,sink_role):
    if sink_role is None:raise E(path+' raw value requires a declared field role')
    if sink_role=='canonical':raise E(path+' raw value cannot fill a canonical field')
    if sink_role=='identifier':
        if raw_kind!='identifier' or not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,64}',value):raise E(path+' identifier field requires identifier lineage')
        return value
    if sink_role=='observation':
        if raw_kind not in {'numeric_observations','observation_table'}:raise E(path+' observation field requires observation lineage')
        if isinstance(value,str):return value
        if isinstance(value,bool) or not isinstance(value,(int,Decimal)):raise E(path+' observation scalar type is not allowed')
        return value
    if sink_role=='source_excerpt':
        if raw_kind!='source_excerpt' or not isinstance(value,str) or not value:raise E(path+' excerpt field requires source_excerpt lineage')
        return value
    raise E(path+' unknown field role '+str(sink_role))

def canonical_ref(v,canonicals,used):
    matches=[key for key in ('$claim','$final_use','$scenario_action') if key in v]
    if len(matches)!=1 or len(v)!=1:return None
    kind=matches[0][1:];item=text(v[matches[0]],matches[0]);key=(kind,item)
    if key not in canonicals:raise E('unknown canonical '+kind+' '+item)
    used.add(key);return copy.deepcopy(canonicals[key])

def refs(v,raw,raw_kinds,used,canonicals,used_canonicals,calculations=None,used_calculations=None,stack=(),sink_role=None,role_map=None):
    role_map=role_map or {}
    if isinstance(v,dict):
        canonical=canonical_ref(v,canonicals,used_canonicals)
        if canonical is not None:
            if sink_role!='canonical':raise E('canonical binding cannot fill a '+str(sink_role)+' field')
            return canonical
    if isinstance(v,dict) and set(v)=={'$ref'}:
        token=text(v['$ref'],'ref');iid,path=token.split('#',1)
        if iid not in raw:raise E('unknown raw input '+iid)
        used.add(iid);value=pointer(raw[iid],path)
        if isinstance(value,(dict,list)):raise E('composite raw reference cannot be copied as finished output')
        return raw_scalar(value,raw_kinds[iid],'raw input '+iid,sink_role)
    if isinstance(v,dict) and set(v)=={'$calc'}:
        if sink_role!='observation':raise E('calculation cannot fill a '+str(sink_role)+' field')
        cid=text(v['$calc'],'calc')
        if calculations is None or cid not in calculations:raise E('unknown calculation '+cid)
        if cid in stack:raise E('calculation cycle '+cid)
        used_calculations.add(cid);spec=calculations[cid];args=[refs(x,raw,raw_kinds,used,canonicals,used_canonicals,calculations,used_calculations,stack+(cid,),sink_role='observation',role_map=role_map) for x in arr(req(spec,'args','calculation'),'calculation.args')]
        if len(args)!=2:raise E('calculation '+cid+' requires two numbers')
        args=[number(x,'calculation '+cid+' argument') for x in args]
        op=choice(req(spec,'op','calculation'),{'add','subtract','multiply','divide'},'calculation.op')
        return compute(op,args[0],args[1],cid)
    if isinstance(v,dict):return {k:refs(x,raw,raw_kinds,used,canonicals,used_canonicals,calculations,used_calculations,stack,role_map.get(k),role_map) for k,x in v.items()}
    if isinstance(v,list):return [refs(x,raw,raw_kinds,used,canonicals,used_canonicals,calculations,used_calculations,stack,sink_role,role_map) for x in v]
    raise E('rebuild contains hardcoded scalar; move it to a raw input')

def raw_array_ref(v,raw,raw_kinds,used):
    if not isinstance(v,dict) or set(v)!={'$ref'}:raise E('CSV source must be one raw reference')
    token=text(v['$ref'],'ref');iid,path=token.split('#',1)
    if iid not in raw:raise E('unknown raw input '+iid)
    used.add(iid);value=pointer(raw[iid],path)
    if raw_kinds[iid]!='observation_table' or not isinstance(value,list):raise E('CSV source must resolve to an observation_table array')
    return value

def render_text_value(v):
    if isinstance(v,bool):return 'true' if v else 'false'
    if isinstance(v,Decimal):return decimal_token(v)
    return str(v)

def text_segment(v,raw,raw_kinds,used,canonicals,used_canonicals,calculations,used_calculations,allowed_literals,value_role):
    if isinstance(v,dict) and set(v)=={'literal'}:
        literal=text(v['literal'],'text literal')
        if literal not in allowed_literals:raise E('text literal not approved by expected artifact')
        punctuation=re.fullmatch(r'[\s:：,，;；\-()（）\[\]【】/]+',literal)
        label=re.fullmatch(r'[^\d\r\n.!?。！？]{1,20}[:：]',literal)
        if len(literal)>24 or not (punctuation or label):raise E('text literal must be short framing only')
        return literal
    if isinstance(v,dict) and set(v)=={'$ref'} and value_role=='canonical':
        raise E('raw text cannot be copied into a finished output')
    return render_text_value(refs(v,raw,raw_kinds,used,canonicals,used_canonicals,calculations,used_calculations,sink_role=value_role))

def volatile_pointers(spec,name):
    paths=strings(spec.get('volatile_json_pointers',[]),name+'.volatile_json_pointers',True)
    allowed={'generated_at','generated_at_utc','run_id','request_id','trace_id'}
    for path in paths:
        parts=path[1:].split('/') if path.startswith('/') else []
        leaf=parts[-1].replace('~1','/').replace('~0','~') if parts else ''
        if leaf not in allowed:raise E(name+' ignore pointer is not approved volatile metadata: '+path)
        for field_spec in spec.get('required_fields',[]):
            selector=field_spec.get('selector')
            if isinstance(selector,str) and (selector==path or selector.startswith(path+'/') or path.startswith(selector+'/')):raise E(name+' ignore pointer overlaps required field')
    return paths

def without_pointers(value,paths):
    parsed=[]
    for path in paths:
        path=text(path,'ignore_pointer')
        if not path.startswith('/') or path=='/':raise E('ignore pointer must be a non-root JSON pointer')
        raw_parts=path[1:].split('/');parts=[]
        for raw in raw_parts:
            if re.search(r'~(?:[^01]|$)',raw):raise E('ignore pointer has invalid escape: '+path)
            parts.append(raw.replace('~1','/').replace('~0','~'))
        parsed.append(tuple(parts))
    ignored=set(parsed)
    if len(ignored)!=len(parsed):raise E('duplicate ignore pointer')
    for path in ignored:
        if any(path[:i] in ignored for i in range(1,len(path))):raise E('overlapping ignore pointers')
        current=value
        for part in path:
            try:
                if isinstance(current,list):
                    if not re.fullmatch(r'0|[1-9][0-9]*',part):raise E('ignore pointer has non-canonical array index')
                    current=current[int(part)]
                elif isinstance(current,dict):current=current[part]
                else:raise E('ignore pointer traverses scalar')
            except (KeyError,IndexError):raise E('ignore pointer missing: /'+'/'.join(path)) from None
    marker=object()
    def prune(current,path=()):
        if path in ignored:return marker
        if isinstance(current,list):return [x for i,v in enumerate(current) if (x:=prune(v,path+(str(i),))) is not marker]
        if isinstance(current,dict):return {k:x for k,v in current.items() if (x:=prune(v,path+(k,))) is not marker}
        return copy.deepcopy(current)
    return prune(value)

def safe_target(root,name):
    current=root
    for part in PurePosixPath(name).parts[:-1]:
        current=current/part
        if current.is_symlink():raise E(name+' parent contains symlink')
        if current.exists() and not current.is_dir():raise E(name+' parent is not a directory')
    target=root/name
    if target.is_symlink():raise E(name+' target is symlink')
    return target

def reject_symlink_components(path,p):
    path=Path(os.path.abspath(path));current=Path(path.anchor)
    for part in path.parts[1:]:
        current=current/part
        try:mode=os.lstat(current).st_mode
        except FileNotFoundError:continue
        if stat.S_ISLNK(mode):raise E(p+' contains symlink: '+str(current))
        if current!=path and not stat.S_ISDIR(mode):raise E(p+' ancestor is not directory: '+str(current))
    return path

def path_conflicts(names):
    parts={name:PurePosixPath(name).parts for name in names}
    for left,a in parts.items():
        for right,b in parts.items():
            if left!=right and (a==b[:len(a)] or b==a[:len(b)]):return left,right
    return None

def mkdir_tracked(path,root,created):
    missing=[];current=path
    while current!=root and not current.exists():missing.append(current);current=current.parent
    if current.is_symlink() or (current.exists() and not current.is_dir()):raise E(str(path)+' parent is unsafe')
    for item in reversed(missing):item.mkdir();created.append(item)

def same_bytes(left,right):
    with left.open('rb') as a,right.open('rb') as b:
        while True:
            x=a.read(1024*1024);y=b.read(1024*1024)
            if x!=y:return False
            if not x:return True

def request_contract(v,p='request'):
    v=obj(v,p);query=text(req(v,'query',p),p+'.query')
    tier=choice(req(v,'analysis_tier',p),{'direct','brief','full'},p+'.analysis_tier')
    form=choice(req(v,'output_form',p),{'files'},p+'.output_form')
    return {'query':query,'analysis_tier':tier,'output_form':form}

def schema_field_roles(spec,name):
    fields=arr(spec.get('schema_fields',[]),name+'.schema_fields');names=[];roles={}
    for i,item in enumerate(fields):
        p=name+'.schema_fields['+str(i)+']'
        if isinstance(item,str):raise E(p+' must declare a role object')
        item=obj(item,p);field_name=text(req(item,'name',p),p+'.name')
        if field_name in roles:raise E(p+' duplicate schema field')
        roles[field_name]=choice(req(item,'role',p),ROLES,p+'.role');names.append(field_name)
    return names,roles

def load_receipt(path):
    receipt_file=reject_symlink_components(Path(path).expanduser(),'receipt')
    if not receipt_file.is_file():raise E('receipt file missing')
    value=obj(sm.load_json(receipt_file.read_text()),'receipt')
    if req(value,'version','receipt')!='sector-expectation-receipt-v1':raise E('unsupported receipt version')
    supplied=text(req(value,'receipt_digest','receipt'),'receipt.receipt_digest')
    payload={k:v for k,v in value.items() if k not in {'receipt_digest','frozen_at'}}
    if supplied!=digest(payload):raise E('receipt digest mismatch')
    text(req(value,'frozen_at','receipt'),'receipt.frozen_at')
    request=request_contract(req(value,'request','receipt'),'receipt.request')
    if text(req(value,'query_digest','receipt'),'receipt.query_digest')!=digest(request):raise E('query digest does not match receipt')
    if text(req(value,'producer','receipt'),'receipt.producer')!='sector-workflow --freeze-expectation':raise E('receipt producer mismatch')
    return value,request,receipt_file

def load_expectation(d,request,receipt_path):
    receipt,receipt_request,receipt_file=load_receipt(receipt_path)
    if not strict_equal(receipt_request,request):raise E('query digest does not match receipt')
    path=Path(text(req(receipt,'expectation_path','receipt'),'receipt.expectation_path')).expanduser()
    if not path.is_absolute():path=receipt_file.parent/path
    path=reject_symlink_components(path,'receipt.expectation_path')
    if 'expectation_path' in d:
        supplied=Path(text(d['expectation_path'],'delivery.expectation_path')).expanduser()
        if not supplied.is_absolute():supplied=receipt_file.parent/supplied
        supplied=reject_symlink_components(supplied,'delivery.expectation_path')
        if supplied!=path:raise E('delivery expectation_path does not match receipt')
    receipt_id=text(req(receipt,'expectation_id','receipt'),'receipt.expectation_id')
    if 'expectation_id' in d and text(d['expectation_id'],'delivery.expectation_id')!=receipt_id:raise E('delivery expectation_id does not match receipt')
    if not path.is_file():raise E('frozen expectation file missing')
    value=obj(sm.load_json(path.read_text()),'expectation')
    if req(value,'version','expectation')!='sector-expectation-v1':raise E('unsupported expectation version')
    expected_id=text(req(value,'expectation_id','expectation'),'expectation.expectation_id')
    payload={k:v for k,v in value.items() if k!='expectation_id'}
    if expected_id!=digest(payload) or expected_id!=receipt_id:raise E('frozen expectation ID mismatch')
    if not strict_equal(request_contract(req(value,'request','expectation'),'expectation.request'),request):raise E('frozen expectation request mismatch')
    return arr(req(value,'artifacts','expectation'),'expectation.artifacts'),expected_id

def freeze_expectation(source,target,receipt_target):
    source=obj(source,'expectation source');request=request_contract(req(source,'request','expectation source'),'expectation source.request');artifacts=arr(req(source,'artifacts','expectation source'),'expectation source.artifacts')
    if not artifacts:raise E('expectation artifacts must not be empty')
    payload={'version':'sector-expectation-v1','request':request,'artifacts':artifacts};value={**payload,'expectation_id':digest(payload)}
    target=Path(target).expanduser();receipt_target=Path(receipt_target).expanduser()
    reject_symlink_components(target,'expectation target');reject_symlink_components(receipt_target,'receipt target')
    if not target.parent.is_dir() or not receipt_target.parent.is_dir():raise E('expectation or receipt target parent missing')
    with target.open('x',encoding='utf-8') as handle:handle.write(dumps_typed(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    receipt_payload={'version':'sector-expectation-receipt-v1','query_digest':digest(request),'request':request,'expectation_id':value['expectation_id'],'expectation_path':str(target.resolve()),'producer':'sector-workflow --freeze-expectation'}
    receipt={**receipt_payload,'frozen_at':iso(datetime.now(timezone.utc)),'receipt_digest':digest(receipt_payload)}
    with receipt_target.open('x',encoding='utf-8') as handle:handle.write(dumps_typed(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return value,receipt

def schema_keys(value):
    out=set()
    if isinstance(value,dict):
        if set(value) in ({'$ref'},{'$calc'},{'$claim'},{'$final_use'},{'$scenario_action'}):return out
        for key,item in value.items():out.add(key);out.update(schema_keys(item))
    elif isinstance(value,list):
        for item in value:out.update(schema_keys(item))
    return out

def canonical_catalog(models,final_uses,scenario_rows):
    values={};required=set()
    for cid,model in models.items():
        values[('claim',cid)]=model['canonical']
        if model['decisive']:required.add(('claim',cid))
    for use in final_uses['uses']:
        key=('final_use',use['id']);values[key]=use['value'];required.add(key)
    for scenario in scenario_rows:
        key=('scenario_action',scenario['id']);values[key]=scenario['action'];required.add(key)
    return values,required

def artifact_bindings(spec,doc,fmt,canonicals,name):
    targets=set()
    for i,binding in enumerate(arr(spec.get('canonical_bindings',[]),name+'.canonical_bindings')):
        p=name+'.canonical_bindings['+str(i)+']';binding=obj(binding,p)
        target=obj(req(binding,'target',p),p+'.target');kind=choice(req(target,'type',p),{'claim','final_use','scenario_action'},p+'.target.type');item=text(req(target,'id',p),p+'.target.id');key=(kind,item)
        if key in targets or key not in canonicals:raise E(p+' duplicate or unknown canonical target')
        value=field(doc,fmt,obj(req(binding,'field',p),p+'.field'))
        if not strict_equal(value,canonicals[key]):raise E(name+' canonical binding differs in type or value')
        targets.add(key)
    return targets

def delivery(d,asof,request,models,final_uses,scenario_rows,receipt_path):
    d=obj(d,'delivery')
    expected_rows,expectation_id=load_expectation(d,request,receipt_path)
    raw_root=Path(text(req(d,'root','delivery'),'delivery.root')).expanduser();root=reject_symlink_components(raw_root,'delivery.root');manifest=rel(req(d,'manifest','delivery'),'delivery.manifest');overwrite=boolean(req(d,'overwrite','delivery'),'delivery.overwrite');expected={}
    for e in expected_rows:
        name=rel(req(e,'path','expected'),'expected.path')
        if name in expected:raise E('duplicate expectation '+name)
        expected[name]=e
    produced={}
    for p in arr(req(d,'produced_artifacts','delivery'),'delivery.produced_artifacts'):
        name=rel(req(p,'path','produced'),'produced.path')
        if name in produced:raise E('duplicate produced artifact '+name)
        fmt,data=render(p,'produced');produced[name]=(p,fmt,data)
    if not expected or set(expected)!=set(produced):raise E('expected and produced artifact sets differ')
    targets=list(expected)+[manifest]
    if manifest in expected:raise E('manifest path collides with artifact')
    conflict=path_conflicts(targets)
    if conflict:raise E('delivery target paths conflict: '+conflict[0]+' and '+conflict[1])
    if root.exists() and not root.is_dir():raise E('delivery root must be a real directory')
    if not root.parent.is_dir():raise E('delivery root parent missing')
    for name in targets:safe_target(root,name)
    canonicals,required_canonicals=canonical_catalog(models,final_uses,scenario_rows)
    workspace=Path(tempfile.mkdtemp(prefix='.sector-workflow-',dir=str(root.parent)));stage=workspace/'stage';backup=workspace/'backup';stage.mkdir();backup.mkdir();docs={};bound_canonicals=set()
    try:
        for name,(p,fmt,data) in produced.items():
            if fmt!=req(expected[name],'format','expected'):raise E(name+' format mismatch')
            if set(strings(req(expected[name],'sources','expected'),'sources',True))!=set(strings(req(p,'sources','produced'),'sources',True)) or set(strings(req(expected[name],'calculations','expected'),'calculations',True))!=set(strings(req(p,'calculations','produced'),'calculations',True)):raise E(name+' dependency mismatch')
            path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);docs[name]=(fmt,parse(fmt,path.read_bytes()));required=arr(req(expected[name],'required_fields','expected'),'required_fields')
            if not required:raise E(name+' required_fields must not be empty')
            for spec in required:
                value=field(docs[name][1],fmt,spec)
                if value is None or value=='':raise E(name+' required field empty')
                if 'expected' in spec and not strict_equal(value,spec['expected']):raise E(name+' required field differs in type or value')
            current_bindings=artifact_bindings(expected[name],docs[name][1],fmt,canonicals,name)
            if bound_canonicals.intersection(current_bindings):raise E(name+' repeats canonical binding from another artifact')
            bound_canonicals.update(current_bindings)
        if bound_canonicals!=required_canonicals:raise E('delivery canonical bindings are incomplete')
        repro=None
        if boolean(req(d,'reproduction_required','delivery'),'delivery.reproduction_required'):
            r=obj(req(d,'reproduction','delivery'),'delivery.reproduction');raw={};raw_kinds={}
            for i,x in enumerate(arr(req(r,'raw_inputs','reproduction'),'raw_inputs')):
                q='reproduction.raw_inputs['+str(i)+']';x=obj(x,q);iid=text(req(x,'id',q),q+'.id')
                if iid in raw:raise E('duplicate raw input '+iid)
                raw_kinds[iid]=choice(req(x,'kind',q),{'identifier','numeric_observations','observation_table','source_excerpt'},q+'.kind');raw[iid]=req(x,'content',q)
            calculations={}
            for i,x in enumerate(arr(r.get('calculations',[]),'reproduction.calculations')):
                q='reproduction.calculations['+str(i)+']';x=obj(x,q);cid=text(req(x,'id',q),q+'.id')
                if cid in calculations:raise E('duplicate calculation '+cid)
                calculations[cid]=x
            clean=workspace/'clean';clean.mkdir();built=set()
            for o in arr(req(r,'outputs','reproduction'),'outputs'):
                name=rel(req(o,'path','rebuild'),'rebuild.path')
                if name in built:raise E('duplicate reproduction output '+name)
                fmt=req(expected.get(name,{}),'format','expected');used=set();used_calculations=set();used_canonicals=set();kind=choice(req(o,'kind','rebuild'),{'json','text','csv'},'rebuild.kind');field_names,role_map=schema_field_roles(expected[name],name);approved_schema=set(field_names)
                if kind=='json' and fmt=='json':
                    template=req(o,'template','rebuild')
                    if schema_keys(template)!=approved_schema:raise E(name+' JSON keys differ from frozen schema fields')
                    data=(dumps_typed(refs(template,raw,raw_kinds,used,canonicals,used_canonicals,calculations,used_calculations,role_map=role_map),ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
                elif kind=='text' and fmt=='text':
                    if approved_schema:raise E(name+' text artifact cannot declare schema fields')
                    value_role=choice(expected[name].get('value_role','canonical'),ROLES,name+'.value_role')
                    allowed_literals=set(strings(expected[name].get('allowed_literals',[]),'expected.allowed_literals',True))
                    data=''.join(text_segment(x,raw,raw_kinds,used,canonicals,used_canonicals,calculations,used_calculations,allowed_literals,value_role) for x in arr(req(o,'segments','rebuild'),'segments')).encode()
                elif kind=='csv' and fmt=='csv':
                    rows=raw_array_ref(req(o,'source','rebuild'),raw,raw_kinds,used);cols=arr(req(o,'columns','rebuild'),'rebuild.columns');names=[]
                    for i,col in enumerate(cols):
                        q='rebuild.columns['+str(i)+']';col=obj(col,q);col_name=text(req(col,'name',q),q+'.name')
                        if col_name in names:raise E(q+' duplicate column')
                        names.append(col_name);role=choice(col.get('role',role_map.get(col_name)),ROLES,q+'.role')
                        if role_map.get(col_name)!=role:raise E(q+' column role differs from frozen schema')
                    if set(names)!=approved_schema or len(names)!=len(approved_schema):raise E(name+' CSV headers differ from frozen schema fields')
                    _,data=render({'format':'csv','content':{'columns':names,'rows':[{x['name']:raw_scalar(pointer(row,x['pointer']),'observation_table','CSV field',role_map[x['name']]) for x in cols} for row in rows]}},'rebuild')
                else:raise E('rebuild kind/format mismatch')
                if not used and not used_canonicals:raise E(name+' rebuild has no validated lineage')
                declared_sources=set(strings(req(expected[name],'sources','expected'),'expected.sources',True));produced_sources=set(strings(req(produced[name][0],'sources','produced'),'produced.sources',True));declared_calculations=set(strings(req(expected[name],'calculations','expected'),'expected.calculations',True));produced_calculations=set(strings(req(produced[name][0],'calculations','produced'),'produced.calculations',True))
                if used!=declared_sources or used!=produced_sources:raise E(name+' actual raw lineage differs from declared sources')
                if used_calculations!=declared_calculations or used_calculations!=produced_calculations:raise E(name+' actual calculations differ from declarations')
                declared_bindings={(x['target']['type'],x['target']['id']) for x in expected[name].get('canonical_bindings',[])}
                if used_canonicals!=declared_bindings:raise E(name+' actual canonical lineage differs from frozen bindings')
                path=clean/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);actual=produced[name][2]
                if fmt=='json':
                    a=parse(fmt,actual);b=parse(fmt,data);ignored=strings(o.get('ignore_pointers',[]),'ignore_pointers',True);approved=volatile_pointers(expected[name],name)
                    if ignored!=approved:raise E(name+' ignore pointers differ from expected approval')
                    if not strict_equal(without_pointers(a,ignored),without_pointers(b,ignored)):raise E(name+' rebuilt JSON differs')
                elif actual.decode().replace('\r\n','\n').strip()!=data.decode().replace('\r\n','\n').strip():raise E(name+' rebuilt content differs')
                built.add(name)
            if built!=set(expected):raise E('rebuild does not cover all expected artifacts')
            repro={'status':'structurally_reproduced','outputs':sorted(built),'raw_provenance_verified':False,'substantive_correctness_verified':False,'semantic_review_required':True}
        elif d.get('reproduction') is not None:raise E('reproduction supplied while reproduction_required is false')
        entries=[{'path':n,'bytes':len(produced[n][2]),'sha256':hashlib.sha256(produced[n][2]).hexdigest()} for n in expected];manifest_data={'version':'sector-delivery-manifest-v2','as_of':asof,'expectation_id':expectation_id,'files':entries,'reproduction':repro};(stage/manifest).parent.mkdir(parents=True,exist_ok=True);(stage/manifest).write_text(dumps_typed(manifest_data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        committed=[];created_dirs=[];root_created=not root.exists()
        if root_created:root.mkdir()
        reject_symlink_components(raw_root,'delivery.root')
        originals={}
        for name in targets:
            dst=safe_target(root,name)
            if dst.exists() and (not overwrite or not dst.is_file()):raise E(name+' exists and cannot be overwritten')
            if dst.exists():originals[name]=dst.read_bytes()
        for name in targets:
            dst=safe_target(root,name);mkdir_tracked(dst.parent,root,created_dirs);dst=safe_target(root,name);old=dst.exists()
            if old:
                saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);os.replace(dst,saved)
            committed.append((name,old));os.replace(stage/name,dst)
        for entry in entries:
            data=(root/entry['path']).read_bytes()
            if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise E('committed artifact changed')
        result={'manifest':manifest,'expectation_id':expectation_id,'files':entries,'reproduction':repro,'semantic_review_required':list(expected)}
    except Exception as original:
        errors=[]
        for name,old in reversed(locals().get('committed',[])):
            try:
                dst=root/name
                if old:
                    saved=backup/name
                    if dst.exists():dst.unlink()
                    shutil.copy2(saved,dst)
                    if not same_bytes(saved,dst) or dst.read_bytes()!=locals().get('originals',{}).get(name):raise E('restored bytes differ')
                elif dst.exists():dst.unlink()
            except Exception as x:errors.append(name+': '+str(x))
        for item in reversed(locals().get('created_dirs',[])):
            try:
                if item.exists():item.rmdir()
            except Exception as x:errors.append(str(item)+': '+str(x))
        if locals().get('root_created',False):
            try:
                if root.exists():root.rmdir()
            except Exception as x:errors.append(str(root)+': '+str(x))
        if errors:raise E('delivery failed: '+str(original)+'; rollback incomplete: '+' | '.join(errors)+'; retained '+str(workspace))
        shutil.rmtree(workspace);raise
    shutil.rmtree(workspace);return result

def process(doc,receipt_path=None):
    root=obj(doc,'input')
    if req(root,'version','input')!='sector-workflow-v2':raise E('unsupported workflow version')
    raw_as=req(root,'as_of','input');asof=sm.timestamp(raw_as,'input.as_of');cals=calendars(req(root,'calendars','input'));claim_result,models,evidence=claims(req(root,'claims','input'),asof,cals);metric=None;rolling=None
    if root.get('metrics') is not None:
        if sm.timestamp(req(root['metrics'],'as_of','metrics'),'metrics.as_of')!=asof:raise E('metrics.as_of mismatch')
        metric=sm.process(root['metrics'])
    if root.get('rolling_metrics') is not None:
        if sm.timestamp(req(root['rolling_metrics'],'as_of','rolling_metrics'),'rolling_metrics.as_of')!=asof:raise E('rolling_metrics.as_of mismatch')
        rolling=rm.process(root['rolling_metrics'])
    final_use_result=uses(req(root,'final_uses','input'),req(root,'final_uses_complete','input'),models)
    scenario_result=scenarios(req(root,'scenarios','input'),models,evidence,asof)
    request=None if root.get('delivery') is None else request_contract(req(root,'request','input'),'input.request')
    if root.get('delivery') is not None and not receipt_path:raise E('delivery requires --receipt')
    delivered=None if root.get('delivery') is None else delivery(root['delivery'],raw_as,request,models,final_use_result,scenario_result,receipt_path)
    return {'version':'sector-workflow-v2','claims':claim_result,'final_uses':final_use_result,'events':events(req(root,'events','input'),cals,asof),'metrics':metric,'rolling_metrics':rolling,'scenarios':scenario_result,'delivery':delivered,'semantic_review_required':['source truth and proposition support','complete decisive claims and final uses','scenario fit and reproduction semantics']}
def schema():return {'$schema':'https://json-schema.org/draft/2020-12/schema','title':'sector-workflow-v2','input_required':['version','as_of','claims','final_uses_complete','final_uses','calendars','events','scenarios'],'delivery_requires':['request.query','request.analysis_tier','request.output_form=files','CLI --receipt','sector-expectation-receipt-v1'],'expectation_contract':'sector-expectation-v1','receipt_contract':'sector-expectation-receipt-v1','field_roles':sorted(ROLES),'artifact_formats':['json','text','csv'],'claim_status':['supported','unverified','contradicted','conditional'],'scenario_state':['reinforcement','invalidation','missing_data'],'success_required':['version','claims','final_uses','events','metrics','rolling_metrics','scenarios','delivery','semantic_review_required'],'error_required':['error.code','error.message'],'nested_contract':'references/verification-workflow.md'}
def emit(v):sys.stdout.write(dumps_typed(v,ensure_ascii=False,separators=(',',':'))+'\n')
def main():
    try:
        args=sys.argv[1:]
        if args[:1]==['--freeze-expectation']:
            if len(args)!=4:raise E('usage: sector_workflow.py --freeze-expectation REQUEST.json EXPECTATION.json RECEIPT.json')
            value,receipt=freeze_expectation(sm.load_json(Path(args[1]).read_text()),args[2],args[3]);emit({'expectation_id':value['expectation_id'],'receipt_digest':receipt['receipt_digest'],'path':str(Path(args[2]).resolve()),'receipt_path':str(Path(args[3]).resolve())});return 0
        receipt_path=None;input_path=None;i=0
        while i<len(args):
            if args[i]=='--receipt':
                if i+1>=len(args):raise E('usage: sector_workflow.py --receipt RECEIPT.json INPUT.json')
                receipt_path=args[i+1];i+=2;continue
            if input_path is not None:raise E('usage: sector_workflow.py [--receipt RECEIPT.json] INPUT.json, -, or --schema')
            input_path=args[i];i+=1
        if input_path=='--schema':emit(schema());return 0
        if input_path is None:raise E('usage: sector_workflow.py [--receipt RECEIPT.json] INPUT.json, -, --schema, or --freeze-expectation REQUEST.json EXPECTATION.json RECEIPT.json')
        raw=sys.stdin.read() if input_path=='-' else Path(input_path).read_text();value=process(sm.load_json(raw),receipt_path)
    except E as x:emit({'error':{'code':'invalid_input','message':str(x) or 'invalid input'}});return 1
    except Exception as x:emit({'error':{'code':'processing_failed','message':str(x) or 'processing failed'}});return 1
    emit(value);return 0
if __name__=='__main__':sys.exit(main())
