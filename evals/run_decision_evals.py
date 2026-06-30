#!/usr/bin/env python3
"""
Decision eval runner for interpret_response().

Each case calls the real agent function with real API calls and compares the
returned `decision` to the expected set. Results are never fabricated — if the
model makes a surprising call, the test fails and shows the agent's own reasoning.

Exit codes: 0 = all passed, 1 = at least one failed.
"""
import sys
import os

# Repo root on sys.path so agent_service imports cleanly
REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_service import interpret_response  # real API, real model
from decision_cases import CASES

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def run_case(case: dict) -> tuple[str, dict, bool, bool]:
    """
    Call interpret_response and evaluate against expected outcomes.
    Returns (decision, raw_result, passed, guardrail_violated).
    """
    result = interpret_response(
        response_text=case["reply"],
        strategy=case["strategy"],
        history=case["history"],
    )
    decision = (result.get("decision") or "").lower().strip()
    expected = case["expected"]

    in_expected = decision in expected
    guardrail_violated = case.get("guardrail_no_accept", False) and decision == "accept"

    passed = in_expected and not guardrail_violated
    return decision, result, passed, guardrail_violated


def main() -> None:
    total = len(CASES)
    passed_count = 0
    failures = []

    print(f"\n{BOLD}=== RatePilot Decision Evals — {total} cases ==={RESET}\n")

    for i, case in enumerate(CASES, 1):
        name = case["name"]
        print(f"  [{i:02d}/{total}] {name} ...", end=" ", flush=True)

        try:
            decision, result, passed, guardrail_violated = run_case(case)
        except Exception as exc:
            print(f"{RED}ERROR{RESET}")
            print(f"          exception: {exc}")
            failures.append((name, None, None, False, str(exc)))
            continue

        expected_str = " | ".join(sorted(case["expected"]))
        if passed:
            print(f"{GREEN}PASS{RESET}  (got={decision!r}, expected={{{expected_str}}})")
            passed_count += 1
        else:
            tag = f"{RED}GUARDRAIL-VIOLATED{RESET}" if guardrail_violated else f"{RED}FAIL{RESET}"
            print(f"{tag}  (got={decision!r}, expected={{{expected_str}}})")
            failures.append((name, decision, result, guardrail_violated, None))

    # ── failure detail block ────────────────────────────────────────────────
    if failures:
        print(f"\n{BOLD}── Failure details ──{RESET}")
        for name, decision, result, guardrail_violated, exc in failures:
            print(f"\n  {RED}✗{RESET} {name}")
            if exc:
                print(f"    exception: {exc}")
                continue
            if guardrail_violated:
                print(f"    {RED}GUARDRAIL: agent chose 'accept' when no acceptance was valid{RESET}")
            case = next(c for c in CASES if c["name"] == name)
            print(f"    rationale : {case['rationale']}")
            reasoning = (result or {}).get("decision_reasoning", "(none)")
            print(f"    agent said: {reasoning[:300]}")
            offered = (result or {}).get("offered_amount")
            if offered is not None:
                print(f"    offered_amount extracted: {offered}")

    # ── summary ────────────────────────────────────────────────────────────
    print(f"\n{BOLD}=== Summary: {passed_count}/{total} passed ==={RESET}")
    failed_count = total - passed_count
    if failed_count:
        print(f"{RED}{failed_count} case(s) failed.{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}All cases passed.{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
