import { AbsoluteFill, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion"
import durations from "../public/voice/durations.json"
import { Backdrop } from "./components/Backdrop"
import { FULL, Footage, type Key, type Rect, type Segment, segmentsFrames } from "./components/Footage"
import { Subtitles, Tag, TitleCard } from "./components/Text"
import { box, mark } from "./footage"
import { Evidence } from "./scenes/Evidence"
import { Flow } from "./scenes/Flow"
import { Idea } from "./scenes/Idea"
import { Outro } from "./scenes/Outro"
import { CHAPTERS, type ChapterId } from "./script"
import { FPS, s } from "./theme"

const TITLE = s(1.6)
// Breathing room after each line before the next chapter starts.
const TAIL = s(0.8)

type Body =
  | { kind: "scene"; render: () => React.ReactNode }
  | { kind: "footage"; segments: Segment[]; camera?: Key[]; tags?: { at: number; until?: number; text: string }[] }

const R = (x: number, y: number, w: number, h: number): Rect => ({ x, y, w, h })
const seg = (clip: string, from: number | string, to: number | string, rate = 1): Segment => ({
  clip,
  from: typeof from === "string" ? mark(clip, from) : from,
  to: typeof to === "string" ? mark(clip, to) : to,
  rate,
})

// What plays under each line. Camera and tag times are seconds into the body.
const BODIES: Record<ChapterId, Body> = {
  idea: { kind: "scene", render: () => <Idea /> },
  flow: { kind: "scene", render: () => <Flow /> },
  signin: {
    kind: "footage",
    segments: [seg("landing", "start", "end")],
    camera: [
      { t: 0, rect: FULL },
      { t: 5.6, rect: FULL },
      { t: 6.8, rect: R(640, 268, 740, 416) },
    ],
    tags: [
      { at: 6.6, until: 8.6, text: "Clinician → their patient panel" },
      { at: 9, text: "Patient → only their own data" },
    ],
  },
  panel: {
    kind: "footage",
    segments: [seg("panel", "start", "end", 1.05)],
    camera: [
      { t: 0, rect: FULL },
      { t: 2.5, rect: FULL },
      { t: 4.2, rect: R(100, 190, 1240, 340) },
      { t: 8.5, rect: R(100, 340, 1240, 300) },
      { t: 14.5, rect: FULL },
    ],
  },
  detail: {
    kind: "footage",
    segments: [seg("detail", "open", 4.6), seg("detail", "loaded", "changed", 1.5), seg("detail", "changed", "end", 1.35)],
    camera: [
      { t: 0, rect: FULL },
      { t: 3.4, rect: FULL },
      { t: 4.4, rect: R(700, 80, 740, 416) },
      { t: 9.8, rect: FULL },
      { t: 15, rect: FULL },
      { t: 16.5, rect: R(60, 40, 900, 506) },
      { t: 23, rect: FULL },
    ],
    tags: [{ at: 15.5, until: 22, text: "Associations, not causes" }],
  },
  live: {
    kind: "footage",
    segments: [seg("live", "start", "end")],
    camera: [
      { t: 0, rect: FULL },
      { t: 1.2, rect: R(0, 40, 720, 405) },
      { t: 6.5, rect: box("live", "tiles", 40) },
      { t: 13, rect: FULL },
    ],
    tags: [{ at: 7.5, until: 15, text: "Labelled simulation of real minute data" }],
  },
  patient: {
    kind: "footage",
    segments: [seg("patient", "start", "end", 1.2)],
    camera: [
      { t: 0, rect: FULL },
      { t: 2.5, rect: R(90, 150, 1260, 709) },
      { t: 6, rect: FULL },
    ],
    tags: [{ at: 10, until: 15, text: "Always an estimate, never a diagnosis" }],
  },
  chat: {
    kind: "footage",
    segments: [
      // Body seconds at each cut: 5.4, 10.6, 18.0, 20.0, 25.1, 29.1.
      seg("chat", "start", "ask:Which patients need follow-up?", 1.5),
      seg("chat", "ask:Which patients need follow-up?", "answered:Which patients need follow-up?", 4),
      seg("chat", "answered:Which patients need follow-up?", "ask:Build a widget ranking the 5 lowest Gluco Scores", 1.6),
      seg("chat", "ask:Build a widget ranking the 5 lowest Gluco Scores", "answered:Build a widget ranking the 5 lowest Gluco Scores", 3),
      seg("chat", "answered:Build a widget ranking the 5 lowest Gluco Scores", mark("chat", "close") + 1.2, 1.4),
      seg("chat", "pinned", "end"),
    ],
    camera: [
      { t: 0, rect: FULL },
      { t: 1.2, rect: FULL },
      { t: 2.4, rect: R(620, 40, 820, 461) },
      { t: 23.6, rect: R(620, 40, 820, 461) },
      { t: 24.6, rect: FULL },
    ],
    tags: [{ at: 25.3, text: "Pinned: re-runs as data streams in" }],
  },
  guard: {
    kind: "footage",
    segments: [
      seg("patient-chat", "ask:Why did my score change?", "answered:Why did my score change?", 3),
      seg("patient-chat", "answered:Why did my score change?", "ask:What is Patient 013's Gluco Score?", 1.3),
      seg("patient-chat", "ask:What is Patient 013's Gluco Score?", "answered:What is Patient 013's Gluco Score?", 2),
      seg("patient-chat", "answered:What is Patient 013's Gluco Score?", "end"),
    ],
    camera: [{ t: 0, rect: R(700, 40, 740, 416) }],
  },
  evidence: { kind: "scene", render: () => <Evidence /> },
  outro: { kind: "scene", render: () => <Outro /> },
}

const voice = (id: ChapterId) => s((durations as Record<string, number>)[id])

/** Each chapter's body runs as long as its line or its footage, whichever is longer. */
const bodyFrames = (id: ChapterId) => {
  const body = BODIES[id]
  const footage = body.kind === "footage" ? segmentsFrames(body.segments) : 0
  return Math.max(voice(id) + TAIL, footage)
}

export const CHAPTER_FRAMES = CHAPTERS.map((c) => (c.id === "idea" ? 0 : TITLE) + bodyFrames(c.id))
export const WALKTHROUGH_FRAMES = CHAPTER_FRAMES.reduce((a, b) => a + b, 0)

function FootageBody({ body }: { body: Extract<Body, { kind: "footage" }> }) {
  const frame = useCurrentFrame()
  const enter = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" })
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 40 }}>
      <div style={{ opacity: enter, transform: `scale(${interpolate(enter, [0, 1], [0.96, 1])})` }}>
        <Footage segments={body.segments} camera={body.camera} />
      </div>
      {body.tags?.map((tag) => (
        <div key={tag.text} style={{ position: "absolute", left: 200, top: 110 }}>
          <Tag delay={s(tag.at)} out={tag.until === undefined ? undefined : s(tag.until)}>
            {tag.text}
          </Tag>
        </div>
      ))}
    </AbsoluteFill>
  )
}

function Chapter({ index, id, title, line }: { index: number; id: ChapterId; title: string; line: string }) {
  const { durationInFrames } = useVideoConfig()
  const body = BODIES[id]
  const title_ = id === "idea" ? 0 : TITLE
  return (
    <AbsoluteFill>
      {title_ ? (
        <Sequence durationInFrames={title_}>
          <TitleCard index={index} title={title} />
        </Sequence>
      ) : null}
      <Sequence from={title_} durationInFrames={durationInFrames - title_}>
        {body.kind === "scene" ? body.render() : <FootageBody body={body} />}
        <Html5Audio src={staticFile(`voice/${id}.wav`)} />
        <Subtitles line={line} seconds={voice(id) / FPS} />
      </Sequence>
    </AbsoluteFill>
  )
}

export function Walkthrough() {
  let at = 0
  return (
    <AbsoluteFill>
      <Backdrop />
      {CHAPTERS.map((c, i) => {
        const from = at
        at += CHAPTER_FRAMES[i]
        return (
          <Sequence key={c.id} from={from} durationInFrames={CHAPTER_FRAMES[i]} name={c.title}>
            <Chapter index={i + 1} id={c.id} title={c.title} line={c.line} />
          </Sequence>
        )
      })}
    </AbsoluteFill>
  )
}
