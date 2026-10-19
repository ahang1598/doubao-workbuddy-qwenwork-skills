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
  return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
}
function timeButton(start, end) {
  const video = state.report.video;
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
  const gaps = (report.coverage?.gaps || []).filter(g => g.start_ms < row.end_time && g.end_ms > row.start_time);
  const refs = new Set((report.evidence || []).filter(e => e.start_ms < row.end_time && e.end_ms > row.start_time).map(e => e.id));
  const analysis = report.document.modules?.content_analysis || {};
  const notes = Object.entries(report.references || {}).flatMap(([key, groups]) => groups.flatMap((ids, i) => {
    if (!ids.some(id => refs.has(id))) return [];
    const item = analysis[key]?.[i];
    return [typeof item === "string" ? item : item?.reason || item?.title || ""];
  }));
  const detail = row.moment_detail;
  const result = {
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

function renderContent() {
  const query = state.query.trim().toLocaleLowerCase();
  const rows = state.report.document.content.segments.filter((row) => {
    const detail = query ? detailText(row) : null;
    const matches =
      state.filter === "all" ||
      (state.filter === "product"
        ? row.labels.includes(1)
        : state.filter === "highlights"
          ? row.labels.includes(2)
          : row.labels.includes(3) || row.labels.includes(4));
    return (
      matches &&
      (!query ||
        [
          row.content,
          row.title,
          ...row.tags,
          detail.title,
          ...detail.paragraphs,
        ].some((text) => text?.toLocaleLowerCase().includes(query)))
    );
  });
  window.LiteUI.renderRows(byId("timeline"), rows,
      (row) =>
        `<li class="segment"><div class="timeRow"><span class="dot"></span>${timeButton(row.start_time, row.end_time)}</div><article class="segmentBody"><div class="segmentTitle"><h3>${escapeHtml(row.title || "语音识别内容")}</h3><div class="tags">${row.tags.map((tag) => `<span class="${tag.includes("问题") || tag.includes("违规") ? "problemTag" : tag.includes("高光") ? "highlightTag" : "tag"}">${escapeHtml(tag)}</span>`).join("")}</div></div><p>${escapeHtml(row.content)}</p>${contentDetails(row)}${row.frame_images?.length ? `<div class="images">${row.frame_images.map((url) => `<button type="button" data-preview="${escapeHtml(url)}" aria-label="查看画面证据"><img src="${escapeHtml(url)}" alt="该时间段的质检画面证据" loading="lazy"></button>`).join("")}</div>` : ""}</article></li>`,
    );
  byId("timeline-end").textContent = rows.length
    ? "没有更多数据了"
    : "当前筛选下没有内容片段";
  byId("analysis-body").scrollTop = 0;
}
function renderReport(report) {
  state.report = report;
  byId("review-state").hidden = report.available;
  byId("report").hidden = !report.available;
  byId("review-state").textContent = report.message;
  if (!report.available) return;
  const doc = report.document;
  const analysis = doc.modules.content_analysis;
  const media = report.identity.kind === "video" ? "视频" : "直播";
  document.title = `${doc.live.title} · 复盘`;
  byId("report-title").textContent = `${media}复盘报告`;
  byId("cover-label").textContent = `${media}复盘`;
  byId("task-name").textContent = `${doc.live.title} · 复盘`;
  byId("duration").textContent = `${media}时长：${doc.live.duration_text}`;
  byId("scenario").textContent = doc.live.scenario_name;
  byId("scenario").hidden = !doc.live.scenario_name;
  const rows = doc.content.segments;
  byId("session").textContent = rows.length
    ? `${time(rows[0].start_time)} ~ ${time(rows.at(-1).end_time)}`
    : "无有效内容";
  byId("data-title").textContent = `${media}数据`;
  byId("playback-title").textContent = `${media}回放`;
  byId("conclusion").textContent = analysis.conclusion + (report.coverage?.gaps?.length ? ` ${report.coverage.message} ${[...new Set(report.coverage.gaps.map(g => g.reason).filter(Boolean))].join("；")}` : "");
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
      (row) =>
        `<div class="metric"><div>${escapeHtml(row.label)}</div><strong>${escapeHtml(row.value)}</strong><p>${escapeHtml(row.sub_label)}</p></div>`,
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
  window.LiteUI.seek(byId("video"), at);
  byId("video").focus({ preventScroll: true });
  byId("video").scrollIntoView({
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
