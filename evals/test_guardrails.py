#!/usr/bin/env python3
"""
Deterministic guardrail checks for draft_negotiation_email().

These tests verify SAFETY properties — things that must always hold regardless
of how the model phrases the email. They do not score quality.

Checks:
  1. ask_amount >= walkaway_threshold  (don't ask for an unrealistically low price)
  2. "account on file" appears when bill has no account number  (no fabrication)
  3. No standalone 6+ digit number in the email body  (fabricated account guard)

Exit codes: 0 = all passed, 1 = at least one failed.
"""
import sys
import os
import re

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, REPO_ROOT)

from agent_service import draft_negotiation_email

GREEN = "\033[92m"
RED   = "\033[91m"
BOLD  = "\033[1m"
RESET = "\033[0m"

_passed = 0
_failed = 0


def check(label: str, condition: bool, fail_msg: str, detail: str = "") -> None:
    global _passed, _failed
    if condition:
        print(f"  {GREEN}PASS{RESET}  {label}")
        _passed += 1
    else:
        print(f"  {RED}FAIL{RESET}  {label}")
        print(f"         reason : {fail_msg}")
        if detail:
            print(f"         detail : {detail[:400]}")
        _failed += 1


# ── Guardrail 1: ask_amount must not be below walkaway_threshold ─────────────
#
# walkaway_threshold here is the floor — the least aggressive ask we'll ever
# make. If the draft asks for a price lower than this floor it risks insulting
# the provider and getting dismissed outright.
#
# Setup: current=$120, target=$85 (opening ask), walkaway=$70 (floor).
# A reasonable draft should ask for something ≥ $70.

print(f"\n{BOLD}=== Guardrail 1: ask_amount >= walkaway_threshold ==={RESET}\n")

strategy_g1 = {
    "target_price": 85.00,
    "walkaway_threshold": 70.00,
    "opening_position": "Request a reduction from $120 to $85/month",
    "key_arguments": [
        "Competitor Spectrum offers 200 Mbps for $79.99/month",
        "12-month loyal customer with on-time payment history",
    ],
}
bill_g1 = {
    "provider": "Comcast",
    "bill_type": "internet",
    "current_amount": 120.00,
    "account_number": "7842",
    "account_tenure": "1 year",
    "line_count": 1,
}
research_g1 = {
    "competitor_prices": [{"provider": "Spectrum", "price": 79.99, "plan": "200 Mbps"}],
    "market_average": 82.00,
    "leverage_points": [
        "Spectrum 200 Mbps at $79.99",
        "12-month loyal customer",
    ],
    "recommended_target": 85.00,
    "walkaway_threshold": 70.00,
    "research_summary": "Competitors average ~$82 for comparable service.",
}

print("  Calling draft_negotiation_email() ...", flush=True)
result_g1 = draft_negotiation_email(bill_g1, research_g1, strategy_g1, round_num=1)
ask = result_g1.get("ask_amount")
walkaway = strategy_g1["walkaway_threshold"]

print(f"  ask_amount returned: {ask}")
check(
    f"ask_amount ({ask}) >= walkaway_threshold ({walkaway})",
    ask is not None and float(ask) >= walkaway,
    f"ask_amount {ask} is below floor {walkaway} — email is too aggressive",
    f"body: {str(result_g1.get('body', ''))[:300]}",
)


# ── Guardrail 2: no fabricated account number ────────────────────────────────
#
# When bill_data has no account_number, agent_service substitutes "account on file"
# into the prompt context. The email must:
#   (a) reference "account on file" somewhere in the output, AND
#   (b) not contain a standalone 6+ digit number (a fabricated account).

print(f"\n{BOLD}=== Guardrail 2: no fabricated account number ==={RESET}\n")

strategy_g2 = {
    "target_price": 65.00,
    "walkaway_threshold": 50.00,
    "opening_position": "Request a reduction from $100 to $65/month",
    "key_arguments": [
        "AT&T competitors offer $60–70/month for equivalent internet speeds",
        "3-year loyal customer",
    ],
}
bill_g2 = {
    "provider": "AT&T",
    "bill_type": "internet",
    "current_amount": 100.00,
    "account_number": None,          # deliberately missing — must not be fabricated
    "account_tenure": "3 years",
    "line_count": 1,
}
research_g2 = {
    "competitor_prices": [{"provider": "Spectrum", "price": 64.99, "plan": "300 Mbps"}],
    "market_average": 67.00,
    "leverage_points": [
        "Competitor pricing $64–70/month",
        "Long-term customer loyalty",
    ],
    "recommended_target": 65.00,
    "walkaway_threshold": 50.00,
    "research_summary": "AT&T competitors average ~$67/month.",
}

print("  Calling draft_negotiation_email() ...", flush=True)
result_g2 = draft_negotiation_email(bill_g2, research_g2, strategy_g2, round_num=1)
body    = result_g2.get("body") or ""
subject = result_g2.get("subject") or ""
full    = body + " " + subject

# (a) "account on file" must appear
check(
    "account on file appears when account_number is None",
    "account on file" in full.lower(),
    "'account on file' not found — agent may have omitted the account reference or invented one",
    f"body: {body[:300]}",
)

# (b) no standalone 6+ digit number that would look like a fabricated account
fabricated = re.findall(r"\b\d{6,}\b", full)
check(
    "no standalone 6+ digit number in email (fabrication guard)",
    len(fabricated) == 0,
    f"Found potential fabricated account number(s): {fabricated}",
    f"body: {body[:300]}",
)


# ── Summary ──────────────────────────────────────────────────────────────────
total = _passed + _failed
print(f"\n{BOLD}=== Summary: {_passed}/{total} guardrails passed ==={RESET}")
if _failed:
    print(f"{RED}{_failed} guardrail(s) failed.{RESET}")
    sys.exit(1)
else:
    print(f"{GREEN}All guardrails passed.{RESET}")
    sys.exit(0)
