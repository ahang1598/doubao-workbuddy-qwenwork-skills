#!/usr/bin/env node
/* Node-side harness for semantic-trap fixtures.
 * Runs the pure facts/membership modules of report-runtime.js against one
 * fixture directory and prints results as JSON. Used by test_contracts.py to
 * compare JS runtime output with the Python oracle and the human-reviewed
 * expected values. */

const fs = require('fs');
const path = require('path');

const fixtureDir = process.argv[2];
if (!fixtureDir) {
  console.error('Usage: run_semantic_checks.js <fixture-dir>');
  process.exit(2);
}

const runtime = require(path.join(__dirname, '..', 'assets', 'components', 'report-runtime.js'));
const facts = runtime.facts;
const membership = runtime.membership;

const records = JSON.parse(fs.readFileSync(path.join(fixtureDir, 'records.json'), 'utf8'));
const fields = JSON.parse(fs.readFileSync(path.join(fixtureDir, 'fields.json'), 'utf8'));
const caseData = JSON.parse(fs.readFileSync(path.join(fixtureDir, 'case.json'), 'utf8'));

const results = {};
for (const check of caseData.checks) {
  if (check.kind === 'aggregate') {
    const scoped = check.filter_ast ? membership.filterRecords(records, check.filter_ast) : records;
    results[check.id] = facts.aggregateField(scoped, check.field, check.function, check.null_policy || 'exclude');
  } else if (check.kind === 'group') {
    const config = Object.assign({}, check.config, { fields });
    const rows = facts.groupAggregate(records, config);
    results[check.id] = {
      categories: rows.map(row => row.label),
      values: rows.map(row => row.value),
    };
  } else if (check.kind === 'filter') {
    results[check.id] = { count: membership.filterRecords(records, check.filter_ast).length };
  } else if (check.kind === 'format') {
    results[check.id] = facts.roundHalfAwayFromZero(check.value, check.decimals);
  } else if (check.kind === 'bucket') {
    results[check.id] = facts.bucketDate(check.ms, check.granularity);
  } else {
    console.error(`unknown check kind: ${check.kind}`);
    process.exit(2);
  }
}

console.log(JSON.stringify(results));
