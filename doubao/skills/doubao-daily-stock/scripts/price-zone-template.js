/*
Canonical price-zone helpers for the daily stock analysis report.
Use these helpers to calculate all left/width percentages. Do not hand-place
the current price or oscillation band. Support and pressure must not be drawn
on the price-zone axis; render them only as text in the zone-note rows.
*/

function clampPct(value) {
  return Math.max(0, Math.min(100, value));
}

function pct(price, scaleMin, scaleMax) {
  const min = Number(scaleMin);
  const max = Number(scaleMax);
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) {
    throw new Error('Invalid price-zone scale');
  }
  return clampPct(((Number(price) - min) / (max - min)) * 100);
}

function collectPriceZoneValues(zone) {
  const values = [];
  const add = (value) => {
    const number = Number(value);
    if (Number.isFinite(number)) values.push(number);
  };
  add(zone && zone.current && zone.current.value);
  add(zone && zone.oscillation && zone.oscillation.low);
  add(zone && zone.oscillation && zone.oscillation.high);
  ['pressure', 'support'].forEach((key) => {
    const items = Array.isArray(zone && zone[key]) ? zone[key] : [];
    items.forEach((item) => {
      add(item.value);
      add(item.low);
      add(item.high);
    });
  });
  return values;
}

function calculatePriceZoneScale(zone, paddingRatio = 0.07) {
  const values = collectPriceZoneValues(zone);
  if (values.length < 2) throw new Error('Price-zone scale requires at least two finite values');
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, Math.abs(max || min) * 0.02, 1);
  const padding = span * paddingRatio;
  return {
    scaleMin: min - padding,
    scaleMax: max + padding
  };
}

function zonePointStyle(price, scaleMin, scaleMax) {
  return `left: ${pct(price, scaleMin, scaleMax).toFixed(1)}%;`;
}

function zoneRangeStyle(low, high, scaleMin, scaleMax) {
  const left = pct(low, scaleMin, scaleMax);
  const right = pct(high, scaleMin, scaleMax);
  return `left: ${left.toFixed(1)}%; width: ${Math.max(0, right - left).toFixed(1)}%;`;
}

function zoneOscillationLowStyle(oscillation, scaleMin, scaleMax) {
  return zonePointStyle(oscillation.low, scaleMin, scaleMax);
}

function zoneOscillationHighStyle(oscillation, scaleMin, scaleMax) {
  return zonePointStyle(oscillation.high, scaleMin, scaleMax);
}

if (typeof module !== 'undefined') {
  module.exports = {
    pct,
    collectPriceZoneValues,
    calculatePriceZoneScale,
    zonePointStyle,
    zoneRangeStyle,
    zoneOscillationLowStyle,
    zoneOscillationHighStyle
  };
}
