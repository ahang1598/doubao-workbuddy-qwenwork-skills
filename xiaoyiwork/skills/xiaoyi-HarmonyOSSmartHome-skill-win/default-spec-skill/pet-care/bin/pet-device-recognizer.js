#!/usr/bin/env node

/**
 * 宠物设备识别模块
 * 根据 prodId 或 deviceType 识别宠物相关设备
 *
 * 功能：
 * - 识别智能猫砂盆
 * - 识别智能喂食器
 * - 识别宠物定位器
 * - 识别温湿度传感器（用于宠物环境监测）
 * - 识别空调（用于温度监控联动）
 * - 识别摄像头（用于宠物位置确认）
 *
 * 使用方法：
 * node pet-device-recognizer.js
 * node pet-device-recognizer.js --devices '{"devices": [...]}'
 */

import { getDevicesInfo } from '../../../common-skill/bin/get_devices_info.js';

// ==================== 宠物设备类型定义 ====================

/**
 * 宠物设备映射表
 * 用于通过 prodId 关键字识别宠物相关设备
 */
const PET_DEVICE_KEYWORDS = {
  catLitter: ['litter', 'cat-litter', 'cat_litter', '猫砂', '猫砂盆', '猫厕所', 'cat-toilet', 'cat_toilet'],
  feeder: ['feeder', 'pet-feeder', 'pet_feeder', '喂食器', '自动喂食器', '宠物喂食器'],
  petTracker: ['tracker', 'pet-tracker', 'pet_tracker', '定位', '宠物定位', 'GPS'],
  tempHumiditySensor: ['temp-humidity', 'temp_humidity', '温湿度', '湿度传感器', '环境传感器'],
  airConditioner: ['air-conditioner', 'air_conditioner', '空调', 'AC'],
  camera: ['camera', '摄像头', '摄影头', 'IPC', '监控']
};

/**
 * 设备类型到分类的映射
 * 用于通过 deviceType 识别设备类型
 */
const DEVICE_TYPE_MAP = {
  // 温湿度传感器
  'temp': 'tempHumiditySensor',
  'humidity': 'tempHumiditySensor',
  'sensor': 'tempHumiditySensor',
  // 空调
  'AC': 'airConditioner',
  'airConditioner': 'airConditioner',
  // 摄像头
  'camera': 'camera',
  'IPC': 'camera'
};

/**
 * 温度异常阈值（摄氏度）
 */
const TEMP_ABNORMAL_THRESHOLD = 26;

/**
 * 排除名单 — 匹配了关键词但实际不是宠物设备的
 * 通过设备名/productName 中是否包含这些关键词来过滤
 */
const PET_DEVICE_EXCLUDE_KEYWORDS = ['freelace', 'freebuds', '耳机', '手表', 'watch'];

/**
 * @typedef {Object} PetDevice
 * @property {string} deviceId - 设备ID
 * @property {string} deviceName - 设备名称
 * @property {string} roomName - 房间名称
 * @property {string} category - 设备分类 (catLitter|feeder|petTracker|tempHumiditySensor|airConditioner|camera)
 * @property {string} prodId - 产品ID
 * @property {boolean} online - 是否在线
 */

/**
 * @typedef {Object} PetDevicesResult
 * @property {PetDevice[]} catLitter - 猫砂盆设备列表
 * @property {PetDevice[]} feeder - 喂食器设备列表
 * @property {PetDevice[]} petTracker - 宠物定位器列表
 * @property {PetDevice[]} tempHumiditySensor - 温湿度传感器列表
 * @property {PetDevice[]} airConditioner - 空调设备列表
 * @property {PetDevice[]} camera - 摄像头设备列表
 * @property {number} totalCount - 宠物相关设备总数
 */

/**
 * 根据设备信息判断设备类型
 * @param {object} device - 设备信息
 * @returns {string|null} 设备分类或null（不是宠物相关设备）
 */
function recognizeDeviceCategory(device) {
  if (!device) return null;

  const { prodId, deviceType, deviceName, productName } = device;
  const searchText = `${prodId || ''} ${deviceType || ''} ${deviceName || ''} ${productName || ''}`.toLowerCase();

  // ⚠️ 先检查排除名单 — 如果匹配了排除关键词，直接返回 null
  for (const excludeKw of PET_DEVICE_EXCLUDE_KEYWORDS) {
    if (searchText.includes(excludeKw.toLowerCase())) {
      return null;
    }
  }

  // 检查每个设备类别的关键字
  for (const [category, keywords] of Object.entries(PET_DEVICE_KEYWORDS)) {
    for (const keyword of keywords) {
      if (searchText.includes(keyword.toLowerCase())) {
        return category;
      }
    }
  }

  // 检查 deviceType 映射
  if (deviceType && DEVICE_TYPE_MAP[deviceType]) {
    return DEVICE_TYPE_MAP[deviceType];
  }

  return null;
}

/**
 * 识别设备列表中的宠物相关设备
 * @param {object} devicesInfo - getDevicesInfo 返回的设备信息
 * @returns {PetDevicesResult} 分类后的宠物设备
 */
export function recognizePetDevices(devicesInfo) {
  const result = {
    catLitter: [],
    feeder: [],
    petTracker: [],
    tempHumiditySensor: [],
    airConditioner: [],
    camera: [],
    totalCount: 0
  };

  if (!devicesInfo || !devicesInfo.devices) {
    return result;
  }

  const devices = devicesInfo.devices;

  for (const device of devices) {
    const category = recognizeDeviceCategory(device);
    if (category && result[category]) {
      const petDevice = {
        deviceId: device.deviceId || device.devId || '',
        deviceName: device.deviceName || device.deviceName || '',
        roomName: device.roomName || '未分类',
        category: category,
        prodId: device.prodId || '',
        online: true // 在线状态需要单独查询
      };
      result[category].push(petDevice);
    }
  }

  // 计算总数
  result.totalCount = result.catLitter.length +
    result.feeder.length +
    result.petTracker.length +
    result.tempHumiditySensor.length +
    result.airConditioner.length +
    result.camera.length;

  return result;
}

/**
 * 获取宠物相关设备（从云端获取设备列表）
 * @returns {Promise<PetDevicesResult>} 分类后的宠物设备
 */
export async function fetchPetDevices() {
  const devicesInfo = await getDevicesInfo({});
  return recognizePetDevices(devicesInfo);
}

/**
 * 从已有设备列表中提取宠物相关设备
 * @param {object} devicesInfo - 设备信息对象
 * @returns {PetDevicesResult} 分类后的宠物设备
 */
export function extractPetDevicesFromList(devicesInfo) {
  return recognizePetDevices(devicesInfo);
}

/**
 * 打印设备识别结果
 * @param {PetDevicesResult} petDevices - 宠物设备识别结果
 */
function printRecognizedDevices(petDevices) {
  console.log('\n========== 宠物设备识别结果 ==========');

  const categories = [
    { key: 'catLitter', name: '猫砂盆' },
    { key: 'feeder', name: '喂食器' },
    { key: 'petTracker', name: '宠物定位器' },
    { key: 'tempHumiditySensor', name: '温湿度传感器' },
    { key: 'airConditioner', name: '空调' },
    { key: 'camera', name: '摄像头' }
  ];

  for (const { key, name } of categories) {
    const devices = petDevices[key];
    if (devices.length > 0) {
      console.log(`\n${name} (${devices.length}个):`);
      for (const device of devices) {
        console.log(`  - ${device.deviceName} (${device.roomName}) [${device.deviceId}]`);
      }
    }
  }

  console.log(`\n总计: ${petDevices.totalCount} 个宠物相关设备`);
  console.log('========================================\n');
}

// ==================== CLI 入口 ====================

async function main() {
  const args = process.argv.slice(2);

  // 检查是否有传入设备数据
  let devicesInfo = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--devices' && args[i + 1]) {
      try {
        devicesInfo = JSON.parse(args[i + 1]);
      } catch (e) {
        console.error('[error] 设备数据 JSON 格式错误');
        process.exit(1);
      }
      break;
    }
  }

  // 如果没有传入设备数据，则从云端获取
  if (!devicesInfo) {
    console.log('[info] 未传入设备数据，正在从云端获取...');
    try {
      devicesInfo = await getDevicesInfo({});
    } catch (error) {
      console.error('[error] 获取设备信息失败:', error.message);
      process.exit(1);
    }
  }

  // 识别宠物设备
  const petDevices = recognizePetDevices(devicesInfo);

  // 打印结果
  printRecognizedDevices(petDevices);

  // 输出 JSON 格式结果
  console.log('--- START JSON OUTPUT ---');
  console.log(JSON.stringify({
    type: 'pet_devices',
    data: petDevices
  }));
  console.log('--- END JSON OUTPUT ---');
}

// 运行
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export {
  recognizeDeviceCategory,
  TEMP_ABNORMAL_THRESHOLD
};