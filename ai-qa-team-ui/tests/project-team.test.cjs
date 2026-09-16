/* eslint-disable @typescript-eslint/no-require-imports */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const read = (name) => fs.readFileSync(path.join(root, name), "utf8");

test("onboarding includes the optional shared project team step", () => {
  const onboarding = read("src/components/onboarding/OnboardingModal.tsx");
  const teamStep = read("src/components/onboarding/steps/StepTeam.tsx");
  const teamManager = read("src/components/team/TeamManager.tsx");
  assert.match(onboarding, /Project.*Application.*Team.*Automation.*Ready/s);
  assert.match(teamStep, /TeamManager/);
  assert.match(teamManager, /Skip for now/);
});

test("project team settings and role-aware administrative controls are wired", () => {
  const sidebar = read("src/components/layout/Sidebar.tsx");
  const teamPage = read("src/app/(app)/projects/[projectId]/settings/team/page.tsx");
  const repositories = read("src/components/repositories/RepositoryManager.tsx");
  assert.match(sidebar, /current_user_role === "ADMIN"/);
  assert.match(teamPage, /TeamManager/);
  assert.match(repositories, /readOnly/);
});
