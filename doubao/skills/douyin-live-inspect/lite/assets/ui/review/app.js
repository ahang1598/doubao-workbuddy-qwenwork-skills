"use strict";
const byId = (id) => document.getElementById(id);
const state = { report: null, filter: "all", query: "" };
const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function time(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const relative = [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
  const recorded = recordedAt(ms);
  return relative + (recorded ? `（${recorded.slice(0, 10) === recordedAt(0).slice(0, 10) ? recorded.slice(11) : recorded}）` : "");
}
function recordedAt(ms = 0) {
  const epoch = state.report?.capture_epoch;
  if (state.report?.identity?.kind !== "live" || !Number.isFinite(epoch) || epoch <= 0) return "";
  return new Intl.DateTimeFormat("sv-SE", {timeZone:"Asia/Shanghai", year:"numeric", month:"2-digit", day:"2-digit",
    hour:"2-digit", minute:"2-digit", second:"2-digit", hourCycle:"h23"}).format(new Date(epoch * 1000 + ms));
}
function timeButton(start, end) {
  const video = state.report?.video;
  const seekable =
    video?.url &&
    window.LiteUI.mediaTime(start / 1000, video.timeline) !== null;
  return `<button class="timecode" type="button" data-seek="${start}" ${seekable ? "" : "disabled"}>${time(start)} ~ ${time(end)}</button>`;
}
let detailReport;
let detailCache = new WeakMap();
function detailText(row) {
  if (detailReport !== state.report) { detailReport = state.report; detailCache = new WeakMap(); }
  if (detailCache.has(row)) return detailCache.get(row);
  const report = state.report;
  const gaps = (report.coverage?.gaps || []).filter(g => (report.identity?.kind !== "live" || window.LiteUI.reportGapDetail(g)) && g.start_ms < row.end_time && g.end_ms > row.start_time);
  const refs = new Set([...(row.evidence_ids || []), ...(report.evidence || []).filter(e => e.start_ms < row.end_time &&
    (e.end_ms > row.start_time || e.end_ms === e.start_ms && e.start_ms >= row.start_time)).map(e => e.id)]);
  const analysis = report.document.modules?.content_analysis || {};
  const findings = [];
  const groups = {...report.references};
  for (const key of ['highlights', 'problems']) groups[key] ||= (analysis[key] || []).map(item => item.evidence_ids || []);
  const notes = Object.entries(groups).flatMap(([key, groups]) => groups.flatMap((ids, i) => {
    if (!ids.some(id => refs.has(id))) return [];
    const item = analysis[key]?.[i];
    if (item && ['highlights','problems'].includes(key)) findings.push({kind:key, title:item.title, reason:item.reason});
    return [typeof item === "string" ? item : item?.reason || item?.title || ""];
  }));
  const detail = row.moment_detail;
  const result = {
    findings,
    title: detail ? detail.title || "分析依据" : "",
    paragraphs: [detail?.reason, detail?.suggestion, ...notes, ...gaps.map(g =>
      `${time(g.start_ms)} ~ ${time(g.end_ms)}：${g.kind === "capture" ? "该时段未采集，无法定位" : g.kind === "judgment" ? "部分规则依据不足，无法确认" : "该时段部分内容证据缺失"}`)].filter(Boolean),
  };
  detailCache.set(row, result);
  return result;
}
function contentDetails(row) {
  const detail = detailText(row);
  if (!detail.title && !detail.paragraphs.length) return "";
  return `<details class="detail"><summary>查看分析详情</summary>${detail.title ? `<h4>${escapeHtml(detail.title)}</h4>` : ""}${detail.paragraphs.map(text => `<p>${escapeHtml(text)}</p>`).join("")}</details>`;
}

function segmentImages(row) {
  const urls = row.period_image ? [row.period_image] : row.frame_images;
  if (!urls?.length) return "";
  const label = row.period_image ? "该时段画面" : "画面证据";
  return `${row.period_image ? "<p>该时段画面</p>" : ""}<div class="images">${urls.map(url =>
    `<button type="button" data-preview="${escapeHtml(url)}" aria-label="查看${label}"><img src="${escapeHtml(url)}" alt="${label}" loading="lazy"></button>`).join("")}</div>`;
}

function segmentFindings(row) {
  return detailText(row).findings;
}
function segmentKinds(row) {
  const findings = segmentFindings(row);
  return {highlight:(row.labels || []).includes(2) || findings.some(f => f.kind === 'highlights'),
    problem:(row.labels || []).some(label => label === 3 || label === 4) || findings.some(f => f.kind === 'problems')};
}
function segmentTags(row) {
  const kinds = segmentKinds(row);
  return [...new Set([
    ...(kinds.highlight ? ["高光时刻"] : []),
    ...(kinds.problem ? ["问题时刻"] : []),
    ...(row.tags || []),
  ])];
}

function renderContent() {
  const query = state.query.trim().toLocaleLowerCase();
  const rows = state.report.document.content.segments.filter((row) => {
    const detail = query ? detailText(row) : null;
    const matches =
      state.filter === "all" ||
      (state.filter === "product"
        ? row.labels.includes(1)
        : state.filter === "highlights"
          ? segmentKinds(row).highlight
          : segmentKinds(row).problem);
    return (
      matches &&
      (!query ||
        [
          row.content,
          row.title,
          ...segmentTags(row),
          detail.title,
          ...detail.paragraphs,
        ].some((text) => text?.toLocaleLowerCase().includes(query)))
    );
  });
  window.LiteUI.renderRows(byId("timeline"), rows,
      (row) => {
        const kinds = segmentKinds(row);
        const notes = segmentFindings(row).map(f => `<div class="moment-note ${f.kind}"><strong>${f.kind === 'highlights' ? '亮点' : '改进项'}</strong><span>${escapeHtml(f.title)}</span></div>`).join('');
        return `<li class="segment${kinds.highlight ? ' has-highlight' : ''}${kinds.problem ? ' has-problem' : ''}"><div class="timeRow"><span class="dot"></span>${timeButton(row.start_time, row.end_time)}</div><article class="segmentBody"><div class="segmentTitle"><h3>${escapeHtml(row.title || "语音识别内容")}</h3><div class="tags">${segmentTags(row).map((tag) => `<span class="${tag.includes("问题") || tag.includes("违规") ? "problemTag" : tag.includes("高光") ? "highlightTag" : "tag"}">${escapeHtml(tag)}</span>`).join("")}</div></div>${notes ? `<div class="moment-notes">${notes}</div>` : ''}<p>${escapeHtml(row.content)}</p>${contentDetails(row)}${segmentImages(row)}</article></li>`;
      },
    );
  byId("timeline-end").textContent = rows.length
    ? "没有更多数据了"
    : "当前筛选下没有内容片段";
  byId("analysis-body").scrollTop = 0;
}
function renderConclusionScore(score) {
  const box = byId("conclusion-score");
  const detail = byId("scoring-details");
  box.hidden = !Number.isFinite(score?.total);
  detail.hidden = !score;
  if (!score) { box.innerHTML = ""; detail.innerHTML = ""; return; }
  const statuses = {not_applicable:"不适用", insufficient:"证据不足"};
  const refs = items => items.map(e => `<p>${Number.isFinite(e.start_ms) ? timeButton(e.start_ms, e.end_ms ?? e.start_ms) : "无时间定位"} ${escapeHtml(e.text || e.quote || "")}</p>`).join("");
  box.innerHTML = !box.hidden ? `<span class="scoreEyebrow">${score.status === "provisional" ? "参考评分" : "综合评分"}</span><div class="scoreNumber">${score.total.toFixed(1)}<small>/ 10</small></div>` : "";
  detail.innerHTML = `<h2>分项评分</h2>
    <table class="scoreTable"><thead><tr><th>维度</th><th>评分</th><th>依据</th></tr></thead><tbody>${score.dimensions.map(d => `<tr><td>${escapeHtml(d.name)}</td><td>${d.score === null ? (d.id === "compliance" ? "—" : statuses[d.status]) : d.score + " / 10"}</td><td>${escapeHtml(d.reason)}${d.evidence.length ? `<details class="detail"><summary>查看评分证据</summary>${refs(d.evidence)}</details>` : ""}</td></tr>`).join("")}</tbody></table>`;
}
function commentSummary(viewer, brief) {
  const count = viewer.live_room?.comment_count;
  const overview = viewer.qa_total == null && brief?.overview
    ? brief.overview : `${count == null ? '评论总量未采集' : `本场采集评论 ${count} 条`}；仅总结观众关注的内容。`;
  const fields = [['demand', '关注主题'], ['sentiment', '情绪'], ['purchase_intent', '购买意向']];
  const requests = viewer.comment_extraction?.purchase_requests || [];
  const products = requests.length ? `<p><strong>观众点名求购：</strong>${requests.map(r =>
    `${escapeHtml(r.name)}（${({other:'其他商品',current:'当前商品',unknown:'与主推关系待确认'})[r.relation] || '与主推关系待确认'}，${escapeHtml(String(r.count))}条评论）`).join('、')}</p>` : '';
  return `<div class="interaction-brief"><p>${escapeHtml(overview)}</p>${products}${fields
    .filter(([key]) => brief?.[key])
    .map(([key, label]) => `<p><strong>${label}：</strong>${escapeHtml(brief[key])}</p>`).join('')}</div>`;
}

// Historical matching renderer retained while its product entry is disabled.
function interactionSummary(viewer, brief) {
  const questions = viewer.qa || [];
  const counts = viewer.qa_summary || {total:questions.length,
    answered:questions.filter(q => q.answers?.some(a => a.answer_complete === true)).length};
  const publicCounts = viewer.interaction_optimization?.public;
  const personal = viewer.interaction_optimization?.personalized?.question_count || 0;
  const sampled = !viewer.qa_summary && viewer.qa_total > questions.length;
  const total = publicCounts?.question_count ?? counts.total;
  const answered = publicCounts?.answered ?? counts.answered;
  const commentCount = viewer.live_room?.comment_count;
  const overview = brief?.overview || `${commentCount == null ? '评论总量未采集' : `本场采集评论 ${commentCount} 条`}，${sampled ? `展示样本 ${questions.length}/${viewer.qa_total} 项中` : '已识别问题中'}${total ? `${publicCounts ? '公共问题' : '问题'} ${total} 项、确认解答 ${answered} 项` : '暂无可评价问题'}${personal ? `，${personal} 项个性化问题需客服跟进` : ''}。`;
  const checking = publicCounts?.pending ?? counts.pending ?? 0;
  const unmatched = publicCounts?.unanswered ?? counts.unanswered ?? 0;
  const partial = publicCounts?.reply_detected ?? counts.reply_detected ?? 0;
  const progressNote = viewer.qa_processing ? `<p class="scope-note">待检查 ${checking} 项 · 部分回应 ${partial} 项 · 已检查暂未找到回答 ${unmatched} 项；处理积压与 ASR 缺失不计为主播漏答。</p>` : '';
  const skipped = viewer.qa_processing?.comment_rate_limit?.dropped || 0;
  const limitNote = skipped ? `<p class="scope-note">评论问答为限量分析：${escapeHtml(skipped)} 条评论因超额跳过，未计入问答分析，不代表主播未回答。</p>` : '';
  const topics = (viewer.interaction_optimization?.public?.topics || []).slice(0,2).map(t => t.topic);
  const demand = brief?.demand || `${topics.length ? `主要疑问为${topics.join('、')}` : '集中疑问尚未提炼'}，最想要的商品尚无足够求购证据确定。`;
  const insights = [['sentiment', '情绪'], ['purchase_intent', '购买意向']]
    .filter(([key]) => brief?.[key])
    .map(([key, label]) => `<p><strong>${label}：</strong>${escapeHtml(brief[key])}</p>`).join('');
  return `<div class="interaction-brief"><p>${escapeHtml(overview)}</p><p>${escapeHtml(demand)}</p>${progressNote}${limitNote}${insights}</div>`;
}

function renderReport(report) {
  state.report = report;
  byId("review-state").hidden = report.available;
  byId("report").hidden = !report.available;
  byId("review-state").textContent = report.message;
  if (!report.available) return;
  const viewer = report.viewer_context;
  byId("viewer-context").hidden = !viewer;
  byId("viewer-scope").textContent = viewer
    ? `${viewer.qa_total == null ? viewer.scope : "评论总结仅覆盖已采集评论，未采集或省略不代表无人评论。"} 图表展示 ${viewer.live_room.samples.length}/${viewer.audience_sample_count} 个人数采样点。`
    : "";
  byId("interaction-summary").innerHTML = viewer ? commentSummary(viewer, report.document?.modules?.content_analysis?.interaction_summary) : '';
  window.LiteUI.renderLiveRoom({...viewer, clarifications:report.clarifications, sales_state:report.sales_state, recap:true}, time);
  const doc = report.document;
  const analysis = doc.modules.content_analysis;
  renderConclusionScore(analysis.scoring);
  const media = report.identity.kind === "video" ? "视频" : "直播";
  document.title = `${doc.live.title} · 复盘`;
  byId("report-title").textContent = `${media}复盘报告`;
  byId("cover-label").textContent = `${media}复盘`;
  byId("task-name").textContent = `${doc.live.title} · 复盘`;
  byId("duration").textContent = `${media}时长：${doc.live.duration_text}`;
  byId("recording-date").textContent = report.identity.kind === "live"
    ? recordedAt() ? `${recordedAt().slice(0, 10)} · ${recordedAt().slice(11)} 起记录 · 北京时间`
      : "记录日期未知 · 仅展示相对时间"
    : `视频复盘 · ${doc.live.duration_text}`;
  byId("clock-scope").textContent = report.identity.kind === 'live'
    ? '时间点同时保留相对时间与北京时间，跨日注明日期。记录起点不代表整场开播时间。' : '';
  byId("scenario").textContent = doc.live.scenario_name;
  byId("scenario").hidden = !doc.live.scenario_name;
  const rows = doc.content.segments;
  byId("session").textContent = rows.length
    ? `${time(rows[0].start_time)} ~ ${time(rows.at(-1).end_time)}`
    : "无有效内容";
  byId("data-title").textContent = `${media}数据`;
  byId("playback-title").textContent = `${media}回放`;
  byId("conclusion").textContent = analysis.conclusion;
  byId("report-scope").textContent = report.identity.kind === "live" ? window.LiteUI.reportScope(report)
    : report.coverage?.message || '复盘基于本次已采集内容。';
  for (const [key, title] of [
    ["highlights", "表现亮点"],
    ["problems", "主要问题"],
  ]) {
    byId(key).innerHTML =
      analysis[key]
        .map(
          (row) =>
            `<article class="finding"><h4>${escapeHtml(row.title)}</h4><p>${escapeHtml(row.reason)}</p></article>`,
        )
        .join("") || `<p class="empty">暂无${title}</p>`;
  }
  byId("structure").innerHTML = analysis.recommended_structure
    .map((text) => `<li><span>${escapeHtml(text)}</span></li>`)
    .join("");
  byId("actions").innerHTML =
    analysis.recommendations
      .map(
        (text, i) =>
          `<li><span class="actionIndex">${i + 1}</span><span>${escapeHtml(text)}</span></li>`,
      )
      .join("") || '<li class="empty">暂无建议</li>';
  byId("metrics").innerHTML = doc.metrics
    .map(
      (row) => {
        const value = row.label === '高光时刻' ? rows.filter(r => segmentKinds(r).highlight).length
          : row.label === '问题时刻' ? rows.filter(r => segmentKinds(r).problem).length : row.value;
        const hint = ['高光时刻','问题时刻'].includes(row.label) ? '按对应内容时段计数' : row.sub_label;
        return `<div class="metric"><div>${escapeHtml(row.label)}</div><strong>${escapeHtml(value)}</strong><p>${escapeHtml(hint)}</p></div>`;
      },
    )
    .join("");
  byId("filters").innerHTML = [
    ["all", "全部"],
    ["product", ({ 电商: "商品讲解", 金融: "知识讲解", 汽车: "车型讲解" })[doc.live.scenario_name] || "内容讲解"],
    ["highlights", "高光时刻"],
    ["problems", "问题时刻"],
  ]
    .map(
      ([value, label]) =>
        `<label class="arco-radio-button${value === state.filter ? " arco-radio-checked" : ""}"><input type="radio" name="content-filter" value="${value}" ${value === state.filter ? "checked" : ""}><span class="arco-radio-button-inner">${label}</span></label>`,
    )
    .join("");
  const video = byId("video");
  if (report.video.url) {
    video.src = report.video.url;
    video.hidden = false;
    byId("video-empty").hidden = true;
  }
  renderContent();
}
byId("filters").addEventListener("change", (event) => {
  state.filter = event.target.value;
  byId("filters")
    .querySelectorAll("label")
    .forEach((label) =>
      label.classList.toggle(
        "arco-radio-checked",
        label.querySelector("input").checked,
      ),
    );
  renderContent();
});
byId("search").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderContent();
});
byId("video").addEventListener("error", () => {
  byId("video-empty").hidden = false;
  byId("video-empty").textContent = "视频播放失败；请完整解压报告 ZIP 并保留 media 目录，或下载单文件报告后用本地 Chrome 或 Edge 打开。";
});
document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-seek]");
  if (!target || target.disabled || !state.report?.video.url) return;
  const at = window.LiteUI.mediaTime(
    Number(target.dataset.seek) / 1000,
    state.report.video.timeline,
  );
  if (at === null) {
    byId("playback-tip").textContent = "该时段未录制，无法定位";
    return;
  }
  const video = byId("video");
  window.LiteUI.seek(video, at);
  video.play().catch(error => {
    if (error.name !== "AbortError") byId("playback-tip").textContent = "回放未能开始，请点击播放器重试";
  });
  video.focus({ preventScroll: true });
  video.scrollIntoView({
    block: "center",
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "auto"
      : "smooth",
  });
});
(() => {
  if (window.__reviewPayload) return renderReport(window.__reviewPayload.report);
  byId('review-state').hidden = false;
  byId('review-state').textContent = '报告缺少内嵌数据，请回到原对话重新导出。';
})();
