"use strict";

const state = { report: null, duration: 0, activeEvidenceId: null, analysisTab: "global" };
const byId = (id) => document.getElementById(id);


// Source timestamps retain capture gaps; concatenated replay omits those gaps.
function sourceToMedia(seconds) {
  const spans = state.report?.video.timeline || [];
  if (!spans.length) return seconds;
  const at = seconds * 1000;
  const span = spans.find(s => at >= s.start_ms && at < s.end_ms);
  return span ? (span.media_start_ms + Math.min(at - span.start_ms, span.media_end_ms - span.media_start_ms)) / 1000 : null;
}
function mediaToSource(seconds) {
  const spans = state.report?.video.timeline || [];
  if (!spans.length) return seconds;
  const at = seconds * 1000;
  const span = spans.find(s => at >= s.media_start_ms && at < s.media_end_ms);
  return span ? Math.min(span.end_ms, span.start_ms + at - span.media_start_ms) / 1000 : seconds;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

function formatTime(value, includeHours = false) {
  const seconds = Math.max(0, Math.floor(Number(value) || 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  return `${includeHours || hours ? `${String(hours).padStart(2, "0")}:` : ""}${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function toast(message) {
  const element = byId("toast");
  element.textContent = message;
  element.classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("visible"), 2200);
}

function evidenceAtTime(seconds) {
  const current = Number(seconds) || 0;
  return state.report?.evidence.find((item) => current >= item.start && current <= Math.max(item.end, item.start + 0.5)) || null;
}

function selectEvidence(evidenceId, scroll = false) {
  state.activeEvidenceId = evidenceId || null;
  document.querySelectorAll("[data-evidence-id]").forEach((element) => {
    element.classList.toggle("active", Boolean(evidenceId) && element.dataset.evidenceId === evidenceId);
  });
  if (scroll && evidenceId) {
    requestAnimationFrame(() => {
      document.querySelector(`.evidence-card[data-evidence-id="${CSS.escape(evidenceId)}"]`)?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "center",
      });
    });
  }
}

function setAnalysisTab(tab, evidenceId = null, scroll = false) {
  const nextTab = tab === "risk" ? "risk" : "global";
  state.analysisTab = nextTab;
  byId("analysis-pane-global").scrollTop = 0;
  byId("analysis-pane-risk").scrollTop = 0;
  document.querySelectorAll("[data-analysis-tab]").forEach((button) => {
    const active = button.dataset.analysisTab === nextTab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  byId("analysis-pane-global").hidden = nextTab !== "global";
  byId("analysis-pane-risk").hidden = nextTab !== "risk";
  if (nextTab === "risk") {
    if (evidenceId) byId("asr-search").value = "";
    const current = evidenceId || evidenceAtTime(mediaToSource(byId("video").currentTime))?.id || state.activeEvidenceId;
    renderEvidence(byId("asr-search").value, current);
    selectEvidence(current, scroll);
  } else {
    renderTranscript(byId("asr-search").value);
  }
}

function seekTo(seconds, label, evidenceId, scrollDestination = "player") {
  const video = byId("video");
  const target = Math.max(0, Number(seconds) || 0);
  const mediaTime = sourceToMedia(target);
  if (mediaTime === null) { toast("该时段缺少录制内容"); return; }
  if (!state.report?.video.url) { toast("该报告没有可用回放"); return; }
  window.LiteUI.seek(video, mediaTime);
  video.focus({ preventScroll: true });
  byId("active-caption").textContent = label || `已定位至 ${formatTime(target, true)}`;
  if (evidenceId) {
    setAnalysisTab("risk", evidenceId, scrollDestination === "evidence");
  }
  if (scrollDestination === "player") {
    document.querySelector(".player-panel")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
  }
  toast(`已定位到 ${formatTime(target, true)}`);
}

function timeButton(seconds, label, evidenceId, className = "timecode") {
  return `<button class="${className}" type="button" data-seek="${Number(seconds) || 0}"${evidenceId ? ` data-evidence-id="${escapeHtml(evidenceId)}"` : ""}>${escapeHtml(label)}</button>`;
}

function evidenceKindLabel(kind) {
  const labels = {
    text: "语音文本",
    image: "画面截图",
    audio: "音频证据",
    "custom-sensitive": "自定义敏感词",
    "system-sensitive": "系统敏感词",
    "ocr-text": "画面文字",
    "ocr-subtitle": "底部字幕",
    ocr: "文字识别",
    "sensitive-word": "敏感词",
  };
  return labels[kind] || "命中证据";
}

function renderEvidenceImages(item) {
  const images = Array.isArray(item.images) ? item.images : [];
  if (!images.length) return "";
  return `<div class="evidence-images">${images.map((url, index) => `
    <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer noopener" aria-label="查看${escapeHtml(item.rule_name)}证据图 ${index + 1}">
      <img src="${escapeHtml(url)}" alt="${escapeHtml(item.rule_name)}证据图 ${index + 1}" loading="lazy" referrerpolicy="no-referrer">
    </a>`).join("")}</div>`;
}

function renderTimeline() {
  const timeline = byId("timeline");
  const duration = Math.max(1, state.duration);
  const palette = ["#d7312a", "#d46b08", "#c2417c", "#7c4dcc", "#1664ff", "#14857a"];
  const ruleNames = [...new Set(state.report.evidence.map((item) => item.rule_name || "未分类风险"))].sort((left, right) => left.localeCompare(right, "zh-CN"));
  const ruleColors = new Map(ruleNames.map((name, index) => [name, palette[index % palette.length]]));
  const groups = [];
  for (const item of [...state.report.evidence].sort((left, right) => left.start - right.start || left.end - right.end)) {
    const previous = groups.at(-1);
    if (previous && item.start < previous.end) {
      previous.items.push(item);
      previous.end = Math.max(previous.end, item.end);
    } else groups.push({ start: item.start, end: item.end, items: [item] });
  }
  const segments = groups.map((group) => {
    const left = Math.min(99.5, (group.start / duration) * 100);
    const width = Math.max(0.8, ((Math.max(group.end, group.start + 0.5) - group.start) / duration) * 100);
    const names = [...new Set(group.items.map((item) => item.rule_name || "未分类风险"))];
    const colors = names.map((name) => ruleColors.get(name));
    const background = colors.length === 1 ? colors[0] : `linear-gradient(90deg, ${colors.map((color, index) => `${color} ${index / colors.length * 100}% ${(index + 1) / colors.length * 100}%`).join(", ")})`;
    const label = names.join("、");
    return `<button class="timeline-segment" type="button" style="left:${left}%;width:${Math.min(width, 100 - left)}%;--segment-color:${background}" data-seek="${group.start}" data-evidence-id="${escapeHtml(group.items[0].id)}" aria-label="${escapeHtml(`${label}，${formatTime(group.start, true)}`)}"></button>`;
  }).join("");
  timeline.innerHTML = `<div class="timeline-track"></div>${segments}<div class="playhead" id="playhead"></div>`;
  byId("timeline-legend").innerHTML = `${ruleNames.map((name) => `<span title="${escapeHtml(name)}"><i style="background:${ruleColors.get(name)}"></i>${escapeHtml(name)}</span>`).join("")}<span><i class="legend-playhead"></i>当前播放位置</span>`;
}

function transcriptSegments(utterances) {
  const segments = [];
  for (const utterance of utterances) {
    const last = segments.at(-1);
    const text = String(utterance.text || "").trim();
    if (!text) continue;
    const canMerge = last && utterance.start - last.end <= 8 && utterance.end - last.start <= 60 && last.text.length + text.length <= 240;
    if (canMerge) {
      last.end = Math.max(last.end, utterance.end);
      last.text += `${/[，。！？；：、,.!?;:]$/.test(last.text) ? "" : "。"}${text}`;
    } else {
      segments.push({ start: utterance.start, end: utterance.end, text });
    }
  }
  return segments;
}

function analysisSegment({ start, end, title, text, tags = "", extra = "", evidenceId = "" }) {
  const evidenceAttribute = evidenceId ? ` data-evidence-id="${escapeHtml(evidenceId)}"` : "";
  return `<article class="analysis-segment${evidenceId ? " evidence-card" : ""}"${evidenceAttribute}>
    <div class="analysis-time"><span class="analysis-dot"></span>${timeButton(start, `${formatTime(start, true)} ~ ${formatTime(end, true)}`, evidenceId)}</div>
    <div class="analysis-segment-body">
      <div class="analysis-segment-title"><h3>${escapeHtml(title)}</h3>${tags}</div>
      <p>${text}</p>${extra}
    </div>
  </article>`;
}

function renderTranscript(query = "") {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const segments = transcriptSegments(state.report.asr.utterances).filter((item) => !normalizedQuery || item.text.toLocaleLowerCase().includes(normalizedQuery));
  window.LiteUI.renderRows(byId("transcript-list"), segments, (item) => {
    const pattern = normalizedQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const copy = normalizedQuery ? item.text.split(new RegExp(`(${pattern})`, "ig"))
      .map((part, index) => index % 2 ? `<mark>${escapeHtml(part)}</mark>` : escapeHtml(part)).join("") : escapeHtml(item.text);
    return analysisSegment({ start: item.start, end: item.end, title: "语音识别内容", text: copy });
  }, `<div class="empty-state">没有匹配的语音片段</div>`);
}

function renderEvidence(query = "", revealId = null) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const allEvidence = state.report.evidence;
  const evidence = allEvidence.filter((item) => !normalizedQuery || [item.rule_name, item.text, item.reason, evidenceKindLabel(item.kind)].some((value) => String(value || "").toLocaleLowerCase().includes(normalizedQuery)));
  const conclusions = (state.report.rule_conclusions || []).filter((rule) => !normalizedQuery ||
    [rule.rule_name, ...rule.reasons].some((text) => String(text).toLocaleLowerCase().includes(normalizedQuery)));
  const hasConclusions = Boolean(state.report.rule_conclusions?.length);
  const emptyTitle = normalizedQuery ? "没有匹配的风险片段"
    : state.report.hit_rule_count ? "命中规则暂无风险片段"
      : !state.report.rules.length ? "暂无规则检测明细" : "暂无可定位的风险片段";
  const emptyCopy = normalizedQuery ? "请调整或清除搜索条件。"
    : state.report.hit_rule_count ? "可查看下方规则检测明细。"
      : !state.report.rules.length ? "本次报告暂无规则检测明细。" : "可查看下方规则检测明细。";
  byId("evidence-summary").textContent = normalizedQuery ? `找到 ${evidence.length} 个相关风险片段，${conclusions.length} 条规则结论`
    : allEvidence.length || hasConclusions ? `共识别 ${allEvidence.length} 个风险片段，${state.report.rule_conclusions?.length || 0} 条规则结论` : emptyTitle;
  const rows = [...evidence, ...conclusions.map(rule => ({conclusion: rule}))];
  window.LiteUI.renderRows(byId("evidence-list"), rows, (item) => item.conclusion ? `<article class="analysis-segment rule-conclusion"><div class="analysis-segment-body">
    <div class="analysis-segment-title"><h3>${escapeHtml(item.conclusion.rule_name)}</h3><span class="rule-tag">规则结论</span></div>
    <p>${escapeHtml(item.conclusion.reasons.join("；"))}</p></div></article>` : analysisSegment({
    start: item.start,
    end: item.end,
    title: item.text || (item.images?.length ? "检测到画面风险" : "风险片段"),
    text: escapeHtml(item.reason || "该片段触发了规则判断，请结合直播回放复核。"),
    evidenceId: item.id,
    tags: `<div class="evidence-actions"><div class="evidence-tags"><span class="rule-tag">${escapeHtml(item.rule_name)}</span><span class="evidence-kind">${escapeHtml(evidenceKindLabel(item.kind))}</span></div><button class="review-button" type="button" data-seek="${item.start}" data-evidence-id="${escapeHtml(item.id)}">定位复核 <span>↗</span></button></div>`,
    extra: renderEvidenceImages(item),
  }), `<div class="empty-state"><strong>${emptyTitle}</strong><span>${emptyCopy}</span></div>`, evidence.findIndex(item => item.id === revealId));
}

function scopedAssessment(rule) {
  if (rule.assessment) return rule.assessment;
  const counts = rule.counts || {};
  const status = ['number', 'string'].includes(typeof rule.status) && String(rule.status).trim() !== '' ? Number(rule.status) : null;
  if (Number(counts.hit) > 0 || rule.result === "hit" || status === 2) return "hit";
  if (Number(counts.no_hit) > 0 || ["clear", "no_hit"].includes(rule.result)) return "no_hit_in_checked_scope";
  if (Number(counts.not_applicable) > 0 || rule.result === "not_applicable") return "not_applicable";
  if (rule.result || Object.keys(counts).length) return "undetermined";
  return [0, 1].includes(status) ? "no_hit_in_checked_scope" : "undetermined";
}

function rulePresentation(rule) {
  if (rule.display_scope === "checked_content" && scopedAssessment(rule) === "undetermined") return {kind: "clear", label: "检测未完成"};
  return scopedAssessment(rule) === "hit" ? {kind: "hit", label: "命中"} : {kind: "clear", label: "通过"};
}

function renderRules() {
  byId("rule-grid").innerHTML = state.report.rules.map((rule) => {
    const presentation = rulePresentation(rule);
    return `<article class="rule-card rule-${presentation.kind}"><span class="rule-status">${presentation.label}</span>
      <div><h3>${escapeHtml(rule.name)}</h3></div></article>`;
  }).join("") || `<div class="empty-state">报告未返回规则检测明细</div>`;
}

function diagnosisSummary(report) {
  const assessment = report.conclusion?.assessment || (report.rules.some(r => scopedAssessment(r) === "hit") ? "hit"
    : report.rules.some(r => scopedAssessment(r) === "no_hit_in_checked_scope") ? "no_hit_in_checked_scope"
    : report.rules.some(r => scopedAssessment(r) === "not_applicable") ? "not_applicable" : "undetermined");
  const scope = report.inspection_scope === "speech_only" ? "已检测字幕" : "已检测范围";
  let text = report.conclusion?.summary || ({hit: "已发现规则命中。", no_hit_in_checked_scope: `${scope}中未发现规则命中。`,
    not_applicable: "已判定内容中的规则均不适用。", undetermined: "没有足够的有效判断，无法给出质检结论。"})[assessment];
  const coverage = report.conclusion?.coverage_summary;
  if (coverage) {
    text += ` 已采集内容：${coverage.counts.checked} 段有效判定；${coverage.counts.evidence_insufficient} 段证据不足；${coverage.counts.unchecked} 段未完成检测；${coverage.counts.pending} 段待判定。`;
    if (coverage.checked_segment_ratio != null) text += ` 有效判定片段占比 ${(coverage.checked_segment_ratio * 100).toFixed(1)}%。`;
    if (coverage.checked_time_ratio != null) text += ` 已采集内容有效判定时间占比 ${(coverage.checked_time_ratio * 100).toFixed(1)}%。`;
  } else if (report.conclusion?.has_incomplete_results || report.conclusion?.coverage_complete === false || report.coverage?.gaps?.length || report.rules.some(r => ["insufficient", "pending", "skipped"].includes(r.result))) {
    text += " 存在检测缺口或待判定内容，旧报告未记录完整分类。";
  }
  const reasons = [...new Set((report.conclusion?.coverage_summary?.issues || report.coverage?.gaps || []).map(g => g.reason).filter(Boolean))];
  if (reasons.length) text += ` 未检测原因：${reasons.join("；")}。`;
  text += " 结论仅适用于已完成判定的范围。";
  if (report.inspection_scope === "speech_only") text += " 仅字幕检测，画面未检测。";
  if (report.sampling) text += ` ${report.conclusion.scope}；已完成 ${report.sampling.completed_windows} 个窗口，抽检 ${report.sampling.sampled_ms / 1000} 秒。`;
  return text;
}

function formatDateTime(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return "";
  const date = new Date(numeric < 1e12 ? numeric * 1000 : numeric);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (part) => String(part).padStart(2, "0");
  return `${date.getFullYear()}年${pad(date.getMonth() + 1)}月${pad(date.getDate())}日 ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function qualitySceneLabel(value, reportKind = 'live', name = '') {
  // Scenario IDs are scoped to customer projects, never global industry labels.
  return String(name || '').trim() || '—';
}

function formatDurationText(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds || 0)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remainder = total % 60;
  if (hours) return `${hours}小时${minutes}分`;
  if (minutes) return `${minutes}分${remainder ? `${remainder}秒` : ""}`;
  return `${remainder}秒`;
}

function reportPresentation(reportKind) {
  const mediaLabel = reportKind === "live" ? "直播" : "视频";
  return {
    mediaLabel,
    reportLabel: `${mediaLabel}质检报告`,
    coverLabel: `${mediaLabel}质检`,
    playerLabel: `${mediaLabel}回放`,
    durationLabel: `${mediaLabel}时长`,
    sessionLabel: `${mediaLabel}场次`,
  };
}

function renderReport(report) {
  state.report = report;
  const coveragePanel = byId("video-coverage");
  if (coveragePanel && report.report_kind === "video") {
    const cov = report.coverage || {};
    coveragePanel.hidden = false;
    byId("coverage-title").textContent = report.conclusion.label || "部分检测结果";
    byId("coverage-summary").textContent = cov.message || "未完成有效检测";
    byId("video-report-note").textContent = `${report.coverage_complete ? "" : "存在未检测或证据不足的内容，不能据此认定全片无其他风险。"} 报告版本 ${report.report_version || "—"}；此文件是生成时的历史快照。${report.hit_count_basis || ""} 下载媒体 ZIP 并解压后可播放视频。`;
    byId("coverage-details").hidden = !(cov.gaps || []).length;
    byId("video-report-gaps").innerHTML = (cov.gaps || []).map(g => `<li>${escapeHtml(formatTime(g.start, true))}–${escapeHtml(formatTime(g.end, true))}：${escapeHtml(g.reason).replace(/，具体原因见规则判断依据$/, "")}</li>`).join("");
  }
  state.duration = Number(report.duration_seconds || report.video.duration_seconds || 0);
  const presentation = reportPresentation(report.report_kind);
  byId("report-brand-title").textContent = presentation.reportLabel;
  byId("task-cover-label").textContent = presentation.coverLabel;
  byId("player-title").textContent = presentation.playerLabel;
  byId("duration-label").textContent = presentation.durationLabel;
  byId("task-name").textContent = report.task.name || presentation.reportLabel;
  const taskAccount = String(report.task.account_name || "").trim();
  byId("task-account").hidden = !taskAccount;
  byId("task-account").textContent = taskAccount ? `@${taskAccount}` : "";
  byId("task-account").title = taskAccount;
  document.title = `${report.task.name || presentation.reportLabel} · 本地报告`;
  byId("task-meta").textContent = `${presentation.durationLabel}：${formatDurationText(state.duration)}`;
  const taskScene = qualitySceneLabel(report.task.scenario_id, report.report_kind, report.task.scenario_name);
  byId("task-scene-tags").hidden = !taskScene || taskScene === "—";
  byId("task-scene").textContent = taskScene;
  const session = byId("task-session");
  const sessionStart = formatDateTime(report.task.machine_start_time || report.task.created_time);
  const sessionEnd = formatDateTime(report.task.machine_end_time);
  session.hidden = !sessionStart && !sessionEnd;
  byId("task-session-label").textContent = presentation.sessionLabel;
  byId("task-session-time").textContent = sessionStart ? `${sessionStart}${sessionEnd ? ` — ${sessionEnd}` : ""}` : "时间暂未返回";
  byId("risk-count").textContent = report.evidence.length;
  byId("hit-count").textContent = report.hit_rule_count;
  byId("rule-count").textContent = report.rules.length;
  byId("duration").textContent = formatTime(state.duration, true);
  byId("utterance-count").textContent = report.asr.utterances.length;
  byId("diagnosis-summary").textContent = diagnosisSummary(report);
  const topRules = report.rules.filter(rule => rulePresentation(rule).kind === "hit").map(rule => ({...rule, evidence: report.evidence.filter(item => item.rule_id === rule.id)}))
    .sort((a, b) => b.evidence.length - a.evidence.length || a.name.localeCompare(b.name, "zh-CN")).slice(0, 3);
  byId("top-hit-rules").hidden = !topRules.length;
  byId("top-hit-rules").innerHTML = '<span>主要命中规则</span>' + topRules.map(rule => `<button type="button" class="review-button" data-top-evidence="${escapeHtml(rule.evidence[0]?.id || "")}" ${rule.evidence.length ? "" : "disabled"}>${escapeHtml(rule.name)} · ${rule.evidence.length ? `${rule.evidence.length} 个片段` : "片段暂无"}</button>`).join("");
  const video = byId("video");
  if (report.video.url) video.src = report.video.url;
  else {
    byId("video-empty").hidden = false;
    byId("video-empty").textContent = "未保存可用回放，仍可查看文字报告。";
  }
  video.addEventListener("loadedmetadata", () => {
    if (Number.isFinite(video.duration) && !report.video.timeline?.length) {
      state.duration = video.duration;
      byId("duration").textContent = formatTime(video.duration, true);
      renderTimeline();
    }
  }, { once: true });
  video.addEventListener("error", () => { byId("video-empty").hidden = false; });
  video.addEventListener("timeupdate", () => {
    const duration = Math.max(1, state.duration);
    byId("playhead-time").textContent = formatTime(mediaToSource(video.currentTime), true);
    const playhead = byId("playhead");
    if (playhead) playhead.style.left = `${Math.min(100, (mediaToSource(video.currentTime) / duration) * 100)}%`;
    if (state.analysisTab === "risk") {
      const currentEvidence = evidenceAtTime(mediaToSource(video.currentTime));
      if (currentEvidence?.id !== state.activeEvidenceId) selectEvidence(currentEvidence?.id || null);
    }
  });
  renderTimeline();
  renderEvidence();
  renderRules();
  setAnalysisTab("global");
}

document.addEventListener("click", (event) => {
  const top = event.target.closest("[data-top-evidence]");
  if (top && !top.disabled) {
    byId("asr-search").value = "";
    byId("asr-search-clear").hidden = true;
    setAnalysisTab("risk", top.dataset.topEvidence, true);
    return;
  }

  const tab = event.target.closest("[data-analysis-tab]");
  if (tab) {
    setAnalysisTab(tab.dataset.analysisTab, null, tab.dataset.analysisTab === "risk");
    return;
  }
  const target = event.target.closest("[data-seek]");
  if (!target) return;
  const evidence = state.report?.evidence.find((item) => item.id === target.dataset.evidenceId);
  const scrollDestination = target.classList.contains("timeline-segment") ? "evidence" : "player";
  seekTo(target.dataset.seek, evidence ? evidence.rule_name : target.textContent.trim(), target.dataset.evidenceId, scrollDestination);
});

byId("asr-search").addEventListener("input", (event) => {
  byId("asr-search-clear").hidden = !event.target.value;
  if (state.analysisTab === "risk") renderEvidence(event.target.value);
  else renderTranscript(event.target.value);
});
byId("asr-search-clear").addEventListener("click", () => {
  const input = byId("asr-search");
  input.value = "";
  byId("asr-search-clear").hidden = true;
  if (state.analysisTab === "risk") renderEvidence();
  else renderTranscript();
  input.focus();
});

(async () => {
  const embeddedPayload = window.__reportPayload;
  if (!embeddedPayload) throw new Error('报告缺少内嵌数据');
  renderReport(embeddedPayload.report);
})().catch((error) => {
  document.body.innerHTML = `<main class="fatal"><h1>无法打开质检报告</h1><p>报告页面暂不可用，请回到对话重新获取报告。</p><small>已有质检任务不会因此重新创建。</small></main>`;
});
