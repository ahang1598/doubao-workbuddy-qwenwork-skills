export function onlineEnvironment(env = process.env) {
  return { ...env, DOUYIN_INSPECT_BASE_URL: 'https://livesaas.volcengineapi.com',
    DOUYIN_INSPECT_ENV: 'online', DOUYIN_INSPECT_ENV: 'online', DOUYIN_INSPECT_AUTO_LOGIN: '0' };
}
