// ==================== get_device_info 子技能 ====================
// 功能：获取设备基础信息、设备在线状态、设备服务快照
import path from 'path';
import { fileURLToPath } from 'url';
import { hagSkillServicePost, hagSkillServicePostWithPathParams, saveDataToTxt, generateTraceId } from '../../utils/hag-connect/utils.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEVICE_INFO_DIR = path.join(__dirname, '../out_put/get_devices_info');
const DEVICE_INFO_TXT = path.join(DEVICE_INFO_DIR, 'devices_info.txt');

// ==================== 设备过滤配置 ====================
// 需要过滤的虚拟设备 prodId 列表
const VIRTUAL_PROD_IDS = ['ZG28', 'ZG29', '113X', '113Y', '113Z', '114A', '114B', '114C', 'Y200'];
// 需要过滤的 HiCar 设备 prodId 列表
const HICAR_PROD_IDS = ['2ABX', '2JTZ', '25EB', '2EWN'];
// 需要过滤的红外设备 prodId 列表
const INFRARED_PROD_IDS = ['21Z6', 'infrared'];
// 需要过滤的设备类型列表
const FILTERED_DEVICE_TYPES = ['051', 'A31', '06D', '06E'];

/**
 * 统一的设备过滤函数
 * @param {object} device - 转换后的设备对象
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {boolean} true-需要过滤(排除), false-保留
 */
function shouldFilterDevice(device, verbose) {
  if (!device) return true;

  const { prodId, deviceType, deviceName } = device;

  // 过滤虚拟设备
  if (VIRTUAL_PROD_IDS.includes(prodId)) {
    if (verbose) console.error(`[filter] 已过滤虚拟设备: ${deviceName} (prodId: ${prodId})`);
    return true;
  }

  // 过滤 HiCar 设备
  if (HICAR_PROD_IDS.includes(prodId)) {
    if (verbose) console.error(`[filter] 已过滤HiCar设备: ${deviceName} (prodId: ${prodId})`);
    return true;
  }

  // 过滤红外设备
  if (INFRARED_PROD_IDS.includes(prodId)) {
    if (verbose) console.error(`[filter] 已过滤红外设备: ${deviceName} (prodId: ${prodId})`);
    return true;
  }

  // 过滤指定设备类型
  if (FILTERED_DEVICE_TYPES.includes(deviceType)) {
    if (verbose) console.error(`[filter] 已过滤设备类型${deviceType}: ${deviceName}`);
    return true;
  }

  return false;
}

// ==================== 功能1：获取设备基础信息 ====================

/**
 * 获取设备基础信息 - 全量查询（使用 getCustomData API）
 */
async function fetchDevicesByCustomData(verbose) {
  const deviceResp = await hagSkillServicePost('getCustomData', {}, verbose);
  const rawData = deviceResp?.data;

  if (!rawData) {
    throw new Error('设备API返回了无效的数据结构');
  }

  const rawDevices = Array.isArray(rawData) ? rawData : (rawData.devices || []);
  const homes = rawData.homes;

  // 构建家庭字典
  const homeDict = {};
  if (homes && Array.isArray(homes)) {
    for (const home of homes) {
      homeDict[home.homeId] = home.homeName;
    }
  }

  return { rawDevices, homeDict };
}

/**
 * 获取设备基础信息 - 过滤查询（使用 getHouseDevicesV5 API）
 */
async function fetchDevicesByHouseV5(pathParams, verbose) {
  const deviceResp = await hagSkillServicePostWithPathParams('getHouseDevicesV5', pathParams, verbose);
  const rawDevices = Array.isArray(deviceResp?.data) ? deviceResp.data : [];

  // 构建家庭字典
  const homeDict = {};
  rawDevices.forEach(item => {
    if (item.homeId && item.homeName && !homeDict[item.homeId]) {
      homeDict[item.homeId] = item.homeName;
    }
  });

  return { rawDevices, homeDict };
}

/**
 * 转换设备数据 - 适配 getCustomData 响应格式
 */
function transformDeviceFromCustomData(item, homeDict, verbose) {
  const prodId = item.capabilityId || '';

  // 过滤子系统设备
  if (item.resourceType === 'subSystem') {
    if (verbose) console.error(`[filter] 已过滤子系统设备: ${item.devName}`);
    return null;
  }

  return {
    deviceId: item.devId || '',
    deviceName: item.devName || '',
    roomName: item.roomName || '未分类',
    homeId: item.homeId || '',
    homeName: homeDict[item.homeId] || '',
    deviceType: item.devType || '',
    productName: item.deviceTypeName || '',
    prodId: prodId
  };
}

/**
 * 转换设备数据 - 适配 getHouseDevicesV5 响应格式
 */
function transformDeviceFromHouseV5(item, homeDict, verbose) {
  const prodId = item.devInfo?.prodId || '';

  return {
    deviceId: item.devId || '',
    deviceName: item.devName || '',
    roomName: item.roomName || '未分类',
    homeId: item.homeId || '',
    homeName: item.homeName || homeDict[item.homeId] || '',
    deviceType: item.devInfo?.devType || '',
    deviceTypeName: item.devInfo?.deviceName || '',
    prodId: prodId,
    deviceAliasNames: item.deviceAliasNames || [],
    roomAliasNames: item.roomAliasNames || []
  };
}

/**
 * 获取设备基础信息（统一入口）
 * @param {object} params - 查询参数
 * @param {string} [params.deviceType] - 设备类型过滤（如 "01D"）
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} 设备列表
 */
export async function getDevicesInfo(params = {}, verbose = false) {
  const traceId = generateTraceId();
  process.stderr.write(`[trace-id] ${traceId}\n`);

  const { deviceType } = params;

  if (verbose) {
    console.error('[verbose] 开始获取设备基础信息');
    if (deviceType) console.error(`[verbose] 设备类型过滤: ${deviceType}`);
  }

  try {
    let rawDevices = [];
    let homeDict = {};

    // 根据是否有 deviceType 参数选择调用不同的 API
    // - getCustomData：全量查询
    // - getHouseDevicesV5：支持 deviceType 过滤
    if (deviceType) {
      // 使用 getHouseDevicesV5 接口（支持 deviceType 过滤）
      if (verbose) console.error('[verbose] 使用 getHouseDevicesV5 接口（deviceType过滤）');
      const result = await fetchDevicesByHouseV5({ deviceType }, verbose);
      rawDevices = result.rawDevices;
      homeDict = result.homeDict;
    } else {
      // 使用 getCustomData 接口（全量查询）
      if (verbose) console.error('[verbose] 使用 getCustomData 接口（全量查询）');
      const result = await fetchDevicesByCustomData(verbose);
      rawDevices = result.rawDevices;
      homeDict = result.homeDict;
    }

    if (!Array.isArray(rawDevices)) {
      throw new Error('设备数据不是数组格式');
    }

    if (verbose) console.error(`[verbose] 原始设备数量: ${rawDevices.length}`);

    // 根据是否有 deviceType 选择对应的转换函数
    const transformFn = deviceType
      ? transformDeviceFromHouseV5
      : transformDeviceFromCustomData;

    // 转换设备数据并过滤
    const deviceList = rawDevices
      .map((item, index) => {
        if (!item || typeof item !== 'object') {
          console.warn(`[warning] 设备数据索引${index}不是有效对象，跳过`);
          return null;
        }

        const transformed = transformFn(item, homeDict, verbose);
        if (!transformed) return null;

        // 使用统一过滤函数
        if (shouldFilterDevice(transformed, verbose)) {
          return null;
        }

        return transformed;
      })
      .filter(Boolean);

    if (!deviceType) { // 全量查询接口时缓存数据
      saveDataToTxt(DEVICE_INFO_TXT, deviceList, '设备信息');
    }

    if (verbose) console.error(`[verbose] 获取到 ${deviceList.length} 个设备`);

    return { traceId, totalDevices: deviceList.length, devices: deviceList };

  } catch (apiError) {
    console.error(`[error] 获取设备信息失败: ${apiError.message}`);
    throw apiError;
  }
}

// ==================== 功能2：获取设备在线状态 ====================

/**
 * 根据设备Id列表获取设备的在线状态
 * @param {string[]} deviceIds - 设备ID数组
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} 设备在线状态列表
 */
export async function getDevicesOnlineStatus(deviceIds = [], verbose = false) {
  const traceId = generateTraceId();
  process.stderr.write(`[trace-id] ${traceId}\n`);

  if (!Array.isArray(deviceIds) || deviceIds.length === 0) {
    throw new Error('设备ID列表不能为空');
  }

  if (verbose) {
    console.error('[verbose] 开始获取设备在线状态');
    console.error(`[verbose] 设备数量: ${deviceIds.length}`);
  }

  try {
    const response = await hagSkillServicePost('getDeviceStatus', deviceIds, verbose);

    const rawData = response?.data;
    if (!rawData || !Array.isArray(rawData)) {
      throw new Error('设备在线状态API返回了无效的数据结构');
    }

    const statusList = rawData.map(item => ({
      deviceId: item.devId || '',
      status: item.status || 'unknown',
      gatewayId: item.gatewayId || ''
    }));

    if (verbose) console.error(`[verbose] 获取到 ${statusList.length} 个设备状态`);

    return {
      traceId,
      totalDevices: statusList.length,
      statuses: statusList
    };
  } catch (apiError) {
    console.error(`[error] 获取设备在线状态失败: ${apiError.message}`);
    throw apiError;
  }
}

// ==================== 功能3：获取设备服务快照 ====================

/**
 * 获取设备的服务快照信息（包含在线状态和服务数据）
 * @param {string[]} deviceIds - 设备ID数组
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} 设备服务快照列表
 */
export async function getDeviceServiceSnapshot(deviceIds, verbose = false) {
  const traceId = generateTraceId();
  process.stderr.write(`[trace-id] ${traceId}\n`);

  if (!Array.isArray(deviceIds) || deviceIds.length === 0) {
    throw new Error('设备ID列表不能为空');
  }

  if (verbose) {
    console.error('[verbose] 开始获取设备服务快照');
    console.error(`[verbose] 设备数量: ${deviceIds.length}`);
  }

  try {
    const response = await hagSkillServicePost('getDevDynamicData', deviceIds, verbose);

    const rawData = response?.data;
    if (!rawData || !Array.isArray(rawData)) {
      throw new Error('设备服务快照API返回了无效的数据结构');
    }

    const snapshotList = rawData.map(item => ({
      deviceId: item.devId || '',
      status: item.status || 'offline',
      services: (item.services || []).map(s => ({
        serviceId: s.sid || '',
        serviceType: s.st || '',
        timestamp: s.ts || '',
        data: s.data || {}
      }))
    }));

    if (verbose) console.error(`[verbose] 获取到 ${snapshotList.length} 个设备服务快照`);

    return {
      traceId,
      totalDevices: snapshotList.length,
      snapshots: snapshotList
    };
  } catch (apiError) {
    console.error(`[error] 获取设备服务快照失败: ${apiError.message}`);
    throw apiError;
  }
}

// ==================== 功能4：获取设备标准profile服务快照 ====================

/**
 * 获取设备的服务快照信息（包含在线状态和服务数据）
 * @param {string[]} deviceIds - 设备ID数组
 * @param {boolean} verbose - 是否显示详细日志
 * @returns {Promise<object>} 设备服务快照列表
 */
export async function getDeviceServiceSnapshotCeliaClaw(deviceIds, verbose = false) {
  const traceId = generateTraceId();
  process.stderr.write(`[trace-id] ${traceId}\n`);

  if (!Array.isArray(deviceIds) || deviceIds.length === 0) {
    throw new Error('设备ID列表不能为空');
  }

  if (verbose) {
    console.error('[verbose] 开始获取设备服务快照');
    console.error(`[verbose] 设备数量: ${deviceIds.length}`);
  }

  try {
    // 并发请求所有设备的快照数据
    const rawData = await Promise.all(
        deviceIds.map(async deviceId => {
          try {
            // 构建请求体
            const body = {
              devId: deviceId,
            };

            // 调用单个设备快照接口
            const response = await hagSkillServicePostWithPathParams("getDevSnapshot", body, verbose);

            // 提取数据
            return response.data;
          } catch (error) {
            console.error(`获取设备 ${deviceId} 快照数据失败：`, error);
            return null;
          }
        })
    );
    if (!rawData || !Array.isArray(rawData)) {
      throw new Error('设备服务快照API返回了无效的数据结构');
    }

    const snapshotList = rawData.map(item => ({
      deviceId: item.devId || '',
      status: item.status || 'offline',
      services: (item.services || []).map(s => ({
        serviceId: s.sid || '',
        serviceType: s.st || '',
        timestamp: s.ts || '',
        data: s.data || {}
      }))
    }));

    if (verbose) console.error(`[verbose] 获取到 ${snapshotList.length} 个设备服务快照`);

    return {
      traceId,
      totalDevices: snapshotList.length,
      snapshots: snapshotList
    };
  } catch (apiError) {
    console.error(`[error] 获取设备服务快照失败: ${apiError.message}`);
    throw apiError;
  }
}
