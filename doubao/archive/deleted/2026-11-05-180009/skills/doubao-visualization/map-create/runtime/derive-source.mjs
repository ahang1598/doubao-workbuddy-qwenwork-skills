/** Deterministic host-owned predicates and metrics, shared by compilation tests
 * and the browser. All consumers receive the same effective row identities. */
export function deriveSource(source, filters, selected, metrics = []) {
  const fold = value => value.normalize('NFKC').toLocaleLowerCase('und');
  const predicates = filters.map((filter, index) => {
    const condition = selected[index];
    if (condition === null) return () => true;
    if (filter.kind === 'enum') {
      if (
        !Array.isArray(condition) ||
        new Set(condition).size !== condition.length ||
        condition.some(
          value =>
            !Number.isInteger(value) ||
            value < 0 ||
            value >= filter.options.length,
        )
      )
        throw new Error('枚举筛选选项无效');
      const values = new Set(
        condition.map(option => filter.options[option].value),
      );
      return row => values.has(row.values[filter.fieldId]);
    }
    if (filter.kind === 'text') {
      if (typeof condition !== 'string')
        throw new Error('文本筛选必须是字符串');
      const query = fold(condition);
      return row =>
        typeof row.values[filter.fieldId] === 'string' &&
        fold(row.values[filter.fieldId]).includes(query);
    }
    if (
      !['number-range', 'time-range'].includes(filter.kind) ||
      !Array.isArray(condition) ||
      condition.length !== 2 ||
      condition.some(value => value !== null && !Number.isFinite(value)) ||
      (condition[0] !== null &&
        condition[1] !== null &&
        condition[0] > condition[1])
    )
      throw new Error('范围必须为包含边界的合法上下限');
    return row =>
      Number.isFinite(row.values[filter.fieldId]) &&
      (condition[0] === null || row.values[filter.fieldId] >= condition[0]) &&
      (condition[1] === null || row.values[filter.fieldId] <= condition[1]);
  });
  const rows = source.rows.filter(row =>
    predicates.every(predicate => predicate(row)),
  );
  const results = metrics.map(metric => {
    const population = metric.scope === 'all-source' ? source.rows : rows;
    const values = population
      .map(row => row.values[metric.fieldId])
      .filter(value => value !== null && value !== undefined);
    let value;
    if (metric.op === 'count') value = population.length;
    else if (metric.op === 'distinct-count') value = new Set(values).size;
    else {
      if (values.some(value => !Number.isFinite(value)))
        throw new Error('指标需要有限数值');
      if (!values.length) value = null;
      else if (metric.op === 'min')
        value = values.reduce((a, b) => Math.min(a, b));
      else if (metric.op === 'max')
        value = values.reduce((a, b) => Math.max(a, b));
      else if (metric.op === 'sum') value = values.reduce((a, b) => a + b, 0);
      else if (metric.op === 'average')
        value = values.reduce((a, b) => a + b / values.length, 0);
      else throw new Error('未知指标运算');
      if (value !== null && !Number.isFinite(value))
        throw new Error('指标聚合溢出');
    }
    return {
      id: metric.id,
      label: metric.label,
      value,
      unit: metric.unit ?? '',
      scope: metric.scope,
      sampleCount: metric.op === 'count' ? population.length : values.length,
    };
  });
  return { pointIds: rows.map(row => row.id), metrics: results };
}
