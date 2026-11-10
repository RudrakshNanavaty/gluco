// Opens a visible browser so a person can sign in through Clerk. The profile is
// kept in capture/auth/<role>/ (gitignored), and the recorder reuses it headless.
//
//   bun capture/login.ts clinician
//   bun capture/login.ts patient
import { chromium } from "playwright"
import { profileDir, BASE_URL, VIEWPORT } from "./config"

const role = process.argv[2]
if (role !== "clinician" && role !== "patient") {
  console.error("usage: bun capture/login.ts <clinician|patient>")
  process.exit(1)
}
const landing = role === "clinician" ? /\/clinician/ : /\/me/

const context = await chromium.launchPersistentContext(profileDir(role), {
  headless: false,
  viewport: VIEWPORT,
})
const page = context.pages()[0] ?? (await context.newPage())
await page.goto(BASE_URL)
console.log(`Sign in as a ${role} in the browser window. Waiting up to 10 minutes...`)
await page.waitForURL(landing, { timeout: 600_000 })
// Let Clerk finish writing its session cookies before the profile is closed.
await page.waitForTimeout(3_000)
console.log(`Signed in as ${role} (${page.url()}). Session saved.`)
await context.close()
