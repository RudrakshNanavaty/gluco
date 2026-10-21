# Team rehearsal: each person runs and explains Gluco

This guide is a procedure, not evidence that all members have passed. Each
member must run the same merged commit on their own machine and record their
own result. Another teammate witnesses the run and asks questions outside the
operator's usual component. Do not fill in outcomes from someone else's run.

## Preflight (before recording or meeting the tutor)

1. Record `git rev-parse HEAD`, Python/uv/Bun versions and OS. Use the reviewed
   main commit; don't overwrite local work to update it.
2. From `back-end`, run `uv sync --locked`. From `front-end`, run
   `bun install --frozen-lockfile`. No manual lockfile edits.
3. Create env files from the examples only if absent. Obtain settings from the
   team's approved secret-sharing channel. Do not put values in evidence files.
   Secret Manager pulls replace whole env files: use the documented diff first.
4. Backend needs AGENT_MODEL, LLM_API_KEY and Clerk JWKS/issuer configuration;
   frontend needs the matching Clerk publishable key and API URL. Current app
   startup constructs an LLM client even for mock data, so a blank key is not a
   complete runnable demo configuration. Chat needs a real working model/key.
5. Have approved patient and clinician accounts ready, each with correct Clerk
   metadata. One authorized maintainer handles account seeding; don't have every
   teammate rerun provisioning. Never share tokens/passwords in a recording.
6. Choose and state the data mode: `DATA_BACKEND=mock` for reproducible synthetic
   fixtures, or approved Postgres settings plus the intended dashboard session.
   Mock data cannot verify the cloud pipeline. SIMULATE_LIVE is display
   simulation and does not prove measured ingestion.

## Start and check

In separate terminals, from the corresponding directory:

```sh
# back-end: uses approved local env; explicitly selects mock data
DATA_BACKEND=mock uv run agent serve --port 8000

# front-end: NEXT_PUBLIC_API_BASE_URL must match the API port
bun dev
```

If ports are occupied, select spare ports and update API URL/CORS settings
consistently. Don't terminate another teammate's service or overwrite env files.

```sh
curl --fail http://127.0.0.1:8000/health
# Without a token, protected data must be denied (expect HTTP 401).
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/me
```

Sign into the dashboard. Health passing does not establish sign-in, chat or
cloud connectivity; check them separately below.

## Five-minute demonstration

| Time | Demonstrate | Explain |
|---|---|---|
| 0:00–0:25 | Open Gluco and identify the current data mode | Research prototype, intended audience and measured/simulated boundary |
| 0:25–1:20 | Patient dashboard, history and score | Score is cohort resemblance, not glucose or diagnosis |
| 1:20–2:10 | Clinician cohort and participant details | Backend enforces visibility; UI hiding alone is insufficient |
| 2:10–3:00 | Ask one rehearsed factual chat question | Tool grounding, role scope and how unavailable LLMs are reported |
| 3:00–3:35 | Show denied unauthenticated access or a tested failure case | Expected denial is evidence, not a broken demo |
| 3:35–4:20 | Trace Volume → Bronze → Silver → features/model → Gold/Tiger → API | Dashboard reads don't launch training; replay is not a physical feed |
| 4:20–5:00 | Show M0 CI and the recorded real model result | Synthetic instrument check differs from 66.86% best development result; 70% unmet |

Use fictional/research-demo content. Do not show personal health records, env
files, tokens, database URLs or cloud secrets. Keep the app ready alongside the
walkthrough video; if asked, reproduce a shown action live.

## Everyone must answer these

- What changes when DATA_BACKEND switches from mock to postgres?
- Where is patient scope enforced? What happens if someone edits an ID in a URL?
- What does Databricks do, and why does a dashboard read not retrain the model?
- How does replay retry avoid duplicate events, and when may its cursor advance?
- Why are 660 windows only 15 independent training/evaluation participants?
- What does line coverage measure, and what does it fail to prove?

## Record actual evidence

Copy `docs/rehearsal/EVIDENCE_TEMPLATE.md` to a new file using your GitHub handle.
Keep unchecked items unchecked until you personally verify them. Witnesses add
a real review/comment; never manufacture signatures or review evidence.
Record failures in GitHub issues with redacted reproduction steps, then rerun.

A complete team rehearsal requires all four members' records, witness reviews,
and resolved or clearly disclosed blockers. This PR prepares that process;
it does not award the team a completed-demo score.
