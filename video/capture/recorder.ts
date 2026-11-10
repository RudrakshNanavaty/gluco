// Records a page through the Chrome DevTools screencast. Frames arrive only when
// the page repaints, so each one is held until the next and ffmpeg turns the
// list into constant 30 fps. Marks are timestamps (seconds into the clip) that
// the compositions use to time captions and push-ins.
import { mkdir, rm, writeFile } from "node:fs/promises"
import { join } from "node:path"
import type { BrowserContext, CDPSession, Locator, Page } from "playwright"
import { footageDir, SCALE, VIEWPORT } from "./config"

// A visible pointer. Headless Chrome draws none, and viewers need to see clicks.
const CURSOR_SCRIPT = `
(() => {
  if (window.__glucoCursor) return
  window.__glucoCursor = true
  const install = () => {
    const c = document.createElement('div')
    c.id = '__gluco-cursor'
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l16 9.5-7 1.5-3.5 6.5z" fill="#0d1d2d" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    Object.assign(c.style, { position: 'fixed', left: '0', top: '0', zIndex: 2147483647,
      pointerEvents: 'none', transform: 'translate(-100px,-100px)', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,.35))' })
    const ring = document.createElement('div')
    Object.assign(ring.style, { position: 'fixed', left: '0', top: '0', width: '36px', height: '36px', marginLeft: '-18px',
      marginTop: '-18px', borderRadius: '50%', border: '3px solid #19A99A', opacity: '0', zIndex: 2147483646,
      pointerEvents: 'none', transition: 'transform 400ms cubic-bezier(.2,.8,.2,1), opacity 400ms ease-out' })
    document.documentElement.append(ring, c)
    addEventListener('mousemove', e => { c.style.transform = 'translate(' + (e.clientX - 3) + 'px,' + (e.clientY - 2) + 'px)' }, true)
    addEventListener('mousedown', e => {
      ring.style.transition = 'none'; ring.style.opacity = '1'
      ring.style.transform = 'translate(' + e.clientX + 'px,' + e.clientY + 'px) scale(.4)'
      requestAnimationFrame(() => requestAnimationFrame(() => {
        ring.style.transition = ''; ring.style.opacity = '0'
        ring.style.transform = 'translate(' + e.clientX + 'px,' + e.clientY + 'px) scale(1.4)'
      }))
    }, true)
  }
  if (document.documentElement) install(); else addEventListener('DOMContentLoaded', install)
})()
`

// The Next.js dev-mode badge is not part of the product.
const HIDE_DEV_BADGE = `
addEventListener('DOMContentLoaded', () => {
  const s = document.createElement('style')
  s.textContent = 'nextjs-portal { display: none !important }'
  document.head.append(s)
})
`

export async function prepare(context: BrowserContext) {
  await context.addInitScript(CURSOR_SCRIPT)
  await context.addInitScript(HIDE_DEV_BADGE)
}

export class Clip {
  private frames: { file: string; t: number }[] = []
  private marks: Record<string, number> = {}
  private cdp!: CDPSession
  private start = 0
  private mouse = { x: VIEWPORT.width / 2, y: VIEWPORT.height / 2 }
  private dir: string

  constructor(
    readonly page: Page,
    readonly name: string,
  ) {
    this.dir = join(footageDir, `${name}.frames`)
  }

  async begin() {
    await rm(this.dir, { recursive: true, force: true })
    await mkdir(this.dir, { recursive: true })
    this.cdp = await this.page.context().newCDPSession(this.page)
    let n = 0
    const pending: Promise<unknown>[] = []
    this.cdp.on("Page.screencastFrame", (frame) => {
      const t = frame.metadata.timestamp ?? Date.now() / 1000
      if (!this.start) this.start = t
      const file = `${String(n++).padStart(6, "0")}.jpg`
      this.frames.push({ file, t: t - this.start })
      pending.push(writeFile(join(this.dir, file), Buffer.from(frame.data, "base64")))
      void this.cdp.send("Page.screencastFrameAck", { sessionId: frame.sessionId })
    })
    this.flush = () => Promise.all(pending)
    await this.cdp.send("Page.startScreencast", {
      format: "jpeg",
      quality: 92,
      maxWidth: VIEWPORT.width * SCALE,
      maxHeight: VIEWPORT.height * SCALE,
    })
    await this.page.mouse.move(this.mouse.x, this.mouse.y)
    await this.wait(300)
    this.mark("start")
  }

  private flush: () => Promise<unknown> = async () => {}

  /** Seconds since the first frame. */
  now() {
    return this.start ? Date.now() / 1000 - this.start : 0
  }

  mark(label: string) {
    this.marks[label] = Number(this.now().toFixed(3))
  }

  wait(ms: number) {
    return this.page.waitForTimeout(ms)
  }

  /** Glide the pointer to a point with an ease-in-out path. */
  async moveTo(x: number, y: number, ms = 700) {
    const from = { ...this.mouse }
    const steps = Math.max(8, Math.round(ms / 16))
    for (let i = 1; i <= steps; i++) {
      const p = i / steps
      const e = p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2
      await this.page.mouse.move(from.x + (x - from.x) * e, from.y + (y - from.y) * e)
      await this.page.waitForTimeout(ms / steps)
    }
    this.mouse = { x, y }
  }

  async hover(target: Locator, ms = 700) {
    await target.scrollIntoViewIfNeeded()
    const box = await target.boundingBox()
    if (!box) throw new Error(`${this.name}: no box for ${target}`)
    await this.moveTo(box.x + box.width / 2, box.y + box.height / 2, ms)
  }

  async click(target: Locator, ms = 700) {
    await this.hover(target, ms)
    await this.wait(150)
    await this.page.mouse.down()
    await this.wait(70)
    await this.page.mouse.up()
  }

  async type(target: Locator, text: string, delay = 45) {
    await this.click(target)
    await this.wait(200)
    await this.page.keyboard.type(text, { delay })
  }

  /** Scroll the page smoothly by dy pixels over ms. */
  async scroll(dy: number, ms = 1200) {
    const steps = Math.max(10, Math.round(ms / 16))
    let done = 0
    for (let i = 1; i <= steps; i++) {
      const p = i / steps
      const e = p < 0.5 ? 2 * p * p : 1 - (-2 * p + 2) ** 2 / 2
      const target = Math.round(dy * e)
      await this.page.mouse.wheel(0, target - done)
      done = target
      await this.page.waitForTimeout(ms / steps)
    }
  }

  /** Bounding box of a locator in CSS pixels of the viewport, for push-ins. */
  async region(label: string, target: Locator) {
    this.boxes[label] = await target.boundingBox()
  }

  private boxes: Record<string, { x: number; y: number; width: number; height: number } | null> = {}

  async end() {
    this.mark("end")
    await this.cdp.send("Page.stopScreencast")
    await this.flush()
    const end = this.now()
    // ffmpeg concat list: each frame lasts until the next one.
    const lines = this.frames.map((f, i) => {
      const next = this.frames[i + 1]?.t ?? end
      return `file '${f.file}'\nduration ${Math.max(0.001, next - f.t).toFixed(4)}`
    })
    lines.push(`file '${this.frames.at(-1)?.file}'`)
    await writeFile(join(this.dir, "list.txt"), lines.join("\n") + "\n")
    const out = join(footageDir, `${this.name}.mp4`)
    const ff = Bun.spawnSync([
      "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
      "-i", join(this.dir, "list.txt"),
      "-vf", `fps=30,scale=${VIEWPORT.width * SCALE}:${VIEWPORT.height * SCALE}:flags=lanczos,format=yuv420p`,
      "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-movflags", "+faststart", out,
    ])
    if (ff.exitCode !== 0) throw new Error(ff.stderr.toString())
    await rm(this.dir, { recursive: true, force: true })
    await writeFile(
      join(footageDir, `${this.name}.json`),
      JSON.stringify({ duration: Number(end.toFixed(3)), viewport: VIEWPORT, marks: this.marks, boxes: this.boxes }, null, 2) + "\n",
    )
    console.log(`${this.name}: ${end.toFixed(1)} s, ${this.frames.length} frames`)
  }
}
