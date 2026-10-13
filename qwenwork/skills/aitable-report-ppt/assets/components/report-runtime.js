/* Visual Report Runtime — shared correctness layer for all themes.
 *
 * Contract 1.0. Implements semantics-1.0 (references/reporting/semantics.md).
 * Modules: facts / membership / charts / presentation.
 * facts and membership are pure (no DOM) and Node-testable.
 * Themes hand nodes to the runtime via the explicit mount API; the runtime
 * never queries theme-internal selectors.
 * The verification surface (window.__visualReport) reports OBSERVATIONS ONLY:
 * no `passed`, no expected values, no self-comparison verdicts.
 */
(function (global) {
  'use strict';

  /* 1.1 — chart activation is now bound by interaction geometry: axis charts
   * (bar/line/area) route clicks through the axis so the hit area matches the
   * axis tooltip, and no longer bind the series click; item charts (pie/donut)
   * keep it. Reports built against 1.0 have a different click model, so the
   * fingerprint gate must reject them rather than silently compare. */
  var CONTRACT_VERSION = '1.1';
  var SEMANTICS_VERSION = '1.0';

  /* ======================== facts (pure) ======================== */

  function isNull(value) {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string' && value.trim() === '') return true;
    if (Array.isArray(value) && value.length === 0) return true;
    return false;
  }

  var NUMERIC_RE = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

  function toNumber(value) {
    if (typeof value === 'number') return isFinite(value) ? value : null;
    if (typeof value === 'string') {
      var text = value.trim();
      if (NUMERIC_RE.test(text)) return parseFloat(text);
      return null;
    }
    return null;
  }

  function normText(value) {
    return String(value).normalize('NFC').trim();
  }

  function codePointCompare(a, b) {
    var A = Array.from(String(a));
    var B = Array.from(String(b));
    var n = Math.min(A.length, B.length);
    for (var i = 0; i < n; i++) {
      var x = A[i].codePointAt(0);
      var y = B[i].codePointAt(0);
      if (x !== y) return x < y ? -1 : 1;
    }
    return A.length === B.length ? 0 : (A.length < B.length ? -1 : 1);
  }

  function roundHalfAwayFromZero(value, decimals) {
    if (value === null || value === undefined) return null;
    var factor = Math.pow(10, decimals || 0);
    var sign = value < 0 ? -1 : 1;
    return sign * Math.floor(Math.abs(value) * factor + 0.5) / factor;
  }

  function numericValues(records, field, nullPolicy) {
    var out = [];
    for (var i = 0; i < records.length; i++) {
      var raw = records[i][field];
      var num = isNull(raw) ? null : toNumber(raw);
      if (num === null) {
        if (nullPolicy === 'as_zero') out.push(0);
      } else {
        out.push(num);
      }
    }
    return out;
  }

  function aggregateField(records, field, fn, nullPolicy) {
    nullPolicy = nullPolicy || 'exclude';
    if (fn === 'count') return records.length;
    if (fn === 'distinct_count') {
      var seen = Object.create(null);
      var count = 0;
      for (var i = 0; i < records.length; i++) {
        var raw = records[i][field];
        if (isNull(raw)) continue;
        var key = normText(String(raw));
        if (!(key in seen)) { seen[key] = true; count += 1; }
      }
      return count;
    }
    var values = numericValues(records, field, nullPolicy);
    if (fn === 'sum') {
      var total = 0;
      for (var j = 0; j < values.length; j++) total += values[j];
      return total;
    }
    if (fn === 'avg') {
      var denominator = nullPolicy === 'as_zero' ? records.length : values.length;
      if (denominator === 0) return null;
      var s = 0;
      for (var k = 0; k < values.length; k++) s += values[k];
      return s / denominator;
    }
    if (fn === 'min' || fn === 'max') {
      if (!values.length) return null;
      var extreme = values[0];
      for (var m = 1; m < values.length; m++) {
        if (fn === 'min' ? values[m] < extreme : values[m] > extreme) extreme = values[m];
      }
      return extreme;
    }
    if (fn === 'median') {
      if (!values.length) return null;
      var sorted = values.slice().sort(function (a, b) { return a - b; });
      var mid = sorted.length >> 1;
      return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    }
    throw runtimeError('CONTRACT_VIOLATION', 'semantics_unsupported aggregation: ' + fn);
  }

  function bucketDate(ms, granularity, tzOffsetMinutes) {
    var offset = tzOffsetMinutes === undefined ? 480 : tzOffsetMinutes;
    var shifted = new Date(ms + offset * 60000);
    var year = shifted.getUTCFullYear();
    var month = String(shifted.getUTCMonth() + 1).padStart(2, '0');
    if (granularity === 'month') return year + '-' + month;
    var day = String(shifted.getUTCDate()).padStart(2, '0');
    return year + '-' + month + '-' + day;
  }

  function fieldOptions(fields, fieldName) {
    if (!Array.isArray(fields)) return null;
    for (var i = 0; i < fields.length; i++) {
      var entry = fields[i];
      if (!entry) continue;
      var entryName = entry.fieldName != null ? entry.fieldName : entry.name;
      var entryId = entry.fieldId != null ? entry.fieldId : entry.field;
      if (entryName !== fieldName && entryId !== fieldName) continue;
      var options = entry.options || (entry.config && entry.config.options);
      if (!Array.isArray(options)) return null;
      return options.map(function (option) {
        if (option === null || option === undefined) return '';
        if (typeof option === 'object') return String(option.name != null ? option.name : (option.label != null ? option.label : option.value));
        return String(option);
      });
    }
    return null;
  }

  // Build a fieldId -> human name map from the snapshot field definitions,
  // tolerating both the DingTalk shape ({fieldId, fieldName}) and the generic
  // ({field, name}) shape. Used to render drill-down column headers in Chinese
  // even when a drilldown's `columns` are bare field ids.
  function fieldLabelMap(fields) {
    var map = {};
    if (!Array.isArray(fields)) return map;
    fields.forEach(function (entry) {
      if (!entry) return;
      var fid = entry.fieldId != null ? entry.fieldId : entry.field;
      var name = entry.fieldName != null ? entry.fieldName : entry.name;
      if (fid != null && name != null) map[String(fid)] = String(name);
    });
    return map;
  }

  function groupKeysOf(record, groupBy, nullPolicy, dateGranularity, tzOffsetMinutes) {
    var raw = record[groupBy];
    if (isNull(raw)) {
      if (nullPolicy === 'as_category') return ['未填写'];
      return []; // exclude and as_zero both drop the row from grouping
    }
    if (Array.isArray(raw)) {
      var keys = [];
      for (var i = 0; i < raw.length; i++) {
        if (!isNull(raw[i])) keys.push(normText(String(raw[i])));
      }
      return keys.length ? keys : (nullPolicy === 'as_category' ? ['未填写'] : []);
    }
    if (dateGranularity) {
      var ms = toNumber(raw);
      if (ms === null) return nullPolicy === 'as_category' ? ['未填写'] : [];
      return [bucketDate(ms, dateGranularity, tzOffsetMinutes)];
    }
    return [normText(String(raw))];
  }

  function groupAggregate(records, config) {
    var groupBy = config.group_by;
    var valueField = config.value_field;
    var fn = config.function || 'count';
    var nullPolicy = config.null_policy || 'exclude';
    var zeroPolicy = config.zero_policy || 'show';
    var groups = Object.create(null);
    var order = [];
    for (var i = 0; i < records.length; i++) {
      var keys = groupKeysOf(records[i], groupBy, nullPolicy, config.date_granularity, config.tz_offset_minutes);
      for (var j = 0; j < keys.length; j++) {
        var key = keys[j];
        if (!(key in groups)) { groups[key] = []; order.push(key); }
        groups[key].push(records[i]);
      }
    }
    if ((zeroPolicy === 'show' || zeroPolicy === 'placeholder') && config.fields) {
      var declared = fieldOptions(config.fields, groupBy);
      if (declared) {
        for (var d = 0; d < declared.length; d++) {
          var declaredKey = normText(declared[d]);
          if (!(declaredKey in groups)) { groups[declaredKey] = []; order.push(declaredKey); }
        }
      }
    }
    var grandTotal = null;
    if (fn === 'percentage') {
      grandTotal = aggregateField(records, valueField, 'sum', nullPolicy);
    }
    var rows = [];
    for (var g = 0; g < order.length; g++) {
      var label = order[g];
      var members = groups[label];
      var value;
      if (fn === 'percentage') {
        var part = aggregateField(members, valueField, 'sum', nullPolicy);
        value = grandTotal === 0 ? null : part / grandTotal * 100;
      } else {
        value = aggregateField(members, valueField, fn, nullPolicy);
      }
      rows.push({ label: label, value: value, count: members.length });
    }
    if (zeroPolicy === 'hide') {
      rows = rows.filter(function (row) { return row.value !== 0 && row.value !== null; });
    }
    rows = sortRows(rows, config.sort);
    if (nullPolicy === 'as_category') {
      var tail = rows.filter(function (row) { return row.label === '未填写'; });
      rows = rows.filter(function (row) { return row.label !== '未填写'; }).concat(tail);
    }
    return rows;
  }

  function sortRows(rows, sort) {
    var by = (sort && sort.by) || 'value';
    var direction = (sort && sort.order) === 'asc' ? 1 : -1;
    if (sort && Array.isArray(sort.values) && !sort.custom_order) {
      by = 'custom';
      sort = { by: 'custom', custom_order: sort.values };
    }
    var customIndex = Object.create(null);
    if (by === 'custom' && sort && Array.isArray(sort.custom_order)) {
      sort.custom_order.forEach(function (label, index) { customIndex[normText(String(label))] = index; });
    }
    return rows.slice().sort(function (a, b) {
      var primary = 0;
      if (by === 'value') {
        var av = a.value === null ? -Infinity : a.value;
        var bv = b.value === null ? -Infinity : b.value;
        primary = av === bv ? 0 : (av < bv ? -1 : 1) * direction;
      } else if (by === 'label') {
        primary = codePointCompare(a.label, b.label) * direction;
      } else if (by === 'custom') {
        var ai = a.label in customIndex ? customIndex[a.label] : Infinity;
        var bi = b.label in customIndex ? customIndex[b.label] : Infinity;
        primary = ai === bi ? 0 : (ai < bi ? -1 : 1);
      }
      if (primary !== 0) return primary;
      return codePointCompare(a.label, b.label);
    });
  }

  /* ===================== membership (pure) ===================== */

  function normalizeAst(ast) {
    if (!ast) return { op: 'and', children: [] };
    var op = ast.op;
    if (op === 'all') return { op: 'and', children: [] };
    if (op === 'is_null') return { op: 'eq', field: ast.field, value: null };
    if (op === 'not_null') return { op: 'ne', field: ast.field, value: null };
    var node = { op: op, field: ast.field, value: ast.value };
    if (op === 'in' && ast.value === undefined && Array.isArray(ast.values)) node.value = ast.values;
    var children = ast.children || ast.items;
    if (Array.isArray(children)) node.children = children.map(normalizeAst);
    return node;
  }

  function eqScalar(fieldValue, target) {
    if (target === null || target === undefined) return isNull(fieldValue);
    if (isNull(fieldValue)) return false;
    var numTarget = typeof target === 'number' ? target : null;
    if (numTarget !== null) {
      var numField = toNumber(fieldValue);
      if (numField !== null) return numField === numTarget;
    }
    return normText(String(fieldValue)) === normText(String(target));
  }

  function evalAst(record, ast) {
    var node = normalizeAst(ast);
    var op = node.op;
    if (op === 'and') return (node.children || []).every(function (child) { return evalAst(record, child); });
    if (op === 'or') return (node.children || []).some(function (child) { return evalAst(record, child); });
    if (op === 'not') {
      var children = node.children || [];
      if (children.length !== 1) throw runtimeError('CONTRACT_VIOLATION', 'not requires exactly one child');
      return !evalAst(record, children[0]);
    }
    var actual = record[node.field];
    var elements = Array.isArray(actual) ? actual : [actual];
    if (op === 'eq') {
      if (node.value === null || node.value === undefined) return isNull(actual);
      return elements.some(function (element) { return eqScalar(element, node.value); });
    }
    if (op === 'ne') return !evalAst(record, { op: 'eq', field: node.field, value: node.value });
    if (op === 'in') {
      var list = Array.isArray(node.value) ? node.value : [];
      if (isNull(actual)) return list.some(function (item) { return item === null || item === undefined; });
      return elements.some(function (element) {
        return list.some(function (item) { return eqScalar(element, item); });
      });
    }
    if (op === 'contains') {
      if (isNull(actual)) return false;
      if (node.value === null || node.value === undefined) return false;
      var needle = normText(String(node.value));
      if (needle === '') return false;
      return elements.some(function (element) {
        return !isNull(element) && normText(String(element)).indexOf(needle) !== -1;
      });
    }
    if (op === 'gt' || op === 'gte' || op === 'lt' || op === 'lte') {
      var left = isNull(actual) ? null : toNumber(actual);
      var right = toNumber(node.value);
      if (left === null || right === null) return false;
      if (op === 'gt') return left > right;
      if (op === 'gte') return left >= right;
      if (op === 'lt') return left < right;
      return left <= right;
    }
    throw runtimeError('CONTRACT_VIOLATION', 'semantics_unsupported operator: ' + op);
  }

  function filterRecords(records, ast) {
    return records.filter(function (record) { return evalAst(record, ast); });
  }

  function memberKeyOf(record, confidentiality) {
    if (confidentiality === 'external_masked') return record.__member_key || null;
    return record.__record_id || record.__local_row_key || null;
  }

  /* ========================= runtime ========================= */

  function runtimeError(code, message) {
    var error = new Error('[' + code + '] ' + message);
    error.code = code;
    return error;
  }

  function create(config) {
    if (!config || !config.spec) throw runtimeError('CONTRACT_VIOLATION', 'create() requires spec');
    if (global.__visualReportRuntimeInstance) return global.__visualReportRuntimeInstance;

    var spec = config.spec;
    var records = Array.isArray(config.records) ? config.records : [];
    var fields = Array.isArray(config.fields) ? config.fields : [];
    var echartsLib = config.echarts || global.echarts || null;
    var confidentiality = (spec.report && spec.report.confidentiality) || 'internal';
    var fingerprints = config.fingerprints || global.REPORT_FINGERPRINTS || {};
    var destroyed = false;
    var mountedCharts = Object.create(null);
    var boundDrilldowns = Object.create(null);
    var deck = null;
    var drillComponent = null;
    var drillComponentMode = null;

    var chartById = indexById(spec.charts);
    var metricById = indexById(spec.metrics);
    var drilldownById = indexById(spec.drilldowns);

    function indexById(list) {
      var out = Object.create(null);
      (list || []).forEach(function (item) { if (item && item.id) out[item.id] = item; });
      return out;
    }

    function ensureAlive() {
      if (destroyed) throw runtimeError('DESTROYED', 'runtime has been destroyed');
    }

    function requireDef(map, id, kind) {
      var def = map[id];
      if (!def) throw runtimeError('UNKNOWN_ID', 'unknown ' + kind + ': ' + id);
      return def;
    }

    function normalizeChartConfig(def) {
      var agg = def.aggregation && typeof def.aggregation === 'object' ? def.aggregation : {};
      return {
        group_by: agg.group_by || def.dimension,
        value_field: agg.value_field || def.measure,
        function: agg.function || (typeof def.aggregation === 'string' ? def.aggregation : null) || 'count',
        null_policy: def.null_policy || 'exclude',
        zero_policy: def.zero_policy || 'show',
        sort: def.sort,
        date_granularity: def.date_granularity,
        fields: fields,
      };
    }

    function chartRows(chartId) {
      var def = requireDef(chartById, chartId, 'chart');
      return groupAggregate(records, normalizeChartConfig(def));
    }

    /* Chart text is authored on the fixed 1920x1080 stage and then scaled down
     * with it, so ECharts' 12px default lands at ~8px on a 1280-wide window —
     * unreadable. The runtime supplies stage-scale defaults; a theme may raise
     * or lower them through these CSS variables. The theme still owns the look
     * (iron rule 9) — this only stops charts falling into the library default.
     * Minimums are enforced by validate_visual_report.js, not clamped here. */
    var CHART_FONT_DEFAULTS = { axis: 21, label: 21, tooltip: 21 };

    function chartFontSize(role) {
      var fallback = CHART_FONT_DEFAULTS[role];
      if (typeof document === 'undefined') return fallback;
      var raw = getComputedStyle(document.documentElement)
        .getPropertyValue('--chart-' + role + '-font-size').trim();
      var parsed = parseFloat(raw);
      return isFinite(parsed) && parsed > 0 ? parsed : fallback;
    }

    function getChartOption(chartId) {
      ensureAlive();
      var def = requireDef(chartById, chartId, 'chart');
      var rows = chartRows(chartId);
      var palette = paletteFromTheme();
      var axisFont = chartFontSize('axis');
      var labelFont = chartFontSize('label');
      var tooltipFont = chartFontSize('tooltip');
      if (def.type === 'pie' || def.type === 'donut') {
        return {
          color: palette,
          textStyle: { fontSize: labelFont },
          tooltip: { trigger: 'item', textStyle: { fontSize: tooltipFont } },
          series: [{
            type: 'pie',
            radius: def.type === 'donut' ? ['40%', '70%'] : '70%',
            label: { fontSize: labelFont },
            data: rows.map(function (row) { return { name: row.label, value: row.value }; }),
          }],
        };
      }
      return {
        color: palette,
        /* Root textStyle is the default for any component a theme adds later
         * (e.g. its own legend); explicit axisLabel below covers the axes we
         * do declare. No legend key is added here — creating one would change
         * the layout of every existing report. */
        textStyle: { fontSize: labelFont },
        tooltip: { trigger: 'axis', textStyle: { fontSize: tooltipFont } },
        /* containLabel keeps wide axis labels (e.g. 10,000,000) inside the
         * grid margin instead of clipping their leading digits. */
        grid: { left: 55, right: 20, top: 28, bottom: 52, containLabel: true },
        xAxis: {
          type: 'category',
          data: rows.map(function (row) { return row.label; }),
          axisLabel: { fontSize: axisFont },
        },
        yAxis: { type: 'value', axisLabel: { fontSize: axisFont } },
        series: [{
          type: def.type === 'line' || def.type === 'area' ? 'line' : 'bar',
          areaStyle: def.type === 'area' ? {} : undefined,
          data: rows.map(function (row) { return row.value; }),
          smooth: true,
          barMaxWidth: 52,
        }],
      };
    }

    function paletteFromTheme() {
      if (typeof document === 'undefined') return undefined;
      var style = getComputedStyle(document.documentElement);
      var colors = ['--chart-1', '--chart-2', '--chart-3', '--chart-4']
        .map(function (name) { return style.getPropertyValue(name).trim(); })
        .filter(Boolean);
      return colors.length ? colors : undefined;
    }

    function mountChart(el, chartId) {
      ensureAlive();
      if (!el) throw runtimeError('CONTRACT_VIOLATION', 'mountChart requires an element');
      if (mountedCharts[chartId]) throw runtimeError('ALREADY_MOUNTED', 'chart already mounted: ' + chartId);
      if (!echartsLib) throw runtimeError('CONTRACT_VIOLATION', 'echarts library not provided');
      var def = requireDef(chartById, chartId, 'chart');
      var instance = echartsLib.init(el);
      instance.setOption(getChartOption(chartId));
      var drillDefs = findDrilldownsForChart(def);
      if (drillDefs.length) {
        bindChartActivation(instance, def, chartId, drillDefs);
        drillDefs.forEach(function (item) { boundDrilldowns[item.id] = true; });
      }
      var handle = {
        chartId: chartId,
        resize: function () { instance.resize(); },
        dispose: function () { instance.dispose(); delete mountedCharts[chartId]; },
      };
      mountedCharts[chartId] = { instance: instance, handle: handle };
      return handle;
    }

    /* Where a click may legitimately land differs by chart geometry, and the
     * hit area must match whatever the tooltip already promised. An axis
     * tooltip reacts to the whole category band, so a 4px line symbol as the
     * only click target reads as a broken feature: the reader is shown a value
     * and then cannot open it. Bar charts have the same mismatch in the blank
     * space above a short bar. Pie and donut sectors are their own hit area,
     * so those keep the series click. */
    var AXIS_GEOMETRY = { bar: 1, stacked_bar: 1, grouped_bar: 1, line: 1, area: 1 };

    /* Single entry point: every geometry funnels here so a chart can never
     * open two drill-downs from one click. */
    function activateDrilldown(def, chartId, drillDefs, categoryName) {
      if (categoryName === undefined || categoryName === null) return;
      var match = null;
      for (var i = 0; i < drillDefs.length; i++) {
        var trig = drillDefs[i].trigger || {};
        if (trig.category !== undefined && normText(String(trig.category)) === normText(String(categoryName))) {
          match = drillDefs[i];
          break;
        }
      }
      if (!match) {
        for (var j = 0; j < drillDefs.length; j++) {
          if ((drillDefs[j].trigger || {}).category === undefined) { match = drillDefs[j]; break; }
        }
      }
      if (match && match.mode !== 'aggregate_only') {
        openDrilldownInternal(match, (def.title || chartId) + ' · ' + categoryName, def, categoryName);
      }
    }

    function bindChartActivation(instance, def, chartId, drillDefs) {
      if (!AXIS_GEOMETRY[def.type]) {
        instance.on('click', function (params) {
          activateDrilldown(def, chartId, drillDefs, params && params.name);
        });
        return;
      }
      /* Axis geometry: map the click position to a category through the axis
       * itself, so the whole band is clickable. The series click is
       * deliberately NOT bound here — binding both would open the drill-down
       * twice for a click that happens to land on the symbol. */
      instance.getZr().on('click', function (event) {
        var point = [event.offsetX, event.offsetY];
        if (typeof instance.containPixel === 'function'
          && !instance.containPixel({ gridIndex: 0 }, point)) return;
        var index = instance.convertFromPixel({ xAxisIndex: 0 }, point[0]);
        if (index === null || index === undefined || isNaN(index)) return;
        var axis = (instance.getOption().xAxis || [{}])[0] || {};
        var categories = axis.data || [];
        activateDrilldown(def, chartId, drillDefs, categories[Math.round(index)]);
      });
    }

    /* A chart may route to several drill-downs: category-specific ones
     * (trigger.category matches the clicked series label) plus at most one
     * whole-chart fallback (no category). */
    function findDrilldownsForChart(chartDef) {
      var out = [];
      if (chartDef.drilldown_id && drilldownById[chartDef.drilldown_id]) out.push(drilldownById[chartDef.drilldown_id]);
      var list = spec.drilldowns || [];
      for (var i = 0; i < list.length; i++) {
        var trigger = list[i].trigger;
        if (trigger && trigger.type === 'chart' && trigger.ref_id === chartDef.id && out.indexOf(list[i]) === -1) {
          out.push(list[i]);
        }
      }
      return out.filter(function (item) { return item.mode !== 'aggregate_only'; });
    }

    function resolveMembersInternal(def, legacyField, legacyValue) {
      var ast = def.membership && def.membership.filter_ast;
      var members;
      if (ast) {
        members = filterRecords(records, ast);
      } else if (legacyField) {
        members = records.filter(function (record) {
          var raw = record[legacyField];
          var key = isNull(raw) ? '未分类' : normText(String(raw));
          return key === normText(String(legacyValue));
        });
      } else {
        members = records.slice();
      }
      return members;
    }

    function resolveMembers(drilldownId) {
      ensureAlive();
      var def = requireDef(drilldownById, drilldownId, 'drilldown');
      var members = resolveMembersInternal(def);
      if (confidentiality === 'public') {
        return { count: members.length, memberKeys: null };
      }
      var keys = members
        .map(function (record) { return memberKeyOf(record, confidentiality); })
        .filter(function (key) { return key !== null; })
        .map(String)
        .sort(codePointCompare);
      return { count: members.length, memberKeys: keys };
    }

    function ensureDrillComponent(def) {
      if (typeof global.AITableDrilldown === 'undefined') {
        throw runtimeError('CONTRACT_VIOLATION', 'AITableDrilldown component not loaded');
      }
      if (drillComponent && drillComponentMode === def.mode) return drillComponent;
      if (drillComponent) drillComponent.root.remove();
      drillComponent = global.AITableDrilldown.create({
        mode: def.mode,
        columns: def.columns || [],
        detailFields: def.detail_fields || def.columns || [],
        searchFields: def.search_fields || def.columns || [],
        // Auto-derive Chinese column headers from field definitions; an
        // explicit def.labels still wins per key.
        labels: Object.assign(fieldLabelMap(fields), def.labels || {}),
        titleField: def.title_field,
        recordUrlField: def.record_url_field,
        embedOriginal: def.embed_original !== false,
        themeClass: 'avd-theme-' + ((typeof document !== 'undefined' && document.documentElement.dataset.theme) || 'default'),
      });
      drillComponentMode = def.mode;
      return drillComponent;
    }

    function openDrilldownInternal(def, title, chartDef, categoryValue) {
      if (!def || def.mode === 'aggregate_only') return;
      var legacyField = def.filter_field || (chartDef && (chartDef.dimension || (chartDef.aggregation && chartDef.aggregation.group_by)));
      var hasAst = def.membership && def.membership.filter_ast;
      var rows = hasAst ? resolveMembersInternal(def) : resolveMembersInternal(def, legacyField, categoryValue);
      ensureDrillComponent(def).open({ title: title, records: rows });
    }

    function bindDrilldown(el, drilldownId) {
      ensureAlive();
      if (!el) throw runtimeError('CONTRACT_VIOLATION', 'bindDrilldown requires an element');
      var def = requireDef(drilldownById, drilldownId, 'drilldown');
      if (def.mode === 'aggregate_only') return { drilldownId: drilldownId, bound: false };
      var title = (el.textContent || '明细').trim();
      el.addEventListener('click', function () { openDrilldownInternal(def, title); });
      boundDrilldowns[drilldownId] = true;
      return { drilldownId: drilldownId, bound: true };
    }

    function computeMetric(metricId) {
      ensureAlive();
      var def = requireDef(metricById, metricId, 'metric');
      var formula = def.formula;
      if (!formula || !formula.aggregation) {
        return { value: null, formatted: null, source: 'declared' };
      }
      var scoped = def.filter_ast ? filterRecords(records, def.filter_ast) : records;
      var field = (formula.fields && formula.fields[0]) || null;
      var value = aggregateField(scoped, field, formula.aggregation, def.null_policy || 'exclude');
      var formatted = value === null
        ? null
        : (typeof def.decimals === 'number' ? String(roundHalfAwayFromZero(value, def.decimals)) : String(value));
      return { value: value, formatted: formatted, source: 'computed' };
    }

    function createDeckController(options) {
      ensureAlive();
      if (!options || !options.stage || !options.slides) {
        throw runtimeError('CONTRACT_VIOLATION', 'createDeckController requires stage and slides');
      }
      if (deck) throw runtimeError('ALREADY_MOUNTED', 'deck controller already created');
      var stage = options.stage;
      var slides = Array.prototype.slice.call(options.slides);
      var current = 0;

      function fit() {
        var k = Math.min(global.innerWidth / 1920, global.innerHeight / 1080);
        var x = (global.innerWidth - 1920 * k) / 2;
        var y = (global.innerHeight - 1080 * k) / 2;
        stage.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(' + k + ')';
      }

      function goTo(index) {
        current = Math.max(0, Math.min(index, slides.length - 1));
        slides.forEach(function (slide, i) {
          slide.classList.toggle('active', i === current);
          slide.classList.toggle('visible', i === current);
        });
        if (typeof options.onChange === 'function') options.onChange(current, slides.length);
        setTimeout(function () {
          Object.keys(mountedCharts).forEach(function (id) { mountedCharts[id].instance.resize(); });
        }, 70);
      }

      if (options.keyboard !== false) {
        global.addEventListener('keydown', function (event) {
          if (typeof document !== 'undefined' && document.body.dataset.drillOpen === 'true') return;
          if (['ArrowRight', 'PageDown', ' '].indexOf(event.key) !== -1) goTo(current + 1);
          if (['ArrowLeft', 'PageUp'].indexOf(event.key) !== -1) goTo(current - 1);
          if (event.key === 'Home') goTo(0);
          if (event.key === 'End') goTo(slides.length - 1);
        });
      }
      global.addEventListener('resize', fit);
      fit();
      goTo(0);

      deck = {
        goTo: goTo,
        next: function () { goTo(current + 1); },
        prev: function () { goTo(current - 1); },
        current: function () { return current; },
        count: function () { return slides.length; },
      };
      exposeVerification();
      return deck;
    }

    function verificationSnapshot() {
      ensureAlive();
      var snapshot = {
        version: '1.0',
        contractVersion: CONTRACT_VERSION,
        fingerprints: fingerprints,
        confidentiality: confidentiality,
        slideCount: deck ? deck.count() : 0,
        currentSlide: deck ? deck.current() : 0,
        chartIds: Object.keys(mountedCharts),
        charts: {},
        metrics: {},
        drilldowns: {},
      };
      Object.keys(chartById).forEach(function (id) {
        try {
          var rows = chartRows(id);
          snapshot.charts[id] = {
            mounted: Boolean(mountedCharts[id]),
            categories: rows.map(function (row) { return row.label; }),
            values: rows.map(function (row) { return row.value; }),
          };
        } catch (error) {
          snapshot.charts[id] = { error: String(error && error.message) };
        }
      });
      Object.keys(metricById).forEach(function (id) {
        try { snapshot.metrics[id] = computeMetric(id); }
        catch (error) { snapshot.metrics[id] = { error: String(error && error.message) }; }
      });
      Object.keys(drilldownById).forEach(function (id) {
        try {
          var resolved = resolveMembers(id);
          snapshot.drilldowns[id] = {
            bound: Boolean(boundDrilldowns[id]),
            count: resolved.count,
            memberKeys: confidentiality === 'public' ? null : resolved.memberKeys,
          };
        } catch (error) {
          snapshot.drilldowns[id] = { error: String(error && error.message) };
        }
      });
      return snapshot;
    }

    function exposeVerification() {
      global.__visualReport = {
        version: '1.0',
        contractVersion: CONTRACT_VERSION,
        fingerprints: fingerprints,
        ready: true,
        confidentiality: confidentiality,
        getSlideCount: function () { return deck ? deck.count() : 0; },
        getCurrentSlide: function () { return deck ? deck.current() : 0; },
        getChartIds: function () { return Object.keys(mountedCharts); },
        getChartSeries: function (chartId) {
          var rows = chartRows(chartId);
          return { categories: rows.map(function (r) { return r.label; }), values: rows.map(function (r) { return r.value; }) };
        },
        getDrilldownIds: function () { return Object.keys(boundDrilldowns); },
        computeMetric: computeMetric,
        resolveMembers: resolveMembers,
        verificationSnapshot: verificationSnapshot,
        /* legacy compatibility for validators driving slides directly */
        showSlide: function (index) { if (deck) deck.goTo(index); },
      };
    }

    function destroy() {
      ensureAlive();
      Object.keys(mountedCharts).forEach(function (id) { mountedCharts[id].instance.dispose(); });
      if (drillComponent) drillComponent.root.remove();
      destroyed = true;
      delete global.__visualReportRuntimeInstance;
    }

    /* Eagerly mount the drill component for the first non-aggregate
     * drill-down so its (hidden) root exists before any interaction —
     * structural validators and screen readers can see it, matching the
     * legacy baseline behavior. */
    if (typeof document !== 'undefined' && global.AITableDrilldown) {
      var eagerDef = (spec.drilldowns || []).filter(function (item) {
        return item && item.mode !== 'aggregate_only';
      })[0];
      if (eagerDef) ensureDrillComponent(eagerDef);
    }

    var runtime = {
      contractVersion: CONTRACT_VERSION,
      semanticsVersion: SEMANTICS_VERSION,
      mountChart: mountChart,
      getChartOption: getChartOption,
      computeMetric: computeMetric,
      resolveMembers: resolveMembers,
      bindDrilldown: bindDrilldown,
      createDeckController: createDeckController,
      verificationSnapshot: verificationSnapshot,
      destroy: destroy,
    };
    global.__visualReportRuntimeInstance = runtime;
    exposeVerification();
    return runtime;
  }

  var VisualReportRuntime = {
    contractVersion: CONTRACT_VERSION,
    semanticsVersion: SEMANTICS_VERSION,
    create: create,
    /* pure modules exposed for Node-side contract tests */
    facts: {
      isNull: isNull,
      toNumber: toNumber,
      normText: normText,
      codePointCompare: codePointCompare,
      roundHalfAwayFromZero: roundHalfAwayFromZero,
      aggregateField: aggregateField,
      groupAggregate: groupAggregate,
      bucketDate: bucketDate,
    },
    membership: {
      evalAst: evalAst,
      filterRecords: filterRecords,
    },
  };

  global.VisualReportRuntime = VisualReportRuntime;
  if (typeof module !== 'undefined' && module.exports) module.exports = VisualReportRuntime;
})(typeof window !== 'undefined' ? window : globalThis);
