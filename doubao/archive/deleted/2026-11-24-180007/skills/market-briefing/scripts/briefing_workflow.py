#!/usr/bin/env python3
import csv, datetime as dt, hashlib, io, json, math, os, re, shutil, sys
from pathlib import Path, PurePosixPath

SCHEMA='market-briefing-workflow-v1'; RID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
UOFFSET=re.compile(r'-00(?::?00(?::?00(?:[.,]\d+)?)?)?$')
STATES={'confirmed','unknown','disputed','superseded'}
POWER={'observation':0,'association':1,'hypothesis':2,'causal':3}
ESTRENGTH={'observation':'observation','association':'association','mechanism_hypothesis':'hypothesis','causal_conclusion':'causal'}
ELEVEL={'observation':0,'association':1,'mechanism_hypothesis':2,'causal_conclusion':3}
SLEVEL={'market_reaction':0,'participation':0,'implementation':1,'economic_transmission':3}
MCOLS=['value','operation','object','universe','unit','window','baseline','sample','source_id','source_sha256','sample_count','missing_count','observed_sum','numerator','denominator','start','end','gross_product']
NUMERIC_MCOLS={'value','sample_count','missing_count','observed_sum','numerator','denominator','start','end','gross_product'}

class WorkflowError(ValueError):
 def __init__(self,message,path='input',kind='validation_error'): super().__init__(message); self.message=message; self.path=path; self.kind=kind

def bad(message,path='input',kind='validation_error'): raise WorkflowError(message,path,kind)
def shape(v,req,opt,p):
 if type(v) is not dict: bad('must be an object',p)
 if req-set(v): bad('missing fields: '+repr(sorted(req-set(v))),p)
 if set(v)-req-opt: bad('unknown fields: '+repr(sorted(set(v)-req-opt)),p)
def txt(v,p):
 if type(v) is not str or not v or v!=v.strip(): bad('must be a non-empty trimmed string',p)
 return v
def ident(v,p):
 v=txt(v,p)
 if not RID.fullmatch(v): bad('invalid identifier',p)
 return v
def integer(v,p,n=0):
 if type(v) is not int or v<n: bad('must be an integer >= '+str(n),p)
 return v
def num(v,p):
 if type(v) not in (int,float): bad('must be a finite number, not a boolean',p)
 try: x=float(v)
 except (OverflowError,ValueError) as exc: raise WorkflowError('must be a finite number, not a boolean',p) from exc
 if not math.isfinite(x): bad('must be a finite number, not a boolean',p)
 return x
def finite(v,p):
 if v is None: return None
 if type(v) not in (int,float): bad('non-finite arithmetic value: expected an int or float, not a boolean or other type',p,'arithmetic_error')
 try: x=float(v)
 except (OverflowError,ValueError,TypeError) as exc: raise WorkflowError('non-finite arithmetic value cannot be converted to float',p,'arithmetic_error') from exc
 if not math.isfinite(x): bad('non-finite arithmetic value',p,'arithmetic_error')
 return x
def fsum(values,p):
 checked=[finite(v,p+'['+str(i)+']') for i,v in enumerate(values)]
 try: total=math.fsum(checked)
 except OverflowError as exc: raise WorkflowError('non-finite aggregate from math.fsum overflow',p,'arithmetic_error') from exc
 return finite(total,p)
def render_value(v,p):
 if v is None: return 'unknown'
 if type(v) is bool: bad('non-finite or boolean metric output value',p,'arithmetic_error')
 if type(v) is float: return format(finite(v,p),'.17g')
 if type(v) is int:
  finite(v,p)
  return str(v)
 if type(v) is str: return v
 bad('non-finite or unsupported metric output value',p,'arithmetic_error')
def reject_json_constant(value):
 raise WorkflowError('invalid JSON numeric constant: '+str(value),'manifest.json','malformed_json')
def arr(v,p,nonempty=False):
 if type(v) is not list or (nonempty and not v): bad('must be '+('a non-empty ' if nonempty else 'an ')+'array',p)
 return v
def strs(v,p,nonempty=False):
 out=[]
 for i,x in enumerate(arr(v,p,nonempty)):
  x=txt(x,p+'['+str(i)+']')
  if x in out: bad('duplicate value',p)
  out.append(x)
 return out
def idx(items,p):
 out={}
 for i,x in enumerate(arr(items,p)):
  if type(x) is not dict: bad('must be an object',p+'['+str(i)+']')
  k=ident(x.get('id'),p+'['+str(i)+'].id')
  if k in out: bad('duplicate id',p+'['+str(i)+'].id')
  out[k]=x
 return out
def ref(v,p):
 v=txt(v,p); a,s,b=v.rpartition('@')
 if not s or not b.isdigit(): bad('reference must use id@revision',p)
 return ident(a,p),integer(int(b),p,1)
def refs(v,p,nonempty=False):
 out=[ref(x,p) for x in strs(v,p,nonempty)]
 if len(out)!=len(set(out)): bad('duplicate reference',p)
 return out
def cur(items,r,p):
 if r[0] not in items or items[r[0]]['revision']!=r[1]: bad('missing or stale reference',p)
 return items[r[0]]
def stamp(v,p):
 v=txt(v,p)
 if v=='unknown': return None
 if UOFFSET.search(v): bad('unknown UTC offset',p)
 try: x=dt.datetime.fromisoformat(v[:-1]+'+00:00' if v.endswith(('Z','z')) else v)
 except ValueError as exc: raise WorkflowError('invalid ISO8601 timestamp',p) from exc
 if x.tzinfo is None or x.utcoffset() is None: bad('explicit UTC offset required',p)
 return x.astimezone(dt.timezone.utc)
def mkeys(m): return tuple(m['keys']+([m['order_by']] if m['operation']=='window_mean' else []))

def validate(doc):
 common={'schema_version','mode'}; optional={'as_of','evidence','metrics','conditions','claims','signals','uses','subjects','limits'}
 if doc.get('mode')=='build': shape(doc,common|{'requirements','build'},optional,'input')
 elif doc.get('mode')=='validate': shape(doc,common,optional,'input')
 else: bad('mode must be validate or build','mode')
 if doc['schema_version']!=SCHEMA: bad('unsupported schema_version','schema_version')
 names=['evidence','metrics','conditions','claims','signals','uses','subjects','limits']; C={n:idx(doc.get(n,[]),n) for n in names}
 E,M,Q,K,S,U,X=C['evidence'],C['metrics'],C['conditions'],C['claims'],C['signals'],C['uses'],C['subjects']
 astext=None; cutoff=None
 if 'as_of' in doc:
  astext=txt(doc['as_of'],'as_of'); cutoff=stamp(astext,'as_of')
  if cutoff is None: bad('as_of cannot be unknown','as_of','cutoff_error')
 if (K or U) and cutoff is None: bad('as_of is required for a claim or use task graph','as_of','cutoff_error')
 for i,e in enumerate(doc.get('evidence',[])):
  p='evidence['+str(i)+']'; shape(e,{'id','revision','source_id','locator','available_at','status','layer','max_strength'},set(),p); integer(e['revision'],p+'.revision',1); txt(e['source_id'],p+'.source_id'); txt(e['locator'],p+'.locator'); a=stamp(e['available_at'],p+'.available_at')
  if e['status'] not in STATES or (e['status']=='confirmed' and a is None): bad('invalid evidence state',p)
  if e['layer'] not in ESTRENGTH: bad('invalid evidence layer',p+'.layer')
  if e['max_strength']!=ESTRENGTH[e['layer']]: bad('max_strength must match evidence layer',p+'.max_strength')
  if cutoff is not None and a is not None and a>cutoff: bad('evidence available_at is after the as_of cutoff',p+'.available_at','cutoff_error')
 ops={'sum':{'field'},'count':set(),'mean':{'field'},'group_mean':{'field'},'ratio':{'numerator','denominator'},'return':{'start','end','output_scale'},'window_mean':{'field','order_by','order_by_type','window_rows'},'compound_return':{'field','input_scale','output_scale'}}
 base={'id','revision','source_id','operation','object','universe','unit','window','baseline','sample','keys'}
 for i,m in enumerate(doc.get('metrics',[])):
  p='metrics['+str(i)+']'; op=m.get('operation')
  if op not in ops: bad('unsupported operation',p+'.operation')
  shape(m,base|ops[op],{'field'} if op=='count' else set(),p); integer(m['revision'],p+'.revision',1); ident(m['source_id'],p+'.source_id'); m['keys']=strs(m['keys'],p+'.keys')
  for n in ('object','universe','unit','window','baseline','sample'): txt(m[n],p+'.'+n)
  for n in ('field','numerator','denominator','start','end','order_by'):
   if n in m: txt(m[n],p+'.'+n)
  if op=='group_mean' and not m['keys']: bad('group_mean requires keys',p)
  if op=='window_mean':
   integer(m['window_rows'],p+'.window_rows',1)
   if m['order_by_type'] not in {'number','timestamp','string'}: bad('order_by_type must be number, timestamp, or string',p+'.order_by_type')
  for n in ('input_scale','output_scale'):
   if n in m and m[n] not in {'decimal','percent'}: bad('invalid scale',p+'.'+n)
 qdata={}
 for i,q in enumerate(doc.get('conditions',[])):
  p='conditions['+str(i)+']'; shape(q,{'id','revision','logic','predicates'},set(),p); integer(q['revision'],p+'.revision',1)
  if q['logic'] not in {'all','any'}: bad('logic must be all or any',p)
  ps=[]; shapes=set(); seen=set()
  for j,z in enumerate(arr(q['predicates'],p+'.predicates',True)):
   zp=p+'.predicates['+str(j)+']'; shape(z,{'id','metric','operator','value','unit'},set(),zp); zid=ident(z['id'],zp+'.id')
   if zid in seen: bad('duplicate predicate id',zp+'.id')
   seen.add(zid); mr=ref(z['metric'],zp+'.metric'); m=cur(M,mr,zp)
   if z['operator'] not in {'gt','ge','lt','le','eq','ne'} or z['unit']!=m['unit']: bad('invalid operator or unit',zp)
   num(z['value'],zp+'.value'); ps.append((z,mr)); shapes.add(mkeys(m))
  if len(shapes)!=1: bad('condition metrics need identical keys',p)
  qdata[q['id']]={'predicates':ps,'keys':next(iter(shapes))}
 kdata={}
 for i,k in enumerate(doc.get('claims',[])):
  p='claims['+str(i)+']'; shape(k,{'id','revision','proposition','target','scope','horizon','view','premises','state','evidence','support','falsify','alternatives','on_support','on_falsify'},set(),p); integer(k['revision'],p+'.revision',1)
  for n in ('proposition','target','scope','on_support','on_falsify'): txt(k[n],p+'.'+n)
  if k['horizon'] not in {'intraday','multi_day','multi_week','quarter','unknown'} or k['view'] not in {'positive','negative','neutral','mixed'} or k['state'] not in {'supported','falsified','mixed','unknown'}: bad('invalid claim classification',p)
  strs(k['premises'],p+'.premises',True); strs(k['alternatives'],p+'.alternatives',True); ev=refs(k['evidence'],p+'.evidence',True)
  for r in ev: cur(E,r,p+'.evidence')
  kdata[k['id']]={'evidence':ev,'support':refs(k['support'],p+'.support',True),'falsify':refs(k['falsify'],p+'.falsify',True)}
 sdata={}
 for i,s in enumerate(doc.get('signals',[])):
  p='signals['+str(i)+']'; shape(s,{'id','revision','claim','condition','key','direction','polarity','layer','adjudication'},set(),p); integer(s['revision'],p+'.revision',1); kr=ref(s['claim'],p+'.claim'); qr=ref(s['condition'],p+'.condition'); cur(K,kr,p); q=cur(Q,qr,p)
  if type(s['key']) is not dict or set(s['key'])!=set(qdata[q['id']]['keys']): bad('key must match condition keys',p+'.key')
  for n,v in s['key'].items(): txt(v,p+'.key.'+n)
  if s['direction'] not in {'support','falsify'} or s['polarity'] not in {'favorable','adverse','neutral','mixed','not_applicable'} or s['layer'] not in SLEVEL: bad('invalid signal classification',p)
  txt(s['adjudication'],p+'.adjudication'); sdata[s['id']]={'claim':kr,'condition':qr}
 for kid,k in K.items():
  a,b=set(kdata[kid]['support']),set(kdata[kid]['falsify'])
  if a&b: bad('signal cannot support and falsify','claims.'+kid)
  levels=[ELEVEL[cur(E,r,'claims.'+kid)['layer']] for r in kdata[kid]['evidence'] if cur(E,r,'claims.'+kid)['status']!='superseded']; high=max(levels,default=-1); seen=set()
  for r in sorted(a|b):
   s=cur(S,r,'claims.'+kid); direction='support' if r in a else 'falsify'
   if sdata[s['id']]['claim']!=(kid,k['revision']) or s['direction']!=direction: bad('signal claim or direction mismatch','claims.'+kid)
   marker=(s['condition'],tuple(sorted(s['key'].items()))); opposite='falsify' if direction=='support' else 'support'
   if (marker,opposite) in seen: bad('opposite roles for one condition/key','claims.'+kid)
   seen.add((marker,direction))
   if high<SLEVEL[s['layer']]: bad('claim evidence is insufficient for signal layer '+s['layer'],'claims.'+kid+'.evidence')
 reports=[]
 for i,x in enumerate(doc.get('subjects',[])):
  p='subjects['+str(i)+']'
  if x.get('kind')=='text': shape(x,{'id','kind','content'},set(),p); raw=x['content'].encode('utf-8') if type(x['content']) is str else bad('content must be string',p)
  elif x.get('kind')=='items': shape(x,{'id','kind','items'},set(),p); raw=json.dumps(arr(x['items'],p+'.items'),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
  else: bad('kind must be text or items',p)
  reports.append({'id':x['id'],'kind':x['kind'],'sha256':hashlib.sha256(raw).hexdigest()})
 for i,u in enumerate(doc.get('uses',[])):
  p='uses['+str(i)+']'; shape(u,{'id','claim','state','strength','evidence','signals','metrics','conditions','subject','fragment'},set(),p); kr=ref(u['claim'],p+'.claim'); k=cur(K,kr,p)
  if u['state']!=k['state'] or u['strength'] not in POWER: bad('use state or strength mismatch',p)
  ev=set(refs(u['evidence'],p+'.evidence',True)); sr=set(refs(u['signals'],p+'.signals',True))
  if ev!=set(kdata[k['id']]['evidence']) or not sr<=(set(kdata[k['id']]['support'])|set(kdata[k['id']]['falsify'])): bad('use evidence or signals mismatch',p)
  qr={sdata[cur(S,r,p)['id']]['condition'] for r in sr}; supplied=set(refs(u['conditions'],p+'.conditions',True))
  if qr!=supplied: bad('use conditions mismatch',p)
  mr=set()
  for r in qr:
   for _,mref in qdata[cur(Q,r,p)['id']]['predicates']: mr.add(mref)
  if mr!=set(refs(u['metrics'],p+'.metrics')): bad('use metrics mismatch',p)
  if POWER[u['strength']]>min(POWER[cur(E,r,p)['max_strength']] for r in ev): bad('use exceeds evidence strength',p)
  for r in ev:
   state=cur(E,r,p)['status']
   if state=='superseded' or (u['state'] in {'supported','falsified'} and state!='confirmed'): bad('unusable evidence state',p)
  subject=ident(u['subject'],p+'.subject'); fragment=txt(u['fragment'],p+'.fragment')
  if subject not in X or X[subject]['kind']!='text' or fragment not in X[subject]['content']: bad('fragment absent from actual text',p)
 counts=[]
 for i,l in enumerate(doc.get('limits',[])):
  p='limits['+str(i)+']'; shape(l,{'id','subject','measure'},{'exact','minimum','maximum'},p); x=X.get(ident(l['subject'],p+'.subject'))
  if x is None: bad('missing subject',p)
  m=l['measure']; actual=len(x['content']) if m=='characters' and x['kind']=='text' else len(x['content'].encode('utf-8')) if m=='utf8_bytes' and x['kind']=='text' else len(x['content'].split()) if m=='whitespace_words' and x['kind']=='text' else len(x['items']) if m=='items' and x['kind']=='items' else bad('incompatible measure',p)
  exact=integer(l['exact'],p+'.exact') if 'exact' in l else None; low=integer(l['minimum'],p+'.minimum') if 'minimum' in l else None; highlim=integer(l['maximum'],p+'.maximum') if 'maximum' in l else None
  if exact is None and low is None and highlim is None: bad('limit needs exact/minimum/maximum',p)
  if low is not None and highlim is not None and low>highlim: bad('minimum cannot exceed maximum',p)
  if (exact is not None and actual!=exact) or (low is not None and actual<low) or (highlim is not None and actual>highlim): bad('actual count violates limit: '+str(actual),p)
  counts.append({'id':l['id'],'subject':l['subject'],'measure':m,'actual':actual})
 return {'C':C,'qdata':qdata,'kdata':kdata,'sdata':sdata,'reports':reports,'counts':counts,'as_of':astext}

def safe(v,p):
 v=txt(v,p)
 if v.startswith('/') or '\\' in v or any(x in {'','.','..'} for x in v.split('/')): bad('unsafe relative path',p)
 q=PurePosixPath(v)
 if q.suffix.lower()!='.csv': bad('path must end in .csv',p)
 return q
def inside(a,b):
 try: a.relative_to(b); return True
 except ValueError: return False
def read_source(root,s,p):
 q=safe(s['path'],p+'.path')
 try:
  target=root
  for part in q.parts:
   target/=part
   if target.is_symlink(): bad('symlink source path',p,'input_error')
  if not target.is_file(): bad('missing or unreadable source',p,'input_error')
  raw=target.read_bytes()
 except WorkflowError: raise
 except OSError as exc: raise WorkflowError('raw source read failed: '+str(exc),p,'input_error') from exc
 try: decoded=raw.decode('utf-8')
 except UnicodeError as exc: raise WorkflowError('raw source is not valid UTF-8: '+str(exc),p,'input_error') from exc
 try: rows=list(csv.reader(io.StringIO(decoded,newline=''),delimiter=s['delimiter'],strict=True))
 except (csv.Error,TypeError) as exc: raise WorkflowError('raw CSV parsing failed: '+str(exc),p,'input_error') from exc
 if not rows: bad('CSV has no header',p,'input_error')
 header=rows[0]
 if len(header)!=len(set(header)) or any(not x or x!=x.strip() for x in header): bad('invalid CSV header',p,'input_error')
 if not set(s['required_columns'])<=set(header): bad('missing required columns',p,'input_error')
 out=[]
 for n,row in enumerate(rows[1:],2):
  if len(row)!=len(header): bad('CSV width mismatch',p+':row:'+str(n),'input_error')
  out.append((n,dict(zip(header,row))))
 return {'id':s['id'],'path':s['path'],'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'header':header,'rows':out}
def cell(row,name,p):
 v=row[name].strip()
 if not v: return None
 try: v=float(v)
 except ValueError as exc: raise WorkflowError('non-numeric cell',p) from exc
 if not math.isfinite(v): bad('non-finite cell',p)
 return v
def orderval(v,t,p):
 v=txt(v,p)
 if t=='string': return v
 if t=='number':
  try: x=float(v)
  except ValueError as exc: raise WorkflowError('non-numeric window order value',p) from exc
  if not math.isfinite(x): bad('non-finite window order value',p)
  return x
 if t=='timestamp':
  x=stamp(v,p)
  if x is None: bad('window timestamp cannot be unknown',p)
  return x
 bad('invalid window order type',p)
def groups(src,keys):
 out={}
 for n,row in src['rows']:
  k=tuple(row[x] for x in keys)
  if any(not x or x!=x.strip() for x in k): bad('invalid group key','source.'+src['id']+':'+str(n))
  out.setdefault(k,[]).append((n,row))
 if not keys and not out: out[()]=[]
 return out
def vals(entries,name,src):
 out=[]; missing=0
 for n,row in entries:
  v=cell(row,name,'source.'+src['id']+':'+str(n)+':'+name)
  if v is None: missing+=1
  else: out.append(v)
 return out,missing
def rec(m,s,value,n,missing,**extra):
 p='metrics.'+m['id']; value=finite(value,p+'.value'); extra=dict(extra)
 for name in ('observed_sum','numerator','denominator','start','end','gross_product'):
  if name in extra: extra[name]=finite(extra[name],p+'.'+name)
 out={x:None for x in MCOLS}; out.update({'value':value,'operation':m['operation'],'object':m['object'],'universe':m['universe'],'unit':m['unit'],'window':m['window'],'baseline':m['baseline'],'sample':m['sample'],'source_id':s['id'],'source_sha256':s['sha256'],'sample_count':n,'missing_count':missing}); out.update(extra); return out
def compute(m,s):
 out={}; op=m['operation']; mp='metrics.'+m['id']
 if op=='window_mean':
  for base,entries in groups(s,m['keys']).items():
   ordered=[]; seen=set()
   for n,row in entries:
    raw=txt(row[m['order_by']],'source.'+s['id']+':'+str(n)+':'+m['order_by']); parsed=orderval(raw,m['order_by_type'],'source.'+s['id']+':'+str(n)+':'+m['order_by'])
    if parsed in seen: bad('duplicate window order value within group','source.'+s['id']+':'+str(n)+':'+m['order_by'])
    seen.add(parsed); ordered.append((parsed,n,row,raw))
   ordered.sort(key=lambda z:z[0])
   for pos,(_,n,row,raw) in enumerate(ordered):
    selected=[(rn,rr) for _,rn,rr,_ in ordered[max(0,pos-m['window_rows']+1):pos+1]]; found,missing=vals(selected,m['field'],s); total=fsum(found,mp+'.window_mean.observed_sum') if found else None
    value=None if not selected or missing else finite(total/len(selected),mp+'.window_mean.value')
    out[base+(raw,)]=rec(m,s,value,len(selected),missing,observed_sum=total)
  return {'keys':mkeys(m),'rows':out}
 for key,entries in groups(s,m['keys']).items():
  n=len(entries)
  if op=='count': found,missing=vals(entries,m['field'],s) if 'field' in m else (entries,0); item=rec(m,s,len(found),n,missing)
  elif op in {'sum','mean','group_mean'}:
   found,missing=vals(entries,m['field'],s); total=fsum(found,mp+'.observed_sum') if found else None
   value=None if not n or missing else total if op=='sum' else finite(total/n,mp+'.'+op+'.value'); item=rec(m,s,value,n,missing,observed_sum=total)
  elif op=='ratio':
   a,ma=vals(entries,m['numerator'],s); b,mb=vals(entries,m['denominator'],s); A=fsum(a,mp+'.ratio.numerator') if a else None; B=fsum(b,mp+'.ratio.denominator') if b else None
   value=None if not n or ma+mb or B in {None,0} else finite(A/B,mp+'.ratio non-finite result'); item=rec(m,s,value,n,ma+mb,numerator=A,denominator=B)
  elif op=='return':
   if n>1: bad('return permits at most one row per group',mp)
   A=cell(entries[0][1],m['start'],mp) if n else None; B=cell(entries[0][1],m['end'],mp) if n else None; missing=int(A is None)+int(B is None); value=None
   if n and not missing and A!=0:
    quotient=finite(B/A,mp+'.return non-finite ratio'); value=finite(quotient-1,mp+'.return non-finite result')
    if m['output_scale']=='percent': value=finite(value*100,mp+'.return non-finite percentage scaling')
   item=rec(m,s,value,n,missing,start=A,end=B)
  else:
   found,missing=vals(entries,m['field'],s); gross=None
   if found:
    gross=finite(1,mp+'.compound initial gross_product')
    for pos,v in enumerate(found):
     scaled=finite(v/100 if m['input_scale']=='percent' else v,mp+'.compound non-finite input['+str(pos)+']'); factor=finite(1+scaled,mp+'.compound non-finite factor['+str(pos)+']'); gross=finite(gross*factor,mp+'.compound non-finite multiplication['+str(pos)+']')
   value=None if not n or missing or gross is None else finite(gross-1,mp+'.compound non-finite result')
   if value is not None and m['output_scale']=='percent': value=finite(value*100,mp+'.compound non-finite percentage scaling')
   item=rec(m,s,value,n,missing,gross_product=gross)
  out[key]=item
 return {'keys':mkeys(m),'rows':out}
def compare(a,op,b):
 if a is None or b is None: return 'unknown'
 left=finite(a,'compare.left non-finite operand'); right=finite(b,'compare.right non-finite operand')
 result={'gt':left>right,'ge':left>=right,'lt':left<right,'le':left<=right,'eq':left==right,'ne':left!=right}[op]
 return 'true' if result else 'false'
def evaluate(ctx,mr):
 out={}
 for qid,q in ctx['C']['conditions'].items():
  data=ctx['qdata'][qid]; keys=set()
  for _,mref in data['predicates']: keys.update(mr[mref[0]]['rows'])
  rows={}
  for key in keys:
   states=[compare(mr[mref[0]]['rows'].get(key,{}).get('value'),z['operator'],z['value']) for z,mref in data['predicates']]
   if any(x not in {'true','false','unknown'} for x in states): bad('condition result must be true, false, or unknown','conditions.'+qid,'arithmetic_error')
   result=('false' if 'false' in states else 'true' if all(x=='true' for x in states) else 'unknown') if q['logic']=='all' else ('true' if 'true' in states else 'false' if all(x=='false' for x in states) else 'unknown')
   if result not in {'true','false','unknown'}: bad('condition result must be true, false, or unknown','conditions.'+qid,'arithmetic_error')
   rows[key]=result
  out[qid]={'keys':data['keys'],'rows':rows}
 return out
def reopened_number(v,p):
 if v=='unknown': return None
 if v in {'Infinity','-Infinity','NaN'}: bad('non-finite reopened numeric token: '+v,p,'build_error')
 try: x=float(v)
 except (ValueError,OverflowError) as exc: raise WorkflowError('non-finite reopened or non-numeric metric value',p,'build_error') from exc
 if not math.isfinite(x): bad('non-finite reopened metric value',p,'build_error')
 return x
def status(coverage): return {'deterministic':{'status':'passed','coverage':coverage},'semantic_review':{'status':'not-run','coverage':[]},'source_truth':{'status':'not-run','coverage':[]}}
def graphcov(ctx):
 out=['reference-integrity','canonical-metrics-and-conditions','evidence-layer-strength','signal-layer-evidence']
 if ctx['as_of'] is not None: out.append('evidence-cutoff')
 if any(m['operation']=='window_mean' for m in ctx['C']['metrics'].values()): out.append('typed-window-order')
 return out

def build(doc,ctx):
 b=doc['build']; shape(b,{'input_root','output_root','sources','tables'},set(),'build'); inp=Path(txt(b['input_root'],'build.input_root')); out=Path(txt(b['output_root'],'build.output_root'))
 try:
  invalid=not inp.is_absolute() or not out.is_absolute() or inp.is_symlink() or not inp.is_dir() or out.exists() or out.parent.is_symlink() or not out.parent.is_dir()
  inp=inp.resolve(); guess=out.parent.resolve()/out.name
 except OSError as exc: raise WorkflowError('input/output root inspection failed: '+str(exc),'build','input_error') from exc
 if invalid: bad('invalid input/output roots','build','input_error')
 if inside(guess,inp) or inside(inp,guess): bad('input/output roots overlap','build')
 specs=idx(b['sources'],'build.sources'); reqs=idx(doc['requirements'],'requirements'); idx(b['tables'],'build.tables'); sources={}
 for i,r in enumerate(doc['requirements']):
  p='requirements['+str(i)+']'; shape(r,{'id','path','fields'},set(),p); safe(r['path'],p+'.path'); r['fields']=strs(r['fields'],p+'.fields',True)
 for i,s in enumerate(b['sources']):
  p='build.sources['+str(i)+']'; shape(s,{'id','path','role','encoding','delimiter','required_columns'},set(),p); safe(s['path'],p); s['required_columns']=strs(s['required_columns'],p+'.required_columns',True)
  if s['role']!='raw' or s['encoding']!='utf-8' or type(s['delimiter']) is not str or len(s['delimiter'])!=1 or s['delimiter'] in {'\r','\n','\x00'}: bad('invalid source declaration',p)
  sources[s['id']]=read_source(inp,s,p)
 M=ctx['C']['metrics']
 for mid,m in M.items():
  if m['source_id'] not in specs: bad('undeclared metric source','metrics.'+mid)
  fields=set(m['keys'])|{m[x] for x in ('field','numerator','denominator','start','end','order_by') if x in m}
  if not fields<=set(specs[m['source_id']]['required_columns']) or not fields<=set(sources[m['source_id']]['header']): bad('metric fields absent from declared raw source','metrics.'+mid)
 mr={mid:compute(m,sources[m['source_id']]) for mid,m in M.items()}; qr=evaluate(ctx,mr); prepared=[]; used=set()
 for i,t in enumerate(b['tables']):
  p='build.tables['+str(i)+']'; shape(t,{'id','requirement','path','metrics','conditions'},set(),p); path=safe(t['path'],p); rid=ident(t['requirement'],p+'.requirement')
  if path.stem!=t['id'] or rid not in reqs or rid in used: bad('invalid table/requirement binding',p)
  used.add(rid); r=reqs[rid]
  if r['path']!=t['path']: bad('table and requirement paths differ',p)
  mrefs=refs(t['metrics'],p+'.metrics'); qrefs=refs(t['conditions'],p+'.conditions'); shapes=[]
  for x in mrefs: shapes.append(mkeys(cur(M,x,p)))
  for x in qrefs: shapes.append(ctx['qdata'][cur(ctx['C']['conditions'],x,p)['id']]['keys'])
  if not shapes or len(set(shapes))!=1: bad('table dependencies need identical keys',p)
  header=list(shapes[0]); numeric_columns=[]
  for x in mrefs:
   for c in MCOLS:
    name=x[0]+'__'+c; header.append(name)
    if c in NUMERIC_MCOLS: numeric_columns.append(name)
  for x in qrefs: header += [x[0]+'__result',x[0]+'__logic',x[0]+'__predicate_ids']
  if header!=r['fields']: bad('requirement fields differ from canonical header','requirements.'+rid)
  keys=set(); deps={x[0] for x in mrefs}
  for x in mrefs: keys.update(mr[x[0]]['rows'])
  for x in qrefs:
   keys.update(qr[x[0]]['rows']); deps.update(y[1][0] for y in ctx['qdata'][x[0]]['predicates'])
  types={M[x]['order_by_type'] for x in deps if M[x]['operation']=='window_mean'}
  if len(types)>1: bad('table window dependencies use conflicting order_by_type',p)
  otype=next(iter(types),None); ordered=sorted(keys,key=lambda k:tuple(k) if otype is None else tuple(k[:-1])+(orderval(k[-1],otype,p+'.order_by'),))
  buf=io.StringIO(newline=''); w=csv.writer(buf,lineterminator='\n'); w.writerow(header)
  for row_number,key in enumerate(ordered,2):
   row=list(key)
   for x in mrefs:
    item=mr[x[0]]['rows'].get(key,{})
    for c in MCOLS: row.append(render_value(item.get(c),p+':row:'+str(row_number)+':'+x[0]+'__'+c))
   for x in qrefs:
    q=ctx['C']['conditions'][x[0]]; result=qr[x[0]]['rows'].get(key,'unknown')
    if result not in {'true','false','unknown'}: bad('condition result must be true, false, or unknown',p+':row:'+str(row_number),'arithmetic_error')
    row += [result,q['logic'],json.dumps([z['id'] for z,_ in ctx['qdata'][x[0]]['predicates']],separators=(',',':'))]
   w.writerow(row)
  prepared.append({'requirement':rid,'table':t['id'],'path':t['path'],'data':buf.getvalue().encode('utf-8'),'header':header,'numeric_columns':numeric_columns,'rows':len(ordered),'dependencies':{'metric_ids':sorted(deps),'condition_ids':sorted(x[0] for x in qrefs),'source_ids':sorted({M[x]['source_id'] for x in deps})}})
 if used!=set(reqs) or {x['path'] for x in prepared}!={x['path'] for x in doc['requirements']}: bad('requirements and tables are not one-to-one','build.tables')
 created=False
 try:
  os.mkdir(out,0o700); created=True
  for item in prepared:
   q=safe(item['path'],item['path']); parent=out
   for part in q.parent.parts: parent/=part; parent.mkdir(mode=0o700,exist_ok=True)
   target=out.joinpath(*q.parts); fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(fd,'wb') as f: f.write(item['data'])
  reopened=[]
  for item in prepared:
   target=out.joinpath(*safe(item['path'],item['path']).parts)
   if target.is_symlink() or not target.is_file(): bad('missing or symlink output',item['path'],'build_error')
   raw=target.read_bytes(); rows=list(csv.reader(io.StringIO(raw.decode('utf-8'),newline=''),strict=True))
   if not rows or rows[0]!=item['header'] or len(rows)-1!=item['rows']: bad('reopened output mismatch',item['path'],'build_error')
   positions={name:i for i,name in enumerate(rows[0])}
   for row_number,row in enumerate(rows[1:],2):
    if len(row)!=len(rows[0]): bad('reopened output width mismatch',item['path']+':row:'+str(row_number),'build_error')
    for name in item['numeric_columns']: reopened_number(row[positions[name]],item['path']+':row:'+str(row_number)+':'+name)
   reopened.append({'requirement_id':item['requirement'],'table_id':item['table'],'path':item['path'],'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'header':rows[0],'row_count':len(rows)-1,'dependencies':item['dependencies']})
  val=status(graphcov(ctx)+['raw-csv-arithmetic','requirements-binding','exclusive-write','reopened-bytes','manifest-from-reopened-outputs'])
  manifest={'schema_version':SCHEMA,'sources':[{'id':x['id'],'path':x['path'],'sha256':x['sha256'],'size':x['size'],'header':x['header'],'row_count':len(x['rows'])} for x in sources.values()],'outputs':reopened,'subjects':ctx['reports'],'counts':ctx['counts'],'validation':val}
  if ctx['as_of'] is not None: manifest['as_of']=ctx['as_of']
  raw=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8'); mp=out/'manifest.json'; fd=os.open(mp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f: f.write(raw)
  checked=mp.read_bytes(); parsed=json.loads(checked.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject_json_constant)
  if parsed!=manifest: bad('reopened manifest mismatch','manifest.json','build_error')
  return {'output_root':str(out),'outputs':reopened,'manifest':{'path':'manifest.json','sha256':hashlib.sha256(checked).hexdigest(),'size':len(checked)},'validation':val}
 except Exception as exc:
  if created: shutil.rmtree(out,ignore_errors=True)
  if isinstance(exc,WorkflowError): raise
  raise WorkflowError(str(exc),'build','build_error') from exc

def process(doc):
 if type(doc) is not dict: bad('top-level JSON must be an object')
 ctx=validate(doc); result={'ok':True,'schema_version':SCHEMA,'mode':doc['mode'],'subjects':ctx['reports'],'counts':ctx['counts']}
 if ctx['as_of'] is not None: result['as_of']=ctx['as_of']
 result.update(build(doc,ctx) if doc['mode']=='build' else {'validation':status(graphcov(ctx)+['actual-subject-hashes']+(['actual-counts'] if ctx['counts'] else []))})
 return result
def pairs(items):
 out={}
 for k,v in items:
  if k in out: raise WorkflowError('duplicate JSON key: '+repr(k),'input','malformed_json')
  out[k]=v
 return out
def write(v): sys.stdout.write(json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
def error(e): return {'ok':False,'error':{'type':e.kind,'message':e.message,'path':e.path},'validation':{'deterministic':{'status':'failed','coverage':[e.path]},'semantic_review':{'status':'not-run','coverage':[]},'source_truth':{'status':'not-run','coverage':[]}}}
def main():
 if len(sys.argv)!=2: write(error(WorkflowError('usage: python3 scripts/briefing_workflow.py INPUT.json (or -)','argv','usage_error'))); return 2
 try: raw=sys.stdin.read() if sys.argv[1]=='-' else Path(sys.argv[1]).read_text(encoding='utf-8')
 except (OSError,UnicodeError) as exc: write(error(WorkflowError(str(exc),'input','input_error'))); return 2
 try: result=process(json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:bad('invalid numeric constant','input','malformed_json')))
 except json.JSONDecodeError as exc: write(error(WorkflowError(exc.msg+' at line '+str(exc.lineno),'input','malformed_json'))); return 2
 except WorkflowError as exc: write(error(exc)); return 2
 except (OSError,UnicodeError,csv.Error) as exc: write(error(WorkflowError(str(exc),'input','input_error'))); return 2
 except Exception as exc: write(error(WorkflowError(str(exc),'input','internal_error'))); return 2
 write(result); return 0
if __name__=='__main__': raise SystemExit(main())
