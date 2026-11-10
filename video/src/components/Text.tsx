import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion"
import { C, FPS, SANS } from "../theme"

const enter = (frame: number, fps: number, delay = 0) =>
  spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: 24 })

/** Short label that rises in: used for teaser captions and chapter kickers. */
export function Rise({
  children,
  delay = 0,
  size = 64,
  weight = 700,
  color = C.text,
  out,
}: {
  children: React.ReactNode
  delay?: number
  size?: number
  weight?: number
  color?: string
  /** Frame at which the text fades away again. */
  out?: number
}) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const p = enter(frame, fps, delay)
  const leave = out === undefined ? 1 : interpolate(frame, [out, out + 10], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  return (
    <div
      style={{
        fontFamily: SANS,
        fontSize: size,
        fontWeight: weight,
        letterSpacing: "-0.025em",
        lineHeight: 1.1,
        color,
        opacity: p * leave,
        transform: `translateY(${interpolate(p, [0, 1], [28, 0])}px)`,
      }}
    >
      {children}
    </div>
  )
}

/** Chapter opener: number, title, and a growing rule. */
export function TitleCard({ index, title }: { index: number; title: string }) {
  const frame = useCurrentFrame()
  const { fps, durationInFrames } = useVideoConfig()
  const rule = enter(frame, fps, 4)
  const fade = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], { extrapolateLeft: "clamp" })
  return (
    <AbsoluteFill style={{ justifyContent: "center", paddingLeft: 200, opacity: fade }}>
      <Rise size={34} weight={600} color={C.mint}>
        {String(index).padStart(2, "0")}
      </Rise>
      <div style={{ height: 4, width: 120 * rule, background: C.teal, borderRadius: 4, margin: "22px 0 26px" }} />
      <Rise size={104} weight={800} delay={6}>
        {title}
      </Rise>
    </AbsoluteFill>
  )
}

/**
 * Narration shown as subtitles: the line is split into sentences, each shown
 * for a share of the audio proportional to its length.
 */
export function Subtitles({ line, seconds, offset = 0 }: { line: string; seconds: number; offset?: number }) {
  const frame = useCurrentFrame()
  const t = frame / FPS - offset
  const parts = line.match(/[^.?!:]+[.?!:]?/g)?.map((p) => p.trim()).filter(Boolean) ?? [line]
  const total = parts.reduce((n, p) => n + p.length, 0)
  let start = 0.15
  const speaking = seconds - 0.3
  const current = parts.find((p) => {
    const len = (p.length / total) * speaking
    const hit = t >= start && t < start + len
    start += len
    return hit
  })
  if (!current) return null
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 34,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <span
        style={{
          maxWidth: 1400,
          textAlign: "center",
          fontFamily: SANS,
          fontWeight: 600,
          fontSize: 34,
          lineHeight: 1.3,
          color: "#fff",
          background: "rgba(8,18,20,0.82)",
          padding: "10px 22px",
          borderRadius: 12,
          boxDecorationBreak: "clone",
          WebkitBoxDecorationBreak: "clone",
        }}
      >
        {current}
      </span>
    </div>
  )
}

/** Pill caption that slides in from the left, used over footage. */
export function Tag({ children, delay = 0, out }: { children: React.ReactNode; delay?: number; out?: number }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const p = enter(frame, fps, delay)
  const leave = out === undefined ? 1 : interpolate(frame, [out, out + 10], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 14,
        fontFamily: SANS,
        fontWeight: 700,
        fontSize: 40,
        letterSpacing: "-0.02em",
        color: C.text,
        background: "rgba(13,26,29,0.88)",
        border: `1px solid rgba(89,216,197,0.35)`,
        padding: "14px 26px",
        borderRadius: 16,
        opacity: p * leave,
        transform: `translateX(${interpolate(p, [0, 1], [-40, 0])}px)`,
        boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
      }}
    >
      <span style={{ width: 12, height: 12, borderRadius: 99, background: C.mint }} />
      {children}
    </div>
  )
}
