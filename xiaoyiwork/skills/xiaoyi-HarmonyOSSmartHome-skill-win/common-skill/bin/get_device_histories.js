// ==================== get_device_histories 子技能 ====================
// 功能：查询设备历史记录
import path from 'path';
import {fileURLToPath} from 'url';
import {
    hagSkillServicePostWithPathParams,
    hagSkillServicePostBody,
    saveDataToTxt,
    generateTraceId
} from '../../utils/hag-connect/utils.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEVICE_HISTORIES_DIR = path.join(__dirname, '../out_put/get_device_histories');
const DEVICE_HISTORIES_TXT = path.join(DEVICE_HISTORIES_DIR, 'device_histories.txt');

/**
 * 格式化时间为 ISO 字符串（格式：YYYYMMDD'T'HHMMSS'Z'）
 * @param {number} timeMills - 毫秒时间戳
 * @returns {string} 格式化后的时间字符串
 */
function formatTimeToISO(timeMills) {
    const date = new Date(timeMills);
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');
    return `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
}

/**
 * 解析时间范围选项
 * @param {object} opts - 选项对象
 * @returns {object} 包含 startTime 和 endTime 的对象（ISO 格式字符串）
 */
function resolveTimeRange(opts) {
    const now = Date.now();
    const maxDays = 30;
    let startTime;
    let endTime = now;

    if (opts.lastMinutes) {
        const mins = parseInt(opts.lastMinutes, 10);
        if (isNaN(mins) || mins <= 0) {
            throw new Error('lastMinutes必须是大于0的整数');
        }
        startTime = now - mins * 60 * 1000;
    } else if (opts.lastDays) {
        const days = parseInt(opts.lastDays, 10);
        if (isNaN(days) || days <= 0) {
            throw new Error('lastDays必须是大于0的整数');
        }
        if (days > maxDays) {
            throw new Error(`lastDays不能超过${maxDays}天`);
        }
        startTime = now - days * 24 * 60 * 60 * 1000;
    } else if (opts.startTime && opts.endTime) {
        startTime = new Date(opts.startTime).getTime();
        endTime = new Date(opts.endTime).getTime();
        if (isNaN(startTime) || isNaN(endTime)) {
            throw new Error('startTime 和 endTime 必须是有效的时间字符串');
        }
    } else if (opts.date) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (opts.date === 'today') {
            startTime = today.getTime();
        } else if (opts.date === 'yesterday') {
            startTime = today.getTime() - 24 * 60 * 60 * 1000;
            endTime = today.getTime();
        }
    } else {
        // 默认查询最近1天
        startTime = now - 24 * 60 * 60 * 1000;
    }

    return {
        startTime: formatTimeToISO(startTime),
        endTime: formatTimeToISO(endTime)
    };
}

/**
 * 获取设备历史记录
 * @param {object} opts - 查询选项
 * @param {string} opts.devId - 设备ID（必填）
 * @param {string} opts.sid - 服务ID（必填，如 switch, brightness 等）
 * @param {number} [opts.lastDays] - 查询最近N天
 * @param {string} [opts.date] - 查询特定日期 'today' | 'yesterday'
 * @param {string} [opts.startTime] - 开始时间（ISO 字符串）
 * @param {string} [opts.endTime] - 结束时间（ISO 字符串）
 * @param {number} [opts.pageSize=100] - 每页大小，默认100
 * @param {boolean} [verbose=false] - 是否显示详细日志
 * @returns {Promise<object>} 查询结果
 */
export async function getDeviceHistories(opts = {}, verbose = false) {
    if (!opts || typeof opts !== 'object') {
        opts = {};
    }

    const traceId = generateTraceId();
    process.stderr.write(`[trace-id] ${traceId}\n`);

    try {
        // 验证必填参数
        const devId = opts.devId;
        const sid = opts.sid;

        if (!devId) {
            throw new Error('devId 是必填参数');
        }
        if (!sid) {
            throw new Error('sid 是必填参数（服务ID，如 eventData, event 等）');
        }

        const timeRange = resolveTimeRange(opts);
        const pageSize = opts.pageSize || 100;

        if (verbose) console.error(`[verbose] 查询时间范围：${timeRange.startTime} - ${timeRange.endTime}`);
        if (verbose) console.error('[verbose] 开始查询设备历史记录');

        const allHistories = [];
        let hasMore = true;
        let cursor = '';

        while (hasMore) {
            // 构建请求体
            const body = {
                type: 'getHistories',
                pathParams: {
                    sid: sid,
                    pageSize: String(pageSize),
                    startTime: timeRange.startTime,
                    endTime: timeRange.endTime,
                    cursor: cursor
                },
                urlParams: {
                    devId: devId
                }
            };

            if (verbose) console.error(`[verbose] 请求参数：${JSON.stringify(body)}`);

            // HAG 请求
            const resp = await hagSkillServicePostBody(body, verbose);

            // 解析响应
            const respData = resp?.data || {};
            const list = respData?.list || [];

            if (verbose) console.error(`[verbose] 本次获取 ${list.length} 条历史记录`);

            if (list.length > 0) {
                allHistories.push(...list);
            }

            // 判断是否还有更多数据
            hasMore = respData?.hasMore || false;
            cursor = respData?.cursor || '';

            if (verbose) console.error(`[verbose] hasMore: ${hasMore}, cursor: ${cursor}`);

            if (!hasMore || !cursor) {
                break;
            }
        }

        // 按时间戳降序排序
        allHistories.sort((a, b) => (b?.timeMills || 0) - (a?.timeMills || 0));

        // 限制返回记录数量，避免过大响应
        const maxRecords = 1000;
        let finalResult = allHistories;
        if (allHistories.length > maxRecords) {
            finalResult = allHistories.slice(0, maxRecords);
            console.warn(`[warning] 历史记录总数${allHistories.length}超过限制${maxRecords}，只返回前${maxRecords}条`);
        }

        if (verbose) console.error(`[verbose] 最终返回 ${finalResult.length} 条历史记录`);

        // 保存到文件
        saveDataToTxt(DEVICE_HISTORIES_TXT, finalResult, '设备历史记录');

        return {
            traceId,
            devId: devId,
            sid: sid,
            totalRecords: finalResult.length,
            timeRange: {
                startTime: timeRange.startTime,
                endTime: timeRange.endTime
            },
            histories: finalResult
        };

    } catch (error) {
        console.error(`[error] 获取设备历史记录失败: ${error.message}`);
        throw error;
    }
}
