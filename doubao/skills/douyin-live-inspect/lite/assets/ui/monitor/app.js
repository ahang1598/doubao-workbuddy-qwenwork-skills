let latestSnapshot = null;
let pollingComplete = false;
const params = new URLSearchParams(location.search);
const previewMode = params.get('preview') || '';
const byId = (id) => document.getElementById(id);
let latestTask = null;
let snapshotConnectionFailed = false;
let snapshotErrorMessage = '';
let refreshInFlight = false;
let requestSequence = 0;
let appliedSequence = 0;
let latestIssues = [];
let endRequestAccepted = false;
let endAcceptedAt = null;
const capturedRecords = new Map();
const renderedCards = new Map();
const MAX_CAPTURED_RECORDS = 200;
let initialRecordsLoaded = false;
let activeRule = 'all';
let lastSuccessfulRefresh = 0;
let recentRecordIds = new Set();
let highlightTimer = null;
let latestCoverage = null;
let lastConfirmedDurationMs = 0;

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
  const captureClosed = ['stopped', 'ended', 'failed'].includes(snapshot.task.capture_status);
  setText('status', captureClosed ? snapshot.task.status_text : '已收到结束请求，正在停止采集');
  byId('status').className = `detail-status ${statusClass(captureClosed ? 4 : 2)}`;
  setText('page-context', captureClosed
    ? '采集已结束，正在完成当前检测。'
    : '已收到结束请求，正在停止采集；已采集内容将继续检测。');
  renderReportAccess(snapshot);
}

function renderEndActions(snapshot) {
  if (snapshot.report_blocked_reason || snapshot.recap?.status === 'failed') {
    byId('end-task-actions').hidden = true;
    setText('end-task-note', '本轮检测已结束，请查看检测结果。');
    return;
  }
  const active = Number(latestTask?.status) === 2;
  const draining = snapshot.finishing?.phase === 'draining';
  byId('end-task-actions').hidden = !active && !draining;
  setText('end-task-note', snapshot.finishing?.mode === 'immediate'
    ? '已确认舍弃剩余处理，正在准备部分报告。'
    : ['review_paused', 'review_stalled'].includes(snapshot.processing_progress?.state)
    ? '剩余内容判定暂无进展，请回到原对话继续检测。'
    : endRequestAccepted || draining
    ? '正在完成当前检测，完成后生成双报告。'
    : '如需结束质检，请在当前对话发送“结束质检”');
}

function formatMonitoredDuration(task) {
  const startedAt = Number(task.created_at);
  if (!Number.isFinite(startedAt) || startedAt <= 0) return null;
  const terminal = [3, 4, 5].includes(Number(task.status));
  const snapshot = latestSnapshot || window.__monitorPayload;
  const observedAt = Date.parse(snapshot?.refreshed_at || snapshot?.generated_at || '') / 1000;
  const endedAt = Number(task.monitor_ended_at) || endAcceptedAt;
  const fixed = task.monitored_duration_ms;
  const stopped = endedAt != null || terminal || snapshot?.frozen;
  const fresh = !snapshotConnectionFailed && Number.isFinite(observedAt) && Date.now() / 1000 - observedAt < 15;
  const at = endedAt ?? (Number.isFinite(observedAt) ? observedAt : startedAt);
  const confirmed = Math.max(0, (at - startedAt) * 1000);
  if (Number.isFinite(fixed) && fixed >= 0) lastConfirmedDurationMs = fixed;
  else if (stopped || !fresh) lastConfirmedDurationMs = confirmed;
  else lastConfirmedDurationMs = Math.max(0, Date.now() - startedAt * 1000);
  const seconds = Math.floor(lastConfirmedDurationMs / 1000);
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
  byId('task-account').closest('.task-account').hidden = !task.account_name;
  const scenario = byId('task-scenario');
  scenario.textContent = scenarioName;
  scenario.hidden = !task.scenario_name;
  const duration = byId('task-duration');
  duration.textContent = monitoredDuration ? `已监控 ${monitoredDuration}` : '';
  duration.hidden = !monitoredDuration;
  const stopProgress = byId('stop-progress');
  const stopping = endAcceptedAt != null && !['stopped', 'ended', 'failed'].includes(task.capture_status);
  const seconds = stopping ? Math.max(0, Math.floor(Date.now() / 1_000 - endAcceptedAt)) : 0;
  stopProgress.textContent = stopping ? `停止采集中 ${seconds} 秒` : '';
  stopProgress.hidden = !stopping;
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

function failedWithoutMedia(snapshot) {
  return Number(snapshot.task?.status) === 5 && snapshot.coverage?.segments === 0;
}

function renderReportAccess(snapshot) {
  const status = Number(snapshot.task.status);
  const access = byId('report-access');
  const button = byId('report-button');
  const reviewLink = byId('review-report-button');
  const terminal = [3, 4, 5].includes(status) || isEnding();
  const qualityReady = previewMode !== 'loading' && Boolean(snapshot.quality_report_url);
  const reviewSupported = supportsReviewReport(snapshot);
  const reviewReady = reviewSupported && previewMode !== 'loading' && Boolean(snapshot.review_report_url);
  const noMedia = failedWithoutMedia(snapshot);
  const progress = snapshot.processing_progress;
  const blocked = snapshot.report_blocked_reason;
  byId('generation-status').classList.toggle('settled', noMedia || Boolean(progress && progress.state !== 'processing'));
  if (blocked) {
    setText('generation-title', snapshot.task.status_text);
    setText('generation-copy', progress?.message || snapshot.task.status_text);
  } else if (snapshot.reports_terminal && !qualityReady) {
    setText('generation-title', '本轮报告处理已结束');
    setText('generation-copy', '请在原对话查看质检与复盘结果。');
  } else if (snapshot.task?.media_frozen && snapshot.finishing?.phase !== 'draining' && !qualityReady) {
    setText('generation-title', '正在生成报告');
    setText('generation-copy', '基于已检测内容生成质检报告和复盘。');
  } else if (noMedia) {
    setText('generation-title', '未采集到内容，无法生成报告');
    setText('generation-copy', '本次采集失败，未采集到可检测的音视频内容。');
  } else if (progress && !qualityReady) {
    setText('generation-title', progress.title);
    setText('generation-copy', progress.message);
  } else if (snapshot.finishing?.phase === 'draining') {
    setText('generation-title', snapshot.task.status_text || '采集已结束，当前检测中');
    if (snapshot.task?.kind === 'video' || (Number.isFinite(snapshot.finishing.remaining_seconds) && snapshot.finishing.mode !== 'drain' && snapshot.finishing.mode !== 'immediate')) {
      setText('generation-copy', snapshot.finishing.waiting_for_frames ? '正在补齐画面与语音证据，完成后继续判定并生成报告。' : snapshot.finishing.waiting_for_asr ? '正在补齐语音识别，完成后继续判定并生成报告。' : `剩余 ${snapshot.finishing.remaining_seconds} 秒，待处理 ${snapshot.finishing.pending_segments} 个片段；到期后将基于已完成结果生成报告。`);
    } else {
      setText('generation-copy', snapshot.finishing.mode === 'immediate' ? '正在停止剩余检测，随后基于已完成的结果生成报告。' : `已判定 ${snapshot.finishing.reviewed_segments ?? snapshot.coverage?.reviewed ?? 0} 个片段，剩余 ${snapshot.finishing.pending_segments} 个。正在完成当前检测，完成后生成质检报告和复盘。`);
    }

  } else if (!reviewSupported || !reviewReady) {
    setText('generation-title', qualityReady ? '质检报告已生成' : '质检报告生成中');
    setText('generation-copy', qualityReady
      ? '质检报告已生成，可直接查看。'
      : isEnding() ? '正在完成当前检测，完成后将在此更新。'
        : '采集已结束，正在完成当前检测，完成后将在此更新。');
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
  button.disabled = !qualityReady;
  button.onclick = () => { if (qualityReady) window.open(snapshot.quality_report_url, '_blank', 'noopener,noreferrer'); };
  reviewLink.hidden = noMedia || !reviewSupported || !terminal || !qualityReady;
  reviewLink.setAttribute('aria-disabled', String(!reviewReady));
  reviewLink.disabled = !reviewReady;
  reviewLink.onclick = () => { if (reviewReady) window.open(snapshot.review_report_url, '_blank', 'noopener,noreferrer'); };
  setText('review-report-action', reviewReady ? '查看复盘报告' : snapshot.recap?.message || '复盘尚未开始');
  byId('review-report-spinner').hidden = reviewReady || snapshot.recap?.status !== 'generating' || snapshot.recap?.needs_resume === true;
  setText('review-report-status', byId('review-report-action').textContent);
  if (snapshot.standalone) {
    setText('generation-copy', '此页面为工作台快照；报告请查看当前对话中新交付的 HTML 附件。');
    reviewLink.hidden = true;
  }
  access.hidden = noMedia || !terminal || (!qualityReady && !reviewSupported);
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
  const root = byId('records');
  const cards = [];
  const filtering = selectedRule() !== 'all';
  const summary = byId('record-summary');
  summary.hidden = false;
  summary.textContent = filtering ? `筛选显示 ${records.length} / ${capturedRecords.size} 条` : `已加载 ${records.length} 条`;
  renderRiskOverview();
  if (!records.length) {
    renderedCards.clear();
    root.replaceChildren();
    const empty = document.createElement('div');
    empty.className = 'audit-empty';
    const reviewed = Number(latestCoverage?.reviewed || 0);
    empty.textContent = capturedRecords.size ? '当前规则筛选下暂无风险命中'
      : failedWithoutMedia({task: latestTask, coverage: latestCoverage}) ? '本次采集失败，未采集到可判定的内容。'
      : reviewed && latestTask?.inspection_policy ? '已检测内容中未发现规则命中' : reviewed ? '当前暂无风险命中'
        : '正在等待首个片段完成判定…';
    root.append(empty);
    return;
  }
  for (const record of records) {
    const signature = JSON.stringify(record);
    const cached = renderedCards.get(record.id);
    if (cached?.signature === signature) { cards.push(cached.article); continue; }
    const article = document.createElement('article');
    const evidenceId = record.samples?.find((item) => item.evidence_id)?.evidence_id;
    article.className = `audit rejected${evidenceId ? ' has-evidence' : ''}`;
    if (recentRecordIds.has(record.id)) article.classList.add('new-arrival');
    const head = document.createElement('div');
    head.className = 'audit-head';
    const title = document.createElement('strong');
    title.textContent = displayRuleName(record.rule_name);
    title.title = record.rule_name;
    const time = document.createElement('time');
    const newestTime = record.samples?.[0]?.time;
    time.textContent = newestTime || record.created_at || `记录 #${record.id}`;
    head.append(title, time);
    const sample = document.createElement('p');
    sample.textContent = sampleText(record);
    article.append(head, sample);
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
      const imageUrl = record.samples?.find((item) => item.evidence_id === evidenceId)?.image_url || '';
      const evidence = document.createElement('button');
      evidence.type = 'button';
      evidence.className = 'audit-evidence';
      evidence.addEventListener('click', () => window.LiteUI.preview(imageUrl, `${record.rule_name}异常画面`, evidence));
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
    renderedCards.set(record.id, {signature, article});
    cards.push(article);
  }
  const visibleIds = new Set(records.map(record => record.id));
  for (const id of renderedCards.keys()) if (!visibleIds.has(id)) renderedCards.delete(id);
  const retained = new Set(cards);
  for (const child of Array.from(root.children)) if (!retained.has(child)) root.removeChild(child);
  cards.forEach((card, index) => { if (root.children[index] !== card) root.insertBefore(card, root.children[index] || null); });
}

function mergeRecords(records) {
  const root = byId('records');
  const wasNearTop = root.scrollTop <= 24;
  const hadInitialRecords = initialRecordsLoaded;
  let newCount = 0;
  const newIds = [];
  const unknownCount = records.filter((record) => !['hit', 'clear', 'not_applicable'].includes(record.machine_result)).length;
  const progressNote = latestCoverage
    ? `内容片段 ${latestCoverage.segments || 0} 个：已判定 ${latestCoverage.reviewed || 0} 个；待判定 ${latestCoverage.pending || 0} 个`
    : '';
  const unknownNote = unknownCount ? `本轮返回 ${unknownCount} 条记录的自动质检状态或来源未明确，未纳入命中统计。` : '';
  byId('audit-status-note').textContent = [progressNote, unknownNote].filter(Boolean).join('；');
  byId('audit-status-note').hidden = !progressNote && !unknownNote;
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

function updateMonitorState(forceError = snapshotConnectionFailed) {
  const root = document.querySelector('.refresh-state');
  root.classList.toggle('error', forceError || Number(latestTask?.status) === 5);
  if (pollingComplete) {
    setText('monitor-state', latestTask?.status_text || '报告已生成');
    setText('refresh-frequency', '已停止自动更新');
    return;
  }
  const terminal = isEnding() || (latestTask && [3, 4, 5].includes(Number(latestTask.status)));
  const age = lastSuccessfulRefresh ? Math.floor((Date.now() - lastSuccessfulRefresh) / 1_000) : null;
  const failed = Number(latestTask?.status) === 5;
  const noMedia = failedWithoutMedia({task: latestTask, coverage: latestCoverage});
  root.classList.toggle('stale', !forceError && !terminal && age !== null && age >= 15);
  setText('monitor-state', forceError ? `${snapshotErrorMessage}${appliedVersion ? '，当前显示上次状态' : ''}` : failed ? latestTask.status_text || '检测失败' : terminal ? latestTask?.status_text || '监测已结束' : age !== null && age >= 15 ? '更新延迟' : '实时监测中');
  setText('refresh-frequency', forceError ? window.__liveMonitor ? '正在重试更新' : '请重新获取工作台快照' : noMedia ? '未采集到内容' : terminal ? '报告状态自动更新' : age === null ? '正在连接' : age < 10 ? '刚刚更新' : `${age} 秒前更新`);
}

function render(snapshot, sequence = ++requestSequence) {
  if (latestTask?.monitor_ended_at && !snapshot.task.monitor_ended_at) return;
  latestSnapshot = snapshot;
  const task = snapshot.task;
  latestTask = task;
  latestIssues = snapshot.issues || [];
  if (task.stop_requested || snapshot.end_request_accepted) endRequestAccepted = true;
  if (task.monitor_ended_at > 0) endAcceptedAt = task.monitor_ended_at;
  else if (task.stop_requested_at > 0) endAcceptedAt = task.stop_requested_at;
  else if (snapshot.end_accepted_at != null) endAcceptedAt = snapshot.end_accepted_at;
  const terminal = [3, 4].includes(Number(task.status));
  const reviewSupported = supportsReviewReport(snapshot);
  const isVideo = snapshot.task?.kind === 'video';
  setText('page-title', isVideo ? '本地视频质检工作台' : '直播实时质检工作台');
  setText('page-context', failedWithoutMedia(snapshot) ? '本次采集失败，未采集到可检测内容'
    : ['review_paused', 'review_stalled'].includes(snapshot.processing_progress?.state)
    ? '剩余内容判定暂无进展，请回到原对话继续检测。'
    : snapshot.finishing?.phase === 'draining'
    ? '正在完成当前检测，完成后生成质检报告和复盘。'
    : terminal
    ? reviewSupported ? '实时监控已结束，可查看质检与复盘结果' : '实时监控已结束，可查看质检结果'
    : '持续监测直播内容，实时展示质检结果');
  document.title = isVideo ? '本地视频质检工作台' : '直播实时质检工作台';
  if (isVideo) setText('page-context', `视频预处理 ${Math.round((snapshot.task.processed_ms || 0) / 1000)} / ${Math.round((snapshot.task.source_duration_ms || 0) / 1000)} 秒；识别与判定进度见下方`);
  setText('task-name', task.name);
  const status = byId('status');
  status.textContent = task.status_text;
  status.className = `detail-status ${statusClass(task.status)}`.trim();
  renderReportAccess(snapshot);
  renderEndProgress(snapshot);
  renderTaskMeta(task);
  renderEndActions(snapshot);
  const records = snapshot.records || [];
  latestCoverage = snapshot.coverage || null;
  setText('stream-status', `采集：${task.capture_status_text || ({pending:'待开始',running:'进行中',stopped:'已停止',ended:'已结束',failed:'失败'})[snapshot.pipeline?.capture?.status] || '状态未知'}`);
  setText('refreshed-at', new Date(snapshot.refreshed_at).toLocaleTimeString('zh-CN', { hour12: false }));
  lastSuccessfulRefresh = Date.now();
  updateMonitorState();
  mergeRecords(records);
  syncTimers(snapshot);
}

let appliedVersion = 0;
let loadingData = false;

let refreshTimer = null;
let clockTimer = null;
let refreshTimerDelay = null;

const ACTIVE_REFRESH_MS = 2_000;
const SETTLING_REFRESH_MS = 10_000;
const CLOCK_REFRESH_MS = 1_000;

function terminalSnapshot(snapshot) {
  return Boolean(snapshot && [3, 4, 5].includes(Number(snapshot.task?.status)));
}

function clearRefreshTimer() {
  if (refreshTimer !== null) clearInterval(refreshTimer);
  refreshTimer = null;
  refreshTimerDelay = null;
}

function clearClockTimer() {
  if (clockTimer !== null) clearInterval(clockTimer);
  clockTimer = null;
}

function stopTimers() {
  clearRefreshTimer();
  clearClockTimer();
}

function updateLocalClock() {
  if (latestTask && ![3, 4, 5].includes(Number(latestTask.status))) renderTaskMeta(latestTask);
  updateMonitorState();
}

function syncTimers(snapshot = latestSnapshot) {
  if (!window.__liveMonitor) return;
  if (snapshot) latestSnapshot = snapshot;
  if (latestSnapshot?.complete === true) {
    pollingComplete = true;
    stopTimers();
    setText('refresh-frequency', '结果已完整，已停止自动更新');
    return;
  }
  if (pollingComplete || document.hidden) {
    stopTimers();
    return;
  }
  const delay = terminalSnapshot(latestSnapshot) ? SETTLING_REFRESH_MS : ACTIVE_REFRESH_MS;
  if (refreshTimer === null || refreshTimerDelay !== delay) {
    clearRefreshTimer();
    refreshTimerDelay = delay;
    refreshTimer = setInterval(refresh, delay);
  }
  if (terminalSnapshot(latestSnapshot) || latestSnapshot?.task?.monitor_ended_at || latestSnapshot?.task?.stop_requested) clearClockTimer();
  else if (clockTimer === null) clockTimer = setInterval(updateLocalClock, CLOCK_REFRESH_MS);
}

function validSnapshot(data) {
  const object = value => value && typeof value === 'object' && !Array.isArray(value);
  const scalar = value => value == null || ['string', 'boolean'].includes(typeof value) || (typeof value === 'number' && Number.isFinite(value));
  const fields = value => object(value) && Object.values(value).every(scalar);
  const selected = (value, keys) => object(value) && keys.every(key => scalar(value[key]));
  const initial = window.__monitorPayload;
  if (typeof initial?.task_id !== 'string' || !initial.task_id
      || !data || data.ok !== true || data.task_id !== initial.task_id || data.task?.id !== initial.task_id
      || !Number.isSafeInteger(data.version) || data.version < 1
      || !Array.isArray(data.records) || !object(data.pipeline) || !object(data.coverage)
      || !fields(data.task) || !selected(data.coverage, ['reviewed','segments','skipped','message'])
      || (data.coverage.capture != null && !selected(data.coverage.capture, ['message']))
      || (data.finishing != null && (!object(data.finishing) || !Object.entries(data.finishing).every(([key, value]) =>
        key === 'review_targets' ? Array.isArray(value) && value.every(id => Number.isSafeInteger(id) && id > 0) : scalar(value))))
      || (data.recap != null && !selected(data.recap, ['status','message','needs_resume']))
      || (data.pipeline.capture != null && !fields(data.pipeline.capture))
      || !['generated_at','refreshed_at','quality_report_url','review_report_url','end_accepted_at'].every(key => scalar(data[key]))
      || !Number.isFinite(Date.parse(data.generated_at)) || !Number.isFinite(Date.parse(data.refreshed_at))
      || ![1,2,3,4,5].includes(data.task.status) || typeof data.task.name !== 'string'
      || !data.records.every(row => row && Number.isSafeInteger(row.id) && Array.isArray(row.samples)
        && Object.entries(row).every(([key, value]) => key === 'samples' || scalar(value))
        && row.samples.every(fields))) return false;
  return true;
}
function acceptSnapshot(data) {
  if (!validSnapshot(data) || data.version <= appliedVersion
      || (latestTask?.monitor_ended_at && !data.task.monitor_ended_at)) return false;
  render(data);
  appliedVersion = data.version;
  byId('error').hidden = true;
  return true;
}

function setSnapshotError(message = '') {
  snapshotErrorMessage = message;
  snapshotConnectionFailed = Boolean(message);
  byId('error').hidden = true;
  if (message && !appliedVersion) {
    setText('status', '状态暂不可用');
    byId('status').className = 'detail-status status-pending';
    setText('page-context', '尚未读取到有效任务状态，暂无法显示检测结果。');
    for (const id of ['report-outcome', 'report-access', 'end-task-actions', 'audit-status-note']) byId(id).hidden = true;
    for (const id of ['risk-total', 'risk-rules', 'risk-latest', 'risk-top']) setText(id, '—');
    setText('record-summary', '状态暂不可用');
    setText('records', '状态暂不可用，请等待更新或重新获取工作台。');
  }
  updateMonitorState();
}

function receiveSnapshot(data) {
  if (!validSnapshot(data)) return setSnapshotError('工作台数据格式异常');
  if (data.version < appliedVersion || (latestTask?.monitor_ended_at && !data.task.monitor_ended_at)) return;
  const previous = latestSnapshot;
  const refreshedAt = lastSuccessfulRefresh;
  try {
    if (data.version > appliedVersion) acceptSnapshot(data);
  } catch {
    latestSnapshot = previous;
    latestTask = previous?.task || null;
    lastSuccessfulRefresh = refreshedAt;
    return setSnapshotError('工作台显示异常');
  }
  setSnapshotError();
}

function refresh() {
  if (loadingData || pollingComplete || document.hidden) return;
  loadingData = true;
  window.__INSPECT_DATA__ = null;
  const script = document.createElement('script');
  let settled = false;
  const finish = (message = '') => {
    if (settled) return;
    settled = true;
    clearTimeout(timeout);
    script.remove();
    loadingData = false;
    if (message) setSnapshotError(message);
  };
  const timeout = setTimeout(() => finish('无法读取工作台数据'), 5000);
  script.onload = () => {
    if (settled) return;
    finish();
    receiveSnapshot(window.__INSPECT_DATA__);
  };
  script.onerror = () => finish('无法读取工作台数据');
  script.src = './data.js?t=' + Date.now();
  document.body.append(script);
}
function refreshContinuously() {
  receiveSnapshot(window.__monitorPayload);
  if (window.__liveMonitor) {
    if (!pollingComplete && !document.hidden) refresh();
    syncTimers();
  } else if (!snapshotConnectionFailed) {
    setText('monitor-state', '工作台快照');
    setText('refresh-frequency', '此页面不自动更新');
    setText('page-context', '此页面为生成时的工作台快照，后续结果请查看对话中新交付的版本');
  }
}

refreshContinuously();
document.addEventListener('visibilitychange', () => {
  if (!window.__liveMonitor || pollingComplete) return;
  if (document.hidden) {
    stopTimers();
  } else {
    refresh();
    syncTimers();
  }
});
window.addEventListener('pagehide', stopTimers);
window.addEventListener('beforeunload', stopTimers);
window.addEventListener('pageshow', () => {
  if (!window.__liveMonitor || pollingComplete || document.hidden) return;
  refresh();
  syncTimers();
});
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
