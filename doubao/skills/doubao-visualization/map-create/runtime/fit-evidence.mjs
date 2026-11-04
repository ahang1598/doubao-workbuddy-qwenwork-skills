export function classifyFitGeometry(cells, canvas, reservations, safe) {
  const strokeIntersects = (stroke, rect) => {
    const padding = stroke.width / 2 + 0.25;
    for (let index = 1; index < stroke.points.length; index++) {
      const start = stroke.points[index - 1],
        end = stroke.points[index];
      let enter = 0,
        leave = 1;
      for (const [axis, minimum, maximum] of [
        ['x', rect.left - padding, rect.right + padding],
        ['y', rect.top - padding, rect.bottom + padding],
      ]) {
        const delta = end[axis] - start[axis];
        if (delta === 0) {
          if (start[axis] < minimum || start[axis] > maximum) {
            enter = 2;
            break;
          }
        } else {
          const first = (minimum - start[axis]) / delta;
          const last = (maximum - start[axis]) / delta;
          enter = Math.max(enter, Math.min(first, last));
          leave = Math.min(leave, Math.max(first, last));
        }
      }
      if (enter <= leave) return true;
    }
    return false;
  };
  const intersects = (left, right) =>
    left.left < right.right &&
    left.right > right.left &&
    left.top < right.bottom &&
    left.bottom > right.top;
  const outside = (bounds, rect) =>
    bounds.left < rect.left ||
    bounds.right > rect.right ||
    bounds.top < rect.top ||
    bounds.bottom > rect.bottom;
  const failures = [],
    warnings = [];
  for (const cell of cells) {
    const clipped = outside(cell.bounds, canvas);
    const obstacles = reservations
      .filter(
        item =>
          item.blocksPointer !== false &&
          (cell.strokes?.length
            ? cell.strokes.some(stroke =>
                strokeIntersects(stroke, {
                  left: item.rect.x,
                  top: item.rect.y,
                  right: item.rect.x + item.rect.width,
                  bottom: item.rect.y + item.rect.height,
                }),
              )
            : intersects(cell.bounds, {
                left: item.rect.x,
                top: item.rect.y,
                right: item.rect.x + item.rect.width,
                bottom: item.rect.y + item.rect.height,
              })),
      )
      .map(item => item.id);
    const evidence = { featureId: cell.featureId, clipped, obstacles };
    if (clipped || obstacles.length) failures.push(evidence);
    else if (outside(cell.bounds, safe))
      warnings.push({ ...evidence, reason: 'safe-padding' });
  }
  return { failures, warnings };
}
