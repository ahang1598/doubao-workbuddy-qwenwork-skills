#!/usr/bin/env python3
"""Render a single-file holiday business report from structured JSON.

Normal use:
    python3 scripts/render_report.py report_data.json report.html

The --bootstrap-base option is only used to rebuild the checked-in template from
the approved visual. Normal rendering needs no access to that source file.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from report_guard import prepare_report, output_path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "assets" / "miaoda-template" / "index.html"
DATA_RE = re.compile(
    r'(<script\s+id="report-data"\s+type="application/json">).*?(</script>)',
    re.DOTALL,
)


BODY = r'''
<style>
.status-chip{display:inline-flex;align-items:center;gap:5px;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:600;white-space:nowrap}.status-chip::before{content:"";width:6px;height:6px;border-radius:50%}.status-observed{background:#e8f5ee;color:#247959}.status-observed::before{background:#2f8b68}.status-zero{background:#ebf1fa;color:#537cad}.status-zero::before{background:#5f80ad}.status-unavailable{background:#fff1e1;color:#ab6526}.status-unavailable::before{background:#cb7b32}.status-na{background:#eff3f5;color:#657983}.status-na::before{background:#91a0a6}.scope-chip{display:inline-flex;border:1px solid #dce6e2;border-radius:5px;padding:2px 6px;font-size:10px;font-weight:600;color:#6f827b;background:#f8fbf9;white-space:nowrap}.scope-merchant{color:#8a6a31;border-color:#eadfca;background:#fffaf0}.seasonal-intro{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(310px,.9fr)}.festival-side{position:relative;min-height:238px;border-left:1px solid #dbe9e1;display:flex;align-items:center;justify-content:center;overflow:hidden;background:linear-gradient(145deg,#f8f3e7,#eef5ef)}.festival-art{width:330px;max-width:95%;height:auto}.festival-dates{position:absolute;left:20px;right:20px;bottom:14px;display:flex;justify-content:space-between;gap:10px}.festival-date{display:flex;align-items:center;gap:10px;padding:7px 10px;border:1px solid #dfd4b6;background:#fffbeed9;border-radius:8px;font-size:11px;color:#7b6b48}.festival-date b{font-size:13px}.festival-date small{display:block;font-size:8px;letter-spacing:.08em;font-weight:450}.festival-date.national{color:#864f43;border-color:#e0c6bc;background:#fff7f4df}.holiday-overview{border-top:1px solid #dbe9e1;padding:22px 28px;background:#fffefa}.overview-heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:16px}.overview-heading h3{font-size:17px}.overview-heading span{font-size:12px;color:#8a999f}.trend-narrative{display:grid;grid-template-columns:1fr 1fr;gap:12px}.trend-prose{border:1px solid #e8ece8;border-radius:10px;padding:14px 16px;background:#fff}.trend-prose h4{font-size:13px;margin-bottom:5px}.trend-prose p{font-size:12px;line-height:1.8;color:#798b87}.overview-source{margin-top:14px;display:flex;justify-content:space-between;gap:16px;align-items:center;color:#8a999f;font-size:11px}.store-translation{border-top:1px solid #dbe9e1;padding:19px 28px;display:flex;justify-content:space-between;align-items:center;gap:20px}.translation-label{font-size:11px;color:#6d8b80}.store-translation h3{font-size:18px;margin:4px 0}.store-translation p{font-size:13px;color:#72857e}.action-name{font-size:12px;color:#55766c;font-weight:650}.dimension-tags{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 12px}.dimension-tag{font-size:10px;padding:3px 6px;border-radius:4px;background:#f1f5f3;color:#71877e}.data-card{padding:18px;border:1px solid var(--line);border-radius:12px;background:#fff}.data-card h4{font-size:14px;margin-bottom:5px}.data-card p{font-size:12px;color:#7e8e93;line-height:1.8}.insight-empty{padding:34px;border:1px dashed #dbe3e5;border-radius:10px;background:#fafcfc;text-align:center;color:#809198}.insight-empty strong{display:block;color:#506a72;margin-bottom:6px}.source-group{margin-top:22px}.source-group:first-child{margin-top:0}.source-group-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.source-group-head h3{margin:0!important}.source-group-head span{font-size:11px;color:#8b999f}.source-status-cell{display:flex;align-items:center;gap:8px;min-width:125px}.modal-wide{width:min(980px,calc(100vw - 32px))}.next-hidden{display:none!important}
@media(max-width:700px){.seasonal-intro{grid-template-columns:1fr}.festival-side{border-left:0;border-top:1px solid #dbe9e1}.trend-narrative{grid-template-columns:1fr}.store-translation{align-items:flex-start;flex-direction:column}.overview-source{align-items:flex-start;flex-direction:column}.source-status-cell{min-width:0}}
.metric-label{display:block!important}.metric-name{display:block;white-space:normal;word-break:normal;overflow-wrap:break-word}.metric-badges{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.metric-badges>*{flex-shrink:0}.metric-number{margin-top:10px}.metric{min-width:0}.overview-source,.source-line,.source-box,.status-observed{display:none!important}.data-availability{display:none;margin:14px 0 0;padding:11px 14px;border:1px solid #eadfca;border-radius:8px;background:#fffaf0;color:#8a6a31;font-size:12px;line-height:1.7}.data-availability.show{display:block}
</style>
<aside class="sidebar">
  <p class="outline-title">本次经营方案</p>
  <nav class="nav" aria-label="报告目录">
    <a class="active" href="#overview"><svg class="icon"><use href="#i-grid"/></svg>经营总览</a>
    <a href="#actions"><svg class="icon"><use href="#i-list"/></svg>经营调整<span class="count" id="navActionCount"></span></a>
    <a href="#evidence"><svg class="icon"><use href="#i-chart"/></svg>双节消费趋势<span class="count">05</span></a>
    <a href="#schedule"><svg class="icon"><use href="#i-calendar"/></svg>双节执行安排</a>
    <a href="#next" id="nextNav"><svg class="icon"><use href="#i-spark"/></svg>继续完成任务</a>
  </nav>
  <div class="sidebar-bottom"><b>月满中秋 · 共赴国庆</b><p>聚焦商品、内容与节日接待。</p></div>
</aside>
<main><div class="content">
<section id="overview">
  <div class="page-head">
    <div><div class="eyebrow"><span class="season-edition">双节特辑</span>HOLIDAY BUSINESS REPORT · <span id="reportYear"></span></div><h1 id="reportTitle"></h1><div class="store"><svg class="icon"><use href="#i-pin"/></svg><b id="storeName"></b><span class="dotsep">/</span><span id="storeLocation"></span><span class="dotsep">/</span><span id="storeCategory"></span></div></div>
    <div class="report-meta"><div>报告日 <span id="reportDate"></span> <span class="dotsep">·</span> <span id="windowLabel"></span></div></div>
  </div>
  <div class="strategy">
    <div class="seasonal-intro">
      <div class="strategy-main"><div class="ai-label"><svg class="icon"><use href="#i-spark"/></svg>AI 双节经营总览</div><h2><span id="overviewHeadline"></span><br><em id="overviewEmphasis"></em></h2><p class="strategy-desc" id="overviewSummary"></p><div class="overview-kicker" id="overviewSourceNote"></div></div>
      <div class="festival-side">
        <svg class="festival-art" viewBox="0 0 360 240" fill="none" aria-hidden="true"><defs><radialGradient id="moon-gold" cx=".35" cy=".28" r=".78"><stop stop-color="#fcf5d9"/><stop offset=".67" stop-color="#e9d69d"/><stop offset="1" stop-color="#cfb878"/></radialGradient><linearGradient id="red-ribbon" x1="256" y1="90" x2="291" y2="220" gradientUnits="userSpaceOnUse"><stop stop-color="#bc6e51"/><stop offset="1" stop-color="#8f4436"/></linearGradient></defs><circle cx="156" cy="104" r="86" stroke="#c3ad76" stroke-opacity=".3"/><circle cx="156" cy="104" r="74" fill="url(#moon-gold)"/><ellipse cx="173" cy="122" rx="151" ry="47" transform="rotate(-23 173 122)" stroke="#b49a66" stroke-opacity=".3"/><path d="M27 203C90 186 165 225 247 202c30-9 53-11 90-7" stroke="#b5a17d" stroke-opacity=".3"/><text x="151" y="89" fill="#947e49" font-family="Songti SC,serif" font-size="23" letter-spacing="5">中秋</text><text x="153" y="112" fill="#a5915b" font-size="8" letter-spacing="2.5">月满 · 人团圆</text><path d="M177 188v-29h16v-24h22v53h12v-53l10-15 10 15v53h18v-48h21v48h19" fill="#d4b78755" stroke="#bda57c"/><path d="M251 79c14 6 30 8 45 5v125l-22-12-23 10V79Z" fill="url(#red-ribbon)"/><text x="264" y="139" fill="#f5e3bd" font-family="Songti SC,serif" font-size="19">国</text><text x="264" y="164" fill="#f5e3bd" font-family="Songti SC,serif" font-size="19">庆</text></svg>
        <div class="festival-dates"><div class="festival-date"><b>中秋<small id="midDate"></small></b><span id="midScene"></span></div><div class="festival-date national"><b>国庆<small id="nationalDate"></small></b><span id="nationalScene"></span></div></div>
      </div>
    </div>
    <div class="holiday-overview"><div class="overview-heading"><h3>双节期间，经营有哪些不一样？</h3><span>从消费变化，看商品与运营的调整方向</span></div><div class="trend-narrative" id="seasonDifferences"></div></div>
    <div class="store-translation"><div><div class="translation-label"><svg class="icon"><use href="#i-pin"/></svg><span id="translationLabel"></span></div><h3 id="translationHeadline"></h3><p id="translationDescription"></p></div><div class="strategy-points" id="strategyPoints"></div></div>
  </div>
  <div class="baseline" id="metrics" aria-label="门店经营基线"></div><p class="data-availability" id="dataAvailability"></p>
</section>
<section class="section" id="actions"><div class="section-header"><div><div class="section-heading"><span class="section-index">01</span><h2>双节经营调整<span id="actionCount"></span></h2></div><p class="section-desc">每项标明具体动作与经营维度，展开查看改什么、为什么改。</p></div></div><div class="priority-grid" id="priorityGrid"></div><div class="secondary-grid" id="secondaryGrid"></div><p class="filter-caption"><svg class="icon"><use href="#i-info"/></svg><span id="filterCaption"></span></p></section>
<section class="section" id="evidence"><div class="section-header"><div><div class="section-heading"><span class="section-index">02</span><h2>双节消费趋势</h2></div><p class="section-desc">从消费趋势、热点、同行、投流与商品，看到本次门店如何承接。</p></div><span class="pill outline">认知 × 门店 × 市场</span></div><div class="insights"><div class="insight-tabs" role="tablist" aria-label="五类经营洞察"><button id="tab-trends" class="active" data-insight="trends" role="tab" aria-selected="true"><svg class="icon"><use href="#i-chart"/></svg>消费趋势</button><button id="tab-hotspots" data-insight="hotspots" role="tab"><svg class="icon"><use href="#i-spark"/></svg>热点洞察</button><button id="tab-peers" data-insight="peers" role="tab"><svg class="icon"><use href="#i-people"/></svg>同行动作</button><button id="tab-ads" data-insight="ads" role="tab"><svg class="icon"><use href="#i-chart"/></svg>投流复盘</button><button id="tab-products" data-insight="products" role="tab"><svg class="icon"><use href="#i-box"/></svg>商品诊断</button></div><div class="insight-body" id="insightPanel" role="tabpanel"></div></div></section>
<section class="section" id="schedule"><div class="section-header"><div><div class="section-heading"><span class="section-index">03</span><h2>把调整，放进双节节奏里</h2></div><p class="section-desc">按门店当前基础安排节前准备、节中执行与复盘。</p></div><span class="meta">建议执行安排</span></div><div class="timeline" id="timeline"></div></section>
<section class="section" id="next"><div class="section-header"><div><div class="section-heading"><span class="section-index">04</span><h2>在豆包办公，继续完成</h2></div><p class="section-desc">复制任务说明，调用对应技能继续完成。</p></div></div><div class="skill-grid" id="nextTasks"></div></section>
</div></main>
<dialog id="detailDialog" aria-labelledby="modalTitle"><div class="modal-head"><div><p id="modalEyebrow"></p><h2 id="modalTitle"></h2></div><button class="close" aria-label="关闭详情"><svg class="icon"><use href="#i-close"/></svg></button></div><div class="modal-body" id="modalBody"></div><div class="modal-footer" id="modalFooter"></div></dialog><div id="toast" class="toast" role="status" aria-live="polite"></div>
<script id="report-data" type="application/json">{}</script>
<script>
'use strict';
const EMBEDDED_DATA=JSON.parse(document.getElementById('report-data').textContent),D=window.REPORT_DATA&&typeof window.REPORT_DATA==='object'?window.REPORT_DATA:EMBEDDED_DATA,$=id=>document.getElementById(id);let insight='trends',copyPayload='',toastTimer;
const E=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const I=n=>'<svg class="icon" aria-hidden="true"><use href="#i-'+E(n)+'"/></svg>';
const list=v=>Array.isArray(v)?v:[];
const statuses={observed:['','status-observed'],zero:['零值','status-zero'],unavailable:['暂无数据','status-unavailable'],not_applicable:['不适用','status-na']};
function statusChip(s){const x=statuses[s]||statuses.unavailable;return '<span class="status-chip '+x[1]+'">'+x[0]+'</span>'}
function scopeChip(s){const merchant=s==='merchant';return '<span class="scope-chip '+(merchant?'scope-merchant':'')+'">'+(merchant?'账号信息':s==='store_set'?'所选门店汇总':'单店数据')+'</span>'}
function put(id,v){const el=$(id);if(el)el.textContent=v??''}
const moduleHasData=x=>x&&x.status!=='unavailable'&&x.status!=='not_applicable'&&(list(x.items).length||list(x.stats).length||list(x.bars).length||list(x.table?.rows).length||String(x.takeaway||'').trim());
function configureModules(){const names={trends:'消费趋势',hotspots:'热点洞察',peers:'同行动作',ads:'投流复盘',products:'商品诊断'},available=Object.keys(names).filter(k=>moduleHasData(D.insights?.[k])),missing=Object.keys(names).filter(k=>!moduleHasData(D.insights?.[k]));document.querySelectorAll('[data-insight]').forEach(b=>{if(!available.includes(b.dataset.insight))b.remove()});if(!available.length){$('evidence').hidden=true;document.querySelector('a[href="#evidence"]')?.remove()}else{insight=available[0];renderInsight()}const missingFields=[...missing.map(k=>names[k]),...list(D.missing).map(x=>x.field).filter(Boolean)],unique=[...new Set(missingFields)];if(unique.length){const el=$('dataAvailability');el.textContent=unique.join('、')+'暂无数据，相关模块已隐藏。';el.classList.add('show')}}
function init(){if(D.collection?.account_check?.status!=='matched'){document.querySelector('main').innerHTML='<div class="content"><h1>尚未通过账号一致性校验</h1><p>请先完成商家账号校验后再生成经营方案。</p></div>';document.querySelector('.sidebar').hidden=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);return;}document.title=(D.report?.title||'中秋国庆经营方案')+' · '+(D.store?.name||'门店');put('reportYear',D.report?.year);put('reportTitle',D.report?.title);put('storeName',D.store?.name+' · '+(D.store?.count||1)+'家门店');put('storeLocation',D.store?.mode==='store_set'?'本次分析范围':([D.store?.city,D.store?.district].filter(Boolean).join(' · ')||'区域待确认'));put('storeCategory',[D.store?.category_l1,D.store?.category_l2].filter(Boolean).join(' · '));put('reportDate',D.report?.report_date);put('windowLabel',D.report?.window_label);put('overviewHeadline',D.overview?.headline);put('overviewEmphasis',D.overview?.emphasis);put('overviewSummary',D.overview?.summary);put('midDate',D.holidays?.mid_autumn?.date);put('midScene',D.holidays?.mid_autumn?.scene);put('nationalDate',D.holidays?.national_day?.date);put('nationalScene',D.holidays?.national_day?.scene);put('translationLabel',D.overview?.store_translation?.label);put('translationHeadline',D.overview?.store_translation?.headline);put('translationDescription',D.overview?.store_translation?.description);$('seasonDifferences').innerHTML=list(D.overview?.season_differences).map(x=>'<div class="trend-prose"><h4>'+E(x.title)+'</h4><p>'+E(x.body)+'</p></div>').join('');$('metrics').innerHTML=list(D.metrics).map(m=>'<div class="metric"><div class="metric-label"><span class="metric-name">'+E(m.label)+'</span><div class="metric-badges">'+scopeChip(m.scope)+' '+statusChip(m.status)+'</div></div><div class="metric-number num">'+E(m.value)+(m.unit?'<small>'+E(m.unit)+'</small>':'')+'</div><div class="metric-foot">'+E(m.foot)+'</div></div>').join('');const hi=list(D.overview?.store_translation?.highlight_action_ids);$('strategyPoints').innerHTML=hi.map((id,i)=>{const a=list(D.actions).find(x=>x.id===id);return a?'<button data-action-id="'+E(a.id)+'"><b>'+String(i+1).padStart(2,'0')+'</b>'+E(a.action_name)+'</button>':''}).join('');put('navActionCount',String(list(D.actions).length).padStart(2,'0'));renderActions();configureModules();renderTimeline();renderTasks();}
function dims(a){return '<div class="dimension-tags">'+list(a.dimensions).map(x=>'<span class="dimension-tag">'+E(x)+'</span>').join('')+'</div>'}
function renderActions(){const shown=list(D.actions);const card=a=>'<article class="action-card"><div class="action-top"><span class="action-name"><span class="order">'+E(a.order)+'</span> '+E(a.action_name)+'</span><span class="pill '+E(a.tone||'amber')+'">'+E(a.kind)+'</span></div>'+dims(a)+'<h3>'+E(a.title)+'</h3><p class="description">'+E(a.description)+'</p><div class="evidence-mini">'+I('chart')+'<span>'+E(a.evidence)+'</span></div><div class="card-bottom"><span>'+E(a.deadline)+'</span><button class="link" data-action-id="'+E(a.id)+'">看具体方案 '+I('arrow')+'</button></div></article>';const row=a=>'<button class="action-row" data-action-id="'+E(a.id)+'"><span class="row-number">'+E(a.order)+'</span><div class="row-content"><div class="rowtags"><span class="action-name">'+E(a.action_name)+'</span><span class="pill '+E(a.tone||'amber')+'">'+E(a.kind)+'</span><span class="meta">'+E(a.tag)+'</span></div>'+dims(a)+'<h3>'+E(a.title)+'</h3><p>'+E(a.description)+'</p></div>'+I('chevron')+'</button>';$('priorityGrid').innerHTML=shown.slice(0,3).map(card).join('');$('secondaryGrid').innerHTML=shown.slice(3).map(row).join('');put('actionCount',shown.length+' 项建议');put('filterCaption','点击查看具体调整、执行步骤和效果观察。')}
function insightHead(x){return '<div class="insight-heading"><div><h3>'+E(x.title)+'</h3><p>'+E(x.description)+'</p></div><span class="pill gray">'+E(x.badge)+'</span></div>'}
function renderInsight(){const x=D.insights?.[insight]||{};if(!moduleHasData(x))return;let h=insightHead(x);if(list(x.stats).length)h+='<div class="ad-metrics">'+x.stats.map(s=>'<div><p>'+E(s.label)+'</p><strong class="num">'+E(s.value)+'</strong></div>').join('')+'</div>';if(list(x.items).length)h+='<div class="insight-content '+(x.items.length===3?'three':'')+'">'+x.items.map(i=>'<div class="data-card">'+(i.label?'<span class="pill '+E(i.tone||'outline')+'">'+E(i.label)+'</span>':'')+'<h4>'+E(i.title)+'</h4><p>'+E(i.body)+'</p></div>').join('')+'</div>';if(x.table?.columns&&list(x.table.rows).length)h+=makeTable(x.table.columns,x.table.rows);if(list(x.bars).length)h+='<div style="max-width:650px">'+x.bars.map(b=>'<div class="bar-row"><span>'+E(b.label)+'</span><div class="bar-track"><div class="bar" style="width:'+Math.max(0,Math.min(100,Number(b.percent)||0))+'%"></div></div><span class="num">'+E(b.value)+'</span></div>').join('')+'</div>';if(x.takeaway)h+='<div class="takeaway">'+I('spark')+'<span>'+E(x.takeaway)+'</span></div>';$('insightPanel').innerHTML=h;document.querySelectorAll('[data-insight]').forEach(b=>{const on=b.dataset.insight===insight;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1})}
function makeTable(columns,rows){return '<div class="table-scroll"><table><thead><tr>'+columns.map(c=>'<th>'+E(c)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>'<td>'+E(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>'}
function renderTimeline(){$('timeline').innerHTML=list(D.timeline).map(x=>'<div class="phase"><div class="phase-dot"></div><div class="date num">'+E(x.date)+'</div><h3>'+E(x.title)+'</h3><p>'+list(x.tasks).map(E).join('<br>')+'</p><small>'+E(x.owner)+'</small></div>').join('')}
function renderTasks(){const ts=list(D.next_tasks);$('nextTasks').innerHTML=ts.map(t=>'<div class="skill-card"><div class="skill-icon">'+I(t.icon||'spark')+'</div><div class="skill-content"><h3>'+E(t.title)+'</h3><p>'+E(t.description)+'</p></div><button class="btn" data-task-id="'+E(t.id)+'">查看任务 '+I('arrow')+'</button></div>').join('');$('next').classList.toggle('next-hidden',!ts.length);$('nextNav').classList.toggle('next-hidden',!ts.length)}
function showModal(title,body,footer,eyebrow,wide=false){put('modalTitle',title);put('modalEyebrow',eyebrow||'双节经营建议');$('modalBody').innerHTML=body;$('modalFooter').innerHTML=footer||'<button class="btn primary" data-close>我了解了</button>';const d=$('detailDialog');d.classList.toggle('modal-wide',wide);if(!d.open)d.showModal();document.body.style.overflow='hidden'}
function closeModal(){$('detailDialog').close();document.body.style.overflow=''}
function showAction(id){const a=list(D.actions).find(x=>x.id===id);if(!a)return;let body='<div class="callout">'+E(a.description)+'</div><span class="pill '+E(a.tone||'amber')+'">'+E(a.kind)+'</span> '+dims(a)+'<h3>适用门店</h3><p>'+E(list(a.applicable_store_indices).map(i=>D.store.names[i-1]).join("、"))+'</p><h3>经营判断</h3><p>'+E(a.why)+'</p><h3>具体调整方向</h3><div class="compare"><div><b>当前情况</b>'+E(a.current)+'</div><div><b>建议方案</b>'+E(a.proposal)+'</div></div><h3>执行角色与时间</h3><p><b>'+E(a.owner)+'</b> · '+E(a.deadline)+'</p><h3>执行步骤</h3><ol>'+list(a.steps).map(s=>'<li>'+E(s)+'</li>').join('')+'</ol><h3>效果怎么观察</h3><p>'+E(a.measurement)+'</p><h3>落实条件</h3><p>'+E(a.condition)+'</p>';showModal(a.title,body,null,a.action_name+' · 双节经营建议')}
function showTask(id){const t=list(D.next_tasks).find(x=>x.id===id);if(!t)return;copyPayload=t.prompt||'';showModal(t.title,'<p>'+E(t.description)+'</p><pre class="task-text">'+E(copyPayload)+'</pre>','<button class="btn" data-close>返回报告</button><button class="btn primary" id="copyTask">'+I('copy')+'复制任务说明</button>','后续技能 · 任务衔接')}
function toast(m){const t=$('toast');t.textContent=m;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),2200)}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.insight){insight=b.dataset.insight;renderInsight()}else if(b.dataset.actionId)showAction(b.dataset.actionId);else if(b.dataset.taskId)showTask(b.dataset.taskId);else if(b.hasAttribute('data-close')||b.classList.contains('close'))closeModal();else if(b.id==='copyTask'){navigator.clipboard?.writeText(copyPayload).then(()=>toast('任务说明已复制')).catch(()=>toast('请选中文字手动复制'))}});
$('detailDialog').addEventListener('close',()=>document.body.style.overflow='');document.querySelector('.insight-tabs').addEventListener('keydown',e=>{const ts=[...document.querySelectorAll('[data-insight]')],i=ts.indexOf(document.activeElement);if(i<0||!['ArrowRight','ArrowLeft'].includes(e.key))return;e.preventDefault();const n=(i+(e.key==='ArrowRight'?1:-1)+ts.length)%ts.length;insight=ts[n].dataset.insight;renderInsight();ts[n].focus()});
if('IntersectionObserver'in window){const links=[...document.querySelectorAll('.nav a')];const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)links.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id))}),{rootMargin:'-90px 0px -65% 0px'});document.querySelectorAll('main section[id]').forEach(s=>io.observe(s))}
init();if(!list(D.metrics).length)$('metrics')?.setAttribute('hidden','');
</script>
</body>
</html>
'''


def _validate_display(data: dict[str, Any], *, allow_incomplete: bool = False) -> None:
    required = ("report", "store", "collection", "holidays", "overview", "metrics", "actions", "insights", "timeline", "sources", "missing", "next_tasks")
    absent = [key for key in required if key not in data]
    if absent:
        raise ValueError("缺少顶层字段: " + ", ".join(absent))
    if data["report"].get("title") != "中秋国庆经营方案" or not data["report"].get("year"):
        raise ValueError("report.title 必须为“中秋国庆经营方案”，且 report.year 必须存在")
    if not data["report"].get("status_label"):
        raise ValueError("report.status_label 必须存在")
    if not data["store"].get("name"):
        raise ValueError("store.name 必须存在")
    if not data["actions"]:
        raise ValueError("至少需要一条能成立的经营建议")

    blocked_keys = {
        "groupid", "store_id", "merchant_groupid", "store_ref", "backend_url",
        "poi_id", "shop_id", "merchant_id", "account_id", "life_account_id",
        "life_biz_id", "provider_store_id", "account_ref", "backend_params", "query_params",
    }
    blocked_string_tokens = (
        "groupid=", "store_id=", "poi_id=", "shop_id=", "merchant_id=",
        "account_id=", "life_account_biz_ids=", "life_biz_view_id=",
    )
    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in blocked_keys:
                    raise ValueError(f"可分享 report_data 不得包含后台标识: {path + key}")
                walk(child, path + key + ".")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}{index}.")
        elif isinstance(value, str) and any(token in value.lower() for token in blocked_string_tokens):
            raise ValueError("可分享 report_data 不得包含后台原始标识或查询参数")
    walk(data)

    insight_keys = {"trends", "hotspots", "peers", "ads", "products"}
    missing_insights = insight_keys - set(data["insights"])
    if missing_insights:
        raise ValueError("缺少五类洞察: " + ", ".join(sorted(missing_insights)))
    ids = [item.get("id") for item in data["actions"]]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("actions.id 必须存在且唯一")
    orders = [item.get("order") for item in data["actions"]]
    expected_orders = [f"{index:02d}" for index in range(1, len(orders) + 1)]
    if orders != expected_orders:
        raise ValueError("actions.order 必须从 01 起连续排列")
    valid_holidays = {"all", "mid", "national"}
    valid_kinds = {"延续亮点", "优化改进", "机会拓展"}
    valid_tones = {"green", "amber"}
    valid_dimensions = {
        "消费人数", "食材", "节日含义", "抖音短视频运营", "消费场景", "价格带",
        "餐型", "商品品类", "名字", "消费趋势", "运营活动",
    }
    bad_holidays = [item.get("id") for item in data["actions"] if item.get("holiday") not in valid_holidays]
    if bad_holidays:
        raise ValueError("holiday 仅支持 all/mid/national: " + ", ".join(bad_holidays))
    for action in data["actions"]:
        required_action = {
            "action_name", "kind", "tone", "holiday", "title", "description", "evidence",
            "deadline", "owner", "why", "current", "proposal", "steps", "measurement",
            "condition", "source_ids",
        }
        absent_action = sorted(key for key in required_action if not action.get(key))
        if absent_action:
            raise ValueError(f"动作 {action.get('id')} 缺少字段: " + ", ".join(absent_action))
        if action.get("kind") not in valid_kinds:
            raise ValueError(f"动作 {action.get('id')} 的 kind 不合法")
        if action.get("tone") not in valid_tones:
            raise ValueError(f"动作 {action.get('id')} 的 tone 不合法")
        if action.get("kind") == "延续亮点" and action.get("tone") != "green":
            raise ValueError(f"动作 {action.get('id')} 的延续亮点必须使用 green")
        if action.get("kind") != "延续亮点" and action.get("tone") != "amber":
            raise ValueError(f"动作 {action.get('id')} 的优化/机会动作必须使用 amber")
        dimensions = action.get("dimensions") or []
        if not dimensions or any(value not in valid_dimensions for value in dimensions):
            raise ValueError(f"动作 {action.get('id')} 的 dimensions 不合法")
        if not action.get("owner"):
            raise ValueError(f"动作 {action.get('id')} 缺少 owner")
        if not 3 <= len(action.get("steps") or []) <= 5:
            raise ValueError(f"动作 {action.get('id')} 的 steps 必须为 3—5 项")
    valid_priorities = {"platform_core", "platform_extended", "merchant_backend", "historical_reference"}
    valid_statuses = {"observed", "zero", "unavailable", "not_applicable"}
    source_ids = [source.get("id") for source in data["sources"]]
    if any(not source_id for source_id in source_ids) or len(source_ids) != len(set(source_ids)):
        raise ValueError("sources.id 必须存在且唯一")
    source_id_set = set(source_ids)
    for source in data["sources"]:
        if source.get("priority") not in valid_priorities:
            raise ValueError(f"来源 {source.get('id')} 的 priority 不合法")
        if source.get("status") not in valid_statuses:
            raise ValueError(f"来源 {source.get('id')} 的 status 不合法")
    for metric in data["metrics"]:
        if metric.get("status") not in valid_statuses:
            raise ValueError(f"指标 {metric.get('label')} 的 status 不合法")
        if metric.get("scope") not in {"store", "store_set", "merchant"}:
            raise ValueError(f"指标 {metric.get('label')} 的 scope 仅支持 store/store_set/merchant")
        if not metric.get("source_ids"):
            raise ValueError(f"指标 {metric.get('label')} 缺少 source_ids")
    for key, module in data["insights"].items():
        if module.get("status") not in valid_statuses:
            raise ValueError(f"洞察 {key} 的 status 不合法")
        table = module.get("table")
        if table:
            columns = table.get("columns") or []
            if not columns or any(len(row) != len(columns) for row in table.get("rows") or []):
                raise ValueError(f"洞察 {key} 的 table 行列不匹配")
        for bar in module.get("bars") or []:
            percent = bar.get("percent")
            if not isinstance(percent, (int, float)) or percent < 0 or percent > 100:
                raise ValueError(f"洞察 {key} 的 bars.percent 必须在 0 到 100 之间")
    referenced = set()
    for metric in data["metrics"]:
        referenced.update(metric.get("source_ids") or [])
    for action in data["actions"]:
        referenced.update(action.get("source_ids") or [])
    for module in data["insights"].values():
        referenced.update(module.get("source_ids") or [])
    unknown_sources = sorted(referenced - source_id_set)
    if unknown_sources:
        raise ValueError("存在无法解析的 source_id: " + ", ".join(unknown_sources))
    task_ids = [task.get("id") for task in data["next_tasks"]]
    if any(not task_id for task_id in task_ids) or len(task_ids) != len(set(task_ids)):
        raise ValueError("next_tasks.id 必须存在且唯一")
    valid_icons = {"spark", "box", "video", "copy", "chart"}
    for task in data["next_tasks"]:
        if task.get("icon") not in valid_icons:
            raise ValueError(f"任务 {task.get('id')} 的 icon 不合法")
    for item in data["missing"]:
        if item.get("status") not in {"unavailable", "not_applicable"}:
            raise ValueError("missing.status 仅支持 unavailable/not_applicable")
    collection = data.get("collection") or {}
    if collection.get("route") not in {"F0", "F1", "F2", "F3", "FX"}:
        raise ValueError("collection.route 仅支持 F0/F1/F2/F3/FX")
    p0_specs = (("platform_p0", 9, "DP0-"), ("backend_p0", 6, "BP0-"))
    p0_groups = []
    for key, expected_total, prefix in p0_specs:
        group = collection.get(key) or {}
        checked, total, checked_ids = group.get("checked"), group.get("total"), group.get("checked_ids")
        if not isinstance(checked, int) or not isinstance(total, int):
            raise ValueError(f"collection.{key} 的 checked/total 必须为整数")
        if not isinstance(checked_ids, list) or len(checked_ids) != len(set(checked_ids)):
            raise ValueError(f"collection.{key}.checked_ids 必须为不重复数组")
        if total != expected_total:
            raise ValueError(f"collection.{key}.total 必须为 {expected_total}")
        allowed_ids = {f"{prefix}{index:02d}" for index in range(1, expected_total + 1)}
        if any(check_id not in allowed_ids for check_id in checked_ids):
            raise ValueError(f"collection.{key}.checked_ids 含未知 check_id")
        if checked != len(checked_ids):
            raise ValueError(f"collection.{key}.checked 必须等于 checked_ids 长度")
        if checked < 0 or checked > total:
            raise ValueError(f"collection.{key}.checked 必须在 0 到 {total} 之间")
        p0_groups.append(group)
    incomplete_p0 = any(group.get("checked", 0) < group.get("total", 0) for group in p0_groups)
    if incomplete_p0 and not allow_incomplete:
        raise ValueError("P0 检查未完成，不能生成最终报告；运行中预览可显式使用 --allow-incomplete")
    if incomplete_p0 and "P0采集未完成" not in str(data["report"].get("status_label", "")):
        raise ValueError("P0 检查未完成的预览必须在 status_label 标明“P0采集未完成”")


def safe_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def merchant_projection(data: dict[str, Any]) -> dict[str, Any]:
    """Remove audit-only acquisition metadata before data reaches the merchant UI."""
    visible = copy.deepcopy(data)
    visible["collection"] = {"account_check": {"status": data["collection"]["account_check"]["status"]}}
    visible["sources"] = []
    for metric in visible["metrics"]:
        for key in ("source_ids", "record_id", "store_index"):
            metric.pop(key, None)
    for action in visible["actions"]:
        for key in ("source_ids", "evidence_item_ids", "basis_type"):
            action.pop(key, None)
    for module in visible["insights"].values():
        module.pop("source_ids", None)
        module.pop("history_scope", None)
    visible["missing"] = [
        {"field": item.get("field", "相关模块"), "status": item.get("status", "unavailable")}
        for item in visible["missing"]
    ]
    for key in ("edition", "status_label", "footer"):
        visible["report"].pop(key, None)
    visible["overview"].pop("source_note", None)
    visible["overview"].pop("season_note", None)
    return visible


def validate(data: dict[str, Any], *, collection_result=None, allow_incomplete: bool = False) -> None:
    prepared = prepare_report(data, collection_result, allow_incomplete=allow_incomplete)
    _validate_display(prepared, allow_incomplete=allow_incomplete)


def render(template: str, data: dict[str, Any], *, collection_result=None, allow_incomplete: bool = False) -> str:
    data = prepare_report(data, collection_result, allow_incomplete=allow_incomplete)
    _validate_display(data, allow_incomplete=allow_incomplete)
    payload = safe_json(merchant_projection(data))
    output, count = DATA_RE.subn(lambda m: m.group(1) + payload + m.group(2), template, count=1)
    if count != 1:
        raise ValueError("模板缺少唯一的 report-data JSON 节点")
    title = f"{data['report'].get('title', '中秋国庆经营方案')} · {data['store'].get('name', '门店')}"
    output = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", output, count=1, flags=re.DOTALL)
    return output


def bootstrap(base: Path, target: Path) -> None:
    source = base.read_text(encoding="utf-8")
    marker = '<aside class="sidebar">'
    if marker not in source:
        raise ValueError("基础视觉缺少 sidebar 标记")
    prefix = source.split(marker, 1)[0]
    prefix = re.sub(r"<title>.*?</title>", "<title>中秋国庆经营方案 · 等待已校验数据</title>", prefix, count=1, flags=re.DOTALL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(prefix + BODY.lstrip(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="将节日经营结构化 JSON 渲染为单文件 HTML")
    parser.add_argument("input_json", nargs="?", type=Path, help="输入 report_data.json")
    parser.add_argument("output_html", nargs="?", type=Path, help="输出 HTML")
    parser.add_argument("--collection", type=Path, help="必需：已审核账号校验结果与任务内逐指标记录JSON")
    parser.add_argument("--data-only", action="store_true", help="输出经同一校验的妙搭展示JSON")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="妙搭固定模板")
    parser.add_argument("--bootstrap-base", type=Path, help="从批准的 HTML 抽取视觉外壳并重建模板")
    parser.add_argument("--allow-incomplete", action="store_true", help="仅用于运行中预览或旧样例迁移；正式交付不得使用")
    args = parser.parse_args()
    if args.bootstrap_base:
        bootstrap(args.bootstrap_base, args.template)
        print(f"template: {args.template}")
        return
    if not args.input_json or not args.output_html or not args.collection:
        parser.error("需要 input_json、output_html 和 --collection；账号一致性校验不可跳过")
    data = json.loads(args.input_json.read_text(encoding="utf-8"))
    template = args.template.read_text(encoding="utf-8")
    context = json.loads(args.collection.read_text(encoding="utf-8"))
    prepared = prepare_report(data, context, allow_incomplete=args.allow_incomplete)
    _validate_display(prepared, allow_incomplete=args.allow_incomplete)
    output = json.dumps(merchant_projection(prepared), ensure_ascii=False, indent=2) if args.data_only else render(template, data, collection_result=context, allow_incomplete=args.allow_incomplete)
    destination = output_path(args.output_html, prepared, data_only=args.data_only)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(output, encoding="utf-8")
    print(f"report: {destination}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, KeyError, OSError) as error:
        print(json.dumps({"status": "stopped", "reason": str(error), "report_created": False}, ensure_ascii=False))
        sys.exit(2)
