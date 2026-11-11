/* eslint-disable @typescript-eslint/no-require-imports */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

test("Next rewrite strips the browser /api prefix and uses API_BACKEND_URL", () => {
  const config = fs.readFileSync(
    path.join(__dirname, "..", "next.config.ts"),
    "utf8",
  );

  assert.match(config, /process\.env\.API_BACKEND_URL/);
  assert.match(config, /source:\s*["']\/api\/:path\*["']/);
  assert.match(config, /destination:\s*`\$\{apiBackendUrl\}\/\:path\*`/);
  assert.doesNotMatch(config, /destination:\s*`\$\{apiBackendUrl\}\/api\//);
});

test("middleware matchers do not intercept proxied API routes", () => {
  const middleware = fs.readFileSync(
    path.join(__dirname, "..", "middleware.ts"),
    "utf8",
  );

  assert.doesNotMatch(middleware, /["']\/api(?:\/|["'])/);
  assert.match(middleware, /["']\/dashboard\/:path\*["']/);
  assert.match(middleware, /["']\/projects\/:path\*["']/);
});
