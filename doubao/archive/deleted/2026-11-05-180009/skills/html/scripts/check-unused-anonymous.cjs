'use strict';

// Parse only; never execute the HTML's JavaScript. Keep the rule deliberately
// narrow: an ExpressionStatement whose entire value is an anonymous function.
const fs = require('node:fs');
const acorn = require('../assets/vendor/acorn.cjs');
const scripts = JSON.parse(fs.readFileSync(0, 'utf8'));
const findings = [], skippedScripts = [];

for (const [index, script] of scripts.entries()) {
  let tree;
  try {
    tree = acorn.parse(script.code, {
      ecmaVersion: 'latest', sourceType: script.sourceType,
      preserveParens: true, allowHashBang: true,
    });
  } catch (error) {
    // Don't guess with a regex when the AST cannot be built; report where parsing stopped.
    const pos = typeof error.pos === 'number' ? error.pos : null;
    skippedScripts.push({index, reason: 'script_parse_failed',
      message: String(error.message || '').replace(/\s*\(\d+:\d+\)\s*$/, ''),
      offset: pos === null ? null : Array.from(script.code.slice(0, pos)).length});
    continue;
  }
  const pending = [tree];
  while (pending.length) {
    const node = pending.pop();
    if (node.type === 'ExpressionStatement') {
      let expression = node.expression;
      while (expression.type === 'ParenthesizedExpression') {
        expression = expression.expression;
      }
      if (expression.type === 'ArrowFunctionExpression' ||
          (expression.type === 'FunctionExpression' && !expression.id)) {
        // Acorn offsets are UTF-16; Python source offsets count code points.
        findings.push({index, kind: expression.type === 'ArrowFunctionExpression' ? 'arrow' : 'function',
          offset: Array.from(script.code.slice(0, expression.start)).length});
      }
    }
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) {
        for (let i = value.length - 1; i >= 0; i--) {
          if (value[i] && typeof value[i].type === 'string') pending.push(value[i]);
        }
      } else if (value && typeof value.type === 'string') pending.push(value);
    }
  }
}
process.stdout.write(JSON.stringify({findings, skippedScripts}));
