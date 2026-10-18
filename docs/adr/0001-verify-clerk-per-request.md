# 0001. Verify the Clerk session on every request; no app token

Status: accepted, 18 Oct 2026. Implemented by #95.

## Context

Sign-in happens only through Clerk. The front-end swapped the short-lived Clerk session token for the back-end's own 24-hour token, kept it in localStorage, and sent that on every request. Two tokens meant two expiries that could disagree: a 401 on the app token while Clerk was still signed in left the user stuck. It also needed `AUTH_SECRET`, a dev-secret guard, an exchange route, and a client-side session store kept in sync with Clerk by hand.

## Decision

The back-end verifies the Clerk session token on every request, through one Authenticator (`authenticate(bearer) -> Principal`). Clerk's signing keys are cached, so this costs no network call per request. The front-end asks Clerk for a token per request; on a 401 it retries once with a fresh token, then signs out.

The Authenticator is a seam with two adapters: Clerk in production, and a fake that signs its own tokens in tests. It is built by the API app, so `just ask`, `just eval` and tests need no auth configuration.

## Consequences

- `TokenSigner`, `/auth/clerk-login`, `AUTH_SECRET`, `ALLOW_DEV_AUTH_SECRET`, `TOKEN_TTL_HOURS` and the front-end session store go away.
- The API server needs the Clerk settings to start.
- Long-lived streams are checked when they connect, as before.
