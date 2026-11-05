import { prepareGraph } from '../lib/engine.mjs';
import { deriveSource } from '../runtime/derive-source.mjs';

// Recompute from the serialized root tables, not the Runtime's reported counts
// or its mutable component projection. Observe the actual Kit boundary and DOM.
export function compareSourceEvidence({ graph, state, elements, metrics }) {
  if (![2, 3].includes(graph.contractRevision))
    return { status: 'not-applicable', errors: [] };
  const view = prepareGraph(graph).views.find(
    view => view.id === state.activeViewId,
  );
  const errors = [];
  const groups = [];
  for (const group of view.analysisFilters) {
    const observed = state.analysisFilters.find(
      item => item.sourceId === group.sourceId,
    );
    if (!observed) {
      errors.push(`${group.sourceId}: missing filter state`);
      continue;
    }
    const expected = deriveSource(
      { rows: group.sourceRows },
      group.fields,
      observed.selected,
      group.metricDefinitions,
    );
    if (
      JSON.stringify(expected.pointIds) !== JSON.stringify(observed.pointIds) ||
      observed.effectiveCount !== expected.pointIds.length ||
      observed.sourceCount !== group.sourceRows.length
    )
      errors.push(
        `${group.sourceId}: effective rows differ from source predicates`,
      );
    for (const id of group.elementIds) {
      const actual = elements.find(element => element.id === id);
      const layer = graph.layers.find(layer => layer.elementIds.includes(id));
      const expectedPoints = group.sourceRows.map(row => ({
        id: row.id,
        position: row.position,
        value:
          layer.analysis.hexbin.aggregation.op === 'count'
            ? 1
            : row.values[layer.analysis.hexbin.aggregation.fieldId],
        weight: layer.analysis.continuous.weightFieldId
          ? row.values[layer.analysis.continuous.weightFieldId]
          : 1,
        sourceRef: { type: row.entity.kind, id: row.entity.id },
      }));
      if (
        JSON.stringify(actual?.points) !== JSON.stringify(expectedPoints) ||
        JSON.stringify(actual?.filter?.pointIds) !==
          JSON.stringify(expected.pointIds) ||
        actual?.filter?.scalePopulation !== group.scalePopulation
      )
        errors.push(
          `${id}: component rows or scale population differ from root bindings`,
        );
    }
    for (const metric of expected.metrics) {
      const matches = metrics.filter(item => item.id === metric.id);
      const expectedText =
        `${metric.value === null ? '无数据' : metric.value} ${metric.unit}`.trim();
      if (
        matches.length !== 1 ||
        matches[0].value !== String(metric.value) ||
        matches[0].text.trim() !== expectedText
      )
        errors.push(
          `${metric.id}: rendered metric differs from source aggregation`,
        );
    }
    groups.push({
      sourceId: group.sourceId,
      rowCount: group.sourceRows.length,
      effectiveCount: expected.pointIds.length,
      metricIds: expected.metrics.map(item => item.id),
    });
  }
  return { status: errors.length ? 'failed' : 'passed', groups, errors };
}

export async function inspectSourceEvidence(page) {
  return compareSourceEvidence(
    await page.evaluate(() => ({
      graph: window.mapCreateGraph,
      state: window.mapCreateState,
      elements: window.mapCreateRuntime.layer.getElements(),
      metrics: [...document.querySelectorAll('[data-metric-id]')].map(node => ({
        id: node.dataset.metricId,
        value: node.dataset.metricValue,
        text: node.querySelector('dd')?.textContent ?? '',
      })),
    })),
  );
}
