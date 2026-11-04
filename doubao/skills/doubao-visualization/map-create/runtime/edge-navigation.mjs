export function classifyViewportEntries(
  elements,
  geometry,
  canvas,
  reservations = [],
) {
  const intersection = (bounds, other) => ({
    left: Math.max(bounds.left, other.left),
    right: Math.min(bounds.right, other.right),
    top: Math.max(bounds.top, other.top),
    bottom: Math.min(bounds.bottom, other.bottom),
  });
  const hasArea = bounds =>
    bounds.right > bounds.left && bounds.bottom > bounds.top;
  const obstacles = reservations
    .filter(item => item.blocksPointer)
    .map(({ rect }) => ({
      left: rect.x,
      top: rect.y,
      right: rect.x + rect.width,
      bottom: rect.y + rect.height,
    }));
  const hasVisibleArea = bounds => {
    let remaining = [intersection(bounds, canvas)].filter(hasArea);
    for (const obstacle of obstacles) {
      remaining = remaining.flatMap(rect => {
        const overlap = intersection(rect, obstacle);
        if (!hasArea(overlap)) return [rect];
        return [
          { ...rect, bottom: overlap.top },
          { ...rect, top: overlap.bottom },
          {
            left: rect.left,
            right: overlap.left,
            top: overlap.top,
            bottom: overlap.bottom,
          },
          {
            left: overlap.right,
            right: rect.right,
            top: overlap.top,
            bottom: overlap.bottom,
          },
        ].filter(hasArea);
      });
      if (!remaining.length) return false;
    }
    return remaining.length > 0;
  };
  const groups = { left: [], right: [], top: [], bottom: [] };
  const entries = [];
  const partsById = new Map();
  const seen = new Set();
  for (const item of geometry.items || []) {
    if (!['anchor', 'icon', 'label', 'description', 'body'].includes(item.part))
      continue;
    if (!partsById.has(item.elementId)) partsById.set(item.elementId, []);
    partsById.get(item.elementId).push(item);
  }
  for (const element of elements) {
    if (element.visible === false || !element.position || seen.has(element.id))
      continue;
    seen.add(element.id);
    const parts = partsById.get(element.id) || [];
    if (!parts.length) continue;
    const title = String(element.label || element.name || element.id);
    const visible = parts.some(part => hasVisibleArea(part.bounds));
    const clipped = parts.some(
      ({ bounds }) =>
        bounds.left < canvas.left ||
        bounds.top < canvas.top ||
        bounds.right > canvas.right ||
        bounds.bottom > canvas.bottom,
    );
    let direction = null;
    if (!visible) {
      const bounds = parts[0].bounds;
      const horizontal =
        ((bounds.left + bounds.right) / 2 - (canvas.left + canvas.right) / 2) /
        Math.max(1, canvas.right - canvas.left);
      const vertical =
        ((bounds.top + bounds.bottom) / 2 - (canvas.top + canvas.bottom) / 2) /
        Math.max(1, canvas.bottom - canvas.top);
      direction =
        Math.abs(horizontal) >= Math.abs(vertical)
          ? horizontal < 0
            ? 'left'
            : 'right'
          : vertical < 0
            ? 'top'
            : 'bottom';
      groups[direction].push({ id: element.id, title });
    }
    entries.push({ id: element.id, visible, clipped, direction });
  }
  return { groups, entries };
}
