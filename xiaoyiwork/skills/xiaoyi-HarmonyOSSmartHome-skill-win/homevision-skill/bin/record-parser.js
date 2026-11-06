// ==================== 观影记录解析工具 ====================
// 功能：解析MateTV观影记录数据，生成待展示内容

const VIDEO_CATEGORY = {
  MOVIE: 1,        // 电影
  TV_SERIES: 2,    // 电视剧
  VARIETY: 3,      // 综艺
  ANIMATION: 4,    // 动漫
  SPORTS: 5,       // 体育
  // 6-12 为其他类型视频，如果volumeIndex大于0，则显示第 xx 集
};

const DEFAULT_MAX_RECORDS = 5;

function isMinorModeRecord(userName) {
  return userName && typeof userName === 'string' && userName.includes('recordInMinorMode');
}

function parseEpisodeInfo(videoCategoryType, volumeIndex) {
  if (volumeIndex <= 0) {
    return '';
  }

  if (!videoCategoryType) {
    // 兼容老版本
    return `第 ${volumeIndex} 集`;
  }

  const category = parseInt(videoCategoryType, 10);

  if (category === VIDEO_CATEGORY.VARIETY) {
    return `第 ${volumeIndex} 期`;
  }
  if (category === VIDEO_CATEGORY.MOVIE) {
    return '';
  }

  return `第 ${volumeIndex} 集`;
}

function parseProgress(playRate) {
  const rate = parseFloat(playRate);
  if (isNaN(rate) || rate <= 0) {
    return '不足1%';
  }
  return `${rate}%`;
}

function parseSingleRecord(record) {
  return {
    filmTitle: record.filmTitle || '',
    episodeInfo: parseEpisodeInfo(record.videoCategoryType, record.volumeIndex),
    progress: parseProgress(record.playRate)
  };
}

export function parseRecordData(rawData, deviceName, options = {}) {
  const { maxRecords = DEFAULT_MAX_RECORDS, includeMinorMode = false } = options;

  if (!rawData || !rawData.mediaRecordList || !Array.isArray(rawData.mediaRecordList)) {
    return {
      success: false,
      error: 'invalid_data',
      deviceName,
      records: [],
      hasMinorMode: false,
      totalCount: 0
    };
  }

  const allRecords = rawData.mediaRecordList;
  const result = {
    success: true,
    deviceName,
    records: [],
    hasMinorMode: false,
    totalCount: allRecords.length
  };

  let filteredRecords = allRecords;

  if (!includeMinorMode) {
    filteredRecords = allRecords.filter(record => !isMinorModeRecord(record.userName));
    result.hasMinorMode = allRecords.length !== filteredRecords.length;
  }

  const sortedRecords = filteredRecords.sort((a, b) => {
    const timeA = a.watchedTime || 0;
    const timeB = b.watchedTime || 0;
    return timeB - timeA;
  });

  const limitedRecords = sortedRecords.slice(0, maxRecords);

  result.records = limitedRecords.map(parseSingleRecord);

  return result;
}

export function buildDisplayTitle(deviceName) {
  return `${deviceName}上华为视频的最近观影记录如下：`;
}

export function buildDisplayTable(records) {
  if (!records || records.length === 0) {
    return null;
  }

  const rows = records.map((record, index) => {
    const episodeCell = record.episodeInfo ? record.episodeInfo : '';
    return `| ${index + 1} | 《${record.filmTitle}》 | ${episodeCell} | ${record.progress} |`;
  });

  return [
    '| 序号 | 影片名称 | 集数 | 播放进度 |',
    '|------|----------|------|----------|',
    ...rows
  ].join('\n');
}

export function buildMinorModeNotice() {
  return '当前展示的信息不包含未成年人模式下的观影记录';
}

export function buildUnsupportedDeviceNotice(deviceName) {
  return `${deviceName} 暂不支持查询观影记录，仅Mate TV支持查询观影记录`;
}

export function buildParseErrorNotice(deviceName) {
  return `${deviceName} 暂不支持查询观影记录，请将智慧屏升级到7.0.0.103版本后重试`;
}

export function buildQueryLimitNotice() {
  return '仅查询最近五条历史记录数据';
}
