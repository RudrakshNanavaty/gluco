// Metadata written by capture/record.ts next to each clip: duration, named
// marks (seconds into the clip) and the boxes of regions worth pushing in on.
import chat from "../public/footage/chat.json"
import detail from "../public/footage/detail.json"
import landing from "../public/footage/landing.json"
import live from "../public/footage/live.json"
import panel from "../public/footage/panel.json"
import patient from "../public/footage/patient.json"
import patientChat from "../public/footage/patient-chat.json"
import type { Rect } from "./components/Footage"

type Meta = { duration: number; marks: Record<string, number>; boxes: Record<string, { x: number; y: number; width: number; height: number } | null> }

export const CLIPS: Record<string, Meta> = {
  chat,
  detail,
  landing,
  live,
  panel,
  patient,
  "patient-chat": patientChat,
}

export const mark = (clip: string, name: string) => {
  const t = CLIPS[clip]?.marks[name]
  if (t === undefined) throw new Error(`No mark ${name} in ${clip}`)
  return t
}

/** A box from the capture, padded, as a camera rect. */
export const box = (clip: string, name: string, pad = 24): Rect => {
  const b = CLIPS[clip]?.boxes[name]
  if (!b) throw new Error(`No box ${name} in ${clip}`)
  return { x: b.x - pad, y: b.y - pad, w: b.width + pad * 2, h: b.height + pad * 2 }
}
