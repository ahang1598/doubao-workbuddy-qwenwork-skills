// ==================== get_control_records 子技能 ====================
// 功能：获取设备控制记录（概要 + 详情）
import path from 'path';
import {fileURLToPath} from 'url';
import {
    hagSkillServicePost,
    saveDataToTxt,
    generateTraceId,
    getDefaultTimeRange
} from '../../utils/hag-connect/utils.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONTROL_RECORD_DIR = path.join(__dirname, '../out_put/get_control_records');
const CONTROL_BRIEF_TXT = path.join(CONTROL_RECORD_DIR, 'control_brief.txt');
const CONTROL_DETAIL_TXT = path.join(CONTROL_RECORD_DIR, 'control_detail.txt');

function getTimeRange(lastDay = '1') {
    const now = Date.now();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterdayStart = today.getTime() - 24 * 60 * 60 * 1000 * parseInt(lastDay, 10);
    return {startTime: yesterdayStart, endTime: now};
}

/**
 * 获取设备控制记录
 */
export async function getControlRecords(opts = {}, verbose = false) {
    const homeId = opts.homeId;

    const traceId = generateTraceId();
    process.stderr.write(`[trace-id] ${traceId}\n`);

    if (verbose) console.error(`[verbose] 开始获取家庭 ${homeId} 的控制记录`);

    const {startTime, endTime} = getTimeRange(opts.lastDays || '1');

    // 验证时间范围
    if (!startTime || !endTime || startTime >= endTime) {
        throw new Error('无效的时间范围配置');
    }

    // ==================== 第一步：查询控制记录概要 ====================
    const briefPayload = {
        homeId: homeId,
        startTime: startTime,
        endTime: endTime
    };

    if (verbose) {
        console.error('[verbose] 查询控制记录概要');
        console.error(`[verbose] 概要请求 payload: ${JSON.stringify(briefPayload)}`);
    }

    const briefResp = await hagSkillServicePost('queryBriefCtrlRecord', briefPayload, verbose);

    // 解析响应（hag 返回格式：{"errorCode":"0","errorMsg":"success","data":{"data":[...]}}）
    const briefData = briefResp.data;
    const briefList = briefData.data || [];
    saveDataToTxt(CONTROL_BRIEF_TXT, briefResp, '控制记录概要');

    if (verbose) console.error(`[verbose] 概要记录总数：${briefList.length}`);

    // ==================== 第二步：查询控制记录详情 ====================
    const detailResults = [];
    const batchSize = 50;

    if (briefList.length > 0) {
        if (verbose) console.error(`[verbose] 开始分片查询详情，批次大小：${batchSize}`);

        for (let i = 0; i < briefList.length; i += batchSize) {
            const batch = briefList.slice(i, i + batchSize);
            if (verbose) {
                console.error(`[verbose] 查询详情批次 ${Math.floor(i / batchSize) + 1}，条数：${batch.length}`);
                console.error(`[verbose] 详情请求 payload: ${JSON.stringify({request: batch})}`);
            }

            const detailPayload = {
                request: batch
            };

            try {
                const detailResp = await hagSkillServicePost('queryCtrlRecord', detailPayload, verbose);
                const records = detailResp.data.data || [];
                const filter = records.filter(record=>record.functionName)||[];
                detailResults.push(filter);
            } catch (batchError) {
                console.error(`[error] 批次 ${Math.floor(i / batchSize) + 1} 查询失败: ${batchError.message}`);
                // 继续处理其他批次而不是中断整个流程
                continue;
            }
        }

        saveDataToTxt(CONTROL_DETAIL_TXT, detailResults, '控制记录详情');
    }

    const totalDetailCount = detailResults.reduce((sum, r) => {
        return sum + (r?.length || 0);
    }, 0);

    if (verbose) console.error(`[verbose] 详情记录总数：${totalDetailCount}`);

    return {
        traceId,
        homeId,
        timeRange: {startTime, endTime},
        briefCount: briefList.length,
        detailCount: totalDetailCount,
        briefList,
        detailList: detailResults
    };
}
