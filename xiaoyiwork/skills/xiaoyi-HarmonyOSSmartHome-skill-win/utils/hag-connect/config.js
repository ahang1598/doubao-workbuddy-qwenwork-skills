// ==================== HAG 云侧技能服务 API 配置 ====================
// 功能：集中管理 HAG 云侧技能服务的 API 配置（HTTPS + 认证）
// 版本：v1.1.0
// 说明：这些是默认值，实际使用时会优先从环境变量加载

/**
 * HAG API 配置（默认值）
 * 优先级：环境变量文件 > process.env > 默认值
 * 
 * 注意：SERVICE_URL 是基础域名，需要拼接 API 路径
 * 完整 URL = SERVICE_URL + '/celia-claw/v1/rest-api/skill/execute'
 */
export const HAG_CONFIG = {
  apiPath: '/celia-claw/v1/rest-api/skill/execute',
  // 桌面管道形态默认代理：SERVICE_URL 缺省时兜底，避免拼出 undefined/…
  serviceUrl: 'np://claw-skill',
  skillId: 'smartHome',
  requestFrom: 'openclaw'
};

/**
 * 获取 HAG 配置
 * @returns {object} HAG 配置
 */
export function getHagConfig() {
  return { ...HAG_CONFIG };
}

/**
 * 更新 HAG 配置
 * @param {object} updates - 更新内容
 */
export function updateHagConfig(updates) {
  if (updates.baseUrl) HAG_CONFIG.baseUrl = updates.baseUrl;
  if (updates.uid) HAG_CONFIG.uid = updates.uid;
  if (updates.apiKey) HAG_CONFIG.apiKey = updates.apiKey;
  if (updates.huid) HAG_CONFIG.huid = updates.huid;
  if (updates.skillId) HAG_CONFIG.skillId = updates.skillId;
  if (updates.requestFrom) HAG_CONFIG.requestFrom = updates.requestFrom;
}
