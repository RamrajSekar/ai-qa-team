// Trusted TSX rendering only; no browser, API or authentication substitutes.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const filename = path.resolve(__dirname, '../src/components/visual-lab/PreparationEvidence.tsx');
const component = new Module(filename, module);
component.filename = filename;
component.paths = Module._nodeModulePaths(path.dirname(filename));
component._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
}).outputText, filename);
const Evidence = component.exports.default;

test('shows exact preparation failure, bounded timing and timestamped stage', () => {
  const html = renderToStaticMarkup(React.createElement(Evidence, { diagnostics: {
    stage:'manifest_copy', error_stage:'manifest_copy', reason:'command_timeout',
    timings_ms:{manifest_copy:30000}, events:[{stage:'manifest_copy', phase:'failed', at:'2026-11-03T15:00:00Z'}],
  } }));
  assert.match(html, /Failed stage: manifest copy/);
  assert.match(html, /Reason: command timeout/);
  assert.match(html, /30000/);
  assert.match(html, /manifest copy failed/);
  assert.match(html, /No browser execution is inferred/);
});

test('old records do not invent preparation diagnostics', () => {
  assert.equal(renderToStaticMarkup(React.createElement(Evidence, {})), '');
});
