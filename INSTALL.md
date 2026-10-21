# Installing Gluco

This guide takes a new contributor from a clean checkout to a working local
research demo. Gluco can run with seeded mock data; cloud database access is
optional. Never commit local environment files or credentials.

## Prerequisites

- Git
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) 1.4 or newer
- [just](https://just.systems/) for the short back-end commands

## 1. Clone the repository

```sh
git clone https://github.com/RudrakshNanavaty/gluco.git
cd gluco
```

## 2. Install and start the back end

```sh
cd back-end
uv sync --locked
cp .env.example .env
uv run agent serve
```

The API starts at <http://localhost:8000>. Its interactive OpenAPI reference is
at <http://localhost:8000/docs>. When no database is configured, Gluco uses the
seeded mock dataset. Chat additionally needs a working `LLM_API_KEY` and
`AGENT_MODEL` in `back-end/.env`.

## 3. Install and start the front end

Open a second terminal from the repository root:

```sh
cd front-end
bun install --frozen-lockfile
cp .env.example .env.local
bun dev
```

Open <http://localhost:3000>. The Clerk publishable key in `.env.local` must
belong to the same Clerk instance configured by the API. Authorized maintainers
can use the documented back-end seeding command to create demo accounts; do not
share passwords or session tokens in issues or recordings.

## 4. Verify the installation

```sh
curl --fail http://localhost:8000/health

cd back-end
just test
just lint

cd ../front-end
bun run test
bun run typecheck
bun run lint
bun run build
```

The protected API intentionally returns `401` when no Clerk session token is
provided. See the [team rehearsal guide](docs/TEAM_REHEARSAL.md) for a complete
patient-and-clinician demo checklist.

## Troubleshooting

- **Authentication settings are invalid:** confirm that the front-end
  publishable key and back-end Clerk issuer/JWKS settings reference the same
  Clerk instance. Restart both development servers after changing env files.
- **Port already in use:** choose another port and update the front-end API URL
  and back-end CORS origins together.
- **Dashboard works but chat does not:** mock dashboard data does not require a
  model key; chat does. Check `/health` without posting credentials publicly.
- **Dependency mismatch:** use the locked install commands above. Do not edit
  `uv.lock` or `bun.lock` manually.

For cloud data-pipeline setup, follow
[`databricks/tiger/README.md`](databricks/tiger/README.md). For component details,
see the [back-end](back-end/README.md) and [front-end](front-end/README.md) guides.
