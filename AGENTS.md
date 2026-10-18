# Gluco

Research prototype (not a medical device): wearable signals → metabolic-pattern context for patients and clinicians. AGPL-3.0.

## Layout

- `back-end/` — Python 3.12, uv, FastAPI, openai-agents. Read-only agent layer.
- `front-end/` — Next.js 16, React 19, Tailwind 4, shadcn, bun.
- `databricks/` — research/pilot scripts and the Tiger (Postgres) live feed.

## Commands

Back-end (from `back-end/`): `just mock` (run on mock data), `just test`, `just lint` (ruff + basedpyright).
Front-end (from `front-end/`): `bun dev`, `bun run test`, `bun run lint`, `bun run typecheck`, `bun run gen:api` (needs API on :8000).

## Rules

- Never commit `.env*` (except `.env.example`) or data files.
- Don't hand-edit `uv.lock` / `bun.lock`.
- Don't make medical or diagnostic claims in code, copy, or docs.
- Make code changes on feature branches, never directly on `main`. Use
  Conventional Commits for commit messages.
