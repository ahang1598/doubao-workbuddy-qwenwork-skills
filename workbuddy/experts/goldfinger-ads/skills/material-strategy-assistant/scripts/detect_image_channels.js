#!/usr/bin/env node
/*
 * 生图渠道探测脚本（material-strategy-assistant）
 *
 * 作用：在准备生图前，先探测本机可用的"兜底生图渠道"（用户已配置 key 的模型），
 *      避免直接盲调导致报错、来回试错。
 *
 * 用法：
 *   node scripts/detect_image_channels.js
 *   node scripts/detect_image_channels.js --json
 *
 * 说明：
 *   L1「WorkBuddy 内置生图」是 Agent 侧工具能力，脚本探测不到，恒定视为首选，由 Agent 直接尝试。
 *   本脚本只负责探测 L2 兜底渠道（用户自带 key 的模型）。
 *
 * 退出码：
 *   0  至少有一个 L2 兜底渠道可用
 *   1  无任何 L2 兜底渠道（需向用户索要 API Key）
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

const SKILLS_DIR = path.join(os.homedir(), '.workbuddy', 'skills');

function has(bin) {
  try {
    execSync(`command -v ${bin}`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function fileExists(p) {
  try {
    return fs.existsSync(p);
  } catch {
    return false;
  }
}

function readMoltbotKey() {
  const p = path.join(os.homedir(), '.clawdbot', 'moltbot.json');
  if (!fileExists(p)) return null;
  try {
    const cfg = JSON.parse(fs.readFileSync(p, 'utf8'));
    const s = cfg && cfg.skills && cfg.skills['nano-banana-pro'];
    if (!s) return null;
    return s.apiKey || (s.env && s.env.GEMINI_API_KEY) || null;
  } catch {
    return null;
  }
}

const channels = [];

// --- 渠道 A：API易代理（NanoBananaPro，国内直连，Node 零依赖，最省事） ---
{
  const base = path.join(SKILLS_DIR, 'nano-banana-pro-image-gen__skillhub');
  const script = path.join(base, 'scripts', 'generate_image.js');
  const keyed = !!process.env.APIYI_API_KEY;
  channels.push({
    id: 'apiyi-nanobanana',
    label: 'API易代理 · NanoBananaPro（国内直连）',
    priority: 1,
    scriptExists: fileExists(script),
    runtimeOk: has('node'),
    keySource: keyed ? 'env:APIYI_API_KEY' : null,
    keyName: 'APIYI_API_KEY',
    keyUrl: 'https://api.apiyi.com',
    cmdTemplate: `node ${script} -p "{prompt}" -f "{outfile}" -a {ratio} -r {res}`,
    editFlag: '-i {inputImage}',
    ratioSupport: ['1:1', '16:9', '9:16', '4:3', '3:4', '3:2', '2:3', '5:4', '4:5', '21:9'],
  });
}

// --- 渠道 B：Gemini 官方 nano-banana-pro（需 uv + 外网） ---
{
  const base = path.join(SKILLS_DIR, 'nano-banana-pro');
  const script = path.join(base, 'scripts', 'generate_image.py');
  const envKey = process.env.GEMINI_API_KEY || null;
  const cfgKey = readMoltbotKey();
  channels.push({
    id: 'gemini-nanobanana-pro',
    label: 'Gemini 官方 · Nano Banana Pro（需 uv + 外网）',
    priority: 2,
    scriptExists: fileExists(script),
    runtimeOk: has('uv'),
    runtimeHint: has('uv') ? null : '缺少 uv：brew install uv',
    keySource: envKey ? 'env:GEMINI_API_KEY' : cfgKey ? 'file:~/.clawdbot/moltbot.json' : null,
    keyName: 'GEMINI_API_KEY',
    keyUrl: 'https://aistudio.google.com/apikey',
    cmdTemplate: `uv run ${script} --prompt "{prompt}" --filename "{outfile}" --resolution {res}`,
    editFlag: '--input-image {inputImage}',
    ratioSupport: [],
  });
}

for (const c of channels) {
  c.ready = !!(c.scriptExists && c.runtimeOk && c.keySource);
  c.blockedBy = c.ready
    ? null
    : !c.scriptExists
    ? 'script-missing'
    : !c.runtimeOk
    ? 'runtime-missing'
    : 'key-missing';
}

const ready = channels.filter((c) => c.ready).sort((a, b) => a.priority - b.priority);
const result = {
  builtinFirst: true,
  builtinNote: 'L1 = WorkBuddy 内置生图能力，恒定首选，由 Agent 直接调用，脚本无法探测',
  readyChannels: ready.map((c) => c.id),
  channels,
};

if (process.argv.includes('--json')) {
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log('[L1] WorkBuddy 内置生图 —— 恒定首选，直接调用（脚本探测不到）');
  console.log('[L2] 兜底渠道探测结果：');
  for (const c of channels) {
    const mark = c.ready ? 'READY' : 'NOT_READY';
    console.log(`  - ${mark} | ${c.label}`);
    if (!c.ready) {
      if (c.blockedBy === 'key-missing') {
        console.log(`      缺少 API Key：${c.keyName}（获取：${c.keyUrl}）`);
      } else if (c.blockedBy === 'runtime-missing') {
        console.log(`      运行环境不满足：${c.runtimeHint || 'runtime missing'}`);
      } else {
        console.log('      技能脚本不存在，需先安装对应生图技能');
      }
    } else {
      console.log(`      Key 来源：${c.keySource}`);
    }
  }
  console.log('');
  console.log(
    ready.length
      ? `[RESULT] 可用兜底渠道：${ready.map((c) => c.id).join(', ')}（优先用 ${ready[0].id}）`
      : '[RESULT] 无可用兜底渠道 —— 若 L1 内置生图失败，需向用户索要 API Key'
  );
}

process.exit(ready.length ? 0 : 1);
