// Browser-side evidence: polygon fills and borders may be separate SVG paths.
// Match their actual closed rings; never borrow a border from another polygon.
export function inspectPolygons(viewId) {
  const graph = window.mapCreateEvidenceGraph || window.mapCreateGraph;
  const view = graph.views.find(item => item.id === viewId);
  const drawing = [...document.querySelectorAll('#map [data-element-id]')];
  const alpha = color => {
    if (!color || color === 'none' || color === 'transparent') return 0;
    const match = color.match(/^rgba\([^,]+,[^,]+,[^,]+,\s*([\d.]+)\)$/);
    return match ? Number(match[1]) : 1;
  };
  const inspect = path => {
    const style = getComputedStyle(path),
      matrix = path.getScreenCTM();
    let opacity = 1;
    for (let node = path; node instanceof Element; node = node.parentElement) {
      const css = getComputedStyle(node);
      if (
        css.display === 'none' ||
        ['hidden', 'collapse'].includes(css.visibility)
      )
        opacity = 0;
      opacity *= Number(css.opacity);
    }
    const rect = path.getBoundingClientRect();
    if (!matrix || !rect.width || !rect.height || !(path.getTotalLength() > 0))
      opacity = 0;
    // The locked polygon renderer emits M/L/Z rings, including hole subpaths.
    // Compare screen coordinates so transforms cannot disguise an unrelated border.
    const rings = (path.getAttribute('d') || '').match(/M[^M]*/gi) || [];
    const keys = rings.map(ring => {
      if (
        !/z\s*$/i.test(ring) ||
        /[a-kno-y]/i.test(ring.replace(/e[+-]?\d+/gi, ''))
      )
        return null;
      const values =
        ring
          .match(/[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:e[-+]?\d+)?/gi)
          ?.map(Number) || [];
      if (values.length < 6 || values.length % 2 || !matrix) return null;
      const points = [];
      for (let i = 0; i < values.length; i += 2) {
        const p = new DOMPoint(values[i], values[i + 1]).matrixTransform(
          matrix,
        );
        points.push(`${p.x.toFixed(3)},${p.y.toFixed(3)}`);
      }
      if (points[0] === points.at(-1)) points.pop();
      return points.length >= 3 ? points.join(';') : null;
    });
    const scale = !matrix
      ? 0
      : style.vectorEffect === 'non-scaling-stroke'
        ? 1
        : Math.min(
            Math.hypot(matrix.a, matrix.b),
            Math.hypot(matrix.c, matrix.d),
          );
    return {
      keys,
      hasFill: alpha(style.fill) > 0,
      fillOpacity: opacity * Number(style.fillOpacity) * alpha(style.fill),
      strokeOpacity:
        opacity * Number(style.strokeOpacity) * alpha(style.stroke),
      strokeWidth: parseFloat(style.strokeWidth) * scale,
    };
  };
  return (view?.elementIds || [])
    .map(id => graph.elements.find(item => item.id === id))
    .filter(element => ['polygon', 'circle'].includes(element?.rendererType))
    .map(element => {
      const nodes = drawing.filter(
        node => node.dataset.elementId === element.id,
      );
      const paths = nodes
        .flatMap(node => [...node.querySelectorAll('path')])
        .map(inspect);
      const fills = paths.filter(path => path.hasFill);
      const polygons = element.rendererType === 'circle'
        ? [[window.ContentMapKit.getCircleRing(element.props.center, element.props.radiusMeters)]]
        : element.props.polygons;
      const errors = [];
      if (fills.length !== polygons.length)
        errors.push(
          `填充面数量不符：预期 ${polygons.length}，实际 ${fills.length}`,
        );
      const parts = polygons.map((rings, polygonIndex) => {
        const fill = fills[polygonIndex];
        const fillOpacity = fill?.fillOpacity || 0;
        const borders = rings.map((_, ringIndex) => {
          const key = fill?.keys[ringIndex];
          const matches = key
            ? paths.filter(
                path => path.strokeOpacity > 0 && path.keys.includes(key),
              )
            : [];
          const strokeWidth = Math.max(
            0,
            ...matches.map(path => path.strokeWidth),
          );
          if (strokeWidth < 1.5)
            errors.push(
              `第 ${polygonIndex + 1} 个面${ringIndex ? `的孔洞 ${ringIndex}` : '的外边界'}不可感知：对应可见描边宽度 ${strokeWidth}px，要求 ≥1.5px`,
            );
          return { ringIndex, strokeWidth };
        });
        if (
          !fill ||
          fill.keys.length !== rings.length ||
          fill.keys.some(key => !key)
        )
          errors.push(
            `第 ${polygonIndex + 1} 个面的闭环结构无法匹配：预期 ${rings.length} 个环，实际 ${fill?.keys.length || 0}`,
          );
        if (fillOpacity < 0.12)
          errors.push(
            `第 ${polygonIndex + 1} 个面的填充不可感知：有效透明度 ${fillOpacity}，要求 ≥0.12`,
          );
        return { polygonIndex, fillOpacity, borders };
      });
      return {
        id: element.id,
        status: errors.length ? 'failed' : 'passed',
        pathCount: paths.length,
        parts,
        errors,
      };
    });
}
