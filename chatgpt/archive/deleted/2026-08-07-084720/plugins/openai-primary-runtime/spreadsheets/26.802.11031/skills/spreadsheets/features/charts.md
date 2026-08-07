# Chart Requirements and Guidance

Use a chart only when it makes a KPI, comparison, trend, distribution, ranking, progress measure, or relationship easier to interpret; otherwise use a compact table or summary.

## General Chart Guidance
- Create native workbook chart objects using the chart API for the selected spreadsheet workflow.
- Give each chart one distinct takeaway; avoid redundant charts.
- Keep chart-source tables legible with visible text, wrapping, and appropriate column widths.
- For time-based charts, if raw dates would create crowded labels or unreliable date-axis grouping, add a grouped field such as Year, Quarter, Month, or Week to the chart source.

## Creating Excel Charts

Optimize for one clear takeaway and prioritize the data. Use color only for meaning, and keep labels, units, and comparisons easy to read.

1. Choose the takeaway and most suitable chart type for the data.
Examples below are guidance, not hard rules:
- For category comparison or ranking, consider a sorted bar/column chart.
- For trends over time, consider a line chart; use area charts only when the filled volume adds meaning.
- For part-to-whole, consider a sorted bar chart, compact table, or pie/doughnut when there are only a few slices and the rough share is the point.
- For distributions, consider a histogram; use boxWhisker when median, spread, and outliers are the point.
- For exact values across a small number of items, consider a table instead of a chart.
- For a single metric with context, consider a KPI plus a small trend/sparkline instead of a full chart.
Prefer the chart that makes the intended takeaway easiest to see, even if it differs from the examples.

2. Use auditable chart data
- Chart ranges must be formula-backed, dynamic where practical, and traceable to source data.
- Prefer direct series references to source data, so that when source data changes, charts are updated.
- Fallback: Use helper ranges only for reshaping, grouping dates, shortening labels, export/render workarounds, or a useful compact chart-driving table. Helper ranges must reference source cells with formulas, not hardcoded copied values.
- Before creation, verify categories, headers, series names and values, orientation, and point counts; prevent headers from becoming values or a data column from becoming categories.
- Use blanks, not invented zeroes, for unknown values. Keep category and series ranges aligned; if numeric/date categories or blanks render incorrectly, use a compact formula-backed helper range with explicit labels and disclose omitted observations.

3. Place the chart cleanly
- Place near the KPI block or table they explain.
- Leave enough whitespace. Do not overlap source data, controls, notes, or other charts.
- Align related charts and keep comparable charts consistent in scale, units, colors, and date ranges.
- Size charts by rendered density, not available grid space. Keep small charts compact; expand only when labels, legends, or dense data need it. In visual QA, shrink charts with obvious unused plot area or whitespace around a small number of marks. Very wide or tall charts without a clear need look unprofessional.

4. Format titles, axes, and labels
- Use simple and human readable chart titles, e.g. `Revenue rose 18% YoY, led by Enterprise`, `Profit by Category ($bn)`, `User Engagement`. Do not make up words or use obscure phrases.
- Keep chart titles professional and no larger than surrounding section labels, usually 12-14 pt.
- Make units visible in the title, axis, or labels: %, $, hours, count, dates, etc.
- Set axis number formats explicitly, even when source cells are already formatted. Number formatting is required for percent, currency, dates/timestamps.
- Add axis titles only when the axis meaning or unit is not already clear from the title, tick labels, or data labels.
- Shorten long category labels with formula-backed helper labels; keep full labels in the source table.
- Use data labels only when exact values matter or the axis is hard to read.
- Do not label every point in dense line charts.
- Prefer direct series labels for a few series; use legends only when needed and place them where they do not crowd the plot.

5. Use restrained chart design
- Use color for meaning, not decoration. Keep color meanings consistent across related charts.
- Avoid chartjunk unless asked: unnecessary gradients, heavy borders, excessive gridlines, or decorative effects.
- Use meaningful ordering: time order for time series, descending values for rankings, process order for workflows.
- Ensure titles, axes, tick labels, legends, and important values are readable at normal zoom without clipping or overlap.

6. Render and verify
- Render/inspect the workbook before finishing.
- Check for blank charts, disconnected ranges, stale ranges, formula errors, unreadable units, clipped labels, overcrowded ticks, unintended multi-color single-series charts, and unsupported chart types.
- After creation or editing, verify the expected chart objects, source ranges, orientation, point counts, and placement; remove duplicates or overlaps.
- If categories appear as a series or points disappear, normalize the helper range and rebuild once.
- If the requested chart type does not render reliably, use the closest clear alternative and preserve the intended takeaway.


## Editing Existing Charts
Before editing, inspect the chart object, source ranges and formulas, and rendered output. Preserve the existing layout and scope unless redesign is requested; resize or move the chart minimally to avoid overlap. After editing, recheck the source, formulas, axes, labels, and rendered chart. Leave unrelated pre-existing errors unchanged unless they break the requested chart or the user asks for an audit or repair.
