import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion"
import { C, SANS } from "../theme"

/** The Gluco ring (front-end/src/components/brand.tsx), drawn on as it enters. */
export function Ring({ size, delay = 0, color = C.mint }: { size: number; delay?: number; color?: string }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const p = spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: 40 })
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ overflow: "visible" }}>
      <circle cx="12" cy="12" r="8.5" stroke={color} strokeOpacity={0.22 * p} strokeWidth="3.5" />
      <circle
        cx="12"
        cy="12"
        r="8.5"
        stroke={color}
        strokeWidth="3.5"
        strokeLinecap="round"
        pathLength="100"
        strokeDasharray={`${72 * p} 100`}
        transform={`rotate(${135 - 90 * (1 - p)} 12 12)`}
      />
    </svg>
  )
}

export function Logo({ size = 120, delay = 0 }: { size?: number; delay?: number }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const word = spring({ frame: frame - delay - 10, fps, config: { damping: 200 } })
  return (
    <div style={{ display: "flex", alignItems: "center", gap: size * 0.16 }}>
      <Ring size={size} delay={delay} />
      <span
        style={{
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: size * 0.95,
          letterSpacing: "-0.04em",
          color: C.text,
          opacity: word,
          transform: `translateX(${interpolate(word, [0, 1], [-24, 0])}px)`,
        }}
      >
        gluco
      </span>
    </div>
  )
}
