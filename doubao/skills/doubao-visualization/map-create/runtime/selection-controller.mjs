export function createSelectionController(context) {
  const selectElement = (elementId, options = {}) => {
    const current = context.read();
    if (elementId === null && options.source === 'detail-close' && current.seriesId && context.element(current.elementId)?.businessRef?.type !== 'route') {
      const route = context.elements().find(item => item.businessRef?.type === 'route' && item.seriesId === current.seriesId && context.visible(item.id) && item.props.interaction?.selectable !== false);
      if (route) elementId = route.id;
    }
    if (
      elementId !== null &&
      elementId === current.elementId &&
      ['map', 'ui'].includes(options.source)
    )
      elementId = null;
    const element = elementId === null ? null : context.element(elementId);
    if (
      elementId !== null &&
      (!element ||
        !context.visible(elementId) ||
        element.props.interaction?.selectable === false)
    )
      return false;
    context.commit({
      elementId,
      seriesId:
        element?.businessRef?.type === 'route'
          ? element.seriesId || null
          : element?.relatedSeriesIds?.includes(current.seriesId)
            ? current.seriesId
            : null,
      reason: elementId ? 'element-select' : 'element-clear',
    });
    return true;
  };
  const selectSeries = (seriesId, options = {}) => {
    if (
      seriesId === null ||
      (seriesId === context.read().seriesId &&
        ['map', 'ui'].includes(options.source))
    )
      return selectElement(null);
    if (!context.view().legendSeriesIds?.includes(seriesId)) return false;
    const representative = context
      .elements()
      .find(
        element =>
          context.visible(element.id) &&
          element.seriesId === seriesId &&
          element.props?.interaction?.selectable !== false,
      );
    if (!representative) return false;
    context.commit({
      elementId: representative.id,
      seriesId,
      reason: 'series-select',
    });
    return true;
  };
  return { selectElement, selectSeries };
}
