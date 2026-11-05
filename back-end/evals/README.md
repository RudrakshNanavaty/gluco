# Evals

Two evals call the real model. They need `LLM_API_KEY` and `AGENT_MODEL` in `back-end/.env`.

| Command | What it measures |
|---|---|
| `just eval` | 16 end-to-end cases (`cases.yaml`): tools called, answer patterns, and numbers no tool returned. Ends with a grounding-clean smoke figure (`k/n`, no bound). |
| `just guardrail-eval` | How often the input guardrail lets a should-decline prompt through (bypass) or blocks a should-pass prompt (false positive). Classifier only; no tools run. |

## Guardrail eval

Cases live in `guardrail_cases.yaml`: `role`, `text`, `expect` (a decline category or `none`) and
`source` (`agent` or `user`). The eval runs each prompt through the same `InputGuardrail` objects the
app builds, so there is no copy of the classifier.

- A *bypass* is a should-decline prompt that is not declined. A *false positive* is a should-pass
  prompt that is declined. A decline in the wrong category counts as a decline and is listed as a
  category mismatch.
- `k/n` is over distinct prompts, with a Wilson 95% upper bound. Per-role and per-category counts
  are diagnostics: the cells are small, so their bounds are wide.
- `--repeats N` runs each prompt N times. A prompt fails if any repeat fails, and prompts that
  differ between repeats are listed. Calls that error are reported separately and never count as
  a decline or a pass.
- The cases are not held out. The first pass is agent-drafted; add your own `source: user` prompts
  (aim for 30 or more) and do not tune the guardrail prompt after the user cases are first run.

## What the figures do and do not show

They describe this internal prompt set on one model on one date. They are not a safety
certification, and the classifier's rate cannot be shown to be 100%.

Isolation is a separate, structural claim with two parts:

1. Patient tools take no person identifier (`tests/test_tools.py` checks the parameter names and
   sweeps the free-text parameters with other participants' ids and names).
2. `QueryService` checks scope itself and raises `ForbiddenError` for anyone else
   (`tests/test_query.py`).

Planted-number tests of the grounding check (`tests/test_grounding.py`) test the checker against
chosen examples. They are a unit-test property, not a measure of how often the agent hallucinates.
The check covers numbers only.
