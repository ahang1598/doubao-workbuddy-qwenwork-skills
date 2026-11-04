// 提供字段与身份校验、事实整理、确定性标识和限时等待等通用工具。
// 不读写业务状态或发送事件；身份解析、文件锁及 SDK 适配分别由对应模块负责。
import crypto from 'node:crypto';

// 公共字段校验与安全归属。
function validIso(value) {
  return (
    typeof value === 'string' &&
    value.length <= 64 &&
    /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value) &&
    Number.isFinite(Date.parse(value))
  );
}
function validIdentity(id) {
  return typeof id === 'string' && /^\d{1,64}$/.test(id);
}
function validIdentityEmail(email) {
  return (
    typeof email === 'string' && email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  );
}
function validIdentityUsername(name) {
  return (
    typeof name === 'string' &&
    name.length >= 1 &&
    name.length <= 64 &&
    !/\s/.test(name) &&
    !name.includes('@')
  );
}
export function enumFields(value, enums, keys = Object.keys(enums)) {
  return Object.fromEntries(
    keys.filter((key) => enums[key].includes(value[key])).map((key) => [key, value[key]]),
  );
}
export function owner(value = {}) {
  return Object.fromEntries(
    Object.entries({
      doubao_user_id: validIdentity,
      doubao_email: validIdentityEmail,
      doubao_username: validIdentityUsername,
    })
      .filter(([key, valid]) => valid(value[key]))
      .map(([key]) => [key, value[key]]),
  );
}
export { validIso, validIdentity, validIdentityEmail, validIdentityUsername };
export const hasSavedReview = (segment) =>
  segment.review_status === 'done' &&
  !!segment.review_result &&
  Object.keys(segment.review_result).length > 0;

// 事实取值、稳定比较与确定性事件标识。
const pick = (value, keys) =>
  Object.fromEntries(keys.filter((k) => value?.[k] !== undefined).map((k) => [k, value[k]]));
const equal = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
function canonical(v) {
  return Array.isArray(v)
    ? v.map(canonical)
    : v && typeof v === 'object'
      ? Object.fromEntries(
          Object.keys(v)
            .sort()
            .map((k) => [k, canonical(v[k])]),
        )
      : v;
}
function uuid5(namespace, name) {
  const bytes = Buffer.from(namespace.replaceAll('-', ''), 'hex');
  if (bytes.length !== 16) throw Error('Invalid namespace');
  const hash = crypto.createHash('sha1').update(bytes).update(name).digest().subarray(0, 16);
  hash[6] = (hash[6] & 15) | 80;
  hash[8] = (hash[8] & 63) | 128;
  const h = hash.toString('hex');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
const id = (v) => typeof v === 'string' && /^[0-9a-f]{32}$/.test(v);
export { crypto, pick, equal, canonical, uuid5, id };

// 等待超时不代表发送成功，也不会主动取消底层网络请求。
async function settleWithin(promises, timeout) {
  let timer;
  try {
    await Promise.race([
      Promise.allSettled([...(promises || [])]),
      new Promise((resolve) => {
        timer = setTimeout(resolve, timeout);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

export { settleWithin };
