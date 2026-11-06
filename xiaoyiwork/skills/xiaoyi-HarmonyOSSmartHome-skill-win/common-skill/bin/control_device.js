import { hagSkillServicePost, saveDataToTxt, generateTraceId, getDefaultTimeRange, maskSecret } from '../../utils/hag-connect/utils.js';

export async function controlDevice(devId, prodId, operation, sid, data, verbose = false) {
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
  if (!prodId || typeof prodId !== 'string') {
    const error = {
      success: false,
      error: {
        code: 'INVALID_PARAM',
        message: 'prodId 不能为空且必须是字符串',
        field: 'prodId'
      },
      traceId
    };
    return error;
  }
  if (!operation || typeof operation !== 'string') {
    const error = {
      success: false,
      error: {
        code: 'INVALID_PARAM',
        message: 'operation 不能为空且必须是字符串',
        field: 'operation'
      },
      traceId
    };
    return error;
  }
  if (!sid || typeof sid !== 'string') {
    const error = {
      success: false,
      error: {
        code: 'INVALID_PARAM',
        message: 'sid 不能为空且必须是字符串',
        field: 'sid'
      },
      traceId
    };
    return error;
  }
  if (!data) {
    const error = {
      success: false,
      error: {
        code: 'INVALID_PARAM',
        message: 'data 不能为空',
        field: 'data'
      },
      traceId
    };
    return error;
  }
  
  if (verbose) console.info('[verbose] 开始控制设备');
  if (verbose) console.info(`[verbose] 设备ID: ${maskSecret(devId)}, 产品ID: ${prodId}, 操作: ${operation}, 服务: ${sid}`);
  
  const mode = 'ACK';
  const requestId = traceId;
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const timestamp = `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
  
  let parsedData;
  if (typeof data === 'string') {
    try {
      parsedData = JSON.parse(data);
    } catch (err) {
      const error = {
        success: false,
        error: {
          code: 'INVALID_JSON',
          message: 'data 解析失败，请传入有效的 JSON 字符串',
          field: 'data'
        },
        traceId
      };
      return error;
    }
  } else if (typeof data === 'object') {
    parsedData = data;
  } else {
    const error = {
      success: false,
      error: {
        code: 'INVALID_PARAM',
        message: 'data 必须是 JSON 字符串或对象',
        field: 'data'
      },
      traceId
    };
    return error;
  }
  
  const body = {
    mode,
    requestId,
    timestamp,
    devId,
    prodId,
    operation,
    sid,
    data: parsedData
  };
  
  if (verbose) console.info('[verbose] 请求体:', JSON.stringify({ ...body, devId: maskSecret(devId) }, null, 2));

  let response;
  try {
    response = await hagSkillServicePost("hagControl", body, verbose);
  } catch (error) {
    const errorResult = {
      success: false,
      error: {
        code: 'CONTROL_FAILED',
        message: `设备控制失败: ${error.message}`,
        detail: error.name
      },
      traceId
    };
    return errorResult;
  }
  
  if (verbose) console.info('[verbose] 控制响应: [已隐藏，如需查看请取消注释上一行]');
  
  return {
    success: true,
    data: {
      requestId,
      timestamp,
      traceId,
      devId: maskSecret(devId),
      prodId,
      operation,
      sid,
      response
    }
  };
}