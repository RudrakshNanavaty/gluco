# Gluco demo videos

The two Project 2 videos, built with [Remotion](https://www.remotion.dev/) from
real screen captures of the running app.

| Video | Length | Composition | Output |
| --- | --- | --- | --- |
| Teaser | ~28 s (brief: 12–30 s) | `Teaser` | `out/gluco-teaser.mp4` |
| Feature walk-through | ~4:10 (brief: 2–5 min) | `Walkthrough` | `out/gluco-walkthrough.mp4` |

Both have narration. The teaser has one short line per shot (`TEASER_LINES`
in `src/script.ts`), and its on-screen captions carry it when muted. The
walk-through has a line per chapter and burned-in subtitles. At the live demo you can
play it with the sound on, or mute it and narrate from `src/script.ts`.

## What's real

Every app shot is the running app on the real Tiger data (live mode,
`SIMULATE_LIVE=true`). The chat answers come from the configured LLM. Only the
title cards, the research-question graphic and the data-flow diagram are motion
graphics. The test counts in the evidence chapter come from
`public/evidence.json`, written by actually running the three suites. The
evaluation figures are the README's.

## Rebuild

Needs Bun, ffmpeg, the API on :8000 and the web app on :3000.

```bash
cd video
bun install
bunx playwright install chromium
```

1. **Sign in once per role.** A browser window opens. Sign in, and the
   session is kept in `capture/auth/` (gitignored).

   ```bash
   bun run login clinician
   bun run login patient
   ```

2. **Start the API with a scratch widget store** so the panel starts with no
   pinned widgets and your own `var/sessions.sqlite` is untouched. This is the
   `gluco-api-video` entry in `.claude/launch.json`:

   ```bash
   cd back-end && SESSION_DB_PATH=var/video-sessions.sqlite TRACE_PATH=var/video-trace.jsonl uv run agent serve
   ```

   Delete `back-end/var/video-sessions.sqlite` before recording the `chat` shot
   again, or the widget it pins will already be there.

3. **Record the shots** (all of them, or name some). The clips and their timing
   marks land in `public/footage/` (gitignored).

   ```bash
   bun run capture
   bun run capture chat patient-chat
   ```

4. **Refresh the test evidence and the narration** (both videos' lines). Narration uses
   [Kokoro](https://github.com/thewh1teagle/kokoro-onnx), an offline TTS model.
   `KOKORO_DIR` needs a venv with `kokoro-onnx` and `soundfile`, and the files
   `kokoro-v1.0.onnx` and `voices-v1.0.bin`.

   ```bash
   bun capture/evidence.ts
   KOKORO_DIR=~/kokoro bun run voice
   ```

5. **Preview and render.**

   ```bash
   bun run studio
   bun run render:teaser
   bun run render:walkthrough
   ```

## Layout

- `capture/`: Playwright recorder. It uses the Chrome DevTools screencast at
  2x and draws an on-screen pointer.
- `src/script.ts`: the walk-through narration, one line per chapter. Each
  chapter runs as long as its line or its footage, whichever is longer.
- `src/Walkthrough.tsx`, `src/Teaser.tsx`: which clip plays under each line,
  and where the camera pushes in.
- `src/scenes/`: the motion-graphic chapters (idea, data flow, evidence,
  outro).
- `voice/`: the narration generator.

Changing a line in `src/script.ts` needs `bun run voice` before rendering.
UI changes need the affected shots recorded again.
