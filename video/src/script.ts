// Narration for the walk-through, one entry per chapter. `bun voice` turns each
// line into public/voice/<id>.wav, and the compositions size every chapter to
// fit its line. Claims here must match the README and the running app.
export const CHAPTERS = [
  {
    id: "idea",
    title: "The idea",
    line:
      "Wearables record movement, heart rate and skin temperature all day. " +
      "Lab results like HbA1c live somewhere else, and are looked at far less often. " +
      "Gluco asks one research question: can recent wearable patterns give useful context " +
      "about a person's metabolic pattern, without using glucose as an input?",
  },
  {
    id: "flow",
    title: "How it works",
    line:
      "Wearable data flows through Databricks, from bronze to silver to gold tables, " +
      "into rolling twenty-four hour features and an experimental research score. " +
      "Those are published to Tiger Data. A read-only FastAPI service feeds the dashboard, " +
      "and an agent answers questions through role-scoped tools and guardrails. " +
      "Reading the dashboard never triggers training.",
  },
  {
    id: "signin",
    title: "Sign-in and roles",
    line:
      "Everyone signs in with Clerk, and the back end verifies every request. " +
      "Your role decides what you see. Clinicians get their patient panel. " +
      "Patients only ever see their own readings.",
  },
  {
    id: "panel",
    title: "The clinician's panel",
    line:
      "This is the clinician's panel: sixty-six participants from two public research datasets. " +
      "Up top, the panel's Gluco Scores at a glance. Then three ranked lists: the lowest scores, " +
      "the largest declines over the last twenty-four hours, and the largest increases. " +
      "The seven-day trend shows the hourly mean across everyone, " +
      "and the table lists every patient, with live columns that update each second.",
  },
  {
    id: "detail",
    title: "One patient, in detail",
    line:
      "Selecting a patient opens their detail page. The charts switch between twenty-four hours, " +
      "seventy-two hours and seven days, and each sensor trend reflects the preceding day. " +
      "What changed compares the latest window with earlier ones and with the patient's own " +
      "seven-day baseline, and flags the largest deviations. These are associations, not causes.",
  },
  {
    id: "live",
    title: "The live feed",
    line:
      "The strip at the top is the live feed. Heart rate, movement and skin temperature update every second. " +
      "In this prototype the feed is a labelled simulation, interpolated from real minute summaries. " +
      "The score and the twenty-four hour averages refresh every five to fifteen minutes.",
  },
  {
    id: "patient",
    title: "The patient's view",
    line:
      "Patients get a simpler view of their own week: their Gluco Score and how it moved, " +
      "a daily chart, live vitals compared with their usual week, and what stands out. " +
      "The score is always labelled an estimate, never a diagnosis.",
  },
  {
    id: "chat",
    title: "Ask Gluco",
    line:
      "Anyone can ask Gluco a question in plain language. The agent calls tools that only return " +
      "data the user is allowed to see, then explains it, and a grounding check flags any number " +
      "it can't trace back to those tools. Ask for a widget, and it builds a chart you can pin. " +
      "Pinned widgets re-run their query and compliance check as new data streams in.",
  },
  {
    id: "guard",
    title: "Guardrails",
    line:
      "Two layers on the server protect people's data. A guardrail screens every request, " +
      "and the data layer only ever returns a patient's own readings. " +
      "So a patient can ask about their own week, but a question about someone else is declined.",
  },
  {
    id: "evidence",
    title: "Engineering evidence",
    line:
      "All of this is backed by the repository. The back-end, front-end and Databricks test suites " +
      "run on every pull request. The model was evaluated on six hundred and sixty real twenty-four hour windows " +
      "from fifteen participants: sixty point four percent participant-weighted accuracy, against a " +
      "fifty-three point three percent baseline. That shows the pipeline works end to end. " +
      "It is not clinical validation.",
  },
  {
    id: "outro",
    title: "Gluco",
    line:
      "Gluco is a research prototype, not a medical device, and it's open source under the AGPL. " +
      "Thanks for watching.",
  },
] as const

export type ChapterId = (typeof CHAPTERS)[number]["id"]

// Teaser voice-over, one line per shot (src/Teaser.tsx), read as one story:
// what Gluco is and who it's for, then what it does. Each shot runs at least
// as long as its line, and the teaser has to stay under 30 s.
export const TEASER_LINES = [
  {
    id: "t-intro",
    line: "Gluco turns everyday wearable data into metabolic-health context, for patients and their care team.",
  },
  { id: "t-live", line: "It follows heart rate, movement and skin temperature, second by second," },
  { id: "t-score", line: "and scores each day: a research estimate, never a diagnosis." },
  { id: "t-panel", line: "Clinicians see their whole panel, and exactly what changed for each patient." },
  { id: "t-chat", line: "And anyone can ask Gluco about their data, in plain language." },
  { id: "t-outro", line: "Gluco. A research prototype, open source on GitHub." },
] as const

export type TeaserLineId = (typeof TEASER_LINES)[number]["id"]
