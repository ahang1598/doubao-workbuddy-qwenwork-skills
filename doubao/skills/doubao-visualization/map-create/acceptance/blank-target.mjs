export function findBlankMapTarget() {
  const runtime = window.mapCreateRuntime;
  const box = document.getElementById('map').getBoundingClientRect();
  const elements = runtime.layer
    .getElements()
    .filter(
      element =>
        element.visible !== false && element.interaction?.selectable !== false,
    );
  const inRing = (point, ring) => {
    let inside = false;
    for (
      let index = 0, previous = ring.length - 1;
      index < ring.length;
      previous = index++
    ) {
      const start = ring[index],
        end = ring[previous];
      if (
        start[1] > point[1] !== end[1] > point[1] &&
        point[0] <
          ((end[0] - start[0]) * (point[1] - start[1])) / (end[1] - start[1]) +
            start[0]
      )
        inside = !inside;
    }
    return inside;
  };
  const geometry = runtime.layer.getScreenGeometry?.().items || [];
  for (const horizontal of [0.1, 0.9, 0.3, 0.7, 0.02, 0.98]) {
    for (const vertical of [0.1, 0.85, 0.3, 0.6, 0.02, 0.98]) {
      const x = box.left + box.width * horizontal,
        y = box.top + box.height * vertical;
      const target = document.elementFromPoint(x, y);
      if (
        !target ||
        target.closest(
          '#selection-details,#content-map-ui,#map-sources,#map-legend,#map-controls,#heatmap-controls',
        )
      )
        continue;
      const hitId = target
        .closest('[data-element-id]')
        ?.getAttribute('data-element-id');
      if (elements.some(element => element.id === hitId)) continue;
      const coordinate = runtime.map.containerToLngLat([
        x - box.left,
        y - box.top,
      ]);
      const point = [coordinate.getLng(), coordinate.getLat()];
      const occupied = elements.some(element => {
        if (element.type === 'circle' && inRing(point,
          window.ContentMapKit.getCircleRing(element.center, element.radiusMeters))) return true;
        if (
          element.polygons?.some(
            polygon =>
              inRing(point, polygon[0]) &&
              !polygon.slice(1).some(ring => inRing(point, ring)),
          )
        )
          return true;
        return (
          element.type === 'heatmap' &&
          geometry.some(
            item =>
              item.elementId === element.id &&
              x - box.left >= item.bounds.left &&
              x - box.left <= item.bounds.right &&
              y - box.top >= item.bounds.top &&
              y - box.top <= item.bounds.bottom,
          )
        );
      });
      if (!occupied) return { x, y };
    }
  }
  return null;
}
