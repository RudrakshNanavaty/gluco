// Times of day are shown in the viewer's local timezone. Day-level labels
// (`formatReplayDay`, daily axis ticks) stay in UTC so they match the
// back-end's UTC day buckets.

const options: Intl.DateTimeFormatOptions = {
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
}
const localParts = new Intl.DateTimeFormat("en-US", options)
const utcParts = new Intl.DateTimeFormat("en-US", {
  ...options,
  timeZone: "UTC",
})

function pieces(iso: string, utc = false) {
  const out: Record<string, string> = {}
  for (const part of (utc ? utcParts : localParts).formatToParts(new Date(iso)))
    out[part.type] = part.value
  return out
}

/** "Tue 29 Sep, 14:00" */
export function formatReplayTime(iso: string | null | undefined): string {
  if (!iso) return "—"
  const p = pieces(iso)
  return `${p.weekday} ${p.day} ${p.month}, ${p.hour}:${p.minute}`
}

/** "14:07:12", for live sensor times. */
export function formatClockTime(iso: string | null | undefined): string {
  if (!iso) return "—"
  const p = pieces(iso)
  const seconds = String(new Date(iso).getSeconds()).padStart(2, "0")
  return `${p.hour}:${p.minute}:${seconds}`
}

/** "Tue 29 Sep" */
export function formatReplayDay(iso: string | null | undefined): string {
  if (!iso) return "—"
  const p = pieces(iso, true)
  return `${p.weekday} ${p.day} ${p.month}`
}

/** Axis tick for a point time, by the query's bucket. */
export function formatTick(iso: string, bucket: string): string {
  const p = pieces(iso, bucket === "day")
  if (bucket === "day") return `${p.weekday} ${p.day}`
  return `${p.weekday} ${p.hour}:${p.minute}`
}

/** 1 -> "1st", 22 -> "22nd", 13 -> "13th". */
export function ordinal(n: number): string {
  const value = Math.round(n)
  const mod100 = value % 100
  if (mod100 >= 11 && mod100 <= 13) return `${value}th`
  const suffix = { 1: "st", 2: "nd", 3: "rd" }[value % 10] ?? "th"
  return `${value}${suffix}`
}
