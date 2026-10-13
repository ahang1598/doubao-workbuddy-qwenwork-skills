const params = new URLSearchParams(location.search);
const token = params.get('token') || '';
const previewMode = params.get('preview') || '';
const byId = (id) => document.getElementById(id);
let latestTask = null;
let endRequestAccepted = false;
let endAcceptedAt = null;
let healthInFlight = false;
let endOperation = null;
let endBusy = false;
let endTransportUnknown = false;
const capturedRecords = new Map();
const MAX_CAPTURED_RECORDS = 200;
const ACTIVE_REFRESH_MS = 4_000;
const TERMINAL_REFRESH_MS = 5_000;
let initialRecordsLoaded = false;
let activeRule = 'all';
let lastSuccessfulRefresh = 0;
let recentRecordIds = new Set();
let highlightTimer = null;

function setText(id, value) {
  byId(id).textContent = value === null || value === undefined || value === '' ? '—' : `${value}`;
}

function statusClass(status) {
  if (status === 2) return '';
  if ([3, 4].includes(status)) return 'status-done';
  if (status === 5) return 'status-failed';
  return 'status-pending';
}

function isEnding() {
  return endRequestAccepted && ![3, 4, 5].includes(Number(latestTask?.status));
}

function renderEndProgress(snapshot = { task: latestTask || {} }) {
  if (!isEnding()) return;
  setText('status', '已结束');
  byId('status').className = `detail-status ${statusClass(4)}`;
  setText('page-context', '已停止继续采集，预计约 3 分钟完成剩余处理');
  renderReportAccess(snapshot);
}

function receiveEndOperation(operation) {
  if (!operation || (endOperation && operation.revision < endOperation.revision)) return;
  endOperation = operation;
  if (operation.end_accepted_at != null) endAcceptedAt = operation.end_accepted_at;
  if (operation.status === 'accepted') endRequestAccepted = true;
  endTransportUnknown = false;
  renderEndActions();
  renderEndProgress();
  if (latestTask) renderTaskMeta(latestTask);
  updateMonitorState();
}

function renderEndActions() {
  const terminal = [3, 4, 5].includes(Number(latestTask?.status)) || endOperation?.status === 'terminal';
  const active = Number(latestTask?.status) === 2;
  byId('end-task-actions').hidden = terminal || (!active && !endRequestAccepted);
  const status = endOperation?.status;
  const button = byId('end-task-button');
  const pending = status === 'submitting' || endBusy === 'submit';
  button.disabled = !active || !endOperation?.can_end || pending || endRequestAccepted || endTransportUnknown;
  button.textContent = endTransportUnknown || status === 'unknown' ? '结束结果待确认'
    : endRequestAccepted ? '已结束' : pending ? '正在提交' : '结束质检';
  const retryable = status === 'failed' || (status === 'ready' && !endOperation.can_end);
  byId('end-task-retry').hidden = !retryable || endBusy || endTransportUnknown;
  setText('end-task-message', endTransportUnknown ? '连接中断，正在核对结束结果，请勿重复提交'
    : status === 'preparing' ? '正在准备结束操作…' : endOperation?.message || '');
  byId('end-task-message').hidden = !endTransportUnknown && status !== 'preparing' && !endOperation?.message;
}

async function endRequest(path, body) {
  const response = await fetch(path, {
    method: 'POST', headers: { 'content-type': 'application/json', 'x-dashboard-token': token },
    body: JSON.stringify(body), signal: AbortSignal.timeout(120_000),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error('结束操作暂不可用');
  receiveEndOperation(data.end_operation);
}

async function prepareEnd() {
  if (endBusy || endRequestAccepted || endTransportUnknown || Number(latestTask?.status) !== 2) return;
  endBusy = 'prepare';
  renderEndActions();
  try { await endRequest('/api/task/end/prepare', {}); }
  catch {
    // Preparation cannot send EndTask; it is safe to offer an explicit retry.
    endOperation = { ...endOperation, status: 'failed', can_end: false, message: '无法准备结束操作，请重试' };
  } finally { endBusy = false; renderEndActions(); }
}

async function submitEnd() {
  if (endBusy || endTransportUnknown || !endOperation?.can_end || endRequestAccepted || Number(latestTask?.status) !== 2) return;
  endBusy = 'submit';
  renderEndActions();
  try { await endRequest('/api/task/end', { operation_id: endOperation.operation_id }); }
  catch { endTransportUnknown = true; }
  finally { endBusy = false; renderEndActions(); void refreshEndStatus(); }
}

async function refreshEndStatus() {
  if (healthInFlight) return;
  healthInFlight = true;
  try {
    const response = await fetch(`/api/health?token=${encodeURIComponent(token)}`, {
      cache: 'no-store', signal: AbortSignal.timeout(3_000),
    });
    if (!response.ok) return;
    const data = await response.json();
    if (data.ok && data.end_operation) {
      receiveEndOperation(data.end_operation);
      const state = endOperation.status;
      if (state === 'idle' || (state === 'ready' && Date.parse(endOperation.expires_at) <= Date.now())) void prepareEnd();
    }
    if (data.ok && data.end_request_accepted === true) {
      // A stale snapshot or failed health read must not erase a successful acknowledgement.
      endRequestAccepted = true;
      renderEndProgress();
      updateMonitorState();
      renderEndActions();
    }
  } catch {
    // Snapshot polling owns connection errors; health failure is not end acceptance.
  } finally {
    healthInFlight = false;
  }
}

function formatMonitoredDuration(task) {
  const startedAt = Number(task.created_at);
  if (!Number.isFinite(startedAt) || startedAt <= 0) return null;
  const terminal = [3, 4, 5].includes(Number(task.status));
  const finishedAt = endAcceptedAt ?? (terminal && Number(task.updated_at) > 0 ? Number(task.updated_at) : Date.now() / 1_000);
  const seconds = Math.max(0, Math.floor(finishedAt - startedAt));
  const hours = Math.floor(seconds / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  const remainder = seconds % 60;
  if (hours) return `${hours}小时${minutes ? `${minutes}分` : ''}`;
  if (minutes) return `${minutes}分${remainder ? `${remainder}秒` : ''}`;
  return `${remainder}秒`;
}

function renderTaskMeta(task) {
  const accountName = task.account_name || '—';
  const scenarioName = task.scenario_name || '—';
  const monitoredDuration = formatMonitoredDuration(task);
  setText('task-account', accountName);
  const scenario = byId('task-scenario');
  scenario.textContent = scenarioName;
  scenario.hidden = !task.scenario_name;
  const duration = byId('task-duration');
  duration.textContent = monitoredDuration ? `已监控 ${monitoredDuration}` : '';
  duration.hidden = !monitoredDuration;
}

function sampleText(record) {
  const sample = record.samples?.find((item) => item.text || item.reason);
  return sample?.text || sample?.reason || record.audit_comment || '本条记录暂无可展示的命中片段';
}

function supportsReviewReport(snapshot) {
  if (snapshot.review_report_supported !== undefined) return snapshot.review_report_supported === true;
  const task = snapshot.task || {};
  return [9056, 9057, 9058].includes(Number(task.scenario_id))
    || ['金融', '汽车', '电商'].includes(`${task.scenario_name || ''}`.trim());
}

function renderReportAccess(snapshot) {
  const status = Number(snapshot.task.status);
  const access = byId('report-access');
  const button = byId('report-button');
  const reviewLink = byId('review-report-link');
  const terminal = [3, 4].includes(status) || isEnding();
  const qualityReady = previewMode !== 'loading' && Boolean(snapshot.quality_report_url);
  const reviewSupported = supportsReviewReport(snapshot);
  const reviewReady = reviewSupported && previewMode !== 'loading' && Boolean(snapshot.review_report_url);
  if (!reviewSupported || !reviewReady) {
    setText('generation-title', qualityReady ? '质检报告已生成' : '质检报告生成中');
    setText('generation-copy', qualityReady
      ? '质检报告已生成，可直接查看。'
      : isEnding() ? '预计约 3 分钟完成剩余处理并生成质检报告，实际时间可能有所变化。'
        : '实时质检已结束，正在生成质检报告，预计约 3 分钟完成。');
  } else if (!qualityReady && reviewReady) {
    setText('generation-title', '直播复盘报告已生成');
    setText('generation-copy', '质检报告仍在生成，完成后将在此自动显示。');
  } else {
    setText('generation-title', '报告已生成');
    setText('generation-copy', '质检报告与直播复盘已生成，可直接查看。');
  }
  byId('report-outcome').hidden = !terminal;
  byId('generation-status').hidden = !terminal || qualityReady;
  button.hidden = !qualityReady;
  button.href = snapshot.quality_report_url || '#';
  reviewLink.hidden = !reviewSupported || !reviewReady;
  reviewLink.href = snapshot.review_report_url || '#';
  access.hidden = !terminal || (!qualityReady && (!reviewSupported || !reviewReady));
}

function selectedRule() {
  return activeRule;
}

function displayRuleName(name) {
  return `${name || '质检规则'}`;
}

function ruleKey(record) {
  return record.rule_id === null || record.rule_id === undefined
    ? `name:${record.rule_name || ''}` : `id:${record.rule_id}`;
}

function isMachineHit(record) {
  return record.machine_result === 'hit';
}

function updateRuleOptions(records) {
  const root = byId('rule-filter');
  const names = new Map(records.map((record) => [ruleKey(record), displayRuleName(record.rule_name)]));
  const counts = new Map();
  for (const record of records) counts.set(ruleKey(record), (counts.get(ruleKey(record)) || 0) + 1);
  if (activeRule !== 'all' && !names.has(activeRule)) activeRule = 'all';
  const options = [['all', '全部'], ...[...names].sort((a, b) => a[1].localeCompare(b[1], 'zh-CN'))];
  root.replaceChildren(...options.map(([value, label]) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `rule-filter-chip${value === activeRule ? ' active' : ''}`;
    button.dataset.rule = value;
    button.append(document.createTextNode(value === 'all' ? '全部' : displayRuleName(label)));
    const count = document.createElement('em');
    count.textContent = value === 'all' ? records.length : counts.get(value);
    button.append(count);
    button.title = label;
    button.setAttribute('aria-pressed', value === activeRule ? 'true' : 'false');
    return button;
  }));
}

function visibleRecords() {
  const records = [...capturedRecords.values()].sort((left, right) => right.id - left.id);
  const rule = selectedRule();
  return rule === 'all' ? records : records.filter((record) => ruleKey(record) === rule);
}

function sampleSecond(record) {
  const value = record.samples?.[0]?.time;
  if (!value) return null;
  const parts = value.split(':').map(Number);
  return parts.length === 3 ? parts[0] * 3600 + parts[1] * 60 + parts[2] : null;
}

function groupedRecords(records) {
  const groups = [];
  const latestByRule = new Map();
  for (const record of records) {
    const second = sampleSecond(record);
    // 不把不同复核/处置结果合并到一张卡片，避免隐藏已通过复核的记录。
    const groupKey = JSON.stringify([ruleKey(record), record.review_label || null, record.disposition_label || null]);
    const previous = latestByRule.get(groupKey);
    if (previous && second !== null && previous.lastSecond !== null && previous.lastSecond - second <= 30) {
      previous.records.push(record);
      previous.lastSecond = second;
    } else {
      const group = { primary: record, records: [record], firstSecond: second, lastSecond: second };
      groups.push(group);
      latestByRule.set(groupKey, group);
    }
  }
  return groups;
}

function renderRiskOverview() {
  const records = [...capturedRecords.values()];
  const counts = new Map();
  for (const record of records) counts.set(ruleKey(record), (counts.get(ruleKey(record)) || 0) + 1);
  const top = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  const topName = top ? records.find((record) => ruleKey(record) === top[0])?.rule_name : null;
  const latest = [...records].sort((a, b) => b.id - a.id)[0];
  setText('risk-total', records.length);
  setText('risk-rules', counts.size);
  setText('risk-latest', latest?.samples?.[0]?.time || '—');
  setText('risk-top', top ? displayRuleName(topName) : '—');
  byId('risk-top').title = topName || '';
}

function renderRecords() {
  const records = visibleRecords();
  const groups = groupedRecords(records);
  const root = byId('records');
  root.replaceChildren();
  setText('record-summary', selectedRule() === 'all'
    ? `已加载 ${capturedRecords.size} 条`
    : `筛选显示 ${records.length} / ${capturedRecords.size} 条`);
  renderRiskOverview();
  if (!records.length) {
    const empty = document.createElement('div');
    empty.className = 'audit-empty';
    empty.textContent = capturedRecords.size ? '当前筛选暂无质检识别记录' : '本页已加载记录中暂无质检识别结果，不代表完整历史无风险';
    root.append(empty);
    return;
  }
  for (const group of groups) {
    const record = group.primary;
    const article = document.createElement('article');
    const evidenceId = record.samples?.find((item) => item.evidence_id)?.evidence_id;
    article.className = `audit rejected${evidenceId ? ' has-evidence' : ''}`;
    if (group.records.some((item) => recentRecordIds.has(item.id))) article.classList.add('new-arrival');
    const head = document.createElement('div');
    head.className = 'audit-head';
    const title = document.createElement('strong');
    title.textContent = displayRuleName(record.rule_name);
    title.title = record.rule_name;
    if (group.records.length > 1) {
      const count = document.createElement('span');
      count.className = 'audit-count';
      count.textContent = `连续命中 ${group.records.length} 次`;
      title.append(count);
    }
    const time = document.createElement('time');
    const newestTime = record.samples?.[0]?.time;
    const oldestTime = group.records.at(-1)?.samples?.[0]?.time;
    time.textContent = group.records.length > 1 && oldestTime && newestTime ? `${oldestTime}–${newestTime}` : newestTime || record.created_at || `记录 #${record.id}`;
    head.append(title, time);
    const sample = document.createElement('p');
    sample.textContent = sampleText(record);
    article.append(head, time, sample);
    const annotations = [record.review_label ? `复核：${record.review_label}` : '', record.disposition_label ? `处置：${record.disposition_label}` : ''].filter(Boolean);
    if (annotations.length) {
      const statusNote = document.createElement('p');
      statusNote.className = 'reason';
      statusNote.textContent = `${annotations.join('；')}（不改变自动质检命中计数）`;
      article.append(statusNote);
    }
    const reason = record.samples?.find((item) => item.reason)?.reason || record.audit_comment;
    if (reason && reason !== sample.textContent) {
      const reasonEl = document.createElement('p');
      reasonEl.className = 'reason';
      reasonEl.textContent = `判断依据：${reason}`;
      article.append(reasonEl);
    }
    if (evidenceId) {
      const imageUrl = `/api/evidence?token=${encodeURIComponent(token)}&id=${encodeURIComponent(evidenceId)}`;
      const evidence = document.createElement('a');
      evidence.className = 'audit-evidence';
      evidence.href = imageUrl;
      evidence.target = '_blank';
      evidence.rel = 'noopener noreferrer';
      evidence.setAttribute('aria-label', '查看异常画面大图');
      const image = document.createElement('img');
      image.src = imageUrl;
      image.alt = `${record.rule_name}异常画面`;
      image.loading = 'lazy';
      image.referrerPolicy = 'no-referrer';
      evidence.append(image);
      const evidenceLabel = document.createElement('small');
      evidenceLabel.append(document.createTextNode('查看大图'));
      const contextLabel = document.createElement('span');
      contextLabel.textContent = ' · 命中附近画面';
      evidenceLabel.append(contextLabel);
      evidence.append(evidenceLabel);
      article.append(evidence);
    }
    root.append(article);
  }
}

function mergeRecords(records) {
  const root = byId('records');
  const wasNearTop = root.scrollTop <= 24;
  const hadInitialRecords = initialRecordsLoaded;
  let newCount = 0;
  const newIds = [];
  const unknownCount = records.filter((record) => !['hit', 'clear', 'not_applicable'].includes(record.machine_result)).length;
  setText('audit-status-note', unknownCount ? `本轮返回 ${unknownCount} 条记录的自动质检状态或来源未明确，未纳入命中统计。` : '');
  byId('audit-status-note').hidden = unknownCount === 0;
  for (const record of records) {
    // 只跟随机审结论更新缓存；人审通过、驳回或警告由适配层独立保留。
    if (!isMachineHit(record)) {
      capturedRecords.delete(record.id);
      continue;
    }
    if (!capturedRecords.has(record.id)) { newCount += 1; newIds.push(record.id); }
    capturedRecords.set(record.id, record);
  }
  const ordered = [...capturedRecords.values()].sort((left, right) => right.id - left.id);
  for (const record of ordered.slice(MAX_CAPTURED_RECORDS)) capturedRecords.delete(record.id);
  updateRuleOptions(ordered.slice(0, MAX_CAPTURED_RECORDS));
  renderRecords();
  if (wasNearTop) root.scrollTop = 0;
  const prompt = byId('new-records');
  if (initialRecordsLoaded && newCount > 0 && !wasNearTop) {
    prompt.textContent = `有 ${newCount} 条新结果，回到最新`;
    prompt.hidden = false;
  }
  initialRecordsLoaded = true;
  if (newIds.length && hadInitialRecords) {
    recentRecordIds = new Set(newIds);
    clearTimeout(highlightTimer);
    highlightTimer = setTimeout(() => {
      recentRecordIds.clear();
      document.querySelectorAll('.new-arrival').forEach((node) => node.classList.remove('new-arrival'));
    }, 1_800);
  }
}

function updateMonitorState(forceError = false) {
  const root = document.querySelector('.refresh-state');
  const terminal = isEnding() || (latestTask && [3, 4, 5].includes(Number(latestTask.status)));
  const age = lastSuccessfulRefresh ? Math.floor((Date.now() - lastSuccessfulRefresh) / 1_000) : null;
  root.classList.toggle('error', forceError);
  root.classList.toggle('stale', !forceError && !terminal && age !== null && age >= 15);
  setText('monitor-state', isEnding() ? '已结束' : terminal ? '监测已结束' : forceError ? '连接异常' : age !== null && age >= 15 ? '更新延迟' : '实时监测中');
  setText('refresh-frequency', terminal ? '报告状态自动更新' : age === null ? '正在连接' : age < 10 ? '刚刚更新' : `${age} 秒前更新`);
}

function render(snapshot) {
  const task = snapshot.task;
  if ([3, 4, 5].includes(Number(latestTask?.status)) && ![3, 4, 5].includes(Number(task.status))) return;
  latestTask = task;
  if (snapshot.end_request_accepted) endRequestAccepted = true;
  if (snapshot.end_accepted_at != null) endAcceptedAt = snapshot.end_accepted_at;
  const terminal = [3, 4].includes(Number(task.status));
  const reviewSupported = supportsReviewReport(snapshot);
  setText('page-title', '直播实时质检工作台');
  setText('page-context', terminal
    ? reviewSupported ? '实时监控已结束，可查看质检与复盘结果' : '实时监控已结束，可查看质检结果'
    : '持续监测直播内容，实时展示质检结果');
  document.title = '直播实时质检工作台';
  setText('task-name', task.name);
  const status = byId('status');
  status.textContent = task.status_text;
  status.className = `detail-status ${statusClass(task.status)}`.trim();
  renderReportAccess(snapshot);
  renderEndProgress(snapshot);
  renderTaskMeta(task);
  renderEndActions();
  if (endOperation?.status === 'idle') void prepareEnd();
  const records = snapshot.records || [];
  setText('refreshed-at', new Date(snapshot.refreshed_at).toLocaleTimeString('zh-CN', { hour12: false }));
  lastSuccessfulRefresh = Date.now();
  updateMonitorState();
  if (!endRequestAccepted || !initialRecordsLoaded) mergeRecords(records);
}

async function refresh() {
  const notice = byId('error');
  try {
    const response = await fetch(`/api/snapshot?token=${encodeURIComponent(token)}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || '读取自动质检结果失败');
    notice.hidden = true;
    render(data);
  } catch (error) {
    byId('error-text').textContent = error.message || '读取自动质检结果失败，稍后自动重试';
    notice.hidden = false;
    updateMonitorState(true);
  }
}

async function refreshContinuously() {
  await refresh();
  const terminal = latestTask && [3, 4, 5].includes(Number(latestTask.status));
  setTimeout(refreshContinuously, terminal ? TERMINAL_REFRESH_MS : ACTIVE_REFRESH_MS);
}

refreshContinuously();
byId('end-task-button').addEventListener('click', submitEnd);
byId('end-task-retry').addEventListener('click', prepareEnd);
// Local acknowledgement remains responsive even while the audit snapshot is blocked.
refreshEndStatus();
setInterval(refreshEndStatus, ACTIVE_REFRESH_MS);
setInterval(() => {
  if (latestTask && ![3, 4, 5].includes(Number(latestTask.status))) renderTaskMeta(latestTask);
  updateMonitorState();
}, 1_000);
byId('rule-filter').addEventListener('click', (event) => {
  const button = event.target.closest('[data-rule]');
  if (!button) return;
  activeRule = button.dataset.rule;
  for (const chip of byId('rule-filter').querySelectorAll('[data-rule]')) {
    const active = chip.dataset.rule === activeRule;
    chip.classList.toggle('active', active);
    chip.setAttribute('aria-pressed', active ? 'true' : 'false');
  }
  renderRecords();
});
byId('new-records').addEventListener('click', () => {
  byId('records').scrollTo({ top: 0, behavior: 'smooth' });
  byId('new-records').hidden = true;
});
