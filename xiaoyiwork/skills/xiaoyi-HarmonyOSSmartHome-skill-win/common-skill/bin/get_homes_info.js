// ==================== get_homes_info 子技能 ====================
// 功能：获取家庭信息（HAG 云侧技能服务 API）
import path from 'path';
import {fileURLToPath} from 'url';
import {
    hagSkillServicePost,
    saveDataToTxt,
    generateTraceId,
    getHagConfigFromEnv
} from '../../utils/hag-connect/utils.js';
import {getHagConfig} from "../../utils/hag-connect/config.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HOME_INFO_DIR = path.join(__dirname, '../out_put/get_homes_info');
const HOME_INFO_TXT = path.join(HOME_INFO_DIR, 'homes_info.txt');

/**
 * 获取家庭信息
 * @param {boolean} verbose - 是否显示详细日志
 * @throws {Error} 当API调用失败或数据解析出错时抛出异常
 */
export async function getHomesInfo(verbose = false) {
    const traceId = generateTraceId();
    process.stderr.write(`[trace-id] ${traceId}\n`);

    if (verbose) console.error('[verbose] 开始获取家庭信息');

    try {
        // 调用 HAG 云侧技能服务 API（使用 UID + API_KEY 鉴权）
        const response = await hagSkillServicePost('getHouses', {}, verbose);

        // 验证响应数据基本结构
        if (!response) {
            throw new Error('API响应为空对象');
        }

        // 解析响应数据
        let rawHomes = [];

        if (response.data) {
            if (Array.isArray(response.data)) {
                rawHomes = response.data;
            }
        }

        // 确保rawHomes是数组
        if (!Array.isArray(rawHomes)) {
            throw new Error('解析到的家庭数据不是数组格式');
        }
        // 处理家庭列表，验证每个家庭数据
        const homeList = rawHomes.map((item, index) => {
            // 验证每个家庭对象的基本结构
            if (!item || typeof item !== 'object') {
                console.warn(`[warning] 家庭数据索引${index}不是有效对象，跳过`);
                return null;
            }
            if (item.role === 'family' && item.memberType !== '1') {
                return null;
            }
            return {
                homeId: item.homeId || item.id || '',
                homeName: item.homeName || item.name || '未命名家庭',
                name: item.name || '',  // 保留原始 name 字段（HAG API 返回）
                role: item.role || '成员',
                extendRole: item.extendRole || '',
                memberType: item.memberType || ''
            };
        }).filter(Boolean); // 过滤掉无效的家庭数据

        saveDataToTxt(HOME_INFO_TXT, homeList, '家庭信息');

        if (verbose) console.error(`[verbose] 获取到 ${homeList.length} 个家庭`);

        return {traceId, totalHomes: homeList.length, homes: homeList};

    } catch (apiError) {
        console.error(`[error] 获取家庭信息失败: ${apiError.message}`);
        throw apiError;
    }
}
