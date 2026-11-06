#!/usr/bin/env node

/**
 * 宠物数据采集模块
 * 批量获取宠物设备的服务快照
 *
 * 功能：
 * - 获取猫砂盆设备服务快照（使用次数、最后使用时间）
 * - 获取喂食器设备服务快照（出粮次数、最后出粮时间）
 * - 获取温湿度传感器数据
 * - 获取空调温度传感器数据
 * - 获取摄像头/定位设备状态
 *
 * 使用方法：
 * node pet-data-collector.js --device-ids "id1,id2,id3"
 */

import { getDeviceServiceSnapshot } from '../../../common-skill/bin/get_devices_info.js';
import { recognizePetDevices } from './pet-device-recognizer.js';

// ==================== 数据字段定义 ====================

/**
 * 猫砂盆服务数据字段映射
 * 不同品牌的字段名可能不同，尝试多个可能的字段名
 */
const CAT_LITTER_FIELDS = {
  // 实际API返回: serviceId="data", data={"excretedCount": 0, "cleanCount": 0, "interceptCount": 0}
  // cleanCount=自动清理次数, excretedCount=排泄次数(使用次数)
  useCount: ['useCount', 'use_count', 'usageCount', 'usage_count', 'usedCount', 'used_count', 'count', 'totalUse', 'excretedCount', 'cleanCount', 'interceptCount'],
  lastUseTime: ['lastUseTime', 'last_use_time', 'lastUse', 'last_use', 'lastTime', 'last_time', 'timestamp']
};

/**
 * 喂食器服务数据字段映射
 */
const FEEDER_FIELDS = {
  // 实际API返回: serviceId="food1"/"food2", data={"Hopper01": 2} — 粮仓余量
  // serviceId="feederPortion", data={"FeederPortion01": 2, "FeederPortion02": 1} — 每次出粮量
  // 注意: 此API没有直接给出"今日出粮次数"，需通过"出粮"action记录或状态变化推算
  feedCount: ['feedCount', 'feed_count', 'feedTimes', 'feed_times', 'portionCount', 'totalFeed', 'todayFeed'],
  lastFeedTime: ['lastFeedTime', 'last_feed_time', 'lastFeed', 'last_feed', 'lastMealTime', 'last_meal_time'],
  portionSize: ['portionSize', 'portion_size', 'portion', 'singlePortion', 'feedAmount', 'amount', 'FeederPortion01', 'FeederPortion02']
};

/**
 * 温湿度传感器字段映射
 * 实际API返回: serviceId="temperature", data={"current": 248, "level": 3}  ← 248=24.8°C (×10)
 *              serviceId="humidity", data={"current": 100, "level": 4}     ← 湿度值
 */
const TEMP_HUMIDITY_FIELDS = {
  temperature: ['temperature', 'temp', 'currentTemp', 'indoorTemp', 'roomTemp', 'current'],
  humidity: ['humidity', 'hum', 'currentHumidity', 'indoorHumidity', 'roomHumidity', 'current']
};

/**
 * 从服务数据中提取字段值
 * @param {object} serviceData - 服务数据对象
 * @param {string[]} fieldNames - 可能的字段名数组
 * @returns {*} 字段值或null
 */
function extractFieldValue(serviceData, fieldNames) {
  for (const fieldName of fieldNames) {
    if (serviceData[fieldName] !== undefined && serviceData[fieldName] !== null) {
      return serviceData[fieldName];
    }
  }
  return null;
}

/**
 * 归一化温度值
 * 鸿蒙API返回的温度可能为整数*10（如248=24.8°C），也可能直接是浮点数
 * @param {number|null} rawValue - 原始温度值
 * @returns {number|null} 归一化后的摄氏温度
 */
function normalizeTemperature(rawValue) {
  if (rawValue === null || rawValue === undefined) return null;
  // 如果数值 > 100，大概率是 ×10 格式（如248=24.8°C）
  // 如果数值在合理温度范围内（-10~50），直接使用
  if (rawValue > 100 || rawValue < -100) {
    return parseFloat((rawValue / 10).toFixed(1));
  }
  return rawValue;
}

/**
 * 归一化湿度值
 * @param {number|null} rawValue - 原始湿度值
 * @returns {number|null} 归一化后的湿度百分比
 */
function normalizeHumidity(rawValue) {
  if (rawValue === null || rawValue === undefined) return null;
  // 如果 > 100，大概率是 ×10 格式
  if (rawValue > 100) {
    return parseFloat((rawValue / 10).toFixed(0));
  }
  return rawValue;
}

/**
 * @typedef {Object} CatLitterData
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {number|null} useCount - 今日使用次数
 * @property {string|null} lastUseTime - 最后使用时间
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} FeederData
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {number|null} feedCount - 今日出粮次数
 * @property {string|null} lastFeedTime - 最后出粮时间
 * @property {number|null} portionSize - 每次出粮量（克）
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} TemperatureData
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} source - 数据来源
 * @property {number|null} value - 温度值
 * @property {number|null} humidity - 湿度值
 * @property {boolean} isAbnormal - 是否异常（>26°C）
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} PetLocationData
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} location - 位置描述
 * @property {string} source - 数据来源
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} AirConditionerData
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {boolean} powerState - 电源状态
 * @property {number|null} currentTemp - 当前温度
 * @property {number|null} targetTemp - 目标温度
 * @property {string} mode - 运行模式
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} PetDeviceSnapshots
 * @property {CatLitterData[]} catLitter - 猫砂盆数据列表
 * @property {FeederData[]} feeder - 喂食器数据列表
 * @property {TemperatureData[]} temperature - 温度数据列表
 * @property {PetLocationData[]} petLocation - 宠物位置数据列表
 * @property {AirConditionerData[]} airConditioner - 空调数据列表
 */

/**
 * 解析猫砂盆服务数据
 * @param {object} snapshot - 设备服务快照
 * @param {object} deviceInfo - 设备基础信息
 * @returns {CatLitterData} 解析后的猫砂盆数据
 */
function parseCatLitterData(snapshot, deviceInfo) {
  const result = {
    deviceId: snapshot.deviceId || deviceInfo?.deviceId || '',
    deviceName: deviceInfo?.deviceName || '猫砂盆',
    roomName: deviceInfo?.roomName || '未分类',
    useCount: null,
    lastUseTime: null,
    online: snapshot.status === 'online'
  };

  // 遍历服务列表查找猫砂盆相关服务
  for (const service of snapshot.services || []) {
    const serviceData = service.data || {};
    const serviceId = (service.serviceId || '').toLowerCase();

    // 检查是否是猫砂盆相关的服务
    // 实际API: 猫砂盆数据在 serviceId="data" 中, 字段为 excretedCount(排泄=使用次数)
    if (serviceId === 'data' || serviceId.includes('litter') || serviceId.includes('cat') || serviceId.includes('使用')) {
      result.useCount = extractFieldValue(serviceData, CAT_LITTER_FIELDS.useCount);
      result.lastUseTime = extractFieldValue(serviceData, CAT_LITTER_FIELDS.lastUseTime);
      // 如果有 useCount 就 break，否则继续遍历找更好的匹配
      if (result.useCount !== null) break;
    }
  }

  return result;
}

/**
 * 解析喂食器服务数据
 * @param {object} snapshot - 设备服务快照
 * @param {object} deviceInfo - 设备基础信息
 * @returns {FeederData} 解析后的喂食器数据
 */
function parseFeederData(snapshot, deviceInfo) {
  const result = {
    deviceId: snapshot.deviceId || deviceInfo?.deviceId || '',
    deviceName: deviceInfo?.deviceName || '喂食器',
    roomName: deviceInfo?.roomName || '未分类',
    feedCount: null,
    lastFeedTime: null,
    portionSize: null,
    online: snapshot.status === 'online'
  };

  // 遍历服务列表查找喂食器相关服务
  for (const service of snapshot.services || []) {
    const serviceData = service.data || {};
    const serviceId = (service.serviceId || '').toLowerCase();

    // 检查是否是喂食器相关的服务
    if (serviceId.includes('feed') || serviceId.includes('food') || serviceId.includes('粮') || serviceId === 'feederportion') {
      result.feedCount = extractFieldValue(serviceData, FEEDER_FIELDS.feedCount);
      result.lastFeedTime = extractFieldValue(serviceData, FEEDER_FIELDS.lastFeedTime);
      result.portionSize = extractFieldValue(serviceData, FEEDER_FIELDS.portionSize);
      // 如果找到了出粮量就 break，否则继续找
      if (result.portionSize !== null) break;
    }
  }

  return result;
}

/**
 * 解析温湿度传感器数据
 * @param {object} snapshot - 设备服务快照
 * @param {object} deviceInfo - 设备基础信息
 * @returns {TemperatureData} 解析后的温度数据
 */
function parseTemperatureData(snapshot, deviceInfo) {
  const result = {
    deviceId: snapshot.deviceId || deviceInfo?.deviceId || '',
    deviceName: deviceInfo?.deviceName || '温湿度传感器',
    source: '温湿度传感器',
    value: null,
    humidity: null,
    isAbnormal: false,
    online: snapshot.status === 'online'
  };

  // 遍历服务列表查找温湿度数据
  // 注意: 实际API服务有 temperature(温度数据), humidity(湿度数据), tempReportSetting(无关配置) 等
  // 要精确匹配真正的温湿度 service，不能一匹配就 break
  for (const service of snapshot.services || []) {
    const serviceData = service.data || {};
    const serviceId = (service.serviceId || '').toLowerCase();

    // 精确匹配: temperature 和 humidity 是实际数据源，其他含 temp/hum 的是配置服务
    const isTempService = serviceId === 'temperature';
    const isHumidityService = serviceId === 'humidity';

    if (isTempService) {
      const rawTemp = extractFieldValue(serviceData, TEMP_HUMIDITY_FIELDS.temperature);
      if (rawTemp !== null) {
        result.value = normalizeTemperature(rawTemp);
      }
    }

    if (isHumidityService) {
      const rawHumidity = extractFieldValue(serviceData, TEMP_HUMIDITY_FIELDS.humidity);
      if (rawHumidity !== null) {
        result.humidity = normalizeHumidity(rawHumidity);
      }
    }

    // 如果温度和湿度都有了就提前退出
    if (result.value !== null && result.humidity !== null) break;
  }

  // 判断温度是否异常
  if (result.value !== null && result.value > 26) {
    result.isAbnormal = true;
  }

  return result;
}

/**
 * 解析空调温度传感器数据
 * @param {object} snapshot - 设备服务快照
 * @param {object} deviceInfo - 设备基础信息
 * @returns {TemperatureData} 解析后的空调温度数据
 */
function parseAirConditionerTempData(snapshot, deviceInfo) {
  const result = {
    deviceId: snapshot.deviceId || deviceInfo?.deviceId || '',
    deviceName: deviceInfo?.deviceName || '空调',
    source: '空调温度传感器',
    value: null,
    humidity: null,
    isAbnormal: false,
    online: snapshot.status === 'online'
  };

  // 遍历服务列表查找空调温度数据
  for (const service of snapshot.services || []) {
    const serviceData = service.data || {};
    const serviceId = (service.serviceId || '').toLowerCase();

    // 空调通常有 temperature 或 indoor_temp 服务
    // 实际API: 空调 serviceId="temperature", data={"current": 28.1, "target": 230}
    // 注意: 空调的温度字段名可能是 current，且 target=230 需要归一化
    if (serviceId.includes('temperature') || serviceId.includes('temp') || serviceId.includes('温度')) {
      const rawTemp = extractFieldValue(serviceData, TEMP_HUMIDITY_FIELDS.temperature);
      result.value = normalizeTemperature(rawTemp);

      // 判断温度是否异常
      if (result.value !== null && result.value > 26) {
        result.isAbnormal = true;
      }
      break;
    }
  }

  return result;
}

/**
 * 解析宠物位置数据（从摄像头或定位设备）
 * @param {object} snapshot - 设备服务快照
 * @param {object} deviceInfo - 设备基础信息
 * @returns {PetLocationData} 解析后的宠物位置数据
 */
function parsePetLocationData(snapshot, deviceInfo) {
  const result = {
    deviceId: snapshot.deviceId || deviceInfo?.deviceId || '',
    deviceName: deviceInfo?.deviceName || '宠物摄像头',
    location: '未检测到宠物位置',
    source: deviceInfo?.category === 'petTracker' ? '宠物定位器' : '摄像头',
    online: snapshot.status === 'online'
  };

  // 遍历服务列表查找位置相关数据
  for (const service of snapshot.services || []) {
    const serviceData = service.data || {};
    const serviceId = (service.serviceId || '').toLowerCase();

    // 定位设备或摄像头
    if (serviceId.includes('location') || serviceId.includes('position') ||
        serviceId.includes('tracking') || serviceId.includes('位置') ||
        serviceId.includes('motion') || serviceId.includes('移动')) {

      // 尝试获取位置信息
      if (serviceData.location) {
        result.location = serviceData.location;
      } else if (serviceData.position) {
        result.location = serviceData.position;
      } else if (serviceData.roomName) {
        result.location = serviceData.roomName;
      } else if (serviceData.area) {
        result.location = serviceData.area;
      } else if (serviceData.detected) {
        result.location = '检测到宠物活动';
      }

      break;
    }
  }

  return result;
}

/**
 * 解析空调设备数据
 * @param {object} snapshot - 设备服务快照
 * @param {object} deviceInfo - 设备基础信息
 * @returns {AirConditionerData} 解析后的空调数据
 */
function parseAirConditionerData(snapshot, deviceInfo) {
  const result = {
    deviceId: snapshot.deviceId || deviceInfo?.deviceId || '',
    deviceName: deviceInfo?.deviceName || '空调',
    roomName: deviceInfo?.roomName || '未分类',
    powerState: false,
    currentTemp: null,
    targetTemp: null,
    mode: '',
    online: snapshot.status === 'online'
  };

  // 遍历服务列表查找空调数据
  for (const service of snapshot.services || []) {
    const serviceData = service.data || {};
    const serviceId = (service.serviceId || '').toLowerCase();

    // 实际API: 空调各数据分布在不同的serviceId中
    //   switch(电源) → data={"on": 0}
    //   temperature(温度) → data={"current": 28.1, "target": 230}
    //   mode(模式) → data={"mode": 3}
    //   fan(风速) → data={"gear": 0, "direction": 1}
    if (serviceId === 'switch') {
      // 电源状态
      if (serviceData.on !== undefined) {
        result.powerState = serviceData.on === 1 || serviceData.on === true;
      }
    } else if (serviceId === 'temperature') {
      // 温度
      const rawCurrent = extractFieldValue(serviceData, ['current', 'indoorTemp', 'temperature']);
      result.currentTemp = normalizeTemperature(rawCurrent);

      const rawTarget = extractFieldValue(serviceData, ['target', 'targetTemp', 'setTemp', 'temperatureSet']);
      result.targetTemp = normalizeTemperature(rawTarget);
    } else if (serviceId === 'mode') {
      // 模式
      if (serviceData.mode !== undefined) result.mode = String(serviceData.mode);
    } else if (serviceId === 'power') {
      // 部分空调用 power 表示功耗，非电源开关，忽略
    }
  }

  return result;
}

/**
 * 批量获取宠物设备服务快照
 * @param {PetDevicesResult} petDevices - 宠物设备识别结果
 * @returns {Promise<PetDeviceSnapshots>} 宠物设备快照数据
 */
export async function fetchPetDeviceSnapshots(petDevices) {
  const result = {
    catLitter: [],
    feeder: [],
    temperature: [],
    petLocation: [],
    airConditioner: []
  };

  if (!petDevices || petDevices.totalCount === 0) {
    return result;
  }

  // 收集所有宠物设备的ID
  const allDeviceIds = [];

  const deviceInfoMap = {};

  // 添加猫砂盆设备
  for (const device of (petDevices.catLitter || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'catLitter' };
  }

  // 添加喂食器设备
  for (const device of (petDevices.feeder || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'feeder' };
  }

  // 添加温湿度传感器
  for (const device of (petDevices.tempHumiditySensor || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'tempHumiditySensor' };
  }

  // 添加空调（同时获取温度和控制状态）
  for (const device of (petDevices.airConditioner || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'airConditioner' };
  }

  // 添加摄像头（用于宠物位置）
  for (const device of (petDevices.camera || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'camera' };
  }

  // 添加宠物定位器
  for (const device of (petDevices.petTracker || [])) {
    allDeviceIds.push(device.deviceId);
    deviceInfoMap[device.deviceId] = { ...device, category: 'petTracker' };
  }

  if (allDeviceIds.length === 0) {
    return result;
  }

  // 批量获取设备快照
  let snapshots;
  try {
    const snapshotResult = await getDeviceServiceSnapshot(allDeviceIds);
    snapshots = snapshotResult.snapshots || [];
  } catch (error) {
    console.error('[error] 获取设备快照失败:', error.message);
    return result;
  }

  // 解析每个设备的快照数据
  for (const snapshot of snapshots) {
    const deviceId = snapshot.deviceId;
    const deviceInfo = deviceInfoMap[deviceId];
    const category = deviceInfo?.category;

    switch (category) {
      case 'catLitter':
        result.catLitter.push(parseCatLitterData(snapshot, deviceInfo));
        break;
      case 'feeder':
        result.feeder.push(parseFeederData(snapshot, deviceInfo));
        break;
      case 'tempHumiditySensor':
        result.temperature.push(parseTemperatureData(snapshot, deviceInfo));
        break;
      case 'airConditioner': {
        // 空调需要同时获取温度和控制状态
        result.airConditioner.push(parseAirConditionerData(snapshot, deviceInfo));
        // 同时将空调温度添加到温度列表（作为备用温度源）
        const acTempData = parseAirConditionerTempData(snapshot, deviceInfo);
        if (acTempData.value !== null) {
          result.temperature.push(acTempData);
        }
        break;
      }
      case 'camera':
      case 'petTracker':
        result.petLocation.push(parsePetLocationData(snapshot, deviceInfo));
        break;
      default:
        console.error(`[warning] 未知类型：${category}`);
        continue;
    }
  }

  return result;
}

/**
 * 打印采集结果
 * @param {PetDeviceSnapshots} snapshots - 宠物设备快照
 */
function printCollectedData(snapshots) {
  console.log('\n========== 宠物设备数据采集结果 ==========');

  // 猫砂盆数据
  if (snapshots.catLitter.length > 0) {
    console.log('\n【猫砂盆】');
    for (const data of snapshots.catLitter) {
      console.log(`  ${data.deviceName} (${data.roomName}):`);
      console.log(`    使用次数: ${data.useCount ?? '未知'}`);
      console.log(`    最后使用: ${data.lastUseTime ?? '未知'}`);
      console.log(`    在线状态: ${data.online ? '在线' : '离线'}`);
    }
  }

  // 喂食器数据
  if (snapshots.feeder.length > 0) {
    console.log('\n【喂食器】');
    for (const data of snapshots.feeder) {
      console.log(`  ${data.deviceName} (${data.roomName}):`);
      console.log(`    出粮次数: ${data.feedCount ?? '未知'}`);
      console.log(`    最后出粮: ${data.lastFeedTime ?? '未知'}`);
      console.log(`    出粮量: ${data.portionSize ?? '未知'}克`);
      console.log(`    在线状态: ${data.online ? '在线' : '离线'}`);
    }
  }

  // 温度数据
  if (snapshots.temperature.length > 0) {
    console.log('\n【环境温度】');
    for (const data of snapshots.temperature) {
      const abnormalTag = data.isAbnormal ? ' ⚠️ 温度偏高' : '';
      console.log(`  ${data.deviceName} (${data.source}):`);
      console.log(`    温度: ${data.value ?? '未知'}°C`);
      console.log(`    湿度: ${data.humidity ?? '未知'}%`);
      console.log(`    在线状态: ${data.online ? '在线' : '离线'}${abnormalTag}`);
    }
  }

  // 宠物位置
  if (snapshots.petLocation.length > 0) {
    console.log('\n【宠物位置】');
    for (const data of snapshots.petLocation) {
      console.log(`  ${data.deviceName} (${data.source}):`);
      console.log(`    位置: ${data.location}`);
      console.log(`    在线状态: ${data.online ? '在线' : '离线'}`);
    }
  }

  // 空调数据
  if (snapshots.airConditioner.length > 0) {
    console.log('\n【空调状态】');
    for (const data of snapshots.airConditioner) {
      console.log(`  ${data.deviceName} (${data.roomName}):`);
      console.log(`    电源: ${data.powerState ? '开' : '关'}`);
      console.log(`    当前温度: ${data.currentTemp ?? '未知'}°C`);
      console.log(`    目标温度: ${data.targetTemp ?? '未知'}°C`);
      console.log(`    模式: ${data.mode || '未知'}`);
      console.log(`    在线状态: ${data.online ? '在线' : '离线'}`);
    }
  }

  console.log('\n==========================================\n');
}

// ==================== CLI 入口 ====================

async function main() {
  const args = process.argv.slice(2);

  // 解析命令行参数
  let petDevicesResult = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--device-ids' && args[i + 1]) {
      // 从设备ID列表获取（需要先识别设备类型）
      const deviceIds = args[i + 1].split(',');
      console.log(`[info] 将获取 ${deviceIds.length} 个设备的快照`);
      // 这里需要配合 pet-device-recognizer 使用，简化处理
      try {
        const deviceIdSet = new Set(deviceIds);
        const { getDevicesInfo } = await import('../../../common-skill/bin/get_devices_info.js');
        const devicesInfo = await getDevicesInfo({});
        const devices = devicesInfo.devices.filter(d => deviceIdSet.has(d.deviceId || d.devId));
        petDevicesResult = recognizePetDevices({ devices });
      } catch (error) {
        console.error('[error] 获取设备信息失败:', error.message);
        process.exit(1);
      }
      break;
    }
  }

  // 如果没有传入设备数据，则自动识别
  if (!petDevicesResult) {
    console.log('[info] 正在自动识别宠物设备...');
    petDevicesResult = await import('./pet-device-recognizer.js').then(m => m.fetchPetDevices());
  }

  console.log(`[info] 识别到 ${petDevicesResult.totalCount} 个宠物相关设备`);

  // 采集设备快照
  const snapshots = await fetchPetDeviceSnapshots(petDevicesResult);

  // 打印结果
  printCollectedData(snapshots);

  // 输出 JSON 格式结果
  console.log('--- START JSON OUTPUT ---');
  console.log(JSON.stringify({
    type: 'pet_device_snapshots',
    data: snapshots
  }));
  console.log('--- END JSON OUTPUT ---');
}

// 运行
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export {
  parseCatLitterData,
  parseFeederData,
  parseTemperatureData,
  parseAirConditionerTempData,
  parsePetLocationData,
  parseAirConditionerData,
  extractFieldValue,
  normalizeTemperature,
  normalizeHumidity
};