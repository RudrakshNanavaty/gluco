import { Freeze, OffthreadVideo, Sequence, staticFile, useCurrentFrame, interpolate, Easing } from "remotion"
import { C, FPS } from "../theme"

// Captures are 1440x810 CSS px recorded at 2x. Camera rects use CSS px.
export const VIEW = { width: 1440, height: 810 }

export type Rect = { x: number; y: number; w: number; h: number }
export const FULL: Rect = { x: 0, y: 0, w: VIEW.width, h: VIEW.height }

/** A stretch of one recorded clip, in source seconds, played at `rate`. */
export type Segment = { clip: string; from: number; to: number; rate?: number }

/** Camera keyframe: at `t` seconds into the scene, frame this rect. */
export type Key = { t: number; rect: Rect }

export const segmentFrames = (seg: Segment) => Math.round(((seg.to - seg.from) / (seg.rate ?? 1)) * FPS)
export const segmentsFrames = (segs: Segment[]) => segs.reduce((n, seg) => n + segmentFrames(seg), 0)

/** Plays segments back to back, then holds the last frame for the rest of the scene. */
function Reel({ segments }: { segments: Segment[] }) {
  let at = 0
  const last = segments.at(-1)!
  const total = segmentsFrames(segments)
  return (
    <>
      {segments.map((seg, i) => {
        const len = segmentFrames(seg)
        const from = at
        at += len
        return (
          <Sequence key={i} from={from} durationInFrames={len} layout="none">
            <OffthreadVideo
              src={staticFile(`footage/${seg.clip}.mp4`)}
              trimBefore={Math.round(seg.from * FPS)}
              playbackRate={seg.rate ?? 1}
              muted
              style={{ width: "100%", height: "100%", display: "block" }}
            />
          </Sequence>
        )
      })}
      <Sequence from={total} layout="none">
        <Freeze frame={Math.round(last.to * FPS) - 1}>
          <OffthreadVideo
            src={staticFile(`footage/${last.clip}.mp4`)}
            muted
            style={{ width: "100%", height: "100%", display: "block" }}
          />
        </Freeze>
      </Sequence>
    </>
  )
}

const ease = Easing.bezier(0.65, 0, 0.35, 1)

function cameraAt(keys: Key[], seconds: number): Rect {
  if (keys.length === 0) return FULL
  if (seconds <= keys[0].t) return keys[0].rect
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1]
    const b = keys[i]
    if (seconds <= b.t) {
      // Hold on `a`, then move to `b` over the last 1.1 s before b.t.
      const moveStart = Math.max(a.t, b.t - 1.1)
      const p = interpolate(seconds, [moveStart, b.t], [0, 1], {
        easing: ease,
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
      return {
        x: a.rect.x + (b.rect.x - a.rect.x) * p,
        y: a.rect.y + (b.rect.y - a.rect.y) * p,
        w: a.rect.w + (b.rect.w - a.rect.w) * p,
        h: a.rect.h + (b.rect.h - a.rect.h) * p,
      }
    }
  }
  return keys.at(-1)!.rect
}

/**
 * The app inside a browser window, with a camera that pushes in on regions.
 * Rects are fitted to the window's 16:9 by their width or height, whichever
 * is the tighter fit, and kept inside the capture.
 */
export function Footage({
  segments,
  camera = [],
  width = 1600,
  url = "localhost:3000",
}: {
  segments: Segment[]
  camera?: Key[]
  width?: number
  url?: string
}) {
  const frame = useCurrentFrame()
  const height = (width * VIEW.height) / VIEW.width
  const r = cameraAt(camera, frame / FPS)
  const zoom = Math.min(VIEW.width / r.w, VIEW.height / r.h)
  const cx = r.x + r.w / 2
  const cy = r.y + r.h / 2
  const vw = VIEW.width / zoom
  const vh = VIEW.height / zoom
  const left = Math.min(Math.max(cx - vw / 2, 0), VIEW.width - vw)
  const top = Math.min(Math.max(cy - vh / 2, 0), VIEW.height - vh)
  const k = width / VIEW.width
  return (
    <div
      style={{
        width,
        borderRadius: 18,
        overflow: "hidden",
        background: C.paper,
        boxShadow: "0 40px 120px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.08)",
      }}
    >
      <div
        style={{
          height: 40,
          background: "#E3EAE8",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "0 16px",
          borderBottom: "1px solid #D2DCDA",
        }}
      >
        {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
          <span key={c} style={{ width: 13, height: 13, borderRadius: 99, background: c }} />
        ))}
        <span
          style={{
            margin: "0 auto",
            fontFamily: "system-ui, sans-serif",
            fontSize: 15,
            color: "#5B6C69",
            background: "#F4F7F6",
            padding: "4px 120px",
            borderRadius: 8,
          }}
        >
          {url}
        </span>
      </div>
      <div style={{ width, height, overflow: "hidden", position: "relative" }}>
        <div
          style={{
            position: "absolute",
            width: VIEW.width * k,
            height: VIEW.height * k,
            transformOrigin: "0 0",
            transform: `scale(${zoom}) translate(${-left * k}px, ${-top * k}px)`,
          }}
        >
          <Reel segments={segments} />
        </div>
      </div>
    </div>
  )
}
