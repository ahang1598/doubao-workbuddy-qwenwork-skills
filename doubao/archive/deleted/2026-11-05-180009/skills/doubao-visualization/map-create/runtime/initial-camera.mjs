export function resolveInitialCamera(viewport, bounds, size, padding = {}) {
  if (!Number.isFinite(size.width) || !Number.isFinite(size.height) || size.width <= 0 || size.height <= 0)
    throw Object.assign(new Error('地图容器暂不可见，无法计算初始视野'), { code: 'NO_MAP_SIZE' });
  if (viewport.strategy === 'fixed-camera' || viewport.strategy === 'focus-element')
    return { center: [...viewport.center], zoom: viewport.zoom ?? 15, source: viewport.strategy };
  if (viewport.strategy === 'focus-radius')
    return {
      center: [...viewport.center],
      zoom: Math.max(3, Math.min(20, Math.round(16 - Math.log2(viewport.radiusMeters / 500)))),
      source: viewport.strategy,
    };
  if (!bounds) return { center: [0, 0], zoom: 2, source: 'empty-world' };
  const projectLatitude = latitude => {
    const radians = Math.max(-85, Math.min(85, latitude)) * Math.PI / 180;
    return (1 - Math.log(Math.tan(Math.PI / 4 + radians / 2)) / Math.PI) / 2;
  };
  const west = (bounds.southwest[0] + 180) / 360;
  let east = (bounds.northeast[0] + 180) / 360;
  if (east < west) east += 1;
  const north = projectLatitude(bounds.northeast[1]);
  const south = projectLatitude(bounds.southwest[1]);
  const inset = { left: 0, right: 0, top: 0, bottom: 0, ...padding };
  const width = size.width - inset.left - inset.right;
  const height = size.height - inset.top - inset.bottom;
  if (width <= 0 || height <= 0)
    throw Object.assign(new Error('浮层占满了可用地图区域，请收起面板后全览'), { code: 'NO_SAFE_VIEWPORT' });
  const zoom = Math.max(2, Math.min(
    viewport.maxZoom ?? 18,
    east === west ? Infinity : Math.log2(width / (256 * (east - west))),
    south === north ? Infinity : Math.log2(height / (256 * (south - north))),
  ));
  const scale = 256 * 2 ** zoom;
  const centerX = (west + east) / 2 - (inset.left - inset.right) / (2 * scale);
  const centerY = (north + south) / 2 - (inset.top - inset.bottom) / (2 * scale);
  return {
    center: [((centerX * 360) % 360 + 360) % 360 - 180,
      Math.atan(Math.sinh(Math.PI * (1 - 2 * centerY))) * 180 / Math.PI],
    zoom,
    source: 'visible-elements',
  };
}
