// Executed in the browser. Compare actual map SVG and legend SVG, not the
// component's claimed recipe or a second hand-maintained railway definition.
export function inspectRouteSymbols() {
  const supported =
    window.ContentMapKit.getRuntimeContract?.().capabilities?.includes(
      'route.legend-symbol@1',
    ) === true;
  if (!supported)
    return { method: 'legacy-css', status: 'not-run', errors: [] };
  const attributes = [
    'stroke',
    'stroke-width',
    'stroke-dasharray',
    'stroke-opacity',
    'stroke-linecap',
    'fill',
    'href',
  ];
  const signature = root =>
    [...root.querySelectorAll('[data-part="body"], [data-part="arrow"]')]
      .filter(node => ['path', 'image'].includes(node.tagName.toLowerCase()))
      .map(node => ({
        tag: node.tagName.toLowerCase(),
        part: node.dataset.part,
        attrs: Object.fromEntries(
          attributes.map(name => [name, node.getAttribute(name)]),
        ),
      }));
  const errors = [];
  const entries = [
    ...document.querySelectorAll('#map-legend .legend__swatch--line'),
  ].map(swatch => {
    const id = swatch.dataset.symbolElementId;
    const mapElement = [
      ...document.querySelectorAll('#map [data-element-id]'),
    ].find(node => node.dataset.elementId === id);
    const actual = signature(swatch);
    const expected = mapElement ? signature(mapElement) : [];
    if (
      !id ||
      !expected.length ||
      !actual.length ||
      swatch.dataset.symbolScale !== '1' ||
      JSON.stringify(actual) !== JSON.stringify(expected)
    )
      errors.push(`路线与图例实际符号不一致：${id || '缺少来源身份'}`);
    return {
      elementId: id,
      map: expected,
      legend: actual,
      scale: swatch.dataset.symbolScale,
    };
  });
  return {
    method: 'actual-svg-attributes',
    status: errors.length ? 'failed' : 'passed',
    entries,
    errors,
  };
}
