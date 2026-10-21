# Contributing to Gluco

Thank you for improving Gluco. The project is a research prototype, so changes
must preserve privacy boundaries, visible uncertainty, and reproducibility.

## Before starting

1. Search existing issues and open or claim one before substantial work.
2. Branch from the latest reviewed `main`; do not develop directly on `main`.
3. Install with [`INSTALL.md`](INSTALL.md) and keep both lockfiles unchanged
   unless the contribution intentionally changes dependencies.
4. Never commit `.env` files, credentials, tokens, raw participant data, local
   databases, generated coverage folders, or recordings containing health data.

Use a focused branch such as `fix/history-retry` or `docs/install-guide`. Keep
commits small and use Conventional Commits, for example:

```text
fix(front-end): retry failed conversation history
docs: explain mock-data installation
test(back-end): cover expired Clerk tokens
```

## Development checks

Run checks for every component you changed before requesting review.

```sh
# back end
cd back-end
just test
just lint

# front end
cd front-end
bun run test
bun run typecheck
bun run lint
bun run format:check   # `bun run format` fixes it
bun run build
```

The same checks run in GitHub Actions. Add tests for expected behavior and for
at least one meaningful failure path whenever behavior changes.

## Extending the system safely

- **API and authorization:** enforce patient/clinician scope in the back end,
  never only in the UI. A patient identifier from a URL or model response is
  untrusted. Test both the allowed request and the denied cross-patient request.
- **Metrics:** add metric definitions to the back-end catalog so labels, units,
  API responses, tools, and UI descriptions remain aligned.
- **Agent tools:** use the role-scoped `QueryService`; do not bypass it with
  direct database access. Keep numeric outputs available to grounding checks.
- **Front-end API types:** change the API contract first, run the API, then use
  `bun run gen:api`. Do not hand-edit the generated schema.
- **Data pipeline:** retain dataset-qualified participant identifiers and keep
  participant-held-out evaluation. Dashboard reads must not trigger training.
- **Copy and visuals:** describe Gluco as a research prototype. Do not present
  the score as glucose, diagnosis, treatment advice, or clinical validation.

Architecture decisions that affect trust boundaries should receive an ADR in
`docs/adr/`. Data-contract changes should also update
`databricks/DATA_FLOW.md` and the relevant component README.

## Pull requests

A reviewable pull request should:

- link the issue it resolves (`Closes #123` when appropriate);
- explain the user-visible behavior and the reason for the change;
- list tests and manual checks actually performed;
- include screenshots for visual changes without exposing personal data;
- call out migrations, configuration changes, and known limitations; and
- remain focused enough to review and revert independently.

Record substantive design discussion in the issue or PR so the decision remains
visible after chat messages disappear. AI-assisted changes must be checked by a
human contributor; document what was verified rather than treating generated
output as evidence by itself.

By participating, you agree to follow the
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Contributions are licensed under the
repository's [GNU AGPL v3](LICENSE).
