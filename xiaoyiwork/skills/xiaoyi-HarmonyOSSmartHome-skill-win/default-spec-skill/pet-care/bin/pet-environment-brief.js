#!/usr/bin/env node

/**
 * 宠物环境简报数据获取模块
 *
 * 功能：从云端获取宠物环境简报所需的原始数据
 * 描述类逻辑（简报生成、格式化输出）移至 SKILL.md 文件
 *
 * 使用方法：
 * node pet-environment-brief.js
 */

import { fetchPetCareData } from './pet-care-data-collector.js';

// ==================== 常量定义 ====================

/**
 * 简报生成配置
 */
const BRIEF_CONFIG = {
  TEMP_THRESHOLD: 26,
  CAT_LITTER_THRESHOLD: {
    LOW: 1,
    HIGH: 10
  },
  FEEDER_THRESHOLD: {
    MIN: 1,
    MAX: 5
  }
};

/**
 * @typedef {Object} PetEnvironmentBrief
 * @property {string} summaryPrefix - 简报摘要前缀
 * @property {string[]} alerts - 告警信息列表
 * @property {string[]} statusDetails - 状态详情列表
 * @property {string[]} suggestions - 建议列表
 * @property {boolean} isOwnerAway - 主人是否不在家
 * @property {string} generatedAt - 生成时间
 */

// ==================== 数据组装函数 ====================

/**
 * 提取猫砂盆状态数据
 * @param {object} catLitter - 猫砂盆快照数据
 * @returns {object} 猫砂盆状态
 */
function extractCatLitterStatus(catLitter) {
  if (!catLitter) return null;

  return {
    deviceName: catLitter.deviceName,
    roomName: catLitter.roomName,
    online: catLitter.online,
    useCount: catLitter.useCount,
    lastUseTime: catLitter.lastUseTime
  };
}

/**
 * 提取喂食器状态数据
 * @param {object} feeder - 喂食器快照数据
 * @returns {object} 喂食器状态
 */
function extractFeederStatus(feeder) {
  if (!feeder) return null;

  return {
    deviceName: feeder.deviceName,
    roomName: feeder.roomName,
    online: feeder.online,
    feedCount: feeder.feedCount,
    lastFeedTime: feeder.lastFeedTime,
    portionSize: feeder.portionSize
  };
}

/**
 * 提取温度状态数据
 * @param {object} temperature - 温度监控数据
 * @returns {object} 温度状态
 */
function extractTemperatureStatus(temperature) {
  return {
    value: temperature.value,
    humidity: temperature.humidity,
    source: temperature.source,
    status: temperature.status,
    isAbnormal: temperature.isAbnormal,
    shouldTurnOnAc: temperature.shouldTurnOnAc,
    acSuggestion: temperature.acSuggestion
  };
}

/**
 * 提取宠物位置数据
 * @param {object} petLocation - 宠物位置数据
 * @returns {object} 宠物位置
 */
function extractPetLocationStatus(petLocation) {
  if (!petLocation) return null;

  return {
    location: petLocation.location,
    source: petLocation.source,
    online: petLocation.online
  };
}

/**
 * 生成告警判断数据
 * @param {object} data - 宠物照护全量数据
 * @returns {string[]} 告警类型列表
 */
function extractAlerts(data) {
  const alerts = [];
  const { snapshots, temperature } = data;

  // 温度异常
  if (temperature.status === 'abnormal') {
    alerts.push('TEMP_ABNORMAL');
  }

  // 猫砂盆离线
  const catLitter = snapshots.catLitter?.[0];
  if (catLitter && !catLitter.online) {
    alerts.push('CAT_LITTER_OFFLINE');
  }

  // 喂食器离线
  const feeder = snapshots.feeder?.[0];
  if (feeder && !feeder.online) {
    alerts.push('FEEDER_OFFLINE');
  }

  // 猫砂盆未使用
  if (catLitter?.useCount === 0) {
    alerts.push('CAT_LITTER_NOT_USED');
  }

  // 未喂食
  if (feeder?.feedCount === 0) {
    alerts.push('NOT_FED');
  }

  return alerts;
}

/**
 * 生成建议判断数据
 * @param {object} data - 宠物照护全量数据
 * @returns {string[]} 建议类型列表
 */
function extractSuggestions(data) {
  const suggestions = [];
  const { temperature } = data;

  // 需要开空调
  if (temperature.shouldTurnOnAc) {
    suggestions.push('TURN_ON_AC');
  }

  // 喂食次数偏少
  const feeder = data.snapshots.feeder?.[0];
  if (feeder?.feedCount < BRIEF_CONFIG.FEEDER_THRESHOLD.MIN) {
    suggestions.push('LOW_FEED_COUNT');
  }

  return suggestions;
}

/**
 * 生成宠物环境简报数据对象
 * @param {object} data - 宠物照护全量数据
 * @returns {PetEnvironmentBrief} 简报数据对象
 */
function generatePetBriefData(data) {
  const { snapshots, temperature, isOwnerAway } = data;

  return {
    // 基础信息
    summaryPrefix: isOwnerAway ? '主人外出期间' : '当前在家',
    isOwnerAway,

    // 原始状态数据（供 SKILL.md 描述逻辑使用）
    catLitter: extractCatLitterStatus(snapshots.catLitter?.[0]),
    feeder: extractFeederStatus(snapshots.feeder?.[0]),
    temperature: extractTemperatureStatus(temperature),
    petLocation: extractPetLocationStatus(snapshots.petLocation?.[0]),

    // 告警和建议类型（供 SKILL.md 描述逻辑使用）
    alerts: extractAlerts(data),
    suggestions: extractSuggestions(data),

    // 时间戳
    generatedAt: data.timestamp
  };
}

/**
 * 从云端获取宠物环境简报数据
 * @returns {Promise<PetEnvironmentBrief>} 简报数据对象
 */
async function fetchPetBriefData() {
  console.log('[info] 正在获取宠物环境简报数据...');
  const data = await fetchPetCareData();
  return generatePetBriefData(data);
}

export {
  BRIEF_CONFIG,
  generatePetBriefData,
  fetchPetBriefData
};