import anthropic
import json
import re
import sys
from typing import Optional

client = anthropic.Anthropic(timeout=30.0)
MODEL = "claude-sonnet-4-5"

def call_with_retry(fn, *args, **kwargs):
    import time
    for attempt in range(5):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "rate_limit" in str(e).lower():
                wait = 20
                response = getattr(e, "response", None)
                retry_after = response.headers.get("retry-after") if response is not None else None
                if retry_after:
                    try:
                        wait = float(retry_after) + 1
                    except ValueError:
                        pass
                print(f"Rate limited, waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
    raise Exception("Max retries exceeded")


def extract_json(text: str) -> dict:
    """Robustly extract JSON from Claude's response."""
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass
    # Strip markdown fences
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(clean)
    except:
        pass
    # Find first {...} block
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return {}



def research_competitors(provider: str, bill_type: str, current_amount: float, line_count: int = 1) -> dict:
    """Use Claude market knowledge to estimate competitor pricing."""
    line_count = int(line_count or 1)
    account_context = ""
    if line_count > 1:
        account_context = (
            f"\nIMPORTANT: This is a {line_count}-LINE FAMILY/GROUP ACCOUNT. "
            f"Compare {line_count}-line family plan pricing only. Do not use single-line pricing."
        )

    messages = [{
        "role": "user",
        "content": f"Research {provider} {bill_type}. Current bill ${current_amount}. line_count={line_count}.{account_context}"
    }]
    print(f"RESEARCH USER MESSAGE: {messages[0]['content'][:500]}")
    sys.stdout.flush()

    response = call_with_retry(client.messages.create,
        model=MODEL,
        max_tokens=500,
        system="""You are a bill negotiation expert with deep knowledge of telecom and utility pricing. Based on your knowledge of current market rates, return ONLY this JSON:
{
  "competitor_prices": [
    {"provider": "name", "price": 0.00, "plan": "description"}
  ],
  "market_average": 0.00,
  "leverage_points": ["point 1", "point 2", "point 3"],
  "recommended_target": 0.00,
  "walkaway_threshold": 0.00,
  "plan_context": "individual or family-X-lines",
  "research_summary": "one sentence summary"
}
JSON only. No preamble.""",
        messages=messages
    )
    print(f"RESEARCH TOKENS - input: {response.usage.input_tokens}, output: {response.usage.output_tokens}")
    sys.stdout.flush()
    text_blocks = []
    for block in response.content:
        if block.type == "text":
            text_blocks.append(block.text)
    return extract_json("\n".join(text_blocks)) if text_blocks else {}


def build_strategy(bill_data: dict, research: dict) -> dict:
    """Use Claude to build a negotiation strategy."""
    response = call_with_retry(client.messages.create,
        model=MODEL,
        max_tokens=300,
        system="""Return ONLY valid JSON. No other text:
{
  "opening_position": "string",
  "key_arguments": ["string"],
  "target_price": 0.00,
  "walkaway_threshold": 0.00
}""",
        messages=[{
            "role": "user",
            "content": f"Bill: {json.dumps(bill_data)}\nResearch: {json.dumps(research)}"
        }]
    )
    print(f"STRATEGY TOKENS - input: {response.usage.input_tokens}, output: {response.usage.output_tokens}")
    sys.stdout.flush()
    return extract_json(response.content[0].text)


def draft_negotiation_email(bill_data: dict, research: dict, strategy: dict, round_num: int = 1, previous_response: Optional[str] = None) -> dict:
    """Use Claude to draft a negotiation email."""
    account_number = bill_data.get("account_number") or "account on file"
    line_count = int(bill_data.get("line_count") or 1)
    line_context = ""
    if line_count > 1:
        line_context = f"\nUse {line_count}-line family plan comparisons only. Switching {line_count} lines is disruptive leverage."
    context = f"""Account number: {account_number}
Bill data: {json.dumps(bill_data)}
Research: {json.dumps(research)}
Strategy: {json.dumps(strategy)}
Round: {round_num}"""
    if previous_response:
        context += f"\nTheir previous response: {previous_response}"

    response = call_with_retry(client.messages.create,
        model=MODEL,
        max_tokens=1500,
        system=f"""You are writing a bill negotiation email AS THE CUSTOMER — a real person writing on their own behalf, not a lawyer or "professional negotiator." It should read like an actual email a smart, reasonable customer sends: natural, plain language, firm but friendly. Use contractions. Vary sentence length. No corporate boilerplate.

USE THE DATA AS PRIVATE CONTEXT, DON'T RECITE IT. The bill/research/strategy below is for you to reason from — it is NOT a list to paste into the email. Pick the ONE or TWO strongest, most natural points and build around them. A real person leads with their situation, not a spreadsheet.

GROUND IT IN WHAT THE CUSTOMER ACTUALLY KNOWS: how long they've been a customer, what they currently pay, that they're a reliable account. You may mention the market the way a normal person would ("I've seen comparable plans advertised for less") but do NOT cite precise competitor prices as hard quotes — those figures are estimates and exact numbers read as fake. Keep the ask concrete (a specific target amount), the reasoning human.

AVOID THESE ROBOTIC TELLS: "I am writing to formally request," opening with the account number, bullet-pointed demands, restating every stat, stiff sign-offs.

If this is a reply to their offer, acknowledge it like a person would ("Thanks for getting back to me — I appreciate you coming down to $X, but...") before countering.

Aim for this register (illustrative — use the REAL figures from the data):
---
Subject: Hoping to lower my monthly rate as a long-time customer

Hi,

I've been with you about three years and I've been happy with the service, but my bill's crept up to $95 a month and that's getting hard to justify. I've been looking around and there are clearly better rates out there for what I actually use.

I'd much rather stay than switch — can you get me down to around $70 a month? Happy to keep things as they are otherwise.

Thanks,
Sriya
---

Account number rule: use ONLY the exact account number provided. Never invent one. If none is provided, write "account on file."{line_context}

Return ONLY a valid JSON object with keys: subject, body, key_arguments_used, ask_amount, reasoning. No preamble, no markdown fences.""",
        messages=[{"role": "user", "content": context}]
    )
    print(f"EMAIL TOKENS - input: {response.usage.input_tokens}, output: {response.usage.output_tokens}")
    sys.stdout.flush()
    return extract_json(response.content[0].text)


def interpret_response(response_text: str, strategy: dict, history: list) -> dict:
    """Use Claude to interpret a company's response and decide next action."""
    response = call_with_retry(client.messages.create,
        model=MODEL,
        max_tokens=1000,
        system="""You are a negotiation expert analyzing a company's response.
Return ONLY a JSON object:
{
  "classification": "accepted/partial_offer/rejected/stalling/needs_info",
  "offered_amount": 55.00,
  "offered_details": "what they offered",
  "sentiment": "positive/neutral/negative",
  "decision": "accept/counter/escalate/close",
  "decision_reasoning": "detailed explanation of why",
  "next_ask": 49.99,
  "confidence": 0.85,
  "summary": "one sentence summary"
}
No preamble. JSON only.""",
        messages=[{
            "role": "user",
            "content": f"""Company response: {response_text}
Our strategy: {json.dumps(strategy)}
Negotiation history: {json.dumps(history)}
Analyze and decide next action."""
        }]
    )
    return extract_json(response.content[0].text)


def generate_final_summary(bill_data: dict, steps: list, outcome: str, savings: float) -> str:
    """Generate a human-readable summary of the negotiation."""
    response = call_with_retry(client.messages.create,
        model=MODEL,
        max_tokens=800,
        system="You are a concise writer. Summarize negotiation outcomes in 3-4 sentences. Be specific about what was achieved and why the strategy worked or didn't.",
        messages=[{
            "role": "user",
            "content": f"""Summarize this negotiation:
Original bill: ${bill_data.get('current_amount')} with {bill_data.get('provider')}
Outcome: {outcome}
Total savings: ${savings}/month
Steps taken: {len(steps)}
Key steps: {json.dumps([s.get('step_type') for s in steps])}"""
        }]
    )
    return response.content[0].text


def parse_bill_from_image(image_bytes: bytes, media_type: str) -> dict:
    """Use Claude vision to extract bill data from an image."""
    import base64
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = call_with_retry(client.messages.create,
        model=MODEL,
        max_tokens=1000,
        system="""You are a bill parsing expert. Extract structured data from bill images.
Return ONLY a JSON object with these exact fields:
{
  "provider": "company name",
  "bill_type": "internet/phone/insurance/subscription/rent/utility/other",
  "current_amount": 99.99,
  "account_tenure": "2 years 3 months",
  "contract_end": "March 2025 or null",
  "account_number": "last 4 digits or null",
  "line_count": 1,
  "services": ["list of services included"],
  "payment_history": "good/unknown",
  "key_details": "any other important details"
}
line_count: count the number of phone lines or service lines on this bill. For a single person internet/cable bill this is 1. For a wireless family plan count each phone number listed as a separate line.
No preamble. No markdown. JSON only.""",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Extract all billing information from this bill image."
                }
            ],
        }]
    )
    return extract_json(response.content[0].text)
