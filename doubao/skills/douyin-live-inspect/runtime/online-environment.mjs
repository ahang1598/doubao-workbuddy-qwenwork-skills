// 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
export function onlineEnvironment(env = process.env) {
  return { ...env, DOUYIN_INSPECT_BASE_URL: 'https://livesaas.volcengineapi.com',
    DOUYIN_INSPECT_ENV: 'online', DOUYIN_INSPECT_ENV: 'online', DOUYIN_INSPECT_AUTO_LOGIN: '0' };
}
