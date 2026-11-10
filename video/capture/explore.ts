// Dev helper: screenshot and dump the aria tree of a route for shot planning.
//   bun capture/explore.ts clinician /clinician
import { chromium } from "playwright"
import { BASE_URL, profileDir, VIEWPORT } from "./config"
const [role, route = "/"] = process.argv.slice(2) as ["clinician" | "patient", string]
const ctx = await chromium.launchPersistentContext(profileDir(role), { headless: true, viewport: VIEWPORT })
const page = ctx.pages()[0] ?? (await ctx.newPage())
await page.goto(BASE_URL + route)
await page.waitForLoadState("networkidle").catch(() => {})
await page.waitForTimeout(4000)
const name = route.replace(/\W+/g, "_") || "root"
await page.screenshot({ path: `capture/footage/${role}${name}.png`, fullPage: true })
console.log(page.url())
console.log(await page.locator("body").ariaSnapshot())
await ctx.close()
