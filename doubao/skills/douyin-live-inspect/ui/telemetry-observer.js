'use strict';

const $ = id => document.getElementById(id);
const labels = {started:'已开始',selected:'已选择',unknown:'未知',success:'成功',failure:'失败',cancelled:'已取消',completed:'已完成',partial:'部分完成',stopped:'已停止',failed:'失败',attempt_failed:'单次尝试失败',retrying:'重试中',legacy_failed:'失败（终态未标记）'};
const modes = {formal:'正式版',lite:'Lite',shared:'公共'};
const state = {records:[],received:0,limit:1000,selected:null,session:null};
const modeOf = row => ['formal','lite'].includes(row.extra.inspection_mode) ? row.extra.inspection_mode : 'shared';
const eventKeyOf = row => modeOf(row) === 'lite' ? `lite.${row.event.command}` : row.event.command;
const taskNames = {live_recap:'复盘报告',live_inspection:'直播质检',video_inspection:'视频质检',video_batch:'视频批次质检'};
function eventNameOf(row) {
  if (row.event.command === 'asr.diagnostic') return {attempt:'ASR 开始尝试',result:'ASR 尝试结果',route:'ASR 路由选择',recovery:'ASR 恢复结果'}[row.extra.phase] || 'ASR 诊断';
  if (row.extra.recap_attempt_state === 'failed') return '复盘单次尝试失败（仅本机）';
  if (row.extra.recap_attempt_state === 'retrying') return '复盘正在重试（仅本机）';
  if (row.extra.recap_final === true && row.extra.task_result === 'failed') return '复盘任务最终失败';
  const task = taskNames[row.extra.task_type];
  const phase = {'task.started':'开始','task.resumed':'恢复','task.finished':'完成'}[row.event.command];
  if (!task || !phase) return eventKeyOf(row);
  if (row.event.command === 'task.finished' && row.extra.task_result !== 'completed') return `${task}${row.extra.task_type === 'live_recap' ? '生成' : ''}结束`;
  return task + (row.extra.task_type === 'live_recap' ? (phase === '完成' ? '生成完成' : `${phase}生成`) : phase);
}
const descriptionOf = row => row.event.command === 'asr.diagnostic'
  ? [eventNameOf(row), row.extra.segment_id !== undefined ? `片段 ${row.extra.segment_id}` : '', row.extra.attempt !== undefined ? `第 ${row.extra.attempt} 次` : '', row.extra.backend || '', row.extra.outcome === 'failed' ? (row.extra.recovery_code || row.extra.reason || '') : '', `事件 Key：${eventKeyOf(row)}`].filter(Boolean).join(' · ')
  : eventNameOf(row) === eventKeyOf(row) ? row.description : `${eventNameOf(row)}；事件 Key：${eventKeyOf(row)}`;
const resultOf = row => row.event.command === 'asr.diagnostic' ? row.extra.outcome || 'unknown' : row.extra.recap_attempt_state === 'failed' ? 'attempt_failed' :
  row.extra.recap_attempt_state === 'retrying' ? 'retrying' :
  row.extra.task_type === 'live_recap' && row.extra.task_result === 'failed' && row.extra.recap_final !== true ? 'legacy_failed' :
  row.extra.task_result || row.event.result || '';
const reasons = {none:'无',RECAP_TIMEOUT:'单次分析超过 120 秒',RECAP_ATTEMPT_FAILED:'本次分析主动报告失败（无更细原因）'};
function recapSummary(row) {
  if (row.extra.task_type !== 'live_recap') return {retry:'—',reason:'—',final:'—'};
  const id = row.extra.telemetry_task_id;
  const related = id ? state.records.filter(r => r.extra.task_type === 'live_recap' && r.extra.telemetry_task_id === id) : [row];
  const terminal = r => Number(r.extra.recap_final === true || ['completed','partial'].includes(r.extra.task_result));
  const latest = [...related].sort((a,b) => (b.extra.run_index || 1)-(a.extra.run_index || 1) || terminal(b)-terminal(a) ||
    Date.parse(b.extra.task_finished_at || b.captured_at)-Date.parse(a.extra.task_finished_at || a.captured_at)).at(0);
  const currentRun = related.filter(r => (r.extra.run_index || 1) === (latest.extra.run_index || 1));
  const attempt = currentRun.reduce((n,r)=>Math.max(n,r.extra.recap_attempt || r.extra.run_index || 1),1);
  const final = latest.extra.recap_final === true ? (labels[latest.extra.task_result] || '未知') :
    ['completed','partial'].includes(latest.extra.task_result) ? labels[latest.extra.task_result] :
    latest.extra.recap_attempt_state ? '尚未结束' : latest.extra.task_result === 'failed' ? '未知（旧事件未标记终态）' : '尚未结束';
  return {retry:String(attempt-1),reason:reasons[row.extra.recap_failure_reason] || '未提供',final};
}
const timeOf = value => new Date(value).toLocaleTimeString('zh-CN',{hour12:false});

function select(row) {
  state.selected = row.id;
  $('detail-status').textContent = row.event.observation_only ? '仅本机 · 未上报' : '已捕获发送事件';
  const recap = recapSummary(row);
  $('detail-description').textContent = descriptionOf(row) + (row.extra.task_type === 'live_recap' ? `；已重试 ${recap.retry} 次；最近失败原因：${recap.reason}；任务最终状态：${recap.final}` : '');
  $('detail-meta').textContent = `捕获时间：${new Date(row.captured_at).toLocaleString('zh-CN',{hour12:false})} · 进程 ${row.pid} · Skill ${row.event.skill_version || row.event.cli_version || '未知版本'}`;
  $('detail').hidden = false;
  $('detail').textContent = JSON.stringify({...row.event,extra:row.extra},null,2);
  for(const tr of $('events').children) tr.classList.toggle('selected',Number(tr.dataset.id) === row.id);
}

function render() {
  const query = $('search').value.trim().toLowerCase();
  const mode = $('mode').value;
  const rows = state.records.filter(row => (mode === 'all' || modeOf(row) === mode) &&
    `${eventNameOf(row)} ${eventKeyOf(row)} ${descriptionOf(row)} ${row.extra.task_type || ''}`.toLowerCase().includes(query));
  $('count').textContent = `${state.received ? "已捕获 Skill 事件" : "等待 Skill 事件"} · 累计捕获 ${state.received} 条 · 当前显示 ${rows.length} 条`;
  $('empty').hidden = rows.length > 0;
  if (!rows.length) {
    $('empty').textContent = state.records.length ? '没有符合筛选条件的事件。' : '等待下一条埋点。现在正常使用 Skill；服务开启前的事件不会补发，关闭遥测时不会捕获。';
  }
  const fragment = document.createDocumentFragment();
  for(const row of [...rows].reverse()) {
    const tr = document.createElement('tr');
    tr.dataset.id = row.id;
    tr.classList.toggle('selected',row.id === state.selected);
    tr.addEventListener('click',()=>select(row));
    const time = document.createElement('td');time.className='nowrap';time.textContent=timeOf(row.captured_at);
    const event = document.createElement('td');
    const button = document.createElement('button');button.className='event-key';button.textContent=eventNameOf(row);
    const description = document.createElement('div');description.className='event-description';description.textContent=descriptionOf(row);
    event.append(button,description);
    const version = document.createElement('td');version.className='nowrap';version.textContent=modes[modeOf(row)];
    const result = document.createElement('td');result.className='result nowrap';result.dataset.result=resultOf(row);result.textContent=labels[resultOf(row)] || resultOf(row) || '—';
    const recap = recapSummary(row);
    const retry=document.createElement('td');retry.textContent=recap.retry;
    const reason=document.createElement('td');reason.textContent=recap.reason;
    const final=document.createElement('td');final.textContent=recap.final;
    tr.append(time,event,version,result,retry,reason,final);fragment.append(tr);
  }
  $('events').replaceChildren(fragment);
  const selected=rows.find(r=>r.id===state.selected);
  if(selected) select(selected);
  else if(rows.length) select(rows.at(-1));
}

const stream = new EventSource('/api/stream');
stream.onopen = () => { $('connection').dataset.state='connected';$('connection').textContent='● 网页已连接观察服务'; };
stream.onerror = () => { $('connection').dataset.state='error';$('connection').textContent='连接已断开，正在重连'; };
stream.addEventListener('snapshot',message => {
  const next = JSON.parse(message.data);
  if(state.session !== next.session) {
    state.selected=null;$('detail').hidden=true;$('detail-meta').textContent='';
    $('detail-status').textContent='未选择';$('detail-description').textContent='从左侧选择一条事件，查看中文说明和实际发送字段。';
  }
  Object.assign(state,next);render();
});
stream.addEventListener('event',message => {
  const {record,received,limit} = JSON.parse(message.data);
  state.records.push(record);state.records=state.records.slice(-limit);state.received=received;render();
});
$('search').addEventListener('input',render);
$('mode').addEventListener('change',render);
