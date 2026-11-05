// 仅采集链路标识，不保存请求头、凭证或业务参数。
export function requestTrace(stage, api_name, response, entity_id) {
  const value = response?.logid;
  const logid = typeof value === 'string' && /^[A-Za-z0-9_-]{1,256}$/.test(value)
    ? value : null;
  return { stage, api_name, logid, ...(entity_id ? { entity_id } : {}) };
}

export function toolCall(tool_name, entity_ids, requests) {
  return { tool_name, entity_ids: [...new Set(entity_ids)], requests };
}

export function mergeToolCalls(...lists) {
  return [...new Map(lists.flat().map(call => [JSON.stringify(call), call])).values()];
}
