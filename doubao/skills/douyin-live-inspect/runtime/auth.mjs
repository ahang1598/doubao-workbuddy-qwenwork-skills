import { taskBindingError } from './task-binding.mjs';
import { observeAccount } from './telemetry.mjs';
import {
  profileName,
  readStore,
  writeStore,
  removeStore,
  withProfileLock,
} from "./auth-store.mjs";
export const SIGNIN = "https://signin.volcengine.com";
export const SCOPE = "Console:All:All";
export const CLIENT_LOCAL = "trn:signin:::devtools/same-device";
export const CLIENT_REMOTE = "trn:signin:::devtools/cross-device";
export function requireOnline(input = {}) {
  if (
    input.boe ||
    !["online", "prod", "production"].includes(
      input.environment || input.env || "online"
    )
  )
    throw Object.assign(new Error("Only online authentication is supported"), {
      code: "INVALID_INPUT",
    });
}
export function authRequired() {
  return Object.assign(
    new Error("Independent login required; run scripts/login.mjs"),
    { code: "SETUP_PENDING", stage: "authentication", retryable: false }
  );
}
export function parseSts(value) {
  try {
    let p = value;
    for (let i = 0; i < 2 && typeof p === "string"; i++) p = JSON.parse(p);
    const result = {
      accessKeyId: p.access_key_id || p.AccessKeyID || p.accessKeyId,
      secretAccessKey:
        p.secret_access_key || p.SecretAccessKey || p.secretAccessKey,
      sessionToken: p.session_token || p.SessionToken || p.sessionToken,
    };
    if (Object.values(result).some((v) => typeof v !== "string" || !v.trim()))
      throw 0;
    return result;
  } catch {
    throw authRequired();
  }
}
export function accountIdentity(token) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return undefined;
    const p = JSON.parse(Buffer.from(parts[1], "base64url").toString());
    if (typeof p.trn !== "string" || /[\u0000-\u0020\u007f]/.test(p.trn))
      return undefined;
    return /^trn:[^:]+:[^:]*:([0-9]{1,128}):[^:]+$/.exec(p.trn)?.[1];
  } catch {
    return undefined;
  }
}
export async function exchangeToken(
  params,
  { fetchImpl = globalThis.fetch, signal } = {}
) {
  let response;
  try {
    response = await fetchImpl(`${SIGNIN}/authorize/oauth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(params).toString(),
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(30000)])
        : AbortSignal.timeout(30000),
      redirect: "error",
    });
    if (!response.ok) throw Object.assign(new Error('OAuth response rejected'), {
      code: response.status >= 500 ? 'NETWORK_ERROR' : 'AUTH_EXCHANGE_FAILED',
    });
    const chunks = [];
    let size = 0;
    if (response.body) {
      for await (const chunk of response.body) {
        const bytes = Buffer.from(chunk);
        size += bytes.length;
        if (size > 1024 * 1024) throw new Error("OAuth response too large");
        chunks.push(bytes);
      }
    } else {
      const bytes = Buffer.from(await response.text());
      if (bytes.length > 1024 * 1024)
        throw new Error("OAuth response too large");
      chunks.push(bytes);
    }
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch (error) {
    throw Object.assign(new Error("OAuth token exchange failed"), {
      code: signal?.aborted ? "ABORTED" : response ? (error?.code || "AUTH_EXCHANGE_FAILED") : "NETWORK_ERROR",
    });
  }
}
export function tokenSession(token, previous = {}, now = Date.now()) {
  parseSts(token.access_token);
  const account_id = accountIdentity(token.id_token || previous.idToken);
  const expiresIn = Number(token.expires_in);
  if (!account_id || !Number.isFinite(expiresIn) || expiresIn <= 0)
    throw authRequired();
  if (previous.account_id && account_id !== previous.account_id)
    throw taskBindingError();
  return {
    ...previous,
    environment: "online",
    account_id,
    accessToken: token.access_token,
    refreshToken: token.refresh_token || previous.refreshToken,
    idToken: token.id_token || previous.idToken,
    expiresAt: now + expiresIn * 1000,
  };
}
function validateSession(s) {
  if (
    !s ||
    !s.account_id ||
    s.environment !== "online" ||
    ![CLIENT_LOCAL, CLIENT_REMOTE].includes(s.clientId) ||
    s.account_id !== accountIdentity(s.idToken)
  )
    throw authRequired();
  return s;
}
export async function resolveCredentials(
  input = {},
  {
    env = process.env,
    fetchImpl = globalThis.fetch,
    now = Date.now,
    forceRefresh = false,
    signal,
  } = {}
) {
  requireOnline(input);
  const profile = profileName(input);
  const clock = typeof now === "function" ? now : () => now;
  return withProfileLock(
    profile,
    env,
    async () => {
      if (signal?.aborted)
        throw Object.assign(new Error("Authentication cancelled"), {
          code: "ABORT_ERR",
        });
      let s = validateSession(await readStore(profile, "session", env, signal));
      if (input.account_id && input.account_id !== s.account_id)
        throw taskBindingError();
      if (forceRefresh || input.forceRefresh || s.expiresAt - clock() < 60000) {
        if (!s.refreshToken) throw authRequired();
        const token = await exchangeToken(
          {
            grant_type: "refresh_token",
            client_id: s.clientId,
            scope: SCOPE,
            refresh_token: s.refreshToken,
          },
          { fetchImpl, signal }
        );
        s = tokenSession(token, s, clock());
        await writeStore(profile, "session", s, env);
      }
      if (!(s.expiresAt > clock())) throw authRequired();
      const credentials = { ...parseSts(s.accessToken), profile, account_id: s.account_id };
      observeAccount(credentials.account_id);
      return credentials;
    },
    { signal }
  );
}
export async function getAuthStatus(
  input = {},
  { env = process.env, now = Date.now, signal } = {}
) {
  requireOnline(input);
  const profile = profileName(input);
  try {
    const s = validateSession(await readStore(profile, "session", env, signal));
    if (input.account_id && input.account_id !== s.account_id)
      throw authRequired();
    parseSts(s.accessToken);
    const t = typeof now === "function" ? now() : now;
    return {
      profile,
      environment: "online",
      account_id: s.account_id,
      status: s.expiresAt > t ? "authenticated" : "expired",
      expires_at: new Date(s.expiresAt).toISOString(),
      refresh_available: !!s.refreshToken,
    };
  } catch (error) {
    if (signal?.aborted || error.code === "ABORT_ERR") throw error;
    return { profile, environment: "online", status: "login_required" };
  }
}
export async function resolveProfileBinding(input = {}, deps = {}) {
  requireOnline(input);
  const profile = profileName(input);
  const s = validateSession(await readStore(profile, "session", deps.env, deps.signal));
  if (input.account_id && input.account_id !== s.account_id)
    throw taskBindingError();
  return { profile, environment: "online", account_id: s.account_id };
}
export async function logout(input = {}, { env = process.env } = {}) {
  requireOnline(input);
  const profile = profileName(input);
  await withProfileLock(profile, env, async () => {
    await removeStore(profile, "session", env);
    await removeStore(profile, "pending", env);
  });
  return { profile, status: "logged_out" };
}
