function safeText(value, maximum = 500) {
  return `${value ?? ''}`.trim().slice(0, maximum);
}

export function buildChatUpdate(snapshot, seenIds = []) {
  const seen = new Set((Array.isArray(seenIds) ? seenIds : []).map(Number).filter(Number.isSafeInteger));
  const records = Array.isArray(snapshot?.records) ? snapshot.records : [];
  const hits = records.filter((record) => record?.machine_result === 'hit' && Number.isSafeInteger(Number(record.id)));
  const newFindings = hits.filter((record) => !seen.has(Number(record.id))).map((record) => ({
    event_id: Number(record.id),
    rule_name: safeText(record.rule_name, 200) || '质检规则',
    time: safeText(record.samples?.[0]?.time, 20) || null,
    evidence: safeText(record.samples?.[0]?.text, 300) || null,
    reason: safeText(record.samples?.[0]?.reason, 300) || null,
  }));
  const ruleCounts = new Map();
  for (const record of hits) {
    const name = safeText(record.rule_name, 200) || '质检规则';
    ruleCounts.set(name, (ruleCounts.get(name) || 0) + 1);
  }
  const topRule = [...ruleCounts.entries()].sort((left, right) => right[1] - left[1])[0] || null;
  const createdAt = Number(snapshot?.task?.created_at);
  const updatedAt = Number(snapshot?.task?.updated_at);
  const endAt = [3, 4, 5].includes(Number(snapshot?.task?.status)) && Number.isFinite(updatedAt) ? updatedAt : Date.now() / 1_000;
  const monitoredSeconds = Number.isFinite(createdAt) && createdAt > 0
    ? Math.max(0, Math.floor(endAt - createdAt)) : null;
  return {
    task: {
      task_id: Number(snapshot?.task?.id) || null,
      task_name: safeText(snapshot?.task?.name, 200) || '直播质检任务',
      scenario: safeText(snapshot?.task?.scenario_name, 20) || null,
      status: safeText(snapshot?.task?.status_text, 20) || '状态同步中',
      monitored_seconds: monitoredSeconds,
    },
    summary: {
      finding_count: hits.length,
      rule_count: ruleCounts.size,
      latest_finding_time: safeText(hits[0]?.samples?.[0]?.time, 20) || null,
      top_rule: topRule ? { name: topRule[0], count: topRule[1] } : null,
    },
    new_findings: newFindings,
    cursor: [...new Set([...seen, ...hits.map((record) => Number(record.id))])],
    checked_at: snapshot?.refreshed_at || new Date().toISOString(),
  };
}
