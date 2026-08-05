#!/usr/bin/env node
/*
检查飞书报告草稿中的外部参考链接是否可访问。
用法：node scripts/check-reference-links.js path/to/draft.xml
*/

const fs = require('fs');

const file = process.argv[2];
if (!file) {
  console.error('用法：node check-reference-links.js <draft.xml>');
  process.exit(2);
}

const text = fs.readFileSync(file, 'utf8');
const urls = new Set();

for (const match of text.matchAll(/href=["'](https?:\/\/[^"']+)["']/gi)) {
  urls.add(match[1]);
}
for (const match of text.matchAll(/\[[^\]]+\]\((https?:\/\/[^)\s]+)\)/g)) {
  urls.add(match[1]);
}
for (const match of text.matchAll(/https?:\/\/[^\s<>"')]+/gi)) {
  urls.add(match[0]);
}

const uniqueUrls = [...urls].map((url) => url.replace(/[，。；;,.]+$/, ''));
const failures = [];

function timeoutSignal(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, clear: () => clearTimeout(timer) };
}

async function request(url, method) {
  const timeout = timeoutSignal(8000);
  try {
    const response = await fetch(url, {
      method,
      redirect: 'follow',
      signal: timeout.signal,
      headers: {
        'user-agent': 'Mozilla/5.0 health-report-link-checker'
      }
    });
    return response.status;
  } finally {
    timeout.clear();
  }
}

async function checkUrl(url) {
  try {
    let status = await request(url, 'HEAD');
    if (status >= 200 && status < 400) return { ok: true, status };
    status = await request(url, 'GET');
    return { ok: status >= 200 && status < 400, status };
  } catch (error) {
    return { ok: false, status: error.name === 'AbortError' ? 'timeout' : error.message };
  }
}

(async () => {
  if (uniqueUrls.length === 0) {
    console.error('未发现外部链接。信息来源应包含可点击参考文档链接。');
    process.exit(1);
  }

  for (const url of uniqueUrls) {
    if (!/^https?:\/\//i.test(url)) {
      failures.push(`${url} -> URL 格式无效`);
      continue;
    }
    const result = await checkUrl(url);
    if (!result.ok) failures.push(`${url} -> ${result.status}`);
  }

  if (failures.length) {
    console.error(`链接检查失败（${failures.length}项）：`);
    for (const failure of failures) console.error(`- ${failure}`);
    process.exit(1);
  }

  console.log(`链接检查通过（${uniqueUrls.length}个）`);
})();
