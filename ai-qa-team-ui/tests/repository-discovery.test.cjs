/* eslint-disable @typescript-eslint/no-require-imports */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function source(relative) {
  return fs.readFileSync(path.join(__dirname, "..", relative), "utf8");
}

test("onboarding uses the shared repository manager instead of legacy import", () => {
  const step = source("src/components/onboarding/steps/StepTestImport.tsx");
  assert.match(step, /RepositoryManager/);
  assert.match(step, /repository_discovery/);
  assert.match(step, /test_registry/);
  assert.doesNotMatch(step, /RepoImportModal|playwright_repo_adapter|GitLab|Bitbucket/);
});

test("project navigation exposes the repository management page behind discovery flags", () => {
  const sidebar = source("src/components/layout/Sidebar.tsx");
  const page = source("src/app/(app)/projects/[projectId]/repositories/page.tsx");
  assert.match(sidebar, /Repositories/);
  assert.match(sidebar, /repository_discovery/);
  assert.match(page, /RepositoryManager/);
});
