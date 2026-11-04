export function sanitizeTelemetryError(error, unhandled = false) {
  try {
    const names = [
      'TypeError',
      'ReferenceError',
      'RangeError',
      'SyntaxError',
      'EvalError',
      'URIError',
      'AggregateError',
    ];
    const name = error?.name;
    if (!names.includes(name) && !(unhandled && name === 'Error')) return null;
    if (typeof error.stack !== 'string') return null;
    const message = String(error.message || '');
    if (
      /^(?:Failed to fetch|fetch failed|Load failed|NetworkError when attempting to fetch resource\.)$/i.test(
        message,
      )
    )
      return null;
    if (name === 'Error' && /^[A-Z][A-Z0-9_]{2,79}(?=[:\s]|$)/.test(message))
      return null;
    const frames = [];
    for (const line of error.stack.slice(0, 16384).split('\n').slice(1, 33)) {
      const location = line.match(/:(\d{1,7}):(\d{1,7})\)?\s*$/);
      if (!location) continue;
      const module = line.match(
        /(?:\/|\\|\()(bootstrap\.js|browser-runtime\.js|create-map\.mjs|map-workflow\.mjs|map\.html)(?=[:?#])/,
      );
      frames.push(
        `    at <redacted> (${module?.[1] || '<redacted>'}:${location[1]}:${location[2]})`,
      );
      if (frames.length === 12) break;
    }
    return {
      name,
      message: `${name}: details redacted`,
      stack: [`${name}: details redacted`, ...frames].join('\n'),
    };
  } catch {
    return null;
  }
}
