# Gluco

Research prototype (not a medical device): wearable signals → metabolic-pattern context for patients and clinicians. AGPL-3.0.

## Layout

- `back-end/` — Python 3.12, uv, FastAPI, openai-agents. Read-only agent layer.
- `front-end/` — Next.js 16, React 19, Tailwind 4, shadcn, bun.
- `databricks/` — research/pilot scripts and the Tiger (Postgres) live feed.

## Commands

Back-end (from `back-end/`): `just mock` (run on mock data), `just test`, `just lint` (ruff + basedpyright).
Front-end (from `front-end/`): `bun dev`, `bun run test`, `bun run lint`, `bun run typecheck`, `bun run gen:api` (needs API on :8000).

## Secrets

Env files live in Google Secret Manager (`gluco-backend-env`, `gluco-frontend-env`), one blob per file. Needs `gcloud auth login` and a default project (or `GLUCO_GCP_PROJECT`).
Back-end (from `back-end/`): `just secrets-diff`, `just secrets-pull` (overwrites `.env`, keeps `.env.bak`), `just secrets-push`.
Front-end (from `front-end/`): `bun run secrets:diff`, `secrets:pull`, `secrets:push`.
Both wrap `scripts/secrets.sh`. Push and pull replace the whole file, so run `diff` first.

## Rules

- Never commit `.env*` (except `.env.example`) or data files.
- Don't hand-edit `uv.lock` / `bun.lock`.
- Don't make medical or diagnostic claims in code, copy, or docs.
- PR descriptions carry no AI attribution (no "Generated with Claude Code" line). Commit messages keep the `Co-Authored-By` trailer.
- Make code changes on feature branches, never directly on `main`. Use
  Conventional Commits for commit messages.
