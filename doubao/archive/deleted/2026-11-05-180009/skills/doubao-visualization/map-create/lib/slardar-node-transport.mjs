import { telemetryBid } from './task-telemetry.mjs';

export async function sendTelemetryBatch(Slardar, state, request = fetch) {
  const client = new Slardar({
    bid: telemetryBid,
    env: state.env,
    release: state.skill_version,
    userId: state.trace_id,
    deviceId: state.trace_id,
    autoPv: false,
    logger: false,
    size: 1024,
    wait: 60000,
  });
  const sender = client.ctx.client.getSender();
  try {
    const target = new URL(sender.getEndpoint());
    if (target.protocol !== 'https:' || target.hostname !== 'mon.zijieapi.com')
      throw new Error('TELEMETRY_ENDPOINT_INVALID');
    const configuration = await request(
      `${target.origin}/monitor_web/settings/browser-settings?bid=${telemetryBid}`,
      { signal: AbortSignal.timeout(1500) },
    );
    if (!configuration.ok) throw new Error('TELEMETRY_SETTINGS_UNAVAILABLE');
    const { data } = await configuration.json();
    if (
      data?.sample?.sample_rate !== 1 ||
      (data.quota_rate !== undefined && data.quota_rate !== 1)
    )
      throw new Error('TELEMETRY_FULL_SAMPLING_REQUIRED');
    const settings = data.sample.rules;
    if (!Array.isArray(settings))
      throw new Error('TELEMETRY_SETTINGS_UNAVAILABLE');
    const types = new Set(
      state.pending.map(event =>
        event.name === 'generation_exception' ? 'js_error' : 'custom',
      ),
    );
    const blockedTypes = new Set();
    for (const type of types) {
      const rule = settings.find(setting => setting.name === type);
      if (
        rule &&
        (rule.enable === false ||
          (rule.sample_rate !== undefined && rule.sample_rate !== 1) ||
          rule.conditional_sample_rules?.length)
      )
        blockedTypes.add(type);
    }
    const pending = state.pending.filter(
      event =>
        !blockedTypes.has(
          event.name === 'generation_exception' ? 'js_error' : 'custom',
        ),
    );
    if (!pending.length) throw new Error('TELEMETRY_FULL_SAMPLING_REQUIRED');
    client.signSettingsPromise = async () => settings;
    client.ctx.client.on('beforeSend', event => ({
      ...event,
      common: {
        bid: telemetryBid,
        env: state.env,
        release: state.skill_version,
        user_id: state.trace_id,
        device_id: state.trace_id,
        session_id: state.trace_id,
        view_id: event.common?.view_id,
        pid: 'map-create-generation',
        sdk_name: event.common?.sdk_name,
        sdk_version: event.common?.sdk_version,
        timestamp:
          event.payload?.metrics?.event_time ||
          event.payload?.extra?.event_time,
        sample_rate: 1,
        ...(event.ev_type === 'js_error'
          ? {
              context: Object.fromEntries(
                Object.entries(event.payload.extra).map(([key, value]) => [
                  key,
                  String(value),
                ]),
              ),
            }
          : {}),
      },
    }));
    for (const event of pending) {
      const { name, exception, ...fields } = event;
      if (name === 'generation_exception')
        client.sendJsError({
          error: exception,
          breadcrumbs: [],
          extra: fields,
        });
      else
        client.sendEvent({
          name,
          categories: Object.fromEntries(
            Object.entries(fields)
              .filter(([, value]) => typeof value !== 'number')
              .map(([key, value]) => [key, String(value)]),
          ),
          metrics: Object.fromEntries(
            Object.entries(fields).filter(
              ([, value]) => typeof value === 'number',
            ),
          ),
        });
      await new Promise(resolve => setImmediate(resolve));
    }
    const batch = sender.getBatchData();
    sender.clear();
    const events = JSON.parse(batch).list;
    if (events.length !== pending.length)
      throw new Error('TELEMETRY_BATCH_INCOMPLETE');
    if (
      events.some(
        event =>
          typeof event.common?.view_id !== 'string' ||
          !event.common.view_id.trim(),
      )
    )
      throw new Error('TELEMETRY_VIEW_ID_MISSING');
    const endpoint = sender.getEndpoint();
    const response = await request(endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: batch,
      signal: AbortSignal.timeout(1800),
    });
    if (!response.ok) throw new Error('TELEMETRY_SEND_FAILED');
    return pending.map(event => event.event_id);
  } finally {
    sender.clear();
  }
}
