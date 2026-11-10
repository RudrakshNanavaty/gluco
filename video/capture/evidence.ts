// Runs the three test suites the way CI does and keeps their summary lines for
// the "Engineering evidence" chapter: public/evidence.json.
//   bun capture/evidence.ts
import { join } from "node:path"

const root = join(import.meta.dir, "..", "..")
const SUITES = [
  // LIVE_DB=1 includes the read-only checks against the real database (needs back-end/.env).
  {
    command: "cd back-end && LIVE_DB=1 uv run pytest -q",
    cwd: "back-end",
    argv: ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"],
    env: { LIVE_DB: "1" },
  },
  { command: "cd front-end && bun run test", cwd: "front-end", argv: ["bun", "run", "test"] },
  {
    command: "uv run pytest databricks/tests -q",
    cwd: ".",
    argv: ["uv", "run", "--no-project", "--with-requirements", "databricks/requirements-test.txt", "python", "-m", "pytest", "databricks/tests", "-q", "-p", "no:cacheprovider"],
  },
]

// Strip ANSI colour codes and keep only the lines that summarise a run.
const clean = (text: string) => text.replace(/\x1b\[[0-9;]*m/g, "")
const SUMMARY = /(\d+ passed|\d+ failed|Test Files|Tests\s+\d)/

const suites = []
for (const suite of SUITES) {
  const env = { ...process.env, CI: "1", FORCE_COLOR: "0", ...("env" in suite ? suite.env : {}) }
  const run = Bun.spawnSync(suite.argv, { cwd: join(root, suite.cwd), env })
  const out = clean(run.stdout.toString() + run.stderr.toString())
  const summary = out
    .split("\n")
    .map((l) => l.trim().replace(/^=+\s*|\s*=+$/g, ""))
    .filter((l) => SUMMARY.test(l))
  console.log(`${suite.command}: exit ${run.exitCode}\n  ${summary.join("\n  ")}`)
  // The video claims every test ran, so a skip or failure stops the capture.
  if (run.exitCode !== 0 || summary.some((l) => /skipped|failed/.test(l))) {
    throw new Error(`${suite.command} did not run cleanly; fix it before recording evidence`)
  }
  suites.push({ command: suite.command, exitCode: run.exitCode, summary })
}

const ranAt = new Date().toISOString().slice(0, 10)
await Bun.write(join(import.meta.dir, "..", "public", "evidence.json"), JSON.stringify({ ranAt, suites }, null, 2) + "\n")
