import {
  hagSkillServicePost,
  generateTraceId,
} from '../../utils/hag-connect/utils.js';

export async function getDeviceProfile(prodIds = [], verbose = false) {
  const traceId = generateTraceId();
  process.stderr.write(`[trace-id] ${traceId}\n`);

  if (!Array.isArray(prodIds) || prodIds.length === 0) {
    throw new Error('产品ID列表不能为空');
  }

  if (verbose) {
    console.error('[verbose] 开始获取产品profile信息');
    console.error(`[verbose] 产品数量: ${prodIds.length}`);
  }

  const body = {
    "prodIdList": prodIds
  }

  try {
    const response = await hagSkillServicePost('getProfile', body, verbose);

    const rawData = response?.data;
    if (!rawData || !Array.isArray(rawData)) {
      throw new Error('产品profile返回了无效的数据结构');
    }

    if (verbose) console.error(`[verbose] 获取到 ${rawData.length} 个设备profile`);

    return {
      traceId,
      totalDevices: rawData.length,
      deviceProfile: rawData
    };
  } catch (apiError) {
    console.error(`[error] 获取产品profile失败: ${apiError.message}`);
    throw apiError;
  }
}