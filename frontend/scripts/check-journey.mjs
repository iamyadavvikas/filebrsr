/** Rule-engine tests for the CSRD guided journey (node:test, no new deps).
 *
 * Run: `node scripts/check-journey.mjs` from frontend/.
 * Transpiles src/lib/csrd/journey.ts with the repo's own typescript,
 * then asserts the next-action rules + focus ordering.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire, Module } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(here, "..", "package.json"));
const ts = require("typescript");

const src = readFileSync(path.join(here, "..", "src", "lib", "csrd", "journey.ts"), "utf8");
const { outputText } = ts.transpileModule(src, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const mod = new Module("journey.cjs");
mod._compile(outputText, path.join(here, "journey.cjs"));
const { nextAction, stepStates, focusQueue } = mod.exports;

const base = {
  entriesAssessed: 10, entriesTotal: 600, iroCount: 2, orphanIroIds: [],
  methodologyStatus: "approved", stakeholderRecords: 1, reportsGenerated: 0,
};

test("empty workspace starts at registry", () => {
  assert.equal(nextAction({ ...base, entriesAssessed: 0 }).tab, "registry");
});

test("entries without IROs go to materiality", () => {
  assert.equal(nextAction({ ...base, iroCount: 0 }).tab, "materiality");
});

test("orphan IROs stay in materiality", () => {
  const a = nextAction({ ...base, orphanIroIds: ["x"] });
  assert.equal(a.tab, "materiality");
  assert.match(a.title, /orphan/i);
});

test("unapproved methodology blocks filing", () => {
  const a = nextAction({ ...base, methodologyStatus: "draft", stakeholderRecords: 0 });
  assert.equal(a.step, "lock");
  assert.match(a.title, /stakeholder/i);
});

test("ready workspace goes to reports", () => {
  assert.equal(nextAction(base).tab, "reports");
});

test("stepper marks single current step", () => {
  const steps = stepStates({ ...base, iroCount: 0 });
  // Lock stays done (methodology approved); only materiality is current.
  assert.deepEqual(steps.map((s) => s.state), ["done", "done", "current", "done", "todo"]);
  assert.equal(steps.filter((s) => s.state === "current").length, 1);
});

test("focus queue orders by standard then id, skipping assessed", () => {
  const q = focusQueue(
    [
      { id: "E1.b", standard: "E1" },
      { id: "2.a", standard: "2" },
      { id: "E1.a", standard: "E1" },
      { id: "E1.c", standard: "E1" },
    ],
    new Set(["E1.a"]),
    ["2", "E1"]
  );
  assert.deepEqual(q, ["2.a", "E1.b", "E1.c"]);
});
