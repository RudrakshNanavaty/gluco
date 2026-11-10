import { loadFont as loadFigtree } from "@remotion/google-fonts/Figtree"
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono"

// The app sets Avenir Next. Figtree is the closest open geometric sans.
export const SANS = loadFigtree("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] }).fontFamily
export const MONO = loadMono("normal", { weights: ["400", "600"], subsets: ["latin"] }).fontFamily

export const FPS = 30
export const WIDTH = 1920
export const HEIGHT = 1080

// Colours from the app (front-end/src/app/globals.css) and the README diagram.
export const C = {
  ink: "#0D1A1D",
  ink2: "#13262A",
  line: "rgba(255,255,255,0.09)",
  text: "#F2F7F6",
  muted: "#97ABA8",
  teal: "#19A99A",
  primary: "#1E7B78",
  mint: "#59D8C5",
  paper: "#EEF3F2",
  databricks: "#FF6F00",
  tiger: "#FDB515",
  red: "#E5484D",
}

export const s = (seconds: number) => Math.round(seconds * FPS)
