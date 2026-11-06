// ==================== query_record 触发语料（范化版）====================
// 正向语料：可正常触发观影记录查询
// 负向语料：不触发观影记录查询，提示不支持

export const TRIGGER_PATTERNS = {
  POSITIVE: {
    // 基础查询模式
    BASIC:
      /^((查询|查看|显示|查找|调出|列出|输出)?(我的)?(历史)?(观影|播放|观看)(记录|历史|列表)?)$/,

    // 设备 + 记录组合
    DEVICE:
      /^(电视|大屏|智慧屏|客厅电视|主卧电视|卧室大屏)(一|上|的)?(最近|昨天|上周|本月|今年|春节|历史|播放)?(放过|看过|播放过|观看)?(什么|哪些|电影|电视剧|综艺|纪录片)?(记录|历史)?$/,

    // 时间 + 观看组合
    TIME: /^(昨天|上周|本月|今年|上个月|最近三天|最近一周|春节期间)(的)?(观看|播放)?(历史|记录)?$/,

    // 华为视频相关
    HUAWEI_VIDEO:
      /^(电视|智慧屏|大屏)?(一|上)?华为视频(的)?(最近|昨天|上周|今年|历史|播放)?(过|的)?(什么|哪些|电影|电视剧|综艺|纪录片|动漫)?(记录|历史)?$/,

    // 续播/进度查询（含影片名）
    RESUME:
      /^(《.+》|(上次|之前|继续|最近)(看|播放)?(的|那个)?)(看到哪|放到哪|播放到|看到什么位置|进度|第几集)$/,

    // 全量查询
    BULK_QUERY:
      /^(所有|全部|给我\d+条?|列出\d+条?|我要看(所有|全部)|返回所有)(观影|播放|观看)?(记录|历史)?$/,
  },

  NEGATIVE: {
    // 第三方应用查询
    THIRD_PARTY:
      /(腾讯视频|爱奇艺|优酷|芒果TV|哔哩哔哩|b站|奇异果|云视听|CIBN|酷喵)(的|上|的)?(观影|播放|观看)?(记录|历史)?/,
  },
};

export const NEGATIVE_REASON = {
  THIRD_PARTY: "仅支持查询华为视频的观影记录，暂不支持查询第三方应用的观影记录",
};

export function isPositiveTrigger(userInput) {
  const input = userInput.trim();

  for (const pattern of Object.values(TRIGGER_PATTERNS.POSITIVE)) {
    if (pattern.test(input)) {
      return true;
    }
  }

  return false;
}

export function matchNegativePhrase(userInput) {
  const input = userInput.trim();

  if (TRIGGER_PATTERNS.NEGATIVE.THIRD_PARTY.test(input)) {
    return { matched: true, reason: NEGATIVE_REASON.THIRD_PARTY };
  }

  return { matched: false, reason: null };
}

export function shouldTriggerQuery(userInput) {
  const negativeResult = matchNegativePhrase(userInput);
  if (negativeResult.matched) {
    return { shouldTrigger: false, reason: negativeResult.reason };
  }

  if (isPositiveTrigger(userInput)) {
    return { shouldTrigger: true, reason: null };
  }

  return { shouldTrigger: false, reason: null };
}
