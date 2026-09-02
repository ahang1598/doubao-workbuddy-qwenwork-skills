#!/usr/bin/env node
/**
 * query_placement.js — 素材策略助手：版位/尺寸/创意形式本地知识库查询
 *
 * 作用：把"产品+卖点+人群+目标"打包，从本 skill 内置的《腾讯广告投放全链路操作指引》
 * 本地知识库（references/tencent-ads-delivery-guide/）里，抽取该产品适用的
 * 版位适配、主跑尺寸/比例、创意形式、文案调性等官方口径信息。
 *
 * 🚨 已彻底移除对腾讯广告妙问（tencent-ads-assistant / chat.js / API Key）的依赖：
 *    数据全部来自本地打包的指引文档，用户无需配置任何妙问 Key 也能正常出策略。
 *
 * 用法：
 *   node query_placement.js '{"product":"手工香薰蜡烛","industry":"家居/香氛","sellingPoint":"助眠","audience":"25-40都市女性","goal":"购买转化"}'
 *
 * 输出：[PROGRESS] 过程行 + [RESULT] 结果段（结构同旧版，供上层解析）。
 * 退出码：0 成功；4 入参错误；5 本地知识库缺失。
 */
const path = require("path");
const fs = require("fs");

// 本地知识库根目录（打包进本 skill，不再依赖外部 skill）
const GUIDE_DIR = path.join(__dirname, "..", "references", "tencent-ads-delivery-guide", "references");
const CREATIVE_DEEP = path.join(GUIDE_DIR, "creative_inspiration_deep.md");
const CREATIVE_BASIC = path.join(GUIDE_DIR, "creative_inspiration_basic.md");

function fail(msg, code) {
  console.error(msg);
  process.exit(code || 1);
}

function progress(msg) {
  console.log(`[PROGRESS] ${msg}`);
}

let input;
try {
  input = JSON.parse(process.argv[2] || "{}");
} catch (e) {
  fail("[INPUT_ERROR] 参数必须是合法 JSON。示例见脚本头部注释。", 4);
}

const { product, industry = "", sellingPoint = "", audience = "", goal = "" } = input;
if (!product || !sellingPoint) {
  fail("[INPUT_ERROR] 至少需要 product 和 sellingPoint。", 4);
}

if (!fs.existsSync(CREATIVE_DEEP)) {
  fail(
    "[GUIDE_ERROR] 未找到本地投放指引知识库（references/tencent-ads-delivery-guide/）。请确认 skill 安装完整。",
    5
  );
}

progress(`读取本地投放指引知识库：${path.basename(CREATIVE_DEEP)}`);
const deep = fs.readFileSync(CREATIVE_DEEP, "utf8");
progress(`按产品「${product}」/ 行业「${industry}」/ 目标「${goal}」抽取版位与尺寸建议…`);

/**
 * 从指引「五、各版位适合的创意形式与爆款特点」抽取版位规格表。
 * 这是本地知识库里权威的版位/尺寸/创意形式数据。
 */
function extractPlacementSection(md) {
  const start = md.indexOf("## 五、各版位适合的创意形式");
  if (start < 0) return "";
  const rest = md.slice(start);
  const end = rest.indexOf("\n## 六、");
  return end < 0 ? rest : rest.slice(0, end);
}

const placementSection = extractPlacementSection(deep);

// 版位规格速查（本地知识库固化口径，供快速组装策略）
const PLACEMENTS = {
  朋友圈: {
    size: "常规大图/多图 800×800（1:1）；卡片横版视频 16:9 1280×720",
    forms: "单图 / 多图（最多9张）/ 视频 / 轮播卡片（4-6素材）",
    tone: "强广告属性开头，吸睛首帧/封面 + 简洁文案；文案上限约 30 字",
    why: "微信生态、人群精准、观看质量高（约4.6秒但意向强），适合品质转化与本地/兴趣人群",
  },
  视频号: {
    size: "竖版 9:16 720×1280 为主（另有横版16:9、4:3；动态推广不支持4:3）",
    forms: "沉浸式竖版短视频 / 轮播卡片 / 浮层卡片（可数据外显）",
    tone: "真人展示/场景演示，重要信息放安全区内（左右各46px、上154px、下196px）",
    why: "沉浸式全屏、边看边买，适合有视频物料、重展示与转化的产品",
  },
  公众号与小程序: {
    size: "16:9 横版大图 / 横版视频 16:9 / 竖版视频 9:16",
    forms: "横版大图 / 横竖版视频（文底关键词广告外层视频 6-30 秒）",
    tone: "图文资讯语境，标题化表达，信息密度可稍高",
    why: "阅读场景、图文承接自然，适合内容型/知识型产品",
  },
  "腾讯平台与内容媒体（腾讯视频/新闻）": {
    size: "常规多图 1:1 六图 / banner / 视频",
    forms: "banner / 常规多图 / 视频",
    tone: "通投泛化，画面直给核心卖点",
    why: "覆盖广、泛化流量大，适合放量与破圈",
  },
  "优量汇（腾讯营销联盟）": {
    size: "激励视频（全屏）/ 奖励式插屏 / banner / 六图",
    forms: "激励视频为主 / 插屏 / banner / 六图（不支持横版4:3视频）",
    tone: "激励语境，明确告知看完得奖励",
    why: "手游/工具类激励场景强，流量规模大",
  },
};

/**
 * 极简规则：按行业/目标粗选主推版位。
 * 说明：本地知识库不含实时竞价数据，这里给的是「官方口径 + 常识」的稳妥默认，
 * 由上层（模型）结合产品再做判断即可，不追求精确到竞价层。
 */
function recommendPrimary({ industry, audience, goal }) {
  const text = `${industry} ${audience} ${goal}`;
  // 点名视频号 / 强调视频 → 视频号
  if (/视频号|短视频|直播/.test(text)) return "视频号";
  // 手游/工具/APP → 优量汇激励
  if (/游戏|手游|工具|APP|app|应用/.test(text)) return "优量汇（腾讯营销联盟）";
  // 内容/知识/教育/资讯 → 公众号
  if (/教育|知识|课程|资讯|内容|阅读|财经/.test(text)) return "公众号与小程序";
  // 默认：微信朋友圈（人群精准、通用性最强）
  return "朋友圈";
}

const primary = recommendPrimary({ industry, audience, goal });
const p = PLACEMENTS[primary];

progress(`主推版位判定：${primary}`);

// 组装结果段（结构对齐旧版妙问输出，便于上层复用）
const lines = [];
lines.push("[RESULT]");
lines.push(`产品：${product}（行业：${industry || "未指定"}，卖点：${sellingPoint}，人群：${audience || "行业默认"}，目标：${goal || "未指定"}）`);
lines.push("");
lines.push(`1）推荐优先跑版位：${primary}`);
lines.push(`   理由：${p.why}`);
lines.push("");
lines.push(`2）推荐主跑尺寸/比例：${p.size}`);
lines.push(`   通用兜底：竖 9:16 1080×1920 / 方 1:1 800×800 / 横 16:9 1920×1080（整批横/竖/方约 4:4:2）`);
lines.push("");
lines.push(`3）推荐创意形式：${p.forms}`);
lines.push("");
lines.push(`4）文案调性建议：${p.tone}`);
lines.push("");
lines.push("— 以上依据本 skill 内置《腾讯广告投放全链路操作指引》creative_inspiration_deep.md「各版位适合的创意形式与爆款特点」章节（官方口径整理稿）。");
lines.push("");
lines.push("【原文版位规格表（供核对）】");
lines.push(placementSection.trim());

console.log(lines.join("\n"));
process.exit(0);
