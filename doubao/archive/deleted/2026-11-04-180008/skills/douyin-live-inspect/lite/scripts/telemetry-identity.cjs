"use strict";

// 本文件负责遥测身份与设备标识解析：
// 生成或复用持久化 deviceId，并从环境变量或宿主令牌中提取允许上报的低敏身份字段。

// 本模块只负责遥测所需的身份字段和设备标识，不参与业务检查逻辑。
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
// 仅接受符合 UUID v4 格式的持久化设备标识。
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

// Both script tools share the Skill's device directory, independent of task/version.
function telemetryConfigDir(env = process.env, platform = process.platform) {
  if (env.DOUYIN_LIVE_INSPECT_CONFIG_DIR) return env.DOUYIN_LIVE_INSPECT_CONFIG_DIR;
  const home = env.HOME || env.USERPROFILE || os.homedir();
  const base = platform === 'darwin' ? path.join(home, 'Library', 'Application Support')
    : platform === 'win32' ? env.LOCALAPPDATA || path.join(home, 'AppData', 'Local')
    : env.XDG_CONFIG_HOME || path.join(home, '.config');
  return path.join(base, 'douyin-live-inspect');
}

function cachedDeviceId(filename) {
  try {
    const value = fs.readFileSync(filename, 'utf8').trim();
    if (UUID.test(value)) return value;
  } catch { /* Missing or unreadable identity is optional. */ }
}

// 读取或首次生成设备 ID；遥测关闭或本地操作失败时不影响主流程。
function resolveDeviceId(env = process.env, platform = process.platform) {
  // 遥测被明确关闭时，不读取也不创建设备标识。
  if (['1', 'true'].includes(String(env.BYTEDLIVE_TELEMETRY_DISABLED || '').trim().toLowerCase())) return undefined;
  const directory = telemetryConfigDir(env, platform);
  const filename = path.join(directory, 'device-id');
  // Read the persistent cache before attempting any generation or filesystem write.
  // 优先复用有效缓存，避免每次运行都更换设备标识。
  const cached = cachedDeviceId(filename);
  if (cached) return cached;
  // Explicit overrides stay isolated. Only migrate this product's historical ID.
  const legacy = env.DOUYIN_LIVE_INSPECT_CONFIG_DIR ? undefined : cachedDeviceId(path.join(
    env.XDG_CONFIG_HOME || path.join(env.HOME || env.USERPROFILE || os.homedir(), '.config'),
    'byted-live-inspect', 'device-id'));
  // 持久化失败时仍返回本次生成的 ID，保证业务埋点有设备标识。
  const generatedId = legacy || randomUUID();
  let temporary;
  try {
    // 配置目录仅允许当前用户访问；文件权限也限制为当前用户读写。
    fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
    if (!fs.existsSync(filename)) {
      temporary = path.join(directory, `.device-id-${generatedId}`);
      fs.writeFileSync(temporary, generatedId, { flag: 'wx', mode: 0o600 });
      // Publish a complete UUID atomically; concurrent first runs share the winner.
      // 通过硬链接一次性发布完整 ID；并发创建时保留先成功的文件。
      try { fs.linkSync(temporary, filename); } catch (error) { if (error.code !== 'EEXIST') throw error; }
    }
    const id = fs.readFileSync(filename, 'utf8').trim();
    if (UUID.test(id)) return id;
  } catch {
    try {
      const {EVENTS, reportEvent} = require('../../runtime/telemetry-reporter.cjs');
      // 仅上报固定错误分类，不携带异常原文、文件路径或认证信息。
      void reportEvent(EVENTS.identity.DEVICE_ID_WRITE_FAILED, {
        product: 'douyin-live-inspect', record_type: 'telemetry_diagnostic',
        error_code: 'DEVICE_ID_WRITE_FAILED',
      }, {toolName: 'byted-live-inspect', env}).catch(() => {});
    } catch { /* Optional attribution must not block inspection. */ }
  }
  // 无论成功与否都清理本次创建的临时文件。
  finally { if (temporary) { try { fs.unlinkSync(temporary); } catch {} } }
  return generatedId;
}

// 校验数字用户 ID，避免把任意字符串作为遥测身份上报。
function numericUid(raw) {
  if (typeof raw !== "string") return undefined;
  const uid = raw.trim();
  return /^\d{1,64}$/.test(uid) ? uid : undefined;
}

// Deliberately conservative: an internal work email, never a token or arbitrary input.
// 仅接受格式合理且长度受限的邮箱地址。
function validEmail(raw) {
  if (typeof raw !== "string") return undefined;
  const email = raw.trim();
  if (email.length === 0 || email.length > 254) return undefined;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : undefined;
}

// The login name is the mailbox local-part; no separate employee-number claim is trusted.
// 从邮箱 @ 前的部分提取登录名，不推断或伪造员工编号。
function usernameFromEmail(email) {
  const name = email.split("@")[0].trim();
  return name.length >= 1 && name.length <= 64 && !/\s/.test(name) ? name : undefined;
}

// Read only the low-sensitivity claims we are allowed to report. The token itself
// stays in memory: it is deleted from the environment by the callers before business runs.
// 只解析令牌载荷中的允许字段；不验证签名，也不返回或记录令牌本身。
function identityFromDoubaoToken(raw) {
  // 拒绝非字符串、超大输入以及格式不符合三段式的令牌。
  if (typeof raw !== "string" || raw.length > 64 * 1024) return {};
  const parts = raw.split(".");
  if (parts.length !== 3 || !parts[1]) return {};
  try {
    const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8"));
    // 只处理声明为 access_token 的令牌载荷。
    if (!payload || payload.typ !== "access_token") return {};
    const identity = {};
    const uid = numericUid(payload.uid);
    if (uid) identity.uid = uid;
    const email = validEmail(payload.email);
    if (email) identity.email = email;
    return identity;
  } catch {
    // 无效编码或 JSON 均按无身份信息处理。
    return {};
  }
}

// 汇总遥测身份：显式环境变量优先，其次使用令牌载荷中的校验后字段。
async function resolveIdentity(env = process.env) {
  // 关闭遥测时返回空对象，不解析用户身份。
  if (["1", "true"].includes(String(env.BYTEDLIVE_TELEMETRY_DISABLED || "").trim().toLowerCase())) return {};
  const token = identityFromDoubaoToken(env.DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN);
  const identity = {};
  // 显式用户 ID 优先于令牌中的 UID。
  const uid = numericUid(env.BYTEDLIVE_DOUBAO_USER_ID) || token.uid;
  if (uid) identity.doubao_user_id = uid;
  const email = validEmail(env.BYTEDLIVE_DOUBAO_EMAIL) || token.email;
  if (email) {
    identity.doubao_email = email;
    const username = usernameFromEmail(email);
    if (username) identity.doubao_username = username;
  }
  return identity;
}

// 导出配置目录、字段校验器和身份解析函数，供遥测实现复用。
module.exports = { telemetryConfigDir, numericUid, validEmail, resolveIdentity, resolveDeviceId, identityFromDoubaoToken };
