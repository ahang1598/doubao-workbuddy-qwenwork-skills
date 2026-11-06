/*
 * |-----------------------------------------------------------
 * | Copyright (c) 2026 huawei.com, Inc. All Rights Reserved
 * |-----------------------------------------------------------
 * | File: image_search.js
 * | Created: 2026-03-17
 * | Description: 图片搜索 Skill，搜索图片并返回结果
 * |-----------------------------------------------------------
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { getEnvConfig } = require('./env_loader');

// 加载环境变量配置
const envConfig = getEnvConfig();

// 桌面形态默认接入点：主进程 skill API 代理（命名管道，authority 段即管道名）
const DEFAULT_SERVICE_URL = 'np://claw-skill';

// 配置常量（从环境变量/ .xiaoyienv 获取）
const CONFIG = {
    SERVICE_URL: envConfig.SERVICE_URL || envConfig['SERVICE-URL'] || DEFAULT_SERVICE_URL,
    PERSONAL_UID: envConfig.PERSONAL_UID || envConfig['PERSONAL-UID'],
    PERSONAL_API_KEY: envConfig.PERSONAL_API_KEY || envConfig['PERSONAL-API-KEY'],
    CLAW_SKILL_TOKEN: envConfig.CLAW_SKILL_TOKEN || '',
};

// 调试日志配置：设置 IMAGE_SEARCH_DEBUG_LOG 环境变量为日志文件路径即可启用
// 例如: IMAGE_SEARCH_DEBUG_LOG=%TEMP%\image_search.log（Windows）或 /tmp/image_search.log（Linux）
const DEBUG_LOG_PATH = process.env.IMAGE_SEARCH_DEBUG_LOG || '';


/**
 * 将内容追加写入调试日志文件
 * @param {string} label - 日志标签（如 REQUEST / RESPONSE）
 * @param {object} data - 要记录的数据
 */
function debugLog(label, data) {
    if (!DEBUG_LOG_PATH) return;
    try {
        const timestamp = new Date().toISOString();
        const entry = `[${timestamp}] === ${label} ===\n${JSON.stringify(data, null, 2)}\n\n`;
        fs.appendFileSync(DEBUG_LOG_PATH, entry, 'utf8');
    } catch (err) {
        console.error(`写入调试日志失败: ${err.message}`);
    }
}

// 固定值
const FIXED_VALUES = {
    // SKILL_ID: 'xiaoyi_image_search', // 已废弃
    SKILL_ID: 'xiaoyi_doc_convert',
    REQUEST_FROM: 'openclaw',
    API_PATH: '/celia-claw/v1/rest-api/skill/execute',
    MCP_SERVER_NAME: 'browser-use',
    MCP_FUNCTION_NAME: 'image_search',
};

/** 是否为桌面管道形态（SERVICE_URL 为空 → 默认 np://；np:// 开头 → 管道；http(s):// 开头 → 旧沙箱直连） */
function isPipeMode() {
    return CONFIG.SERVICE_URL.toLowerCase().startsWith('np://');
}

/** np://claw-skill → \\.\pipe\claw-skill（authority 段即管道名） */
function pipePathFromUrl(url) {
    const name = url.slice(5).split('/')[0].trim();
    if (!name) throw new Error(`np:// URL 缺少管道名: ${url}`);
    return `\\\\.\\pipe\\${name}`;
}

/**
 * 生成唯一的HAG Trace ID
 * 优先使用 sessionId-interactionId-random 格式，未获取到时按原有逻辑生成
 * @returns {string} 唯一的trace id
 */
function generateHagTraceId() {
    const [sessionId, interactionId] = getSessionInfo();
    const random = Math.random().toString(36).substr(2, 9);

    // 如果获取到了 sessionId 和 interactionId，使用新格式
    if (sessionId && interactionId) {
        return `${sessionId}_${interactionId}_${random}`;
    }

    // 否则按原有逻辑生成
    const timestamp = Date.now().toString(36);
    return `hag-${timestamp}-${random}`;
}

/**
 * 获取 Session ID 和 Interaction ID。
 * 优先从文件读取，如果读取失败或字段缺失，则返回空值。
 *
 * @param {string} [filePath] - 配置文件路径，默认为 ~/.openclaw/.xiaoyiruntime
 * @returns {[string, string]} - [sessionId, interactionId]
 */
function getSessionInfo(filePath) {
    // 1. 确定文件路径
    if (!filePath) {
        filePath = path.join(os.homedir(), '.openclaw', '.xiaoyiruntime');
    }

    let sessionId = '';
    let interactionId = '';

    // 2. 尝试从文件读取
    if (fs.existsSync(filePath)) {
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const lines = content.split('\n');

            for (const line of lines) {
                const trimmedLine = line.trim();
                if (trimmedLine.startsWith('TASK_ID=')) {
                    // 截取等号后面的内容
                    const rawTaskId = trimmedLine.split('=', 2)[1];

                    // 根据 & 符号切分
                    const parts = rawTaskId.split('&');

                    // 获取第一部分 (Session ID)
                    if (parts.length > 0) {
                        sessionId = parts[0];
                    }

                    // 获取第二部分 (Interaction ID)
                    if (parts.length > 1) {
                        interactionId = parts[1];
                    }
                    break;
                }
            }
        } catch (error) {
            // 读取出错则忽略，返回空值
        }
    }

    // 如果文件不存在或读取失败，直接返回空值
    return [sessionId, interactionId];
}

/**
 * 发送图片搜索请求
 * @param {string} query - 搜索关键词
 * @param {number} numResults - 返回结果数量
 * @param {string} store - 图片存储方式
 * @returns {Promise<object>} 响应数据
 */
async function sendRequest(query, numResults, store) {
    const pipeMode = isPipeMode();

    // 验证必要的配置：管道形态仅需 CLAW_SKILL_TOKEN（业务鉴权主进程注入）；旧沙箱形态需 UID/API_KEY
    if (pipeMode) {
        if (!CONFIG.CLAW_SKILL_TOKEN) {
            throw new Error('缺少CLAW_SKILL_TOKEN配置，请设置环境变量CLAW_SKILL_TOKEN（桌面形态由主进程注入）');
        }
    } else {
        if (!CONFIG.SERVICE_URL) {
            throw new Error('缺少SERVICE_URL配置，请设置环境变量SERVICE_URL');
        }
        if (!CONFIG.PERSONAL_UID) {
            throw new Error('缺少PERSONAL_UID配置，请设置环境变量PERSONAL_UID');
        }
        if (!CONFIG.PERSONAL_API_KEY) {
            throw new Error('缺少PERSONAL_API_KEY配置，请设置环境变量PERSONAL_API_KEY');
        }
    }

    const sn = generateHagTraceId();

    // 构建请求体
    const body = {
        sn: sn,
        mcp_server_name: FIXED_VALUES.MCP_SERVER_NAME,
        mcp_function_name: FIXED_VALUES.MCP_FUNCTION_NAME,
        argument: {
            query: query,
            num_results: numResults,
            store: store,
            engines: ["baidu"],
        },
    };

    // 构建请求头（管道形态业务鉴权由主进程注入；x-hag-trace-id 每请求随机，不硬编码）
    const headers = {
        'Content-Type': 'application/json',
        'x-skill-id': FIXED_VALUES.SKILL_ID,
        'x-hag-trace-id': sn,
        'x-request-from': FIXED_VALUES.REQUEST_FROM,
    };
    if (pipeMode) {
        headers['Authorization'] = `Bearer ${CONFIG.CLAW_SKILL_TOKEN}`;
    } else {
        headers['x-uid'] = CONFIG.PERSONAL_UID;
        headers['x-api-key'] = CONFIG.PERSONAL_API_KEY;
    }

    // 记录请求日志
    debugLog('REQUEST', { url: pipeMode ? CONFIG.SERVICE_URL : (CONFIG.SERVICE_URL.replace(/\/$/, '') + FIXED_VALUES.API_PATH) });

    try {
        let response;
        if (pipeMode) {
            // 桌面形态：HTTP over 命名管道（axios socketPath），鉴权主进程注入
            response = await axios.post(`http://claw-skill${FIXED_VALUES.API_PATH}`, body, {
                socketPath: pipePathFromUrl(CONFIG.SERVICE_URL),
                headers,
                timeout: 120000, // 2分钟超时
                // 管道是本地通道：禁用 axios 对环境代理变量的拾取（防御）
                proxy: false,
            });
        } else {
            // 旧沙箱形态：直连云端
            const baseUrl = CONFIG.SERVICE_URL.replace(/\/$/, '');
            response = await axios.post(`${baseUrl}${FIXED_VALUES.API_PATH}`, body, {
                headers,
                timeout: 120000, // 2分钟超时
            });
        }

        // 记录响应日志
        debugLog('RESPONSE', { status: response.status, data: response.data });

        return response.data;
    } catch (error) {
        if (error.response) {
            debugLog('RESPONSE_ERROR', { status: error.response.status, data: error.response.data });
            console.error(`请求失败，状态码: ${error.response.status}`);
            console.error(`响应数据:`, error.response.data);
            throw new Error(`请求失败: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
        } else if (error.request) {
            debugLog('REQUEST_ERROR', { message: error.message });
            console.error(`请求发送但未收到响应: ${error.message}`);
            throw new Error(`网络请求失败: ${error.message}`);
        } else {
            debugLog('CONFIG_ERROR', { message: error.message });
            console.error(`请求配置错误: ${error.message}`);
            throw new Error(`请求配置错误: ${error.message}`);
        }
    }
}

/**
 * 搜索图片
 * @param {string} query - 搜索关键词
 * @param {number} [numResults=5] - 返回结果数量
 * @param {string} [store='osms'] - 图片存储方式
 * @returns {Promise<object[]>} 图片搜索结果列表
 */
async function searchImages(query, numResults = 5, store = 'osms') {
    console.error(`开始图片搜索: query="${query}", num_results=${numResults}, store=${store}`);

    const response = await sendRequest(query, numResults, store);
    
    // 检查响应状态
    if (!response || response.ret !== 0) {
        const errMsg = response ? `ret=${response.ret}` : '空响应';
        throw new Error(`图片搜索失败: ${errMsg}`);
    }

    // result 是 JSON 字符串，需要二次解析
    if (!response.result) {
        throw new Error('图片搜索返回空结果');
    }

    let images;
    try {
        images = JSON.parse(response.result);
    } catch (parseError) {
        console.error(`解析result字段失败: ${parseError.message}`);
        console.error(`原始result: ${response.result}`);
        throw new Error(`解析搜索结果失败: ${parseError.message}`);
    }

    if (!Array.isArray(images)) {
        throw new Error('搜索结果格式异常：期望数组');
    }

    console.error(`图片搜索完成，共获取 ${images.length} 条结果`);
    return images;
}

module.exports = {
    searchImages,
    sendRequest,
    generateHagTraceId,
    getSessionInfo,
    CONFIG,
    FIXED_VALUES,
};
