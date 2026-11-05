// Compare identity, not the presence of an unrelated basemap canvas.
export function compareRenderedElements(expectedIds, svgIds, canvasIds) {
  const expected = new Set(expectedIds);
  const rendered = new Set([...svgIds, ...canvasIds]);
  return {
    missing: [...expected].filter(id => !rendered.has(id)),
    unexpected: [...rendered].filter(id => !expected.has(id)),
  };
}
