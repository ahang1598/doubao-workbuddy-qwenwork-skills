import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
export const SCORING_RULES = JSON.parse(readFileSync(new URL('../references/review-scoring.json', import.meta.url), 'utf8'));

export function calculateScoring(value, context) {
  const require = (ok, field) => { if (!ok) throw Object.assign(new Error(`invalid scoring: ${field}`), {code:'INVALID_SCORING', field}); };
  const text = v => typeof v === 'string' && v.trim() && v.length <= 2000;
  const R = SCORING_RULES;
  require(value && value.version === R.version, 'version');
  if (context.evidence_version) require(value.evidence_version === context.evidence_version, 'evidence_version');
  require(Array.isArray(value.dimensions) && value.dimensions.length === 9, 'dimensions');
  const evidence = new Map(context.evidence.map(e => [e.id, e]));
  const issues = new Map(context.issues.map(i => [i.id, i]));
  require(Array.isArray(value.risks) && value.risks.length === issues.size, 'risks');
  const groups = new Map(), seen = new Set();
  for (const row of value.risks) {
    require(row && typeof row === 'object', 'risk');
    require(issues.has(row.issue_id) && !seen.has(row.issue_id), 'issue_id');
    seen.add(row.issue_id);
    require(['high','medium','low','unknown'].includes(row.level) && text(row.reason), 'risk level/reason');
    const issue = issues.get(row.issue_id);
    require(Boolean(issue.quote) || row.level === 'unknown', 'risk evidence incomplete');
    const key = JSON.stringify([String(issue.rule_id), (issue.quote || '').replace(/\s/g, '') || issue.id]);
    if (!groups.has(key)) groups.set(key, {level:row.level, reason:row.reason, rule_id:issue.rule_id, occurrences:[]});
    const group = groups.get(key);
    require(group.level === row.level, 'inconsistent repeated risk');
    group.occurrences.push(issue);
  }
  const risks = [...groups.values()];
  const high = risks.filter(r => r.level === 'high').length;
  const provisional = !context.compliance_complete || risks.some(r => r.level === 'unknown');
  seen.clear();
  const dimensions = value.dimensions.map(row => {
    require(row && typeof row === 'object', 'dimension');
    const spec = R.dimensions.find(d => d.id === row.id);
    require(spec && !seen.has(spec.id), 'dimension id');
    seen.add(spec.id);
    const {status, score, evidence_ids:refs} = row;
    require(['scored','not_applicable','insufficient'].includes(status) && text(row.reason), 'status/reason');
    require(Array.isArray(refs) && refs.every(i => typeof i === 'string' && evidence.has(i)) && new Set(refs).size === refs.length, 'evidence_ids');
    require(status === 'scored' ? Number.isInteger(score) && score >= 0 && score <= 10 && refs.length > 0 : score === null, 'score');
    if (status === 'scored') require(refs.some(i => (evidence.get(i).kind === 'quality') === (spec.id === 'compliance')), 'evidence kind');
    if (spec.id === 'compliance') {
      require(status !== 'not_applicable', 'compliance applicable');
      if (provisional) require(status === 'insufficient', 'compliance incomplete');
      else {
        require(status === 'scored', 'compliance score required');
        const [lo, hi] = high >= 3 ? [0,2] : high ? [3,4] : risks.some(r => r.level === 'medium') ? [5,6] : risks.length ? [7,8] : [9,10];
        require(score >= lo && score <= hi, 'compliance band');
      }
    }
    return {id:spec.id,name:spec.name,weight:spec.weight,status,score,reason:row.reason.trim(),evidence_ids:refs,evidence:refs.map(i => evidence.get(i))};
  }).sort((a,b) => R.dimensions.findIndex(d => d.id === a.id) - R.dimensions.findIndex(d => d.id === b.id));
  const scored = dimensions.filter(d => d.status === 'scored');
  const cap = R.caps.find(([count]) => high >= count)?.[1] ?? null;
  let total = null;
  if (scored.some(d => d.id !== 'compliance')) {
    total = scored.reduce((n,d) => n+d.score*d.weight,0) / scored.reduce((n,d) => n+d.weight,0);
    total = Math.floor(Math.min(total,cap ?? 10)*10+0.5)/10;
  }
  return {version:R.version,...(context.evidence_version ? {evidence_version:context.evidence_version} : {}),dimensions,risks,high_risk_count:high,total,level:R.levels.find(([min]) => total !== null && total >= min)?.[1] || '',
    status:total === null ? 'unavailable' : provisional ? 'provisional' : 'ready',cap,scope:'已检测内容评分',
    message:total === null ? '没有可评分的内容维度，无法评分' : provisional ? '合规或风险分级不完整，暂定分；封顶尚不能完整判定' : '仅评价本次已检测内容，不代表全场或转化效果'};
}

export function scoringTemplate(context) {
  return {version:SCORING_RULES.version,...(context.evidence_version ? {evidence_version:context.evidence_version} : {}),dimensions:SCORING_RULES.dimensions.map(d => ({id:d.id,status:'insufficient',score:null,reason:'',evidence_ids:[]})),
    risks:context.issues.map(i => ({issue_id:i.id,level:'unknown',reason:''}))};
}

// Use the prepared report only; no model-authored finding can create a new compliance hit.
export function scoringContext(segments, rules) {
  const evidence = segments.map(s => ({id:`speech:${s.i}`,kind:'speech',start_ms:s.st,end_ms:s.et,text:s.tx}));
  const issues = [];
  let complete = rules.length > 0 && evidence.length > 0;
  for (const [index,r] of rules.entries()) {
    const id = `quality:${index}`;
    evidence.push({id,kind:'quality',text:r.rule_name + '：' + r.conclusion,rule_id:String(r.rule_id),
      ...(r.start_time === undefined ? {} : {start_ms:r.start_time,end_ms:r.end_time ?? r.start_time})});
    if (![1,2].includes(r.machine_status_code)) complete = false;
    if (r.machine_status_code === 2) {
      const findings = r.scoring_findings || [];
      if (!findings.length || findings.length !== r.finding_count || findings.some(f => !f.quote)) complete = false;
      for (const [i,f] of (findings.length ? findings : [{}]).entries()) {
        const fid = `${id}:${i}`;
        evidence.push({id:fid,kind:'quality',text:f.quote || r.rule_name,rule_id:String(r.rule_id),
          ...(Number.isInteger(f.start_ms) ? {start_ms:f.start_ms,end_ms:f.end_ms ?? f.start_ms} : {})});
        issues.push({id:fid,rule_id:String(r.rule_id),quote:f.quote || '',evidence_ids:[fid],
          ...(Number.isInteger(f.start_ms) ? {start_ms:f.start_ms,end_ms:f.end_ms ?? f.start_ms} : {})});
      }
    }
  }
  const context = {evidence,issues,compliance_complete:complete};
  return {...context,evidence_version:createHash('sha256').update(JSON.stringify([SCORING_RULES.version,context])).digest('hex')};
}
