// Focused presentation checks; trusted TSX compiled with the existing TypeScript
// package. No browser, API, credentials or runner execution.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const filename = path.resolve(__dirname, '../src/components/visual-lab/StartupEvidence.tsx');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX }, fileName: filename,
}).outputText;
const component = new Module(filename, module);
component.filename = filename;
component.paths = Module._nodeModulePaths(path.dirname(filename));
component._compile(compiled, filename);
const StartupEvidence = component.exports.default;

test('renders startup stage, timings and bounded observations without crash claims', () => {
  const html = renderToStaticMarkup(React.createElement(StartupEvidence, {
    stage: 'session_handshake', timings: { browser_launch: 37667, session_handshake: 1851 },
    diagnostics: { session_created: false, driver_state: 'running', cleanup: 'unverified',
      cleanup_driver_exit_code: -9, native_errors: [] },
  }));
  assert.match(html, /session_handshake/);
  assert.match(html, /browser_launch: 37667 ms/);
  assert.match(html, /Session created<\/dt><dd>No/);
  assert.match(html, /unverified/);
  assert.match(html, /Driver cleanup exit code<\/dt><dd>-9/);
  assert.match(html, /not proof of a browser crash/);
});

test('missing legacy diagnostics remain explicitly unknown', () => {
  const html = renderToStaticMarkup(React.createElement(StartupEvidence, {}));
  assert.match(html, /not recorded or are unavailable/);
  assert.doesNotMatch(html, /Session created|0 ms|Passed/);
  const partial = renderToStaticMarkup(React.createElement(StartupEvidence, { diagnostics: {} }));
  assert.match(partial, /Session created<\/dt><dd>Unknown/);
});
