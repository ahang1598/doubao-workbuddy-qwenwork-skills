export function applyCompiledAppearance(graph, hostTone, systemDark) {
  if (graph.visualTheme.mode !== 'auto') return graph.visualTheme.shell.tone;
  const tone = ['light', 'dark'].includes(hostTone)
    ? hostTone
    : systemDark
      ? 'dark'
      : 'light';
  const appearances = graph.visualTheme.appearances;
  const appearance = appearances?.[tone];
  if (!appearance) throw new Error('THEME_APPEARANCE_MISSING');
  for (const element of graph.elements) {
    const presentation = appearance.elementPresentation[element.id];
    if (!presentation) throw new Error('THEME_ELEMENT_MISSING');
    Object.assign(element.props, structuredClone(presentation));
  }
  for (const view of graph.views) {
    if (appearance.viewUi[view.id] !== undefined)
      view.ui = structuredClone(appearance.viewUi[view.id]);
  }
  graph.tokens = structuredClone(appearance.tokens);
  graph.visualTheme = {
    ...structuredClone(appearance.visualTheme),
    appearances,
  };
  return tone;
}
