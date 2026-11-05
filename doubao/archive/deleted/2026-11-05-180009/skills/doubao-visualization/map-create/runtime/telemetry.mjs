export function installMapTelemetry(config, sanitizeError) {
  if (
    window.mapCreateTelemetryDisabled ||
    config.env !== 'production' ||
    config.disabled
  )
    return;
  const randomId = () =>
    crypto.randomUUID
      ? crypto.randomUUID()
      : Array.from(crypto.getRandomValues(new Uint8Array(16)), value =>
          value.toString(16).padStart(2, '0'),
        ).join('');
  const renderId = randomId();
  const userAgent = navigator.userAgent || '';
  const platform =
    /iPhone|iPad|iPod/.test(userAgent) ||
    (/Macintosh/.test(userAgent) && navigator.maxTouchPoints > 1)
      ? 'ios'
      : /Android/.test(userAgent)
        ? 'android'
        : /Windows|Macintosh|Linux/.test(userAgent)
          ? 'desktop'
          : 'unknown';
  const browser = /Edg\//.test(userAgent)
    ? 'edge'
    : /Chrome\//.test(userAgent)
      ? 'chrome'
      : /Firefox\//.test(userAgent)
        ? 'firefox'
        : /Safari\//.test(userAgent)
          ? 'safari'
          : 'unknown';
  const modes = ['user', 'screenshot', 'acceptance', 'dev'];
  const mode = modes.includes(window.mapCreateTelemetryMode)
    ? window.mapCreateTelemetryMode
    : 'unknown';
  if (mode === 'acceptance' || mode === 'dev') return;
  const pageviewEnabled = mode !== 'screenshot';
  let pageviewSent = false;
  let attempt = 1;
  let started = performance.now();
  let terminal = null;
  let client;
  let trustedAt = -Infinity;
  let source = 'map';
  const queue = [];
  const errors = new Set();
  const exceptions = new Set();
  const approvedExceptions = new Map();
  const interactions = new Map();
  const failures = new WeakMap();
  const failureEvents = new Set();
  let operation = 'initialize';
  const operations = [
    'initialize',
    'switch_view',
    'select_object',
    'clear_selection',
    'locate_object',
    'pan_map',
    'zoom_map',
    'toggle_panel',
    'toggle_children',
    'toggle_visibility',
    'render',
    'camera',
    'layout',
    'cleanup',
    'unknown',
  ];
  const failureId = error => {
    if (!error || typeof error !== 'object') return randomId();
    if (failures.get(error)?.attempt !== attempt)
      failures.set(error, { attempt, id: randomId() });
    return failures.get(error).id;
  };
  const failureFields = error => {
    const id = failureId(error);
    const fields = {
      failure_id: id,
      event_id: failureEvents.has(id) ? randomId() : id,
    };
    failureEvents.add(id);
    return fields;
  };
  const stages = [
    'bootstrap',
    'manifest',
    'data',
    'style',
    'components',
    'resources',
    'container-size',
    'content-layer',
    'runtime',
    'amap-sdk',
    'amap-map',
    'layout',
    'ready',
  ];
  const stage = () =>
    stages.includes(document.documentElement.dataset.bootstrapPhase)
      ? document.documentElement.dataset.bootstrapPhase
      : 'unknown';
  const code = value =>
    String(value || '').match(/^[A-Z][A-Z0-9_]{2,79}(?=[:\s]|$)/)?.[0] ||
    'UNKNOWN_ERROR';
  const deliver = event => {
    if (!event.exception) return client('sendEvent', event);
    const payload = {
      error: event.exception,
      breadcrumbs: [],
      extra: { ...event.categories, ...event.metrics },
    };
    approvedExceptions.set(event.categories.event_id, payload);
    client('report', { ev_type: 'js_error', payload });
  };
  const emit = (name, fields = {}, exception) => {
    try {
      const event = {
        name,
        categories: {
          event_id: randomId(),
          trace_id: config.trace_id,
          map_id: config.map_id,
          artifact_id: config.artifact_id,
          render_id: renderId,
          producer: 'html',
          env: config.env,
          skill_version: config.skill_version,
          runtime_version: config.runtime_version,
          component_version: config.component_version,
          execution_mode: mode,
          runtime_platform: platform,
          platform_source: 'ua',
          browser_name: browser,
        },
        metrics: {
          schema_version: 1,
          event_time: Date.now(),
          attempt_no: attempt,
        },
      };
      for (const [key, value] of Object.entries(fields)) {
        if (typeof value === 'number') event.metrics[key] = value;
        else event.categories[key] = String(value);
      }
      if (exception) event.exception = exception;
      if (client) deliver(event);
      else if (queue.length < 128) queue.push(event);
      else document.documentElement.dataset.telemetryState = 'queue-full';
      return event.categories.event_id;
    } catch {
      document.documentElement.dataset.telemetryState = 'unavailable';
    }
  };
  const runtimeError = (
    errorCode,
    fatal = false,
    error,
    action = operation,
  ) => {
    if (terminal !== 'ready') return;
    const safeCode = code(errorCode);
    const safeOperation = operations.includes(action) ? action : 'unknown';
    const safe = sanitizeError?.(error, true);
    const key = `${attempt}:${safeOperation}:${safeCode}:${safe?.stack || ''}`;
    if (errors.has(key) || errors.size >= 20) return;
    errors.add(key);
    emit('map_runtime_error', {
      ...failureFields(error),
      stage: stage(),
      operation: safeOperation,
      error_code: safeCode,
      fatal,
    });
    exception(error, true, fatal, safeOperation);
  };
  const exception = (
    error,
    unhandled = false,
    fatal = false,
    action = operation,
  ) => {
    if (typeof sanitizeError !== 'function') return;
    const safe = sanitizeError(error, unhandled);
    if (!safe) return;
    const safeOperation = operations.includes(action) ? action : 'unknown';
    const key = `${attempt}:${safeOperation}:${safe.stack}`;
    if (exceptions.has(key) || exceptions.size >= 20) return;
    exceptions.add(key);
    emit(
      'map_code_exception',
      {
        ...failureFields(error),
        stage: stage(),
        operation: safeOperation,
        fatal,
      },
      safe,
    );
  };
  window.mapCreateTelemetry = {
    begin(nextAttempt) {
      attempt = nextAttempt;
      terminal = null;
      started = performance.now();
      operation = 'initialize';
      emit('map_load_started', {
        trigger: attempt === 1 ? 'initial' : 'retry',
      });
    },
    ready() {
      if (terminal) return;
      terminal = 'ready';
      emit('map_init_succeeded', {
        duration_ms: Math.round(performance.now() - started),
      });
    },
    fail(errorCode, retryable, error) {
      if (terminal === 'ready') {
        runtimeError(errorCode, true, error);
        terminal = 'error';
        return;
      }
      if (terminal) return;
      terminal = 'error';
      emit('map_load_failed', {
        ...failureFields(error),
        stage: stage(),
        error_code: code(errorCode),
        retryable,
        duration_ms: Math.round(performance.now() - started),
      });
      exception(error, false, true);
    },
    retry(errorCode) {
      emit('map_retry_clicked', {
        error_code: code(errorCode),
        next_attempt_no: attempt + 1,
      });
    },
    error: runtimeError,
    exception,
    operation(action) {
      operation = operations.includes(action) ? action : 'unknown';
    },
    resource(kind) {
      if (
        ![
          'bootstrap',
          'data',
          'style',
          'components',
          'runtime',
          'amap-sdk',
        ].includes(kind)
      )
        return () => {};
      const begin = performance.now();
      const loadId = randomId();
      const loadAttempt = attempt;
      let finished = false;
      return (error, details = {}) => {
        if (finished) return;
        finished = true;
        const cancelled = details.cancelled || attempt !== loadAttempt;
        emit('map_resource_load_finished', {
          resource_load_id: loadId,
          attempt_no: loadAttempt,
          resource_type: kind,
          status: cancelled ? 'cancelled' : error ? 'failed' : 'succeeded',
          duration_ms: Math.round(performance.now() - begin),
          ...(error && !cancelled
            ? {
                ...failureFields(error),
                error_code: code(error.code || error.message),
              }
            : {}),
          ...(Number.isInteger(details.httpStatus)
            ? { http_status: details.httpStatus }
            : {}),
        });
      };
    },
    interaction(action, actionSource) {
      const allowed = [
        'switch_view',
        'select_object',
        'clear_selection',
        'locate_object',
        'pan_map',
        'zoom_map',
        'toggle_panel',
        'toggle_children',
        'toggle_visibility',
      ];
      if (
        terminal !== 'ready' ||
        performance.now() - trustedAt > 3000 ||
        !allowed.includes(action)
      )
        return;
      const previous = interactions.get(action) || -Infinity;
      if (performance.now() - previous < 400) return;
      interactions.set(action, performance.now());
      emit('map_interaction', {
        action,
        source: ['map', 'sidebar', 'toolbar'].includes(actionSource)
          ? actionSource
          : source,
      });
    },
    connect(createClient) {
      if (client) return;
      try {
        const candidate = createClient();
        candidate('init', {
          bid: 'lbs_map_create_skill',
          env: config.env,
          pid: 'map-create',
          release: config.runtime_version,
          userId: renderId,
          deviceId: renderId,
          sessionId: renderId,
          storageExpires: false,
          plugins: {
            ...Object.fromEntries(
              [
                'ajax',
                'fetch',
                'breadcrumb',
                'jsError',
                'resource',
                'resourceError',
                'performance',
                'tti',
                'fmp',
                'blankScreen',
                'heatmap',
                'action',
              ].map(name => [name, false]),
            ),
            pageview: pageviewEnabled
              ? { sendInit: true, routeMode: 'manual', apdex: 0 }
              : false,
          },
        });
        const names = new Set([
          'map_load_started',
          'map_init_succeeded',
          'map_load_failed',
          'map_retry_clicked',
          'map_runtime_error',
          'map_interaction',
          'map_resource_load_finished',
        ]);
        candidate.on('beforeSend', event => {
          const isPageview =
            event.ev_type === 'pageview' &&
            pageviewEnabled &&
            !pageviewSent &&
            event.payload?.source === 'init' &&
            event.payload?.pid === 'map-create';
          const safeException =
            event.ev_type === 'js_error'
              ? approvedExceptions.get(event.payload?.extra?.event_id)
              : null;
          if (
            !isPageview &&
            !safeException &&
            (event.ev_type !== 'custom' || !names.has(event.payload?.name))
          )
            return false;
          if (isPageview) pageviewSent = true;
          return {
            ev_type: isPageview
              ? 'pageview'
              : safeException
                ? 'js_error'
                : 'custom',
            payload: isPageview
              ? { pid: 'map-create', source: 'init' }
              : safeException || event.payload,
            common: {
              bid: 'lbs_map_create_skill',
              pid: 'map-create',
              env: config.env,
              release: config.runtime_version,
              user_id: renderId,
              device_id: renderId,
              session_id: renderId,
              view_id: renderId,
              sdk_name: event.common?.sdk_name,
              sdk_version: event.common?.sdk_version,
              timestamp: isPageview
                ? event.common?.timestamp || Date.now()
                : safeException?.extra.event_time ||
                  event.payload?.metrics?.event_time,
              sample_rate: event.common?.sample_rate,
              ...(isPageview
                ? {
                    context: {
                      event_id: randomId(),
                      trace_id: config.trace_id,
                      map_id: config.map_id,
                      artifact_id: config.artifact_id,
                      render_id: renderId,
                      producer: 'html',
                      schema_version: '1',
                      skill_version: config.skill_version,
                      runtime_version: config.runtime_version,
                      component_version: config.component_version,
                      execution_mode: mode,
                      runtime_platform: platform,
                      platform_source: 'ua',
                      browser_name: browser,
                    },
                  }
                : safeException
                  ? {
                      context: Object.fromEntries(
                        Object.entries(safeException.extra).map(
                          ([key, value]) => [key, String(value)],
                        ),
                      ),
                    }
                  : {}),
            },
          };
        });
        candidate('start');
        client = candidate;
        document.documentElement.dataset.telemetryState = 'connected';
        while (queue.length) deliver(queue.shift());
      } catch {
        document.documentElement.dataset.telemetryState = 'unavailable';
      }
    },
  };
  for (const type of ['pointerdown', 'pointerup', 'click', 'keydown', 'wheel'])
    document.addEventListener(
      type,
      event => {
        if (!event.isTrusted) return;
        trustedAt = performance.now();
        source = event.target?.closest?.('#content-map-ui')
          ? 'sidebar'
          : event.target?.closest?.('#map-controls')
            ? 'toolbar'
            : 'map';
      },
      { capture: true, passive: true },
    );
  window.addEventListener('error', event => {
    if (event.error) {
      runtimeError('UNCAUGHT_JS_ERROR', false, event.error);
      exception(event.error, true);
    }
  });
  document.addEventListener(
    'click',
    event => {
      if (!event.isTrusted) return;
      const button = event.target?.closest?.(
        '.content-map-kit-relation-toggle, .content-map-kit-panel-button[aria-expanded]',
      );
      if (!button) return;
      const expanded = button.getAttribute('aria-expanded');
      const observer = new MutationObserver(() => {
        if (button.getAttribute('aria-expanded') === expanded) return;
        observer.disconnect();
        window.mapCreateTelemetry.interaction(
          button.classList.contains('content-map-kit-relation-toggle')
            ? 'toggle_children'
            : 'toggle_panel',
          'sidebar',
        );
      });
      observer.observe(button, {
        attributes: true,
        attributeFilter: ['aria-expanded'],
      });
      setTimeout(() => observer.disconnect(), 1000);
    },
    true,
  );
  window.addEventListener('unhandledrejection', event => {
    runtimeError('UNHANDLED_REJECTION', false, event.reason);
    exception(event.reason, true);
  });
  window.mapCreateTelemetry.begin(1);
  const script = document.createElement('script');
  script.src = config.sdk_url;
  script.integrity = config.sdk_integrity;
  script.crossOrigin = 'anonymous';
  script.async = true;
  script.onerror = () => {
    document.documentElement.dataset.telemetryState = 'unavailable';
  };
  document.head.append(script);
}
