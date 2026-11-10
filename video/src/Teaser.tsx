import { AbsoluteFill, Easing, Html5Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion"
import durations from "../public/voice/durations.json"
import { Backdrop } from "./components/Backdrop"
import { FULL, Footage, type Key, type Rect, type Segment } from "./components/Footage"
import { Logo } from "./components/Logo"
import { Rise, Tag } from "./components/Text"
import { box, mark } from "./footage"
import { Outro } from "./scenes/Outro"
import type { TeaserLineId } from "./script"
import { C, s } from "./theme"

const R = (x: number, y: number, w: number, h: number): Rect => ({ x, y, w, h })

type Shot = { seconds: number; voice: TeaserLineId; caption: string; segments: Segment[]; camera: Key[] }

// Each line starts a beat after its shot cuts in and ends a beat before the next.
const LEAD = 4
const GAP = 3
const voiced = (seconds: number, voice: TeaserLineId) =>
  Math.max(s(seconds), LEAD + s((durations as Record<string, number>)[voice]) + GAP)

// After the intro says what Gluco is, each shot shows what its line describes.
// Shots are as long as their lines; `seconds` is only a floor.
const SHOTS: Shot[] = [
  {
    seconds: 3,
    voice: "t-live",
    caption: "Heart rate, movement, skin temperature: live",
    segments: [{ clip: "live", from: mark("live", "hover") + 2, to: mark("live", "end"), rate: 1 }],
    camera: [{ t: 0, rect: R(60, 40, 1320, 400) }, { t: 4.4, rect: box("live", "tiles", 30) }],
  },
  {
    seconds: 3,
    voice: "t-score",
    caption: "A daily research score, never a diagnosis",
    segments: [{ clip: "patient", from: mark("patient", "start"), to: mark("patient", "vitals"), rate: 1 }],
    camera: [{ t: 0, rect: FULL }, { t: 2, rect: R(100, 100, 1240, 500) }],
  },
  {
    // The panel, then a cut to one patient's "What changed" table.
    seconds: 3,
    voice: "t-panel",
    caption: "For clinicians: the whole panel, and what changed",
    segments: [
      { clip: "panel", from: mark("panel", "start"), to: mark("panel", "start") + 3.6, rate: 1.6 },
      { clip: "detail", from: mark("detail", "changed") + 1.6, to: mark("detail", "position"), rate: 1.6 },
    ],
    camera: [
      { t: 0, rect: FULL },
      { t: 2.2, rect: R(100, 190, 1240, 440) },
      { t: 2.25, rect: R(60, 40, 960, 540) },
      { t: 4.9, rect: R(60, 40, 880, 495) },
    ],
  },
  {
    // The answer plays at 10x (about 2.4 s), then the panel with the widget pinned.
    seconds: 3,
    voice: "t-chat",
    caption: "Ask Gluco, in plain language",
    segments: [
      { clip: "chat", from: mark("chat", "ask:Which patients need follow-up?") - 1.6, to: mark("chat", "answered:Which patients need follow-up?") + 1.5, rate: 10 },
      { clip: "chat", from: mark("chat", "pinned") - 0.2, to: mark("chat", "end"), rate: 1 },
    ],
    camera: [
      { t: 0, rect: R(600, 40, 840, 473) },
      { t: 2.35, rect: R(600, 40, 840, 473) },
      { t: 2.4, rect: R(80, 190, 860, 484) },
    ],
  },
]

const INTRO = voiced(3, "t-intro")
const OUTRO = voiced(3, "t-outro")
export const TEASER_FRAMES = INTRO + SHOTS.reduce((n, shot) => n + voiced(shot.seconds, shot.voice), 0) + OUTRO

function Voice({ id }: { id: TeaserLineId }) {
  return (
    <Sequence from={LEAD} layout="none">
      <Html5Audio src={staticFile(`voice/${id}.wav`)} />
    </Sequence>
  )
}

function ShotView({ shot }: { shot: Shot }) {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()
  const enter = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) })
  const exit = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], { extrapolateLeft: "clamp" })
  const tilt = interpolate(frame, [0, durationInFrames], [6, -2])
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", perspective: 2400 }}>
      <div
        style={{
          opacity: Math.min(enter, exit),
          transform: `translateX(${interpolate(enter, [0, 1], [80, 0])}px) rotateY(${tilt}deg) scale(${interpolate(enter, [0, 1], [0.94, 1])})`,
          marginTop: 70,
        }}
      >
        <Footage segments={shot.segments} camera={shot.camera} width={1540} />
      </div>
      <div style={{ position: "absolute", left: 110, top: 46, opacity: exit }}>
        <Tag delay={4}>{shot.caption}</Tag>
      </div>
    </AbsoluteFill>
  )
}

// Says what Gluco is and who it's for before any feature appears. The two
// audience chips land as the line reaches "for patients and their care team".
function Intro() {
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 34 }}>
      <Logo size={150} />
      <Rise size={50} weight={600} color={C.muted} delay={16}>
        Wearable signals. Daily metabolic context.
      </Rise>
      <div style={{ display: "flex", gap: 20, marginTop: 6 }}>
        {["For patients", "For care teams"].map((label, i) => (
          <Rise key={label} size={34} weight={700} color={C.mint} delay={s(4.3 + i * 0.5)}>
            <span style={{ display: "inline-block", padding: "10px 24px", borderRadius: 999, border: `2px solid ${C.teal}`, background: "rgba(25,169,154,0.14)" }}>
              {label}
            </span>
          </Rise>
        ))}
      </div>
    </AbsoluteFill>
  )
}

export function Teaser() {
  let at = INTRO
  return (
    <AbsoluteFill>
      <Backdrop />
      <Sequence durationInFrames={INTRO}>
        <Intro />
        <Voice id="t-intro" />
      </Sequence>
      {SHOTS.map((shot) => {
        const from = at
        const frames = voiced(shot.seconds, shot.voice)
        at += frames
        return (
          <Sequence key={shot.caption} from={from} durationInFrames={frames} name={shot.caption}>
            <ShotView shot={shot} />
            <Voice id={shot.voice} />
          </Sequence>
        )
      })}
      <Sequence from={at} durationInFrames={OUTRO}>
        <Outro qr={false} />
        <Voice id="t-outro" />
      </Sequence>
    </AbsoluteFill>
  )
}
