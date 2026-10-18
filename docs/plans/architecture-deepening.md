# Architecture deepening plan

Agreed 18 Oct 2026, from the architecture review of `79-fix-ci-and-testing`.

## Ground rules

- **Seams:** always inject dependencies; add an interface only where two adapters exist (a test fake counts as one); never fake what runs locally for real (tmp SQLite, `ReplayClock` with `time_source`).
- **Tests:** replace tests that reach past an old interface, don't keep both. Each PR adds a test for the bug or gap it closes, and keeps `just test`, `just lint`, `bun run test`, `bun run lint` and `bun run typecheck` green.
- **Shipping:** one PR per row below, each branched off `main`, named `<issue>-<slug>`. Leanness cuts ride with the PR that touches their files.
- **Out of scope:** `databricks/` (needs its owner's review), merging the clinician and patient prompts.

## PRs, in order

### 1. QueryService decides what a Principal sees (candidates 2 + 3) — #93

- The disclosure rule moves inside `QueryService.query()`: own series only for patients, display names in place of internal keys, cohort points from fewer than 3 people hidden. Every exit gets it: `POST /query`, the clinician and patient tools, and widgets.
- `QueryResult` gains `audit: list[str]`; only the widget card shows it. Run `bun run gen:api`.
- Public per-person methods (`participant`, `explain_change`, `latest`, `live`, `compare_to_cohort`, `cohort_position`) take a reference and resolve it inside. Role extras (e.g. `cohort_position` in explain) are decided inside.
- Front-end series are keyed by display name.
- Lean: shared status/explain/query logic for the patient and clinician tools in `tools/base.py`, keeping thin role wrappers; `widgets.design()` becomes a base spec plus per-kind overrides.
- Also ships: `GLOSSARY.md` and ADRs 0001–0003 (see below).
- New tests: small cells and raw keys never reach `POST /query` or a tool chart; a patient passing another reference gets 403 from each per-person method.

### 2. API transport seam (candidate 8) — #94

- `createClient` takes an injected `fetch`; `sse.ts` uses the same one.
- Tests supply a fake fetch that maps routes to responses. The real `queries.ts` hooks, cache keys and invalidation run in tests.
- Delete the five `vi.mock("@/lib/api/queries")` copies and the hand-declared `keys`.
- `WindowSource` contract suite runs both adapters; Postgres is skipped without a database. Delete the SQL-text assertions in `test_postgres.py`.

### 3. Sign-in: verify Clerk on every request (candidates 4 + 1) — #95

Back-end:
- An `Authenticator` (`authenticate(bearer) -> Principal`) is built in `create_app`, not on `Runtime`. The API server requires the Clerk settings; `just ask`, `just eval` and tests need no auth config.
- A `ClerkMetadata` model in `auth.py` owns `{uuid, role, participant_id, display_name}`; `clerk_seed` writes it and the Authenticator reads it. The patient's participant is checked on every request.
- The JWKS key resolver is injected. Tests use a signed-token fake in `tests/`.
- Delete `TokenSigner`, `/auth/clerk-login`, `LoginResponse`, `AUTH_SECRET`, `ALLOW_DEV_AUTH_SECRET`, `TOKEN_TTL_HOURS`, the dev-secret guard, `test_auth.py`, and the matching `.env.example` and README lines.

Front-end:
- One app session module: Clerk's state plus `GET /me` gives `{status, principal, home, signOut}`, with no browser storage. It registers Clerk's `getToken` with the transport once, at mount.
- On a 401, retry once with a fresh token, then sign out.
- `ClockProvider` reconnects when the user changes, not when the token changes.
- Delete `clerk-auth-sync.tsx`, most of `session.ts` and `session.test.ts`, the three `queryClient.clear()` calls (one remains, inside the module), and the `useAuth` name clash.
- Lean: `useAudience()` plus one role-keyed copy table replace the `audience` prop in 14 files; flatten `TOOL_LABELS`.
- New tests: a Clerk session that is still alive after a 401 recovers instead of spinning; seed metadata round-trips into a Principal.

### 4. One factory per Principal (candidate 5) — #96

- `Runtime.for_principal(p)` gives `queries`, `tools` and `agent`; `agent_for` uses it. A role-keyed `{role: build}` table replaces `tools/registry.py`.
- `POST /clock` is clinician-only (403 for patients); patients see the time but no controls.
- Delete `Runtime.tools_for`, `GET /tools` and `GET /clock`.
- New tests: a patient gets 403 on `POST /clock`; a test that replaces `store` reaches chat too.

### 5. One live view (candidate 6) — #97

- One `view(at)` applies live readings to windows, replacing `_live_for`, `_with_live`, the second merge in `_row`, and the history closure's synthetic window.
- The stream tick's `live_at` invalidates live widget queries, at most once every ~5 s. Delete the 5 s `refetchInterval` and the client-side re-merge in the participant table.
- Lean: one stale-check / lock / back-off helper for `WindowStore` and `LiveStore`; one `numberAt` helper in `lib/catalog.ts`.

### 6. Server-side chat transcript (candidate 7) — #98

- Restored threads are rebuilt from the stored session items in the same part types the stream sends (text, tool, chart, widget). One reducer serves live and restored threads.
- Delete `chart-cache.ts`. No migration of charts already in localStorage.
- Lean: a shared SQLite helper for `ChatSessions` and `WidgetStore` that also closes connections.
- New tests: the reducer, driven through the fake transport; a declined turn doesn't misalign charts.

### 7. Lean sweep — #99

- Delete `ui/command`, `ui/dialog`, `ui/select`, `ui/progress` and the `cmdk` dependency.
- Delete dead code: `WindowStore.refresh`, `LiveStore.latest_sensor_time` and `readings`, `latest(as_of=)`, `formatGap` and its test. Un-export six helpers that are only used in their own file.
- Move `pyyaml` to the dev group. Keep `clerk_seed` as it is and keep the `clerk` CLI devDependency.

## Records to add (in PR 1)

- `GLOSSARY.md`: Principal, participant, cohort, disclosure rule, live reading, live view, replay clock, app session, Authenticator.
- `docs/adr/0001-verify-clerk-per-request.md`
- `docs/adr/0002-clinicians-control-the-replay-clock.md`
- `docs/adr/0003-seam-rule.md`
