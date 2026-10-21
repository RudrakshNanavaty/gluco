# Measured coverage and live badges

Coverage measures executed source lines, not model accuracy or team readiness.
Three separate denominators are intentional:

- Backend: all `back-end/src/agent` Python source, including untouched files.
- Frontend: all `front-end/src` TypeScript/TSX, excluding generated/declaration
  `.d.ts` files. Unit tests don't execute every Next.js server/client path.
- Databricks: all Python under `databricks/tiger`, including unexecuted cloud
  notebooks and orchestration scripts. A low local-unit percentage is not a
  claim that cloud verification failed. Spark notebooks require workspace tests.

No arbitrary passing coverage threshold is introduced, and uncovered code is
not excluded to improve the badge. Per-component HTML and JSON reports plus
JUnit results are retained as CI artifacts. Live database tests run separately;
the badge's unit-test count excludes that additional live job.

## Run locally

```sh
# back-end
uv run pytest --cov=src/agent --cov-report=term-missing --cov-report=html:coverage/html

# front-end
bun run test:coverage

# repository root
uv run --python 3.12 --no-project --with-requirements databricks/requirements-test.txt \
  python -m pytest databricks/tests -q --cov=databricks/tiger --cov-report=term-missing
```

## Publication

CI generates endpoint JSON from measured totals and JUnit cases, never a
hardcoded percent/count. Only a successful report job on a push to main may
publish to the dedicated `coverage-badges` branch, using job-scoped write
permission. PR jobs can produce artifacts but cannot publish badge data.

The first merged main run creates the branch. README endpoint badges initialize
then; until that first publication, they are not live. Badge clicks open the
metrics README containing the exact source commit and run link. Values represent
the latest published successful measurement, not a guarantee that a newer run
passed; the build badge shows current CI state. Shields may cache briefly.

Generated metric files are isolated from application code, and publishing them
does not trigger the main-only push workflow. If repository rules reject the
metrics-branch push, the publishing job fails visibly; don't add a false static
badge as a workaround.
