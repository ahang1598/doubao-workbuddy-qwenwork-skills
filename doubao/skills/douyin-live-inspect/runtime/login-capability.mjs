// 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
export { readAuthorizationResponse } from "./auth-login.mjs";
export { runLogin as runVerifiedLogin } from "./auth-login.mjs";
export function probeLoginCapability() {
  return {
    status: "ready",
    implementation: "standalone-node",
    manual_browser: true,
    remote_resume_stdin: true,
  };
}
export function publicCapabilityResult(result) {
  return result;
}
