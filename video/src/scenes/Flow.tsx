import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion"
import { C, SANS, s } from "../theme"

type Node = { id: string; x: number; y: number; w: number; title: string; sub?: string; color: string; at: number }

// Times are seconds into the narration for this chapter (see src/script.ts).
const NODES: Node[] = [
  { id: "wear", x: 60, y: 400, w: 250, title: "Wearables", sub: "Two public datasets", color: C.mint, at: 0.2 },
  { id: "dbx", x: 370, y: 350, w: 290, title: "Databricks", sub: "Lakeflow pipeline", color: C.databricks, at: 2.0 },
  { id: "feat", x: 720, y: 400, w: 270, title: "24 h features", sub: "+ research score", color: C.databricks, at: 6.2 },
  { id: "tiger", x: 1050, y: 400, w: 220, title: "Tiger Data", sub: "Postgres", color: C.tiger, at: 9.8 },
  { id: "api", x: 1340, y: 400, w: 230, title: "FastAPI", sub: "Read-only", color: C.teal, at: 12.0 },
  { id: "web", x: 1640, y: 250, w: 220, title: "Dashboard", sub: "Next.js", color: C.mint, at: 13.6 },
  { id: "agent", x: 1640, y: 560, w: 220, title: "Agent", sub: "Role-scoped tools", color: "#A78BFA", at: 14.8 },
]
const EDGES: [string, string][] = [
  ["wear", "dbx"],
  ["dbx", "feat"],
  ["feat", "tiger"],
  ["tiger", "api"],
  ["api", "web"],
  ["api", "agent"],
]
const H = 130
const byId = Object.fromEntries(NODES.map((n) => [n.id, n]))

function Layer({ label, color, appear }: { label: string; color: string; appear: number }) {
  return (
    <div style={{ flex: 1, borderRadius: 8, padding: "6px 0", textAlign: "center", fontSize: 18, fontWeight: 700, color: "#1a1a1a", background: color, opacity: appear, transform: `scaleY(${appear})` }}>
      {label}
    </div>
  )
}

export function Flow() {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const at = (sec: number) => spring({ frame: frame - s(sec), fps, config: { damping: 200 } })
  const never = at(19.2)
  return (
    <AbsoluteFill style={{ fontFamily: SANS, color: C.text }}>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {EDGES.map(([a, b]) => {
          const from = byId[a]
          const to = byId[b]
          const x1 = from.x + from.w
          const y1 = from.y + (from.id === "dbx" ? 100 : H / 2)
          const x2 = to.x
          const y2 = to.y + H / 2
          const grow = interpolate(frame, [s(to.at) - 12, s(to.at) + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          const d = `M ${x1} ${y1} C ${x1 + 40} ${y1}, ${x2 - 40} ${y2}, ${x2} ${y2}`
          // A packet travels along each edge once it exists.
          const travel = ((frame - s(to.at)) % 45) / 45
          return (
            <g key={a + b}>
              <path d={d} fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth={3} pathLength={1} style={{ strokeDasharray: `${grow} 1` }} />
              {grow >= 1 ? <Packet d={d} p={travel} color={to.color} /> : null}
            </g>
          )
        })}
      </svg>

      {NODES.map((n) => {
        const p = at(n.at)
        return (
          <div
            key={n.id}
            style={{
              position: "absolute",
              left: n.x,
              top: n.y,
              width: n.w,
              minHeight: H,
              padding: "20px 22px",
              borderRadius: 20,
              background: "rgba(255,255,255,0.06)",
              border: `2px solid ${n.color}`,
              boxShadow: `0 0 ${40 * p}px ${n.color}33`,
              opacity: p,
              transform: `translateY(${interpolate(p, [0, 1], [26, 0])}px) scale(${interpolate(p, [0, 1], [0.94, 1])})`,
            }}
          >
            <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em" }}>{n.title}</div>
            {n.sub ? <div style={{ fontSize: 21, color: C.muted, marginTop: 6 }}>{n.sub}</div> : null}
            {n.id === "dbx" ? (
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <Layer label="Bronze" color="#C98A5A" appear={at(3.0)} />
                <Layer label="Silver" color="#C8D0D4" appear={at(3.6)} />
                <Layer label="Gold" color="#F2C14E" appear={at(4.2)} />
              </div>
            ) : null}
          </div>
        )
      })}

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 150,
          textAlign: "center",
          fontSize: 30,
          fontWeight: 600,
          color: C.muted,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          opacity: at(0),
        }}
      >
        Analytics path → serving path
      </div>

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 800,
          display: "flex",
          justifyContent: "center",
          opacity: never,
          transform: `translateY(${interpolate(never, [0, 1], [20, 0])}px)`,
        }}
      >
        <div style={{ fontSize: 34, fontWeight: 700, padding: "16px 30px", borderRadius: 16, background: "rgba(25,169,154,0.16)", border: `1px solid ${C.teal}` }}>
          Reading the dashboard never triggers training
        </div>
      </div>
    </AbsoluteFill>
  )
}

/** A dot at fraction p along the cubic Bézier in `d`. */
function Packet({ d, p, color }: { d: string; p: number; color: string }) {
  const nums = d.match(/-?\d+(\.\d+)?/g)!.map(Number)
  const [x0, y0, c1x, c1y, c2x, c2y, x1, y1] = nums
  const u = 1 - p
  const x = u * u * u * x0 + 3 * u * u * p * c1x + 3 * u * p * p * c2x + p * p * p * x1
  const y = u * u * u * y0 + 3 * u * u * p * c1y + 3 * u * p * p * c2y + p * p * p * y1
  return <circle cx={x} cy={y} r={7} fill={color} style={{ filter: `drop-shadow(0 0 8px ${color})` }} />
}
