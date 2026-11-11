const { test, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || "playwright");

const base = process.env.REPOSITORY_UI_URL || "http://localhost:3002";
let browser;

before(async () => {
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "msedge", headless: true });
});
after(async () => browser?.close());

for (const viewport of [{ name: "desktop", width: 1440, height: 900 }, { name: "mobile", width: 390, height: 844 }]) {
  test(`repository page renders without runtime errors on ${viewport.name}`, async (t) => {
    const context = await browser.newContext({ viewport });
    t.after(() => context.close());
    await context.addCookies([{ name: "access_token", value: "test-only", url: base }]);
    await context.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
      let body = [];
      if (path === "/features") body = { repository_discovery: true, test_registry: true };
      if (path === "/auth/me") body = { user: { name: "QA User", email: "qa@example.com", onboarding: { onboarding_status: "completed" }, subscription: { plan: "free", usage: {}, limits: {} } } };
      if (path === "/projects") body = [{ project_id: "P1", name: "Customer portal" }];
      if (path === "/repositories/options") body = { local_repository: true };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    });
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    page.setDefaultNavigationTimeout(90000);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(`${base}/projects/P1/repositories`, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { name: "Repositories" }).waitFor();
    await page.getByRole("button", { name: /GitHub Repository/ }).waitFor();
    await page.getByRole("button", { name: /Local Repository/ }).waitFor();
    assert.deepEqual(errors, []);
  });
}
