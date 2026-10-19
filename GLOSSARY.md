# Glossary

The words this codebase uses for its domain. Code, docs and reviews use them with these meanings.

**Principal**: who is asking. It has a role (`clinician` or `patient`), a display name and, for a patient, their participant. Every data read is scoped from the Principal, never from the UI or the LLM. _Avoid_: user (ambiguous with a Clerk user), persona.

**Participant**: one person whose wearable readings are in the data, named by an internal key such as `demo:big_ideas:013`. A patient Principal is linked to exactly one participant. Internal keys never leave the back-end in a series: people see a **display name** such as "Patient 013". A reference to a participant ("13", "Patient 013" or the full key) is resolved by `QueryService`. _Avoid_: subject, user.

**Cohort**: every participant a clinician can see, also called the panel. A **pooled** cohort series combines several participants into one. _Avoid_: group.

**Window**: one participant's derived metrics over a time span, ending at `window_end`. The replay clock decides which windows are visible.

**Disclosure rule**: what every query result passes before anyone sees it: series carry display names, not internal keys, and pooled cohort points built from fewer than 3 people are hidden (the small-cell rule). `QueryService.query()` applies it, so REST, tools and widgets all show the same thing. Each result lists what was applied in `audit`.

**Live reading**: a participant's newest sensor values, taken more often than windows are built. Live readings are applied to the participant's newest window once the replay clock reaches it.

**Live view**: windows with their live readings already applied, as of a given time. One place produces it, and one freshness signal tells the UI when it changed.

**Replay clock**: the shared simulated "now" that walks through the recorded data. It is the same for every user. Only clinicians may move it (ADR 0002).

**App session**: the front-end module that knows who is signed in. It wraps Clerk's state and the back-end's `GET /me`, and gives callers a status, the Principal, their home route and sign-out.

**Authenticator**: the back-end module that turns a bearer token into a Principal. Clerk verification is its production adapter; tests use a fake that signs its own tokens (ADR 0001).
