#!/usr/bin/env python3
"""Render evidence-linked research briefs. Python 3.10+, standard library only."""
import argparse
import html
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import urlparse

FIELDS=('design','population','sample','measures','analysis','findings','limitations')
LABELS={'design':'设计','population':'对象与情境','sample':'样本','measures':'测量/资料','analysis':'分析','findings':'发现','limitations':'局限'}
ACCESS={'fulltext':'全文','abstract':'仅摘要','bibliographic':'仅题录','unavailable':'未取得'}
STATUS={'include':'纳入','exclude':'排除','pending':'待定'}
VERIFY={'crosschecked':'已交叉核验','user_supplied':'用户提供','unverified':'未核实','synthetic':'合成演示'}
KIND={'empirical':'材料报告','synthesis':'综合判断','proposal':'研究建议'}
RELATION={'supports':'支持','contradicts':'相反证据','qualifies':'限定'}
REVIEW={'narrative':'叙述性综述草稿','scoping':'范围综述草稿（方法完成情况需另核）','systematic':'系统综述草稿（方法完成情况需另核）'}
PLAN_KEYS=('background','design','sampling','measurement','analysis','ethics','feasibility','timeline','risks','deliverables')


class ResearchError(ValueError):pass
def require(ok,message):
    if not ok:raise ResearchError(message)
def string(obj,key,where):
    require(isinstance(obj.get(key),str) and obj[key].strip(),f'{where}.{key} 需要非空文本')
def strings(value,where,empty=False):
    require(isinstance(value,list) and (empty or value) and all(isinstance(x,str) and x.strip() for x in value),f'{where} 需要文本数组')
def records(data,key,empty=False):
    x=data.get(key);require(isinstance(x,list) and (empty or x) and all(isinstance(v,dict) for v in x),f'{key} 需要对象数组');return x
def ids(items,prefix):
    values=[]
    for i in items:
        uid=i.get('id');require(isinstance(uid,str) and re.fullmatch(prefix+r'[1-9][0-9]*',uid),f'{prefix}编号无效');values.append(uid)
    require(len(values)==len(set(values)),f'{prefix}编号重复');return set(values)
def refs(value,allowed,where,empty=False):
    strings(value,where,empty);require(set(value)<=allowed,f'{where} 引用不存在');require(len(value)==len(set(value)),f'{where} 引用重复')
def safe_url(value):
    p=urlparse(value);return p.scheme in ('https','http') and bool(p.netloc)

def normalized_doi(value):
    value=(value or '').strip()
    value=re.sub(r'^https?://(?:dx\.)?doi\.org/','',value,flags=re.I)
    value=re.sub(r'^doi\s*:\s*','',value,flags=re.I)
    return value.casefold()


def validate(d):
    require(isinstance(d,dict),'根节点需要JSON对象')
    for key in ('title','topic','scope','review_type','version','search_log'):
        string(d,key,'research')
    require(d['review_type'] in ('narrative','scoping','systematic'),'review_type 无效')
    strings(d.get('assumptions'),'assumptions',True)
    papers=records(d,'papers');pid=ids(papers,'P')
    methods=records(d,'methods');mid=ids(methods,'M')
    claims=records(d,'claims');cid=ids(claims,'C')
    questions=records(d,'research_questions');rid=ids(questions,'R')
    review=records(d,'review_sections');plan=records(d,'plan_sections')
    pmap={p['id']:p for p in papers}
    for p in papers:
        for key in ('title','venue','study_id','verification_note','screening_reason','question','source'):
            string(p,key,p['id'])
        strings(p.get('authors'),p['id']+'.authors')
        require(p.get('year') is None or (type(p['year']) is int and 1500<=p['year']<=2200),p['id']+' 年份无效')
        require(p.get('access') in ACCESS,p['id']+' 访问层级无效')
        require(p.get('screening') in STATUS,p['id']+' 筛选状态无效')
        require(p.get('verification') in ('crosschecked','user_supplied','unverified','synthetic'),p['id']+' 核验状态无效')
        for key in ('doi','url'):
            require(p.get(key) is None or isinstance(p[key],str),p['id']+'.'+key+' 需字符串或null')
        if p.get('url'):require(safe_url(p['url']),p['id']+' URL只允许http/https')
        require(isinstance(p.get('evidence'),dict),p['id']+' 缺少字段出处')
        for field in FIELDS:
            string(p,field,p['id']);string(p['evidence'],field,p['id']+'.evidence')
    for m in methods:
        for key in ('name','fit','requirements','strengths','limitations','feasibility','recommendation'):
            string(m,key,m['id'])
        refs(m.get('paper_ids'),pid,m['id']+'.paper_ids',True)
    for c in claims:
        for key in ('text','certainty','limitations'):string(c,key,c['id'])
        require(c.get('kind') in ('empirical','synthesis','proposal'),c['id']+' kind无效')
        evidence=records(c,'evidence',c['kind']=='proposal')
        for e in evidence:
            require(e.get('paper_id') in pid,c['id']+' 引用了未知文献')
            string(e,'location',c['id']);require(e.get('relation') in ('supports','contradicts','qualifies'),c['id']+' 证据关系无效')
            p=pmap[e['paper_id']]
            require(p['screening']=='include',c['id']+' 引用排除或待定文献不能用于当前综合')
            require(p['access'] in ('fulltext','abstract'),c['id']+' 仅题录或未取得资料不能支持经验论断')
    for q in questions:
        for key in ('text','inference'):string(q,key,q['id'])
        refs(q.get('method_ids'),mid,q['id']+'.method_ids')
    for s in review:
        string(s,'title','review');string(s,'text','review');refs(s.get('claim_ids'),cid,'review.claim_ids')
    keys=[]
    for s in plan:
        string(s,'key','plan');string(s,'title','plan');string(s,'text','plan');keys.append(s['key'])
        refs(s.get('question_ids'),rid,'plan.question_ids')
        refs(s.get('method_ids'),mid,'plan.method_ids',True)
        refs(s.get('claim_ids'),cid,'plan.claim_ids',True)
    require(set(keys)==set(PLAN_KEYS) and len(keys)==len(PLAN_KEYS),'研究方案须恰好包含十个标准章节')
    included_dois={}
    warnings=[]
    for p in papers:
        doi=normalized_doi(p.get('doi'))
        if doi:
            require(bool(re.fullmatch(r'10\.\d{4,9}/\S+',doi)),p['id']+' DOI结构无效，格式正确仍不代表真实存在')
            if p['screening']=='include':
                require(doi not in included_dois,p['id']+' 与 '+included_dois.get(doi,'')+' 的标准化DOI重复，请核对记录并保留筛选说明')
                included_dois[doi]=p['id']
        if p['screening']=='include' and p['access']=='abstract':warnings.append(p['id']+' 仅摘要，全文方法与结果仍需核实。')
        if p['verification']=='unverified':warnings.append(p['id']+' 题录尚未核实。')
    groups={}
    title_groups={}
    for p in papers:
        if p['screening']=='include':groups.setdefault(p['study_id'],[]).append(p['id'])
        key=(re.sub(r'\W+','',p['title']).casefold(),p['year'])
        title_groups.setdefault(key,[]).append(p['id'])
    for group,values in groups.items():
        if len(values)>1:warnings.append('研究标识 '+group+' 含多份报告 '+', '.join(values)+'，不得按独立研究重复计数。')
    for values in title_groups.values():
        if len(values)>1:warnings.append('题名和年份相同的候选记录 '+', '.join(values)+'，需人工确认，不自动删除。')
    if d['review_type']!='narrative':warnings.append('综述类型由输入声明；本程序未验证完整检索、筛选、偏倚评价或报告规范遵循情况。')
    cmap={c['id']:c for c in claims}
    for area,sections in (('review',review),('plan',plan)):
        for s in sections:
            cited=set(re.findall(r'\[(P[1-9][0-9]*)\]',s['text']))
            allowed={e['paper_id'] for cid_ in s['claim_ids'] for e in cmap[cid_]['evidence']}
            require(cited<=pid,area+'正文含不存在的文献编号')
            require(cited<=allowed,area+'正文引用未通过该节论断证据关联，请补齐真实证据关系')
    for c in claims:
        cited=set(re.findall(r'\[(P[1-9][0-9]*)\]',c['text']))
        require(cited<={e['paper_id'] for e in c['evidence']},c['id']+'正文引用未关联证据')
    for q in questions:
        for key in ('design','sampling','measurement','analysis'):
            section=next(s for s in plan if s['key']==key)
            require(q['id'] in section['question_ids'],q['id']+' 缺少'+key+'章节覆盖')
            require(bool(set(q['method_ids'])&set(section['method_ids'])),q['id']+' 在'+key+'章节缺少匹配方法')
    return {'papers':len(papers),'included':sum(p['screening']=='include' for p in papers),
            'claims':len(claims),'questions':len(questions),'methods':len(methods),
            'synthetic':any(p['verification']=='synthetic' for p in papers),'study_groups':len(groups),'warnings':warnings}


CSS='''*{box-sizing:border-box}body{margin:0;background:#f2f3f7;color:#202e45;font:16px/1.8 "Microsoft YaHei","PingFang SC",sans-serif}main{max-width:1180px;padding:48px 56px;margin:36px auto;background:white}h1{font-size:32px;line-height:1.45}h2{font-size:23px;margin-top:34px}h3{font-size:18px;margin-top:28px}p{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#355ca4}small,.meta{font-size:13px;color:#536175}.warning{border-left:4px solid #ae7322;padding-left:18px;color:#805018}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d9dfe8;padding:12px;text-align:left;vertical-align:top;min-width:90px;overflow-wrap:anywhere}th{background:#eaf0f8;font-weight:600}.table-wrap{overflow:auto}input{font:inherit;padding:10px 14px;width:100%;margin:14px 0 22px;border:1px solid #a7b5c8}li{margin:10px 0;overflow-wrap:anywhere}.paper{border-top:1px solid #d9dfe8;padding-top:12px}[hidden]{display:none!important}@media(max-width:700px){main{padding:24px;margin:0}h1{font-size:26px}}@media print{body{background:white;font-size:11pt}main{padding:0;margin:0;max-width:none}input,.filter-label{display:none}.table-wrap{overflow:visible}table{font-size:9pt}th,td{min-width:0;padding:6px}h2,h3{break-after:avoid}tr{break-inside:avoid}thead{display:table-header-group}.paper{break-inside:auto}[hidden]{display:revert!important}@page{size:A4;margin:17mm}}'''
SEARCH='''const box=document.getElementById('search');const groups=new Map();for(const el of document.querySelectorAll('[data-paper]')){const id=el.dataset.paper;if(!groups.has(id))groups.set(id,[]);groups.get(id).push(el)}box.addEventListener('input',()=>{let count=0;for(const els of groups.values()){const match=els.some(el=>el.textContent.toLowerCase().includes(box.value.toLowerCase()));for(const el of els)el.hidden=!match;if(match)count++}document.getElementById('count').textContent='显示 '+count+' 条记录';});'''
def esc(x):return html.escape(str(x),quote=True)
def page(title,content,search=False):
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>'+CSS+'</style></head><body><main>'+content+'</main>'+('<script>'+SEARCH+'</script>' if search else '')+'</body></html>'
def md_cell(x):return str(x).replace('|','／').replace('\n','<br>')
def md_html(lines):
    result=[]
    for value in lines:
        for line in value.splitlines():
            m=re.match(r'^(#{1,3}) (.*)',line)
            if m:n=len(m[1]);result.append(f'<h{n}>'+esc(m[2])+f'</h{n}>')
            elif line.strip():result.append('<p>'+esc(line)+'</p>')
    return '\n'.join(result)
def table(headers,rows,search=False):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr'+(' data-paper="'+esc(row[0])+'"' if search else '')+'>'+''.join('<td>'+esc(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def md_table(headers,rows):
    return '\n'.join(['| '+' | '.join(map(md_cell,headers))+' |','| '+' | '.join('---' for _ in headers)+' |']+['| '+' | '.join(map(md_cell,row))+' |' for row in rows])
def save(out,name,text):
    (out/name).write_text(text,encoding='utf-8')
def docs(out,stem,lines,html_content=None,search=False):
    original=lines[0].lstrip('# ');title=original+' '+stem[2:]
    display=['# '+title]+lines[1:]
    content=html_content.replace('<h1>'+esc(original)+'</h1>','<h1>'+esc(title)+'</h1>',1) if html_content is not None else md_html(display)
    save(out,stem+'.md','\n\n'.join(display)+'\n')
    save(out,stem+'.html',page(title,content,search))
def citation(p):
    return f'[{p["id"]}] '+', '.join(p['authors'])+f'（{p["year"] or "年份未提供"}）'+p['title']+'。'+p['venue']+'。'+(f'DOI: {p["doi"]}。' if p.get('doi') else '')+(p.get('url') or '')+f' 核验：{VERIFY[p["verification"]]}；访问：{ACCESS[p["access"]]}。'
def render(d,out):
    stats=validate(d);require(not out.exists(),'输出目录已存在，请使用新目录避免覆盖')
    out.parent.mkdir(parents=True,exist_ok=True);temp=Path(tempfile.mkdtemp(prefix='.research-',dir=out.parent))
    try:
        banner='合成研究资料演示：记录不是真实论文，内容不能作为学术证据或发表引用。' if stats['synthetic'] else '研究草稿：仅反映实际提供的资料，未核实内容须进一步确认。'
        head=['# '+d['title'],banner,'范围：'+d['scope'],'检索与材料来源：'+d['search_log']]
        headers=['编号','题名与年份','访问/筛选','研究设计','主要发现','局限']
        rows=[[p['id'],p['title']+' / '+str(p['year'] or '待核'),ACCESS[p['access']]+' / '+STATUS[p['screening']],p['design'],p['findings'],p['limitations']] for p in d['papers']]
        details=[];detail_html=[]
        for p in d['papers']:
            x=['## '+p['id']+' '+p['title'],citation(p),'研究标识：'+p['study_id'],'来源：'+p['source'],'筛选：'+STATUS[p['screening']]+'；理由：'+p['screening_reason'],'题录核验：'+p['verification_note'],'研究问题：'+p['question']]
            for field in FIELDS:x+=['### '+LABELS[field],p[field],'出处：'+p['evidence'][field]]
            details+=x;detail_html.append('<section class="paper" data-paper="'+esc(p['id'])+'">'+md_html(x)+'</section>')
        filter_html='<label for="search" class="filter-label">搜索题名、编号、方法或发现</label><input id="search" type="search" placeholder="输入关键词，仅在本页搜索"><p id="count" class="meta">显示 '+str(len(rows))+' 条记录</p>'
        docs(temp,'01文献矩阵',head+['## 文献概览',md_table(headers,rows)]+details,md_html(head)+filter_html+table(headers,rows,True)+''.join(detail_html),True)
        mh=['方法','适配问题','条件与资源','优势','限制','选择建议']
        mr=[[m['id']+' '+m['name'],m['fit'],m['requirements']+'\n'+m['feasibility'],m['strengths'],m['limitations'],m['recommendation']] for m in d['methods']]
        method_sources=['方法参照 '+m['id']+'：'+(', '.join(m['paper_ids']) if m['paper_ids'] else '研究设计建议，未引用具体论文') for m in d['methods']]
        docs(temp,'02方法比较',head+[md_table(mh,mr)]+method_sources,md_html(head)+table(mh,mr)+md_html(method_sources))
        review=head+['综述类型：'+REVIEW[d['review_type']]]
        for section in d['review_sections']:
            review+=['## '+section['title'],section['text'],'论断编号：'+', '.join(section['claim_ids'])]
        review+=['## 论断与证据']
        for c in d['claims']:
            review+=['### '+c['id']+' '+KIND[c['kind']],c['text'],'证据强度与判断：'+c['certainty'],'限制：'+c['limitations']]
            review += ['['+e['paper_id']+'] '+e['location']+'；关系：'+RELATION[e['relation']] for e in c['evidence']]
        review+=['## 参考资料']+[citation(p) for p in d['papers'] if p['screening']=='include']
        docs(temp,'03综述草稿',review)
        plan=head+['## 研究问题']
        for q in d['research_questions']:plan+=[q['id']+' '+q['text'],'目标推断：'+q['inference']+'；方法：'+', '.join(q['method_ids'])]
        for s in d['plan_sections']:plan+=['## '+s['title'],s['text'],'关联问题：'+', '.join(s['question_ids'])+'；方法：'+(', '.join(s['method_ids']) or '本节无指定方法')+'；论断：'+(', '.join(s['claim_ids']) or '本节为方案设计内容')]
        docs(temp,'04研究方案',plan)
        audit=head+['## 来源状态']+[citation(p)+'\n筛选：'+STATUS[p['screening']]+'；'+p['screening_reason'] for p in d['papers']]+['## 假设与待确认']+d['assumptions']+['## 自动核查提示']+(stats['warnings'] or ['未发现程序覆盖的提示项，仍需人工核验事实。'])+['## 使用边界','结构检查不等于完成全文阅读、题录外部核验、科研质量或伦理审查。核验值来自输入，需要人工审核。']
        docs(temp,'05来源与核查清单',audit)
        ch=['论断','类型与判断','来源及位置','用于综述','用于方案']
        cr=[]
        for c in d['claims']:
            proof='；'.join(e['paper_id']+' '+e['location']+' '+RELATION[e['relation']] for e in c['evidence']) or '研究建议，无经验性证据引用'
            cr.append([c['id']+' '+c['text'],KIND[c['kind']]+' / '+c['certainty'],proof,'；'.join(s['title'] for s in d['review_sections'] if c['id'] in s['claim_ids']) or '未用于正文','；'.join(s['title'] for s in d['plan_sections'] if c['id'] in s['claim_ids']) or '未用于方案'])
        qh=['问题','目标推断','方法','设计/抽样/测量/分析覆盖']
        qr=[[q['id']+' '+q['text'],q['inference'],', '.join(q['method_ids']),'；'.join(s['title'] for s in d['plan_sections'] if q['id'] in s['question_ids'] and s['key'] in ('design','sampling','measurement','analysis'))] for q in d['research_questions']]
        counts=f'记录{stats["papers"]}条，纳入{stats["included"]}条，按用户study_id分为{stats["study_groups"]}组。分组数不是已证实的独立研究数。'
        chain=head+['## 记录与研究分组',counts,'## 论断证据链',md_table(ch,cr),'## 研究问题对齐',md_table(qh,qr)]
        docs(temp,'06证据链与研究对齐',chain,md_html(head+['## 记录与研究分组',counts,'## 论断证据链'])+table(ch,cr)+md_html(['## 研究问题对齐'])+table(qh,qr))
        save(temp,'research.json',json.dumps(d,ensure_ascii=False,indent=2)+'\n')
        links=''.join('<li><a href="'+esc(p.name)+'">'+esc(p.name)+'</a></li>' for p in sorted(temp.iterdir()) if p.is_file())
        save(temp,'index.html',page(d['title'],md_html(head)+'<h2>研究成果文件</h2><ul>'+links+'</ul>'))
        temp.rename(out)
    except Exception:
        shutil.rmtree(temp);raise
    return stats
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output');p.add_argument('--check-only',action='store_true');args=p.parse_args()
    try:
        d=json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        if args.check_only:
            result=validate(d);print(json.dumps({'status':'ok','mode':'check-only',**result},ensure_ascii=False))
        else:
            require(bool(args.output),'生成需要--output，只读核验请使用--check-only')
            result=render(d,Path(args.output).resolve());print(json.dumps({'status':'ok','output':str(Path(args.output).resolve()),**result},ensure_ascii=False))
        return 0
    except (ResearchError,OSError,ValueError,TypeError,KeyError) as e:
        print(json.dumps({'status':'error','message':str(e)},ensure_ascii=False),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
