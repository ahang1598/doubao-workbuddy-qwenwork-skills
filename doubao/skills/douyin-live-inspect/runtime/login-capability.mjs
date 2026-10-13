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
