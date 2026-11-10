import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion"
import { Ring } from "../components/Logo"
import { C, SANS, s } from "../theme"

const SIGNALS = [
  { label: "Heart rate", unit: "bpm", color: "#FF7A7A", freq: 0.21, amp: 18 },
  { label: "Movement", unit: "g", color: C.mint, freq: 0.09, amp: 26 },
  { label: "Skin temperature", unit: "°C", color: "#FFB547", freq: 0.03, amp: 12 },
]

function Wave({ color, freq, amp, frame }: { color: string; freq: number; amp: number; frame: number }) {
  const pts = Array.from({ length: 60 }, (_, i) => {
    const x = i * 6
    const y = 40 + Math.sin((i + frame * 0.6) * freq * 2) * amp * 0.6 + Math.sin((i + frame) * freq * 5.3) * amp * 0.25
    return `${x},${y.toFixed(1)}`
  })
  return (
    <svg width={354} height={80}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Card({ children, appear, style }: { children: React.ReactNode; appear: number; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 22,
        padding: "20px 26px",
        opacity: appear,
        transform: `translateY(${interpolate(appear, [0, 1], [30, 0])}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** Wearables on one side, lab results on the other, Gluco between, glucose left out. */
export function Idea() {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const at = (sec: number) => spring({ frame: frame - s(sec), fps, config: { damping: 200 } })
  const join = interpolate(frame, [s(11), s(13)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  const question = at(12.5)
  const strike = interpolate(frame, [s(16.5), s(17.3)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  const label = { fontFamily: SANS, color: C.muted, fontSize: 26, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" as const }
  return (
    <AbsoluteFill style={{ fontFamily: SANS, color: C.text }}>
      <div style={{ position: "absolute", left: 140, top: 110, display: "flex", flexDirection: "column", gap: 22 }}>
        <div style={{ ...label, opacity: at(0.3) }}>Wearables · all day</div>
        {SIGNALS.map((sig, i) => (
          <Card key={sig.label} appear={at(0.6 + i * 0.5)} style={{ width: 420 }}>
            <div style={{ fontSize: 30, fontWeight: 700 }}>{sig.label}</div>
            <Wave color={sig.color} freq={sig.freq} amp={sig.amp} frame={frame} />
          </Card>
        ))}
      </div>

      <div style={{ position: "absolute", right: 140, top: 200, width: 440, display: "flex", flexDirection: "column", gap: 22 }}>
        <div style={{ ...label, opacity: at(5.5) }}>Lab results · now and then</div>
        <Card appear={at(5.8)}>
          <div style={{ fontSize: 30, fontWeight: 700 }}>HbA1c</div>
          <div style={{ display: "flex", gap: 14, marginTop: 16 }}>
            {["Jan", "Apr", "Oct"].map((m, i) => (
              <div key={m} style={{ opacity: at(6.4 + i * 0.35), background: "rgba(255,255,255,0.08)", borderRadius: 12, padding: "10px 16px", fontSize: 24, color: C.muted }}>
                {m}
              </div>
            ))}
          </div>
        </Card>
        <Card appear={at(15.5)} style={{ borderColor: "rgba(229,72,77,0.5)", position: "relative" }}>
          <div style={{ fontSize: 30, fontWeight: 700, color: C.muted }}>Glucose</div>
          <div style={{ fontSize: 22, color: C.muted, marginTop: 6 }}>Not a model input</div>
          <div style={{ position: "absolute", left: 20, right: 20, top: "50%", height: 4, background: C.red, borderRadius: 4, transformOrigin: "left", transform: `scaleX(${strike}) rotate(-6deg)` }} />
        </Card>
      </div>

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {[220, 380, 540].map((y) => (
          <path key={y} d={`M 570 ${y + 30} C 760 ${y + 30}, 760 470, 900 470`} fill="none" stroke={C.teal} strokeWidth={3} strokeDasharray="6 10" pathLength={1} style={{ strokeDasharray: `${join} 1`, opacity: 0.8 }} />
        ))}
        <path d="M 1340 330 C 1180 330, 1180 470, 1020 470" fill="none" stroke={C.teal} strokeWidth={3} pathLength={1} style={{ strokeDasharray: `${join} 1`, opacity: 0.8 }} />
      </svg>

      <div style={{ position: "absolute", left: 960 - 60, top: 410, opacity: at(10.5), transform: `scale(${interpolate(at(10.5), [0, 1], [0.6, 1])})` }}>
        <Ring size={120} delay={s(10.5)} />
      </div>

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 190,
          textAlign: "center",
          fontSize: 50,
          fontWeight: 700,
          letterSpacing: "-0.02em",
          lineHeight: 1.25,
          opacity: question,
          transform: `translateY(${interpolate(question, [0, 1], [24, 0])}px)`,
        }}
      >
        Can recent wearable patterns give useful context
        <br />
        <span style={{ color: C.mint }}>without glucose as an input?</span>
      </div>
    </AbsoluteFill>
  )
}
