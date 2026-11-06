import {
  hagSkillServicePost,
  saveDataToTxt,
  generateTraceId,
  getDefaultTimeRange,
  hagSkillServicePostWithUrlParams,
  maskSecret
} from '../../utils/hag-connect/utils.js';

export async function getDeviceDetail(devId, verbose = false) {
  const traceId = generateTraceId();
  process.stderr.write(`[trace-id] ${traceId}\n`);
  
  // 入参校验
  if (!devId || typeof devId !== 'string') {
    const error = {
      success: false,
      error: {
        code: 'INVALID_PARAM',
        message: 'devId 不能为空且必须是字符串',
        field: 'devId'
      },
      traceId
    };
    return error;
  }
  
  if (verbose) console.info('[verbose] 开始获取设备详细信息');
  if (verbose) console.info(`[verbose] 设备ID: ${maskSecret(devId)}`);
  
  const body = {
    devId
  };

  let response;
  try {
    response = await hagSkillServicePostWithUrlParams("getSmartDevDetail", body, verbose);
  } catch (error) {
    const errorResult = {
      success: false,
      error: {
        code: 'GET_DETAIL_FAILED',
        message: `获取设备详情失败: ${error.message}`,
        detail: error.name
      },
      traceId
    };
    return errorResult;
  }

  return {
    success: true,
    data: {
      traceId,
      devId: maskSecret(devId),
      response
    }
  };
}