// 解析安全的豆包用户归属并读取或创建本机设备 ID，兼容已有设备目录和旧标识。
// 设备标识写入失败时触发独立诊断；不将凭证或原始认证内容放入埋点。
import { validIdentity, validIdentityEmail, validIdentityUsername } from './common.mjs';
import { createRequire } from 'node:module';
import * as io from './io.mjs';
import reporter from './reporter.mjs';

const require = createRequire(import.meta.url);

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const telemetryConfigDir = io.telemetryConfigDir;
const fallbackIds = new Map();
function deviceCache(filename) {
  try {
    const value = io.readText(filename, 128).trim();
    return UUID.test(value) ? { id: value, status: 'valid' } : { status: 'invalid' };
  } catch (error) {
    return {
      status:
        error.code === 'ENOENT' ? 'missing' : error.code === 'EFILESIZE' ? 'invalid' : 'unreadable',
    };
  }
}
function resolveDeviceId(env = process.env, platform = process.platform) {
  // 遥测被明确关闭时，不读取也不创建设备标识。
  if (
    ['1', 'true'].includes(
      String(env.BYTEDLIVE_TELEMETRY_DISABLED || '')
        .trim()
        .toLowerCase(),
    )
  )
    return undefined;
  const directory = telemetryConfigDir(env, platform);
  const filename = path.resolve(directory, 'device-id');
  // Read the persistent cache before attempting any generation or filesystem write.
  // 优先复用有效缓存，避免每次运行都更换设备标识。
  let cache = deviceCache(filename);
  if (cache.id) return cache.id;
  // Explicit overrides stay isolated. Only migrate this product's historical ID.
  const legacy = env.DOUYIN_LIVE_INSPECT_CONFIG_DIR
    ? undefined
    : deviceCache(
        path.join(
          env.XDG_CONFIG_HOME || path.join(env.HOME || env.USERPROFILE || os.homedir(), '.config'),
          'byted-live-inspect',
          'device-id',
        ),
      ).id;
  // 持久化失败时仍返回本次生成的 ID，保证业务埋点有设备标识。
  const generatedId = legacy || fallbackIds.get(filename) || randomUUID();
  fallbackIds.set(filename, generatedId);
  let release;
  try {
    // 配置目录仅允许当前用户访问；文件权限也限制为当前用户读写。
    fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
    release = io.acquireSync(filename + '.lock');
    cache = deviceCache(filename);
    if (cache.id) return cache.id; // A concurrent creator or repairer already won.
    if (cache.status === 'unreadable') throw Error('Device identity unavailable');
    io.atomicWrite(filename, generatedId, { exclusive: cache.status === 'missing' });
    const repaired = deviceCache(filename);
    if (repaired.id) return repaired.id;
    throw Error('Device identity unavailable');
  } catch {
    try {
      const { EVENTS, reportEvent } = reporter;
      // 仅上报固定错误分类，不携带异常原文、文件路径或认证信息。
      void reportEvent(
        EVENTS.identity.DEVICE_ID_WRITE_FAILED,
        {
          product: 'douyin-live-inspect',
          record_type: 'telemetry_diagnostic',
          error_code: 'DEVICE_ID_WRITE_FAILED',
          device_id_cache_status: cache.status,
        },
        { toolName: 'douyin-live-inspect', env },
      ).catch(() => {});
    } catch {
      /* Optional attribution must not block inspection. */
    }
  } finally {
    // 无论成功与否都清理本次创建的临时文件。
    if (release) release();
  }
  return generatedId;
}
function numericUid(raw) {
  if (typeof raw !== 'string') return undefined;
  const uid = raw.trim();
  return validIdentity(uid) ? uid : undefined;
}
function validEmail(raw) {
  if (typeof raw !== 'string') return undefined;
  const email = raw.trim();
  return validIdentityEmail(email) ? email : undefined;
}
function usernameFromEmail(email) {
  const name = email.split('@')[0].trim();
  return validIdentityUsername(name) ? name : undefined;
}
function identityFromDoubaoToken(raw) {
  // 拒绝非字符串、超大输入以及格式不符合三段式的令牌。
  if (typeof raw !== 'string' || raw.length > 64 * 1024) return {};
  const parts = raw.split('.');
  if (parts.length !== 3 || !parts[1]) return {};
  try {
    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
    // 只处理声明为 access_token 的令牌载荷。
    if (!payload || payload.typ !== 'access_token') return {};
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
async function resolveIdentity(env = process.env) {
  // 关闭遥测时返回空对象，不解析用户身份。
  if (
    ['1', 'true'].includes(
      String(env.BYTEDLIVE_TELEMETRY_DISABLED || '')
        .trim()
        .toLowerCase(),
    )
  )
    return {};
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
const identity = {
  telemetryConfigDir,
  numericUid,
  validEmail,
  resolveIdentity,
  resolveDeviceId,
  identityFromDoubaoToken,
};
export default identity;
