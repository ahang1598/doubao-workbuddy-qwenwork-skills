// ==================== HAG 云侧技能服务连接模块 ====================
// 功能：提供云侧技能服务 API 访问能力（HTTPS 协议 + 认证）
import https from 'https';
import http from 'http';
import fs from 'fs';
import path from 'path';
import {randomUUID} from 'crypto';
import {getHagConfig} from './config.js';
import {pipeRequest, pipePathFromUrl} from './claw_pipe_http.js';

// ==================== 设备控制相关 ====================
/**
 * 生成 requestId（36 位 UUID）
 * @returns {string} requestId
 */
export function generateRequestId() {
    return randomUUID();
}

/**
 * 生成 ISO8601 格式时间戳（如：20260401T173429Z）
 * @returns {string} 时间戳字符串
 */
export function generateTimestamp() {
    const now = new Date();
    const year = now.getUTCFullYear();
    const month = String(now.getUTCMonth() + 1).padStart(2, '0');
    const day = String(now.getUTCDate()).padStart(2, '0');
    const hours = String(now.getUTCHours()).padStart(2, '0');
    const minutes = String(now.getUTCMinutes()).padStart(2, '0');
    const seconds = String(now.getUTCSeconds()).padStart(2, '0');
    return `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
}

// ==================== 环境变量加载 ====================

import {fileURLToPath} from 'url';
import {dirname, join} from 'path';

// 跨平台环境变量文件路径
const __dirname = dirname(fileURLToPath(import.meta.url));
const OPENCLAW_ENV_FILE = process.env.OPENCLAW_ENV_FILE ||
    (process.platform === 'win32'
        ? join(process.env.USERPROFILE || '', '.openclaw', '.xiaoyienv')
        : '/home/sandbox/.openclaw/.xiaoyienv');

// ==================== 商城配置加载 ====================
const MALL_CONFIG_PATH = path.join(__dirname, '.mallconfig');

/**
 * 获取商城服务URL（从配置文件读取）
 * @returns {string} 商城服务URL
 */
function getMallServiceUrl() {
    const content = fs.readFileSync(MALL_CONFIG_PATH, 'utf-8');
    const line = content.split('\n').find(l => l.trim().startsWith('MALL_SERVICE_URL='));
    return line.split('=')[1].trim();
}

/**
 * 加载环境变量文件
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {object} 环境变量对象
 */
function loadOpenclawEnv(verbose = false) {
    const env = {};
    try {
        const content = fs.readFileSync(OPENCLAW_ENV_FILE, 'utf-8');
        for (const line of content.split('\n')) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) continue;
            const idx = trimmed.indexOf('=');
            if (idx === -1) continue;
            const key = trimmed.slice(0, idx).trim();
            const value = trimmed.slice(idx + 1).trim();
            env[key] = value;
        }
        if (verbose) {
            console.error(`[verbose] Loaded env from .xiaoyienv`);
        }
    } catch (err) {
        const code = err.code;
        if (code === 'ENOENT') {
            if (verbose) console.error(`[verbose] .xiaoyienv not found, falling back to process.env`);
        } else if (code === 'EACCES') {
            console.error(`Error: Permission denied reading .xiaoyienv`);
            console.error(` Try: chmod 644 .xiaoyienv`);
        } else {
            console.error(`Error: Failed to read .xiaoyienv: ${err.message}`);
        }
    }
    return env;
}

/**
 * 获取 HAG 配置（优先从环境变量加载）
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {object} HAG 配置
 */
export function getHagConfigFromEnv(verbose = false) {
    const fileEnv = loadOpenclawEnv(verbose);

    // 优先从文件加载，其次从 process.env 加载；两者均缺/为空时兜底桌面管道形态默认代理
    const rawServiceUrl = (fileEnv.SERVICE_URL ?? process.env.SERVICE_URL)?.trim();
    const serviceUrl = rawServiceUrl || 'np://claw-skill';
    const uid = fileEnv['PERSONAL-UID'] ?? fileEnv.PERSONAL_UID ?? process.env.PERSONAL_UID;
    const apiKey = fileEnv['PERSONAL-API-KEY'] ?? fileEnv.PERSONAL_API_KEY ?? process.env.PERSONAL_API_KEY;

    if (verbose) {
        console.error(`[verbose] SERVICE_URL exists: ${!!serviceUrl}`);
        console.error(`[verbose] PERSONAL-UID exists: ${!!uid}`);
        console.error(`[verbose] PERSONAL-API-KEY exists: ${!!apiKey}`);
    }

    // 如果环境变量中有配置，则使用；否则使用默认配置
    const defaultConfig = getHagConfig();

    // 桌面管道形态：SERVICE_URL 为 np:// 前缀（np://claw-skill），业务鉴权由主进程注入
    const isPipe = !!(serviceUrl && serviceUrl.toLowerCase().startsWith('np://'));

    // 拼接完整 URL：如果 SERVICE_URL 已包含路径则直接使用，否则拼接 apiPath
    let baseUrl;
    if (serviceUrl) {
        // 检查 SERVICE_URL 是否已包含完整路径
        baseUrl = serviceUrl.includes('/celia-claw/') ? serviceUrl : serviceUrl + defaultConfig.apiPath;
    } else if (isPipe) {
        baseUrl = serviceUrl + defaultConfig.apiPath;
    } else {
        baseUrl = defaultConfig.serviceUrl + defaultConfig.apiPath;
    }

    if (verbose) {
        console.error(`[verbose] API URL configured: ${!!baseUrl}`);
    }

    const config = {
        baseUrl: baseUrl,
        uid: uid,
        apiKey: apiKey,
        huid: uid,
        skillId: defaultConfig.skillId,
        requestFrom: defaultConfig.requestFrom,
        isPipe: isPipe
    };

    return config;
}

// ==================== 工具函数 ====================
/**
 * 生成唯一 trace ID
 * @returns {string} trace ID
 */
export function generateTraceId() {
    return randomUUID();
}

/**
 * 确保目录存在
 * @param {string} dirPath - 目录路径
 */
export function ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, {recursive: true});
    }
}

/**
 * 保存数据到文本文件
 * @param {string} filePath - 文件路径
 * @param {any} data - 数据
 * @param {string} desc - 描述
 */
export function saveDataToTxt(filePath, data, desc) {
    ensureDir(path.dirname(filePath));
    const content = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    fs.writeFileSync(filePath, content, 'utf-8');
    console.error(`[info] ${desc} 已完整保存至：${filePath}`);
}

/**
 * 构建请求头
 * @param {object} config - HAG 配置
 * @param {string} traceId - 追踪 ID
 * @param {number} contentLength - 内容长度
 * @returns {object} 请求头对象
 */
function buildHeaders(config, traceId, contentLength) {
    const headers = {
        'x-skill-id': config.skillId,
        'x-hag-trace-id': traceId,
        'Content-Type': 'application/json',
        'Content-Length': contentLength
    };
    // 桌面（管道）形态：业务鉴权由主进程注入，skill 侧不携带
    if (!config.isPipe) {
        headers['x-request-from'] = config.requestFrom;
        headers['x-uid'] = config.uid;
        headers['x-api-key'] = config.apiKey;
        headers['x-huid'] = config.uid;
    }
    return headers;
}

function buildMallHeaders(contentLength) {
    return {
        'Content-Type': 'application/json',
        'Content-Length': contentLength
    };
}

/**
 * 发起 HTTPS 请求
 * @param {string} baseUrl - 基础 URL
 * @param {object} headers - 请求头
 * @param {string} postData - 请求数据
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} API 响应
 */
function makeHttpsRequest(baseUrl, headers, postData, verbose = false) {
    // 桌面（管道）形态：np:// 前缀 → 经主进程命名管道转发（业务鉴权代理注入）
    if (baseUrl.toLowerCase().startsWith('np://')) {
        try {
            const pipePath = pipePathFromUrl(baseUrl);
            const requestPath = baseUrl.replace(/^np:\/\/[^/]*/, '').replace(/^\//, '/');
            const token = process.env.CLAW_SKILL_TOKEN || '';
            const resp = pipeRequest('POST', requestPath, {
                body: postData,
                headers: headers,
                pipePath: pipePath,
                token: token
            });
            if (verbose) {
                console.error(`[verbose] Pipe HTTP Status: ${resp.status}`);
                console.error(`[verbose] Raw Response: ${resp.text}`);
            }
            try {
                return Promise.resolve(JSON.parse(resp.text));
            } catch (e) {
                return Promise.resolve(resp.text);
            }
        } catch (err) {
            return Promise.reject(err);
        }
    }
    return new Promise((resolve, reject) => {
        const url = new URL(baseUrl);
        const isHttps = url.protocol === 'https:';
        const httpModule = isHttps ? https : http;
        const defaultPort = isHttps ? 443 : 80;

        const req = httpModule.request(
            {
                hostname: url.hostname,
                port: url.port || defaultPort,
                path: url.pathname,
                method: 'POST',
                headers: headers,
            },
            (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    if (verbose) {
                        console.error(`[verbose] HTTP Status: ${res.statusCode}`);
                        console.error(`[verbose] Raw Response: ${data}`);
                    }
                    try {
                        const response = JSON.parse(data);
                        if (verbose) {
                            console.error(`[verbose] Parsed Response:`, JSON.stringify(response, null, 2));
                        }
                        resolve(response);
                    } catch (e) {
                        resolve(data);
                    }
                });
            }
        );

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

/**
 * 调用云侧技能服务 API
 * @param {string} commandType - 命令类型（如 getHouses）
 * @param {object} payload - 请求载荷
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} API 响应
 */
export async function hagSkillServicePost(commandType, payload = {}, verbose = false) {
    const config = getHagConfigFromEnv(verbose);
    const traceId = generateTraceId();

    const postData = JSON.stringify({
        type: commandType,
        payload: JSON.stringify(payload)
    });

    const headers = buildHeaders(config, traceId, Buffer.byteLength(postData));
    return makeHttpsRequest(config.baseUrl, headers, postData, verbose);
}

// ==================== 数据脱敏常量 ====================
const SENSITIVE_REPLACE_STAR = '*';
const SENSITIVE_REPLACE_MAX_STAR = '**********';
const SENSITIVE_LENGTH_THREE = 3;
const SENSITIVE_LENGTH_FIVE = 5;
const SENSITIVE_LENGTH_TEN = 10;
const PHONE_COMMON_LEN = 11;
const SENSITIVE_LENGTH_EIGHTEEN = 18;
const SENSITIVE_START_INDEX_ONE = 1;
const SENSITIVE_START_INDEX_TWO = 2;
const SENSITIVE_START_INDEX_FOUR = 4;
const PHONE_START_INDEX = 3;
const PHONE_END_COUNT = 4;
const SENSITIVE_START_INDEX_SIX = 6;
const SENSITIVE_START_INDEX_NINE = 9;

/**
 * 根据起止位置生成脱敏字符串
 * @param {string} data - 待处理数据
 * @param {number} startIndex - 保留前缀长度
 * @param {number} endCount - 保留后缀长度（0表示不保留后缀）
 * @returns {string} 脱敏结果
 */
function fuzzy(data, startIndex, endCount) {
    if (!data) return SENSITIVE_REPLACE_STAR;
    const len = data.length;
    if (len <= startIndex) {
        return SENSITIVE_REPLACE_STAR.repeat(len);
    }
    const prefix = data.substring(0, startIndex);
    const suffix = endCount > 0 ? data.substring(len - endCount) : '';
    const middleLen = len - startIndex - (endCount > 0 ? endCount : 0);
    const middle = SENSITIVE_REPLACE_STAR.repeat(middleLen > 0 ? middleLen : 1);
    return prefix + middle + suffix;
}

/**
 * ID类字符串匿名化
 * 匿名化原则，数据长度x按如下方式处理：
 * x是1位，则全掩码；
 * x是2-3位，保留前1位，其余的掩码；
 * x是4-5位，保留前2位，其余的掩码；
 * x是6-10位，则保留前4个位，其余的掩码；
 * x是11位，保留前三位和后四位，中间的掩码；
 * x是12-18位，保留前6位，其余的掩码；
 * x大于18位，保留前9位，其余的掩码；
 * 应用在 UserID、OwnerID、昵称、手机号、身份证、邮箱等
 * @param {string} data - 待处理数据
 * @returns {string} 脱敏结果
 */
function fuzzyData(data) {
    if (!data) return '';
    const len = data.length;
    if (len < 1) {
        return SENSITIVE_REPLACE_STAR;
    }
    if (len <= SENSITIVE_LENGTH_THREE) {
        return fuzzy(data, SENSITIVE_START_INDEX_ONE, 0);
    } else if (len <= SENSITIVE_LENGTH_FIVE) {
        return fuzzy(data, SENSITIVE_START_INDEX_TWO, 0);
    } else if (len <= SENSITIVE_LENGTH_TEN) {
        return fuzzy(data, SENSITIVE_START_INDEX_FOUR, 0);
    } else if (len <= PHONE_COMMON_LEN) {
        return fuzzy(data, PHONE_START_INDEX, PHONE_END_COUNT);
    } else if (len <= SENSITIVE_LENGTH_EIGHTEEN) {
        return fuzzy(data, SENSITIVE_START_INDEX_SIX, 0);
    } else {
        return data.substring(0, SENSITIVE_START_INDEX_NINE) + SENSITIVE_REPLACE_MAX_STAR;
    }
}

/**
 * 敏感数据脱敏
 * @param {string} val - 待脱敏数据
 * @returns {string} 脱敏结果
 */
export function maskSecret(val) {
    return fuzzyData(val);
}

/**
 * 调用云侧技能服务 API（仅支持 type 和 urlParams 参数）
 * @param {string} type - 命令类型（如 getHouses）
 * @param {object} urlParams - URL 参数
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} API 响应
 */
export async function hagSkillServicePostWithUrlParams(type, urlParams = {}, verbose = false) {
    const config = getHagConfigFromEnv(verbose);
    const traceId = generateTraceId();

    const postData = JSON.stringify({
        type: type,
        urlParams: urlParams
    });

    const headers = buildHeaders(config, traceId, Buffer.byteLength(postData));
    return makeHttpsRequest(config.baseUrl, headers, postData, verbose);
}

/**
 * 调用云侧技能服务 API（仅支持 type 和 pathParams 参数）
 * @param {string} type - 命令类型（如 getHouses）
 * @param {object} pathParams - 路径参数
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} API 响应
 */
export async function hagSkillServicePostWithPathParams(type, pathParams = {}, verbose = false) {
    const config = getHagConfigFromEnv(verbose);
    const traceId = generateTraceId();

    const postData = JSON.stringify({
        type: type,
        pathParams: pathParams
    });

    const headers = buildHeaders(config, traceId, Buffer.byteLength(postData));
    return makeHttpsRequest(config.baseUrl, headers, postData, verbose);
}

export async function hagSkillServicePostBody(body = {}, verbose = false) {
    const config = getHagConfigFromEnv(verbose);
    const traceId = generateTraceId();
    const headers = buildHeaders(config, traceId, Buffer.byteLength(JSON.stringify(body)));
    return makeHttpsRequest(config.baseUrl, headers, JSON.stringify(body), verbose);
}

/**
 * 调用智慧生活商城 API（支持自定义 API 路径）
 * @param {string} apiPath - API 路径（如 /smart-life/v4/mall/search）
 * @param {object} body - 请求体
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} API 响应
 */
export async function hagSkillServicePostMall(apiPath, body = {}, verbose = false) {
    const serviceUrl = getMallServiceUrl();
    const baseUrl = serviceUrl + apiPath;

    if (verbose) {
        console.error(`[verbose] 商城 API URL = ${!!baseUrl}`);
    }

    const headers = buildMallHeaders(Buffer.byteLength(JSON.stringify(body)));

    return makeHttpsRequest(baseUrl, headers, JSON.stringify(body), verbose);
}

/**
 * 获取默认配置
 * @returns {object} 默认配置
 */
export function getDefaultConfig() {
    return getHagConfig();
}

export function getDefaultTimeRange() {
    const now = Date.now();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterdayStart = today.getTime() - 24 * 60 * 60 * 1000;
    return {startTime: yesterdayStart, endTime: now};
}

/**
 * HAG 设备控制通用方法（支持 GET/POST）
 * @param {object} params - 控制参数
 * @param {string} params.devId - 设备 ID
 * @param {string} params.prodId - 产品 ID
 * @param {string} params.sid - 服务 ID（如：switch, brightness, colour 或路由器路径）
 * @param {string} params.operation - 操作类型（GET/POST）
 * @param {object} [params.data] - 控制数据（POST 时需要，如：{on: "1"}, {brightness: 50}）
 * @param {string} [params.mode] - 模式（默认：NOACK，路由器用 ACK）
 * @param {string} [params.requestId] - 请求 ID（默认自动生成）
 * @param {string} [params.timestamp] - 时间戳（默认自动生成）
 * @param {boolean} [verbose] - 是否显示详细日志
 * @returns {Promise<object>} API 响应
 */
export async function hagControl(params, verbose = false) {
    const {devId, prodId, sid, operation, data, mode = 'NOACK', requestId, timestamp} = params;

    if (!devId) {
        throw new Error('hagControl: devId 不能为空');
    }
    if (!prodId) {
        throw new Error('hagControl: prodId 不能为空');
    }
    if (!sid) {
        throw new Error('hagControl: sid 不能为空');
    }
    if (!operation) {
        throw new Error('hagControl: operation 不能为空 (GET/POST)');
    }
    if (operation === 'POST' && (data === undefined || data === null)) {
        throw new Error('hagControl: POST 操作需要 data 参数');
    }

    const finalRequestId = requestId || generateRequestId();
    const finalTimestamp = timestamp || generateTimestamp();

    // 构建 payload 对象
    const payloadObj = {
        mode: mode,
        requestId: finalRequestId,
        timestamp: finalTimestamp,
        devId: devId,
        prodId: prodId,
        operation: operation,
        sid: sid
    };

    // POST 操作时添加 data 字段
    if (operation === 'POST' && data !== undefined) {
        payloadObj.data = data;
    }

    if (verbose) {
        console.error('[verbose] hagControl 请求参数:', JSON.stringify(params, null, 2));
        console.error('[verbose] hagControl payload 对象:', JSON.stringify(payloadObj, null, 2));
    }

    // 调用 hagSkillServicePost，type 为 hagControl
    const response = await hagSkillServicePost('hagControl', payloadObj, verbose);

    if (verbose) {
        console.error('[verbose] hagControl 响应:', JSON.stringify(response, null, 2));
    }

    return response;
}
