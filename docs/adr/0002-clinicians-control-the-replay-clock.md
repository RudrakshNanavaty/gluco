# 0002. The shared replay clock is controlled by clinicians only

Status: accepted, 18 Oct 2026. Implemented by #96.

## Context

The replay clock is one simulated "now" shared by every user, by design: a demo walks the whole panel through the recorded data together. But `POST /clock` accepted any signed-in Principal, and the replay controls were shown to patients, so one patient pausing or seeking changed what everyone saw.

## Decision

The clock stays shared. Only clinicians may move it: `POST /clock` returns 403 for patients, and patients see the current time but no controls.

## Consequences

- Per-user clocks are out of scope; a future review should not suggest them without a new need.
- The rule lives with the per-Principal wiring, so it is tested in one place.
