"""V6 report preparation: DOM account proof, P0 evidence, types and redaction.
Only validated display data leaves this module. No network or browser operations.
"""
from __future__ import annotations
import copy
import datetime as dt
from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPECS = {r['check_id']: r for r in json.loads((ROOT/'references/data-manifest.json').read_text())}
STATES = {'observed', 'zero', 'unavailable', 'not_applicable'}
PRIVATE_KEYS = {'cookie','setcookie','authorization','accesstoken','refreshtoken','apikey','password','secret','clientsecret','privatekey','sessionid','token','groupid','storeid','merchantgroupid','storeref','poiid','shopid','merchantid','accountid','lifeaccountid','lifebizid','providerstoreid','accountref','backendparams','queryparams','backendurl','storekeys','matchkey'}
SECRET_TEXT = re.compile(r'(?i)(?:cookie|authorization|access[_ -]?token|refresh[_ -]?token|api[_ -]?key|password|client[_ -]?secret)\s*[:=]|\bbearer\s+\S+|-----BEGIN .*PRIVATE KEY-----|(?:groupid|store_id|poi_id|shop_id|merchant_id|account_id|life_account_biz_ids|life_biz_view_id)=')
INTERNAL_DISPLAY_TEXT = re.compile(r'视觉稿|视觉伴侣|视觉评审|虚构门店|样例数据|示例门店|模板示例|本页不能用于真实经营决策|正式运行在真实', re.I)
RISKY_PRICE_ADVICE = re.compile(r'改价|调价|降价|涨价|价格.{0,8}(?:上调|下调|提高|降低)|(?:上调|下调|提高|降低).{0,8}价格|折扣.{0,8}(?:加深|加大|提高|降低)|[¥￥]\s*\d+', re.I)

def redaction_check(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if re.sub(r'[^a-z0-9]','',key.lower()) in PRIVATE_KEYS:
                raise ValueError('报告包含凭据或后台标识字段，拒绝交付')
            redaction_check(child)
    elif isinstance(value, list):
        for child in value: redaction_check(child)
    elif isinstance(value, str) and (SECRET_TEXT.search(value) or re.search(r'(?i)<\s*(?:script|iframe|object)\b', value)):
        raise ValueError('报告包含凭据、后台参数或可执行代码文本，拒绝交付')

def keys(obj: dict, allowed: str, where: str) -> None:
    if not isinstance(obj, dict): raise ValueError(f'{where}必须为对象')
    unknown = set(obj)-set(allowed.split())
    if unknown: raise ValueError(f'{where}含未允许字段: '+','.join(sorted(unknown)))

def iso_date(v: Any) -> dt.date:
    if not isinstance(v,str): raise ValueError('日期必须为YYYY-MM-DD')
    return dt.date.fromisoformat(v.replace('.','-'))

def window(v: Any) -> None:
    keys(v,'start end','window')
    if iso_date(v.get('start')) > iso_date(v.get('end')): raise ValueError('窗口起始日期晚于结束日期')

def state_value(status: str, raw: Any, reason: Any = None) -> None:
    if status not in STATES: raise ValueError('非法数据状态')
    if status in {'unavailable','not_applicable'}:
        if raw is not None or not isinstance(reason,str) or not reason.strip():
            raise ValueError('缺失/不适用必须为null并说明原因，不得写零值')
    elif status == 'zero':
        if isinstance(raw,bool) or not (raw == 0 or raw == []): raise ValueError('zero状态必须对应明确0或空榜单')
    elif raw is None or raw == '' or raw == [] or (isinstance(raw,(int,float)) and not isinstance(raw,bool) and raw == 0):
        raise ValueError('observed状态必须有事实，数值0应标zero')
    if isinstance(raw,float) and not math.isfinite(raw): raise ValueError('指标不能为NaN或无穷值')

def display_schema(data: dict) -> None:
    keys(data,'report store collection holidays overview metrics actions insights timeline sources missing next_tasks','report_data')
    schemas={
        'report':'title year edition status_label report_date window window_label footer',
        'store':'name city district category_l1 category_l2 mode count names categories',
        'collection':'route route_label platform_p0 backend_p0 key_gaps account_check scope_check release_ready',
        'overview':'headline emphasis summary source_note season_note season_differences store_translation',
        'holidays':'mid_autumn national_day',
        'insights':'trends hotspots peers ads products',
    }
    for k, allowed in schemas.items(): keys(data.get(k,{}),allowed,k)
    for k in ['platform_p0','backend_p0']:
        if k in data.get('collection',{}): keys(data['collection'][k],'checked total checked_ids',k)
    if 'account_check' in data.get('collection',{}): keys(data['collection']['account_check'],'status merchant_name checked_at','account_check')
    if 'scope_check' in data.get('collection',{}): keys(data['collection']['scope_check'],'status mode store_count display_name store_names','scope_check')
    for h in data['holidays'].values(): keys(h,'date scene start end','holiday')
    for s in data['overview'].get('season_differences',[]):keys(s,'title body','season_differences')
    keys(data['overview'].get('store_translation',{}),'label headline description highlight_action_ids','store_translation')
    lists={
        'metrics':'label value unit foot status scope source_ids record_id store_index',
        'actions':'id order action_name dimensions kind tone holiday tag title description evidence deadline owner why current proposal steps measurement condition source_ids evidence_item_ids basis_type applicable_store_indices applicable_categories',
        'sources':'id priority status name platform path scope window note',
        'timeline':'date title tasks owner',
        'missing':'field status impact next_step',
        'next_tasks':'id icon title description prompt',
    }
    for key, allowed in lists.items():
        if not isinstance(data.get(key),list):raise ValueError(f'{key}必须为数组')
        for v in data[key]:keys(v,allowed,key)
    for v in data['insights'].values():
        keys(v,'title description badge status source_ids items stats bars table takeaway empty_title empty_body history_scope','insight')
        for x in v.get('items',[]):keys(x,'title body label tone','insight.items')
        for x in v.get('stats',[]):keys(x,'label value','insight.stats')
        for x in v.get('bars',[]):keys(x,'label percent value','insight.bars')
        if 'table' in v: keys(v['table'],'columns rows','insight.table')

    visible = {
        'report': data.get('report', {}),
        'store': data.get('store', {}),
        'collection': data.get('collection', {}),
        'overview': data.get('overview', {}),
        'metrics': data.get('metrics', []),
        'actions': data.get('actions', []),
        'insights': data.get('insights', {}),
        'timeline': data.get('timeline', []),
        'sources': data.get('sources', []),
        'missing': data.get('missing', []),
        'next_tasks': data.get('next_tasks', []),
    }
    if INTERNAL_DISPLAY_TEXT.search(json.dumps(visible, ensure_ascii=False)):
        raise ValueError('用户可见内容包含内部样例或视觉制作说明，拒绝交付')

def approved_account_handoff(context: dict) -> tuple[dict, dict]:
    """Validate the DOM proof produced by this Skill before any report work."""
    account=context.get('account_consistency')
    if not isinstance(account,dict):raise ValueError('缺少账号一致性校验结果')
    if account.get('checked_by')!='local-life-service-holiday-business':
        raise ValueError('账号一致性必须由节日经营 Skill 通过 DOM 校验')
    if account.get('method')!='dom' or account.get('entry') not in {'visible_life_data_link','existing_verified_tab'}:
        raise ValueError('账号一致性必须使用页面 DOM 和可见入口，不得使用 mcp-http')
    if account.get('status')!='matched' or not account.get('merchant_name'):
        raise ValueError('账号一致性未通过，停止经营数据采集')
    clean=lambda value: re.sub(r'[\s\u200b-\u200f\u2060\ufeff]+$','',re.sub(r'^[\s\u200b-\u200f\u2060\ufeff]+','',str(value or '')))
    backend_name=clean(account.get('backend_merchant_name'))
    platform_name=clean(account.get('platform_merchant_name'))
    merchant_name=clean(account.get('merchant_name'))
    if not backend_name or not platform_name or backend_name!=platform_name or merchant_name!=backend_name:
        raise ValueError('两端页面展示的商家名称不一致，停止经营数据采集')
    target=context.get('target')
    if not isinstance(target,dict) or not target.get('display_name'):
        raise ValueError('缺少本次分析对象')
    names=target.get('store_names') or [target['display_name']]
    categories=target.get('categories') or ['通用']*len(names)
    if not isinstance(names,list) or not names or len(set(names))!=len(names):raise ValueError('分析范围名称无效')
    if not isinstance(categories,list) or len(categories)!=len(names):raise ValueError('分析范围品类无效')
    mode=target.get('mode') or ('store' if len(names)==1 else 'store_set')
    if mode not in {'store','store_set'}:raise ValueError('分析范围层级无效')
    scope={'status':'matched','mode':mode,'store_count':len(names),'display_name':target['display_name'],'store_names':names}
    return account,scope

def records_and_counts(context: dict, scope: dict) -> tuple[dict, dict]:
    items=context.get('items')
    if not isinstance(items,list):raise ValueError('缺少逐指标items，不能手填P0完成数')
    wanted=set(context['target'].get('store_keys') or []); by_id={}; complete={}; seen=set()
    source_registry=context.get('sources') or {}
    for item in items:
        if not isinstance(item,dict):raise ValueError('原始记录必须为对象')
        rid=item.get('id'); cid=item.get('check_id'); metric=item.get('metric_key'); spec=SPECS.get(cid)
        if not rid or rid in by_id:raise ValueError('原始记录id缺失或重复')
        if not spec or metric not in spec['metric_keys']:raise ValueError('原始记录check_id/metric_key不在清单中')
        if item.get('priority') != spec['priority']:raise ValueError('原始记录priority与清单不一致')
        pair=(cid,metric)
        if pair in seen:raise ValueError('同一清单子指标重复；门店明细应另存，必采统计仅用目标范围记录')
        seen.add(pair)
        source=source_registry.get(item.get('source_id'))
        if not source or source.get('platform') != ('抖音来客' if spec['platform']=='backend' else '抖音生意经'):
            raise ValueError('取数来源与清单平台不一致')
        if source.get('method')!='dom':
            raise ValueError('经营数据必须来自页面 DOM，不得使用 mcp-http 或内部接口')
        if not item.get('evidence_ref'):raise ValueError('原始记录缺少页面证据引用')
        window(item.get('window'))
        state_value(item.get('status'),item.get('raw_value'),item.get('reason'))
        raw=item.get('raw_value')
        numeric_keys={'transaction_amount','transaction_amount_change_rate','redemption_amount','redemption_amount_change_rate','refund_amount','refund_amount_change_rate','store_count','region_count','selling_store_rate','selling_store_count','avg_daily_transaction_amount_per_store','avg_daily_redemption_amount_per_store','product_count_all','product_count_selling','product_count_slow_moving','search_impressions','search_clicks','search_transactions','impression_count','business_score','douyin_account_count','store_visits','product_count_onsale','ad_spend','rating_score','review_count','traffic_impressions','traffic_visits'}
        if item['status'] in {'observed','zero'} and metric in numeric_keys and (isinstance(raw,bool) or not isinstance(raw,(int,float))):
            raise ValueError('数量、金额、评分及比率必须保存数值，不能用字符串或布尔值冒充')
        list_keys={'product_ranking_top5','search_terms','store_grade_distribution','transaction_source_by_channel','transaction_source_by_content_format','refund_reason_distribution','traffic_channel_distribution','store_ranking'}
        if item['status'] in {'observed','zero'} and metric in list_keys and not isinstance(raw,list):raise ValueError('榜单与分布必须保存数组')
        actual=item.get('actual_scope')
        if actual not in {'store','store_set','merchant'}:raise ValueError('原始取数层级不合法')
        if actual=='merchant':
            identity_keys={'merchant_name','merchant_groupid','store_count','region_count','douyin_account_count','violation_status','payment_status'}
            if item.get('use_policy') != 'identity_only' or metric not in identity_keys:raise ValueError('账号层数据不能冒充本次经营指标')
        else:
            actual_keys=item.get('scope_store_keys')
            if wanted and (not isinstance(actual_keys,list) or len(set(actual_keys))!=len(actual_keys) or set(actual_keys)!=wanted):
                raise ValueError('经营记录与本次分析范围不同')
            if actual!=scope['mode']:raise ValueError('经营记录的单/多店层级与本次分析范围不一致')
        if spec['priority']!='precheck':complete.setdefault(cid,set()).add(metric)
        by_id[rid]=item
    counts={}
    for key,prefix,total in [('platform_p0','DP0-',9),('backend_p0','BP0-',6)]:
        ids=[cid for cid,s in SPECS.items() if cid.startswith(prefix) and complete.get(cid)==set(s['metric_keys'])]
        counts[key]={'checked':len(ids),'total':total,'checked_ids':ids}
    return by_id,counts

def numeric(v: Any) -> Decimal:
    if isinstance(v,bool):raise ValueError('布尔值不是金额')
    return Decimal(re.sub(r'[¥￥,\s]','',str(v)))

def prepare_report(data: dict, context: dict, *, allow_incomplete: bool=False) -> dict:
    account,scope=approved_account_handoff(context)
    redaction_check(data)
    display_schema(data)
    records,counts=records_and_counts(context,scope)
    d=copy.deepcopy(data)
    year=int(d['report']['year']); day=iso_date(d['report']['report_date']); window(d['report']['window'])
    if day.year!=year:raise ValueError('报告年份与报告日期不一致')
    if iso_date(d['report']['window']['end'])>=day:raise ValueError('经营窗口应截至报告日前一个完整自然日')
    for h in d['holidays'].values():
        start,end=iso_date(h.get('start')),iso_date(h.get('end'))
        if start.year!=year or end.year!=year or start>end:raise ValueError('节日日期范围或年份无效')
        h['date']=start.strftime('%m.%d')+'—'+end.strftime('%m.%d')
    for key,count in counts.items():
        supplied=d['collection'].get(key)
        if supplied is not None and supplied != count:raise ValueError('P0声明与原始逐指标记录不一致')
        d['collection'][key]=count
    incomplete=any(v['checked']<v['total'] for v in counts.values())
    if incomplete and not allow_incomplete:raise ValueError('P0明细未齐，不能正式交付')
    if incomplete and 'P0采集未完成' not in d['report']['status_label']:raise ValueError('预览必须显示P0采集未完成')
    d['collection']['account_check']={k:account.get(k) for k in ('status','merchant_name','checked_at')}
    # Compatibility field for the static template. It is derived from the chosen
    # analysis range and never compares platform store counts.
    d['collection']['scope_check']=scope
    d['collection']['release_ready']=not incomplete
    name=scope['display_name']
    if d['store'].get('name')!=name:raise ValueError('报告对象与已核对范围名称不一致')
    categories=context['target'].get('categories') or ['通用']*scope['store_count']
    d['store'].update(mode=scope['mode'],count=scope['store_count'],names=scope['store_names'],categories=categories)
    if scope['mode']=='store_set':
        d['store']['city']='';d['store']['district']=''
        d['store']['category_l1']='多门店';d['store']['category_l2']=' / '.join(sorted(set(c for c in categories if c))) or '品类待确认'
    elif d['store'].get('category_l2') and d['store']['category_l2']!=categories[0]:
        raise ValueError('单店品类必须来自已确认的门店证据')
    # Sources are the trusted private registry's display projection, never URLs/IDs.
    registry=context.get('sources') or {}
    for s in d['sources']:
        if s['priority']=='historical_reference':continue
        trusted=registry.get(s['id'])
        if not trusted:raise ValueError('展示来源没有任务内原始来源记录')
        for field in ['platform','path','scope','window']:
            if s.get(field)!=trusted.get(field):raise ValueError('展示来源的平台、路径、层级或窗口与原始记录不一致')
    for m in d['metrics']:
        item=records.get(m.get('record_id'))
        if not item:raise ValueError('展示指标缺少可解析record_id')
        if m['scope']!=item['actual_scope'] or m['source_ids']!=[item['source_id']] or m['status']!=item['status']:
            raise ValueError('展示指标与原始记录的层级、来源或状态不一致')
        if item['window']!=d['report']['window']:raise ValueError('经营基线卡窗口与原始记录不一致；不能混入其他周期')
        if m['scope']=='merchant':raise ValueError('账号元信息不作为经营指标卡；展示已核对门店数据')
        raw=item['raw_value']
        if item['status'] in {'unavailable','not_applicable'}:
            if m['value'] not in (None,'','—','暂无数据','不适用'):raise ValueError('缺失指标不得伪装成数值')
            m['value']='—'
        elif isinstance(raw,(int,float)) and not isinstance(raw,bool):
            try:
                if numeric(m['value'])!=numeric(raw):raise ValueError('展示数值与原始数值不一致')
            except InvalidOperation:raise ValueError('展示数值格式不可校验')
        elif m['value']!=raw:raise ValueError('展示值与原始值不一致')
    for a in d['actions']:
        indices=a.get('applicable_store_indices')
        if not isinstance(indices,list) or not indices or any(type(i)!=int or i<1 or i>scope['store_count'] for i in indices) or len(set(indices))!=len(indices):
            raise ValueError('建议必须标明有效的适用门店序号')
        allowed_categories=set(categories[i-1] for i in indices)
        declared=a.get('applicable_categories')
        if not isinstance(declared,list) or not declared or not set(declared).issubset(allowed_categories|{'通用'}):
            raise ValueError('建议品类缺少门店事实支持')
        if set(declared)!={'通用'} and any(c not in declared for c in allowed_categories):
            raise ValueError('品类专属建议覆盖了不适用门店')
        if a.get('basis_type') not in {'store_fact','strategy'}:raise ValueError('建议须区分门店事实与策略建议')
        evidence=a.get('evidence_item_ids')
        if not isinstance(evidence,list) or not evidence or any(i not in records for i in evidence):raise ValueError('建议证据明细不可解析')
        if any(records[i]['source_id'] not in a['source_ids'] for i in evidence):raise ValueError('建议证据与来源不一致')
        if a['basis_type']=='store_fact' and not any(records[i]['status'] in {'observed','zero'} for i in evidence):raise ValueError('缺失数据不能作为已证实门店事实')
        if a['kind']=='延续亮点' and not any(records[i]['status']=='observed' for i in evidence):raise ValueError('延续亮点需要已有事实支持，不能用全零/缺失数据凑标签')
        advice_text=json.dumps({k:a.get(k) for k in ('action_name','title','description','why','current','proposal','steps','condition')},ensure_ascii=False)
        if RISKY_PRICE_ADVICE.search(advice_text):raise ValueError('节日经营建议不得包含改价、调价、折扣加深或具体价格建议')
    # Current-window zero spend is never sufficient proof of lifetime no-spend.
    output_text=json.dumps(d,ensure_ascii=False)
    if any(t in output_text for t in ['无投放历史','没有投放历史','从未投放']):
        proof=context.get('ad_history_evidence') or {}
        if proof.get('coverage')!='all_history' or not proof.get('evidence_ref') or proof.get('source_id') not in registry:
            raise ValueError('近30日无消耗不能推断全部历史未投放')
    start,end=d['report']['window']['start'],d['report']['window']['end']
    d['report']['window_label']=start+'—'+end
    # V6 presentation: keep evidence internally, but omit missing modules and
    # source acquisition copy from the merchant-facing report.
    d['metrics']=[m for m in d['metrics'] if m.get('status') not in {'unavailable','not_applicable'}]
    d['overview']['source_note']=''
    d['overview']['season_note']=''
    redaction_check(d)
    return d

def output_path(requested: Path, data: dict, *, data_only: bool=False) -> Path:
    if data_only:return requested
    suffix=''
    status=data['report']['status_label']
    if 'P0采集未完成' in status:suffix='-运行中预览'
    stem=re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',data['store']['name'])[:80]
    return requested.parent/f'{stem}-{data["report"]["year"]}中秋国庆经营方案{suffix}.html'
