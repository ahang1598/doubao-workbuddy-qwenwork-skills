"""Offline structured calculations for industry analysis; JSON in/out."""
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from pathlib import Path

ID = re.compile(r'^[A-Za-z0-9_-]+$')
TS = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$')
ORDER = {'conflict': 0, 'incompatible': 1, 'missing': 2, 'infeasible': 3}


class OutOfRangeNumericLexeme:
    """A finite JSON number retained until fact-level conflict propagation."""

    def __init__(self, lexeme, reason):
        self.lexeme = lexeme
        self.reason = reason


def parse_integer(lexeme):
    digits = lexeme[1:] if lexeme.startswith('-') else lexeme
    limit = sys.get_int_max_str_digits() if hasattr(sys, 'get_int_max_str_digits') else 0
    if limit and len(digits) > limit:
        return OutOfRangeNumericLexeme(lexeme, 'integer exceeds numeric lexical conversion limit')
    return int(lexeme)


def parse_decimal(lexeme):
    try:
        decimal_value = Decimal(lexeme)
        value = float(decimal_value)
    except (InvalidOperation, OverflowError, ValueError):
        return OutOfRangeNumericLexeme(lexeme, 'decimal number is outside supported numeric range')
    if not math.isfinite(value) or (value == 0.0 and decimal_value != 0):
        return OutOfRangeNumericLexeme(lexeme, 'decimal number is outside supported numeric range')
    return value

class Bad(ValueError):
    pass

def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Bad('Duplicate JSON key: ' + key)
        out[key] = value
    return out

def constant(value):
    raise Bad('Nonfinite JSON constant: ' + value)

def exact(value, fields, where):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise Bad(where + ' must contain exactly: ' + ', '.join(sorted(fields)))

def text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise Bad(where + ' must be nonempty text')
    return value

def ident(value, where):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise Bad(where + ' has an invalid identifier')
    return value

def time(value, where, nullable=True):
    if value is None:
        if nullable:
            return None
        raise Bad(where + ' requires an offset timestamp')
    if not isinstance(value, str) or not TS.fullmatch(value):
        raise Bad(where + ' requires an ISO-8601 timestamp with UTC offset')
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00' if value.endswith('Z') else value)
        normalized = parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise Bad(where + ' has an invalid timestamp') from exc
    return normalized

def finite(value, where):
    if value is None:
        return None
    if isinstance(value, OutOfRangeNumericLexeme):
        return value
    if type(value) not in (int, float) or isinstance(value, bool):
        raise Bad(where + ' must be a finite number or null')
    if isinstance(value, float) and not math.isfinite(value):
        raise Bad(where + ' must be a finite number or null')
    return value

def representable(value):
    if isinstance(value, OutOfRangeNumericLexeme):
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, int):
        try:
            return math.isfinite(float(value))
        except OverflowError:
            return False
    return False

def merged(*groups):
    out = []
    for group in groups:
        for item in group:
            if item not in out:
                out.append(item)
    return out

def nonnegative(value):
    return None if value >= 0 else 'must be nonnegative'

def positive(value):
    return None if value > 0 else 'must be strictly positive'

def ratio(value):
    return None if 0 <= value <= 1 else 'must be within [0,1]'

class Workflow:
    def __init__(self, data):
        exact(data, {'version', 'as_of', 'facts', 'jobs', 'obligations'}, 'root')
        if data['version'] != '1':
            raise Bad('version must be "1"')
        self.as_of = time(data['as_of'], 'as_of')
        if not isinstance(data['facts'], dict) or not isinstance(data['jobs'], list) or not isinstance(data['obligations'], list):
            raise Bad('facts must be an object; jobs and obligations must be arrays')
        self.facts = {}
        for fact_id, item in data['facts'].items():
            fact_id = ident(fact_id, 'fact id')
            exact(item, {'value', 'unit', 'basis', 'source', 'evidence', 'known_at'}, 'fact ' + fact_id)
            if item['evidence'] not in {'fact', 'forecast', 'assumption'}:
                raise Bad('invalid evidence class for ' + fact_id)
            self.facts[fact_id] = {'value': finite(item['value'], fact_id), 'unit': text(item['unit'], fact_id + ' unit'), 'basis': text(item['basis'], fact_id + ' basis'), 'source': text(item['source'], fact_id + ' source'), 'evidence': item['evidence'], 'known_at': time(item['known_at'], fact_id + ' known_at')}
        self.jobs, self.obligations, self.results = data['jobs'], data['obligations'], {}

    def ref(self, value, where):
        value = ident(value, where)
        if value not in self.facts:
            raise Bad(where + ' references unknown fact ' + value)
        return value

    def param(self, ref, unit=None, basis=None, rule=None, where='parameter'):
        ref = self.ref(ref, where)
        fact, issues = self.facts[ref], []
        if unit is not None and fact['unit'] != unit:
            issues.append(('incompatible', ref + ' unit is incompatible'))
        if basis is not None and fact['basis'] != basis:
            issues.append(('incompatible', ref + ' basis is incompatible'))
        if fact['value'] is None:
            issues.append(('missing', ref + ' is unknown: ' + fact['source']))
        elif not representable(fact['value']):
            if isinstance(fact['value'], OutOfRangeNumericLexeme):
                detail = fact['value'].reason
            else:
                detail = 'is outside supported numeric range'
            issues.append(('conflict', ref + ' ' + detail))
        if self.as_of is not None:
            if fact['known_at'] is None:
                issues.append(('missing', ref + ' has unknown first-known time'))
            elif fact['known_at'] > self.as_of:
                issues.append(('missing', ref + ' was first known after as_of'))
        if fact['value'] is not None and not issues and rule:
            message = rule(fact['value'])
            if message:
                issues.append(('infeasible', ref + ' ' + message))
        return {'id': ref, 'value': fact['value'], 'issues': issues}

    def emit(self, result_id, value, unit, basis, params=(), issues=(), reason=None, raw=None):
        if result_id in self.results:
            raise Bad('duplicate generated result ' + result_id)
        dependencies = sorted({item['id'] if isinstance(item, dict) else item for item in params})
        issues = merged(issues)
        if not issues and not representable(value):
            issues = [('conflict', 'derived result is nonfinite')]
        if issues:
            status = min((kind for kind, _ in issues), key=lambda kind: ORDER[kind])
            detail = '; '.join(dict.fromkeys(message for _, message in sorted(issues, key=lambda item: (ORDER[item[0]], item[1]))))
            reason = (reason + '; ' + detail) if reason else detail
            value = None
            raw = raw if status == 'infeasible' and representable(raw) else None
        else:
            status, raw = 'calculated', None
        self.results[result_id] = {'value': value, 'status': status, 'reason': reason, 'dependencies': dependencies, 'evidence': sorted({self.facts[item]['evidence'] for item in dependencies}), 'unit': unit, 'basis': basis, 'raw_value': raw}

    def calc(self, result_id, params, unit, basis, function, extra=()):
        issues = merged(*(item['issues'] for item in params), extra)
        if issues:
            self.emit(result_id, None, unit, basis, params, issues)
            return
        try:
            value = function(*(item['value'] for item in params))
        except (ArithmeticError, OverflowError, ValueError):
            self.emit(result_id, None, unit, basis, params, [('conflict', 'arithmetic failed')])
            return
        self.emit(result_id, value, unit, basis, params)

    def safe_fsum(self, values):
        try:
            total = math.fsum(list(values))
        except (OverflowError, ValueError, ArithmeticError):
            return None
        return total if type(total) in (int, float) and not isinstance(total, bool) and math.isfinite(total) else None

    def economics(self, job_id, data):
        exact(data, {'currency', 'basis', 'rows'}, 'economics inputs')
        currency, basis, rows = text(data['currency'], 'currency'), text(data['basis'], 'basis'), data['rows']
        if not isinstance(rows, list) or not rows:
            raise Bad('economics rows must be nonempty')
        row_ids, pairs = set(), set()
        for row in rows:
            exact(row, {'id', 'scenario', 'period', 'values', 'capex'}, 'economics row')
            row_id = ident(row['id'], 'row id')
            pair = (text(row['scenario'], 'scenario'), text(row['period'], 'period'))
            if row_id in row_ids or pair in pairs:
                raise Bad('duplicate economics row or scenario-period pair')
            row_ids.add(row_id); pairs.add(pair)
            fields = {'units','period_units','utilization','unit_price','variable_cost','fee_rate','fixed_cost','target_years','utilization_min','utilization_max','price_index'}
            exact(row['values'], fields, 'economics values')
            v = row['values']
            p = {
                'U': self.param(v['units'], 'unit', basis, nonnegative), 'P': self.param(v['period_units'], 'period_per_year', basis, nonnegative),
                'u': self.param(v['utilization'], 'ratio', basis, ratio), 'price': self.param(v['unit_price'], currency + '/activity', basis, nonnegative),
                'cost': self.param(v['variable_cost'], currency + '/activity', basis, nonnegative), 'fee': self.param(v['fee_rate'], 'ratio', basis, ratio),
                'fixed': self.param(v['fixed_cost'], currency + '/year', basis, nonnegative), 'target': self.param(v['target_years'], 'year', basis, positive),
                'lo': self.param(v['utilization_min'], 'ratio', basis, ratio), 'hi': self.param(v['utilization_max'], 'ratio', basis, ratio),
                'index': self.param(v['price_index'], 'ratio', basis, positive)}
            if not isinstance(row['capex'], list):
                raise Bad('capex must be an array')
            components, component_ids = [], set()
            for component in row['capex']:
                exact(component, {'id', 'amount', 'subsidy_rate'}, 'capex component')
                component_id = ident(component['id'], 'capex component id')
                if component_id in component_ids:
                    raise Bad('duplicate capex component id')
                component_ids.add(component_id)
                components.append((component_id, self.param(component['amount'], currency, basis, nonnegative), self.param(component['subsidy_rate'], 'ratio', basis, ratio)))
            cap = [item for _, amount, subsidy in components for item in (amount, subsidy)]
            prefix = job_id + '.' + row_id + '.'
            activity = [p['U'], p['P'], p['u']]
            gross = activity + [p['price']]
            net = gross + [p['fee'], p['cost'], p['fixed']]
            self.calc(prefix+'activity', activity, 'activity/year', basis, lambda U,P,u: U*P*u)
            self.calc(prefix+'gross_flow', gross, currency+'/year', basis, lambda U,P,u,x: U*P*u*x)
            self.calc(prefix+'fee', gross+[p['fee']], currency+'/year', basis, lambda U,P,u,x,f: U*P*u*x*f)
            self.calc(prefix+'variable_cost_total', activity+[p['cost']], currency+'/year', basis, lambda U,P,u,c: U*P*u*c)
            self.calc(prefix+'net_flow', net, currency+'/year', basis, lambda U,P,u,x,f,c,F: U*P*u*(x*(1-f)-c)-F)
            cap_fn = lambda *x: math.fsum(x[i]*(1-x[i+1]) for i in range(0,len(x),2))
            self.calc(prefix+'net_capex', cap, currency, basis, cap_fn)
            known = [(name,a,s) for name,a,s in components if not a['issues'] and not s['issues']]
            excluded = sorted(name for name,a,s in components if a['issues'] or s['issues'])
            known_params = [item for _,a,s in known for item in (a,s)]
            subtotal_reason = 'Partial known capex subtotal; it does not replace complete net capex' + (('; excluded components: '+', '.join(excluded)) if excluded else '')
            known_capex = self.safe_fsum(
                amount['value'] * (1 - subsidy['value']) for _, amount, subsidy in known
            ) if known else 0.0
            if known_capex is None:
                self.emit(prefix+'net_capex_known_subtotal', None, currency, basis, known_params,
                          [('conflict', 'arithmetic failed')], reason=subtotal_reason)
            else:
                self.emit(prefix+'net_capex_known_subtotal', known_capex, currency, basis, known_params, reason=subtotal_reason)
            pay = cap + net
            issues = merged(*(item['issues'] for item in pay))
            net_capex_result = self.results[prefix+'net_capex']
            net_flow_result = self.results[prefix+'net_flow']
            for derived in (net_capex_result, net_flow_result):
                if derived['status'] != 'calculated':
                    issues.append((derived['status'] if derived['status'] in ORDER else 'conflict',
                                   derived['reason'] or derived['status'] + ' result unavailable'))
            if not issues:
                if net_flow_result['value'] <= 0:
                    issues.append(('infeasible','net flow is not positive'))
                else:
                    def payback_fn(*values):
                        capex = cap_fn(*values[:len(cap)])
                        flow = 0.0
                        U,P,u,x,f,c,F = values[len(cap):]
                        flow = U*P*u*(x*(1-f)-c)-F
                        result = capex/flow
                        if not math.isfinite(result):
                            raise OverflowError('payback is nonfinite')
                        return result
                    self.calc(prefix+'payback_years', pay, 'year', basis, payback_fn)
                    issues = None
            if issues:
                self.emit(prefix+'payback_years', None, 'year', basis, pay, issues)
            self.calc(prefix+'constant_gross_flow', gross+[p['index']], currency+'/year', basis, lambda U,P,u,x,D: U*P*u*x/D)
            self.calc(prefix+'constant_net_flow', net+[p['index']], currency+'/year', basis, lambda U,P,u,x,f,c,F,D: (U*P*u*(x*(1-f)-c)-F)/D)
            contribution = [p['U'],p['P'],p['price'],p['fee'],p['cost']]
            self.calc(prefix+'contribution_at_full_utilization', contribution, currency+'/year', basis, lambda U,P,x,f,c: U*P*(x*(1-f)-c))
            inverse = cap + contribution + [p['target'],p['fixed'],p['lo'],p['hi']]
            issues = merged(*(item['issues'] for item in inverse))
            if issues:
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, issues); continue
            net_capex_result = self.results[prefix+'net_capex']
            contribution_result = self.results[prefix+'contribution_at_full_utilization']
            if net_capex_result['status'] != 'calculated':
                issues.append((net_capex_result['status'], net_capex_result['reason'] or 'net capex unavailable'))
            if contribution_result['status'] != 'calculated':
                issues.append((contribution_result['status'], contribution_result['reason'] or 'contribution unavailable'))
            U,P,x,f,c,T,F,lo,hi = [item['value'] for item in inverse[len(cap):]]
            if issues:
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, issues); continue
            if lo > hi:
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, [('infeasible','utilization bounds are reversed')]); continue
            cap_value = cap_fn(*(item['value'] for item in cap))
            contribution_value = contribution_result['value']
            if contribution_value <= 0:
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, [('infeasible','full-utilization contribution is not positive')]); continue
            try:
                raw = (cap_value/T+F)/contribution_value
                forward_value = U*P*raw*(x*(1-f)-c)-F
            except (ArithmeticError, OverflowError, ValueError):
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, [('conflict','required utilization arithmetic failed')]); continue
            if not math.isfinite(raw):
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, [('conflict','required utilization is nonfinite')]); continue
            if raw < 0 or raw > 1 or raw < lo or raw > hi:
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, [('infeasible','required utilization is outside supplied bounds')], raw=raw); continue
            if not math.isfinite(forward_value) or not math.isclose(forward_value, cap_value/T, rel_tol=1e-12, abs_tol=1e-9):
                self.emit(prefix+'required_utilization', None, 'ratio', basis, inverse, [('conflict','inverse threshold failed forward check')]); continue
            self.emit(prefix+'required_utilization', raw, 'ratio', basis, inverse)

    def projects(self, job_id, data):
        exact(data, {'mode','cutoff','unit','basis','states','records'}, 'projects inputs')
        mode, unit, basis = data['mode'], text(data['unit'],'unit'), text(data['basis'],'basis')
        if mode not in {'snapshot','history'}:
            raise Bad('invalid project mode')
        cutoff = time(data['cutoff'],'cutoff')
        if mode == 'history' and (cutoff is None or self.as_of is None or cutoff != self.as_of):
            raise Bad('history cutoff must equal root as_of')
        if mode == 'snapshot' and cutoff is not None:
            raise Bad('snapshot cutoff must be null')
        if not isinstance(data['states'],list) or not data['states'] or not isinstance(data['records'],list):
            raise Bad('invalid states or records')
        states = {}
        for state in data['states']:
            exact(state, {'id','prospective','weight'}, 'state')
            sid = ident(state['id'],'state id')
            if sid in states or type(state['prospective']) is not bool:
                raise Bad('duplicate state or invalid prospective flag')
            if not state['prospective'] and state['weight'] is not None:
                raise Bad('nonprospective state weight must be null')
            states[sid] = {'prospective':state['prospective'],'weight':None if state['weight'] is None else self.ref(state['weight'],'state weight')}
        records, record_ids = [], set()
        for record in data['records']:
            exact(record, {'id','project_id','state','effective_at','known_at','revision','quantity','capacity_check'}, 'record')
            rid, pid, sid = ident(record['id'],'record id'), ident(record['project_id'],'project id'), ident(record['state'],'state')
            if rid in record_ids or sid not in states:
                raise Bad('duplicate record or unknown state')
            record_ids.add(rid)
            if type(record['revision']) is not int or record['revision'] < 0:
                raise Bad('invalid revision')
            effective, known = time(record['effective_at'],'effective_at'), time(record['known_at'],'known_at')
            if mode == 'history' and (effective is None or known is None):
                raise Bad('history record dates required')
            if mode == 'snapshot' and (effective is not None or known is not None or record['revision'] != 0):
                raise Bad('snapshot records require null dates and revision zero')
            capacity = record['capacity_check']
            if capacity is not None:
                exact(capacity, {'power','duration','reported','power_unit','duration_unit','capacity_unit','factor'}, 'capacity_check')
                capacity = {'power':self.ref(capacity['power'],'power'),'duration':self.ref(capacity['duration'],'duration'),'reported':self.ref(capacity['reported'],'reported'),'factor':self.ref(capacity['factor'],'factor'),'power_unit':text(capacity['power_unit'],'power unit'),'duration_unit':text(capacity['duration_unit'],'duration unit'),'capacity_unit':text(capacity['capacity_unit'],'capacity unit')}
            records.append({'id':rid,'project':pid,'state':sid,'effective':effective,'known':known,'revision':record['revision'],'quantity':self.ref(record['quantity'],'quantity'),'capacity':capacity})
        grouped = {}
        for record in records:
            grouped.setdefault(record['project'],[]).append(record)
        selected, conflicts, omitted = {}, {}, {}
        for pid, group in grouped.items():
            eligible = []
            for r in group:
                if mode == 'snapshot':
                    eligible.append(r)
                elif r['known'] <= cutoff and (
                        states[r['state']]['prospective'] or r['effective'] <= cutoff):
                    # Prospective pipeline records may take effect after the cutoff if they
                    # were already knowable; realized records must be effective by cutoff.
                    eligible.append(r)
            if not eligible:
                omitted[pid] = {r['state'] for r in group}; continue
            if mode == 'history':
                rank = max((r['effective'],r['known'],r['revision']) for r in eligible)
                eligible = [r for r in eligible if (r['effective'],r['known'],r['revision']) == rank]
            payloads = {}
            for r in eligible:
                key = (r['state'],r['quantity'],json.dumps(r['capacity'],sort_keys=True,separators=(',',':')))
                payloads.setdefault(key,[]).append(r)
            if len(payloads) == 1:
                selected[pid] = next(iter(payloads.values()))[0]
            else:
                conflicts[pid] = eligible
        for sid in states:
            rows = [(pid,r) for pid,r in selected.items() if r['state'] == sid]
            disputed_projects = {pid for pid,rs in conflicts.items() if any(r['state'] == sid for r in rs)}
            tied = [(pid,r) for pid,rs in conflicts.items() if pid in disputed_projects for r in rs]
            params = [self.param(r['quantity'],unit,basis,nonnegative) for _,r in rows]
            tied_params = [self.param(r['quantity'],unit,basis,nonnegative) for _,r in tied]
            issues = merged(*(p['issues'] for p in params+tied_params))
            if tied:
                issues.append(('conflict','equally eligible records disagree for '+', '.join(sorted({pid for pid,_ in tied}))))
            if issues:
                self.emit(job_id+'.'+sid+'.total',None,unit,basis,params+tied_params,issues)
            else:
                total = self.safe_fsum(p['value'] for p in params)
                if total is None:
                    self.emit(job_id+'.'+sid+'.total',None,unit,basis,params,[('conflict','arithmetic failed')])
                else:
                    self.emit(job_id+'.'+sid+'.total',total,unit,basis,params)
            known_params = [p for p in params if not p['issues']]
            excluded = [pid for (pid,_),p in zip(rows,params) if p['issues']] + [pid for pid,_ in tied] + [pid for pid,sids in omitted.items() if sid in sids]
            reason = 'Partial known subtotal for the eligible sample; it does not establish population coverage' + (('; excluded projects: '+', '.join(sorted(set(excluded)))) if excluded else '')
            known_total = self.safe_fsum(p['value'] for p in known_params)
            if known_total is None:
                self.emit(job_id+'.'+sid+'.known_subtotal',None,unit,basis,known_params,[('conflict','arithmetic failed')],reason=reason)
            else:
                self.emit(job_id+'.'+sid+'.known_subtotal',known_total,unit,basis,known_params,reason=reason)
        pipeline_params, terms, issues = [], [], []
        conflict_weights = set()
        for pid,r in selected.items():
            state = states[r['state']]
            if not state['prospective']:
                continue
            quantity = self.param(r['quantity'],unit,basis,nonnegative); pipeline_params.append(quantity)
            if state['weight'] is None:
                issues.append(('missing','prospective state '+r['state']+' has no weight'))
            else:
                weight = self.param(state['weight'],'ratio',basis,ratio); pipeline_params.append(weight); terms.append((quantity,weight))
        for pid,rs in conflicts.items():
            prospective_records = [r for r in rs if states[r['state']]['prospective']]
            if prospective_records:
                issues.append(('conflict','prospective state conflict for project '+pid))
                # Keep every competing payload, including a realized challenger, so
                # state totals and the blocked pipeline remain fully traceable.
                for r in rs:
                    pipeline_params.append(self.param(r['quantity'],unit,basis,nonnegative))
                for r in prospective_records:
                    weight_id = states[r['state']]['weight']
                    if weight_id is None:
                        issues.append(('missing','prospective state '+r['state']+' has no weight'))
                    elif r['state'] not in conflict_weights:
                        conflict_weights.add(r['state'])
                        pipeline_params.append(self.param(weight_id,'ratio',basis,ratio))
        issues = merged(issues,*(p['issues'] for p in pipeline_params))
        pipeline_total = None
        if not issues:
            pipeline_total = self.safe_fsum(q['value']*w['value'] for q,w in terms)
            if pipeline_total is None:
                issues.append(('conflict','arithmetic failed'))
        self.emit(job_id+'.pipeline',pipeline_total,unit,basis,pipeline_params,issues)
        for pid,r in selected.items():
            c = r['capacity']
            if c is None:
                continue
            power=self.param(c['power'],c['power_unit'],basis,nonnegative)
            duration=self.param(c['duration'],c['duration_unit'],basis,nonnegative)
            reported=self.param(c['reported'],c['capacity_unit'],basis,nonnegative)
            factor_unit=c['capacity_unit']+'/('+c['power_unit']+'*'+c['duration_unit']+')'
            factor=self.param(c['factor'],factor_unit,basis,positive)
            prefix=job_id+'.'+pid+'.'
            self.calc(prefix+'derived_capacity',[power,duration,factor],c['capacity_unit'],basis,lambda p,d,f:p*d*f)
            self.calc(prefix+'reported_capacity',[reported],c['capacity_unit'],basis,lambda x:x)
            self.calc(prefix+'capacity_residual',[reported,power,duration,factor],c['capacity_unit'],basis,lambda r,p,d,f:r-p*d*f)

    def investment(self, job_id, data):
        exact(data, {'currency','basis','groups','mix'}, 'investment inputs')
        currency,basis,groups_raw=text(data['currency'],'currency'),text(data['basis'],'basis'),data['groups']
        if not isinstance(groups_raw,list) or not groups_raw:
            raise Bad('groups must be nonempty')
        groups, fractions = {}, {}
        for group in groups_raw:
            exact(group, {'id','total','components'}, 'group')
            gid=ident(group['id'],'group id')
            if gid in groups or not isinstance(group['components'],list) or not group['components']:
                raise Bad('duplicate group or empty components')
            total=self.param(group['total'],currency,basis,nonnegative); components=[]; ids=set()
            for component in group['components']:
                exact(component, {'id','share','equipment','accessible'}, 'component')
                cid=ident(component['id'],'component id')
                if cid in ids or type(component['equipment']) is not bool:
                    raise Bad('duplicate component or invalid equipment flag')
                ids.add(cid)
                components.append({'id':cid,'share':self.param(component['share'],'ratio',basis,ratio),'equipment':component['equipment'],'accessible':self.param(component['accessible'],'ratio',basis,ratio)})
            groups[gid]=True
            shares=[c['share'] for c in components]; share_issues=merged(*(p['issues'] for p in shares))
            share_total = None if share_issues else self.safe_fsum(p['value'] for p in shares)
            if not share_issues and share_total is None:
                share_issues.append(('conflict','component share arithmetic failed for '+gid))
            if not share_issues and abs(share_total-1)>1e-6:
                share_issues.append(('conflict','component shares for '+gid+' do not sum to one'))
            equipment=[c for c in components if c['equipment']]; access=[c['accessible'] for c in equipment]
            eq_fraction=None if share_issues else self.safe_fsum(c['share']['value'] for c in equipment)
            if not share_issues and eq_fraction is None:
                share_issues.append(('conflict','equipment fraction arithmetic failed for '+gid)); eq_fraction=None
            eq_issues=merged(total['issues'],share_issues)
            eq_params=[total]+shares
            if eq_issues:self.emit(job_id+'.'+gid+'.equipment',None,currency,basis,eq_params,eq_issues)
            else:self.emit(job_id+'.'+gid+'.equipment',total['value']*eq_fraction,currency,basis,eq_params)
            ac_issues=merged(total['issues'],share_issues,*(p['issues'] for p in access)); ac_params=eq_params+access
            ac_fraction=None if ac_issues else self.safe_fsum(c['share']['value']*c['accessible']['value'] for c in equipment)
            if not ac_issues and ac_fraction is None:
                ac_issues.append(('conflict','accessible fraction arithmetic failed for '+gid))
            if ac_issues:self.emit(job_id+'.'+gid+'.accessible',None,currency,basis,ac_params,ac_issues)
            else:self.emit(job_id+'.'+gid+'.accessible',total['value']*ac_fraction,currency,basis,ac_params)
            known=[c['share'] for c in equipment if not c['share']['issues']]
            excluded=[c['id'] for c in equipment if c['share']['issues']]
            reason='Partial known equipment subtotal; it does not replace the complete component universe'+(('; excluded components: '+', '.join(excluded)) if excluded else '')
            if total['issues']:self.emit(job_id+'.'+gid+'.equipment_known_subtotal',None,currency,basis,[total]+known,total['issues'],reason=reason)
            else:
                known_share = self.safe_fsum(p['value'] for p in known) if known else 0.0
                if known_share is None:
                    self.emit(job_id+'.'+gid+'.equipment_known_subtotal',None,currency,basis,[total]+known,[('conflict','known equipment subtotal arithmetic failed')],reason=reason)
                else:
                    self.emit(job_id+'.'+gid+'.equipment_known_subtotal',total['value']*known_share,currency,basis,[total]+known,reason=reason)
            fractions[gid]={'equipment':(eq_fraction,share_issues,shares),'accessible':(ac_fraction,merged(share_issues,*(p['issues'] for p in access)),shares+access)}
        if data['mix'] is None:
            problem=[('missing','aggregate spending mix not supplied')]
            self.emit(job_id+'.aggregate_equipment',None,currency,basis,(),problem); self.emit(job_id+'.aggregate_accessible',None,currency,basis,(),problem); return
        mix=data['mix']; exact(mix, {'total','weights'}, 'mix')
        total=self.param(mix['total'],currency,basis,nonnegative)
        if not isinstance(mix['weights'],list):raise Bad('weights must be an array')
        weights={}
        for item in mix['weights']:
            exact(item, {'group','weight'}, 'weight'); gid=ident(item['group'],'weight group')
            if gid in weights:raise Bad('duplicate mix group')
            weights[gid]=self.param(item['weight'],'ratio',basis,ratio)
        if set(weights)!=set(groups):raise Bad('mix must exactly cover groups')
        weight_issues=merged(*(p['issues'] for p in weights.values()))
        weight_total = None if weight_issues else self.safe_fsum(p['value'] for p in weights.values())
        if not weight_issues and weight_total is None:
            weight_issues.append(('conflict','aggregate weight arithmetic failed'))
        if not weight_issues and abs(weight_total-1)>1e-6:
            weight_issues.append(('conflict','aggregate weights do not sum to one'))
        effective_groups = [g for g in groups if weights[g]['value'] != 0]
        for name in ('equipment','accessible'):
            params=[total]+list(weights.values())+sum((fractions[g][name][2] for g in effective_groups),[])
            issues=merged(total['issues'],weight_issues,*(fractions[g][name][1] for g in effective_groups))
            fraction_total = None if issues else self.safe_fsum(weights[g]['value']*fractions[g][name][0] for g in effective_groups)
            if not issues and fraction_total is None:
                issues.append(('conflict','aggregate fraction arithmetic failed'))
            if issues or fraction_total is None:
                self.emit(job_id+'.aggregate_'+name,None,currency,basis,params,issues)
            else:
                self.emit(job_id+'.aggregate_'+name,total['value']*fraction_total,currency,basis,params)

    def gates(self, job_id, data):
        exact(data, {'rows'}, 'gates inputs')
        if not isinstance(data['rows'],list) or not data['rows']:raise Bad('gate rows must be nonempty')
        ids=set()
        for row in data['rows']:
            exact(row, {'id','start','gate','duration'}, 'gate row'); rid=ident(row['id'],'gate row id')
            if rid in ids:raise Bad('duplicate gate row id')
            ids.add(rid); start=time(row['start'],'start',False); gate=time(row['gate'],'gate',False); duration_id=self.ref(row['duration'],'duration'); basis=self.facts[duration_id]['basis']; duration=self.param(duration_id,'day',basis,nonnegative)
            result_id=job_id+'.'+rid+'.feasible'
            if duration['issues']:self.emit(result_id,None,'boolean',basis,[duration],duration['issues']);continue
            try:completion=start+timedelta(days=duration['value'])
            except (OverflowError,ValueError):self.emit(result_id,None,'boolean',basis,[duration],[('conflict','completion time is not representable')]);continue
            if completion<=gate:self.emit(result_id,True,'boolean',basis,[duration])
            else:self.emit(result_id,None,'boolean',basis,[duration],[('infeasible','observation completes after the gate')])

    def convert(self, job_id, data):
        exact(data, {'rows', 'ratios'}, 'convert inputs')
        if not isinstance(data['rows'], list) or not data['rows'] or not isinstance(data['ratios'], list):
            raise Bad('convert rows must be nonempty and ratios must be an array')
        rows = {}
        for row in data['rows']:
            exact(row, {'id', 'source', 'declared_source_unit', 'canonical_unit', 'factor'}, 'convert row')
            row_id = ident(row['id'], 'convert row id')
            if row_id in rows:
                raise Bad('duplicate convert row id')
            source_id = self.ref(row['source'], 'convert source')
            source_unit = text(row['declared_source_unit'], 'declared source unit')
            canonical_unit = text(row['canonical_unit'], 'canonical unit')
            basis = self.facts[source_id]['basis']
            source = self.param(source_id, source_unit, basis, where='convert source')
            factor_unit = canonical_unit + (
                '/(' + source_unit + ')' if '*' in source_unit or '/' in source_unit
                else '/' + source_unit
            )
            factor = self.param(row['factor'], factor_unit, basis, positive, where='convert factor')
            prefix = job_id + '.' + row_id + '.'
            self.calc(prefix + 'source_value', [source], source_unit, basis, lambda value: value)
            self.calc(prefix + 'canonical', [source, factor], canonical_unit, basis,
                      lambda value, scale: value * scale)
            rows[row_id] = self.results[prefix + 'canonical']

        ratio_ids = set()
        for ratio in data['ratios']:
            exact(ratio, {'id', 'numerator_row', 'denominator_row'}, 'convert ratio')
            ratio_id = ident(ratio['id'], 'convert ratio id')
            if ratio_id in ratio_ids:
                raise Bad('duplicate convert ratio id')
            ratio_ids.add(ratio_id)
            numerator_id = ident(ratio['numerator_row'], 'convert numerator row')
            denominator_id = ident(ratio['denominator_row'], 'convert denominator row')
            if numerator_id not in rows or denominator_id not in rows:
                raise Bad('convert ratio references an unknown row')
            numerator, denominator = rows[numerator_id], rows[denominator_id]
            params = numerator['dependencies'] + denominator['dependencies']
            issues = []
            for result in (numerator, denominator):
                if result['status'] != 'calculated':
                    issues.append((result['status'], result['reason'] or result['status'] + ' result unavailable'))
            value = None
            if not issues:
                if numerator['unit'] != denominator['unit'] or numerator['basis'] != denominator['basis']:
                    issues.append(('incompatible', 'canonical units or bases differ'))
                elif denominator['value'] == 0:
                    issues.append(('infeasible', 'canonical denominator is zero'))
                else:
                    value = numerator['value'] / denominator['value']
                    if not representable(value):
                        issues.append(('conflict', 'converted multiple is outside supported numeric range'))
            self.emit(job_id + '.' + ratio_id + '.multiple', value, 'ratio',
                      numerator['basis'], params, issues)

    def claims(self, job_id, data):
        exact(data, {'rows'}, 'claims inputs')
        if not isinstance(data['rows'], list) or not data['rows']:
            raise Bad('claims rows must be nonempty')
        row_ids = set()
        treatments = {'retain_residual', 'use_reported', 'use_derived'}
        for row in data['rows']:
            if not isinstance(row, dict):
                raise Bad('claims rows must contain objects')
            row_id = ident(row.get('id'), 'claim row id')
            if row_id in row_ids:
                raise Bad('duplicate claim row id')
            row_ids.add(row_id)
            kind = row.get('kind')
            if kind == 'direction':
                exact(row, {'id', 'kind', 'series', 'claimed'}, 'direction claim')
                series = row['series']
                if not isinstance(series, list) or len(series) < 2:
                    raise Bad('direction claim series must contain at least two fact IDs')
                if not isinstance(row['claimed'], str) or row['claimed'] not in {
                        'all_nondecreasing', 'all_nonincreasing'}:
                    raise Bad('invalid direction claim')
                params = [self.param(fact_id, where='direction series fact') for fact_id in series]
                first = self.facts[params[0]['id']]
                issues = merged(*(param['issues'] for param in params))
                if any(
                        self.facts[param['id']]['unit'] != first['unit']
                        or self.facts[param['id']]['basis'] != first['basis']
                        for param in params):
                    issues.append(('incompatible', 'direction series units or bases differ'))
                if not issues:
                    values = [param['value'] for param in params]
                    if row['claimed'] == 'all_nondecreasing':
                        holds = all(later >= earlier for earlier, later in zip(values, values[1:]))
                    else:
                        holds = all(later <= earlier for earlier, later in zip(values, values[1:]))
                    if not holds:
                        issues.append(('conflict', 'claimed universal direction is violated'))
                self.emit(job_id + '.' + row_id + '.consistent', True, 'boolean',
                          first['basis'], params, issues)
            elif kind == 'treatment':
                exact(row, {'id', 'kind', 'recorded', 'asserted', 'residual'}, 'treatment claim')
                if not isinstance(row['recorded'], str) or not isinstance(row['asserted'], str) or (
                        row['recorded'] not in treatments or row['asserted'] not in treatments):
                    raise Bad('invalid treatment state')
                residual_id = self.ref(row['residual'], 'treatment residual')
                residual = self.param(residual_id, where='treatment residual')
                residual_fact = self.facts[residual_id]
                if residual_fact['value'] is None:
                    # A null residual is still a fact dependency; it is not itself a conflict.
                    residual['issues'] = [
                        issue for issue in residual['issues']
                        if not (issue[0] == 'missing' and issue[1].endswith(residual_fact['source']))
                    ]
                issues = residual['issues'][:]
                if row['recorded'] != row['asserted']:
                    issues.append(('conflict', 'asserted treatment differs from recorded treatment'))
                self.emit(job_id + '.' + row_id + '.consistent', True, 'boolean',
                          residual_fact['basis'], [residual], issues)
            else:
                raise Bad('invalid claim kind')

    def thresholds(self, job_id, data):
        exact(data, {'currency', 'basis', 'rows'}, 'thresholds inputs')
        currency = text(data['currency'], 'currency')
        basis = text(data['basis'], 'basis')
        if not isinstance(data['rows'], list) or not data['rows']:
            raise Bad('thresholds rows must be nonempty')
        fields = {
            'id', 'net_capex', 'period_units', 'benefit_per_unit', 'fixed_cost', 'target_years',
            'observed_units', 'max_units', 'eligible_amount', 'ineligible_amount',
            'observed_subsidy_rate',
        }
        row_ids = set()
        for row in data['rows']:
            exact(row, fields, 'thresholds row')
            row_id = ident(row['id'], 'threshold row id')
            if row_id in row_ids:
                raise Bad('duplicate threshold row id')
            row_ids.add(row_id)
            capex = self.param(row['net_capex'], currency, basis, nonnegative)
            period = self.param(row['period_units'], 'period_per_year', basis, positive)
            benefit = self.param(row['benefit_per_unit'], currency + '/unit', basis, positive)
            fixed = self.param(row['fixed_cost'], currency + '/year', basis, nonnegative)
            target = self.param(row['target_years'], 'year', basis, positive)
            units = self.param(row['observed_units'], 'unit', basis, nonnegative)
            maximum = self.param(row['max_units'], 'unit', basis, nonnegative)
            # A null max_units fact explicitly means there is no upper bound.
            if self.facts[row['max_units']]['value'] is None:
                maximum['issues'] = [
                    issue for issue in maximum['issues']
                    if not (issue[0] == 'missing' and issue[1].endswith(self.facts[row['max_units']]['source']))
                ]
            eligible = self.param(row['eligible_amount'], currency, basis, nonnegative)
            ineligible = self.param(row['ineligible_amount'], currency, basis, nonnegative)
            subsidy = self.param(row['observed_subsidy_rate'], 'ratio', basis, ratio)

            capital_params = [capex, eligible, ineligible, subsidy]
            capital_issues = merged(*(param['issues'] for param in capital_params))
            if not capital_issues and not math.isclose(
                    capex['value'],
                    eligible['value'] * (1 - subsidy['value']) + ineligible['value'],
                    rel_tol=1e-12, abs_tol=1e-9):
                capital_issues.append(('conflict', 'capital identity mismatch'))

            operating_params = [units, period, benefit, fixed]
            prefix = job_id + '.' + row_id + '.'
            self.calc(prefix + 'observed_net_flow', operating_params, currency + '/year', basis,
                      lambda U, P, b, F: U * P * b - F)
            flow_result = self.results[prefix + 'observed_net_flow']
            flow_issues = merged(*(param['issues'] for param in operating_params))
            if flow_result['status'] != 'calculated':
                flow_issues.append((flow_result['status'], flow_result['reason'] or 'flow result unavailable'))

            payback_issues = merged(capital_issues, flow_issues)
            payback = None
            if not payback_issues:
                if flow_result['value'] <= 0:
                    payback_issues.append(('infeasible', 'observed net flow is not positive'))
                else:
                    payback = capex['value'] / flow_result['value']
                    if not representable(payback):
                        payback = None
                        payback_issues.append(('conflict', 'payback is outside supported numeric range'))
            self.emit(prefix + 'payback_years', payback, 'year', basis,
                      capital_params + operating_params, payback_issues)

            required_params = [capex, period, benefit, fixed, target, maximum]
            required_issues = merged(
                capital_issues, period['issues'], benefit['issues'], fixed['issues'],
                target['issues'], maximum['issues'])
            required_units = None
            if not required_issues:
                required_units = (
                    (capex['value'] / target['value'] + fixed['value'])
                    / (period['value'] * benefit['value'])
                )
                if not representable(required_units):
                    required_issues.append(('conflict', 'required units are outside supported numeric range'))
                elif maximum['value'] is not None and required_units > maximum['value']:
                    required_issues.append(('infeasible', 'required units exceed supplied maximum'))
                elif not math.isclose(
                        required_units * period['value'] * benefit['value'] - fixed['value'],
                        capex['value'] / target['value'], rel_tol=1e-12, abs_tol=1e-9):
                    required_issues.append(('conflict', 'required units failed forward check'))
            self.emit(prefix + 'required_units', required_units, 'unit', basis,
                      [capex, eligible, ineligible, subsidy, period, benefit, fixed, target, maximum],
                      required_issues, raw=required_units)

            subsidy_params = capital_params + operating_params + [target]
            subsidy_issues = merged(capital_issues, flow_issues, target['issues'])
            required_subsidy = None
            if not subsidy_issues:
                if flow_result['value'] <= 0:
                    subsidy_issues.append(('infeasible', 'observed net flow is not positive'))
                elif eligible['value'] == 0:
                    subsidy_issues.append(('infeasible', 'eligible amount is not positive'))
                else:
                    target_capex = flow_result['value'] * target['value']
                    required_subsidy = 1 - (target_capex - ineligible['value']) / eligible['value']
                    if not representable(required_subsidy):
                        required_subsidy = None
                        subsidy_issues.append(('conflict', 'required subsidy is outside supported numeric range'))
                    elif required_subsidy < 0 or required_subsidy > 1:
                        subsidy_issues.append(('infeasible', 'required subsidy rate is outside [0,1]'))
                    elif not math.isclose(
                            eligible['value'] * (1 - required_subsidy) + ineligible['value'],
                            target_capex, rel_tol=1e-12, abs_tol=1e-9):
                        required_subsidy = None
                        subsidy_issues.append(('conflict', 'required subsidy failed forward check'))
            self.emit(prefix + 'required_subsidy_rate', required_subsidy, 'ratio', basis,
                      subsidy_params, subsidy_issues, raw=required_subsidy)

    def path(self, job_id, data):
        exact(data, {'unit', 'energy_unit', 'duration_unit', 'basis', 'rows'}, 'path inputs')
        unit = text(data['unit'], 'path unit')
        energy_unit = text(data['energy_unit'], 'energy unit')
        duration_unit = text(data['duration_unit'], 'duration unit')
        basis = text(data['basis'], 'basis')
        if not isinstance(data['rows'], list) or not data['rows']:
            raise Bad('path rows must be nonempty')
        row_ids, periods = set(), set()
        for row in data['rows']:
            exact(row, {'id', 'period', 'opening', 'addition', 'retirement', 'duration', 'factor'},
                  'path row')
            row_id = ident(row['id'], 'path row id')
            period = text(row['period'], 'period')
            if row_id in row_ids or period in periods:
                raise Bad('duplicate path row id or period')
            if (row['duration'] is None) != (row['factor'] is None):
                raise Bad('path duration and factor must both be null or both be fact IDs')
            row_ids.add(row_id)
            periods.add(period)
            opening = self.param(row['opening'], unit, basis, nonnegative)
            addition = self.param(row['addition'], unit, basis, nonnegative)
            retirement = self.param(row['retirement'], unit, basis, nonnegative)
            prefix = job_id + '.' + row_id + '.'
            self.calc(prefix + 'opening', [opening], unit, basis, lambda value: value)
            self.calc(prefix + 'addition', [addition], unit, basis, lambda value: value)
            self.calc(prefix + 'retirement', [retirement], unit, basis, lambda value: value)

            issues = merged(opening['issues'], addition['issues'], retirement['issues'])
            closing = None
            if not issues:
                closing = self.safe_fsum([opening['value'], addition['value'], -retirement['value']])
                if closing is None:
                    issues.append(('conflict', 'closing arithmetic failed'))
                elif closing < 0:
                    issues.append(('infeasible', 'closing is negative'))
            self.emit(prefix + 'closing', closing, unit, basis,
                      [opening, addition, retirement], issues, raw=closing)

            retirement_missing = bool(retirement['issues']) and all(
                issue[0] == 'missing' for issue in retirement['issues'])
            if retirement_missing and not opening['issues'] and not addition['issues']:
                subtotal = self.safe_fsum([opening['value'], addition['value']])
                subtotal_issues = []
                if subtotal is None:
                    subtotal_issues.append(('conflict', 'known path subtotal arithmetic failed'))
                self.emit(
                    prefix + 'known_subtotal', subtotal, unit, basis,
                    [opening, addition, retirement], subtotal_issues,
                    reason='Partial opening-plus-addition subtotal; retirement is unknown')

            if row['duration'] is not None:
                duration = self.param(row['duration'], duration_unit, basis, nonnegative)
                factor_unit = energy_unit + '/(' + unit + '*' + duration_unit + ')'
                factor = self.param(row['factor'], factor_unit, basis, positive)
                self.calc(prefix + 'energy_addition', [addition, duration, factor], energy_unit, basis,
                          lambda added, span, conversion: added * span * conversion)

    def run(self):
        job_ids=set()
        for job in self.jobs:
            exact(job, {'id','kind','inputs'}, 'job'); job_id=ident(job['id'],'job id')
            if job_id in job_ids:raise Bad('duplicate job id')
            job_ids.add(job_id)
            if job['kind']=='economics':self.economics(job_id,job['inputs'])
            elif job['kind']=='projects':self.projects(job_id,job['inputs'])
            elif job['kind']=='investment':self.investment(job_id,job['inputs'])
            elif job['kind']=='gates':self.gates(job_id,job['inputs'])
            elif job['kind']=='convert':self.convert(job_id,job['inputs'])
            elif job['kind']=='claims':self.claims(job_id,job['inputs'])
            elif job['kind']=='thresholds':self.thresholds(job_id,job['inputs'])
            elif job['kind']=='path':self.path(job_id,job['inputs'])
            else:raise Bad('unknown job kind')
        coverage=[]; obligation_ids=set()
        for item in self.obligations:
            exact(item, {'id','result_id','reason'}, 'obligation'); oid=ident(item['id'],'obligation id')
            if oid in obligation_ids:raise Bad('duplicate obligation id')
            obligation_ids.add(oid); has_result=item['result_id'] is not None; has_reason=item['reason'] is not None
            if has_result==has_reason:raise Bad('obligation requires exactly one result_id or reason')
            if has_result:
                result_id=text(item['result_id'],'result_id')
                if result_id not in self.results:raise Bad('unknown obligation result')
                result=self.results[result_id]; coverage.append({'id':oid,'status':'answered' if result['status']=='calculated' else 'limited','result_id':result_id,'reason':None if result['status']=='calculated' else result['reason']})
            else:coverage.append({'id':oid,'status':'limited','result_id':None,'reason':text(item['reason'],'obligation reason')})
        return {'version':'1','results':self.results,'coverage':coverage}

def main():
    try:
        if len(sys.argv)!=2:raise Bad('Use industry_workflow.py INPUT.json or - for stdin')
        raw=sys.stdin.read() if sys.argv[1]=='-' else Path(sys.argv[1]).read_text()
        data=json.loads(raw,object_pairs_hook=unique,parse_constant=constant,
                        parse_int=parse_integer,parse_float=parse_decimal)
        print(json.dumps(Workflow(data).run(),ensure_ascii=False,allow_nan=False));return 0
    except (Bad,json.JSONDecodeError) as exc:
        print(json.dumps({'error':{'message':str(exc) or type(exc).__name__}}));return 2
    except (OSError,ArithmeticError,TypeError,KeyError) as exc:
        print(json.dumps({'error':{'message':str(exc) or type(exc).__name__}}));return 1

if __name__=='__main__':
    sys.exit(main())
