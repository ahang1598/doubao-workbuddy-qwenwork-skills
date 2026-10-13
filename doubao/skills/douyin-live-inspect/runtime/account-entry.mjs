// 本文件负责账号入口探测的最小运行时实现：
// 只读取认证状态，并把底层状态折叠成入口分流所需的 profile_present / no_profile / unknown。
import { getAuthStatus } from "./auth.mjs";
export async function detectAccountEntry(deps = {}) {
  const s = await getAuthStatus({}, deps);
  return {
    state: s.status === "login_required" ? "no_profile" : "profile_present",
    reason: s.status,
    route: s.status === "login_required" ? "select" : "formal",
  };
}

export async function detectAccountEntryAsync({env=process.env,session,profile,readStatus=getAuthStatus}={}) {
  const read = async signal => {
    const state = await readStatus({profile}, {env,signal});
    return {state:state.status==='login_required'?'no_profile':'profile_present',reason:state.status};
  };
  try { return session ? await session.measure('account',read,{timeout:3000}) : await read(); }
  catch (error) {
    // 入口阶段把超时统一折叠成 unknown，交给上层决定是提示重试还是展示版本选择。
    if (['ENTRY_DEADLINE','ETIMEDOUT','ABORT_ERR'].includes(error.code)) return {state:'unknown',reason:'profile_check_timeout'};
    throw error;
  }
}
