import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion"
import { C } from "../theme"

/** Dark field with a slow drifting glow, behind every scene. */
export function Backdrop() {
  const frame = useCurrentFrame()
  const x = 30 + Math.sin(frame / 160) * 12
  const y = 20 + Math.cos(frame / 210) * 10
  const drift = interpolate(frame % 600, [0, 600], [0, 48])
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1200px 800px at ${x}% ${y}%, rgba(25,169,154,0.22), transparent 60%),
          radial-gradient(900px 700px at ${100 - x}% ${100 - y}%, rgba(89,216,197,0.08), transparent 60%), ${C.ink}`,
      }}
    >
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${C.line} 1px, transparent 1px), linear-gradient(90deg, ${C.line} 1px, transparent 1px)`,
          backgroundSize: "48px 48px",
          backgroundPosition: `${drift}px ${drift}px`,
          opacity: 0.35,
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 75%)",
        }}
      />
    </AbsoluteFill>
  )
}
