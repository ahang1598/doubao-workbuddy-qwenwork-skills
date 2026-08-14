#!/usr/bin/env node

const fs = require("fs");

function usage() {
  console.error(
    "用法：node scripts/validate-lark-doc-result.js [--operation create|update|media-insert|fetch] <result.json|->",
  );
}

let operation = null;
const positionalArgs = [];
for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index];
  if (arg === "--operation") {
    operation = process.argv[index + 1];
    index += 1;
    continue;
  }
  if (arg.startsWith("--operation=")) {
    operation = arg.slice("--operation=".length);
    continue;
  }
  positionalArgs.push(arg);
}

const allowedOperations = ["create", "update", "media-insert", "fetch"];
if (operation && !allowedOperations.includes(operation)) {
  console.error(`不支持的操作：${JSON.stringify(operation)}。`);
  usage();
  process.exit(2);
}

const inputPath = positionalArgs[0];
if (!inputPath || positionalArgs.length !== 1) {
  usage();
  process.exit(2);
}

let raw;
try {
  raw = inputPath === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(inputPath, "utf8");
} catch (error) {
  console.error(`读取结果失败：${error.message}`);
  process.exit(2);
}

let outer;
try {
  outer = JSON.parse(raw);
} catch (error) {
  console.error(`结果不是有效的 JSON：${error.message}`);
  process.exit(2);
}

const problems = [];
let payload = outer;

// Super Doubao and similar runners may wrap the lark-cli JSON in stdout.
if (
  payload &&
  typeof payload === "object" &&
  payload.ok === undefined &&
  typeof payload.stdout === "string"
) {
  if (payload.interrupted === true) {
    problems.push("运行器返回 interrupted=true，任务已中断");
  }
  if (typeof payload.stderr === "string" && payload.stderr.trim() !== "") {
    problems.push(`运行器的 stderr 不为空：${payload.stderr.trim()}`);
  }
  try {
    payload = JSON.parse(payload.stdout);
  } catch (error) {
    problems.push(`运行器 stdout 不是有效的 lark-cli JSON：${error.message}`);
  }
}

if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
  problems.push("lark-cli 返回内容必须是 JSON 对象");
} else {
  if (payload.ok !== true) {
    problems.push(`顶层 ok 必须为 true，当前值为 ${JSON.stringify(payload.ok)}`);
  }

  const result = payload.data && payload.data.result;
  if (result !== undefined && result !== "success") {
    problems.push(`存在 data.result 时，其值必须为 success，当前值为 ${JSON.stringify(result)}`);
  }

  const warnings = [];
  const addWarnings = (value) => {
    if (Array.isArray(value)) warnings.push(...value);
    else if (value !== undefined && value !== null && String(value).trim() !== "") warnings.push(value);
  };
  addWarnings(payload.warnings);
  if (payload.data) addWarnings(payload.data.warnings);
  if (warnings.length > 0) {
    problems.push(`warnings 必须为空：${warnings.map(String).join(" | ")}`);
  }

  const data = payload.data && typeof payload.data === "object" ? payload.data : {};
  const document = data.document && typeof data.document === "object" ? data.document : {};

  if (operation === "create") {
    if (!document.document_id) problems.push("create 操作必须返回 data.document.document_id");
    if (!document.url) problems.push("create 操作必须返回 data.document.url");

    const permissionGrant = data.permission_grant || document.permission_grant;
    if (
      permissionGrant &&
      permissionGrant.status &&
      permissionGrant.status !== "granted"
    ) {
      problems.push(
        `存在 permission_grant.status 时，其值必须为 granted，当前值为 ${JSON.stringify(permissionGrant.status)}`,
      );
    }
  }

  if (operation === "update") {
    if (data.result !== "success") {
      problems.push(`update 操作要求 data.result=success，当前值为 ${JSON.stringify(data.result)}`);
    }
    if (!(Number.isFinite(data.updated_blocks_count) && data.updated_blocks_count > 0)) {
      problems.push(
        `update 操作要求 updated_blocks_count > 0，当前值为 ${JSON.stringify(data.updated_blocks_count)}`,
      );
    }
  }

  if (operation === "media-insert") {
    const blockId = data.block_id || document.block_id || (data.block && data.block.block_id);
    const fileToken =
      data.file_token ||
      document.file_token ||
      (data.file && (data.file.file_token || data.file.token));
    const fileName =
      data.file_name ||
      document.file_name ||
      (data.file && (data.file.file_name || data.file.name));
    if (!blockId) problems.push("media-insert 操作必须返回附件 block_id");
    if (!fileToken && !fileName) {
      problems.push("media-insert 操作必须返回文件 token 或文件名");
    }
  }

  if (operation === "fetch") {
    if (typeof document.content !== "string" || document.content.trim() === "") {
      problems.push("fetch 操作必须返回非空的 data.document.content");
    }
  }
}

if (problems.length > 0) {
  console.error("飞书文档操作未通过交付校验：");
  for (const problem of problems) console.error(`- ${problem}`);
  process.exit(1);
}

const result = payload.data && payload.data.result;
console.log(
  JSON.stringify(
    {
      valid: true,
      operation,
      ok: payload.ok,
      result: result === undefined ? null : result,
      warnings: 0,
      note: "命令结果校验通过；仍需通过 fetch 回读并检查文档正文。",
    },
    null,
    2,
  ),
);
