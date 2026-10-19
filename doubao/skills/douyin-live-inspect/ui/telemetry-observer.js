'use strict';

const $ = id => document.getElementById(id);
const labels = {success:'成功',failure:'失败',cancelled:'已取消',completed:'已完成',partial:'部分完成',stopped:'已停止',failed:'失败'};
const modes = {formal:'正式版',lite:'Lite',shared:'公共'};
const state = {records:[],received:0,limit:1000,selected:null,session:null};
const modeOf = row => ['formal','lite'].includes(row.extra.inspection_mode) ? row.extra.inspection_mode : 'shared';
const eventKeyOf = row => modeOf(row) === 'lite' ? `lite.${row.event.command}` : row.event.command;
const taskNames = {live_recap:'复盘报告',live_inspection:'直播质检',video_inspection:'视频质检',video_batch:'视频批次质检'};
function eventNameOf(row) {
  const task = taskNames[row.extra.task_type];
  const phase = {'task.started':'开始','task.resumed':'恢复','task.finished':'完成'}[row.event.command];
  if (!task || !phase) return eventKeyOf(row);
  if (row.event.command === 'task.finished' && row.extra.task_result !== 'completed') return `${task}${row.extra.task_type === 'live_recap' ? '生成' : ''}结束`;
  return task + (row.extra.task_type === 'live_recap' ? (phase === '完成' ? '生成完成' : `${phase}生成`) : phase);
}
const descriptionOf = row => eventNameOf(row) === eventKeyOf(row) ? row.description : `${eventNameOf(row)}；事件 Key：${eventKeyOf(row)}`;
const resultOf = row => row.extra.task_result || row.event.result || '';
const timeOf = value => new Date(value).toLocaleTimeString('zh-CN',{hour12:false});

function select(row) {
  state.selected = row.id;
  $('detail-status').textContent = '已捕获';
  $('detail-description').textContent = descriptionOf(row);
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
    tr.append(time,event,version,result);fragment.append(tr);
  }
  $('events').replaceChildren(fragment);
  if(state.selected === null && rows.length) select(rows.at(-1));
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
