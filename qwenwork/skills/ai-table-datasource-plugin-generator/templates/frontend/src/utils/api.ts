/**
 * 后端 API 调用工具
 *
 * 开发环境：通过 Vite proxy 将 /api 请求代理到 http://localhost:8080
 * 生产环境：前端部署到 CDN 后，需要配置后端服务的完整地址
 *
 * 如需在生产环境指定后端地址，可通过环境变量 VITE_API_BASE_URL 配置：
 *   - .env.development: VITE_API_BASE_URL=（留空，走 Vite proxy）
 *   - .env.production:  VITE_API_BASE_URL=https://your-backend.example.com
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

/**
 * 获取当前用户的登录凭证（authCode）
 * 用于后续调用后端接口时进行身份验证
 */
export async function fetchLoginCode(): Promise<string> {
  const result = await (Dingdocs as any).host.run('base.user.getAuthCode');
  const code = result?.code || result;
  if (!code || typeof code !== 'string') {
    throw new Error('Failed to get auth code, please refresh and try again');
  }
  return code;
}

/**
 * 调用后端 API 的通用方法
 * @param endpoint - API 路径，如 '/your-endpoint'
 * @param loginCode - 登录凭证
 * @param params - 请求参数
 */
export async function callBackendApi<T>(
  endpoint: string,
  loginCode: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  if (!loginCode) {
    throw new Error('No login code available, cannot call API');
  }

  const response = await fetch(`${API_BASE}/api${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Login-Code': loginCode,
    },
    body: JSON.stringify({
      params: JSON.stringify(params),
      requestId: `fe-${Date.now()}`,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const result = await response.json();
  if (result.code !== 0) {
    throw new Error(result.msg || 'API call failed');
  }
  return result.data as T;
}
