import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion"
import evidence from "../../public/evidence.json"
import { C, MONO, SANS, s } from "../theme"

// Figures from the README's "Model at a glance".
const ACCURACY = 60.4
const BASELINE = 53.3

/** Real test-suite summaries (public/evidence.json, from `bun evidence`) and the evaluation result. */
export function Evidence() {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const at = (sec: number) => spring({ frame: frame - s(sec), fps, config: { damping: 200 } })
  const lines = evidence.suites.flatMap((suite) => [
    { text: `$ ${suite.command}`, kind: "cmd" as const },
    ...suite.summary.map((text) => ({ text, kind: "out" as const })),
  ])
  const shown = Math.floor(interpolate(frame, [s(0.5), s(7)], [0, lines.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))
  const bars = interpolate(frame, [s(10), s(13)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
  return (
    <AbsoluteFill style={{ fontFamily: SANS, color: C.text, flexDirection: "row", gap: 60, padding: "150px 120px", alignItems: "flex-start" }}>
      <div
        style={{
          flex: 1.15,
          background: "#081214",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 18,
          overflow: "hidden",
          boxShadow: "0 40px 120px rgba(0,0,0,0.5)",
          opacity: at(0),
        }}
      >
        <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.08)", color: C.muted, fontSize: 20, fontWeight: 600 }}>
          Test suites · run {evidence.ranAt}
        </div>
        <div style={{ padding: "20px 24px", fontFamily: MONO, fontSize: 22, lineHeight: 1.6 }}>
          {lines.slice(0, shown).map((line, i) => (
            <div key={i} style={{ color: line.kind === "cmd" ? C.mint : /fail|error/i.test(line.text) && !/ 0 fail/.test(line.text) ? C.red : "#D8E4E2", whiteSpace: "pre-wrap" }}>
              {line.text}
            </div>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ opacity: at(8.5), fontSize: 26, fontWeight: 600, color: C.muted, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Held-out evaluation
        </div>
        <div style={{ opacity: at(9), fontSize: 46, fontWeight: 800, letterSpacing: "-0.02em", lineHeight: 1.15 }}>
          660 real 24 h windows
          <br />
          from 15 participants
        </div>
        {[
          { label: "Participant-weighted accuracy", value: ACCURACY, color: C.mint },
          { label: "Prior baseline", value: BASELINE, color: "rgba(255,255,255,0.35)" },
        ].map((bar) => (
          <div key={bar.label} style={{ opacity: at(9.8) }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26, marginBottom: 10 }}>
              <span style={{ color: C.muted }}>{bar.label}</span>
              <span style={{ fontWeight: 800 }}>{(bar.value * bars).toFixed(1)}%</span>
            </div>
            <div style={{ height: 22, borderRadius: 11, background: "rgba(255,255,255,0.08)" }}>
              <div style={{ height: "100%", width: `${bar.value * bars}%`, borderRadius: 11, background: bar.color }} />
            </div>
          </div>
        ))}
        <div
          style={{
            opacity: at(18),
            marginTop: 10,
            fontSize: 28,
            fontWeight: 700,
            padding: "16px 22px",
            borderRadius: 14,
            border: `1px solid ${C.tiger}`,
            background: "rgba(253,181,21,0.1)",
          }}
        >
          Evidence the pipeline runs end to end, not clinical validation.
        </div>
      </div>
    </AbsoluteFill>
  )
}
