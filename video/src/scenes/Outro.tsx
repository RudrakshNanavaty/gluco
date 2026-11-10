import QRCode from "qrcode"
import { AbsoluteFill } from "remotion"
import { Logo } from "../components/Logo"
import { Rise } from "../components/Text"
import { C, SANS } from "../theme"

export const REPO = "github.com/RudrakshNanavaty/gluco"

function QR({ text, size }: { text: string; size: number }) {
  const qr = QRCode.create(text, { errorCorrectionLevel: "M" })
  const n = qr.modules.size
  const cells: React.ReactNode[] = []
  for (let y = 0; y < n; y++)
    for (let x = 0; x < n; x++)
      if (qr.modules.get(x, y)) cells.push(<rect key={`${x}-${y}`} x={x} y={y} width={1.02} height={1.02} />)
  return (
    <svg width={size} height={size} viewBox={`-2 -2 ${n + 4} ${n + 4}`} style={{ background: "#fff", borderRadius: 16 }}>
      <g fill={C.ink}>{cells}</g>
    </svg>
  )
}

/** End card: logo, repo link and QR code, and the research-prototype line. */
export function Outro({ qr = true }: { qr?: boolean }) {
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 40, fontFamily: SANS }}>
      <Logo size={130} />
      <Rise size={44} weight={600} color={C.muted} delay={14}>
        Wearable signals. Daily metabolic context.
      </Rise>
      <div style={{ display: "flex", alignItems: "center", gap: 40, marginTop: 10 }}>
        {qr ? (
          <Rise delay={22}>
            <QR text={`https://${REPO}`} size={200} />
          </Rise>
        ) : null}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Rise size={40} weight={700} delay={26}>
            {REPO}
          </Rise>
          <Rise size={30} weight={500} color={C.muted} delay={32}>
            Research prototype · not a medical device · AGPL-3.0
          </Rise>
        </div>
      </div>
    </AbsoluteFill>
  )
}
