# RatePilot Eval Suite

## What it covers

**`run_decision_evals.py`** — 12 end-to-end tests of `interpret_response()`, the
agent's core decision step. Real API calls; results reflect actual model behavior.
Scenarios covered:
- Offer at or below the target price → must `accept`
- Offer between target and walkaway, early round → expect `counter`
- Offer between target and walkaway, late round with "final offer" language → expect `accept` or `counter`
- Offer just inside the walkaway → either `accept` or `counter` are fine
- Offer above the walkaway threshold → must NOT `accept` (hard guardrail on 4 cases)
- Flat refusal or no movement → expect `escalate` or `close`
- Ambiguous/stalling replies with no dollar amount → must NOT `accept`

**`test_guardrails.py`** — 3 deterministic safety checks on `draft_negotiation_email()`:
- `ask_amount` must not fall below `walkaway_threshold` (guards against unrealistically
  aggressive asks that would be dismissed outright)
- `"account on file"` must appear in the email when the bill has no account number
- No standalone 6+ digit number in the body (guards against fabricated account numbers)

## What it does NOT yet cover

- **Email quality / persuasiveness** — LLM-as-judge scoring of tone, argument
  strength, and how well the email uses the provided leverage points. This is the
  most valuable missing coverage and the natural next step.
- **End-to-end outcome metrics** — average savings and success rate across batches
  of simulated multi-round negotiations (requires a mock provider responder).
- **Research accuracy** — whether `research_competitors()` produces plausible market
  prices (would need a curated ground-truth dataset of telecom pricing).
- **Regression tracking** — pass/fail history across model versions or prompt changes.

## How to run

```bash
# From the repo root (ANTHROPIC_API_KEY must be set)
python evals/run_decision_evals.py    # 12 LLM-backed decision tests (~2-3 min)
python evals/test_guardrails.py       # 3 deterministic guardrail checks (~30 sec)
```

Exit code 0 = all passed. Non-zero = at least one failure. All output goes to stdout.
