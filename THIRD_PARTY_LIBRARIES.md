# Third-party libraries and licenses

Gluco is licensed under AGPL-3.0-only, but its dependencies retain their own
licenses. The lockfiles are the authoritative version inventories:
[`back-end/uv.lock`](back-end/uv.lock) and
[`front-end/bun.lock`](front-end/bun.lock). This document records the declared
direct dependencies and the license families reported by their upstream
projects as of October 21, 2026.

## Back end

| Library | Purpose | Upstream license |
|---|---|---|
| FastAPI | HTTP API | MIT |
| NumPy | Numeric operations | BSD-3-Clause |
| OpenAI Agents SDK | Role-scoped agent runtime | MIT |
| Psycopg | PostgreSQL client | LGPL-3.0-or-later |
| Pydantic | Validation and settings | MIT |
| PyJWT | JWT processing | MIT |
| sse-starlette | Server-sent events | BSD-3-Clause |
| Uvicorn | ASGI server | BSD-3-Clause |

Development dependencies include basedpyright (MIT), Faker (MIT), HTTPX
(BSD-3-Clause), pytest and pytest-asyncio (MIT), pytest-cov (MIT), PyYAML (MIT),
and Ruff (MIT).

## Front end

| Library | Purpose | Upstream license |
|---|---|---|
| Clerk Next.js SDK | Authentication UI and session integration | MIT |
| Next.js | React application framework | MIT |
| React and React DOM | User-interface runtime | MIT |
| TanStack Query | Server-state management | MIT |
| Recharts | Dashboard charts | MIT |
| Radix UI | Accessible component primitives | MIT |
| shadcn | Component source and registry tooling | MIT |
| Sonner | Toast notifications | MIT |
| Tailwind CSS | Styling | MIT |
| Lucide React | Icons | ISC |
| react-markdown and remark-gfm | Markdown rendering | MIT |
| openapi-fetch and openapi-typescript | Typed API client generation | MIT |
| eventsource-parser | Streaming-event parser | MIT |
| next-themes | Theme management | MIT |
| class-variance-authority | Component variants | Apache-2.0 |
| tw-animate-css | CSS animation utilities | MIT |

Development dependencies include TypeScript, ESLint, Vitest, Testing Library,
Happy DOM, jsdom, Vite plugins, and Tailwind/PostCSS tooling. Their exact resolved
versions and transitive packages are recorded in `front-end/bun.lock`.

## Verification and updates

This summary is not a replacement for upstream license texts. Before a release,
dependency change, or redistribution:

1. regenerate installs from the committed lockfiles;
2. inspect package metadata for every resolved dependency;
3. retain required copyright and notice files; and
4. update this document in the same pull request as a dependency change.

If package metadata and this summary disagree, the package's distributed
license file controls. Report discrepancies as repository issues.
