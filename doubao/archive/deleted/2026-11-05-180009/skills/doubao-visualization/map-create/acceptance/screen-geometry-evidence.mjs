// Independent SVG evidence. Do not consume the Runtime's safeRect, projected
// bounds or claimed outside list as verification truth. Native 3D and continuous
// raster coverage have separate evidence paths; this check does not certify them.
export function inspectScreenGeometry({ phase = 'current' } = {}) {
  const graph = window.mapCreateEvidenceGraph || window.mapCreateGraph;
  const state = window.mapCreateState;
  const view = graph.views.find(item => item.id === state.activeViewId);
  const result = {
    status: 'legacy',
    phase,
    elements: [],
    reservations: [],
    errors: [],
  };
  if (
    !graph.runtimeRequirements?.capabilities?.includes(
      'layout.screen-geometry@1',
    )
  )
    return result;
  const requiresFit =
    view.viewport.strategy === 'fit-elements' &&
    view.viewport.fitOnActivate !== false &&
    phase !== 'interaction' &&
    (phase === 'initial' || state.cameraContext?.follow !== false);
  const scope = new Set(view.viewport.elementIds || view.elementIds);
  const mapBox = document.querySelector('#map').getBoundingClientRect();
  for (const selector of [
    '#map-controls',
    '#map-legend',
    '#selection-details',
    '#content-map-ui',
    '#map-sources',
    '#heatmap-controls',
    '.amap-logo',
    '.amap-copyright',
  ]) {
    for (const node of document.querySelectorAll(selector)) {
      const style = getComputedStyle(node),
        box = node.getBoundingClientRect();
      if (
        node.hidden ||
        style.display === 'none' ||
        style.visibility === 'hidden' ||
        !box.width ||
        !box.height
      )
        continue;
      const rect = {
        left: Math.max(box.left, mapBox.left),
        top: Math.max(box.top, mapBox.top),
        right: Math.min(box.right, mapBox.right),
        bottom: Math.min(box.bottom, mapBox.bottom),
      };
      if (rect.right > rect.left && rect.bottom > rect.top)
        result.reservations.push({ selector, ...rect });
    }
  }
  const drawing = [...document.querySelectorAll('#map [data-element-id]')];
  const edgeNavigation = graph.runtimeRequirements.capabilities.includes(
    'ui.edge-navigation@1',
  );
  const overlaps = (left, right) =>
    left.left < right.right &&
    left.right > right.left &&
    left.top < right.bottom &&
    left.bottom > right.top;
  const contentIsVisible = bounds => {
    let fragments = [
      {
        left: Math.max(bounds.left, mapBox.left),
        right: Math.min(bounds.right, mapBox.right),
        top: Math.max(bounds.top, mapBox.top),
        bottom: Math.min(bounds.bottom, mapBox.bottom),
      },
    ].filter(rect => rect.right > rect.left && rect.bottom > rect.top);
    for (const obstacle of result.reservations) {
      fragments = fragments.flatMap(rect => {
        if (!overlaps(rect, obstacle)) return [rect];
        const left = Math.max(rect.left, obstacle.left);
        const right = Math.min(rect.right, obstacle.right);
        const top = Math.max(rect.top, obstacle.top);
        const bottom = Math.min(rect.bottom, obstacle.bottom);
        return [
          { ...rect, bottom: top },
          { ...rect, top: bottom },
          { left: rect.left, right: left, top, bottom },
          { left: right, right: rect.right, top, bottom },
        ].filter(part => part.right > part.left && part.bottom > part.top);
      });
    }
    return fragments.length > 0;
  };
  const drawingBoxes = node =>
    [
      ...node.querySelectorAll(
        'path, polyline, line, rect, circle, ellipse, text, image',
      ),
    ].flatMap(shape => {
      const style = getComputedStyle(shape);
      if (
        style.display === 'none' ||
        style.visibility === 'hidden' ||
        Number(style.opacity) === 0
      )
        return [];
      const rect = shape.getBoundingClientRect();
      const matrix = shape.getScreenCTM();
      const width = parseFloat(style.strokeWidth) || 0;
      const stroke =
        style.stroke !== 'none' &&
        Number(style.strokeOpacity) !== 0 &&
        width > 0;
      if (
        !matrix ||
        !stroke ||
        style.fill !== 'none' ||
        typeof shape.getTotalLength !== 'function'
      )
        return rect.width || rect.height ? [rect] : [];
      const length = shape.getTotalLength();
      const scale = Math.max(
        Math.hypot(matrix.a, matrix.b),
        Math.hypot(matrix.c, matrix.d),
      );
      const count = Math.max(
        1,
        Math.min(20000, Math.ceil((length * scale) / 2)),
      );
      const radius =
        (width / 2) * (style.vectorEffect === 'non-scaling-stroke' ? 1 : scale);
      const project = distance => {
        const point = shape.getPointAtLength(distance);
        return {
          x: matrix.a * point.x + matrix.c * point.y + matrix.e,
          y: matrix.b * point.x + matrix.d * point.y + matrix.f,
        };
      };
      const boxes = [];
      let previous = project(0);
      for (let index = 1; index <= count; index++) {
        const next = project((length * index) / count);
        boxes.push({
          left: Math.min(previous.x, next.x) - radius,
          right: Math.max(previous.x, next.x) + radius,
          top: Math.min(previous.y, next.y) - radius,
          bottom: Math.max(previous.y, next.y) + radius,
        });
        previous = next;
      }
      return boxes;
    });
  const geometryAccess = (node, element) => {
    const evidence = { painted: false, clickable: false, hit: null };
    const testPoint = (shape, matrix, point) => {
      const screen = point.matrixTransform(matrix);
      if (
        screen.x < mapBox.left || screen.x >= mapBox.right ||
        screen.y < mapBox.top || screen.y >= mapBox.bottom ||
        result.reservations.some(rect =>
          screen.x >= rect.left && screen.x <= rect.right &&
          screen.y >= rect.top && screen.y <= rect.bottom)
      ) return;
      const style = getComputedStyle(shape);
      const painted =
        (style.fill !== 'none' && Number(style.fillOpacity) > 0 && shape.isPointInFill(point)) ||
        (style.stroke !== 'none' && Number(style.strokeOpacity) > 0 && shape.isPointInStroke(point));
      if (!painted) return;
      evidence.painted = true;
      const top = document.elementFromPoint(screen.x, screen.y);
      const topId = top?.closest('[data-element-id]')?.getAttribute('data-element-id');
      if (top?.closest('#map') && (!topId || topId === element.id)) {
        evidence.clickable = true;
        evidence.hit = { x: screen.x, y: screen.y };
      }
    };
    for (const shape of node.querySelectorAll('path, polyline, polygon, line')) {
      const style = getComputedStyle(shape);
      const matrix = shape.getScreenCTM();
      if (!matrix || style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) continue;
      const box = shape.getBoundingClientRect();
      const left = Math.max(box.left, mapBox.left), right = Math.min(box.right, mapBox.right);
      const top = Math.max(box.top, mapBox.top), bottom = Math.min(box.bottom, mapBox.bottom);
      if (right < left || bottom < top) continue;
      if (style.fill !== 'none' && Number(style.fillOpacity) > 0) {
        for (const horizontal of [0.5, 0.25, 0.75, 0.1, 0.9]) {
          for (const vertical of [0.5, 0.25, 0.75, 0.1, 0.9]) {
            const point = new DOMPoint(left + (right - left) * horizontal, top + (bottom - top) * vertical).matrixTransform(matrix.inverse());
            testPoint(shape, matrix, point);
            if (evidence.clickable) return evidence;
          }
        }
      }
      const length = shape.getTotalLength();
      const samples = Math.max(1, Math.min(20000, Math.ceil(length * Math.max(Math.hypot(matrix.a, matrix.b), Math.hypot(matrix.c, matrix.d)) / 2)));
      for (let index = 0; index <= samples; index++) {
        const point = shape.getPointAtLength(length * index / samples);
        testPoint(shape, matrix, new DOMPoint(point.x, point.y));
        if (evidence.clickable) return evidence;
      }
    }
    return evidence;
  };
  for (const element of window.mapCreateRuntime.layer.getElements()) {
    if (element.visible === false || !scope.has(element.id)) continue;
    if (element.type === 'heatmap' && element.mode !== 'hexbin') continue;
    const required = requiresFit && scope.has(element.id);
    const node = drawing.find(item => item.dataset.elementId === element.id);
    const emptyAnalysis =
      element.type === 'heatmap' &&
      (!element.points.length || element.filter?.pointIds?.length === 0);
    if (emptyAnalysis) continue;
    if (!node) {
      result.errors.push(`${element.id} 缺少实际 SVG 绘制节点`);
      continue;
    }
    let box = node.getBoundingClientRect();
    if (!box.width || !box.height) {
      const strokes = [
        ...node.querySelectorAll('path, polyline, line'),
      ].flatMap(path => {
        const style = getComputedStyle(path);
        const matrix = path.getScreenCTM();
        const width = parseFloat(style.strokeWidth);
        if (
          !matrix ||
          style.display === 'none' ||
          style.visibility === 'hidden' ||
          style.stroke === 'none' ||
          Number(style.strokeOpacity) === 0 ||
          Number(style.opacity) === 0 ||
          !(width > 0) ||
          !(path.getTotalLength() > 0)
        )
          return [];
        const rect = path.getBoundingClientRect();
        const fixed = style.vectorEffect === 'non-scaling-stroke';
        const offsetX =
          (width / 2) * (fixed ? 1 : Math.hypot(matrix.a, matrix.c));
        const offsetY =
          (width / 2) * (fixed ? 1 : Math.hypot(matrix.b, matrix.d));
        return [
          {
            left: rect.left - offsetX,
            right: rect.right + offsetX,
            top: rect.top - offsetY,
            bottom: rect.bottom + offsetY,
          },
        ];
      });
      if (strokes.length) {
        const left = Math.min(...strokes.map(rect => rect.left));
        const right = Math.max(...strokes.map(rect => rect.right));
        const top = Math.min(...strokes.map(rect => rect.top));
        const bottom = Math.max(...strokes.map(rect => rect.bottom));
        box = {
          left,
          right,
          top,
          bottom,
          width: right - left,
          height: bottom - top,
        };
      }
    }
    const hidden =
      getComputedStyle(node).display === 'none' ||
      getComputedStyle(node).visibility === 'hidden' ||
      Number(getComputedStyle(node).opacity) === 0 || !box.width || !box.height;
    const parts = hidden ? [] : drawingBoxes(node);
    const actualBoxes = parts.length ? parts : [box];
    const outside = actualBoxes.some(
      part =>
        part.left < mapBox.left ||
        part.right > mapBox.right ||
        part.top < mapBox.top ||
        part.bottom > mapBox.bottom,
    );
    const obstructedBy = hidden
      ? []
      : result.reservations
          .filter(rect => actualBoxes.some(part => overlaps(part, rect)))
          .map(rect => rect.selector);
    let viewportAccess = null;
    let geometryEvidence = null;
    if (!element.position && element.type !== 'heatmap' && !hidden) {
      geometryEvidence = geometryAccess(node, element);
      if (geometryEvidence.painted && (element.interaction?.selectable === false || geometryEvidence.clickable))
        viewportAccess = ['polygon', 'circle'].includes(element.type) ? 'visible-area' : 'visible-line';
    }
    if (edgeNavigation && element.position && !hidden) {
      const labels = [
        ...node.querySelectorAll(
          'text[data-part="label"], [data-part="label"] text',
        ),
      ]
        .map(label => label.getBoundingClientRect())
        .filter(rect => rect.width && rect.height);
      const readable = labels.length ? labels : actualBoxes;
      const titleVisible = readable.some(rect => overlaps(rect, mapBox));
      const contentVisible = [
        ...node.querySelectorAll(
          '[data-part="anchor"], [data-part="icon"], [data-part="label"], [data-part="description"], [data-part="body"]',
        ),
      ].some(part => {
        const style = getComputedStyle(part);
        return (
          style.display !== 'none' &&
          style.visibility !== 'hidden' &&
          Number(style.opacity) !== 0 &&
          contentIsVisible(part.getBoundingClientRect())
        );
      });
      let clickable = false;
      for (const rect of readable) {
        const left = Math.max(rect.left, mapBox.left),
          right = Math.min(rect.right, mapBox.right);
        const top = Math.max(rect.top, mapBox.top),
          bottom = Math.min(rect.bottom, mapBox.bottom);
        if (right <= left || bottom <= top) continue;
        for (const horizontal of [0.25, 0.5, 0.75])
          for (const vertical of [0.25, 0.5, 0.75])
            if (
              document
                .elementFromPoint(
                  left + (right - left) * horizontal,
                  top + (bottom - top) * vertical,
                )
                ?.closest('[data-element-id]')
                ?.getAttribute('data-element-id') === element.id
            )
              clickable = true;
        if (clickable) break;
      }
      const sign = [
        ...document.querySelectorAll('.content-map-kit-edge-sign'),
      ].find(
        button =>
          JSON.parse(button.dataset.edgeIds || '[]').includes(element.id) &&
          !button.closest('[hidden]'),
      );
      if (sign && contentVisible)
        result.errors.push(`${element.id} 内容部分可见却被计入方向签`);
      if (titleVisible && clickable) {
        viewportAccess = 'visible';
      } else if (!contentVisible && sign) viewportAccess = 'direction-entry';
      if (!viewportAccess && contentVisible) {
        for (const part of actualBoxes) {
          const left = Math.max(part.left, mapBox.left);
          const right = Math.min(part.right, mapBox.right);
          const top = Math.max(part.top, mapBox.top);
          const bottom = Math.min(part.bottom, mapBox.bottom);
          if (right <= left || bottom <= top) continue;
          for (const horizontal of [0.25, 0.5, 0.75])
            for (const vertical of [0.25, 0.5, 0.75])
              if (document.elementFromPoint(
                left + (right - left) * horizontal,
                top + (bottom - top) * vertical,
              )?.closest('[data-element-id]')?.getAttribute('data-element-id') === element.id)
                viewportAccess = 'visible-symbol';
          if (viewportAccess) break;
        }
      }
    }
    const pointAccessRequired = edgeNavigation && Boolean(element.position);
    if (
      (pointAccessRequired || (required &&
      (hidden || outside || obstructedBy.length || (geometryEvidence && !viewportAccess)))) &&
      !viewportAccess
    )
      result.errors.push(
        `VIEWPORT_ACCESS_FAILED: ${element.id} 全览绘制范围${hidden ? '不可见' : outside ? '越界且不可访问' : '缺少可访问的实际绘制证据'}`,
      );
    result.elements.push({
      elementId: element.id,
      hidden,
      outside,
      obstructedBy,
      coverageRequired: required,
      pointAccessRequired,
      viewportAccess,
      geometryEvidence,
    });
  }
  if (
    requiresFit &&
    result.elements.length &&
    state.fitState?.outcome !== 'applied'
  )
    result.errors.push('二维全览尚未完成');
  result.status = result.errors.length ? 'failed' : 'passed';
  return result;
}
