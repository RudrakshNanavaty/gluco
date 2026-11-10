// bun voice: writes the script lines out and runs speak.py in the Kokoro venv.
// KOKORO_DIR holds the venv (.venv) and the two model files.
import { join } from "node:path"
import { CHAPTERS, TEASER_LINES } from "../src/script"

const kokoro = process.env.KOKORO_DIR
if (!kokoro) throw new Error("Set KOKORO_DIR to the folder with .venv and the Kokoro model files")

const here = import.meta.dir
const lines = join(kokoro, "lines.json")
await Bun.write(lines, JSON.stringify([...CHAPTERS, ...TEASER_LINES].map(({ id, line }) => ({ id, line }))))
const run = Bun.spawnSync(
  [join(kokoro, ".venv/bin/python"), "-I", join(here, "speak.py"), lines, join(here, "..", "public", "voice"), kokoro],
  { stdout: "inherit", stderr: "inherit" },
)
process.exit(run.exitCode ?? 1)
