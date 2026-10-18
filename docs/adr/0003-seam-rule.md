# 0003. When to add an interface: the seam rule

Status: accepted, 18 Oct 2026.

## Context

We want a lean codebase and code that is easy to test. Strict dependency inversion would put a Protocol in front of every collaborator, which adds code and indirection where nothing varies.

## Decision

- Always inject dependencies through the constructor; never construct them inside.
- Add an interface (a Protocol, or a `Callable` type for one method) only where two adapters exist. A test fake counts as one.
- Never fake what runs locally for real. Use a tmp SQLite file, or `ReplayClock` and the stores with an injected `time_source`.

Real seams today: `WindowSource` (mock and Postgres), the Authenticator (Clerk and a signed-token fake), and the API transport on the front-end (fetch and a fake).

## Consequences

- Tests cross the same interface callers use; tests that patch private attributes are replaced.
- Single-adapter collaborators such as `ReplayClock`, `ChatSessions` and `WidgetStore` get no Protocol.
