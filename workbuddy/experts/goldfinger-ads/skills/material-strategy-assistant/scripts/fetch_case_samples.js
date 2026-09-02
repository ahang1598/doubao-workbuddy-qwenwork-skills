#!/usr/bin/env node
/**
 * fetch_case_samples.js —— 从平台案例库（creative_examples）拉取官方示例图，落地到输出目录。
 *
 * 覆盖两组资源（同一张 creative_examples 表，按 title 映射）：
 *   A. 13 类官方标准样式示例图 → <outputDir>/assets/case_samples/{类型}.{真实扩展名}
 *   B. 5 张版位结构示意图（朋友圈/视频号/公众号/平台与内容信息流/开屏）→ <outputDir>/assets/placement_structures/{版位}.{真实扩展名}
 *
 * 数据源（平台优先、本地兜底）：
 *   ① 平台：生产 MCP endpoint（默认 PROD_URL，可用 --endpoint 或环境变量 CASE_EXAMPLES_MCP_URL 覆盖）
 *      调 MCP 工具 list_creative_examples()（无入参）→ 返回 items[{id,title,mime_type,extra,file_url}]
 *      → 按 title 先匹配 13 类、再匹配 5 版位（顺序重要：如"公众号资讯"必须先归 13 类，不能错配版位"公众号"）
 *      → GET file_url 下载到对应目录
 *   ② 兜底：平台不可用/表未灌数据/个别下载失败时，自动回退复制本 skill 内置的
 *      assets/case_samples/*.webp 与 assets/placement_structures/*.webp，保证交付链路（HTML → inline_assets.js → PDF）永远有图。
 *
 * 用法：
 *   node fetch_case_samples.js <outputDir> [--endpoint https://.../mcp]
 *
 * 输出约定（与 query_placement.js 一致）：
 *   [PROGRESS] 过程行 / [RESULT] 结果段（含每张图最终文件名，HTML 引用以此为准）/ [WARN] 警告 / [FALLBACK] 回退提示
 *   退出码：0 = 全部就绪（平台或兜底）；2 = 平台与本地双双不可用（此时交付物走「文字兜底」：在原图位置用 1-2 句话描述素材/版位特征代替，不留空图、照常出 PDF）
 *
 * 🚨 环境说明：真正决定读生产库还是测试库的是这里连接的 MCP endpoint 地址本身；
 *    file_url 的域名由平台按请求头动态推导，脚本不做任何域名拼接，只使用返回值。
 */
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const PROD_URL = 'https://ad-goldfinger.app.fitgroup-fat.com/mcp';
const SKILL_ROOT = path.resolve(__dirname, '..');

// 资源组定义：名称集合 + 落地子目录 + 本地兜底目录
const GROUPS = [
  {
    name: '标准样式示例图',
    types: ['常规海报','模拟朋友圈','小红书笔记','仿对话','数字人海报','公众号资讯','榜单素材','户外海报','备忘录','大字报','九图拼接','四图拼接','IP海报'],
    sub: 'case_samples',
  },
  {
    name: '版位结构示意图',
    types: ['朋友圈','视频号','公众号','平台与内容信息流','开屏'],
    sub: 'placement_structures',
  },
];

const MIME_EXT = { 'image/webp':'.webp', 'image/jpeg':'.jpg', 'image/jpg':'.jpg', 'image/png':'.png', 'image/gif':'.gif', 'video/mp4':'.mp4' };

function log(tag, msg) { console.log(`[${tag}] ${msg}`); }

// ---------- MCP JSON-RPC (streamable HTTP) ----------
function rpc(endpoint, method, params) {
  const payload = JSON.stringify({ jsonrpc: '2.0', id: Math.floor(Math.random() * 1e6), method, params: params || {} });
  // 1) initialize（拿 session id；部分无状态服务可省略，失败不阻断）
  let sid = '';
  try {
    const hFile = path.join(os.tmpdir(), `mcp_h_${Date.now()}.txt`);
    execSync(`curl -sS -D ${JSON.stringify(hFile)} -o /dev/null -X POST ${JSON.stringify(endpoint)} `
      + `-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" `
      + `-d ${JSON.stringify(JSON.stringify({ jsonrpc:'2.0', id:1, method:'initialize', params:{ protocolVersion:'2025-03-26', capabilities:{}, clientInfo:{ name:'material-strategy-assistant', version:'1.0' } } }))} `
      + `--max-time 20`, { stdio: 'pipe' });
    const h = fs.readFileSync(hFile, 'utf8');
    const m = h.match(/mcp-session-id:\s*(\S+)/i);
    if (m) sid = m[1].trim();
    try { fs.unlinkSync(hFile); } catch (_) {}
  } catch (_) { /* 无状态服务直接调 tools/call */ }

  // 2) 真正的调用
  const cmd = `curl -sS -X POST ${JSON.stringify(endpoint)} `
    + `-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" `
    + (sid ? `-H "Mcp-Session-Id: ${sid}" ` : '')
    + `-d ${JSON.stringify(payload)} --max-time 30`;
  const raw = execSync(cmd, { stdio: ['ignore','pipe','pipe'], encoding: 'utf8' }).toString();
  // 响应可能是 SSE 帧（data: {...}），逐行取第一个可解析 JSON
  for (const line of raw.split(/\r?\n/)) {
    const s = line.replace(/^data:\s*/, '').trim();
    if (!s.startsWith('{')) continue;
    try { const j = JSON.parse(s); if (j.id !== undefined && j.result !== undefined) return j; } catch (_) {}
  }
  try { const j = JSON.parse(raw); if (j && j.result !== undefined) return j; } catch (_) {}
  throw new Error(`MCP 响应不可解析：${raw.slice(0, 200)}`);
}

function parseItems(resp) {
  const content = resp && resp.result && resp.result.content;
  if (!Array.isArray(content) || !content[0] || typeof content[0].text !== 'string') throw new Error('返回结构缺少 content[0].text');
  if (resp.result.isError) throw new Error(`平台工具执行失败：${content[0].text.slice(0, 200)}`);
  const text = content[0].text;
  let parsed;
  try { parsed = JSON.parse(text); } catch (_) {
    const m = text.match(/\{[\s\S]*\}/); // 从混杂文本里抠出 JSON 体
    if (!m) throw new Error('返回 text 不是合法 JSON');
    parsed = JSON.parse(m[0]);
  }
  if (!Array.isArray(parsed.items)) throw new Error('返回缺少 items 数组');
  return parsed.items;
}

// title → 资源映射：按组顺序（先 13 类、后 5 版位，避免"公众号资讯"错配版位"公众号"）；
// 组内先精确（去空白后全等），再双向包含。
function mapItem(title) {
  const norm = (s) => String(s || '').replace(/[\s\u3000]/g, '').toLowerCase();
  const t = norm(title);
  for (const g of GROUPS) {
    const exact = g.types.find((k) => norm(k) === t);
    if (exact) return { group: g, type: exact };
  }
  for (const g of GROUPS) {
    const contains = g.types.find((k) => t.includes(norm(k)));
    if (contains) return { group: g, type: contains };
  }
  for (const g of GROUPS) {
    const rev = g.types.find((k) => norm(k).includes(t));
    if (rev) return { group: g, type: rev };
  }
  return null;
}

function download(url, dest) {
  execSync(`curl -sSL -o ${JSON.stringify(dest)} ${JSON.stringify(url)} --max-time 60`, { stdio: ['ignore','pipe','pipe'] });
  if (!fs.existsSync(dest)) return false;
  const size = fs.statSync(dest).size;
  // 🚨 校验1：真实图片/视频不会小于 1KB。平台"有记录读不出图"时会返回 49 字节的错误 JSON，必须判失败。
  if (size < 1024) {
    try {
      const head = fs.readFileSync(dest).slice(0, 200).toString('utf8');
      // 🚨 校验2：内容是 JSON 错误体（如 {"success":false,"error":"范例图读取失败"}）视为失败
      if (/^\s*[\{\[]/.test(head) || /success"?\s*:\s*false|error/i.test(head)) {
        try { fs.unlinkSync(dest); } catch (_) {}
        return false;
      }
    } catch (_) {}
    // 即便不是 JSON，<1KB 也几乎不可能是有效图，判失败并删除，交给本地兜底
    try { fs.unlinkSync(dest); } catch (_) {}
    return false;
  }
  return true;
}

function main() {
  const args = process.argv.slice(2);
  const outputDir = args[0];
  if (!outputDir) { console.error('[USAGE] node fetch_case_samples.js <outputDir> [--endpoint URL]'); process.exit(1); }
  const epIdx = args.indexOf('--endpoint');
  const endpoint = epIdx > -1 ? args[epIdx + 1] : (process.env.CASE_EXAMPLES_MCP_URL || PROD_URL);
  const outRoot = path.resolve(outputDir);

  // 每组的落地目录与就绪表
  const state = GROUPS.map((g) => {
    const destDir = path.join(outRoot, 'assets', g.sub);
    fs.mkdirSync(destDir, { recursive: true });
    return { group: g, destDir, landed: {} }; // landed: 类型 -> 文件名
  });

  log('PROGRESS', `连接平台案例库 MCP：${endpoint}`);
  let totalTypes = GROUPS.reduce((n, g) => n + g.types.length, 0);

  // ① 平台链路
  try {
    const resp = rpc(endpoint, 'tools/call', { name: 'list_creative_examples', arguments: {} });
    const items = parseItems(resp);
    log('PROGRESS', `平台返回 ${items.length} 条案例`);
    if (items.length === 0) throw new Error('平台返回空数组（生产库尚未灌入数据）');
    const unmatched = [];
    for (const it of items) {
      const hit = mapItem(it.title);
      if (!hit) { unmatched.push(`${it.title}(${it.id})`); continue; }
      const st = state.find((s) => s.group === hit.group);
      const ext = MIME_EXT[(it.mime_type || '').toLowerCase()] || path.extname(it.file_url || '') || '.webp';
      const fname = `${hit.type}${ext}`;
      const dest = path.join(st.destDir, fname);
      if ((it.mime_type || '').startsWith('video/')) {
        // 视频案例：仅落地记录，不进 PDF 内嵌链路
        if (download(it.file_url, dest)) { st.landed[hit.type] = fname; log('WARN', `${hit.type} 是视频案例（${fname}），已下载但不内嵌 PDF，仅作参考`); }
        continue;
      }
      if (download(it.file_url, dest)) { st.landed[hit.type] = fname; log('PROGRESS', `已下载 ${it.title} → assets/${hit.group.sub}/${fname}`); }
      else log('WARN', `下载失败：${it.title} ${it.file_url}`);
    }
    if (unmatched.length) log('WARN', `未能映射到官方资源名的平台条目：${unmatched.join('、')}（请核对平台 title 命名）`);
  } catch (e) {
    log('WARN', `平台链路不可用：${e.message}`);
  }

  // ② 本地兜底：补齐两组中平台没落地的
  let anyFallback = false;
  for (const st of state) {
    const localDir = path.join(SKILL_ROOT, 'assets', st.group.sub);
    const missing = st.group.types.filter((t) => !st.landed[t]);
    if (!missing.length || !fs.existsSync(localDir)) continue;
    const copied = [];
    for (const t of missing) {
      const src = path.join(localDir, `${t}.webp`);
      if (fs.existsSync(src)) { fs.copyFileSync(src, path.join(st.destDir, `${t}.webp`)); st.landed[t] = `${t}.webp`; copied.push(t); }
    }
    if (copied.length) { anyFallback = true; log('FALLBACK', `${st.group.name}：以下 ${copied.length} 张回退 skill 内置本地样例 → ${copied.join('、')}`); }
  }

  // ③ 汇总
  const readyCount = state.reduce((n, s) => n + Object.keys(s.landed).length, 0);
  log('RESULT', `示例图就绪 ${readyCount}/${totalTypes} 张（案例图 ${Object.keys(state[0].landed).length}/13 类，版位图 ${Object.keys(state[1].landed).length}/5 张），落地根目录：${path.join(outRoot, 'assets')}`);
  const lines = [];
  for (const st of state) {
    lines.push(`  ── ${st.group.name}（assets/${st.group.sub}/）`);
    for (const t of st.group.types) lines.push(st.landed[t] ? `    ${st.landed[t]}  <-  ${t}` : `    ❌ ${t} 未获取到（平台与本地均缺失）→ 该图走文字兜底：在原图位置改用 1-2 句话描述该${st.group.name === '版位结构示意图' ? '版位里外层文案/创意图/转化按钮/首评的位置' : '类型的版式特征'}，不要留空图框`);
  }
  const missingAll = state.reduce((n, s) => n + s.group.types.filter((t) => !s.landed[t]).length, 0);
  if (missingAll > 0) log('WARN', `有 ${missingAll} 张图平台与本地均缺失 → 按 SKILL.md 第 2.5 步「图拉不到时的文字兜底」，在原图位置用 1-2 句话描述素材特征代替，不留空图、不卡流程`);
  log('RESULT', `HTML 引用文件名（相对输出目录）：\n${lines.join('\n')}`);
  if (readyCount === 0) { log('WARN', '平台与本地均无可用示例图 → 全部走文字兜底：交付物里每张图位置改用 1-2 句话描述素材/版位特征（见 SKILL.md 第 2.5 步），不留空图、照常出 PDF；退出码 2 仅表示未落地任何图片文件，不代表流程失败'); process.exit(2); }
  if (readyCount < totalTypes) log('WARN', `有 ${totalTypes - readyCount} 张缺图 → 缺的那几张走文字兜底（1-2 句话描述特征），拿到的照常放图`);
  process.exit(0);
}

main();
