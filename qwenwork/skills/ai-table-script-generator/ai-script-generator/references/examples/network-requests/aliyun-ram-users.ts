/**
 * 阿里云 RAM 用户列表获取工具
 * 基于阿里云 OpenAPI 签名机制 v1.0
 * API文档: https://help.aliyun.com/zh/ram/developer-reference/api-ram-2015-05-01-listusers
 */

/**
 * 获取 RAM 用户列表
 * @param {Object} config - 配置参数
 * @param {string} config.accessKeyId - 阿里云 AccessKey ID
 * @param {string} config.accessKeySecret - 阿里云 AccessKey Secret
 * @param {string} [config.endpoint='ram.aliyuncs.com'] - API endpoint
 * @param {string} [config.marker] - 分页标记，用于获取下一页数据
 * @param {number} [config.maxItems=100] - 每页返回的最大条数，取值范围：1~1000
 * @returns {Promise<Object>} 返回用户列表响应
 */
async function listRamUsers(config) {
  const {
    accessKeyId,
    accessKeySecret,
    endpoint = 'ram.aliyuncs.com',
    marker,
    maxItems = 100
  } = config;

  // 参数校验
  if (!accessKeyId || !accessKeySecret) {
    throw new Error('accessKeyId and accessKeySecret are required');
  }

  // 1. 构建请求参数
  const params = {
    Format: 'JSON',
    Version: '2015-05-01',
    AccessKeyId: accessKeyId,
    SignatureMethod: 'HMAC-SHA1',
    Timestamp: generateTimestamp(),
    SignatureVersion: '1.0',
    SignatureNonce: generateNonce(),
    Action: 'ListUsers'
  };

  // 添加业务参数
  if (marker) {
    params.Marker = marker;
  }
  if (maxItems) {
    params.MaxItems = maxItems.toString();
  }

  // 2. 生成签名
  const signature = await generateSignature(accessKeySecret, params);
  params.Signature = signature;

  // 3. 构建请求 URL
  const url = buildRequestUrl(endpoint, params);

  console.log('Request URL:', url);

  // 4. 发送 HTTP 请求
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // 5. 检查 API 错误
    if (data.Code) {
      throw new Error(`API error: ${data.Code} - ${data.Message}`);
    }

    // 6. 解析响应数据
    const users = data.Users?.User || [];
    const isTruncated = data.IsTruncated || false;
    const nextMarker = data.Marker;

    return {
      totalCount: users.length,
      userList: users,
      hasMore: isTruncated,
      marker: isTruncated ? nextMarker : null,
      requestId: data.RequestId
    };

  } catch (error) {
    console.error('listRamUsers error:', error);
    throw error;
  }
}

/**
 * 生成 UTC 时间戳
 * 格式: yyyy-MM-dd'T'HH:mm:ss'Z'
 */
function generateTimestamp() {
  const now = new Date();
  return now.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

/**
 * 生成随机 Nonce
 */
function generateNonce() {
  return crypto.randomUUID();
}

/**
 * URL 编码（按照阿里云要求）
 * @param {string} value - 要编码的值
 * @returns {string} 编码后的字符串
 */
function percentEncode(value) {
  if (value == null) {
    return '';
  }
  return encodeURIComponent(value)
    .replace(/!/g, '%21')
    .replace(/'/g, '%27')
    .replace(/\(/g, '%28')
    .replace(/\)/g, '%29')
    .replace(/\*/g, '%2A')
    .replace(/\+/g, '%20')
    .replace(/%7E/g, '~');
}

/**
 * 生成签名
 * @param {string} accessKeySecret - AccessKey Secret
 * @param {Object} params - 请求参数
 * @returns {Promise<string>} Base64 编码的签名
 */
async function generateSignature(accessKeySecret, params) {
  // 1. 参数排序（按参数名的字典序升序排列）
  const sortedKeys = Object.keys(params).sort();

  // 2. 构造规范化请求字符串
  const canonicalizedQueryString = sortedKeys
    .filter(key => key !== 'Signature')
    .map(key => `${percentEncode(key)}=${percentEncode(params[key])}`)
    .join('&');

  // 3. 构造待签名字符串
  const stringToSign = `GET&${percentEncode('/')}&${percentEncode(canonicalizedQueryString)}`;

  console.log('String to sign:', stringToSign);

  // 4. 计算签名
  const key = `${accessKeySecret}&`;
  const encoder = new TextEncoder();
  const keyData = encoder.encode(key);
  const messageData = encoder.encode(stringToSign);

  // 使用 Web Crypto API 进行 HMAC-SHA1 签名
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-1' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', cryptoKey, messageData);

  // 转换为 Base64
  const signatureArray = new Uint8Array(signature);
  const base64String = btoa(String.fromCharCode(...signatureArray));

  return base64String;
}

/**
 * 构建完整的请求 URL
 * @param {string} endpoint - API endpoint
 * @param {Object} params - 请求参数
 * @returns {string} 完整的请求 URL
 */
function buildRequestUrl(endpoint, params) {
  const sortedKeys = Object.keys(params).sort();
  const queryString = sortedKeys
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');

  return `https://${endpoint}/?${queryString}`;
}

/**
 * 获取所有 RAM 用户（自动处理分页）
 * @param {Object} config - 配置参数
 * @param {string} config.accessKeyId - 阿里云 AccessKey ID
 * @param {string} config.accessKeySecret - 阿里云 AccessKey Secret
 * @param {string} [config.endpoint='ram.aliyuncs.com'] - API endpoint
 * @param {number} [config.maxItems=100] - 每页返回的最大条数
 * @returns {Promise<Array>} 返回所有用户列表
 */
async function listAllRamUsers(config) {
  const allUsers = [];
  let marker = null;
  let hasMore = true;

  while (hasMore) {
    const response = await listRamUsers({
      ...config,
      marker
    });

    allUsers.push(...response.userList);
    hasMore = response.hasMore;
    marker = response.marker;

    console.log(`Fetched ${response.userList.length} users, total: ${allUsers.length}`);
  }

  return allUsers;
}

// 使用示例
async function main(accessKeyId, accessKeySecret) {
  try {
    // 获取所有用户（自动分页）
    const allUsers = await listAllRamUsers({
      accessKeyId,
      accessKeySecret,
      maxItems: 100
    });

    console.log('All users count:', allUsers.length);
    console.log('All users:', allUsers);

  } catch (error) {
    console.error('Error:', error);
  }
}
Output.info('开始获取RAM用户列表...')
const input = await Input.formAsync('请输入阿里云账号', [{
    type: 'text',
    key: 'accessKeyId',
    option: {
        label: 'AccessKeyId'
    },
}, {
    type: 'text',
    key: 'accessKeySecret',
    option: {
        label: 'AccessKeySecret'
    },
}])
await main(input.accessKeyId, input.accessKeySecret);