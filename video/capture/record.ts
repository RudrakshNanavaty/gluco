// Records every shot the videos use, against the running app.
//   bun capture/record.ts            all shots
//   bun capture/record.ts panel chat only these
import { chromium, type Page } from "playwright"
import { BASE_URL, profileDir, SCALE, VIEWPORT } from "./config"
import { Clip, prepare } from "./recorder"
import { mkdir } from "node:fs/promises"
import { footageDir } from "./config"

type Role = "clinician" | "patient" | "guest"
type Shot = { role: Role; run: (page: Page) => Promise<void> }

async function settle(page: Page, ms = 2500) {
  // The live stream keeps a connection open, so the network never goes idle.
  await page.waitForLoadState("networkidle", { timeout: 4000 }).catch(() => {})
  await page.waitForTimeout(ms)
}

/** Wait for the streaming answer to finish: the stop button goes away. */
async function answered(page: Page) {
  const stop = page.getByRole("button", { name: "Stop answering" })
  await stop.waitFor({ state: "visible", timeout: 20_000 }).catch(() => {})
  await stop.waitFor({ state: "hidden", timeout: 120_000 })
}

async function ask(clip: Clip, question: string) {
  const box = clip.page.getByRole("textbox", { name: "Message Gluco" })
  await clip.type(box, question, 38)
  await clip.wait(400)
  clip.mark(`ask:${question}`)
  await clip.page.keyboard.press("Enter")
  await answered(clip.page)
  clip.mark(`answered:${question}`)
}

const shots: Record<string, Shot> = {
  // Signed out: the landing page and the sign-in card.
  landing: {
    role: "guest",
    async run(page) {
      await page.goto(BASE_URL)
      await settle(page)
      // Clerk autofocuses its username field, which scrolls the hero away.
      await page.evaluate(() => {
        ;(document.activeElement as HTMLElement | null)?.blur()
        window.scrollTo(0, 0)
      })
      await page.waitForTimeout(800)
      const clip = new Clip(page, "landing")
      await clip.begin()
      await clip.moveTo(1000, 380, 1400)
      await clip.wait(2000)
      clip.mark("signin")
      await clip.click(page.getByRole("button", { name: /Get started/ }))
      await clip.wait(3500)
      await clip.end()
    },
  },

  // Clinician panel overview: stats, ranked lists, 7-day trend, patient table.
  panel: {
    role: "clinician",
    async run(page) {
      await page.goto(`${BASE_URL}/clinician`)
      await settle(page)
      const clip = new Clip(page, "panel")
      await clip.begin()
      await clip.wait(2500)
      const overview = page.getByRole("region", { name: "Patient panel overview" })
      clip.mark("overview")
      await clip.scroll((await overview.boundingBox())!.y - 110, 1600)
      await clip.wait(1200)
      await clip.region("stats", overview.locator("> div").first())
      await clip.wait(2500)
      clip.mark("lists")
      await clip.hover(page.getByText("Largest 24 h declines"), 900)
      await clip.wait(3000)
      clip.mark("trend")
      await clip.scroll(420, 1400)
      await clip.wait(3500)
      clip.mark("table")
      await clip.scroll(560, 1400)
      await clip.wait(3500)
      await clip.end()
    },
  },

  // A participant from the declines list: ranges, sensor trends, what changed.
  detail: {
    role: "clinician",
    async run(page) {
      await page.goto(`${BASE_URL}/clinician`)
      await settle(page)
      const link = page.getByRole("link", { name: /^Patient 013 Gluco Score/ }).first()
      await link.scrollIntoViewIfNeeded()
      await page.mouse.wheel(0, -200)
      await page.waitForTimeout(800)
      const clip = new Clip(page, "detail")
      await clip.begin()
      await clip.wait(800)
      clip.mark("open")
      await clip.click(link)
      await page.waitForURL(/participants/)
      await settle(page, 1500)
      clip.mark("loaded")
      await clip.wait(2500)
      for (const range of ["24 h", "72 h", "7 d"]) {
        await clip.click(page.getByRole("radiogroup", { name: "Time range" }).getByRole("radio", { name: range }), 600)
        clip.mark(`range:${range}`)
        await clip.wait(1800)
      }
      clip.mark("sensors")
      await clip.scroll(560, 1500)
      await clip.wait(3000)
      clip.mark("changed")
      const changed = page.getByText("What changed", { exact: true })
      await clip.scroll((await changed.boundingBox())!.y - 90, 1500)
      await clip.wait(2500)
      await clip.hover(page.getByRole("row").filter({ hasText: "Mean heart rate" }).first(), 900)
      await clip.wait(2500)
      await clip.click(page.getByRole("radiogroup", { name: "Compare with" }).getByRole("radio", { name: "72 h" }), 700)
      await clip.wait(2500)
      clip.mark("position")
      await clip.scroll(620, 1500)
      await clip.wait(3000)
      await clip.end()
    },
  },

  // The live strip: sensor clock ticks every second.
  live: {
    role: "clinician",
    async run(page) {
      await page.goto(`${BASE_URL}/clinician/participants/demo%3Abig_ideas%3A013`)
      await settle(page)
      const clip = new Clip(page, "live")
      await clip.begin()
      await clip.region("strip", page.getByText("Analytics as of").locator(".."))
      await clip.region("tiles", page.getByText("Live sensors").locator("..").locator(".."))
      await clip.wait(2000)
      clip.mark("hover")
      await clip.hover(page.getByRole("button", { name: "About live data" }), 900)
      await clip.wait(4000)
      await clip.moveTo(700, 500, 900)
      await clip.wait(5000)
      await clip.end()
    },
  },

  // Clinician chat: a question, then a widget that gets pinned to the panel.
  chat: {
    role: "clinician",
    async run(page) {
      await page.goto(`${BASE_URL}/clinician`)
      await settle(page)
      const clip = new Clip(page, "chat")
      await clip.begin()
      await clip.wait(1200)
      clip.mark("open")
      await clip.click(page.getByRole("button", { name: "Ask Gluco" }), 900)
      await clip.wait(1500)
      await ask(clip, "Which patients need follow-up?")
      await clip.wait(3000)
      await clip.scroll(400, 1500)
      await clip.wait(2500)
      await ask(clip, "Build a widget ranking the 5 lowest Gluco Scores")
      await clip.wait(2500)
      clip.mark("pin")
      const pin = page.getByRole("button", { name: /^Pin/ }).last()
      if (await pin.isVisible().catch(() => false)) {
        await clip.click(pin, 800)
        await clip.wait(1500)
      }
      clip.mark("close")
      await clip.click(page.getByRole("button", { name: "Close chat" }), 800)
      await clip.wait(1500)
      await page.reload()
      await settle(page, 1500)
      clip.mark("pinned")
      await clip.wait(4000)
      await clip.end()
    },
  },

  // Patient's own week: score, week chart, live vitals, what stands out.
  patient: {
    role: "patient",
    async run(page) {
      await page.goto(`${BASE_URL}/me`)
      await settle(page)
      const clip = new Clip(page, "patient")
      await clip.begin()
      await clip.wait(3500)
      clip.mark("vitals")
      const vitals = page.getByRole("heading", { name: "Your vitals" })
      await clip.scroll((await vitals.boundingBox())!.y - 90, 1600)
      await clip.wait(4500)
      clip.mark("more")
      await clip.scroll(520, 1500)
      await clip.wait(3000)
      clip.mark("stands-out")
      const out = page.getByText("What stands out", { exact: true })
      await clip.scroll((await out.boundingBox())!.y - 90, 1500)
      await clip.wait(4000)
      await clip.end()
    },
  },

  // Patient chat: a question about their own score, then one about someone else.
  "patient-chat": {
    role: "patient",
    async run(page) {
      await page.goto(`${BASE_URL}/me`)
      await settle(page)
      const clip = new Clip(page, "patient-chat")
      await clip.begin()
      await clip.wait(1000)
      await clip.click(page.getByRole("button", { name: "Ask Gluco" }), 900)
      await clip.wait(1500)
      await ask(clip, "Why did my score change?")
      await clip.wait(3500)
      clip.mark("guardrail")
      await ask(clip, "What is Patient 013's Gluco Score?")
      await clip.wait(4000)
      await clip.end()
    },
  },
}

const wanted = process.argv.slice(2)
const names = wanted.length ? wanted : Object.keys(shots)
await mkdir(footageDir, { recursive: true })

for (const name of names) {
  const shot = shots[name]
  if (!shot) throw new Error(`unknown shot ${name}`)
  const options = { headless: true, viewport: VIEWPORT, deviceScaleFactor: SCALE, colorScheme: "light" as const }
  const browser = shot.role === "guest" ? await chromium.launch() : null
  const context = browser
    ? await browser.newContext(options)
    : await chromium.launchPersistentContext(profileDir(shot.role as "clinician" | "patient"), options)
  await prepare(context)
  const page = context.pages()[0] ?? (await context.newPage())
  try {
    await shot.run(page)
  } finally {
    await context.close()
    await browser?.close()
  }
}
