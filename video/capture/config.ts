import { join } from "node:path"

export const BASE_URL = process.env.GLUCO_WEB_URL ?? "http://localhost:3000"

// Captured at 2x so the compositions can push in on a panel and stay sharp.
export const VIEWPORT = { width: 1440, height: 810 }
export const SCALE = 2

const here = import.meta.dir
export const profileDir = (role: "clinician" | "patient") =>
  join(here, "auth", role)
export const footageDir = join(here, "..", "public", "footage")
